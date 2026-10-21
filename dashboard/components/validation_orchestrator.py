"""Explicit synthetic checks only; no loading, business mapping or UI integration.

Every dataset needs exactly one SCHEMA check, whose spec is the binding's
schema_spec (the same object). All checks are required in this version;
optional checks are rejected rather than silently omitted. Relation reference
order is left/right or partition/summary. Caller declarations are not evidence
of business truth. A successful result never authorizes production access.
"""

from dataclasses import dataclass
from decimal import localcontext
import re

import pandas as pd

from .artifact_gate import STATUS_SAMPLE
from .consumer_adapter import ConsumerEnvelope, ConsumerIssue, build_synthetic_consumer_envelope
from .contract_validator import FieldSpec, ValidationSpec
from .metric_validator import (
    MetricValidationSpec, MetricValidationResult, MetricValidationIssue,
    validate_metric_contract, _rational,
)
from .cross_table_validator import (
    CrossTableValidationSpec, CrossTableValidationResult, CrossTableValidationIssue,
    validate_cross_table_contract,
)
from .partition_summary_validator import (
    PartitionSummaryValidationSpec, PartitionSummaryValidationResult,
    PartitionSummaryValidationIssue, validate_partition_summary_contract, _safe_identity,
)


@dataclass(frozen=True, slots=True)
class DatasetBinding:
    dataset_id: str
    dataframe: pd.DataFrame
    schema_spec: ValidationSpec
    explicit_origin: str
    origin_column: str


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    check_id: str
    category: str
    dataset_refs: tuple[str, ...]
    spec: object
    required: bool


@dataclass(frozen=True, slots=True)
class ValidationPlan:
    checks: tuple[ValidationCheck, ...]


@dataclass(frozen=True, slots=True)
class SafeIssue:
    check_id: str
    code: str


@dataclass(frozen=True, slots=True)
class CheckResult:
    check_id: str
    category: str
    status: str
    executed: bool
    counts: tuple[tuple[str, int], ...]
    issues: tuple[SafeIssue, ...]


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    overall_status: str
    passed: bool
    schema_scope_completed: bool
    check_results: tuple[CheckResult, ...]
    safe_issues: tuple[SafeIssue, ...]
    executed_check_ids: tuple[str, ...]
    successful_check_ids: tuple[str, ...]
    blocked_check_ids: tuple[str, ...]
    category_statuses: tuple[tuple[str, str], ...]


_CATEGORIES = ("SCHEMA", "METRIC", "SAME_GRAIN", "PARTITION_SUMMARY")
_SCHEMA_CODES = frozenset("INVALID_SPEC MISSING_INPUT INVALID_INPUT INVALID_COLUMNS MISSING_COLUMNS EXTRA_COLUMNS EMPTY_DATASET NULL_NOT_ALLOWED TYPE_MISMATCH NON_FINITE INVALID_COUNT NULL_KEY DUPLICATE_KEY INVALID_DEMO_FLAG INVALID_ORIGIN_BINDING DEMO_DISABLED ORIGIN_BLOCKED MISSING_ORIGIN_COLUMN AMBIGUOUS_ORIGIN_COLUMN INVALID_ORIGIN_MARKER INVALID_VALIDATOR_RESULT SCHEMA_VALIDATOR_EXCEPTION EMPTY_SYNTHETIC_INPUT".split())
_METRIC_CODES = frozenset("INVALID_METRIC_SPEC MISSING_INPUT INVALID_INPUT INVALID_COLUMNS MISSING_COLUMNS INVALID_NUMERATOR INVALID_DENOMINATOR NUMERATOR_EXCEEDS_DENOMINATOR INVALID_RATE INCONSISTENT_ZERO_DENOMINATOR ZERO_DENOMINATOR_REJECTED UNDEFINED_RATE_REQUIRED RATE_OUT_OF_RANGE RATE_INCONSISTENT".split())
_SAME_CODES = frozenset("INVALID_SPEC MISSING_INPUT INVALID_INPUT INVALID_COLUMNS MISSING_COLUMNS EMPTY_INPUT NULL_KEY INVALID_KEY INVALID_CONTEXT INVALID_COUNT DUPLICATE_KEY LEFT_ONLY_KEYS RIGHT_ONLY_KEYS CONTEXT_MISMATCH COUNT_MISMATCH".split())
_PART_CODES = frozenset("INVALID_SPEC INVALID_DECLARATION INVALID_DOMAIN MISSING_INPUT INVALID_INPUT INVALID_COLUMNS MISSING_COLUMNS EMPTY_INPUT INVALID_CONTEXT NULL_KEY INVALID_KEY INVALID_COUNT NULL_PARTITION INVALID_PARTITION UNEXPECTED_PARTITION DUPLICATE_PARTITION SUM_LIMIT DUPLICATE_SUMMARY PARTITION_ONLY_GROUP SUMMARY_ONLY_GROUP MISSING_PARTITION COUNT_MISMATCH".split())


