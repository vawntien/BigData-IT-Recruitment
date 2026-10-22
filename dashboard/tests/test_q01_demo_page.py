"""Actual Streamlit AppTest runs; never a claim of browser runtime validation."""

from dataclasses import replace
from decimal import Decimal
from contextlib import ExitStack
from fractions import Fraction
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
from streamlit.testing.v1 import AppTest
from streamlit.runtime.pages_manager import PagesManager
from streamlit.util import calc_md5

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASHBOARD_DIR))
from components import q01_demo as d, q01_adapter as q, data_loader as legacy


class Q01DemoPageTests(unittest.TestCase):
    def setUp(self):
        # Streamlit 1.38 AppTest omits the page bytecode cache required by
        # native st.navigation. Supply bytecode only in this test harness.
        cache = patch.object(PagesManager, "get_page_script_byte_code",
                             lambda _, path: compile(Path(path).read_text(encoding="utf-8"), str(path), "exec"))
        cache.start()
        self.addCleanup(cache.stop)
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

    def navigate(self, app, name):
        # Native pages use URL hashes; AppTest.switch_page in 1.38 still uses
        # legacy file hashes. Keep the same live session and widget cleanup.
        routes = {"4_Q01_Synthetic_Demo.py": "Q01_Synthetic_Demo",
                  "1_Overview.py": "Overview", "2_Skills.py": "Skills"}
        app._page_hash = calc_md5(routes[name])
        return app.run(timeout=20)

    def page(self):
        app = AppTest.from_file(str(DASHBOARD_DIR / "views" / "4_Q01_Synthetic_Demo.py")).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        return app

    def on(self, app=None):
        app = self.page() if app is None else app
        app.toggle[0].set_value(True).run(timeout=20)
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
        self.assertEqual(len(app.toggle), 1)
        self.assertFalse(app.toggle[0].value)
        self.assertEqual(app.title[0].value, "Q01 · Minh họa")

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
        self.assertTrue(app.toggle[0].value)
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
        self.assertEqual(app.metric[0].label, "Mẫu số giả lập B")
        self.assertEqual(app.metric[0].value, "10")

    def test_t10_unknown_visible(self):
        self.assertIn("DEMO_UNKNOWN", self.on().dataframe[0].value.Category.tolist())

    def test_t11_demo_label_permanent(self):
        app = self.page()
        self.assertIn("SYNTHETIC DEMO ONLY", self.text(app))
        self.on(app)
        self.assertIn("SYNTHETIC DEMO ONLY", self.text(app))

    def test_t12_no_real_findings_claim(self):
        self.assertIn("Không phải kết quả tuyển dụng IT thực tế.", self.text(self.on()))

    def test_t13_overlap_note(self):
        self.assertIn("Nhóm có thể chồng lặp: tổng tỷ lệ có thể vượt 100%", self.text(self.on()))

    def test_t14_shares_remain_160_percent(self):
        shares = self.on().dataframe[0].value["Share %"].tolist()
        self.assertEqual(shares, ["80.00", "70.00", "10.00"])
        self.assertEqual(sum(map(Decimal, shares)), Decimal("160"))

    def test_t15_on_off_clears_findings_without_adapter_call(self):
        app = self.on()
        self.assertEqual(len(app.dataframe), 1)
        with patch.object(q, "build_q01_synthetic_view_model") as adapter:
            app.toggle[0].set_value(False).run(timeout=20)
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
        self.assertNotIn("Ngữ cảnh giả lập", self.text(app))

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
                self.navigate(app, "4_Q01_Synthetic_Demo.py")
                self.on(app)
                self.navigate(app, page)
                self.assertEqual(len(app.exception), 0)
                if page == "1_Overview.py":
                    self.assertFalse(app.toggle[0].value)
                else:
                    self.assertEqual(len(app.toggle), 0)
                self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)

    def test_t25_fresh_session_and_return_navigation_off(self):
        self.on()
        self.assertFalse(self.page().toggle[0].value)
        app = AppTest.from_file(str(DASHBOARD_DIR / "app.py")).run(timeout=20)
        self.navigate(app, "4_Q01_Synthetic_Demo.py")
        self.on(app)
        self.navigate(app, "2_Skills.py")
        self.navigate(app, "4_Q01_Synthetic_Demo.py")
        self.assertFalse(app.toggle[0].value)
        self.no_findings(app)

    def test_t26_existing_overview_behavior_preserved(self):
        frame = pd.DataFrame(dict(category=["DEMO_ONLY"], experience_level=["Entry"],
                                  location=["DEMO"], work_type=["Full-time"], job_count=[2],
                                  data_source=["SYNTHETIC_SAMPLE"]))
        app = AppTest.from_file(str(DASHBOARD_DIR / "views" / "1_Overview.py")).run(timeout=20)
        self.assertFalse(app.toggle[0].value)
        with patch.object(legacy, "load_overview_data", return_value=(frame, "SYNTHETIC_SAMPLE", "demo")):
            app.toggle[0].set_value(True).run(timeout=20)
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

    def _h_chart_mapping(self, app):
        """Decode the named Arrow dataset actually referenced by the chart.

        Streamlit 1.38 AppTest exposes ArrowVegaLiteChart.proto. A changed or
        unsupported representation must fail, never skip numeric assertions.
        """
        charts = app.get("arrow_vega_lite_chart")
        self.assertEqual(len(charts), 1)
        proto = charts[0].proto
        spec = json.loads(proto.spec)
        self.assertEqual(spec["mark"]["type"], "bar")
        self.assertEqual(spec["encoding"]["y"]["field"], "Category")
        self.assertEqual(spec["encoding"]["x"]["field"], "Share %")
        self.assertEqual(spec["encoding"]["x"]["type"], "quantitative")
        self.assertNotEqual(spec["encoding"]["x"].get("stack"), "normalize")
        self.assertFalse(spec.get("transform"))
        # Direct Vega-Lite uses the primary Arrow payload instead of the
        # Altair named dataset. Decode the actual emitted data, never a mock.
        self.assertNotIn("data", spec)
        self.assertEqual(len(proto.datasets), 0)
        payload = proto.data.data
        self.assertTrue(payload)
        with pa.ipc.open_stream(pa.BufferReader(payload)) as reader:
            frame = reader.read_all().to_pandas()
        self.assertEqual(list(frame.columns), ["Category", "Share %"])
        self.assertEqual(len(frame), 3)
        self.assertFalse(frame.isna().any().any())
        categories = frame["Category"].tolist()
        shares = frame["Share %"].tolist()
        self.assertTrue(all(type(category) is str for category in categories))
        self.assertEqual(len(set(categories)), len(categories))
        self.assertTrue(all(type(share) is float for share in shares))
        return dict(zip(categories, shares))

    def _h_assert_success(self, app):
        self.assertEqual(len(app.exception), 0)
        self.assertIs(app.toggle[0].value, True)
        self.assertEqual(len(app.error), 0)
        self.assertEqual(self._h_chart_mapping(app),
                         {"DEMO_A": 80.0, "DEMO_B": 70.0, "DEMO_UNKNOWN": 10.0})
        self.assertEqual(len(app.dataframe), 1)
        table = app.dataframe[0].value
        self.assertEqual(list(table.columns), ["Category", "Count", "Share %"])
        self.assertEqual(table.to_dict("records"), [
            {"Category": "DEMO_A", "Count": 8, "Share %": "80.00"},
            {"Category": "DEMO_B", "Count": 7, "Share %": "70.00"},
            {"Category": "DEMO_UNKNOWN", "Count": 1, "Share %": "10.00"},
        ])
        self.assertEqual(len(app.metric), 1)
        self.assertEqual(app.metric[0].label, "Mẫu số giả lập B")
        self.assertEqual(app.metric[0].value, "10")
        self.assertIn("Ngữ cảnh giả lập (run / population / filter): DEMO_RUN / DEMO_POP / DEMO_ALL", self.text(app))
        self.assertIn("Taxonomy giả lập: DEMO_TAXONOMY", self.text(app))

    def test_h01_actual_chart_arrow_payload_and_independent_table(self):
        with patch.object(q, "build_q01_synthetic_view_model", wraps=q.build_q01_synthetic_view_model) as adapter:
            app = self.on()
        adapter.assert_called_once()
        self._h_assert_success(app)
        chart_values = self._h_chart_mapping(app)
        self.assertEqual(set(chart_values), {"DEMO_A", "DEMO_B", "DEMO_UNKNOWN"})
        self.assertEqual(sum(chart_values.values()), 160.0)
        # Table assertions read the table, not the chart decoder or its output.
        table = app.dataframe[0].value
        self.assertEqual(sum(Decimal(value) for value in table["Share %"]), Decimal("160"))

    def test_h02_stored_fraction_reaches_chart_and_table(self):
        # Probe-only tolerance: exercise real upstream validation before injecting
        # its result at the adapter return seam to isolate actual page rendering.
        # This is not a production tolerance policy or a changed demo fixture.
        inputs = d.build_demo_inputs()
        datasets, plan, mapping = inputs
        datasets[0].dataframe.at[0, "demo_share"] = Decimal("0.800123")
        schema = plan.checks[0]
        metric = replace(plan.checks[1], spec=replace(plan.checks[1].spec, tolerance=Decimal("0.001")))
        probe_plan = replace(plan, checks=(schema, metric))
        before = datasets[0].dataframe.copy(deep=True)
        from decimal import getcontext
        context_before = getcontext().copy()
        validated = q.build_q01_synthetic_view_model(datasets, probe_plan, mapping, True)
        self.assertIs(validated.passed, True)
        self.assertEqual(validated.rows[0].category_count, 8)
        self.assertEqual(validated.population_count, 10)
        self.assertEqual(validated.rows[0].share_fraction, Fraction(800123, 1000000))
        pd.testing.assert_frame_equal(datasets[0].dataframe, before, check_exact=True)
        with patch.object(q, "build_q01_synthetic_view_model", return_value=validated) as adapter:
            app = self.on()
        adapter.assert_called_once()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        chart = self._h_chart_mapping(app)
        self.assertEqual(chart, {"DEMO_A": 80.0123, "DEMO_B": 70.0, "DEMO_UNKNOWN": 10.0})
        self.assertNotEqual(chart["DEMO_A"], 80.0)
        self.assertEqual(len(app.dataframe), 1)
        table = app.dataframe[0].value
        self.assertEqual(table.to_dict("records"), [
            {"Category": "DEMO_A", "Count": 8, "Share %": "80.01"},
            {"Category": "DEMO_B", "Count": 7, "Share %": "70.00"},
            {"Category": "DEMO_UNKNOWN", "Count": 1, "Share %": "10.00"},
        ])
        self.assertEqual(sum(Decimal(str(value)) for value in chart.values()), Decimal("160.0123"))
        context_after = getcontext()
        for name in ("prec", "rounding", "Emin", "Emax", "capitals", "clamp", "flags", "traps"):
            self.assertEqual(getattr(context_after, name), getattr(context_before, name))

    def _h_success_to_failure(self, scenario):
        # Positive control is an actual published pipeline run on a fresh page.
        # Fault patches are installed only after verified successful rendering.
        with patch.object(q, "build_q01_synthetic_view_model", wraps=q.build_q01_synthetic_view_model) as positive:
            app = self.on()
        positive.assert_called_once()
        self._h_assert_success(app)
        actual_adapter = q.build_q01_synthetic_view_model
        actual_orchestrator = q.run_synthetic_validation_plan
        evidence = []

        def observe_orchestration(*args):
            result = actual_orchestrator(*args)
            evidence.append(result)
            return result

        with ExitStack() as stack:
            if scenario in ("schema", "metric"):
                inputs = d.build_demo_inputs()
                column = "demo_n" if scenario == "schema" else "demo_share"
                inputs[0][0].dataframe.at[0, column] = -1 if scenario == "schema" else Decimal("0.2")
                snapshot = inputs[0][0].dataframe.copy(deep=True)
                fixture = stack.enter_context(patch.object(d, "build_demo_inputs", return_value=inputs))
                orchestration = stack.enter_context(patch.object(q, "run_synthetic_validation_plan", side_effect=observe_orchestration))
                fault = stack.enter_context(patch.object(q, "build_q01_synthetic_view_model", wraps=actual_adapter))
                expected_code = "ORCHESTRATION_FAILED"
            elif scenario == "exception":
                fault = stack.enter_context(patch.object(q, "build_q01_synthetic_view_model",
                                                         side_effect=RuntimeError("HARDENING_CANARY_EXCEPTION")))
                expected_code = "DEMO_EXECUTION_EXCEPTION"
            else:
                good = actual_adapter(*d.build_demo_inputs(), True)
                self.assertIs(good.passed, True)
                if scenario == "malformed":
                    bad = {"passed": True, "private": "HARDENING_CANARY_RESULT"}
                elif scenario == "empty":
                    bad = replace(good, rows=())
                elif scenario == "checks":
                    bad = replace(good, completed_check_ids=("Schema",))
                else:
                    self.assertEqual(scenario, "denominator")
                    bad = replace(good, population_count=True)
                fault = stack.enter_context(patch.object(q, "build_q01_synthetic_view_model", return_value=bad))
                expected_code = "INVALID_Q01_RESULT"

            # SAME AppTest instance, permission remains ON; do not recreate page.
            app.run(timeout=20)
            fault.assert_called_once()
            self.assertIs(fault.call_args.args[3], True)
            if scenario in ("schema", "metric"):
                fixture.assert_called_once()
                orchestration.assert_called_once()
                self.assertEqual(len(evidence), 1)
                states = {check.check_id: check.status for check in evidence[0].check_results}
                self.assertEqual(states, {"Schema": "FAIL", "Metric": "BLOCKED"} if scenario == "schema"
                                 else {"Schema": "PASS", "Metric": "FAIL"})
                expected_issue = ("Schema", "INVALID_COUNT") if scenario == "schema" else ("Metric", "RATE_INCONSISTENT")
                self.assertIn(expected_issue, tuple((issue.check_id, issue.code) for issue in evidence[0].safe_issues))
                pd.testing.assert_frame_equal(inputs[0][0].dataframe, snapshot, check_exact=True)

        self.assertIs(app.toggle[0].value, True)
        self.no_findings(app)
        self.assertEqual(len(app.error), 1)
        self.assertEqual(app.error[0].value, "INVALID: " + expected_code)
        visible = self.text(app)
        for forbidden in ("HARDENING_CANARY", "Traceback", "Ngữ cảnh giả lập (", "Taxonomy giả lập:",
                          "Mẫu số giả lập B", "DEMO_A", "DEMO_B", "DEMO_UNKNOWN",
                          "DEMO_RUN", "DEMO_POP", "DEMO_ALL", "DEMO_TAXONOMY", "Nhóm có thể chồng lặp:"):
            self.assertNotIn(forbidden, visible)
        self.assertIn("SYNTHETIC DEMO ONLY", visible)

    def test_h03_success_to_schema_failure(self):
        self._h_success_to_failure("schema")

    def test_h04_success_to_metric_failure(self):
        self._h_success_to_failure("metric")

    def test_h05_success_to_malformed_result(self):
        self._h_success_to_failure("malformed")

    def test_h06_success_to_adapter_exception(self):
        self._h_success_to_failure("exception")

    def test_h07_success_to_empty_findings(self):
        self._h_success_to_failure("empty")

    def test_h08_success_to_missing_required_check(self):
        self._h_success_to_failure("checks")

    def test_h09_success_to_invalid_denominator(self):
        self._h_success_to_failure("denominator")


if __name__ == "__main__":
    unittest.main(verbosity=2)
