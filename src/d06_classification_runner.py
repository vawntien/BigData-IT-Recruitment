"""D06 controlled Pilot only. Full mode is deliberately unavailable.

Example: python src/d06_classification_runner.py --mode pilot --sample-size 1000
 --partitions 4 --output tmp/d06_pilot/<NEW_RUN> --taxonomy-config git:<PIN>:<PATH>
Only aggregate metrics and <=32 deterministic test keys return to the driver.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from d06_taxonomy_adapter import CONFIG_HASH, TV2_COMMIT
from d06_pilot_runtime import PilotDataError, PilotIntegrityError, pilot_schema
from d06_pilot_packaging import CONFIG_REF, build_package, verified_members, worker_runner
from d06_parity_validation import ROOT, protected_snapshot, verify_d05_base, write_json

PARITY_HEAD = "1c365741f0e3dcad9064473ae2c0c6b9f507ae25"
MAX_BASE = 1000
MAX_PILOT = 1200


def validate_options(mode, sample_size, partitions, output, root=ROOT):
    if mode != "pilot":
        raise PilotDataError("FULL mode locked: only --mode pilot is authorized")
    if type(sample_size) is not int or not 1 <= sample_size <= MAX_BASE:
        raise PilotDataError(f"Base sample must be 1..{MAX_BASE}; cannot scale to full dataset")
    if type(partitions) is not int or not 1 <= partitions <= 8:
        raise PilotDataError("Pilot partitions must be 1..8")
    output = Path(output).resolve()
    allowed = (root / "tmp/d06_pilot").resolve()
    if output == allowed or not output.is_relative_to(allowed):
        raise PilotDataError("Output must be a NEW child of tmp/d06_pilot")
    if output.exists():
        raise FileExistsError("Existing output directory; never overwrite")
    for ancestor in output.parents:
        if ancestor.is_symlink() or (ancestor.exists() and getattr(ancestor.lstat(), "st_file_attributes", 0) & 0x400):
            raise PilotDataError("Symlink/junction output path not allowed")
    return output


def validate_input(df):
    from pyspark.sql import functions as F
    required = {"job_id", "source_title", "source_description", "source_title_sha256", "source_description_sha256"}
    if not required.issubset(df.columns):
        raise PilotDataError("Missing canonical source columns")
    if df.schema["job_id"].dataType.simpleString() != "bigint":
        raise PilotDataError("Input job_id must already be canonical bigint")
    stats = df.agg(F.count("*").alias("rows"), F.countDistinct("job_id").alias("unique"),
                   F.sum(F.col("job_id").isNull().cast("long")).alias("nulls")).first().asDict()
    if not 0 < stats["rows"] <= MAX_PILOT or stats["nulls"] or stats["unique"] != stats["rows"]:
        raise PilotDataError(f"Input size/key violation: {stats}")
    bad = df.filter(
        F.col("source_title").isNull() | F.col("source_description").isNull()
        | F.col("source_title_sha256").isNull() | F.col("source_description_sha256").isNull()
        | (F.sha2("source_title", 256) != F.col("source_title_sha256"))
        | (F.sha2("source_description", 256) != F.col("source_description_sha256")))
    if bad.limit(1).count():
        raise PilotDataError("Missing source text/hash or canonical source hash mismatch")
    return stats


def select_sample(spark, sample_size, root=ROOT):
    from pyspark.sql import functions as F
    canonical = spark.read.parquet(str(root / "data/processed/canonical/jobs"))
    # Feature extraction scans canonical, but does NOT call the classifier.
    features = canonical.select("job_id", "job_functions",
        F.length("source_description").alias("description_chars"),
        (F.length(F.trim(F.coalesce(F.col("source_title"), F.lit("")))) == 0).alias("empty_title"),
        (F.length(F.trim(F.coalesce(F.col("source_description"), F.lit("")))) == 0).alias("empty_description"),
        F.col("source_description").rlike(r"<[^>]+>|&(?:[A-Za-z]+|#[0-9]+|#x[0-9a-fA-F]+);").alias("html_entities"),
        (F.col("source_title").rlike(r"[^\x00-\x7f]") |
         F.col("source_description").rlike(r"[^\x00-\x7f]")).alias("unicode")).cache()
    canonical_stats = features.agg(F.count("*").alias("rows"),
        F.countDistinct("job_id").alias("unique"),
        F.sum(F.col("job_id").isNull().cast("long")).alias("nulls")).first().asDict()
    if canonical_stats != {"rows": 123849, "unique": 123849, "nulls": 0}:
        raise PilotDataError("Canonical snapshot/grain differs from D05")

    def ids(df, reason):
        return df.select("job_id").withColumn("selection_reason", F.lit(reason))
    base = features.orderBy(F.xxhash64("job_id", F.lit(42)), "job_id").limit(sample_size)
    selections = ids(base, "hash42_base")
    for name in ("empty_title", "empty_description", "html_entities", "unicode"):
        selections = selections.unionByName(ids(features.filter(F.col(name)).orderBy("job_id").limit(10), name))
    selections = selections.unionByName(ids(features.orderBy(F.desc("description_chars"), "job_id").limit(10), "longest_description"))
    # Small, hash-attributed key metadata only, no private text or manual labels.
    review = json.loads((root / "data/audit/d06/pilot_review_keys.json").read_text(encoding="utf8"))
    if (review["reference_sha256"] != "1c4c8b8d3ab00238e908e834ca615ba4188b6d03858cb5e38648f1565d03266d"
            or len(review["job_ids"]) != 33 or len(set(review["job_ids"])) != 33):
        raise PilotIntegrityError("Invalid known-REVIEW key metadata")
    selections = selections.unionByName(ids(features.filter(F.col("job_id").isin(review["job_ids"])), "known_phase1_review"))
    category_ids = (features.select("job_id", F.explode("job_functions").alias("function"))
        .filter(F.col("function.skill_abr").isNotNull())
        .groupBy(F.col("function.skill_abr").alias("function_code"))
        .agg(F.min("job_id").alias("job_id")).orderBy("function_code").limit(20))
    selections = selections.unionByName(category_ids.select("job_id",
        F.concat(F.lit("function_"), F.col("function_code")).alias("selection_reason")))
    selected_ids = selections.groupBy("job_id").agg(F.sort_array(F.collect_set("selection_reason")).alias("selection_reasons"))
    sample = canonical.select("job_id", "source_title", "source_description",
        "source_title_sha256", "source_description_sha256").join(selected_ids, "job_id", "inner").cache()
    stats = validate_input(sample)
    reasons = {r.selection_reason: r["count"] for r in sample.select(
        F.explode("selection_reasons").alias("selection_reason")).groupBy("selection_reason").count().collect()}
    coverage = features.agg(*[F.sum(F.col(n).cast("long")).alias(n) for n in (
        "empty_title", "empty_description", "html_entities", "unicode")]).first().asDict()
    features.unpersist()
    return sample, {"canonical": canonical_stats, "input": stats, "base_size": sample_size,
        "policy": "xxhash64(job_id,42) ascending + job_id tie-break; capped edges; dedup job_id; no accuracy claim",
        "selection_reason_counts_overlap": reasons, "canonical_edge_availability": coverage}


def jvm_observation(spark):
    factory = spark.sparkContext._jvm.java.lang.management.ManagementFactory
    usage = factory.getMemoryMXBean().getHeapMemoryUsage()
    collectors = factory.getGarbageCollectorMXBeans()
    return {"heap_used_bytes": usage.getUsed(), "heap_committed_bytes": usage.getCommitted(),
            "heap_max_bytes": usage.getMax(), "gc": {str(collectors.get(i).getName()): {
                "count": collectors.get(i).getCollectionCount(), "time_ms": collectors.get(i).getCollectionTime()
            } for i in range(collectors.size())}}


def output_validation(source, output, schema, package_broadcast, checksum):
    from pyspark.sql import functions as F
    if output.schema.toNullable() != schema.toNullable():
        raise PilotDataError("Parquet schema mismatch")
    stats = output.agg(F.count("*").alias("rows"), F.countDistinct("job_id").alias("unique"),
        F.sum(F.col("job_id").isNull().cast("long")).alias("nulls")).first().asDict()
    n = source.count()
    if stats != {"rows": n, "unique": n, "nulls": 0}:
        raise PilotDataError("Output grain mismatch")
    missing = source.select("job_id").join(output.select("job_id"), "job_id", "left_anti").count()
    extra = output.select("job_id").join(source.select("job_id"), "job_id", "left_anti").count()
    bad = output.filter(
        ~F.col("_d06_present").eqNullSafe(True) |
        ~F.col("taxonomy_version").eqNullSafe("0.2.2") |
        ~F.col("taxonomy_sha256").eqNullSafe(CONFIG_HASH) |
        ~((F.col("it_decision").eqNullSafe("ACCEPT") & F.col("is_it").eqNullSafe(True)) |
          (F.col("it_decision").eqNullSafe("REJECT") & F.col("is_it").eqNullSafe(False)) |
          (F.col("it_decision").eqNullSafe("REVIEW") & F.col("is_it").isNull())))
    if missing or extra or bad.limit(1).count():
        raise PilotDataError("Missing classification / decision-null / version-hash mismatch")
    joined = source.select("job_id", F.col("source_title").alias("expected_title"),
        F.col("source_description").alias("expected_description"),
        F.col("source_title_sha256").alias("expected_title_hash"),
        F.col("source_description_sha256").alias("expected_description_hash")).join(output, "job_id")
    if joined.filter(~F.col("expected_title").eqNullSafe(F.col("title")) |
        ~F.col("expected_description").eqNullSafe(F.col("description")) |
        ~F.col("expected_title_hash").eqNullSafe(F.col("source_title_sha256")) |
        ~F.col("expected_description_hash").eqNullSafe(F.col("source_description_sha256"))).limit(1).count():
        raise PilotDataError("Output source text/hash mismatch")
    checked = output.rdd.mapPartitions(worker_runner(package_broadcast, checksum, "verify")).sum()
    if checked != n:
        raise PilotDataError("Nested/Unicode distributed roundtrip check incomplete")
    return {**stats, "missing": missing, "extra": extra, "errors": 0,
        "nested_roundtrip_checked": checked, "all_present": True,
        "decision_counts": {r.it_decision: r["count"] for r in output.groupBy("it_decision").count().collect()}}


def run_pilot(sample_size=1000, partitions=4, output=None, taxonomy_config=CONFIG_REF, mode="pilot", root=ROOT):
    if output is None:
        raise PilotDataError("Explicit new --output is required")
    output = validate_options(mode, sample_size, partitions, output, root)
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root).decode().strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    if branch not in ("feat/tv1-d06-pilot", "feat/tv1-d06-official-runner"):
        raise PilotDataError("Run only on the Pilot branch")
    verify_d05_base(root, branch, head)
    # Integrity validation occurs BEFORE any classifier/Spark execution.
    package, checksum, manifest = build_package(root, taxonomy_config)
    verified_members(package, checksum)
    output.mkdir(parents=True, exist_ok=False)
    before = protected_snapshot(root)
    write_json(output / "protected_before.json", before)
    summary = {"status": "BLOCKED", "mode": "pilot", "full_dataset_executed": False,
        "branch": branch, "head": head, "started_utc": datetime.now(timezone.utc).isoformat(),
        "output": str(output), "package": {"path": str(package), "sha256": checksum, "manifest": manifest},
        "taxonomy_config_argument": taxonomy_config, "a04_acceptance": "PENDING GROUP REVIEW"}
    spark = None
    started = time.perf_counter()
    try:
        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
        os.environ.setdefault("PYSPARK_SUBMIT_ARGS", "--driver-memory 3g pyspark-shell")
        from d05_utils import get_spark_session
        from pyspark.sql import functions as F
        spark = get_spark_session("D06-ControlledPilot", root)
        spark.conf.set("spark.sql.shuffle.partitions", str(partitions))
        spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")
        spark.conf.set("spark.sql.adaptive.autoBroadcastJoinThreshold", "-1")
        java = spark.sparkContext._jvm.java.lang.System.getProperty("java.version")
        summary["environment"] = {"python": sys.version, "spark": spark.version, "java": java,
                                  "master": spark.sparkContext.master, "java_home": os.environ.get("JAVA_HOME")}
        if sys.version_info[:2] != (3, 11) or spark.version != "4.2.0" or not java.startswith("21."):
            raise PilotIntegrityError("Require Python3.11/Spark4.2.0/Java21")
        package_broadcast = spark.sparkContext.broadcast(package.read_bytes())
        summary["package"]["transport"] = "Spark broadcast exact ZIP bytes; verified per worker"
        # Actual worker bootstrap is tested by the materialized write below.
        schema_json = json.loads((root / "data/audit/d06/spark_schema.json").read_text())
        schema = pilot_schema(schema_json)
        write_json(output / "schema.json", schema.jsonValue())
        selection_start = time.perf_counter()
        source, summary["selection"] = select_sample(spark, sample_size, root)
        source.write.mode("errorifexists").parquet(str(output / "input_sample.parquet"))
        summary["selection_seconds"] = time.perf_counter() - selection_start
        n = summary["selection"]["input"]["rows"]
        print(f"Selected {n} real jobs; FULL locked; package {checksum[:12]}", flush=True)
        summary["jvm_before_classification"] = jvm_observation(spark)
        classification_start = time.perf_counter()
        classified = spark.createDataFrame(source.repartition(partitions).rdd.mapPartitions(
            worker_runner(package_broadcast, checksum)), schema, verifySchema=True)
        classified.write.mode("errorifexists").parquet(str(output / "predictions.parquet"))
        seconds = time.perf_counter() - classification_start
        summary["jvm_after_classification"] = jvm_observation(spark)
        readback = spark.read.parquet(str(output / "predictions.parquet"))
        summary["validation"] = output_validation(source, readback, schema, package_broadcast, checksum)
        summary["performance"] = {"classification_write_seconds": seconds, "jobs_per_second": n / seconds,
            "partitions_requested": partitions, "materialization": "actual predictions Parquet write completion"}
        metrics = readback.agg(F.countDistinct("_d06_worker_pid").alias("workers"),
            F.countDistinct("_d06_classifier_instance").alias("classifier_instances"),
            F.max("_d06_python_rss_bytes").alias("max_observed_worker_rss_bytes"),
            F.min("_d06_python_rss_bytes").alias("min_observed_worker_rss_bytes"),
            F.max("_d06_description_chars").alias("max_description_chars"),
            F.expr("percentile_approx(_d06_classify_ns, array(0.5,0.95,0.99))").alias("classify_ns_p50_p95_p99")
        ).first().asDict()
        summary["performance"].update(metrics)
        summary["long_description_observation"] = [r.asDict() for r in readback.withColumn(
            "length_bucket", F.when(F.col("_d06_description_chars") >= 10000, "ge_10000").otherwise("lt_10000"))
            .groupBy("length_bucket").agg(F.count("*").alias("jobs"),
                F.avg("_d06_classify_ns").alias("mean_classify_ns"), F.max("_d06_classify_ns").alias("max_classify_ns")).collect()]
        # Bounded determinism check, different partition count, no predictions collect.
        subset = source.orderBy("job_id").limit(32).cache()
        changed_partitions = 2 if partitions != 2 else 3
        alternate = spark.createDataFrame(subset.repartition(changed_partitions).rdd.mapPartitions(
            worker_runner(package_broadcast, checksum)), schema, verifySchema=True)
        alternate.write.mode("errorifexists").parquet(str(output / "determinism.parquet"))
        other = spark.read.parquet(str(output / "determinism.parquet"))
        output_validation(subset, other, schema, package_broadcast, checksum)
        compared = other.select("job_id", F.col("_d06_prediction_sha256").alias("other_hash")).join(
            readback.select("job_id", "_d06_prediction_sha256"), "job_id", "left")
        if compared.filter(~F.col("other_hash").eqNullSafe(F.col("_d06_prediction_sha256"))).count():
            raise PilotDataError("Partition-count determinism mismatch")
        summary["determinism"] = {"rows": subset.count(), "partitions": changed_partitions, "mismatches": 0}
        summary["output_parquet_bytes"] = sum(p.stat().st_size for p in (output / "predictions.parquet").glob("*.parquet"))
        summary["status"] = "PASS"
        subset.unpersist(); source.unpersist()
    except Exception as exc:
        summary["status"] = "FAIL"
        summary["error"] = {"kind": "DATA_OR_CONTRACT" if isinstance(exc, PilotDataError) or "PilotDataError" in str(exc) else
                            "INTEGRITY" if isinstance(exc, PilotIntegrityError) or "PilotIntegrityError" in str(exc) else "RUNTIME",
                            "type": type(exc).__name__, "message": str(exc)[:4000]}
        # Fail job/run; no synthetic REVIEW, no skip or overwrite/retry by runner.
        raise
    finally:
        if spark is not None:
            try:
                spark.stop()
            except Exception as exc:
                summary["spark_stop_warning"] = str(exc)
        after = protected_snapshot(root)
        changed = [k for k in before.keys() | after.keys() if before.get(k) != after.get(k)]
        summary["preservation"] = {"protected_files": len(before), "changed": sorted(changed)}
        if changed:
            summary["status"] = "FAIL"
        summary["elapsed_total_seconds"] = time.perf_counter() - started
        summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(output / "summary.json", summary)
        print("Pilot summary:", output / "summary.json", flush=True)
    if summary["status"] != "PASS":
        raise PilotDataError("Pilot preservation or validation failed")
    return summary


def main():
    selector = argparse.ArgumentParser(add_help=False)
    selector.add_argument("--mode", default="pilot", choices=["pilot", "preflight", "full"])
    selected, _ = selector.parse_known_args()
    if selected.mode != "pilot":
        from d06_official_runner import main as official_main
        return official_main()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", default="pilot", choices=["pilot"])
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--partitions", type=int, default=4)
    parser.add_argument("--output", required=True)
    parser.add_argument("--taxonomy-config", default=CONFIG_REF)
    args = parser.parse_args()
    run_pilot(**vars(args))


if __name__ == "__main__":
    main()
