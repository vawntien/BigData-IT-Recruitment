"""D09 Pipeline Validation Scaffold runner.

Executes all currently verifiable checks against clean Parquet data,
verifies D05 scaffold grain preservation, and registers pending assertions
for unbuilt pipeline stages (D06, D07, D08, Final Analytics).
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

# Force utf-8 stdout
sys.stdout.reconfigure(encoding="utf-8")

from d05_utils import get_spark_session
from d05_prejoin_validation import (
    validate_bridge_aggregations,
    validate_latest_employee_counts,
    validate_safe_company_join,
    validate_safe_postings_join,
    validate_safe_salary_join,
)
from validation_utils import (
    ValidationRecord,
    check_allowed_values,
    check_file_exists,
    check_no_duplicate_grain,
    check_not_null_key,
    check_reconciliation,
    check_row_count,
    check_synthetic_leakage,
    check_unique_key,
    create_pending_record,
    write_validation_results,
)


def run_d09_scaffold() -> tuple[list[ValidationRecord], dict[str, int]]:
    project_root = Path(__file__).resolve().parent.parent
    clean_dir = project_root / "data" / "processed" / "clean"
    audit_dir = project_root / "data" / "audit"
    results_csv = audit_dir / "d09" / "validation_scaffold_results.csv"

    records: list[ValidationRecord] = []

    print("==================================================")
    print("STARTING D09 FINAL PIPELINE VALIDATION SCAFFOLD")
    print("Note: This is a scaffold run; official=False")
    print("==================================================")

    # ----------------------------------------------------
    # SECTION 1: VERIFIED CHECKS (D01-D04 Clean Parquet Integrity)
    # ----------------------------------------------------
    print("\n--- Executing Stage D01-D04 Integrity Checks ---")

    # 1.1 Audit trail reconciliation
    etl_summary_path = audit_dir / "d04_etl_summary.csv"
    records.append(
        check_file_exists(
            etl_summary_path,
            validation_id="D09-AUDIT-01",
            stage="D04_INTEGRITY",
            dataset="audit_trail",
        )
    )

    etl_summary_rows = {}
    if etl_summary_path.exists():
        with open(etl_summary_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                etl_summary_rows[row["table"]] = {
                    "input": int(row["input_rows"]),
                    "output": int(row["output_rows"]),
                    "rejected": int(row["rejected_rows"]),
                }

    # Verify reconciliation for all 11 tables from D04 audit
    for tbl, vals in etl_summary_rows.items():
        prefix = tbl.upper()[:4]
        records.append(
            check_reconciliation(
                raw_count=vals["input"],
                clean_count=vals["output"],
                rejected_count=vals["rejected"],
                validation_id=f"D09-RECON-{prefix}",
                stage="D04_RECONCILIATION",
                dataset=tbl,
            )
        )

    # Initialize Spark
    spark = get_spark_session("D09-Validation-Scaffold", project_root)

    # 1.2 postings.parquet checks
    postings_path = clean_dir / "postings"
    records.append(
        check_file_exists(
            postings_path,
            validation_id="D09-POST-01",
            stage="D04_CLEAN_DATA",
            dataset="postings",
        )
    )
    df_postings = spark.read.parquet(str(postings_path))
    records.append(
        check_row_count(
            df_postings,
            123849,
            validation_id="D09-POST-02",
            stage="D04_CLEAN_DATA",
            dataset="postings",
        )
    )
    records.append(
        check_not_null_key(
            df_postings,
            "job_id",
            validation_id="D09-POST-03",
            stage="D04_CLEAN_DATA",
            dataset="postings",
        )
    )
    records.append(
        check_unique_key(
            df_postings,
            "job_id",
            validation_id="D09-POST-04",
            stage="D04_CLEAN_DATA",
            dataset="postings",
        )
    )

    # 1.3 companies.parquet checks
    companies_path = clean_dir / "companies"
    records.append(
        check_file_exists(
            companies_path,
            validation_id="D09-COMP-01",
            stage="D04_CLEAN_DATA",
            dataset="companies",
        )
    )
    df_companies = spark.read.parquet(str(companies_path))
    records.append(
        check_row_count(
            df_companies,
            24473,
            validation_id="D09-COMP-02",
            stage="D04_CLEAN_DATA",
            dataset="companies",
        )
    )
    records.append(
        check_not_null_key(
            df_companies,
            "company_id",
            validation_id="D09-COMP-03",
            stage="D04_CLEAN_DATA",
            dataset="companies",
        )
    )
    records.append(
        check_unique_key(
            df_companies,
            "company_id",
            validation_id="D09-COMP-04",
            stage="D04_CLEAN_DATA",
            dataset="companies",
        )
    )

    # 1.4 Allowed values in skills taxonomy table
    skills_path = clean_dir / "skills"
    records.append(
        check_file_exists(
            skills_path,
            validation_id="D09-SKIL-01",
            stage="D04_CLEAN_DATA",
            dataset="skills",
        )
    )
    df_skills = spark.read.parquet(str(skills_path))
    records.append(
        check_row_count(
            df_skills,
            35,
            validation_id="D09-SKIL-02",
            stage="D04_CLEAN_DATA",
            dataset="skills",
        )
    )

    # ----------------------------------------------------
    # SECTION 2: VERIFIED CHECKS (D05 Scaffold Transformations)
    # ----------------------------------------------------
    print("\n--- Executing Stage D05 Scaffold Contract Checks ---")

    agg_tables = validate_bridge_aggregations(clean_dir, spark)
    # Verify aggregate bridge grain
    records.append(
        check_unique_key(
            agg_tables["agg_skills"],
            "job_id",
            validation_id="D09-SCAF-01",
            stage="D05_SCAFFOLD",
            dataset="agg_skills",
        )
    )

    # Employee counts latest snapshot
    latest_ec = validate_latest_employee_counts(clean_dir, spark)
    records.append(
        check_row_count(
            latest_ec,
            24473,
            validation_id="D09-SCAF-02",
            stage="D05_SCAFFOLD",
            dataset="latest_employee_counts",
        )
    )
    records.append(
        check_unique_key(
            latest_ec,
            "company_id",
            validation_id="D09-SCAF-03",
            stage="D05_SCAFFOLD",
            dataset="latest_employee_counts",
        )
    )

    # Safe relation join grain preservation
    postings_res = validate_safe_postings_join(clean_dir, spark, agg_tables)
    records.append(
        check_no_duplicate_grain(
            postings_res["base_rows"],
            postings_res["joined_rows"],
            validation_id="D09-SCAF-04",
            stage="D05_SCAFFOLD",
            dataset="postings_bridge_join",
        )
    )

    # Safe salary join grain preservation
    salary_res = validate_safe_salary_join(clean_dir, spark)
    records.append(
        check_no_duplicate_grain(
            salary_res["base_rows"],
            salary_res["joined_rows"],
            validation_id="D09-SCAF-05",
            stage="D05_SCAFFOLD",
            dataset="postings_salary_join",
        )
    )

    # Synthetic leakage check on pipeline roots
    records.append(
        check_synthetic_leakage(
            data_source_value="AUTHENTIC_LINKEDIN",
            path_checked=str(clean_dir),
            validation_id="D09-LEAK-01",
            stage="PIPELINE_GUARD",
            dataset="clean_parquet",
        )
    )

    # ----------------------------------------------------
    # SECTION 3: PENDING CHECKS (D05 Official, D06, D07, D08, Analytics)
    # ----------------------------------------------------
    print("\n--- Registering Pending Checks for Unbuilt Stages ---")

    # D05 Official Canonical Dataset
    records.append(
        create_pending_record(
            validation_id="D09-CANON-01",
            stage="D05_OFFICIAL",
            dataset="canonical_jobs",
            check_name="canonical_row_count",
            dependency="A03 (TV2 Skill Semantics) and D05 Official Join",
            expected_description="canonical_jobs.parquet exists with exactly 123,849 rows",
        )
    )
    records.append(
        create_pending_record(
            validation_id="D09-CANON-02",
            stage="D05_OFFICIAL",
            dataset="canonical_jobs",
            check_name="canonical_unique_job_id",
            dependency="D05 Official Join",
            expected_description="123,849 unique non-null job_id",
        )
    )

    # D06 IT Classification
    records.append(
        create_pending_record(
            validation_id="D09-D06-01",
            stage="D06_IT_CLASSIFICATION",
            dataset="it_classified_jobs",
            check_name="it_flag_exists",
            dependency="D06 Pipeline Implementation",
            expected_description="Column is_it_job or it_category exists in schema",
        )
    )
    records.append(
        create_pending_record(
            validation_id="D09-D06-02",
            stage="D06_IT_CLASSIFICATION",
            dataset="it_classified_jobs",
            check_name="it_taxonomy_labels",
            dependency="D06 Pipeline Implementation",
            expected_description="IT classification labels belong to validated taxonomy subset",
        )
    )
    records.append(
        create_pending_record(
            validation_id="D09-D06-03",
            stage="D06_IT_CLASSIFICATION",
            dataset="it_classified_jobs",
            check_name="grain_preserved_after_it_tag",
            dependency="D06 Pipeline Implementation",
            expected_description="Row count remains 123,849 with 0 duplicated job_ids",
        )
    )

    # D07 Salary Normalization
    records.append(
        create_pending_record(
            validation_id="D09-D07-01",
            stage="D07_SALARY_NORMALIZATION",
            dataset="salary_normalized_jobs",
            check_name="salary_currency_period_standardization",
            dependency="D07 Salary Normalization Pipeline",
            expected_description="Annualized USD salary columns normalized with documented conversion",
        )
    )
    records.append(
        create_pending_record(
            validation_id="D09-D07-02",
            stage="D07_SALARY_NORMALIZATION",
            dataset="salary_normalized_jobs",
            check_name="salary_range_monotonicity",
            dependency="D07 Salary Normalization Pipeline",
            expected_description="min_salary <= med_salary <= max_salary when all populated",
        )
    )
    records.append(
        create_pending_record(
            validation_id="D09-D07-03",
            stage="D07_SALARY_NORMALIZATION",
            dataset="salary_normalized_jobs",
            check_name="missing_salary_null_policy",
            dependency="D07 Salary Normalization Pipeline",
            expected_description="Missing salaries remain NULL and are never replaced with 0",
        )
    )

    # D08 Spark Benchmark
    records.append(
        create_pending_record(
            validation_id="D09-D08-01",
            stage="D08_SPARK_BENCHMARK",
            dataset="benchmark_audit",
            check_name="official_benchmark_flag",
            dependency="D08 Official Benchmark Execution",
            expected_description="Official execution run with official=True and valid git commit",
        )
    )
    records.append(
        create_pending_record(
            validation_id="D09-D08-02",
            stage="D08_SPARK_BENCHMARK",
            dataset="benchmark_audit",
            check_name="minimum_measured_runs",
            dependency="D08 Official Benchmark Execution",
            expected_description=">= 3 timed runs per configuration with reported median latency",
        )
    )

    # Final Analytics & Dashboard Contract
    records.append(
        create_pending_record(
            validation_id="D09-ANLY-01",
            stage="ANALYTICS_AGGREGATION",
            dataset="gold_analytics_views",
            check_name="sample_size_greater_than_zero",
            dependency="Final Pipeline Analytics Aggregations",
            expected_description="Total aggregated job counts match official filtered population",
        )
    )
    records.append(
        create_pending_record(
            validation_id="D09-ANLY-02",
            stage="ANALYTICS_AGGREGATION",
            dataset="gold_analytics_views",
            check_name="non_negative_metrics",
            dependency="Final Pipeline Analytics Aggregations",
            expected_description="All metric counts, salary averages, and percentages >= 0",
        )
    )
    records.append(
        create_pending_record(
            validation_id="D09-DASH-01",
            stage="DASHBOARD_CONTRACT",
            dataset="dashboard_consumption_layer",
            check_name="schema_contract_conformance",
            dependency="Official Data Export for Dashboard",
            expected_description="All columns required by dashboard loader present and strictly typed",
        )
    )

    spark.stop()

    # Write output to CSV
    write_validation_results(records, results_csv)
    print(f"\n[DONE] Validation scaffold results written to: {results_csv}")

    # Summary tallies
    summary = {"PASS": 0, "FAIL": 0, "PENDING": 0, "TOTAL": len(records)}
    for r in records:
        summary[r.status] = summary.get(r.status, 0) + 1

    print("\n==================================================")
    print("D09 VALIDATION SCAFFOLD SUMMARY:")
    print(f"  TOTAL CHECKS:   {summary['TOTAL']}")
    print(f"  PASS:           {summary['PASS']}")
    print(f"  FAIL:           {summary['FAIL']}")
    print(f"  PENDING:        {summary['PENDING']}")
    print("==================================================")

    return records, summary


if __name__ == "__main__":
    run_d09_scaffold()
