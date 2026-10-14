"""Validate persisted v0.2 trace and add private predictions for frozen seed42.

No classification rerun, edits to raw/labels, or quality metrics. Refuses existing
new artifact paths; provenance includes the exact completed comparison run.
"""
import collections
import gzip
import json
import subprocess
import sys
from pathlib import Path

from compare_a04_versions import inventory, validate_evidence
from it_taxonomy import Taxonomy
from prepare_a04 import MANUAL_FIELDS
from tv2_csv import ROOT, csv_rows, sha256, write_csv, write_json


def main():
    output = ROOT / "data/analytics/a04_taxonomy_v0_2_0_20261008"
    audit = ROOT / "data/audit/tv2_a04_v020_validation.json"
    private = output / "seed42_v020_predictions_private.jsonl"
    if audit.exists():
        raise FileExistsError("Validation summary already exists; do not replace it")
    summary = json.loads((output / "comparison_summary.json").read_text(encoding="utf-8"))
    protected = json.loads((output / "protected_before.json").read_text(encoding="utf-8"))
    assert inventory([ROOT / path for path in protected]) == protected
    trace = output / "all_predictions.jsonl.gz"
    assert sha256(trace) == summary["new_trace_sha256"]
    assert sha256(ROOT / "config/it_taxonomy.json") == summary["taxonomy_sha256"]
    assert (output / "it_taxonomy_v0.2.0.json").read_bytes() == (ROOT / "config/it_taxonomy.json").read_bytes()
    for filename, checksum in summary["implementation_sha256"].items():
        assert sha256(output / "implementation" / filename) == checksum
        assert sha256(ROOT / "src" / filename) == checksum
    model = Taxonomy(output / "it_taxonomy_v0.2.0.json")
    old_blind = list(csv_rows(ROOT / "data/analytics/a04_manual_seed42/a04_manual_labels_blind.csv"))
    reading = list(csv_rows(output / "changed_cases_for_review_blind.csv"))
    seed_ids = {r["job_id"]: r for r in old_blind}
    review_ids = {r["job_id"]: r for r in reading}
    private_rows = [json.loads(line) for line in (output / "changed_case_predictions_private.jsonl").read_text(encoding="utf-8").splitlines()]
    assert set(review_ids) == {r["job_id"] for r in private_rows}
    assert all(not row[key].strip() for row in reading for key in row if key.startswith("manual_") or key in {"reviewer", "reviewed_date"})
    comparison = list(csv_rows(output / "job_comparison.csv"))
    downgrade_ids = {r["job_id"] for r in comparison if r["old_decision"] == "ACCEPT" and r["new_decision"] != "ACCEPT"}
    counts, ids, processing, seed_records, downgrade_records = collections.Counter(), set(), collections.Counter(), {}, {}
    evidence = 0
    with gzip.open(trace, "rt", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            job = record["job_id"]
            assert job not in ids and record["taxonomy_sha256"] == model.sha256
            ids.add(job)
            counts[record["it_decision"]] += 1
            assert (record["primary_group_code"] is not None) == (record["it_decision"] == "ACCEPT")
            evidence += validate_evidence(model, record)
            for key in ["legacy_oversize_units_total", "legacy_oversize_units_processed", "legacy_oversize_units_unresolved", "units", "retained_long_units", "unresolved_units", "dropped_oversize_units"]:
                processing[key] += record["description_processing"][key]
            for pool in [seed_ids, review_ids]:
                if job in pool:
                    assert (record["title"], record["description"]) == (pool[job]["title"], pool[job]["description"])
            if job in seed_ids:
                seed_records[job] = record
            if job in downgrade_ids:
                downgrade_records[job] = record
    assert len(ids) == 123849 and dict(counts) == summary["new_decisions"]
    assert len(seed_records) == len(seed_ids) == 160
    assert evidence == summary["evidence_validated_against_raw"]
    assert all(processing[k] == summary["description_processing"][k] for k in processing)
    assert len(comparison) == len(ids) and {row["job_id"] for row in comparison} == ids
    transitions = collections.Counter(row["old_decision"] + "->" + row["new_decision"] for row in comparison)
    for old, next_counts in summary["transitions"].items():
        for new, count in next_counts.items():
            assert transitions[old + "->" + new] == count
    test = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "src", "-p", "test*a04*.py", "-v"], cwd=ROOT, capture_output=True, text=True)
    if test.returncode:
        raise AssertionError(test.stdout + test.stderr)
    assert "Ran 30 tests" in test.stderr and test.stderr.rstrip().endswith("OK")
    assert inventory([ROOT / path for path in protected]) == protected
    body = "".join(json.dumps(dict(sample_id=row["sample_id"], **seed_records[row["job_id"]]), ensure_ascii=False) + "\n" for row in old_blind)
    if private.exists():
        # An interrupted validation may already have written this new file.
        # Reuse only an exact match; never overwrite a different artifact.
        assert private.read_text(encoding="utf-8") == body
    else:
        with private.open("x", encoding="utf-8") as stream:
            stream.write(body)
    assert len(downgrade_records) == len(downgrade_ids) == 17
    downgrade_blind = output / "accept_downgrades_for_review_blind.csv"
    downgrade_private = output / "accept_downgrade_predictions_private.jsonl"
    blank_rows = [dict(job_id=job, title=downgrade_records[job]["title"], description=downgrade_records[job]["description"],
                       **{key: "" for key in MANUAL_FIELDS}) for job in sorted(downgrade_ids, key=int)]
    if downgrade_blind.exists():
        assert list(csv_rows(downgrade_blind)) == blank_rows
    else:
        write_csv(downgrade_blind, blank_rows, list(blank_rows[0]), exclusive=True, bom=True)
    old_by_id = {r["job_id"]: r for r in comparison if r["job_id"] in downgrade_ids}
    downgrade_body = "".join(json.dumps(dict(job_id=job, old_comparison=old_by_id[job], new_prediction=downgrade_records[job]), ensure_ascii=False) + "\n" for job in sorted(downgrade_ids, key=int))
    if downgrade_private.exists():
        assert downgrade_private.read_text(encoding="utf-8") == downgrade_body
    else:
        with downgrade_private.open("x", encoding="utf-8") as stream:
            stream.write(downgrade_body)
    assert subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() == "feat/tv2-analysis"
    assert not subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT, text=True).strip()
    assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True).strip()
    generated = [p.relative_to(ROOT).as_posix() for p in output.rglob("*") if p.is_file()]
    ignored = subprocess.run(["git", "check-ignore", "--stdin", "-z"], cwd=ROOT,
                             input=b"\0".join(path.encode("utf-8") for path in generated) + b"\0", capture_output=True, check=True)
    assert set(ignored.stdout.decode("utf-8").rstrip("\0").split("\0")) == set(generated)
    value = dict(status="PERSISTED_TRACE_VALIDATED_NOT_EVALUATED", date="2026-10-08", rows=len(ids), distinct_job_ids=len(ids),
                 new_decisions=dict(counts), trace_sha256=summary["new_trace_sha256"], taxonomy_sha256=model.sha256,
                 evidence_revalidated_from_persisted_trace=evidence, processing_totals=dict(processing),
                 transitions_revalidated=True, trace_gzip_read_to_eof=True, protected_artifacts_unchanged=True,
                 protected_artifacts_checked=len(protected), seed42_unchanged=True, seed42_private_predictions_rows=len(seed_records),
                 seed42_private_predictions_file=str(private.resolve()), seed42_private_predictions_sha256=sha256(private),
                 changed_reading_rows=len(reading), changed_reading_full_text_equals_trace=True, changed_manual_fields_blank=True,
                 all_accept_downgrades_exported=17, accept_downgrade_job_ids=sorted(downgrade_ids, key=int),
                 additional_development_exclusion_ids=sorted(downgrade_ids - set(summary["changed_case_review"]["development_job_ids"]), key=int),
                 tests=dict(passed=30, failed=0, illustrative_cases_each_version=57), generated_files_ignored=len(generated),
                 metrics="NOT_COMPUTED_NO_MANUAL_LABELS", spark_jvm_parity="NOT_VERIFIED", tracked_files_unchanged=True,
                 validation_script_sha256=sha256(Path(__file__)))
    write_json(audit, value, exclusive=True)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
