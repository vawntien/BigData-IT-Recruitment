"""Reusable Spark utilities and safety validation helpers for D05."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, SparkSession, Window, functions as F


def get_spark_session(
    app_name: str = "BigDataITRecruitment-D05-Scaffold",
    project_root: Path | None = None,
) -> SparkSession:
    """Create a standard SparkSession with UTC timezone and Windows local-FS support."""
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    builder = (
        SparkSession.builder.appName(app_name)
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
    )

    if os.name == "nt":
        localfs_adapter = project_root / "tmp" / "d04-localfs" / "d04-localfs-adapter.jar"
        if localfs_adapter.exists():
            builder = (
                builder.config("spark.driver.extraClassPath", str(localfs_adapter))
                .config("spark.executor.extraClassPath", str(localfs_adapter))
                .config("spark.hadoop.fs.file.impl", "d04.localfs.NoPermissionLocalFileSystem")
                .config("spark.hadoop.fs.file.impl.disable.cache", "true")
            )

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def aggregate_bridge(
    df: DataFrame,
    entity_key: str | list[str],
    value_column: str,
    output_column: str,
    sort_array: bool = True,
) -> DataFrame:
    """Aggregate a many-to-many bridge table into 1 row per entity key.

    - Excludes NULL values from the collected set.
    - Eliminates duplicate values per entity key.
    - Sorts the resulting array for deterministic output.
    - Does NOT introduce or hardcode business semantics.
    """
    keys = [entity_key] if isinstance(entity_key, str) else list(entity_key)

    filtered_df = df.filter(F.col(value_column).isNotNull())

    agg_expr = F.collect_set(value_column)
    if sort_array:
        agg_expr = F.array_sort(agg_expr)

    return filtered_df.groupBy(*keys).agg(agg_expr.alias(output_column))


def latest_per_key(
    df: DataFrame,
    partition_cols: str | list[str],
    timestamp_col: str,
    tie_break_columns: list[str] | None = None,
) -> DataFrame:
    """Select exactly one latest snapshot per key deterministically.

    - Uses Window.partitionBy with descending timestamp.
    - Resolves ties deterministically using tie_break_columns.
    - Guarantees exactly 1 row per partition key.
    """
    keys = [partition_cols] if isinstance(partition_cols, str) else list(partition_cols)
    order_cols = [F.col(timestamp_col).desc()]

    if tie_break_columns:
        for col_name in tie_break_columns:
            order_cols.append(F.col(col_name).asc())

    window_spec = Window.partitionBy(*keys).orderBy(*order_cols)

    ranked_df = df.withColumn("_row_num", F.row_number().over(window_spec))
    return ranked_df.filter(F.col("_row_num") == 1).drop("_row_num")


def assert_unique_key(
    df: DataFrame,
    key_cols: str | list[str],
    label: str = "",
) -> None:
    """Assert that key_cols form a non-null, unique key on DataFrame."""
    keys = [key_cols] if isinstance(key_cols, str) else list(key_cols)
    prefix = f"[{label}] " if label else ""

    null_cond = F.col(keys[0]).isNull()
    for k in keys[1:]:
        null_cond = null_cond | F.col(k).isNull()
    null_count = df.filter(null_cond).count()
    if null_count > 0:
        raise AssertionError(f"{prefix}Found {null_count} rows with NULL in key {keys}")

    total_count = df.count()
    distinct_count = df.select(*keys).distinct().count()
    if total_count != distinct_count:
        dups = total_count - distinct_count
        raise AssertionError(
            f"{prefix}Key {keys} is not unique: {dups} duplicate rows detected "
            f"({total_count} total vs {distinct_count} distinct)"
        )


def profile_join(
    left: DataFrame,
    right: DataFrame,
    join_keys: str | list[str],
    join_type: str = "left",
) -> dict[str, Any]:
    """Profile a join operation to detect grain change or row multiplication."""
    keys = [join_keys] if isinstance(join_keys, str) else list(join_keys)
    left_rows = left.count()
    right_rows = right.count()

    joined = left.join(right, on=keys, how=join_type)
    joined_rows = joined.count()

    return {
        "join_keys": keys,
        "join_type": join_type,
        "left_rows": left_rows,
        "right_rows": right_rows,
        "joined_rows": joined_rows,
        "row_diff": joined_rows - left_rows,
        "is_grain_preserved": joined_rows == left_rows,
    }


def check_grain_preserved(
    before_count: int,
    after_count: int,
    before_distinct_key: int,
    after_distinct_key: int,
    key_name: str = "key",
) -> bool:
    """Validate that a join preserved the primary grain without duplication or loss."""
    if before_count != after_count:
        return False
    if before_distinct_key != after_distinct_key:
        return False
    if before_count != before_distinct_key:
        return False
    return True
