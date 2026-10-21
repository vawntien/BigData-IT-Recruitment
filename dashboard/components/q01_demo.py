"""Fixed in-memory Q01 demo integration; no I/O, UI, cache or approval."""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction

import pandas as pd

from . import q01_adapter as q01
from .artifact_gate import STATUS_SAMPLE
from .contract_validator import FieldSpec, ValidationSpec
from .metric_validator import MetricValidationSpec
from .validation_orchestrator import DatasetBinding, ValidationCheck, ValidationPlan


_CATEGORIES = ("DEMO_A", "DEMO_B", "DEMO_UNKNOWN")
_CONTEXT = ("DEMO_RUN", "DEMO_POP", "DEMO_ALL")
_CHECKS = ("Schema", "Metric")
_SCOPE = "Q01_SYNTHETIC_LOGICAL"
_STAGES = frozenset(("mapping", "selection", "coverage", "origin", "input",
                     "orchestration", "logical", "internal"))
_CODES = frozenset((
    "INVALID_MAPPING", "INVALID_DEMO_PERMISSION", "DEMO_DISABLED",
    "MISSING_SOURCE", "INVALID_DATASET_BINDING", "MISSING_OR_AMBIGUOUS_SOURCE",
    "INVALID_PLAN", "PARTITION_CONTRACT_OUT_OF_SCOPE",
    "REQUIRED_SCHEMA_CHECK_MISSING", "REQUIRED_METRIC_CHECK_MISSING",
    "CHECK_COVERAGE_MISMATCH", "SCHEMA_COVERAGE_MISMATCH",
    "METRIC_COVERAGE_MISMATCH", "UNSUPPORTED_TOLERANCE", "ORIGIN_BLOCKED",
    "MISSING_OR_INVALID_SOURCE", "INVALID_COLUMNS", "MISSING_LOGICAL_COLUMNS",
    "UNSUPPORTED_IDENTITY", "UNSUPPORTED_NUMBER", "ORCHESTRATOR_EXCEPTION",
    "INVALID_ORCHESTRATION_RESULT", "ORCHESTRATION_FAILED",
    "EMPTY_ANALYTICAL_RESULT", "CONTEXT_MISMATCH", "UNDECLARED_CATEGORY",
    "DUPLICATE_CATEGORY", "INVALID_COUNTS", "INCONSISTENT_DENOMINATOR",
    "UNDEFINED_DENOMINATOR", "INVALID_FRACTION", "ADAPTER_EXCEPTION",
))


@dataclass(frozen=True, slots=True)
class DemoRow:
    category_id: str
    count: int
    share_percent: Fraction


@dataclass(frozen=True, slots=True)
class DemoPresentation:
    status: str
    passed: bool
    population_count: int | None
    context: tuple[str, str, str] | None
    taxonomy_id: str | None
    rows: tuple[DemoRow, ...]
    issue_codes: tuple[str, ...]


def _failure(code, status="INVALID"):
    return DemoPresentation(status, False, None, None, None, (), (code,))


def build_demo_inputs():
    """Build new borrowed inputs each time; these aliases are DEMO ONLY.

    Zero tolerance is local to this exact Decimal fixture, never a production
    policy. Overlapping artificial category counts do not establish job lineage.
    """
    frame = pd.DataFrame({
        "demo_cat": list(_CATEGORIES), "demo_n": [8, 7, 1], "demo_b": [10] * 3,
        "demo_share": [Decimal("0.8"), Decimal("0.7"), Decimal("0.1")],
        "demo_run": [_CONTEXT[0]] * 3, "demo_pop": [_CONTEXT[1]] * 3,
        "demo_filter": [_CONTEXT[2]] * 3, "source": [STATUS_SAMPLE] * 3,
    }, dtype=object)
    fields = {name: FieldSpec("integer" if name in ("demo_n", "demo_b") else
                             "number" if name == "demo_share" else "string", False)
              for name in frame.columns}
    schema = ValidationSpec(fields, tuple(fields),
                            ("demo_run", "demo_pop", "demo_filter", "demo_cat"),
                            ("demo_n", "demo_b"), False, False)
    binding = DatasetBinding("Demo", frame, schema, STATUS_SAMPLE, "source")
    metric = MetricValidationSpec("demo_n", "demo_b", "demo_share", "FRACTION",
                                  "NULL", Decimal("0"), True)
    plan = ValidationPlan((
        ValidationCheck(_CHECKS[0], "SCHEMA", ("Demo",), schema, True),
        ValidationCheck(_CHECKS[1], "METRIC", ("Demo",), metric, True),
    ))
    mapping = q01.Q01Mapping(
        "Demo", "demo_cat", "demo_n", "demo_b", "demo_share",
        ("demo_run", "demo_pop", "demo_filter"), q01.Q01Context(*_CONTEXT),
        q01.SyntheticCategoryDomain("DEMO_TAXONOMY", _CATEGORIES, "DEMO_UNKNOWN",
                                    "KEEP_IF_PRESENT", "MAY_OVERLAP"), *_CHECKS,
    )
    return (binding,), plan, mapping


