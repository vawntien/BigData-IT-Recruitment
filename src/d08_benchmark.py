"""Real D05/D07 Spark-local benchmark, NOT D06/full-pipeline or distributed-cluster results."""
from __future__ import annotations
import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re
import statistics
import subprocess
import sys
import time
from xml.sax.saxutils import escape

from normalize_salary import ROOT, inventory, file_sha, write_new, key_stats

BASE = "479d3d83ff3194a5556ce29884c92478c90a969c"
WORKLOADS = ("W1", "W2", "W3", "W4", "W5")
MASTERS = ("local[1]", "local[2]", "local[4]")
POLICY = "SPARK_UNCACHED_OS_CACHE_UNCONTROLLED_POST_WARMUP"
ROWS = 123849


def utc():
    return datetime.now(timezone.utc).isoformat()


def check_options(args):
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.run_id)
            or args.repeats < 3 or args.repeats > 10 or args.partitions not in (2, 4, 8)
            or args.master not in MASTERS):
        raise ValueError("Invalid run ID/configuration; require >=3 measured repeats")


def hardware():
    script = "$c=Get-CimInstance Win32_Processor;$s=Get-CimInstance Win32_ComputerSystem;$o=Get-CimInstance Win32_OperatingSystem;[pscustomobject]@{cpu=$c.Name;physical_cores=$c.NumberOfCores;logical_processors=$c.NumberOfLogicalProcessors;ram_total_bytes=[long]$s.TotalPhysicalMemory;ram_free_snapshot_bytes=[long]$o.FreePhysicalMemory*1024;os=$o.Caption;os_version=$o.Version}|ConvertTo-Json -Compress"
    return json.loads(subprocess.check_output(["powershell", "-NoProfile", "-Command", script], encoding="utf8"))


def protected_snapshot():
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE], cwd=ROOT).decode().splitlines()
    paths = {ROOT / n for n in names}
    for directory in ("data/raw", "data/processed"):
        paths.update(p for p in (ROOT / directory).rglob("*") if p.is_file())
    return {p.relative_to(ROOT).as_posix(): [p.stat().st_size, p.stat().st_mtime_ns, file_sha(p)]
            for p in sorted(paths) if p.is_file()}


def create_session(args, events=None):
    from pyspark.sql import SparkSession
    check_options(args)
    jar = Path(args.windows_fs_jar).resolve()
    if not jar.is_file():
        raise ValueError("Explicit filesystem JAR required for this Windows benchmark")
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    # 1GiB heap: machine has16GiB total but little currently free. No parallel sessions.
    os.environ["PYSPARK_SUBMIT_ARGS"] = "--driver-memory 1g pyspark-shell"
    settings = {
        "spark.driver.extraClassPath": str(jar), "spark.executor.extraClassPath": str(jar),
        "spark.hadoop.fs.file.impl": "d04.localfs.NoPermissionLocalFileSystem",
        "spark.hadoop.fs.file.impl.disable.cache": "true", "spark.sql.session.timeZone": "UTC",
        "spark.sql.shuffle.partitions": str(args.partitions), "spark.default.parallelism": "4",
        "spark.sql.files.maxPartitionBytes": str(128 * 1024 * 1024), "spark.sql.files.minPartitionNum": "4",
        "spark.sql.adaptive.enabled": "false", "spark.sql.autoBroadcastJoinThreshold": "-1",
        "spark.sql.exchange.reuse": "false", "spark.sql.execution.reuseSubquery": "false",
        "spark.sql.parquet.aggregatePushdown": "false", "spark.speculation": "false",
        "spark.sql.ansi.enabled": "true", "spark.ui.enabled": "false",
    }
    if events:
        events.mkdir(parents=True, exist_ok=False)
        settings.update({"spark.eventLog.enabled": "true", "spark.eventLog.dir": events.as_uri(),
            "spark.eventLog.compress": "false", "spark.eventLog.rolling.enabled": "false"})
    b = SparkSession.builder.master(args.master).appName("D08-" + args.master)
    for k, v in settings.items():
        b = b.config(k, v)
    start = time.perf_counter()
    spark = b.getOrCreate()
    startup = time.perf_counter() - start
    spark.sparkContext.setLogLevel("ERROR")
    java = spark.sparkContext._jvm.java.lang.System.getProperty("java.version")
    if sys.version_info[:2] != (3, 11) or spark.version != "4.2.0" or not java.startswith("21."):
        spark.stop()
        raise ValueError("Require Python3.11/PySpark4.2.0/Java21")
    config = {k: spark.sparkContext.getConf().get(k) for k in settings}
    config.update(master=spark.sparkContext.master, python=sys.version, spark=spark.version, java=java,
        startup_seconds=startup, java_max_heap_bytes=spark.sparkContext._jvm.java.lang.Runtime.getRuntime().maxMemory(),
        cache_policy=POLICY, timing_boundary="Query construction through collect of distributed scalar summary; validation/digest comparison and metric parsing excluded")
    return spark, config


