"""Contract validation utility for incoming analytics DataFrames.

Validates schemas against the draft data contract before rendering,
preventing UI crashes caused by missing columns or unexpected types.
NOTE: This validates against the DRAFT data contract (subject to A03-A08).
"""

from __future__ import annotations

from typing import Tuple, List, Set
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import isfinite
from numbers import Integral, Real
from typing import Mapping
import pandas as pd
from pandas.api.types import is_bool, is_scalar


@dataclass(frozen=True)
class FieldSpec:
    """Logical value rules, independent of storage dtype/physical schema.

    Supported types: string, boolean, integer, number, datetime. Integral real
    values (e.g. 1.0) are integer-compatible, but strings and booleans are not.
    Nullable numeric fields allow pandas missing sentinels, including NaN;
    finite=True rejects nonmissing infinity. Counts must be non-nullable.
    Decimal precision, timestamp timezone and business semantics are deferred.
    """

    logical_type: str
    nullable: bool
    finite: bool = True


@dataclass(frozen=True)
class ValidationSpec:
    """Caller-supplied rules only; no approved Q01-Q08 layouts are encoded."""

    fields: Mapping[str, FieldSpec]
    required_fields: tuple[str, ...]
    unique_key: tuple[str, ...]
    count_fields: tuple[str, ...]
    allow_empty: bool
    allow_extra_columns: bool


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    fields: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class ValidationResult:
    """Validation evidence only. PASS never establishes production eligibility."""

    passed: bool
    errors: tuple[ValidationIssue, ...]
    row_count: int | None


def _missing(value) -> bool:
    if isinstance(value, Decimal) and value.is_snan():
        return False  # Invalid numeric value, never an ordinary nullable sentinel.
    return is_scalar(value) and bool(pd.isna(value))


def _numeric(value) -> bool:
    return not is_bool(value) and isinstance(value, (Real, Decimal))


def _finite(value) -> bool:
    if isinstance(value, Integral):
        return True
    if isinstance(value, Decimal):
        return value.is_finite()
    return isfinite(value)


def _integer(value) -> bool:
    return _numeric(value) and _finite(value) and value == int(value)


def _compatible(value, logical_type: str) -> bool:
    if isinstance(value, Decimal) and value.is_snan():
        return False  # Reject even when the field permits non-finite numbers.
    if logical_type == "string":
        return isinstance(value, str)
    if logical_type == "boolean":
        return is_bool(value)
    if logical_type == "integer":
        return _integer(value)
    if logical_type == "number":
        return _numeric(value)
    return isinstance(value, (datetime, pd.Timestamp))


