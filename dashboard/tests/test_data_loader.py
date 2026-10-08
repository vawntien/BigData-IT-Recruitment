"""Automated tests for data loader behavior and safety guards."""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DASHBOARD_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from components.data_loader import (
    load_overview_data,
    load_skills_data,
    load_salary_quality_data,
    STATUS_SAMPLE,
    STATUS_MISSING,
    STATUS_PRODUCTION,
    ANALYTICS_DIR,
)


def test_sample_mode_enabled():
    """Verify data loader successfully returns sample data when sample_mode is True."""
    df_ov, status_ov, _ = load_overview_data(enable_sample_mode=True)
    assert df_ov is not None, "Overview dataframe should not be None in sample mode"
    assert not df_ov.empty, "Overview sample should not be empty"
    assert status_ov in (STATUS_SAMPLE, STATUS_PRODUCTION)

    df_sk, status_sk, _ = load_skills_data(enable_sample_mode=True)
    assert df_sk is not None, "Skills dataframe should not be None in sample mode"
    assert not df_sk.empty, "Skills sample should not be empty"
    assert status_sk in (STATUS_SAMPLE, STATUS_PRODUCTION)

    df_sq, status_sq, _ = load_salary_quality_data(enable_sample_mode=True)
    assert df_sq is not None, "Salary/Quality dataframe should not be None in sample mode"
    assert not df_sq.empty, "Salary/Quality sample should not be empty"
    assert status_sq in (STATUS_SAMPLE, STATUS_PRODUCTION)
    print("  [PASS] test_sample_mode_enabled passed.")


def test_missing_data_behavior():
    """Verify data loader cleanly returns MISSING status without crashing when sample_mode is False."""
    # When no production file exists in data/analytics/
    has_prod_overview = (ANALYTICS_DIR / "overview_analytics.parquet").exists() or (ANALYTICS_DIR / "overview_analytics.csv").exists()

    if not has_prod_overview:
        df, status, msg = load_overview_data(enable_sample_mode=False)
        assert df is None, "Dataframe should be None when production data missing and sample_mode False"
        assert status == STATUS_MISSING, f"Expected STATUS_MISSING, got {status}"
        assert "not available yet" in msg.lower(), "Message should explain that data is not available yet"
        print("  [PASS] test_missing_data_behavior passed.")
    else:
        print("  [SKIP] Production overview data exists; skipping missing-data check.")


def test_no_raw_data_access():
    """Verify dashboard data loader never attempts to read data/raw/."""
    from components import data_loader
    source_code = Path(data_loader.__file__).read_text(encoding="utf-8")
    assert "data/raw" not in source_code and "data\\raw" not in source_code, (
        "data_loader.py must NOT access data/raw directly!"
    )
    print("  [PASS] test_no_raw_data_access passed.")


def main():
    print("Running test_data_loader.py...")
    test_sample_mode_enabled()
    test_missing_data_behavior()
    test_no_raw_data_access()
    print("All data_loader tests PASSED successfully.")


if __name__ == "__main__":
    main()