def group_summary(grouped, dimensions):
    from pyspark.sql import functions as F
    return grouped.agg(F.count("*").alias("output_groups"), F.sum("job_count").alias("membership_count"),
        F.min("job_count").alias("smallest_group"), F.max("job_count").alias("largest_group"),
        F.sum(F.xxhash64(*dimensions, "job_count").cast("decimal(38,0)")).alias("group_digest_sum"))


def build_query(name, jobs, salary):
    """Materialize scalar summaries of REAL aggregations, not lazy schema-only/count-of-groups shortcuts."""
    from pyspark.sql import functions as F
    if name == "W1":
        return jobs.agg(F.count("*").alias("rows"), F.countDistinct("job_id").alias("unique"),
            F.sum(F.col("job_id").isNull().cast("long")).alias("nulls"))
    if name == "W2":
        dims = ["formatted_experience_level", "work_type", "location"]
        # Native Spark NULL group, no sentinel collision and no implicit onsite/Unknown imputation.
        grouped = jobs.groupBy(*dims).agg(F.countDistinct("job_id").alias("job_count"))
        return group_summary(grouped, dims)
    if name == "W3":
        member = jobs.select("job_id", F.explode("job_industries").alias("i"))
        grouped = member.groupBy(F.col("i.industry_id").alias("industry_id"),
            F.col("i.industry_name").alias("industry_name")).agg(F.countDistinct("job_id").alias("job_count"))
        return group_summary(grouped, ["industry_id", "industry_name"])
    if name == "W4":
        dims = ["normalization_status", "canonical_currency"]
        grouped = salary.groupBy(*dims).agg(F.countDistinct("job_id").alias("job_count"))
        return group_summary(grouped, dims)
    if name == "W5":
        joined = jobs.select("job_id").join(salary.select("job_id", "normalization_status"), "job_id", "inner")
        return joined.agg(F.count("*").alias("rows"), F.countDistinct("job_id").alias("unique"),
            *[F.sum((F.col("normalization_status") == s).cast("long")).alias(s.lower())
              for s in ("USABLE", "MISSING", "INVALID", "AMBIGUOUS", "EXCLUDED")])
    raise ValueError("Unknown workload")


def plain_result(row):
    # Decimal digest stored as string, never a float.
    return json.loads(json.dumps(row.asDict(), default=str, sort_keys=True))


def check_result(name, result, expected, reference=None):
    if name == "W1":
        assert result == {"rows": expected["rows"], "unique": expected["rows"], "nulls": 0}
    elif name in ("W2", "W4"):
        assert result["membership_count"] == expected["rows"]
    elif name == "W3":
        assert result["membership_count"] == expected["industry_memberships"]
        assert result["output_groups"] == expected["industry_groups"]
    elif name == "W5":
        assert result["rows"] == result["unique"] == expected["rows"]
        assert {s: result[s.lower()] for s in expected["statuses"]} == expected["statuses"]
    else:
        raise ValueError("Unknown workload")
    if reference is not None:
        assert result == reference, f"Repeated/config result mismatch: {name}"


def preflight(jobs, salary, expected_rows=ROWS):
    from pyspark.sql import functions as F
    key_stats(jobs, expected_rows)
    key_stats(salary, expected_rows)
    assert jobs.select("job_id").join(salary.select("job_id"), "job_id", "left_anti").count() == 0
    assert salary.select("job_id").join(jobs.select("job_id"), "job_id", "left_anti").count() == 0
    statuses = {r.normalization_status: r['count'] for r in salary.groupBy("normalization_status").count().collect()}
    if expected_rows == ROWS:
        assert statuses == {"USABLE": 36059, "MISSING": 87776, "INVALID": 14}
    for s in ("USABLE", "MISSING", "INVALID", "AMBIGUOUS", "EXCLUDED"):
        statuses.setdefault(s, 0)
    member = jobs.select("job_id", F.explode("job_industries").alias("i"))
    n = member.count()
    assert member.select("job_id", "i.industry_id").distinct().count() == n, "Duplicate job/industry membership"
    groups = member.select("i.industry_id", "i.industry_name").distinct().count()
    return {"rows": expected_rows, "statuses": statuses, "industry_memberships": n,
            "industry_groups": groups, "key_sets_equal": True, "null_keys": 0, "duplicate_keys": 0}