def validate_dataset_contract(
    dataframe: pd.DataFrame | None, spec: ValidationSpec
) -> ValidationResult:
    """Validate without coercion/mutation or any production acceptance decision.

    Diagnostics contain field names and violation counts, never input values
    or row labels. Empty frames still require the declared columns; only value
    checks are vacuous. Optional fields are checked when present. Key/count
    fields must explicitly be required. A required key is always non-null.
    """
    errors = []

    def issue(code, fields, detail):
        errors.append(ValidationIssue(code, tuple(fields), detail))

    if not isinstance(spec, ValidationSpec):
        issue("INVALID_SPEC", (), "Expected an explicit ValidationSpec.")
    else:
        supported = {"string", "boolean", "integer", "number", "datetime"}
        if not isinstance(spec.fields, Mapping) or not all(
            isinstance(name, str) and isinstance(rule, FieldSpec)
            and isinstance(rule.logical_type, str) and rule.logical_type in supported
            and type(rule.nullable) is bool and type(rule.finite) is bool
            for name, rule in spec.fields.items()
        ):
            issue("INVALID_SPEC", (), "Fields must declare supported types and boolean policies.")
        sequences = (spec.required_fields, spec.unique_key, spec.count_fields)
        if not all(isinstance(names, tuple) and all(isinstance(n, str) for n in names)
                   and len(names) == len(set(names)) for names in sequences):
            issue("INVALID_SPEC", (), "Field lists must be tuples of distinct names.")
        if type(spec.allow_empty) is not bool or type(spec.allow_extra_columns) is not bool:
            issue("INVALID_SPEC", (), "Empty and extra-column policies must be booleans.")
        if not errors:
            if any(n not in spec.fields for names in sequences for n in names):
                issue("INVALID_SPEC", (), "All referenced fields need explicit field rules.")
            elif not set(spec.unique_key + spec.count_fields) <= set(spec.required_fields):
                issue("INVALID_SPEC", (), "Key and count fields must be required fields.")
            elif any(spec.fields[n].nullable or spec.fields[n].logical_type not in ("integer", "number")
                     for n in spec.count_fields):
                issue("INVALID_SPEC", spec.count_fields, "Counts must declare non-nullable numeric rules.")
    if errors:
        return ValidationResult(False, tuple(errors), None)
    if dataframe is None:
        return ValidationResult(False, (ValidationIssue("MISSING_INPUT", (), "No dataset supplied."),), None)
    if not isinstance(dataframe, pd.DataFrame):
        return ValidationResult(False, (ValidationIssue("INVALID_INPUT", (), "Expected a pandas DataFrame."),), None)
    row_count = len(dataframe)
    if not dataframe.columns.is_unique or not all(isinstance(c, str) for c in dataframe.columns):
        return ValidationResult(False, (ValidationIssue("INVALID_COLUMNS", (), "Column names must be unique strings."),), row_count)
    missing = tuple(n for n in spec.required_fields if n not in dataframe.columns)
    if missing:
        issue("MISSING_COLUMNS", missing, "Required columns are absent.")
    extras = tuple(n for n in dataframe.columns if n not in spec.fields)
    if extras and not spec.allow_extra_columns:
        issue("EXTRA_COLUMNS", extras, "Undeclared columns are not permitted.")
    if row_count == 0 and not spec.allow_empty:
        issue("EMPTY_DATASET", (), "Empty datasets are not permitted by this spec.")

    invalid_key_type = False
    for name, rule in spec.fields.items():
        if name not in dataframe.columns:
            continue
        values = dataframe[name].tolist()
        nulls = sum(_missing(v) for v in values)
        if nulls and not rule.nullable:
            issue("NULL_NOT_ALLOWED", (name,), f"{nulls} missing values.")
        bad_type = sum(not _compatible(v, rule.logical_type) for v in values if not _missing(v))
        if bad_type:
            issue("TYPE_MISMATCH", (name,), f"{bad_type} incompatible values; expected {rule.logical_type}.")
            invalid_key_type |= name in spec.unique_key
        if rule.logical_type in ("integer", "number") and rule.finite:
            nonfinite = sum(_numeric(v) and not _finite(v) for v in values
                            if not _missing(v) or not rule.nullable)
            if nonfinite:
                issue("NON_FINITE", (name,), f"{nonfinite} non-finite numeric values.")
        if name in spec.count_fields:
            invalid = sum(_missing(v) or not _integer(v) or v < 0 for v in values)
            if invalid:
                issue("INVALID_COUNT", (name,), f"{invalid} values are not nonnegative finite integers.")

    if spec.unique_key and not any(n not in dataframe.columns for n in spec.unique_key):
        keys = dataframe.loc[:, list(spec.unique_key)]
        null_keys = pd.DataFrame({
            name: keys[name].map(_missing).astype(bool) for name in keys.columns
        }).any(axis=1)
        if null_keys.any():
            issue("NULL_KEY", spec.unique_key, f"{int(null_keys.sum())} rows have missing key components.")
        if not invalid_key_type:
            duplicates = keys.loc[~null_keys].duplicated(keep=False)
            if duplicates.any():
                issue("DUPLICATE_KEY", spec.unique_key, f"{int(duplicates.sum())} rows share composite keys.")
    return ValidationResult(not errors, tuple(errors), row_count)

# Draft required column sets
OVERVIEW_REQUIRED_COLUMNS: Set[str] = {
    "category",
    "experience_level",
    "location",
    "work_type",
    "job_count",
}

SKILLS_REQUIRED_COLUMNS: Set[str] = {
    "category",
    "technical_skill",
    "job_count",
}

SALARY_QUALITY_REQUIRED_COLUMNS: Set[str] = {
    "category",
    "currency",
    "pay_period",
    "median_salary",
}


def _validate_schema(
    df: pd.DataFrame | None,
    required_cols: Set[str],
    dataset_name: str,
) -> Tuple[bool, List[str], List[str], str]:
    """Generic schema validation helper."""
    if df is None:
        return False, list(required_cols), [], f"{dataset_name} is None (data missing)."

    if not isinstance(df, pd.DataFrame):
        return False, list(required_cols), [], f"{dataset_name} is not a pandas DataFrame."

    if df.empty:
        return False, [], [], f"{dataset_name} is empty (0 rows)."

    actual_cols = set(df.columns)
    missing = sorted(list(required_cols - actual_cols))
    extra = sorted(list(actual_cols - required_cols))

    if missing:
        msg = f"{dataset_name} is missing required columns: {missing}"
        return False, missing, extra, msg

    return True, [], extra, f"{dataset_name} schema is valid ({len(df)} rows, {len(actual_cols)} columns)."


def validate_overview_schema(df: pd.DataFrame | None) -> Tuple[bool, List[str], List[str], str]:
    """Validate overview analytics schema."""
    return _validate_schema(df, OVERVIEW_REQUIRED_COLUMNS, "overview_analytics")


def validate_skills_schema(df: pd.DataFrame | None) -> Tuple[bool, List[str], List[str], str]:
    """Validate skills analytics schema."""
    return _validate_schema(df, SKILLS_REQUIRED_COLUMNS, "skills_analytics")


def validate_salary_quality_schema(df: pd.DataFrame | None) -> Tuple[bool, List[str], List[str], str]:
    """Validate salary & quality analytics schema."""
    return _validate_schema(df, SALARY_QUALITY_REQUIRED_COLUMNS, "salary_quality_analytics")