def _identifier(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", value) is not None


def _names(values, nonempty=False):
    return (type(values) is tuple and (bool(values) or not nonempty)
            and all(type(v) is str and bool(v.strip()) for v in values)
            and len(set(values)) == len(values))


def _pairs(values, nonempty):
    return (type(values) is tuple and (bool(values) or not nonempty)
            and all(type(p) is tuple and len(p) == 2
                    and all(type(n) is str and bool(n.strip()) for n in p) for p in values)
            and all(len({p[i] for p in values}) == len(values) for i in (0, 1)))


def _schema_config(spec):
    # Configuration shape only. All DataFrame/schema checks stay in the builder.
    if type(spec) is not ValidationSpec or type(spec.fields) is not dict:
        return False
    if not all(type(n) is str and type(r) is FieldSpec
               and type(r.logical_type) is str
               and r.logical_type in ("string", "boolean", "integer", "number", "datetime")
               and type(r.nullable) is bool and type(r.finite) is bool
               for n, r in spec.fields.items()):
        return False
    sequences = (spec.required_fields, spec.unique_key, spec.count_fields)
    return (all(_names(s) and set(s) <= spec.fields.keys() for s in sequences)
            and set(spec.unique_key + spec.count_fields) <= set(spec.required_fields)
            and all(not spec.fields[n].nullable
                    and spec.fields[n].logical_type in ("integer", "number") for n in spec.count_fields)
            and type(spec.allow_empty) is bool and type(spec.allow_extra_columns) is bool)


def _check_config(check):
    spec = check.spec
    if check.category == "SCHEMA":
        return _schema_config(spec)
    if check.category == "METRIC":
        if type(spec) is not MetricValidationSpec:
            return False
        tolerance = _rational(spec.tolerance)
        return (_names((spec.numerator_column, spec.denominator_column, spec.rate_column), True)
                and type(spec.rate_unit) is str and spec.rate_unit == "FRACTION"
                and type(spec.zero_denominator_policy) is str
                and spec.zero_denominator_policy in ("NULL", "REJECT")
                and type(spec.subset_of_population) is bool
                and tolerance is not None and tolerance >= 0)
    expected = CrossTableValidationSpec if check.category == "SAME_GRAIN" else PartitionSummaryValidationSpec
    if type(spec) is not expected or type(spec.allow_empty) is not bool:
        return False
    keys = spec.key_pairs if check.category == "SAME_GRAIN" else spec.group_key_pairs
    if not (_pairs(keys, True) and _pairs(spec.metric_pairs, True) and _pairs(spec.context_pairs, False)):
        return False
    mappings = keys + spec.context_pairs + spec.metric_pairs
    if any(len({p[i] for p in mappings}) != len(mappings) for i in (0, 1)):
        return False
    if check.category == "SAME_GRAIN":
        return spec.require_exact_key_set is True
    if (not all(v is True for v in (spec.additive, spec.disjoint, spec.exhaustive,
                                    spec.same_population_and_context))
            or type(spec.partition_column) is not str or not spec.partition_column.strip()
            or spec.partition_column in {p[0] for p in mappings}
            or type(spec.expected_partitions) is not tuple or not spec.expected_partitions):
        return False
    domain = set()
    for value in spec.expected_partitions:
        token, error = _safe_identity(value)
        if error or token in domain:
            return False
        domain.add(token)
    return True


def _valid_plan(datasets, plan):
    if type(datasets) is not tuple or not datasets or type(plan) is not ValidationPlan:
        return False
    if type(plan.checks) is not tuple or not plan.checks:
        return False
    bindings = {}
    for binding in datasets:
        if (type(binding) is not DatasetBinding or not _identifier(binding.dataset_id)
                or binding.dataset_id in bindings or type(binding.dataframe) is not pd.DataFrame
                or not _schema_config(binding.schema_spec)
                or type(binding.origin_column) is not str or not binding.origin_column.strip()):
            return False
        bindings[binding.dataset_id] = binding
    ids, schemas = set(), set()
    for check in plan.checks:
        if (type(check) is not ValidationCheck or not _identifier(check.check_id)
                or check.check_id in ids or type(check.category) is not str
                or check.category not in _CATEGORIES or check.required is not True
                or not _names(check.dataset_refs, True)
                or not all(_identifier(ref) and ref in bindings for ref in check.dataset_refs)
                or len(check.dataset_refs) != (1 if check.category in ("SCHEMA", "METRIC") else 2)
                or not _check_config(check)):
            return False
        ids.add(check.check_id)
        if check.category == "SCHEMA":
            ref = check.dataset_refs[0]
            if ref in schemas or check.spec is not bindings[ref].schema_spec:
                return False
            schemas.add(ref)
    return schemas == set(bindings)


def _integer(value):
    return type(value) is int and value >= 0


def _envelope(result, rows):
    if (type(result) is not ConsumerEnvelope or type(result.status) is not str
            or result.status not in (STATUS_SAMPLE, "BLOCKED", "INVALID", "MISSING")
            or type(result.demo_candidate) is not bool
            or not any(result.schema_valid is v for v in (True, False, None))
            or type(result.structured_issues) is not tuple
            or not _integer(result.row_count) or result.row_count != rows):
        raise ValueError
    for issue in result.structured_issues:
        if (type(issue) is not ConsumerIssue or type(issue.code) is not str
                or issue.code not in _SCHEMA_CODES or type(issue.fields) is not tuple
                or not all(type(f) is str for f in issue.fields)
                or type(issue.stage) is not str or issue.stage not in ("configuration", "schema", "input", "origin", "availability")
                or type(issue.category) is not str
                or issue.category not in ("configuration", "availability", "input", "source_boundary", "provenance", "internal_failure", "schema_validation")
                or (issue.violation_count is not None and not _integer(issue.violation_count))):
            raise ValueError
    if result.status == STATUS_SAMPLE:
        if not (result.schema_valid is True and result.demo_candidate is True
                and rows > 0 and not result.structured_issues):
            raise ValueError
        return "PASS", ()
    if result.demo_candidate or not result.structured_issues:
        raise ValueError
    if result.schema_valid is True and not (rows == 0 and result.status == "BLOCKED"
                                            and tuple(i.code for i in result.structured_issues) == ("EMPTY_SYNTHETIC_INPUT",)):
        raise ValueError
    return ("BLOCKED" if result.status in ("BLOCKED", "MISSING") else "FAIL",
            tuple(sorted({i.code for i in result.structured_issues})))


def _validator_result(result, category, rows, spec):
    expected, issue_type, codes = {
        "METRIC": (MetricValidationResult, MetricValidationIssue, _METRIC_CODES),
        "SAME_GRAIN": (CrossTableValidationResult, CrossTableValidationIssue, _SAME_CODES),
        "PARTITION_SUMMARY": (PartitionSummaryValidationResult, PartitionSummaryValidationIssue, _PART_CODES),
    }[category]
    if (type(result) is not expected or type(result.passed) is not bool
            or type(result.errors) is not tuple or result.passed != (not result.errors)):
        raise ValueError
    for issue in result.errors:
        if (type(issue) is not issue_type or type(issue.code) is not str or issue.code not in codes
                or type(issue.fields) is not tuple or not all(type(f) is str for f in issue.fields)
                or type(issue.detail) is not str):
            raise ValueError
        if category != "METRIC" and (type(issue.side) is not str
                or issue.side not in ("spec", "input", "left", "right", "both", "partition", "summary")):
            raise ValueError
        if category == "PARTITION_SUMMARY" and (not _integer(issue.violation_count) or issue.violation_count == 0):
            raise ValueError
    if category == "METRIC":
        if not _integer(result.row_count) or result.row_count != rows[0]:
            raise ValueError
        counts = (("row_count", result.row_count),)
    else:
        names = (("left_checked_rows", "right_checked_rows", "left_key_count", "right_key_count",
                  "matched_key_count", "compared_metric_count") if category == "SAME_GRAIN" else
                 ("partition_checked_rows", "summary_checked_rows", "partition_group_count",
                  "summary_group_count", "matched_group_count", "reconciled_group_count", "compared_metric_count"))
        values = tuple(getattr(result, n) for n in names)
        if not all(_integer(v) for v in values):
            raise ValueError
        a, b, ka, kb, matched = values[:5]
        compared = values[-1]
        # Structural failures legitimately return zero checked rows on both sides.
        structural = any(i.code in ("INVALID_SPEC", "INVALID_DECLARATION", "INVALID_DOMAIN",
                                   "MISSING_INPUT", "INVALID_INPUT", "INVALID_COLUMNS", "MISSING_COLUMNS") for i in result.errors)
        if ((a, b) != rows and not (structural and all(v == 0 for v in values))) or ka > a or kb > b or matched > min(ka, kb):
            raise ValueError
        width = len(spec.metric_pairs)
        if compared > matched * width:
            raise ValueError
        if category == "PARTITION_SUMMARY" and (values[5] > matched or values[5] * width > compared):
            raise ValueError
        if result.passed:
            if matched != ka or matched != kb or compared != matched * width:
                raise ValueError
            if category == "SAME_GRAIN" and (ka != a or kb != b):
                raise ValueError
            if category == "PARTITION_SUMMARY" and (values[5] != matched or kb != b
                    or a != ka * len(spec.expected_partitions)):
                raise ValueError
        counts = tuple(zip(names, values))
    return ("PASS" if result.passed else "FAIL", counts,
            tuple(sorted({i.code for i in result.errors})))


def _aggregate(results, invalid=False):
    results = tuple(results)
    issues = tuple(i for r in results for i in r.issues)
    if invalid:
        issues = (SafeIssue("", "INVALID_PLAN"),)
    passed = not invalid and bool(results) and all(r.status == "PASS" for r in results)
    schema = tuple(r for r in results if r.category == "SCHEMA")
    scope = bool(schema) and all(r.status == "PASS" for r in schema)
    statuses = []
    for category in _CATEGORIES:
        selected = tuple(r.status for r in results if r.category == category)
        status = ("NOT_REQUESTED" if not selected else "FAIL" if "FAIL" in selected else
                  "BLOCKED" if "BLOCKED" in selected else "PASS")
        statuses.append((category, status))
    overall = ("INVALID_PLAN" if invalid else "FAIL" if any(r.status == "FAIL" for r in results)
               else "BLOCKED" if not passed else "SCHEMA_ONLY_VALIDATION" if len(schema) == len(results)
               else "SYNTHETIC_VALIDATION_PASS")
    return OrchestrationResult(overall, passed, scope, results, issues,
                               tuple(r.check_id for r in results if r.executed),
                               tuple(r.check_id for r in results if r.status == "PASS"),
                               tuple(r.check_id for r in results if r.status == "BLOCKED"), tuple(statuses))


def run_synthetic_validation_plan(datasets, validation_plan, demo_enabled):
    """Run required explicit checks. Inputs are borrowed, never retained in results.

    Accepted containers are tuples and exact frozen dataclass instances; schema
    field maps are ordinary dicts. Plan configuration is checked before any
    validator call. Independent checks continue when their own schemas pass.
    Numeric helper calls are isolated from the caller's Decimal context.
    """
    try:
        with localcontext():
            valid = _valid_plan(datasets, validation_plan)
    except Exception:
        valid = False
    if not valid or type(demo_enabled) is not bool:
        return _aggregate((), invalid=True)
    bindings = {b.dataset_id: b for b in datasets}
    results, boundaries = [], {}
    for category in _CATEGORIES:
        for check in validation_plan.checks:
            if check.category != category:
                continue
            bound = tuple(bindings[ref] for ref in check.dataset_refs)
            counts, codes = (), ()
            executed = False
            if not demo_enabled:
                status, codes = "BLOCKED", ("DEMO_DISABLED",)
            elif category != "SCHEMA" and not all(boundaries.get(ref) == "PASS" for ref in check.dataset_refs):
                status, codes = "BLOCKED", ("DEPENDENCY_BLOCKED",)
            elif category == "SCHEMA" and not (type(bound[0].explicit_origin) is str
                                                               and bound[0].explicit_origin == STATUS_SAMPLE):
                status, codes = "BLOCKED", ("ORIGIN_BLOCKED",)
            else:
                executed = True
                try:
                    with localcontext():
                        if category == "SCHEMA":
                            b = bound[0]
                            raw = build_synthetic_consumer_envelope(b.dataframe, b.schema_spec,
                                                                   b.explicit_origin, demo_enabled, b.origin_column)
                        elif category == "METRIC":
                            raw = validate_metric_contract(bound[0].dataframe, check.spec)
                        elif category == "SAME_GRAIN":
                            raw = validate_cross_table_contract(bound[0].dataframe, bound[1].dataframe, check.spec)
                        else:
                            raw = validate_partition_summary_contract(bound[0].dataframe, bound[1].dataframe, check.spec)
                except Exception:
                    status, codes = "FAIL", ("VALIDATOR_EXCEPTION",)
                else:
                    try:
                        with localcontext():
                            if category == "SCHEMA":
                                status, codes = _envelope(raw, len(bound[0].dataframe))
                                counts = (("row_count", len(bound[0].dataframe)),)
                            else:
                                status, counts, codes = _validator_result(raw, category,
                                    tuple(len(b.dataframe) for b in bound), check.spec)
                    except Exception:
                        status, counts, codes = "FAIL", (), ("INVALID_VALIDATOR_RESULT",)
            if category == "SCHEMA":
                boundaries[check.dataset_refs[0]] = status
            results.append(CheckResult(check.check_id, category, status, executed, counts,
                                       tuple(SafeIssue(check.check_id, code) for code in codes)))
    return _aggregate(results)
