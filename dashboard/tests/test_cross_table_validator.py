"""Synthetic declarations only, not an approved physical/business contract."""

from dataclasses import replace
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.cross_table_validator import CrossTableValidationSpec, validate_cross_table_contract
from components.artifact_gate import real_artifact_status


class CrossTableValidatorTests(unittest.TestCase):
    def setUp(self):
        self.left = pd.DataFrame({"group": ["DEMO_A", "DEMO_B"], "part": [1, 1],
                                  "run": ["RUN_DEMO"] * 2, "scope": ["SCOPE_DEMO"] * 2,
                                  "count": [100, 20]})
        self.right = self.left.copy(deep=True)
        self.spec = CrossTableValidationSpec(
            key_pairs=(("group", "group"), ("part", "part")),
            metric_pairs=(("count", "count"),),
            context_pairs=(("run", "run"), ("scope", "scope")),
            allow_empty=False, require_exact_key_set=True,
        )

    def check(self, left=None, right=None, spec=None):
        return validate_cross_table_contract(
            self.left if left is None else left, self.right if right is None else right,
            self.spec if spec is None else spec,
        )

    def assert_fail(self, result, code, side=None, fields=None):
        self.assertFalse(result.passed)
        matches = [e for e in result.errors if e.code == code]
        self.assertTrue(matches, result)
        if side is not None:
            self.assertTrue(any(e.side == side for e in matches), result)
        if fields is not None:
            self.assertTrue(any(e.fields == fields for e in matches), result)

    def test_t01_same_keys_counts_different_order(self):
        result = self.check(right=self.right.iloc[::-1])
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())
        self.assertEqual((result.left_checked_rows, result.right_checked_rows), (2, 2))
        self.assertEqual((result.left_key_count, result.right_key_count, result.matched_key_count), (2, 2, 2))
        self.assertEqual(result.compared_metric_count, 2)

    def test_t02_count_mismatch(self):
        self.right.loc[0, "count"] = 120
        self.assert_fail(self.check(), "COUNT_MISMATCH", "both", ("count", "count"))

    def test_t03_key_absent_on_left(self):
        result = self.check(left=self.left.iloc[1:])
        self.assert_fail(result, "RIGHT_ONLY_KEYS", "right")
        self.assertEqual(result.matched_key_count, 1)

    def test_t04_key_absent_on_right(self):
        self.assert_fail(self.check(right=self.right.iloc[1:]), "LEFT_ONLY_KEYS", "left")

    def test_t05_duplicate_key_left(self):
        result = self.check(left=pd.concat([self.left, self.left.iloc[:1]], ignore_index=True))
        self.assert_fail(result, "DUPLICATE_KEY", "left")
        self.assertEqual(result.compared_metric_count, 0)

    def test_t06_duplicate_key_right(self):
        self.assert_fail(self.check(right=pd.concat([self.right, self.right.iloc[:1]], ignore_index=True)),
                         "DUPLICATE_KEY", "right")

    def test_t07_null_composite_key(self):
        for null in (None, pd.NA, float("nan"), Decimal("NaN"), pd.NaT):
            for side in ("left", "right"):
                frame = getattr(self, side).astype({"part": object})
                frame.loc[0, "part"] = null
                self.assert_fail(self.check(**{side: frame}), "NULL_KEY", side, ("part",))

    def test_t08_different_run(self):
        self.right.loc[0, "run"] = "OTHER_RUN"
        result = self.check()
        self.assert_fail(result, "CONTEXT_MISMATCH", "both", ("run", "run"))
        self.assertEqual(result.compared_metric_count, 1)

    def test_t09_different_population(self):
        self.right.loc[0, "scope"] = "OTHER_SCOPE"
        self.assert_fail(self.check(), "CONTEXT_MISMATCH", "both", ("scope", "scope"))

    def test_t10_missing_context_column_or_value(self):
        self.assert_fail(self.check(right=self.right.drop(columns="run")), "MISSING_COLUMNS", "right", ("run",))
        for unknown in (None, pd.NA, ["RUN_DEMO"], Decimal("sNaN")):
            frame = self.right.astype({"run": object})
            frame.at[0, "run"] = unknown
            self.assert_fail(self.check(right=frame), "INVALID_CONTEXT", "right", ("run",))

    def test_t11_explicit_different_column_names(self):
        renamed = self.right.rename(columns={"group": "category", "part": "bucket", "count": "total_jobs",
                                              "run": "run_id", "scope": "population_id"})
        spec = replace(self.spec, key_pairs=(("group", "category"), ("part", "bucket")),
                       metric_pairs=(("count", "total_jobs"),),
                       context_pairs=(("run", "run_id"), ("scope", "population_id")))
        result = self.check(right=renamed, spec=spec)
        self.assertTrue(result.passed)
        self.assertEqual(result.compared_metric_count, 2)

    def test_t12_same_names_do_not_prove_context(self):
        self.right["run"] = ["OTHER_RUN"] * 2
        self.assert_fail(self.check(), "CONTEXT_MISMATCH")

    def test_t13_zero_count_matches(self):
        self.left["count"] = self.right["count"] = [0, 0]
        self.assertTrue(self.check().passed)

    def test_t14_null_count_not_zero(self):
        for null in (None, pd.NA, float("nan"), Decimal("NaN")):
            frame = self.left.astype({"count": object})
            frame.loc[0, "count"] = null
            self.assert_fail(self.check(left=frame), "INVALID_COUNT", "left", ("count",))

    def test_t15_invalid_count_values_on_both_sides(self):
        for invalid in (-1, 1.5, True, np.bool_(False), "100", float("inf"), Decimal("Infinity"), Fraction(1, 2)):
            for side in ("left", "right"):
                frame = getattr(self, side).astype({"count": object})
                frame.at[0, "count"] = invalid
                self.assert_fail(self.check(**{side: frame}), "INVALID_COUNT", side)

    def test_t16_large_exact_counts_do_not_round(self):
        huge = 10 ** 1000
        self.left["count"] = pd.Series([huge, huge + 1], dtype=object)
        self.right["count"] = pd.Series([huge, huge + 1], dtype=object)
        self.assertTrue(self.check().passed)
        self.right.loc[1, "count"] = huge
        self.assert_fail(self.check(), "COUNT_MISMATCH")

    def test_t17_malformed_unhashable_keys_fail(self):
        for bad in ([1], {"nested": 1}, {1, 2}, np.array([1]), Decimal("sNaN"), float("inf")):
            frame = self.left.astype({"part": object})
            frame.at[0, "part"] = bad
            self.assert_fail(self.check(left=frame), "INVALID_KEY", "left")

    def test_t18_duplicate_column_labels(self):
        for side in ("left", "right"):
            frame = getattr(self, side)
            duplicated = pd.concat([frame, frame[["count"]]], axis=1)
            self.assert_fail(self.check(**{side: duplicated}), "INVALID_COLUMNS", side)

    def test_t19_both_empty_require_explicit_policy_and_schema(self):
        left, right = self.left.iloc[:0], self.right.iloc[:0]
        self.assert_fail(self.check(left, right), "EMPTY_INPUT")
        spec = replace(self.spec, allow_empty=True)
        result = self.check(left, right, spec)
        self.assertTrue(result.passed)
        self.assertEqual((result.left_checked_rows, result.right_checked_rows, result.matched_key_count), (0, 0, 0))
        self.assert_fail(self.check(left.drop(columns="part"), right, spec), "MISSING_COLUMNS")

    def test_t20_one_empty_cannot_drop_unmatched_rows(self):
        spec = replace(self.spec, allow_empty=True)
        self.assert_fail(self.check(self.left.iloc[:0], self.right, spec), "RIGHT_ONLY_KEYS")
        self.assert_fail(self.check(self.left, self.right.iloc[:0], spec), "LEFT_ONLY_KEYS")

    def test_t21_input_preservation_pass_and_fail(self):
        for mismatch in (False, True):
            right = self.right.copy(deep=True)
            if mismatch:
                right.loc[0, "count"] = 99
            self.left.index = pd.Index([7, 7], name="synthetic_index")
            right.index = pd.Index([9, 9], name="other_index")
            before_left, before_right = self.left.copy(deep=True), right.copy(deep=True)
            self.assertEqual(self.check(right=right).passed, not mismatch)
            assert_frame_equal(self.left, before_left, check_exact=True)
            assert_frame_equal(right, before_right, check_exact=True)

    def test_t22_diagnostics_do_not_echo_records(self):
        self.left.loc[0, "group"] = "PRIVATE_SYNTHETIC_KEY"
        self.left["payload"] = ["PRIVATE_DESCRIPTION"] * 2
        self.left.index = ["PRIVATE_ROW_LABEL", "SECOND_ROW"]
        result = self.check()
        self.assert_fail(result, "LEFT_ONLY_KEYS")
        for secret in ("PRIVATE_SYNTHETIC_KEY", "PRIVATE_DESCRIPTION", "PRIVATE_ROW_LABEL", "SECOND_ROW"):
            self.assertNotIn(secret, repr(result))

    def test_t23_pass_is_not_production_acceptance(self):
        self.left["accepted"] = self.right["accepted"] = True
        self.assertTrue(self.check().passed)
        self.assertFalse(hasattr(self.check(), "production_eligible"))
        self.assertEqual(real_artifact_status(exists=True), "BLOCKED")

    def test_t24_all_jobs_is_not_it_population(self):
        self.left["scope"] = "ALL_JOBS"
        self.right["scope"] = "IT_ACCEPT"
        self.assert_fail(self.check(), "CONTEXT_MISMATCH", "both", ("scope", "scope"))

    def test_boolean_integer_float_and_string_keys_never_cross_match(self):
        for incompatible in (True, 1.0, Decimal("1"), Fraction(1), "1"):
            frame = self.right.astype({"part": object})
            frame["part"] = [incompatible, incompatible]
            result = self.check(right=frame)
            self.assert_fail(result, "LEFT_ONLY_KEYS")
            self.assert_fail(result, "RIGHT_ONLY_KEYS")

    def test_numpy_nullable_scalars_within_family_match(self):
        frame = self.right.astype({"group": "string", "part": "Int64", "count": "Int64"})
        self.assertTrue(self.check(right=frame).passed)
        frame = self.right.astype({"count": object})
        frame["count"] = [Decimal("100"), np.int64(20)]
        self.assertTrue(self.check(right=frame).passed)

    def test_multiple_metrics_checked_and_unmapped_values_ignored(self):
        self.left["second"] = [10, 20]
        self.right["other"] = [10, 21]
        self.right["unrelated"] = [999, 999]
        spec = replace(self.spec, metric_pairs=(("count", "count"), ("second", "other")))
        result = self.check(spec=spec)
        self.assert_fail(result, "COUNT_MISMATCH", "both", ("second", "other"))
        self.assertEqual(result.compared_metric_count, 4)
        self.right.loc[1, "other"] = 20
        self.assertTrue(self.check(spec=spec).passed)

    def test_missing_input_and_invalid_spec(self):
        self.assert_fail(validate_cross_table_contract(None, self.right, self.spec), "MISSING_INPUT", "left")
        self.assert_fail(validate_cross_table_contract(self.left, [], self.spec), "INVALID_INPUT", "right")
        for spec in (None, {}, replace(self.spec, key_pairs=()), replace(self.spec, metric_pairs=()),
                     replace(self.spec, context_pairs=None), replace(self.spec, key_pairs=(([], "part"),)),
                     replace(self.spec, key_pairs=(("group", "group"), ("group", "part"))),
                     replace(self.spec, allow_empty="yes"), replace(self.spec, require_exact_key_set=False)):
            self.assert_fail(self.check(spec=spec) if spec is not None else
                             validate_cross_table_contract(self.left, self.right, None), "INVALID_SPEC")

    def test_signaling_nan_rejection_preserves_decimal_context(self):
        ctx = getcontext()
        before = (ctx.prec, ctx.rounding, dict(ctx.traps), dict(ctx.flags))
        for field, code in (("part", "INVALID_KEY"), ("run", "INVALID_CONTEXT"), ("count", "INVALID_COUNT")):
            frame = self.left.astype({field: object})
            marker = Decimal("sNaN123")
            frame.at[0, field] = marker
            self.assert_fail(self.check(left=frame), code, "left")
            self.assertIs(frame.at[0, field], marker)
        self.assertEqual(before, (ctx.prec, ctx.rounding, dict(ctx.traps), dict(ctx.flags)))

    def test_declared_context_type_and_key_context_overlap(self):
        self.left["run"] = 1
        self.right["run"] = True
        self.assert_fail(self.check(), "CONTEXT_MISMATCH")
        self.right["run"] = 1
        spec = replace(self.spec, key_pairs=self.spec.key_pairs + (("run", "run"),))
        self.assertTrue(self.check(spec=spec).passed)

    def test_oversized_numeric_and_malformed_column_names(self):
        for field, code in (("part", "INVALID_KEY"), ("count", "INVALID_COUNT")):
            frame = self.left.astype({field: object})
            frame.at[0, field] = 1 << 20000
            self.assert_fail(self.check(left=frame), code)
        frame = self.left.copy()
        frame.columns = pd.Index([0, 1, 2, 3, 4])
        self.assert_fail(self.check(left=frame), "INVALID_COLUMNS")


    def string_fixture(self, field, value, side="left"):
        frame = getattr(self, side).astype({field: object})
        frame.at[0, field] = value
        self.assertIs(type(frame.at[0, field]), type(value))
        self.assertIs(frame.at[0, field], value)
        return frame

    def test_f01_aliased_string_key_rejected(self):
        class AliasedString(str):
            def __str__(self):
                return "DEMO_MATCH"
        frame = self.string_fixture("group", AliasedString("DIFFERENT_KEY"))
        right = self.right.copy(deep=True)
        right.loc[0, "group"] = "DEMO_MATCH"
        result = self.check(frame, right)
        self.assert_fail(result, "INVALID_KEY", "left", ("group",))
        self.assertEqual(result.left_key_count, 1)
        self.assertEqual(result.compared_metric_count, 1)

    def test_f02_aliased_string_context_rejected(self):
        class AliasedString(str):
            def __str__(self):
                return "DEMO_MATCH"
        frame = self.string_fixture("scope", AliasedString("DIFFERENT_CONTEXT"))
        right = self.right.copy(deep=True)
        right.loc[0, "scope"] = "DEMO_MATCH"
        result = self.check(frame, right)
        self.assert_fail(result, "INVALID_CONTEXT", "left", ("scope",))
        self.assertEqual(result.compared_metric_count, 1)

    def test_f03_raising_string_key_controlled_failure(self):
        class RaisingString(str):
            def __str__(self):
                raise ValueError("synthetic error")
        frame = self.string_fixture("group", RaisingString("KEY"))
        self.assert_fail(self.check(left=frame), "INVALID_KEY", "left", ("group",))

    def test_f04_raising_string_context_controlled_failure(self):
        class RaisingString(str):
            def __str__(self):
                raise ValueError("synthetic error")
        frame = self.string_fixture("run", RaisingString("CONTEXT"))
        self.assert_fail(self.check(left=frame), "INVALID_CONTEXT", "left", ("run",))

    def test_f05_builtin_strings_match(self):
        self.assertIs(type(self.left.at[0, "group"]), str)
        result = self.check()
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())

    def test_f06_builtin_strings_differ(self):
        self.right.loc[0, "group"] = "DIFFERENT_BUILTIN_KEY"
        result = self.check()
        self.assert_fail(result, "LEFT_ONLY_KEYS")
        self.assert_fail(result, "RIGHT_ONLY_KEYS")

    def test_f07_exact_numpy_strings_remain_compatible(self):
        frame = self.string_fixture("group", np.str_("DEMO_A"))
        frame.at[0, "run"] = np.str_("RUN_DEMO")
        self.assertIs(type(frame.at[0, "run"]), np.str_)
        result = self.check(left=frame)
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())

    def test_f08_numeric_identity_unchanged(self):
        for left_value, right_value, matches in (
            (True, 1, False), (1, 1.0, False), (Decimal("1"), 1.0, False),
            (1, np.int64(1), True), (0.5, np.float64(0.5), True),
        ):
            left = self.left.astype({"part": object})
            right = self.right.astype({"part": object})
            left.at[0, "part"], right.at[0, "part"] = left_value, right_value
            result = self.check(left, right)
            self.assertEqual(result.passed, matches)
            if matches:
                self.assertEqual(result.errors, ())
            else:
                self.assert_fail(result, "LEFT_ONLY_KEYS")
                self.assert_fail(result, "RIGHT_ONLY_KEYS")

    def test_f09_unsupported_string_inside_composite_key(self):
        class UnsupportedString(str):
            pass
        frame = self.string_fixture("run", UnsupportedString("RUN_DEMO"))
        spec = replace(self.spec, key_pairs=self.spec.key_pairs + (("run", "run"),))
        result = self.check(left=frame, spec=spec)
        self.assert_fail(result, "INVALID_KEY", "left", ("run",))
        self.assert_fail(result, "INVALID_CONTEXT", "left", ("run",))

    def test_f10_one_unsupported_string_invalidates_all_results(self):
        class UnsupportedString(str):
            pass
        for side in ("left", "right"):
            frame = self.string_fixture("group", UnsupportedString("DEMO_A"), side)
            result = self.check(**{side: frame})
            self.assert_fail(result, "INVALID_KEY", side)
            self.assertEqual((result.left_checked_rows, result.right_checked_rows), (2, 2))
            self.assertEqual(result.matched_key_count, 1)

    def test_f11_rejected_string_hooks_never_run_or_leak(self):
        class HookTrapString(str):
            def forbidden(self, *args):
                raise AssertionError("PRIVATE_SYNTHETIC_HOOK_PAYLOAD")
            __str__ = forbidden
            __eq__ = forbidden
            __hash__ = forbidden
            __repr__ = forbidden
        for field, code in (("group", "INVALID_KEY"), ("scope", "INVALID_CONTEXT")):
            frame = self.string_fixture(field, HookTrapString("PRIVATE_SYNTHETIC_VALUE"))
            frame.index = ["PRIVATE_ROW_LABEL", "OTHER_PRIVATE_LABEL"]
            result = self.check(left=frame)
            self.assert_fail(result, code, "left", (field,))
            for secret in ("PRIVATE_SYNTHETIC_VALUE", "PRIVATE_SYNTHETIC_HOOK_PAYLOAD", "PRIVATE_ROW_LABEL", "OTHER_PRIVATE_LABEL"):
                self.assertNotIn(secret, repr(result))

    def test_f12_inputs_and_unsupported_object_identity_preserved(self):
        class UnsupportedString(str):
            pass
        for side in ("left", "right"):
            marker = UnsupportedString("PRIVATE_SYNTHETIC_VALUE")
            frame = self.string_fixture("group", marker, side)
            frame.index = pd.Index([7, 7], name="synthetic_index")
            left = frame if side == "left" else self.left
            right = frame if side == "right" else self.right
            before_left, before_right = left.copy(deep=True), right.copy(deep=True)
            result = self.check(left, right)
            self.assert_fail(result, "INVALID_KEY", side)
            assert_frame_equal(left, before_left, check_exact=True)
            assert_frame_equal(right, before_right, check_exact=True)
            self.assertIs(frame.iloc[0]["group"], marker)
            self.assertIs(type(frame.iloc[0]["group"]), UnsupportedString)


if __name__ == "__main__":
    unittest.main(verbosity=2)
