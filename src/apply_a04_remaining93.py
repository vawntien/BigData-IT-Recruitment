"""Apply the authorized remaining 93 A04 decisions; never run ETL/classification.

Default: back up both workbooks and reports, check job_id/source/evidence and
save a plan. --apply: recheck inputs, validate a staged workbook before replacing
it, recompute separate 160/17 comparisons from saved v0.2.0 predictions.
Only the 'Chot 93 tin' sheet is read; XLSX metric/formula results are not used.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import re
import shutil
import sys
import zipfile

import apply_a04_decisions as base

ROOT = base.ROOT
RUN = ROOT / "data/analytics/a04_apply_remaining93_20261013"
DECISION = "docs/a04_remaining93_chot.xlsx"
PROPOSAL = "docs/a04_review_decisions_remaining93.csv"
AUDIT = "data/audit/tv2_a04_remaining93_applied_20261013.json"
REPORTS = base.REPORTS + ["docs/a04_completion_criteria.md", "docs/a04_remaining93_review_summary.md"]
SEED, DOWN, SOURCES, MANUAL = base.SEED, base.DOWN, base.SOURCES, base.MANUAL
DATE, REVIEWER = base.DATE, base.REVIEWER
sha, dump, keyed, read_csv, write_csv = base.sha, base.dump, base.keyed, base.read_csv, base.write_csv
# The helper's inventory must exclude this run's backup/audit directory.
base.RUN = RUN


def sources():
    info = {rel: base.read_sheet(ROOT / rel, sheet) for rel, (sheet, _) in SOURCES.items()}
    rows = {rel: keyed(data["rows"]) for rel, data in info.items()}
    for rel, (_, count) in SOURCES.items():
        assert len(rows[rel]) == count and not info[rel]["formulas"]
    assert len({r["sample_id"] for r in rows[SEED].values()}) == 160
    assert len(set(rows[SEED]) | set(rows[DOWN])) == 176
    shared = set(rows[SEED]) & set(rows[DOWN])
    assert shared == {"3905848702"}
    assert all(all(rows[SEED][j][f] == rows[DOWN][j][f] for f in MANUAL) for j in shared)
    return info, rows


def evidence_parts(value):
    match = re.fullmatch(r"(title|description):\s*(.+)", value, re.S)
    if match:
        return [(match[1], match[2])]
    numbered = re.findall(r"(?:^|\n\s*\n)\[(\d+)\]\s*(.*?)(?=\n\s*\n\[\d+\]|\Z)", value, re.S)
    if numbered:
        assert [int(n) for n, _ in numbered] == list(range(1, len(numbered) + 1))
        rendered = "\n\n".join(f"[{n}] {q}" for n, q in numbered)
        assert rendered == value, "Evidence cannot be silently reformatted"
        return [("description", q) for _, q in numbered]
    raise ValueError("Evidence needs an explicit field or numbered verbatim quotes")


CONTEXT_NOTES = {
    "A04-044": "Evidence là qualification về sourcing trong sản xuất; title xác định nghề mua sắm, không gọi qualification là task IT.",
    "A04-049": "Description chỉ có lương/lịch/địa điểm; evidence dùng title Ultrasound Tech, ghi rõ giới hạn.",
    "A04-063": "Task R&D data analytics và control có thật; chốt DATA_AI theo yêu cầu, không gọi machine learning trong qualification là task được giao.",
    "A04-082": "Description xác nhận tên vị trí bác sĩ, không có đầy đủ nhiệm vụ; căn cứ nghề là title/profile tuyển dụng.",
    "A04-106": "Evidence là yêu cầu kinh nghiệm heavy civil/marine construction, nhất quán title; không suy task phần mềm.",
    "A04-114": "Giữ nguyên prefix TechnicalExperience: data solutions là qualification, phù hợp title Data Engineer, không diễn giải thành task được giao.",
    "A04-117": "Toàn description 173 ký tự là profile React/HubSpot, chưa có task; title Frontend Developer làm căn cứ nhóm Web.",
    "A04-124": "Responsibilities trực tiếp giao quản lý 25–30 technicians/SLA/ca trực/đào tạo; áp dụng IT_MANAGEMENT theo quyết định đã chốt dù title frontline.",
    "A04-144": "Phân biệt Top Requirements với task phối hợp pentest, kiểm chứng kết quả và chuyển findings thành thay đổi hệ thống.",
    "A04-147": "Title Web trực tiếp và task frontend code phù hợp; ưu tiên title Web hơn Mobile trong description theo A02, không thêm điều kiện native.",
}


def preflight():
    info, rows = sources()
    proposal = keyed(read_csv(ROOT / PROPOSAL)[0])
    decision_info = base.read_sheet(ROOT / DECISION, "Chot 93 tin", 6)
    h = decision_info["headers"]
    expected_headers = {"C": "job_id", "H": "Nhãn chốt", "I": "Nhóm / phân nhóm chốt",
                        "J": "Lý do chốt", "K": "Bằng chứng chốt"}
    assert all(h[k] == v for k, v in expected_headers.items()) and not decision_info["formulas"]
    decisions = keyed(decision_info["rows"])
    old_decisions = keyed(base.read_sheet(ROOT / base.DECISION, "Quyet dinh A04", 6)["rows"])
    assert len(decisions) == len(proposal) == 93 and set(decisions) == set(proposal)
    assert len(old_decisions) == 83 and set(decisions).isdisjoint(old_decisions)
    assert set(decisions) | set(old_decisions) == set(rows[SEED]) | set(rows[DOWN])
    missing_before = {r["job_id"] for r in read_csv(RUN / "reports_before/a04_missing_review_metadata.csv")[0]}
    assert set(decisions) == missing_before
    assert all(rows[SEED][j]["reviewer"] == REVIEWER and rows[SEED][j]["reviewed_date"] == DATE
               for j in old_decisions if j in rows[SEED])
    assert all(r["reviewer"] == REVIEWER and r["reviewed_date"] == DATE for r in rows[DOWN].values())
    assert len([r for r in rows[SEED].values() if r["manual_label"] == "CHUA_RO"]) == 4
    pred, _ = base.predictions()
    assert set(pred) == set(rows[SEED]) | set(rows[DOWN])
    blind = {SEED: keyed(read_csv(ROOT / "data/analytics/a04_manual_seed42/a04_manual_labels_blind.csv")[0]),
             DOWN: keyed(read_csv(ROOT / (base.BASE + "accept_downgrades_for_review_blind.csv"))[0])}
    raw = {}
    with (ROOT / "data/raw/postings.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            job = base.canonical(row["job_id"])
            if job in pred:
                assert job not in raw
                raw[job] = {f: row[f] for f in ["title", "description"]}
    assert set(raw) == set(pred)
    manifest = json.loads((ROOT / "data/analytics/a04_manual_seed42/run_manifest.json").read_text(encoding="utf-8"))
    raw_hash_errors = [p for p, v in manifest["raw_files"].items() if sha(ROOT / "data/raw" / p) != v["sha256"]]
    assert len(manifest["raw_files"]) == len(list((ROOT / "data/raw").rglob("*.csv"))) == 11
    assert not raw_hash_errors
    taxonomy = json.loads((ROOT / "config/it_taxonomy.json").read_text(encoding="utf-8"))
    groups = {g["code"] for g in taxonomy["groups"]}
    subgroups = {g["code"] for g in taxonomy["subgroups"]}
    plan, issues, unchanged_errors = {}, [], []
    for job, d in decisions.items():
        r, p = rows[SEED][job], proposal[job]
        problems = []
        def check(ok, code, detail):
            if not ok:
                problems.append(dict(code=code, detail=detail))
        check(job not in rows[DOWN], "UNEXPECTED_SOURCE", "93 ca phải thuộc mẫu chính, không giao mẫu bổ sung")
        check(p["source"] == SEED and p["source_sheet"] == SOURCES[SEED][0], "PROPOSAL_SOURCE", "Nguồn/sheet khác bảng đề nghị")
        check(r["sample_id"] == d["sample_id"] == p["sample_id"], "SOURCE_SAMPLE_ID", "Sample id khác snapshot; job_id vẫn là khóa JOIN")
        check(r["title"] == d[h["D"]] == p["title"], "SOURCE_TITLE", "Title nguồn khác bảng chốt/đề nghị")
        for f in ["title", "description"]:
            check(base.text_sha(r[f]) == p[f + "_sha256"], "SOURCE_HASH", f"{f} khác hash bảng đề nghị")
            check(r[f] == blind[SEED][job][f] == pred[job][f] == raw[job][f], "SOURCE_TEXT", f"{f} khác blind/dự đoán/raw của đúng job_id")
        for f in MANUAL:
            a, b = r[f], p["current_" + f]
            if f == "manual_is_it":
                a, b = base.boolean(a), base.boolean(b)
            check(a == b, "SOURCE_ANNOTATION", f"{f} khác snapshot bảng đề nghị")
        current_group = " / ".join(x for x in [r["manual_primary_group_code"], r["manual_subgroup_code"]] if x)
        check(d[h["E"]] == r["manual_label"] and d[h["F"]] == current_group, "DECISION_CURRENT", "Nhãn/nhóm hiện tại khác bảng chốt")
        check(d[h["N"]] == REVIEWER and d[h["O"]].startswith(DATE), "DECISION_METADATA", "Người/ngày duyệt khác yêu cầu")
        label, grouping = d[h["H"]], d[h["I"]]
        parts = grouping.split(" / ") if grouping else []
        group, subgroup = (parts + ["", ""])[:2]
        check(label in {"CNTT", "NGOAI_CNTT", "CHUA_RO"}, "LABEL_ENUM", repr(label))
        check(len(parts) <= 2 and all(x == x.strip() and x for x in parts), "GROUP_FORMAT", repr(grouping))
        check(group in groups and (subgroup in subgroups if group == "SOFTWARE" else not subgroup)
              if label == "CNTT" else not parts, "GROUP_SCHEMA", repr(grouping))
        check(bool(d[h["J"]].strip()), "REASON_EMPTY", "Cột J trống")
        found = []
        try:
            for f, q in evidence_parts(d[h["K"]]):
                start = r[f].find(q)
                check(bool(q) and start >= 0, "EVIDENCE_NOT_VERBATIM", f"Cột K không khớp {f} của đúng job_id: {q!r}")
                if start >= 0:
                    found.append(dict(field=f, start=start, end=start + len(q), quote=q,
                                      context=r[f][max(0, start-220):start+len(q)+220]))
        except (AssertionError, ValueError) as error:
            problems.append(dict(code="EVIDENCE_FORMAT", detail=str(error)))
        # Independently verify the proposal's longer quotes and field-specific offsets.
        quotes, offsets = json.loads(p["evidence_quotes_json"]), json.loads(p["evidence_offsets_json"])
        check(len(quotes) == len(offsets) and bool(quotes), "PROPOSAL_QUOTES", "Quotes/offsets thiếu")
        for q, offset in zip(quotes, offsets):
            f, start, end = offset["field"], offset["start"], offset["end"]
            check(f in {"title", "description"} and r[f][start:end] == q, "PROPOSAL_EVIDENCE", "Quote/offset đề nghị khác nguồn")
        check(p["machine_decision"] == pred[job]["it_decision"] and p["taxonomy_version"] == "0.2.0"
              and p["taxonomy_sha256"] == pred[job]["taxonomy_sha256"], "PREDICTION_PROVENANCE", "Bảng đề nghị khác dự đoán đã lưu")
        if problems:
            issues.append(dict(job_id=job, sample_id=r["sample_id"], title=r["title"], problems=problems))
            continue
        values = dict(manual_label=label, manual_is_it={"CNTT": True, "NGOAI_CNTT": False, "CHUA_RO": ""}[label],
                      manual_primary_group_code=group, manual_subgroup_code=subgroup,
                      manual_reason=d[h["J"]], manual_evidence=d[h["K"]], reviewer=REVIEWER, reviewed_date=DATE)
        plan[job] = dict(job_id=job, sources=[SEED], sample_id=r["sample_id"], values=values,
                         evidence=found, context_review=CONTEXT_NOTES.get(r["sample_id"],
                         "Đã đối chiếu title, lý do chốt và ngữ cảnh quanh từng quote: phù hợp nghề của vị trí; không lấy nhắc công nghệ/công ty làm nghề IT."),
                         changed_fields=[f for f in MANUAL if r[f] != values[f]],
                         changed_core_fields=[f for f in base.CORE if r[f] != values[f]])
    for rel, data in rows.items():
        for job, row in data.items():
            if job in decisions:
                continue
            for f in ["title", "description"]:
                if row[f] != blind[rel][job][f] or row[f] != raw[job][f] or row[f] != pred[job][f]:
                    unchanged_errors.append(dict(job_id=job, source=rel, field=f))
    if "3904568619" in plan:
        assert base.core(plan["3904568619"]["values"]) == ("CNTT", True, "DATA_AI", "")
    if "3884430597" in plan:
        assert base.core(plan["3884430597"]["values"]) == ("CNTT", True, "IT_MANAGEMENT", "")
    return dict(plan=plan, issues=issues, source_info=info, preserved_jobs=sorted(old_decisions, key=int),
                raw_hashes_verified=11, nondecision_source_errors=unchanged_errors)


def prepare():
    state = base.git_state()
    assert state["branch"] == "feat/tv2-analysis"
    RUN.mkdir(exist_ok=False)
    (RUN / "backups").mkdir()
    (RUN / "reports_before").mkdir()
    backups = {}
    for rel in SOURCES:
        target = RUN / "backups" / os.path.basename(rel)
        shutil.copy2(ROOT / rel, target)
        assert sha(target) == sha(ROOT / rel)
        backups[rel] = dict(path=target.relative_to(ROOT).as_posix(), sha256=sha(target))
    for rel in REPORTS:
        shutil.copy2(ROOT / rel, RUN / "reports_before" / os.path.basename(rel))
    dump(RUN / "backup_manifest.json", backups)
    dump(RUN / "git_before.json", state)
    print("Backups verified; checking source text and job_id decisions...", flush=True)
    before = base.inventory()
    dump(RUN / "protected_before.json", before)
    checked = preflight()
    dump(RUN / "checked_plan.json", {k: v for k, v in checked.items() if k != "source_info"})
    assert base.inventory() == before
    print(json.dumps(dict(eligible_jobs=len(checked["plan"]), skipped_cases=checked["issues"],
                          evidence_quotes=sum(len(p["evidence"]) for p in checked["plan"].values()),
                          changed_core_jobs={j: p["changed_core_fields"] for j, p in checked["plan"].items() if p["changed_core_fields"]},
                          nondecision_source_errors=checked["nondecision_source_errors"]), ensure_ascii=False, indent=2))


def fraction(numerator, denominator):
    return dict(numerator=numerator, denominator=denominator,
                rate=numerator/denominator if denominator else None)


def sample_metrics(data, pred):
    matrix = {d: {l: sum(pred[j]["it_decision"] == d and r["manual_label"] == l for j, r in data.items())
                  for l in ["CNTT", "NGOAI_CNTT", "CHUA_RO"]} for d in ["ACCEPT", "REJECT", "REVIEW"]}
    clear = {j: r for j, r in data.items() if r["manual_label"] != "CHUA_RO"}
    decided = {j: r for j, r in clear.items() if pred[j]["it_decision"] != "REVIEW"}
    accepted = {j: r for j, r in clear.items() if pred[j]["it_decision"] == "ACCEPT" and r["manual_label"] == "CNTT"}
    software = {j: r for j, r in accepted.items() if r["manual_primary_group_code"] == pred[j]["primary_group_code"] == "SOFTWARE"}
    tp, fp = matrix["ACCEPT"]["CNTT"], matrix["ACCEPT"]["NGOAI_CNTT"]
    fn, tn = matrix["REJECT"]["CNTT"], matrix["REJECT"]["NGOAI_CNTT"]
    return dict(rows=len(data), distinct_job_ids=len(data), labels=dict(collections.Counter(r["manual_label"] for r in data.values())),
                matrix=matrix, tp=tp, fp=fp, fn=fn, tn=tn, chua_ro=len(data)-len(clear),
                machine_review=sum(pred[j]["it_decision"] == "REVIEW" for j in data),
                clear_machine_review=len(clear)-len(decided),
                membership_on_decided=fraction(tp+tn, len(decided)),
                decision_coverage_clear=fraction(len(decided), len(clear)),
                decision_coverage_all=fraction(sum(pred[j]["it_decision"] != "REVIEW" for j in data), len(data)),
                correct_decisions_on_clear=fraction(tp+tn, len(clear)),
                precision_decided=fraction(tp, tp+fp), recall_decided=fraction(tp, tp+fn),
                accept_capture_all_manual_it=fraction(tp, sum(r["manual_label"] == "CNTT" for r in clear.values())),
                primary_group=fraction(sum(r["manual_primary_group_code"] == pred[j]["primary_group_code"] for j, r in accepted.items()), len(accepted)),
                software_subgroup=fraction(sum(r["manual_subgroup_code"] == pred[j]["subgroup_code"] for j, r in software.items()), len(software)),
                fn_examples=[dict(job_id=j, sample_id=r.get("sample_id", ""), title=r["title"], group=r["manual_primary_group_code"],
                                  manual_reason=r["manual_reason"], manual_evidence=r["manual_evidence"],
                                  machine_reason_codes=pred[j]["reason_codes"], machine_selected_rule_id=pred[j]["selected_rule_id"])
                             for j, r in data.items() if r["manual_label"] == "CNTT" and pred[j]["it_decision"] == "REJECT"],
                fp_examples=[dict(job_id=j, title=r["title"]) for j, r in data.items()
                             if r["manual_label"] == "NGOAI_CNTT" and pred[j]["it_decision"] == "ACCEPT"])


def build_reports(plan, issues):
    _, rows = sources()
    pred, down_private = base.predictions()
    all_jobs = set(rows[SEED]) | set(rows[DOWN])
    evidence_checks, schema_errors, metadata = [], [], []
    taxonomy = json.loads((ROOT / "config/it_taxonomy.json").read_text(encoding="utf-8"))
    groups = {g["code"] for g in taxonomy["groups"]}
    subgroups = {g["code"] for g in taxonomy["subgroups"]}
    for rel, data in rows.items():
        for job, row in data.items():
            label, flag, group, subgroup = base.core(row)
            valid = label in {"CNTT", "NGOAI_CNTT", "CHUA_RO"} and flag is {"CNTT": True, "NGOAI_CNTT": False, "CHUA_RO": None}[label]
            valid = valid and (group in groups and (subgroup in subgroups if group == "SOFTWARE" else not subgroup)
                               if label == "CNTT" else not group and not subgroup)
            if not valid:
                schema_errors.append(dict(job_id=job, source=rel))
            missing = [f for f in ["reviewer", "reviewed_date", "manual_reason", "manual_evidence"] if not row[f].strip()]
            if missing:
                metadata.append(dict(source=rel, excel_row=row["_excel_row"], sample_id=row.get("sample_id", ""),
                                     job_id=job, title=row["title"], missing_fields=";".join(missing),
                                     reviewer=row["reviewer"], reviewed_date=row["reviewed_date"]))
            for f, q in evidence_parts(row["manual_evidence"]):
                start = row[f].find(q)
                assert q and start >= 0, (rel, job, f, "Evidence does not match")
                evidence_checks.append(dict(source=rel, job_id=job, field=f, start=start, end=start+len(q), quote=q))
    assert not schema_errors
    notes, note_fields = read_csv(RUN / "reports_before/a04_label_consistency_review.csv")
    notes = [r for r in notes if r["job_id"] not in plan]
    notes_by_job = collections.defaultdict(list)
    for r in notes:
        notes_by_job[r["job_id"]].append(r["issue_code"] + ": " + r["review_note"])
    disagreements, overlap = [], []
    for job in sorted(all_jobs, key=int):
        p, left, right = pred[job], rows[SEED].get(job), rows[DOWN].get(job)
        conflicts = [f for f in MANUAL if left[f] != right[f]] if left and right else []
        if left and right:
            overlap.append(dict(job_id=job, conflict_fields=conflicts, all_manual_fields_equal=not conflicts))
        types = set(t for r in [left, right] if r for t in base.differences(r, p))
        if conflicts:
            types.add("SOURCE_LABEL_CONFLICT")
        if not types:
            continue
        item = dict(job_id=job, title=p["title"],
                    sources=";".join(name for name, r in [("seed42", left), ("accept_downgrades_17", right)] if r),
                    sample_id=left["sample_id"] if left else "", seed42_excel_row=left["_excel_row"] if left else "",
                    downgrade_excel_row=right["_excel_row"] if right else "", difference_types=";".join(sorted(types)),
                    source_conflict_fields=";".join(conflicts), machine_decision=p["it_decision"], machine_is_it=p["is_it"],
                    machine_primary_group_code=p["primary_group_code"], machine_subgroup_code=p["subgroup_code"],
                    machine_selected_rule_id=p["selected_rule_id"], machine_reason_codes=";".join(p["reason_codes"]),
                    machine_candidate_group_codes=";".join(p["candidate_group_codes"]), machine_matched_rule_ids=";".join(p["matched_rule_ids"]),
                    machine_evidence=json.dumps(p["match_evidence"], ensure_ascii=False, separators=(",", ":")),
                    downgrade_old_decision=down_private[job]["old_comparison"]["old_decision"] if right else "",
                    taxonomy_version=p["taxonomy_version"], taxonomy_sha256=p["taxonomy_sha256"],
                    consistency_review_notes=" | ".join(notes_by_job.get(job, [])))
        for suffix, r in [("seed42", left), ("downgrade17", right)]:
            for f in MANUAL:
                item[f + "_" + suffix] = r[f] if r else ""
        disagreements.append(item)
    assert all(not o["conflict_fields"] for o in overlap)
    _, fields = read_csv(RUN / "reports_before/a04_prediction_disagreements.csv")
    write_csv(ROOT / "docs/a04_prediction_disagreements.csv", disagreements, fields)
    _, fields = read_csv(RUN / "reports_before/a04_missing_review_metadata.csv")
    write_csv(ROOT / "docs/a04_missing_review_metadata.csv", metadata, fields)
    write_csv(ROOT / "docs/a04_label_consistency_review.csv", notes, note_fields)
    chua_ro = [dict(job_id=j, sample_id=r["sample_id"], title=r["title"], reason=r["manual_reason"],
                    machine_decision=pred[j]["it_decision"]) for j, r in rows[SEED].items() if r["manual_label"] == "CHUA_RO"]
    summary = dict(date=DATE, timezone="Asia/Bangkok", branch="feat/tv2-analysis", reviewer=REVIEWER,
                   status="LABEL_DECISIONS_APPLIED_A04_ACCEPTANCE_PENDING", join_key="job_id",
                   purpose="ASSISTED_RULE_DEVELOPMENT_NOT_INDEPENDENT_EVALUATION",
                   prediction_sources=[base.PRED, base.DPRED], taxonomy_version="0.2.0",
                   taxonomy_sha256=pred[next(iter(pred))]["taxonomy_sha256"],
                   metric_source="Recomputed from saved predictions and final source workbooks; no XLSX metric sheet read",
                   sources={rel: sample_metrics(data, pred) for rel, data in rows.items()},
                   source_rows=sum(len(r) for r in rows.values()), unique_union_jobs=len(all_jobs),
                   updated_unique_jobs=len(plan), updated_source_rows=len(plan), preserved_prior_decisions=83,
                   overlap=overlap, chua_ro=chua_ro, skipped_cases=issues, schema_errors=schema_errors,
                   missing_metadata_rows=len(metadata), missing_metadata_unique_jobs=len({r["job_id"] for r in metadata}),
                   checked_evidence_instances=len(evidence_checks), prediction_disagreement_unique_jobs=len(disagreements),
                   difference_types=dict(collections.Counter(t for r in disagreements for t in r["difference_types"].split(";"))),
                   machine_review_unique_jobs=sum(pred[j]["it_decision"] == "REVIEW" for j in all_jobs),
                   changed_core_jobs={j: p["changed_core_fields"] for j, p in plan.items() if p["changed_core_fields"]},
                   classifier_rerun=False, etl_rerun=False, a05_performed=False, commit_performed=False, push_performed=False,
                   acceptance_remaining=["Đối soát nguyên nhân và chốt cách xử lý các FN/bất đồng/REVIEW với người phụ trách.",
                                         "Triển khai và xác minh sửa FP/FN nếu được phê duyệt; lượt này không sửa classifier.",
                                         "Người rà soát xác nhận đầu ra và tiêu chí A04; chưa tự đánh dấu hoàn thành/100%."])
    dump(RUN / "evidence_verification.json", evidence_checks)
    dump(RUN / "comparison_summary.json", summary)
    render_reports(summary, plan)
    return summary


def fmt(value):
    n, d, rate = value["numerator"], value["denominator"], value["rate"]
    return f"{n}/{d} = {rate*100:.2f}%" if rate is not None else f"{n}/{d}: không xác định (mẫu số 0)"


def render_reports(s, plan):
    main, extra = s["sources"][SEED], s["sources"][DOWN]
    sections = []
    for name, m in [("Mẫu chính 160", main), ("Mẫu bổ sung 17", extra)]:
        metrics = [
            ("Khớp membership khi máy quyết định", "membership_on_decided"),
            ("Độ phủ quyết định trên nhãn rõ", "decision_coverage_clear"),
            ("Độ phủ quyết định trên toàn mẫu", "decision_coverage_all"),
            ("Quyết định đúng trên toàn mẫu nhãn rõ", "correct_decisions_on_clear"),
            ("Precision trên ca máy ACCEPT có nhãn rõ", "precision_decided"),
            ("Recall có điều kiện trên ca máy ACCEPT/REJECT", "recall_decided"),
            ("Máy ACCEPT trên tất cả CNTT đã duyệt", "accept_capture_all_manual_it"),
            ("Khớp nhóm chính: máy ACCEPT/người đọc CNTT", "primary_group"),
            ("Khớp phân nhóm: cả hai nhóm chính SOFTWARE", "software_subgroup"),
        ]
        table = "\n".join(f"| {label} | {fmt(m[key])} |" for label, key in metrics)
        sections.append(f"### {name}\n\n{base.matrix_md(m['matrix'])}\n\n"
                        f"CHUA_RO: **{m['chua_ro']}/{m['rows']}**; máy REVIEW: **{m['machine_review']}/{m['rows']}**, "
                        f"trong đó **{m['clear_machine_review']}** có nhãn người đọc rõ. "
                        f"TP={m['tp']}, TN={m['tn']}, FP={m['fp']}, FN={m['fn']}.\n\n"
                        f"| Chỉ số và mẫu số | Tử số/mẫu số, kết quả |\n| --- | --- |\n{table}\n")
    metric_text = "\n".join(sections)
    examples = []
    for name, m in [("160", main), ("17", extra)]:
        for e in m["fn_examples"]:
            reason = "; ".join(e["machine_reason_codes"])
            title = e["title"].replace("|", "\\|")
            examples.append(f"| {name} | {e['sample_id'] or 'bổ sung'} | `{e['job_id']}` | {title} | {e['group']} | {reason} |")
    fpfn = ("## FP/FN và đề xuất xử lý\n\n"
            f"Mẫu chính có **FP={main['fp']}, FN={main['fn']}**; mẫu bổ sung có **FP={extra['fp']}, FN={extra['fn']}**. "
            "FP là ACCEPT/NGOAI_CNTT, FN là REJECT/CNTT. Không có FP xác nhận trong hai mẫu, nên không tạo ví dụ FP. "
            "REVIEW chưa quyết định và CHUA_RO không được tính thành FP/FN. Sai nhóm/phân nhóm được báo riêng.\n\n"
            "| Mẫu | Sample | job_id | Title của FN | Nhóm người duyệt | Reason code máy đã lưu |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(examples) + "\n\n"
            "Ví dụ `3899522608` có nhiệm vụ cấu hình/hỗ trợ Philips và Carestream PACS; `3884442452` có tích hợp Workday. "
            "Hai ca là CNTT theo nhiệm vụ hệ thống, máy REJECT. Lý do/bằng chứng nguyên văn của từng ca, rule/reason/evidence máy "
            "nằm trong [bảng bất đồng](a04_prediction_disagreements.csv) và [JSON đối chiếu](../data/analytics/a04_apply_remaining93_20261013/comparison_summary.json).\n\n"
            "Bảy FN mang NO_IT_ROLE_EVIDENCE: rule hiện tại chưa thu được bằng chứng nghề IT, dù người duyệt xác định có nhiệm vụ IT. "
            "Riêng `3904363315` (Oracle Cloud Financial Analyst) mang OUTSIDE_IT_ROLE: cần đối soát exclusion nghề tài chính với task triển khai/cấu hình Oracle Financials đã duyệt IT_BUSINESS. "
            "Cần đối soát task/title/evidence để phân biệt thiếu alias nghề với gate ngữ cảnh hoặc ưu tiên; không coi riêng reason code là chứng minh nguyên nhân gốc. "
            "Đề xuất cho lượt sửa được phép: bổ sung hoặc điều chỉnh rule theo nhiệm vụ PACS, Workday, exclusion Oracle và các ca trong bảng; "
            "kiểm tra ca đối chứng ngoài CNTT, giữ ranh giới qualification/công ty/cộng tác, tăng version/hash/changelog và xác minh lại sau sửa. "
            "Lượt này chỉ ghi nhận và đề xuất, chưa triển khai hoặc xác minh sửa bộ lọc.\n")
    chua = "\n".join(f"| {r['sample_id']} | `{r['job_id']}` | {r['machine_decision']} | {r['reason']} |" for r in s["chua_ro"])
    diffs = ", ".join(f"{k}={v}" for k, v in sorted(s["difference_types"].items()))
    changed = "\n".join(f"| {p['sample_id']} | `{j}` | {', '.join(p['changed_fields'])} |" for j, p in plan.items()
                        if any(f in p["changed_fields"] for f in base.CORE + ["manual_reason", "manual_evidence"]))
    remaining = "\n".join(f"{i}. {v}" for i, v in enumerate(s["acceptance_remaining"], 1))
    text = f"""# A04 – Áp dụng bảng chốt 93 tin và đối chiếu v0.2.0

