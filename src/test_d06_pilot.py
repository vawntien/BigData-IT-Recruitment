"""Pilot guards, lossless bridge controls and live bounded Spark integration.

Never run full mode. Unit controls are explicitly not sample accuracy evidence.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

from d06_classification_runner import ROOT, validate_options, validate_input, run_pilot
from d06_pilot_packaging import build_package, verified_members, validate_config, worker_runner
from d06_pilot_runtime import (
    PilotDataError, PilotIntegrityError, pilot_schema, encode_pilot, decode_pilot,
    validate_prediction, prediction_digest, current_rss,
)
from d06_taxonomy_adapter import bigint_string, differences


class PilotGuardUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parity_json = json.loads((ROOT / "data/audit/d06/spark_schema.json").read_text())
        from pyspark.sql.types import StructType
        cls.parity_schema = StructType.fromJson(cls.parity_json)
        cls.package, cls.checksum, _ = build_package(ROOT)
        cls.members = verified_members(cls.package, cls.checksum)
        reference = ROOT / "tmp/tv2_a04_handoff_extract/tv2_04/a04_taxonomy_v0_2_2_20261014/all_predictions.jsonl"
        data = reference.read_bytes()
        if hashlib.sha256(data).hexdigest() != "1c4c8b8d3ab00238e908e834ca615ba4188b6d03858cb5e38648f1565d03266d":
            raise AssertionError("Frozen reference hash mismatch")
        cls.reference = [json.loads(line) for line in data.decode().splitlines()]

    def test_full_mode_and_oversize_hard_guard(self):
        target = ROOT / "tmp/d06_pilot/guard_unused"
        for mode, size in [("full", 1), ("pilot", 123849), ("pilot", 1001), ("pilot", 0)]:
            with self.subTest(mode=mode, size=size), self.assertRaises(PilotDataError):
                validate_options(mode, size, 4, target)
        self.assertFalse(target.exists())

    def test_existing_output_and_production_path_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp/d06_pilot") as directory:
            with self.assertRaises(FileExistsError):
                validate_options("pilot", 10, 2, directory)
        for path in [ROOT / "data/processed/d06", ROOT / "tmp/d06_pilot", ROOT / "tmp/elsewhere"]:
            with self.assertRaises(PilotDataError):
                validate_options("pilot", 10, 2, path)

    def test_missing_and_tampered_package_fail(self):
        with self.assertRaises(PilotIntegrityError):
            verified_members(ROOT / "tmp/nonexistent_d06_package.zip", self.checksum)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            changed = Path(directory) / "changed.zip"
            changed.write_bytes(self.package.read_bytes() + b"tamper")
            with self.assertRaises(PilotIntegrityError):
                verified_members(changed, self.checksum)

    def test_config_version_hash_and_missing(self):
        data = self.members["it_taxonomy_v0.2.2.json"]
        validate_config(data)
        with self.assertRaises(PilotIntegrityError):
            validate_config(data + b"\n")
        other = json.loads(data); other["version"] = "0.2.0"
        with self.assertRaises(PilotIntegrityError):
            validate_config(json.dumps(other).encode())
        with self.assertRaises(FileNotFoundError):
            build_package(ROOT, str(ROOT / "tmp/missing_candidate_config.json"))

    def test_package_is_reproducible_and_not_tmp_classifier(self):
        path, checksum, manifest = build_package(ROOT)
        self.assertEqual(checksum, self.checksum)
        self.assertEqual(path.read_bytes(), self.package.read_bytes())
        self.assertEqual(manifest["version"], "0.2.2")
        self.assertEqual(len(manifest["files"]), 8)

    def test_boolean_presence_and_nested_absence_roundtrip(self):
        schema = pilot_schema(self.parity_json)
        self.assertEqual(schema["_d06_present"].dataType.simpleString(), "boolean")
        self.assertEqual(schema["_d06_field_keys"].dataType.simpleString(), "array<string>")
        for prediction in self.reference:
            row = encode_pilot(prediction, self.parity_schema)
            self.assertIs(row["_d06_present"], True)
            self.assertEqual(differences(prediction, decode_pilot(row)), [])
            validate_prediction(prediction)
            row["_d06_present"] = None
            with self.assertRaises(PilotDataError):
                decode_pilot(row)

    def test_review_nullability_is_not_missing_or_error(self):
        review = deepcopy(next(r for r in self.reference if r["it_decision"] == "REVIEW"))
        self.assertIsNone(review["is_it"])
        validate_prediction(review)
        review["is_it"] = False
        with self.assertRaises(PilotDataError):
            validate_prediction(review)

    def test_raw_offset_and_nested_tampering_fail(self):
        prediction = deepcopy(next(r for r in self.reference if r["match_evidence"]))
        original = prediction_digest(prediction)
        prediction["match_evidence"][0]["raw_excerpt_end"] = 10**9
        self.assertNotEqual(prediction_digest(prediction), original)
        with self.assertRaises(PilotDataError):
            validate_prediction(prediction)

    def test_invalid_bigint_and_unavailable_rss(self):
        for value in [None, True, 1.2, "1.0", "01", 2**63]:
            with self.assertRaises(ValueError):
                bigint_string(value)
        with patch("d06_pilot_runtime.os.name", "unmeasured_platform"):
            self.assertIsNone(current_rss())

    def test_simulated_oom_is_runtime_failure_not_review(self):
        from types import SimpleNamespace
        from pyspark.sql import Row
        from d06_pilot_runtime import classify_partition
        empty = hashlib.sha256(b"").hexdigest()
        row = Row(job_id=1, source_title="", source_description="",
                  source_title_sha256=empty, source_description_sha256=empty)
        with patch("d06_pilot_runtime.load_model", return_value=object()), \
             patch("d06_pilot_runtime.classify", side_effect=MemoryError("simulated only")), \
             patch("pyspark.TaskContext.get", return_value=SimpleNamespace(partitionId=lambda: 0)):
            with self.assertRaisesRegex(RuntimeError, "D06_RUNTIME_OOM"):
                list(classify_partition([row], ROOT / "tmp", self.parity_json))


class PilotInputSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
        os.environ.setdefault("PYSPARK_SUBMIT_ARGS", "--driver-memory 3g pyspark-shell")
        from d05_utils import get_spark_session
        cls.spark = get_spark_session("D06-PilotInputGuards", ROOT)
        cls.schema = "job_id long, source_title string, source_description string, source_title_sha256 string, source_description_sha256 string"
        cls.empty_hash = hashlib.sha256(b"").hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def row(self, key):
        return (key, "", "", self.empty_hash, self.empty_hash)

    def frame(self, rows, schema=None):
        return self.spark.createDataFrame(self.spark.sparkContext.parallelize(rows, 1), schema or self.schema)

    def test_null_duplicate_and_nonbigint_input_fail(self):
        for rows in [[self.row(None)], [self.row(1), self.row(1)]]:
            with self.assertRaises(PilotDataError):
                validate_input(self.frame(rows))
        with self.assertRaises(PilotDataError):
            validate_input(self.frame([("1", "", "", self.empty_hash, self.empty_hash)],
                self.schema.replace("job_id long", "job_id string")))

    def test_missing_source_and_bad_source_hash_fail(self):
        rows = [(1, None, "", self.empty_hash, self.empty_hash)]
        with self.assertRaises(PilotDataError):
            validate_input(self.frame(rows))
        rows = [(1, "changed", "", self.empty_hash, self.empty_hash)]
        with self.assertRaises(PilotDataError):
            validate_input(self.frame(rows))

    def test_empty_source_distinct_from_missing_and_worker_execution(self):
        # Synthetic empty title/description control only, NOT real pilot sample.
        source = self.frame([self.row(1)])
        self.assertEqual(validate_input(source)["rows"], 1)
        package, checksum, _ = build_package(ROOT)
        broadcast = self.spark.sparkContext.broadcast(package.read_bytes())
        schema = pilot_schema(json.loads((ROOT / "data/audit/d06/spark_schema.json").read_text()))
        df = self.spark.createDataFrame(source.coalesce(1).rdd.mapPartitions(worker_runner(broadcast, checksum)), schema)
        row = df.first()  # one explicitly bounded synthetic control
        self.assertTrue(row._d06_present)
        self.assertEqual(row.it_decision, "REVIEW")
        self.assertIsNone(row.is_it)

    def test_worker_failure_is_not_synthetic_review(self):
        package, checksum, _ = build_package(ROOT)
        broadcast = self.spark.sparkContext.broadcast(package.read_bytes())
        source = self.frame([(1, "wrong_hash", "", self.empty_hash, self.empty_hash)])
        with self.assertRaises(Exception):
            # Deliberately bypass preflight to test the worker fail-closed path.
            source.coalesce(1).rdd.mapPartitions(worker_runner(broadcast, checksum)).count()


class PilotLiveRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        output = ROOT / "tmp/d06_pilot" / ("test_" + uuid.uuid4().hex[:12])
        cls.result = run_pilot(sample_size=8, partitions=2, output=output)

    def test_live_bounded_input_output_and_partition_execution(self):
        result = self.result
        self.assertEqual(result["status"], "PASS")
        self.assertLessEqual(result["validation"]["rows"], 1200)
        self.assertEqual(result["validation"]["rows"], result["selection"]["input"]["rows"])
        self.assertEqual(result["performance"]["classifier_instances"], 2)
        self.assertEqual(result["validation"]["missing"], 0)
        self.assertFalse(result["full_dataset_executed"])

    def test_live_parquet_nested_and_nullable_contract(self):
        v = self.result["validation"]
        self.assertEqual(v["unique"], v["rows"])
        self.assertEqual(v["nulls"], 0)
        self.assertEqual(v["nested_roundtrip_checked"], v["rows"])
        self.assertTrue(v["all_present"])
        self.assertGreaterEqual(v["decision_counts"]["REVIEW"], 33)
        self.assertGreater(self.result["output_parquet_bytes"], 0)

    def test_live_partition_count_determinism_and_protection(self):
        self.assertEqual(self.result["determinism"], {"rows": 32, "partitions": 3, "mismatches": 0})
        self.assertEqual(self.result["preservation"]["changed"], [])
        with self.assertRaises(FileExistsError):
            run_pilot(sample_size=8, partitions=2, output=self.result["output"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
