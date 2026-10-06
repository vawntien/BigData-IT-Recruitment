"""Smoke test suite for D05 implementation scaffold using pure Python assertions."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Force utf-8 stdout
sys.stdout.reconfigure(encoding="utf-8")

from d05_utils import get_spark_session
from d05_prejoin_validation import (
    demonstrate_unsafe_flat_join_detection,
    validate_bridge_aggregations,
    validate_latest_employee_counts,
    validate_safe_company_join,
    validate_safe_postings_join,
    validate_safe_salary_join,
)


def main() -> None:
    start_time = time.time()
    project_root = Path(__file__).resolve().parent.parent
    clean_dir = project_root / "data" / "processed" / "clean"
    processed_dir = project_root / "data" / "processed"

    print("==================================================")
    print("STARTING D05 SCAFFOLD VERIFICATION TEST SUITE")
    print("==================================================")

    # Record files in data/processed before test to ensure no writes occur
    processed_files_before = set(p for p in processed_dir.rglob("*") if p.is_file())

    spark = get_spark_session("D05-Scaffold-Test", project_root)

    print("\n--- TEST A: Generic Bridge Aggregation & Key Uniqueness ---")
    agg_tables = validate_bridge_aggregations(clean_dir, spark)
    print("  [PASS] All 5 many-to-many bridge tables aggregated with unique entity keys:")
    for name, df in agg_tables.items():
        count = df.count()
        cols = df.columns
        print(f"    - {name}: rows={count}, cols={cols}")

    print("\n--- TEST B: Latest Snapshot Per Key (employee_counts) ---")
    latest_ec = validate_latest_employee_counts(clean_dir, spark)
    latest_count = latest_ec.count()
    print(f"  [PASS] Latest employee_counts exactly {latest_count} rows for 24,473 companies.")
    assert latest_count == 24473, f"Expected 24473, got {latest_count}"

    print("\n--- TEST C: Safe LEFT JOIN of Aggregated Relations to Postings ---")
    postings_res = validate_safe_postings_join(clean_dir, spark, agg_tables)
    print("  [PASS] Safe relation join preserved postings grain:")
    print(f"    - Base rows: {postings_res['base_rows']:,}")
    print(f"    - Joined rows: {postings_res['joined_rows']:,}")
    print(f"    - Distinct job_id: {postings_res['joined_distinct_job_id']:,}")
    assert postings_res["base_rows"] == 123849
    assert postings_res["joined_rows"] == 123849
    assert postings_res["joined_distinct_job_id"] == 123849

    print("\n--- TEST D: Company Relations Safe JOIN ---")
    comp_res = validate_safe_company_join(clean_dir, spark, agg_tables, latest_ec)
    print("  [PASS] Safe company join preserved company grain:")
    print(f"    - Base companies: {comp_res['base_rows']:,}")
    print(f"    - Joined rows: {comp_res['joined_rows']:,}")
    print(f"    - Distinct company_id: {comp_res['joined_distinct_company_id']:,}")
    assert comp_res["base_rows"] == 24473
    assert comp_res["joined_rows"] == 24473
    assert comp_res["joined_distinct_company_id"] == 24473

    print("\n--- TEST E: Safe Salaries LEFT JOIN ---")
    salary_res = validate_safe_salary_join(clean_dir, spark)
    print("  [PASS] Salary LEFT JOIN preserved postings grain:")
    print(f"    - Base rows: {salary_res['base_rows']:,}")
    print(f"    - Joined rows: {salary_res['joined_rows']:,}")
    print(f"    - Distinct job_id: {salary_res['distinct_job_id']:,}")
    assert salary_res["base_rows"] == 123849
    assert salary_res["joined_rows"] == 123849
    assert salary_res["distinct_job_id"] == 123849

    print("\n--- TEST F: Direct Flat Join Row-Explosion Guard ---")
    unsafe_res = demonstrate_unsafe_flat_join_detection(clean_dir, spark)
    print("  [PASS] Row-explosion guard successfully detected unsafe flat join:")
    print(f"    - Base postings: {unsafe_res['base_rows']:,}")
    print(f"    - Flat joined rows: {unsafe_res['flat_rows']:,}")
    print(f"    - Row inflation (inflation detected): +{unsafe_res['row_inflation']:,} duplicate rows")
    assert unsafe_res["detected_explosion"] is True
    assert unsafe_res["row_inflation"] > 0

    print("\n--- TEST G: Clean State & No Canonical Production Output ---")
    processed_files_after = set(p for p in processed_dir.rglob("*") if p.is_file())
    new_files = processed_files_after - processed_files_before
    if new_files:
        raise AssertionError(f"Forbidden production files written to data/processed: {new_files}")
    print("  [PASS] No files written to data/processed. State is clean.")

    spark.stop()
    elapsed = time.time() - start_time
    print("\n==================================================")
    print(f"ALL TESTS PASSED SUCCESSFULLY in {elapsed:.2f}s!")
    print("STATUS: D05 SCAFFOLD = PASS")
    print("CONFIRMATION: D05 OFFICIAL NOT EXECUTED")
    print("==================================================")


if __name__ == "__main__":
    main()