Ngày **13/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`.

**Đã áp dụng {len(plan)}/93 job_id** từ [a04_remaining93_chot.xlsx](a04_remaining93_chot.xlsx), sheet `Chot 93 tin`, đối chiếu bằng job_id. Cột H → manual_label; I tách đúng ` / ` → nhóm/phân nhóm; J → manual_reason; K → manual_evidence. Reviewer **Dũng**, reviewed_date **2026-10-13**. manual_is_it là boolean Excel true/false theo CNTT/NGOAI_CNTT; CHUA_RO để ô trống.

Đã giữ nguyên tất cả 8 trường manual của **83 quyết định trước** và **4 CHUA_RO đã duyệt**. A04-063 (`3904568619`) giữ **CNTT/DATA_AI**, cập nhật lý do phân biệt task data analytics với qualification ML; A04-124 (`3884430597`) chuyển **IT_MANAGEMENT** theo task quản lý đội hỗ trợ IT. Bảng chốt có 80 giữ nguyên nội dung và 13 sửa lý do/evidence/nhóm. Số ca bỏ qua: **{len(s['skipped_cases'])}**; không phát hiện nguồn khác snapshot bảng quyết định hoặc evidence sai nguyên văn/ngữ cảnh.

## Sao lưu, nguồn và kiểm tra

- Hai workbook đã sao lưu trước ghi tại [backups](../data/analytics/a04_apply_remaining93_20261013/backups/), kèm [manifest SHA-256](../data/analytics/a04_apply_remaining93_20261013/backup_manifest.json); sao lưu cả báo cáo/CSV trước sửa.
- Workbook chính đủ **160 dòng / 160 job_id**; workbook bổ sung đủ **17 dòng / 17 job_id**; hợp **177 dòng nguồn / 176 job_id duy nhất**. Ca chung `3905848702` khớp cả 8 trường manual, không xung đột.
- Metadata/lý do/evidence không thiếu: **{s['missing_metadata_rows']} dòng / {s['missing_metadata_unique_jobs']} job_id**; [danh sách thiếu metadata](a04_missing_review_metadata.csv) giữ header, không còn bản ghi.
- Title/description của 176 khóa khớp workbook, CSV blind, raw và dự đoán lưu theo job_id; 11 raw CSV khớp manifest. Cả 93 snapshot current_* và hash nguồn khớp trước sửa; mỗi đoạn evidence được kiểm tra field/offset/ngữ cảnh riêng. Sau ghi kiểm tra **{s['checked_evidence_instances']} đoạn evidence** trên 177 dòng nguồn.
- Chỉ sửa ô manual của 93 ca trong workbook chính, giữ nguyên mọi ô khác và nội dung mọi ZIP entry ngoài worksheet đó. Workbook bổ sung giữ nguyên byte. [Script](../src/apply_a04_remaining93.py), [plan/context trước ghi](../data/analytics/a04_apply_remaining93_20261013/checked_plan.json) và [audit sau ghi](../data/analytics/a04_apply_remaining93_20261013/application_validation.json) lưu bằng chứng bảo toàn.

## Kết quả tính lại từ dữ liệu

JOIN nhãn nguồn cuối với [dự đoán 160 đã lưu](../data/analytics/a04_taxonomy_v0_2_0_20261008/seed42_v020_predictions_private.jsonl) và [dự đoán 17 đã lưu](../data/analytics/a04_taxonomy_v0_2_0_20261008/accept_downgrade_predictions_private.jsonl); taxonomy **v0.2.0**, SHA-256 `{s['taxonomy_sha256']}`. Không đọc sheet tỷ lệ trong XLSX để tính kết quả, không chạy classifier hoặc ETL.

Đây là tỷ lệ mô tả **mẫu phát triển** seed42 có chọn ca phủ nghề/ngữ cảnh, đã được dùng khi hỗ trợ rà soát; không là đánh giá độc lập hoặc accuracy toàn dataset. Hai mẫu có cơ chế chọn khác nhau và được báo riêng, không gộp 177 dòng thành mẫu độc lập.

{metric_text}
Tỷ lệ khớp khi máy quyết định dùng `(ACCEPT/CNTT + REJECT/NGOAI_CNTT) / ca nhãn rõ và máy ACCEPT/REJECT`. Độ phủ trên nhãn rõ dùng cùng số ca máy quyết định chia tổng CNTT+NGOAI_CNTT. Tỷ lệ quyết định đúng trên toàn mẫu nhãn rõ tính REVIEW là chưa tạo quyết định đúng, không ánh xạ thành REJECT. Precision/recall có điều kiện không bao gồm CHUA_RO/REVIEW; vì vậy báo thêm ACCEPT trên tất cả CNTT đã duyệt để thể hiện phần máy chưa quyết định.

## Bất đồng và CHUA_RO

[Bảng bất đồng](a04_prediction_disagreements.csv) có **{s['prediction_disagreement_unique_jobs']} job_id duy nhất**: {diffs}. Máy REVIEW có **{s['machine_review_unique_jobs']} khóa duy nhất** trong hợp hai mẫu; ca chung REVIEW chỉ tính một lần. Khác subgroup chỉ so khi cả hai nhóm chính SOFTWARE, không đếm lại ca khác nhóm. Ca REVIEW/CHUA_RO giữ các trạng thái gốc trong ma trận.

**4 CHUA_RO** đều đã duyệt; boolean/nhóm/phân nhóm trống, vẫn cần thông tin nếu muốn nhãn rõ. Không tạo CHUA_RO thứ năm từ đề nghị cũ A04-063.

| Sample | job_id | Máy | Thông tin còn thiếu / lý do đã duyệt |
| --- | --- | --- | --- |
{chua}

{fpfn}
## Nội dung nhãn thay đổi trong 93 ca

Các ca dưới đây thay lý do/evidence hoặc nhóm; mọi ca trong 93 đều được ghi metadata. Chỉ **A04-124** đổi core field (nhóm), không đổi membership hoặc subgroup của ca nào. Các cột H/J/K được giữ đúng nguyên văn bảng chốt, không tự thay bằng đoạn trích bổ sung của CSV đề nghị.

| Sample | job_id | Trường thay đổi so với workbook sao lưu |
| --- | --- | --- |
{changed}

## Đối chiếu nghiệm thu A04

Theo [a04_completion_criteria.md](a04_completion_criteria.md), phần mẫu 100–200 tin, nhãn/metadata, tỷ lệ có tử số/mẫu số và ví dụ lọc sai đã có đầu ra cập nhật. Mẫu chính vẫn 160 tin, 4 CHUA_RO được giữ riêng theo hướng dẫn; không bắt buộc ép thành nhãn nhị phân để đủ số. Việc còn lại:

{remaining}

Mẫu đánh giá độc lập cần khi tuyên bố chất lượng sau sửa/toàn dataset; parity Spark/JVM và canonical phục vụ D06/TV1, không phải hai tiêu chí riêng của I21/A04. Lượt này **chưa tự đánh dấu A04 hoàn thành**, không cập nhật tiến độ workbook phân công. Không sửa raw/title/description/job_id/taxonomy/classifier, không chạy ETL, không làm A05, không commit/push.
"""
    (ROOT / "docs/a04_review_summary.md").write_text(text, encoding="utf-8")
    (ROOT / "docs/a04_validation_report.md").write_text(text.replace("# A04 – Áp dụng bảng chốt 93 tin và đối chiếu v0.2.0",
                                                                          "# A04 – Báo cáo kiểm tra nhãn sau chốt đủ 176 job_id", 1), encoding="utf-8")
    notice = (f"> **Cập nhật sau áp dụng 93 tin, 13/10/2026:** đã duyệt đủ **176 job_id / 177 dòng nguồn**, reviewer Dũng, reviewed_date 2026-10-13. "
              f"Giữ nguyên 83 quyết định trước và 4 CHUA_RO; A04-063 CNTT/DATA_AI, A04-124 IT_MANAGEMENT. "
              f"Metadata thiếu: **{s['missing_metadata_rows']}**. Mẫu chính khớp membership khi máy quyết định **{fmt(main['membership_on_decided'])}**, "
              f"độ phủ trên nhãn rõ **{fmt(main['decision_coverage_clear'])}**; mẫu 17 báo riêng trong [báo cáo hiện hành](a04_validation_report.md). "
              "Các mục bên dưới là lịch sử chuẩn bị/đối chiếu trước lượt áp dụng này. **A04 chưa tự đánh dấu hoàn thành**; phần nghiệm thu còn lại xem [tiêu chí cập nhật](a04_completion_criteria.md).")
    for rel in ["docs/a04_manual_labeling.md", "docs/a04_v020_comparison.md"]:
        original = (RUN / "reports_before" / os.path.basename(rel)).read_text(encoding="utf-8")
        updated, count = re.subn(r"> \*\*Cập nhật 13/10/2026:\*\*[^\n]*", lambda _: notice, original, count=1)
        assert count == 1
        (ROOT / rel).write_text(updated, encoding="utf-8")
    for rel in ["docs/a04_remaining93_review_summary.md"]:
        original = (RUN / "reports_before" / os.path.basename(rel)).read_text(encoding="utf-8")
        first, rest = original.split("\n", 1)
        status = ("\n\n> **Trạng thái hiện hành sau áp dụng bảng chốt 93 tin (13/10/2026):** đủ 160 + 17 dòng nguồn, 176 job_id duy nhất; "
                  "93 quyết định được áp dụng theo job_id, metadata thiếu 0; 83 quyết định trước và 4 CHUA_RO giữ nguyên. "
                  "A04-063 giữ CNTT/DATA_AI, A04-124 chuyển IT_MANAGEMENT. Tỷ lệ và FP/FN đã tính lại từ v0.2.0 lưu sẵn, "
                  "mẫu chính và bổ sung riêng tại [báo cáo hiện hành](a04_validation_report.md). "
                  "Còn đối soát/chốt xử lý FN, bất đồng và REVIEW; triển khai/xác minh sửa bộ lọc trong lượt được phép; "
                  "người rà soát xác nhận tiêu chí nghiệm thu. Chưa tự đánh dấu A04 hoàn thành. "
                  "Đánh giá độc lập phục vụ tuyên bố chất lượng; parity thuộc tích hợp D06, không là tiêu chí riêng của A04. "
                  "Phần bên dưới ghi lại trạng thái **trước áp dụng**; thông tin 93 ca chưa duyệt hoặc A04-063 đề nghị CHUA_RO đã được thay thế bằng trạng thái cập nhật này.\n")
        (ROOT / rel).write_text(first + status + rest, encoding="utf-8")
    completion = f"""# A04 – Đối chiếu tiêu chí hoàn thành sau áp dụng 93 tin

Ngày **13/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`. **Chưa tự đánh dấu A04 hoàn thành hoặc 100%.**

