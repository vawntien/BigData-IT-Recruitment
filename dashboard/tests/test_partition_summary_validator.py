"""Tiny synthetic declarations only; no approved business schemas or data."""

from dataclasses import replace
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.partition_summary_validator import (
    PartitionSummaryValidationSpec, validate_partition_summary_contract,
)
from components.artifact_gate import real_artifact_status


class PartitionSummaryValidatorTests(unittest.TestCase):
    def setUp(self):
        self.partition = pd.DataFrame({
            "group": ["DEMO_G"] * 3, "part": ["P1", "P2", "P3"],
            "run": ["DEMO_RUN"] * 3, "population": ["DEMO_SCOPE"] * 3,
            "n": [40, 35, 25],
        }, dtype=object)
        self.summary = pd.DataFrame({
            "group": ["DEMO_G"], "run": ["DEMO_RUN"],
            "population": ["DEMO_SCOPE"], "n": [100],
        }, dtype=object)
        self.spec = PartitionSummaryValidationSpec(
            group_key_pairs=(("group", "group"),),
            context_pairs=(("run", "run"), ("population", "population")),
            partition_column="part", metric_pairs=(("n", "n"),),
            expected_partitions=("P1", "P2", "P3"), additive=True,
            disjoint=True, exhaustive=True, same_population_and_context=True,
            allow_empty=False,
        )

    def check(self, partition=None, summary=None, spec=None):
        return validate_partition_summary_contract(
            self.partition if partition is None else partition,
            self.summary if summary is None else summary,
            self.spec if spec is None else spec,
        )

    def rejected(self, result, code, side=None, fields=None):
        self.assertFalse(result.passed)
        self.assertTrue(any(e.code == code and (side is None or e.side == side)
                            and (fields is None or e.fields == fields)
                            and e.violation_count > 0 for e in result.errors), result)

    def marker_frame(self, side, field, marker, index=0):
        frame = getattr(self, side).copy(deep=True).astype({field: object})
        # Scalar .at assignment can unpack ndarray markers. Build an object
        # buffer so rejection tests exercise the actual unsupported object.
        values = np.empty(len(frame), dtype=object)
        for position, value in enumerate(frame[field]):
            values[position] = value
        values[index] = marker
        frame[field] = pd.Series(values, index=frame.index, dtype=object)
        self.assertIs(type(frame.at[index, field]), type(marker))
        self.assertIs(frame.at[index, field], marker)
        return frame

    def two_groups(self):
        partition = pd.concat([self.partition, self.partition.assign(group="DEMO_H")], ignore_index=True)
        summary = pd.concat([self.summary, self.summary.assign(group="DEMO_H")], ignore_index=True)
        return partition, summary

    def test_t01_three_partitions(self):
        result = self.check()
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())
        self.assertEqual((result.partition_checked_rows, result.summary_checked_rows), (3, 1))
        self.assertEqual((result.partition_group_count, result.summary_group_count,
                          result.matched_group_count, result.reconciled_group_count,
                          result.compared_metric_count), (1, 1, 1, 1, 1))

    def test_t02_sum_differs(self):
        self.partition.at[0, "n"] = 41
        self.rejected(self.check(), "COUNT_MISMATCH", "both", ("n", "n"))

    def test_t03_summary_greater(self):
        self.summary.at[0, "n"] = 110
        self.rejected(self.check(), "COUNT_MISMATCH")

    def test_t04_summary_smaller(self):
        self.summary.at[0, "n"] = 90
        self.rejected(self.check(), "COUNT_MISMATCH")

    def test_t05_missing_partition(self):
        result = self.check(self.partition.iloc[:2])
        self.rejected(result, "MISSING_PARTITION", "partition", ("part",))
        self.assertEqual(result.compared_metric_count, 0)

    def test_t06_unexpected_partition(self):
        frame = pd.concat([self.partition, self.partition.iloc[:1].assign(part="P4", n=0)])
        result = self.check(frame)
        self.rejected(result, "UNEXPECTED_PARTITION", "partition", ("part",))
        self.assertEqual(result.compared_metric_count, 0)

    def test_t07_duplicate_partition(self):
        for count in (0, 40):
            frame = pd.concat([self.partition, self.partition.iloc[:1].assign(n=count)])
            result = self.check(frame)
            self.rejected(result, "DUPLICATE_PARTITION")
            self.assertEqual(result.compared_metric_count, 0)

    def test_t08_duplicate_summary(self):
        for count in (100, 200):
            frame = pd.concat([self.summary, self.summary.assign(n=count)])
            result = self.check(summary=frame)
            self.rejected(result, "DUPLICATE_SUMMARY", "summary")
            self.assertEqual(result.compared_metric_count, 0)

    def test_t09_null_partition(self):
        for null in (None, pd.NA, pd.NaT, float("nan"), Decimal("NaN")):
            self.rejected(self.check(self.marker_frame("partition", "part", null)), "NULL_PARTITION")

    def test_t10_invalid_group_key(self):
        for side in ("partition", "summary"):
            for value, code in ((None, "NULL_KEY"), ([1], "INVALID_KEY"), ({"x": 1}, "INVALID_KEY")):
                self.rejected(self.check(**{side: self.marker_frame(side, "group", value)}), code, side, ("group",))

    def test_t11_summary_only_group(self):
        summary = pd.concat([self.summary, self.summary.assign(group="EXTRA")])
        result = self.check(summary=summary)
        self.rejected(result, "SUMMARY_ONLY_GROUP", "summary")
        issue = next(e for e in result.errors if e.code == "MISSING_PARTITION")
        self.assertEqual(issue.violation_count, 3)

    def test_t12_partition_only_group(self):
        frame = pd.concat([self.partition, self.partition.assign(group="EXTRA")])
        self.rejected(self.check(frame), "PARTITION_ONLY_GROUP", "partition")

    def test_t13_different_population(self):
        self.summary.at[0, "population"] = "OTHER_SCOPE"
        result = self.check()
        self.rejected(result, "SUMMARY_ONLY_GROUP")
        self.rejected(result, "PARTITION_ONLY_GROUP")
        self.assertEqual(result.compared_metric_count, 0)

    def test_t14_different_run(self):
        self.summary.at[0, "run"] = "OTHER_RUN"
        self.rejected(self.check(), "SUMMARY_ONLY_GROUP")

    def test_t15_matching_counts_different_filter_context(self):
        self.partition["filter"] = "DEMO_FILTER_A"
        self.summary["filter"] = "DEMO_FILTER_B"
        spec = replace(self.spec, context_pairs=self.spec.context_pairs + (("filter", "filter"),))
        result = self.check(spec=spec)
        self.rejected(result, "PARTITION_ONLY_GROUP")
        self.assertEqual(result.compared_metric_count, 0)

    def test_t16_explicit_zero_is_valid(self):
        self.partition["n"] = [0, 0, 0]
        self.summary["n"] = [0]
        self.assertTrue(self.check().passed)

    def test_t17_missing_is_not_zero(self):
        self.partition["n"] = [40, 60, 0]
        result = self.check(self.partition.iloc[:2])
        self.rejected(result, "MISSING_PARTITION")
        self.assertEqual(result.compared_metric_count, 0)

    def test_t18_negative_count(self):
        for side in ("partition", "summary"):
            self.rejected(self.check(**{side: self.marker_frame(side, "n", -1)}), "INVALID_COUNT", side, ("n",))

    def test_t19_fractional_count(self):
        for side in ("partition", "summary"):
            for value in (1.5, Decimal("1.5"), Fraction(1, 2)):
                self.rejected(self.check(**{side: self.marker_frame(side, "n", value)}), "INVALID_COUNT", side)

    def test_t20_boolean_count(self):
        for side in ("partition", "summary"):
            for value in (True, False, np.bool_(True)):
                self.rejected(self.check(**{side: self.marker_frame(side, "n", value)}), "INVALID_COUNT", side)

    def test_t21_nonfinite_and_null_count(self):
        context = getcontext()
        before = (context.prec, context.rounding, dict(context.traps), dict(context.flags))
        for side in ("partition", "summary"):
            for value in (None, pd.NA, pd.NaT, float("nan"), float("inf"), -float("inf"),
                          Decimal("NaN"), Decimal("sNaN123"), Decimal("Infinity")):
                result = self.check(**{side: self.marker_frame(side, "n", value)})
                self.rejected(result, "INVALID_COUNT", side)
                self.assertEqual(result.compared_metric_count, 0)
        self.assertEqual(before, (context.prec, context.rounding, dict(context.traps), dict(context.flags)))

    def test_t22_large_exact_integer(self):
        huge = 10 ** 1000
        self.partition["n"] = pd.Series([huge, huge + 1, huge + 2], dtype=object)
        self.summary["n"] = pd.Series([3 * huge + 3], dtype=object)
        self.assertTrue(self.check().passed)
        self.summary.at[0, "n"] += 1
        self.rejected(self.check(), "COUNT_MISMATCH")

    def test_t23_row_order(self):
        partition, summary = self.two_groups()
        result = self.check(partition.iloc[[5, 0, 3, 1, 4, 2]], summary.iloc[::-1])
        self.assertTrue(result.passed)
        self.assertEqual(result.compared_metric_count, 2)

    def test_t24_multiple_groups(self):
        result = self.check(*self.two_groups())
        self.assertTrue(result.passed)
        self.assertEqual(result.reconciled_group_count, 2)

    def test_t25_one_invalid_among_valid_groups(self):
        partition, summary = self.two_groups()
        partition.at[4, "n"] = -1
        result = self.check(partition, summary)
        self.rejected(result, "INVALID_COUNT")
        self.assertEqual(result.compared_metric_count, 1)
        self.assertEqual((result.partition_checked_rows, result.summary_checked_rows), (6, 2))

    def test_t26_both_empty_policies(self):
        partition, summary = self.partition.iloc[:0], self.summary.iloc[:0]
        self.rejected(self.check(partition, summary), "EMPTY_INPUT")
        result = self.check(partition, summary, replace(self.spec, allow_empty=True))
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())
        self.assertEqual((result.partition_checked_rows, result.summary_checked_rows,
                          result.reconciled_group_count), (0, 0, 0))

    def test_t27_one_empty(self):
        spec = replace(self.spec, allow_empty=True)
        self.rejected(self.check(self.partition.iloc[:0], spec=spec), "SUMMARY_ONLY_GROUP")
        self.rejected(self.check(summary=self.summary.iloc[:0], spec=spec), "PARTITION_ONLY_GROUP")

    def test_t28_invalid_spec(self):
        for spec in (None, {}, replace(self.spec, group_key_pairs=()),
                     replace(self.spec, group_key_pairs=None), replace(self.spec, context_pairs=None),
                     replace(self.spec, metric_pairs=()), replace(self.spec, partition_column=None),
                     replace(self.spec, allow_empty=1), replace(self.spec, group_key_pairs=(([], "group"),)),
                     replace(self.spec, metric_pairs=(("n", "n"), ("n", "n")))):
            result = validate_partition_summary_contract(self.partition, self.summary, spec)
            self.rejected(result, "INVALID_SPEC")
            self.assertEqual(result.partition_checked_rows, 0)

    def test_t29_declarations_required_before_scanning(self):
        for field in ("additive", "disjoint", "exhaustive", "same_population_and_context"):
            for value in (False, None, 1, np.bool_(True), "true"):
                with patch("components.partition_summary_validator._count", side_effect=AssertionError("must not scan")):
                    result = self.check(spec=replace(self.spec, **{field: value}))
                self.rejected(result, "INVALID_DECLARATION", "spec")
                self.assertEqual(result.compared_metric_count, 0)

    def test_t30_string_subclass_hooks_rejected(self):
        class Trap(str):
            def forbidden(self, *args):
                raise RuntimeError("PRIVATE_HOOK")
            __str__ = __eq__ = __hash__ = __repr__ = forbidden
        class Alias(str):
            def __str__(self):
                return "P1"
        for cls in (Trap, Alias):
            for side in ("partition", "summary"):
                for field, code in (("group", "INVALID_KEY"), ("run", "INVALID_CONTEXT")):
                    result = self.check(**{side: self.marker_frame(side, field, cls("PRIVATE_VALUE"))})
                    self.rejected(result, code, side, (field,))
                    self.assertNotIn("PRIVATE", repr(result))
            result = self.check(self.marker_frame("partition", "part", cls("PRIVATE_VALUE")))
            self.rejected(result, "INVALID_PARTITION", "partition", ("part",))

    def test_t31_no_input_mutation(self):
        for invalid in (False, True):
            partition, summary = self.partition.copy(deep=True), self.summary.copy(deep=True)
            partition.index = [7, 7, 7]
            summary.index = [9]
            if invalid:
                partition.iloc[1, partition.columns.get_loc("n")] = -1
            before_p, before_s = partition.copy(deep=True), summary.copy(deep=True)
            self.assertEqual(self.check(partition, summary).passed, not invalid)
            assert_frame_equal(partition, before_p, check_exact=True)
            assert_frame_equal(summary, before_s, check_exact=True)

    def test_t32_diagnostic_safety(self):
        self.partition.at[0, "group"] = "PRIVATE_KEY"
        self.partition.at[1, "part"] = "PRIVATE_PARTITION"
        self.partition.at[2, "n"] = "PRIVATE_COUNT"
        self.partition["description"] = "PRIVATE_PAYLOAD"
        self.partition.index = ["PRIVATE_INDEX"] * 3
        result = self.check()
        self.rejected(result, "UNEXPECTED_PARTITION")
        self.rejected(result, "INVALID_COUNT")
        for secret in ("PRIVATE_KEY", "PRIVATE_PARTITION", "PRIVATE_COUNT", "PRIVATE_PAYLOAD", "PRIVATE_INDEX"):
            self.assertNotIn(secret, repr(result))

    def test_t33_pass_cannot_enable_production(self):
        result = self.check()
        self.assertTrue(result.passed)
        self.assertFalse(hasattr(result, "production_eligible"))
        self.assertEqual(real_artifact_status(exists=True), "BLOCKED")

    def test_t34_invalid_domain(self):
        class Trap(str):
            def __hash__(self):
                raise RuntimeError("PRIVATE_DOMAIN")
        for domain in ((), None, [], {"P1"}, ("P1", "P1"), ("P1", np.str_("P1")),
                       (None,), (pd.NA,), (float("nan"),), ([1],), (Trap("P1"),), (Decimal("sNaN"),)):
            result = self.check(spec=replace(self.spec, expected_partitions=domain))
            self.rejected(result, "INVALID_DOMAIN", "spec")
            self.assertEqual(result.partition_checked_rows, 0)
            self.assertNotIn("PRIVATE_DOMAIN", repr(result))

    def test_t35_multiple_metrics(self):
        self.partition["second"] = [2, 3, 4]
        self.summary["other"] = [9]
        spec = replace(self.spec, metric_pairs=(("n", "n"), ("second", "other")))
        result = self.check(spec=spec)
        self.assertTrue(result.passed)
        self.assertEqual(result.compared_metric_count, 2)
        self.summary.at[0, "other"] = 10
        result = self.check(spec=spec)
        self.rejected(result, "COUNT_MISMATCH", "both", ("second", "other"))
        self.assertEqual(result.compared_metric_count, 2)
        self.partition.at[0, "n"] = None
        result = self.check(spec=spec)
        self.rejected(result, "INVALID_COUNT", "partition", ("n",))
        self.rejected(result, "COUNT_MISMATCH", "both", ("second", "other"))
        self.assertEqual(result.compared_metric_count, 1)

    def test_missing_invalid_input_and_columns(self):
        for index, side in enumerate(("partition", "summary")):
            for value, code in ((None, "MISSING_INPUT"), ([], "INVALID_INPUT")):
                args = [self.partition, self.summary]
                args[index] = value
                self.rejected(validate_partition_summary_contract(*args, self.spec), code, side)
            frame = getattr(self, side).drop(columns="run")
            self.rejected(self.check(**{side: frame}), "MISSING_COLUMNS", side, ("run",))
            duplicate = pd.concat([getattr(self, side), getattr(self, side)[["n"]]], axis=1)
            self.rejected(self.check(**{side: duplicate}), "INVALID_COLUMNS", side)
        empty = self.partition.iloc[:0].drop(columns="part")
        self.rejected(self.check(empty, self.summary.iloc[:0], replace(self.spec, allow_empty=True)), "MISSING_COLUMNS")

    def test_numeric_count_representations_and_bounds(self):
        for values in ([np.int64(40), np.uint64(35), Decimal("25")], [40.0, Fraction(35), np.float32(25)]):
            self.partition["n"] = pd.Series(values, dtype=object)
            self.assertTrue(self.check().passed)
        for value in ("40", object(), 1 << 20000, Decimal("1e1000000000"), Fraction(1, 1 << 20000)):
            self.rejected(self.check(self.marker_frame("partition", "n", value)), "INVALID_COUNT")
        maximum = (1 << 16384) - 1
        self.partition["n"] = pd.Series([maximum, 1, 0], dtype=object)
        self.summary["n"] = pd.Series([maximum], dtype=object)
        result = self.check()
        self.rejected(result, "SUM_LIMIT")
        self.assertEqual(result.compared_metric_count, 0)

    def test_numeric_subclass_rejection_without_hooks(self):
        class TrapInt(int):
            def __int__(self):
                raise RuntimeError("PRIVATE_NUMERIC")
        for field, code in (("group", "INVALID_KEY"), ("part", "INVALID_PARTITION"), ("n", "INVALID_COUNT")):
            self.rejected(self.check(self.marker_frame("partition", field, TrapInt(40))), code)

    def test_typed_identity_and_numpy_strings(self):
        for field in ("group", "run", "part"):
            frame = self.marker_frame("partition", field, np.str_(self.partition.at[0, field]))
            self.assertTrue(self.check(frame).passed)
        for left, right in ((True, 1), (1, 1.0), (Decimal("1"), 1.0)):
            self.partition["group"] = pd.Series([left] * 3, dtype=object)
            self.summary["group"] = pd.Series([right], dtype=object)
            self.rejected(self.check(), "PARTITION_ONLY_GROUP")
        self.partition["part"] = pd.Series([True, 1, 1.0], dtype=object)
        self.partition["group"] = "G"
        self.summary["group"] = "G"
        self.assertTrue(self.check(spec=replace(self.spec, expected_partitions=(True, 1, 1.0))).passed)

    def test_explicit_aliases_and_context_in_group_keys(self):
        summary = self.summary.rename(columns={"group": "category", "run": "snapshot", "population": "scope", "n": "total"})
        spec = replace(self.spec, group_key_pairs=(("group", "category"),),
                       context_pairs=(("run", "snapshot"), ("population", "scope")), metric_pairs=(("n", "total"),))
        self.assertTrue(self.check(summary=summary, spec=spec).passed)
        spec = replace(self.spec, group_key_pairs=self.spec.group_key_pairs + self.spec.context_pairs, context_pairs=())
        self.assertTrue(self.check(spec=spec).passed)
        for spec in (replace(self.spec, partition_column="group"),
                     replace(self.spec, context_pairs=(("group", "run"),)),
                     replace(self.spec, metric_pairs=(("run", "n"),))):
            self.rejected(self.check(spec=spec), "INVALID_SPEC")

    def test_nullable_storage_and_missing_context(self):
        partition = self.partition.astype({"group": "string", "part": "string", "n": "Int64"})
        summary = self.summary.astype({"group": "string", "n": "Int64"})
        self.assertTrue(self.check(partition, summary).passed)
        for side in ("partition", "summary"):
            for value in (None, pd.NA, pd.NaT, float("nan")):
                self.rejected(self.check(**{side: self.marker_frame(side, "run", value)}), "INVALID_CONTEXT", side, ("run",))

    def test_duplicate_group_does_not_block_other_valid_group(self):
        partition, summary = self.two_groups()
        partition = pd.concat([partition, partition.iloc[:1]], ignore_index=True)
        result = self.check(partition, summary)
        self.rejected(result, "DUPLICATE_PARTITION")
        self.assertEqual(result.reconciled_group_count, 1)
        self.assertEqual(result.compared_metric_count, 1)

    def test_contexts_with_same_group_label_are_not_pooled(self):
        partition = pd.concat([self.partition, self.partition.assign(run="OTHER_RUN", n=0)], ignore_index=True)
        summary = pd.concat([self.summary, self.summary.assign(run="OTHER_RUN", n=0)], ignore_index=True)
        result = self.check(partition, summary)
        self.assertTrue(result.passed)
        self.assertEqual(result.reconciled_group_count, 2)
        # Same overall sum, but wrong per-context counts must not pass.
        summary["n"] = [0, 100]
        result = self.check(partition, summary)
        self.rejected(result, "COUNT_MISMATCH")
        issue = next(e for e in result.errors if e.code == "COUNT_MISMATCH")
        self.assertEqual(issue.violation_count, 2)

    def test_duplicate_summary_group_skips_only_affected_group(self):
        partition, summary = self.two_groups()
        summary = pd.concat([summary, summary.iloc[:1].assign(n=999)], ignore_index=True)
        for reordered in (summary, summary.iloc[::-1]):
            result = self.check(partition, reordered)
            self.rejected(result, "DUPLICATE_SUMMARY")
            self.assertEqual(result.compared_metric_count, 1)
            self.assertEqual(result.reconciled_group_count, 1)

    def test_unsupported_partition_scalars_and_numpy_subclass(self):
        class TrapNumpyString(np.str_):
            def __str__(self):
                raise RuntimeError("PRIVATE_NUMPY_HOOK")
        for value in ([1], {"p": 1}, np.array([1]), pd.Timestamp("2026-01-01"),
                      Decimal("sNaN"), TrapNumpyString("P1")):
            result = self.check(self.marker_frame("partition", "part", value))
            self.rejected(result, "INVALID_PARTITION", "partition", ("part",))
            self.assertEqual(result.compared_metric_count, 0)
            self.assertNotIn("PRIVATE_NUMPY_HOOK", repr(result))

    def test_malformed_metadata_names_rejected_without_hooks(self):
        class TrapName(str):
            def __hash__(self):
                raise RuntimeError("PRIVATE_NAME_HOOK")
            def strip(self):
                raise RuntimeError("PRIVATE_NAME_HOOK")
        spec = replace(self.spec, group_key_pairs=((TrapName("group"), "group"),))
        self.rejected(self.check(spec=spec), "INVALID_SPEC")
        frame = self.partition.copy()
        frame.columns = pd.Index([TrapName("group"), "part", "run", "population", "n"])
        self.rejected(self.check(frame), "INVALID_COLUMNS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
