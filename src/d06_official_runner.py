"""Real D06 engine + nonclassifying preflight + externally guarded full entrypoint.

Full cannot run without external human A04/schema/run approval files AND explicit
operator acknowledgement. No approval generation or --force/skip-validation path.
"""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from d06_official_contract import (
    ROWS, SCHEMA_VERSION, SCHEMA_SHA, _FullGrant, require_approvals,
    official_schema, checked_package, safe_destination, sha, json_bytes, ApprovalRequired,
)
from d06_official_state import RunJournal, exclusive_json, parquet_fingerprint, inspect_run, utcnow
from d06_pilot_packaging import worker_runner
from d06_taxonomy_adapter import CONFIG_HASH, TV2_COMMIT
from d06_classification_runner import output_validation, jvm_observation
from d06_parity_validation import ROOT, verify_d05_base


def input_checks(df, expected_rows):
    """Generic distributed contract checks, also used by the <=32-row test engine."""
    from pyspark.sql import functions as F
    required = {"job_id": "bigint", "source_title": "string", "source_description": "string",
                "source_title_sha256": "string", "source_description_sha256": "string"}
    actual = {f.name: f.dataType.simpleString() for f in df.schema}
    if any(actual.get(k) != typ for k, typ in required.items()):
        raise ValueError("Invalid canonical schema: use bigint job_id and ORIGINAL source columns")
    result = df.agg(F.count("*").alias("rows"), F.countDistinct("job_id").alias("unique"),
        F.sum(F.col("job_id").isNull().cast("long")).alias("nulls")).first().asDict()
    if result != {"rows": expected_rows, "unique": expected_rows, "nulls": 0}:
        raise ValueError("Input grain/count/null/duplicate violation")
    bad = F.lit(False)
    for field in ("title", "description"):
        text, checksum = F.col("source_" + field), F.col("source_" + field + "_sha256")
        bad = bad | text.isNull() | checksum.isNull() | ~checksum.rlike("^[0-9a-f]{64}$") | ~F.sha2(text, 256).eqNullSafe(checksum)
    if df.filter(bad).limit(1).count():
        raise ValueError("Missing source/raw hash mismatch")
    return result


def create_session(args):
    from pyspark.sql import SparkSession
    if not 1 <= args.partitions <= 256:
        raise ValueError("partitions must be 1..256")
    if not args.master.startswith("local[") and not args.worker_python:
        raise ValueError("Remote deployment requires explicit --worker-python environment")
    os.environ["PYSPARK_PYTHON"] = args.worker_python or sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    os.environ.setdefault("PYSPARK_SUBMIT_ARGS", "--driver-memory 3g pyspark-shell")
    builder = SparkSession.builder.appName("D06-Official-" + args.mode).master(args.master)
    settings = {"spark.sql.session.timeZone": "UTC", "spark.sql.shuffle.partitions": str(args.partitions),
        "spark.sql.autoBroadcastJoinThreshold": "-1", "spark.sql.adaptive.autoBroadcastJoinThreshold": "-1",
        "spark.python.worker.reuse": "true", "spark.speculation": "false", "spark.task.maxFailures": "4"}
    if os.name == "nt" and args.master.startswith("local["):
        if not args.windows_fs_jar or not Path(args.windows_fs_jar).is_file():
            raise ValueError("Windows local runtime requires explicit --windows-fs-jar artifact")
        settings.update({"spark.driver.extraClassPath": str(Path(args.windows_fs_jar).resolve()),
            "spark.executor.extraClassPath": str(Path(args.windows_fs_jar).resolve()),
            "spark.hadoop.fs.file.impl": "d04.localfs.NoPermissionLocalFileSystem",
            "spark.hadoop.fs.file.impl.disable.cache": "true"})
    for k, v in settings.items():
        builder = builder.config(k, v)
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    java = spark.sparkContext._jvm.java.lang.System.getProperty("java.version")
    if sys.version_info[:2] != (3, 11) or spark.version != "4.2.0" or not java.startswith("21."):
        spark.stop()
        raise ValueError("Require Python3.11/PySpark4.2.0/Java21")
    return spark