## Căn cứ phân công

Nguồn đã đọc ở lượt đối chiếu trước: [Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsm](C:/Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsm), SHA-256 `9343cc8b5c17beb343ec98fa57bb00bff6cb4609aa12cbffb0100ef461c3df26`. Trích địa chỉ ô/nội dung tại [assignment_context.json](../data/analytics/a04_remaining93_review_20261013/assignment_context.json); bản tài liệu tiêu chí trước cập nhật được lưu trong [reports_before](../data/analytics/a04_apply_remaining93_20261013/reports_before/a04_completion_criteria.md). Lượt này không sửa file phân công hay chạy macro.

Sheet `Cong viec`, dòng 21, A04, chủ trì TV2, bắt buộc, phụ thuộc A02/A03:

| Ô | Nội dung phân công |
| --- | --- |
| F21 | Kiểm tra bộ lọc CNTT |
| G21 | Gán nhãn thủ công mẫu 100–200 tin gồm được chọn và bị loại. Sửa false positive/negative. |
| H21 | Mẫu gán nhãn và kết quả đánh giá |
| I21 | Có mẫu, tỷ lệ đúng trên mẫu và ví dụ lọc sai. Không chỉ tìm chuỗi IT. |

`Tong quan!D8` yêu cầu chỉ nhập 100% sau khi người rà soát xác nhận đầu ra và tiêu chí đạt.

