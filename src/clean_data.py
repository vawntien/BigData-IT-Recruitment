"""D04 read-only raw-to-clean staging pipeline for the 11 LinkedIn CSV files."""

from __future__ import annotations

import csv
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession, Window, functions as F
from pyspark.sql.types import (
    BooleanType,
    DecimalType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)
import pyspark


APP_NAME = "BigDataITRecruitment-DataCleaning"
MISSING_TOKENS = ["NULL", "N/A", "NA"]

TABLE_SPECS: dict[str, dict[str, Any]] = {
    "postings": {
        "path": "postings.csv",
        "columns": [
            "job_id", "company_name", "title", "description", "max_salary",
            "pay_period", "location", "company_id", "views", "med_salary",
            "min_salary", "formatted_work_type", "applies",
            "original_listed_time", "remote_allowed", "job_posting_url",
            "application_url", "application_type", "expiry", "closed_time",
            "formatted_experience_level", "skills_desc", "listed_time",
            "posting_domain", "sponsored", "work_type", "currency",
            "compensation_type", "normalized_salary", "zip_code", "fips",
        ],
        "expected_rows": 123849,
        "multiline": True,
        "required_key": ["job_id"],
        "unique_key": ["job_id"],
    },
    "companies": {
        "path": "companies/companies.csv",
        "columns": [
            "company_id", "name", "description", "company_size", "state",
            "country", "city", "zip_code", "address", "url",
        ],
        "expected_rows": 24473,
        "multiline": True,
        "required_key": ["company_id"],
        "unique_key": ["company_id"],
    },
    "company_industries": {
        "path": "companies/company_industries.csv",
        "columns": ["company_id", "industry"],
        "expected_rows": 24375,
        "multiline": False,
        "required_key": ["company_id", "industry"],
        "unique_key": ["company_id", "industry"],
    },
    "company_specialities": {
        "path": "companies/company_specialities.csv",
        "columns": ["company_id", "speciality"],
        "expected_rows": 169387,
        "multiline": False,
        "required_key": ["company_id", "speciality"],
        "unique_key": ["company_id", "speciality"],
    },
    "employee_counts": {
        "path": "companies/employee_counts.csv",
        "columns": ["company_id", "employee_count", "follower_count", "time_recorded"],
        "expected_rows": 35787,
        "multiline": False,
        "required_key": ["company_id", "time_recorded"],
        "unique_key": ["company_id", "time_recorded"],
    },
    "benefits": {
        "path": "jobs/benefits.csv",
        "columns": ["job_id", "inferred", "type"],
        "expected_rows": 67943,
        "multiline": False,
        "required_key": ["job_id", "type"],
        "unique_key": ["job_id", "type"],
    },
    "job_industries": {
        "path": "jobs/job_industries.csv",
        "columns": ["job_id", "industry_id"],
        "expected_rows": 164808,
        "multiline": False,
        "required_key": ["job_id", "industry_id"],
        "unique_key": ["job_id", "industry_id"],
    },
    "job_skills": {
        "path": "jobs/job_skills.csv",
        "columns": ["job_id", "skill_abr"],
        "expected_rows": 213768,
        "multiline": False,
        "required_key": ["job_id", "skill_abr"],
        "unique_key": ["job_id", "skill_abr"],
    },
    "salaries": {
        "path": "jobs/salaries.csv",
        "columns": [
            "salary_id", "job_id", "max_salary", "med_salary", "min_salary",
            "pay_period", "currency", "compensation_type",
        ],
        "expected_rows": 40785,
        "multiline": False,
        "required_key": ["salary_id", "job_id"],
        "unique_key": ["salary_id"],
        "additional_unique_keys": [["job_id"]],
    },
    "industries": {
        "path": "mappings/industries.csv",
        "columns": ["industry_id", "industry_name"],
        "expected_rows": 422,
        "multiline": False,
        "required_key": ["industry_id"],
        "unique_key": ["industry_id"],
    },
    "skills": {
        "path": "mappings/skills.csv",
        "columns": ["skill_abr", "skill_name"],
        "expected_rows": 35,
        "multiline": False,
        "required_key": ["skill_abr"],
        "unique_key": ["skill_abr"],
    },
}

