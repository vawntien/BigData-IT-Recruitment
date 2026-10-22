"""Synthetic-only safety regressions; no real datasets or Spark execution."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import sys
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASHBOARD_DIR))

from components import data_loader as dl, ui_helpers
from components.artifact_gate import real_artifact_status

LOADERS = (
    (dl.load_overview_data, "overview_analytics", "overview_sample.csv"),
    (dl.load_skills_data, "skills_analytics", "skills_sample.csv"),
    (dl.load_salary_quality_data, "salary_quality_analytics", "salary_quality_sample.csv"),
)
PAGES = (
    ("1_Overview.py", "load_overview_data"),
    ("2_Skills.py", "load_skills_data"),
    ("3_Salary_Quality.py", "load_salary_quality_data"),
)


def fixture():
    # One deliberately synthetic row fits the existing scaffold validators.
    return pd.DataFrame([dict(
        category="DEMO_ONLY", experience_level="Entry", location="DEMO",
        work_type="Full-time", job_count=2, technical_skill="DEMO_SKILL",
        currency="USD", pay_period="YEARLY", median_salary=10,
        data_source="SYNTHETIC_SAMPLE",
    )])


class ArtifactGateTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.analytics = self.root / "analytics"
        self.demo = self.root / "demo"
        self.analytics.mkdir()
        self.demo.mkdir()
        for attribute, value in [("ANALYTICS_DIR", self.analytics), ("SAMPLE_DIR", self.demo)]:
            patcher = patch.object(dl, attribute, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        for _, _, sample in LOADERS:
            fixture().to_csv(self.demo / sample, index=False)

    def assert_closed(self, loader, expected):
        df, status, _ = loader(enable_sample_mode=False)
        self.assertIsNone(df)
        self.assertEqual(status, expected)
        self.assertNotIn(status, ("PRODUCTION", "ACCEPTED_PRODUCTION"))

    def test_t01_default_off_missing_never_falls_back(self):
        for loader, _, _ in LOADERS:
            with self.subTest(loader=loader.__name__):
                df, status, _ = loader()
                self.assertIsNone(df)
                self.assertEqual(status, dl.STATUS_MISSING)

    def test_t02_demo_selection_ignores_analytics(self):
        for _, table, _ in LOADERS:
            (self.analytics / (table + ".parquet")).write_bytes(b"not parquet")
        reader = pd.read_csv
        with patch.object(dl.pd, "read_csv", wraps=reader) as csv_reader, patch.object(dl.pd, "read_parquet") as parquet_reader:
            for loader, _, sample in LOADERS:
                df, status, _ = loader(enable_sample_mode=True)
                self.assertEqual(status, "SYNTHETIC_SAMPLE")
                self.assertEqual(df.category.tolist(), ["DEMO_ONLY"])
                self.assertEqual(csv_reader.call_args.args[0], self.demo / sample)
            parquet_reader.assert_not_called()

    def test_t03_readable_unverified_artifact_is_blocked(self):
        for loader, table, _ in LOADERS:
            pd.DataFrame({"job_count": [1]}).to_csv(self.analytics / (table + ".csv"), index=False)
            self.assert_closed(loader, dl.STATUS_BLOCKED)

    def test_t04_renamed_synthetic_is_not_production(self):
        for loader, table, _ in LOADERS:
            fixture().to_csv(self.analytics / (table + ".csv"), index=False)
            self.assert_closed(loader, dl.STATUS_BLOCKED)

    def test_t05_all_jobs_cannot_reach_it_display(self):
        for loader, table, _ in LOADERS:
            fixture().assign(population_scope="ALL_JOBS", data_source="REAL").to_csv(
                self.analytics / (table + ".csv"), index=False)
            self.assert_closed(loader, dl.STATUS_BLOCKED)

    def test_t06_staging_cannot_reach_it_display(self):
        for loader, table, _ in LOADERS:
            fixture().assign(release_status="REAL_STAGING", data_source="REAL").to_csv(
                self.analytics / (table + ".csv"), index=False)
            self.assert_closed(loader, dl.STATUS_BLOCKED)

    def test_t07_corrupt_parquet_is_invalid_without_csv_or_demo_fallback(self):
        for loader, table, _ in LOADERS:
            (self.analytics / (table + ".parquet")).write_bytes(b"synthetic corrupt parquet")
            fixture().to_csv(self.analytics / (table + ".csv"), index=False)
            self.assert_closed(loader, dl.STATUS_INVALID)

    def test_t08_corrupt_csv_is_invalid_without_demo_fallback(self):
        for loader, table, _ in LOADERS:
            (self.analytics / (table + ".csv")).write_text('column\n"unterminated', encoding="utf-8")
            self.assert_closed(loader, dl.STATUS_INVALID)

    def test_t09_sample_schema_and_tags_are_validated(self):
        for bad in [pd.DataFrame({"unrelated": [1]}), fixture().drop(columns="data_source"),
                    fixture().assign(data_source="REAL"), fixture().iloc[:0]]:
            for loader, _, sample in LOADERS:
                with self.subTest(sample=sample, columns=list(bad.columns)):
                    bad.to_csv(self.demo / sample, index=False)
                    df, status, _ = loader(enable_sample_mode=True)
                    self.assertIsNone(df)
                    self.assertEqual(status, dl.STATUS_INVALID)

    def test_access_or_reader_failure_is_blocked_not_claimed_corrupt(self):
        fixture().to_csv(self.analytics / "overview_analytics.csv", index=False)
        for error in [PermissionError(), ImportError()]:
            with patch.object(dl.pd, "read_csv", side_effect=error):
                self.assert_closed(dl.load_overview_data, dl.STATUS_BLOCKED)

    def test_t10_unknown_and_legacy_statuses_never_render_success(self):
        with patch.object(ui_helpers, "st") as st:
            for status in ["PRODUCTION", "ACCEPTED_PRODUCTION", "REAL_STAGING", "unknown"]:
                ui_helpers.render_data_status_banner(status, "untrusted claim")
            st.success.assert_not_called()
            self.assertEqual(st.error.call_count, 4)

    def test_t12_fabricated_approval_and_manifest_cannot_open_gate(self):
        fake = dict(approved=True, accepted=True, population_scope="IT_ACCEPTED",
                    release_status="ACCEPTED_PRODUCTION", data_source="REAL")
        for loader, table, _ in LOADERS:
            fixture().assign(**fake).to_csv(self.analytics / (table + ".csv"), index=False)
            (self.analytics / (table + ".manifest.json")).write_text(json.dumps(fake), encoding="utf-8")
            self.assert_closed(loader, dl.STATUS_BLOCKED)
        for exists in [False, True]:
            for failed in [False, True]:
                self.assertNotIn(real_artifact_status(exists=exists, read_failed=failed),
                                 ("PRODUCTION", "ACCEPTED_PRODUCTION"))


class PageSafetyTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        patcher = patch.object(dl, "ANALYTICS_DIR", Path(temp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def page(self, name, enable=False):
        # Samples moved into the isolated Demo area; exercise the same loaders
        # and safety assertions through their new presentation entrypoint.
        target = name if name == "1_Overview.py" else "7_Demo_Analytics.py"
        app = AppTest.from_file(str(DASHBOARD_DIR / "views" / target)).run(timeout=20)
        if enable:
            app.toggle[1 if name == "3_Salary_Quality.py" else 0].set_value(True).run(timeout=20)
        return app

    def test_t11_all_pages_require_explicit_demo_and_still_render(self):
        for name, _ in PAGES:
            with self.subTest(page=name):
                app = self.page(name)
                self.assertEqual(len(app.exception), 0)
                self.assertFalse(app.toggle[0].value)
                self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)
                self.assertEqual(len(app.success), 0)
                app.toggle[1 if name == "3_Salary_Quality.py" else 0].set_value(True).run(timeout=20)
                self.assertEqual(len(app.exception), 0)
                self.assertTrue(any("SYNTHETIC MOCKUP DATA" in w.value for w in app.warning))
                self.assertGreater(len(app.get("arrow_vega_lite_chart")), 0)
                self.assertEqual(len(app.success), 0)
                if name == "3_Salary_Quality.py":
                    # Historical audit now has its own page, never salary findings.
                    quality = AppTest.from_file(str(DASHBOARD_DIR / "views" / "6_Data_Quality.py")).run(timeout=20)
                    self.assertIn("HISTORICAL", " ".join(m.value for m in quality.markdown))

    def test_unverified_files_never_reach_page_charts(self):
        for name, loader in PAGES:
            with self.subTest(page=name), patch.object(dl, loader, return_value=(fixture(), dl.STATUS_BLOCKED, "unverified")):
                app = self.page(name, enable=True)
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)
                self.assertEqual(len(app.success), 0)
                self.assertTrue(any("DATA BLOCKED" in w.value for w in app.warning))

    def test_legacy_production_tuple_cannot_bypass_page_gate(self):
        for name, loader in PAGES:
            with self.subTest(page=name), patch.object(dl, loader, return_value=(fixture(), "PRODUCTION", "untrusted")):
                app = self.page(name, enable=True)
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)
                self.assertEqual(len(app.success), 0)
                self.assertTrue(any("DATA BLOCKED" in e.value for e in app.error))

    def test_invalid_sample_cannot_show_demo_banner_or_charts(self):
        for name, loader in PAGES:
            bad = pd.DataFrame({"wrong_column": [1]})
            with self.subTest(page=name), patch.object(dl, loader, return_value=(bad, dl.STATUS_SAMPLE, "invalid demo")):
                app = self.page(name, enable=True)
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)
                self.assertEqual(len(app.success), 0)
                self.assertFalse(any("SYNTHETIC MOCKUP DATA" in w.value for w in app.warning))
                self.assertTrue(any("INVALID DATA" in e.value for e in app.error))


if __name__ == "__main__":
    unittest.main(verbosity=2)
