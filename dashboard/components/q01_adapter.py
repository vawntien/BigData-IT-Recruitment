"""Single-context Q01 synthetic projection, never an official Q01 contract.

The draft describes an intended primary-category analysis. This demo does not
establish that taxonomy, DISTINCT-job lineage, disjointness or exhaustiveness.
MAY_OVERLAP is a conservative synthetic declaration, not a change to A02.
All physical columns are caller-bound; no loaders, charts or real-data option.
"""

from dataclasses import dataclass
from decimal import localcontext
from fractions import Fraction
import re

import pandas as pd

from .artifact_gate import STATUS_SAMPLE
from .contract_validator import FieldSpec, ValidationSpec
from .cross_table_validator import CrossTableValidationSpec
from .metric_validator import MetricValidationSpec, _rational
from .partition_summary_validator import _NUMERIC_TYPES
from .validation_orchestrator import (
    DatasetBinding, ValidationPlan, ValidationCheck, OrchestrationResult,
    CheckResult, SafeIssue, run_synthetic_validation_plan,
)


@dataclass(frozen=True, slots=True)
class Q01Context:
    run_id: str
    population_id: str
    filter_id: str


@dataclass(frozen=True, slots=True)
class SyntheticCategoryDomain:
    taxonomy_id: str
    category_ids: tuple[str, ...]
    unknown_id: str
    unknown_policy: str
    overlap_policy: str


@dataclass(frozen=True, slots=True)
class Q01Mapping:
    dataset_id: str
    category_column: str
    count_column: str
    population_column: str
    fraction_column: str
    context_columns: tuple[str, str, str]
    context: Q01Context
    domain: SyntheticCategoryDomain
    schema_check_id: str
    metric_check_id: str


@dataclass(frozen=True, slots=True)
class Q01Issue:
    stage: str
    code: str
    roles: tuple[str, ...]
    violation_count: int | None


@dataclass(frozen=True, slots=True)
class Q01CategoryRow:
    category_id: str
    category_count: int
    share_fraction: Fraction
    is_unknown: bool


@dataclass(frozen=True, slots=True)
class Q01ConsumerResult:
    status: str
    passed: bool
    logical_scope: str
    context: Q01Context | None
    taxonomy_id: str | None
    population_count: int | None
    rows: tuple[Q01CategoryRow, ...]
    completed_check_ids: tuple[str, ...]
    issues: tuple[Q01Issue, ...]


