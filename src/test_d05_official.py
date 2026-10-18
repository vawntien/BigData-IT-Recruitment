"""Small Spark regression checks for D05 contracts; no production writes."""
import unittest
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_canonical_jobs import ROOT, canonical_id, mapped_bridge, save_csv
from d05_utils import aggregate_bridge, check_grain_preserved, get_spark_session, latest_per_key


class D05OfficialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = get_spark_session('BigDataITRecruitment-D05-Regression', ROOT)
        cls.spark.conf.set('spark.sql.shuffle.partitions', '4')

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_integral_identifier_without_float_precision_loss(self):
        self.assertEqual(canonical_id(' 9007199254740993.000 '), 9007199254740993)
        self.assertEqual(canonical_id(str(2**63-1)), 2**63-1)
        for value in ['123.5', '1e3', '', 'NA', str(2**63)]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_id(value)

    def test_missing_industry_name_preserves_code(self):
        bridge = self.spark.sql('SELECT 1L job_id, 99L industry_id UNION ALL SELECT 1L, 4L')
        mapping = self.spark.sql("SELECT 99L industry_id, CAST(NULL AS STRING) industry_name UNION ALL SELECT 4L, 'Software Development'")
        result = mapped_bridge('bridge','mapping','industry_id','industry_name','labels',
                               {'bridge':bridge, 'mapping':mapping}).first()
        self.assertEqual([x.industry_id for x in result.labels], [4,99])
        self.assertEqual(result.labels[1].mapping_status, 'MISSING_LABEL')
        self.assertIsNone(result.labels[1].industry_name)

    def test_sorted_unique_bridge_and_left_join_retains_no_link_job(self):
        bridge = self.spark.sql("SELECT 1L job_id, 'IT' skill_abr UNION ALL SELECT 1L, 'ENG' UNION ALL SELECT 1L, 'IT'")
        jobs = self.spark.sql('SELECT 1L job_id UNION ALL SELECT 2L')
        a = aggregate_bridge(bridge.repartition(2),'job_id','skill_abr','codes')
        b = aggregate_bridge(bridge.repartition(3),'job_id','skill_abr','codes')
        self.assertEqual(a.collect(), b.collect())
        rows = jobs.join(a,'job_id','left').orderBy('job_id').collect()
        self.assertEqual(rows[0].codes, ['ENG','IT'])
        self.assertIsNone(rows[1].codes)
        self.assertEqual(len(rows),2)

    def test_snapshot_is_latest_with_explicit_tie_break(self):
        df = self.spark.sql("""SELECT 1L company_id, TIMESTAMP '2024-01-01 00:00:00' t, 100L employees
            UNION ALL SELECT 1L, TIMESTAMP '2024-02-01 00:00:00', 20L
            UNION ALL SELECT 1L, TIMESTAMP '2024-02-01 00:00:00', 10L""")
        for parts in [2,3]:
            result = latest_per_key(df.repartition(parts),'company_id','t',['employees']).first()
            self.assertEqual(result.employees,10)

    def test_grain_guard_rejects_loss_and_multiplication(self):
        self.assertTrue(check_grain_preserved(2,2,2,2))
        self.assertFalse(check_grain_preserved(2,3,2,2))
        self.assertFalse(check_grain_preserved(2,1,2,1))


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(D05OfficialTests))
    save_csv('d05_official_regression_tests.csv', [dict(
        run_utc=datetime.now(timezone.utc).isoformat(),
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), status='PASS' if result.wasSuccessful() else 'FAIL',
        test_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())])
    sys.exit(0 if result.wasSuccessful() else 1)
