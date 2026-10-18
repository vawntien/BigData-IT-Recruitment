"""D06 unit tests AND live frozen-176 integration tests (not synthetic parity).

PowerShell, from root, with process-scoped Java 21:
  .\.venv\Scripts\python.exe -B -m unittest discover -s src -p test_d06_parity.py -v
Integration tests deliberately run actual Python workers and temporary Parquet.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from d06_taxonomy_adapter import (
    CONFIG_HASH, bigint_string, classify, decode, derive_schema, differences,
    encode, load_model,
)
from d06_parity_validation import D05_HEAD, ROOT, checked_relative, exact_file, frozen_records, prepare, run


class AdapterUnitTests(unittest.TestCase):
    """Small isolated adapter controls; these are NOT the frozen parity result."""

    def test_bigint_to_canonical_string(self):
        for value in (0, 3905848702, -(2**63), 2**63 - 1):
            self.assertEqual(bigint_string(value), str(value))
            self.assertEqual(bigint_string(str(value)), str(value))

    def test_reject_lossy_null_or_noncanonical_keys(self):
        for value in (None, True, 1.0, "01", "1.0", " 1", "+1", "-0", "", 2**63, -(2**63)-1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bigint_string(value)

    def test_structured_comparison_contract(self):
        self.assertEqual(differences({"a": 1, "b": []}, {"b": [], "a": 1}), [])
        for left, right in [([1, 2], [2, 1]), ({}, {"x": None}),
                            (None, False), (False, 0), ([], None)]:
            self.assertTrue(differences(left, right))

    def test_reject_zip_traversal_and_windows_aliases(self):
        for name in ("../x", "/tv2_04/x", "tv2_04/../x", "tv2_04/./x",
                     "tv2_04//x", "tv2_04/x\\y", "tv2_04/CON.txt", "tv2_04/x.",
                     "tv2_04/x ", "tv2_04/x:stream", "other/x", "tv2_04/\x00x"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                checked_relative(name)
        self.assertEqual(str(checked_relative("tv2_04/baseline/source_rows.json")),
                         "tv2_04/baseline/source_rows.json")

    def test_never_overwrite_existing_reference(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            path = Path(directory) / "reference.bin"
            exact_file(path, b"original\r\n")
            exact_file(path, b"original\r\n")
            with self.assertRaises(ValueError):
                exact_file(path, b"changed\n")
            self.assertEqual(path.read_bytes(), b"original\r\n")


class FrozenAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference, snapshot, cls.integrity = prepare()
        cls.inputs, cls.expected = frozen_records(reference)
        cls.model = load_model(snapshot)
        cls.schema = derive_schema(list(cls.expected.values()))

    def test_exact_frozen_keys_and_integrity(self):
        self.assertEqual(len(self.inputs), 176)
        self.assertEqual(self.inputs.keys(), self.expected.keys())
        self.assertTrue(all(h["status"] == "MATCH" for h in self.integrity["hashes"]))

    def test_all_176_python_predictions_and_determinism(self):
        for job, pair in self.inputs.items():
            with self.subTest(job_id=job):
                first = classify(self.model, int(job), *pair)
                second = classify(self.model, job, *pair)
                self.assertEqual(differences(self.expected[job], first), [])
                self.assertEqual(differences(first, second), [])

    def test_version_and_exact_config_hash(self):
        for record in self.expected.values():
            self.assertEqual(record["taxonomy_version"], "0.2.2")
            self.assertEqual(record["taxonomy_sha256"], CONFIG_HASH)

    def test_accept_reject_review_and_nullable_boolean(self):
        counts = {decision: 0 for decision in ("ACCEPT", "REJECT", "REVIEW")}
        for record in self.expected.values():
            decision = record["it_decision"]
            counts[decision] += 1
            self.assertIs(record["is_it"], {"ACCEPT": True, "REJECT": False, "REVIEW": None}[decision])
        self.assertEqual(counts, {"ACCEPT": 86, "REJECT": 57, "REVIEW": 33})

    def test_all_nested_typed_serialization_and_key_presence(self):
        for job, record in self.expected.items():
            with self.subTest(job_id=job):
                self.assertEqual(differences(record, decode(encode(record, self.schema))), [])
        self.assertEqual(self.schema["job_id"].dataType.simpleString(), "bigint")
        self.assertTrue(self.schema["is_it"].nullable)
        self.assertEqual(self.schema["match_evidence"].dataType.typeName(), "array")
        self.assertEqual(self.schema["description_processing"].dataType.typeName(), "struct")

    def test_explicit_synthetic_diagnostics_control(self):
        # These two arrays are empty in all frozen records. Exercise their
        # code-backed element types separately; do NOT count as frozen parity.
        record = deepcopy(next(iter(self.expected.values())))
        record["description_processing"]["parser_issues"] = ["UNCLOSED_SCRIPT_OR_STYLE"]
        record["description_processing"]["removed_source_ranges"] = [
            {"start": 0, "end": 15, "reason": "script"}]
        self.assertEqual(differences(record, decode(encode(record, self.schema))), [])

    def test_unmodelled_field_is_not_silently_dropped(self):
        record = deepcopy(next(iter(self.expected.values())))
        record["description_processing"]["new_diagnostic"] = True
        with self.assertRaises(ValueError):
            encode(record, self.schema)


class LiveSparkIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = run()  # actual 176 predictions on Python + Spark, live readback

    def test_python_spark_full_field_parity(self):
        for stage in ("python", "determinism", "spark"):
            self.assertEqual(self.summary[stage]["status"], "PASS")
            self.assertEqual(self.summary[stage]["exact_matches"], 176)
            self.assertEqual(self.summary[stage]["field_mismatches"], 0)

    def test_spark_grain_and_partition_loading(self):
        result = self.summary["spark"]
        self.assertEqual((result["rows"], result["unique_job_id"], result["null_keys"], result["duplicate_keys"]),
                         (176, 176, 0, 0))
        self.assertEqual(result["partitions"], 4)
        self.assertEqual(result["classifier_instances"], 4)

    def test_d05_source_compatibility_live_left_join(self):
        result = self.summary["canonical"]
        self.assertEqual(result, {"status": "PASS", "found": 176, "missing": 0,
                                  "text_hash_matches": 176, "text_hash_mismatch_jobs": 0})

    def test_parquet_nested_schema_null_and_exact_roundtrip(self):
        result = self.summary["roundtrip"]
        self.assertEqual(result["exact_matches"], 176)
        self.assertEqual(result["field_mismatches"], 0)
        self.assertTrue(result["schema_types_unchanged"])
        self.assertEqual(result["review_nulls"], 33)
        schema = json.loads((Path(self.summary["output"]) / "schema.json").read_text(encoding="utf-8"))
        self.assertTrue(next(f for f in schema["fields"] if f["name"] == "is_it")["nullable"])

    def test_runtime_scope_and_protected_files(self):
        self.assertEqual(self.summary["verdict"], "PASS")
        self.assertEqual(self.summary["d05_base"], D05_HEAD)
        self.assertEqual(self.summary["environment"]["spark"], "4.2.0")
        self.assertTrue(self.summary["environment"]["java"].startswith("21."))
        self.assertTrue(self.summary["preservation"]["hash_size_mtime_unchanged"])
        self.assertFalse(self.summary["full_dataset_classification"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