def _id(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", value) is not None


def _failure(stage, code, roles=(), count=None, blocked=False):
    return Q01ConsumerResult("BLOCKED" if blocked else "INVALID", False,
                             "Q01_SYNTHETIC_LOGICAL", None, None, None, (), (),
                             (Q01Issue(stage, code, roles, count),))


def _mapping_valid(mapping):
    if type(mapping) is not Q01Mapping:
        return False
    if not all(_id(v) for v in (mapping.dataset_id, mapping.schema_check_id, mapping.metric_check_id)):
        return False
    if mapping.schema_check_id == mapping.metric_check_id or type(mapping.context_columns) is not tuple or len(mapping.context_columns) != 3:
        return False
    columns = (mapping.category_column, mapping.count_column, mapping.population_column,
               mapping.fraction_column) + mapping.context_columns
    if not all(type(c) is str and bool(c.strip()) for c in columns) or len(set(columns)) != 7:
        return False
    context, domain = mapping.context, mapping.domain
    if type(context) is not Q01Context or not all(_id(v) for v in (context.run_id, context.population_id, context.filter_id)):
        return False
    if (type(domain) is not SyntheticCategoryDomain or not _id(domain.taxonomy_id)
            or type(domain.category_ids) is not tuple or not domain.category_ids
            or not all(_id(v) for v in domain.category_ids)
            or len(set(domain.category_ids)) != len(domain.category_ids)
            or not _id(domain.unknown_id) or domain.unknown_id not in domain.category_ids):
        return False
    return (type(domain.unknown_policy) is str and domain.unknown_policy == "KEEP_IF_PRESENT"
            and type(domain.overlap_policy) is str and domain.overlap_policy == "MAY_OVERLAP")


def _coverage(datasets, plan, mapping):
    """Bind coverage to actual specs/refs, never to a check ID alone.

    Full plan validity remains delegated to the published orchestrator.
    """
    if type(datasets) is not tuple or not datasets:
        return None, "MISSING_SOURCE"
    if not all(type(b) is DatasetBinding and _id(b.dataset_id) for b in datasets):
        return None, "INVALID_DATASET_BINDING"
    matches = tuple(b for b in datasets if b.dataset_id == mapping.dataset_id)
    if len(matches) != 1:
        return None, "MISSING_OR_AMBIGUOUS_SOURCE"
    binding = matches[0]
    if type(plan) is not ValidationPlan or type(plan.checks) is not tuple:
        return None, "INVALID_PLAN"
    if not all(type(c) is ValidationCheck and _id(c.check_id) for c in plan.checks):
        return None, "INVALID_PLAN"
    if len({c.check_id for c in plan.checks}) != len(plan.checks):
        return None, "INVALID_PLAN"
    # This task has no approved Q01 partition contract. Do not execute caller
    # partition assertions as if they established category additivity.
    if any(type(c.category) is str and c.category == "PARTITION_SUMMARY" for c in plan.checks):
        return None, "PARTITION_CONTRACT_OUT_OF_SCOPE"
    chosen = []
    for check_id, category in ((mapping.schema_check_id, "SCHEMA"), (mapping.metric_check_id, "METRIC")):
        candidates = tuple(c for c in plan.checks if c.check_id == check_id)
        if not candidates:
            return None, "REQUIRED_" + category + "_CHECK_MISSING"
        check = candidates[0]
        if (type(check.category) is not str or check.category != category or check.required is not True
                or type(check.dataset_refs) is not tuple or len(check.dataset_refs) != 1
                or not _id(check.dataset_refs[0]) or check.dataset_refs[0] != mapping.dataset_id):
            return None, "CHECK_COVERAGE_MISMATCH"
        chosen.append(check)
    schema, metric = chosen[0].spec, chosen[1].spec
    if type(schema) is not ValidationSpec or schema is not binding.schema_spec:
        return None, "SCHEMA_COVERAGE_MISMATCH"
    roles = (mapping.count_column, mapping.population_column, mapping.fraction_column)
    if (type(metric) is not MetricValidationSpec
            or not all(type(v) is str for v in (metric.numerator_column, metric.denominator_column, metric.rate_column))
            or (metric.numerator_column, metric.denominator_column, metric.rate_column) != roles
            or type(metric.rate_unit) is not str or metric.rate_unit != "FRACTION"
            or metric.subset_of_population is not True):
        return None, "METRIC_COVERAGE_MISMATCH"
    # Avoid executing arbitrary numeric subclass hooks during tolerance preflight.
    if type(metric.tolerance) not in _NUMERIC_TYPES:
        return None, "UNSUPPORTED_TOLERANCE"
    if (type(schema.fields) is not dict or type(schema.required_fields) is not tuple
            or not all(type(n) is str for n in schema.required_fields)
            or type(schema.count_fields) is not tuple or not all(type(n) is str for n in schema.count_fields)
            or not all(type(n) is str for n in schema.fields)):
        return None, "SCHEMA_COVERAGE_MISMATCH"
    columns = (mapping.category_column,) + roles + mapping.context_columns
    if not set(columns) <= set(schema.required_fields) or not set(roles[:2]) <= set(schema.count_fields):
        return None, "SCHEMA_COVERAGE_MISMATCH"
    for name in columns:
        rule = schema.fields.get(name)
        expected = ("integer", "number") if name in roles[:2] else ("number",) if name == roles[2] else ("string",)
        if (type(rule) is not FieldSpec or type(rule.logical_type) is not str
                or rule.logical_type not in expected):
            return None, "SCHEMA_COVERAGE_MISMATCH"
    return binding, None


def _safe_input_boundary(binding, mapping):
    """Representation guard before schema hashing; not a second schema validator."""
    frame = binding.dataframe
    if type(frame) is not pd.DataFrame:
        return "MISSING_OR_INVALID_SOURCE"
    if not all(type(c) is str for c in frame.columns) or not frame.columns.is_unique:
        return "INVALID_COLUMNS"
    columns = (mapping.category_column, mapping.count_column, mapping.population_column,
               mapping.fraction_column) + mapping.context_columns
    if not all(c in frame.columns for c in columns):
        return "MISSING_LOGICAL_COLUMNS"
    for name in (mapping.category_column,) + mapping.context_columns:
        if any(type(v) is not str for v in frame[name]):
            return "UNSUPPORTED_IDENTITY"
    for name in (mapping.count_column, mapping.population_column, mapping.fraction_column):
        if any(v is not None and v is not pd.NA and v is not pd.NaT
               and type(v) not in _NUMERIC_TYPES for v in frame[name]):
            return "UNSUPPORTED_NUMBER"
    return None


def _counter_contract_valid(check, declared, bindings):
    """Check emitted evidence only; never rerun a validator or inspect row data.

    Orchestrator failures may have no counters after an exception/result-guard
    rejection. SAME_GRAIN structural failures emit all six counters as zero;
    ordinary comparisons report scanned rows, distinct keys and comparisons.
    These are different contracts, not interchangeable dataset row counts.
    """
    if not check.executed:
        return check.status == "BLOCKED" and check.counts == ()
    if check.status == "FAIL" and check.counts == ():
        return (len(check.issues) == 1
                and check.issues[0].code in ("VALIDATOR_EXCEPTION", "INVALID_VALIDATOR_RESULT"))
    refs = declared.dataset_refs
    lengths = tuple(len(bindings[ref].dataframe) for ref in refs)
    if declared.category in ("SCHEMA", "METRIC"):
        if check.counts != (("row_count", lengths[0]),):
            return False
        if check.status == "BLOCKED":
            return (declared.category == "SCHEMA" and lengths[0] == 0
                    and tuple(i.code for i in check.issues) == ("EMPTY_SYNTHETIC_INPUT",))
        return check.status != "PASS" or lengths[0] > 0
    if declared.category != "SAME_GRAIN" or check.status == "BLOCKED":
        return False
    names = ("left_checked_rows", "right_checked_rows", "left_key_count", "right_key_count",
             "matched_key_count", "compared_metric_count")
    # Fixed emitted order also rejects duplicates, omissions and unknown names.
    if tuple(name for name, _ in check.counts) != names:
        return False
    a, b, ka, kb, matched, compared = (value for _, value in check.counts)
    structural = any(i.code in ("INVALID_SPEC", "MISSING_INPUT", "INVALID_INPUT",
                                "INVALID_COLUMNS", "MISSING_COLUMNS") for i in check.issues)
    if (a, b) != lengths:
        return check.status == "FAIL" and structural and all(v == 0 for _, v in check.counts)
    width = len(declared.spec.metric_pairs)
    if ka > a or kb > b or matched > min(ka, kb) or compared > matched * width:
        return False
    if check.status == "PASS":
        return ka == a and kb == b and matched == ka == kb and compared == matched * width
    return True


def _evidence_bindings(datasets, plan):
    """Resolve all supported plan references with guards before hash/equality.

    Full spec/data validation belongs to the already-invoked orchestrator. Here
    only the declarations needed to interpret emitted count metadata are read.
    """
    if type(datasets) is not tuple or not datasets:
        return None
    bindings = {}
    for binding in datasets:
        if (type(binding) is not DatasetBinding or not _id(binding.dataset_id)
                or binding.dataset_id in bindings or type(binding.dataframe) is not pd.DataFrame):
            return None
        bindings[binding.dataset_id] = binding
    schemas = {}
    for declared in plan.checks:
        if (type(declared.category) is not str or declared.category not in ("SCHEMA", "METRIC", "SAME_GRAIN")
                or declared.required is not True or type(declared.dataset_refs) is not tuple
                or len(declared.dataset_refs) != (2 if declared.category == "SAME_GRAIN" else 1)
                or not all(_id(ref) and ref in bindings for ref in declared.dataset_refs)
                or len(set(declared.dataset_refs)) != len(declared.dataset_refs)):
            return None
        if declared.category == "SCHEMA":
            ref = declared.dataset_refs[0]
            if (ref in schemas or type(declared.spec) is not ValidationSpec
                    or declared.spec is not bindings[ref].schema_spec):
                return None
            schemas[ref] = declared.check_id
        elif declared.category == "METRIC":
            if type(declared.spec) is not MetricValidationSpec:
                return None
        else:
            spec = declared.spec
            if (type(spec) is not CrossTableValidationSpec or spec.require_exact_key_set is not True
                    or type(spec.metric_pairs) is not tuple or not spec.metric_pairs
                    or not all(type(pair) is tuple and len(pair) == 2
                               and all(type(name) is str for name in pair) for pair in spec.metric_pairs)):
                return None
    return (bindings, schemas) if set(schemas) == set(bindings) else None


def _evidence_valid(result, plan, mapping, datasets):
    if (type(result) is not OrchestrationResult or type(result.passed) is not bool
            or type(result.schema_scope_completed) is not bool or type(result.overall_status) is not str
            or result.overall_status not in ("INVALID_PLAN", "FAIL", "BLOCKED", "SCHEMA_ONLY_VALIDATION", "SYNTHETIC_VALIDATION_PASS")
            or type(result.check_results) is not tuple or type(result.safe_issues) is not tuple):
        return False
    for issue in result.safe_issues:
        if type(issue) is not SafeIssue or type(issue.code) is not str or type(issue.check_id) is not str:
            return False
    if result.overall_status == "INVALID_PLAN":
        # A real preflight rejection has no per-check executions or counters.
        # Its invalid declarations need not satisfy successful-plan contracts.
        return (result.passed is False and result.schema_scope_completed is False
                and result.check_results == ()
                and type(result.executed_check_ids) is tuple and result.executed_check_ids == ()
                and type(result.successful_check_ids) is tuple and result.successful_check_ids == ()
                and type(result.blocked_check_ids) is tuple and result.blocked_check_ids == ()
                and result.safe_issues == (SafeIssue("", "INVALID_PLAN"),)
                and type(result.category_statuses) is tuple
                and all(type(pair) is tuple and len(pair) == 2 and all(type(v) is str for v in pair)
                        for pair in result.category_statuses)
                and result.category_statuses == tuple((c, "NOT_REQUESTED") for c in
                    ("SCHEMA", "METRIC", "SAME_GRAIN", "PARTITION_SUMMARY")))
    resolved = _evidence_bindings(datasets, plan)
    if resolved is None:
        return False
    bindings, schemas = resolved
    planned = {c.check_id: c for c in plan.checks}
    seen = set()
    for check in result.check_results:
        if (type(check) is not CheckResult or not _id(check.check_id) or check.check_id in seen
                or check.check_id not in planned or type(check.category) is not str
                or check.category != planned[check.check_id].category
                or type(check.status) is not str or check.status not in ("PASS", "FAIL", "BLOCKED")
                or type(check.executed) is not bool or type(check.issues) is not tuple
                or type(check.counts) is not tuple):
            return False
        seen.add(check.check_id)
        if check.status == "PASS" and (not check.executed or check.issues):
            return False
        if check.status != "PASS" and not check.issues:
            return False
        for issue in check.issues:
            if type(issue) is not SafeIssue or type(issue.check_id) is not str or issue.check_id != check.check_id or type(issue.code) is not str:
                return False
        if not all(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str
                   and type(pair[1]) is int and pair[1] >= 0 for pair in check.counts):
            return False
        if not _counter_contract_valid(check, planned[check.check_id], bindings):
            return False
    for attr, expected in (
        ("executed_check_ids", tuple(c.check_id for c in result.check_results if c.executed)),
        ("successful_check_ids", tuple(c.check_id for c in result.check_results if c.status == "PASS")),
        ("blocked_check_ids", tuple(c.check_id for c in result.check_results if c.status == "BLOCKED")),
    ):
        value = getattr(result, attr)
        if type(value) is not tuple or not all(_id(v) for v in value) or value != expected:
            return False
    if seen != set(planned) or result.safe_issues != tuple(i for c in result.check_results for i in c.issues):
        return False
    by_id = {check.check_id: check for check in result.check_results}
    for check in result.check_results:
        declared = planned[check.check_id]
        if declared.category != "SCHEMA":
            ready = all(by_id[schemas[ref]].status == "PASS" for ref in declared.dataset_refs)
            if check.executed is not ready:
                return False
    success = all(c.status == "PASS" for c in result.check_results)
    schema_success = all(c.status == "PASS" for c in result.check_results if c.category == "SCHEMA")
    if result.passed != success or result.schema_scope_completed != schema_success:
        return False
    categories = []
    for category in ("SCHEMA", "METRIC", "SAME_GRAIN", "PARTITION_SUMMARY"):
        states = tuple(c.status for c in result.check_results if c.category == category)
        categories.append((category, "NOT_REQUESTED" if not states else "FAIL" if "FAIL" in states
                           else "BLOCKED" if "BLOCKED" in states else "PASS"))
    if (type(result.category_statuses) is not tuple
            or not all(type(pair) is tuple and len(pair) == 2
                       and all(type(value) is str for value in pair) for pair in result.category_statuses)
            or result.category_statuses != tuple(categories)):
        return False
    expected_status = "SYNTHETIC_VALIDATION_PASS" if success else "FAIL" if any(c.status == "FAIL" for c in result.check_results) else "BLOCKED"
    return result.overall_status == expected_status


def build_q01_synthetic_view_model(datasets, validation_plan, q01_mapping, demo_enabled):
    """Return curated aggregates only after exact configured synthetic checks.

    Context columns are ordered run/population/filter. IDs use bounded ordinary
    strings; numeric values use published bounded representations. Output shares
    preserve the validated stored fraction as an exact Fraction (no percent
    conversion). Required metrics retain caller tolerance/zero-denominator policy.
    """
    try:
        with localcontext():
            return _build(datasets, validation_plan, q01_mapping, demo_enabled)
    except Exception:
        return _failure("internal", "ADAPTER_EXCEPTION")


def _build(datasets, plan, mapping, demo):
    if not _mapping_valid(mapping):
        return _failure("mapping", "INVALID_MAPPING")
    if type(demo) is not bool:
        return _failure("selection", "INVALID_DEMO_PERMISSION")
    if not demo:
        return _failure("selection", "DEMO_DISABLED", blocked=True)
    binding, error = _coverage(datasets, plan, mapping)
    if error:
        return _failure("coverage", error)
    if type(binding.explicit_origin) is not str or binding.explicit_origin != STATUS_SAMPLE:
        return _failure("origin", "ORIGIN_BLOCKED", blocked=True)
    error = _safe_input_boundary(binding, mapping)
    if error:
        return _failure("input", error)
    try:
        result = run_synthetic_validation_plan(datasets, plan, demo)
    except Exception:
        return _failure("orchestration", "ORCHESTRATOR_EXCEPTION")
    if not _evidence_valid(result, plan, mapping, datasets):
        return _failure("orchestration", "INVALID_ORCHESTRATION_RESULT")
    if not result.passed:
        return _failure("orchestration", "ORCHESTRATION_FAILED", blocked=result.overall_status == "BLOCKED")
    # Both exact required checks are present, executed and PASS by the evidence
    # guard. No SCHEMA_ONLY, unrelated metrics or caller envelope token suffice.
    frame = binding.dataframe
    if frame.empty:
        return _failure("logical", "EMPTY_ANALYTICAL_RESULT", blocked=True)
    expected_context = (mapping.context.run_id, mapping.context.population_id, mapping.context.filter_id)
    if any(any(value != expected for value in frame[column])
           for column, expected in zip(mapping.context_columns, expected_context)):
        return _failure("logical", "CONTEXT_MISMATCH", ("context",))
    categories = tuple(frame[mapping.category_column])
    if not all(_id(value) and value in mapping.domain.category_ids for value in categories):
        return _failure("logical", "UNDECLARED_CATEGORY", ("category_id",))
    if len(set(categories)) != len(categories):
        return _failure("logical", "DUPLICATE_CATEGORY", ("category_id",))
    rows, population = [], None
    for category, raw_n, raw_b, raw_share in zip(categories, frame[mapping.count_column],
            frame[mapping.population_column], frame[mapping.fraction_column]):
        n, b, share = _rational(raw_n), _rational(raw_b), _rational(raw_share)
        if n is None or b is None or n.denominator != 1 or b.denominator != 1 or not 0 <= n <= b:
            return _failure("logical", "INVALID_COUNTS", ("category_count", "population_count"))
        if population is not None and b.numerator != population:
            return _failure("logical", "INCONSISTENT_DENOMINATOR", ("population_count",))
        population = b.numerator
        if population == 0:
            return _failure("logical", "UNDEFINED_DENOMINATOR", ("population_count",), blocked=True)
        if share is None or not 0 <= share <= 1:
            return _failure("logical", "INVALID_FRACTION", ("share_fraction",))
        rows.append(Q01CategoryRow(category, n.numerator, share, category == mapping.domain.unknown_id))
    return Q01ConsumerResult("SYNTHETIC_DEMO_ONLY", True, "Q01_SYNTHETIC_LOGICAL",
                             mapping.context, mapping.domain.taxonomy_id, population, tuple(rows),
                             (mapping.schema_check_id, mapping.metric_check_id), ())