def event_metrics(events):
    stage_groups = defaultdict(set)
    tasks = []
    files = []
    for path in sorted(events.rglob("*")):
        if not path.is_file() or path.name.startswith(".") or not path.name.startswith(("events", "app-", "local-")):
            continue
        files.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": file_sha(path)})
        with path.open(encoding="utf8") as f:
            for line in f:
                e = json.loads(line)
                if e.get("Event") == "SparkListenerJobStart":
                    group = (e.get("Properties") or {}).get("spark.jobGroup.id")
                    if group:
                        for stage in e.get("Stage IDs", []):
                            stage_groups[stage].add(group)
                elif e.get("Event") == "SparkListenerTaskEnd":
                    tasks.append(e)
    values = defaultdict(lambda: {"task_attempts": 0, "stage_ids": set(), "metrics": defaultdict(list)})
    for e in tasks:
        owners = stage_groups[e["Stage ID"]]
        if len(owners) != 1:
            if owners:
                raise ValueError("Stage shared across benchmark groups: metrics ambiguous")
            continue
        group = next(iter(owners))
        d = values[group]; d["task_attempts"] += 1; d["stage_ids"].add(e["Stage ID"])
        m = e.get("Task Metrics") or {}
        for key, label in [("Executor Run Time", "executor_run_ms"), ("Executor CPU Time", "executor_cpu_ns"),
            ("JVM GC Time", "jvm_gc_ms"), ("Memory Bytes Spilled", "memory_spilled_bytes"),
            ("Disk Bytes Spilled", "disk_spilled_bytes"), ("Peak Execution Memory", "peak_execution_memory_bytes")]:
            if key in m: d["metrics"][label].append(m[key])
        read, write = m.get("Shuffle Read Metrics", {}), m.get("Shuffle Write Metrics", {})
        if "Remote Bytes Read" in read and "Local Bytes Read" in read:
            d["metrics"]["shuffle_read_bytes"].append(read["Remote Bytes Read"] + read["Local Bytes Read"])
        if "Shuffle Bytes Written" in write:
            d["metrics"]["shuffle_write_bytes"].append(write["Shuffle Bytes Written"])
    out = {}
    for group, d in values.items():
        out[group] = {"task_attempts": d["task_attempts"], "stages": len(d["stage_ids"]),
            **{k: (max(v) if k == "peak_execution_memory_bytes" else sum(v)) for k, v in d["metrics"].items()}}
    return out, files


