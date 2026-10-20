"""Develop A05 on raw descriptions of the 105 manually approved A04 IT jobs.

No membership reclassification, label edits, ETL or full-dataset extraction.
Outputs are exclusive, under data/analytics; official Parquet is a Spark step.
"""
from __future__ import annotations

import argparse
import collections
import html
import importlib.util
import json
import platform
from pathlib import Path

from apply_a04_decisions import read_sheet
from tech_skill_extractor import TechSkillExtractor
from tv2_csv import ROOT, csv_rows, integer_key, sha256, write_csv, write_json

MAIN_LABELS = ROOT / "data/analytics/a04_manual_seed42/a04_manual_labels_filled.xlsx"
EXTRA_LABELS = ROOT / "data/analytics/a04_taxonomy_v0_2_0_20261008/accept_downgrades_for_review_blind.xlsx"
MANUAL_FIELDS = ["manual_label", "manual_is_it", "manual_primary_group_code", "manual_subgroup_code",
                 "manual_reason", "manual_evidence", "reviewer", "reviewed_date"]
BRIDGE_FIELDS = ["job_id", "skill_code", "skill_name", "skill_group", "mention_types", "evidence_count",
                 "evidence_ids", "source_field", "run_id", "dictionary_version", "dictionary_sha256", "extractor_version"]


def approved_a04(main=MAIN_LABELS, extra=EXTRA_LABELS):
    unique, source_counts = {}, []
    for path, sheet, count in [(Path(main), "A04 manual labels", 160), (Path(extra), "Review", 17)]:
        rows = read_sheet(path, sheet)["rows"]
        if len(rows) != count or len({integer_key(row["job_id"]) for row in rows}) != count:
            raise ValueError("A04 source grain/count changed")
        source_counts.append(dict(path=str(path), sheet=sheet, rows=count, sha256=sha256(path),
                                  approved_it_rows=sum(row["manual_label"] == "CNTT" for row in rows)))
        for row in rows:
            job = integer_key(row["job_id"])
            if not job or not all(row[k] != "" for k in ["manual_label", "manual_reason", "manual_evidence", "reviewer", "reviewed_date"]):
                raise ValueError("Missing approved label metadata")
            if row["manual_label"] not in {"CNTT", "NGOAI_CNTT", "CHUA_RO"}:
                raise ValueError("Unknown manual label")
            if row["manual_is_it"] is not {"CNTT": True, "NGOAI_CNTT": False, "CHUA_RO": ""}[row["manual_label"]]:
                # Empty Excel cells are strings; boolean CNTT/non-IT must be real booleans.
                if row["manual_label"] != "CHUA_RO" or row["manual_is_it"] != "":
                    raise ValueError("Manual boolean/label conflict")
            ref = dict(path=str(path), sheet=sheet, excel_row=row["_excel_row"], sample_id=row.get("sample_id"))
            if job in unique:
                old = unique[job]
                if any(old[k] != row[k] for k in [*MANUAL_FIELDS, "title", "description"]):
                    raise ValueError("A04 duplicate source conflict")
                old["source_refs"].append(ref)
            else:
                unique[job] = dict(row, job_id=job, source_refs=[ref])
    if len(unique) != 176:
        raise ValueError("Frozen A04 union must contain 176 keys")
    approved = {job:row for job, row in unique.items() if row["manual_label"] == "CNTT"}
    if len(approved) != 105:
        raise ValueError("Approved A04 IT set changed; review the run scope first")
    return approved, source_counts


def raw_for_jobs(path, expected):
    found, scanned = {}, 0
    for row in csv_rows(path):
        scanned += 1
        job = integer_key(row["job_id"])
        if job not in expected:
            continue
        if job in found:
            raise ValueError("Duplicate selected job_id in raw")
        if any(row[field] != expected[job][field] for field in ["title", "description"]):
            raise ValueError("Raw full text differs from approved A04 source")
        found[job] = row
    if set(found) != set(expected):
        raise ValueError("Approved A04 job missing in raw")
    return found, scanned


