"""Apply authorized A04 decisions by job_id, using saved predictions only.

Standard library, no classifier/ETL imports. First run without --apply to back up
inputs and build a checked plan. Then --apply rechecks the inputs, stages and
validates both workbooks, writes only authorized cells, and refreshes reports.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data/analytics/a04_apply_decisions_20261013"
DATE = "2026-10-13"
REVIEWER = "Dũng"
SEED = "data/analytics/a04_manual_seed42/a04_manual_labels_filled.xlsx"
DOWN = "data/analytics/a04_taxonomy_v0_2_0_20261008/accept_downgrades_for_review_blind.xlsx"
SOURCES = {SEED: ("A04 manual labels", 160), DOWN: ("Review", 17)}
DECISION = "docs/a04_review_decisions_chot.xlsx"
CSV_SOURCE = "docs/a04_review_decisions.csv"
BASE = "data/analytics/a04_taxonomy_v0_2_0_20261008/"
PRED = BASE + "seed42_v020_predictions_private.jsonl"
DPRED = BASE + "accept_downgrade_predictions_private.jsonl"
CORE = ["manual_label", "manual_is_it", "manual_primary_group_code", "manual_subgroup_code"]
MANUAL = CORE + ["manual_reason", "manual_evidence", "reviewer", "reviewed_date"]
REPORTS = ["docs/a04_review_summary.md", "docs/a04_validation_report.md",
           "docs/a04_prediction_disagreements.csv", "docs/a04_missing_review_metadata.csv",
           "docs/a04_label_consistency_review.csv", "docs/a04_manual_labeling.md",
           "docs/a04_v020_comparison.md"]
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
CELL = re.compile(r'<c\b[^>]*?\br="([A-Z]+[0-9]+)"[^>]*?(?:/>|>.*?</c>)', re.S)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader), reader.fieldnames


def csv_value(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "" if value is None else value


def write_csv(path, rows, fields):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: csv_value(v) for k, v in row.items()} for row in rows)
    reread, actual_fields = read_csv(path)
    assert len(reread) == len(rows) and actual_fields == fields


def canonical(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"Non-integral job_id: {value!r}")
    return str(int(value))


def keyed(rows):
    result = {}
    for row in rows:
        key = canonical(row["job_id"])
        if key in result:
            raise ValueError(f"Duplicate job_id: {key}")
        result[key] = row
    return result


def boolean(value):
    if isinstance(value, bool):
        return value
    if value == "":
        return None
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValueError(f"Invalid boolean: {value!r}")


def core(row):
    return (row[CORE[0]], boolean(row[CORE[1]]), row[CORE[2]], row[CORE[3]])


def read_sheet(path, name, header_row=1):
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ["".join(t.text or "" for t in item.findall(".//s:t", NS))
                      for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("s:si", NS)]
        rels = {r.attrib["Id"]: r.attrib["Target"]
                for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        sheets = ET.fromstring(archive.read("xl/workbook.xml")).findall("s:sheets/s:sheet", NS)
        sheet = next(s for s in sheets if s.attrib["name"] == name)
        target = rels[sheet.attrib["{" + NS["r"] + "}id"]]
        target = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
        table, formulas = {}, []
        for row in ET.fromstring(archive.read(target)).findall("s:sheetData/s:row", NS):
            values = {}
            for cell in row.findall("s:c", NS):
                column = re.match(r"[A-Z]+", cell.attrib["r"]).group()
                value = cell.findtext("s:v", "", NS)
                typ = cell.attrib.get("t")
                if typ == "s":
                    value = shared[int(value)] if value else ""
                elif typ == "inlineStr":
                    value = "".join(t.text or "" for t in cell.findall(".//s:t", NS))
                elif typ == "b":
                    value = value == "1"
                if cell.find("s:f", NS) is not None:
                    formulas.append(cell.attrib["r"])
                values[column] = value
            table[int(row.attrib["r"])] = values
        headers = table[header_row]
        assert len(headers) == len(set(headers.values())), "Duplicate headers"
        rows = [dict(_excel_row=n, **{h: values.get(c, "") for c, h in headers.items()})
                for n, values in table.items() if n > header_row and any(v != "" for v in values.values())]
        return dict(rows=rows, headers=headers, formulas=formulas, target=target, table=table)


def inventory():
    result = {}
    for directory in ["data/raw", "config", "src", "docs", "data/audit", "data/analytics"]:
        for path in sorted((ROOT / directory).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or RUN in path.parents:
                continue
            st = path.stat()
            result[path.relative_to(ROOT).as_posix()] = dict(bytes=st.st_size, mtime_ns=st.st_mtime_ns, sha256=sha(path))
    return result


def git_state():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")
    return {"branch": git("branch", "--show-current").strip(), "head": git("rev-parse", "HEAD").strip(),
            "staged_sha256": text_sha(git("diff", "--cached", "--binary")),
            "tracked_diff_sha256": text_sha(git("diff", "--binary"))}


def predictions():
    def load(rel):
        with (ROOT / rel).open(encoding="utf-8") as stream:
            return keyed([json.loads(line) for line in stream if line.strip()])
    seed, down = load(PRED), load(DPRED)
    assert len(seed) == 160 and len(down) == 17
    result = dict(seed)
    for job, record in down.items():
        old = record["old_comparison"]
        p = record["new_prediction"]
        assert old["old_decision"] == "ACCEPT" and old["new_decision"] == p["it_decision"] != "ACCEPT"
        if job in result:
            assert {k: v for k, v in result[job].items() if k != "sample_id"} == p
        else:
            result[job] = p
    taxonomy_sha = sha(ROOT / "config/it_taxonomy.json")
    previous = json.loads((ROOT / "data/audit/tv2_a04_v020_validation.json").read_text(encoding="utf-8"))
    assert sha(ROOT / PRED) == previous["seed42_private_predictions_sha256"]
    assert taxonomy_sha == previous["taxonomy_sha256"] == sha(ROOT / (BASE + "it_taxonomy_v0.2.0.json"))
    assert sha(ROOT / (BASE + "all_predictions.jsonl.gz")) == previous["trace_sha256"]
    for job, p in result.items():
        assert canonical(p["job_id"]) == job
        assert p["taxonomy_version"] == "0.2.0" and p["taxonomy_sha256"] == taxonomy_sha
        assert p["is_it"] is {"ACCEPT": True, "REJECT": False, "REVIEW": None}[p["it_decision"]]
        for field in ["title", "description"]:
            assert text_sha(p[field]) == p["source_" + field + "_sha256"]
    return result, down


def preflight():
    source_info = {rel: read_sheet(ROOT / rel, sheet) for rel, (sheet, _) in SOURCES.items()}
    sources = {rel: keyed(info["rows"]) for rel, info in source_info.items()}
    for rel, (_, count) in SOURCES.items():
        assert len(sources[rel]) == count and not source_info[rel]["formulas"]
    assert len({r["sample_id"] for r in sources[SEED].values()}) == 160
    csv_rows, _ = read_csv(ROOT / CSV_SOURCE)
    csv_by_job = keyed(csv_rows)
    info = read_sheet(ROOT / DECISION, "Quyet dinh A04", header_row=6)
    assert info["headers"]["H"] == "Nhãn chốt" and info["headers"]["I"] == "Nhóm / phân nhóm chốt"
    assert not info["formulas"]
    decisions = keyed([dict(job_id=r["job_id"], row=r) for r in info["rows"]])
    assert len(csv_by_job) == len(decisions) == 83 and set(csv_by_job) == set(decisions)
    pred, _ = predictions()
    assert set(sources[SEED]) <= set(pred) and set(sources[DOWN]) <= set(pred)
    all_jobs = set(sources[SEED]) | set(sources[DOWN])
    assert len(all_jobs) == 176
    # Read-only source JOIN; no ETL, no classification, no dependence on row order.
    raw = {}
    with (ROOT / "data/raw/postings.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            job = canonical(row["job_id"])
            if job in all_jobs:
                assert job not in raw
                raw[job] = {k: row[k] for k in ["title", "description"]}
    assert set(raw) == all_jobs
    blind = {SEED: keyed(read_csv(ROOT / "data/analytics/a04_manual_seed42/a04_manual_labels_blind.csv")[0]),
             DOWN: keyed(read_csv(ROOT / (BASE + "accept_downgrades_for_review_blind.csv"))[0])}
    for rel in SOURCES:
        assert set(blind[rel]) == set(sources[rel])
    manifest = json.loads((ROOT / "data/analytics/a04_manual_seed42/run_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["raw_files"]) == len(list((ROOT / "data/raw").rglob("*.csv"))) == 11
    raw_hash_mismatches = [rel for rel, old in manifest["raw_files"].items()
                           if sha(ROOT / "data/raw" / rel) != old["sha256"]]
    config = json.loads((ROOT / "config/it_taxonomy.json").read_text(encoding="utf-8"))
    groups, subgroups = {g["code"] for g in config["groups"]}, {g["code"] for g in config["subgroups"]}
    issues, plan, evidence_count = [], {}, 0
    for job in sorted(decisions, key=int):
        d, c = decisions[job]["row"], csv_by_job[job]
        problems = []
        def check(condition, code, detail):
            if not condition:
                problems.append(dict(code=code, detail=detail))
        check(d["Chức danh"] == c["title"], "DECISION_CSV_TITLE", "Title bảng chốt khác CSV nguồn")
        check(d["Nhãn hiện tại"] == c["current_manual_label"], "DECISION_CSV_CURRENT_LABEL", "Nhãn hiện tại khác CSV")
        current_group = " / ".join(x for x in [c["current_primary_group_code"], c["current_subgroup_code"]] if x)
        check(d["Nhóm / phân nhóm hiện tại"] == current_group, "DECISION_CSV_CURRENT_GROUP", "Nhóm hiện tại khác CSV")
        check(d["Người duyệt"] == REVIEWER and d["Ngày duyệt"].startswith(DATE),
              "DECISION_REVIEW_METADATA", "Người/ngày duyệt bảng chốt khác yêu cầu")
        label = d["Nhãn chốt"]
        parts = [p.strip() for p in d["Nhóm / phân nhóm chốt"].split("/") if p.strip()]
        group, subgroup = (parts + ["", ""])[:2]
        check(label in {"CNTT", "NGOAI_CNTT", "CHUA_RO"}, "DECISION_LABEL_ENUM", repr(label))
        if label == "CNTT":
            check(group in groups and len(parts) <= 2, "DECISION_GROUP", repr(parts))
            check(subgroup in subgroups if group == "SOFTWARE" else not subgroup, "DECISION_SUBGROUP", repr(parts))
        else:
            check(not parts, "DECISION_NON_IT_GROUP", "NGOAI_CNTT/CHUA_RO phải trống nhóm")
        quotes = json.loads(c["evidence_quotes_json"])
        offsets = json.loads(c["evidence_description_offsets_json"])
        rendered = "\n\n".join(f"[{i}] {quote}" for i, quote in enumerate(quotes, 1))
        check(bool(quotes) and len(quotes) == len(offsets), "CSV_EVIDENCE_FORMAT", "Quote/offset thiếu hoặc không cùng số lượng")
        check(d["Bằng chứng nguyên văn"] == c["verbatim_evidence"] == rendered,
              "DECISION_CSV_EVIDENCE", "Bằng chứng bảng chốt khác quotes trong CSV")
        check(bool(d["Lý do gợi ý"].strip()), "DECISION_REASON_MISSING", "Lý do chốt trống")
        annotations = {a["path"]: a for a in json.loads(c["source_annotations_json"])}
        actual_refs = {rel for rel in SOURCES if job in sources[rel]}
        check(set(annotations) == actual_refs and bool(actual_refs), "SOURCE_MEMBERSHIP", "Nguồn workbook khác snapshot CSV")
        found_evidence = []
        for rel in sorted(actual_refs):
            row, annotation = sources[rel][job], annotations.get(rel)
            for field in ["title", "description"]:
                check(row[field] == blind[rel][job][field] == pred[job][field] == raw[job][field],
                      "SOURCE_TEXT_MISMATCH", f"{rel}: {field} khác CSV blind/dự đoán/raw")
            check(row["title"] == c["title"] and text_sha(row["description"]) == c["description_sha256"],
                  "CSV_DESCRIPTION_HASH", f"{rel}: title/hash description khác bảng quyết định")
            if rel == SEED:
                check(row["sample_id"] == blind[rel][job]["sample_id"] == c["source_sample_ids"] == d["sample_id"],
                      "SOURCE_SAMPLE_ID", f"{rel}: sample_id khác nguồn")
            if annotation:
                for field in MANUAL + ["job_id"]:
                    # Cell coordinates in annotations are provenance only, never JOIN keys.
                    check(row[field] == annotation[field], "SOURCE_ANNOTATION_MISMATCH", f"{rel}: {field} khác snapshot CSV")
            for i, (quote, offset) in enumerate(zip(quotes, offsets), 1):
                start, end = offset["start"], offset["end"]
                ok = bool(quote) and quote in row["description"] and row["description"][start:end] == quote
                check(ok, "EVIDENCE_NOT_VERBATIM", f"{rel}: quote {i} không khớp description tại [{start},{end})")
                if ok:
                    found_evidence.append(dict(source=rel, quote_no=i, start=start, end=end, quote=quote))
        # The machine details in the source decision CSV must still refer to this saved prediction.
        check(c["machine_decision"] == pred[job]["it_decision"] and c["taxonomy_version"] == "0.2.0",
              "CSV_PREDICTION_MISMATCH", "CSV không khớp dự đoán lưu v0.2.0")
        if problems:
            issues.append(dict(job_id=job, title=c["title"], sources=sorted(actual_refs), problems=problems))
            continue
        values = dict(manual_label=label, manual_is_it={"CNTT": True, "NGOAI_CNTT": False, "CHUA_RO": ""}[label],
                      manual_primary_group_code=group, manual_subgroup_code=subgroup,
                      manual_reason=d["Lý do gợi ý"], manual_evidence=rendered,
                      reviewer=REVIEWER, reviewed_date=DATE)
        evidence_count += len(quotes)
        plan[job] = dict(job_id=job, sources=sorted(actual_refs), values=values, evidence=found_evidence,
                         decision=d, csv_description_sha256=c["description_sha256"],
                         changed_core_fields=[f for f, a, b in zip(CORE, core(sources[sorted(actual_refs)[0]][job]), core(values)) if a != b])
    # Non-decision jobs are never edited; report any source problems as a validation failure.
    other_errors = []
    for job in all_jobs - set(decisions):
        for rel in SOURCES:
            if job in sources[rel]:
                row = sources[rel][job]
                for field in ["title", "description"]:
                    if row[field] != blind[rel][job][field] or row[field] != raw[job][field] or row[field] != pred[job][field]:
                        other_errors.append(dict(job_id=job, source=rel, field=field))
    return dict(plan=plan, issues=issues, source_info=source_info,
                distinct_evidence_quotes=evidence_count, raw_hash_mismatches=raw_hash_mismatches,
                nondecision_source_errors=other_errors)


def prepare():
    state = git_state()
    assert state["branch"] == "feat/tv2-analysis"
    RUN.mkdir(exist_ok=False)
    (RUN / "backups").mkdir()
    (RUN / "reports_before").mkdir()
    # Backups exist and hash-match before preflight or any label mutation.
    backup_info = {}
    for rel in SOURCES:
        target = RUN / "backups" / Path(rel).name
        shutil.copy2(ROOT / rel, target)
        assert sha(target) == sha(ROOT / rel)
        backup_info[rel] = dict(path=target.relative_to(ROOT).as_posix(), sha256=sha(target))
    for rel in REPORTS:
        if (ROOT / rel).exists():
            shutil.copy2(ROOT / rel, RUN / "reports_before" / Path(rel).name)
    dump(RUN / "backup_manifest.json", backup_info)
    print("Backed up both label workbooks; capturing protected input hashes...", flush=True)
    dump(RUN / "protected_before.json", inventory())
    dump(RUN / "git_before.json", state)
    result = preflight()
    dump(RUN / "checked_plan.json", {k: v for k, v in result.items() if k != "source_info"})
    assert inventory() == json.loads((RUN / "protected_before.json").read_text(encoding="utf-8"))
    print(json.dumps({"eligible_jobs": len(result["plan"]),
                      "source_rows_to_update": sum(len(p["sources"]) for p in result["plan"].values()),
                      "unique_evidence_quotes": result["distinct_evidence_quotes"],
                      "labels": dict(collections.Counter(p["values"]["manual_label"] for p in result["plan"].values())),
                      "core_changed_jobs": {j: p["changed_core_fields"] for j, p in result["plan"].items() if p["changed_core_fields"]},
                      "issues": result["issues"], "raw_hash_mismatches": result["raw_hash_mismatches"],
                      "nondecision_source_errors": result["nondecision_source_errors"]}, ensure_ascii=False, indent=2), flush=True)


def patch_workbook(source, target, info, plan):
    edits = {}
    for row in info["rows"]:
        job = canonical(row["job_id"])
        if job in plan and source.relative_to(ROOT).as_posix() in plan[job]["sources"]:
            for column, field in info["headers"].items():
                if field in MANUAL:
                    edits[column + str(row["_excel_row"])] = plan[job]["values"][field]
    with zipfile.ZipFile(source) as archive:
        xml = archive.read(info["target"]).decode("utf-8")
        replaced = set()
        def replace(match):
            ref = match.group(1)
            if ref not in edits:
                return match.group()
            value = edits[ref]
            replaced.add(ref)
            opening = match.group().split(">", 1)[0].rstrip("/")
            opening = re.sub(r'\s+t="[^"]*"', "", opening)
            if isinstance(value, bool):
                return opening + ' t="b"><v>' + ("1" if value else "0") + "</v></c>"
            if value == "":
                return opening + "/>"
            return opening + ' t="inlineStr"><is><t xml:space="preserve">' + escape(value) + "</t></is></c>"
        updated = CELL.sub(replace, xml)
        assert replaced == set(edits), f"Missing cells: {set(edits) - replaced}"
        assert CELL.sub(lambda m: "" if m.group(1) in edits else m.group(), xml) == CELL.sub(
            lambda m: "" if m.group(1) in edits else m.group(), updated)
        ET.fromstring(updated)
        with zipfile.ZipFile(target, "x") as output:
            output.comment = archive.comment
            for entry in archive.infolist():
                output.writestr(entry, updated.encode("utf-8") if entry.filename == info["target"] else archive.read(entry.filename))
    with zipfile.ZipFile(source) as left, zipfile.ZipFile(target) as right:
        assert left.namelist() == right.namelist() and right.testzip() is None
        assert [name for name in left.namelist() if left.read(name) != right.read(name)] == [info["target"]]
    return len(edits)


def verify_candidate(rel, candidate, original, plan):
    sheet, count = SOURCES[rel]
    after = read_sheet(candidate, sheet)
    before_rows, after_rows = keyed(original["rows"]), keyed(after["rows"])
    assert len(after_rows) == count and set(after_rows) == set(before_rows)
    assert original["headers"] == after["headers"] and not after["formulas"]
    assert [r["job_id"] for r in original["rows"]] == [r["job_id"] for r in after["rows"]]
    for job, row in after_rows.items():
        for field, value in before_rows[job].items():
            expected = plan[job]["values"][field] if job in plan and field in MANUAL else value
            assert row[field] == expected, (rel, job, field)
    return after


def differences(row, p):
    if row["manual_label"] == "CHUA_RO":
        return ["MANUAL_CHUA_RO"]
    if p["it_decision"] == "REVIEW":
        return ["MACHINE_REVIEW"]
    if (row["manual_label"] == "CNTT") != (p["it_decision"] == "ACCEPT"):
        return ["MEMBERSHIP_MISMATCH"]
    result = []
    if row["manual_label"] == "CNTT":
        if row["manual_primary_group_code"] != p["primary_group_code"]:
            result.append("GROUP_MISMATCH")
        if row["manual_primary_group_code"] == p["primary_group_code"] == "SOFTWARE" and row["manual_subgroup_code"] != p["subgroup_code"]:
            result.append("SUBGROUP_MISMATCH")
    return result


def reports(plan, issues):
    rows = {rel: read_sheet(ROOT / rel, name)["rows"] for rel, (name, _) in SOURCES.items()}
    by_source = {rel: keyed(data) for rel, data in rows.items()}
    pred, down_private = predictions()
    all_jobs = set(by_source[SEED]) | set(by_source[DOWN])
    metadata = []
    for rel, data in rows.items():
        for row in data:
            missing = [f for f in ["reviewer", "reviewed_date"] if not row[f].strip()]
            if missing:
                metadata.append(dict(source=rel, excel_row=row["_excel_row"], sample_id=row.get("sample_id", ""),
                                     job_id=row["job_id"], title=row["title"], missing_fields=";".join(missing),
                                     reviewer=row["reviewer"], reviewed_date=row["reviewed_date"]))
    old_notes, note_fields = read_csv(RUN / "reports_before/a04_label_consistency_review.csv")
    remaining_notes = [r for r in old_notes if r["job_id"] not in plan]
    # Old semantic warnings on applied jobs are historical findings, preserved in the backup.
    # CHUA_RO is an endorsed label but still needs information before a clear label is possible.
    for job, item in plan.items():
        if item["values"]["manual_label"] == "CHUA_RO":
            rel = SEED if job in by_source[SEED] else DOWN
            row = by_source[rel][job]
            remaining_notes.append(dict(source=rel, excel_row=row["_excel_row"], sample_id=row.get("sample_id", ""),
                                        job_id=job, title=row["title"], manual_label="CHUA_RO",
                                        manual_primary_group_code="", manual_subgroup_code="", issue_code="MANUAL_CHUA_RO_INFORMATION_PENDING",
                                        review_note="Đã duyệt CHUA_RO ngày 2026-10-13; cần thêm thông tin để chốt CNTT/NGOAI_CNTT. " + row["manual_reason"],
                                        manual_reason=row["manual_reason"], manual_evidence=row["manual_evidence"]))
    notes_by_job = collections.defaultdict(list)
    for row in remaining_notes:
        notes_by_job[row["job_id"]].append(row["issue_code"] + ": " + row["review_note"])
    disagreements = []
    _, difference_fields = read_csv(RUN / "reports_before/a04_prediction_disagreements.csv")
    overlaps = []
    for job in sorted(all_jobs, key=int):
        p, left, right = pred[job], by_source[SEED].get(job), by_source[DOWN].get(job)
        conflicts = []
        if left and right:
            conflicts = [f for f, a, b in zip(CORE, core(left), core(right)) if a != b]
            overlaps.append(dict(job_id=job, conflict_fields=conflicts,
                                 all_manual_fields_equal=all(left[f] == right[f] for f in MANUAL)))
        types = set(t for row in [left, right] if row for t in differences(row, p))
        if conflicts:
            types.add("SOURCE_LABEL_CONFLICT")
        if not types:
            continue
        item = dict(job_id=job, title=p["title"],
                    sources=";".join(name for name, row in [("seed42", left), ("accept_downgrades_17", right)] if row),
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
        for suffix, row in [("seed42", left), ("downgrade17", right)]:
            for field in MANUAL:
                item[field + "_" + suffix] = row[field] if row else ""
        disagreements.append(item)
    write_csv(ROOT / "docs/a04_prediction_disagreements.csv", disagreements, difference_fields)
    _, meta_fields = read_csv(RUN / "reports_before/a04_missing_review_metadata.csv")
    write_csv(ROOT / "docs/a04_missing_review_metadata.csv", metadata, meta_fields)
    write_csv(ROOT / "docs/a04_label_consistency_review.csv", remaining_notes, note_fields)
    schema_errors, evidence_checks = [], []
    config = json.loads((ROOT / "config/it_taxonomy.json").read_text(encoding="utf-8"))
    groups, subgroups = {g["code"] for g in config["groups"]}, {g["code"] for g in config["subgroups"]}
    for rel, data in rows.items():
        for row in data:
            job = row["job_id"]
            label, is_it, group, subgroup = core(row)
            valid = is_it is {"CNTT": True, "NGOAI_CNTT": False, "CHUA_RO": None}.get(label)
            valid = valid and (group in groups and (subgroup in subgroups if group == "SOFTWARE" else not subgroup)
                               if label == "CNTT" else not group and not subgroup)
            if not valid:
                schema_errors.append(dict(job_id=job, source=rel))
            if job in plan:
                quotes = [e for e in plan[job]["evidence"] if e["source"] == rel]
                assert all(row["description"][e["start"]:e["end"]] == e["quote"] for e in quotes)
                evidence_checks.extend(dict(job_id=job, **e) for e in quotes)
            else:
                ev = row["manual_evidence"]
                match = re.match(r"^(title|description):\s*(.*)$", ev, re.S)
                choices = [(match[1], match[2])] if match else [(f, ev) for f in ["description", "title"]]
                found = [(field, quote, row[field].find(quote)) for field, quote in choices if quote and quote in row[field]]
                assert found, (rel, job, "unchanged evidence does not match")
                field, quote, start = found[0]
                evidence_checks.append(dict(job_id=job, source=rel, field=field, start=start, end=start+len(quote), quote=quote))
    assert not schema_errors and all(not r["conflict_fields"] and r["all_manual_fields_equal"] for r in overlaps)
    def matrix(data):
        return {decision: {label: sum(pred[r["job_id"]]["it_decision"] == decision and r["manual_label"] == label for r in data)
                           for label in ["CNTT", "NGOAI_CNTT", "CHUA_RO"]} for decision in ["ACCEPT", "REJECT", "REVIEW"]}
    source_summaries = {}
    for rel, data in rows.items():
        source_summaries[rel] = dict(rows=len(data), distinct_job_ids=len(keyed(data)),
                                    labels=dict(collections.Counter(r["manual_label"] for r in data)), matrix=matrix(data),
                                    updated_rows=sum(r["job_id"] in plan for r in data),
                                    missing_metadata_rows=sum(r["source"] == rel for r in metadata),
                                    differences=dict(collections.Counter(t for r in data for t in differences(r, pred[r["job_id"]]))),
                                    primary_groups=dict(collections.Counter(r["manual_primary_group_code"] for r in data if r["manual_primary_group_code"])),
                                    subgroups=dict(collections.Counter(r["manual_subgroup_code"] for r in data if r["manual_subgroup_code"])))
    chua_ro = [dict(job_id=job, sample_id=(by_source[SEED].get(job) or {}).get("sample_id", ""),
                    title=pred[job]["title"], reason=(by_source[SEED].get(job) or by_source[DOWN][job])["manual_reason"],
                    machine_decision=pred[job]["it_decision"]) for job in sorted(all_jobs, key=int)
               if (by_source[SEED].get(job) or by_source[DOWN][job])["manual_label"] == "CHUA_RO"]
    summary = dict(date=DATE, timezone="Asia/Bangkok", reviewer=REVIEWER, branch="feat/tv2-analysis",
                   status="DECISIONS_APPLIED_REMAINING_REVIEW_METADATA_PENDING", join_key="job_id",
                   purpose="ASSISTED_RULE_DEVELOPMENT_NOT_INDEPENDENT_EVALUATION", sources=source_summaries,
                   unique_union_jobs=len(all_jobs), updated_unique_jobs=len(plan),
                   updated_source_rows=sum(len(p["sources"]) for p in plan.values()), overlap=overlaps,
                   skipped_cases=issues, schema_errors=schema_errors,
                   distinct_decision_quotes=sum(len({e["quote_no"] for e in p["evidence"]}) for p in plan.values()),
                   checked_evidence_instances=len(evidence_checks),
                   core_changed_jobs={j: p["changed_core_fields"] for j, p in plan.items() if p["changed_core_fields"]},
                   prediction_disagreement_unique_jobs=len(disagreements),
                   difference_types=dict(collections.Counter(t for r in disagreements for t in r["difference_types"].split(";"))),
                   machine_review_unique_jobs=sum(pred[j]["it_decision"] == "REVIEW" for j in all_jobs),
                   chua_ro=chua_ro, missing_metadata_rows=len(metadata),
                   missing_metadata_unique_jobs=len({r["job_id"] for r in metadata}),
                   consistency_pending_notes=len(remaining_notes),
                   metrics="NOT_COMPUTED; development sample, pending 93 reviewer/date records",
                   classifier_rerun=False, etl_rerun=False, a05_performed=False, commit_performed=False, push_performed=False)
    dump(RUN / "evidence_verification.json", evidence_checks)
    dump(RUN / "comparison_summary.json", summary)
    render_reports(summary)
    return summary


def matrix_md(matrix):
    lines = ["| Máy v0.2.0 | CNTT | NGOAI_CNTT | CHUA_RO | Tổng |", "| --- | ---: | ---: | ---: | ---: |"]
    for decision, counts in matrix.items():
        lines.append(f"| {decision} | {counts['CNTT']} | {counts['NGOAI_CNTT']} | {counts['CHUA_RO']} | {sum(counts.values())} |")
    lines.append("| Tổng | " + " | ".join(str(sum(r[l] for r in matrix.values())) for l in ["CNTT", "NGOAI_CNTT", "CHUA_RO"]) + " | " + str(sum(sum(r.values()) for r in matrix.values())) + " |")
    return "\n".join(lines)


def render_reports(s):
    seed, down = s["sources"][SEED], s["sources"][DOWN]
    chua_table = "\n".join(f"| {r['sample_id']} | `{r['job_id']}` | {r['machine_decision']} | {r['reason'].replace(chr(10), ' ')} |" for r in s["chua_ro"])
    core_rows = "\n".join(f"| `{job}` | {', '.join(fields)} |" for job, fields in s["core_changed_jobs"].items())
    skips = "Không có ca bị bỏ qua; không phát hiện dữ liệu nguồn khác bảng quyết định hoặc bằng chứng sai nguyên văn." if not s["skipped_cases"] else json.dumps(s["skipped_cases"], ensure_ascii=False, indent=2)
    common = f"""Ngày cập nhật: **13/10/2026**, múi giờ `Asia/Bangkok`; nhánh **`feat/tv2-analysis`**.

