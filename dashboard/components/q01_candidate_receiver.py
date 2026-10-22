"""Pure six-column Q01 checks for explicitly synthetic in-memory tests only.

No loader, UI, manifest, approval or production authorization API. A caller's
synthetic declaration is a test convention, never proof of data authenticity.
Counts require integer scalars (not integral floats). Rates retain their input
representation/precision. Limits below bound computation, not business policy.
"""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from math import gcd
import re

import numpy as np
import pandas as pd

from .metric_validator import _rational


COLUMNS = ("category", "job_count", "denominator_all_it", "denominator_known",
           "share_all_it", "share_known")
SYNTHETIC_ORIGIN = "SYNTHETIC_TEST_ONLY"
_MAX_ROWS = 1024
_MAX_DOMAIN = 256
_MAX_COUNT_BITS = 16384
_INT_TYPES = frozenset((int, np.int8, np.int16, np.int32, np.int64,
                        np.uint8, np.uint16, np.uint32, np.uint64))
_RATE_TYPES = _INT_TYPES | {float, Decimal, Fraction, np.float16, np.float32, np.float64}
StoredRate = int | float | Decimal | Fraction | np.integer | np.floating
_RateSnapshot = int | float | Decimal | np.integer | np.floating | tuple[int, int]


@dataclass(frozen=True, slots=True)
class SyntheticPolicy:
    origin: str
    taxonomy_id: str
    category_domain: tuple[str, ...]
    comparison: str
    tolerance: StoredRate


@dataclass(frozen=True, slots=True)
class SyntheticContext:
    origin: str
    run_id: str
    population_id: str
    filter_id: str
    taxonomy_id: str


@dataclass(frozen=True, slots=True, init=False)
class CandidateRow:
    category: str | None
    is_missing: bool
    job_count: int
    denominator_all_it: int
    denominator_known: int
    _share_all_it: _RateSnapshot
    _share_known: _RateSnapshot | None

    def __init__(self, category: str | None, is_missing: bool, job_count: int,
                 denominator_all_it: int, denominator_known: int,
                 share_all_it: StoredRate, share_known: StoredRate | None):
        # Preserve the constructor's public keywords, but retain only immutable
        # scalar snapshots. Never expose an authoritative Fraction instance.
        for name, value in (("category", category), ("is_missing", is_missing),
                            ("job_count", job_count),
                            ("denominator_all_it", denominator_all_it),
                            ("denominator_known", denominator_known),
                            ("_share_all_it", _stored(share_all_it)),
                            ("_share_known", None if share_known is None else _stored(share_known))):
            object.__setattr__(self, name, value)

    @property
    def share_all_it(self) -> StoredRate:
        return _observed(self._share_all_it)

    @property
    def share_known(self) -> StoredRate | None:
        return None if self._share_known is None else _observed(self._share_known)


@dataclass(frozen=True, slots=True)
class CandidateResult:
    status: str
    passed: bool
    rows: tuple[CandidateRow, ...]
    population_n: int | None
    known_k: int | None
    context: SyntheticContext | None
    issues: tuple[str, ...]


def _failure(code: str) -> CandidateResult:
    return CandidateResult("CANDIDATE_VALIDATION_FAILED", False, (), None, None,
                           None, (code,))


def _identifier(value: object) -> bool:
    return type(value) is str and bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value))


def _category(value: object) -> bool:
    return (type(value) is str and 0 < len(value) <= 128
            and value.strip() == value and value.isprintable())


def _fraction_parts(value: Fraction) -> tuple[int, int] | None:
    # Fraction slots can be tampered with. Check exact endpoint types before
    # arithmetic/conversion; int subclasses and bool must never run hooks.
    try:
        numerator, denominator = value.numerator, value.denominator
    except AttributeError:
        return None
    if type(numerator) is not int or type(denominator) is not int:
        return None
    if (denominator <= 0 or numerator.bit_length() > _MAX_COUNT_BITS
            or denominator.bit_length() > _MAX_COUNT_BITS
            or gcd(numerator, denominator) != 1):
        return None
    return numerator, denominator


def _number(value: object) -> Fraction | None:
    if type(value) not in _RATE_TYPES:
        return None
    if type(value) is Fraction:
        parts = _fraction_parts(value)
        return None if parts is None else _rational(Fraction(*parts))
    return _rational(value)


def _count(value: object) -> int | None:
    if type(value) not in _INT_TYPES:
        return None
    number = int(value)
    return number if 0 <= number and number.bit_length() <= _MAX_COUNT_BITS else None


def _stored(value: StoredRate) -> _RateSnapshot:
    # Other accepted scalar types are immutable; Fraction has writable slots.
    if type(value) is Fraction:
        parts = _fraction_parts(value)
        if parts is None:
            raise ValueError("Invalid Fraction representation")
        return parts
    return value


def _observed(value: _RateSnapshot) -> StoredRate:
    return Fraction(*value) if type(value) is tuple else value


