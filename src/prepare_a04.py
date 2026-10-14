"""Apply the shared taxonomy to raw postings and prepare a blind 160-job A04 sample.

Outputs are exploratory predictions, never canonical production data or gold labels.
Existing output directories are refused to protect manual annotations.
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import gzip
import hashlib
import html
import json
import re
import sys
from pathlib import Path

from it_taxonomy import Taxonomy
from tv2_csv import ROOT, csv_rows, integer_key, sha256, write_csv, write_json

STRATA = ["ACCEPT_SINGLE_GROUP", "ACCEPT_MULTIPLE_OR_SUBGROUP", "REJECT_BY_EXCLUSION", "REJECT_NO_MATCH", "REVIEW_AMBIGUOUS_OR_MISSING"]
MANUAL_FIELDS = ["manual_label", "manual_is_it", "manual_primary_group_code", "manual_subgroup_code", "manual_reason", "manual_evidence", "reviewer", "reviewed_date"]


def stratum(record):
    if record["it_decision"] == "ACCEPT":
        return STRATA[1] if len(record["candidate_group_codes"]) > 1 or record["subgroup_code"] in {"SOFTWARE_MOBILE", "SOFTWARE_WEB"} else STRATA[0]
    if record["it_decision"] == "REJECT":
        return STRATA[2] if "OUTSIDE_IT_ROLE" in record["reason_codes"] else STRATA[3]
    return STRATA[4]


def choose_sample(records, taxonomy, metadata_jobs):
    design = taxonomy.config["a04_review_design"]
    seed = design["seed"]
    quota = {s["code"]: s["target"] for s in design["strata"]}
    buckets = {s: [] for s in quota}
    for record in records:
        job = record["job_id"]
        record["sampling_hash"] = hashlib.sha256(f"{seed}:{job}".encode("utf-8")).hexdigest()
        record["stratum"] = stratum(record)
        buckets[record["stratum"]].append(record)
    for bucket in buckets.values():
        bucket.sort(key=lambda r: (r["sampling_hash"], int(r["job_id"])))
    selected, counts, reservations = {}, collections.Counter(), []

    def reserve(name, candidates, target):
        candidates = sorted(candidates, key=lambda r: (r["sampling_hash"], int(r["job_id"])))
        existing = sum(r["job_id"] in selected for r in candidates)
        added = 0
        for record in candidates:
            s, job = record["stratum"], record["job_id"]
            if existing + added >= target:
                break
            if job not in selected and counts[s] < quota[s]:
                selected[job] = record
                counts[s] += 1
                added += 1
        reservations.append(dict(name=name, requested=target, available=len(candidates), achieved=existing + added))

    accepted = buckets[STRATA[0]] + buckets[STRATA[1]]
    for code in ["SOFTWARE_MOBILE", "SOFTWARE_WEB"]:
        reserve(code, [r for r in accepted if r["subgroup_code"] == code], 5)
    for group in sorted(taxonomy.groups.values(), key=lambda g: g["priority"]):
        reserve(group["code"], [r for r in accepted if r["primary_group_code"] == group["code"]], 1 if group["code"] == "IT_OTHER" else 4)
    for tier in ["TITLE_DIRECT", "TITLE_CONTEXT", "DESCRIPTION_ROLE_TASK"]:
        reserve(tier, [r for r in accepted if tier in r["reason_codes"]], 1)
    reserve("MULTIPLE_GROUP_CANDIDATES", [r for r in buckets[STRATA[1]] if "MULTIPLE_GROUP_CANDIDATES" in r["reason_codes"]], 1)
    reserve("SHORT_ACRONYM_TITLE", [r for r in accepted if re.search(r"\b(?:SRE|DBA|CTO|CIO|SDET)\b", r["title"], re.I)], 1)
    for rule in taxonomy.config["exclusion_rules"]:
        reserve(rule["id"], [r for r in buckets[STRATA[2]] if rule["id"] in r["matched_rule_ids"]], 3)
    reserve("NO_MATCH_WITH_IT_OR_SOFTWARE_METADATA", [r for r in buckets[STRATA[3]] if r["job_id"] in metadata_jobs], 5)
    for reason in ["POSITIVE_EXCLUSION_CONFLICT", "MISSING_TITLE", "AMBIGUOUS_TITLE_WITHOUT_CONTEXT", "DESCRIPTION_SEGMENT_SKIPPED"]:
        reserve(reason, [r for r in buckets[STRATA[4]] if reason in r["reason_codes"]], 3)
    for code, bucket in buckets.items():
        reserve(f"FILL_{code}", bucket, quota[code])
    shortages = {s: quota[s] - counts[s] for s in quota if counts[s] < quota[s]}
    # A02 allows explicit shortfall transfers; never duplicate a job.
    if shortages:
        needed = sum(shortages.values())
        candidates = sorted((r for bucket in buckets.values() for r in bucket if r["job_id"] not in selected), key=lambda r: (r["sampling_hash"], int(r["job_id"])))
        for r in candidates[:needed]:
            selected[r["job_id"]] = r
            counts[r["stratum"]] += 1
    result = sorted(selected.values(), key=lambda r: (r["sampling_hash"], int(r["job_id"])))
    assert len({r["job_id"] for r in result}) == len(result) == design["target_unique_jobs"]
    return result, dict(seed=seed, quotas=quota, populations={s: len(b) for s, b in buckets.items()}, sample_counts=dict(counts), reservations=reservations, shortfall_transfers=shortages, method="Disjoint strata; reserve A02 coverage targets then fill each stratum by SHA-256('42:<canonical_job_id>'), numeric job_id tie-break; shuffle blind rows by same hash", purpose="RULE_DEVELOPMENT_ONLY_NOT_FINAL_EVALUATION", estimation_limit="Coverage reservations are purposive; do not use n/N as inclusion probabilities or extrapolate metrics to all postings.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--config", type=Path, default=ROOT / "config/it_taxonomy.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/analytics/a04_taxonomy_v0_1_0_seed42")
    parser.add_argument("--reuse-predictions", type=Path, help="Reuse this run's frozen gzip JSONL after checking source/config hashes and full text against raw")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError("Use the project Python 3.11 .venv")
    if args.output.exists():
        raise FileExistsError("Output already exists; use another --output to preserve manual labels")
    model = Taxonomy(args.config)
    cases = model.check_illustrative_cases()
    raw_files = sorted(args.raw.rglob("*.csv"))
    before = {str(p.relative_to(args.raw)): dict(bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns, sha256=sha256(p)) for p in raw_files}
    if len(before) != 11:
        raise ValueError("Expected all 11 raw CSVs")
    prediction_file = args.reuse_predictions or args.output / "all_predictions.jsonl.gz"
    if args.reuse_predictions:
        parent_manifest = json.loads((prediction_file.parent / "run_manifest.json").read_text(encoding="utf-8"))
        if parent_manifest["raw_files"] != before or parent_manifest["taxonomy_sha256"] != model.sha256:
            raise ValueError("Cached predictions source/taxonomy mismatch")
    metadata_jobs = {integer_key(r["job_id"]) for r in csv_rows(args.raw / "jobs/job_skills.csv") if r["skill_abr"] == "IT"}
    software_ids = {integer_key(r["industry_id"]) for r in csv_rows(args.raw / "mappings/industries.csv") if r["industry_name"] == "Software Development"}
    metadata_jobs.update(integer_key(r["job_id"]) for r in csv_rows(args.raw / "jobs/job_industries.csv") if integer_key(r["industry_id"]) in software_ids)
    args.output.mkdir(parents=True)
    counts, groups, reasons = collections.Counter(), collections.Counter(), collections.Counter()
    records, seen = [], set()
    output_context = contextlib.nullcontext(None) if args.reuse_predictions else gzip.open(prediction_file, "xt", encoding="utf-8")
    input_context = gzip.open(prediction_file, "rt", encoding="utf-8") if args.reuse_predictions else contextlib.nullcontext(None)
    with output_context as out, input_context as cached:
        for row in csv_rows(args.raw / "postings.csv"):
            job = integer_key(row["job_id"])
            if job is None or job in seen:
                raise ValueError(f"Missing/duplicate job_id: {job}")
            seen.add(job)
            if cached:
                full = json.loads(next(cached))
                if full["job_id"] != job or full["title"] != row["title"] or full["description"] != row["description"] or full["taxonomy_sha256"] != model.sha256:
                    raise ValueError("Cached prediction grain/source text/config mismatch")
                prediction = {f["name"]: full[f["name"]] for f in model.config["proposed_output_contract"]["fields"]}
            else:
                prediction = model.classify(row["title"], row["description"], job)
                full = dict(**prediction, title=row["title"], description=row["description"], source_title_sha256=hashlib.sha256(row["title"].encode()).hexdigest(), source_description_sha256=hashlib.sha256(row["description"].encode()).hexdigest())
            assert (prediction["primary_group_code"] is not None) == (prediction["it_decision"] == "ACCEPT")
            if out:
                out.write(json.dumps(full, ensure_ascii=False, separators=(",", ":")) + "\n")
            records.append({k: v for k, v in prediction.items() if k != "match_evidence"} | {"title": row["title"]})
            counts[prediction["it_decision"]] += 1
            if prediction["primary_group_code"]:
                groups[prediction["primary_group_code"]] += 1
            reasons.update(prediction["reason_codes"])
            if len(seen) % 5000 == 0:
                print(f"{'Reused' if cached else 'Classified'} {len(seen)} jobs: {dict(counts)}", flush=True)
        if cached and cached.readline():
            raise ValueError("Cached predictions contain extra rows")
    sample, sampling = choose_sample(records, model, metadata_jobs)
    ids = {r["job_id"] for r in sample}
    full_sample = {}
    with gzip.open(prediction_file, "rt", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record["job_id"] in ids:
                full_sample[record["job_id"]] = record
    blind, private, reader = [], [], []
    for i, item in enumerate(sample, 1):
        record = full_sample[item["job_id"]]
        blind.append(dict(sample_id=f"A04-{i:03d}", job_id=record["job_id"], title=record["title"], description=record["description"], **{c: "" for c in MANUAL_FIELDS}))
        private.append(dict(sample_id=f"A04-{i:03d}", stratum=item["stratum"], sampling_hash=item["sampling_hash"], **record))
        reader.append(f'<article id="A04-{i:03d}"><h2>A04-{i:03d} · job_id {html.escape(record["job_id"])}</h2><h3>{html.escape(record["title"])}</h3><pre>{html.escape(record["description"])}</pre></article>')
    write_csv(args.output / "a04_manual_labels_blind.csv", blind, list(blind[0]), exclusive=True, bom=True)
    with (args.output / "sample_predictions_private.jsonl").open("x", encoding="utf-8") as stream:
        for record in private:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    write_csv(args.output / "sampling_manifest_private.csv", [dict(sample_id=f"A04-{i:03d}", job_id=r["job_id"], stratum=r["stratum"], sampling_hash=r["sampling_hash"]) for i, r in enumerate(sample, 1)], ["sample_id", "job_id", "stratum", "sampling_hash"], exclusive=True)
    (args.output / "a04_blind_reader.html").write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>A04 – Bản đọc gán nhãn</title><style>body{max-width:1000px;margin:30px auto;font:16px/1.6 system-ui}article{border-top:2px solid #888;margin-top:40px}pre{white-space:pre-wrap;font:inherit;overflow-wrap:anywhere}</style><h1>A04 – 160 tin để gán nhãn</h1><p>Đọc title và toàn bộ description. Điền nhãn trong a04_manual_labels_blind.csv theo sample_id/job_id. Các dự đoán được giữ trong file riêng; chỉ mở sau vòng nhãn tay đầu.</p>' + '\n'.join(reader) + '</html>', encoding="utf-8")
    after = {str(p.relative_to(args.raw)): dict(bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns, sha256=sha256(p)) for p in raw_files}
    assert before == after, "Raw source changed"
    assert sha256(args.config) == model.sha256, "Taxonomy changed during run"
    assert len(seen) == sum(counts.values())
    run = dict(status="PREDICTIONS_NOT_MANUALLY_EVALUATED", input="raw CSV, not D04 Parquet or canonical D05", taxonomy_version=model.version, taxonomy_sha256=model.sha256, python=sys.version, python_executable=sys.executable, date="2026-10-08", illustrative_cases_passed=cases, rows=len(seen), distinct_job_ids=len(seen), decisions=dict(counts), predicted_primary_groups=dict(groups), reason_counts=dict(reasons), raw_files=before, raw_unchanged=True, sampling=sampling, sample_group_counts=dict(collections.Counter(r["primary_group_code"] for r in sample if r["primary_group_code"])), sample_subgroup_counts=dict(collections.Counter(r["subgroup_code"] for r in sample if r["subgroup_code"])), manual_labels_filled=0, final_evaluation_sample="NOT_CREATED; draw independently after rules freeze, exclude all development job_ids", clean_parquet_present=any((ROOT / "data/processed").rglob("*.parquet")), spark_jvm_parity="PENDING_TV1", metrics="NOT_COMPUTED_NO_MANUAL_LABELS")
    run.update(output_path=str(args.output.resolve()), all_predictions_file=str(prediction_file.resolve()), all_predictions_sha256=sha256(prediction_file), interpreter_sha256=sha256(ROOT / "src/it_taxonomy.py"), runner_sha256=sha256(Path(__file__)), reused_predictions=bool(args.reuse_predictions))
    write_json(args.output / "run_manifest.json", run, exclusive=True)
    write_json(ROOT / "data/audit/tv2_a04_summary.json", {k: v for k, v in run.items() if k != "raw_files"})
    print(json.dumps({"decisions": dict(counts), "sample": sampling, "output": str(args.output)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