**Đã áp dụng {s['updated_unique_jobs']} job_id duy nhất vào {s['updated_source_rows']} dòng nguồn: {seed['updated_rows']} dòng của workbook 160 và {down['updated_rows']} dòng của workbook 17.** Reviewer **Dũng**, reviewed_date **2026-10-13**, chỉ được ghi vào các dòng thuộc quyết định đã chốt. Còn **{s['missing_metadata_rows']} dòng / {s['missing_metadata_unique_jobs']} job_id** thiếu reviewer/ngày duyệt, đều ở mẫu 160.

Đây là **mẫu phát triển quy tắc có hỗ trợ gán nhãn**, chưa phải mẫu đánh giá độc lập. Các số đếm mô tả hai tập mẫu hiện có; không tính accuracy/precision/recall hoặc suy rộng ra toàn dataset/thị trường.

## Nguồn, sao lưu và cách áp dụng

- Quyết định: [a04_review_decisions_chot.xlsx](a04_review_decisions_chot.xlsx), sheet `Quyet dinh A04`, header Excel 6. **H** là nhãn chốt, **I** tách thành nhóm/phân nhóm; J là manual_reason, K là các trích dẫn nguyên văn; L được lưu trong audit để giữ căn cứ/giới hạn. Dòng/STT chỉ phục vụ truy vết, mọi JOIN dùng **job_id**.
- [CSV nguồn](a04_review_decisions.csv) giữ nguyên 83 bản ghi đề nghị ban đầu, snapshot nhãn nguồn, description_sha256, evidence_quotes_json và offsets `[start,end)`; không đổi CSV đề nghị thành quyết định cuối.
- [Workbook 160](../{SEED}) và [workbook 17](../{DOWN}) có đủ **160 và 17 dòng**, tương ứng **176 job_id**. `3905848702` có trong cả hai, cập nhật giống nhau cả 8 trường manual, chỉ tính một job.
- [Hai bản sao lưu](../data/analytics/a04_apply_decisions_20261013/backups/), [manifest SHA-256](../data/analytics/a04_apply_decisions_20261013/backup_manifest.json) và [báo cáo/CSV trước sửa](../data/analytics/a04_apply_decisions_20261013/reports_before/) được tạo trước khi sửa nhãn.
- Chuẩn hóa manual_is_it thành boolean Excel true/false; CHUA_RO để ô boolean, nhóm và phân nhóm thực sự trống. Ngoài CNTT cũng để nhóm trống. Không sửa job_id/title/description/sample_id, không sửa các dòng ngoài danh sách chốt.
- Kiểm tra {s['distinct_decision_quotes']} đoạn trích độc lập của 83 ca với CSV, hash mô tả và offset trong **description của đúng job_id** trước khi ghi; không nối các đoạn rời rồi coi là một câu liên tục. Workbook lưu dạng `[1] ...`, `[2] ...`, kiểm tra từng đoạn riêng. Đã kiểm tra lại toàn bộ lý do/bằng chứng và schema sau ghi.

