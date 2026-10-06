"""Reusable benchmarking utilities and metrics recording for Apache Spark jobs.

Designed for D08 performance evaluation scaffold.
Provides timer contexts, Spark configuration capture, partition inspectors,
and standardized CSV logging.
"""

from __future__ import annotations

import csv
import datetime
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from pyspark.sql import DataFrame, SparkSession


class BenchmarkTimer:
    """Accurate wall-clock timer context manager."""

    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.elapsed_seconds: float = 0.0

    def __enter__(self) -> BenchmarkTimer:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.end_time = time.perf_counter()
        self.elapsed_seconds = max(0.0, self.end_time - self.start_time)


def capture_spark_config(spark: SparkSession) -> Dict[str, Any]:
    """Capture relevant runtime Spark environment and tuning parameters."""
    conf = spark.sparkContext.getConf()
    sql_conf = spark.conf

    return {
        "spark_version": spark.version,
        "spark_master": spark.sparkContext.master,
        "app_name": spark.sparkContext.appName,
        "shuffle_partitions": sql_conf.get("spark.sql.shuffle.partitions", "200"),
        "session_timezone": sql_conf.get("spark.sql.session.timeZone", "UTC"),
        "default_parallelism": str(spark.sparkContext.defaultParallelism),
    }


def capture_partition_count(df: DataFrame | None) -> Optional[int]:
    """Capture RDD partition count safely from a Spark DataFrame."""
    if df is None:
        return None
    try:
        return df.rdd.getNumPartitions()
    except Exception:
        return None


def create_benchmark_record(
    benchmark_id: str,
    operation: str,
    dataset: str,
    elapsed_seconds: float,
    input_rows: Optional[int] = None,
    output_rows: Optional[int] = None,
    input_partitions: Optional[int] = None,
    output_partitions: Optional[int] = None,
    spark_config: Optional[Dict[str, Any]] = None,
    dev_smoke_only: bool = True,
    official: bool = False,
    notes: str = "",
) -> Dict[str, Any]:
    """Construct a standardized benchmark observation dictionary."""
    config = spark_config or {}
    timestamp_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {
        "benchmark_id": benchmark_id,
        "timestamp_utc": timestamp_utc,
        "operation": operation,
        "dataset": dataset,
        "input_rows": input_rows if input_rows is not None else "",
        "output_rows": output_rows if output_rows is not None else "",
        "input_partitions": input_partitions if input_partitions is not None else "",
        "output_partitions": output_partitions if output_partitions is not None else "",
        "elapsed_seconds": round(elapsed_seconds, 4),
        "spark_master": config.get("spark_master", ""),
        "spark_version": config.get("spark_version", ""),
        "shuffle_partitions": config.get("shuffle_partitions", ""),
        "dev_smoke_only": "true" if dev_smoke_only else "false",
        "official": "true" if official else "false",
        "notes": notes,
    }


BENCHMARK_CSV_FIELDS = [
    "benchmark_id",
    "timestamp_utc",
    "operation",
    "dataset",
    "input_rows",
    "output_rows",
    "input_partitions",
    "output_partitions",
    "elapsed_seconds",
    "spark_master",
    "spark_version",
    "shuffle_partitions",
    "dev_smoke_only",
    "official",
    "notes",
]


def write_benchmark_results(
    filepath: Path,
    records: List[Dict[str, Any]],
    fieldnames: Optional[List[str]] = None,
) -> None:
    """Append or write benchmark records to CSV."""
    fields = fieldnames or BENCHMARK_CSV_FIELDS
    filepath.parent.mkdir(parents=True, exist_ok=True)
    write_header = not filepath.exists() or filepath.stat().st_size == 0

    with open(filepath, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerows(records)


def benchmark_action(
    spark: SparkSession,
    benchmark_id: str,
    operation: str,
    dataset: str,
    action_fn: Callable[[], Any],
    input_rows: Optional[int] = None,
    input_partitions: Optional[int] = None,
    output_partitions: Optional[int] = None,
    dev_smoke_only: bool = True,
    official: bool = False,
    notes: str = "",
) -> Tuple[Any, Dict[str, Any]]:
    """Execute a Spark action under timer, return result and benchmark record."""
    spark_config = capture_spark_config(spark)

    with BenchmarkTimer() as timer:
        result = action_fn()

    # Determine output rows if result is int or DataFrame
    output_rows = None
    if isinstance(result, int):
        output_rows = result
    elif isinstance(result, DataFrame):
        output_partitions = capture_partition_count(result)

    record = create_benchmark_record(
        benchmark_id=benchmark_id,
        operation=operation,
        dataset=dataset,
        elapsed_seconds=timer.elapsed_seconds,
        input_rows=input_rows,
        output_rows=output_rows,
        input_partitions=input_partitions,
        output_partitions=output_partitions,
        spark_config=spark_config,
        dev_smoke_only=dev_smoke_only,
        official=official,
        notes=notes,
    )

    return result, record
