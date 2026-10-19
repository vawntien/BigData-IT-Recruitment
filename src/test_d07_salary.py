"""D07 synthetic contract fixtures plus live Spark/Parquet tests. No classifiers."""
from decimal import Decimal
import json
import os
from pathlib import Path
import unittest
import uuid

from normalize_salary import (ROOT, FIELDS, AMOUNTS, load_policy, normalize, key_stats,
                              input_schema_check, validate, create_session, safe_output,
                              join_classification, write_new)


class SalaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql.types import StructType
        cls.spark = create_session("local[2]", 2, os.environ.get("D07_WINDOWS_FS_JAR"))
        whole = json.loads((ROOT / "data/audit/d05_canonical_schema.json").read_text(encoding="utf8"))
        required = {"job_id", "normalized_salary", "salary_record", "source_text_file", "canonical_schema_version", *FIELDS}
        cls.schema = StructType.fromJson({"type": "struct", "fields": [f for f in whole["fields"] if f["name"] in required]})
        cls.policy = load_policy()

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def row(self, job=1, minimum=None, median=None, maximum=None, currency="USD", period="YEARLY", compensation="BASE_SALARY", record=None):
        return {"job_id": job, "min_salary": Decimal(minimum) if minimum is not None else None,
            "med_salary": Decimal(median) if median is not None else None,
            "max_salary": Decimal(maximum) if maximum is not None else None,
            "currency": currency, "pay_period": period, "compensation_type": compensation,
            "normalized_salary": None, "salary_record": record,
            "source_text_file": "SYNTHETIC_TEST_ONLY", "canonical_schema_version": "d05-v1"}

    def df(self, rows):
        return self.spark.createDataFrame(rows, self.schema)

    def output(self, row):
        return normalize(self.df([row]), self.policy).first()

    def record(self, row):
        return {"salary_id": 100, **{f: row[f] for f in FIELDS}}

    def test_missing_salary_preserves_null_not_zero(self):
        row = self.output(self.row())
        self.assertEqual(row.normalization_status, "MISSING")
        self.assertEqual(row.reason_codes, ["NO_SALARY_AMOUNT"])
        self.assertIsNone(row.normalized_min_salary)
        self.assertIsNone(row.normalized_med_salary)
        self.assertIsNone(row.conversion_factor)

    def test_all_five_real_periods_factors(self):
        rows = [self.row(i, minimum="10.1234", period=p) for i, p in enumerate(self.policy["period_factors"], 1)]
        for row in normalize(self.df(rows), self.policy).collect():
            factor = self.policy["period_factors"][row.source_pay_period]
            self.assertEqual(row.normalization_status, "USABLE")
            self.assertEqual(row.conversion_factor, Decimal(factor))
            self.assertEqual(row.normalized_min_salary, Decimal("10.1234") * factor)
            self.assertIsNone(row.normalized_med_salary)

    def test_unknown_and_missing_period_not_annualized(self):
        for period in ("DAILY", "FORTNIGHT", "ONCE", None, ""):
            with self.subTest(period=period):
                row = self.output(self.row(minimum="10", period=period))
                self.assertEqual(row.normalization_status, "AMBIGUOUS")
                self.assertIsNone(row.normalized_min_salary)
                self.assertIsNone(row.conversion_factor)

    def test_missing_currency(self):
        row = self.output(self.row(median="100", currency=None))
        self.assertEqual(row.normalization_status, "AMBIGUOUS")
        self.assertIn("MISSING_CURRENCY", row.reason_codes)
        self.assertIsNone(row.normalized_currency)

    def test_multiple_currencies_not_converted(self):
        rows = [self.row(i, median="100", currency=c) for i, c in enumerate(self.policy["currencies"], 1)]
        out = normalize(self.df(rows), self.policy).collect()
        self.assertEqual({r.normalized_currency for r in out}, set(self.policy["currencies"]))
        self.assertTrue(all(r.normalized_med_salary == Decimal("100") for r in out))
        other = self.output(self.row(median="100", currency="XYZ"))
        self.assertEqual(other.normalization_status, "EXCLUDED")
        self.assertIsNone(other.normalized_med_salary)

    def test_negative_and_zero_invalid(self):
        for value in ("-0.0001", "0", "-100"):
            row = self.output(self.row(median=value))
            self.assertEqual(row.normalization_status, "INVALID")
            self.assertIn("NONPOSITIVE_SALARY", row.reason_codes)
            self.assertIsNone(row.normalized_med_salary)

    def test_all_pairwise_bound_orders(self):
        for low, med, high in (("20", None, "10"), ("20", "10", None), (None, "20", "10")):
            row = self.output(self.row(minimum=low, median=med, maximum=high))
            self.assertEqual(row.normalization_status, "INVALID")
            self.assertIn("INVALID_BOUNDS_ORDER", row.reason_codes)
        self.assertEqual(self.output(self.row(minimum="10", median="10", maximum="10")).normalization_status, "USABLE")

    def test_conflicting_sources_abstain_no_max_average(self):
        raw = self.row(minimum="10", maximum="20")
        record = self.record(raw)
        record["max_salary"] = Decimal("30")
        raw["salary_record"] = record
        row = self.output(raw)
        self.assertEqual(row.salary_source, "CONFLICT")
        self.assertEqual(row.normalization_status, "AMBIGUOUS")
        self.assertIsNone(row.selected_salary)
        self.assertIsNone(row.normalized_max_salary)
        self.assertEqual(row.raw_postings.max_salary, Decimal("20"))
        self.assertEqual(row.raw_salary_record.max_salary, Decimal("30"))

    def test_whole_source_selection_no_field_coalesce(self):
        raw = self.row(minimum="10", maximum="20")
        raw["salary_record"] = self.record(raw)
        self.assertEqual(self.output(raw).salary_source, "BOTH_AGREE")
        only_record = self.row()
        only_record["salary_record"] = self.record(raw)
        self.assertEqual(self.output(only_record).salary_source, "SALARIES")
        partial = self.row(minimum="10", maximum=None)
        partial["salary_record"] = self.record(raw)
        self.assertEqual(self.output(partial).normalization_status, "AMBIGUOUS")

    def test_currency_period_and_compensation_conflict(self):
        for field, value in (("currency", "CAD"), ("pay_period", "MONTHLY"), ("compensation_type", "COMMISSION")):
            raw = self.row(median="100")
            raw["salary_record"] = self.record(raw)
            raw["salary_record"][field] = value
            self.assertTrue(self.output(raw).source_conflict)

    def test_precision_and_max_d05_domain_no_overflow(self):
        row = self.output(self.row(minimum="9999999999999999.9999", period="HOURLY"))
        self.assertEqual(row.normalized_min_salary, Decimal("9999999999999999.9999") * Decimal(2080))
        self.assertEqual(row.normalization_status, "USABLE")
        source = self.df([self.row(minimum="0.0001", period="MONTHLY")])
        out = normalize(source, self.policy)
        self.assertEqual(out.schema["normalized_min_salary"].dataType.simpleString(), "decimal(38,4)")
        self.assertEqual(out.first().normalized_min_salary, Decimal("0.0012"))

    def test_compensation_excluded_or_ambiguous(self):
        commission = self.output(self.row(median="100", compensation="COMMISSION"))
        self.assertEqual(commission.normalization_status, "EXCLUDED")
        self.assertIn("EXCLUDED_COMPENSATION_TYPE", commission.reason_codes)
        self.assertEqual(self.output(self.row(median="100", compensation=None)).normalization_status, "AMBIGUOUS")

    def test_token_case_whitespace_raw_preserved(self):
        row = self.output(self.row(median="100", currency=" usd ", period=" yearly "))
        self.assertEqual(row.normalized_currency, "USD")
        self.assertEqual(row.raw_postings.currency, " usd ")
        self.assertEqual(row.source_pay_period, " yearly ")

    def test_upstream_normalized_salary_never_used_as_fallback(self):
        row = self.row()
        row["normalized_salary"] = Decimal("100000")
        out = self.output(row)
        self.assertEqual(out.normalization_status, "MISSING")
        self.assertEqual(out.raw_postings_normalized_salary, Decimal("100000"))
        self.assertIsNone(out.normalized_med_salary)

    def test_grain_schema_null_and_duplicate_guard(self):
        from pyspark.sql import functions as F
        with self.assertRaises(ValueError):
            key_stats(self.df([self.row(), self.row()]))
        with self.assertRaises(ValueError):
            key_stats(self.df([self.row(job=None)]))
        with self.assertRaises(ValueError):
            input_schema_check(self.df([self.row()]).withColumn("min_salary", F.lit(1.1)))

    def test_parquet_roundtrip_determinism_and_tamper_validation(self):
        from pyspark.sql import functions as F
        source = self.df([self.row(1), self.row(2, minimum="12.1234", maximum="30", period="HOURLY"), self.row(3, median="0")])
        out = normalize(source, self.policy)
        path = ROOT / "tmp/d07_tests" / uuid.uuid4().hex / "salaries.parquet"
        out.repartition(2).write.mode("errorifexists").parquet(str(path))
        readback = self.spark.read.parquet(str(path))
        self.assertEqual(validate(source, readback, self.policy, 3)["status"], "PASS")
        self.assertEqual(out.exceptAll(normalize(source.repartition(1), self.policy)).count(), 0)
        with self.assertRaises(ValueError):
            validate(source, readback.withColumn("normalized_currency", F.lit("USD")), self.policy, 3)

    def test_existing_output_and_traversal_refused(self):
        with self.assertRaises(ValueError):
            safe_output(ROOT, "../canonical")
        temp = ROOT / "tmp/d07_tests" / uuid.uuid4().hex
        target = safe_output(temp, "first")
        target.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            safe_output(temp, "first")

    def test_downstream_contract_guard_and_three_way_population(self):
        source = self.df([self.row(1, median="100"), self.row(2), self.row(3)])
        salary = normalize(source, self.policy)
        classification = self.spark.createDataFrame([(1, "ACCEPT", True, True, "0.2.2", "fixture"),
            (2, "REVIEW", None, True, "0.2.2", "fixture"), (3, "REJECT", False, True, "0.2.2", "fixture")],
            "job_id long, it_decision string, is_it boolean, _d06_present boolean, taxonomy_version string, taxonomy_sha256 string")
        with self.assertRaises(PermissionError):
            join_classification(salary, classification)
        # Synthetic DataFrames only; not an Official approval or FULL execution.
        joined = join_classification(salary, classification, accept_policy_approved=True)
        self.assertEqual(joined.count(), 3)
        self.assertEqual(joined.filter("it_decision='REVIEW' AND is_it IS NULL").count(), 1)
        with self.assertRaises(ValueError):
            join_classification(salary, classification.union(classification.limit(1)), accept_policy_approved=True)

    def test_invalid_policy_rejected(self):
        policy = json.loads((ROOT / "config/d07_salary_policy_v1.json").read_text(encoding="utf8"))
        policy["annualization"]["hours_per_week"] = 0
        path = ROOT / "tmp/d07_tests" / uuid.uuid4().hex / "bad_policy.json"
        write_new(path, policy)
        with self.assertRaises(ValueError):
            load_policy(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