def preflight(spark, args, root=ROOT):
    from pyspark.sql import functions as F
    destination = safe_destination(root, args.run_id, args.output)
    checked_package(args.package, args.package_sha256)
    schema = official_schema(root)
    input_dir = Path(args.input).resolve()
    if input_dir != (Path(root) / "data/processed/canonical/jobs").resolve():
        raise ValueError("Official input must be the D05 canonical jobs snapshot")
    inventory = parquet_fingerprint(input_dir)
    df = spark.read.parquet(str(input_dir))
    if len(df.columns) != 50 or "canonical_schema_version" not in df.columns:
        raise ValueError("D05 baseline requires canonical50 columns/schema version")
    if df.filter(~F.col("canonical_schema_version").eqNullSafe("d05-v1")).limit(1).count():
        raise ValueError("Unsupported canonical schema version")
    stats = input_checks(df, ROWS)
    if parquet_fingerprint(input_dir)["fingerprint"] != inventory["fingerprint"]:
        raise ValueError("Input changed during preflight")
    bc = spark.sparkContext.broadcast(Path(args.package).read_bytes())
    count = min(args.partitions, 4)
    probes = spark.sparkContext.parallelize([], count).mapPartitions(worker_runner(bc, args.package_sha256, "probe")).collect()
    if len(probes) != count or any(p["version"] != "0.2.2" or p["config_sha256"] != CONFIG_HASH
        or p["classified_jobs"] != 0 for p in probes):
        raise ValueError("Worker package/config probe failed")
    return df, {"status": "PASS", "classified_jobs": 0, "input": stats,
        "input_columns": len(df.columns), "input_inventory": inventory,
        "schema_version": SCHEMA_VERSION, "schema_sha256": SCHEMA_SHA,
        "taxonomy_version": "0.2.2", "taxonomy_sha256": CONFIG_HASH,
        "package_sha256": args.package_sha256, "destination": str(destination),
        "destination_created": False, "worker_probes": probes,
        "a04_acceptance": "PENDING_UNLESS_EXTERNALLY_APPROVED", "full_execution_authorized": False,
        "spark_version": spark.version, "master": spark.sparkContext.master, "at_utc": utcnow()}


def execute_run(spark, source, *, root, run_id, output, package, checksum,
                expected_rows, input_inventory, partitions=4, grant=None, scope="TEST", input_recheck=None):
    """Shared REAL write/read/validate/publication engine; tests cannot invoke full scope.

    TEST namespace + <=32 hard cap is independent of the guarded FULL API. No
    fake A04 approvals are needed or accepted for tests. No production path used.
    """
    if scope not in ("TEST", "FULL"):
        raise ValueError("Unknown execution scope")
    destination = safe_destination(root, run_id, output, scope)
    if scope == "FULL":
        if not isinstance(grant, _FullGrant) or expected_rows != ROWS:
            raise ApprovalRequired("Full execution engine requires validated external grant")
        if (grant.run_id != run_id or grant.input_fingerprint != input_inventory["fingerprint"]
                or grant.package_sha256 != checksum or grant.output_relative != destination.relative_to(Path(root).resolve()).as_posix()):
            raise ApprovalRequired("Full grant does not bind this input/package/output/run")
        if input_recheck is None:
            raise ValueError("FULL requires post-execution immutable input recheck")
    elif grant is not None or not 1 <= expected_rows <= 32:
        raise ValueError("TEST is isolated, capped32; cannot use full approvals")
    checked_package(package, checksum)
    schema = official_schema(root)
    input_checks(source, expected_rows)
    bc = spark.sparkContext.broadcast(Path(package).read_bytes())
    manifest = {"scope": scope, "run_id": run_id, "expected_rows": expected_rows,
        "input_inventory": input_inventory, "taxonomy_version": "0.2.2", "taxonomy_sha256": CONFIG_HASH,
        "tv2_commit": TV2_COMMIT, "package_sha256": checksum, "schema_version": SCHEMA_VERSION,
        "schema_sha256": SCHEMA_SHA, "approvals": grant.documents if grant else {},
        "runtime": {"partitions": partitions, "master": spark.sparkContext.master,
            "python": sys.version, "spark": spark.version, "speculation": False,
            "task_max_failures": spark.sparkContext.getConf().get("spark.task.maxFailures", "engine default")}}
    journal = RunJournal(destination, manifest)
    start, stage = time.perf_counter(), "CLASSIFICATION_WRITE"
    try:
        before_jvm = jvm_observation(spark)
        df = spark.createDataFrame(source.repartition(partitions).rdd.mapPartitions(
            worker_runner(bc, checksum)), schema, verifySchema=True)
        df.write.mode("errorifexists").parquet(str(destination / "predictions"))
        write_seconds = time.perf_counter() - start
        journal.event("WRITTEN", seconds=write_seconds)
        stage = "DISTRIBUTED_VALIDATION"
        readback = spark.read.parquet(str(destination / "predictions"))
        validation = output_validation(source, readback, schema, bc, checksum)
        if sum(validation["decision_counts"].values()) != expected_rows:
            raise ValueError("Decision counts do not reconcile")
        validation.update(status="PASS", schema_version=SCHEMA_VERSION,
            classification_write_seconds=write_seconds, jobs_per_second=expected_rows / write_seconds,
            jvm_before=before_jvm, jvm_after=jvm_observation(spark))
        from pyspark.sql import functions as F
        validation["worker_metrics"] = readback.agg(
            F.countDistinct("_d06_worker_pid").alias("observed_workers"),
            F.countDistinct("_d06_classifier_instance").alias("classifier_instances"),
            F.max("_d06_python_rss_bytes").alias("max_observed_worker_working_set_bytes"),
            F.max("_d06_description_chars").alias("max_description_codepoints"),
            F.expr("percentile_approx(_d06_classify_ns, array(0.5,0.95,0.99))").alias("classify_ns_p50_p95_p99")
        ).first().asDict()
        stage = "INPUT_RECHECK"
        if input_recheck is not None and input_recheck() != input_inventory["fingerprint"]:
            raise ValueError("Canonical snapshot changed during execution")
        stage = "PUBLICATION"
        inventory = parquet_fingerprint(destination / "predictions")
        journal.complete(validation, inventory)
        result = inspect_run(destination)
        if result["status"] != "SUCCEEDED":
            raise ValueError("Publication verification failed")
        return result
    except BaseException as exc:
        journal.fail(exc, stage)
        raise


