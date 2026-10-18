"""Append-only run evidence. No directory rename, resume, append-data or overwrite."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from d06_official_contract import sha, json_bytes


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def exclusive_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(json_bytes(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def parquet_fingerprint(directory):
    directory = Path(directory).resolve()
    files = sorted(directory.rglob("*.parquet"))
    if not files or not (directory / "_SUCCESS").is_file():
        raise ValueError("Incomplete Parquet dataset: no files/_SUCCESS")
    entries = []
    for p in files:
        if any(part.startswith(("_temporary", ".")) for part in p.relative_to(directory).parts):
            raise ValueError("Uncommitted Parquet file in inventory")
        if p.is_symlink():
            raise ValueError("Symlink Parquet input refused")
        s = p.stat()
        checksum = file_sha(p)
        if (s.st_size, s.st_mtime_ns) != (p.stat().st_size, p.stat().st_mtime_ns):
            raise ValueError("Dataset changed during fingerprint")
        entries.append({"path": p.relative_to(directory).as_posix(), "bytes": s.st_size, "sha256": checksum})
    return {"fingerprint": sha(json_bytes(entries)), "files": entries,
            "bytes": sum(x["bytes"] for x in entries)}


class RunJournal:
    def __init__(self, path, manifest):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=False)
        self.sequence = 0
        exclusive_json(self.path / "run_manifest.json", {**manifest, "started_utc": utcnow()})
        self.event("RUNNING")

    def event(self, status, **metadata):
        self.sequence += 1
        exclusive_json(self.path / "events" / f"{self.sequence:04d}_{status}.json",
                       {"status": status, "at_utc": utcnow(), **metadata})

    def fail(self, exc, stage):
        # No raw texts / full Spark exception traceback in publish metadata.
        text = str(exc)
        category = "DATA_OR_CONTRACT" if "PilotDataError" in text or isinstance(exc, ValueError) else "RUNTIME"
        exclusive_json(self.path / "failure.json", {"status": "FAILED", "stage": stage,
            "type": type(exc).__name__, "category": category, "at_utc": utcnow(),
            "message": "Run aborted. Inspect protected execution logs; failed jobs were not converted to REVIEW."})
        self.event("FAILED", stage=stage)

    def complete(self, validation, inventory):
        if validation.get("status") != "PASS":
            raise ValueError("Cannot publish failed validation")
        exclusive_json(self.path / "validation.json", validation)
        exclusive_json(self.path / "output_inventory.json", inventory)
        self.event("VALIDATED")
        manifest = json.loads((self.path / "run_manifest.json").read_text(encoding="utf8"))
        # Last publication operation. A partially written JSON is rejected by inspect_run.
        exclusive_json(self.path / "completion.json", {"status": "SUCCEEDED",
            "scope": manifest["scope"], "run_id": manifest["run_id"], "finished_utc": utcnow(),
            "manifest_sha256": file_sha(self.path / "run_manifest.json"),
            "validation_sha256": file_sha(self.path / "validation.json"),
            "inventory_sha256": file_sha(self.path / "output_inventory.json"),
            "data_fingerprint": inventory["fingerprint"], "rows": validation["rows"]})


def inspect_run(path):
    """Fail closed; _SUCCESS alone is NOT a successful D06 run."""
    path = Path(path)
    if not path.is_dir():
        return {"status": "ABSENT"}
    if (path / "failure.json").exists():
        return {"status": "FAILED"}
    try:
        completion = json.loads((path / "completion.json").read_text(encoding="utf8"))
        manifest = json.loads((path / "run_manifest.json").read_text(encoding="utf8"))
        validation = json.loads((path / "validation.json").read_text(encoding="utf8"))
        if completion["status"] != "SUCCEEDED" or validation["status"] != "PASS":
            raise ValueError("Invalid publication states")
        for name, key in [("run_manifest.json", "manifest_sha256"),
                          ("validation.json", "validation_sha256"), ("output_inventory.json", "inventory_sha256")]:
            if file_sha(path / name) != completion[key]:
                raise ValueError("Publication metadata changed")
        inventory = parquet_fingerprint(path / "predictions")
        if (inventory["fingerprint"] != completion["data_fingerprint"] or
                completion["run_id"] != manifest["run_id"] or
                completion["rows"] != validation["rows"] or
                validation["rows"] != manifest["expected_rows"] or
                validation.get("unique") != validation["rows"] or
                sum(validation.get("decision_counts", {}).values()) != validation["rows"] or
                validation.get("nested_roundtrip_checked") != validation["rows"] or
                validation.get("all_present") is not True or
                validation.get("missing") != 0 or validation.get("extra") != 0 or
                validation.get("nulls") != 0 or validation.get("errors") != 0):
            raise ValueError("Publication reconciliation mismatch")
        return {"status": "SUCCEEDED", "scope": manifest["scope"], "rows": validation["rows"],
                "run_id": manifest["run_id"], "data_fingerprint": inventory["fingerprint"]}
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "INCOMPLETE_OR_CORRUPT"}
