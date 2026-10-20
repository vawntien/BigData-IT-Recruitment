"""Explicit partition-to-summary count checks; never business acceptance."""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pandas as pd

from .cross_table_validator import _identity
from .metric_validator import _MAX_BITS, _rational


@dataclass(frozen=True)
class PartitionSummaryValidationSpec:
    group_key_pairs: tuple[tuple[str, str], ...]
    context_pairs: tuple[tuple[str, str], ...]
    partition_column: str
    metric_pairs: tuple[tuple[str, str], ...]
    expected_partitions: tuple[object, ...]
    additive: bool
    disjoint: bool
    exhaustive: bool
    same_population_and_context: bool
    allow_empty: bool


@dataclass(frozen=True)
class PartitionSummaryValidationIssue:
    code: str
    side: str
    fields: tuple[str, ...]
    violation_count: int
    detail: str


@dataclass(frozen=True)
class PartitionSummaryValidationResult:
    """Counts of checks performed, not production eligibility or availability."""

    passed: bool
    errors: tuple[PartitionSummaryValidationIssue, ...]
    partition_checked_rows: int
    summary_checked_rows: int
    partition_group_count: int
    summary_group_count: int
    matched_group_count: int
    reconciled_group_count: int
    compared_metric_count: int


# Exact scalar types only: do not dispatch custom numeric or string hooks.
# These are computational representations, not approved business schemas.
_NUMERIC_TYPES = frozenset((int, float, Decimal, Fraction, np.int8, np.int16,
                           np.int32, np.int64, np.uint8, np.uint16, np.uint32,
                           np.uint64, np.float16, np.float32, np.float64,
                           np.longdouble, np.int_, np.uint))
_IDENTITY_TYPES = _NUMERIC_TYPES | {str, np.str_, bool, np.bool_}


def _safe_identity(value):
    if value is None or value is pd.NA or value is pd.NaT:
        return None, "NULL"
    if type(value) not in _IDENTITY_TYPES:
        return None, "INVALID"
    return _identity(value)


def _count(value):
    if type(value) not in _NUMERIC_TYPES:
        return None
    number = _rational(value)
    if number is None or number.denominator != 1 or number < 0:
        return None
    return number.numerator