def run(args, root=ROOT):
    # Missing approval stops BEFORE Spark, input scan, run directory or classify.
    grant = require_approvals(args) if args.mode == "full" else None
    report_path = None
    if args.mode == "preflight" or args.report:
        if not args.report:
            raise ValueError("Preflight requires explicit NEW --report path")
        report_path = Path(args.report).resolve()
        if not report_path.is_relative_to((Path(root) / "tmp").resolve()):
            raise ValueError("Diagnostic report must be under project tmp")
        if report_path.exists():
            raise FileExistsError("Existing diagnostic report refused")
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root).decode().strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    if branch != "feat/tv1-d06-official-runner":
        raise ValueError("Use Official-runner branch")
    verify_d05_base(root, branch, head)
    safe_destination(root, args.run_id, args.output)
    spark = None
    try:
        checked_package(args.package, args.package_sha256)
        spark = create_session(args)
        source, report = preflight(spark, args, root)
        if args.mode == "preflight":
            exclusive_json(report_path, report)
            print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
            return report
        inventory = report["input_inventory"]
        # Approval input binding checked AFTER real canonical validation, BEFORE write/classify.
        return execute_run(spark, source.select("job_id", "source_title", "source_description",
            "source_title_sha256", "source_description_sha256"), root=root, run_id=args.run_id,
            output=args.output, package=args.package, checksum=args.package_sha256,
            expected_rows=ROWS, input_inventory=inventory, partitions=args.partitions,
            grant=grant, scope="FULL", input_recheck=lambda: parquet_fingerprint(args.input)["fingerprint"])
    except BaseException as exc:
        if report_path is not None and not report_path.exists():
            exclusive_json(report_path, {"status": "FAIL", "phase": "PREFLIGHT_OR_EXECUTION",
                "error_type": type(exc).__name__, "at_utc": utcnow()})
        raise
    finally:
        if spark is not None:
            spark.stop()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["preflight", "full"], required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--input", default=str(ROOT / "data/processed/canonical/jobs"))
    p.add_argument("--output")
    p.add_argument("--package")
    p.add_argument("--package-sha256")
    p.add_argument("--partitions", type=int, default=4)
    p.add_argument("--master", default="local[4]")
    p.add_argument("--worker-python")
    p.add_argument("--windows-fs-jar")
    p.add_argument("--report")
    p.add_argument("--execute-full", action="store_true")
    for name in ("a04-approval", "schema-approval", "run-authorization"):
        p.add_argument("--" + name)
        p.add_argument("--" + name + "-sha256")
    return p


def main(argv=None):
    return run(parser().parse_args(argv))


if __name__ == "__main__":
    main()