## Đầu ra hiện có và việc còn thiếu

| Yêu cầu | Hiện trạng kiểm tra từ nguồn cuối | Việc còn thiếu để nghiệm thu |
| --- | --- | --- |
| Mẫu 100–200 tin gồm được chọn/bị loại | Mẫu chính 160 job_id, gồm ACCEPT/REJECT/REVIEW theo thiết kế seed42 đóng băng; 17 ca bổ sung báo riêng | Không thiếu số lượng mẫu; không cần lấy lại mẫu chỉ để đủ số |
| Nhãn thủ công theo nghề, lý do/evidence/metadata | Đã áp dụng 93 bảng chốt; giữ 83 quyết định trước. Đủ 160+17 dòng, 176 job_id duy nhất; metadata thiếu {s['missing_metadata_rows']}, ca chung không xung đột. Reviewer Dũng, ngày 2026-10-13 | Không còn 93 ca chờ duyệt/thiếu metadata. 4 CHUA_RO đã duyệt giữ riêng, thông tin thiếu ghi rõ |
| Tỷ lệ đúng trên mẫu và kết quả đánh giá | Đã tính lại v0.2.0: mẫu 160 khớp khi máy quyết định {fmt(main['membership_on_decided'])}, độ phủ nhãn rõ {fmt(main['decision_coverage_clear'])}, quyết định đúng trên nhãn rõ {fmt(main['correct_decisions_on_clear'])}. Mẫu 17: khớp {fmt(extra['membership_on_decided'])}, độ phủ {fmt(extra['decision_coverage_clear'])}. Có ma trận 3 trạng thái và mẫu số tại [báo cáo](a04_validation_report.md) | Người rà soát xác nhận cách tính/phạm vi này đáp ứng tiêu chí mẫu. Các tỷ lệ mô tả mẫu phát triển, không suy accuracy toàn dataset |
| Ví dụ lọc sai, đối soát và sửa FP/FN theo G21 | Mẫu chính FP={main['fp']}, FN={main['fn']}; bổ sung FP={extra['fp']}, FN={extra['fn']}. Có ví dụ PACS, Workday, Oracle exclusion và đầy đủ 8 FN; [bảng bất đồng](a04_prediction_disagreements.csv) có {s['prediction_disagreement_unique_jobs']} khóa, nguyên nhân/đề xuất trong báo cáo | Cần đối soát/chốt nguyên nhân và phương án xử lý FN, sai nhóm/phân nhóm, REVIEW. Chưa triển khai hoặc xác minh sửa classifier trong lượt này; bước sửa FP/FN của G21 chưa được chứng minh hoàn tất |
| Xác nhận đầu ra/tiêu chí bởi người rà soát | Việc duyệt nhãn 93 ca đã được cho phép; chưa có xác nhận nghiệm thu toàn A04 hoặc cập nhật tiến độ | Người rà soát xác nhận đầu ra, kết quả mẫu và cách xử lý lỗi; sau đó mới quyết định nghiệm thu/100% |