{skips}

## Đối chiếu với dự đoán v0.2.0 đã lưu

Chỉ đọc [dự đoán 160](../{PRED}) và [dự đoán 17](../{DPRED}), kiểm tra version/hash/provenance và JOIN theo job_id; không gọi classifier hoặc chạy ETL.

### Mẫu 160

{matrix_md(seed['matrix'])}

### Mẫu 17

{matrix_md(down['matrix'])}

[Bảng bất đồng](a04_prediction_disagreements.csv) hiện có **{s['prediction_disagreement_unique_jobs']} job_id duy nhất**. Số theo loại: {', '.join(f"{k}={v}" for k, v in s['difference_types'].items())}. Chỉ so phân nhóm khi cả hai nhóm chính đều SOFTWARE; không đếm lại khác nhóm thành khác phân nhóm. Bảng giữ nhãn/lý do/evidence/reviewer/ngày của từng workbook ở cột riêng và đầy đủ rule/reason/evidence của máy.

**REVIEW của máy có is_it=NULL, không coi là NGOAI_CNTT hoặc REJECT.** Toàn hợp hai mẫu có **{s['machine_review_unique_jobs']} job_id máy REVIEW**. Với nhãn CHUA_RO, difference_types ưu tiên MANUAL_CHUA_RO để giữ nhãn người đọc riêng; ma trận phía trên vẫn giữ nguyên trạng thái máy, kể cả ca máy REVIEW đồng thời nhãn CHUA_RO. Bất đồng là kết quả đối chiếu, không tự sửa máy hoặc nhãn theo bên còn lại.

