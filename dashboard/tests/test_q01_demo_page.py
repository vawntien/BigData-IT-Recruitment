"""Actual Streamlit AppTest runs; never a claim of browser runtime validation."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASHBOARD_DIR))
from components import q01_demo as d, q01_adapter as q, data_loader as legacy


class Q01DemoPageTests(unittest.TestCase):
    def setUp(self):
        # Fail on any CSV/Parquet reader, including unexpected real/private I/O.
        for name in ("read_csv", "read_parquet"):
            patcher = patch.object(pd, name, side_effect=AssertionError("SENSITIVE_FORBIDDEN_READER"))
            spy = patcher.start()
            self.addCleanup(patcher.stop)
            self.addCleanup(spy.assert_not_called)
        missing = DASHBOARD_DIR / "tests" / "_missing_analytics"
        self.assertFalse(missing.exists())
        patcher = patch.object(legacy, "ANALYTICS_DIR", missing)
        patcher.start()
        self.addCleanup(patcher.stop)

    def page(self):
        app = AppTest.from_file(str(DASHBOARD_DIR / "pages" / "4_Q01_Synthetic_Demo.py")).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        return app

    def on(self, app=None):
        app = self.page() if app is None else app
        app.checkbox[0].set_value(True).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        return app

    def no_findings(self, app):
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)
        self.assertEqual(len(app.dataframe), 0)
        self.assertEqual(len(app.metric), 0)

    def text(self, app):
        return "\n".join(str(item.value) for name in ("title", "warning", "caption", "info", "error")
                         for item in getattr(app, name))

    def test_t01_initial_off(self):
        app = self.page()
        self.assertEqual(len(app.checkbox), 1)
        self.assertFalse(app.checkbox[0].value)
        self.assertEqual(app.title[0].value, "Q01 — Synthetic Demo")

    def test_t02_off_banner_and_disabled_state(self):
        app = self.page()
        self.assertIn("SYNTHETIC DEMO ONLY", self.text(app))
        self.assertIn("DEMO_DISABLED", self.text(app))

    def test_t03_off_no_fixture_or_adapter(self):
        with patch.object(d, "build_demo_inputs") as fixture, patch.object(q, "build_q01_synthetic_view_model") as adapter:
            self.no_findings(self.page())
        fixture.assert_not_called()
        adapter.assert_not_called()

    def test_t04_off_no_chart_table_or_denominator(self):
        self.no_findings(self.page())

    def test_t05_opt_in_runs_synthetic_flow(self):
        app = self.on()
        self.assertTrue(app.checkbox[0].value)
        self.assertEqual(len(app.error), 0)
        self.assertEqual(len(app.dataframe), 1)

    def test_t06_actual_adapter_executed(self):
        with patch.object(q, "build_q01_synthetic_view_model", wraps=q.build_q01_synthetic_view_model) as adapter:
            self.on()
        adapter.assert_called_once()
        self.assertIs(adapter.call_args.args[3], True)
        self.assertEqual(adapter.call_args.args[0][0].dataframe.source.tolist(), ["SYNTHETIC_SAMPLE"] * 3)

    def test_t07_bar_chart_exists(self):
        app = self.on()
        self.assertEqual(len(app.get("arrow_vega_lite_chart")), 1)
        # The supported chart element contains the emitted Vega-Lite specification.
        self.assertIn('"bar"', app.get("arrow_vega_lite_chart")[0].proto.spec)
        self.assertNotIn('"arc"', app.get("arrow_vega_lite_chart")[0].proto.spec)

    def test_t08_curated_table_only(self):
        table = self.on().dataframe[0].value
        self.assertEqual(list(table.columns), ["Category", "Count", "Share %"])
        self.assertEqual(table["Count"].tolist(), [8, 7, 1])
        self.assertEqual(len(table), 3)

    def test_t09_declared_denominator(self):
        app = self.on()
        self.assertEqual(len(app.metric), 1)
        self.assertEqual(app.metric[0].label, "Declared synthetic denominator B")
        self.assertEqual(app.metric[0].value, "10")

    def test_t10_unknown_visible(self):
        self.assertIn("DEMO_UNKNOWN", self.on().dataframe[0].value.Category.tolist())

    def test_t11_demo_label_permanent(self):
        app = self.page()
        self.assertIn("SYNTHETIC DEMO ONLY", self.text(app))
        self.on(app)
        self.assertIn("SYNTHETIC DEMO ONLY", self.text(app))

    def test_t12_no_real_findings_claim(self):
        self.assertIn("No real IT recruitment findings.", self.text(self.on()))

    def test_t13_overlap_note(self):
        self.assertIn("Overlapping groups: shares may sum above 100%", self.text(self.on()))

    def test_t14_shares_remain_160_percent(self):
        shares = self.on().dataframe[0].value["Share %"].tolist()
        self.assertEqual(shares, ["80.00", "70.00", "10.00"])
        self.assertEqual(sum(map(Decimal, shares)), Decimal("160"))

    def test_t15_on_off_clears_findings_without_adapter_call(self):
        app = self.on()
        self.assertEqual(len(app.dataframe), 1)
        with patch.object(q, "build_q01_synthetic_view_model") as adapter:
            app.checkbox[0].set_value(False).run(timeout=20)
        adapter.assert_not_called()
        self.no_findings(app)

    def test_t16_failed_rerun_drops_previous_success(self):
        app = self.on()
        bad = q.Q01ConsumerResult("INVALID", False, "Q01_SYNTHETIC_LOGICAL", None, None,
                                  None, (), (), (q.Q01Issue("orchestration", "ORCHESTRATION_FAILED", (), None),))
        with patch.object(q, "build_q01_synthetic_view_model", return_value=bad):
            app.run(timeout=20)
        self.no_findings(app)
        self.assertIn("ORCHESTRATION_FAILED", self.text(app))
        self.assertNotIn("Synthetic context", self.text(app))

    def test_t17_malformed_q01_result_no_findings(self):
        with patch.object(q, "build_q01_synthetic_view_model", return_value={"passed": True, "SENSITIVE": 10}):
            app = self.on()
        self.no_findings(app)
        self.assertIn("INVALID_Q01_RESULT", self.text(app))
        self.assertNotIn("SENSITIVE", self.text(app))

    def test_t18_actual_schema_failure(self):
        inputs = d.build_demo_inputs()
        inputs[0][0].dataframe.at[0, "demo_n"] = -1
        with patch.object(d, "build_demo_inputs", return_value=inputs):
            app = self.on()
        self.no_findings(app)
        self.assertIn("ORCHESTRATION_FAILED", self.text(app))

    def test_t19_actual_metric_failure(self):
        inputs = d.build_demo_inputs()
        inputs[0][0].dataframe.at[0, "demo_share"] = Decimal("0.2")
        with patch.object(d, "build_demo_inputs", return_value=inputs):
            app = self.on()
        self.no_findings(app)
        self.assertIn("ORCHESTRATION_FAILED", self.text(app))

    def test_t20_adapter_exception_controlled(self):
        with patch.object(q, "build_q01_synthetic_view_model", side_effect=RuntimeError("SENSITIVE_EXCEPTION")):
            app = self.on()
        self.no_findings(app)
        self.assertIn("DEMO_EXECUTION_EXCEPTION", self.text(app))

    def test_t21_private_exception_text_absent(self):
        with patch.object(q, "build_q01_synthetic_view_model", side_effect=ValueError("SENSITIVE_DESCRIPTION")):
            app = self.on()
        self.assertNotIn("SENSITIVE", self.text(app))
        self.assertNotIn("Traceback", self.text(app))
        self.no_findings(app)

    def test_t22_no_legacy_loader_calls(self):
        with patch.object(legacy, "load_overview_data") as overview, patch.object(
                legacy, "load_skills_data") as skills, patch.object(legacy, "load_salary_quality_data") as salary:
            app = self.page()
            self.on(app)
        for loader in (overview, skills, salary):
            loader.assert_not_called()

    def test_t23_no_file_readers(self):
        # Reader mocks in setUp assert zero calls even if an exception is caught.
        self.no_findings(self.page())
        self.assertEqual(len(self.on().dataframe), 1)

    def test_t24_navigation_no_permission_transfer(self):
        for page in ("1_Overview.py", "2_Skills.py"):
            with self.subTest(page=page):
                app = AppTest.from_file(str(DASHBOARD_DIR / "app.py")).run(timeout=20)
                app.switch_page("pages/4_Q01_Synthetic_Demo.py").run(timeout=20)
                self.on(app)
                app.switch_page("pages/" + page).run(timeout=20)
                self.assertEqual(len(app.exception), 0)
                self.assertFalse(app.checkbox[0].value)
                self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)

    def test_t25_fresh_session_and_return_navigation_off(self):
        self.on()
        self.assertFalse(self.page().checkbox[0].value)
        app = AppTest.from_file(str(DASHBOARD_DIR / "app.py")).run(timeout=20)
        app.switch_page("pages/4_Q01_Synthetic_Demo.py").run(timeout=20)
        self.on(app)
        app.switch_page("pages/2_Skills.py").run(timeout=20)
        app.switch_page("pages/4_Q01_Synthetic_Demo.py").run(timeout=20)
        self.assertFalse(app.checkbox[0].value)
        self.no_findings(app)

    def test_t26_existing_overview_behavior_preserved(self):
        frame = pd.DataFrame(dict(category=["DEMO_ONLY"], experience_level=["Entry"],
                                  location=["DEMO"], work_type=["Full-time"], job_count=[2],
                                  data_source=["SYNTHETIC_SAMPLE"]))
        app = AppTest.from_file(str(DASHBOARD_DIR / "pages" / "1_Overview.py")).run(timeout=20)
        self.assertFalse(app.checkbox[0].value)
        with patch.object(legacy, "load_overview_data", return_value=(frame, "SYNTHETIC_SAMPLE", "demo")):
            app.checkbox[0].set_value(True).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.get("arrow_vega_lite_chart")), 4)
        self.assertEqual(len(app.metric), 4)

    def test_t27_nested_failure_no_uncaught_exception(self):
        inputs = d.build_demo_inputs()
        result = q.build_q01_synthetic_view_model(*inputs, True)
        bad = replace(result, rows=(replace(result.rows[0], share_fraction="SENSITIVE_SHARE"),))
        with patch.object(q, "build_q01_synthetic_view_model", return_value=bad):
            app = self.on()
        self.no_findings(app)
        self.assertNotIn("SENSITIVE", self.text(app))

    def test_t28_no_production_eligibility_display(self):
        app = self.on()
        self.assertEqual(len(app.success), 0)
        self.assertNotIn("production_eligible", self.text(app))
        self.assertNotIn("ACCEPTED_PRODUCTION", self.text(app))


if __name__ == "__main__":
    unittest.main(verbosity=2)