def write_csv(path, rows):
    if not rows: raise ValueError("No rows to publish")
    columns = sorted({key for row in rows for key in row})
    with Path(path).open("x", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def worker(args):
    folder = Path(args.worker_dir)
    if not folder.resolve().is_relative_to((ROOT / "tmp/d08_benchmark").resolve()):
        raise ValueError("Worker evidence must be under dedicated tmp/d08_benchmark")
    folder.mkdir(parents=True, exist_ok=False)
    spark, config = create_session(args, folder / "events")
    records, refs, plans = [], {}, {}
    try:
        jobs = spark.read.parquet(str(ROOT / "data/processed/canonical/jobs"))
        salary = spark.read.parquet(str(ROOT / "data/processed/d07/staging/d07_20261019_01/salaries.parquet"))
        assert len(jobs.columns) == 50 and len(salary.columns) == 28
        expected = preflight(jobs, salary)
        config["input_partitions"] = {"D05": jobs.rdd.getNumPartitions(), "D07": salary.rdd.getNumPartitions()}
        sequence = [("warmup", 0, name) for name in WORKLOADS]
        for repeat in range(1, args.repeats + 1):
            order = list(WORKLOADS); random.Random(args.seed + repeat).shuffle(order)
            sequence += [("measured", repeat, name) for name in order]
        for phase, repeat, name in sequence:
            spark.catalog.clearCache()
            assert spark.sparkContext._jsc.sc().getPersistentRDDs().size() == 0
            group = f"{name}_{phase}_{repeat}"
            spark.sparkContext.setJobGroup(group, group)
            at = utc(); start = time.perf_counter()
            query = build_query(name, jobs, salary)
            rows = query.collect()
            elapsed = time.perf_counter() - start
            assert len(rows) == 1
            result = plain_result(rows[0])
            check_result(name, result, expected, refs.get(name))
            refs.setdefault(name, result)
            if name not in plans:
                plans[name] = query._jdf.queryExecution().executedPlan().toString()
            records.append({"workload": name, "phase": phase, "repeat": repeat, "elapsed_seconds": elapsed,
                "timestamp_utc": at, "master": args.master, "shuffle_partitions": args.partitions,
                "input_rows": ROWS, "secondary_input_rows": ROWS if name == "W5" else 0,
                "expanded_memberships": expected["industry_memberships"] if name == "W3" else 0,
                "output_groups": result.get("output_groups", 1), "result_json": json.dumps(result, sort_keys=True),
                "correctness": "PASS", "cache_policy": POLICY, "job_group": group})
            print("OBSERVATION", args.master, group, round(elapsed, 6), "PASS", flush=True)
        write_new(folder / "query_plans.json", plans)
    finally:
        spark.stop()
    metrics, event_files = event_metrics(folder / "events")
    for row in records:
        observed = metrics.get(row["job_group"])
        if not observed: raise ValueError("No task metric evidence for " + row["job_group"])
        row.update(observed)
    write_new(folder / "result.json", {"records": records, "config": config, "expected": expected,
        "references": refs, "event_files": event_files, "metrics_source": "SparkListenerTaskEnd; task attempts, not system CPU/RAM"})


def summarize(records):
    grouped = defaultdict(list)
    for r in records:
        if r["phase"] == "measured": grouped[(r["master"], r["workload"])].append(r["elapsed_seconds"])
    result = [{"master": m, "workload": w, "samples": len(v), "min_seconds": min(v),
        "median_seconds": statistics.median(v), "max_seconds": max(v)} for (m, w), v in sorted(grouped.items())]
    baseline = {r["workload"]: r["median_seconds"] for r in result if r["master"] == "local[1]"}
    for r in result:
        r["speedup_vs_local1"] = baseline[r["workload"]] / r["median_seconds"]
    return result


def chart(path, summary, field, title):
    # Dependency-free native SVG, exact data values also retained in CSV.
    width, height, left, top = 1100, 480, 80, 65
    maximum = max(r[field] for r in summary) * 1.2
    bars = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="30" y="28" font-size="21" font-family="sans-serif">{escape(title)}</text>',
        '<text x="30" y="48" font-size="12" font-family="sans-serif">D05/D07 real data; median of3; Spark uncached; OS cache uncontrolled; single-machine local mode</text>']
    for tick in range(6):
        value = maximum * tick / 5; y = 385 - value / maximum * 300
        bars += [f'<line x1="{left}" y1="{y}" x2="1070" y2="{y}" stroke="#ddd"/>',
            f'<text x="8" y="{y+4}" font-size="12" font-family="sans-serif">{value:.2f}</text>']
    colors = ["#2563eb", "#ea580c", "#0d9488"]
    for i, workload in enumerate(WORKLOADS):
        for j, master in enumerate(MASTERS):
            r = next(r for r in summary if r["workload"] == workload and r["master"] == master)
            x = left + i * 195 + j * 48 + 8; h = r[field] / maximum * 300
            bars += [f'<rect x="{x}" y="{385-h}" width="40" height="{h}" fill="{colors[j]}"/>',
                f'<text x="{x}" y="{378-h}" font-size="11" font-family="sans-serif">{r[field]:.3f}</text>']
        bars.append(f'<text x="{left+i*195+55}" y="410" font-size="15" font-family="sans-serif">{workload}</text>')
    for j, master in enumerate(MASTERS):
        bars += [f'<rect x="{220+j*230}" y="440" width="20" height="15" fill="{colors[j]}"/>',
            f'<text x="{248+j*230}" y="453" font-size="14" font-family="sans-serif">{master}</text>']
    bars.append('</svg>')
    with Path(path).open("x", encoding="utf8") as f: f.write("\n".join(bars))


