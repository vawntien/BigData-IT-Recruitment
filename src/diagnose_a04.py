"""Read-only A04 v0.1.0 diagnostics: segmentation, lost evidence, fallback gates.

This analyzes existing predictions; it never re-labels jobs or updates seed42.
Potential matches in excluded segments are diagnostics, not gold labels or a
new classifier. All aliases and input conditions come from the existing JSON.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

from it_taxonomy import Taxonomy
from tv2_csv import ROOT, sha256, write_json

HTML_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*|\s*/?)>")
HTML_ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]+|#\d+|#x[0-9a-fA-F]+);")


def split_spans(model, description):
    """Same splitter as production, preserving source offsets for inspection."""
    cursor, segments = 0, []
    for match in model.splitter.finditer(description):
        segments.append((cursor, match.start(), description[cursor:match.start()]))
        cursor = match.end()
    segments.append((cursor, len(description), description[cursor:]))
    assert [r[2] for r in segments] == model.splitter.split(description)
    return segments


def descriptor(model, record):
    title = model.normalize(record["title"])
    gate = model.is_missing(record["title"]) or title in {v for _, v in model.aliases["generic_exact_titles"]}
    segments = []
    for index, (start, end, raw) in enumerate(split_spans(model, record["description"])):
        value = model.normalize(raw)
        if not value:
            continue
        segments.append(dict(index=index, start=start, end=end, raw=raw, normalized=value,
                             length=len(value), skipped=len(value) > model.segment_config["max_normalized_characters"]))
    cache = {}

    def hit(segment, term_set):
        key = segment["index"], term_set
        if key not in cache:
            cache[key] = bool(model.fast_patterns[term_set].search(segment["normalized"]))
        return cache[key]

    blocked_sets = model.segment_config["blocked_term_sets"]
    for segment in segments:
        segment["blocked"] = any(hit(segment, k) for k in blocked_sets)
    return gate, segments, hit


def specimen(model, record, category):
    gate, segments, hit = descriptor(model, record)
    rule_rows = []
    active_long = []
    for rule in model.config["include_rules"]:
        if rule["evidence_tier"] == "DESCRIPTION_ROLE_TASK":
            sets = rule["condition"]["all"][1]["same_segment"]["all_term_sets"]
            joint = [s for s in segments if all(hit(s, k) for k in sets)]
            rule_rows.append(dict(rule_id=rule["id"], title_gate=gate, term_sets=sets,
                                  any_hit_by_set={k: any(hit(s, k) for s in segments) for k in sets},
                                  joint_segments=[s["index"] for s in joint],
                                  joint_short_unblocked=[s["index"] for s in joint if not s["skipped"] and not s["blocked"]],
                                  joint_long=[s["index"] for s in joint if s["skipped"]],
                                  joint_blocked=[s["index"] for s in joint if s["blocked"]]))
        elif rule["evidence_tier"] == "TITLE_CONTEXT":
            title_term_set = rule["condition"]["all"][0]["match"]["term_set"]
            if model.fast_patterns[title_term_set].search(model.normalize(record["title"])):
                sets = rule["condition"]["all"][1]["same_segment"]["all_term_sets"]
                active_long.extend(dict(rule_id=rule["id"], segment_index=s["index"], blocked=s["blocked"]) for s in segments if s["skipped"] and all(hit(s, k) for k in sets))
    term_sets = model.config["term_sets"]
    segment_rows = []
    for segment in segments:
        hits = {}
        for key in term_sets:
            if hit(segment, key):
                hits[key] = [alias for alias, pattern in model.patterns[key] if pattern.search(segment["normalized"])]
        segment_rows.append(dict(index=segment["index"], raw_start=segment["start"], raw_end=segment["end"],
                                 normalized_codepoints=segment["length"], normalized_words=len(segment["normalized"].split()),
                                 normalized_utf16_units=len(segment["normalized"].encode("utf-16-le")) // 2,
                                 skipped=segment["skipped"], blocked=segment["blocked"], term_set_hits=hits, raw_text=segment["raw"]))
    current = model.classify(record["title"], record["description"], record["job_id"])
    contract = ["it_decision", "is_it", "primary_group_code", "subgroup_code", "selected_rule_id", "reason_codes", "matched_rule_ids"]
    assert all(current[k] == record[k] for k in contract), f"Saved trace no longer matches code: {record['job_id']}"
    return dict(category=category, job_id=record["job_id"], title=record["title"], description=record["description"],
                original_prediction={k: record[k] for k in contract}, title_gate=gate, segments=segment_rows,
                description_rule_diagnostics=rule_rows, active_context_matches_in_skipped_segments=active_long,
                trace_replay_equal=True, manual_label=None)


def snapshot(paths):
    return {str(p.relative_to(ROOT)): dict(bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns, sha256=sha256(p)) for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/analytics/a04_diagnostics_v0_1_0_20261008")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Diagnostic output exists; choose a new directory")
    model = Taxonomy(ROOT / "config/versions/it_taxonomy_v0.1.0.json")
    run = json.loads((ROOT / "data/analytics/a04_manual_seed42/run_manifest.json").read_text(encoding="utf-8"))
    trace = Path(run["all_predictions_file"])
    assert model.sha256 == run["taxonomy_sha256"]
    assert sha256(trace) == run["all_predictions_sha256"]
    protected = [p for folder in [ROOT / "data/analytics/a04_manual_seed42", ROOT / "data/analytics/a04_taxonomy_v0_1_0_seed42"] for p in folder.rglob("*") if p.is_file()]
    protected += [ROOT / "config/versions/it_taxonomy_v0.1.0.json", ROOT / "src/it_taxonomy_v010.py"]
    before = snapshot(protected)
    args.output.mkdir(parents=True)
    write_json(args.output / "protected_before.json", before, exclusive=True)
    description_rules = [r for r in model.config["include_rules"] if r["evidence_tier"] == "DESCRIPTION_ROLE_TASK"]
    stages = {r["id"]: collections.Counter() for r in description_rules}
    counts, formats, flag_states, combinations = (collections.Counter() for _ in range(4))
    generic_titles, fallback_trace_rules, gate_states = (collections.Counter() for _ in range(3))
    long_lengths, gate_task_records = [], {}
    pools = collections.defaultdict(list)
    quotas = {"REVIEW_ACTIVE_CONTEXT_IN_SKIPPED": 4, "REVIEW_GENERIC_TITLE": 3, "REVIEW_NO_ACTIVE_CONTEXT_IN_SKIPPED": 4, "ACCEPT_FLAGGED": 3, "REJECT_FLAGGED": 3, "HTML_FLAGGED": 1}

    def add_candidate(category, record):
        key = hashlib.sha256(f"a04-diagnostics-20261008:{record['job_id']}".encode()).hexdigest()
        pool = pools[category]
        pool.append((key, record))
        pool.sort(key=lambda pair: (pair[0], int(pair[1]["job_id"])))
        del pool[24:]

    per_job_fields = ["job_id", "it_decision", "flagged", "description_codepoints", "segments", "skipped_segments", "skipped_codepoints", "title_gate", "active_context_long_joint", "active_context_long_unblocked", "has_html_tag", "has_lf", "has_crlf"]
    import csv
    with (args.output / "per_job_diagnostics.csv").open("x", encoding="utf-8", newline="") as diagnostics, gzip.open(trace, "rt", encoding="utf-8") as stream:
        writer = csv.DictWriter(diagnostics, fieldnames=per_job_fields)
        writer.writeheader()
        for line in stream:
            record = json.loads(line)
            counts["jobs"] += 1
            counts[record["it_decision"]] += 1
            gate, segments, hit = descriptor(model, record)
            flagged = "DESCRIPTION_SEGMENT_SKIPPED" in record["reason_codes"]
            assert flagged == any(s["skipped"] for s in segments)
            skipped = [s for s in segments if s["skipped"]]
            long_lengths.extend(s["length"] for s in skipped)
            counts["segments"] += len(segments)
            counts["skipped_segments"] += len(skipped)
            counts["normalized_segment_codepoints"] += sum(s["length"] for s in segments)
            counts["skipped_normalized_codepoints"] += sum(s["length"] for s in skipped)
            text = record["description"]
            format_flags = {"lf": "\n" in text, "crlf": "\r\n" in text,
                            "lone_cr": bool(re.search(r"\r(?!\n)", text)),
                            "html_tag": bool(HTML_TAG.search(text)), "html_entity": bool(HTML_ENTITY.search(text)),
                            "literal_backslash_n": r"\n" in text, "unicode_line_separator": "\u2028" in text or "\u2029" in text,
                            "no_lf_or_cr": "\n" not in text and "\r" not in text,
                            "punctuation_without_following_space": bool(re.search(r"[.!?;](?=[A-Za-z])", text))}
            formats.update(k for k, v in format_flags.items() if v)
            if flagged:
                counts["flagged"] += 1
                flag_states[record["it_decision"]] += 1
                formats.update("flagged_" + k for k, v in format_flags.items() if v)
                if record["it_decision"] == "REVIEW":
                    combinations[" + ".join(sorted(record["reason_codes"]))] += 1
                    if set(record["reason_codes"]) == {"DESCRIPTION_SEGMENT_SKIPPED"}:
                        counts["review_due_only_to_skipped_reason"] += 1
            for rule_id in record["matched_rule_ids"]:
                if rule_id in stages:
                    fallback_trace_rules[rule_id] += 1
            active_long, active_long_unblocked = [], []
            if flagged:
                title_value = model.normalize(record["title"])
                for rule in model.config["include_rules"]:
                    if rule["evidence_tier"] != "TITLE_CONTEXT":
                        continue
                    title_set = rule["condition"]["all"][0]["match"]["term_set"]
                    if not model.fast_patterns[title_set].search(title_value):
                        continue
                    sets = rule["condition"]["all"][1]["same_segment"]["all_term_sets"]
                    for segment in skipped:
                        if all(hit(segment, k) for k in sets):
                            active_long.append((rule["id"], segment["index"]))
                            if not segment["blocked"]:
                                active_long_unblocked.append((rule["id"], segment["index"]))
                if active_long:
                    counts["flagged_with_active_context_joint_in_long"] += 1
                if active_long_unblocked:
                    counts["flagged_with_active_context_joint_in_long_unblocked"] += 1
                    if record["it_decision"] == "REVIEW":
                        counts["review_with_active_context_joint_in_long_unblocked"] += 1
            if gate:
                counts["description_title_gate_jobs"] += 1
                generic_titles[model.normalize(record["title"])] += 1
                gate_states[record["it_decision"]] += 1
                if flagged:
                    counts["description_title_gate_flagged"] += 1
                for rule in description_rules:
                    rule_counts = stages[rule["id"]]
                    rule_counts["title_gate_pass"] += 1
                    sets = rule["condition"]["all"][1]["same_segment"]["all_term_sets"]
                    any_hits = [any(hit(s, k) for s in segments) for k in sets]
                    # Inspect the few fallback-eligible jobs with literal task
                    # evidence, including a no-length-flag control. This uses
                    # existing JSON term sets, not hand-selected gold labels.
                    if any(present and key.endswith("_tasks") for key, present in zip(sets, any_hits)):
                        gate_task_records[record["job_id"]] = record
                    for k, present in zip(sets, any_hits):
                        if present:
                            rule_counts["anywhere_" + k] += 1
                    joint = [s for s in segments if all(hit(s, k) for k in sets)]
                    valid = [s for s in joint if not s["skipped"]]
                    unblocked = [s for s in valid if not s["blocked"]]
                    rule_counts["all_four_anywhere"] += all(any_hits)
                    rule_counts["all_four_joint_before_length_or_block"] += bool(joint)
                    rule_counts["all_four_joint_valid_length"] += bool(valid)
                    rule_counts["all_four_joint_valid_unblocked"] += bool(unblocked)
                    rule_counts["all_four_joint_long_unblocked"] += any(s["skipped"] and not s["blocked"] for s in joint)
                    rule_counts["all_four_joint_short_blocked"] += any(not s["skipped"] and s["blocked"] for s in joint)
                    rule_counts["all_four_anywhere_but_not_same_segment"] += all(any_hits) and not joint
                    assert bool(unblocked) == (rule["id"] in record["matched_rule_ids"]), f"Fallback implementation mismatch: {record['job_id']} {rule['id']}"
            writer.writerow(dict(job_id=record["job_id"], it_decision=record["it_decision"], flagged=flagged,
                                 description_codepoints=len(text), segments=len(segments), skipped_segments=len(skipped),
                                 skipped_codepoints=sum(s["length"] for s in skipped), title_gate=gate,
                                 active_context_long_joint=len(active_long), active_context_long_unblocked=len(active_long_unblocked),
                                 has_html_tag=format_flags["html_tag"], has_lf=format_flags["lf"], has_crlf=format_flags["crlf"]))
            if flagged:
                if record["it_decision"] == "REVIEW":
                    if active_long:
                        add_candidate("REVIEW_ACTIVE_CONTEXT_IN_SKIPPED", record)
                    if gate:
                        add_candidate("REVIEW_GENERIC_TITLE", record)
                    if not active_long:
                        add_candidate("REVIEW_NO_ACTIVE_CONTEXT_IN_SKIPPED", record)
                else:
                    add_candidate(record["it_decision"] + "_FLAGGED", record)
                if format_flags["html_tag"]:
                    add_candidate("HTML_FLAGGED", record)
            if counts["jobs"] % 10000 == 0:
                print(f"Diagnosed {counts['jobs']} existing predictions; title gate {counts['description_title_gate_jobs']}", flush=True)
    selected, seen = [], set()
    for category, quota in quotas.items():
        for _, record in pools[category]:
            if record["job_id"] not in seen:
                selected.append(specimen(model, record, category))
                seen.add(record["job_id"])
                quota -= 1
                if quota == 0:
                    break
    assert 10 <= len(selected) <= 20
    write_json(args.output / "real_job_specimens.json", selected, exclusive=True)
    gate_task_examples = [specimen(model, record, "DESCRIPTION_GATE_TASK_EXAMPLE")
                          for _, record in sorted(gate_task_records.items(), key=lambda pair: int(pair[0]))]
    write_json(args.output / "description_gate_task_examples.json", gate_task_examples, exclusive=True)
    lengths = sorted(long_lengths)
    summary = dict(status="DIAGNOSTICS_ONLY_NOT_GOLD_LABELS", date="2026-10-08", output=str(args.output.resolve()),
                   taxonomy_version=model.version, taxonomy_sha256=model.sha256, interpreter_sha256=sha256(ROOT / "src/it_taxonomy_v010.py"),
                   source_trace=str(trace), source_trace_sha256=sha256(trace), counts=dict(counts),
                   flagged_states=dict(flag_states), review_flag_reason_combinations=dict(combinations),
                   input_formats=dict(formats), generic_exact_title_counts=dict(generic_titles), title_gate_states=dict(gate_states),
                   description_rule_stage_counts={k: dict(v) for k, v in stages.items()}, description_rules_matched_in_saved_trace=dict(fallback_trace_rules),
                   long_segment_lengths=dict(min=lengths[0], median=lengths[len(lengths)//2], p90=lengths[int(len(lengths)*.9)], max=lengths[-1]),
                   specimens=[dict(job_id=r["job_id"], title=r["title"], category=r["category"], decision=r["original_prediction"]["it_decision"], title_gate=r["title_gate"], active_long=r["active_context_matches_in_skipped_segments"]) for r in selected],
                   gate_task_example_job_ids=[r["job_id"] for r in gate_task_examples],
                   protected_artifacts_unchanged=snapshot(protected) == before, no_new_predictions=True, manual_labels_untouched=True,
                   fallback_condition_parity_checked_on_all_gate_jobs=True)
    assert summary["protected_artifacts_unchanged"]
    assert counts["flagged"] == 71150 and flag_states["REVIEW"] == 59831
    assert dict((k, counts[k]) for k in ["ACCEPT", "REJECT", "REVIEW"]) == run["decisions"]
    write_json(args.output / "diagnostics_summary.json", summary, exclusive=True)
    write_json(ROOT / "data/audit/tv2_a04_review_diagnostics.json", summary, exclusive=True)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
