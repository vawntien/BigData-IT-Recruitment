"""Semantics, final Arrow payloads and authorization boundaries of MVP demos.

Only in-memory fixtures; no received analytics payload is read by these tests.
Existing Q01 suite separately covers real ZIP/hash/manifest/consent failures.
"""
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASHBOARD))
from components import analytics_demo as model, analytics_views as view, q01_real_preview as real, artifact_gate


class SemanticTests(unittest.TestCase):
    def test_all_queries_have_fresh_valid_synthetic_fixtures(self):
        for query in view.QUERIES:
            with self.subTest(query=query):
                first = model.validate_demo(model.build_demo(query), query)
                second = model.build_demo(query)
                self.assertEqual(first, second)
                self.assertIsNot(first, second)
                self.assertEqual(first.origin, "SYNTHETIC_SAMPLE")

    def test_missing_and_literal_unknown_stay_distinct(self):
        p = model.build_demo("Q02").partitions[0]
        self.assertEqual((p.population, p.known, p.missing), (100, 85, 15))
        rows = {r.key: r for r in p.rows}
        self.assertEqual(rows[None].count, 15)
        self.assertIsNone(rows[None].share_known)
        self.assertEqual(rows["Unknown"].count, 5)
        self.assertNotEqual(model.bucket_label(None), model.bucket_label("Unknown"))

    def test_raw_locations_not_merged(self):
        p = model.build_demo("Q03").partitions[0]
        self.assertEqual({r.key: r.count for r in p.rows}, {"Hanoi": 35, "Ha Noi": 25, "Remote": 20, "Unknown": 10, None: 10})

    def test_remote_false_null_and_conditional_denominator(self):
        p = model.build_demo("Q04").partitions[1]
        rows = {r.key: r for r in p.rows}
        self.assertEqual((rows[True].count, rows[False].count, rows[None].count), (30, 10, 60))
        self.assertEqual((p.population, p.known), (100, 40))
        self.assertEqual(rows[True].share_all, .3)
        self.assertEqual(rows[True].share_known, .75)

    def test_time_gaps_and_bases_remain_separate(self):
        demo = model.build_demo("Q08")
        self.assertEqual([sum(r.count for r in p.rows) for p in demo.partitions], [90, 90, 80, 80])
        self.assertEqual([p.missing for p in demo.partitions], [10, 10, 20, 20])
        self.assertEqual([r.key for r in demo.partitions[0].rows], ["2026-01", "2026-02", "2026-04"])

    def test_skill_scopes_include_zero_hit_and_overlap(self):
        d = model.build_demo("Q06")
        global_scope = d.skills[0]
        self.assertEqual((global_scope.population, global_scope.zero_hit), (12, 4))
        self.assertEqual({r.name: r.count for r in global_scope.rows}, {"Python": 6, "SQL": 5, "Docker": 3})
        self.assertGreater(sum(r.share for r in global_scope.rows), 1)
        missing = next(s for s in d.skills if s.dimension == "experience" and s.bucket is None)
        self.assertEqual((missing.population, missing.zero_hit), (3, 1))

    def test_zero_denominator_has_no_zero_rate(self):
        d = model.Demo("Q02", (model.Partition("experience", 0, 0, 0, (model.Bucket(None, 0, None, None),)),))
        model.validate_demo(d, "Q02")
        p = replace(d.partitions[0], rows=(model.Bucket(None, 0, 0., None),))
        with self.assertRaises(ValueError):
            model.validate_demo(replace(d, partitions=(p,)), "Q02")

    def test_reject_wrong_origin_query_duplicate_and_bad_rate(self):
        d = model.build_demo("Q02")
        p = d.partitions[0]
        invalids = (replace(d, origin="REAL"), replace(d, query="Q03"),
                    replace(d, partitions=(replace(p, rows=p.rows + (p.rows[0],)),)),
                    replace(d, partitions=(replace(p, rows=(replace(p.rows[0], share_all=float("nan")),) + p.rows[1:]),)),
                    replace(d, partitions=(replace(p, population=99),)))
        for invalid in invalids:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                model.validate_demo(invalid, "Q02")

    def test_reject_negative_bool_count_and_skill_scope_mismatch(self):
        d = model.build_demo("Q02")
        for count in (-1, True):
            p = replace(d.partitions[0], rows=(replace(d.partitions[0].rows[0], count=count),) + d.partitions[0].rows[1:])
            with self.assertRaises(ValueError):
                model.validate_demo(replace(d, partitions=(p,)), "Q02")
        skills = model.build_demo("Q06")
        with self.assertRaises(ValueError):
            model.validate_demo(replace(skills, skills=(replace(skills.skills[0], zero_hit=13),) + skills.skills[1:]), "Q06")
        with self.assertRaises(ValueError):
            model.validate_demo(replace(skills, skills=skills.skills[:-1]), "Q06")

    def test_week_starts_and_granularity_totals_are_validated(self):
        d = model.build_demo("Q08")
        p = d.partitions[1]
        invalid = replace(p, rows=(replace(p.rows[0], key="2026-01-06"),) + p.rows[1:])
        with self.assertRaises(ValueError):
            model.validate_demo(replace(d, partitions=(d.partitions[0], invalid) + d.partitions[2:]), "Q08")

    def test_time_bases_cannot_claim_different_populations(self):
        d = model.build_demo("Q08")
        doubled = tuple(replace(p, population=2 * p.population, known=2 * p.known,
                              missing=2 * p.missing, rows=tuple(replace(r, count=2 * r.count) for r in p.rows))
                        for p in d.partitions[2:])
        with self.assertRaises(ValueError):
            model.validate_demo(replace(d, partitions=d.partitions[:2] + doubled), "Q08")


class PageTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.readers = []
        for target, name in ((pd, "read_csv"), (pd, "read_parquet"), (pq, "read_table"), (pq, "ParquetFile"), (real, "load_q01_preview")):
            self.readers.append(stack.enter_context(patch.object(target, name, side_effect=AssertionError("FORBIDDEN_REAL_READER"))))

    def page(self, name="12_Query_Demo.py"):
        a = AppTest.from_file(str(DASHBOARD / "views" / name)).run(timeout=20)
        self.assertFalse(a.exception)
        return a

    def on(self, query):
        a = self.page()
        if query != "Q02":
            a.selectbox[0].set_value(query).run(timeout=20)
        a.toggle[0].set_value(True).run(timeout=20)
        self.assertFalse(a.exception)
        return a

    def charts(self, app):
        result = []
        for chart in app.get("arrow_vega_lite_chart"):
            with pa.ipc.open_stream(pa.BufferReader(chart.proto.data.data)) as reader:
                result.append((json.loads(chart.proto.spec), reader.read_all().to_pandas()))
        return result

    def no_findings(self, a):
        self.assertEqual((len(a.metric), len(a.dataframe), len(self.charts(a))), (0, 0, 0))

    def test_real_pages_require_submit_without_reader_or_false_kpi(self):
        for name in ("8_Experience.py", "9_Locations.py", "10_Work_Type.py", "11_Time_Trends.py", "2_Skills.py"):
            with self.subTest(name=name):
                a = self.page(name)
                self.no_findings(a)
                self.assertFalse(a.toggle)
                self.assertTrue(any("Production Gate CLOSED" in x.value for x in a.warning))
        for reader in self.readers:
            reader.assert_not_called()
        self.assertEqual(artifact_gate.real_artifact_status(exists=True), "BLOCKED")

    def test_demo_default_off_and_no_build_or_real_read(self):
        with patch.object(view, "build_demo") as build:
            a = self.page()
        build.assert_not_called()
        self.assertFalse(a.toggle[0].value)
        self.no_findings(a)
        for reader in self.readers:
            reader.assert_not_called()

    def test_demo_readers_never_called_for_all_queries(self):
        for query in view.QUERIES:
            self.on(query)
        for reader in self.readers:
            reader.assert_not_called()

    def test_query_change_does_not_transfer_opt_in(self):
        a = self.on("Q02")
        a.selectbox[0].set_value("Q06").run(timeout=20)
        self.assertFalse(a.toggle[0].value)
        self.no_findings(a)
        a.selectbox[0].set_value("Q02").run(timeout=20)
        self.assertFalse(a.toggle[0].value)
        self.no_findings(a)

    def test_off_clears_results(self):
        a = self.on("Q02")
        a.toggle[0].set_value(False).run(timeout=20)
        self.no_findings(a)

    def test_failure_after_success_has_no_partial_or_cached_results(self):
        a = self.on("Q02")
        bad = replace(model.build_demo("Q02"), origin="REAL")
        for result in (bad, None):
            with patch.object(view, "build_demo", return_value=result):
                a.run(timeout=20)
            self.assertFalse(a.exception)
            self.no_findings(a)
            self.assertIn("INVALID_SYNTHETIC_DATA", a.error[0].value)
        with patch.object(view, "build_demo", side_effect=ValueError("PRIVATE_CANARY")):
            a.run(timeout=20)
        self.no_findings(a)
        self.assertNotIn("PRIVATE_CANARY", " ".join(x.value for x in a.error))

    def test_q02_chart_table_and_null_bucket_parity(self):
        a = self.on("Q02")
        self.assertEqual([m.value for m in a.metric], ["100", "85", "15"])
        spec, frame = self.charts(a)[0]
        self.assertEqual(frame["Số tin mẫu"].tolist(), a.dataframe[0].value["Số tin mẫu"].tolist())
        self.assertEqual(dict(zip(frame["Nhóm"], frame["Số tin mẫu"])),
                         {"Entry": 35, "Mid-Senior": 30, "Associate": 15, "Unknown": 5, "Không xác định (NULL)": 15})
        self.assertEqual(spec["encoding"]["x"]["field"], "Số tin mẫu")
        self.assertEqual(spec["encoding"]["x"]["axis"]["tickMinStep"], 1)

    def test_location_top_n_keeps_denominators_and_complete_table(self):
        a = self.on("Q03")
        before = [m.value for m in a.metric]
        a.selectbox[1].set_value(3).run(timeout=20)
        _, frame = self.charts(a)[0]
        self.assertEqual(len(frame), 3)
        self.assertEqual([m.value for m in a.metric], before)
        self.assertTrue((frame["Mẫu số có giá trị"] == 90).all())
        self.assertEqual(len(a.dataframe[0].value), 5)

    def test_remote_final_payload_retains_three_buckets(self):
        a = self.on("Q04")
        frame = self.charts(a)[1][1]
        self.assertEqual(dict(zip(frame["Nhóm"], frame["Số tin mẫu"])), {"TRUE": 30, "FALSE": 10, "Không xác định (NULL)": 60})
        self.assertEqual(a.dataframe[1].value["Mẫu số có giá trị"].tolist(), [40] * 3)

    def test_time_granularity_changes_only_periods_not_basis_populations(self):
        a = self.on("Q08")
        before = [m.value for m in a.metric]
        self.assertEqual(before, ["100", "90", "10", "100", "80", "20"])
        self.assertEqual([c[1]["Số tin mẫu"].sum() for c in self.charts(a)], [90, 80])
        self.assertNotIn("2026-03", self.charts(a)[0][1]["Kỳ UTC"].tolist())
        a.radio[0].set_value("Tuần").run(timeout=20)
        self.assertEqual([m.value for m in a.metric], before)
        self.assertEqual(self.charts(a)[0][1]["Kỳ UTC"].tolist(), ["2026-01-05", "2026-02-02", "2026-04-06"])

    def test_skills_top_n_uses_zero_hit_in_denominator(self):
        a = self.on("Q06")
        self.assertEqual([m.value for m in a.metric[:3]], ["12", "8", "4"])
        self.assertEqual(len(self.charts(a)), 3)
        before = [m.value for m in a.metric]
        a.selectbox[1].set_value(1).run(timeout=20)
        frame = self.charts(a)[0][1]
        self.assertEqual(frame["Số tin mẫu"].tolist(), [6])
        self.assertEqual(frame["Mẫu số scope"].tolist(), [12])
        self.assertEqual(frame["Tỷ lệ (%)"].tolist(), [50.])
        self.assertEqual([m.value for m in a.metric], before)
        self.assertEqual(len(a.dataframe[0].value), 3)

    def test_skills_group_and_experience_are_independent(self):
        a = self.on("Q06")
        # query, global Top N, group scope, group Top N, experience scope, experience Top N
        before = self.charts(a)[2][1].copy(deep=True)
        self.assertEqual(self.charts(a)[2][0]["encoding"]["x"]["axis"]["values"], [0, 1, 2])
        a.selectbox[2].set_value(1).run(timeout=20)
        self.assertEqual([m.value for m in a.metric[3:6]], ["5", "3", "2"])
        pd.testing.assert_frame_equal(self.charts(a)[2][1], before)
        self.assertFalse(a.multiselect)


if __name__ == "__main__":
    unittest.main(verbosity=2)
