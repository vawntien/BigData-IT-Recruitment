"""In-memory artificial fixtures only. No physical Q schemas or source artifacts."""

from dataclasses import asdict, fields, replace
from decimal import Decimal, getcontext
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components import validation_orchestrator as o
from components.artifact_gate import STATUS_SAMPLE, real_artifact_status
from components.consumer_adapter import ConsumerEnvelope, ConsumerIssue
from components.contract_validator import FieldSpec, ValidationSpec
from components.metric_validator import MetricValidationSpec, MetricValidationResult, MetricValidationIssue
from components.cross_table_validator import CrossTableValidationSpec, CrossTableValidationResult
from components.partition_summary_validator import PartitionSummaryValidationSpec, PartitionSummaryValidationResult


class Hostile:
    def __str__(self):
        raise AssertionError("SECRET")

    __repr__ = __str__

    def __hash__(self):
        raise AssertionError("SECRET")

    def __eq__(self, other):
        raise AssertionError("SECRET")


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({"key": ["ARTIFICIAL"], "ctx": ["RUN_DEMO"],
                                   "n": [2], "d": [4], "rate": [0.5], "origin": [STATUS_SAMPLE]}, dtype=object)
        self.metric = MetricValidationSpec("n", "d", "rate", "FRACTION", "NULL", Decimal("0"), True)
        self.same = CrossTableValidationSpec((("key", "key"),), (("n", "n"),),
                                             (("ctx", "ctx"),), False, True)
        self.partition = PartitionSummaryValidationSpec((("key", "key"),), (("ctx", "ctx"),),
            "part", (("n", "n"),), ("P1", "P2"), True, True, True, True, False)

    def binding(self, name="A", frame=None, **changes):
        frame = self.frame.copy(deep=True) if frame is None else frame
        rules = {n: FieldSpec("integer" if n in ("n", "d") else "number" if n == "rate" else "string", False)
                 for n in frame.columns}
        spec = ValidationSpec(rules, tuple(rules), (), (), True, False)
        binding = o.DatasetBinding(name, frame, spec, STATUS_SAMPLE, "origin")
        return replace(binding, **changes)

    def check(self, category="METRIC", refs=("A",), spec=None, name="Check"):
        if spec is None:
            spec = {"METRIC": self.metric, "SAME_GRAIN": self.same,
                    "PARTITION_SUMMARY": self.partition}.get(category)
        return o.ValidationCheck(name, category, refs, spec, True)

    def run_plan(self, bindings=None, checks=(), demo=True):
        bindings = (self.binding(),) if bindings is None else bindings
        schemas = tuple(o.ValidationCheck("Schema_" + b.dataset_id, "SCHEMA", (b.dataset_id,), b.schema_spec, True)
                        for b in bindings)
        return o.run_synthetic_validation_plan(bindings, o.ValidationPlan(schemas + checks), demo)

    def result(self, category, **kwargs):
        if category == "SAME_GRAIN":
            bindings = (self.binding(), self.binding("B"))
            refs = ("A", "B")
        elif category == "PARTITION_SUMMARY":
            p = pd.concat([self.frame.assign(part="P1", n=1), self.frame.assign(part="P2", n=1)], ignore_index=True)
            bindings = (self.binding("A", p), self.binding("B"))
            refs = ("A", "B")
        else:
            bindings, refs = (self.binding(),), ("A",)
        return self.run_plan(bindings, (self.check(category, refs),), **kwargs)

    def code(self, result, code):
        self.assertFalse(result.passed)
        self.assertIn(code, tuple(i.code for i in result.safe_issues))

    def test_t01_schema_only(self):
        r = self.run_plan()
        self.assertTrue(r.passed)
        self.assertEqual(r.overall_status, "SCHEMA_ONLY_VALIDATION")
        self.assertTrue(r.schema_scope_completed)
        self.assertEqual(r.successful_check_ids, ("Schema_A",))

    def test_t02_disabled(self):
        with patch.object(o, "build_synthetic_consumer_envelope") as builder:
            r = self.run_plan(demo=False)
        builder.assert_not_called()
        self.code(r, "DEMO_DISABLED")
        self.assertEqual(r.executed_check_ids, ())

    def test_t03_demo_type(self):
        for value in (1, "true", pd.NA, None, Hostile()):
            self.assertEqual(self.run_plan(demo=value).overall_status, "INVALID_PLAN")

    def test_t04_origins(self):
        for origin in ("REAL", "UNKNOWN", Hostile()):
            self.code(self.run_plan((self.binding(explicit_origin=origin),)), "ORIGIN_BLOCKED")

    def test_t05_schema_blocks_metric(self):
        b = self.binding()
        b.dataframe.at[0, "n"] = "PRIVATE_VALUE"
        with patch.object(o, "validate_metric_contract") as validator:
            r = self.run_plan((b,), (self.check(),))
        validator.assert_not_called()
        self.assertEqual(r.overall_status, "FAIL")
        self.code(r, "DEPENDENCY_BLOCKED")

    def test_t06_one_bad_of_two(self):
        a, b = self.binding(), self.binding("B")
        b.dataframe.at[0, "origin"] = "REAL"
        r = self.run_plan((a, b))
        self.assertEqual(r.overall_status, "FAIL")
        self.assertEqual(r.successful_check_ids, ("Schema_A",))

    def test_t07_metric_pass(self):
        self.assertTrue(self.result("METRIC").passed)

    def test_t08_ratio_mismatch(self):
        b = self.binding()
        b.dataframe.at[0, "rate"] = 0.75
        self.code(self.run_plan((b,), (self.check(),)), "RATE_INCONSISTENT")

    def test_t09_bad_metric_spec(self):
        for spec in (object(), replace(self.metric, rate_unit="PERCENT"),
                     replace(self.metric, tolerance=-1), replace(self.metric, numerator_column="d")):
            with patch.object(o, "validate_metric_contract") as validator:
                r = self.run_plan(checks=(self.check(spec=spec),))
            validator.assert_not_called()
            self.assertEqual(r.overall_status, "INVALID_PLAN")

    def test_t10_same_pass(self):
        self.assertTrue(self.result("SAME_GRAIN").passed)

    def test_t11_same_count(self):
        a, b = self.binding(), self.binding("B")
        b.dataframe.at[0, "n"] = 3
        self.code(self.run_plan((a, b), (self.check("SAME_GRAIN", ("A", "B")),)), "COUNT_MISMATCH")

    def test_t12_same_context(self):
        a, b = self.binding(), self.binding("B")
        b.dataframe.at[0, "ctx"] = "OTHER"
        self.code(self.run_plan((a, b), (self.check("SAME_GRAIN", ("A", "B")),)), "CONTEXT_MISMATCH")

    def test_t13_partition_pass(self):
        self.assertTrue(self.result("PARTITION_SUMMARY").passed)

    def test_t14_missing_partition(self):
        p = self.binding("A", self.frame.assign(part="P1"))
        self.code(self.run_plan((p, self.binding("B")),
            (self.check("PARTITION_SUMMARY", ("A", "B")),)), "MISSING_PARTITION")

    def test_t15_partition_count(self):
        p = pd.concat([self.frame.assign(part="P1"), self.frame.assign(part="P2")], ignore_index=True)
        self.code(self.run_plan((self.binding("A", p), self.binding("B")),
            (self.check("PARTITION_SUMMARY", ("A", "B")),)), "COUNT_MISMATCH")

    def test_t16_declarations(self):
        for field in ("additive", "disjoint", "exhaustive", "same_population_and_context"):
            r = self.run_plan((self.binding(), self.binding("B")),
                (self.check("PARTITION_SUMMARY", ("A", "B"), replace(self.partition, **{field: False})),))
            self.assertEqual(r.overall_status, "INVALID_PLAN")

    def test_t17_multiple_pass(self):
        r = self.run_plan((self.binding(), self.binding("B")),
            (self.check(name="Metric_A"), self.check(refs=("B",), name="Metric_B"),
             self.check("SAME_GRAIN", ("A", "B"), name="Same")))
        self.assertTrue(r.passed)
        self.assertEqual(len(r.successful_check_ids), 5)
        self.assertEqual(r.executed_check_ids, r.successful_check_ids)

    def test_t18_failure_aggregate(self):
        b = self.binding("B")
        b.dataframe.at[0, "rate"] = 0.8
        r = self.run_plan((self.binding(), b),
            (self.check(name="Good"), self.check(refs=("B",), name="Bad")))
        self.assertEqual(r.overall_status, "FAIL")
        self.assertIn("Good", r.successful_check_ids)
        self.assertNotIn("Bad", r.successful_check_ids)

    def test_t19_unknown_type(self):
        self.assertEqual(self.run_plan(checks=(self.check("UNKNOWN"),)).overall_status, "INVALID_PLAN")

    def test_t20_missing_reference(self):
        self.assertEqual(self.run_plan(checks=(self.check(refs=("Unknown",)),)).overall_status, "INVALID_PLAN")

    def test_t21_duplicate_check(self):
        self.assertEqual(self.run_plan(checks=(self.check(), self.check())).overall_status, "INVALID_PLAN")

    def test_t22_malformed_metric_result(self):
        for result in (None, MetricValidationResult(1, (), 1), MetricValidationResult(True, (), 99),
                       MetricValidationResult(True, (MetricValidationIssue("INVALID_RATE", (), "SECRET"),), 1)):
            with patch.object(o, "validate_metric_contract", return_value=result):
                self.code(self.result("METRIC"), "INVALID_VALIDATOR_RESULT")

    def test_t23_malformed_same_result(self):
        for result in (None, CrossTableValidationResult(True, (), 1, 1, 0, 0, 0, 0),
                       CrossTableValidationResult(True, (), 1, 1, 1, 1, 1, 2)):
            with patch.object(o, "validate_cross_table_contract", return_value=result):
                self.code(self.result("SAME_GRAIN"), "INVALID_VALIDATOR_RESULT")

    def test_t24_malformed_partition_result(self):
        for result in (None, PartitionSummaryValidationResult(True, (), 2, 1, 1, 1, 1, 0, 1),
                       PartitionSummaryValidationResult(True, (), 2, 1, 1, 1, 1, 1, True)):
            with patch.object(o, "validate_partition_summary_contract", return_value=result):
                self.code(self.result("PARTITION_SUMMARY"), "INVALID_VALIDATOR_RESULT")

    def test_t25_exceptions(self):
        for category, function in (("SCHEMA", "build_synthetic_consumer_envelope"),
                ("METRIC", "validate_metric_contract"), ("SAME_GRAIN", "validate_cross_table_contract"),
                ("PARTITION_SUMMARY", "validate_partition_summary_contract")):
            with patch.object(o, function, side_effect=RuntimeError("SECRET_RECORD")):
                r = self.run_plan() if category == "SCHEMA" else self.result(category)
            self.code(r, "VALIDATOR_EXCEPTION")
            self.assertNotIn("SECRET_RECORD", repr(r))

    def test_t26_malformed_envelope(self):
        good = ConsumerEnvelope(STATUS_SAMPLE, True, True, 1, ())
        for result in (None, replace(good, schema_valid=1), replace(good, row_count=True),
                       replace(good, demo_candidate=False), replace(good, row_count=2),
                       replace(good, structured_issues=(ConsumerIssue("schema", "INVALID_COUNT", (), None, "schema_validation"),))):
            with patch.object(o, "build_synthetic_consumer_envelope", return_value=result):
                self.code(self.run_plan(), "INVALID_VALIDATOR_RESULT")

    def test_t27_schema_blocks_all_relations(self):
        a, b = self.binding(), self.binding("B")
        b.dataframe.at[0, "origin"] = "REAL"
        with patch.object(o, "validate_cross_table_contract") as validator:
            r = self.run_plan((a, b), (self.check("SAME_GRAIN", ("A", "B")),))
        validator.assert_not_called()
        self.assertEqual(r.blocked_check_ids, ("Check",))

    def test_t28_independent_continues(self):
        a, b = self.binding(), self.binding("B")
        b.dataframe.at[0, "n"] = "BAD"
        r = self.run_plan((a, b), (self.check(),))
        self.assertFalse(r.passed)
        self.assertIn("Check", r.successful_check_ids)

    def test_t29_not_requested(self):
        self.assertEqual(dict(self.run_plan().category_statuses),
            {"SCHEMA": "PASS", "METRIC": "NOT_REQUESTED", "SAME_GRAIN": "NOT_REQUESTED", "PARTITION_SUMMARY": "NOT_REQUESTED"})

    def test_t30_no_inference(self):
        b = self.binding()
        self.assertEqual(o.run_synthetic_validation_plan((b,), o.ValidationPlan(()), True).overall_status, "INVALID_PLAN")
        with patch.object(o, "validate_metric_contract") as validator:
            self.run_plan()
        validator.assert_not_called()

    def test_t31_no_input_mutation(self):
        a, b = self.binding(), self.binding("B")
        copies = [x.dataframe.copy(deep=True) for x in (a, b)]
        self.run_plan((a, b), (self.check(), self.check("SAME_GRAIN", ("A", "B"), name="Same")))
        for binding, original in zip((a, b), copies):
            assert_frame_equal(binding.dataframe, original)

    def test_t32_metadata_only(self):
        def walk(value):
            self.assertNotIsInstance(value, (pd.DataFrame, pd.Series))
            if type(value) is dict:
                for v in value.values():
                    walk(v)
            elif type(value) in (tuple, list):
                for v in value:
                    walk(v)
            else:
                self.assertIn(type(value), (str, int, bool))
        walk(asdict(self.result("PARTITION_SUMMARY")))

    def test_t33_no_raw_diagnostics(self):
        b = self.binding()
        b.dataframe.index = ["SECRET_INDEX"]
        b.dataframe.at["SECRET_INDEX", "n"] = "SECRET_VALUE"
        r = self.run_plan((b,), (self.check(),))
        self.assertNotIn("SECRET", repr(r))

    def test_t34_repeatable(self):
        self.assertEqual(self.result("PARTITION_SUMMARY"), self.result("PARTITION_SUMMARY"))

    def test_t35_no_production_rights(self):
        r = self.result("METRIC")
        self.assertEqual(real_artifact_status(exists=True), "BLOCKED")
        self.assertFalse(any("production" in f.name.lower() or "approved" in f.name.lower() for f in fields(r)))
        self.assertEqual(r.overall_status, "SYNTHETIC_VALIDATION_PASS")

    def test_t36_hostile_identifiers(self):
        b = replace(self.binding(), dataset_id=Hostile())
        r = o.run_synthetic_validation_plan((b,), o.ValidationPlan(()), True)
        self.assertEqual(r.overall_status, "INVALID_PLAN")
        self.assertNotIn("SECRET", repr(r))

    def test_t37_ids_and_refs_before_execution(self):
        for check in (replace(self.check(), check_id=Hostile()), self.check(refs=("A", "A")),
                      replace(self.check(), check_id="unsafe/path")):
            with patch.object(o, "build_synthetic_consumer_envelope") as builder:
                r = self.run_plan(checks=(check,))
            builder.assert_not_called()
            self.assertEqual(r.overall_status, "INVALID_PLAN")

    def test_t38_actual_apis(self):
        for category in ("METRIC", "SAME_GRAIN", "PARTITION_SUMMARY"):
            r = self.result(category)
            self.assertTrue(r.passed, r)
            self.assertEqual(r.check_results[-1].category, category)
            self.assertTrue(r.check_results[-1].counts)

    def test_t39_failure_not_hidden(self):
        b = self.binding("B")
        b.dataframe.at[0, "n"] = 3
        r = self.run_plan((self.binding(), b), (self.check(name="Metric"),
            self.check("SAME_GRAIN", ("A", "B"), name="Same")))
        self.assertEqual(r.overall_status, "FAIL")
        self.assertEqual(r.check_results[-1].status, "FAIL")
        self.assertIn("Metric", r.successful_check_ids)
        self.code(r, "COUNT_MISMATCH")

    def test_t40_empty_not_findings(self):
        r = self.run_plan((self.binding(frame=self.frame.iloc[:0].copy()),))
        self.code(r, "EMPTY_SYNTHETIC_INPUT")
        self.assertEqual(r.overall_status, "BLOCKED")
        self.assertEqual(r.executed_check_ids, ("Schema_A",))

    def test_t41_plan_shapes(self):
        b = self.binding()
        schema = o.ValidationCheck("Schema", "SCHEMA", ("A",), b.schema_spec, True)
        for bindings, plan in (((), o.ValidationPlan((schema,))), ((b, b), o.ValidationPlan((schema,))),
                ((b,), None), ((b,), o.ValidationPlan([schema])),
                ((b,), o.ValidationPlan((replace(schema, required=False),))),
                ((replace(b, dataframe=None),), o.ValidationPlan((schema,)))):
            self.assertEqual(o.run_synthetic_validation_plan(bindings, plan, True).overall_status, "INVALID_PLAN")

    def test_t42_wrong_result_issues(self):
        for issue in (object(), MetricValidationIssue("SECRET", (), "SECRET"),
                      MetricValidationIssue("INVALID_RATE", (Hostile(),), "SECRET")):
            with patch.object(o, "validate_metric_contract", return_value=MetricValidationResult(False, (issue,), 1)):
                self.code(self.result("METRIC"), "INVALID_VALIDATOR_RESULT")

    def test_t43_declared_fields_missing_at_data_boundary(self):
        check = self.check(spec=replace(self.metric, numerator_column="absent"))
        r = self.run_plan(checks=(check,))
        self.code(r, "MISSING_COLUMNS")
        self.assertNotIn("INVALID_VALIDATOR_RESULT", [i.code for i in r.safe_issues])

    def test_t44_decimal_context_preserved(self):
        before = getcontext().copy()
        self.result("METRIC")
        self.assertEqual(getcontext().prec, before.prec)
        self.assertEqual(getcontext().flags, before.flags)

    def test_t45_relational_structural_failure(self):
        for category, spec in (("SAME_GRAIN", replace(self.same, metric_pairs=(("absent", "n"),))),
                ("PARTITION_SUMMARY", replace(self.partition, metric_pairs=(("absent", "n"),)))):
            r = self.run_plan((self.binding(), self.binding("B")),
                (self.check(category, ("A", "B"), spec),))
            self.code(r, "MISSING_COLUMNS")
            self.assertEqual(r.check_results[-1].counts[0][1], 0)

    def test_t46_zero_denominator_and_decimal(self):
        b = self.binding()
        b.dataframe.loc[0, ["n", "d", "rate"]] = [0, 0, pd.NA]
        rules = dict(b.schema_spec.fields)
        rules["rate"] = FieldSpec("number", True)
        b = replace(b, schema_spec=replace(b.schema_spec, fields=rules))
        self.assertTrue(self.run_plan((b,), (self.check(),)).passed)
        b.dataframe.loc[0, ["n", "d", "rate"]] = [Decimal(2), Decimal(4), Decimal("0.5")]
        self.assertTrue(self.run_plan((b,), (self.check(),)).passed)

    def test_t47_failed_result_count_invariants(self):
        issue = MetricValidationIssue("INVALID_RATE", (), "SECRET")
        for count in (None, -1, True, 100):
            with patch.object(o, "validate_metric_contract", return_value=MetricValidationResult(False, (issue,), count)):
                r = self.result("METRIC")
            self.code(r, "INVALID_VALIDATOR_RESULT")
            self.assertNotIn("SECRET", repr(r))

    def test_t48_invalid_relational_configs(self):
        for spec in (replace(self.partition, expected_partitions=()),
                     replace(self.partition, expected_partitions=("P1", "P1")),
                     replace(self.partition, partition_column="key"),
                     replace(self.partition, expected_partitions=(Hostile(),)),
                     replace(self.partition, context_pairs=None)):
            r = self.run_plan((self.binding(), self.binding("B")),
                (self.check("PARTITION_SUMMARY", ("A", "B"), spec),))
            self.assertEqual(r.overall_status, "INVALID_PLAN")

    def test_t49_frozen_results_and_original_arguments(self):
        from dataclasses import FrozenInstanceError
        b = self.binding()
        with patch.object(o, "validate_metric_contract", wraps=o.validate_metric_contract) as validator:
            r = self.run_plan((b,), (self.check(),))
        self.assertIs(validator.call_args.args[0], b.dataframe)
        self.assertIs(validator.call_args.args[1], self.metric)
        with self.assertRaises(FrozenInstanceError):
            r.passed = False

    def test_t50_schema_failure_blocks_partition(self):
        a, b = self.binding(), self.binding("B")
        a.dataframe.at[0, "n"] = "BAD"
        with patch.object(o, "validate_partition_summary_contract") as validator:
            r = self.run_plan((a, b), (self.check("PARTITION_SUMMARY", ("A", "B")),))
        validator.assert_not_called()
        self.assertEqual(r.check_results[-1].status, "BLOCKED")
        self.assertEqual(r.overall_status, "FAIL")

    # Hardening additions: retain the published 50 tests above unchanged.
    def _h_fixture(self, relational=False):
        class Description(str):
            pass

        frame = pd.DataFrame({
            "key": ["DEMO_B", "DEMO_A"], "ctx": ["RUN_DEMO"] * 2,
            "n": [Decimal("2"), Decimal("2")], "d": [4, 4],
            "rate": [Decimal("0.5"), Decimal("0.5")],
            "description": [Description("SENSITIVE_DESCRIPTION_B"),
                            Description("SENSITIVE_DESCRIPTION_A")],
            "origin": [STATUS_SAMPLE] * 2,
        }, index=pd.Index([29, 7], name="SENSITIVE_INDEX"), dtype=object)
        frame["d"] = frame["d"].astype("Int64")
        binding = self.binding("A", frame)
        binding = replace(binding, schema_spec=replace(binding.schema_spec,
                          unique_key=("key",), count_fields=("n", "d")))
        if relational:
            return (binding, replace(binding, dataset_id="B", dataframe=frame.copy(deep=True)))
        return (binding,)

    def _h_snapshots(self, bindings):
        return tuple((b.dataframe, b.dataframe.copy(deep=True),
                      tuple((i, j, b.dataframe.iat[i, j])
                            for j, dtype in enumerate(b.dataframe.dtypes) if dtype == object
                            for i in range(len(b.dataframe)))) for b in bindings)

    def _h_assert_preserved(self, snapshots):
        for frame, before, identities in snapshots:
            assert_frame_equal(frame, before, check_exact=True, check_dtype=True,
                               check_index_type=True, check_column_type=True, check_like=False)
            for i, j, original in identities:
                self.assertIs(frame.iat[i, j], original)

    def _h_assert_outcome(self, result, overall, states, issues=()):
        self.assertEqual(result.overall_status, overall)
        self.assertIs(result.passed, overall == "SYNTHETIC_VALIDATION_PASS")
        self.assertEqual(tuple((c.check_id, c.status, c.executed) for c in result.check_results), states)
        self.assertEqual(result.executed_check_ids, tuple(i for i, _, ran in states if ran))
        self.assertEqual(result.blocked_check_ids, tuple(i for i, status, _ in states if status == "BLOCKED"))
        self.assertEqual(result.successful_check_ids, tuple(i for i, status, _ in states if status == "PASS"))
        if overall == "INVALID_PLAN":
            self.assertEqual(result.safe_issues, (o.SafeIssue("", "INVALID_PLAN"),))
        else:
            self.assertEqual(result.safe_issues, tuple(issue for c in result.check_results for issue in c.issues))
        for check_id, code in issues:
            self.assertTrue(any(issue.check_id == check_id and issue.code == code
                                for issue in result.safe_issues))
            check = next(c for c in result.check_results if c.check_id == check_id)
            self.assertTrue(any(issue.check_id == check_id and issue.code == code for issue in check.issues))
        self.assertNotIn("SENSITIVE", repr(result))

    def _h_hostile_id(self, dataset_id):
        hooks = []

        class HostileId(str):
            def forbidden(self, *args):
                hooks.append("called")
                raise RuntimeError("SENSITIVE_ID")

            __str__ = __repr__ = __hash__ = __eq__ = forbidden

        binding = self.binding()
        schema = o.ValidationCheck("Schema_A", "SCHEMA", ("A",), binding.schema_spec, True)
        plan = o.ValidationPlan((schema,))
        positive = o.run_synthetic_validation_plan((binding,), plan, True)
        self.assertTrue(positive.passed)
        self.assertEqual(positive.overall_status, "SCHEMA_ONLY_VALIDATION")
        self.assertEqual(tuple((c.check_id, c.status, c.executed) for c in positive.check_results),
                         (("Schema_A", "PASS", True),))
        self.assertEqual(positive.executed_check_ids, ("Schema_A",))
        self.assertEqual(positive.successful_check_ids, ("Schema_A",))
        self.assertEqual(positive.blocked_check_ids, ())
        self.assertEqual(positive.safe_issues, ())
        # Keep the underlying ID identical to the positive control: only its
        # unsupported subclass changes, not references or uniqueness.
        hostile = HostileId("A" if dataset_id else "Schema_A")
        self.assertIs(type(hostile), HostileId)
        if dataset_id:
            bindings = (replace(binding, dataset_id=hostile),)
            self.assertIs(bindings[0].dataset_id, hostile)
        else:
            bindings = (binding,)
            plan = o.ValidationPlan((replace(schema, check_id=hostile),))
            self.assertIs(plan.checks[0].check_id, hostile)
        # Observe the actual identifier guard without replacing its behavior.
        with patch.object(o, "_identifier", wraps=o._identifier) as identifier, \
                patch.object(o, "build_synthetic_consumer_envelope") as builder, \
                patch.object(o, "validate_metric_contract") as metric, \
                patch.object(o, "validate_cross_table_contract") as same, \
                patch.object(o, "validate_partition_summary_contract") as partition:
            result = o.run_synthetic_validation_plan(bindings, plan, True)
        self.assertTrue(any(call.args[0] is hostile for call in identifier.call_args_list))
        for dependency in (builder, metric, same, partition):
            dependency.assert_not_called()
        self.assertEqual(hooks, [])
        self._h_assert_outcome(result, "INVALID_PLAN", ())
        self.assertFalse(result.schema_scope_completed)
        self.assertEqual(result.safe_issues, (o.SafeIssue("", "INVALID_PLAN"),))
        self.assertEqual(result.category_statuses, tuple((c, "NOT_REQUESTED") for c in
                         ("SCHEMA", "METRIC", "SAME_GRAIN", "PARTITION_SUMMARY")))

    def test_t51_hostile_dataset_string_id_reaches_binding_guard(self):
        self._h_hostile_id(dataset_id=True)

    def test_t52_hostile_check_string_id_reaches_check_guard(self):
        self._h_hostile_id(dataset_id=False)

    def test_t53_schema_failure_preserves_inputs_and_blocks_dependencies(self):
        bindings = self._h_fixture(relational=True)
        bindings[0].dataframe.at[29, "n"] = "SENSITIVE_BAD_COUNT"
        snapshots = self._h_snapshots(bindings)
        with patch.object(o, "validate_metric_contract") as metric, \
                patch.object(o, "validate_cross_table_contract") as same, \
                patch.object(o, "build_synthetic_consumer_envelope",
                             wraps=o.build_synthetic_consumer_envelope) as builder:
            result = self.run_plan(bindings, (self.check(name="Metric"),
                self.check("SAME_GRAIN", ("A", "B"), name="Same")))
        self.assertEqual(builder.call_count, 2)
        metric.assert_not_called()
        same.assert_not_called()
        self._h_assert_outcome(result, "FAIL", (("Schema_A", "FAIL", True),
            ("Schema_B", "PASS", True), ("Metric", "BLOCKED", False), ("Same", "BLOCKED", False)),
            (("Schema_A", "TYPE_MISMATCH"), ("Schema_A", "INVALID_COUNT"),
             ("Metric", "DEPENDENCY_BLOCKED"), ("Same", "DEPENDENCY_BLOCKED")))
        self._h_assert_preserved(snapshots)

    @staticmethod
    def _h_context_state():
        context = getcontext()
        return (context.prec, context.rounding, context.Emin, context.Emax,
                context.capitals, context.clamp, dict(context.traps), dict(context.flags))

    @staticmethod
    def _h_raise_after_context_change(*args):
        from decimal import ROUND_UP
        context = getcontext()
        context.prec = 7
        context.rounding = ROUND_UP
        context.Emin, context.Emax = -100, 100
        context.capitals, context.clamp = 0, 1
        for signal in context.traps:
            context.traps[signal] = not context.traps[signal]
        for signal in context.flags:
            context.flags[signal] = not context.flags[signal]
        raise RuntimeError("SENSITIVE_EXCEPTION_RECORD")

    def _h_exception_case(self, category):
        from decimal import Inexact, ROUND_FLOOR, Rounded, localcontext
        from components import consumer_adapter

        relational = category == "SAME_GRAIN"
        bindings = self._h_fixture(relational=relational)
        snapshots = self._h_snapshots(bindings)
        check = self.check("SAME_GRAIN", ("A", "B"), name="Same") if relational else self.check(name="Metric")
        owner, attribute = ((consumer_adapter, "validate_dataset_contract") if category == "SCHEMA" else
                            (o, "validate_cross_table_contract" if relational else "validate_metric_contract"))
        ambient = self._h_context_state()
        with localcontext() as context:
            context.prec, context.rounding = 31, ROUND_FLOOR
            context.Emin, context.Emax = -999, 999
            context.capitals, context.clamp = 1, 0
            context.clear_flags()
            context.flags[Rounded] = True
            context.traps[Inexact] = True
            before = self._h_context_state()
            with patch.object(owner, attribute, side_effect=self._h_raise_after_context_change) as validator:
                if category == "SCHEMA":
                    with patch.object(o, "validate_metric_contract") as dependent:
                        result = self.run_plan(bindings, (check,))
                    dependent.assert_not_called()
                else:
                    result = self.run_plan(bindings, (check,))
            validator.assert_called_once()
            self.assertIs(validator.call_args.args[0], bindings[0].dataframe)
            self.assertEqual(self._h_context_state(), before)
        self.assertEqual(self._h_context_state(), ambient)
        if category == "SCHEMA":
            states = (("Schema_A", "FAIL", True), ("Metric", "BLOCKED", False))
            issues = (("Schema_A", "SCHEMA_VALIDATOR_EXCEPTION"), ("Metric", "DEPENDENCY_BLOCKED"))
        elif relational:
            states = (("Schema_A", "PASS", True), ("Schema_B", "PASS", True), ("Same", "FAIL", True))
            issues = (("Same", "VALIDATOR_EXCEPTION"),)
            self.assertIs(validator.call_args.args[1], bindings[1].dataframe)
        else:
            states = (("Schema_A", "PASS", True), ("Metric", "FAIL", True))
            issues = (("Metric", "VALIDATOR_EXCEPTION"),)
        self._h_assert_outcome(result, "FAIL", states, issues)
        self._h_assert_preserved(snapshots)

    def test_t54_schema_exception_preserves_input_and_complete_decimal_context(self):
        self._h_exception_case("SCHEMA")

    def test_t55_metric_exception_preserves_input_and_complete_decimal_context(self):
        self._h_exception_case("METRIC")

    def test_t56_same_grain_exception_preserves_both_inputs_and_decimal_context(self):
        self._h_exception_case("SAME_GRAIN")

    def _h_normal_context_case(self, failure):
        from decimal import Inexact, ROUND_CEILING, Rounded, localcontext
        bindings = self._h_fixture()
        if failure:
            bindings[0].dataframe.at[29, "rate"] = Decimal("0.75")
        snapshots = self._h_snapshots(bindings)
        ambient = self._h_context_state()
        with localcontext() as context:
            context.prec, context.rounding = 33, ROUND_CEILING
            context.Emin, context.Emax = -888, 888
            context.capitals, context.clamp = 0, 1
            context.clear_flags()
            context.flags[Rounded] = True
            context.traps[Inexact] = True
            before = self._h_context_state()
            result = self.run_plan(bindings, (self.check(name="Metric"),))
            self.assertEqual(self._h_context_state(), before)
        self.assertEqual(self._h_context_state(), ambient)
        self._h_assert_outcome(result, "FAIL" if failure else "SYNTHETIC_VALIDATION_PASS",
            (("Schema_A", "PASS", True), ("Metric", "FAIL" if failure else "PASS", True)),
            (("Metric", "RATE_INCONSISTENT"),) if failure else ())
        if not failure:
            self.assertEqual(result.safe_issues, ())
        self._h_assert_preserved(snapshots)

    def test_t57_success_preserves_input_and_complete_decimal_context(self):
        self._h_normal_context_case(failure=False)

    def test_t58_controlled_failure_preserves_input_and_complete_decimal_context(self):
        self._h_normal_context_case(failure=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