CHUA_RO là trạng thái hướng dẫn A04 cho phép: **không phải ép 4 ca đã duyệt thành nhãn nhị phân để đủ 160**. Nhãn này được báo riêng, boolean/nhóm/phân nhóm trống; membership dùng mẫu số nhãn rõ. A04-063 giữ CNTT/DATA_AI theo bảng chốt và yêu cầu hiện hành, không cộng thành CHUA_RO thứ năm; A04-124 chuyển IT_MANAGEMENT.

## Quy ước kết quả mẫu

- JOIN bằng job_id với v0.2.0 đã lưu; tính lại từ nhãn workbook cuối, không sao chép tỷ lệ trong XLSX. Hai mẫu 160/17 có cơ chế chọn khác nhau, không gộp 177 dòng nguồn thành 177 tin độc lập.
- Khớp có điều kiện = `(ACCEPT/CNTT + REJECT/NGOAI_CNTT) / số ca nhãn rõ và máy ACCEPT/REJECT`. Báo đồng thời độ phủ trên nhãn rõ/toàn mẫu và tỷ lệ quyết định đúng trên toàn mẫu nhãn rõ.
- REVIEW giữ is_it=NULL, không ánh xạ thành NGOAI_CNTT/REJECT hoặc FN. CHUA_RO loại khỏi mẫu số membership nhãn rõ; vẫn hiện trong ma trận. Mẫu chính: CHUA_RO 4/160, REVIEW 24/160; bổ sung: CHUA_RO 0/17, REVIEW 14/17.
- Khớp nhóm chính chỉ trên máy ACCEPT/người đọc CNTT; khớp phân nhóm chỉ khi cả hai nhóm chính SOFTWARE. Không cộng khác nhóm thành khác phân nhóm lần nữa. Không bịa FP khi không có ACCEPT/NGOAI_CNTT xác nhận.
- Mẫu seed42 đã dùng phát triển/rà soát, có chọn ca phủ nghề và hỗ trợ đọc; tỷ lệ không là đánh giá độc lập hoặc ước lượng chất lượng toàn tập.

