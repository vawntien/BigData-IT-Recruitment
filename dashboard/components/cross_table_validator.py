"""Explicit one-to-one, same-grain count reconciliation; never acceptance."""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from numbers import Integral

import pandas as pd
from numpy import str_
from pandas.api.types import is_bool, is_float

# Reuse the existing bounded conversion only; no metric/rate policy is inferred.
from .metric_validator import _rational


@dataclass(frozen=True)
class CrossTableValidationSpec:
    key_pairs: tuple[tuple[str, str], ...]
    metric_pairs: tuple[tuple[str, str], ...]
    context_pairs: tuple[tuple[str, str], ...]
    allow_empty: bool
    require_exact_key_set: bool


@dataclass(frozen=True)
class CrossTableValidationIssue:
    code: str
    side: str
    fields: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class CrossTableValidationResult:
    """Counts describe checks performed, never production eligibility."""

    passed: bool
    errors: tuple[CrossTableValidationIssue, ...]
    left_checked_rows: int
    right_checked_rows: int
    left_key_count: int
    right_key_count: int
    matched_key_count: int
    compared_metric_count: int


def _identity(value):
    """Typed identity token or NULL/INVALID; no pandas hashing of raw objects.

    Supported families: string, boolean, integer, float, Decimal, Fraction.
    String identities accept exact built-in str and numpy.str_ only.
    Numeric families stay distinct (1, 1.0, Decimal(1), True never cross-match).
    NumPy/Pandas scalars within a family are compatible. Other representations,
    including datetime/containers, require a later explicit contract; reject.
    """
    if isinstance(value, str):
        if type(value) is not str and type(value) is not str_:
            return None, "INVALID"
        return ("string", str.__str__(value)), None
    if value is None or value is pd.NA or value is pd.NaT:
        return None, "NULL"
    if isinstance(value, Decimal) and value.is_qnan():
        return None, "NULL"
    if is_float(value) and bool(pd.isna(value)):
        return None, "NULL"
    if is_bool(value):
        return ("boolean", bool(value)), None
    if isinstance(value, Integral):
        family = "integer"
    elif is_float(value):
        family = "float"
    elif isinstance(value, Decimal):
        family = "decimal"
    elif isinstance(value, Fraction):
        family = "fraction"
    else:
        return None, "INVALID"
    number = _rational(value)
    if number is None:
        return None, "INVALID"
    return (family, number), None


