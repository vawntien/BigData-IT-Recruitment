"""Reconcile existing proposed workbook with frozen A05 evidence, read-only.

No extraction, approval, dictionary edit or publication of proposed decisions.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

from apply_a04_decisions import read_sheet
from tv2_csv import ROOT, csv_rows, integer_key, sha256, write_csv, write_json


def reconcile(rows, evidence):
    index = {e["evidence_id"]: e for e in evidence}
    if len(index) != len(evidence):
        raise ValueError("Duplicate frozen evidence_id")
    seen, errors, decisions = set(), [], collections.Counter()
    reviewer_count = date_count = 0
    for row in rows:
        key = row["evidence_id"]
        if key in seen:
            raise ValueError("Duplicate workbook evidence_id")
        seen.add(key)
        e = index.get(key)
        reviewer_count += bool(row.get("Người duyệt"))
        date_count += bool(row.get("Ngày duyệt"))
        decisions[row["Quyết định đề nghị"]] += 1
        if e is None:
            errors.append(dict(evidence_id=key, field="evidence_id", issue="NOT_IN_FROZEN_SOURCE"))
            continue
        checks = {"job_id":integer_key(str(row["job_id"])) == e["job_id"],
                  "Skill nguồn":row["Skill nguồn"] == e["skill_code"],
                  "Loại nguồn":row["Loại nguồn"] == e["mention_type"],
                  "Máy nhận":row["Máy nhận"] is e["accepted"],
                  "Matched text nguồn":row["Matched text nguồn"] == (e["matched_text"] or ""),
                  "Raw ranges nguồn":json.loads(row["Raw ranges nguồn"]) == e["raw_match_ranges"],
                  "Quote nguyên văn":row["Quote nguyên văn"] == (e["excerpt"] or "")}
        errors.extend(dict(evidence_id=key, field=field, issue="SOURCE_MISMATCH") for field, ok in checks.items() if not ok)
    return dict(rows=len(rows), source_evidence=len(evidence), missing_ids=sorted(set(index)-seen),
                source_mismatches=errors, proposal_counts=dict(decisions), reviewer_nonempty=reviewer_count,
                approval_date_nonempty=date_count, decisions_applied=False,
                status="PROPOSED_NOT_APPROVED" if not reviewer_count and not date_count else "REQUIRES_HUMAN_CONFIRMATION")


def run(workbook, output):
    workbook, output = Path(workbook), Path(output)
    if output.exists() or not output.resolve().is_relative_to(ROOT):
        raise ValueError("Choose a new repository audit directory")
    source = ROOT/"data/analytics/a05_development_v0_1_2_20261014"
    paths = [workbook, ROOT/"data/raw/postings.csv", ROOT/"config/tech_skills.json",
             source/"technical_skill_evidence.jsonl",source/"skill_source_processing.jsonl",source/"job_skill_technical.csv"]
    before = {str(p):sha256(p) for p in paths}
    rows = read_sheet(workbook,"Review 661 evidence")["rows"]
    additions = read_sheet(workbook,"Bo sot de nghi")["rows"]
    evidence = [json.loads(line) for line in (source/"technical_skill_evidence.jsonl").read_text(encoding="utf-8").splitlines()]
    states = {r["job_id"]:r for r in [json.loads(line) for line in (source/"skill_source_processing.jsonl").read_text(encoding="utf-8").splitlines()]}
    result = reconcile(rows,evidence)
    wanted = {e["job_id"] for e in evidence} | {integer_key(str(r["job_id"])) for r in additions}
    raw = {integer_key(r["job_id"]):r for r in csv_rows(ROOT/"data/raw/postings.csv") if integer_key(r["job_id"]) in wanted}
    raw_errors=[]
    import hashlib
    for job in wanted:
        if job not in raw:raise ValueError("Workbook job missing in raw")
        if hashlib.sha256(raw[job]["description"].encode()).hexdigest()!=states[job]["source_text_sha256"]:
            raise ValueError("Frozen A05 source hash differs from raw")
    for e in evidence:
        text=raw[e["job_id"]]["description"]
        if e["mapping_status"]=="MAPPED_TO_RAW":
            if text[e["raw_excerpt_start"]:e["raw_excerpt_end"]]!=e["excerpt"] or "".join(text[a:b] for a,b in e["raw_match_ranges"])!=e["matched_text"]:
                raw_errors.append(e["evidence_id"])
    codes={s["code"] for s in json.loads((ROOT/"config/tech_skills.json").read_text(encoding="utf-8"))["skills"]}
    additional_checks=[]
    for row in additions:
        job=integer_key(str(row["job_id"])); text=raw[job]["description"]
        a,b=int(row["Raw start"]),int(row["Raw end"])
        additional_checks.append(dict(job_id=job,skill_code=row["Skill đề nghị"],alias=row["Alias"],
            source_quote_found=row["Quote nguồn"] in text,raw_range_matches_alias=0<=a<b<=len(text) and text[a:b]==row["Alias"],
            dictionary_code_exists=row["Skill đề nghị"] in codes,reviewer_empty=not row["Người duyệt"],
            approval_date_empty=not row["Ngày duyệt"],status="PROPOSED_NOT_APPLIED",raw_start=a,raw_end=b))
    output.mkdir(parents=True,exist_ok=False)
    result.update(workbook=str(workbook.resolve()),workbook_sha256=before[str(workbook)],
        workbook_requested_name_present=(workbook.parent/"a05_skill_review_decisions.xlsx").exists(),
        dictionary_version="0.1.2",dictionary_sha256=sha256(ROOT/"config/tech_skills.json"),
        frozen_job_skill_rows=len(list(csv_rows(source/"job_skill_technical.csv"))),
        raw_jobs_checked=len(raw),raw_evidence_errors=raw_errors,additional_proposals=additional_checks,
        extractor_executed=False,taxonomy_executed=False,skill_gold_labels_created=False)
    result["source_validation_passed"]=not result["source_mismatches"] and not result["missing_ids"] and not raw_errors
    assert all(sha256(Path(p))==h for p,h in before.items()),"Protected input changed"
    result["protected_inputs_unchanged"]=True
    write_json(output/"review_audit.json",result,exclusive=True)
    queue=[dict(evidence_id=r["evidence_id"],job_id=r["job_id"],proposal=r["Quyết định đề nghị"],
                proposed_skill=r["Skill đề nghị"],proposed_type=r["Loại đề nghị"],reason=r["Lý do"],
                reviewer=r["Người duyệt"],reviewed_date=r["Ngày duyệt"],status="PROPOSAL_ONLY_NOT_APPLIED") for r in rows]
    write_csv(output/"existing_review_queue.csv",queue,list(queue[0]),exclusive=True,bom=True)
    write_csv(output/"additional_proposal_checks.csv",additional_checks,list(additional_checks[0]),exclusive=True,bom=True)
    print(json.dumps({k:result[k] for k in ["status","rows","proposal_counts","source_validation_passed","raw_jobs_checked","frozen_job_skill_rows"]},ensure_ascii=False))
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workbook",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();sys.stdout.reconfigure(encoding="utf-8");run(a.workbook,a.output)