## Phạm vi đánh giá độc lập và D06

Mẫu độc lập seed khác, loại job từng dùng phát triển, cần khi tuyên bố chất lượng độc lập sau đóng băng/sửa rule hoặc ước lượng toàn dataset; không được ghi là đầu ra bắt buộc riêng tại G21–I21. Nếu triển khai sửa rule/alias/priority, phải version/hash/changelog và kiểm tra sau sửa theo A02 mục 7 bước 8. Việc chưa có đánh giá độc lập không thay thế yêu cầu báo tỷ lệ trên mẫu phát triển, và cũng không phải lý do duy nhất giữ A04 chưa nghiệm thu.

Parity Python–Spark/JVM, schema/canonical và mapping evidence phục vụ tích hợp D06 do TV1 chủ trì (`Cong viec!11`), phụ thuộc D05/A02/A04. Dataset CNTT Parquet và mốc M3 (`Moc va nghiem thu!8`) là nghiệm thu chung D05/D06/A04/A05/V04; không đảo thành điều kiện D06/A05 phải hoàn tất trước nghiệm thu riêng A04.

Hiện phần nhãn/metadata, tỷ lệ mẫu và ví dụ lỗi đã có. **Còn chốt đối soát/xử lý lỗi, triển khai/xác minh sửa được phép và xác nhận nghiệm thu của người rà soát.** Không sửa raw/title/description/job_id/taxonomy/classifier, không chạy ETL, không làm A05, không commit/push trong lượt này.
"""
    (ROOT / "docs/a04_completion_criteria.md").write_text(completion, encoding="utf-8")


def apply():
    saved = json.loads((RUN / "protected_before.json").read_text(encoding="utf-8"))
    assert base.git_state() == json.loads((RUN / "git_before.json").read_text(encoding="utf-8"))
    assert base.inventory() == saved, "Input changed after backup; do not overwrite"
    checked = preflight()
    expected = json.loads((RUN / "checked_plan.json").read_text(encoding="utf-8"))
    assert {k: v for k, v in checked.items() if k != "source_info"} == expected
    assert not checked["nondecision_source_errors"]
    plan = checked["plan"]
    # Invalid-source jobs are omitted from the write plan and reported explicitly.
    assert plan
    stage = RUN / "a04_manual_labels_filled.candidate.xlsx"
    authorized_cells = base.patch_workbook(ROOT / SEED, stage, checked["source_info"][SEED], plan)
    base.verify_candidate(SEED, stage, checked["source_info"][SEED], plan)
    assert sha(ROOT / DOWN) == saved[DOWN]["sha256"]
    assert sha(ROOT / SEED) == saved[SEED]["sha256"]
    os.replace(stage, ROOT / SEED)
    base.verify_candidate(SEED, ROOT / SEED, checked["source_info"][SEED], plan)
    summary = build_reports(plan, checked["issues"])
    after = base.inventory()
    allowed = {SEED} | set(REPORTS)
    protected = {p: v for p, v in saved.items() if p not in allowed}
    assert {p: after[p] for p in protected} == protected
    assert base.git_state() == json.loads((RUN / "git_before.json").read_text(encoding="utf-8"))
    before_rows = keyed(checked["source_info"][SEED]["rows"])
    _, final = sources()
    assert all(all(before_rows[j][f] == final[SEED][j][f] for f in MANUAL)
               for j in checked["preserved_jobs"] if j in before_rows)
    changes = [dict(job_id=j, sample_id=p["sample_id"], source=SEED,
                    changes={f: dict(before=before_rows[j][f], after=p["values"][f]) for f in p["changed_fields"]})
               for j, p in plan.items()]
    validation = dict(date=DATE, branch="feat/tv2-analysis", updated_unique_jobs=len(plan), updated_source_rows=len(plan),
                      skipped_cases=checked["issues"], authorized_manual_cells=authorized_cells,
                      changed_cells=sum(len(c["changes"]) for c in changes), changes=changes,
                      preserved_prior_decisions=83, preserved_chua_ro=4, supplemental_workbook_byte_unchanged=True,
                      protected_artifacts_checked=len(protected), protected_artifacts_unchanged=True,
                      source_fields_and_nondecision_cells_unchanged=True, workbook_unmodified_zip_entries_unchanged=True,
                      same_job_consistent_across_workbooks=True, all_source_counts_valid=True,
                      raw_hashes_match_manifest=11, git_head_index_tracked_diff_unchanged=True,
                      before_sha256={r: saved[r]["sha256"] for r in SOURCES}, after_sha256={r: after[r]["sha256"] for r in SOURCES},
                      generated_reports={r: after[r]["sha256"] for r in REPORTS}, comparison=summary)
    dump(RUN / "application_validation.json", validation)
    dump(ROOT / AUDIT, {k: v for k, v in validation.items() if k != "changes"})
    print(json.dumps({k: v for k, v in summary.items() if k not in {"sources", "chua_ro"}}, ensure_ascii=False, indent=2))
    print(json.dumps(summary["sources"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    csv.field_size_limit(16*1024*1024)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    apply() if args.apply else prepare()
