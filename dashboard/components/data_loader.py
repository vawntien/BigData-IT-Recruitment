"""Data loader module for the Big Data IT Recruitment Dashboard.

Handles safe loading of production analytics tables (when available)
with explicit, non-silent fallback to small development sample data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Optional
import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ANALYTICS_DIR = PROJECT_ROOT / "data" / "analytics"
SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"

STATUS_PRODUCTION = "PRODUCTION"
STATUS_SAMPLE = "SAMPLE"
STATUS_MISSING = "MISSING"

MISSING_MSG = (
    "Analytics data is not available yet.\n"
    "Run the upstream pipeline (D05-D07 / A06-A08) or enable sample development mode in the sidebar."
)


def _load_table(
    table_name: str,
    sample_file_name: str,
    enable_sample_mode: bool,
) -> Tuple[Optional[pd.DataFrame], str, str]:
    """Generic table loader supporting production check and explicit sample fallback."""
    # 1. Check production analytics directory (parquet or csv)
    prod_parquet = ANALYTICS_DIR / f"{table_name}.parquet"
    prod_csv = ANALYTICS_DIR / f"{table_name}.csv"

    if prod_parquet.exists():
        try:
            df = pd.read_parquet(prod_parquet)
            return df, STATUS_PRODUCTION, f"Production data loaded from {prod_parquet.name}"
        except Exception as e:
            pass

    if prod_csv.exists():
        try:
            df = pd.read_csv(prod_csv)
            return df, STATUS_PRODUCTION, f"Production data loaded from {prod_csv.name}"
        except Exception as e:
            pass

    # 2. Check sample fallback
    if enable_sample_mode:
        sample_path = SAMPLE_DIR / sample_file_name
        if sample_path.exists():
            df = pd.read_csv(sample_path)
            return df, STATUS_SAMPLE, f"DEVELOPMENT SAMPLE MODE: Loaded synthetic data from {sample_file_name}"

    # 3. Missing data
    return None, STATUS_MISSING, MISSING_MSG


def load_overview_data(enable_sample_mode: bool = True) -> Tuple[Optional[pd.DataFrame], str, str]:
    """Load overview analytics data (jobs by category, experience, location)."""
    return _load_table(
        table_name="overview_analytics",
        sample_file_name="overview_sample.csv",
        enable_sample_mode=enable_sample_mode,
    )


def load_skills_data(enable_sample_mode: bool = True) -> Tuple[Optional[pd.DataFrame], str, str]:
    """Load technical skills analytics data (skills by job category, frequency)."""
    return _load_table(
        table_name="skills_analytics",
        sample_file_name="skills_sample.csv",
        enable_sample_mode=enable_sample_mode,
    )


def load_salary_quality_data(enable_sample_mode: bool = True) -> Tuple[Optional[pd.DataFrame], str, str]:
    """Load salary and quality analytics data."""
    return _load_table(
        table_name="salary_quality_analytics",
        sample_file_name="salary_quality_sample.csv",
        enable_sample_mode=enable_sample_mode,
    )