def verify_result(model, result, raw):
    pairs = [(row["job_id"], row["skill_code"]) for row in result["job_skills"]]
    if len(pairs) != len(set(pairs)):
        raise AssertionError("Duplicate job-skill")
    evidence = result["evidence"]
    if len(evidence) != len({e["evidence_id"] for e in evidence}):
        raise AssertionError("Duplicate evidence ID")
    for e in evidence:
        if e["mapping_status"] != "MAPPED_TO_RAW":
            if e["accepted"]:
                raise AssertionError("Unmapped accepted evidence")
            continue
        ranges = e["raw_match_ranges"]
        if not ranges or any(not 0 <= a < b <= len(raw) for a, b in ranges):
            raise AssertionError("Invalid raw ranges")
        quote = "".join(raw[a:b] for a, b in ranges)
        if quote != e["matched_text"] or e["excerpt"] != raw[e["raw_excerpt_start"]:e["raw_excerpt_end"]]:
            raise AssertionError("Evidence is not exact raw text")
        if model.normalize(html.unescape(quote)) != model.normalize(e["matched_alias"]):
            raise AssertionError("Alias does not map back to original source")
    for row in result["job_skills"]:
        ev = [e for e in evidence if e["accepted"] and e["skill_code"] == row["skill_code"]]
        if len(ev) != row["evidence_count"] or [e["evidence_id"] for e in ev] != row["evidence_ids"]:
            raise AssertionError("Lost evidence during deduplication")


def write_jsonl(path, records):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        for row in records:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def csv_value(value):
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) or value is None else value


def write_outputs(output, model, inputs, results):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    jobs = sorted(inputs, key=int)
    bridge = [row for job in jobs for row in results[job]["job_skills"]]
    evidence = [row for job in jobs for row in results[job]["evidence"]]
    states = [results[job]["processing"] for job in jobs]
    write_csv(output/"job_skill_technical.csv", [{k:csv_value(row[k]) for k in BRIDGE_FIELDS} for row in bridge], BRIDGE_FIELDS, exclusive=True)
    write_jsonl(output/"technical_skill_evidence.jsonl", evidence)
    write_jsonl(output/"skill_source_processing.jsonl", states)
    review = [dict(job_id=e["job_id"], title=inputs[e["job_id"]]["title"], skill_code=e["skill_code"],
                   skill_name=e["skill_name"], mention_type=e["mention_type"], accepted=e["accepted"],
                   matched_alias=e["matched_alias"], matched_text=e["matched_text"], excerpt=e["excerpt"],
                   raw_match_ranges=json.dumps(e["raw_match_ranges"]), rule_id=e["rule_id"],
                   manual_review_decision="", manual_review_note="") for e in evidence]
    fields = ["job_id", "title", "skill_code", "skill_name", "mention_type", "accepted", "matched_alias",
              "matched_text", "excerpt", "raw_match_ranges", "rule_id", "manual_review_decision", "manual_review_note"]
    write_csv(output/"review_skill_sample.csv", review, fields, exclusive=True, bom=True)
    review_jobs = [dict(job_id=job, title=inputs[job]["title"], source_status=results[job]["processing"]["source_status"],
                       technical_skills=json.dumps(results[job]["processing"]["technical_skills"]),
                       review_required=results[job]["processing"]["review_required"]) for job in jobs]
    write_csv(output/"review_jobs.csv", review_jobs, list(review_jobs[0]) if review_jobs else ["job_id","title","source_status","technical_skills","review_required"], exclusive=True, bom=True)
    coverage = []
    for code, skill in model.skills.items():
        mentions = [e for e in evidence if e["skill_code"] == code]
        accepted = [e for e in mentions if e["accepted"]]
        example = next(iter(accepted or mentions), None)
        coverage.append(dict(skill_code=code, skill_name=skill["name"], skill_group=skill["group"],
                             distinct_jobs_with_literal=len({e["job_id"] for e in mentions}),
                             distinct_jobs_with_accepted_skill=len({e["job_id"] for e in accepted}),
                             example_job_id=example["job_id"] if example else "",
                             example_alias=example["matched_alias"] if example else "",
                             example_raw_ranges=json.dumps(example["raw_match_ranges"]) if example else ""))
    write_csv(output/"dictionary_coverage.csv", coverage, list(coverage[0]), exclusive=True)
    good = [s for s in states if s["source_status"] in {"PROCESSED_WITH_MATCH", "PROCESSED_NO_MATCH"}]
    return dict(input_jobs=len(jobs), processed_successfully=len(good),
                jobs_with_skills=len({row["job_id"] for row in bridge}), job_skill_rows=len(bridge),
                unique_job_skill_pairs=len({(row["job_id"],row["skill_code"]) for row in bridge}),
                evidence_rows=len(evidence), accepted_evidence_rows=sum(e["accepted"] for e in evidence),
                mention_type_counts=dict(collections.Counter(e["mention_type"] for e in evidence)),
                source_status_counts=dict(collections.Counter(s["source_status"] for s in states)),
                jobs_needing_review=sum(s["review_required"] for s in states),
                dictionary_skills=len(model.skills), skills_seen_in_descriptions=sum(c["distinct_jobs_with_literal"]>0 for c in coverage),
                skills_with_accepted_evidence=sum(c["distinct_jobs_with_accepted_skill"]>0 for c in coverage),
                distinct_job_counts_by_skill={c["skill_code"]:c["distinct_jobs_with_accepted_skill"] for c in coverage},
                processing_coverage=dict(numerator=len(good),denominator=len(jobs)),
                long_units_retained=sum(s["long_units_retained"] for s in states),
                dropped_oversize_units=sum(s["dropped_oversize_units"] for s in states),
                metrics_are_accuracy=False, skill_gold_labels_available=False)