## CHUA_RO đã duyệt, vẫn cần thêm thông tin

**{len(s['chua_ro'])} job_id CHUA_RO** đều đã được Dũng duyệt ngày 2026-10-13; không nằm trong danh sách metadata thiếu. Chưa đủ thông tin để chốt CNTT/NGOAI_CNTT; không đưa vào đối chiếu membership trên nhãn rõ.

| Sample | job_id | Máy | Thông tin còn thiếu / lý do chốt |
| --- | --- | --- | --- |
{chua_table}

## Thay đổi nhãn/nhóm so với workbook trước sửa

**{len(s['core_changed_jobs'])} job_id** thay đổi ít nhất một trường label/boolean/nhóm/phân nhóm. Các job còn lại trong 83 ca cũng được áp dụng lý do/bằng chứng đã chốt và metadata duyệt; không tính mỗi trường là một job.

| job_id | Trường thay đổi |
| --- | --- |
{core_rows}

## Những việc còn lại để hoàn thành A04

1. Dũng/người đọc hoàn tất việc duyệt thực tế và metadata cho **{s['missing_metadata_unique_jobs']} job_id** trong [danh sách thiếu metadata](a04_missing_review_metadata.csv). Các nhãn có sẵn trên những dòng này được giữ nguyên và chưa được lượt chốt này phê duyệt.
2. Bổ sung thông tin cho **4 CHUA_RO** nếu cần nhãn nghề rõ; giữ trạng thái này riêng khi chưa có căn cứ mới. [Bảng ngữ nghĩa hiện hành](a04_label_consistency_review.csv) giữ các ca còn thiếu thông tin, không tiếp tục gắn cảnh báo “chưa nhóm chốt” cho các quyết định đã áp dụng. Ghi chú ngữ nghĩa cũ giữ trong bản sao lưu.
3. Đối soát các bất đồng với máy và thống nhất tác động thiết kế cần phiên bản sau; lượt này hoàn tất áp dụng quyết định, **không thay taxonomy/classifier**. Giữ các quyết định ưu tiên task/title và phạm vi IT_BUSINESS trong bảng chốt/audit để review.
4. Nếu mục tiêu là kết luận chất lượng độc lập: đóng băng phạm vi/rule/version, lấy mẫu độc lập seed khác và loại các job đã dùng phát triển; gán nhãn trước xem máy, định nghĩa mẫu số/REVIEW/CHUA_RO và thiết kế/trọng số trước khi tính chỉ số. Mẫu đánh giá cuối chưa tạo.
5. Xác nhận bàn giao schema/canonical và parity Spark/JVM với TV1 trước tích hợp production; phần này chưa được xác minh trong A04 hiện tại.

