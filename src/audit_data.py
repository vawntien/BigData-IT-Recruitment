"""Reproducible, read-only Spark audit for the 11 raw LinkedIn CSV files."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession, functions as F


APP_NAME = "BigDataITRecruitment-DataAudit"
MISSING_TOKENS = ["NULL", "N/A", "NA"]
MOJIBAKE_PATTERNS = ["â€™", "â€œ", "â€\u009d", "â€“", "â€”", "Ã", "Â"]

TABLES = {
    "postings": "postings.csv",
    "companies": "companies/companies.csv",
    "company_industries": "companies/company_industries.csv",
    "company_specialities": "companies/company_specialities.csv",
    "employee_counts": "companies/employee_counts.csv",
    "benefits": "jobs/benefits.csv",
    "job_industries": "jobs/job_industries.csv",
    "job_skills": "jobs/job_skills.csv",
    "salaries": "jobs/salaries.csv",
    "industries": "mappings/industries.csv",
    "skills": "mappings/skills.csv",
}

# Files with long free text need multiline-safe parsing. The remaining relationship
# and mapping tables use one logical record per physical line.
MULTILINE_TABLES = {"postings", "companies"}

CANDIDATE_KEYS = {
    "postings": [("job_id",), ("company_id",)],
    "companies": [("company_id",)],
    "company_industries": [("company_id",), ("company_id", "industry")],
    "company_specialities": [("company_id",), ("company_id", "speciality")],
    "employee_counts": [("company_id",), ("company_id", "time_recorded")],
    "benefits": [("job_id",), ("job_id", "type")],
    "job_industries": [("job_id",), ("job_id", "industry_id")],
    "job_skills": [("job_id",), ("job_id", "skill_abr")],
    "salaries": [("salary_id",), ("job_id",)],
    "industries": [("industry_id",)],
    "skills": [("skill_abr",)],
}

TIME_COLUMNS = {
    "postings": ["original_listed_time", "listed_time", "expiry", "closed_time"],
    "employee_counts": ["time_recorded"],
}

# parent table, child table, parent column, child column
RELATIONSHIPS = [
    ("companies", "postings", "company_id", "company_id"),
    ("postings", "job_skills", "job_id", "job_id"),
    ("postings", "job_industries", "job_id", "job_id"),
    ("postings", "benefits", "job_id", "job_id"),
    ("postings", "salaries", "job_id", "job_id"),
    ("skills", "job_skills", "skill_abr", "skill_abr"),
    ("industries", "job_industries", "industry_id", "industry_id"),
    ("companies", "company_industries", "company_id", "company_id"),
    ("companies", "company_specialities", "company_id", "company_id"),
    ("companies", "employee_counts", "company_id", "company_id"),
]

RELATION_KEY_COLUMNS = {
    (table, column)
    for parent, child, parent_column, child_column in RELATIONSHIPS
    for table, column in ((parent, parent_column), (child, child_column))
}


def missing_condition(column: str):
    value = F.trim(F.col(column))
    return F.col(column).isNull() | (value == "") | F.upper(value).isin(MISSING_TOKENS)


def key_missing_condition(columns: tuple[str, ...]):
    condition = missing_condition(columns[0])
    for column in columns[1:]:
        condition = condition | missing_condition(column)
    return condition


def mojibake_condition(column: str):
    condition = F.lit(False)
    for pattern in MOJIBAKE_PATTERNS:
        condition = condition | (F.instr(F.col(column), pattern) > 0)
    return condition


def read_table(spark: SparkSession, raw_dir: Path, table: str) -> DataFrame:
    return (
        spark.read.option("header", "true")
        .option("inferSchema", "false")
        .option("multiLine", "true" if table in MULTILINE_TABLES else "false")
        .option("quote", '"')
        .option("escape", '"')
        .option("encoding", "UTF-8")
        .csv(str(raw_dir / TABLES[table]))
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
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


def candidate_role(table: str, column: str) -> str:
    foreign_keys = {
        (child, child_column) for _, child, _, child_column in RELATIONSHIPS
    }
    primary_identifiers = {
        ("postings", "job_id"),
        ("companies", "company_id"),
        ("salaries", "salary_id"),
        ("industries", "industry_id"),
        ("skills", "skill_abr"),
    }
    lower = column.lower()
    if (table, column) in primary_identifiers:
        return "identifier"
    if (table, column) in foreign_keys:
        return "foreign key candidate"
    if column in TIME_COLUMNS.get(table, []) or any(
        token in lower for token in ("time", "date", "expiry", "closed")
    ):
        return "timestamp candidate"
    if "url" in lower or "domain" in lower:
        return "URL"
    if any(
        token in lower
        for token in ("salary", "count", "views", "applies", "company_size")
    ):
        return "measure"
    if any(
        token in lower
        for token in ("description", "title", "speciality", "address", "skills_desc")
    ):
        return "text"
    if lower.endswith("_id"):
        return "identifier"
    if table in {"industries", "skills"} and lower.endswith("_name"):
        return "mapping value"
    return "categorical"


def role_notes(table: str, column: str) -> str:
    notes = []
    if any(column in key for key in CANDIDATE_KEYS.get(table, [])):
        notes.append("Included in candidate-key audit")
    if (table, column) in RELATION_KEY_COLUMNS:
        notes.append("Included in referential-coverage audit")
    if column in TIME_COLUMNS.get(table, []):
        notes.append("Unit inferred only after inspecting actual values")
    return "; ".join(notes)


def detect_epoch_unit(samples: list[str]) -> str:
    if not samples:
        return "UNKNOWN"
    try:
        numeric = [int(Decimal(str(value))) for value in samples]
    except (InvalidOperation, TypeError, ValueError):
        return "UNKNOWN"

    def plausible(divisor: int) -> bool:
        try:
            years = [datetime.fromtimestamp(value / divisor, tz=timezone.utc).year for value in numeric]
        except (OSError, OverflowError, ValueError):
            return False
        return all(1990 <= year <= 2100 for year in years)

    seconds_plausible = plausible(1)
    milliseconds_plausible = plausible(1000)
    if seconds_plausible and not milliseconds_plausible:
        return "UNIX_SECONDS"
    if milliseconds_plausible and not seconds_plausible:
        return "UNIX_MILLISECONDS"
    return "UNKNOWN"


def interpret_epoch(value: str | None, unit: str) -> str:
    if value is None or unit == "UNKNOWN":
        return ""
    divisor = 1000 if unit == "UNIX_MILLISECONDS" else 1
    try:
        timestamp = datetime.fromtimestamp(
            int(Decimal(str(value))) / divisor, tz=timezone.utc
        )
    except (InvalidOperation, OSError, OverflowError, TypeError, ValueError):
        return ""
    return timestamp.isoformat().replace("+00:00", "Z")


def raw_file_snapshot(raw_dir: Path) -> dict[str, tuple[int, int]]:
    return {
        str(path.relative_to(raw_dir)).replace("\\", "/"): (
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for path in sorted(raw_dir.rglob("*.csv"))
    }


def audit_table(
    spark: SparkSession,
    raw_dir: Path,
    table: str,
    inventory_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
    key_rows: list[dict[str, Any]],
    duplicate_rows: list[dict[str, Any]],
    time_rows: list[dict[str, Any]],
    encoding_rows: list[dict[str, Any]],
    relation_values: dict[tuple[str, str], set[str]],
) -> None:
    relative_path = f"data/raw/{TABLES[table]}"
    print(f"\n{'=' * 72}\nAUDITING {table}: {relative_path}\n{'=' * 72}")
    storage_level = (
        StorageLevel.DISK_ONLY if table == "postings" else StorageLevel.MEMORY_AND_DISK
    )
    df = read_table(spark, raw_dir, table).persist(storage_level)
    try:
        total_rows = df.count()
        columns = df.columns
        print(f"Rows={total_rows:,}; Columns={len(columns)}")
        print(f"Column names: {columns}")
        print("Raw schema:")
        df.printSchema()

        inventory_rows.append(
            {
                "table": table,
                "path": relative_path,
                "rows": total_rows,
                "columns": len(columns),
                "column_names": json.dumps(columns, ensure_ascii=False),
                "schema_json": df.schema.json(),
            }
        )

        aggregate_expressions = []
        for index, column in enumerate(columns):
            aggregate_expressions.append(
                F.sum(F.when(missing_condition(column), 1).otherwise(0)).alias(
                    f"missing_{index}"
                )
            )
            aggregate_expressions.append(
                F.sum(F.when(mojibake_condition(column), 1).otherwise(0)).alias(
                    f"encoding_{index}"
                )
            )
        aggregate = df.agg(*aggregate_expressions).first().asDict()

        for index, column in enumerate(columns):
            missing_count = int(aggregate[f"missing_{index}"] or 0)
            affected_records = int(aggregate[f"encoding_{index}"] or 0)
            missing_rows.append(
                {
                    "table": table,
                    "column": column,
                    "raw_spark_type": df.schema[column].dataType.simpleString(),
                    "total_rows": total_rows,
                    "missing_count": missing_count,
                    "missing_percent": round(
                        100 * missing_count / total_rows, 6
                    )
                    if total_rows
                    else 0.0,
                    "candidate_role": candidate_role(table, column),
                    "notes": role_notes(table, column),
                }
            )
            if affected_records:
                samples = [
                    row[column]
                    for row in df.where(mojibake_condition(column))
                    .select(column)
                    .limit(3)
                    .collect()
                ]
            else:
                samples = []
            encoding_rows.append(
                {
                    "table": table,
                    "column": column,
                    "total_rows": total_rows,
                    "affected_records": affected_records,
                    "affected_percent": round(
                        100 * affected_records / total_rows, 6
                    )
                    if total_rows
                    else 0.0,
                    "sample_values": json.dumps(samples, ensure_ascii=False),
                }
            )

        for configured_key in CANDIDATE_KEYS.get(table, []):
            key = tuple(column for column in configured_key if column in columns)
            if len(key) != len(configured_key):
                continue
            missing_key = key_missing_condition(key)
            null_key_count = df.where(missing_key).count()
            valid_keys = df.where(~missing_key).select(*key).distinct().persist(
                StorageLevel.MEMORY_AND_DISK
            )
            try:
                distinct_count = valid_keys.count()
                non_missing_rows = total_rows - null_key_count
                duplicate_count = non_missing_rows - distinct_count
                assessment = (
                    "UNIQUE"
                    if null_key_count == 0 and duplicate_count == 0
                    else "NON_UNIQUE"
                )
                key_name = " + ".join(key)
                key_rows.append(
                    {
                        "table": table,
                        "candidate_key": key_name,
                        "total_rows": total_rows,
                        "null_key_count": null_key_count,
                        "distinct_count": distinct_count,
                        "duplicate_count": duplicate_count,
                        "assessment": assessment,
                    }
                )
                print(
                    f"Key {key_name}: null={null_key_count:,}, "
                    f"distinct={distinct_count:,}, duplicate={duplicate_count:,}, "
                    f"assessment={assessment}"
                )
                if len(key) == 1 and (table, key[0]) in RELATION_KEY_COLUMNS:
                    relation_values[(table, key[0])] = {
                        str(row[0]) for row in valid_keys.collect()
                    }
            finally:
                valid_keys.unpersist()

        # Referential columns are collected independently from candidate keys.
        # This covers fields such as job_skills.skill_abr that participate in a
        # relationship but are audited as part of a composite candidate key.
        relation_columns = sorted(
            column
            for relation_table, column in RELATION_KEY_COLUMNS
            if relation_table == table and column in columns
        )
        for column in relation_columns:
            if (table, column) in relation_values:
                continue
            relation_values[(table, column)] = {
                str(row[0])
                for row in df.where(~missing_condition(column))
                .select(column)
                .distinct()
                .collect()
            }

        # Grouping the full 493 MB postings rows (including long descriptions) can
        # exhaust a local JVM heap. A deterministic SHA-256 fingerprint keeps the
        # shuffle compact. JSON retains field boundaries and explicit NULL values.
        row_json = F.to_json(
            F.struct(*[F.col(column) for column in columns]),
            options={"ignoreNullFields": "false"},
        )
        distinct_rows = df.select(F.sha2(row_json, 256).alias("row_sha256")).distinct().count()
        full_row_duplicates = total_rows - distinct_rows
        duplicate_rows.append(
            {
                "table": table,
                "total_rows": total_rows,
                "distinct_full_rows": distinct_rows,
                "duplicate_full_rows": full_row_duplicates,
            }
        )
        print(f"Full-row duplicates: {full_row_duplicates:,}")

        for column in TIME_COLUMNS.get(table, []):
            if column not in columns:
                continue
            valid = df.where(~missing_condition(column)).select(column)
            samples = [str(row[column]) for row in valid.limit(20).collect()]
            unit = detect_epoch_unit(samples)
            if unit in {"UNIX_SECONDS", "UNIX_MILLISECONDS"}:
                bounds = valid.agg(
                    F.min(F.col(column).cast("decimal(38,0)")).alias("raw_min"),
                    F.max(F.col(column).cast("decimal(38,0)")).alias("raw_max"),
                ).first()
                raw_min = str(int(bounds["raw_min"])) if bounds["raw_min"] is not None else ""
                raw_max = str(int(bounds["raw_max"])) if bounds["raw_max"] is not None else ""
            else:
                bounds = valid.agg(
                    F.min(F.col(column)).alias("raw_min"),
                    F.max(F.col(column)).alias("raw_max"),
                ).first()
                raw_min = bounds["raw_min"] or ""
                raw_max = bounds["raw_max"] or ""
            time_rows.append(
                {
                    "table": table,
                    "column": column,
                    "detected_unit": unit,
                    "raw_min": raw_min,
                    "raw_max": raw_max,
                    "interpreted_min_utc": interpret_epoch(raw_min, unit),
                    "interpreted_max_utc": interpret_epoch(raw_max, unit),
                    "sample_values": json.dumps(samples[:5], ensure_ascii=False),
                }
            )
            print(f"Time {column}: unit={unit}, min={raw_min}, max={raw_max}")
    finally:
        df.unpersist()


def build_referential_profile(
    missing_rows: list[dict[str, Any]],
    relation_values: dict[tuple[str, str], set[str]],
) -> list[dict[str, Any]]:
    def canonical_numeric_sets(
        parent_values: set[str], child_values: set[str]
    ) -> tuple[set[str], set[str], str]:
        combined = parent_values | child_values
        try:
            converted = {
                value: str(int(Decimal(value)))
                for value in combined
                if Decimal(value) == Decimal(value).to_integral_value()
            }
        except (InvalidOperation, OverflowError, ValueError):
            return parent_values, child_values, "EXACT_RAW"
        if len(converted) != len(combined):
            return parent_values, child_values, "EXACT_RAW"
        canonical_parent = {converted[value] for value in parent_values}
        canonical_child = {converted[value] for value in child_values}
        mode = (
            "NUMERIC_CANONICAL"
            if canonical_parent != parent_values or canonical_child != child_values
            else "EXACT_RAW"
        )
        return canonical_parent, canonical_child, mode

    missing_lookup = {
        (row["table"], row["column"]): row for row in missing_rows
    }
    output = []
    for parent, child, parent_column, child_column in RELATIONSHIPS:
        parent_values = relation_values.get((parent, parent_column))
        child_values = relation_values.get((child, child_column))
        child_profile = missing_lookup.get((child, child_column))
        if parent_values is None or child_values is None or child_profile is None:
            continue
        exact_matched = len(child_values & parent_values)
        exact_unmatched = len(child_values - parent_values)
        compared_parent, compared_child, comparison_mode = canonical_numeric_sets(
            parent_values, child_values
        )
        matched = len(compared_child & compared_parent)
        unmatched = len(compared_child - compared_parent)
        distinct_child = len(compared_child)
        output.append(
            {
                "parent_table": parent,
                "child_table": child,
                "parent_key": parent_column,
                "child_key": child_column,
                "child_non_missing_rows": child_profile["total_rows"]
                - child_profile["missing_count"],
                "raw_child_distinct_keys": len(child_values),
                "comparison_mode": comparison_mode,
                "compared_child_distinct_keys": distinct_child,
                "exact_matched_distinct_keys": exact_matched,
                "exact_unmatched_distinct_keys": exact_unmatched,
                "matched_distinct_keys": matched,
                "unmatched_distinct_keys": unmatched,
                "coverage_percent": round(100 * matched / distinct_child, 6)
                if distinct_child
                else 100.0,
            }
        )
    return output


def write_data_dictionary(
    docs_dir: Path,
    inventory_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
) -> None:
    missing_lookup = {
        (row["table"], row["column"]): row for row in missing_rows
    }
    lines = [
        "# Data Dictionary",
        "",
        "Generated by `src/audit_data.py` from the raw CSV headers and Spark audit. ",
        "All raw types are strings because `inferSchema=false`; no business meaning is ",
        "inferred beyond column names and observed audit roles.",
        "",
    ]
    for inventory in inventory_rows:
        table = inventory["table"]
        columns = json.loads(inventory["column_names"])
        lines.extend(
            [
                f"## {table}",
                "",
                f"Source: `{inventory['path']}`",
                "",
                f"Rows: {inventory['rows']}",
                "",
                f"Columns: {inventory['columns']}",
                "",
            ]
        )
        rows = []
        for column in columns:
            profile = missing_lookup[(table, column)]
            rows.append(
                [
                    column,
                    profile["raw_spark_type"],
                    f"{profile['missing_percent']:.6f}",
                    profile["candidate_role"],
                    profile["notes"],
                ]
            )
        lines.extend(
            markdown_table(
                ["Column", "Raw Spark Type", "Missing %", "Candidate Role", "Notes"],
                rows,
            )
        )
        lines.append("")
    (docs_dir / "data_dictionary.md").write_text(
        "\n".join(lines).rstrip() + "\n", encoding="utf-8"
    )


def write_quality_report(
    docs_dir: Path,
    inventory_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
    key_rows: list[dict[str, Any]],
    duplicate_rows: list[dict[str, Any]],
    time_rows: list[dict[str, Any]],
    encoding_rows: list[dict[str, Any]],
    referential_rows: list[dict[str, Any]],
    spark_version: str,
) -> None:
    notable_missing = sorted(
        (row for row in missing_rows if row["missing_percent"] >= 20),
        key=lambda row: (-row["missing_percent"], row["table"], row["column"]),
    )
    encoding_findings = [row for row in encoding_rows if row["affected_records"] > 0]
    non_unique = [row for row in key_rows if row["assessment"] != "UNIQUE"]
    full_duplicates = [row for row in duplicate_rows if row["duplicate_full_rows"] > 0]
    orphan_relations = [row for row in referential_rows if row["unmatched_distinct_keys"] > 0]

    lines = [
        "# D03 Data Quality Report",
        "",
        "## 1. Audit Environment",
        "",
        "- OS: Windows",
        "- Python: 3.11",
        "- Java: OpenJDK 21 LTS Temurin",
        f"- PySpark: {spark_version}",
        "- Spark mode: `local[*]`",
        "- Reader: UTF-8, header enabled, `inferSchema=false`, quote/escape `\"`",
        "",
        "## 2. Dataset Inventory",
        "",
    ]
    lines.extend(
        markdown_table(
            ["File", "Rows", "Columns"],
            [[row["path"], row["rows"], row["columns"]] for row in inventory_rows],
        )
    )
    lines.extend(["", "## 3. Candidate Keys", ""])
    lines.extend(
        markdown_table(
            ["Table", "Candidate Key", "Null", "Distinct", "Duplicate", "Assessment"],
            [
                [
                    row["table"],
                    row["candidate_key"],
                    row["null_key_count"],
                    row["distinct_count"],
                    row["duplicate_count"],
                    row["assessment"],
                ]
                for row in key_rows
            ],
        )
    )
    lines.extend(
        [
            "",
            "Composite keys are evaluated only when every named column exists. A key is ",
            "marked UNIQUE only when it has no missing component and no duplicate among ",
            "non-missing rows.",
            "",
            "## 4. Missing Data",
            "",
            "Missing includes Spark NULL, blank strings, `null`, `NULL`, `N/A`, and `NA` ",
            "after trimming/case normalization. Columns at or above 20% missing:",
            "",
        ]
    )
    if notable_missing:
        lines.extend(
            markdown_table(
                ["Table", "Column", "Missing", "Missing %"],
                [
                    [
                        row["table"],
                        row["column"],
                        row["missing_count"],
                        f"{row['missing_percent']:.6f}",
                    ]
                    for row in notable_missing
                ],
            )
        )
    else:
        lines.append("No column reached the 20% summary threshold.")
    lines.extend(
        [
            "",
            "The complete column-level profile is in `data/audit/missing_profile.csv`.",
            "",
            "## 5. Duplicate Analysis",
            "",
            "Full-row equality is measured with a SHA-256 fingerprint of a JSON ",
            "representation that retains field boundaries and explicit NULL values. This ",
            "keeps the local Spark shuffle bounded for long description text.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Table", "Rows", "Distinct Full Rows", "Duplicate Full Rows"],
            [
                [
                    row["table"],
                    row["total_rows"],
                    row["distinct_full_rows"],
                    row["duplicate_full_rows"],
                ]
                for row in duplicate_rows
            ],
        )
    )
    lines.extend(["", "## 6. Time Coverage", ""])
    lines.extend(
        markdown_table(
            [
                "Table",
                "Column",
                "Unit",
                "Raw Min",
                "Raw Max",
                "Interpreted Min UTC",
                "Interpreted Max UTC",
            ],
            [
                [
                    row["table"],
                    row["column"],
                    row["detected_unit"],
                    row["raw_min"],
                    row["raw_max"],
                    row["interpreted_min_utc"],
                    row["interpreted_max_utc"],
                ]
                for row in time_rows
            ],
        )
    )
    lines.extend(["", "## 7. Encoding Findings", ""])
    if encoding_findings:
        lines.append(
            "Mojibake-like sequences were found in strings decoded by Spark as UTF-8. "
            "This confirms that the sequences are present in decoded data and are not "
            "only a PowerShell display artifact. No values were changed."
        )
        lines.append("")
        lines.extend(
            markdown_table(
                ["Table", "Column", "Affected Records", "Affected %"],
                [
                    [
                        row["table"],
                        row["column"],
                        row["affected_records"],
                        f"{row['affected_percent']:.6f}",
                    ]
                    for row in encoding_findings
                ],
            )
        )
    else:
        lines.append(
            "Spark found none of the configured mojibake patterns in decoded cell values. "
            "The earlier PowerShell rendering is therefore a terminal-display issue or "
            "remains unsupported by evidence from this audit."
        )
    lines.extend(
        [
            "",
            "Configured patterns and samples are recorded in ",
            "`data/audit/encoding_profile.csv`.",
            "",
            "## 8. Referential Coverage",
            "",
            "Comparison uses exact raw strings by default. When both sides contain only ",
            "integral numeric values but differ in representation (for example `123` versus ",
            "`123.0`), the audit additionally uses a numeric canonical form. Exact-raw and ",
            "compared counts are both preserved in `data/audit/referential_profile.csv`; ",
            "raw files are not changed.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            [
                "Parent",
                "Child",
                "Key",
                "Child Non-Missing Rows",
                "Comparison",
                "Compared Child Keys",
                "Matched",
                "Unmatched",
                "Coverage %",
            ],
            [
                [
                    row["parent_table"],
                    row["child_table"],
                    f"{row['child_key']} → {row['parent_key']}",
                    row["child_non_missing_rows"],
                    row["comparison_mode"],
                    row["compared_child_distinct_keys"],
                    row["matched_distinct_keys"],
                    row["unmatched_distinct_keys"],
                    f"{row['coverage_percent']:.6f}",
                ]
                for row in referential_rows
            ],
        )
    )
    lines.extend(["", "## 9. Important Findings", ""])
    findings = [
        f"All {len(inventory_rows)} raw CSV files were readable by Spark.",
        f"{len(notable_missing)} columns have at least 20% missing values.",
        f"{len(non_unique)} audited candidate/key fields are non-unique or contain missing values.",
        f"{len(full_duplicates)} tables contain duplicate full rows.",
        f"{len(orphan_relations)} audited relationships contain unmatched distinct child keys.",
    ]
    if encoding_findings:
        findings.append(
            f"Mojibake-like patterns occur in {len(encoding_findings)} table/column profiles."
        )
    else:
        findings.append("No configured mojibake pattern was found by Spark.")
    lines.extend(f"- {finding}" for finding in findings)
    lines.extend(
        [
            "",
            "## 10. Implications for D04",
            "",
            "D04 will need explicit, documented rules for missing values, duplicates, key ",
            "cardinality, orphan records, timestamp conversion, and any confirmed encoding ",
            "issues. This D03 audit does not clean, drop, replace, join, or otherwise alter ",
            "the raw data.",
            "",
        ]
    )
    (docs_dir / "d03_data_quality_report.md").write_text(
        "\n".join(lines).rstrip() + "\n", encoding="utf-8"
    )


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    raw_dir = project_root / "data" / "raw"
    audit_dir = project_root / "data" / "audit"
    docs_dir = project_root / "docs"
    before_snapshot = raw_file_snapshot(raw_dir)

    if len(before_snapshot) != len(TABLES):
        raise RuntimeError(
            f"Expected {len(TABLES)} raw CSV files, found {len(before_snapshot)}"
        )

    spark = (
        SparkSession.builder.appName(APP_NAME).master("local[*]").getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    inventory_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    time_rows: list[dict[str, Any]] = []
    encoding_rows: list[dict[str, Any]] = []
    relation_values: dict[tuple[str, str], set[str]] = {}

    try:
        print(f"Spark version: {spark.version}")
        print(f"Application: {APP_NAME}")
        print("Master: local[*]")
        for table in TABLES:
            audit_table(
                spark,
                raw_dir,
                table,
                inventory_rows,
                missing_rows,
                key_rows,
                duplicate_rows,
                time_rows,
                encoding_rows,
                relation_values,
            )

        referential_rows = build_referential_profile(missing_rows, relation_values)

        write_csv(
            audit_dir / "table_inventory.csv",
            inventory_rows,
            ["table", "path", "rows", "columns", "column_names", "schema_json"],
        )
        write_csv(
            audit_dir / "missing_profile.csv",
            missing_rows,
            [
                "table",
                "column",
                "raw_spark_type",
                "total_rows",
                "missing_count",
                "missing_percent",
                "candidate_role",
                "notes",
            ],
        )
        write_csv(
            audit_dir / "key_profile.csv",
            key_rows,
            [
                "table",
                "candidate_key",
                "total_rows",
                "null_key_count",
                "distinct_count",
                "duplicate_count",
                "assessment",
            ],
        )
        write_csv(
            audit_dir / "duplicate_profile.csv",
            duplicate_rows,
            ["table", "total_rows", "distinct_full_rows", "duplicate_full_rows"],
        )
        write_csv(
            audit_dir / "time_profile.csv",
            time_rows,
            [
                "table",
                "column",
                "detected_unit",
                "raw_min",
                "raw_max",
                "interpreted_min_utc",
                "interpreted_max_utc",
                "sample_values",
            ],
        )
        write_csv(
            audit_dir / "encoding_profile.csv",
            encoding_rows,
            [
                "table",
                "column",
                "total_rows",
                "affected_records",
                "affected_percent",
                "sample_values",
            ],
        )
        write_csv(
            audit_dir / "referential_profile.csv",
            referential_rows,
            [
                "parent_table",
                "child_table",
                "parent_key",
                "child_key",
                "child_non_missing_rows",
                "raw_child_distinct_keys",
                "comparison_mode",
                "compared_child_distinct_keys",
                "exact_matched_distinct_keys",
                "exact_unmatched_distinct_keys",
                "matched_distinct_keys",
                "unmatched_distinct_keys",
                "coverage_percent",
            ],
        )
        write_data_dictionary(docs_dir, inventory_rows, missing_rows)
        write_quality_report(
            docs_dir,
            inventory_rows,
            missing_rows,
            key_rows,
            duplicate_rows,
            time_rows,
            encoding_rows,
            referential_rows,
            spark.version,
        )

        after_snapshot = raw_file_snapshot(raw_dir)
        if before_snapshot != after_snapshot:
            raise RuntimeError("Raw CSV file size or modification time changed during audit")

        postings = next(row for row in inventory_rows if row["table"] == "postings")
        if postings["rows"] != 123849:
            raise RuntimeError(
                f"Expected 123849 postings rows, found {postings['rows']}"
            )

        print("\n" + "=" * 72)
        print(f"Audited CSV files: {len(inventory_rows)}")
        print(f"postings rows: {postings['rows']}")
        print("Raw CSV snapshot unchanged: True")
        print(f"Audit output: {audit_dir}")
        print("D03 data audit completed successfully.")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
