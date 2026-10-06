"""Validation logic for D05 pre-join transformations and safety guards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, SparkSession, functions as F

from d05_utils import (
    aggregate_bridge,
    assert_unique_key,
    check_grain_preserved,
    latest_per_key,
    profile_join,
)


def validate_bridge_aggregations(
    clean_dir: Path,
    spark: SparkSession,
) -> dict[str, DataFrame]:
    """Test bridge aggregations on all many-to-many clean Parquet datasets.

    Neutral naming convention: job_function_codes for job_skills until A03.
    """
    df_js = spark.read.parquet(str(clean_dir / "job_skills"))
    df_ji = spark.read.parquet(str(clean_dir / "job_industries"))
    df_ben = spark.read.parquet(str(clean_dir / "benefits"))
    df_ci = spark.read.parquet(str(clean_dir / "company_industries"))
    df_cs = spark.read.parquet(str(clean_dir / "company_specialities"))

    # Neutral column names
    agg_skills = aggregate_bridge(df_js, "job_id", "skill_abr", "job_function_codes")
    agg_industries = aggregate_bridge(df_ji, "job_id", "industry_id", "industry_ids")
    agg_benefits = aggregate_bridge(df_ben, "job_id", "type", "benefit_types")
    agg_comp_ind = aggregate_bridge(df_ci, "company_id", "industry", "company_industries")
    agg_comp_spec = aggregate_bridge(df_cs, "company_id", "speciality", "company_specialities")

    # Assert uniqueness of entity keys on aggregated frames
    assert_unique_key(agg_skills, "job_id", "agg_job_skills")
    assert_unique_key(agg_industries, "job_id", "agg_job_industries")
    assert_unique_key(agg_benefits, "job_id", "agg_benefits")
    assert_unique_key(agg_comp_ind, "company_id", "agg_comp_industries")
    assert_unique_key(agg_comp_spec, "company_id", "agg_comp_specialities")

    return {
        "agg_skills": agg_skills,
        "agg_industries": agg_industries,
        "agg_benefits": agg_benefits,
        "agg_comp_ind": agg_comp_ind,
        "agg_comp_spec": agg_comp_spec,
    }


def validate_latest_employee_counts(
    clean_dir: Path,
    spark: SparkSession,
) -> DataFrame:
    """Test latest snapshot extraction on clean employee_counts.

    Verifies input = 35,665, output = exactly 24,473 distinct companies.
    """
    df_ec = spark.read.parquet(str(clean_dir / "employee_counts"))
    input_rows = df_ec.count()
    if input_rows != 35665:
        raise AssertionError(f"Expected 35,665 employee_counts rows, got {input_rows}")

    latest_ec = latest_per_key(
        df_ec,
        partition_cols="company_id",
        timestamp_col="time_recorded",
        tie_break_columns=["employee_count", "follower_count"],
    )

    output_rows = latest_ec.count()
    if output_rows != 24473:
        raise AssertionError(f"Expected 24,473 latest employee_counts, got {output_rows}")

    assert_unique_key(latest_ec, "company_id", "latest_employee_counts")
    return latest_ec


def validate_safe_postings_join(
    clean_dir: Path,
    spark: SparkSession,
    aggregated_tables: dict[str, DataFrame],
) -> dict[str, Any]:
    """Test safe LEFT JOIN of aggregated bridge tables to postings.

    Proves grain preservation: rows = 123,849, distinct job_id = 123,849.
    Does NOT write canonical dataset to disk.
    """
    df_postings = spark.read.parquet(str(clean_dir / "postings"))
    base_rows = df_postings.count()
    base_distinct_job_id = df_postings.select("job_id").distinct().count()

    joined = (
        df_postings
        .join(aggregated_tables["agg_skills"], on="job_id", how="left")
        .join(aggregated_tables["agg_industries"], on="job_id", how="left")
        .join(aggregated_tables["agg_benefits"], on="job_id", how="left")
    )

    joined_rows = joined.count()
    joined_distinct_job_id = joined.select("job_id").distinct().count()

    preserved = check_grain_preserved(
        before_count=base_rows,
        after_count=joined_rows,
        before_distinct_key=base_distinct_job_id,
        after_distinct_key=joined_distinct_job_id,
        key_name="job_id",
    )
    if not preserved:
        raise AssertionError(
            f"Grain violation! base=({base_rows}, {base_distinct_job_id}), "
            f"joined=({joined_rows}, {joined_distinct_job_id})"
        )

    return {
        "base_rows": base_rows,
        "base_distinct_job_id": base_distinct_job_id,
        "joined_rows": joined_rows,
        "joined_distinct_job_id": joined_distinct_job_id,
        "is_grain_preserved": preserved,
    }


def validate_safe_company_join(
    clean_dir: Path,
    spark: SparkSession,
    aggregated_tables: dict[str, DataFrame],
    latest_ec: DataFrame,
) -> dict[str, Any]:
    """Test safe LEFT JOIN of company attributes.

    Proves grain preservation: rows = 24,473, distinct company_id = 24,473.
    """
    df_companies = spark.read.parquet(str(clean_dir / "companies"))
    base_rows = df_companies.count()
    base_distinct_company_id = df_companies.select("company_id").distinct().count()

    joined = (
        df_companies
        .join(aggregated_tables["agg_comp_ind"], on="company_id", how="left")
        .join(aggregated_tables["agg_comp_spec"], on="company_id", how="left")
        .join(latest_ec, on="company_id", how="left")
    )

    joined_rows = joined.count()
    joined_distinct_company_id = joined.select("company_id").distinct().count()

    preserved = check_grain_preserved(
        before_count=base_rows,
        after_count=joined_rows,
        before_distinct_key=base_distinct_company_id,
        after_distinct_key=joined_distinct_company_id,
        key_name="company_id",
    )
    if not preserved:
        raise AssertionError(
            f"Company grain violation! base=({base_rows}, {base_distinct_company_id}), "
            f"joined=({joined_rows}, {joined_distinct_company_id})"
        )

    return {
        "base_rows": base_rows,
        "base_distinct_company_id": base_distinct_company_id,
        "joined_rows": joined_rows,
        "joined_distinct_company_id": joined_distinct_company_id,
        "is_grain_preserved": preserved,
    }


def validate_safe_salary_join(
    clean_dir: Path,
    spark: SparkSession,
) -> dict[str, Any]:
    """Test LEFT JOIN postings with salaries.

    Proves grain preservation: rows = 123,849, distinct job_id = 123,849.
    Does NOT perform currency/annualization/normalization (reserved for D07).
    """
    df_postings = spark.read.parquet(str(clean_dir / "postings"))
    df_salaries = spark.read.parquet(str(clean_dir / "salaries"))

    base_rows = df_postings.count()
    base_distinct = df_postings.select("job_id").distinct().count()

    joined = df_postings.join(df_salaries, on="job_id", how="left")
    joined_rows = joined.count()
    joined_distinct = joined.select("job_id").distinct().count()

    preserved = check_grain_preserved(
        before_count=base_rows,
        after_count=joined_rows,
        before_distinct_key=base_distinct,
        after_distinct_key=joined_distinct,
        key_name="job_id",
    )
    if not preserved:
        raise AssertionError(
            f"Salary join grain violation! base={base_rows}, joined={joined_rows}"
        )

    return {
        "base_rows": base_rows,
        "joined_rows": joined_rows,
        "distinct_job_id": joined_distinct,
        "is_grain_preserved": preserved,
    }


def demonstrate_unsafe_flat_join_detection(
    clean_dir: Path,
    spark: SparkSession,
) -> dict[str, Any]:
    """Demonstrate that flat unaggregated join causes row explosion and is detected."""
    df_postings = spark.read.parquet(str(clean_dir / "postings"))
    df_js = spark.read.parquet(str(clean_dir / "job_skills"))

    base_rows = df_postings.count()
    flat_joined = df_postings.join(df_js, on="job_id", how="left")
    flat_rows = flat_joined.count()

    detected_explosion = flat_rows > base_rows
    row_inflation = flat_rows - base_rows

    return {
        "base_rows": base_rows,
        "flat_rows": flat_rows,
        "row_inflation": row_inflation,
        "detected_explosion": detected_explosion,
    }
