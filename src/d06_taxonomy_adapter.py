"""Lossless, local-mode D06 transport for the unmodified TV2 classifier.

Schema is derived from every frozen prediction, not Spark's dict/map inference.
Each struct carries its original keys: an absent key is NOT a JSON null.
No classifier rules, labels, or reference predictions are used by workers.
"""
from __future__ import annotations

import hashlib
import importlib
import re
import sys
from pathlib import Path

TV2_COMMIT = "e437dcc11dda61f847673b9cc8c5801886c1996d"
CONFIG_HASH = "1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874"
CODE_HASHES = {
    "it_taxonomy.py": "841231033c546cc2bedf141386038104c0a0f1cf9f5a01b80535457c8b42312f",
    "description_processing.py": "ad579397753f2de115faad3bf9ff4d1c8dfebf5ce76eb898f3368ca02a6fec78",
    "it_taxonomy_v010.py": "453bb6bcd22d4cdf866c670f3634b8f1e42a233eb086b650e579b4b1d429dc86",
    "tv2_csv.py": "7839763017c281c36126b8ece9c2015da41b54cccdfca0f365ac4feb48beb903",
}
PRESENCE = "_d06_present"
WORKER_FIELDS = {"_d06_partition_id", "_d06_worker_pid", "_d06_classifier_instance"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bigint_string(value) -> str:
    """Accept bigint or canonical numeric string, reject lossy/coercive inputs."""
    if type(value) is int:
        result = value
    elif type(value) is str and re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        result = int(value)
        if str(result) != value:
            raise ValueError("Noncanonical job_id")
    else:
        raise ValueError("job_id must be a non-null bigint or canonical numeric string")
    if not -(2**63) <= result < 2**63:
        raise ValueError("job_id outside signed bigint")
    return str(result)


def load_model(snapshot: str | Path):
    snapshot = Path(snapshot).resolve()
    for name, expected in CODE_HASHES.items():
        if digest((snapshot / name).read_bytes()) != expected:
            raise ValueError(f"TV2 code hash mismatch: {name}")
    config = snapshot / "it_taxonomy_v0.2.2.json"
    if digest(config.read_bytes()) != CONFIG_HASH:
        raise ValueError("Candidate config hash mismatch")
    sys.path.insert(0, str(snapshot))
    # Refuse an already-imported different implementation; never silently shadow it.
    for name in CODE_HASHES:
        module = sys.modules.get(Path(name).stem)
        if module and Path(module.__file__).resolve() != snapshot / name:
            raise ValueError(f"Foreign TV2 module already loaded: {name}")
    model = importlib.import_module("it_taxonomy").Taxonomy(config)
    if model.version != "0.2.2" or model.sha256 != CONFIG_HASH:
        raise ValueError("Classifier version/hash mismatch")
    return model


def classify(model, job_id, title: str, description: str) -> dict:
    if type(title) is not str or type(description) is not str:
        raise ValueError("Frozen source text must be strings, without normalization")
    result = model.classify(title, description, bigint_string(job_id))
    result.update(title=title, description=description,
                  source_title_sha256=digest(title.encode("utf-8")),
                  source_description_sha256=digest(description.encode("utf-8")))
    if result["taxonomy_version"] != "0.2.2" or result["taxonomy_sha256"] != CONFIG_HASH:
        raise ValueError("Prediction version/hash mismatch")
    if result["it_decision"] not in ("ACCEPT", "REJECT", "REVIEW"):
        raise ValueError("Unknown decision")
    expected = {"ACCEPT": True, "REJECT": False, "REVIEW": None}[result["it_decision"]]
    if result["is_it"] is not expected:
        raise ValueError("Decision/is_it contract violation")
    return result


def derive_schema(records: list[dict]):
    """Union actual object keys/types; explicit code-backed types for empty arrays.

    The 176 records have no parser issues or removed script/style ranges. Their
    element types below come from description_processing.py at the pinned commit.
    Unknown empty/all-null fields fail closed instead of being silently strings.
    """
    from pyspark.sql import types as T

    empty_types = {
        "description_processing.parser_issues": T.StringType(),
        "description_processing.removed_source_ranges": T.StructType([
            T.StructField("start", T.LongType(), True),
            T.StructField("end", T.LongType(), True),
            T.StructField("reason", T.StringType(), True),
            T.StructField(PRESENCE, T.ArrayType(T.StringType(), False), False),
        ]),
    }

    def infer(values, path):
        values = [v for v in values if v is not None]
        kinds = {type(v) for v in values}
        if not values or len(kinds) != 1:
            raise ValueError(f"Unobserved or conflicting types at {path}: {kinds}")
        kind = type(values[0])
        if kind is dict:
            keys = sorted({k for v in values for k in v})
            if PRESENCE in keys or WORKER_FIELDS.intersection(keys):
                raise ValueError("Reserved transport field collision")
            fields = []
            for key in keys:
                p = f"{path}.{key}" if path else key
                data_type = T.LongType() if p == "job_id" else infer(
                    [v.get(key) for v in values], p)
                nullable = any(key not in v or v[key] is None for v in values)
                fields.append(T.StructField(key, data_type, nullable))
            fields.append(T.StructField(PRESENCE, T.ArrayType(T.StringType(), False), False))
            return T.StructType(fields)
        if kind is list:
            items = [x for v in values for x in v]
            element = infer(items, path + "[]") if items else empty_types.get(path)
            if element is None:
                raise ValueError(f"Undeclared empty array type at {path}")
            return T.ArrayType(element, any(x is None for x in items))
        types = {str: T.StringType, bool: T.BooleanType, int: T.LongType}
        if kind not in types:
            raise ValueError(f"Unsupported type at {path}: {kind}")
        return types[kind]()

    schema = infer(records, "")
    for name, typ in [("_d06_partition_id", T.LongType()),
                      ("_d06_worker_pid", T.LongType()),
                      ("_d06_classifier_instance", T.StringType())]:
        schema.add(T.StructField(name, typ, False))
    return schema


def encode(record: dict, schema) -> dict:
    """Encode every leaf into typed structs; retain key presence at every level."""
    from pyspark.sql import types as T

    def visit(value, typ, path):
        if value is None:
            return None
        if isinstance(typ, T.StructType):
            allowed = {f.name for f in typ} - {PRESENCE} - WORKER_FIELDS
            if set(value) - allowed:
                raise ValueError(f"Unmodelled fields at {path}: {set(value) - allowed}")
            result = {f.name: visit(value[f.name], f.dataType, path + "." + f.name)
                      if f.name in value else None for f in typ if f.name not in WORKER_FIELDS}
            result[PRESENCE] = sorted(value)
            return result
        if isinstance(typ, T.ArrayType):
            return [visit(x, typ.elementType, path + "[]") for x in value]
        return int(bigint_string(value)) if path == ".job_id" else value

    return visit(record, schema, "")


def decode(row) -> dict:
    """Reconstruct JSON from typed data, NOT a serialized prediction backup."""
    if hasattr(row, "asDict"):
        row = row.asDict(recursive=True)

    def visit(value):
        if isinstance(value, dict):
            keys = value[PRESENCE]
            return {k: visit(value[k]) for k in keys}
        if isinstance(value, list):
            return [visit(x) for x in value]
        return value

    result = visit(row)
    result["job_id"] = bigint_string(result["job_id"])
    return result


def differences(expected, actual, path="$") -> list[dict]:
    """Strict JSON equality: distinguish bool/int, missing/null, ordered arrays."""
    if type(expected) is not type(actual):
        return [{"field": path, "expected": expected, "actual": actual}]
    if isinstance(expected, dict):
        out = []
        for key in sorted(set(expected) | set(actual)):
            if key not in expected or key not in actual:
                out.append({"field": path + "." + key,
                            "expected": expected.get(key, {"_missing": True}),
                            "actual": actual.get(key, {"_missing": True})})
            else:
                out.extend(differences(expected[key], actual[key], path + "." + key))
        return out
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [{"field": path, "expected": expected, "actual": actual}]
        return [d for i, (e, a) in enumerate(zip(expected, actual))
                for d in differences(e, a, f"{path}[{i}]")]
    return [] if expected == actual else [{"field": path, "expected": expected, "actual": actual}]


def partition_runner(snapshot: str, adapter_dir: str, schema_json: dict):
    """Local-mode closure. Only code/config paths travel; no expected predictions.

    All workers share this machine's verified snapshot. This is not a claim of
    cluster deployment readiness; remote executors require packaged resources.
    """
    def run(rows):
        import os
        import sys
        import uuid
        sys.path.insert(0, adapter_dir)
        from pyspark import TaskContext
        from pyspark.sql.types import StructType
        from d06_taxonomy_adapter import load_model, classify, encode
        model = load_model(snapshot)  # exactly once per executed partition
        schema = StructType.fromJson(schema_json)
        instance = str(uuid.uuid4())
        partition = TaskContext.get().partitionId()
        for row in rows:
            result = encode(classify(model, row.job_id, row.title, row.description), schema)
            result.update(_d06_partition_id=partition, _d06_worker_pid=os.getpid(),
                          _d06_classifier_instance=instance)
            yield result
    return run