TYPE_RULES: dict[str, dict[str, str]] = {
    "postings": {
        "job_id": "identifier_long",
        "company_id": "identifier_long",
        "max_salary": "decimal",
        "med_salary": "decimal",
        "min_salary": "decimal",
        "normalized_salary": "decimal",
        "views": "measure_long",
        "applies": "measure_long",
        "remote_allowed": "boolean",
        "sponsored": "boolean",
        "original_listed_time": "epoch_milliseconds",
        "listed_time": "epoch_milliseconds",
        "expiry": "epoch_milliseconds",
        "closed_time": "epoch_milliseconds",
    },
    "companies": {
        "company_id": "identifier_long",
        "company_size": "measure_long",
    },
    "company_industries": {"company_id": "identifier_long"},
    "company_specialities": {"company_id": "identifier_long"},
    "employee_counts": {
        "company_id": "identifier_long",
        "employee_count": "measure_long",
        "follower_count": "measure_long",
        "time_recorded": "epoch_seconds",
    },
    "benefits": {"job_id": "identifier_long", "inferred": "boolean"},
    "job_industries": {
        "job_id": "identifier_long",
        "industry_id": "identifier_long",
    },
    "job_skills": {"job_id": "identifier_long"},
    "salaries": {
        "salary_id": "identifier_long",
        "job_id": "identifier_long",
        "max_salary": "decimal",
        "med_salary": "decimal",
        "min_salary": "decimal",
    },
    "industries": {"industry_id": "identifier_long"},
    "skills": {},
}

ENCODING_COLUMNS = {
    "postings": ["title", "description"],
    "companies": ["description"],
}

# Explicit replacements only for patterns confirmed by D03.
MOJIBAKE_REPLACEMENTS = [
    ("â€™", "’"),
    ("â€œ", "“"),
    ("â€\u009d", "”"),
    ("â€“", "–"),
    ("â€”", "—"),
    ("Â", ""),
]

TRUE_TOKENS = ["true", "1", "1.0"]
FALSE_TOKENS = ["false", "0", "0.0"]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def markdown_escape(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(markdown_escape(value) for value in row) + " |"
        for row in rows
    )
    return lines