## Kiểm tra và bảo toàn

Script [apply_a04_decisions.py](../src/apply_a04_decisions.py) chỉ dùng thư viện chuẩn Python, sửa các ô manual trong XML worksheet và giữ nguyên byte nội dung mọi ZIP entry khác. Hai workbook được tạo bản ứng viên và kiểm tra trước khi thay file nguồn. Các ô ngoài danh sách 83 job và mọi trường nguồn đều được so trước/sau; có kiểm tra lại bản workbook đã ghi.

Đối chiếu full text theo job_id với CSV blind, dự đoán lưu và raw postings ở chế độ đọc; đủ 176 khóa. SHA-256 11 raw CSV khớp manifest đóng băng; taxonomy và dự đoán khớp provenance v0.2.0. [Audit áp dụng](../data/analytics/a04_apply_decisions_20261013/application_validation.json) ghi hash trước/sau, mọi trường đổi, các ca bỏ qua và kết quả kiểm tra; [đối chiếu chi tiết](../data/analytics/a04_apply_decisions_20261013/comparison_summary.json) giữ số đếm/ma trận.

Không sửa raw/taxonomy/classifier hoặc dự đoán đã lưu; không chạy lại ETL, không làm A05, không commit/push. HEAD, index và diff tracked giữ nguyên. A04 **chưa hoàn tất toàn bộ** vì còn các dòng chưa được duyệt và các việc đánh giá/bàn giao nêu trên.
"""
    (ROOT / "docs/a04_review_summary.md").write_text("# A04 – Áp dụng quyết định đã chốt ngày 13/10/2026\n\n" + common, encoding="utf-8")
    (ROOT / "docs/a04_validation_report.md").write_text("# A04 – Kiểm tra sau áp dụng quyết định và đối chiếu v0.2.0\n\n" + common, encoding="utf-8")
    status = f"""> **Cập nhật 13/10/2026:** đã áp dụng **{s['updated_unique_jobs']} job_id / {s['updated_source_rows']} dòng nguồn** từ bảng quyết định đã chốt; reviewer Dũng, reviewed_date 2026-10-13 chỉ cho các dòng đó. Hai workbook vẫn đủ 160 và 17 dòng. Còn **{s['missing_metadata_unique_jobs']} job_id** thiếu metadata duyệt; **4 CHUA_RO** giữ riêng. Xem [báo cáo hiện hành](a04_validation_report.md) và [kết quả áp dụng](a04_review_summary.md). Các mục bên dưới ghi lại quá trình chuẩn bị/so sánh phiên bản ngày 08/10/2026; trạng thái nhãn hiện tại lấy từ báo cáo cập nhật.

