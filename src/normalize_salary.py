"""D07 all-jobs salary staging. Spark expressions only; never calls a classifier.

No imputation, FX, D05 mutation, source blending, inferred hours, or IT population.
Annual equivalents are policy assumptions, not observed annual earnings.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
BASE = "5fda1789b84494a856743c087d10fc511d013d93"
FIELDS = ("min_salary", "med_salary", "max_salary", "currency", "pay_period", "compensation_type")
AMOUNTS = FIELDS[:3]
POLICY_PATH = ROOT / "config/d07_salary_policy_v1.json"
STATUSES = ("MISSING", "USABLE", "INVALID", "AMBIGUOUS", "EXCLUDED")


def now():
    return datetime.now(timezone.utc).isoformat()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_data(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2,
                      default=lambda v: str(v) if isinstance(v, Decimal) else _unsupported(v), allow_nan=False)


def _unsupported(value):
    raise TypeError(type(value).__name__)


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8", newline="\n") as stream:
        stream.write(json_data(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def inventory(directory):
    directory = Path(directory).resolve()
    if not (directory / "_SUCCESS").is_file():
        raise ValueError("Parquet _SUCCESS missing")
    entries = []
    for p in sorted(directory.rglob("*.parquet")):
        if p.is_symlink() or any(x.startswith((".", "_temporary")) for x in p.relative_to(directory).parts):
            raise ValueError("Uncommitted/linked Parquet file")
        st = p.stat()
        digest = file_sha(p)
        if (st.st_size, st.st_mtime_ns) != (p.stat().st_size, p.stat().st_mtime_ns):
            raise ValueError("Dataset changed during hashing")
        entries.append({"path": p.relative_to(directory).as_posix(), "bytes": st.st_size, "sha256": digest})
    if not entries:
        raise ValueError("No Parquet files")
    # Same canonical inventory serialization as D06, without importing its classifier modules.
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {"fingerprint": hashlib.sha256(encoded).hexdigest(), "files": entries,
            "bytes": sum(x["bytes"] for x in entries)}


def load_policy(path=POLICY_PATH):
    data = Path(path).read_bytes()
    p = json.loads(data)
    if (p.get("version") != "d07-salary-v1"
            or p.get("scope") != "ALL_JOBS_NORMALIZATION_STAGING_NOT_OFFICIAL_IT"
            or p.get("fx_conversion") != "NONE" or p.get("output_decimal") != "decimal(38,4)"
            or p.get("source_resolution") != "WHOLE_SOURCE_NO_COALESCE_CONFLICT_ABSTAIN"
            or p.get("nonpositive_values") != "INVALID"
            or p.get("compensation_types") != ["BASE_SALARY"]):
        raise ValueError("Unsupported D07 policy")
    a = p["annualization"]
    if (set(a) != {"hours_per_week", "weeks_per_year", "months_per_year", "weeks_per_biweekly_period"}
            or any(type(v) is not int for v in a.values())
            or not 1 <= a["hours_per_week"] <= 168 or not 1 <= a["weeks_per_year"] <= 53
            or a["months_per_year"] != 12 or a["weeks_per_biweekly_period"] != 2
            or a["weeks_per_year"] % 2):
        raise ValueError("Annualization assumptions invalid; require whole integer factors")
    currencies = p.get("currencies", [])
    if (not currencies or len(set(currencies)) != len(currencies)
            or any(not isinstance(c, str) or not re.fullmatch("[A-Z]{3}", c) for c in currencies)):
        raise ValueError("Explicit distinct currency codes required")
    p["sha256"] = hashlib.sha256(data).hexdigest()
    p["period_factors"] = {"YEARLY": 1, "MONTHLY": 12, "WEEKLY": a["weeks_per_year"],
        "BIWEEKLY": a["weeks_per_year"] // 2, "HOURLY": a["weeks_per_year"] * a["hours_per_week"]}
    return p


def create_session(master="local[4]", partitions=4, windows_fs_jar=None):
    from pyspark.sql import SparkSession
    if master not in ("local[1]", "local[2]", "local[4]") or not 1 <= partitions <= 64:
        raise ValueError("D07 validated scope is local[1/2/4], partitions 1..64")
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    os.environ.setdefault("PYSPARK_SUBMIT_ARGS", "--driver-memory 3g pyspark-shell")
    b = SparkSession.builder.master(master).appName("D07-Salary-Staging")
    if os.name == "nt":
        if not windows_fs_jar or not Path(windows_fs_jar).is_file():
            raise ValueError("Explicit Windows filesystem JAR required")
        jar = str(Path(windows_fs_jar).resolve())
        b = (b.config("spark.driver.extraClassPath", jar).config("spark.executor.extraClassPath", jar)
             .config("spark.hadoop.fs.file.impl", "d04.localfs.NoPermissionLocalFileSystem")
             .config("spark.hadoop.fs.file.impl.disable.cache", "true"))
    spark = (b.config("spark.sql.session.timeZone", "UTC").config("spark.sql.ansi.enabled", "true")
             .config("spark.sql.shuffle.partitions", str(partitions))
             .config("spark.sql.autoBroadcastJoinThreshold", "-1")
             .config("spark.sql.adaptive.autoBroadcastJoinThreshold", "-1")
             .config("spark.speculation", "false").getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    java = spark.sparkContext._jvm.java.lang.System.getProperty("java.version")
    if sys.version_info[:2] != (3, 11) or spark.version != "4.2.0" or not java.startswith("21."):
        spark.stop()
        raise ValueError("Require Python3.11/PySpark4.2.0/Java21")
    return spark


def input_schema_check(df):
    from pyspark.sql import types as T
    required = {"job_id": "bigint", "normalized_salary": "decimal(20,4)",
                "source_text_file": "string", "canonical_schema_version": "string"}
    required.update({f: "decimal(20,4)" if f in AMOUNTS else "string" for f in FIELDS})
    actual = {f.name: f.dataType.simpleString() for f in df.schema}
    if any(actual.get(k) != v for k, v in required.items()):
        raise ValueError("Salary input types must match D05; no lossy casts accepted")
    if "salary_record" not in df.columns or not isinstance(df.schema["salary_record"].dataType, T.StructType):
        raise ValueError("Missing salary_record struct")
    nested = {f.name: f.dataType.simpleString() for f in df.schema["salary_record"].dataType}
    if nested != {"salary_id": "bigint", **{f: required[f] for f in FIELDS}}:
        raise ValueError("Unexpected salary_record schema")


def key_stats(df, expected=None):
    from pyspark.sql import functions as F
    if df.schema["job_id"].dataType.simpleString() != "bigint":
        raise ValueError("job_id must be bigint")
    s = df.agg(F.count("*").alias("rows"), F.countDistinct("job_id").alias("unique"),
               F.coalesce(F.sum(F.col("job_id").isNull().cast("long")), F.lit(0)).alias("nulls")).first().asDict()
    s["duplicates"] = s["rows"] - s["unique"] - s["nulls"]
    if s["nulls"] or s["duplicates"] or (expected is not None and s["rows"] != expected):
        raise ValueError(f"Input/output grain violation: {s}")
    return s


def normalize(df, policy):
    """Pure deterministic distributed transform. Preserves both complete raw sources."""
    from pyspark.sql import functions as F
    input_schema_check(df)
    def token(c):
        s = F.upper(F.trim(c))
        return F.when(F.length(s) > 0, s)
    d = df.select("job_id", F.struct(*[F.col(f).alias(f) for f in FIELDS]).alias("raw_postings"),
        F.col("normalized_salary").alias("raw_postings_normalized_salary"),
        F.col("salary_record").alias("raw_salary_record"), "source_text_file", "canonical_schema_version")
    def has(prefix):
        return F.greatest(*[F.col(prefix + f).isNotNull().cast("int") for f in AMOUNTS]) == 1
    d = d.withColumn("postings_has_amount", has("raw_postings.")).withColumn("salaries_has_amount", has("raw_salary_record."))
    same = F.lit(True)
    for f in FIELDS:
        a, b = F.col("raw_postings." + f), F.col("raw_salary_record." + f)
        if f not in AMOUNTS:
            a, b = token(a), token(b)
        same = same & a.eqNullSafe(b)
    d = d.withColumn("source_conflict", F.col("postings_has_amount") & F.col("salaries_has_amount") & ~same)
    d = d.withColumn("salary_source", F.when(F.col("source_conflict"), "CONFLICT")
        .when(F.col("postings_has_amount") & F.col("salaries_has_amount"), "BOTH_AGREE")
        .when(F.col("postings_has_amount"), "POSTINGS").when(F.col("salaries_has_amount"), "SALARIES").otherwise("NONE"))
    d = d.withColumn("selected_salary", F.when(F.col("salary_source").isin("POSTINGS", "BOTH_AGREE"), F.col("raw_postings"))
        .when(F.col("salary_source") == "SALARIES", F.struct(*[F.col("raw_salary_record." + f).alias(f) for f in FIELDS])))
    for field in ("currency", "pay_period", "compensation_type"):
        d = d.withColumn("source_" + field, F.col("selected_salary." + field))
        d = d.withColumn("canonical_" + field, token(F.col("source_" + field)))
    v = {f: F.col("selected_salary." + f) for f in AMOUNTS}
    invalid = F.lit(False)
    for value in v.values():
        invalid = invalid | (value.isNotNull() & (value <= 0))
    ordering = F.lit(False)
    for a, b in (("min_salary", "med_salary"), ("med_salary", "max_salary"), ("min_salary", "max_salary")):
        ordering = ordering | (v[a].isNotNull() & v[b].isNotNull() & (v[a] > v[b]))
    checks = [
        (F.col("salary_source") == "NONE", "NO_SALARY_AMOUNT"),
        (F.col("source_conflict"), "SOURCE_CONFLICT"),
        (invalid, "NONPOSITIVE_SALARY"), (ordering, "INVALID_BOUNDS_ORDER"),
        ((F.col("salary_source") != "NONE") & ~F.col("source_conflict") & F.col("canonical_currency").isNull(), "MISSING_CURRENCY"),
        (F.col("canonical_currency").isNotNull() & ~F.col("canonical_currency").isin(policy["currencies"]), "UNSUPPORTED_CURRENCY"),
        ((F.col("salary_source") != "NONE") & ~F.col("source_conflict") & F.col("canonical_pay_period").isNull(), "MISSING_PERIOD"),
        (F.col("canonical_pay_period").isNotNull() & ~F.col("canonical_pay_period").isin(list(policy["period_factors"])), "UNKNOWN_PERIOD"),
        ((F.col("salary_source") != "NONE") & ~F.col("source_conflict") & F.col("canonical_compensation_type").isNull(), "MISSING_COMPENSATION_TYPE"),
        (F.col("canonical_compensation_type").isNotNull() & ~F.col("canonical_compensation_type").isin(policy["compensation_types"]), "EXCLUDED_COMPENSATION_TYPE"),
    ]
    d = d.withColumn("reason_codes", F.filter(F.array(*[F.when(c, F.lit(r)) for c, r in checks]), lambda x: x.isNotNull()))
    def reason(r):
        return F.array_contains(F.col("reason_codes"), r)
    status = (F.when(reason("NO_SALARY_AMOUNT"), "MISSING").when(reason("SOURCE_CONFLICT"), "AMBIGUOUS")
        .when(reason("NONPOSITIVE_SALARY") | reason("INVALID_BOUNDS_ORDER"), "INVALID")
        .when(reason("UNSUPPORTED_CURRENCY") | reason("EXCLUDED_COMPENSATION_TYPE"), "EXCLUDED")
        .when(F.size("reason_codes") > 0, "AMBIGUOUS").otherwise("USABLE"))
    d = d.withColumn("normalization_status", status)
    factor = F.create_map(*[item for k, n in policy["period_factors"].items() for item in (F.lit(k), F.lit(n))])[F.col("canonical_pay_period")]
    d = d.withColumn("conversion_factor", F.when(F.col("normalization_status") == "USABLE", factor.cast("decimal(10,0)")))
    d = d.withColumn("normalized_currency", F.when(F.col("normalization_status") == "USABLE", F.col("canonical_currency")))
    d = d.withColumn("normalized_unit", F.when(F.col("normalization_status") == "USABLE", F.lit("ANNUAL_EQUIVALENT")))
    for f in AMOUNTS:
        d = d.withColumn("normalized_" + f, (F.col("selected_salary." + f) * F.col("conversion_factor")).cast("decimal(38,4)"))
    return (d.withColumn("conversion_policy_version", F.lit(policy["version"]))
             .withColumn("conversion_policy_sha256", F.lit(policy["sha256"]))
             .withColumn("population_scope", F.lit(policy["scope"])))


def profile(df):
    from pyspark.sql import functions as F
    result = {"denominator_all_jobs": df.count(), "salary_record_rows": df.filter(F.col("salary_record").isNotNull()).count()}
    for name, prefix in (("postings", ""), ("salaries", "salary_record.")):
        result[name] = {"coverage_and_ranges": df.agg(
            *[F.count(F.col(prefix + f)).alias(f + "_non_null") for f in FIELDS],
            *[op(F.col(prefix + f)).alias(f + "_" + n) for f in AMOUNTS for n, op in (("min", F.min), ("max", F.max))]
        ).first().asDict(), "distributions": {}}
        for f in FIELDS[3:]:
            result[name]["distributions"][f] = [r.asDict() for r in df.groupBy(F.col(prefix + f).alias(f)).count().orderBy(F.desc("count"), F.asc(f)).collect()]
    result["upstream_normalized_salary"] = df.agg(F.count("normalized_salary").alias("non_null"),
        F.min("normalized_salary").alias("min"), F.max("normalized_salary").alias("max")).first().asDict()
    return result


def validate(source, output, policy, expected_rows=None):
    from pyspark.sql import functions as F
    input_stats, output_stats = key_stats(source, expected_rows), key_stats(output, expected_rows)
    if input_stats != output_stats:
        raise ValueError("Row counts differ")
    if source.select("job_id").exceptAll(output.select("job_id")).limit(1).count() or output.select("job_id").exceptAll(source.select("job_id")).limit(1).count():
        raise ValueError("Input/output key sets differ")
    recomputed = normalize(source, policy)
    if output.schema.toNullable() != recomputed.schema.toNullable():
        raise ValueError("Parquet schema changed")
    # Full typed distributed comparison checks decimals, NULLs, both raw structs, metadata, factors, reasons.
    if recomputed.exceptAll(output).limit(1).count() or output.exceptAll(recomputed).limit(1).count():
        raise ValueError("Determinism/raw preservation/Parquet value mismatch")
    usable = F.col("normalization_status") == "USABLE"
    bad = ~F.col("normalization_status").isin(*STATUSES) | F.col("normalization_status").isNull()
    bad = bad | (usable & (F.col("conversion_factor").isNull() | F.col("normalized_currency").isNull()))
    for f in AMOUNTS:
        a, b = F.col("selected_salary." + f), F.col("normalized_" + f)
        bad = bad | (usable & (a.isNull() != b.isNull())) | (~usable & b.isNotNull())
        bad = bad | (usable & b.isNotNull() & (b <= 0))
    bad = bad | (~usable & (F.col("conversion_factor").isNotNull() | F.col("normalized_unit").isNotNull() | F.col("normalized_currency").isNotNull()))
    bad = bad | (usable & ~F.col("normalized_currency").eqNullSafe(F.col("canonical_currency")))
    bad = bad | (~usable & (F.size("reason_codes") == 0))
    for a, b in (("min_salary", "med_salary"), ("med_salary", "max_salary"), ("min_salary", "max_salary")):
        bad = bad | (F.col("normalized_" + a) > F.col("normalized_" + b))
    if output.filter(bad).limit(1).count():
        raise ValueError("Normalization invariant / numeric overflow violation")
    counts = {r.normalization_status: r['count'] for r in output.groupBy("normalization_status").count().collect()}
    if sum(counts.values()) != input_stats["rows"]:
        raise ValueError("Status reconciliation failed")
    return {"status": "PASS", "input": input_stats, "output": output_stats, "status_counts": counts,
        "source_counts": {r.salary_source: r['count'] for r in output.groupBy("salary_source").count().collect()},
        "source_conflicts": output.filter("source_conflict").count(),
        "reason_counts_overlapping": {r.reason: r['count'] for r in output.select(F.explode("reason_codes").alias("reason")).groupBy("reason").count().collect()},
        "usable_currency_period_counts": [r.asDict() for r in output.filter(usable).groupBy("normalized_currency", "canonical_pay_period", "conversion_factor").count().orderBy("normalized_currency", "canonical_pay_period").collect()],
        "parquet_roundtrip_all_fields": "PASS", "raw_values_and_nulls_preserved": True,
        "numeric_overflow": 0, "invalid_period_annualized": 0, "fx_conversions": 0}


def join_classification(salary, classification, *, accept_policy_approved=False):
    """Contract only. Caller must verify an Official FULL completion seal first.

    Preserves all three populations in one frame; never uses Pilot as official IT.
    No analytics or ACCEPT population is returned without explicit policy acknowledgement.
    """
    from pyspark.sql import functions as F
    if not accept_policy_approved:
        raise PermissionError("Official FULL seal and human ACCEPT policy required before integration")
    key_stats(salary)
    key_stats(classification)
    required = {"it_decision", "is_it", "_d06_present", "taxonomy_version", "taxonomy_sha256"}
    if not required.issubset(classification.columns):
        raise ValueError("Incomplete D06 classification contract")
    if (salary.select("job_id").exceptAll(classification.select("job_id")).limit(1).count()
            or classification.select("job_id").exceptAll(salary.select("job_id")).limit(1).count()):
        raise ValueError("Official FULL key sets must match salary staging")
    valid = ((F.col("it_decision").eqNullSafe("ACCEPT") & F.col("is_it").eqNullSafe(True))
        | (F.col("it_decision").eqNullSafe("REJECT") & F.col("is_it").eqNullSafe(False))
        | (F.col("it_decision").eqNullSafe("REVIEW") & F.col("is_it").isNull()))
    if classification.filter(~valid | ~F.col("_d06_present").eqNullSafe(True)).limit(1).count():
        raise ValueError("Invalid classification decisions")
    return salary.join(classification.select("job_id", *sorted(required)), "job_id", "inner")


def safe_output(root, run_id):
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("Invalid run_id")
    target = root / "data/processed/d07/staging" / run_id
    if not target.resolve().is_relative_to(root):
        raise ValueError("Output escaped workspace")
    for p in (target, *target.parents):
        if p.is_symlink() or (p.exists() and getattr(p.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Linked output refused")
    if target.exists():
        raise FileExistsError("Never overwrite/resume existing run; choose NEW run_id")
    return target


def run(args):
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT).decode().strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    if branch != "feat/tv1-d07-salary" or subprocess.run(["git", "merge-base", "--is-ancestor", BASE, head], cwd=ROOT).returncode:
        raise ValueError("Use D07 branch descended from Official Runner")
    protected = set(subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE], cwd=ROOT).decode().splitlines())
    changed = set(subprocess.check_output(["git", "diff", "--name-only", BASE, "--"], cwd=ROOT).decode().splitlines())
    changed.update(subprocess.check_output(["git", "diff", "--cached", "--name-only", BASE, "--"], cwd=ROOT).decode().splitlines())
    if protected.intersection(changed):
        raise ValueError("D01-D06 tracked files changed")
    destination = safe_output(ROOT, args.run_id)
    audit = ROOT / "data/audit/d07" / args.run_id
    if audit.exists():
        raise FileExistsError("Existing audit refused")
    input_dir = ROOT / "data/processed/canonical/jobs"
    before = inventory(input_dir)
    policy = load_policy(args.policy)
    spark = create_session(args.master, args.partitions, args.windows_fs_jar)
    started, start = now(), time.perf_counter()
    created = False
    try:
        source = spark.read.parquet(str(input_dir))
        reference_schema = json.loads((ROOT / "data/audit/d05_canonical_schema.json").read_text(encoding="utf8"))
        if source.schema.jsonValue() != reference_schema:
            raise ValueError("Actual canonical schema differs from committed D05 schema")
        input_schema_check(source)
        stats = key_stats(source, 123849)
        from pyspark.sql import functions as F
        if source.filter(~F.col("canonical_schema_version").eqNullSafe("d05-v1")).limit(1).count():
            raise ValueError("Wrong canonical version")
        if inventory(input_dir)["fingerprint"] != before["fingerprint"]:
            raise ValueError("Input mutated during preflight")
        source_profile = profile(source)
        destination.mkdir(parents=True, exist_ok=False)
        created = True
        manifest = {"status": "RUNNING", "scope": policy["scope"], "run_id": args.run_id,
            "started_utc": started, "git_head": head, "branch": branch, "input_path": str(input_dir),
            "input_inventory": before, "input_stats": stats, "output_path": str(destination / "salaries.parquet"),
            "policy": policy, "source_sha256": file_sha(__file__),
            "environment": {"python": sys.version, "spark": spark.version,
                "java": spark.sparkContext._jvm.java.lang.System.getProperty("java.version"),
                "master": args.master, "partitions": args.partitions, "ansi_enabled": True},
            "d06_full_executed": False, "official_it_salary_executed": False}
        write_new(destination / "run_manifest.json", manifest)
        write_new(audit / "run_manifest.json", manifest)
        write_new(audit / "source_profile.json", source_profile)
        transformed = normalize(source, policy)
        write_start = time.perf_counter()
        transformed.repartition(args.partitions, "job_id").write.mode("errorifexists").parquet(str(destination / "salaries.parquet"))
        write_seconds = time.perf_counter() - write_start
        readback = spark.read.parquet(str(destination / "salaries.parquet"))
        validation = validate(source, readback, policy, 123849)
        if inventory(input_dir)["fingerprint"] != before["fingerprint"]:
            raise ValueError("Canonical changed during execution")
        write_new(audit / "output_schema.json", readback.schema.jsonValue())
        write_new(audit / "validation_summary.json", validation)
        write_new(destination / "validation_summary.json", validation)
        write_new(destination / "output_inventory.json", inventory(destination / "salaries.parquet"))
        seal = {"status": "SUCCEEDED", "scope": policy["scope"], "run_id": args.run_id,
            "finished_utc": now(), "total_seconds": time.perf_counter() - start, "write_seconds": write_seconds,
            "rows": stats["rows"], "manifest_sha256": file_sha(destination / "run_manifest.json"),
            "validation_sha256": file_sha(destination / "validation_summary.json"),
            "output_inventory_sha256": file_sha(destination / "output_inventory.json"),
            "output_fingerprint": inventory(destination / "salaries.parquet")["fingerprint"],
            "d06_full_executed": False, "official_it_salary_executed": False}
        write_new(destination / "completion.json", seal)
        write_new(audit / "completion.json", seal)
        print(json_data({"run": seal, "validation": validation}), flush=True)
        return seal
    except BaseException as exc:
        if created:
            failure = {"status": "FAILED", "error_type": type(exc).__name__, "at_utc": now(),
                       "run_id": args.run_id, "instruction": "Preserve partial run. Rerun with NEW run_id; never append/overwrite."}
            write_new(destination / "failure.json", failure)
            write_new(audit / "failure.json", failure)
        raise
    finally:
        spark.stop()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--policy", default=str(POLICY_PATH))
    p.add_argument("--master", default="local[4]")
    p.add_argument("--partitions", type=int, default=4)
    p.add_argument("--windows-fs-jar")
    run(p.parse_args())


if __name__ == "__main__":
    main()
