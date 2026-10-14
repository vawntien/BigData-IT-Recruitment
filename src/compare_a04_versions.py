"""Run v0.2 on raw, compare frozen v0.1 by job_id, never replace seed42.

Comparison counts and changed-case reading files are predictions, not metrics or
manual labels. No ETL, Parquet, sampling replacement, or canonical TV1 writes.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import html
import json
import platform
import sys
import time
from pathlib import Path

from it_taxonomy import Taxonomy
from prepare_a04 import MANUAL_FIELDS
from tv2_csv import ROOT, csv_rows, integer_key, sha256, write_csv, write_json

CONTRACT = ["it_decision", "is_it", "primary_group_code", "subgroup_code", "selected_rule_id", "reason_codes", "matched_rule_ids", "candidate_group_codes"]


def inventory(paths):
    return {str(p.relative_to(ROOT)): dict(bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns, sha256=sha256(p)) for p in paths}


def validate_evidence(model, record):
    count = 0
    units = {unit["index"]: unit for unit in record["description_segments"]}
    for e in record["match_evidence"]:
        source = record[e["field"]]
        assert e["excerpt"] == source[e["raw_excerpt_start"]:e["raw_excerpt_end"]]
        assert len(e["excerpt"]) <= model.config["proposed_output_contract"]["evidence_excerpt_max_characters"]
        assert e["mapping_status"] == "MAPPED_TO_RAW"
        assert all(0 <= a < b <= len(source) for a, b in e["raw_match_ranges"])
        # Tags are absent from the match ranges, while entities remain raw.
        matched_source = "".join(source[a:b] for a, b in e["raw_match_ranges"])
        if e["field"] == "description":
            matched_source = html.unescape(matched_source)
            unit = units[e["segment_index"]]
            a, b = e["derived_start"] - unit["derived_start"], e["derived_end"] - unit["derived_start"]
            assert unit["text"][a:b] == e["derived_matched_text"]
            assert not unit["blocked_reasons"]
        assert model.normalize(matched_source) == model.normalize(e["matched_alias"]), (record["job_id"], e)
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/it_taxonomy.json")
    parser.add_argument("--raw", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--old-trace", type=Path, default=ROOT / "data/analytics/a04_taxonomy_v0_1_0_seed42/all_predictions.jsonl.gz")
    parser.add_argument("--old-provenance", type=Path, default=ROOT / "data/analytics/a04_manual_seed42/run_manifest.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/analytics/a04_taxonomy_v0_2_0_20261008")
    parser.add_argument("--audit-output", type=Path, default=ROOT / "data/audit/tv2_a04_v020_comparison.json")
    args = parser.parse_args()
    if args.output.exists() or args.audit_output.exists():
        raise FileExistsError("Choose new output and audit paths; existing runs/labels are protected")
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError("Use project Python 3.11 .venv")
    started = time.monotonic()
    model = Taxonomy(args.config)
    assert model.version == "0.2.0"
    assert model.check_illustrative_cases() == 57
    old_manifest = json.loads((args.old_trace.parent / "run_manifest.json").read_text(encoding="utf-8"))
    # The initial v0.1 manifest predates hash fields. Its frozen resampling
    # manifest records exact trace/code hashes; verify both rather than infer.
    old_provenance = json.loads(args.old_provenance.read_text(encoding="utf-8"))
    assert Path(old_provenance["all_predictions_file"]).resolve() == args.old_trace.resolve()
    for key in ["taxonomy_sha256", "raw_files", "rows", "decisions"]:
        assert old_provenance[key] == old_manifest[key], key
    assert sha256(args.old_trace) == old_provenance["all_predictions_sha256"]
    before = inventory(sorted(args.raw.rglob("*.csv")))
    expected_raw = {str(Path("data/raw") / k): v for k, v in old_manifest["raw_files"].items()}
    assert before == expected_raw and len(before) == 11
    old_config = ROOT / "config/versions/it_taxonomy_v0.1.0.json"
    assert sha256(old_config) == old_manifest["taxonomy_sha256"]
    assert sha256(ROOT / "src/it_taxonomy_v010.py") == old_provenance["interpreter_sha256"]
    protected_before = json.loads((ROOT / "data/audit/tv2_a04_v020_protected_before.json").read_text(encoding="utf-8"))
    assert inventory([ROOT / p for p in protected_before]) == protected_before
    old_model = Taxonomy(old_config)
    for key in ["groups", "subgroups", "term_sets", "include_rules", "general_it_rules", "exclusion_rules", "a04_review_design"]:
        assert model.config[key] == old_model.config[key], key
    implementation = [ROOT / "src" / name for name in ["it_taxonomy.py", "it_taxonomy_v010.py", "description_processing.py", "tv2_csv.py", "compare_a04_versions.py", "prepare_a04.py"]]
    implementation_hashes = {p.name: sha256(p) for p in implementation}
    baseline, old_counts = {}, collections.Counter()
    with gzip.open(args.old_trace, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            assert row["job_id"] not in baseline
            baseline[row["job_id"]] = {key: row[key] for key in CONTRACT} | {
                "title_sha256": hashlib.sha256(row["title"].encode()).hexdigest(),
                "description_sha256": hashlib.sha256(row["description"].encode()).hexdigest(),
            }
            old_counts[row["it_decision"]] += 1
    assert len(baseline) == 123849 and dict(old_counts) == old_manifest["decisions"]
    print(f"Loaded {len(baseline)} frozen v0.1 jobs for join by job_id", flush=True)
    args.output.mkdir(parents=True)
    (args.output / "implementation").mkdir()
    for path in implementation:
        with (args.output / "implementation" / path.name).open("xb") as out:
            out.write(path.read_bytes())
    for source, target in [(args.config, args.output / "it_taxonomy_v0.2.0.json"), (old_config, args.output / "it_taxonomy_v0.1.0.json")]:
        with target.open("xb") as out:
            out.write(source.read_bytes())
    write_json(args.output / "protected_before.json", protected_before, exclusive=True)
    fixed_ids = set()
    folder = ROOT / "data/analytics/a04_diagnostics_v0_1_0_20261008"
    for filename in ["real_job_specimens.json", "description_gate_task_examples.json"]:
        fixed_ids.update(r["job_id"] for r in json.loads((folder / filename).read_text(encoding="utf-8")))
    counts, groups, reasons, transitions, changed_categories, processing, reason_changes, rule_matches = (collections.Counter() for _ in range(8))
    seen, pools, fixed_comparisons = set(), collections.defaultdict(list), []
    fields = ["job_id", "old_decision", "new_decision", "old_group", "new_group", "old_subgroup", "new_subgroup", "old_selected_rule", "new_selected_rule",
              "old_reasons", "new_reasons", "change_categories", "legacy_long_units", "legacy_long_processed", "legacy_long_unresolved", "new_long_units", "new_unresolved_units"]
    import csv
    trace = args.output / "all_predictions.jsonl.gz"
    validated_evidence, changed_jobs = 0, 0
    with gzip.open(trace, "xt", encoding="utf-8", compresslevel=6) as output, (args.output / "job_comparison.csv").open("x", encoding="utf-8", newline="") as comparison:
        writer = csv.DictWriter(comparison, fieldnames=fields)
        writer.writeheader()
        for row in csv_rows(args.raw / "postings.csv"):
            job = integer_key(row["job_id"])
            assert job is not None and job not in seen and job in baseline
            seen.add(job)
            old = baseline[job]
            assert hashlib.sha256(row["title"].encode()).hexdigest() == old["title_sha256"]
            assert hashlib.sha256(row["description"].encode()).hexdigest() == old["description_sha256"]
            record = model.classify(row["title"], row["description"], job)
            record.update(title=row["title"], description=row["description"], source_title_sha256=old["title_sha256"], source_description_sha256=old["description_sha256"])
            assert (record["primary_group_code"] is not None) == (record["it_decision"] == "ACCEPT")
            assert record["description_processing"]["dropped_oversize_units"] == 0
            validated_evidence += validate_evidence(model, record)
            output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            counts[record["it_decision"]] += 1
            if record["primary_group_code"]:
                groups[record["primary_group_code"]] += 1
            reasons.update(record["reason_codes"])
            rule_matches.update(record["matched_rule_ids"])
            key = old["it_decision"] + "->" + record["it_decision"]
            transitions[key] += 1
            categories = [k for k in CONTRACT if old[k] != record[k]]
            if categories:
                changed_jobs += 1
                changed_categories.update(categories)
                reason_changes[json.dumps([old["reason_codes"], record["reason_codes"]], separators=(",", ":"))] += 1
                pool = pools[key if old["it_decision"] != record["it_decision"] else "SAME_STATE_DETAILS_CHANGED"]
                hash_key = hashlib.sha256(("a04-v020-review:" + job).encode()).hexdigest()
                pool.append((hash_key, record, old, categories))
                pool.sort(key=lambda item: (item[0], int(item[1]["job_id"])))
                del pool[5:]
            if job in fixed_ids:
                fixed_comparisons.append(dict(job_id=job, old_prediction=old, new_prediction=record, change_categories=categories, manual_label=None))
            stats = record["description_processing"]
            for k in ["units", "retained_long_units", "unresolved_units", "legacy_oversize_units_total", "legacy_oversize_units_processed", "legacy_oversize_units_unresolved", "dropped_oversize_units"]:
                processing[k] += stats[k]
            processing["jobs_incomplete"] += stats["incomplete"]
            processing["jobs_with_legacy_long"] += bool(stats["legacy_oversize_units_total"])
            processing["jobs_with_legacy_long_all_processed"] += bool(stats["legacy_oversize_units_total"]) and not stats["legacy_oversize_units_unresolved"]
            processing["jobs_html_or_entity_parser"] += stats["parser"] == "HTMLParser"
            processing["jobs_parser_issues"] += bool(stats["parser_issues"])
            processing["jobs_mapping_unavailable"] += not stats["source_mapping_available"]
            processing["candidate_windows_blocked"] += sum(bool(w["blocked_reason"]) for unit in record["description_segments"] for w in unit.get("window_diagnostics", []))
            writer.writerow(dict(job_id=job, old_decision=old["it_decision"], new_decision=record["it_decision"], old_group=old["primary_group_code"], new_group=record["primary_group_code"],
                                 old_subgroup=old["subgroup_code"], new_subgroup=record["subgroup_code"], old_selected_rule=old["selected_rule_id"], new_selected_rule=record["selected_rule_id"],
                                 old_reasons="|".join(old["reason_codes"]), new_reasons="|".join(record["reason_codes"]), change_categories="|".join(categories),
                                 legacy_long_units=stats["legacy_oversize_units_total"], legacy_long_processed=stats["legacy_oversize_units_processed"], legacy_long_unresolved=stats["legacy_oversize_units_unresolved"],
                                 new_long_units=stats["retained_long_units"], new_unresolved_units=stats["unresolved_units"]))
            if len(seen) % 5000 == 0:
                print(f"v0.2 {len(seen)}/{len(baseline)}: {dict(counts)}; elapsed {time.monotonic() - started:.1f}s", flush=True)
    assert seen == set(baseline)
    assert processing["jobs_with_legacy_long"] == 71150 and processing["legacy_oversize_units_total"] == 118943
    assert inventory([ROOT / p for p in protected_before]) == protected_before
    assert inventory(sorted(args.raw.rglob("*.csv"))) == before
    assert sha256(args.config) == model.sha256
    assert {p.name: sha256(p) for p in implementation} == implementation_hashes
    write_json(args.output / "diagnostic_cases_comparison_private.json", sorted(fixed_comparisons, key=lambda r: int(r["job_id"])), exclusive=True)
    selected = {record["job_id"]: (record, old, categories) for pool in pools.values() for _, record, old, categories in pool}
    for item in fixed_comparisons:
        if item["change_categories"]:
            selected[item["job_id"]] = (item["new_prediction"], item["old_prediction"], item["change_categories"])
    blind, private = [], []
    for job, (record, old, categories) in sorted(selected.items(), key=lambda pair: hashlib.sha256(("a04-v020-review:" + pair[0]).encode()).hexdigest()):
        blind.append(dict(job_id=job, title=record["title"], description=record["description"], **{name: "" for name in MANUAL_FIELDS}))
        private.append(dict(job_id=job, old_prediction=old, new_prediction={k: v for k, v in record.items() if k not in {"title", "description"}}, change_categories=categories))
    write_csv(args.output / "changed_cases_for_review_blind.csv", blind, ["job_id", "title", "description", *MANUAL_FIELDS], exclusive=True, bom=True)
    with (args.output / "changed_case_predictions_private.jsonl").open("x", encoding="utf-8") as stream:
        for row in private:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    matrix = {old: {new: transitions[old + "->" + new] for new in ["ACCEPT", "REJECT", "REVIEW"]} for old in ["ACCEPT", "REJECT", "REVIEW"]}
    summary = dict(status="VERSION_COMPARISON_PREDICTIONS_NOT_EVALUATED", date="2026-10-08", taxonomy_version=model.version,
                   taxonomy_sha256=model.sha256, old_taxonomy_version=old_model.version, old_taxonomy_sha256=old_model.sha256,
                   old_trace_sha256=sha256(args.old_trace), new_trace_sha256=sha256(trace), rows=len(seen), distinct_job_ids=len(seen),
                   old_decisions=dict(old_counts), new_decisions=dict(counts), transitions=matrix, changed_jobs_any_contract_field=changed_jobs,
                   change_categories=dict(changed_categories), reason_transition_counts=dict(reason_changes), new_reason_counts=dict(reasons),
                   predicted_primary_groups=dict(groups), matched_rule_counts=dict(rule_matches), description_processing=dict(processing),
                   evidence_validated_against_raw=validated_evidence, raw_full_text_equal_old_trace=True, raw_unchanged=True,
                   protected_artifacts_unchanged=True, protected_artifacts_checked=len(protected_before), occupational_rules_aliases_groups_priorities_unchanged=True,
                   changed_case_review=dict(rows=len(blind), purpose="RULE_DEVELOPMENT_ONLY_NOT_FINAL_EVALUATION", manual_fields_blank=True,
                                            method="Five smallest SHA-256('a04-v020-review:<job_id>') per state transition, plus five same-state detail changes and changed diagnostic cases; deduplicate job_id",
                                            development_job_ids=sorted(set(selected) | fixed_ids, key=int)),
                   illustrative_cases_passed=57, python=platform.python_version(), python_executable=sys.executable,
                   implementation_sha256=implementation_hashes, output_path=str(args.output.resolve()),
                   spark_jvm_parity="NOT_VERIFIED", metrics="NOT_COMPUTED_NO_MANUAL_LABELS", elapsed_seconds=round(time.monotonic() - started, 2))
    write_json(args.output / "comparison_summary.json", summary, exclusive=True)
    write_json(args.output / "run_manifest.json", summary | dict(raw_files=old_manifest["raw_files"], all_predictions_file=str(trace.resolve()), all_predictions_sha256=summary["new_trace_sha256"], decisions=dict(counts)), exclusive=True)
    write_json(args.audit_output, summary, exclusive=True)
    print(json.dumps({k: summary[k] for k in ["old_decisions", "new_decisions", "transitions", "description_processing", "changed_case_review", "elapsed_seconds"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
