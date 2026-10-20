"""Illustrative synthetic specs only; no physical Q01-Q08 contract or datasets."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import sys
import unittest

import pandas as pd
import pyarrow as pa
from pandas.testing import assert_frame_equal

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASHBOARD_DIR))

from components.contract_validator import (
    FieldSpec, ValidationSpec, validate_dataset_contract,
)
from components.artifact_gate import real_artifact_status


class ContractValidatorFoundationTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "demo_id": pd.Series(["DEMO_A", "DEMO_A"], dtype="string"),
            "bucket": pd.Series(["X", "Y"], dtype="string"),
            "count": pd.Series([0, 2], dtype="Int64"),
            "value": pd.Series([1.5, 2.5], dtype="Float64"),
            "flag": pd.Series([True, False], dtype="boolean"),
            "when": pd.to_datetime(["2026-01-01", "2026-01-02"], utc=True),
        })
        self.spec = ValidationSpec(
            fields={
                "demo_id": FieldSpec("string", False),
                "bucket": FieldSpec("string", True),
                "count": FieldSpec("integer", False),
                "value": FieldSpec("number", True),
                "flag": FieldSpec("boolean", True),
                "when": FieldSpec("datetime", True),
            },
            required_fields=tuple(self.frame.columns),
            unique_key=("demo_id", "bucket"), count_fields=("count",),
            allow_empty=False, allow_extra_columns=False,
        )

    def validate(self, frame=None, spec=None):
        return validate_dataset_contract(
            self.frame if frame is None else frame,
            self.spec if spec is None else spec,
        )

    def assert_rejected(self, result, code, fields=None):
        self.assertFalse(result.passed)
        matching = [error for error in result.errors if error.code == code]
        self.assertTrue(matching, result)
        if fields is not None:
            self.assertTrue(any(error.fields == fields for error in matching), result)

    def test_t01_valid_schema_and_composite_grain(self):
        result = self.validate()
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())
        self.assertEqual(result.row_count, 2)

    def test_t02_missing_required_column(self):
        self.assert_rejected(self.validate(self.frame.drop(columns="value")),
                             "MISSING_COLUMNS", ("value",))

    def test_t03_wrong_logical_types_are_not_coerced(self):
        for name, bad in [("demo_id", 123), ("count", "2"), ("value", "1.5"),
                          ("flag", 1), ("when", "2026-01-01")]:
            with self.subTest(field=name):
                frame = self.frame.copy()
                frame[name] = pd.Series([bad, bad], dtype=object)
                self.assert_rejected(self.validate(frame), "TYPE_MISMATCH", (name,))

    def test_t04_nonnullable_field_rejects_null(self):
        self.frame.loc[0, "demo_id"] = pd.NA
        self.assert_rejected(self.validate(), "NULL_NOT_ALLOWED", ("demo_id",))

    def test_t05_nullable_nonkey_values_are_preserved(self):
        self.frame.loc[0, ["value", "flag", "when"]] = None
        before = self.frame.copy(deep=True)
        self.assertTrue(self.validate().passed)
        assert_frame_equal(self.frame, before)

    def test_t06_duplicate_composite_key(self):
        self.frame.loc[1, "bucket"] = "X"
        self.assert_rejected(self.validate(), "DUPLICATE_KEY", ("demo_id", "bucket"))

    def test_t07_null_key_rejected_even_when_field_nullable(self):
        self.frame.loc[0, "bucket"] = pd.NA
        self.assert_rejected(self.validate(), "NULL_KEY", ("demo_id", "bucket"))

    def test_t08_negative_count(self):
        self.frame.loc[0, "count"] = -1
        self.assert_rejected(self.validate(), "INVALID_COUNT", ("count",))

    def test_t09_fractional_and_boolean_counts(self):
        for bad in [1.25, True, False, Decimal("2.5")]:
            with self.subTest(value=bad):
                self.frame["count"] = pd.Series([bad, 2], dtype=object)
                self.assert_rejected(self.validate(), "INVALID_COUNT", ("count",))

    def test_t10_counts_reject_nan_infinity_and_missing(self):
        for bad in [float("nan"), float("inf"), -float("inf"), pd.NA, None,
                    Decimal("NaN"), Decimal("Infinity")]:
            with self.subTest(value=bad):
                self.frame["count"] = pd.Series([bad, 2], dtype=object)
                self.assert_rejected(self.validate(), "INVALID_COUNT", ("count",))

    def test_t11_zero_and_integral_numeric_counts(self):
        for values in [[0, 2], [0.0, 2.0], [Decimal("0"), Decimal("2")],
                       [0, 2 ** 100]]:
            with self.subTest(values=values):
                self.frame["count"] = pd.Series(values, dtype=object)
                self.assertTrue(self.validate().passed)

    def test_t12_no_mutation_on_pass_or_failure(self):
        for duplicate in [False, True]:
            frame = self.frame.copy(deep=True)
            if duplicate:
                frame.loc[1, "bucket"] = "X"
            frame.index = pd.Index([7, 7], name="synthetic_index")
            before = frame.copy(deep=True)
            result = self.validate(frame)
            self.assertEqual(result.passed, not duplicate)
            self.assertEqual(result.row_count, len(before))
            assert_frame_equal(frame, before, check_exact=True)

    def test_t13_extra_column_policy_is_explicit(self):
        frame = self.frame.assign(extra="DEMO_ONLY")
        self.assert_rejected(self.validate(frame), "EXTRA_COLUMNS", ("extra",))
        self.assertTrue(self.validate(frame, replace(self.spec, allow_extra_columns=True)).passed)

    def test_t14_empty_policy_is_separate_from_missing(self):
        empty = self.frame.iloc[:0]
        self.assert_rejected(self.validate(empty), "EMPTY_DATASET")
        allowed = replace(self.spec, allow_empty=True)
        result = self.validate(empty, allowed)
        self.assertTrue(result.passed)
        self.assertEqual(result.row_count, 0)
        self.assert_rejected(self.validate(empty.drop(columns="count"), allowed), "MISSING_COLUMNS")
        missing = validate_dataset_contract(None, allowed)
        self.assert_rejected(missing, "MISSING_INPUT")
        self.assertIsNone(missing.row_count)

    def test_t15_nullable_pandas_and_arrow_storage_are_compatible(self):
        self.frame.loc[0, "value"] = pd.NA
        self.frame.loc[0, "flag"] = pd.NA
        self.assertTrue(self.validate().passed)
        arrow_frame = pa.Table.from_pandas(self.frame, preserve_index=False).to_pandas(types_mapper=pd.ArrowDtype)
        before = arrow_frame.copy(deep=True)
        self.assertTrue(self.validate(arrow_frame).passed)
        assert_frame_equal(arrow_frame, before)
        arrow_frame.loc[0, "count"] = pd.NA
        self.assert_rejected(self.validate(arrow_frame), "INVALID_COUNT")

    def test_t16_validation_pass_cannot_open_production(self):
        frame = self.frame.assign(accepted=True, release_status="ACCEPTED_PRODUCTION")
        result = self.validate(frame, replace(self.spec, allow_extra_columns=True))
        self.assertTrue(result.passed)
        self.assertFalse(hasattr(result, "production_eligible"))
        self.assertEqual(real_artifact_status(exists=True), "BLOCKED")
        self.assertEqual(real_artifact_status(exists=True, read_failed=not result.passed), "BLOCKED")

    def test_numeric_finiteness_and_nullable_nan_policy(self):
        for bad in [float("inf"), -float("inf"), Decimal("Infinity")]:
            self.frame["value"] = pd.Series([bad, 1], dtype=object)
            self.assert_rejected(self.validate(), "NON_FINITE", ("value",))
        self.frame["value"] = [float("nan"), 1.0]
        self.assertTrue(self.validate().passed)  # pandas NULL allowed by field policy
        fields = dict(self.spec.fields, value=FieldSpec("number", False))
        self.assert_rejected(self.validate(spec=replace(self.spec, fields=fields)), "NON_FINITE")
        fields["value"] = FieldSpec("number", True, finite=False)
        self.frame["value"] = [float("inf"), 1.0]
        self.assertTrue(self.validate(spec=replace(self.spec, fields=fields)).passed)

    def test_invalid_spec_never_silently_passes(self):
        for spec in [None, replace(self.spec, count_fields=("absent",)),
                     replace(self.spec, unique_key=("bucket", "bucket")),
                     replace(self.spec, required_fields=()),
                     replace(self.spec, fields={"x": FieldSpec("unknown", False)}),
                     replace(self.spec, fields={"x": FieldSpec([], False)}),
                     replace(self.spec, allow_empty="yes"),
                     replace(self.spec, fields=dict(self.spec.fields, count=FieldSpec("number", True)))]:
            self.assert_rejected(validate_dataset_contract(self.frame, spec), "INVALID_SPEC")

    def test_duplicate_column_names_are_rejected(self):
        frame = pd.concat([self.frame, self.frame[["count"]]], axis=1)
        self.assert_rejected(self.validate(frame), "INVALID_COLUMNS")

    def test_optional_fields_are_validated_when_present(self):
        optional = replace(self.spec, required_fields=tuple(c for c in self.frame.columns if c != "value"))
        self.assertTrue(self.validate(self.frame.drop(columns="value"), optional).passed)
        self.frame["value"] = ["bad", "bad"]
        self.assert_rejected(self.validate(spec=optional), "TYPE_MISMATCH")

    def test_bad_nested_key_values_fail_without_crashing(self):
        self.frame["bucket"] = [["X"], ["Y"]]
        self.assert_rejected(self.validate(), "TYPE_MISMATCH", ("bucket",))

    def test_safe_diagnostics_do_not_echo_values_or_row_labels(self):
        self.frame["count"] = ["SYNTHETIC_SECRET", 2]
        self.frame.index = ["SYNTHETIC_ROW_LABEL", "SECOND_ROW"]
        result = self.validate()
        self.assert_rejected(result, "INVALID_COUNT")
        self.assertNotIn("SYNTHETIC_SECRET", repr(result))
        self.assertNotIn("SYNTHETIC_ROW_LABEL", repr(result))

    def test_non_dataframe_is_distinct_from_missing(self):
        self.assert_rejected(validate_dataset_contract([], self.spec), "INVALID_INPUT")

    def test_f01_signaling_nan_nonnullable_number(self):
        self.frame["value"] = pd.Series([Decimal("sNaN"), Decimal("1.5")], dtype=object)
        fields = dict(self.spec.fields, value=FieldSpec("number", False))
        result = self.validate(spec=replace(self.spec, fields=fields))
        self.assert_rejected(result, "NON_FINITE", ("value",))
        self.assert_rejected(result, "TYPE_MISMATCH", ("value",))
        self.assertNotIn("NULL_NOT_ALLOWED", [error.code for error in result.errors])

    def test_f02_signaling_nan_nullable_number_is_not_null(self):
        self.frame["value"] = pd.Series([Decimal("sNaN"), Decimal("1.5")], dtype=object)
        for finite in (True, False):
            with self.subTest(finite=finite):
                fields = dict(self.spec.fields, value=FieldSpec("number", True, finite=finite))
                result = self.validate(spec=replace(self.spec, fields=fields))
                self.assert_rejected(result, "TYPE_MISMATCH", ("value",))
                self.assertNotIn("NULL_NOT_ALLOWED", [error.code for error in result.errors])

    def test_f03_signaling_nan_integer_and_key(self):
        self.frame["value"] = pd.Series([Decimal("sNaN"), Decimal("2")], dtype=object)
        for nullable in (True, False):
            fields = dict(self.spec.fields, value=FieldSpec("integer", nullable))
            result = self.validate(spec=replace(self.spec, fields=fields, unique_key=("value",)))
            self.assert_rejected(result, "TYPE_MISMATCH", ("value",))
            self.assert_rejected(result, "NON_FINITE", ("value",))
            self.assertNotIn("NULL_KEY", [error.code for error in result.errors])

    def test_f04_signaling_nan_configured_count(self):
        self.frame["count"] = pd.Series([Decimal("sNaN"), Decimal("2")], dtype=object)
        for logical in ("integer", "number"):
            fields = dict(self.spec.fields, count=FieldSpec(logical, False))
            result = self.validate(spec=replace(self.spec, fields=fields))
            self.assert_rejected(result, "INVALID_COUNT", ("count",))
            self.assert_rejected(result, "NON_FINITE", ("count",))

    def test_f05_quiet_nan_and_missing_policies_unchanged(self):
        for missing in (None, pd.NA, float("nan"), Decimal("NaN")):
            self.frame["value"] = pd.Series([missing, Decimal("2.5")], dtype=object)
            allowed = self.validate()
            self.assertTrue(allowed.passed)
            self.assertEqual(allowed.errors, ())
            fields = dict(self.spec.fields, value=FieldSpec("number", False))
            self.assert_rejected(self.validate(spec=replace(self.spec, fields=fields)),
                                 "NULL_NOT_ALLOWED", ("value",))

    def test_f06_valid_decimal_integer_and_numeric_values(self):
        self.frame["count"] = pd.Series([Decimal("0"), Decimal("2")], dtype=object)
        for values in ([Decimal("1.25"), Decimal("-2.5")], [1, 2.5]):
            self.frame["value"] = pd.Series(values, dtype=object)
            result = self.validate()
            self.assertTrue(result.passed)
            self.assertEqual(result.errors, ())

    def test_f07_signaling_nan_input_preserved_without_nan_comparison(self):
        self.frame["value"] = pd.Series([Decimal("sNaN"), Decimal("1.5")], dtype=object)
        self.frame.index = pd.Index([7, 7], name="synthetic_index")
        before = self.frame.copy(deep=True)
        result = self.validate(spec=replace(self.spec, unique_key=("value",)))
        self.assert_rejected(result, "TYPE_MISMATCH", ("value",))
        self.assertEqual(result.row_count, len(before))
        # pandas equality itself traps on sNaN; use identity for that immutable scalar.
        self.assertIs(self.frame.iloc[0]["value"], before.iloc[0]["value"])
        self.assertTrue(self.frame.iloc[0]["value"].is_snan())
        self.assertEqual(self.frame.iloc[1]["value"], before.iloc[1]["value"])
        self.assertEqual(self.frame["value"].dtype, before["value"].dtype)
        pd.testing.assert_index_equal(self.frame.index, before.index)
        pd.testing.assert_index_equal(self.frame.columns, before.columns)
        assert_frame_equal(self.frame.drop(columns="value"), before.drop(columns="value"))

    def test_f08_signaling_nan_diagnostics_do_not_echo_values(self):
        self.frame["count"] = pd.Series([Decimal("sNaN123"), Decimal("2")], dtype=object)
        self.frame.index = ["PRIVATE_SYNTHETIC_LABEL", "SECOND_LABEL"]
        result = self.validate()
        self.assert_rejected(result, "INVALID_COUNT", ("count",))
        self.assertNotIn("sNaN", repr(result))
        self.assertNotIn("PRIVATE_SYNTHETIC_LABEL", repr(result))
        self.assertNotIn("SECOND_LABEL", repr(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
