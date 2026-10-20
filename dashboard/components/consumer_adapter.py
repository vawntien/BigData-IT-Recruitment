"""Standalone synthetic schema boundary; no loading, rendering or approval."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import localcontext

import numpy as np
import pandas as pd

from .artifact_gate import STATUS_BLOCKED, STATUS_INVALID, STATUS_MISSING, STATUS_SAMPLE
from .contract_validator import (
    ValidationIssue, ValidationResult, ValidationSpec, validate_dataset_contract,
)


@dataclass(frozen=True, slots=True)
class ConsumerIssue:
    stage: str
    code: str
    fields: tuple[str, ...]
    violation_count: int | None
    category: str


@dataclass(frozen=True, slots=True)
class ConsumerEnvelope:
    """Metadata only. schema_valid=None means not run; never authorization."""

    status: str
    schema_valid: bool | None
    demo_candidate: bool
    row_count: int | None
    structured_issues: tuple[ConsumerIssue, ...]


_SCHEMA_CODES = frozenset((
    "INVALID_SPEC", "MISSING_INPUT", "INVALID_INPUT", "INVALID_COLUMNS",
    "MISSING_COLUMNS", "EXTRA_COLUMNS", "EMPTY_DATASET", "NULL_NOT_ALLOWED",
    "TYPE_MISMATCH", "NON_FINITE", "INVALID_COUNT", "NULL_KEY", "DUPLICATE_KEY",
))


def _synthetic_marker(value):
    # Reject subclasses before equality/conversion hooks, including pd.NA.
    return (type(value) is str or type(value) is np.str_) and value == STATUS_SAMPLE


def build_synthetic_consumer_envelope(
    dataframe, schema_spec, explicit_origin, demo_enabled, origin_column,
) -> ConsumerEnvelope:
    """Describe explicitly selected synthetic input using schema checks only.

    All arguments are required; origin_column is a caller-bound field name,
    never inferred. Input must be an ordinary pandas DataFrame. Exact str and
    numpy.str_ markers are supported; custom subclasses are rejected. Marker
    claims do not establish authenticity, IT population or production rights.

    Order: argument guards, demo/origin gate, safe marker binding/row checks,
    published schema validator, safe issue conversion, metadata-only result.
    Column guards only protect marker access; schema/type/grain/count rules
    remain delegated. An empty schema PASS is BLOCKED, not a demo candidate.

    No input coercion, cleanup, mutation, source discovery, payload or business
    schema is supplied. Only schema validation is performed, not DR03C-02
    metric/relational orchestration. Existing runtime and gate are untouched.
    """
    row_count = None

    def failure(status, stage, code, category, fields=(), count=None, schema_valid=None):
        issue = ConsumerIssue(stage, code, fields, count, category)
        return ConsumerEnvelope(status, schema_valid, False, row_count, (issue,))

    if type(demo_enabled) is not bool:
        return failure(STATUS_INVALID, "configuration", "INVALID_DEMO_FLAG", "configuration")
    if type(origin_column) is not str or not origin_column.strip():
        return failure(STATUS_INVALID, "configuration", "INVALID_ORIGIN_BINDING", "configuration")
    if type(schema_spec) is not ValidationSpec:
        return failure(STATUS_INVALID, "schema", "INVALID_SPEC", "configuration", schema_valid=False)
    if dataframe is None:
        return failure(STATUS_MISSING, "input", "MISSING_INPUT", "availability")
    if type(dataframe) is not pd.DataFrame:
        return failure(STATUS_INVALID, "input", "INVALID_INPUT", "input")
    row_count = len(dataframe)
    if demo_enabled is not True:
        return failure(STATUS_BLOCKED, "origin", "DEMO_DISABLED", "source_boundary")
    if not _synthetic_marker(explicit_origin):
        return failure(STATUS_BLOCKED, "origin", "ORIGIN_BLOCKED", "source_boundary")

    # Never hash or compare unsupported column-name objects to bind provenance.
    if not all(type(name) is str or type(name) is np.str_ for name in dataframe.columns):
        return failure(STATUS_INVALID, "input", "INVALID_COLUMNS", "input")
    positions = [i for i, name in enumerate(dataframe.columns) if name == origin_column]
    if len(positions) != 1:
        code = "MISSING_ORIGIN_COLUMN" if not positions else "AMBIGUOUS_ORIGIN_COLUMN"
        return failure(STATUS_INVALID, "origin", code, "provenance", (origin_column,))
    invalid_markers = sum(not _synthetic_marker(value) for value in dataframe.iloc[:, positions[0]])
    if invalid_markers:
        return failure(STATUS_INVALID, "origin", "INVALID_ORIGIN_MARKER", "provenance",
                       (origin_column,), invalid_markers)

    # Narrow boundary around the published validator and its result conversion.
    # Unexpected Exceptions are explicit internal failures, never ordinary PASS
    # or copied exception text. BaseException (interrupt/exit) is not swallowed.
    try:
        with localcontext():
            validation = validate_dataset_contract(dataframe, schema_spec)
            if (type(validation) is not ValidationResult or type(validation.passed) is not bool
                    or type(validation.errors) is not tuple
                    or validation.passed != (not validation.errors)
                    or (validation.passed is True and (
                        type(validation.row_count) is not int
                        or validation.row_count < 0
                        or validation.row_count != row_count))):
                return failure(STATUS_INVALID, "schema", "INVALID_VALIDATOR_RESULT", "internal_failure", schema_valid=False)
            allowed_fields = set()
            if isinstance(schema_spec.fields, Mapping):
                allowed_fields = {name for name in schema_spec.fields if type(name) is str}
            issues = []
            for error in validation.errors:
                if (type(error) is not ValidationIssue or type(error.code) is not str
                        or error.code not in _SCHEMA_CODES or type(error.fields) is not tuple):
                    return failure(STATUS_INVALID, "schema", "INVALID_VALIDATOR_RESULT", "internal_failure", schema_valid=False)
                fields = tuple(name for name in error.fields if type(name) is str and name in allowed_fields)
                # The published API has no structured violation count. Preserve
                # UNKNOWN instead of parsing human-readable detail strings.
                issues.append(ConsumerIssue("schema", error.code, fields, None, "schema_validation"))
    except Exception:
        return failure(STATUS_INVALID, "schema", "SCHEMA_VALIDATOR_EXCEPTION", "internal_failure", schema_valid=False)

    if not validation.passed:
        return ConsumerEnvelope(STATUS_INVALID, False, False, row_count, tuple(issues))
    if row_count == 0:
        return failure(STATUS_BLOCKED, "availability", "EMPTY_SYNTHETIC_INPUT", "availability", schema_valid=True)
    return ConsumerEnvelope(STATUS_SAMPLE, True, True, row_count, ())
