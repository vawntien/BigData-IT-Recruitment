"""Contract validation utility for incoming analytics DataFrames.

Validates schemas against the draft data contract before rendering,
preventing UI crashes caused by missing columns or unexpected types.
NOTE: This validates against the DRAFT data contract (subject to A03-A08).
"""

from __future__ import annotations

from typing import Tuple, List, Set
import pandas as pd

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
