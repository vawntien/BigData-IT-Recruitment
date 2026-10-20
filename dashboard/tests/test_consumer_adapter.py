"""In-memory synthetic envelope tests; no accepted analytics or UI payload."""

from dataclasses import FrozenInstanceError, asdict, fields, replace
from decimal import Decimal, getcontext
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.consumer_adapter import build_synthetic_consumer_envelope
from components.contract_validator import (
    FieldSpec, ValidationSpec, ValidationIssue, ValidationResult, validate_dataset_contract,
)
from components.artifact_gate import (
    STATUS_SAMPLE, STATUS_BLOCKED, STATUS_INVALID, STATUS_MISSING, real_artifact_status,
)


class ConsumerAdapterTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "demo_id": ["A", "A"], "bucket": ["X", "Y"],
            "count": [0, 2], "value": [1.5, 2.5],
            "origin": [STATUS_SAMPLE, STATUS_SAMPLE],
        }, dtype=object)
        self.spec = ValidationSpec(
            fields={"demo_id": FieldSpec("string", False),
                    "bucket": FieldSpec("string", False),
                    "count": FieldSpec("integer", False),
                    "value": FieldSpec("number", True),
                    "origin": FieldSpec("string", False)},
            required_fields=tuple(self.frame.columns), unique_key=("demo_id", "bucket"),
            count_fields=("count",), allow_empty=False, allow_extra_columns=False,
        )

    def build(self, **overrides):
        arguments = dict(dataframe=self.frame, schema_spec=self.spec,
                         explicit_origin=STATUS_SAMPLE, demo_enabled=True, origin_column="origin")
        arguments.update(overrides)
        return build_synthetic_consumer_envelope(**arguments)

    def rejected(self, result, code, stage=None, field_ids=None, status=STATUS_INVALID):
        self.assertEqual(result.status, status)
        self.assertFalse(result.demo_candidate)
        self.assertTrue(any(issue.code == code and (stage is None or issue.stage == stage)
                            and (field_ids is None or issue.fields == field_ids)
                            for issue in result.structured_issues), result)

    def marker_frame(self, field, marker):
        frame = self.frame.copy(deep=True).astype({field: object})
        values = np.empty(len(frame), dtype=object)
        for i, value in enumerate(frame[field]):
            values[i] = value
        values[0] = marker
        frame[field] = pd.Series(values, dtype=object)
        self.assertIs(type(frame.at[0, field]), type(marker))
        self.assertIs(frame.at[0, field], marker)
        return frame

    def test_t01_explicit_valid_synthetic_candidate(self):
        result = self.build()
        self.assertEqual(result.status, STATUS_SAMPLE)
        self.assertIs(result.schema_valid, True)
        self.assertIs(result.demo_candidate, True)
        self.assertEqual(result.row_count, 2)
        self.assertEqual(result.structured_issues, ())

    def test_t02_disabled_demo(self):
        with patch("components.consumer_adapter.validate_dataset_contract") as validator:
            result = self.build(demo_enabled=False)
            validator.assert_not_called()
        self.rejected(result, "DEMO_DISABLED", "origin", status=STATUS_BLOCKED)
        self.assertIsNone(result.schema_valid)

    def test_t03_exact_boolean_required(self):
        for value in (1, 0, "true", None, np.bool_(True), [], pd.NA):
            with patch("components.consumer_adapter.validate_dataset_contract") as validator:
                result = self.build(demo_enabled=value)
                validator.assert_not_called()
            self.rejected(result, "INVALID_DEMO_FLAG", "configuration")

    def test_t04_unknown_explicit_origin(self):
        self.rejected(self.build(explicit_origin="UNKNOWN"), "ORIGIN_BLOCKED", status=STATUS_BLOCKED)

    def test_t05_real_origin(self):
        self.rejected(self.build(explicit_origin="REAL"), "ORIGIN_BLOCKED", status=STATUS_BLOCKED)

    def test_t06_staging_unverified_origin(self):
        for origin in ("STAGING", "REAL_STAGING", "UNVERIFIED_ARTIFACT", "PRODUCTION", "ACCEPTED_PRODUCTION"):
            self.rejected(self.build(explicit_origin=origin), "ORIGIN_BLOCKED", status=STATUS_BLOCKED)

    def test_t07_missing_dataframe(self):
        result = self.build(dataframe=None)
        self.rejected(result, "MISSING_INPUT", "input", status=STATUS_MISSING)
        self.assertIsNone(result.row_count)
        self.assertIsNone(result.schema_valid)

    def test_t08_wrong_input_type(self):
        for frame in ([], {}, "PRIVATE_INPUT", np.array([1])):
            self.rejected(self.build(dataframe=frame), "INVALID_INPUT", "input")

    def test_t09_required_column_missing(self):
        result = self.build(dataframe=self.frame.drop(columns="count"))
        self.rejected(result, "MISSING_COLUMNS", "schema", ("count",))
        self.assertIs(result.schema_valid, False)

    def test_t10_wrong_logical_type(self):
        self.rejected(self.build(dataframe=self.marker_frame("value", "PRIVATE_VALUE")),
                      "TYPE_MISMATCH", "schema", ("value",))

    def test_t11_null_violation(self):
        for null in (None, pd.NA, pd.NaT, float("nan")):
            self.rejected(self.build(dataframe=self.marker_frame("demo_id", null)),
                          "NULL_NOT_ALLOWED", "schema", ("demo_id",))

    def test_t12_duplicate_composite_key(self):
        self.frame.at[1, "bucket"] = "X"
        self.rejected(self.build(), "DUPLICATE_KEY", "schema", ("demo_id", "bucket"))

    def test_t13_invalid_counts(self):
        for bad in (-1, 1.25, Decimal("2.5"), True, np.bool_(False), "2"):
            self.rejected(self.build(dataframe=self.marker_frame("count", bad)),
                          "INVALID_COUNT", "schema", ("count",))

    def test_t14_nonfinite_counts(self):
        for bad in (float("nan"), float("inf"), -float("inf"), Decimal("Infinity"), pd.NA):
            self.rejected(self.build(dataframe=self.marker_frame("count", bad)), "INVALID_COUNT", "schema")

    def test_t15_unsupported_schema_specification(self):
        for spec in (None, {}, [], "PRIVATE_SPEC"):
            self.rejected(self.build(schema_spec=spec), "INVALID_SPEC", "schema")
        for spec in (replace(self.spec, count_fields=("absent",)),
                     replace(self.spec, unique_key=("bucket", "bucket")),
                     replace(self.spec, allow_empty="yes"),
                     replace(self.spec, fields={"x": FieldSpec("unsupported", False)})):
            result = self.build(schema_spec=spec)
            self.rejected(result, "INVALID_SPEC", "schema")
            self.assertIs(result.schema_valid, False)

    def test_t16_missing_origin_column(self):
        result = self.build(dataframe=self.frame.drop(columns="origin"))
        self.rejected(result, "MISSING_ORIGIN_COLUMN", "origin", ("origin",))
        self.assertIsNone(result.schema_valid)

    def test_t17_single_mismatched_marker(self):
        result = self.build(dataframe=self.marker_frame("origin", "SAMPLE"))
        self.rejected(result, "INVALID_ORIGIN_MARKER", "origin", ("origin",))
        self.assertEqual(result.structured_issues[0].violation_count, 1)

    def test_t18_mixed_real_synthetic_markers(self):
        with patch("components.consumer_adapter.validate_dataset_contract") as validator:
            result = self.build(dataframe=self.marker_frame("origin", "REAL"))
            validator.assert_not_called()
        self.rejected(result, "INVALID_ORIGIN_MARKER", "origin")

    def test_t19_null_unsupported_origin_marker(self):
        for value in (None, pd.NA, pd.NaT, float("nan"), [STATUS_SAMPLE], {"origin": STATUS_SAMPLE}, 1, True):
            self.rejected(self.build(dataframe=self.marker_frame("origin", value)), "INVALID_ORIGIN_MARKER", "origin")

    def test_t20_empty_input_is_never_demo_candidate(self):
        frame = self.frame.iloc[:0]
        self.rejected(self.build(dataframe=frame), "EMPTY_DATASET", "schema")
        result = self.build(dataframe=frame, schema_spec=replace(self.spec, allow_empty=True))
        self.rejected(result, "EMPTY_SYNTHETIC_INPUT", "availability", status=STATUS_BLOCKED)
        self.assertIs(result.schema_valid, True)
        self.assertEqual(result.row_count, 0)

    def test_t21_input_unchanged(self):
        for invalid in (False, True):
            frame = self.frame.copy(deep=True)
            frame.index = pd.Index([7, 7], name="PRIVATE_INDEX")
            if invalid:
                frame.at[7, "count"] = -1
            before = frame.copy(deep=True)
            self.assertEqual(self.build(dataframe=frame).demo_candidate, not invalid)
            assert_frame_equal(frame, before, check_exact=True)

    def test_t22_metadata_only_frozen_result(self):
        result = self.build()
        self.assertEqual({field.name for field in fields(result)},
                         {"status", "schema_valid", "demo_candidate", "row_count", "structured_issues"})
        self.assertFalse(any(isinstance(value, (pd.DataFrame, pd.Series)) for value in asdict(result).values()))
        with self.assertRaises(FrozenInstanceError):
            result.demo_candidate = False
        with self.assertRaises((AttributeError, TypeError)):
            result.payload = self.frame

    def test_t23_diagnostics_never_echo_records(self):
        frame = self.marker_frame("count", "PRIVATE_COUNT")
        frame.index = ["PRIVATE_ROW_1", "PRIVATE_ROW_2"]
        frame["PRIVATE_UNDECLARED_COLUMN"] = "PRIVATE_DESCRIPTION"
        result = self.build(dataframe=frame)
        self.rejected(result, "INVALID_COUNT")
        self.rejected(result, "EXTRA_COLUMNS", field_ids=())
        for secret in ("PRIVATE_COUNT", "PRIVATE_ROW_1", "PRIVATE_ROW_2", "PRIVATE_DESCRIPTION", "PRIVATE_UNDECLARED_COLUMN"):
            self.assertNotIn(secret, repr(result))
        self.assertTrue(all(issue.violation_count is None for issue in result.structured_issues))

    def test_t24_no_production_authorization(self):
        for result in (self.build(), self.build(demo_enabled=False), self.build(dataframe=None)):
            self.assertNotIn(result.status, ("PRODUCTION", "ACCEPTED_PRODUCTION"))
            self.assertFalse(hasattr(result, "production_eligible"))
            self.assertFalse(hasattr(result, "accepted"))
        self.assertEqual(real_artifact_status(exists=True), STATUS_BLOCKED)

    def test_t25_repeatable_outcomes(self):
        self.assertEqual(self.build(), self.build())
        frame = self.marker_frame("count", -1)
        self.assertEqual(self.build(dataframe=frame), self.build(dataframe=frame))
        self.assertEqual(self.build(explicit_origin="REAL"), self.build(explicit_origin="REAL"))

    def test_t26_synthetic_marker_cannot_hide_bad_schema(self):
        result = self.build(dataframe=self.frame.drop(columns="bucket"))
        self.rejected(result, "MISSING_COLUMNS", "schema", ("bucket",))
        self.assertIs(result.schema_valid, False)

    def test_t27_forged_marker_cannot_authorize_real(self):
        with patch("components.consumer_adapter.validate_dataset_contract") as validator:
            result = self.build(explicit_origin="REAL")
            validator.assert_not_called()
        self.rejected(result, "ORIGIN_BLOCKED", status=STATUS_BLOCKED)
        self.assertIsNone(result.schema_valid)

    def test_t28_unsupported_scalar_and_signaling_nan(self):
        context = getcontext()
        before = (context.prec, context.rounding, dict(context.traps), dict(context.flags))
        for value in (Decimal("sNaN123"), [1], {"nested": 1}, object()):
            frame = self.marker_frame("count", value)
            result = self.build(dataframe=frame)
            self.rejected(result, "INVALID_COUNT", "schema", ("count",))
            self.assertIs(result.schema_valid, False)
            self.assertIs(frame.at[0, "count"], value)
        self.assertEqual(before, (context.prec, context.rounding, dict(context.traps), dict(context.flags)))

    def test_published_validator_is_called_with_original_arguments(self):
        with patch("components.consumer_adapter.validate_dataset_contract", wraps=validate_dataset_contract) as validator:
            result = self.build()
            validator.assert_called_once()
            self.assertIs(validator.call_args.args[0], self.frame)
            self.assertIs(validator.call_args.args[1], self.spec)
        self.assertTrue(result.demo_candidate)

    def test_unexpected_validator_exception_explicit_internal_failure(self):
        for exception in (RuntimeError("PRIVATE_RECORD"), AssertionError("PRIVATE_ASSERT"), ValueError("PRIVATE_INDEX")):
            with patch("components.consumer_adapter.validate_dataset_contract", side_effect=exception):
                result = self.build()
            self.rejected(result, "SCHEMA_VALIDATOR_EXCEPTION", "schema")
            self.assertEqual(result.structured_issues[0].category, "internal_failure")
            self.assertIs(result.schema_valid, False)
            self.assertNotIn("PRIVATE", repr(result))

    def test_decimal_context_is_restored_on_validator_exception(self):
        context = getcontext()
        before = (context.prec, dict(context.traps), dict(context.flags))
        def broken_validator(*args):
            getcontext().prec = 7
            Decimal(1) / Decimal(3)
            raise RuntimeError("PRIVATE_ERROR")
        with patch("components.consumer_adapter.validate_dataset_contract", side_effect=broken_validator):
            self.rejected(self.build(), "SCHEMA_VALIDATOR_EXCEPTION")
        self.assertEqual(before, (context.prec, dict(context.traps), dict(context.flags)))

    def test_origin_subclass_hooks_never_run(self):
        class Trap(str):
            def forbidden(self, *args):
                raise AssertionError("PRIVATE_HOOK")
            __str__ = __eq__ = __hash__ = __repr__ = forbidden
        class Alias(str):
            def __str__(self):
                return STATUS_SAMPLE
        for cls in (Trap, Alias):
            marker = cls("PRIVATE_ORIGIN")
            self.rejected(self.build(explicit_origin=marker), "ORIGIN_BLOCKED", status=STATUS_BLOCKED)
            result = self.build(dataframe=self.marker_frame("origin", marker))
            self.rejected(result, "INVALID_ORIGIN_MARKER")
            self.assertNotIn("PRIVATE", repr(result))

    def test_numpy_and_nullable_representations(self):
        frame = self.marker_frame("origin", np.str_(STATUS_SAMPLE))
        self.assertTrue(self.build(dataframe=frame, explicit_origin=np.str_(STATUS_SAMPLE)).demo_candidate)
        frame = self.frame.astype({"demo_id": "string", "bucket": "string", "count": "Int64", "value": "Float64", "origin": "string"})
        frame.at[0, "value"] = pd.NA
        before = frame.copy(deep=True)
        self.assertTrue(self.build(dataframe=frame).demo_candidate)
        assert_frame_equal(frame, before)

    def test_duplicate_column_behavior(self):
        frame = pd.concat([self.frame, self.frame[["count"]]], axis=1)
        result = self.build(dataframe=frame)
        self.rejected(result, "INVALID_COLUMNS", "schema")
        self.assertIs(result.schema_valid, False)
        frame = pd.concat([self.frame, self.frame[["origin"]]], axis=1)
        self.rejected(self.build(dataframe=frame), "AMBIGUOUS_ORIGIN_COLUMN", "origin")

    def test_explicit_alternate_origin_binding(self):
        frame = self.frame.rename(columns={"origin": "demo_source"})
        rules = dict(self.spec.fields)
        rules["demo_source"] = rules.pop("origin")
        spec = replace(self.spec, fields=rules, required_fields=tuple(frame.columns))
        self.assertTrue(self.build(dataframe=frame, schema_spec=spec, origin_column="demo_source").demo_candidate)
        for binding in (None, "", " ", [], 1):
            self.rejected(self.build(origin_column=binding), "INVALID_ORIGIN_BINDING", "configuration")

    def test_missing_and_unsupported_explicit_origin(self):
        for origin in (None, pd.NA, [], 1, True):
            self.rejected(self.build(explicit_origin=origin), "ORIGIN_BLOCKED", status=STATUS_BLOCKED)

    def test_safe_conversion_discards_validator_detail(self):
        validation = ValidationResult(False, (ValidationIssue("INVALID_COUNT", ("count",), "PRIVATE_RAW_DESCRIPTION"),), 2)
        with patch("components.consumer_adapter.validate_dataset_contract", return_value=validation):
            result = self.build()
        self.rejected(result, "INVALID_COUNT", "schema", ("count",))
        self.assertNotIn("PRIVATE_RAW_DESCRIPTION", repr(result))

    def test_malformed_validator_results_fail_closed(self):
        for validation in (None, True, ValidationResult(True, (ValidationIssue("INVALID_COUNT", (), "PRIVATE"),), 2),
                           ValidationResult(False, (), 2),
                           ValidationResult(False, (ValidationIssue("PRIVATE_CODE", (), "PRIVATE"),), 2)):
            with patch("components.consumer_adapter.validate_dataset_contract", return_value=validation):
                result = self.build()
            self.rejected(result, "INVALID_VALIDATOR_RESULT")
            self.assertNotIn("PRIVATE", repr(result))

    def test_all_invalid_markers_counted(self):
        self.frame["origin"] = [None, "REAL"]
        result = self.build()
        self.rejected(result, "INVALID_ORIGIN_MARKER")
        self.assertEqual(result.structured_issues[0].violation_count, 2)

    def test_unsupported_column_names_do_not_invoke_hooks(self):
        class Trap(str):
            def forbidden(self, *args):
                raise RuntimeError("PRIVATE_COLUMN")
            __str__ = __eq__ = __hash__ = __repr__ = forbidden
        frame = self.frame.copy()
        frame.columns = pd.Index([Trap("PRIVATE_COLUMN"), "bucket", "count", "value", "origin"])
        result = self.build(dataframe=frame)
        self.rejected(result, "INVALID_COLUMNS", "input")
        self.assertNotIn("PRIVATE_COLUMN", repr(result))

    def test_finiteness_extra_column_and_mapping_policies_delegated(self):
        from types import MappingProxyType
        self.rejected(self.build(dataframe=self.marker_frame("value", float("inf"))),
                      "NON_FINITE", "schema", ("value",))
        frame = self.frame.assign(extra="PRIVATE_DESCRIPTION")
        result = self.build(dataframe=frame, schema_spec=replace(self.spec, allow_extra_columns=True))
        self.assertTrue(result.demo_candidate)
        self.assertNotIn("PRIVATE_DESCRIPTION", repr(result))
        spec = replace(self.spec, fields=MappingProxyType(self.spec.fields))
        self.assertTrue(self.build(schema_spec=spec).demo_candidate)
        result = self.build(dataframe=self.marker_frame("count", -1), schema_spec=spec)
        self.rejected(result, "INVALID_COUNT", "schema", ("count",))

    def test_empty_input_does_not_bypass_invalid_schema(self):
        spec = replace(self.spec, allow_empty=True, unique_key=("MISSING_KEY",))
        result = self.build(dataframe=self.frame.iloc[:0], schema_spec=spec)
        self.rejected(result, "INVALID_SPEC", "schema")
        self.assertIs(result.schema_valid, False)


    def reject_success_row_count(self, value):
        validation = ValidationResult(True, (), value)
        with patch("components.consumer_adapter.validate_dataset_contract", return_value=validation):
            result = self.build()
        self.rejected(result, "INVALID_VALIDATOR_RESULT", "schema", ())
        self.assertIs(result.schema_valid, False)
        self.assertIs(result.demo_candidate, False)
        self.assertEqual(result.row_count, 2)
        self.assertEqual(len(result.structured_issues), 1)
        self.assertEqual(result.structured_issues[0].category, "internal_failure")
        return result

    def test_f01_success_row_count_zero_rejected(self):
        self.reject_success_row_count(0)

    def test_f02_success_row_count_mismatch_rejected(self):
        self.reject_success_row_count(99)

    def test_f03_success_row_count_none_rejected(self):
        self.reject_success_row_count(None)

    def test_f04_success_row_count_negative_rejected(self):
        self.reject_success_row_count(-1)

    def test_f05_success_row_count_boolean_rejected(self):
        self.reject_success_row_count(True)

    def test_f06_success_row_count_string_rejected(self):
        self.reject_success_row_count("2")

    def test_f07_success_row_count_numpy_integer_rejected(self):
        self.reject_success_row_count(np.int64(2))

    def test_f08_success_exact_integer_matches_input(self):
        count = 2
        self.assertIs(type(count), int)
        with patch("components.consumer_adapter.validate_dataset_contract",
                   return_value=ValidationResult(True, (), count)):
            result = self.build()
        self.assertEqual(result.status, STATUS_SAMPLE)
        self.assertIs(result.schema_valid, True)
        self.assertIs(result.demo_candidate, True)
        self.assertEqual(result.row_count, len(self.frame))
        self.assertEqual(result.structured_issues, ())

    def test_f09_real_published_validator_success_unchanged(self):
        with patch("components.consumer_adapter.validate_dataset_contract",
                   wraps=validate_dataset_contract) as validator:
            result = self.build()
        validator.assert_called_once()
        self.assertIs(validator.call_args.args[0], self.frame)
        self.assertIs(validator.call_args.args[1], self.spec)
        self.assertEqual(result.status, STATUS_SAMPLE)
        self.assertIs(result.schema_valid, True)
        self.assertIs(result.demo_candidate, True)
        self.assertEqual(result.row_count, 2)
        self.assertEqual(result.structured_issues, ())

    def test_f10_failure_row_count_none_preserved(self):
        for code in ("INVALID_SPEC", "INVALID_COUNT"):
            validation = ValidationResult(False, (ValidationIssue(code, (), "PRIVATE_DETAIL"),), None)
            with patch("components.consumer_adapter.validate_dataset_contract", return_value=validation):
                result = self.build()
            self.rejected(result, code, "schema", ())
            self.assertIs(result.schema_valid, False)
            self.assertEqual(result.row_count, 2)
            self.assertEqual(len(result.structured_issues), 1)
            self.assertEqual(result.structured_issues[0].category, "schema_validation")
            self.assertNotIn("PRIVATE_DETAIL", repr(result))
        # The published validator genuinely returns None for invalid specs.
        spec = replace(self.spec, unique_key=("absent",))
        self.assertIsNone(validate_dataset_contract(self.frame, spec).row_count)
        result = self.build(schema_spec=spec)
        self.rejected(result, "INVALID_SPEC", "schema")
        self.assertIs(result.schema_valid, False)

    def test_f11_malformed_success_diagnostics_do_not_leak(self):
        frame = self.frame.copy(deep=True)
        frame["demo_id"] = ["PRIVATE_ID_A", "PRIVATE_ID_B"]
        frame.index = ["PRIVATE_ROW_A", "PRIVATE_ROW_B"]
        with patch("components.consumer_adapter.validate_dataset_contract",
                   return_value=ValidationResult(True, (), "PRIVATE_VALIDATOR_COUNT")):
            result = self.build(dataframe=frame)
        self.rejected(result, "INVALID_VALIDATOR_RESULT", "schema", ())
        self.assertIs(result.schema_valid, False)
        self.assertNotIn("PRIVATE", repr(result))

    def test_f12_input_unchanged_for_valid_and_rejected_success(self):
        for count, candidate in ((2, True), (0, False)):
            frame = self.frame.copy(deep=True)
            frame.index = pd.Index([9, 9], name="synthetic_duplicate_index")
            before = frame.copy(deep=True)
            with patch("components.consumer_adapter.validate_dataset_contract",
                       return_value=ValidationResult(True, (), count)):
                result = self.build(dataframe=frame)
            self.assertIs(result.demo_candidate, candidate)
            if not candidate:
                self.rejected(result, "INVALID_VALIDATOR_RESULT", "schema")
            assert_frame_equal(frame, before, check_exact=True)

    def test_f13_decimal_context_unchanged_on_row_count_rejection(self):
        context = getcontext()
        before = (context.prec, context.rounding, dict(context.traps), dict(context.flags))
        def malformed_validator(*args):
            getcontext().prec = 7
            Decimal(1) / Decimal(3)
            return ValidationResult(True, (), 0)
        with patch("components.consumer_adapter.validate_dataset_contract", side_effect=malformed_validator):
            result = self.build()
        self.rejected(result, "INVALID_VALIDATOR_RESULT", "schema")
        self.assertIs(result.schema_valid, False)
        self.assertEqual(before, (context.prec, context.rounding, dict(context.traps), dict(context.flags)))

    def test_f14_row_count_outcomes_repeatable(self):
        for count in (2, 0, None, True, "2", np.int64(2)):
            with patch("components.consumer_adapter.validate_dataset_contract",
                       return_value=ValidationResult(True, (), count)):
                first, second = self.build(), self.build()
            self.assertEqual(first, second)
            self.assertIs(first.demo_candidate, type(count) is int and count == 2)

    def test_f15_non_integer_types_and_hooks_rejected_before_comparison(self):
        class HookTrap:
            def forbidden(self, *args):
                raise AssertionError("PRIVATE_COUNT_HOOK")
            __eq__ = __ne__ = __lt__ = __ge__ = __int__ = __index__ = __str__ = __repr__ = forbidden
        class IntSubclass(int):
            def __int__(self):
                raise AssertionError("PRIVATE_INT_HOOK")
        for count in (2.0, Decimal("2"), np.float64(2), np.bool_(True), pd.NA,
                      HookTrap(), IntSubclass(2)):
            result = self.reject_success_row_count(count)
            self.assertNotIn("PRIVATE", repr(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
