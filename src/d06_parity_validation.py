"""D06 Phase 1 only: verified frozen 176 -> Python -> Spark -> temporary Parquet.

Run from project root with Python 3.11 and process-scoped Java 21. No commit,
merge, config promotion, production write, or full-dataset classification.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import uuid
import zipfile

from d06_taxonomy_adapter import (
    TV2_COMMIT, CODE_HASHES, CONFIG_HASH, bigint_string, classify, decode,
    derive_schema, differences, digest, encode, load_model, partition_runner,
)

ROOT = Path(__file__).resolve().parent.parent
D05_HEAD = "457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b"
REFERENCE_SUBDIR = "tv2_04/a04_taxonomy_v0_2_2_20261014"
REFERENCE_HASHES = {
    "run_manifest.json": "4d4aac5d52c1f98e656b0a2fb376712aabc580cbdb75bedf6d4c34df4ca3d3e8",
    "all_predictions.jsonl": "1c4c8b8d3ab00238e908e834ca615ba4188b6d03858cb5e38648f1565d03266d",
    "baseline/source_rows.json": "4fa5a35a5e06f1bb676833ba698cb6b2a96c5f2ff6a49b99f2e3214e216b0c14",
}


class ParityMismatch(ValueError):
    """Observed prediction/storage mismatch, distinct from a runtime blocker."""


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def checked_relative(name: str) -> PurePosixPath:
    """Reject Windows aliases, devices, streams, symlinks and traversal."""
    path = PurePosixPath(name)
    if (not name or "\\" in name or path.is_absolute()
            or any(p in ("", ".", "..") for p in name.rstrip("/").split("/"))
            or path.parts[0] != "tv2_04"):
        raise ValueError(f"Unsafe ZIP path: {name!r}")
    for part in path.parts:
        if (re.search(r'[<>:"|?*\x00-\x1f\x7f]', part) or part.endswith((" ", "."))
                or re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", part)):
            raise ValueError(f"Unsafe ZIP filename: {name!r}")
    return path


def exact_file(path: Path, data: bytes):
    """Idempotent byte-identical reuse, never overwrite any existing file."""
    if path.is_symlink():
        raise ValueError(f"Symlink destination: {path}")
    if path.exists():
        if not path.is_file() or path.read_bytes() != data:
            raise ValueError(f"Refusing overwrite: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)


def prepare(root: Path = ROOT):
    archive = root / "tmp/tv2(1).zip"
    destination = root / "tmp/tv2_a04_handoff_extract"
    hashes = []

    def check(label, data, expected):
        actual = digest(data)
        hashes.append(dict(path=label, expected=expected, actual=actual,
                           status="MATCH" if actual == expected else "MISMATCH"))
        if actual != expected:
            raise ValueError(f"Integrity mismatch: {label}")

    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if len([i for i in infos if not i.is_dir()]) != 44:
            raise ValueError("Unexpected handoff file count")
        seen = set()
        for info in infos:
            relative = checked_relative(info.filename)
            folded = str(relative).casefold()
            if folded in seen:
                raise ValueError("Duplicate/case-colliding ZIP path")
            seen.add(folded)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError("Non-regular ZIP entry")
            if info.flag_bits & 1 or info.file_size > 64 * 1024**2:
                raise ValueError("Encrypted/oversized ZIP entry")
            target = destination.joinpath(*relative.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError("Extraction escapes destination")
            for ancestor in [target, *target.parents]:
                reparse = (ancestor.exists() and getattr(ancestor.lstat(), "st_file_attributes", 0)
                           & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
                if ancestor.is_symlink() or reparse:
                    raise ValueError("Symlink/junction extraction destination")
            if target.exists() and not info.is_dir() and target.read_bytes() != z.read(info):
                raise ValueError(f"Refusing ZIP overwrite: {target}")
        if sum(i.file_size for i in infos) > 128 * 1024**2 or z.testzip() is not None:
            raise ValueError("ZIP size/CRC validation failed")
        base = REFERENCE_SUBDIR + "/"
        for name, expected in REFERENCE_HASHES.items():
            check(name, z.read(base + name), expected)
        manifest = json.loads(z.read(base + "run_manifest.json"))
        for name, expected in manifest["output_sha256"].items():
            checked_relative(base + name)
            check(name, z.read(base + name), expected)
        check("baseline/manifest.json", z.read(base + "baseline/manifest.json"),
              manifest["baseline_manifest_sha256"])
        if manifest["frozen_source_rows_sha256"] != REFERENCE_HASHES["baseline/source_rows.json"]:
            raise ValueError("Frozen source manifest disagrees with pinned digest")
        if (manifest["version"] != "0.2.2" or manifest["unique_jobs"] != 176
                or manifest["source_rows"] != 177 or manifest["candidate_config_sha256"] != CONFIG_HASH):
            raise ValueError("Manifest contract mismatch")
        # All validation above precedes extraction; ZIP content is never executed.
        for info in infos:
            target = destination.joinpath(*PurePosixPath(info.filename).parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                exact_file(target, z.read(info))

    snapshot = root / "tmp/d06_tv2_snapshot" / TV2_COMMIT
    for name, expected in CODE_HASHES.items():
        relative = "src/" + name
        if manifest["implementation_sha256"][relative] != expected:
            raise ValueError(f"Pinned code disagrees with manifest: {relative}")
        data = subprocess.check_output(["git", "show", f"{TV2_COMMIT}:{relative}"], cwd=root)
        check(relative, data, expected)
        exact_file(snapshot / name, data)
    relative = "config/versions/it_taxonomy_v0.2.2.json"
    data = subprocess.check_output(["git", "show", f"{TV2_COMMIT}:{relative}"], cwd=root)
    check(relative, data, CONFIG_HASH)
    exact_file(snapshot / "it_taxonomy_v0.2.2.json", data)
    for name in ("a04_handoff_tv1.md", "a04_final_report.md"):
        exact_file(snapshot / name, subprocess.check_output(
            ["git", "show", f"{TV2_COMMIT}:docs/{name}"], cwd=root))
    return destination / REFERENCE_SUBDIR, snapshot, {
        "zip_sha256": digest(archive.read_bytes()), "files": 44, "crc": "PASS",
        "safe_paths": "PASS", "hashes": hashes,
        "main_manual_workbook_received": any(
            PurePosixPath(i.filename).name == "a04_manual_labels_filled.xlsx" for i in infos),
        "tv2_commit": TV2_COMMIT,
    }


def frozen_records(reference: Path):
    frozen = json.loads((reference / "baseline/source_rows.json").read_text(encoding="utf-8"))
    inputs = {}
    for rows in frozen.values():
        for row in rows:
            job = bigint_string(row["job_id"])
            pair = (row["title"], row["description"])
            if job in inputs and inputs[job] != pair:
                raise ValueError("Conflicting duplicate frozen key")
            inputs[job] = pair
    expected = {}
    for line in (reference / "all_predictions.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        job = bigint_string(record["job_id"])
        if job in expected:
            raise ValueError("Duplicate reference key")
        expected[job] = record
    if len(inputs) != 176 or len(expected) != 176 or inputs.keys() != expected.keys():
        raise ValueError("Frozen/reference must have exactly the same 176 keys")
    return inputs, expected


def compare(expected, actual, stage, output):
    mismatches = []
    for job in sorted(expected.keys() | actual.keys(), key=int):
        for entry in differences(expected.get(job), actual.get(job)):
            mismatches.append(dict(stage=stage, job_id=job, **entry))
    write_json(output / f"{stage}_mismatches.json", mismatches)
    if mismatches:
        raise ParityMismatch(f"{stage}: {len(mismatches)} field mismatches (see ignored diagnostics)")
    return {"status": "PASS", "exact_matches": len(expected), "field_mismatches": 0}


def protected_snapshot(root: Path):
    """Content+metadata for D01-D05 tracked files and raw/processed outputs."""
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", D05_HEAD], cwd=root).decode().splitlines()
    all_paths = {root / p for p in paths}
    for directory in ("data/raw", "data/processed"):
        all_paths.update(p for p in (root / directory).rglob("*") if p.is_file())
    result = {}
    for path in sorted(all_paths):
        if path.is_file():
            s = path.stat()
            import hashlib
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024**2), b""):
                    h.update(block)
            result[str(path.relative_to(root))] = [s.st_size, s.st_mtime_ns, h.hexdigest()]
    return result


def verify_d05_base(root: Path, branch: str, head: str):
    """Allow the D06 release commit, not just the original uncommitted D05 HEAD.

    D05 must remain an ancestor and every path tracked at D05 must be unchanged
    in both the committed tree and working tree/index. D06-only additions are OK.
    """
    if branch != "feat/tv1-d06-parity" or subprocess.run(
        ["git", "merge-base", "--is-ancestor", D05_HEAD, head], cwd=root,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode != 0:
        raise ValueError("Unexpected D06 branch/base; inspect Git manually")
    protected = set(subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", D05_HEAD], cwd=root,
    ).decode().splitlines())
    changed = set(subprocess.check_output(
        ["git", "diff", "--name-only", D05_HEAD, "--"], cwd=root,
    ).decode().splitlines())
    changed.update(subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", D05_HEAD, "--"], cwd=root,
    ).decode().splitlines())
    if protected.intersection(changed):
        raise ValueError("D01-D05 tracked paths changed; inspect Git manually")


def run(root: Path = ROOT, prepare_only=False):
    output = root / "tmp/d06_parity" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    summary = {"verdict": "BLOCKED", "started_utc": datetime.now(timezone.utc).isoformat(),
               "git_branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=root).decode().strip(),
               "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip(),
               "d05_base": D05_HEAD,
               "output": str(output), "full_dataset_classification": False,
               "a04_acceptance": "PENDING GROUP REVIEW"}
    spark = None
    before = protected_snapshot(root)
    write_json(output / "protected_before.json", before)
    try:
        verify_d05_base(root, summary["git_branch"], summary["git_head"])
        reference, snapshot, summary["integrity"] = prepare(root)
        print("Integrity PASS: safe ZIP + exact-byte reference/code/config hashes", flush=True)
        inputs, expected = frozen_records(reference)
        if prepare_only:
            summary["preparation"] = "PASS"
            return summary
        model = load_model(snapshot)
        replay = {job: classify(model, job, *pair) for job, pair in inputs.items()}
        summary["python"] = compare(expected, replay, "python", output)
        repeated = {job: classify(model, int(job), *pair) for job, pair in inputs.items()}
        summary["determinism"] = compare(replay, repeated, "determinism", output)
        summary["decisions"] = dict(Counter(r["it_decision"] for r in replay.values()))
        print("Python replay + repeat determinism: 176/176 exact", flush=True)
        schema = derive_schema(list(replay.values()))
        write_json(output / "schema.json", schema.jsonValue())
        for job, record in replay.items():
            if differences(record, decode(encode(record, schema))):
                raise ParityMismatch(f"Typed adapter loses fields before Spark: {job}")

        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
        os.environ.setdefault("PYSPARK_SUBMIT_ARGS", "--driver-memory 3g pyspark-shell")
        from d05_utils import get_spark_session
        from pyspark.sql import functions as F, types as T
        spark = get_spark_session("D06-Frozen176-Parity", root)
        spark.conf.set("spark.sql.shuffle.partitions", "4")
        spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")
        spark.conf.set("spark.sql.adaptive.autoBroadcastJoinThreshold", "-1")
        summary["environment"] = {"python": sys.version, "python_executable": sys.executable,
                                  "spark": spark.version,
                                  "java": spark.sparkContext._jvm.java.lang.System.getProperty("java.version"),
                                  "java_home": os.environ.get("JAVA_HOME"), "master": spark.sparkContext.master}
        if not (sys.version_info[:2] == (3, 11) and spark.version == "4.2.0"
                and summary["environment"]["java"].startswith("21.")):
            raise ValueError("Runtime is not Python3.11 / Spark4.2.0 / Java21")
        input_schema = T.StructType([T.StructField("job_id", T.LongType(), False),
                                     T.StructField("title", T.StringType(), False),
                                     T.StructField("description", T.StringType(), False)])
        source = spark.createDataFrame([(int(job), *inputs[job]) for job in sorted(inputs, key=int)], input_schema).repartition(4)
        df = spark.createDataFrame(source.rdd.mapPartitions(partition_runner(
            str(snapshot), str(root / "src"), schema.jsonValue())), schema).cache()
        rows = df.collect()  # actual Python workers; schema verification enabled

        def collect_predictions(records):
            ids = [r.job_id for r in records]
            if len(ids) != 176 or len(set(ids)) != 176 or any(i is None for i in ids):
                raise ParityMismatch("Spark grain/null/duplicate violation")
            return {bigint_string(r.job_id): decode(r) for r in records}

        actual = collect_predictions(rows)
        summary["spark"] = compare(expected, actual, "spark", output)
        summary["spark"].update(rows=len(rows), unique_job_id=len(actual), null_keys=0, duplicate_keys=0,
                                partitions=len({r._d06_partition_id for r in rows}),
                                workers=len({r._d06_worker_pid for r in rows}),
                                classifier_instances=len({r._d06_classifier_instance for r in rows}))
        print("Spark mapPartitions: 176/176 full nested exact", flush=True)

        # Projection is read-only. LEFT JOIN starts at frozen keys, not all jobs.
        canonical = spark.read.parquet(str(root / "data/processed/canonical/jobs")).select(
            "job_id", "source_title", "source_description", "source_title_sha256", "source_description_sha256"
        ).withColumn("_canonical_found", F.lit(True))
        joined = source.select("job_id").join(canonical, "job_id", "left").collect()
        if len(joined) != 176:
            raise ParityMismatch("Canonical join changed frozen grain")
        found, mismatches = 0, []
        for row in joined:
            job = bigint_string(row.job_id)
            if row._canonical_found is not True:
                mismatches.append({"job_id": job, "field": "$canonical", "expected": "present", "actual": "missing"})
                continue
            found += 1
            for field in ("title", "description", "source_title_sha256", "source_description_sha256"):
                value = row["source_" + field] if field in ("title", "description") else row[field]
                mismatches.extend(dict(job_id=job, **d) for d in differences(expected[job][field], value, "$canonical." + field))
        write_json(output / "canonical_mismatches.json", mismatches)
        summary["canonical"] = {"status": "PASS" if not mismatches else "FAIL", "found": found,
                                "missing": 176 - found, "text_hash_matches": 176 - len({m["job_id"] for m in mismatches}),
                                "text_hash_mismatch_jobs": len({m["job_id"] for m in mismatches})}
        if mismatches:
            raise ParityMismatch("D05 source compatibility mismatch; D05 left untouched")
        print("Canonical LEFT JOIN: 176/176 source text + hashes match", flush=True)
        parquet = output / "predictions.parquet"
        df.write.mode("errorifexists").parquet(str(parquet))
        readback = spark.read.parquet(str(parquet))
        if schema.toNullable() != readback.schema.toNullable():
            raise ParityMismatch("Parquet changed schema beyond physical nullability relaxation")
        summary["roundtrip"] = compare(expected, collect_predictions(readback.collect()), "roundtrip", output)
        summary["roundtrip"]["schema_types_unchanged"] = True
        summary["roundtrip"]["parquet_nullable_relaxation"] = True
        summary["roundtrip"]["review_nulls"] = readback.filter((F.col("it_decision") == "REVIEW") & F.col("is_it").isNull()).count()
        if summary["roundtrip"]["review_nulls"] != 33:
            raise ParityMismatch("REVIEW/null lost in Parquet")
        summary["verdict"] = "PASS"
        print("Parquet readback: 176/176 exact; REVIEW nulls retained", flush=True)
    except Exception as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
        # Incompatible artifacts/runtime block validation; mismatches fail parity.
        if isinstance(exc, ParityMismatch) or "mismatch" in str(exc).lower():
            summary["verdict"] = "FAIL"
        print(summary["error"], flush=True)
        raise
    finally:
        if spark is not None:
            try:
                spark.stop()
            except Exception as exc:
                summary["spark_stop_warning"] = str(exc)
        after = protected_snapshot(root)
        changed = [k for k in sorted(before.keys() | after.keys()) if before.get(k) != after.get(k)]
        summary["preservation"] = {"protected_files": len(before), "changed": changed,
                                   "hash_size_mtime_unchanged": not changed}
        if changed:
            summary["verdict"] = "FAIL"
        summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(output / "summary.json", summary)
        print("D06 summary:", output / "summary.json", flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    arguments = parser.parse_args()
    result = run(prepare_only=arguments.prepare_only)
    if not arguments.prepare_only and result["verdict"] != "PASS":
        raise SystemExit(1)
