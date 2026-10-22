"""Explicit local receiving of one pinned VALIDATED snapshot, never authorization.

No extraction, discovery, fallback, cache, upstream jobs or production gate API.
The 1e-12 comparison is the technical audit policy, not production approval.
"""

from dataclasses import dataclass
import csv
import hashlib
import io
import json
import math
import ntpath
from pathlib import Path, PurePosixPath
import stat
import zipfile

import pyarrow as pa
import pyarrow.parquet as pq


EXPECTED_SHA256 = "d70cda5639478977cd028dc61411e3d8cf1430a886ac99f27834f44e4d04b004"
RUN_ID = "tv2_q01_q04_q08_official_20261022_01"
D06_RUN = "official_20261021_a9dddfe4"
TAXONOMY_SHA = "1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874"
INPUT_DIGEST = "17ae5383e848f7323b99800bd3d79a72e84e2bca62844f66dd00aaa06e80a9b2"
SOURCE_COMMIT = "3c7c6285a59af8ae9eebfdc2d3667f3fcff92180"
ROOT = "TV2_Q01_HANDOFF_TV3_20261022/"
PART = "q01_role_groups.parquet/part-00000-eec9e245-8fcb-43e4-8bd2-fb90b682f011-c000.snappy.parquet"
COLUMNS = ("category", "job_count", "denominator_all_it", "denominator_known",
           "share_all_it", "share_known")
DOMAIN = frozenset(("SOFTWARE", "DATA_AI", "NETWORK_SYSTEMS", "DEVOPS_CLOUD",
                    "SECURITY", "IT_SUPPORT", "QA_TESTING", "IT_BUSINESS",
                    "IT_MANAGEMENT", "IT_OTHER"))
SCHEMAS = ("q01_role_groups", "q02_experience", "q03_location", "q04_remote_flag",
           "q04_work_type_crosscheck", "q04_work_type", "q08_listed_month",
           "q08_listed_week_start_utc", "q08_original_month", "q08_original_week_start_utc")
MEMBERS = frozenset(("DATA_CONTRACT_Q01.md", "PACKAGE_MANIFEST.json", "README_TV3.md",
                     "SHA256_INVENTORY.json", "manifest.json", "q01_handoff_manifest.json",
                     "q01_official_validation_20261022.md", "q01_role_groups.csv",
                     "q01_role_groups.parquet/_SUCCESS", PART,
                     "independent_validation/completion.json", "independent_validation/validation.json",
                     *("independent_validation/" + name + "_schema.json" for name in SCHEMAS)))
MAX_BYTES = 2_000_000


@dataclass(frozen=True, slots=True)
class PreviewRow:
    category: str
    job_count: int
    denominator_all_it: int
    denominator_known: int
    share_all_it: float
    share_known: float


@dataclass(frozen=True, slots=True)
class PreviewResult:
    passed: bool
    issue: str
    rows: tuple[PreviewRow, ...] = ()


class _Rejected(Exception):
    pass


def _require(condition, code):
    if not condition:
        raise _Rejected(code)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "INVALID_JSON")
        result[key] = value
    return result


def _invalid_constant(_):
    raise _Rejected("INVALID_JSON")