def run(args):
    output = Path(args.output).resolve()
    if not output.is_relative_to((ROOT/"data/analytics").resolve()) or output == (ROOT/"data/analytics").resolve() or output.exists():
        raise ValueError("Choose a new output directory inside data/analytics")
    raw, config = Path(args.raw).resolve(), Path(args.config).resolve()
    approved, sources = approved_a04()
    before = {str(p):sha256(p) for p in [raw, config, MAIN_LABELS, EXTRA_LABELS, ROOT/"config/it_taxonomy.json"]}
    inputs, scanned = raw_for_jobs(raw, approved)
    model = TechSkillExtractor(config)
    results = {}
    for job, row in inputs.items():
        results[job] = model.extract(row["description"], job, run_id=output.name)
        verify_result(model, results[job], row["description"])
    if any(sha256(Path(p)) != h for p,h in before.items()):
        raise AssertionError("A protected input changed during the run")
    summary = write_outputs(output, model, inputs, results)
    write_json(output/"input_manifest.json", dict(source="raw postings.description; selection from manually approved A04 labels",
        raw_file=str(raw), raw_sha256=before[str(raw)], raw_rows_scanned_for_selection=scanned,
        descriptions_extracted=len(inputs), labels=sources, a04_source_rows=177, a04_unique_jobs=176,
        approved_it_unique_jobs=105, excluded_non_it=67, excluded_chua_ro=4,
        overlap_job_id="3905848702", selection_uses_machine_decision=False,
        jobs=[dict(job_id=j, source_refs=approved[j]["source_refs"]) for j in sorted(inputs,key=int)]), exclusive=True)
    write_json(output/"summary.json", summary, exclusive=True)
    manifest = dict(status="DEVELOPMENT_COMPLETE_PENDING_OFFICIAL_INPUT_AND_SPARK",
        run_id=output.name, dictionary_version=model.version, dictionary_sha256=model.sha256,
        dictionary_config=str(config), extractor_version=results[next(iter(results))]["processing"]["extractor_version"],
        python=platform.python_version(), pyspark_installed=importlib.util.find_spec("pyspark") is not None,
        spark_executed=False, official_parquet_created=False, full_dataset_extraction=False, etl_rerun=False,
        skills_desc_enabled=False, source_function_labels_used_as_technology=False,
        canonical_input_present=False, a04_candidate_promoted=False,
        active_taxonomy_sha256=before[str(ROOT/"config/it_taxonomy.json")],
        implementation_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha256(p) for p in [
            ROOT/"src/tech_skill_extractor.py", ROOT/"src/prepare_a05.py", ROOT/"src/a05_spark.py",
            ROOT/"src/test_a05_skills.py", ROOT/"src/description_processing.py", ROOT/"src/tv2_csv.py", ROOT/"src/apply_a04_decisions.py"]},
        input_hashes_unchanged=True, output_sha256={p.name:sha256(p) for p in output.iterdir() if p.is_file()})
    write_json(output/"run_manifest.json", manifest, exclusive=True)
    print(json.dumps(dict(output=str(output), **summary),ensure_ascii=False,indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw",default=ROOT/"data/raw/postings.csv")
    parser.add_argument("--config",default=ROOT/"config/tech_skills.json")
    parser.add_argument("--output",required=True)
    run(parser.parse_args())
