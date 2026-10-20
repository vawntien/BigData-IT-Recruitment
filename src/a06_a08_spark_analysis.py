"""Integrate the supplied candidate with A01/A03/A05 contracts; no raw fallback.

Real schemas remain subject to TV1 D06/D07 confirmation. Imports are lazy so a
missing runtime produces a persisted blocked manifest, not fictitious results.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from tv2_csv import ROOT, sha256, write_json
from tech_skill_extractor import SOURCE_FIELD

SUCCESS_STATES = ("PROCESSED_WITH_MATCH", "PROCESSED_NO_MATCH")
PROVENANCE = ["run_id", "dictionary_version", "dictionary_sha256", "extractor_version", "source_field"]
F = T = None


def load_spark():
    global F, T
    from pyspark.sql import functions, types
    F, T = functions, types


def artifact_digest(path):
    path = Path(path)
    if path.is_file():
        return sha256(path)
    files = sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        raise ValueError(f"Missing/empty artifact: {path}")
    body = [[p.relative_to(path).as_posix(), p.stat().st_size, sha256(p)] for p in files]
    return hashlib.sha256(json.dumps(body, separators=(",", ":")).encode()).hexdigest()


def runtime():
    result = subprocess.run(["java", "-version"], capture_output=True, text=True) if __import__("shutil").which("java") else None
    java = ((result.stderr or result.stdout).splitlines()[0] if result else "NOT_FOUND")
    return dict(pyspark_available=importlib.util.find_spec("pyspark") is not None, java=java,
                spark_executed=False)


def confirmation(receipt, digests):
    if not isinstance(receipt, dict) or not receipt.get("approved_by") or not receipt.get("approved_on"):
        return False
    return all(receipt.get(k) == v for k, v in digests.items())


def preflight(config):
    """Verify explicit confirmations against the exact artifacts, without Spark."""
    ready, notes = {}, {}
    if config.get("schema_version") != 1 or config.get("run_kind") != "OFFICIAL":
        raise ValueError("Use a schema_version=1 OFFICIAL input contract; synthetic tests call frames directly")
    def path(key):
        value = config.get(key)
        return Path(value) if value and Path(value).exists() else None
    jobs = path("it_jobs")
    ready["D06"] = bool(jobs and confirmation(config.get("d06_confirmation"), {"input_sha256": artifact_digest(jobs)}))
    js, sk = path("job_skills"), path("skill_map")
    ready["D05"] = bool(js and sk and confirmation(config.get("d05_confirmation"), {"job_skills_sha256": artifact_digest(js), "skill_map_sha256": artifact_digest(sk)}))
    a05 = path("a05_run_directory")
    a05_manifest = a05 / "run_manifest.json" if a05 else None
    ready["A05"] = bool(a05_manifest and a05_manifest.is_file() and
                         all((a05 / (name + ".parquet")).exists() for name in ["job_skill_technical", "skill_source_processing"]) and
                         confirmation(config.get("a05_confirmation"), {"run_manifest_sha256": sha256(a05_manifest)}))
    if ready["A05"]:
        m = json.loads(a05_manifest.read_text(encoding="utf-8"))
        ready["A05"] = m.get("status") in {"PARQUET_WRITTEN_PENDING_REVIEW", "SUCCESS"} and m.get("dictionary_version") == "0.1.2"
        notes["a05_manifest"] = m
    salary = path("salary_clean")
    approval = config.get("d07_approval") or {}
    ready["D07"] = bool(salary and confirmation(approval, {"input_sha256": artifact_digest(salary)}) and
                         approval.get("policy") == "posted_min_max_separate_currency_period_source" and
                         approval.get("q07_contract_version") == 2 and
                         approval.get("quantile_method") == "exact_continuous_linear_interpolation_double" and
                         approval.get("eligibility") == "D07_USABLE_WHOLE_SELECTED_BUNDLE" and
                         approval.get("source_grain") == "salary_source" and
                         approval.get("outlier_policy") == "NO_ADDITIONAL_FILTER" and
                         "minimum_salary_group_n" in approval and
                         approval["minimum_salary_group_n"] == config.get("minimum_salary_group_n") and
                         bool(config.get("q07_scope_id")))
    return ready, notes


def new_manifest(config, run_id):
    deps, notes = preflight(config)
    environment = runtime()
    states = {}
    for q in range(1, 9):
        required = ["D06"] + (["D05"] if q == 5 else ["A05"] if q == 6 else ["D07"] if q == 7 else [])
        missing = [k for k in required if not deps[k]]
        states[f"Q{q:02d}"] = dict(status="BLOCKED_DEPENDENCY" if missing else "READY", missing=missing,
                                     denominator=None, coverage=None, tables=[])
    return dict(schema_version=1, run_id=run_id, run_kind="OFFICIAL", date="2026-10-19",
                created_utc=datetime.now(timezone.utc).isoformat(), status="BLOCKED_DEPENDENCY" if not deps["D06"] else "READY",
                dependencies=deps, environment=environment, queries=states, tables={}, input_contract=config,
                provenance={"analysis_sha256": sha256(Path(__file__)), "dictionary_sha256": sha256(ROOT / "config/tech_skills.json"),
                            "q07_implementation_sha256": sha256(ROOT / "src/q07_salary.py"),
                            "q07_contract_sha256": sha256(ROOT / "config/q07_salary_contract_v2.json")},
                a05_manifest=notes.get("a05_manifest"), taxonomy_executed=False, etl_executed=False)


def require(df, columns, label):
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f"{label}: missing columns {sorted(missing)}")


def unique(df, keys, label):
    require(df, keys, label)
    bad = F.lit(False)
    for key in keys:
        bad = bad | F.col(key).isNull()
    if df.filter(bad).limit(1).count() or df.groupBy(*keys).count().filter("count > 1").limit(1).count():
        raise ValueError(f"{label}: NULL/duplicate key {keys}")


def category(name):
    value = F.trim(F.col(name))
    return F.when(value == "", F.lit(None)).otherwise(value)


def ratio(numerator, denominator):
    return F.when(F.lit(denominator) > 0, numerator / F.lit(denominator)).otherwise(F.lit(None).cast("double"))


def validate_d06(d, group):
    require(d, ["job_id", "description", "it_decision", "is_it", "taxonomy_version", "taxonomy_sha256", group], "D06")
    unique(d, ["job_id"], "D06")
    expected = {"job_id": T.LongType, "description": T.StringType, "is_it": T.BooleanType,
                "taxonomy_version": T.StringType, "taxonomy_sha256": T.StringType, "it_decision": T.StringType, group: T.StringType}
    if any(not isinstance(d.schema[k].dataType, typ) for k, typ in expected.items()):
        raise ValueError("D06 schema differs from A04 handoff/A05 adapter")
    if d.filter(F.col("it_decision").isNull() | (F.col("it_decision") != "ACCEPT") | F.col("is_it").isNull() | ~F.col("is_it") |
                F.col("taxonomy_version").isNull() | (F.trim("taxonomy_version") == "") |
                F.col("taxonomy_sha256").isNull() | (F.trim("taxonomy_sha256") == "")).limit(1).count():
        raise ValueError("D06 must contain confirmed ACCEPT/true with taxonomy provenance")
    if d.select("taxonomy_version", "taxonomy_sha256").distinct().count() != 1:
        raise ValueError("D06 must use one version/hash")
    if not d.count():
        raise ValueError("D06 is empty")


def categorical(d, column, n):
    require(d, [column], column)
    if not isinstance(d.schema[column].dataType, T.StringType):
        raise ValueError(f"Expected string {column}")
    values = d.select("job_id", category(column).alias("category"))
    valid = values.filter("category IS NOT NULL").count()
    table = values.groupBy("category").agg(F.countDistinct("job_id").alias("job_count"))
    table = table.withColumn("denominator_all_it", F.lit(n)).withColumn("denominator_known", F.lit(valid))
    return table.withColumn("share_all_it", ratio(F.col("job_count"), n)).withColumn("share_known", F.when(F.col("category").isNotNull(), ratio(F.col("job_count"), valid))), valid


def technical_tables(d, bridge, proc):
    """A05 source_status (not status); zero-hit jobs remain in every denominator."""
    require(bridge, ["job_id", "skill_code", "skill_name", *PROVENANCE], "A05 bridge")
    require(proc, ["job_id", "source_status", "technical_skills", *PROVENANCE], "A05 processing")
    unique(bridge, ["job_id", "skill_code"], "A05 bridge")
    unique(proc, ["job_id", "source_field"], "A05 processing")
    for frame in [proc, bridge]:
        if not isinstance(frame.schema["job_id"].dataType, T.LongType):
            raise ValueError("A05 job_id must be bigint, no implicit string JOIN")
        if frame.select("job_id").distinct().join(d.select("job_id"), "job_id", "left_anti").limit(1).count():
            raise ValueError("A05 orphan outside D06")
        if frame.filter(F.col("source_field").isNull() | (F.col("source_field") != SOURCE_FIELD)).limit(1).count():
            raise ValueError(f"A05 only {SOURCE_FIELD} is enabled")
        for col in PROVENANCE:
            if frame.filter(F.col(col).isNull() | (F.trim(F.col(col)) == "")).limit(1).count():
                raise ValueError("A05 missing provenance")
    if proc.count() != d.count():
        raise ValueError("A05 must have status for all D06 jobs, including zero-hit/missing")
    versions = proc.select(*PROVENANCE).unionByName(bridge.select(*PROVENANCE)).distinct().collect()
    if len(versions) != 1 or versions[0]["dictionary_version"] != "0.1.2":
        raise ValueError("Mixed A05 runs/dictionaries or dictionary differs from frozen v0.1.2")
    expected_hash = sha256(ROOT / "config/versions/tech_skills_v0.1.2.json")
    if versions[0]["dictionary_sha256"] != expected_hash:
        raise ValueError("A05 dictionary hash is not v0.1.2")
    statuses = [*SUCCESS_STATES, "SOURCE_MISSING", "FAILED", "PARTIAL"]
    if proc.filter(F.col("source_status").isNull() | ~F.col("source_status").isin(statuses)).limit(1).count():
        raise ValueError("Unknown A05 source_status")
    success = proc.filter(F.col("source_status").isin(*SUCCESS_STATES))
    if success.filter(F.col("technical_skills").isNull() |
                      ((F.col("source_status") == "PROCESSED_NO_MATCH") & (F.size("technical_skills") != 0)) |
                      ((F.col("source_status") == "PROCESSED_WITH_MATCH") & (F.size("technical_skills") == 0))).limit(1).count():
        raise ValueError("A05 NULL/empty status mismatch")
    pairs = success.select("job_id", F.explode("technical_skills").alias("skill_code"))
    unique(pairs, ["job_id", "skill_code"], "A05 processing skills")
    actual = bridge.select("job_id", "skill_code")
    if pairs.exceptAll(actual).limit(1).count() or actual.exceptAll(pairs).limit(1).count():
        raise ValueError("A05 bridge and successful status skills differ")
    if bridge.select("skill_code", "skill_name").distinct().groupBy("skill_code").count().filter("count > 1").limit(1).count():
        raise ValueError("Inconsistent skill name")
    processed = success.select("job_id").join(d.select("job_id", "a02_group", "formatted_experience_level"), "job_id")
    count = processed.count()
    tables = {"q06_skills_global": bridge.groupBy("skill_code", "skill_name").agg(F.countDistinct("job_id").alias("job_count"))
              .withColumn("processed_n", F.lit(count)).withColumn("share_of_processed", ratio(F.col("job_count"), count))}
    for column, suffix in [("a02_group", "group"), ("formatted_experience_level", "experience")]:
        # Explicit missing category token is avoided: NULL groups join null-safe.
        base = processed.withColumn("dimension", category(column)).drop(column)
        denom = base.groupBy("dimension").agg(F.countDistinct("job_id").alias("processed_n"))
        numbers = bridge.join(base.select("job_id", "dimension"), "job_id").groupBy("dimension", "skill_code", "skill_name").agg(F.countDistinct("job_id").alias("job_count"))
        joined = numbers.alias("a").join(denom.alias("b"), F.col("a.dimension").eqNullSafe(F.col("b.dimension")), "left")
        tables["q06_skills_by_" + suffix] = joined.select(F.col("a.dimension").alias(column), "skill_code", "skill_name", "job_count", "processed_n").withColumn("share_of_processed_group", F.col("job_count") / F.col("processed_n"))
    return tables, dict(denominator=count, all_it=d.count(), zero_hit_jobs=success.filter("source_status = 'PROCESSED_NO_MATCH'").count(),
                        coverage=count / d.count(), provenance=versions[0].asDict(),
                        source_status_counts=[r.asDict() for r in proc.groupBy("source_status").count().collect()])


def analyze_frames(d, config, bridge=None, proc=None, js=None, sk=None, salary=None):
    load_spark()
    validate_d06(d, config["group_column"])
    n = d.count()
    d = d.withColumn("a02_group", category(config["group_column"]))
    tables, metadata = {}, {}
    for q, column, name in [("Q01", "a02_group", "q01_role_groups"), ("Q02", "formatted_experience_level", "q02_experience"),
                             ("Q03", "location", "q03_location"), ("Q04", "formatted_work_type", "q04_work_type")]:
        tables[name], valid = categorical(d, column, n)
        metadata[q] = dict(status="SUCCESS", denominator=valid if q == "Q03" else n, known_jobs=valid,
                           coverage=valid/n, missing_jobs=n-valid, tables=[name])
    require(d, ["remote_allowed"], "D06")
    if not isinstance(d.schema["remote_allowed"].dataType, T.BooleanType):
        raise ValueError("remote_allowed must be nullable boolean; do not infer onsite/hybrid")
    tables["q04_remote_flag"] = d.groupBy("remote_allowed").agg(F.countDistinct("job_id").alias("job_count")).withColumn("denominator_all_it", F.lit(n)).withColumn("share_all_it", ratio(F.col("job_count"), n))
    metadata["Q04"]["tables"].append("q04_remote_flag")
    if "work_type" in d.columns:
        tables["q04_work_type_crosscheck"] = d.groupBy("formatted_work_type", "work_type").agg(F.countDistinct("job_id").alias("job_count"))
        metadata["Q04"]["tables"].append("q04_work_type_crosscheck")
    if js is not None and sk is not None:
        require(js, ["job_id", "skill_abr"], "D05 job_skills")
        require(sk, ["skill_abr", "skill_name"], "D05 skills")
        unique(sk, ["skill_abr"], "D05 skills")
        if not isinstance(js.schema["job_id"].dataType,T.LongType) or any(not isinstance(frame.schema[col].dataType,T.StringType) for frame,col in [(js,"skill_abr"),(sk,"skill_abr"),(sk,"skill_name")]):
            raise ValueError("Q05 explicit bigint/string JOIN schema required; no implicit cast")
        scoped = js.join(d.select("job_id"), "job_id", "inner").select("job_id", "skill_abr").distinct()
        labels = scoped.join(sk.select("skill_abr", "skill_name"), "skill_abr", "left")
        valid = labels.filter(category("skill_name").isNotNull())
        covered = valid.select("job_id").distinct().count()
        tables["q05_functional_labels"] = valid.groupBy("skill_abr", "skill_name").agg(F.countDistinct("job_id").alias("job_count")).withColumn("labeled_n", F.lit(covered)).withColumn("share_of_labeled_jobs", ratio(F.col("job_count"), covered))
        tables["q05_unmapped_labels"] = labels.filter(category("skill_name").isNull()).groupBy("skill_abr").agg(F.countDistinct("job_id").alias("job_count"))
        metadata["Q05"] = dict(status="SUCCESS", denominator=covered, coverage=covered/n, all_it=n, tables=["q05_functional_labels", "q05_unmapped_labels"])
    if bridge is not None and proc is not None:
        skill_tables, details = technical_tables(d, bridge, proc)
        tables.update(skill_tables)
        metadata["Q06"] = dict(status="SUCCESS", tables=list(skill_tables), **details)
    if salary is not None:
        from q07_salary import salary_tables
        scope_id = config.get("q07_scope_id")
        salary_outputs = salary_tables(d, salary, scope_id=scope_id,
                                       minimum_n=config.get("minimum_salary_group_n"))
        tables.update(salary_outputs)
        metadata["Q07"] = dict(status="SUCCESS", denominator=None, coverage=None,
            population_n=n, salary_basis="POSTED_NATIVE", contract_version=2,
            quantile_method="exact_continuous_linear_interpolation_double",
            denominators="n_min/n_max per cell; coverage uses population_n per group/experience",
            tables=list(salary_outputs))
    metadata["Q08"] = dict(status="SUCCESS", denominator=n, coverage={}, tables=[])
    for column, prefix in [("original_listed_time", "q08_original"), ("listed_time", "q08_listed")]:
        require(d, [column], "D04 timestamp on D06")
        if not isinstance(d.schema[column].dataType, T.TimestampType):
            raise ValueError(f"{column} must be Spark timestamp UTC; no epoch/string guessing")
        valid = d.filter(F.col(column).isNotNull())
        count = valid.count()
        metadata["Q08"]["coverage"][column] = dict(valid_jobs=count, all_it=n, share=count/n)
        for suffix, expr in [("month", F.date_format(column, "yyyy-MM")), ("week_start_utc", F.date_format(F.date_trunc("week", F.col(column)), "yyyy-MM-dd"))]:
            name = prefix + "_" + suffix
            tables[name] = valid.select("job_id", expr.alias("period")).groupBy("period").agg(F.countDistinct("job_id").alias("job_count")).withColumn("valid_timestamp_n", F.lit(count)).withColumn("share_of_valid", ratio(F.col("job_count"), count))
            metadata["Q08"]["tables"].append(name)
    return tables, metadata, n


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    out = Path(args.output).resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError("Choose a new output directory inside this repository")
    config = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    manifest = new_manifest(config, args.run_id)
    manifest["provenance"]["contract_sha256"] = sha256(args.contract)
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "manifest.json", manifest, exclusive=True)
    if not manifest["dependencies"]["D06"]:
        print(json.dumps({"status":"BLOCKED_DEPENDENCY", "queries":manifest["queries"]}))
        return 2
    if not manifest["environment"]["pyspark_available"]:
        manifest["status"] = "BLOCKED_ENVIRONMENT"
        write_json(out / "manifest.json", manifest)
        return 2
    spark = None
    try:
        load_spark()
        from d05_utils import get_spark_session
        spark = get_spark_session("TV2-A06-A08", ROOT)
        spark.conf.set("spark.sql.session.timeZone", "UTC")
        d = spark.read.parquet(config["it_jobs"])
        optional = {}
        if manifest["dependencies"]["A05"]:
            for key, name in [("bridge", "job_skill_technical"), ("proc", "skill_source_processing")]:
                optional[key] = spark.read.parquet(str(Path(config["a05_run_directory"]) / (name + ".parquet")))
        if manifest["dependencies"]["D05"]:
            optional.update(js=spark.read.parquet(config["job_skills"]), sk=spark.read.parquet(config["skill_map"]))
        if manifest["dependencies"]["D07"]:
            optional["salary"] = spark.read.parquet(config["salary_clean"])
        tables, details, n = analyze_frames(d, config, **optional)
        if "Q06" in details:
            for key in ["run_id", "dictionary_version", "dictionary_sha256"]:
                if details["Q06"]["provenance"][key] != manifest["a05_manifest"][key]:
                    raise ValueError("A05 table provenance differs from its confirmed run manifest")
        manifest.update(confirmed_it_jobs=n, spark_version=spark.version, timezone="UTC")
        manifest["environment"]["spark_executed"] = True
        manifest["provenance"]["taxonomy"] = [r.asDict() for r in d.select("taxonomy_version", "taxonomy_sha256").distinct().collect()]
        for name, table in tables.items():
            destination = out / (name + ".parquet")
            table.write.mode("errorifexists").parquet(str(destination))
            saved = spark.read.parquet(str(destination))
            if saved.count() != table.count() or table.exceptAll(saved.select(table.columns)).limit(1).count():
                raise AssertionError(f"Parquet readback mismatch: {name}")
            with (out / (name + ".csv")).open("x", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=table.columns)
                writer.writeheader()
                for row in saved.toLocalIterator():
                    writer.writerow({k: json.dumps(v,default=str) if isinstance(v, (list,dict)) else v for k,v in row.asDict().items()})
            manifest["tables"][name] = dict(rows=saved.count(), parquet=str(destination), parquet_sha256=artifact_digest(destination), csv=name + ".csv", csv_sha256=sha256(out / (name + ".csv")))
        for q, detail in details.items():
            manifest["queries"][q] = detail
        manifest["status"] = "SUCCESS" if all(q["status"] == "SUCCESS" for q in manifest["queries"].values()) else "PARTIAL_SUCCESS"
    except Exception as error:
        manifest.update(status="FAILED", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        if spark:
            spark.stop()
        write_json(out / "manifest.json", manifest)
    print(json.dumps({"status":manifest["status"], "queries":manifest["queries"]}, default=str))
    return 0 if manifest["status"] == "SUCCESS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