def validate_partition_summary_contract(partition_dataframe, summary_dataframe, spec):
    """Validate an explicitly additive, disjoint, exhaustive count partition.

    Pair order is (partition column, summary column). Group and context pairs
    jointly define identity: contexts are never pooled, inferred or coerced.
    context_pairs=() explicitly skips additional contexts; relevant dimensions
    must then be in group keys. Declarations apply to ALL mapped count metrics.
    They must be true; their business truth cannot be established here.

    expected_partitions is a nonempty tuple of unique typed scalar identities,
    shared by every group. Missing partitions never imply zero. Duplicates and
    malformed partition rows block reconciliation of the affected group.
    Invalid counts block their metric. Summary duplicates are never selected.
    Rows are scanned columnwise, without pandas joins or record diagnostics.

    Exact supported numeric representations follow the bounded rational helper;
    custom scalar subclasses are rejected before hooks. Sum intermediates have
    the same bit bound as scalar counts. No rates, authenticity verification,
    acceptance, production capability, or dynamic per-group domain is provided.
    Reconciled groups count groups with ALL metric comparisons performed, even
    if their counts differ. Empty structural PASS is not dataset availability.
    """
    issues = {}
    stats = dict(partition_checked_rows=0, summary_checked_rows=0,
                 partition_group_count=0, summary_group_count=0,
                 matched_group_count=0, reconciled_group_count=0,
                 compared_metric_count=0)

    def issue(code, side, fields, detail, count=1):
        key = (code, side, tuple(fields), detail)
        issues[key] = issues.get(key, 0) + count

    def result():
        errors = tuple(PartitionSummaryValidationIssue(code, side, fields, count, detail)
                       for (code, side, fields, detail), count in sorted(issues.items()))
        return PartitionSummaryValidationResult(not errors, errors, **stats)

    if type(spec) is not PartitionSummaryValidationSpec:
        issue("INVALID_SPEC", "spec", (), "An explicit specification is required.")
        return result()
    for pairs, required in ((spec.group_key_pairs, True), (spec.context_pairs, False),
                            (spec.metric_pairs, True)):
        valid = type(pairs) is tuple and (bool(pairs) or not required)
        valid = valid and all(type(pair) is tuple and len(pair) == 2
                             and all(type(name) is str and bool(name.strip()) for name in pair)
                             for pair in pairs)
        if valid:
            valid = all(len({pair[i] for pair in pairs}) == len(pairs) for i in (0, 1))
        if not valid:
            issue("INVALID_SPEC", "spec", (), "Mappings require distinct nonempty column pairs.")
    if type(spec.partition_column) is not str or not spec.partition_column.strip():
        issue("INVALID_SPEC", "spec", (), "An explicit partition column is required.")
    if type(spec.allow_empty) is not bool:
        issue("INVALID_SPEC", "spec", (), "Empty-input policy must be boolean.")
    if any(value is not True for value in (spec.additive, spec.disjoint, spec.exhaustive,
                                           spec.same_population_and_context)):
        issue("INVALID_DECLARATION", "spec", (), "All count and population declarations must be true.")
    if issues:
        return result()

    identity_pairs = spec.group_key_pairs + spec.context_pairs
    mappings = identity_pairs + spec.metric_pairs
    for i in (0, 1):
        names = tuple(pair[i] for pair in mappings)
        if len(names) != len(set(names)) or (i == 0 and spec.partition_column in names):
            issue("INVALID_SPEC", "spec", (), "Column roles must not overlap on either side.")
    domain = set()
    if type(spec.expected_partitions) is not tuple or not spec.expected_partitions:
        issue("INVALID_DOMAIN", "spec", (), "Expected partition domain must be a nonempty tuple.")
    else:
        for value in spec.expected_partitions:
            token, failure = _safe_identity(value)
            if failure or token in domain:
                issue("INVALID_DOMAIN", "spec", (), "Domain identities must be supported, non-null and unique.")
            else:
                domain.add(token)
    if issues:
        return result()

    structural = True
    for i, (side, frame) in enumerate((("partition", partition_dataframe), ("summary", summary_dataframe))):
        if frame is None:
            issue("MISSING_INPUT", side, (), "No DataFrame supplied.")
            structural = False
        elif not isinstance(frame, pd.DataFrame):
            issue("INVALID_INPUT", side, (), "Expected a pandas DataFrame.")
            structural = False
        elif not all(type(c) in (str, np.str_) for c in frame.columns) or not frame.columns.is_unique:
            issue("INVALID_COLUMNS", side, (), "Column names must be unique supported strings.")
            structural = False
        else:
            required = tuple(pair[i] for pair in mappings) + ((spec.partition_column,) if i == 0 else ())
            absent = tuple(name for name in required if name not in frame.columns)
            if absent:
                issue("MISSING_COLUMNS", side, absent, "Declared columns are absent.")
                structural = False
            if len(frame) == 0 and not spec.allow_empty:
                issue("EMPTY_INPUT", side, (), "Empty tables are not permitted by spec.")
    if not structural:
        return result()

    def rows(frame, index, side):
        names = tuple(pair[index] for pair in mappings) + ((spec.partition_column,) if index == 0 else ())
        for values in zip(*(frame[name] for name in names)):
            stats[side + "_checked_rows"] += 1
            row = dict(zip(names, values))
            key, valid = [], True
            for position, pair in enumerate(identity_pairs):
                name = pair[index]
                token, failure = _safe_identity(row[name])
                if failure:
                    code = "INVALID_CONTEXT" if position >= len(spec.group_key_pairs) else (
                        "NULL_KEY" if failure == "NULL" else "INVALID_KEY")
                    issue(code, side, (name,), "Identity must be supported and non-null.")
                    valid = False
                key.append(token)
            counts = []
            for pair in spec.metric_pairs:
                name = pair[index]
                count = _count(row[name])
                if count is None:
                    issue("INVALID_COUNT", side, (name,), "Count must be a bounded nonnegative finite integer.")
                counts.append(count)
            yield tuple(key) if valid else None, counts, row

    partitions = {}
    for key, counts, row in rows(partition_dataframe, 0, "partition"):
        label, failure = _safe_identity(row[spec.partition_column])
        if failure:
            issue("NULL_PARTITION" if failure == "NULL" else "INVALID_PARTITION", "partition",
                  (spec.partition_column,), "Partition identity must be supported and non-null.")
        elif label not in domain:
            issue("UNEXPECTED_PARTITION", "partition", (spec.partition_column,), "Partition is outside the declared domain.")
        if key is None:
            continue
        observed, totals, sound = partitions.setdefault(key, (set(), [0] * len(spec.metric_pairs), [True]))
        if failure or label not in domain:
            sound[0] = False
            continue
        if label in observed:
            issue("DUPLICATE_PARTITION", "partition", tuple(p[0] for p in identity_pairs) + (spec.partition_column,),
                  "Repeated group and partition; no duplicate row is selected.")
            sound[0] = False
            continue
        observed.add(label)
        for i, count in enumerate(counts):
            if count is None or totals[i] is None:
                totals[i] = None
            else:
                total = totals[i] + count
                if total.bit_length() > _MAX_BITS:
                    issue("SUM_LIMIT", "partition", (spec.metric_pairs[i][0],), "Exact sum exceeds computational bit bound.")
                    totals[i] = None
                else:
                    totals[i] = total
    summaries, duplicate_summary = {}, set()
    for key, counts, _ in rows(summary_dataframe, 1, "summary"):
        if key is None:
            continue
        if key in summaries:
            issue("DUPLICATE_SUMMARY", "summary", tuple(p[1] for p in identity_pairs), "Repeated summary group; no row is selected.")
            duplicate_summary.add(key)
        else:
            summaries[key] = counts

    stats["partition_group_count"], stats["summary_group_count"] = len(partitions), len(summaries)
    only_partition, only_summary = partitions.keys() - summaries.keys(), summaries.keys() - partitions.keys()
    if only_partition:
        issue("PARTITION_ONLY_GROUP", "partition", tuple(p[0] for p in identity_pairs), "Group absent from summary.", len(only_partition))
    if only_summary:
        issue("SUMMARY_ONLY_GROUP", "summary", tuple(p[1] for p in identity_pairs), "Group absent from partitions.", len(only_summary))
    # Count missing domain members without constructing group x domain products.
    for observed, _, sound in partitions.values():
        missing = len(domain) - len(observed)
        if missing:
            issue("MISSING_PARTITION", "partition", (spec.partition_column,), "Expected partition rows are absent.", missing)
            sound[0] = False
    if only_summary:
        issue("MISSING_PARTITION", "partition", (spec.partition_column,), "Expected partition rows are absent.", len(only_summary) * len(domain))
    common = partitions.keys() & summaries.keys()
    stats["matched_group_count"] = len(common)
    for key in common:
        _, totals, sound = partitions[key]
        if not sound[0] or key in duplicate_summary:
            continue
        compared = 0
        for pair, total, count in zip(spec.metric_pairs, totals, summaries[key]):
            if total is not None and count is not None:
                stats["compared_metric_count"] += 1
                compared += 1
                if total != count:
                    issue("COUNT_MISMATCH", "both", pair, "Partition sum differs from summary count.")
        if compared == len(spec.metric_pairs):
            stats["reconciled_group_count"] += 1
    return result()
