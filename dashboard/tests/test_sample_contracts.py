"""Automated tests for sample data schemas and contract validation logic."""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DASHBOARD_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from components.contract_validator import (
    validate_overview_schema,
    validate_skills_schema,
    validate_salary_quality_schema,
)
from components.data_loader import SAMPLE_DIR


def test_overview_sample_contract():
    """Verify overview_sample.csv conforms to draft contract."""
    sample_file = SAMPLE_DIR / "overview_sample.csv"
    assert sample_file.exists(), "overview_sample.csv must exist"
    df = pd.read_csv(sample_file)
    assert len(df) > 0, "overview_sample.csv must have > 0 rows"

    # Schema validation
    is_valid, missing, _, msg = validate_overview_schema(df)
    assert is_valid, f"overview_sample schema validation failed: {msg}"
    assert len(missing) == 0

    # Ensure synthetic tagging
    assert "data_source" in df.columns, "overview_sample must have data_source tag column"
    assert (df["data_source"] == "SYNTHETIC_SAMPLE").all(), "All rows must be tagged SYNTHETIC_SAMPLE"
    print(f"  [PASS] test_overview_sample_contract passed ({len(df)} rows).")


def test_skills_sample_contract():
    """Verify skills_sample.csv conforms to draft contract."""
    sample_file = SAMPLE_DIR / "skills_sample.csv"
    assert sample_file.exists(), "skills_sample.csv must exist"
    df = pd.read_csv(sample_file)
    assert len(df) > 0, "skills_sample.csv must have > 0 rows"

    # Schema validation
    is_valid, missing, _, msg = validate_skills_schema(df)
    assert is_valid, f"skills_sample schema validation failed: {msg}"
    assert len(missing) == 0

    # Ensure synthetic tagging
    assert "data_source" in df.columns, "skills_sample must have data_source tag column"
    assert (df["data_source"] == "SYNTHETIC_SAMPLE").all(), "All rows must be tagged SYNTHETIC_SAMPLE"
    print(f"  [PASS] test_skills_sample_contract passed ({len(df)} rows).")


def test_salary_quality_sample_contract():
    """Verify salary_quality_sample.csv conforms to draft contract."""
    sample_file = SAMPLE_DIR / "salary_quality_sample.csv"
    assert sample_file.exists(), "salary_quality_sample.csv must exist"
    df = pd.read_csv(sample_file)
    assert len(df) > 0, "salary_quality_sample.csv must have > 0 rows"

    # Schema validation
    is_valid, missing, _, msg = validate_salary_quality_schema(df)
    assert is_valid, f"salary_quality_sample schema validation failed: {msg}"
    assert len(missing) == 0

    # Ensure synthetic tagging
    assert "data_source" in df.columns, "salary_quality_sample must have data_source tag column"
    assert (df["data_source"] == "SYNTHETIC_SAMPLE").all(), "All rows must be tagged SYNTHETIC_SAMPLE"
    print(f"  [PASS] test_salary_quality_sample_contract passed ({len(df)} rows).")


def test_validator_detects_missing_columns():
    """Verify contract validator correctly detects missing columns."""
    broken_df = pd.DataFrame({"some_other_column": [1, 2, 3]})
    is_valid, missing, _, msg = validate_overview_schema(broken_df)
    assert not is_valid, "Validator should flag missing columns"
    assert "category" in missing
    assert "job_count" in missing
    print("  [PASS] test_validator_detects_missing_columns passed.")


def main():
    print("Running test_sample_contracts.py...")
    test_overview_sample_contract()
    test_skills_sample_contract()
    test_salary_quality_sample_contract()
    test_validator_detects_missing_columns()
    print("All sample contract tests PASSED successfully.")


if __name__ == "__main__":
    main()
