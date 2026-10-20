"""Pure row-level division checks; no business schema or acceptance decision."""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from numbers import Integral

import pandas as pd
from pandas.api.types import is_bool, is_float


@dataclass(frozen=True)
class MetricValidationSpec:
    numerator_column: str
    denominator_column: str
    rate_column: str
    rate_unit: str
    zero_denominator_policy: str
    tolerance: object
    subset_of_population: bool


@dataclass(frozen=True)
class MetricValidationIssue:
    code: str
    fields: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class MetricValidationResult:
    """Validation evidence only; passed never grants production eligibility."""

    passed: bool
    errors: tuple[MetricValidationIssue, ...]
    row_count: int | None


# Computational guardrails, NOT physical count widths or business thresholds.
# Oversized/unsupported scalars receive controlled rejection, never coercion.
_MAX_BITS = 16384
_MAX_DECIMAL_DIGITS = 4096


def _rational(value) -> Fraction | None:
    """Finite supported scalar -> exact rational, with bounded intermediates.

    Floats retain their stored binary value; Decimal uses its exact ratio.
    No Decimal arithmetic/context changes or conversion of counts to float.
    """
    if is_bool(value):
        return None
    try:
        if isinstance(value, Integral):
            numerator, denominator = int(value), 1
        elif isinstance(value, Decimal):
            if not value.is_finite():
                return None
            parts = value.as_tuple()
            if len(parts.digits) > _MAX_DECIMAL_DIGITS or abs(parts.exponent) > _MAX_DECIMAL_DIGITS:
                return None
            numerator, denominator = value.as_integer_ratio()
        elif isinstance(value, Fraction):
            numerator, denominator = value.numerator, value.denominator
        elif is_float(value):
            numerator, denominator = value.as_integer_ratio()
        else:
            return None
        if not isinstance(numerator, Integral) or not isinstance(denominator, Integral):
            return None
        numerator, denominator = int(numerator), int(denominator)
        if max(numerator.bit_length(), denominator.bit_length()) > _MAX_BITS or denominator == 0:
            return None
        return Fraction(numerator, denominator)
    except (ArithmeticError, TypeError, ValueError):
        # Numeric conversion boundary only; no record values enter diagnostics.
        return None


def _null_rate(value) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, Decimal):
        return value.is_qnan()  # Signaling NaN is invalid, never a NULL rate.
    return is_float(value) and bool(pd.isna(value))


def validate_metric_contract(dataframe, spec: MetricValidationSpec) -> MetricValidationResult:
    """Check every row without mutation, aggregation, unit inference or approval.

    Only FRACTION is supported. Comparison is abs(stored_rate - n/d) <=
    tolerance, with no relative tolerance. All rates must be nonnegative;
    subset rates must also be <=1, independently of tolerance. Positive d
    always requires a finite rate.
    NULL policy permits a missing rate only for n=d=0; REJECT disallows any
    zero denominator. Quiet NaN/pandas sentinels represent missing rates, not
    zero counts. Structurally valid empty frames have no row violations and
    row_count=0; this does not assert availability or production acceptance.
    Diagnostics aggregate violation counts per code/fields, never row labels.
    """
    issues = {}

    def issue(code, fields, detail):
        key = (code, tuple(fields), detail)
        issues[key] = issues.get(key, 0) + 1

    def result(row_count):
        errors = tuple(MetricValidationIssue(code, fields, f"{count} violation(s): {detail}")
                       for (code, fields, detail), count in issues.items())
        return MetricValidationResult(not errors, errors, row_count)

    if not isinstance(spec, MetricValidationSpec):
        issue("INVALID_METRIC_SPEC", (), "An explicit MetricValidationSpec is required.")
        return result(None)
    columns = (spec.numerator_column, spec.denominator_column, spec.rate_column)
    valid_names = all(isinstance(c, str) and bool(c.strip()) for c in columns)
    if not valid_names or len(set(columns)) != 3:
        issue("INVALID_METRIC_SPEC", (), "Three distinct nonempty column names are required.")
    if not isinstance(spec.rate_unit, str) or spec.rate_unit != "FRACTION":
        issue("INVALID_METRIC_SPEC", (), "Only explicit FRACTION representation is supported.")
    if not isinstance(spec.zero_denominator_policy, str) or spec.zero_denominator_policy not in ("NULL", "REJECT"):
        issue("INVALID_METRIC_SPEC", (), "Zero-denominator policy must be NULL or REJECT.")
    if type(spec.subset_of_population) is not bool:
        issue("INVALID_METRIC_SPEC", (), "Subset relationship must be an explicit boolean.")
    tolerance = _rational(spec.tolerance)
    if tolerance is None or tolerance < 0:
        issue("INVALID_METRIC_SPEC", (), "Absolute tolerance must be finite, supported and nonnegative.")
    if issues:
        return result(None)
    if dataframe is None:
        issue("MISSING_INPUT", (), "No dataset supplied.")
        return result(None)
    if not isinstance(dataframe, pd.DataFrame):
        issue("INVALID_INPUT", (), "Expected a pandas DataFrame.")
        return result(None)
    if not dataframe.columns.is_unique or not all(isinstance(c, str) for c in dataframe.columns):
        issue("INVALID_COLUMNS", (), "Column names must be unique strings.")
        return result(len(dataframe))
    absent = tuple(c for c in columns if c not in dataframe.columns)
    if absent:
        issue("MISSING_COLUMNS", absent, "Configured metric columns are absent.")
        return result(len(dataframe))

    # Read columns separately: mixed DataFrame row representations must not
    # coerce exact integer counts to float or homogenize nullable sentinels.
    for raw_n, raw_d, raw_rate in zip(*(dataframe[c] for c in columns)):
        n, d = _rational(raw_n), _rational(raw_d)
        valid_counts = True
        for value, code, field in ((n, "INVALID_NUMERATOR", columns[0]),
                                   (d, "INVALID_DENOMINATOR", columns[1])):
            if value is None or value.denominator != 1 or value < 0:
                issue(code, (field,), "Count must be a supported nonnegative finite integer, never NULL or boolean.")
                valid_counts = False
        if not valid_counts:
            continue
        if spec.subset_of_population and n > d:
            issue("NUMERATOR_EXCEEDS_DENOMINATOR", columns[:2], "Declared subset count exceeds population count.")

        missing_rate = _null_rate(raw_rate)
        rate = None if missing_rate else _rational(raw_rate)
        if not missing_rate and rate is None:
            issue("INVALID_RATE", (columns[2],), "Rate must be a supported finite numeric value, never boolean.")
        if d == 0:
            if n > 0:
                issue("INCONSISTENT_ZERO_DENOMINATOR", columns[:2], "Positive numerator cannot have zero denominator.")
            if spec.zero_denominator_policy == "REJECT":
                issue("ZERO_DENOMINATOR_REJECTED", (columns[1],), "Spec disallows zero denominators.")
            elif not missing_rate:
                issue("UNDEFINED_RATE_REQUIRED", (columns[2],), "Zero denominator requires a NULL stored rate.")
            continue
        if missing_rate:
            issue("INVALID_RATE", (columns[2],), "Positive denominator requires a finite stored rate.")
        elif rate is not None:
            if rate < 0 or (spec.subset_of_population and rate > 1):
                issue("RATE_OUT_OF_RANGE", (columns[2],), "FRACTION must be nonnegative; subset FRACTION must also be <=1.")
            if abs(rate - n / d) > tolerance:
                issue("RATE_INCONSISTENT", columns, "Stored FRACTION disagrees with n/d beyond absolute tolerance.")
    return result(len(dataframe))
