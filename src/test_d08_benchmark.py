"""Synthetic correctness/unit tests only; never published as official timing evidence."""
import csv
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid
import xml.etree.ElementTree as ET

from d08_benchmark import (ROOT, WORKLOADS, MASTERS, POLICY, build_query, plain_result,
    check_result, preflight, create_session, check_options, event_metrics, summarize, write_csv, chart)


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args = SimpleNamespace(run_id="unit_tests", master="local[2]", repeats=3, partitions=4,
            windows_fs_jar=os.environ.get("D08_WINDOWS_FS_JAR"))
        cls.spark, cls.config = create_session(cls.args)
        cls.jobs = cls.spark.createDataFrame([
            (1, None, "FULL_TIME", "A", [(1, "Tech"), (2, "Other")]),
            (2, None, "FULL_TIME", "A", [(1, "Tech")]),
            (3, "Senior", "PART_TIME", None, None)],
            "job_id long, formatted_experience_level string, work_type string, location string, job_industries array<struct<industry_id:long,industry_name:string>>")
        cls.salary = cls.spark.createDataFrame([(1, "USABLE", "USD"), (2, "USABLE", "CAD"), (3, "MISSING", None)],
            "job_id long, normalization_status string, canonical_currency string")
        cls.expected = {"rows": 3, "industry_memberships": 3, "industry_groups": 2,
            "statuses": {"USABLE": 2, "MISSING": 1, "INVALID": 0, "AMBIGUOUS": 0, "EXCLUDED": 0}}
        cls.temp = ROOT / "tmp/d08_tests" / uuid.uuid4().hex
        cls.temp.mkdir(parents=True)

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def result(self, name, jobs=None, salary=None):
        return plain_result(build_query(name, jobs if jobs is not None else self.jobs,
                                        salary if salary is not None else self.salary).first())

    def test_five_real_query_shapes_and_scalar_correctness(self):
        for w in WORKLOADS:
            with self.subTest(workload=w):
                check_result(w, self.result(w), self.expected)

    def test_population_and_join_preflight(self):
        expected = preflight(self.jobs, self.salary, 3)
        self.assertEqual(expected["rows"], 3)
        self.assertTrue(expected["key_sets_equal"])
        self.assertEqual(expected["statuses"], self.expected["statuses"])

    def test_duplicate_join_cannot_pass_count_distinct_alone(self):
        duplicates = self.salary.union(self.salary.limit(1))
        result = self.result("W5", salary=duplicates)
        self.assertEqual(result["unique"], 3)
        self.assertEqual(result["rows"], 4)
        with self.assertRaises(AssertionError):
            check_result("W5", result, self.expected)
        with self.assertRaises(ValueError):
            preflight(self.jobs, duplicates, 3)

    def test_missing_job_and_null_key_rejected(self):
        from pyspark.sql import functions as F
        with self.assertRaises(ValueError):
            preflight(self.jobs, self.salary.filter("job_id != 2"), 3)
        with self.assertRaises(ValueError):
            preflight(self.jobs.withColumn("job_id", F.lit(None).cast("long")), self.salary, 3)

    def test_null_groups_not_dropped_or_converted_to_sentinel(self):
        from pyspark.sql import functions as F
        jobs = self.jobs.withColumn("work_type", F.lit("FULL_TIME")).withColumn("location", F.lit("A"))
        jobs = jobs.withColumn("formatted_experience_level", F.when(F.col("job_id") == 1, F.lit(None).cast("string")).otherwise("Unknown"))
        out = self.result("W2", jobs=jobs)
        self.assertEqual(out["output_groups"], 2)
        self.assertEqual(out["membership_count"], 3)

    def test_industry_explode_distinct_and_currency_separation(self):
        w3 = self.result("W3")
        self.assertEqual((w3["output_groups"], w3["membership_count"]), (2, 3))
        w4 = self.result("W4")
        self.assertEqual(w4["output_groups"], 3)  # USABLE USD/CAD distinct + MISSING NULL
        self.assertEqual(w4["membership_count"], 3)

    def test_repartition_result_digest_stable(self):
        for w in ("W2", "W3", "W4"):
            baseline = self.result(w)
            check_result(w, self.result(w, self.jobs.repartition(1), self.salary.repartition(2)), self.expected, baseline)

    def test_reproducible_config_and_minimum_repeats(self):
        self.assertEqual(self.config["spark.sql.shuffle.partitions"], "4")
        self.assertEqual(self.config["spark.sql.adaptive.enabled"], "false")
        self.assertEqual(self.config["spark.sql.autoBroadcastJoinThreshold"], "-1")
        self.assertEqual(self.config["cache_policy"], POLICY)
        self.assertEqual(self.config["spark.sql.session.timeZone"], "UTC")
        for patch in ({"run_id": "../outside"}, {"repeats": 1}, {"partitions": 200}, {"master": "local[*]"}):
            args = SimpleNamespace(**{**vars(self.args), **patch})
            with self.assertRaises(ValueError): check_options(args)

    def test_summary_uses_measured_only_and_real_baseline(self):
        rows = [{"master": m, "workload": "W1", "phase": p, "elapsed_seconds": n}
            for m in MASTERS for p, n in (("warmup", 100), ("measured", 1), ("measured", 2), ("measured", 3))]
        summary = summarize(rows)
        self.assertTrue(all(r["samples"] == 3 and r["median_seconds"] == 2 for r in summary))
        self.assertTrue(all(r["speedup_vs_local1"] == 1 for r in summary))

    def test_audit_csv_and_svg_format_and_no_overwrite(self):
        rows = [{"master": m, "workload": w, "median_seconds": 1.0, "speedup_vs_local1": 1.0}
            for m in MASTERS for w in WORKLOADS]
        path = self.temp / "fixture.csv"
        write_csv(path, rows)
        with path.open(encoding="utf8", newline="") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 15)
        with self.assertRaises(FileExistsError): write_csv(path, rows)
        svg = self.temp / "fixture.svg"
        chart(svg, rows, "median_seconds", "TEST fixture, not benchmark")
        self.assertEqual(ET.parse(svg).getroot().tag, "{http://www.w3.org/2000/svg}svg")

    def test_metrics_require_observed_fields_not_fabricated_values(self):
        events = self.temp / "events"; events.mkdir()
        sample = [{"Event": "SparkListenerJobStart", "Stage IDs": [1], "Properties": {"spark.jobGroup.id": "test"}},
            {"Event": "SparkListenerTaskEnd", "Stage ID": 1, "Task Metrics": {"Executor Run Time": 7,
                "Disk Bytes Spilled": 0, "Shuffle Read Metrics": {"Remote Bytes Read": 2, "Local Bytes Read": 3},
                "Shuffle Write Metrics": {"Shuffle Bytes Written": 11}}}]
        with (events / "events_fixture").open("x", encoding="utf8") as f:
            f.write("\n".join(json.dumps(e) for e in sample))
        metrics, files = event_metrics(events)
        self.assertEqual(metrics["test"]["shuffle_read_bytes"], 5)
        self.assertEqual(metrics["test"]["shuffle_write_bytes"], 11)
        self.assertEqual(metrics["test"]["disk_spilled_bytes"], 0)
        self.assertNotIn("executor_cpu_ns", metrics["test"])
        self.assertEqual(len(files), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