"""
    for rel in ["docs/a04_manual_labeling.md", "docs/a04_v020_comparison.md"]:
        path = ROOT / rel
        original = path.read_text(encoding="utf-8")
        first, rest = original.split("\n", 1)
        path.write_text(first + "\n\n" + status + rest.lstrip("\n"), encoding="utf-8")


def apply():
    saved = json.loads((RUN / "protected_before.json").read_text(encoding="utf-8"))
    assert git_state() == json.loads((RUN / "git_before.json").read_text(encoding="utf-8"))
    assert inventory() == saved, "An input changed since prepare; no overwrites"
    checked = preflight()
    expected = json.loads((RUN / "checked_plan.json").read_text(encoding="utf-8"))
    assert {k: v for k, v in checked.items() if k != "source_info"} == expected
    assert not checked["raw_hash_mismatches"] and not checked["nondecision_source_errors"]
    plan = checked["plan"]
    candidates, cell_counts = {}, {}
    (RUN / "candidates").mkdir(exist_ok=True)
    for rel in SOURCES:
        candidate = RUN / "candidates" / Path(rel).name
        cell_counts[rel] = patch_workbook(ROOT / rel, candidate, checked["source_info"][rel], plan)
        verify_candidate(rel, candidate, checked["source_info"][rel], plan)
        candidates[rel] = candidate
    print(f"Validated staged workbooks for {len(plan)} job_id; writing authorized manual cells...", flush=True)
    for rel, candidate in candidates.items():
        assert sha(ROOT / rel) == saved[rel]["sha256"]
        os.replace(candidate, ROOT / rel)
        verify_candidate(rel, ROOT / rel, checked["source_info"][rel], plan)
    summary = reports(plan, checked["issues"])
    after = inventory()
    allowed = set(SOURCES) | set(REPORTS)
    protected = {k: v for k, v in saved.items() if k not in allowed}
    assert {k: after[k] for k in protected} == protected
    assert git_state() == json.loads((RUN / "git_before.json").read_text(encoding="utf-8"))
    assert all(sha(ROOT / rel) == data["sha256"] for rel, data in saved.items() if rel in [DECISION, CSV_SOURCE, PRED, DPRED])
    changes = []
    for rel in SOURCES:
        final_rows = keyed(read_sheet(ROOT / rel, SOURCES[rel][0])["rows"])
        for original in checked["source_info"][rel]["rows"]:
            job = original["job_id"]
            if job in plan:
                final = final_rows[job]
                changes.append(dict(source=rel, job_id=job, excel_row=original["_excel_row"],
                                    changes={f: dict(before=original[f], after=final[f]) for f in MANUAL if original[f] != final[f]}))
    validation = dict(date=DATE, branch="feat/tv2-analysis", updated_unique_jobs=len(plan), updated_source_rows=len(changes),
                      skipped_cases=checked["issues"], changed_cells=cell_counts, changes=changes,
                      protected_artifacts_checked=len(protected), protected_artifacts_unchanged=True,
                      workbook_nonmanual_cells_unchanged=True, nondecision_rows_unchanged=True,
                      workbook_unmodified_zip_entries_unchanged=True, same_job_consistent_across_workbooks=True,
                      all_source_counts_valid=True, raw_hashes_match_manifest=11,
                      git_head_index_tracked_diff_unchanged=True, classifier_rerun=False, etl_rerun=False,
                      before_sha256={rel: saved[rel]["sha256"] for rel in SOURCES},
                      after_sha256={rel: after[rel]["sha256"] for rel in SOURCES},
                      generated_reports={rel: after[rel]["sha256"] for rel in REPORTS})
    dump(RUN / "application_validation.json", validation)
    dump(ROOT / "data/audit/tv2_a04_decisions_applied_20261013.json", {k: v for k, v in validation.items() if k != "changes"} | {"comparison": summary})
    print(json.dumps({k: v for k, v in summary.items() if k not in {"sources", "chua_ro"}}, ensure_ascii=False, indent=2), flush=True)
    print(json.dumps(summary["sources"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    csv.field_size_limit(16 * 1024 * 1024)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    apply() if args.apply else prepare()
