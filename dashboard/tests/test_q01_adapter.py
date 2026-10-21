"""Artificial in-memory Q01 roles, not accepted taxonomy or business findings."""

from dataclasses import FrozenInstanceError, asdict, replace
from decimal import Decimal, Inexact, Rounded, ROUND_UP, getcontext, localcontext
from fractions import Fraction
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components import q01_adapter as q
from components import validation_orchestrator as o
from components.contract_validator import FieldSpec, ValidationSpec
from components.metric_validator import MetricValidationSpec
from components.artifact_gate import STATUS_SAMPLE, real_artifact_status


class Q01AdapterTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "demo_cat": ["DEMO_B", "DEMO_UNKNOWN"], "demo_n": [2, 1], "demo_b": [10, 10],
            "demo_share": [Decimal("0.2"), Decimal("0.1")],
            "demo_run": ["DEMO_RUN"] * 2, "demo_pop": ["DEMO_POP"] * 2,
            "demo_filter": ["DEMO_ALL"] * 2, "source": [STATUS_SAMPLE] * 2,
        }, index=[7, 3], dtype=object)
        rules = {name: FieldSpec("integer" if name in ("demo_n", "demo_b") else
                 "number" if name == "demo_share" else "string", name == "demo_share") for name in self.frame.columns}
        self.schema = ValidationSpec(rules, tuple(rules), (), ("demo_n", "demo_b"), True, False)
        self.binding = o.DatasetBinding("Demo", self.frame, self.schema, STATUS_SAMPLE, "source")
        self.metric = MetricValidationSpec("demo_n", "demo_b", "demo_share", "FRACTION", "NULL", Decimal("0"), True)
        self.plan = o.ValidationPlan((o.ValidationCheck("Schema", "SCHEMA", ("Demo",), self.schema, True),
                                      o.ValidationCheck("Metric", "METRIC", ("Demo",), self.metric, True)))
        self.mapping = q.Q01Mapping("Demo", "demo_cat", "demo_n", "demo_b", "demo_share",
            ("demo_run", "demo_pop", "demo_filter"), q.Q01Context("DEMO_RUN", "DEMO_POP", "DEMO_ALL"),
            q.SyntheticCategoryDomain("DEMO_TAXONOMY", ("DEMO_A", "DEMO_B", "DEMO_UNKNOWN"),
                                      "DEMO_UNKNOWN", "KEEP_IF_PRESENT", "MAY_OVERLAP"), "Schema", "Metric")

    def build(self, **overrides):
        args = dict(datasets=(self.binding,), validation_plan=self.plan, q01_mapping=self.mapping, demo_enabled=True)
        args.update(overrides)
        return q.build_q01_synthetic_view_model(**args)

    def rejected(self, result, code, status="INVALID"):
        self.assertFalse(result.passed)
        self.assertEqual(result.status, status)
        self.assertEqual(result.rows, ())
        self.assertIsNone(result.context)
        self.assertIsNone(result.population_count)
        self.assertEqual(result.completed_check_ids, ())
        self.assertTrue(any(i.code == code and type(i.stage) is str for i in result.issues), result)
        self.assertNotIn("SENSITIVE", repr(result))

    def metric_plan(self, spec):
        return replace(self.plan, checks=(self.plan.checks[0], replace(self.plan.checks[1], spec=spec)))

    def test_t01_valid_projection(self):
        result = self.build()
        self.assertTrue(result.passed, result)
        self.assertEqual(result.status, "SYNTHETIC_DEMO_ONLY")
        self.assertEqual(result.logical_scope, "Q01_SYNTHETIC_LOGICAL")
        self.assertEqual(result.context, self.mapping.context)
        self.assertEqual(result.population_count, 10)
        self.assertEqual(result.completed_check_ids, ("Schema", "Metric"))
        self.assertEqual(result.rows, (q.Q01CategoryRow("DEMO_B", 2, Fraction(1, 5), False),
                                       q.Q01CategoryRow("DEMO_UNKNOWN", 1, Fraction(1, 10), True)))

    def test_t02_demo_disabled(self):
        with patch.object(q, "run_synthetic_validation_plan") as orchestrator:
            result = self.build(demo_enabled=False)
        orchestrator.assert_not_called()
        self.rejected(result, "DEMO_DISABLED", "BLOCKED")

    def test_t03_real_origin(self):
        self.rejected(self.build(datasets=(replace(self.binding, explicit_origin="REAL"),)), "ORIGIN_BLOCKED", "BLOCKED")

    def test_t04_forged_markers_cannot_authorize_real(self):
        self.assertTrue(self.frame["source"].eq(STATUS_SAMPLE).all())
        with patch.object(q, "run_synthetic_validation_plan") as orchestrator:
            result = self.build(datasets=(replace(self.binding, explicit_origin="REAL"),))
        orchestrator.assert_not_called()
        self.rejected(result, "ORIGIN_BLOCKED", "BLOCKED")

    def test_t05_missing_schema(self):
        self.rejected(self.build(validation_plan=replace(self.plan, checks=self.plan.checks[1:])), "REQUIRED_SCHEMA_CHECK_MISSING")

    def test_t06_missing_metric(self):
        self.rejected(self.build(validation_plan=replace(self.plan, checks=self.plan.checks[:1])), "REQUIRED_METRIC_CHECK_MISSING")

    def test_t07_schema_only_cannot_succeed(self):
        schema_only = replace(self.plan, checks=self.plan.checks[:1])
        self.assertEqual(o.run_synthetic_validation_plan((self.binding,), schema_only, True).overall_status, "SCHEMA_ONLY_VALIDATION")
        self.rejected(self.build(validation_plan=schema_only), "REQUIRED_METRIC_CHECK_MISSING")

    def test_t08_metric_failure(self):
        self.frame.at[7, "demo_share"] = Decimal("0.8")
        evidence = o.run_synthetic_validation_plan((self.binding,), self.plan, True)
        self.assertEqual(evidence.check_results[-1].status, "FAIL")
        self.rejected(self.build(), "ORCHESTRATION_FAILED")

    def test_t09_blocked_metric(self):
        self.frame.at[7, "demo_n"] = -1
        evidence = o.run_synthetic_validation_plan((self.binding,), self.plan, True)
        self.assertEqual(evidence.blocked_check_ids, ("Metric",))
        self.assertNotIn("Metric", evidence.executed_check_ids)
        self.rejected(self.build(), "ORCHESTRATION_FAILED")

    def test_t10_malformed_evidence(self):
        good = o.run_synthetic_validation_plan((self.binding,), self.plan, True)
        cases = (None, {}, replace(good, passed=1), replace(good, schema_scope_completed=False),
            replace(good, overall_status="SCHEMA_ONLY_VALIDATION"), replace(good, check_results=()),
            replace(good, executed_check_ids=("Schema",)), replace(good, successful_check_ids=[]),
            replace(good, check_results=(good.check_results[0], replace(good.check_results[1], executed=False))),
            replace(good, check_results=(good.check_results[0], replace(good.check_results[1], status="BLOCKED"))),
            replace(good, check_results=(good.check_results[0], replace(good.check_results[1], counts=(("row_count", True),)))),
            replace(good, category_statuses=(("SCHEMA", "PASS"), ("METRIC", "NOT_REQUESTED"))))
        for evidence in cases:
            with patch.object(q, "run_synthetic_validation_plan", return_value=evidence):
                self.rejected(self.build(), "INVALID_ORCHESTRATION_RESULT")

    def test_t11_wrong_dataset_or_columns(self):
        other = replace(self.binding, dataset_id="Other", dataframe=self.frame.copy(deep=True))
        plan = replace(self.plan, checks=(self.plan.checks[0],
            o.ValidationCheck("OtherSchema", "SCHEMA", ("Other",), self.schema, True),
            replace(self.plan.checks[1], dataset_refs=("Other",))))
        datasets = (self.binding, other)
        self.assertTrue(o.run_synthetic_validation_plan(datasets, plan, True).passed)
        self.rejected(self.build(datasets=datasets, validation_plan=plan), "CHECK_COVERAGE_MISMATCH")
        for spec in (replace(self.metric, numerator_column="other_n"), replace(self.metric, denominator_column="other_b"),
                     replace(self.metric, rate_column="other_rate")):
            with patch.object(q, "run_synthetic_validation_plan") as orchestrator:
                result = self.build(validation_plan=self.metric_plan(spec))
            orchestrator.assert_not_called()
            self.rejected(result, "METRIC_COVERAGE_MISMATCH")

    def test_t12_valid_ratio_is_fraction(self):
        row = self.build().rows[0]
        self.assertEqual(row.share_fraction, Fraction(1, 5))
        self.assertIs(type(row.share_fraction), Fraction)

    def test_t13_wrong_fraction(self):
        self.frame.at[7, "demo_share"] = 20
        self.rejected(self.build(), "ORCHESTRATION_FAILED")

    def test_t14_inconsistent_b(self):
        self.frame.at[3, "demo_b"] = 20
        self.frame.at[3, "demo_share"] = Decimal("0.05")
        self.rejected(self.build(), "INCONSISTENT_DENOMINATOR")

    def test_t15_missing_b(self):
        for value in (None, pd.NA, float("nan")):
            self.frame.at[7, "demo_b"] = value
            self.rejected(self.build(), "ORCHESTRATION_FAILED")
        frame = self.frame.drop(columns="demo_b")
        self.rejected(self.build(datasets=(replace(self.binding, dataframe=frame),)), "MISSING_LOGICAL_COLUMNS")

    def test_t16_negative_count(self):
        self.frame.at[7, "demo_n"] = -1
        self.rejected(self.build(), "ORCHESTRATION_FAILED")

    def test_t17_fractional_or_boolean_count(self):
        for value, code in ((Decimal("1.5"), "ORCHESTRATION_FAILED"), (True, "UNSUPPORTED_NUMBER")):
            self.frame.at[7, "demo_n"] = value
            self.rejected(self.build(), code)

    def test_t18_large_exact_counts(self):
        huge = 10 ** 1000
        self.frame["demo_n"] = pd.Series([huge, huge], index=self.frame.index, dtype=object)
        self.frame["demo_b"] = pd.Series([2 * huge, 2 * huge], index=self.frame.index, dtype=object)
        self.frame["demo_share"] = Decimal("0.5")
        result = self.build()
        self.assertTrue(result.passed, result)
        self.assertEqual(result.population_count, 2 * huge)
        self.assertEqual(result.rows[0].category_count, huge)
        self.assertEqual(result.rows[0].share_fraction, Fraction(1, 2))

    def test_t19_zero_population_no_finding(self):
        self.frame["demo_n"] = 0
        self.frame["demo_b"] = 0
        self.frame["demo_share"] = None
        self.rejected(self.build(), "UNDEFINED_DENOMINATOR", "BLOCKED")
        self.rejected(self.build(validation_plan=self.metric_plan(replace(self.metric, zero_denominator_policy="REJECT"))), "ORCHESTRATION_FAILED")

    def test_t20_unknown_retained(self):
        result = self.build()
        self.assertTrue(result.passed)
        self.assertEqual(tuple(r.category_id for r in result.rows if r.is_unknown), ("DEMO_UNKNOWN",))

    def test_t21_unknown_not_fabricated(self):
        binding = replace(self.binding, dataframe=self.frame.iloc[:1].copy())
        result = self.build(datasets=(binding,))
        self.assertTrue(result.passed)
        self.assertEqual(len(result.rows), 1)
        self.assertFalse(result.rows[0].is_unknown)

    def test_t22_duplicate_category(self):
        self.frame.at[3, "demo_cat"] = "DEMO_B"
        self.rejected(self.build(), "DUPLICATE_CATEGORY")

    def test_t23_string_subclass_rejected(self):
        class Alias(str):
            pass
        self.frame.at[7, "demo_cat"] = Alias("DEMO_B")
        self.rejected(self.build(), "UNSUPPORTED_IDENTITY")

    def test_t24_hostile_hooks_not_executed(self):
        calls = []
        class Trap(str):
            def forbidden(self, *args):
                calls.append("hook")
                raise RuntimeError("SENSITIVE_HOOK")
            __str__ = __repr__ = __hash__ = __eq__ = forbidden
        marker = Trap("DEMO_B")
        self.frame.at[7, "demo_cat"] = marker
        self.assertIs(self.frame.at[7, "demo_cat"], marker)
        with patch.object(q, "run_synthetic_validation_plan") as orchestrator:
            result = self.build()
        orchestrator.assert_not_called()
        self.rejected(result, "UNSUPPORTED_IDENTITY")
        self.assertEqual(calls, [])

    def test_t25_multiple_contexts(self):
        for column in self.mapping.context_columns:
            before = self.frame.at[7, column]
            self.frame.at[7, column] = "DEMO_OTHER"
            self.rejected(self.build(), "CONTEXT_MISMATCH")
            self.frame.at[7, column] = before

    def test_t26_overlap_no_partition_assumption(self):
        self.frame["demo_n"] = [8, 7]
        self.frame["demo_share"] = [Decimal("0.8"), Decimal("0.7")]
        with patch.object(o, "validate_partition_summary_contract") as partition:
            result = self.build()
        partition.assert_not_called()
        self.assertTrue(result.passed, result)
        self.assertGreater(sum(r.share_fraction for r in result.rows), 1)
        self.assertEqual(result.population_count, 10)

    def test_t27_count_exceeds_b(self):
        self.frame.at[7, "demo_n"] = 11
        self.frame.at[7, "demo_share"] = Decimal("1.1")
        self.rejected(self.build(), "ORCHESTRATION_FAILED")

    def test_t28_empty(self):
        self.rejected(self.build(datasets=(replace(self.binding, dataframe=self.frame.iloc[:0].copy()),)), "ORCHESTRATION_FAILED", "BLOCKED")

    def test_t29_inputs_preserved(self):
        for bad in (False, True):
            if bad:
                self.frame.at[7, "demo_share"] = Decimal("0.9")
            before = self.frame.copy(deep=True)
            identities = tuple(tuple(self.frame.iat[i, j] for j in range(len(self.frame.columns))) for i in range(len(self.frame)))
            result = self.build()
            self.assertIs(result.passed, not bad)
            assert_frame_equal(self.frame, before, check_exact=True)
            for i, row in enumerate(identities):
                for j, value in enumerate(row):
                    self.assertIs(self.frame.iat[i, j], value)

    @staticmethod
    def context_state():
        c = getcontext()
        return (c.prec, c.rounding, c.Emin, c.Emax, c.capitals, c.clamp, dict(c.traps), dict(c.flags))

    def test_t30_decimal_context_preserved(self):
        ambient = self.context_state()
        with localcontext() as context:
            context.prec = 31
            context.flags[Rounded] = True
            context.traps[Inexact] = True
            before = self.context_state()
            self.assertTrue(self.build().passed)
            self.assertEqual(self.context_state(), before)
            def broken(*args):
                c = getcontext()
                c.prec, c.rounding, c.Emin, c.Emax = 7, ROUND_UP, -100, 100
                c.capitals, c.clamp = 0, 1
                c.clear_flags()
                c.traps[Inexact] = False
                raise RuntimeError("SENSITIVE_ERROR")
            with patch.object(q, "run_synthetic_validation_plan", side_effect=broken):
                self.rejected(self.build(), "ORCHESTRATOR_EXCEPTION")
            self.assertEqual(self.context_state(), before)
        self.assertEqual(self.context_state(), ambient)

    def test_t31_no_raw_payload(self):
        self.frame["description"] = "SENSITIVE_DESCRIPTION"
        spec = replace(self.schema, allow_extra_columns=True)
        binding = replace(self.binding, schema_spec=spec)
        plan = replace(self.plan, checks=(replace(self.plan.checks[0], spec=spec), self.plan.checks[1]))
        result = self.build(datasets=(binding,), validation_plan=plan)
        self.assertTrue(result.passed, result)
        def walk(value):
            self.assertNotIsInstance(value, (pd.DataFrame, pd.Series))
            if type(value) is dict:
                for v in value.values():
                    walk(v)
            elif type(value) in (tuple, list):
                for v in value:
                    walk(v)
        walk(asdict(result))
        self.assertNotIn("SENSITIVE", repr(result))
        self.assertNotIn("description", repr(result))

    def test_t32_safe_exception_diagnostics(self):
        with patch.object(o, "validate_metric_contract", side_effect=RuntimeError("SENSITIVE_DESCRIPTION")):
            self.rejected(self.build(), "ORCHESTRATION_FAILED")

    def test_t33_repeatable(self):
        self.assertEqual(self.build(), self.build())

    def test_t34_no_production_authorization(self):
        result = self.build()
        self.assertEqual(real_artifact_status(exists=True), "BLOCKED")
        self.assertFalse(hasattr(result, "production_eligible"))
        self.assertEqual(result.status, "SYNTHETIC_DEMO_ONLY")

    def test_t35_frozen_nested_result(self):
        result = self.build()
        for target, field, value in ((result, "status", "PRODUCTION"), (result.rows[0], "category_count", 0),
                                     (result.context, "run_id", "OTHER")):
            with self.assertRaises(FrozenInstanceError):
                setattr(target, field, value)
        self.assertIs(type(result.rows), tuple)

    def test_t36_unrelated_passing_metric_does_not_cover_q01(self):
        plan = replace(self.plan, checks=(self.plan.checks[0], replace(self.plan.checks[1], check_id="Unrelated")))
        self.assertTrue(o.run_synthetic_validation_plan((self.binding,), plan, True).passed)
        self.rejected(self.build(validation_plan=plan), "REQUIRED_METRIC_CHECK_MISSING")

    def test_t37_explicit_domain(self):
        self.frame.at[7, "demo_cat"] = "UNDECLARED"
        self.rejected(self.build(), "UNDECLARED_CATEGORY")
        domain = replace(self.mapping.domain, category_ids=self.mapping.domain.category_ids + ("UNDECLARED",))
        self.assertTrue(self.build(q01_mapping=replace(self.mapping, domain=domain)).passed)

    def test_t38_no_alias_inference(self):
        for mapping in (None, {}, replace(self.mapping, count_column=None), replace(self.mapping, context_columns=()),
                        replace(self.mapping, count_column="demo_b")):
            self.rejected(self.build(q01_mapping=mapping), "INVALID_MAPPING")
        self.rejected(self.build(q01_mapping=replace(self.mapping, count_column="unknown_alias")), "METRIC_COVERAGE_MISMATCH")

    def test_t39_invalid_demo_and_missing_source(self):
        for demo in (1, "true", None, pd.NA):
            self.rejected(self.build(demo_enabled=demo), "INVALID_DEMO_PERMISSION")
        self.rejected(self.build(datasets=()), "MISSING_SOURCE")
        self.rejected(self.build(datasets=(replace(self.binding, dataframe=None),)), "MISSING_OR_INVALID_SOURCE")

    def test_t40_schema_roles_must_be_validated(self):
        spec = replace(self.schema, count_fields=())
        plan = replace(self.plan, checks=(replace(self.plan.checks[0], spec=spec), self.plan.checks[1]))
        self.rejected(self.build(datasets=(replace(self.binding, schema_spec=spec),), validation_plan=plan), "SCHEMA_COVERAGE_MISMATCH")

    def test_t41_subset_and_unit_required(self):
        for spec in (replace(self.metric, subset_of_population=False), replace(self.metric, rate_unit="PERCENT")):
            self.rejected(self.build(validation_plan=self.metric_plan(spec)), "METRIC_COVERAGE_MISMATCH")

    def test_t42_original_arguments_to_orchestrator(self):
        with patch.object(q, "run_synthetic_validation_plan", wraps=o.run_synthetic_validation_plan) as orchestrator:
            result = self.build()
        self.assertTrue(result.passed)
        orchestrator.assert_called_once()
        self.assertIs(orchestrator.call_args.args[0][0], self.binding)
        self.assertIs(orchestrator.call_args.args[1], self.plan)

    def test_t43_explicit_aliases_not_fixed_physical_names(self):
        aliases = {name: "renamed_" + name for name in self.frame.columns}
        frame = self.frame.rename(columns=aliases)
        spec = replace(self.schema, fields={aliases[n]: rule for n, rule in self.schema.fields.items()},
            required_fields=tuple(aliases[n] for n in self.schema.required_fields),
            count_fields=tuple(aliases[n] for n in self.schema.count_fields))
        binding = replace(self.binding, dataframe=frame, schema_spec=spec, origin_column=aliases["source"])
        metric = replace(self.metric, numerator_column=aliases["demo_n"], denominator_column=aliases["demo_b"],
                         rate_column=aliases["demo_share"])
        plan = replace(self.plan, checks=(replace(self.plan.checks[0], spec=spec), replace(self.plan.checks[1], spec=metric)))
        mapping = replace(self.mapping, category_column=aliases["demo_cat"], count_column=aliases["demo_n"],
            population_column=aliases["demo_b"], fraction_column=aliases["demo_share"],
            context_columns=tuple(aliases[n] for n in self.mapping.context_columns))
        self.assertEqual(self.build(datasets=(binding,), validation_plan=plan, q01_mapping=mapping), self.build())

    def test_t44_mapping_domain_guards_without_hooks(self):
        calls = []
        class Trap(str):
            def forbidden(self, *args):
                calls.append("hook")
                raise RuntimeError("SENSITIVE_DOMAIN")
            __str__ = __repr__ = __hash__ = __eq__ = forbidden
        for domain in (replace(self.mapping.domain, category_ids=(Trap("DEMO_B"),)),
                       replace(self.mapping.domain, unknown_id=None),
                       replace(self.mapping.domain, category_ids=("DEMO_B", "DEMO_B")),
                       replace(self.mapping.domain, unknown_policy="DROP")):
            self.rejected(self.build(q01_mapping=replace(self.mapping, domain=domain)), "INVALID_MAPPING")
        self.assertEqual(calls, [])

    def test_t45_null_missing_and_unsafe_category_ids(self):
        for value in (None, pd.NA, ["DEMO_B"], 1):
            # Scalar assignment into an object column preserves the unsupported value.
            self.frame.at[7, "demo_cat"] = value
            self.rejected(self.build(), "UNSUPPORTED_IDENTITY")
        self.frame.at[7, "demo_cat"] = "unsafe/free text"
        self.rejected(self.build(), "UNDECLARED_CATEGORY")

    def test_t46_required_check_not_executed_or_wrong_category(self):
        good = o.run_synthetic_validation_plan((self.binding,), self.plan, True)
        for evidence in (replace(good, blocked_check_ids=("Metric",)),
                         replace(good, safe_issues=(o.SafeIssue("Metric", "SENSITIVE_PAYLOAD"),)),
                         replace(good, check_results=(good.check_results[0],
                             replace(good.check_results[1], category="SCHEMA")))):
            with patch.object(q, "run_synthetic_validation_plan", return_value=evidence):
                self.rejected(self.build(), "INVALID_ORCHESTRATION_RESULT")

    def test_t47_declared_tolerance_not_replaced(self):
        self.frame.at[7, "demo_share"] = Decimal("0.2001")
        self.rejected(self.build(), "ORCHESTRATION_FAILED")
        result = self.build(validation_plan=self.metric_plan(replace(self.metric, tolerance=Decimal("0.001"))))
        self.assertTrue(result.passed, result)
        self.assertEqual(result.rows[0].share_fraction, Fraction(2001, 10000))

    def test_t48_all_required_checks_must_pass(self):
        # The Q01-required metric passes, but another explicitly required check fails.
        plan = replace(self.plan, checks=self.plan.checks + (
            o.ValidationCheck("Extra", "METRIC", ("Demo",), replace(self.metric, numerator_column="absent"), True),))
        self.rejected(self.build(validation_plan=plan), "ORCHESTRATION_FAILED")

    def test_t49_no_unapproved_partition_contract_execution(self):
        plan = replace(self.plan, checks=self.plan.checks + (
            o.ValidationCheck("Partition", "PARTITION_SUMMARY", ("Demo", "Other"), None, True),))
        with patch.object(q, "run_synthetic_validation_plan") as orchestrator:
            result = self.build(validation_plan=plan)
        orchestrator.assert_not_called()
        self.rejected(result, "PARTITION_CONTRACT_OUT_OF_SCOPE")

    def test_t50_schema_exception_preserves_input_context_and_diagnostics(self):
        from components import consumer_adapter
        before = self.frame.copy(deep=True)
        identities = tuple(tuple(self.frame.iat[i, j] for j in range(len(self.frame.columns))) for i in range(len(self.frame)))
        state = self.context_state()
        def broken(*args):
            getcontext().prec = 7
            getcontext().flags[Inexact] = True
            raise RuntimeError("SENSITIVE_SCHEMA_ERROR")
        with patch.object(consumer_adapter, "validate_dataset_contract", side_effect=broken) as validator:
            self.rejected(self.build(), "ORCHESTRATION_FAILED")
        validator.assert_called_once()
        self.assertIs(validator.call_args.args[0], self.frame)
        self.assertEqual(self.context_state(), state)
        assert_frame_equal(self.frame, before, check_exact=True)
        for i, row in enumerate(identities):
            for j, value in enumerate(row):
                self.assertIs(self.frame.iat[i, j], value)

    def _fix_expanded(self, same=True, metric=False, other_frame=None):
        from components.cross_table_validator import CrossTableValidationSpec
        other = replace(self.binding, dataset_id="Other",
                        dataframe=self.frame.copy(deep=True) if other_frame is None else other_frame)
        checks = self.plan.checks + (o.ValidationCheck("OtherSchema", "SCHEMA", ("Other",), self.schema, True),)
        if same:
            spec = CrossTableValidationSpec((("demo_cat", "demo_cat"),), (("demo_n", "demo_n"),),
                                            (("demo_run", "demo_run"),), False, True)
            checks += (o.ValidationCheck("Same", "SAME_GRAIN", ("Demo", "Other"), spec, True),)
        if metric:
            checks += (o.ValidationCheck("OtherMetric", "METRIC", ("Other",), self.metric, True),)
        return (self.binding, other), replace(self.plan, checks=checks)

    def _fix_evidence(self, datasets, plan):
        evidence = o.run_synthetic_validation_plan(datasets, plan, True)
        self.assertTrue(evidence.passed, evidence)
        self.assertTrue(all(c.status == "PASS" and c.executed for c in evidence.check_results))
        return evidence

    @staticmethod
    def _fix_corrupt(evidence, check_id, **changes):
        return replace(evidence, check_results=tuple(replace(c, **changes) if c.check_id == check_id else c
                                                     for c in evidence.check_results))

    def _fix_inject(self, datasets, plan, evidence):
        with patch.object(q, "run_synthetic_validation_plan", return_value=evidence) as orchestrator:
            result = self.build(datasets=datasets, validation_plan=plan)
        orchestrator.assert_called_once()
        self.assertIs(orchestrator.call_args.args[0], datasets)
        self.assertIs(orchestrator.call_args.args[1], plan)
        return result

    def _fix_rejected(self, datasets, plan, evidence):
        result = self._fix_inject(datasets, plan, evidence)
        self.rejected(result, "INVALID_ORCHESTRATION_RESULT")
        self.assertEqual(result.issues, (q.Q01Issue("orchestration", "INVALID_ORCHESTRATION_RESULT", (), None),))
        self.assertIsNone(result.taxonomy_id)
        return result

    def test_f01_valid_expanded_schema_and_same_grain(self):
        datasets, plan = self._fix_expanded()
        with patch.object(q, "run_synthetic_validation_plan", wraps=o.run_synthetic_validation_plan) as orchestrator:
            result = self.build(datasets=datasets, validation_plan=plan)
        orchestrator.assert_called_once()
        self.assertTrue(result.passed, result)
        self.assertEqual(result, self.build())
        self.assertEqual(result.population_count, 10)
        self.assertEqual(result.rows[0].share_fraction, Fraction(1, 5))

    def test_f02_other_schema_wrong_row_count(self):
        datasets, plan = self._fix_expanded()
        evidence = self._fix_evidence(datasets, plan)
        self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "OtherSchema", counts=(("row_count", 999),)))

    def test_f03_same_grain_wrong_rows_missing_counters(self):
        datasets, plan = self._fix_expanded()
        evidence = self._fix_evidence(datasets, plan)
        self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "Same", counts=(("left_checked_rows", 999),)))

    def test_f04_exact_int_counter_types(self):
        import numpy as np
        datasets, plan = self._fix_expanded()
        evidence = self._fix_evidence(datasets, plan)
        for value in (True, np.int64(2), 2.0, Decimal(2), "2", None, -1):
            self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "OtherSchema", counts=(("row_count", value),)))

    def test_f05_missing_mandatory_counters(self):
        datasets, plan = self._fix_expanded(metric=True)
        evidence = self._fix_evidence(datasets, plan)
        for check_id in ("OtherSchema", "OtherMetric", "Same"):
            self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, check_id, counts=()))
        same = next(c for c in evidence.check_results if c.check_id == "Same")
        for index in range(len(same.counts)):
            self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "Same", counts=same.counts[:index] + same.counts[index + 1:]))

    def test_f06_duplicate_unexpected_and_malformed_counters(self):
        datasets, plan = self._fix_expanded()
        evidence = self._fix_evidence(datasets, plan)
        for counts in ((("row_count", 2), ("row_count", 2)), (("wrong_counter", 2),),
                       (("row_count", 2, 3),), (["row_count", 2],), {"row_count": 2}):
            self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "OtherSchema", counts=counts))
        same = next(c for c in evidence.check_results if c.check_id == "Same")
        self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "Same", counts=same.counts + same.counts[:1]))

    def test_f07_execution_success_inventory_consistency(self):
        datasets, plan = self._fix_expanded()
        evidence = self._fix_evidence(datasets, plan)
        for bad in (replace(evidence, executed_check_ids=("Schema", "Metric")),
                    replace(evidence, successful_check_ids=("Schema", "Metric")),
                    replace(evidence, blocked_check_ids=("Same",)),
                    self._fix_corrupt(evidence, "Same", executed=False)):
            self._fix_rejected(datasets, plan, bad)

    def test_f08_extra_schema_metric_different_dataset_length(self):
        other = pd.concat([self.frame, self.frame.iloc[:1]], ignore_index=True)
        datasets, plan = self._fix_expanded(same=False, metric=True, other_frame=other)
        evidence = self._fix_evidence(datasets, plan)
        self.assertEqual(next(c.counts for c in evidence.check_results if c.check_id == "OtherSchema"), (("row_count", 3),))
        self.assertEqual(next(c.counts for c in evidence.check_results if c.check_id == "OtherMetric"), (("row_count", 3),))
        self.assertEqual(self.build(datasets=datasets, validation_plan=plan), self.build())
        for check_id in ("OtherSchema", "OtherMetric"):
            self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, check_id, counts=(("row_count", 2),)))

    def test_f09_original_q01_coverage_still_required(self):
        datasets, plan = self._fix_expanded()
        self.assertTrue(self.build(datasets=datasets, validation_plan=plan).passed)
        wrong = replace(plan, checks=tuple(replace(c, dataset_refs=("Other",)) if c.check_id == "Metric" else c for c in plan.checks))
        self.rejected(self.build(datasets=datasets, validation_plan=wrong), "CHECK_COVERAGE_MISMATCH")
        missing = replace(plan, checks=tuple(c for c in plan.checks if c.check_id != "Schema"))
        self.rejected(self.build(datasets=datasets, validation_plan=missing), "REQUIRED_SCHEMA_CHECK_MISSING")

    def test_f10_one_bad_additional_metric_blocks_all_findings(self):
        datasets, plan = self._fix_expanded(metric=True)
        evidence = self._fix_evidence(datasets, plan)
        self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "OtherMetric", counts=(("row_count", 999),)))

    def test_f11_hostile_counter_metadata_no_hooks_or_leakage(self):
        calls = []
        class TrapInt(int):
            def forbidden(self, *args):
                calls.append("hook")
                raise RuntimeError("SENSITIVE_COUNTER_EXCEPTION")
            __int__ = __str__ = __repr__ = __eq__ = __lt__ = __hash__ = forbidden
        class TrapName(str):
            __str__ = __repr__ = __eq__ = __hash__ = TrapInt.forbidden
        datasets, plan = self._fix_expanded()
        evidence = self._fix_evidence(datasets, plan)
        for counts in ((("row_count", TrapInt(2)),), ((TrapName("row_count"), 2),),
                       (("SENSITIVE_COUNTER_NAME", 999),)):
            result = self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "OtherSchema", counts=counts))
            self.assertNotIn("999", repr(result))
        self.assertEqual(calls, [])

    def test_f12_expanded_inputs_preserved_success_and_rejection(self):
        datasets, plan = self._fix_expanded()
        snapshots = tuple((b.dataframe.copy(deep=True), tuple(tuple(b.dataframe.iat[i, j]
                          for j in range(len(b.dataframe.columns))) for i in range(len(b.dataframe)))) for b in datasets)
        evidence = self._fix_evidence(datasets, plan)
        self.assertTrue(self.build(datasets=datasets, validation_plan=plan).passed)
        self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "Same", counts=()))
        for binding, (before, identities) in zip(datasets, snapshots):
            assert_frame_equal(binding.dataframe, before, check_exact=True, check_like=False)
            for i, row in enumerate(identities):
                for j, value in enumerate(row):
                    self.assertIs(binding.dataframe.iat[i, j], value)

    def test_f13_complete_decimal_context_success_and_rejection(self):
        ambient = self.context_state()
        datasets, plan = self._fix_expanded()
        with localcontext() as context:
            context.prec, context.rounding, context.Emin, context.Emax = 31, ROUND_UP, -900, 900
            context.capitals, context.clamp = 0, 1
            context.flags[Rounded] = True
            context.traps[Inexact] = True
            before = self.context_state()
            evidence = self._fix_evidence(datasets, plan)
            self.assertTrue(self.build(datasets=datasets, validation_plan=plan).passed)
            self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "Same", counts=(("left_checked_rows", 999),)))
            self.assertEqual(self.context_state(), before)
        self.assertEqual(self.context_state(), ambient)

    def test_f14_repeatability(self):
        datasets, plan = self._fix_expanded()
        self.assertEqual(self.build(datasets=datasets, validation_plan=plan), self.build(datasets=datasets, validation_plan=plan))
        evidence = self._fix_corrupt(self._fix_evidence(datasets, plan), "OtherSchema", counts=())
        self.assertEqual(self._fix_rejected(datasets, plan, evidence), self._fix_rejected(datasets, plan, evidence))

    def test_f15_no_validator_reexecution_for_evidence_or_production_rights(self):
        from components import consumer_adapter
        datasets, plan = self._fix_expanded()
        evidence = self._fix_evidence(datasets, plan)
        with patch.object(consumer_adapter, "validate_dataset_contract") as schema, \
                patch.object(o, "validate_metric_contract") as metric, \
                patch.object(o, "validate_cross_table_contract") as same:
            result = self._fix_inject(datasets, plan, evidence)
            self.assertTrue(result.passed)
            self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "Same", counts=()))
        for validator in (schema, metric, same):
            validator.assert_not_called()
        self.assertEqual(real_artifact_status(exists=True), "BLOCKED")
        self.assertFalse(hasattr(result, "production_eligible"))

    def test_f16_same_grain_cardinality_invariants(self):
        datasets, plan = self._fix_expanded()
        evidence = self._fix_evidence(datasets, plan)
        original = next(c.counts for c in evidence.check_results if c.check_id == "Same")
        for name, value in (("left_checked_rows", 999), ("right_checked_rows", 0),
                            ("left_key_count", 3), ("right_key_count", 0),
                            ("matched_key_count", 0), ("compared_metric_count", 0),
                            ("compared_metric_count", 3)):
            counts = tuple((n, value if n == name else v) for n, v in original)
            self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "Same", counts=counts))

    def test_f17_multiple_same_grain_metric_counters(self):
        datasets, plan = self._fix_expanded()
        spec = replace(plan.checks[-1].spec, metric_pairs=(("demo_n", "demo_n"), ("demo_b", "demo_b")))
        plan = replace(plan, checks=plan.checks[:-1] + (replace(plan.checks[-1], spec=spec),))
        evidence = self._fix_evidence(datasets, plan)
        same = next(c for c in evidence.check_results if c.check_id == "Same")
        self.assertEqual(dict(same.counts)["compared_metric_count"], 4)
        self.assertTrue(self.build(datasets=datasets, validation_plan=plan).passed)
        counts = tuple((n, 2 if n == "compared_metric_count" else v) for n, v in same.counts)
        self._fix_rejected(datasets, plan, self._fix_corrupt(evidence, "Same", counts=counts))

    def test_f18_same_grain_structural_failure_zero_counters_remains_valid_failure(self):
        datasets, plan = self._fix_expanded()
        spec = replace(plan.checks[-1].spec, metric_pairs=(("absent", "demo_n"),))
        plan = replace(plan, checks=plan.checks[:-1] + (replace(plan.checks[-1], spec=spec),))
        evidence = o.run_synthetic_validation_plan(datasets, plan, True)
        same = next(c for c in evidence.check_results if c.check_id == "Same")
        self.assertEqual(same.status, "FAIL")
        self.assertTrue(all(value == 0 for _, value in same.counts))
        self.rejected(self.build(datasets=datasets, validation_plan=plan), "ORCHESTRATION_FAILED")

    def test_f19_exception_and_guard_failures_with_no_counters(self):
        datasets, plan = self._fix_expanded()
        for return_bad_result in (False, True):
            kwargs = {"return_value": None} if return_bad_result else {"side_effect": RuntimeError("SENSITIVE_SAME_EXCEPTION")}
            with patch.object(o, "validate_cross_table_contract", **kwargs):
                self.rejected(self.build(datasets=datasets, validation_plan=plan), "ORCHESTRATION_FAILED")

    def test_f20_schema_failure_blocks_expanded_dependencies(self):
        datasets, plan = self._fix_expanded(metric=True)
        datasets[1].dataframe.at[7, "demo_n"] = -1
        evidence = o.run_synthetic_validation_plan(datasets, plan, True)
        self.assertEqual(set(evidence.blocked_check_ids), {"Same", "OtherMetric"})
        self.rejected(self.build(datasets=datasets, validation_plan=plan), "ORCHESTRATION_FAILED")

    def test_f21_partition_policy_unchanged(self):
        from components.partition_summary_validator import PartitionSummaryValidationSpec
        datasets, plan = self._fix_expanded()
        self.assertTrue(self.build(datasets=datasets, validation_plan=plan).passed)
        spec = PartitionSummaryValidationSpec((("demo_run", "demo_run"),), (("demo_pop", "demo_pop"),),
            "demo_cat", (("demo_n", "demo_n"),), ("DEMO_B", "DEMO_UNKNOWN"), True, True, True, True, False)
        plan = replace(plan, checks=plan.checks + (
            o.ValidationCheck("Partition", "PARTITION_SUMMARY", ("Demo", "Other"), spec, True),))
        with patch.object(q, "run_synthetic_validation_plan") as orchestrator, \
                patch.object(o, "validate_partition_summary_contract") as partition:
            result = self.build(datasets=datasets, validation_plan=plan)
        orchestrator.assert_not_called()
        partition.assert_not_called()
        self.rejected(result, "PARTITION_CONTRACT_OUT_OF_SCOPE")

    def test_f22_same_grain_legitimate_count_failure(self):
        datasets, plan = self._fix_expanded()
        datasets[1].dataframe.at[7, "demo_n"] = 3
        evidence = o.run_synthetic_validation_plan(datasets, plan, True)
        same = next(c for c in evidence.check_results if c.check_id == "Same")
        self.assertEqual(same.status, "FAIL")
        self.assertEqual(tuple(v for _, v in same.counts), (2, 2, 2, 2, 2, 2))
        self.rejected(self.build(datasets=datasets, validation_plan=plan), "ORCHESTRATION_FAILED")

    def test_f23_same_grain_duplicate_keys_do_not_invent_matched_counts(self):
        other = pd.concat([self.frame, self.frame.iloc[:1]], ignore_index=True)
        datasets, plan = self._fix_expanded(other_frame=other)
        evidence = o.run_synthetic_validation_plan(datasets, plan, True)
        same = next(c for c in evidence.check_results if c.check_id == "Same")
        self.assertEqual(same.status, "FAIL")
        self.assertEqual(tuple(v for _, v in same.counts), (2, 3, 2, 2, 0, 0))
        self.rejected(self.build(datasets=datasets, validation_plan=plan), "ORCHESTRATION_FAILED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