def _receive(data):
    _require(_sha(data) == EXPECTED_SHA256, "ARCHIVE_HASH_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        _require(len(entries) == 22, "UNSAFE_ARCHIVE")
        seen = set()
        for entry in entries:
            name = entry.filename.replace("\\", "/")
            mode = stat.S_IFMT(entry.external_attr >> 16)
            _require(not name.startswith("/") and not ntpath.splitdrive(name)[0]
                     and ".." not in PurePosixPath(name).parts and ":" not in name
                     and "\\" not in entry.filename and name.casefold() not in seen
                     and mode in (0, stat.S_IFREG) and not entry.is_dir()
                     and not entry.flag_bits & 1
                     and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                     and entry.file_size <= MAX_BYTES, "UNSAFE_ARCHIVE")
            seen.add(name.casefold())
        _require(sum(e.file_size for e in entries) <= MAX_BYTES
                 and {e.filename for e in entries} == {ROOT + n for n in MEMBERS}, "UNSAFE_ARCHIVE")
        _require(archive.testzip() is None, "ARCHIVE_CRC_FAILED")
        payload = {n: archive.read(ROOT + n) for n in MEMBERS}

    def document(name):
        return json.loads(payload[name].decode("utf-8-sig"), object_pairs_hook=_object,
                          parse_constant=_invalid_constant)

    inventory = document("SHA256_INVENTORY.json")
    items = inventory["files"]
    paths = [e["path"] for e in items]
    _require(inventory["algorithm"] == "SHA256" and inventory["excludes_self"] is True
             and len(paths) == len(set(paths))
             and set(paths) == MEMBERS - {"SHA256_INVENTORY.json"}, "INVENTORY_MISMATCH")
    for entry in items:
        raw = payload[entry["path"]]
        _require(type(entry["bytes"]) is int and len(raw) == entry["bytes"]
                 and _sha(raw) == entry["sha256"], "INVENTORY_MISMATCH")

    package = document("PACKAGE_MANIFEST.json")
    manifest = document("manifest.json")
    handoff = document("q01_handoff_manifest.json")
    validation = document("independent_validation/validation.json")
    seal = document("independent_validation/completion.json")
    for obj in (package, manifest, handoff, validation, seal):
        _require(obj["run_id"] == RUN_ID, "RUN_MISMATCH")
    for obj in (package, handoff, validation, seal, validation["q01"]):
        _require(obj["business_accepted"] is False if "business_accepted" in obj
                 else obj["accepted"] is False, "ACCEPTANCE_MISMATCH")
    _require(package["q01_status"] == handoff["status"] == validation["q01_status"]
             == validation["q01"]["status"] == "VALIDATED"
             and validation["status"] == seal["status"] == "PASS"
             and handoff["accepted_by"] is None
             and package["business_group_acceptance"] == "PENDING", "ACCEPTANCE_MISMATCH")
    taxonomy = [{"taxonomy_version": "0.2.2", "taxonomy_sha256": TAXONOMY_SHA}]
    _require(package["taxonomy_version"] == "0.2.2" and package["taxonomy_sha256"] == TAXONOMY_SHA
             and handoff["taxonomy"] == manifest["provenance"]["taxonomy"] == taxonomy
             and validation["q01"]["taxonomy_version"] == "0.2.2"
             and validation["q01"]["taxonomy_sha256"] == TAXONOMY_SHA
             and {g["code"] for g in validation["taxonomy_groups"]} == DOMAIN, "TAXONOMY_MISMATCH")
    _require(package["source_commit"] == handoff["source_commit"] == validation["commit"] == SOURCE_COMMIT
             and handoff["confirmed_input_digest"] == validation["input_digest"]
             == manifest["input_contract"]["d06_confirmation"]["input_sha256"] == INPUT_DIGEST
             and D06_RUN in payload["q01_official_validation_20261022.md"].decode("utf-8-sig"), "LINEAGE_MISMATCH")
    _require(seal["validation_sha256"] == _sha(payload["independent_validation/validation.json"])
             and seal["runner_manifest_sha256"] == validation["runner_manifest_sha256"]
             == _sha(payload["manifest.json"]), "EVIDENCE_BINDING_MISMATCH")
    originals = package["original_source_bytes"]
    _require(set(originals) == MEMBERS - {"SHA256_INVENTORY.json", "PACKAGE_MANIFEST.json",
                                         "README_TV3.md", "DATA_CONTRACT_Q01.md"}, "EVIDENCE_BINDING_MISMATCH")
    for mapping in (originals, handoff["evidence"]):
        for name, digest in mapping.items():
            _require(name in payload and _sha(payload[name]) == digest, "EVIDENCE_BINDING_MISMATCH")
    checks = validation["checks"]
    _require(len(checks) == 94 and all(c["pass"] is True for c in checks.values())
             and checks["exact_d06_accept_population"]["detail"] == {"missing": 0, "extra": 0}, "VALIDATION_FAILED")
    for obj in (package, handoff, validation["q01"]):
        _require(all(type(obj[k]) is int and obj[k] == v for k, v in
                     (("N", 5206), ("K", 5206), ("missing", 0))), "POPULATION_MISMATCH")
    directory = [[name.split("/", 1)[1], len(payload[name]), _sha(payload[name])]
                 for name in sorted((PART, "q01_role_groups.parquet/_SUCCESS"))]
    digest = _sha(json.dumps(directory, separators=(",", ":")).encode())
    _require(digest == package["q01_parquet_artifact_digest"] == handoff["physical_table"]["parquet_sha256"]
             == manifest["tables"]["q01_role_groups"]["parquet_sha256"]
             and _sha(payload["q01_role_groups.csv"]) == package["q01_csv_sha256"]
             == handoff["physical_table"]["csv_sha256"], "OUTPUT_BINDING_MISMATCH")

    # No protected table decoding occurs until archive, identity and evidence pass.
    parquet = pq.ParquetFile(io.BytesIO(payload[PART]))
    _require(parquet.metadata.num_rows == 10, "INVALID_ROWS")
    types = (pa.string(), pa.int64(), pa.int32(), pa.int32(), pa.float64(), pa.float64())
    _require(parquet.schema_arrow.names == list(COLUMNS)
             and tuple(f.type for f in parquet.schema_arrow) == types
             and tuple(f.nullable for f in parquet.schema_arrow) == (True, False, False, False, True, True),
             "INVALID_PHYSICAL_SCHEMA")
    readback = document("independent_validation/q01_role_groups_schema.json")
    _require(readback == {"type": "struct", "fields": [
        {"name": n, "type": t, "nullable": True, "metadata": {}}
        for n, t in zip(COLUMNS, ("string", "long", "integer", "integer", "double", "double"))]},
        "INVALID_READBACK_SCHEMA")
    records = parquet.read().to_pylist()
    seen = set()
    for row in records:
        category = row["category"]
        _require(type(category) is str and category in DOMAIN and category not in seen, "INVALID_CATEGORY")
        seen.add(category)
        n, N, K = (row[name] for name in COLUMNS[1:4])
        _require(type(n) is int and 0 < n <= 5206 and type(N) is int and type(K) is int
                 and N == K == 5206, "INVALID_COUNTS")
        for name, denominator in (("share_all_it", N), ("share_known", K)):
            rate = row[name]
            _require(type(rate) is float and math.isfinite(rate) and 0 <= rate <= 1
                     and math.isclose(rate, n / denominator, rel_tol=1e-12, abs_tol=1e-12), "INVALID_RATE")
    _require(seen == DOMAIN and sum(r["job_count"] for r in records) == 5206
             and next(r["job_count"] for r in records if r["category"] == "IT_OTHER") == 77,
             "CONSERVATION_MISMATCH")
    csv_rows = list(csv.DictReader(io.StringIO(payload["q01_role_groups.csv"].decode("utf-8-sig"))))
    _require(len(csv_rows) == 10 and tuple(csv_rows[0]) == COLUMNS, "CSV_MISMATCH")
    by_category = {r["category"]: r for r in records}
    _require(len({r["category"] for r in csv_rows}) == 10, "CSV_MISMATCH")
    for row in csv_rows:
        target = by_category.get(row["category"])
        _require(target is not None and all(int(row[k]) == target[k] for k in COLUMNS[1:4])
                 and all(float(row[k]) == target[k] for k in COLUMNS[4:]), "CSV_MISMATCH")
    return PreviewResult(True, "", tuple(PreviewRow(**r) for r in
                                        sorted(records, key=lambda r: (-r["job_count"], r["category"]))))


def load_q01_preview(local_path: str, *, confirmed: bool = False) -> PreviewResult:
    """Read only after explicit confirmation; failures return no partial rows.

    This receipt permits technical preview of the pinned artifact only. It does
    not authenticate organizational authority or prove the analyzer's input keys.
    """
    if confirmed is not True:
        return PreviewResult(False, "CONFIRMATION_REQUIRED")
    try:
        _require(type(local_path) is str and bool(local_path.strip())
                 and not local_path.startswith(("\\\\", "//")), "INVALID_LOCAL_PATH")
        path = Path(local_path)
        _require(path.is_absolute() and path.suffix.lower() == ".zip"
                 and not path.is_symlink() and path.is_file(), "INVALID_LOCAL_PATH")
        _require(path.stat().st_size <= MAX_BYTES, "ARCHIVE_TOO_LARGE")
        with path.open("rb") as source:
            data = source.read(MAX_BYTES + 1)
        _require(len(data) <= MAX_BYTES, "ARCHIVE_TOO_LARGE")
        return _receive(data)
    except _Rejected as error:
        return PreviewResult(False, error.args[0])
    except Exception:
        # No exception text, local paths, arbitrary ZIP content or partial rows.
        return PreviewResult(False, "UNREADABLE_OR_INVALID_ARTIFACT")
