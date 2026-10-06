"""D08 Spark Benchmark Scaffold & Development Smoke Runner.

Executes lightweight smoke workloads against clean Parquet data to validate
the benchmarking harness.
IMPORTANT: All measurements here are strictly labeled DEV_SMOKE_ONLY and
OFFICIAL = False. These do NOT represent official D08 benchmark conclusions.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding="utf-8")

from benchmark_utils import (
    BenchmarkTimer,
    benchmark_action,
    capture_partition_count,
    capture_spark_config,
    write_benchmark_results,
)
from d05_utils import aggregate_bridge, get_spark_session


def run_benchmark_smoke_suite(project_root: Path | None = None) -> List[Dict[str, Any]]:
    """Execute a set of 4 safe smoke benchmark workloads on clean Parquet data."""
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    clean_dir = project_root / "data" / "processed" / "clean"
    audit_d08_dir = project_root / "data" / "audit" / "d08"
    audit_d08_dir.mkdir(parents=True, exist_ok=True)
    smoke_output_csv = audit_d08_dir / "benchmark_smoke.csv"

    print("==================================================")
    print("STARTING D08 SPARK BENCHMARK SCAFFOLD SMOKE RUN")
    print("Notice: DEV_SMOKE_ONLY = true, OFFICIAL = false")
    print("==================================================")

    spark = get_spark_session("D08-Benchmark-Scaffold-Smoke", project_root)
    spark_conf = capture_spark_config(spark)
    print(f"Spark Version: {spark_conf['spark_version']}")
    print(f"Spark Master: {spark_conf['spark_master']}")
    print(f"Shuffle Partitions: {spark_conf['shuffle_partitions']}")

    records: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # WORKLOAD A: Read Clean Postings Parquet (Scan & Schema Materialization)
    # -------------------------------------------------------------------------
    print("\n[SMOKE A] Reading clean postings Parquet...")
    postings_path = str(clean_dir / "postings")

    with BenchmarkTimer() as timer:
        df_postings = spark.read.parquet(postings_path)
        # Materialize schema and partition metadata
        num_partitions = capture_partition_count(df_postings)

    rec_a = {
        "benchmark_id": "SMOKE_A_READ_POSTINGS",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "operation": "READ_PARQUET_POSTINGS",
        "dataset": "data/processed/clean/postings",
        "input_rows": "",
        "output_rows": "",
        "input_partitions": "",
        "output_partitions": num_partitions,
        "elapsed_seconds": round(timer.elapsed_seconds, 4),
        "spark_master": spark_conf["spark_master"],
        "spark_version": spark_conf["spark_version"],
        "shuffle_partitions": spark_conf["shuffle_partitions"],
        "dev_smoke_only": "true",
        "official": "false",
        "notes": "Metadata & schema scan only (lazy evaluation)",
    }
    records.append(rec_a)
    print(f"  -> Done in {timer.elapsed_seconds:.4f}s (partitions={num_partitions})")

    # -------------------------------------------------------------------------
    # WORKLOAD B: Count Postings (Full Scan Action)
    # -------------------------------------------------------------------------
    print("\n[SMOKE B] Full Dataset Count Action (postings.count())...")
    count_val, rec_b = benchmark_action(
        spark=spark,
        benchmark_id="SMOKE_B_COUNT_POSTINGS",
        operation="COUNT_FULL_SCAN",
        dataset="clean/postings",
        action_fn=lambda: df_postings.count(),
        input_partitions=num_partitions,
        output_partitions=num_partitions,
        dev_smoke_only=True,
        official=False,
        notes="Eager full dataset scan action",
    )
    records.append(rec_b)
    print(f"  -> Rows counted: {count_val:,} in {rec_b['elapsed_seconds']}s")

    # -------------------------------------------------------------------------
    # WORKLOAD C: Simple GroupBy Aggregation (Experience Level)
    # -------------------------------------------------------------------------
    print("\n[SMOKE C] Simple GroupBy & Aggregation (formatted_experience_level)...")
    def run_groupby():
        grouped_df = df_postings.groupBy("formatted_experience_level").count()
        return grouped_df.count()

    grp_count, rec_c = benchmark_action(
        spark=spark,
        benchmark_id="SMOKE_C_GROUPBY_EXP",
        operation="GROUPBY_EXPERIENCE_LEVEL",
        dataset="clean/postings",
        action_fn=run_groupby,
        input_rows=count_val,
        input_partitions=num_partitions,
        dev_smoke_only=True,
        official=False,
        notes="Shuffled aggregation on categorical field",
    )
    records.append(rec_c)
    print(f"  -> Unique groups: {grp_count} in {rec_c['elapsed_seconds']}s")

    # -------------------------------------------------------------------------
    # WORKLOAD D: Safe Aggregate Bridge on job_skills (collect_set & sort)
    # -------------------------------------------------------------------------
    print("\n[SMOKE D] Safe Bridge Aggregation (aggregate_bridge on job_skills)...")
    df_js = spark.read.parquet(str(clean_dir / "job_skills"))
    js_partitions = capture_partition_count(df_js)

    def run_bridge_agg():
        agg_df = aggregate_bridge(
            df=df_js,
            entity_key="job_id",
            value_column="skill_abr",
            output_column="job_function_codes",
            sort_array=True,
        )
        return agg_df.count()

    agg_count, rec_d = benchmark_action(
        spark=spark,
        benchmark_id="SMOKE_D_AGG_BRIDGE_SKILLS",
        operation="AGGREGATE_BRIDGE_ARRAY_SORT",
        dataset="clean/job_skills",
        action_fn=run_bridge_agg,
        input_partitions=js_partitions,
        dev_smoke_only=True,
        official=False,
        notes="Deterministic array aggregation (collect_set + array_sort)",
    )
    records.append(rec_d)
    print(f"  -> Distinct aggregated entities: {agg_count:,} in {rec_d['elapsed_seconds']}s")

    # Write records to CSV
    write_benchmark_results(smoke_output_csv, records)
    print(f"\nSaved smoke benchmark results to: {smoke_output_csv}")

    spark.stop()
    print("==================================================")
    print("D08 BENCHMARK SMOKE RUN COMPLETED SUCCESSFULLY")
    print("STATUS: HARNESS VALIDATED (OFFICIAL = FALSE)")
    print("==================================================")

    return records


if __name__ == "__main__":
    run_benchmark_smoke_suite()
