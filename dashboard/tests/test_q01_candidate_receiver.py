"""Fully synthetic receiver tests. No readers, artifacts or authorization grants.

Forged/revoked production approval boundary tests are DEFERRED: this module
has no approval/reader API. Rejecting a policy dict is not authentication.
"""

import ast
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, Inexact, Rounded, localcontext
from fractions import Fraction
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components import q01_candidate_receiver as q
from components.artifact_gate import real_artifact_status


def isolation_violations(source: str) -> tuple[str, ...]:
    """Deterministic syntax guard, not an IO sandbox or authorization proof.

    Covers explicit imports/calls and import aliases. Arbitrary reflection,
    runtime rebinding and transitive dependency behavior are outside its scope.
    Snippets are parsed only, never executed.
    """
    tree = ast.parse(source)
    aliases = {}
    issues = set()
    forbidden_modules = {"streamlit", "pyspark", "socket", "subprocess", "os",
                         "requests", "urllib", "http", "aiohttp", "ftplib",
                         "importlib", "runpy"}
    forbidden_calls = {
        "open", "read_csv", "read_parquet", "read_json", "read_pickle",
        "read_excel", "read_feather", "read_sql", "read_table", "read_orc",
        "read_bytes", "read_text", "write_bytes", "write_text", "to_csv",
        "to_parquet", "to_pickle", "glob", "rglob", "iterdir", "listdir",
        "scandir", "walk", "stat", "lstat", "__import__", "eval", "exec",
        "compile", "import_module", "load_dataset", "load_table", "_load_table",
        "load_overview_data", "load_skills_data", "load_salary_quality_data",
        "load_spark", "get_spark_session",
    }

    def forbidden_import(name):
        return name.split(".")[0] in forbidden_modules or "data_loader" in name.split(".")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = item.name if item.asname else item.name.split(".")[0]
                if forbidden_import(item.name):
                    issues.add("IMPORT:" + item.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if forbidden_import(module):
                issues.add("IMPORT:" + module)
            for item in node.names:
                full = module + "." + item.name if module else item.name
                aliases[item.asname or item.name] = full
                if forbidden_import(full):
                    issues.add("IMPORT:" + full)

    def qualified(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            parent = qualified(node.value)
            return parent + "." + node.attr if parent else node.attr
        if isinstance(node, ast.Call):
            return qualified(node.func)
        return ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = qualified(node.func)
            if name.split(".")[-1] in forbidden_calls or forbidden_import(name):
                issues.add("CALL:" + name)
    return tuple(sorted(issues))


class CandidateReceiverTests(unittest.TestCase):
    def setUp(self):
        self.policy = q.SyntheticPolicy(
            "SYNTHETIC_TEST_ONLY", "TEST_TAXONOMY",
            ("FIX_A", "FIX_B", "Unknown", "UNKNOWN", "N/A", "IT_OTHER", "UNUSED"),
            "ABSOLUTE_FRACTION", Decimal("0.000000000001"))
        self.context = q.SyntheticContext("SYNTHETIC_TEST_ONLY", "TEST_RUN",
                                          "TEST_POPULATION", "TEST_ALL", "TEST_TAXONOMY")

    def frame(self, rows=None):
        if rows is None:
            rows = [("FIX_A", 6, 10, 10, Decimal("0.6"), Decimal("0.6")),
                    ("FIX_B", 4, 10, 10, Decimal("0.4"), Decimal("0.4"))]
        return pd.DataFrame(rows, columns=q.COLUMNS, dtype=object)

    def missing(self):
        return self.frame([("FIX_A", 5, 10, 8, Decimal("0.5"), Fraction(5, 8)),
                           ("FIX_B", 3, 10, 8, Decimal("0.3"), Fraction(3, 8)),
                           (None, 2, 10, 8, Decimal("0.2"), None)])

    def run_frame(self, frame=None, **kwargs):
        return q.validate_q01_candidate(self.frame() if frame is None else frame,
                                        kwargs.get("policy", self.policy),
                                        kwargs.get("context", self.context))

    def assert_rejected(self, result, code):
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "CANDIDATE_VALIDATION_FAILED")
        self.assertEqual(result.issues, (code,))
        self.assertEqual(result.rows, ())
        self.assertIsNone(result.context)
        self.assertIsNone(result.population_n)
        self.assertIsNone(result.known_k)

    def changed(self, column, value, row=0, frame=None):
        frame = self.frame() if frame is None else frame
        frame.at[row, column] = value
        return self.run_frame(frame)

    def test_two_known_categories(self):
        result = self.run_frame()
        self.assertTrue(result.passed)
        self.assertEqual(result.status, "CANDIDATE_VALIDATED_FOR_TEST")
        self.assertEqual(result.issues, ())
        self.assertEqual((result.population_n, result.known_k), (10, 10))
        self.assertEqual(tuple(r.job_count for r in result.rows), (6, 4))
        self.assertEqual(result.context, self.context)
        self.assertIsNot(result.context, self.context)

    def test_known_and_missing_two_bases(self):
        result = self.run_frame(self.missing())
        self.assertTrue(result.passed)
        self.assertEqual((result.population_n, result.known_k), (10, 8))
        self.assertEqual(result.rows[0].share_all_it, Decimal("0.5"))
        self.assertEqual(result.rows[0].share_known, Fraction(5, 8))
        self.assertTrue(result.rows[2].is_missing)
        self.assertIsNone(result.rows[2].category)
        self.assertIsNone(result.rows[2].share_known)

    def test_all_missing_k_zero(self):
        result = self.run_frame(self.frame([(None, 10, 10, 0, 1.0, None)]))
        self.assertTrue(result.passed)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.known_k, 0)
        self.assertEqual(result.rows[0].share_all_it, 1.0)
        self.assertIsNone(result.rows[0].share_known)

    def test_all_known_n_equals_k(self):
        result = self.run_frame()
        self.assertTrue(result.passed)
        self.assertFalse(any(r.is_missing for r in result.rows))
        self.assertEqual(sum(r.job_count for r in result.rows), result.population_n)

    def test_it_other_is_known(self):
        frame = self.frame()
        frame.at[0, "category"] = "IT_OTHER"
        result = self.run_frame(frame)
        self.assertTrue(result.passed)
        self.assertFalse(result.rows[0].is_missing)
        self.assertEqual(result.rows[0].category, "IT_OTHER")

    def test_literal_unknown_variants_remain_distinct(self):
        frame = self.frame([("Unknown", 1, 4, 4, 0.25, 0.25),
                            ("UNKNOWN", 1, 4, 4, 0.25, 0.25),
                            ("N/A", 2, 4, 4, 0.5, 0.5)])
        result = self.run_frame(frame)
        self.assertTrue(result.passed)
        self.assertEqual(tuple(r.category for r in result.rows), ("Unknown", "UNKNOWN", "N/A"))
        self.assertFalse(any(r.is_missing for r in result.rows))

    def test_unknown_and_none_distinct(self):
        result = self.run_frame(self.frame([("Unknown", 1, 2, 1, 0.5, 1.0),
                                            (None, 1, 2, 1, 0.5, None)]))
        self.assertTrue(result.passed)
        self.assertEqual(tuple(r.is_missing for r in result.rows), (False, True))

    def test_row_order_changed(self):
        forward = self.run_frame(self.missing())
        reverse = self.run_frame(self.missing().iloc[::-1])
        self.assertTrue(reverse.passed)
        self.assertEqual(reverse.rows, tuple(reversed(forward.rows)))

    def test_compatible_integer_widths(self):
        frame = self.frame()
        frame.at[0, "job_count"] = np.int32(6)
        frame.at[1, "job_count"] = np.uint64(4)
        frame.at[0, "denominator_all_it"] = np.int64(10)
        frame.at[1, "denominator_all_it"] = np.int16(10)
        frame.at[0, "denominator_known"] = np.uint32(10)
        self.assertTrue(self.run_frame(frame).passed)

    def test_stored_decimal_precision_preserved(self):
        frame = self.frame()
        stored = Decimal("0.6000000000000000000000000000")
        frame.at[0, "share_all_it"] = stored
        result = self.run_frame(frame)
        self.assertTrue(result.passed)
        self.assertEqual(result.rows[0].share_all_it.as_tuple(), stored.as_tuple())
        self.assertIs(type(result.rows[0].share_all_it), Decimal)

    def test_fraction_detached_from_input(self):
        frame = self.missing()
        original = frame.at[0, "share_known"]
        result = self.run_frame(frame)
        self.assertTrue(result.passed)
        self.assertIsNot(result.rows[0].share_known, original)
        original._numerator = 999
        self.assertEqual(result.rows[0].share_known, Fraction(5, 8))

    def test_n_zero(self):
        self.assert_rejected(self.changed("denominator_all_it", 0), "INVALID_COUNTS")

    def test_empty_input(self):
        self.assert_rejected(self.run_frame(self.frame([])), "EMPTY_OR_OVERSIZED_INPUT")

    def test_missing_physical_column(self):
        self.assert_rejected(self.run_frame(self.frame().drop(columns="share_known")), "INVALID_SIX_COLUMN_SCHEMA")

    def test_extra_physical_column(self):
        self.assert_rejected(self.run_frame(self.frame().assign(run_id="NOT_PHYSICAL")), "INVALID_SIX_COLUMN_SCHEMA")

    def test_duplicate_logical_columns(self):
        frame = self.frame()
        frame.columns = ["category", "job_count", "job_count", "denominator_known", "share_all_it", "share_known"]
        self.assert_rejected(self.run_frame(frame), "DUPLICATE_COLUMNS")

    def test_bad_column_name_types(self):
        frame = self.frame()
        frame.columns = [None, *q.COLUMNS[1:]]
        self.assert_rejected(self.run_frame(frame), "INVALID_COLUMNS")

    def test_wrong_count_types(self):
        for bad in ("6", 6.0, 6.5, Decimal("6"), Fraction(6), None, pd.NA, float("nan")):
            with self.subTest(kind=type(bad).__name__):
                self.assert_rejected(self.changed("job_count", bad), "INVALID_COUNTS")

    def test_boolean_job_count(self):
        for bad in (True, False, np.bool_(True)):
            self.assert_rejected(self.changed("job_count", bad), "INVALID_COUNTS")

    def test_boolean_denominators(self):
        for column in ("denominator_all_it", "denominator_known"):
            for bad in (True, np.bool_(False)):
                self.assert_rejected(self.changed(column, bad), "INVALID_COUNTS")

    def test_negative_count_and_denominators(self):
        for column in q.COLUMNS[1:4]:
            self.assert_rejected(self.changed(column, -1), "INVALID_COUNTS")

    def test_zero_emitted_bucket(self):
        self.assert_rejected(self.changed("job_count", 0), "INVALID_COUNTS")

    def test_duplicate_known_category(self):
        self.assert_rejected(self.changed("category", "FIX_A", row=1), "DUPLICATE_CATEGORY")

    def test_duplicate_none_category(self):
        frame = self.frame([(None, 5, 10, 0, 0.5, None), (None, 5, 10, 0, 0.5, None)])
        self.assert_rejected(self.run_frame(frame), "DUPLICATE_CATEGORY")

    def test_inconsistent_n(self):
        self.assert_rejected(self.changed("denominator_all_it", 11, row=1), "INCONSISTENT_DENOMINATORS")

    def test_inconsistent_k(self):
        self.assert_rejected(self.changed("denominator_known", 9, row=1), "INCONSISTENT_DENOMINATORS")

    def test_k_greater_than_n(self):
        self.assert_rejected(self.changed("denominator_known", 11), "INVALID_COUNTS")

    def test_k_zero_known_bucket(self):
        frame = self.frame([("FIX_A", 10, 10, 0, 1.0, None)])
        self.assert_rejected(self.run_frame(frame), "COUNT_EXCEEDS_POPULATION")

    def test_missing_count_mismatch(self):
        frame = self.frame([("FIX_A", 5, 10, 8, 0.5, 0.625),
                            ("FIX_B", 3, 10, 8, 0.3, 0.375), (None, 1, 10, 8, 0.1, None)])
        self.assert_rejected(self.run_frame(frame), "CONSERVATION_MISMATCH")

    def test_missing_conditional_share_zero(self):
        self.assert_rejected(self.changed("share_known", 0, row=2, frame=self.missing()), "UNEXPECTED_KNOWN_RATE")

    def test_known_conditional_share_none(self):
        self.assert_rejected(self.changed("share_known", None), "INVALID_KNOWN_RATE")

    def test_nan_rates(self):
        for bad in (float("nan"), np.float64("nan"), Decimal("NaN"), Decimal("sNaN")):
            self.assert_rejected(self.changed("share_all_it", bad), "INVALID_ALL_RATE")
            self.assert_rejected(self.changed("share_known", bad), "INVALID_KNOWN_RATE")

    def test_infinity_rates(self):
        for bad in (float("inf"), -float("inf"), Decimal("Infinity")):
            self.assert_rejected(self.changed("share_all_it", bad), "INVALID_ALL_RATE")

    def test_wrong_all_rate(self):
        self.assert_rejected(self.changed("share_all_it", Decimal("0.7")), "INCONSISTENT_ALL_RATE")

    def test_wrong_known_rate(self):
        self.assert_rejected(self.changed("share_known", Decimal("0.7")), "INCONSISTENT_KNOWN_RATE")

    def test_percent_instead_of_fraction(self):
        self.assert_rejected(self.changed("share_all_it", 80), "INVALID_ALL_RATE")

    def test_negative_or_above_one_rates(self):
        for bad in (-0.1, 1.1):
            self.assert_rejected(self.changed("share_all_it", bad), "INVALID_ALL_RATE")

    def test_blank_and_noncanonical_categories(self):
        for bad in ("", " ", "\t", " FIX_A", "FIX_A ", "FIX_\nA"):
            self.assert_rejected(self.changed("category", bad), "INVALID_CATEGORY")

    def test_unexpected_category(self):
        self.assert_rejected(self.changed("category", "NOT_IN_DOMAIN"), "INVALID_CATEGORY")

    def test_auto_zero_fill_rejected(self):
        frame = self.frame()
        frame.loc[2] = ["UNUSED", 0, 10, 10, 0, 0]
        self.assert_rejected(self.run_frame(frame), "INVALID_COUNTS")

    def test_absent_categories_not_created(self):
        result = self.run_frame()
        self.assertTrue(result.passed)
        self.assertEqual(len(result.rows), 2)
        self.assertNotIn("UNUSED", tuple(r.category for r in result.rows))

    def test_input_mutation_does_not_change_result(self):
        frame = self.frame()
        result = self.run_frame(frame)
        frame.at[0, "category"] = "IT_OTHER"
        frame.at[0, "job_count"] = 999
        frame.at[0, "share_all_it"] = Decimal("0.99")
        self.assertEqual(result.rows[0].category, "FIX_A")
        self.assertEqual(result.rows[0].job_count, 6)
        self.assertEqual(result.rows[0].share_all_it, Decimal("0.6"))

    def test_missing_policy(self):
        self.assert_rejected(self.run_frame(policy=None), "INVALID_SYNTHETIC_POLICY")

    def test_invalid_tolerance(self):
        for bad in (None, -0.1, 2, True, "0.01", float("nan"), float("inf"), Decimal("sNaN")):
            self.assert_rejected(self.run_frame(policy=replace(self.policy, tolerance=bad)), "INVALID_TEST_TOLERANCE")

    def test_explicit_comparison_required(self):
        for bad in (None, "RELATIVE", "", True):
            self.assert_rejected(self.run_frame(policy=replace(self.policy, comparison=bad)), "INVALID_SYNTHETIC_POLICY")

    def test_unsupported_context(self):
        for bad in (None, {}, "TEST_RUN", Path("not-a-context")):
            self.assert_rejected(self.run_frame(context=bad), "INVALID_SYNTHETIC_CONTEXT")

    def test_wrong_origin(self):
        self.assert_rejected(self.run_frame(policy=replace(self.policy, origin="REAL")), "INVALID_SYNTHETIC_POLICY")
        self.assert_rejected(self.run_frame(context=replace(self.context, origin="REAL")), "INVALID_SYNTHETIC_CONTEXT")

    def test_context_identity_and_taxonomy(self):
        for bad in ("", "private/path", None, True):
            self.assert_rejected(self.run_frame(context=replace(self.context, run_id=bad)), "INVALID_SYNTHETIC_CONTEXT")
        self.assert_rejected(self.run_frame(context=replace(self.context, taxonomy_id="OTHER")), "INVALID_SYNTHETIC_CONTEXT")

    def test_unsupported_structures(self):
        for bad in (None, [], (), {}, "private/path.csv", Path("not-a-dataset"), np.array([1])):
            self.assert_rejected(q.validate_q01_candidate(bad, self.policy, self.context), "INVALID_INPUT_STRUCTURE")

    def test_malformed_decoded_category(self):
        for bad in (["FIX_A"], {"category": "FIX_A"}, pd.NA, float("nan"), 1):
            self.assert_rejected(self.changed("category", bad), "INVALID_CATEGORY")

    def test_bad_domain(self):
        for bad in (None, [], (), ("FIX_A", "FIX_A"), (None,), (" FIX_A",)):
            self.assert_rejected(self.run_frame(policy=replace(self.policy, category_domain=bad)), "INVALID_SYNTHETIC_DOMAIN")

    def test_required_all_share_none_and_bad_types(self):
        for bad in (None, pd.NA, True, "0.6", [], {}):
            self.assert_rejected(self.changed("share_all_it", bad), "INVALID_ALL_RATE")

    def test_missing_share_requires_literal_none(self):
        for bad in (pd.NA, float("nan"), False, Decimal("NaN")):
            self.assert_rejected(self.changed("share_known", bad, row=2, frame=self.missing()), "UNEXPECTED_KNOWN_RATE")

    def test_missing_bucket_required(self):
        self.assert_rejected(self.run_frame(self.missing().iloc[:2]), "CONSERVATION_MISMATCH")

    def test_known_count_conservation(self):
        frame = self.frame([("FIX_A", 5, 10, 10, 0.5, 0.5), ("FIX_B", 4, 10, 10, 0.4, 0.4)])
        self.assert_rejected(self.run_frame(frame), "CONSERVATION_MISMATCH")

    def test_count_above_n(self):
        self.assert_rejected(self.changed("job_count", 11), "COUNT_EXCEEDS_POPULATION")

    def test_no_input_mutation(self):
        frame = self.missing()
        before = frame.copy(deep=True)
        self.assertTrue(self.run_frame(frame).passed)
        assert_frame_equal(frame, before)

    def test_result_is_frozen(self):
        result = self.run_frame()
        with self.assertRaises(FrozenInstanceError):
            result.population_n = 999
        with self.assertRaises(FrozenInstanceError):
            result.rows[0].job_count = 999
        with self.assertRaises(FrozenInstanceError):
            result.context.run_id = "OTHER"

    def test_failure_never_reuses_previous_success(self):
        first = self.run_frame()
        self.assertTrue(first.passed)
        self.assert_rejected(self.changed("share_all_it", 80, row=1), "INVALID_ALL_RATE")
        self.assertEqual(first.rows[0].job_count, 6)

    def test_tolerance_does_not_replace_stored_rate(self):
        frame = self.frame()
        frame.at[0, "share_all_it"] = Decimal("0.6001")
        policy = replace(self.policy, tolerance=Decimal("0.001"))
        result = self.run_frame(frame, policy=policy)
        self.assertTrue(result.passed)
        self.assertEqual(result.rows[0].share_all_it, Decimal("0.6001"))
        self.assert_rejected(self.run_frame(frame, policy=replace(policy, tolerance=Decimal("0"))), "INCONSISTENT_ALL_RATE")

    def test_decimal_context_does_not_change_decisions(self):
        frame = self.frame()
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            self.assertTrue(self.run_frame(frame).passed)

    def test_large_exact_counts_no_float_conversion(self):
        n = 2**60
        frame = self.frame([("FIX_A", n, n, n, Fraction(1), Fraction(1))])
        result = self.run_frame(frame)
        self.assertTrue(result.passed)
        self.assertEqual(result.population_n, n)

    def test_bounded_counts_and_input(self):
        self.assert_rejected(self.changed("job_count", 2**16385), "INVALID_COUNTS")
        large = pd.concat([self.frame()] * 513, ignore_index=True)
        self.assert_rejected(self.run_frame(large), "EMPTY_OR_OVERSIZED_INPUT")

    def test_no_reader_calls(self):
        with patch.object(pd, "read_csv", side_effect=AssertionError("reader called")) as csv_reader, \
                patch.object(pd, "read_parquet", side_effect=AssertionError("reader called")) as parquet_reader:
            self.assertTrue(self.run_frame().passed)
            csv_reader.assert_not_called()
            parquet_reader.assert_not_called()

    def test_diagnostics_do_not_echo_input(self):
        secret = "SENSITIVE_PRIVATE_PATH_OR_TOKEN"
        result = self.changed("category", secret)
        self.assert_rejected(result, "INVALID_CATEGORY")
        self.assertNotIn(secret, repr(result))
        result = self.run_frame(context=replace(self.context, run_id="private/" + secret))
        self.assertNotIn(secret, repr(result))

    def test_no_production_api_and_gate_closed(self):
        result = self.run_frame()
        for name in ("production_eligible", "official_accepted", "authorize", "reader", "approval"):
            self.assertFalse(hasattr(result, name))
            self.assertFalse(hasattr(q, name))
        self.assertEqual(real_artifact_status(exists=True), "BLOCKED")

    def test_column_reordering_binds_names(self):
        self.assertEqual(self.run_frame(self.frame()[list(reversed(q.COLUMNS))]), self.run_frame())

    def test_custom_scalar_hooks_not_executed(self):
        class HostileInt(int):
            def __int__(self):
                raise AssertionError("custom conversion")
        class HostileString(str):
            def strip(self):
                raise AssertionError("custom normalization")
        self.assert_rejected(self.changed("job_count", HostileInt(6)), "INVALID_COUNTS")
        self.assert_rejected(self.changed("category", HostileString("FIX_A")), "INVALID_CATEGORY")

    def test_no_side_effect_import_statements(self):
        # Source inspection only: no execution of external tools or artifact IO.
        self.assertEqual(isolation_violations(Path(q.__file__).read_text(encoding="utf-8")), ())

    def fraction_result(self):
        frame = self.missing()
        frame.at[0, "share_all_it"] = Fraction(1, 2)
        result = self.run_frame(frame)
        self.assertTrue(result.passed)
        return frame, result

    def test_returned_known_fraction_numerator_is_defensive(self):
        _, result = self.fraction_result()
        returned = result.rows[0].share_known
        returned._numerator = 999
        self.assertEqual(returned.numerator, 999)  # Caller object is still mutable.
        self.assertEqual(result.rows[0].share_known.numerator, 5)
        self.assertEqual(result.rows[0].share_known.denominator, 8)
        self.assertEqual(result.rows[0].share_known, Fraction(5, 8))
        self.assertIsNot(result.rows[0].share_known, result.rows[0].share_known)

    def test_returned_all_fraction_numerator_is_defensive(self):
        _, result = self.fraction_result()
        returned = result.rows[0].share_all_it
        returned._numerator = 999
        self.assertEqual(result.rows[0].share_all_it, Fraction(1, 2))
        self.assertEqual((result.rows[0].share_all_it.numerator,
                          result.rows[0].share_all_it.denominator), (1, 2))
        self.assertIsNot(result.rows[0].share_all_it, result.rows[0].share_all_it)

    def test_returned_fraction_denominators_are_defensive(self):
        _, result = self.fraction_result()
        for name, expected in (("share_all_it", Fraction(1, 2)), ("share_known", Fraction(5, 8))):
            returned = getattr(result.rows[0], name)
            returned._denominator = 0
            self.assertEqual(returned.denominator, 0)
            self.assertEqual(getattr(result.rows[0], name), expected)

    def test_fraction_mutation_leaves_siblings_and_metadata_unchanged(self):
        _, result = self.fraction_result()
        sibling_before = result.rows[1:]
        context_before = result.context
        result.rows[0].share_known._numerator = 999
        result.rows[0].share_all_it._denominator = 999
        self.assertEqual(result.rows[1:], sibling_before)
        self.assertEqual(result.rows[1].share_known, Fraction(3, 8))
        self.assertIsNone(result.rows[2].share_known)
        self.assertEqual((result.population_n, result.known_k), (10, 8))
        self.assertEqual(result.context, context_before)
        self.assertEqual(result.context, self.context)
        self.assertEqual(result.status, "CANDIDATE_VALIDATED_FOR_TEST")
        self.assertTrue(result.passed)
        self.assertEqual(result.issues, ())

    def test_fraction_snapshot_survives_input_and_call_sequence(self):
        frame, first = self.fraction_result()
        frame.at[0, "share_known"]._numerator = 333
        frame.at[0, "share_all_it"]._denominator = 777
        frame.at[0, "job_count"] = 999
        first.rows[0].share_known._numerator = 222
        first.rows[0].share_all_it._denominator = 555
        failed = self.run_frame(frame)
        self.assert_rejected(failed, "COUNT_EXCEEDS_POPULATION")
        _, last = self.fraction_result()
        self.assertTrue(last.passed)
        self.assertEqual(first, last)
        self.assertEqual(first.rows[0].share_known, Fraction(5, 8))
        self.assertEqual(first.rows[0].share_all_it, Fraction(1, 2))

    def test_nontrivial_stored_fraction_is_not_recomputed(self):
        frame = self.frame()
        stored = Fraction(3, 5) + Fraction(1, 10**30 + 7)
        frame.at[0, "share_all_it"] = stored
        result = self.run_frame(frame)
        self.assertTrue(result.passed)
        actual = result.rows[0].share_all_it
        self.assertEqual((actual.numerator, actual.denominator), (stored.numerator, stored.denominator))
        self.assertNotEqual(actual, Fraction(3, 5))
        actual._numerator = 1
        self.assertEqual(result.rows[0].share_all_it, stored)

    def test_row_public_constructor_keywords_preserved(self):
        row = q.CandidateRow(category="FIX_A", is_missing=False, job_count=1,
                             denominator_all_it=1, denominator_known=1,
                             share_all_it=Fraction(1), share_known=Fraction(1))
        row.share_all_it._numerator = 99
        self.assertEqual(row.share_all_it, Fraction(1))
        self.assertEqual(row.share_known, Fraction(1))

    def test_fraction_authoritative_snapshot_contains_no_fraction(self):
        _, result = self.fraction_result()
        from dataclasses import asdict
        # Reflection sees immutable integer pairs, not authoritative Fraction objects.
        row = asdict(result.rows[0])
        self.assertEqual(row["_share_all_it"], (1, 2))
        self.assertEqual(row["_share_known"], (5, 8))

    def test_ast_rejects_streamlit_import(self):
        self.assertTrue(isolation_violations("import streamlit"))

    def test_ast_rejects_streamlit_from_import(self):
        self.assertTrue(isolation_violations("from streamlit import session_state"))

    def test_ast_rejects_bare_open(self):
        self.assertIn("CALL:open", isolation_violations('open("SYNTHETIC_NOT_OPENED")'))

    def test_ast_rejects_pyspark_import(self):
        self.assertTrue(isolation_violations("import pyspark"))

    def test_ast_rejects_socket_import(self):
        self.assertTrue(isolation_violations("import socket"))

    def test_ast_rejects_subprocess_import(self):
        self.assertTrue(isolation_violations("import subprocess"))

    def test_ast_rejects_aliased_pandas_reader(self):
        self.assertIn("CALL:pandas.read_parquet", isolation_violations(
            'import pandas as pd\npd.read_parquet("SYNTHETIC_NOT_READ")'))

    def test_ast_rejects_path_open(self):
        self.assertIn("CALL:pathlib.Path.open", isolation_violations(
            'from pathlib import Path\nPath("SYNTHETIC_NOT_READ").open()'))

    def test_ast_rejects_from_reader_alias(self):
        self.assertIn("CALL:pandas.read_csv", isolation_violations(
            'from pandas import read_csv as reader\nreader("SYNTHETIC_NOT_READ")'))

    def test_ast_rejects_builtin_open_alias(self):
        self.assertIn("CALL:builtins.open", isolation_violations(
            'from builtins import open as reader\nreader("SYNTHETIC_NOT_OPENED")'))

    def test_ast_rejects_obvious_loader_imports_and_calls(self):
        for snippet in ("from components import data_loader", "import components.data_loader as loader",
                        "from components.data_loader import load_overview_data as load\nload()",
                        "loader.load_dataset()", "load_overview_data()"):
            self.assertTrue(isolation_violations(snippet), snippet)

    def test_ast_rejects_dynamic_import_and_execution_primitives(self):
        for snippet in ('__import__("socket")', 'eval("SYNTHETIC")', 'exec("SYNTHETIC")',
                        'compile("SYNTHETIC", "synthetic", "exec")',
                        'import importlib as il\nil.import_module("socket")'):
            self.assertTrue(isolation_violations(snippet), snippet)

    def test_ast_allows_pure_numeric_and_typing_code(self):
        snippet = '''from dataclasses import dataclass
from decimal import Decimal as D
from fractions import Fraction as F
from typing import Optional
import pandas as pd
import numpy as np
from .metric_validator import _rational
value = F(1, 2)
frame = pd.DataFrame({"value": [D("0.5")]})
count = np.int32(1)
'''
        self.assertEqual(isolation_violations(snippet), ())

    def test_ast_ignores_comments_and_string_literals(self):
        self.assertEqual(isolation_violations(
            '# import socket; open("not executed")\nmessage = "pandas.read_parquet; import streamlit"'), ())

    def test_ast_guard_is_deterministic(self):
        snippet = "import socket as s\nimport streamlit as st\ns.socket()"
        self.assertEqual(isolation_violations(snippet), isolation_violations(snippet))
        self.assertEqual(isolation_violations(snippet), tuple(sorted(set(isolation_violations(snippet)))))

    def endpoint(self, n):
        class HookedInt(int):
            def __new__(cls, value):
                instance = int.__new__(cls, value)
                instance.calls = []
                instance.current = value
                return instance

            def invoked(self, name):
                self.calls.append(name)
                raise AssertionError("Nested numeric hook executed")

            def __int__(self):
                return self.invoked("int")

            def __float__(self):
                return self.invoked("float")

            def __index__(self):
                return self.invoked("index")

            def __eq__(self, other):
                return self.invoked("eq")

            def __lt__(self, other):
                return self.invoked("lt")

            @property
            def numerator(self):
                return self.invoked("numerator")

        return HookedInt(n)

    def malformed_rate(self, numerator=5, denominator=8):
        rate = Fraction(5, 8)
        # Setup edits slots only: do not call numeric hooks to build fixtures.
        rate._numerator = numerator
        rate._denominator = denominator
        return rate

    def test_mutable_fraction_numerator_rejected(self):
        nested = self.endpoint(5)
        rate = self.malformed_rate(numerator=nested)
        self.assert_rejected(self.changed("share_known", rate, frame=self.missing()), "INVALID_KNOWN_RATE")
        self.assertEqual(nested.calls, [])

    def test_mutable_fraction_denominator_rejected(self):
        nested = self.endpoint(8)
        rate = self.malformed_rate(denominator=nested)
        self.assert_rejected(self.changed("share_known", rate, frame=self.missing()), "INVALID_KNOWN_RATE")
        self.assertEqual(nested.calls, [])

    def test_both_fraction_endpoints_malformed(self):
        numerator, denominator = self.endpoint(5), self.endpoint(8)
        rate = self.malformed_rate(numerator, denominator)
        self.assert_rejected(self.changed("share_known", rate, frame=self.missing()), "INVALID_KNOWN_RATE")
        self.assertEqual(numerator.calls, [])
        self.assertEqual(denominator.calls, [])

    def test_boolean_fraction_numerator_rejected(self):
        for bad in (True, False):
            self.assert_rejected(self.changed("share_known", self.malformed_rate(numerator=bad),
                                              frame=self.missing()), "INVALID_KNOWN_RATE")

    def test_boolean_fraction_denominator_rejected(self):
        for bad in (True, False):
            self.assert_rejected(self.changed("share_known", self.malformed_rate(denominator=bad),
                                              frame=self.missing()), "INVALID_KNOWN_RATE")

    def test_fraction_endpoint_hooks_not_run_for_either_share(self):
        for column, code in (("share_all_it", "INVALID_ALL_RATE"), ("share_known", "INVALID_KNOWN_RATE")):
            for slot, n in (("_numerator", 5), ("_denominator", 8)):
                with self.subTest(column=column, slot=slot):
                    nested = self.endpoint(n)
                    rate = Fraction(5, 8)
                    setattr(rate, slot, nested)
                    frame = self.missing()
                    frame.at[0, column] = rate
                    setup_calls = tuple(nested.calls)
                    nested.calls.clear()
                    self.assert_rejected(self.run_frame(frame), code)
                    self.assertEqual(nested.calls, [])
                    self.assertEqual(setup_calls, ())

    def test_non_integer_fraction_endpoints_rejected(self):
        for bad in (5.0, Decimal(5), Fraction(5), None, object(), np.int64(5)):
            for slot in ("_numerator", "_denominator"):
                rate = Fraction(5, 8)
                setattr(rate, slot, bad)
                self.assert_rejected(self.changed("share_known", rate, frame=self.missing()), "INVALID_KNOWN_RATE")

    def test_missing_fraction_endpoint_rejected(self):
        for slot in ("_numerator", "_denominator"):
            rate = Fraction(5, 8)
            delattr(rate, slot)
            self.assert_rejected(self.changed("share_known", rate, frame=self.missing()), "INVALID_KNOWN_RATE")

    def test_nonpositive_fraction_denominator_rejected(self):
        for denominator in (0, -8):
            rate = self.malformed_rate(denominator=denominator)
            self.assert_rejected(self.changed("share_known", rate, frame=self.missing()), "INVALID_KNOWN_RATE")

    def test_unreduced_fraction_is_not_silently_repaired(self):
        rate = self.malformed_rate(10, 16)
        self.assert_rejected(self.changed("share_known", rate, frame=self.missing()), "INVALID_KNOWN_RATE")

    def test_oversized_fraction_endpoint_rejected(self):
        self.assert_rejected(self.changed("share_known", self.malformed_rate(2**16385, 8),
                                          frame=self.missing()), "INVALID_KNOWN_RATE")

    def test_malformed_fraction_tolerance_rejected_without_hooks(self):
        nested = self.endpoint(0)
        rate = self.malformed_rate(nested, 1)
        policy = replace(self.policy, tolerance=rate)
        self.assert_rejected(self.run_frame(policy=policy), "INVALID_TEST_TOLERANCE")
        self.assertEqual(nested.calls, [])

    def test_direct_row_constructor_cannot_retain_malformed_endpoints(self):
        nested = self.endpoint(5)
        for column in ("share_all_it", "share_known"):
            rates = {"share_all_it": Fraction(1), "share_known": Fraction(1)}
            rates[column] = self.malformed_rate(nested, 8)
            with self.assertRaisesRegex(ValueError, "^Invalid Fraction representation$"):
                q.CandidateRow("FIX_A", False, 1, 1, 1, **rates)
            self.assertEqual(nested.calls, [])

    def test_normal_fraction_snapshots_have_only_primitive_ints(self):
        _, result = self.fraction_result()
        for snapshot in (result.rows[0]._share_all_it, result.rows[0]._share_known,
                         result.rows[1]._share_known):
            self.assertIs(type(snapshot), tuple)
            self.assertEqual(len(snapshot), 2)
            self.assertTrue(all(type(v) is int for v in snapshot))
        self.assertEqual(result.rows[0]._share_known, (5, 8))
        self.assertEqual(result.rows[0].share_known, Fraction(5, 8))

    def test_malformed_failure_does_not_change_prior_or_later_success(self):
        frame, first = self.fraction_result()
        nested = self.endpoint(5)
        frame.at[0, "share_known"] = self.malformed_rate(nested, 8)
        self.assert_rejected(self.run_frame(frame), "INVALID_KNOWN_RATE")
        nested.current = 999
        _, last = self.fraction_result()
        self.assertEqual(first, last)
        self.assertEqual(first.rows[0].share_known, Fraction(5, 8))
        self.assertEqual(first.rows[0].share_all_it, Fraction(1, 2))
        self.assertEqual(nested.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