def _same_strings(values, expected):
    return (type(values) is tuple and len(values) == len(expected)
            and all(type(value) is str for value in values) and values == expected)


def prepare_q01_presentation(result):
    """Guard the entire result before projecting any findings.

    This checks representation/metadata at the consumer boundary. It does not
    rerun validators or recalculate stored shares as n/B. Only run_q01_demo
    invokes the published validation pipeline; this function grants no rights.
    """
    if (type(result) is not q01.Q01ConsumerResult or type(result.passed) is not bool
            or type(result.status) is not str or type(result.logical_scope) is not str
            or result.logical_scope != _SCOPE or type(result.rows) is not tuple
            or type(result.issues) is not tuple):
        return _failure("INVALID_Q01_RESULT")
    if not result.passed:
        if (result.status not in ("BLOCKED", "INVALID") or result.rows
                or result.context is not None or result.taxonomy_id is not None
                or result.population_count is not None
                or not _same_strings(result.completed_check_ids, ()) or not result.issues):
            return _failure("INVALID_Q01_RESULT")
        codes = []
        for issue in result.issues:
            if (type(issue) is not q01.Q01Issue or type(issue.stage) is not str
                    or issue.stage not in _STAGES or type(issue.code) is not str
                    or issue.code not in _CODES or type(issue.roles) is not tuple
                    or not all(type(role) is str for role in issue.roles)
                    or (issue.violation_count is not None
                        and (type(issue.violation_count) is not int or issue.violation_count < 0))):
                return _failure("INVALID_Q01_RESULT")
            codes.append(issue.code)
        return DemoPresentation(result.status, False, None, None, None, (), tuple(codes))
    if (result.status != "SYNTHETIC_DEMO_ONLY" or result.issues
            or not _same_strings(result.completed_check_ids, _CHECKS)
            or type(result.context) is not q01.Q01Context
            or not _same_strings((result.context.run_id, result.context.population_id,
                                  result.context.filter_id), _CONTEXT)
            or type(result.taxonomy_id) is not str or result.taxonomy_id != "DEMO_TAXONOMY"
            or type(result.population_count) is not int or result.population_count != 10
            or not result.rows or len(result.rows) > len(_CATEGORIES)):
        return _failure("INVALID_Q01_RESULT")
    seen = set()
    for row in result.rows:
        if (type(row) is not q01.Q01CategoryRow or type(row.category_id) is not str
                or row.category_id not in _CATEGORIES or row.category_id in seen
                or type(row.category_count) is not int
                or not 0 <= row.category_count <= result.population_count
                or type(row.share_fraction) is not Fraction
                or type(row.share_fraction.numerator) is not int
                or type(row.share_fraction.denominator) is not int
                or row.share_fraction.denominator <= 0
                or not 0 <= row.share_fraction <= 1
                or type(row.is_unknown) is not bool
                or row.is_unknown != (row.category_id == "DEMO_UNKNOWN")):
            return _failure("INVALID_Q01_RESULT")
        seen.add(row.category_id)
    # No renderable row is created until every row has passed the guard.
    rows = tuple(DemoRow(row.category_id, row.category_count, 100 * row.share_fraction)
                 for row in result.rows)
    return DemoPresentation("SYNTHETIC_DEMO_ONLY", True, 10, _CONTEXT,
                            "DEMO_TAXONOMY", rows, ())


def run_q01_demo(demo_enabled):
    """OFF never builds inputs. ON revalidates fresh inputs without cache/state."""
    if type(demo_enabled) is not bool:
        return _failure("INVALID_DEMO_PERMISSION")
    if not demo_enabled:
        return _failure("DEMO_DISABLED", "BLOCKED")
    try:
        with localcontext():
            datasets, plan, mapping = build_demo_inputs()
            result = q01.build_q01_synthetic_view_model(datasets, plan, mapping, demo_enabled)
            return prepare_q01_presentation(result)
    except Exception:
        return _failure("DEMO_EXECUTION_EXCEPTION")
