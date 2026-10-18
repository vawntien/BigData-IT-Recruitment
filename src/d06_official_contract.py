"""Frozen Official v1 contract and external human-approval gate. No approvals minted here."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from d06_taxonomy_adapter import CONFIG_HASH, TV2_COMMIT
from d06_pilot_packaging import verified_members
from d06_pilot_runtime import PilotIntegrityError

ROWS = 123849
SCHEMA_VERSION = "d06-official-v1"
SCHEMA_SHA = "44ee9bcc29f5ace90161b6bea67d6543ced30925944761f56e28c7df76a67a68"
HELPER_HASHES = {
    "d06_taxonomy_adapter.py": "d79ee515ada7c2cdb96764244fa35e4c9c90b093480d8940dee5326f29019f49",
    "d06_pilot_runtime.py": "48a7732b5763c6d7e0f2d7df344cb316b40e01e24dbaddaa94a51a7dde0fbfd4",
    "parity_schema.json": "83c04c144d3d2b516d8e4fe5338fab250136e5179c85c96441b43b24e3594b2a",
}


class ApprovalRequired(PermissionError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf8")


def official_schema(root):
    from pyspark.sql.types import StructType
    value = json.loads((Path(root) / "data/audit/d06/pilot_spark_schema.json").read_text(encoding="utf8"))
    if sha(json_bytes(value)) != SCHEMA_SHA:
        raise PilotIntegrityError("Frozen production schema fingerprint mismatch")
    return StructType.fromJson(value)


def checked_package(path, checksum):
    if not path or not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise PilotIntegrityError("Explicit immutable --package and SHA-256 required")
    members = verified_members(path, checksum)
    if len(members) != 8:
        raise PilotIntegrityError("Unexpected runtime package members")
    for name, expected in HELPER_HASHES.items():
        if sha(members[name]) != expected:
            raise PilotIntegrityError(f"Unreviewed runtime helper/schema: {name}")
    return members


def safe_destination(root, run_id, output=None, scope="FULL"):
    if scope not in ("FULL", "TEST"):
        raise ValueError("Unknown execution scope")
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("Invalid run_id")
    parent = root / ("data/processed/d06/v0.2.2" if scope == "FULL" else "tmp/d06_official_tests")
    expected = parent / run_id
    target = Path(output).absolute() if output is not None else expected
    if (target != expected or not expected.resolve().is_relative_to(root)
            or target.resolve() != expected.resolve() or target == parent):
        raise ValueError("Destination must match dedicated version/run_id namespace")
    for p in [target, *target.parents]:
        if p.is_symlink() or (p.exists() and getattr(p.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Reparse point/symlink destination refused")
    if target.exists():
        raise FileExistsError("Run already exists, including incomplete runs; choose NEW run_id")
    return target.resolve()


def _approval(path, checksum, kind):
    if not path or not checksum:
        raise ApprovalRequired(f"Missing external {kind} approval and exact file SHA-256")
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise ApprovalRequired(f"Missing/unreadable external {kind} approval") from exc
    if sha(data) != checksum:
        raise ApprovalRequired(f"{kind} approval file hash mismatch")
    doc = json.loads(data)
    if (doc.get("kind") != kind or doc.get("status") != "APPROVED"
            or not isinstance(doc.get("approved_by"), str) or not doc["approved_by"].strip()
            or not doc.get("decision_id")):
        raise ApprovalRequired(f"{kind}: responsible human decision missing")
    try:
        when = datetime.fromisoformat(doc["approved_at"].replace("Z", "+00:00"))
        if when.tzinfo is None or when > datetime.now(timezone.utc):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise ApprovalRequired(f"{kind}: invalid approval timestamp")
    if doc.get("taxonomy_version") != "0.2.2" or doc.get("taxonomy_sha256") != CONFIG_HASH:
        raise ApprovalRequired(f"{kind}: taxonomy version/hash mismatch")
    return doc


@dataclass(frozen=True)
class _FullGrant:
    run_id: str
    input_fingerprint: str
    output_relative: str
    package_sha256: str
    documents: dict


def require_approvals(args):
    """Fail BEFORE Spark/full classification. Files are trusted human records, not electronic signatures.

    This code checks consistency, not the reviewer's organizational authority.
    Approval files/workbook must be supplied externally; tests never create APPROVED records.
    """
    if not args.execute_full:
        raise ApprovalRequired("Explicit --execute-full authorization is missing")
    a04 = _approval(args.a04_approval, args.a04_approval_sha256, "A04_BUSINESS")
    if a04.get("tv2_commit") != TV2_COMMIT or a04.get("accepted_v022_limitations") is not True:
        raise ApprovalRequired("A04 limitations/pinned code have not been accepted")
    workbook = a04.get("main_workbook", {})
    if (not workbook.get("path") or not workbook.get("sha256")
            or sha(Path(workbook["path"]).read_bytes()) != workbook["sha256"]
            or a04.get("manual_review_completed") is not True):
        raise ApprovalRequired("Main reviewed workbook missing/unverified")
    schema = _approval(args.schema_approval, args.schema_approval_sha256, "D06_SCHEMA")
    if schema.get("schema_version") != SCHEMA_VERSION or schema.get("schema_sha256") != SCHEMA_SHA:
        raise ApprovalRequired("Production schema not approved")
    run = _approval(args.run_authorization, args.run_authorization_sha256, "D06_FULL_RUN")
    if (run.get("run_id") != args.run_id or run.get("expected_rows") != ROWS
            or run.get("package_sha256") != args.package_sha256
            or not re.fullmatch(r"[0-9a-f]{64}", run.get("input_fingerprint", ""))
            or run.get("a04_approval_sha256") != args.a04_approval_sha256
            or run.get("schema_approval_sha256") != args.schema_approval_sha256
            or run.get("schema_sha256") != SCHEMA_SHA):
        raise ApprovalRequired("Run-specific user authorization/input binding missing")
    return _FullGrant(args.run_id, run["input_fingerprint"], run.get("output_relative", ""),
                      args.package_sha256, {"a04": args.a04_approval_sha256,
                        "schema": args.schema_approval_sha256, "run": args.run_authorization_sha256})