def raw_snapshot(raw_dir: Path) -> dict[str, tuple[int, int]]:
    return {
        str(path.relative_to(raw_dir)).replace("\\", "/"): (
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for path in sorted(raw_dir.rglob("*.csv"))
    }


def ensure_windows_localfs_adapter(project_root: Path) -> Path | None:
    """Compile the narrow Windows local-FS permission adapter into ignored tmp/."""
    if os.name != "nt":
        return None
    source = project_root / "src" / "windows" / "NoPermissionLocalFileSystem.java"
    build_root = project_root / "tmp" / "d04-localfs"
    classes_dir = build_root / "classes"
    jar_path = build_root / "d04-localfs-adapter.jar"
    if jar_path.exists() and jar_path.stat().st_mtime_ns >= source.stat().st_mtime_ns:
        return jar_path

    java_home = Path(os.environ.get("JAVA_HOME", ""))
    javac = shutil.which("javac") or str(java_home / "bin" / "javac.exe")
    jar_tool = shutil.which("jar") or str(java_home / "bin" / "jar.exe")
    if not Path(javac).exists() or not Path(jar_tool).exists():
        raise RuntimeError("JDK javac/jar tools are required for the Windows local-FS adapter")

    classes_dir.mkdir(parents=True, exist_ok=True)
    jars_wildcard = str(Path(pyspark.__file__).resolve().parent / "jars" / "*")
    subprocess.run(
        [javac, "-proc:none", "-cp", jars_wildcard, "-d", str(classes_dir), str(source)],
        check=True,
    )
    subprocess.run(
        [jar_tool, "--create", "--file", str(jar_path), "-C", str(classes_dir), "."],
        check=True,
    )
    return jar_path


def raw_schema(columns: list[str]) -> StructType:
    fields = [StructField(column, StringType(), True) for column in columns]
    fields.append(StructField("_corrupt_record", StringType(), True))
    return StructType(fields)


def read_raw(spark: SparkSession, raw_dir: Path, table: str) -> DataFrame:
    spec = TABLE_SPECS[table]
    return (
        spark.read.schema(raw_schema(spec["columns"]))
        .option("header", "true")
        .option("enforceSchema", "true")
        .option("multiLine", "true" if spec["multiline"] else "false")
        .option("quote", '"')
        .option("escape", '"')
        .option("encoding", "UTF-8")
        .option("mode", "PERMISSIVE")
        .option("columnNameOfCorruptRecord", "_corrupt_record")
        .csv(str(raw_dir / spec["path"]))
    )


def sentinel_condition(column: str):
    trimmed = F.trim(F.col(column))
    return F.col(column).isNotNull() & (
        (trimmed == "") | F.upper(trimmed).isin(MISSING_TOKENS)
    )


def normalize_missing(df: DataFrame, columns: list[str]) -> DataFrame:
    output = df
    for column in columns:
        trimmed = F.trim(F.col(column))
        output = output.withColumn(
            column,
            F.when(
                F.col(column).isNull()
                | (trimmed == "")
                | F.upper(trimmed).isin(MISSING_TOKENS),
                F.lit(None).cast("string"),
            ).otherwise(trimmed),
        )
    return output


def strict_integer(column: str):
    value = F.col(column)
    canonical = F.regexp_replace(value, r"\.0+$", "")
    return F.when(
        value.rlike(r"^[+-]?\d+(?:\.0+)?$"), canonical.try_cast(LongType())
    ).otherwise(F.lit(None).cast(LongType()))


def cast_expression(column: str, rule: str):
    value = F.col(column)
    if rule in {"identifier_long", "measure_long"}:
        return strict_integer(column)
    if rule == "decimal":
        return value.try_cast(DecimalType(20, 4))
    if rule == "boolean":
        lowered = F.lower(value)
        return (
            F.when(lowered.isin(TRUE_TOKENS), F.lit(True))
            .when(lowered.isin(FALSE_TOKENS), F.lit(False))
            .otherwise(F.lit(None).cast(BooleanType()))
        )
    if rule == "epoch_milliseconds":
        return F.timestamp_millis(strict_integer(column))
    if rule == "epoch_seconds":
        return F.timestamp_seconds(strict_integer(column))
    raise ValueError(f"Unsupported cast rule: {rule}")


def clean_type_name(rule: str) -> str:
    return {
        "identifier_long": "bigint",
        "measure_long": "bigint",
        "decimal": "decimal(20,4)",
        "boolean": "boolean",
        "epoch_milliseconds": "timestamp",
        "epoch_seconds": "timestamp",
    }[rule]


def rule_description(rule: str) -> str:
    return {
        "identifier_long": "Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint",
        "measure_long": "Trim; missing→NULL; strict integral cast; failures logged",
        "decimal": "Trim; missing→NULL; try-cast to decimal(20,4); no salary business normalization",
        "boolean": "Explicit true/1/1.0 and false/0/0.0 mapping; failures logged",
        "epoch_milliseconds": "Preserve *_raw; strict integer epoch milliseconds→UTC timestamp",
        "epoch_seconds": "Preserve *_raw; strict integer epoch seconds→UTC timestamp",
    }[rule]


def mojibake_condition(column: str):
    condition = F.lit(False)
    for bad, _ in MOJIBAKE_REPLACEMENTS:
        condition = condition | (F.instr(F.col(column), bad) > 0)
    return condition


def repaired_text(column: str):
    result = F.col(column)
    for bad, replacement in MOJIBAKE_REPLACEMENTS:
        result = F.regexp_replace(result, re.escape(bad), replacement)
    return result


def apply_encoding_repairs(
    table: str,
    df: DataFrame,
    encoding_rows: list[dict[str, Any]],
) -> tuple[DataFrame, int]:
    columns = ENCODING_COLUMNS.get(table, [])
    if not columns:
        return df, 0
    output = df
    total_fixed = 0
    for column in columns:
        condition = mojibake_condition(column)
        before_count = output.where(condition).count()
        samples = []
        if before_count:
            sample_rows = (
                output.where(condition)
                .select(
                    F.substring(F.col(column), 1, 300).alias("before"),
                    F.substring(repaired_text(column), 1, 300).alias("after"),
                )
                .limit(3)
                .collect()
            )
            samples = [row.asDict() for row in sample_rows]
        output = output.withColumn(column, repaired_text(column))
        after_count = output.where(mojibake_condition(column)).count()
        encoding_rows.append(
            {
                "table": table,
                "column": column,
                "before_cells": before_count,
                "after_cells": after_count,
                "cells_fixed": before_count - after_count,
                "mapping": json.dumps(MOJIBAKE_REPLACEMENTS, ensure_ascii=False),
                "samples_json": json.dumps(samples, ensure_ascii=False),
            }
        )
        total_fixed += before_count - after_count
    return output, total_fixed


def apply_casts(
    table: str,
    df: DataFrame,
    cast_failure_rows: list[dict[str, Any]],
    schema_rows: list[dict[str, Any]],
) -> tuple[DataFrame, int]:
    rules = TYPE_RULES[table]
    failure_expressions = []
    for index, (column, rule) in enumerate(rules.items()):
        failure_expressions.append(
            F.sum(
                F.when(
                    F.col(column).isNotNull() & cast_expression(column, rule).isNull(),
                    1,
                ).otherwise(0)
            ).alias(f"failure_{index}")
        )
    failures = df.agg(*failure_expressions).first().asDict() if rules else {}

    output = df
    total_failures = 0
    for index, (column, rule) in enumerate(rules.items()):
        failure_count = int(failures.get(f"failure_{index}", 0) or 0)
        samples: list[str] = []
        if failure_count:
            samples = [
                str(row[column])
                for row in df.where(
                    F.col(column).isNotNull() & cast_expression(column, rule).isNull()
                )
                .select(column)
                .distinct()
                .limit(10)
                .collect()
            ]
        cast_failure_rows.append(
            {
                "table": table,
                "column": column,
                "target_type": clean_type_name(rule),
                "failure_count": failure_count,
                "sample_values": json.dumps(samples, ensure_ascii=False),
            }
        )
        total_failures += failure_count
        if rule.startswith("epoch_"):
            output = output.withColumn(f"{column}_raw", F.col(column))
        output = output.withColumn(column, cast_expression(column, rule))

    timestamp_raw_columns = {
        column for column, rule in rules.items() if rule.startswith("epoch_")
    }
    for column in TABLE_SPECS[table]["columns"]:
        rule = rules.get(column)
        schema_rows.append(
            {
                "table": table,
                "column": column,
                "raw_type": "string",
                "clean_type": clean_type_name(rule) if rule else "string",
                "rule": rule_description(rule)
                if rule
                else "Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text",
            }
        )
        if column in timestamp_raw_columns:
            schema_rows.append(
                {
                    "table": table,
                    "column": f"{column}_raw",
                    "raw_type": "derived copy",
                    "clean_type": "string",
                    "rule": f"Preserved normalized raw value for auditability of {column}",
                }
            )
    return output, total_failures


def invalid_required_condition(columns: list[str]):
    condition = F.col(columns[0]).isNull()
    for column in columns[1:]:
        condition = condition | F.col(column).isNull()
    return condition


def write_rejects(df: DataFrame, path: Path) -> None:
    df.coalesce(1).write.mode("overwrite").parquet(str(path))


def resolve_employee_duplicates(
    df: DataFrame,
    rejected_root: Path,
    duplicate_group_rows: list[dict[str, Any]],
) -> tuple[DataFrame, int, int]:
    key = ["company_id", "time_recorded"]
    groups = (
        df.groupBy(*key)
        .agg(
            F.count("*").alias("group_rows"),
            F.countDistinct("employee_count").alias("employee_count_variants"),
            F.countDistinct("follower_count").alias("follower_count_variants"),
        )
        .where(F.col("group_rows") > 1)
        .orderBy(*key)
        .collect()
    )
    duplicate_group_rows.extend(row.asDict() for row in groups)

    business_fields = ["employee_count", "follower_count"]
    score = sum(
        (F.when(F.col(column).isNotNull(), 1).otherwise(0) for column in business_fields),
        F.lit(0),
    )
    row_json = F.to_json(
        F.struct(*[F.col(column) for column in df.columns]),
        options={"ignoreNullFields": "false"},
    )
    ranked = (
        df.withColumn("_non_null_business_score", score)
        .withColumn("_employee_present", F.col("employee_count").isNotNull().cast("int"))
        .withColumn("_follower_present", F.col("follower_count").isNotNull().cast("int"))
        .withColumn("_row_sha256", F.sha2(row_json, 256))
        .withColumn(
            "_duplicate_rank",
            F.row_number().over(
                Window.partitionBy(*key).orderBy(
                    F.col("_non_null_business_score").desc(),
                    F.col("_employee_present").desc(),
                    F.col("_follower_present").desc(),
                    F.col("_row_sha256").asc(),
                )
            ),
        )
    )
    helper_columns = [
        "_non_null_business_score",
        "_employee_present",
        "_follower_present",
        "_row_sha256",
        "_duplicate_rank",
    ]
    rejected = (
        ranked.where(F.col("_duplicate_rank") > 1)
        .withColumn("_reject_reason", F.lit("duplicate_company_id_time_recorded"))
    )
    removed = rejected.count()
    if removed:
        write_rejects(
            rejected,
            rejected_root / "employee_counts_duplicate_keys",
        )
    clean = ranked.where(F.col("_duplicate_rank") == 1).drop(*helper_columns)
    return clean, len(groups), removed


def resolve_post_normalization_duplicates(
    df: DataFrame,
    table: str,
    key: list[str],
    rejected_root: Path,
    normalization_duplicate_rows: list[dict[str, Any]],
) -> tuple[DataFrame, int, int]:
    """Resolve only key collisions introduced/exposed by typed normalization."""
    duplicate_groups = (
        df.groupBy(*key).count().where(F.col("count") > 1).count()
    )
    if duplicate_groups == 0:
        return df, 0, 0

    business_fields = [column for column in df.columns if column not in key]
    score = sum(
        (F.when(F.col(column).isNotNull(), 1).otherwise(0) for column in business_fields),
        F.lit(0),
    )
    row_json = F.to_json(
        F.struct(*[F.col(column) for column in df.columns]),
        options={"ignoreNullFields": "false"},
    )
    ranked = (
        df.withColumn("_non_null_score", score)
        .withColumn("_row_sha256", F.sha2(row_json, 256))
        .withColumn(
            "_duplicate_rank",
            F.row_number().over(
                Window.partitionBy(*key).orderBy(
                    F.col("_non_null_score").desc(),
                    F.col("_row_sha256").asc(),
                )
            ),
        )
    )
    helpers = ["_non_null_score", "_row_sha256", "_duplicate_rank"]
    rejected = ranked.where(F.col("_duplicate_rank") > 1).withColumn(
        "_reject_reason",
        F.lit(f"post_normalization_duplicate_key:{'+'.join(key)}"),
    )
    removed = rejected.count()
    key_path = "__".join(key)
    write_rejects(
        rejected,
        rejected_root / f"{table}_duplicate_keys" / key_path,
    )
    normalization_duplicate_rows.append(
        {
            "table": table,
            "candidate_key": " + ".join(key),
            "duplicate_groups": duplicate_groups,
            "removed_rows": removed,
            "keep_rule": "most non-null non-key fields, then ascending SHA-256 typed-row fingerprint",
        }
    )
    return ranked.where(F.col("_duplicate_rank") == 1).drop(*helpers), duplicate_groups, removed


def validate_unique(df: DataFrame, columns: list[str]) -> tuple[bool, int]:
    duplicate_groups = (
        df.groupBy(*columns).count().where(F.col("count") > 1).count()
    )
    return duplicate_groups == 0, duplicate_groups


def process_table(
    spark: SparkSession,
    raw_dir: Path,
    clean_root: Path,
    rejected_root: Path,
    table: str,
    metrics_rows: list[dict[str, Any]],
    cast_failure_rows: list[dict[str, Any]],
    encoding_rows: list[dict[str, Any]],
    schema_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    duplicate_group_rows: list[dict[str, Any]],
    normalization_duplicate_rows: list[dict[str, Any]],
) -> None:
    spec = TABLE_SPECS[table]
    storage = StorageLevel.DISK_ONLY if table == "postings" else StorageLevel.MEMORY_AND_DISK
    raw = read_raw(spark, raw_dir, table).persist(storage)
    try:
        input_rows = raw.count()
        if input_rows != spec["expected_rows"]:
            raise RuntimeError(
                f"{table}: expected {spec['expected_rows']} input rows, found {input_rows}"
            )
        malformed = raw.where(F.col("_corrupt_record").isNotNull())
        malformed_count = malformed.count()
        if malformed_count:
            write_rejects(
                malformed.withColumn("_reject_reason", F.lit("malformed_csv")),
                rejected_root / table / "malformed_csv",
            )
        good_raw = raw.where(F.col("_corrupt_record").isNull()).drop("_corrupt_record")

        sentinel_exprs = [
            F.sum(F.when(sentinel_condition(column), 1).otherwise(0)).alias(column)
            for column in spec["columns"]
        ]
        sentinel_counts = good_raw.agg(*sentinel_exprs).first().asDict()
        normalized_sentinels = sum(int(value or 0) for value in sentinel_counts.values())

        normalized = normalize_missing(good_raw, spec["columns"])
        repaired, encoding_cells_fixed = apply_encoding_repairs(
            table, normalized, encoding_rows
        )
        typed, cast_failure_count = apply_casts(
            table, repaired, cast_failure_rows, schema_rows
        )

        invalid_condition = invalid_required_condition(spec["required_key"])
        invalid = typed.where(invalid_condition).withColumn(
            "_reject_reason", F.lit("missing_or_invalid_required_key")
        )
        invalid_count = invalid.count()
        if invalid_count:
            write_rejects(invalid, rejected_root / table / "invalid_required_key")
        valid = typed.where(~invalid_condition)

        duplicate_groups = 0
        duplicate_removed = 0
        if table == "employee_counts":
            clean, duplicate_groups, duplicate_removed = resolve_employee_duplicates(
                valid, rejected_root, duplicate_group_rows
            )
        else:
            clean = valid
            for unique_key in [spec["unique_key"]] + spec.get(
                "additional_unique_keys", []
            ):
                clean, groups, removed = resolve_post_normalization_duplicates(
                    clean,
                    table,
                    unique_key,
                    rejected_root,
                    normalization_duplicate_rows,
                )
                duplicate_groups += groups
                duplicate_removed += removed

        clean = clean.persist(storage)
        try:
            output_rows = clean.count()
            rejected_rows = malformed_count + invalid_count + duplicate_removed
            if input_rows != output_rows + rejected_rows:
                raise RuntimeError(
                    f"{table}: reconciliation failed: {input_rows} != "
                    f"{output_rows} + {rejected_rows}"
                )

            unique_keys = [spec["unique_key"]] + spec.get(
                "additional_unique_keys", []
            )
            for key in unique_keys:
                passed, groups = validate_unique(clean, key)
                validation_rows.append(
                    {
                        "table": table,
                        "check": f"unique({', '.join(key)})",
                        "status": "PASS" if passed else "FAIL",
                        "details": f"duplicate_groups={groups}",
                    }
                )
                if not passed:
                    raise RuntimeError(f"{table}: key {key} is not unique after cleaning")

            null_required = clean.where(invalid_required_condition(spec["required_key"])).count()
            validation_rows.append(
                {
                    "table": table,
                    "check": f"required_non_null({', '.join(spec['required_key'])})",
                    "status": "PASS" if null_required == 0 else "FAIL",
                    "details": f"null_rows={null_required}",
                }
            )
            if null_required:
                raise RuntimeError(f"{table}: required key contains NULL after cleaning")

            output_path = clean_root / table
            output_partitions = 4 if output_rows >= 100000 else 1
            clean.coalesce(output_partitions).write.mode("overwrite").parquet(
                str(output_path)
            )
            written = spark.read.parquet(str(output_path))
            written_rows = written.count()
            validation_rows.append(
                {
                    "table": table,
                    "check": "parquet_readback_row_count",
                    "status": "PASS" if written_rows == output_rows else "FAIL",
                    "details": f"expected={output_rows};actual={written_rows}",
                }
            )
            if written_rows != output_rows:
                raise RuntimeError(f"{table}: Parquet readback count mismatch")

            for column, rule in TYPE_RULES[table].items():
                actual_type = written.schema[column].dataType
                expected_type = {
                    "identifier_long": LongType(),
                    "measure_long": LongType(),
                    "decimal": DecimalType(20, 4),
                    "boolean": BooleanType(),
                    "epoch_milliseconds": TimestampType(),
                    "epoch_seconds": TimestampType(),
                }[rule]
                passed = actual_type == expected_type
                validation_rows.append(
                    {
                        "table": table,
                        "check": f"type({column})",
                        "status": "PASS" if passed else "FAIL",
                        "details": f"expected={expected_type.simpleString()};actual={actual_type.simpleString()}",
                    }
                )
                if not passed:
                    raise RuntimeError(f"{table}.{column}: unexpected Parquet type")

            metrics_rows.append(
                {
                    "table": table,
                    "input_rows": input_rows,
                    "output_rows": output_rows,
                    "rejected_rows": rejected_rows,
                    "malformed_rows": malformed_count,
                    "invalid_key_rows": invalid_count,
                    "duplicate_groups": duplicate_groups,
                    "duplicate_rows_removed": duplicate_removed,
                    "missing_sentinels_normalized": normalized_sentinels,
                    "encoding_cells_fixed": encoding_cells_fixed,
                    "cast_failure_count": cast_failure_count,
                    "notes": "Orphan foreign keys preserved; no cross-table filtering",
                }
            )
            print(
                f"{table}: input={input_rows:,}, output={output_rows:,}, "
                f"rejected={rejected_rows:,}, duplicate_removed={duplicate_removed:,}, "
                f"cast_failures={cast_failure_count:,}"
            )
        finally:
            clean.unpersist()
    finally:
        raw.unpersist()


def write_report(
    path: Path,
    metrics_rows: list[dict[str, Any]],
    schema_rows: list[dict[str, Any]],
    cast_failure_rows: list[dict[str, Any]],
    encoding_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    duplicate_group_rows: list[dict[str, Any]],
    normalization_duplicate_rows: list[dict[str, Any]],
    spark_version: str,
    java_version: str,
) -> None:
    employee = next(row for row in metrics_rows if row["table"] == "employee_counts")
    remaining_encoding = sum(row["after_cells"] for row in encoding_rows)
    failed_validations = [row for row in validation_rows if row["status"] != "PASS"]
    nonzero_casts = [row for row in cast_failure_rows if row["failure_count"] > 0]
    lines = [
        "# D04 Data Cleaning Report",
        "",
        "## 1. Environment",
        "",
        f"- Python: {platform.python_version()}",
        f"- Java: {java_version}",
        f"- PySpark: {spark_version}",
        "- Spark master: `local[*]`",
        "- Spark SQL session timezone: `UTC`",
        "- Output format: Parquet",
        "- Windows local write adapter: project-local Java adapter; no Hadoop/winutils installation",
        "",
        "## 2. Cleaning Principles",
        "",
        "- Raw CSV files are immutable and were verified by size and mtime before/after.",
        "- Missing numeric/boolean values remain NULL; they are never replaced with zero or false.",
        "- Cleaning and duplicate resolution are deterministic.",
        "- No JOIN, IT filtering, salary conversion, annualization, or business aggregation is performed.",
        "- Orphan foreign keys identified by D03 are preserved.",
        "",
        "## 3. Schema Normalization",
        "",
    ]
    lines.extend(
        markdown_table(
            ["Table", "Column", "Raw Type", "Clean Type", "Rule"],
            [
                [row["table"], row["column"], row["raw_type"], row["clean_type"], row["rule"]]
                for row in schema_rows
            ],
        )
    )
    lines.extend(
        [
            "",
            "## 4. Missing-value Normalization",
            "",
            "Spark NULL, blank strings, and the case-insensitive sentinels `null`, `N/A`, and `NA` ",
            "are normalized to NULL after trimming. Internal free-text whitespace is preserved. ",
            "No missing measure or flag is imputed.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Table", "Sentinel Cells Normalized"],
            [[row["table"], row["missing_sentinels_normalized"]] for row in metrics_rows],
        )
    )
    lines.extend(
        [
            "",
            "## 5. Identifier Normalization",
            "",
            "Numeric identifiers use a strict integral grammar before `LongType` conversion. ",
            "A value such as `123.0` is accepted only because its fractional portion is entirely ",
            "zero and becomes canonical ID `123`. Non-integral, malformed, or out-of-range values ",
            "become cast failures; required-key failures are quarantined rather than silently dropped.",
            "",
        ]
    )
    if nonzero_casts:
        lines.extend(
            markdown_table(
                ["Table", "Column", "Target", "Failures", "Samples"],
                [
                    [row["table"], row["column"], row["target_type"], row["failure_count"], row["sample_values"]]
                    for row in nonzero_casts
                ],
            )
        )
    else:
        lines.append("No cast failure was observed in any configured typed column.")
    lines.extend(
        [
            "",
            "## 6. Timestamp Normalization",
            "",
            "The four postings epoch fields are interpreted as Unix milliseconds; ",
            "`employee_counts.time_recorded` is interpreted as Unix seconds. Typed columns are ",
            "Spark `TimestampType` under UTC session timezone. A normalized string copy named ",
            "`*_raw` is retained for auditability.",
            "",
            "## 7. Encoding Repairs",
            "",
            "Only D03-confirmed mappings are applied; no global encode/decode operation is used.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Table", "Column", "Before Cells", "After Cells", "Fixed", "Samples"],
            [
                [
                    row["table"], row["column"], row["before_cells"],
                    row["after_cells"], row["cells_fixed"], row["samples_json"],
                ]
                for row in encoding_rows
            ],
        )
    )
    lines.extend(
        [
            "",
            "Explicit mapping: `â€™→’`, `â€œ→“`, `â€→”`, `â€“→–`, `â€”→—`, and stray `Â→` empty.",
            "",
            f"Remaining configured mojibake cells after repair: {remaining_encoding}.",
            "",
            "## 8. Duplicate Handling",
            "",
            f"`employee_counts` before rows: {employee['input_rows']}; duplicate logical-key groups: ",
            f"{employee['duplicate_groups']}; removed rows: {employee['duplicate_rows_removed']}; ",
            f"after rows: {employee['output_rows']}.",
            "",
            "Keep rule for `(company_id, time_recorded)`: highest count of non-null business fields, ",
            "then presence of `employee_count`, then presence of `follower_count`, then ascending ",
            "SHA-256 fingerprint of the complete typed row. Removed rows are preserved under ",
            "`data/processed/rejected/employee_counts_duplicate_keys/`.",
            "",
            f"Detailed duplicate groups recorded: {len(duplicate_group_rows)}.",
            "",
            "Other candidate-key collisions introduced or exposed by missing/trim/type ",
            "normalization are not silently deleted. Extra rows are content-ranked, written ",
            "under `data/processed/rejected/<table>_duplicate_keys/`, and listed below.",
            "",
            "## 9. Rejected / Quarantined Records",
            "",
        ]
    )
    if normalization_duplicate_rows:
        lines.extend(
            markdown_table(
                ["Table", "Candidate Key", "Groups", "Removed", "Keep Rule"],
                [
                    [
                        row["table"], row["candidate_key"], row["duplicate_groups"],
                        row["removed_rows"], row["keep_rule"],
                    ]
                    for row in normalization_duplicate_rows
                ],
            )
        )
        lines.append("")
    lines.extend(
        markdown_table(
            ["Table", "Malformed", "Invalid Required Key", "Duplicate Removed", "Total Rejected"],
            [
                [
                    row["table"], row["malformed_rows"], row["invalid_key_rows"],
                    row["duplicate_rows_removed"], row["rejected_rows"],
                ]
                for row in metrics_rows
            ],
        )
    )
    lines.extend(["", "## 10. Row Reconciliation", ""])
    lines.extend(
        markdown_table(
            ["Table", "Input", "Output", "Rejected", "Duplicate Removed"],
            [
                [
                    row["table"], row["input_rows"], row["output_rows"],
                    row["rejected_rows"], row["duplicate_rows_removed"],
                ]
                for row in metrics_rows
            ],
        )
    )
    lines.extend(
        [
            "",
            "For every table: `input_rows = output_rows + rejected_rows`.",
            "",
            "## 11. Validation",
            "",
            f"Validation checks executed: {len(validation_rows)}; failures: {len(failed_validations)}.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Table", "Check", "Status", "Details"],
            [[row["table"], row["check"], row["status"], row["details"]] for row in validation_rows],
        )
    )
    lines.extend(
        [
            "",
            "## 12. Remaining Issues for Later Tasks",
            "",
            "- D05: decide JOIN scope and treatment of orphan foreign keys.",
            "- D06: identify and filter IT-related postings.",
            "- D07: define salary semantics, currency conversion, pay-period normalization, and analytics.",
            "",
            "D04 does not implement any of those downstream decisions.",
            "",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    raw_dir = project_root / "data" / "raw"
    clean_root = project_root / "data" / "processed" / "clean"
    rejected_root = project_root / "data" / "processed" / "rejected"
    audit_dir = project_root / "data" / "audit"
    report_path = project_root / "docs" / "d04_cleaning_report.md"
    before = raw_snapshot(raw_dir)
    if len(before) != 11:
        raise RuntimeError(f"Expected 11 raw CSV files, found {len(before)}")

    localfs_adapter = ensure_windows_localfs_adapter(project_root)
    builder = (
        SparkSession.builder.appName(APP_NAME)
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
    )
    if localfs_adapter is not None:
        builder = (
            builder.config("spark.driver.extraClassPath", str(localfs_adapter))
            .config("spark.executor.extraClassPath", str(localfs_adapter))
            .config("spark.hadoop.fs.file.impl", "d04.localfs.NoPermissionLocalFileSystem")
            .config("spark.hadoop.fs.file.impl.disable.cache", "true")
        )
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    metrics_rows: list[dict[str, Any]] = []
    cast_failure_rows: list[dict[str, Any]] = []
    encoding_rows: list[dict[str, Any]] = []
    schema_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    duplicate_group_rows: list[dict[str, Any]] = []
    normalization_duplicate_rows: list[dict[str, Any]] = []

    try:
        if spark.conf.get("spark.sql.session.timeZone") != "UTC":
            raise RuntimeError("Spark SQL session timezone is not UTC")
        print(f"Spark version: {spark.version}")
        print(f"Application: {APP_NAME}")
        print("Master: local[*]")
        print("Session timezone: UTC")

        for table in TABLE_SPECS:
            process_table(
                spark, raw_dir, clean_root, rejected_root, table,
                metrics_rows, cast_failure_rows, encoding_rows, schema_rows,
                validation_rows, duplicate_group_rows, normalization_duplicate_rows,
            )

        after = raw_snapshot(raw_dir)
        if before != after:
            raise RuntimeError("Raw CSV size or mtime changed during D04")

        failed = [row for row in validation_rows if row["status"] != "PASS"]
        if failed:
            raise RuntimeError(f"Validation failures: {failed}")

        write_csv(
            audit_dir / "d04_etl_summary.csv",
            metrics_rows,
            [
                "table", "input_rows", "output_rows", "rejected_rows",
                "malformed_rows", "invalid_key_rows", "duplicate_groups",
                "duplicate_rows_removed", "missing_sentinels_normalized",
                "encoding_cells_fixed", "cast_failure_count", "notes",
            ],
        )
        write_csv(
            audit_dir / "d04_cast_failures.csv",
            cast_failure_rows,
            ["table", "column", "target_type", "failure_count", "sample_values"],
        )
        write_csv(
            audit_dir / "d04_encoding_fixes.csv",
            encoding_rows,
            ["table", "column", "before_cells", "after_cells", "cells_fixed", "mapping", "samples_json"],
        )
        write_csv(
            audit_dir / "d04_schema_changes.csv",
            schema_rows,
            ["table", "column", "raw_type", "clean_type", "rule"],
        )
        write_csv(
            audit_dir / "d04_validation.csv",
            validation_rows,
            ["table", "check", "status", "details"],
        )
        write_csv(
            audit_dir / "d04_employee_counts_duplicate_groups.csv",
            duplicate_group_rows,
            [
                "company_id", "time_recorded", "group_rows",
                "employee_count_variants", "follower_count_variants",
            ],
        )
        write_csv(
            audit_dir / "d04_post_normalization_duplicates.csv",
            normalization_duplicate_rows,
            ["table", "candidate_key", "duplicate_groups", "removed_rows", "keep_rule"],
        )
        java_version = spark.sparkContext._jvm.java.lang.System.getProperty("java.version")
        write_report(
            report_path, metrics_rows, schema_rows, cast_failure_rows,
            encoding_rows, validation_rows, duplicate_group_rows,
            normalization_duplicate_rows,
            spark.version, java_version,
        )

        postings = next(row for row in metrics_rows if row["table"] == "postings")
        if postings["output_rows"] != 123849:
            raise RuntimeError("postings clean output must contain 123849 rows")

        print("=" * 72)
        print("Clean tables written: 11")
        print("Raw CSV snapshot unchanged: True")
        print(f"Validation checks: {len(validation_rows)} PASS")
        print(f"Clean output: {clean_root}")
        print("D04 data cleaning completed successfully.")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
