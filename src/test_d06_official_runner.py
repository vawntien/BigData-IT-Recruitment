"""Official guards + real3-row frozen TEST engine. NO approved A04/full records created.

Real preflight123849 is tested separately without classification. These tests
never enter a positively authorized FULL branch or modify frozen references.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from d06_official_contract import (
    ApprovalRequired, SCHEMA_SHA, SCHEMA_VERSION, _approval, checked_package,
    official_schema, safe_destination, sha,
)
from d06_official_state import RunJournal, exclusive_json, inspect_run
from d06_official_runner import ROOT, parser, run, input_checks, execute_run, create_session
from d06_pilot_packaging import build_package
from d06_classification_runner import output_validation


def new_id(prefix="test"):
    return prefix + "_" + uuid.uuid4().hex[:12]


class OfficialGuardTests(unittest.TestCase):
    def test_full_without_explicit_authorization_stops_before_spark(self):
        args = parser().parse_args(["--mode", "full", "--run-id", new_id()])
        with patch("d06_official_runner.create_session") as session:
            with self.assertRaises(ApprovalRequired):
                run(args)
            session.assert_not_called()

    def test_missing_a04_even_with_operator_flag_stops(self):
        args = parser().parse_args(["--mode", "full", "--run-id", new_id(), "--execute-full"])
        with patch("d06_official_runner.create_session") as session:
            with self.assertRaises(ApprovalRequired):
                run(args)
            session.assert_not_called()

    def test_pending_record_and_wrong_approval_hash_refused(self):
        path = ROOT / "tmp/d06_official_tests" / new_id() / "pending.json"
        exclusive_json(path, {"kind": "A04_BUSINESS", "status": "PENDING"})
        # Never manufacture a positively approved human record, even as a fixture.
        for checksum in ["0" * 64, sha(path.read_bytes())]:
            with self.assertRaises(ApprovalRequired):
                _approval(path, checksum, "A04_BUSINESS")

    def test_missing_package_and_bad_hash_refused(self):
        with self.assertRaises(ValueError):
            checked_package(None, None)
        package, checksum, _ = build_package(ROOT)
        with self.assertRaises(ValueError):
            checked_package(package, "0" * 64)
        self.assertEqual(len(checked_package(package, checksum)), 8)

    def test_frozen_schema_and_boolean_presence(self):
        schema = official_schema(ROOT)
        self.assertEqual(len(schema.fields), 27)
        self.assertEqual(schema["job_id"].dataType.simpleString(), "bigint")
        self.assertEqual(schema["_d06_present"].dataType.simpleString(), "boolean")
        self.assertTrue(schema["is_it"].nullable)
        self.assertEqual(SCHEMA_VERSION, "d06-official-v1")
        self.assertEqual(len(SCHEMA_SHA), 64)

    def test_unreviewed_schema_refused(self):
        root = ROOT / "tmp/d06_official_tests" / new_id()
        exclusive_json(root / "data/audit/d06/pilot_spark_schema.json", {"type": "struct", "fields": []})
        with self.assertRaises(ValueError):
            official_schema(root)

    def test_versioned_destination_and_existing_run(self):
        name = new_id()
        target = safe_destination(ROOT, name)
        self.assertEqual(target.parent, (ROOT / "data/processed/d06/v0.2.2").resolve())
        self.assertFalse(target.exists())
        for bad in ["../canonical", "x/y", "a:b"]:
            with self.assertRaises(ValueError):
                safe_destination(ROOT, bad)
        with self.assertRaises(ValueError):
            safe_destination(ROOT, name, ROOT / "data/processed/canonical/jobs")
        original_resolve = Path.resolve
        def resolved_outside(path, *args, **kwargs):
            if path == target:
                return ROOT.parent / "external_target" / name
            return original_resolve(path, *args, **kwargs)
        # Model an ancestor junction without creating/deleting filesystem links.
        with patch.object(Path, "resolve", resolved_outside):
            with self.assertRaises(ValueError):
                safe_destination(ROOT, name)
        own = safe_destination(ROOT, name, scope="TEST")
        RunJournal(own, {"scope": "TEST", "run_id": name, "expected_rows": 1})
        with self.assertRaises(FileExistsError):
            safe_destination(ROOT, name, scope="TEST")

    def test_interrupted_or_malformed_completion_not_success(self):
        name = new_id()
        own = safe_destination(ROOT, name, scope="TEST")
        RunJournal(own, {"scope": "TEST", "run_id": name, "expected_rows": 1})
        self.assertEqual(inspect_run(own)["status"], "INCOMPLETE_OR_CORRUPT")
        exclusive_json(own / "completion.json", {"status": "SUCCEEDED"})
        self.assertEqual(inspect_run(own)["status"], "INCOMPLETE_OR_CORRUPT")


class OfficialEngineSmallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args = SimpleNamespace(mode="preflight", partitions=2, master="local[2]",
            worker_python=None, windows_fs_jar=str(ROOT / "tmp/d04-localfs/d04-localfs-adapter.jar"))
        cls.spark = create_session(cls.args)
        cls.package, cls.checksum, _ = build_package(ROOT, artifact_dir=ROOT / "tmp/d06_official_artifacts",
            code_ref="0ca38ab90a05acfac1f191da45dba7511ab094be")
        cls.input_schema = "job_id long, source_title string, source_description string, source_title_sha256 string, source_description_sha256 string"
        reference = (ROOT / "tmp/tv2_a04_handoff_extract/tv2_04/a04_taxonomy_v0_2_2_20261014/all_predictions.jsonl").read_bytes()
        if hashlib.sha256(reference).hexdigest() != "1c4c8b8d3ab00238e908e834ca615ba4188b6d03858cb5e38648f1565d03266d":
            raise AssertionError("Frozen reference integrity failure")
        records = [json.loads(line) for line in reference.decode().splitlines()]
        # Machine decisions select coverage only, never override classifier output.
        selected = [next(r for r in records if r["it_decision"] == decision)
                    for decision in ("ACCEPT", "REJECT", "REVIEW")]
        rows = [(int(r["job_id"]), r["title"], r["description"], r["source_title_sha256"],
                 r["source_description_sha256"]) for r in selected]
        cls.first_id, _, cls.first_description, _, _ = rows[0]
        cls.source = cls.spark.createDataFrame(cls.spark.sparkContext.parallelize(rows, 1), cls.input_schema)
        cls.inventory = {"fingerprint": sha(json.dumps(rows, ensure_ascii=False).encode()), "scope": "TEST"}
        cls.run_id = new_id("engine")
        cls.path = safe_destination(ROOT, cls.run_id, scope="TEST")
        cls.result = execute_run(cls.spark, cls.source, root=ROOT, run_id=cls.run_id,
            output=cls.path, package=cls.package, checksum=cls.checksum, expected_rows=3,
            input_inventory=cls.inventory, partitions=2, scope="TEST")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_real_small_engine_write_read_publish_and_review(self):
        self.assertEqual(self.result["status"], "SUCCEEDED")
        self.assertEqual(self.result["scope"], "TEST")
        validation = json.loads((self.path / "validation.json").read_text())
        self.assertEqual(validation["rows"], 3)
        self.assertEqual(validation["decision_counts"], {"ACCEPT": 1, "REJECT": 1, "REVIEW": 1})
        self.assertEqual(validation["nested_roundtrip_checked"], 3)

    def test_reuse_run_id_refused_without_append(self):
        with self.assertRaises(FileExistsError):
            execute_run(self.spark, self.source, root=ROOT, run_id=self.run_id, output=self.path,
                package=self.package, checksum=self.checksum, expected_rows=3,
                input_inventory=self.inventory, scope="TEST")
        self.assertEqual(inspect_run(self.path)["rows"], 3)

    def test_test_cap_and_engine_full_guard(self):
        for scope, size, error in [("TEST", 123849, ValueError), ("FULL", 123849, ApprovalRequired)]:
            name = new_id()
            with self.assertRaises(error):
                execute_run(self.spark, self.source, root=ROOT, run_id=name, output=None,
                    package=self.package, checksum=self.checksum, expected_rows=size,
                    input_inventory=self.inventory, scope=scope)

    def test_invalid_keys_and_missing_source_schema(self):
        from pyspark.sql import functions as F
        with self.assertRaises(ValueError):
            input_checks(self.source.drop("source_title"), 3)
        with self.assertRaises(ValueError):
            input_checks(self.source.withColumn("job_id", F.lit(None).cast("long")), 3)
        with self.assertRaises(ValueError):
            input_checks(self.source.withColumn("job_id", F.lit(1).cast("long")), 3)
        with self.assertRaises(ValueError):
            input_checks(self.source.withColumn("source_title", F.lit("clean replacement")), 3)

    def test_source_text_is_original_and_nested_schema_exact(self):
        from pyspark.sql import functions as F
        data = self.spark.read.parquet(str(self.path / "predictions"))
        self.assertEqual(data.schema.toNullable(), official_schema(ROOT).toNullable())
        self.assertEqual(data.filter((F.col("job_id") == self.first_id) &
            (F.col("description") == self.first_description)).count(), 1)
        self.assertEqual(data.filter((F.col("it_decision") == "REVIEW") & F.col("is_it").isNull()).count(), 1)

    def test_reject_bad_nullable_conversion(self):
        from pyspark.sql import functions as F
        data = self.spark.read.parquet(str(self.path / "predictions")).withColumn("is_it", F.lit(False))
        bc = self.spark.sparkContext.broadcast(Path(self.package).read_bytes())
        with self.assertRaises(ValueError):
            output_validation(self.source, data, official_schema(ROOT), bc, self.checksum)

    def test_failed_write_has_evidence_and_no_completion(self):
        from pyspark.sql.readwriter import DataFrameWriter
        name = new_id("failure")
        path = safe_destination(ROOT, name, scope="TEST")
        with patch.object(DataFrameWriter, "parquet", side_effect=RuntimeError("simulated storage interruption")):
            with self.assertRaises(RuntimeError):
                execute_run(self.spark, self.source, root=ROOT, run_id=name, output=path,
                    package=self.package, checksum=self.checksum, expected_rows=3,
                    input_inventory=self.inventory, scope="TEST")
        self.assertEqual(inspect_run(path)["status"], "FAILED")
        self.assertFalse((path / "completion.json").exists())
        with self.assertRaises(FileExistsError):
            safe_destination(ROOT, name, scope="TEST")

    def test_new_run_retry_deterministic_without_duplicate_data(self):
        from pyspark.sql import functions as F
        name = new_id("new_attempt")
        path = safe_destination(ROOT, name, scope="TEST")
        result = execute_run(self.spark, self.source, root=ROOT, run_id=name, output=path,
            package=self.package, checksum=self.checksum, expected_rows=3,
            input_inventory=self.inventory, partitions=1, scope="TEST")
        self.assertEqual(result["rows"], 3)
        first = self.spark.read.parquet(str(self.path / "predictions")).select("job_id", "_d06_prediction_sha256")
        second = self.spark.read.parquet(str(path / "predictions")).select("job_id", F.col("_d06_prediction_sha256").alias("other"))
        self.assertEqual(first.join(second, "job_id").filter(F.col("other") != F.col("_d06_prediction_sha256")).count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
