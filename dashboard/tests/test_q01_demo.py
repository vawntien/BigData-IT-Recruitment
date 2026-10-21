"""Pure in-memory integration and hostile-result consumer-boundary tests."""

from dataclasses import FrozenInstanceError, asdict, replace
from decimal import Decimal, Inexact, ROUND_UP, getcontext, localcontext
from fractions import Fraction
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components import q01_demo as d, q01_adapter as q
from components.artifact_gate import real_artifact_status
from components.contract_validator import FieldSpec, ValidationSpec
from components.metric_validator import MetricValidationSpec
from components.validation_orchestrator import DatasetBinding, ValidationCheck, ValidationPlan


class Q01DemoTests(unittest.TestCase):
    def setUp(self):
        self.inputs = d.build_demo_inputs()
        self.good = q.build_q01_synthetic_view_model(*self.inputs, True)
        self.assertTrue(self.good.passed)

    def rejected(self, result, code=None):
        self.assertIs(result.passed, False)
        self.assertIn(result.status, ("INVALID", "BLOCKED"))
        self.assertEqual(result.rows, ())
        self.assertIsNone(result.population_count)
        self.assertIsNone(result.context)
        self.assertIsNone(result.taxonomy_id)
        self.assertTrue(result.issue_codes)
        if code:
            self.assertEqual(result.issue_codes, (code,))
        self.assertNotIn("SENSITIVE", repr(result))

    def test_u01_fixed_fixture_synthetic_only(self):
        datasets, _, mapping = self.inputs
        frame = datasets[0].dataframe
        self.assertEqual(frame.source.tolist(), ["SYNTHETIC_SAMPLE"] * 3)
        self.assertEqual(datasets[0].explicit_origin, "SYNTHETIC_SAMPLE")
        self.assertEqual(frame.demo_cat.tolist(), list(mapping.domain.category_ids))
        self.assertEqual(frame.demo_n.tolist(), [8, 7, 1])
        self.assertEqual(frame.demo_b.tolist(), [10, 10, 10])
        self.assertEqual(frame.demo_share.tolist(), [Decimal("0.8"), Decimal("0.7"), Decimal("0.1")])

    def test_u02_real_types_schema_identity_and_policies(self):
        datasets, plan, mapping = self.inputs
        binding = datasets[0]
        self.assertIs(type(binding), DatasetBinding)
        self.assertIs(type(binding.schema_spec), ValidationSpec)
        self.assertIs(type(plan), ValidationPlan)
        self.assertIs(type(mapping), q.Q01Mapping)
        self.assertEqual(len(plan.checks), 2)
        self.assertTrue(all(type(c) is ValidationCheck and c.required is True for c in plan.checks))
        self.assertIs(plan.checks[0].spec, binding.schema_spec)
        self.assertFalse(binding.schema_spec.allow_empty)
        self.assertFalse(binding.schema_spec.allow_extra_columns)
        self.assertEqual(binding.schema_spec.unique_key, ("demo_run", "demo_pop", "demo_filter", "demo_cat"))
        self.assertEqual(set(binding.schema_spec.required_fields), set(binding.dataframe.columns))
        self.assertEqual(len(binding.schema_spec.required_fields), 8)
        self.assertTrue(all(type(rule) is FieldSpec and not rule.nullable and rule.finite
                            for rule in binding.schema_spec.fields.values()))

    def test_u03_logical_columns_and_metric(self):
        binding, plan, mapping = self.inputs[0][0], self.inputs[1], self.inputs[2]
        self.assertEqual(binding.dataset_id, "Demo")
        self.assertEqual(binding.origin_column, "source")
        self.assertEqual(tuple(c.category for c in plan.checks), ("SCHEMA", "METRIC"))
        self.assertEqual(tuple(c.dataset_refs for c in plan.checks), (("Demo",), ("Demo",)))
        self.assertEqual(plan.checks[1].spec, MetricValidationSpec(
            "demo_n", "demo_b", "demo_share", "FRACTION", "NULL", Decimal("0"), True))
        for name in ("demo_n", "demo_b"):
            self.assertEqual(binding.schema_spec.fields[name].logical_type, "integer")
        self.assertEqual(binding.schema_spec.fields["demo_share"].logical_type, "number")
        self.assertEqual(mapping.domain.unknown_policy, "KEEP_IF_PRESENT")
        self.assertEqual(mapping.domain.overlap_policy, "MAY_OVERLAP")

    def test_u04_original_arguments_reach_published_adapter(self):
        with patch.object(d, "build_demo_inputs", return_value=self.inputs), patch.object(
                q, "build_q01_synthetic_view_model", wraps=q.build_q01_synthetic_view_model) as adapter:
            result = d.run_q01_demo(True)
        self.assertTrue(result.passed)
        adapter.assert_called_once()
        for actual, expected in zip(adapter.call_args.args[:3], self.inputs):
            self.assertIs(actual, expected)
        self.assertIs(adapter.call_args.args[3], True)

    def test_u05_renderable_immutable_presentation(self):
        result = d.run_q01_demo(True)
        self.assertEqual(result.status, "SYNTHETIC_DEMO_ONLY")
        self.assertTrue(result.passed)
        self.assertEqual(result.issue_codes, ())
        self.assertEqual(result.context, ("DEMO_RUN", "DEMO_POP", "DEMO_ALL"))
        self.assertEqual(result.taxonomy_id, "DEMO_TAXONOMY")
        with self.assertRaises(FrozenInstanceError):
            result.rows[0].count = 0

    def test_u06_denominator(self):
        self.assertEqual(d.run_q01_demo(True).population_count, 10)

    def test_u07_stored_percentages(self):
        shares = tuple(row.share_percent for row in d.run_q01_demo(True).rows)
        self.assertEqual(shares, (Fraction(80), Fraction(70), Fraction(10)))
        self.assertTrue(all(type(value) is Fraction for value in shares))

    def test_u08_sum_not_normalized(self):
        result = d.run_q01_demo(True)
        self.assertEqual(sum(row.share_percent for row in result.rows), 160)
        self.assertNotEqual(sum(row.count for row in result.rows), result.population_count)

    def test_u09_unknown_retained(self):
        self.assertEqual(d.run_q01_demo(True).rows[-1].category_id, "DEMO_UNKNOWN")

    def test_u10_no_partition_or_pie_logic(self):
        self.assertEqual(tuple(c.category for c in self.inputs[1].checks), ("SCHEMA", "METRIC"))
        self.assertEqual(tuple(row.count for row in d.run_q01_demo(True).rows), (8, 7, 1))

    def test_u11_failed_q01_result(self):
        bad = q.Q01ConsumerResult("INVALID", False, "Q01_SYNTHETIC_LOGICAL", None, None,
                                  None, (), (), (q.Q01Issue("orchestration", "ORCHESTRATION_FAILED", (), None),))
        self.rejected(d.prepare_q01_presentation(bad), "ORCHESTRATION_FAILED")

    def test_u12_malformed_result_type(self):
        for bad in (None, {}, True, "SENSITIVE_RESULT", object()):
            self.rejected(d.prepare_q01_presentation(bad), "INVALID_Q01_RESULT")

    def test_u13_forged_pass_or_status(self):
        for changes in ({"passed": 1}, {"passed": False}, {"status": "PRODUCTION"},
                        {"logical_scope": "OTHER"}, {"taxonomy_id": "OFFICIAL"},
                        {"context": q.Q01Context("OTHER", "DEMO_POP", "DEMO_ALL")}):
            self.rejected(d.prepare_q01_presentation(replace(self.good, **changes)))

    def test_u14_malformed_nested_rows_and_collections(self):
        for rows in ([self.good.rows[0]], ({},), (None,), (object(),)):
            self.rejected(d.prepare_q01_presentation(replace(self.good, rows=rows)))
        for changes in ({"issues": []}, {"completed_check_ids": ["Schema", "Metric"]}):
            self.rejected(d.prepare_q01_presentation(replace(self.good, **changes)))

    def test_u15_required_check_inventory(self):
        for checks in (("Schema",), ("Metric", "Schema"), ("Schema", "Metric", "Extra")):
            self.rejected(d.prepare_q01_presentation(replace(self.good, completed_check_ids=checks)))

    def test_u16_pass_with_issues(self):
        self.rejected(d.prepare_q01_presentation(replace(self.good, issues=(q.Q01Issue(
            "internal", "ADAPTER_EXCEPTION", (), None),))))

    def test_u17_invalid_denominator(self):
        for population in (None, True, 10.0, -1, 0, 11):
            self.rejected(d.prepare_q01_presentation(replace(self.good, population_count=population)))

    def test_u18_unsupported_and_duplicate_category(self):
        for rows in ((replace(self.good.rows[0], category_id="SENSITIVE_ID"),),
                     (self.good.rows[0], self.good.rows[0])):
            self.rejected(d.prepare_q01_presentation(replace(self.good, rows=rows)))

    def test_u19_failure_diagnostics_allowlist(self):
        bad = q.Q01ConsumerResult("INVALID", False, "Q01_SYNTHETIC_LOGICAL", None, None,
                                  None, (), (), (q.Q01Issue("internal", "SENSITIVE_CODE", (), None),))
        self.rejected(d.prepare_q01_presentation(bad), "INVALID_Q01_RESULT")

    def test_u20_no_dataframe_or_source_payload_retained(self):
        def walk(value):
            self.assertNotIsInstance(value, (pd.DataFrame, pd.Series, q.Q01ConsumerResult))
            if type(value) is dict:
                for item in value.values():
                    walk(item)
            elif type(value) in (tuple, list):
                for item in value:
                    walk(item)
            else:
                self.assertIn(type(value), (str, int, bool, Fraction))
        walk(asdict(d.run_q01_demo(True)))

    def test_u21_no_borrowed_configuration_in_output(self):
        with patch.object(d, "build_demo_inputs", return_value=self.inputs):
            presentation = d.run_q01_demo(True)
        self.inputs[0][0].schema_spec.fields.clear()
        self.inputs[0][0].dataframe.iloc[0, 0] = "SENSITIVE_MUTATION"
        self.assertEqual(presentation.rows[0].category_id, "DEMO_A")
        self.assertEqual(presentation.rows[0].share_percent, 80)

    def test_u22_fresh_inputs_every_call(self):
        calls = []
        original = q.build_q01_synthetic_view_model
        def spy(*args):
            calls.append(args)
            return original(*args)
        with patch.object(q, "build_q01_synthetic_view_model", side_effect=spy):
            self.assertEqual(d.run_q01_demo(True), d.run_q01_demo(True))
        for first, second in zip(calls[0][:3], calls[1][:3]):
            self.assertIsNot(first, second)
        self.assertIsNot(calls[0][0][0].dataframe, calls[1][0][0].dataframe)
        self.assertIsNot(calls[0][0][0].schema_spec.fields, calls[1][0][0].schema_spec.fields)

    def test_u23_complete_decimal_context_preserved(self):
        def state():
            c = getcontext()
            return (c.prec, c.rounding, c.Emin, c.Emax, c.capitals, c.clamp, dict(c.flags), dict(c.traps))
        with localcontext() as context:
            context.prec, context.rounding = 9, ROUND_UP
            context.flags[Inexact] = True
            before = state()
            self.assertTrue(d.run_q01_demo(True).passed)
            self.assertEqual(state(), before)
            def broken(*args):
                getcontext().prec = 2
                raise ValueError("SENSITIVE_DECIMAL")
            with patch.object(q, "build_q01_synthetic_view_model", side_effect=broken):
                self.rejected(d.run_q01_demo(True))
            self.assertEqual(state(), before)

    def test_u24_adapter_exception_safe_failure(self):
        with patch.object(q, "build_q01_synthetic_view_model", side_effect=RuntimeError("SENSITIVE_EXCEPTION")):
            self.rejected(d.run_q01_demo(True), "DEMO_EXECUTION_EXCEPTION")

    def test_u25_preserve_stored_fraction_not_recalculate(self):
        stored = Fraction(800001, 1000000)
        good = replace(self.good, rows=(replace(self.good.rows[0], share_fraction=stored),))
        result = d.prepare_q01_presentation(good)
        self.assertTrue(result.passed)
        self.assertEqual(result.rows[0].share_percent, stored * 100)
        self.assertNotEqual(result.rows[0].share_percent, Fraction(100 * 8, 10))

    def test_u26_off_and_invalid_permission_do_not_build(self):
        with patch.object(d, "build_demo_inputs") as fixture, patch.object(q, "build_q01_synthetic_view_model") as adapter:
            self.rejected(d.run_q01_demo(False), "DEMO_DISABLED")
            for permission in (1, "true", None, pd.NA):
                self.rejected(d.run_q01_demo(permission), "INVALID_DEMO_PERMISSION")
        fixture.assert_not_called()
        adapter.assert_not_called()

    def test_u27_hostile_types_no_hooks(self):
        calls = []
        class Trap(str):
            def forbidden(self, *args):
                calls.append("hook")
                raise RuntimeError("SENSITIVE_HOOK")
            __eq__ = __hash__ = __repr__ = __str__ = __bool__ = forbidden
        for bad in (Trap("result"), replace(self.good, status=Trap("SYNTHETIC_DEMO_ONLY")),
                    replace(self.good, passed=Trap("true")),
                    replace(self.good, rows=(replace(self.good.rows[0], category_id=Trap("DEMO_A")),)),
                    replace(self.good, context=q.Q01Context(Trap("DEMO_RUN"), "DEMO_POP", "DEMO_ALL"))):
            self.rejected(d.prepare_q01_presentation(bad))
        self.assertEqual(calls, [])

    def test_u28_empty_and_zero_denominator(self):
        self.rejected(d.prepare_q01_presentation(replace(self.good, rows=())))
        self.rejected(d.prepare_q01_presentation(replace(self.good, population_count=0)))

    def test_invalid_rows_never_return_partial_findings(self):
        for changes in ({"category_count": True}, {"category_count": -1}, {"category_count": 11},
                        {"share_fraction": 0.8}, {"share_fraction": Fraction(-1)},
                        {"share_fraction": Fraction(2)}, {"is_unknown": 1}, {"is_unknown": True}):
            bad_row = replace(self.good.rows[0], **changes)
            self.rejected(d.prepare_q01_presentation(replace(self.good, rows=(self.good.rows[1], bad_row))))

    def test_fixture_failures_use_actual_published_pipeline(self):
        cases = ("missing", "schema", "metric", "required", "partition", "origin", "empty")
        for case in cases:
            datasets, plan, mapping = d.build_demo_inputs()
            if case == "missing":
                datasets = ()
            elif case == "schema":
                datasets[0].dataframe.at[0, "demo_n"] = -1
            elif case == "metric":
                datasets[0].dataframe.at[0, "demo_share"] = Decimal("0.2")
            elif case == "required":
                plan = replace(plan, checks=plan.checks[:1])
            elif case == "partition":
                plan = replace(plan, checks=plan.checks + (ValidationCheck("Part", "PARTITION_SUMMARY", ("Demo",), None, True),))
            elif case == "origin":
                datasets = (replace(datasets[0], explicit_origin="REAL"),)
            else:
                datasets = (replace(datasets[0], dataframe=datasets[0].dataframe.iloc[:0].copy()),)
            with self.subTest(case=case), patch.object(d, "build_demo_inputs", return_value=(datasets, plan, mapping)):
                self.rejected(d.run_q01_demo(True))

    def test_gate_still_closed(self):
        self.assertEqual(real_artifact_status(exists=True), "BLOCKED")
        self.assertFalse(hasattr(d.run_q01_demo(True), "production_eligible"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
