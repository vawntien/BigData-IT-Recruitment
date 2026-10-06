"""Reusable validation assertions, contract guards, and audit loggers for D09."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from pyspark.sql import DataFrame, functions as F


@dataclass
class ValidationRecord:
    """Structured record of a single pipeline validation check."""

    validation_id: str
    stage: str
    status: str  # PASS | FAIL | PENDING
    severity: str  # BLOCKER | CRITICAL | WARNING
    dataset: str
    check_name: str
    expected: str
    actual: str
    message: str
    official: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_file_exists(
    path: Path,
    validation_id: str,
    stage: str,
    dataset: str,
    severity: str = "BLOCKER",
    official: bool = False,
) -> ValidationRecord:
    """Validate that a target path/file exists."""
    exists = path.exists()
    status = "PASS" if exists else "FAIL"
    msg = f"Path exists: {path}" if exists else f"Missing expected path: {path}"
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status=status,
        severity=severity,
        dataset=dataset,
        check_name="file_exists",
        expected=f"Path exists: {path.name}",
        actual=f"Exists: {exists}",
        message=msg,
        official=official,
    )


def check_row_count(
    df: DataFrame,
    expected_count: int,
    validation_id: str,
    stage: str,
    dataset: str,
    severity: str = "BLOCKER",
    official: bool = False,
) -> ValidationRecord:
    """Validate exact row count of a Spark DataFrame."""
    actual_count = df.count()
    status = "PASS" if actual_count == expected_count else "FAIL"
    msg = (
        f"Row count matched: {actual_count:,}"
        if status == "PASS"
        else f"Row count mismatch! Expected {expected_count:,}, got {actual_count:,}"
    )
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status=status,
        severity=severity,
        dataset=dataset,
        check_name="row_count",
        expected=str(expected_count),
        actual=str(actual_count),
        message=msg,
        official=official,
    )


def check_unique_key(
    df: DataFrame,
    key_cols: str | Sequence[str],
    validation_id: str,
    stage: str,
    dataset: str,
    severity: str = "BLOCKER",
    official: bool = False,
) -> ValidationRecord:
    """Validate that key columns are strictly unique."""
    keys = [key_cols] if isinstance(key_cols, str) else list(key_cols)
    total_count = df.count()
    distinct_count = df.select(*keys).distinct().count()
    status = "PASS" if total_count == distinct_count else "FAIL"
    diff = total_count - distinct_count
    msg = (
        f"Key ({', '.join(keys)}) is unique across {total_count:,} rows"
        if status == "PASS"
        else f"Key ({', '.join(keys)}) has {diff:,} duplicate rows ({total_count:,} vs {distinct_count:,})"
    )
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status=status,
        severity=severity,
        dataset=dataset,
        check_name="unique_key",
        expected=f"{total_count} distinct keys",
        actual=f"{distinct_count} distinct keys",
        message=msg,
        official=official,
    )


def check_not_null_key(
    df: DataFrame,
    key_cols: str | Sequence[str],
    validation_id: str,
    stage: str,
    dataset: str,
    severity: str = "BLOCKER",
    official: bool = False,
) -> ValidationRecord:
    """Validate that key columns have 0 NULL values."""
    keys = [key_cols] if isinstance(key_cols, str) else list(key_cols)
    null_cond = F.col(keys[0]).isNull()
    for k in keys[1:]:
        null_cond = null_cond | F.col(k).isNull()
    null_count = df.filter(null_cond).count()
    status = "PASS" if null_count == 0 else "FAIL"
    msg = (
        f"Key ({', '.join(keys)}) contains 0 NULL values"
        if status == "PASS"
        else f"Key ({', '.join(keys)}) contains {null_count:,} NULL values"
    )
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status=status,
        severity=severity,
        dataset=dataset,
        check_name="not_null_key",
        expected="0 NULL rows",
        actual=f"{null_count} NULL rows",
        message=msg,
        official=official,
    )


def check_reconciliation(
    raw_count: int,
    clean_count: int,
    rejected_count: int,
    validation_id: str,
    stage: str,
    dataset: str,
    severity: str = "BLOCKER",
    official: bool = False,
) -> ValidationRecord:
    """Validate row reconciliation: raw == clean + rejected."""
    sum_out = clean_count + rejected_count
    status = "PASS" if raw_count == sum_out else "FAIL"
    msg = (
        f"Reconciliation verified: raw ({raw_count:,}) == clean ({clean_count:,}) + rejected ({rejected_count:,})"
        if status == "PASS"
        else f"Reconciliation broken: raw={raw_count:,} != clean+rejected={sum_out:,} (diff={raw_count - sum_out:,})"
    )
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status=status,
        severity=severity,
        dataset=dataset,
        check_name="row_reconciliation",
        expected=f"raw == clean + rejected ({raw_count})",
        actual=f"clean+rejected = {sum_out}",
        message=msg,
        official=official,
    )


def check_no_duplicate_grain(
    before_count: int,
    after_count: int,
    validation_id: str,
    stage: str,
    dataset: str,
    severity: str = "BLOCKER",
    official: bool = False,
) -> ValidationRecord:
    """Validate that transformation/join preserved primary grain row count."""
    status = "PASS" if before_count == after_count else "FAIL"
    msg = (
        f"Grain count preserved exactly: {before_count:,} == {after_count:,}"
        if status == "PASS"
        else f"Grain explosion or loss detected: before={before_count:,}, after={after_count:,} (diff={after_count - before_count:,})"
    )
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status=status,
        severity=severity,
        dataset=dataset,
        check_name="grain_preservation",
        expected=f"{before_count} rows",
        actual=f"{after_count} rows",
        message=msg,
        official=official,
    )


def check_allowed_values(
    df: DataFrame,
    column: str,
    allowed: Iterable[Any],
    validation_id: str,
    stage: str,
    dataset: str,
    severity: str = "CRITICAL",
    allow_null: bool = True,
    official: bool = False,
) -> ValidationRecord:
    """Validate that values in a column belong to an allowed set."""
    allowed_set = set(allowed)
    target = df.filter(F.col(column).isNotNull()) if allow_null else df
    distinct_vals = [r[0] for r in target.select(column).distinct().collect()]
    disallowed = [v for v in distinct_vals if v not in allowed_set]
    status = "PASS" if not disallowed else "FAIL"
    msg = (
        f"All distinct values in '{column}' are within allowed set ({len(allowed_set)} items)"
        if status == "PASS"
        else f"Disallowed values found in '{column}': {disallowed[:10]}"
    )
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status=status,
        severity=severity,
        dataset=dataset,
        check_name="allowed_values",
        expected=f"Subset of {sorted(list(str(x) for x in allowed_set))[:5]}...",
        actual="Valid" if not disallowed else f"{len(disallowed)} unexpected values",
        message=msg,
        official=official,
    )


def check_range(
    df: DataFrame,
    column: str,
    min_val: float | int | None = None,
    max_val: float | int | None = None,
    validation_id: str = "",
    stage: str = "",
    dataset: str = "",
    severity: str = "CRITICAL",
    official: bool = False,
) -> ValidationRecord:
    """Validate numeric range constraints on a column."""
    cond = F.col(column).isNotNull()
    if min_val is not None:
        cond = cond & (F.col(column) < min_val)
    if max_val is not None:
        cond = cond | (F.col(column) > max_val)

    violating_count = df.filter(cond).count()
    status = "PASS" if violating_count == 0 else "FAIL"
    msg = (
        f"All values in '{column}' satisfy [{min_val}, {max_val}]"
        if status == "PASS"
        else f"Found {violating_count:,} rows violating range [{min_val}, {max_val}] in '{column}'"
    )
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status=status,
        severity=severity,
        dataset=dataset,
        check_name="range_check",
        expected=f"[{min_val}, {max_val}]",
        actual="All compliant" if violating_count == 0 else f"{violating_count} violations",
        message=msg,
        official=official,
    )


def check_synthetic_leakage(
    data_source_value: str | None = None,
    path_checked: str | None = None,
    validation_id: str = "D09-LEAK-01",
    stage: str = "PIPELINE_GUARD",
    dataset: str = "production_analytics",
    severity: str = "BLOCKER",
    official: bool = False,
) -> ValidationRecord:
    """Guard against mock or synthetic sample data leaking into production analytics."""
    is_synthetic_tag = (data_source_value or "").upper() == "SYNTHETIC_SAMPLE"
    is_sample_path = "sample_data" in (path_checked or "").lower()

    leakage = is_synthetic_tag or is_sample_path
    status = "FAIL" if leakage else "PASS"
    msg = (
        f"Synthetic leakage detected! source={data_source_value}, path={path_checked}"
        if leakage
        else "No synthetic sample leakage detected. Production source is authentic."
    )
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status=status,
        severity=severity,
        dataset=dataset,
        check_name="synthetic_leakage_guard",
        expected="data_source != SYNTHETIC_SAMPLE and path not containing sample_data",
        actual=f"source={data_source_value}, path={path_checked}",
        message=msg,
        official=official,
    )


def create_pending_record(
    validation_id: str,
    stage: str,
    dataset: str,
    check_name: str,
    dependency: str,
    expected_description: str,
    severity: str = "CRITICAL",
    official: bool = False,
) -> ValidationRecord:
    """Construct a standardized PENDING validation record for unbuilt pipeline stages."""
    return ValidationRecord(
        validation_id=validation_id,
        stage=stage,
        status="PENDING",
        severity=severity,
        dataset=dataset,
        check_name=check_name,
        expected=expected_description,
        actual=f"BLOCKED: Awaiting completion of {dependency}",
        message=f"Check cannot execute because dependency {dependency} has not been produced.",
        official=official,
    )


def write_validation_results(
    records: list[ValidationRecord],
    output_path: Path,
) -> None:
    """Write validation records to a standard CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "validation_id",
        "stage",
        "status",
        "severity",
        "dataset",
        "check_name",
        "expected",
        "actual",
        "official",
        "timestamp",
        "message",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))
