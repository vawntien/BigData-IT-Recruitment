"""Pilot transport, lossless schema bridge and worker-side validation.

The Phase1 adapter is reused unchanged. Top-level _d06_present is Boolean;
original-key metadata is moved to _d06_field_keys at every struct level.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from pathlib import Path

from d06_taxonomy_adapter import (
    CONFIG_HASH, PRESENCE, WORKER_FIELDS, bigint_string, classify, decode,
    differences, encode, load_model,
)

FIELD_KEYS = "_d06_field_keys"
METRICS = {"_d06_prediction_sha256", "_d06_classify_ns", "_d06_python_rss_bytes", "_d06_description_chars"}


class PilotDataError(ValueError):
    """Bad input/contract; never translate to machine REVIEW."""


class PilotIntegrityError(ValueError):
    """Wrong/missing package/config/schema."""


def prediction_digest(prediction):
    return hashlib.sha256(json.dumps(prediction, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf8")).hexdigest()


def rename_keys(value, old, new):
    if isinstance(value, dict):
        return {new if k == old else k: rename_keys(v, old, new) for k, v in value.items()}
    if isinstance(value, list):
        return [rename_keys(v, old, new) for v in value]
    return value


def pilot_schema(parity_json):
    from pyspark.sql import types as T
    def visit(value):
        if isinstance(value, dict):
            return {k: FIELD_KEYS if k == "name" and v == PRESENCE else visit(v) for k, v in value.items()}
        if isinstance(value, list):
            return [visit(v) for v in value]
        return value
    schema = T.StructType.fromJson(visit(parity_json))
    schema.add(T.StructField(PRESENCE, T.BooleanType(), False))
    for name in sorted(METRICS):
        typ = T.StringType() if name == "_d06_prediction_sha256" else T.LongType()
        schema.add(T.StructField(name, typ, name == "_d06_python_rss_bytes"))
    return schema


def encode_pilot(prediction, parity_schema):
    encoded = rename_keys(encode(prediction, parity_schema), PRESENCE, FIELD_KEYS)
    encoded[PRESENCE] = True
    return encoded


def decode_pilot(row):
    value = row.asDict(recursive=True) if hasattr(row, "asDict") else dict(row)
    if value.pop(PRESENCE, None) is not True:
        raise PilotDataError("Missing classification output, not REVIEW")
    for key in METRICS | WORKER_FIELDS:
        value.pop(key, None)
    return decode(rename_keys(value, FIELD_KEYS, PRESENCE))


def validate_prediction(result):
    job = bigint_string(result["job_id"])
    if result["taxonomy_version"] != "0.2.2" or result["taxonomy_sha256"] != CONFIG_HASH:
        raise PilotIntegrityError("Wrong prediction version/hash")
    decision = result["it_decision"]
    if decision not in ("ACCEPT", "REJECT", "REVIEW"):
        raise PilotDataError("Unknown classifier decision")
    if result["is_it"] is not {"ACCEPT": True, "REJECT": False, "REVIEW": None}[decision]:
        raise PilotDataError("Unexpected REVIEW/null conversion")
    for field in ("title", "description"):
        text = result[field]
        if type(text) is not str:
            raise PilotDataError("Null source text must not be silently normalized")
        if hashlib.sha256(text.encode("utf8")).hexdigest() != result["source_" + field + "_sha256"]:
            raise PilotDataError(f"Source hash mismatch: {job}/{field}")
    if result["description_processing"]["source_sha256"] != result["source_description_sha256"]:
        raise PilotDataError("Parser source hash differs")

    def ranges(values, text):
        for pair in values:
            if (not isinstance(pair, list) or len(pair) != 2 or any(type(x) is not int for x in pair)
                    or not 0 <= pair[0] <= pair[1] <= len(text)):
                raise PilotDataError("Raw Unicode codepoint range outside source")
    for hit in result["match_evidence"]:
        text = result[hit["field"]]
        start, end = hit["raw_excerpt_start"], hit["raw_excerpt_end"]
        ranges([[start, end]], text)
        if text[start:end] != hit["excerpt"]:
            raise PilotDataError("Raw excerpt/Unicode offset mismatch")
        ranges(hit["raw_match_ranges"], text)
    for segment in result["description_segments"]:
        ranges(segment["raw_ranges"], result["description"])
    for removed in result["description_processing"]["removed_source_ranges"]:
        ranges([[removed["start"], removed["end"]]], result["description"])


def current_rss():
    """Observed current working set, not JVM heap or total-machine memory."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        api = ctypes.WinDLL("psapi", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        api.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        if api.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize
    return None  # explicitly unavailable on uninstrumented platforms


def verify_roundtrip_partition(rows):
    """Distributed full typed reconstruction/hash check, no prediction collect."""
    checked = 0
    for row in rows:
        prediction = decode_pilot(row)
        validate_prediction(prediction)
        if prediction_digest(prediction) != row["_d06_prediction_sha256"]:
            raise PilotDataError("Nested serialization/Parquet mismatch")
        checked += 1
    yield checked


def classify_partition(rows, snapshot, parity_json):
    import uuid
    from pyspark import TaskContext
    from pyspark.sql.types import StructType
    schema = StructType.fromJson(parity_json)
    try:
        model = load_model(snapshot)  # one instance per executed partition
    except ValueError as exc:
        raise PilotIntegrityError("Worker classifier/config integrity failure") from exc
    instance, partition = str(uuid.uuid4()), TaskContext.get().partitionId()
    for row in rows:
        try:
            title, description = row.source_title, row.source_description
            if type(title) is not str or type(description) is not str:
                raise PilotDataError("Missing source field, not empty string")
            for field, text in (("title", title), ("description", description)):
                if hashlib.sha256(text.encode("utf8")).hexdigest() != row["source_" + field + "_sha256"]:
                    raise PilotDataError("Canonical source hash mismatch")
            start = time.perf_counter_ns()
            prediction = classify(model, row.job_id, title, description)
            elapsed = time.perf_counter_ns() - start
            validate_prediction(prediction)
            try:
                record = encode_pilot(prediction, schema)
            except ValueError as exc:
                raise PilotDataError("Output schema contract mismatch") from exc
            if differences(prediction, decode_pilot(record)):
                raise PilotDataError("Typed adapter loses nested fields")
            record.update(_d06_partition_id=partition, _d06_worker_pid=os.getpid(),
                          _d06_classifier_instance=instance, _d06_classify_ns=elapsed,
                          _d06_python_rss_bytes=current_rss(), _d06_description_chars=len(description),
                          _d06_prediction_sha256=prediction_digest(prediction))
            yield record
        except MemoryError as exc:
            raise RuntimeError(f"D06_RUNTIME_OOM job_id={row.job_id}, partition={partition}") from exc
        except PilotIntegrityError:
            raise
        except PilotDataError as exc:
            # Keep private text out of error messages; task failure is fatal.
            raise PilotDataError(f"job_id={row.job_id}, partition={partition}, {type(exc).__name__}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"D06_RUNTIME_CLASSIFIER job_id={row.job_id}, partition={partition}, {type(exc).__name__}") from exc