def validate_q01_candidate(
    dataframe: object, policy: SyntheticPolicy | None, context: SyntheticContext | None,
) -> CandidateResult:
    """Validate an ordinary pandas DataFrame; return no rows on any failure.

    Columns bind by exact name, independent of column/row order. Only None is
    a missing category/conditional rate; pd.NA/NaN are not decoded NULL here.
    Explicit ABSOLUTE_FRACTION tolerance must be finite and in [0, 1]. This
    synthetic comparison policy is never an approved production epsilon.
    Category domains contain canonical printable strings; no normalization,
    zero-fill, rate replacement, percentage conversion or population claims.
    """
    if type(policy) is not SyntheticPolicy:
        return _failure("INVALID_SYNTHETIC_POLICY")
    if (type(policy.origin) is not str or policy.origin != SYNTHETIC_ORIGIN
            or not _identifier(policy.taxonomy_id)
            or type(policy.comparison) is not str or policy.comparison != "ABSOLUTE_FRACTION"):
        return _failure("INVALID_SYNTHETIC_POLICY")
    domain = policy.category_domain
    if (type(domain) is not tuple or not 0 < len(domain) <= _MAX_DOMAIN
            or not all(_category(v) for v in domain) or len(set(domain)) != len(domain)):
        return _failure("INVALID_SYNTHETIC_DOMAIN")
    tolerance = _number(policy.tolerance)
    if tolerance is None or not 0 <= tolerance <= 1:
        return _failure("INVALID_TEST_TOLERANCE")
    if type(context) is not SyntheticContext:
        return _failure("INVALID_SYNTHETIC_CONTEXT")
    if (type(context.origin) is not str or context.origin != SYNTHETIC_ORIGIN
            or not all(_identifier(v) for v in (context.run_id, context.population_id,
                                               context.filter_id, context.taxonomy_id))
            or context.taxonomy_id != policy.taxonomy_id):
        return _failure("INVALID_SYNTHETIC_CONTEXT")
    if type(dataframe) is not pd.DataFrame:
        return _failure("INVALID_INPUT_STRUCTURE")
    columns = tuple(dataframe.columns)
    if not all(type(v) is str for v in columns):
        return _failure("INVALID_COLUMNS")
    if len(set(columns)) != len(columns):
        return _failure("DUPLICATE_COLUMNS")
    if set(columns) != set(COLUMNS):
        return _failure("INVALID_SIX_COLUMN_SCHEMA")
    if not 0 < len(dataframe) <= _MAX_ROWS:
        return _failure("EMPTY_OR_OVERSIZED_INPUT")

    # Read columns separately; mixed row iteration can lose integer precision.
    snapshot = tuple(tuple(dataframe[name]) for name in COLUMNS)
    seen: set[str | None] = set()
    mapped = []
    population = known = None
    total = known_total = missing_total = 0
    for category, raw_n, raw_N, raw_K, all_rate, known_rate in zip(*snapshot):
        if category is not None and (not _category(category) or category not in domain):
            return _failure("INVALID_CATEGORY")
        if category in seen:
            return _failure("DUPLICATE_CATEGORY")
        seen.add(category)
        n, N, K = _count(raw_n), _count(raw_N), _count(raw_K)
        if n is None or N is None or K is None or n == 0 or N == 0 or K > N:
            return _failure("INVALID_COUNTS")
        if population is not None and (N != population or K != known):
            return _failure("INCONSISTENT_DENOMINATORS")
        population, known = N, K
        if n > N or (category is not None and (K == 0 or n > K)):
            return _failure("COUNT_EXCEEDS_POPULATION")
        all_fraction = _number(all_rate)
        if all_fraction is None or not 0 <= all_fraction <= 1:
            return _failure("INVALID_ALL_RATE")
        if abs(all_fraction - Fraction(n, N)) > tolerance:
            return _failure("INCONSISTENT_ALL_RATE")
        if category is None:
            if known_rate is not None:
                return _failure("UNEXPECTED_KNOWN_RATE")
            missing_total += n
        else:
            known_fraction = _number(known_rate)
            if known_fraction is None or not 0 <= known_fraction <= 1:
                return _failure("INVALID_KNOWN_RATE")
            if abs(known_fraction - Fraction(n, K)) > tolerance:
                return _failure("INCONSISTENT_KNOWN_RATE")
            known_total += n
        total += n
        # For Fraction inputs retain the primitive snapshot already checked,
        # not endpoints re-read from the caller's mutable Fraction slots.
        mapped.append(CandidateRow(category, category is None, n, N, K,
                                   all_fraction if type(all_rate) is Fraction else all_rate,
                                   known_fraction if category is not None and type(known_rate) is Fraction
                                   else known_rate))
    if (total != population or known_total != known or missing_total != population - known
            or ((None in seen) != (population > known))):
        return _failure("CONSERVATION_MISMATCH")
    safe_context = SyntheticContext(context.origin, context.run_id, context.population_id,
                                    context.filter_id, context.taxonomy_id)
    return CandidateResult("CANDIDATE_VALIDATED_FOR_TEST", True, tuple(mapped),
                           population, known, safe_context, ())
