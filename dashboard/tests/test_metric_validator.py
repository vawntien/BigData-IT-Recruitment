"""Tiny synthetic metric fixtures; no accepted business spec or real records."""

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
from components.metric_validator import MetricValidationSpec, validate_metric_contract
from components.artifact_gate import real_artifact_status


class MetricValidatorTests(unittest.TestCase):
    def setUp(self):
        self.spec = MetricValidationSpec(
            numerator_column="demo_n", denominator_column="demo_d", rate_column="demo_rate",
            rate_unit="FRACTION", zero_denominator_policy="NULL",
            tolerance=Decimal("0.000000001"), subset_of_population=True,
        )

    def frame(self, rows):
        # Preserve individual synthetic scalar representations for rejection tests.
        return pd.DataFrame(rows, columns=["demo_n", "demo_d", "demo_rate"], dtype=object)

    def check(self, rows, spec=None):
        return validate_metric_contract(self.frame(rows), self.spec if spec is None else spec)

    def assert_fail(self, result, code, fields=None):
        self.assertFalse(result.passed)
        matching = [error for error in result.errors if error.code == code]
        self.assertTrue(matching, result)
        if fields is not None:
            self.assertTrue(any(error.fields == fields for error in matching), result)

    def test_t01_valid_fraction(self):
        result = self.check([(40, 100, 0.4)])
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())
        self.assertEqual(result.row_count, 1)

    def test_t02_valid_zero_numerator(self):
        self.assertTrue(self.check([(0, 100, 0)]).passed)

    def test_t03_valid_full_population(self):
        self.assertTrue(self.check([(100, 100, 1)]).passed)

    def test_t04_subset_relation_must_be_explicit(self):
        self.assert_fail(self.check([(101, 100, 1.01)]), "NUMERATOR_EXCEEDS_DENOMINATOR", ("demo_n", "demo_d"))
        self.assertTrue(self.check([(101, 100, 1.01)], replace(self.spec, subset_of_population=False)).passed)

    def test_t05_negative_numerator(self):
        self.assert_fail(self.check([(-1, 100, 0)]), "INVALID_NUMERATOR", ("demo_n",))

    def test_t06_negative_denominator(self):
        self.assert_fail(self.check([(1, -100, 0)]), "INVALID_DENOMINATOR", ("demo_d",))

    def test_t07_fractional_boolean_and_string_counts(self):
        for bad in (0.5, True, False, np.bool_(True), "40", Decimal("1.2")):
            for index, code in ((0, "INVALID_NUMERATOR"), (1, "INVALID_DENOMINATOR")):
                with self.subTest(type=type(bad).__name__, field=index):
                    row = [40, 100, 0.4]
                    row[index] = bad
                    self.assert_fail(self.check([row]), code)

    def test_t08_nonfinite_and_null_counts(self):
        for bad in (None, pd.NA, float("nan"), float("inf"), -float("inf"), Decimal("NaN"), Decimal("Infinity")):
            for index, code in ((0, "INVALID_NUMERATOR"), (1, "INVALID_DENOMINATOR")):
                row = [40, 100, 0.4]
                row[index] = bad
                self.assert_fail(self.check([row]), code)

    def test_t09_zero_over_zero_requires_declared_null_policy(self):
        for null in (None, pd.NA, float("nan"), Decimal("NaN"), pd.NaT):
            self.assertTrue(self.check([(0, 0, null)]).passed)
        self.assert_fail(self.check([(0, 0, None)], replace(self.spec, zero_denominator_policy="REJECT")),
                         "ZERO_DENOMINATOR_REJECTED")

    def test_t10_undefined_rate_cannot_be_zero_or_one(self):
        for rate in (0, 1, Decimal("0")):
            self.assert_fail(self.check([(0, 0, rate)]), "UNDEFINED_RATE_REQUIRED", ("demo_rate",))

    def test_t11_positive_numerator_zero_denominator_always_fails(self):
        for subset in (False, True):
            self.assert_fail(self.check([(1, 0, None)], replace(self.spec, subset_of_population=subset)),
                             "INCONSISTENT_ZERO_DENOMINATOR")

    def test_t12_percentage_value_rejected_as_fraction(self):
        result = self.check([(40, 100, 40)])
        self.assert_fail(result, "RATE_OUT_OF_RANGE", ("demo_rate",))
        self.assert_fail(result, "RATE_INCONSISTENT")

    def test_t13_explicit_absolute_tolerance(self):
        spec = replace(self.spec, tolerance=Decimal("0.001"))
        self.assertTrue(self.check([(40, 100, Decimal("0.401"))], spec).passed)
        self.assert_fail(self.check([(40, 100, Decimal("0.4010001"))], spec), "RATE_INCONSISTENT")
        self.assertTrue(self.check([(40, 100, Decimal("0.4"))], replace(spec, tolerance=0)).passed)

    def test_t14_inconsistent_rate(self):
        self.assert_fail(self.check([(40, 100, 0.5)]), "RATE_INCONSISTENT", ("demo_n", "demo_d", "demo_rate"))

    def test_t15_positive_denominator_requires_rate(self):
        for null in (None, pd.NA, float("nan"), Decimal("NaN")):
            self.assert_fail(self.check([(40, 100, null)]), "INVALID_RATE", ("demo_rate",))

    def test_t16_invalid_rate_representations(self):
        for bad in (float("nan"), float("inf"), -float("inf"), Decimal("Infinity"), True, np.bool_(False), "0.4", [0.4], complex(0.4)):
            self.assert_fail(self.check([(40, 100, bad)]), "INVALID_RATE")
        for bad in (float("inf"), Decimal("Infinity")):
            self.assert_fail(self.check([(0, 0, bad)]), "INVALID_RATE")

    def test_t17_every_row_checked_without_group_aggregation(self):
        frame = self.frame([(40, 100, 0.4), (40, 100, 0.5), (0, 0, None), (40, 100, None), (20, 100, 0.4)])
        frame["group"] = ["DEMO"] * len(frame)
        result = validate_metric_contract(frame, self.spec)
        self.assert_fail(result, "RATE_INCONSISTENT")
        self.assert_fail(result, "INVALID_RATE")
        inconsistent = next(e for e in result.errors if e.code == "RATE_INCONSISTENT")
        self.assertIn("2 violation(s)", inconsistent.detail)
        self.assertEqual(result.row_count, 5)

    def test_t18_no_input_mutation(self):
        for rows, passed in [([(40, 100, 0.4), (0, 0, None)], True), ([(40, 100, 0.5)], False)]:
            frame = self.frame(rows)
            frame.index = pd.Index([7] * len(frame), name="synthetic_index")
            before = frame.copy(deep=True)
            result = validate_metric_contract(frame, self.spec)
            self.assertEqual(result.passed, passed)
            assert_frame_equal(frame, before, check_exact=True)

    def test_t19_safe_diagnostics(self):
        frame = self.frame([("PRIVATE_SYNTHETIC_VALUE", 100, "PRIVATE_RATE")])
        frame.index = ["PRIVATE_ROW_LABEL"]
        result = validate_metric_contract(frame, self.spec)
        self.assert_fail(result, "INVALID_NUMERATOR", ("demo_n",))
        for secret in ("PRIVATE_SYNTHETIC_VALUE", "PRIVATE_RATE", "PRIVATE_ROW_LABEL"):
            self.assertNotIn(secret, repr(result))

    def test_t20_no_production_acceptance(self):
        result = self.check([(40, 100, 0.4)])
        self.assertTrue(result.passed)
        self.assertFalse(hasattr(result, "production_eligible"))
        self.assertEqual(real_artifact_status(exists=True), "BLOCKED")

    def test_t21_signaling_decimal_nan_rejected_without_context_changes(self):
        context = getcontext()
        before = (dict(context.traps), dict(context.flags), context.prec, context.rounding)
        for index, code in ((0, "INVALID_NUMERATOR"), (1, "INVALID_DENOMINATOR"), (2, "INVALID_RATE")):
            row = [40, 100, 0.4]
            marker = Decimal("sNaN123")
            row[index] = marker
            frame = self.frame([row])
            result = validate_metric_contract(frame, self.spec)
            self.assert_fail(result, code)
            self.assertIs(frame.iloc[0, index], marker)
            self.assertNotIn("sNaN", repr(result))
        self.assert_fail(self.check([(0, 0, Decimal("sNaN"))]), "INVALID_RATE")
        self.assertEqual(before, (dict(context.traps), dict(context.flags), context.prec, context.rounding))

    def test_t22_invalid_spec_and_missing_fields_are_controlled(self):
        invalid = [None, {}, replace(self.spec, numerator_column=None), replace(self.spec, numerator_column=[]),
                   replace(self.spec, rate_column="demo_n"), replace(self.spec, rate_unit=None),
                   replace(self.spec, zero_denominator_policy="ZERO"), replace(self.spec, subset_of_population=1)]
        for tolerance in (-1, None, True, "0.01", float("inf"), Decimal("sNaN")):
            invalid.append(replace(self.spec, tolerance=tolerance))
        for spec in invalid:
            self.assert_fail(validate_metric_contract(self.frame([(40, 100, 0.4)]), spec), "INVALID_METRIC_SPEC")
        self.assert_fail(validate_metric_contract(pd.DataFrame({"demo_n": [1]}), self.spec),
                         "MISSING_COLUMNS", ("demo_d", "demo_rate"))

    def test_t23_units_cannot_silently_switch(self):
        for unit in ("PERCENTAGE", "PERCENT", "fraction", "", ["FRACTION"]):
            self.assert_fail(self.check([(40, 100, 40)], replace(self.spec, rate_unit=unit)), "INVALID_METRIC_SPEC")
        self.assert_fail(self.check([(40, 100, 40)]), "RATE_INCONSISTENT")

    def test_large_exact_counts_never_need_float_conversion(self):
        huge = 10 ** 1000
        self.assertTrue(self.check([(huge, 2 * huge, Fraction(1, 2))], replace(self.spec, tolerance=0)).passed)
        self.assert_fail(self.check([(huge, huge + 1, 1)], replace(self.spec, tolerance=0)), "RATE_INCONSISTENT")

    def test_computational_bounds_reject_without_overflow(self):
        for bad in (1 << 20000, Decimal("1e1000000000"), Fraction(1, 1 << 20000)):
            self.assert_fail(self.check([(bad, 100, 0.4)]), "INVALID_NUMERATOR")
            self.assert_fail(self.check([(40, 100, bad)]), "INVALID_RATE")

    def test_numpy_and_nullable_storage(self):
        self.assertTrue(self.check([(np.int64(40), np.uint64(100), np.float64(0.4))]).passed)
        self.assertTrue(self.check([(40.0, Decimal("100"), Decimal("0.4"))]).passed)
        frame = pd.DataFrame({"demo_n": pd.Series([40, 0], dtype="Int64"),
                              "demo_d": pd.Series([100, 0], dtype="Int64"),
                              "demo_rate": pd.Series([0.4, pd.NA], dtype="Float64")})
        before = frame.copy(deep=True)
        self.assertTrue(validate_metric_contract(frame, self.spec).passed)
        assert_frame_equal(frame, before)
        frame.loc[0, "demo_n"] = pd.NA
        self.assert_fail(validate_metric_contract(frame, self.spec), "INVALID_NUMERATOR")

    def test_subset_bounds_are_not_relaxed_by_tolerance(self):
        spec = replace(self.spec, tolerance=10)
        self.assert_fail(self.check([(0, 100, -0.001)], spec), "RATE_OUT_OF_RANGE")
        self.assert_fail(self.check([(100, 100, 1.001)], spec), "RATE_OUT_OF_RANGE")

    def test_missing_empty_and_duplicate_columns(self):
        self.assert_fail(validate_metric_contract(None, self.spec), "MISSING_INPUT")
        self.assert_fail(validate_metric_contract([], self.spec), "INVALID_INPUT")
        empty = self.check([])
        self.assertTrue(empty.passed)
        self.assertEqual(empty.row_count, 0)
        frame = self.frame([(40, 100, 0.4)])
        frame = pd.concat([frame, frame[["demo_rate"]]], axis=1)
        self.assert_fail(validate_metric_contract(frame, self.spec), "INVALID_COLUMNS")


    def test_f01_non_subset_negative_within_tolerance(self):
        spec = replace(self.spec, subset_of_population=False)
        result = self.check([(0, 100, Decimal("-0.0000000001"))], spec)
        self.assert_fail(result, "RATE_OUT_OF_RANGE", ("demo_rate",))
        self.assertNotIn("RATE_INCONSISTENT", [error.code for error in result.errors])

    def test_f02_non_subset_negative_outside_tolerance(self):
        result = self.check([(0, 100, Decimal("-0.1"))], replace(self.spec, subset_of_population=False))
        self.assert_fail(result, "RATE_OUT_OF_RANGE", ("demo_rate",))
        self.assert_fail(result, "RATE_INCONSISTENT")

    def test_f03_subset_negative_within_tolerance(self):
        self.assert_fail(self.check([(0, 100, Decimal("-1e-10"))]),
                         "RATE_OUT_OF_RANGE", ("demo_rate",))

    def test_f04_non_subset_zero_rate(self):
        result = self.check([(0, 100, 0)], replace(self.spec, subset_of_population=False))
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())

    def test_f05_negative_zero_is_zero(self):
        for subset in (False, True):
            for zero in (Decimal("-0"), -0.0):
                with self.subTest(subset=subset, type=type(zero).__name__):
                    result = self.check([(0, 100, zero)], replace(self.spec, subset_of_population=subset))
                    self.assertTrue(result.passed)
                    self.assertEqual(result.errors, ())

    def test_f06_non_subset_ratio_above_one(self):
        result = self.check([(150, 100, Decimal("1.5"))], replace(self.spec, subset_of_population=False))
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())

    def test_f07_subset_ratio_above_one(self):
        result = self.check([(150, 100, Decimal("1.5"))])
        self.assert_fail(result, "NUMERATOR_EXCEEDS_DENOMINATOR")
        self.assert_fail(result, "RATE_OUT_OF_RANGE", ("demo_rate",))

    def test_f08_non_subset_negative_with_large_finite_tolerance(self):
        spec = replace(self.spec, subset_of_population=False, tolerance=10 ** 1000)
        result = self.check([(0, 100, Decimal("-1e-10"))], spec)
        self.assert_fail(result, "RATE_OUT_OF_RANGE", ("demo_rate",))
        self.assertNotIn("INVALID_METRIC_SPEC", [error.code for error in result.errors])
        self.assertNotIn("RATE_INCONSISTENT", [error.code for error in result.errors])

    def test_f09_nonnegative_tolerance_boundary_preserved(self):
        for subset in (False, True):
            spec = replace(self.spec, subset_of_population=subset, tolerance=Decimal("0.001"))
            result = self.check([(40, 100, Decimal("0.401"))], spec)
            self.assertTrue(result.passed)
            self.assertEqual(result.errors, ())
            self.assert_fail(self.check([(40, 100, Decimal("0.4010001"))], spec), "RATE_INCONSISTENT")

    def test_f10_negative_rate_input_and_diagnostics_preserved(self):
        marker = Decimal("-0.000000000123456789")
        frame = self.frame([(0, 100, marker)])
        frame.index = pd.Index(["PRIVATE_SYNTHETIC_RATE_ROW"], name="synthetic_index")
        before = frame.copy(deep=True)
        result = validate_metric_contract(frame, replace(self.spec, subset_of_population=False))
        self.assert_fail(result, "RATE_OUT_OF_RANGE", ("demo_rate",))
        assert_frame_equal(frame, before, check_exact=True)
        self.assertNotIn(str(marker), repr(result))
        self.assertNotIn("PRIVATE_SYNTHETIC_RATE_ROW", repr(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