def run(args):
    check_options(args)
    assert subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT).decode().strip() == "feat/tv1-d08-benchmark"
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    assert subprocess.run(["git", "merge-base", "--is-ancestor", BASE, head], cwd=ROOT).returncode == 0
    protected_names = set(subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE], cwd=ROOT).decode().splitlines())
    changed = set(subprocess.check_output(["git", "diff", "--name-only", BASE], cwd=ROOT).decode().splitlines())
    changed.update(subprocess.check_output(["git", "diff", "--cached", "--name-only", BASE], cwd=ROOT).decode().splitlines())
    assert not protected_names.intersection(changed), "D01-D07 tracked files changed"
    audit = ROOT / "data/audit/d08" / args.run_id
    temp = ROOT / "tmp/d08_benchmark" / args.run_id
    if audit.exists() or temp.exists(): raise FileExistsError("New run ID required; no audit overwrite")
    inputs = {"D05": inventory(ROOT / "data/processed/canonical/jobs"),
        "D07": inventory(ROOT / "data/processed/d07/staging/d07_20261019_01/salaries.parquet")}
    seal = json.loads((ROOT / "data/processed/d07/staging/d07_20261019_01/completion.json").read_text(encoding="utf8"))
    assert inputs["D07"]["fingerprint"] == seal["output_fingerprint"]
    assert not (ROOT / "data/processed/d06").exists()
    machine = hardware()
    before = protected_snapshot()
    audit.mkdir(parents=True, exist_ok=False); temp.mkdir(parents=True, exist_ok=False)
    write_new(temp / "protected_before.json", before)
    configs, records, first = [], [], None
    order = list(MASTERS); random.Random(args.seed).shuffle(order)
    try:
        for master in order:
            directory = temp / master.replace("[", "_").replace("]", "")
            command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--worker-dir", str(directory),
                "--run-id", args.run_id, "--master", master, "--partitions", str(args.partitions),
                "--repeats", str(args.repeats), "--seed", str(args.seed), "--windows-fs-jar", args.windows_fs_jar]
            subprocess.run(command, cwd=ROOT, check=True)
            result = json.loads((directory / "result.json").read_text(encoding="utf8"))
            if first is None: first = result["references"]
            assert first == result["references"], "Cross-config scalar/group digest mismatch"
            configs.append(result); records += result["records"]
        assert len(records) == 3 * 5 * (args.repeats + 1)
        after = protected_snapshot()
        assert before == after, "Protected input/code changed"
        summary = summarize(records)
        write_csv(audit / "benchmark_results.csv", records)
        write_csv(audit / "benchmark_summary.csv", summary)
        manifest = {"run_id": args.run_id, "scope": "OFFICIAL_D05_D07_AVAILABLE_WORKLOADS_ONLY",
            "full_pipeline": "PENDING_D06_FULL", "d06_full": "NOT_EXECUTED", "head": head, "base_commit": BASE,
            "source_sha256": file_sha(__file__), "hardware": machine, "inputs": inputs,
            "seed": args.seed, "execution_order": order, "measured_repeats": args.repeats,
            "warmups_per_workload_config": 1, "cache_policy": POLICY, "at_utc": utc(),
            "configs": configs, "protected_files": len(before), "protected_before_evidence": str(temp.relative_to(ROOT) / "protected_before.json"),
            "scaffold_review": "support/tv1-d08-benchmark-scaffold smoke is DEV_SMOKE_ONLY; metadata-only and single measurements not reused as official evidence",
            "limitations": ["Local single machine, not multi-node cluster", "OS cache/JIT/background load uncontrolled; no cold-cache claim",
                "One fresh process/config block,3 timing repeats; no cross-day replicate or statistical CI",
                "Task CPU/GC/shuffle/spill metrics are Spark event observations, not system utilization/RAM peaks",
                "W1 column-pruned scan, not full50-column decode or end-to-end ETL", "No cache-on/off or partition sweep/CSV-vs-Parquet study",
                "No D06 classifier, full pipeline, official IT population, salary median or analytics publication"]}
        write_new(audit / "benchmark_manifest.json", manifest)
        write_new(audit / "benchmark_validation.json", {"status": "PASS", "measured_observations": 3 * 5 * args.repeats,
            "warmup_observations": 15, "every_observation_correct": True, "cross_config_results_exact": True,
            "preflight_per_config": [c["expected"] for c in configs], "protected_inputs_and_baseline_code_unchanged": True,
            "task_metric_groups": len(records), "timings_materialized": True, "d06_full_executed": False})
        chart(audit / "runtime_median.svg", summary, "median_seconds", "D08: median wall-clock seconds (lower is better)")
        chart(audit / "speedup.svg", summary, "speedup_vs_local1", "D08: observed speedup vs local[1] (higher is better)")
        print("D08_BENCHMARK_PASS", str(audit), json.dumps(summary), flush=True)
    except BaseException as e:
        write_new(audit / "failure.json", {"status": "FAIL", "type": type(e).__name__, "at_utc": utc()})
        raise


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--master", default="local[1]")
    p.add_argument("--partitions", type=int, default=4)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--windows-fs-jar", required=True)
    p.add_argument("--worker", action="store_true")
    p.add_argument("--worker-dir")
    return p


if __name__ == "__main__":
    options = parser().parse_args()
    worker(options) if options.worker else run(options)