def validate_cross_table_contract(left_dataframe, right_dataframe, spec):
    """Compare explicitly equivalent integer counts at exactly the same grain.

    Pairs are (left_column, right_column). All declared columns are required;
    context values are non-null typed identities checked per matched key.
    context_pairs=() deliberately requests no context checks, not evidence of
    compatible business scope. Exact key sets are mandatory in this version.
    Empty frames still require schema and allow_empty=True on both sides.
    Unknown metadata authenticity and business equivalence remain caller duties.
    No joins, aggregation, sorting, input mutation or raw-record diagnostics.
    """
    issues = {}
    stats = dict(left_checked_rows=0, right_checked_rows=0, left_key_count=0,
                 right_key_count=0, matched_key_count=0, compared_metric_count=0)

    def issue(code, side, fields, detail, count=1):
        key = (code, side, tuple(fields), detail)
        issues[key] = issues.get(key, 0) + count

    def result():
        errors = tuple(CrossTableValidationIssue(code, side, fields,
                       f"{count} violation(s): {detail}")
                       for (code, side, fields, detail), count in issues.items())
        return CrossTableValidationResult(not errors, errors, **stats)

    if not isinstance(spec, CrossTableValidationSpec):
        issue("INVALID_SPEC", "spec", (), "An explicit CrossTableValidationSpec is required.")
        return result()
    for pairs, required in ((spec.key_pairs, True), (spec.metric_pairs, True), (spec.context_pairs, False)):
        valid = isinstance(pairs, tuple) and (bool(pairs) or not required)
        valid = valid and all(isinstance(pair, tuple) and len(pair) == 2
                             and all(isinstance(name, str) and bool(name.strip()) for name in pair)
                             for pair in pairs)
        if valid:
            valid = all(len({pair[index] for pair in pairs}) == len(pairs) for index in (0, 1))
        if not valid:
            issue("INVALID_SPEC", "spec", (), "Mappings require tuples of distinct left/right column pairs.")
    if type(spec.allow_empty) is not bool or spec.require_exact_key_set is not True:
        issue("INVALID_SPEC", "spec", (), "Explicit boolean empty policy and exact key sets are required.")
    if issues:
        return result()

    mappings = spec.key_pairs + spec.context_pairs + spec.metric_pairs
    frames = (left_dataframe, right_dataframe)
    structural = True
    for index, (side, frame) in enumerate(zip(("left", "right"), frames)):
        if frame is None:
            issue("MISSING_INPUT", side, (), "No DataFrame supplied.")
            structural = False
        elif not isinstance(frame, pd.DataFrame):
            issue("INVALID_INPUT", side, (), "Expected a pandas DataFrame.")
            structural = False
        elif not all(isinstance(c, str) for c in frame.columns) or not frame.columns.is_unique:
            issue("INVALID_COLUMNS", side, (), "Column names must be unique strings.")
            structural = False
        else:
            absent = tuple(dict.fromkeys(pair[index] for pair in mappings if pair[index] not in frame.columns))
            if absent:
                issue("MISSING_COLUMNS", side, absent, "Declared key/context/metric columns are absent.")
                structural = False
            if len(frame) == 0 and not spec.allow_empty:
                issue("EMPTY_INPUT", side, (), "Empty tables are not permitted by spec.")
    if not structural:
        return result()

    def scan(frame, side, index):
        names = tuple(dict.fromkeys(pair[index] for pair in mappings))
        records = {}
        for values in zip(*(frame[name] for name in names)):
            stats[side + "_checked_rows"] += 1
            row = dict(zip(names, values))
            key, context, counts = [], [], []
            valid_key = True
            for pair in spec.key_pairs:
                name = pair[index]
                token, failure = _identity(row[name])
                if failure:
                    issue("NULL_KEY" if failure == "NULL" else "INVALID_KEY", side, (name,), "Key must have a supported non-null typed identity.")
                    valid_key = False
                key.append(token)
            for pair in spec.context_pairs:
                name = pair[index]
                token, failure = _identity(row[name])
                if failure:
                    issue("INVALID_CONTEXT", side, (name,), "Required context must have a known non-null typed identity.")
                context.append(token)
            for pair in spec.metric_pairs:
                name = pair[index]
                count = _rational(row[name])
                if count is None or count.denominator != 1 or count < 0:
                    issue("INVALID_COUNT", side, (name,), "Metric must be a supported nonnegative finite integer count.")
                    count = None
                counts.append(count)
            if valid_key:
                key = tuple(key)
                if key in records:
                    issue("DUPLICATE_KEY", side, tuple(pair[index] for pair in spec.key_pairs), "Repeated typed composite key; no rows are aggregated.")
                else:
                    records[key] = (tuple(context), tuple(counts))
        stats[side + "_key_count"] = len(records)
        return records

    left = scan(left_dataframe, "left", 0)
    right = scan(right_dataframe, "right", 1)
    only_left, only_right = left.keys() - right.keys(), right.keys() - left.keys()
    if only_left:
        issue("LEFT_ONLY_KEYS", "left", tuple(p[0] for p in spec.key_pairs), "Key absent from right table.", len(only_left))
    if only_right:
        issue("RIGHT_ONLY_KEYS", "right", tuple(p[1] for p in spec.key_pairs), "Key absent from left table.", len(only_right))
    # Duplicates invalidate one-to-one alignment; do not compare an arbitrary row.
    if any(code == "DUPLICATE_KEY" for code, _, _, _ in issues):
        return result()
    common = left.keys() & right.keys()
    stats["matched_key_count"] = len(common)
    for key in common:
        left_context, left_counts = left[key]
        right_context, right_counts = right[key]
        compatible_context = True
        for pair, lvalue, rvalue in zip(spec.context_pairs, left_context, right_context):
            if lvalue is None or rvalue is None or lvalue != rvalue:
                issue("CONTEXT_MISMATCH", "both", pair, "Declared contexts do not match for an aligned key.")
                compatible_context = False
        if compatible_context:
            for pair, lcount, rcount in zip(spec.metric_pairs, left_counts, right_counts):
                if lcount is not None and rcount is not None:
                    stats["compared_metric_count"] += 1
                    if lcount != rcount:
                        issue("COUNT_MISMATCH", "both", pair, "Declared same-grain counts differ.")
    return result()
