"""Audit all 11 original CSVs, safely copy raw, and verify A01/A03 evidence.

Uses Python 3.11 stdlib CSV, not ETL; existing D03-D05 artifacts remain intact.
"""
from __future__ import annotations

import argparse
import ast
import collections
import datetime as dt
import json
import shutil
import sys
from decimal import Decimal
from pathlib import Path

from tv2_csv import ROOT, csv_header, csv_rows, integer_key, sha256, text_value, write_csv, write_json

KEYS = {
    "postings": [("job_id",), ("company_id",)],
    "companies": [("company_id",)],
    "company_industries": [("company_id",), ("company_id", "industry")],
    "company_specialities": [("company_id",), ("company_id", "speciality")],
    "employee_counts": [("company_id",), ("company_id", "time_recorded")],
    "benefits": [("job_id",), ("job_id", "type")],
    "job_industries": [("job_id",), ("job_id", "industry_id")],
    "job_skills": [("job_id",), ("job_id", "skill_abr")],
    "salaries": [("salary_id",), ("job_id",)],
    "industries": [("industry_id",)], "skills": [("skill_abr",)],
}
RELATIONS = [
    ("companies", "postings", "company_id", "company_id"),
    ("postings", "job_skills", "job_id", "job_id"),
    ("postings", "job_industries", "job_id", "job_id"),
    ("postings", "benefits", "job_id", "job_id"),
    ("postings", "salaries", "job_id", "job_id"),
    ("skills", "job_skills", "skill_abr", "skill_abr"),
    ("industries", "job_industries", "industry_id", "industry_id"),
    ("companies", "company_industries", "company_id", "company_id"),
    ("companies", "company_specialities", "company_id", "company_id"),
    ("companies", "employee_counts", "company_id", "company_id"),
]


def table_specs():
    # Read existing TV1 constants without importing Spark or changing TV1 code.
    tree = ast.parse((ROOT / "src/clean_data.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "TABLE_SPECS":
            return ast.literal_eval(node.value)
    raise ValueError("TABLE_SPECS not found")


def pct(n, d):
    return round(100 * n / d, 6) if d else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    archive = args.archive.resolve()
    specs = table_specs()
    previous = {r["table"]: r for r in csv_rows(ROOT / "data/audit/table_inventory.csv")}
    files = {t: archive / s["path"] for t, s in specs.items()}
    if any(not p.is_file() for p in files.values()):
        raise FileNotFoundError("Archive must contain all 11 CSVs in the documented layout")
    source_before = {t: (p.stat().st_size, p.stat().st_mtime_ns, sha256(p)) for t, p in files.items()}
    # Check every existing destination before any copying. Differing raw is never overwritten.
    for table, spec in specs.items():
        destination = ROOT / "data/raw" / spec["path"]
        if destination.exists() and sha256(destination) != source_before[table][2]:
            raise FileExistsError(f"Raw conflict; no files copied: {destination}")
    inventory, missing_rows, key_rows, profiles = [], [], [], {}
    tables, postings_companies, examples = {}, {}, []
    for table, path in files.items():
        print(f"Parsing {table} ...", flush=True)
        headers = csv_header(path)
        count = 0
        missing = collections.Counter()
        values = {c: collections.Counter() for c in headers if c not in {"description", "skills_desc", "title", "name", "url", "application_url", "job_posting_url"}}
        key_counts = {key: collections.Counter() for key in KEYS[table]}
        key_nulls = collections.Counter()
        small_rows = []
        timestamps = {c: [] for c in headers if c in {"original_listed_time", "listed_time", "expiry", "closed_time", "time_recorded"}}
        numeric = {c: [] for c in headers if "salary" in c}
        multiline = 0
        both_text, auxiliary_only = 0, 0
        work_type_pairs = collections.Counter()
        for row in csv_rows(path):
            count += 1
            clean = {c: text_value(v) for c, v in row.items()}
            if any("\n" in v or "\r" in v for v in row.values()):
                multiline += 1
            for c, value in clean.items():
                if value is None:
                    missing[c] += 1
                elif c in values:
                    values[c][value] += 1
                if value is not None and c in timestamps:
                    timestamps[c].append(Decimal(value))
                if value is not None and c in numeric:
                    numeric[c].append(Decimal(value))
            for key in key_counts:
                parts = tuple(integer_key(row[c]) if c.endswith("_id") else text_value(row[c]) for c in key)
                if None in parts:
                    key_nulls[key] += 1
                else:
                    key_counts[key][parts] += 1
            if table == "postings":
                job = integer_key(row["job_id"])
                if job in postings_companies:
                    raise ValueError(f"Duplicate postings.job_id: {job}")
                postings_companies[job] = integer_key(row["company_id"])
                if len(examples) < 8:
                    examples.append({c: row[c] for c in ["job_id", "title", "description", "location", "formatted_experience_level", "formatted_work_type", "work_type", "remote_allowed", "min_salary", "max_salary", "med_salary", "normalized_salary", "currency", "pay_period", "compensation_type", "original_listed_time", "listed_time"]})
                both_text += clean["description"] is not None and clean["skills_desc"] is not None
                auxiliary_only += clean["description"] is None and clean["skills_desc"] is not None
                work_type_pairs[(row["formatted_work_type"], row["work_type"])] += 1
                small_rows.append({c: row[c] for c in ["job_id", "company_id", "min_salary", "max_salary", "med_salary", "currency", "pay_period", "compensation_type"]})
            else:
                small_rows.append(row)
        tables[table] = small_rows
        if table == "postings":
            write_csv(ROOT / "data/audit/tv2_work_type_pairs.csv", [dict(formatted_work_type=a, work_type=b, raw_postings=n) for (a, b), n in sorted(work_type_pairs.items())], ["formatted_work_type", "work_type", "raw_postings"])
        expected = previous[table]
        destination = ROOT / "data/raw" / specs[table]["path"]
        action = "IDENTICAL_SKIPPED" if destination.exists() else "COPIED"
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with path.open("rb") as src, destination.open("xb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            shutil.copystat(path, destination)
        digest = sha256(destination)
        assert digest == source_before[table][2], f"Copy verification failed: {table}"
        inventory.append(dict(table=table, source_path=str(path), relative_path=specs[table]["path"], bytes=path.stat().st_size, mib=round(path.stat().st_size / 1024**2, 4), rows=count, columns=len(headers), headers_json=json.dumps(headers), expected_rows=int(expected["rows"]), rows_match=count == int(expected["rows"]), headers_match=headers == json.loads(expected["column_names"]), tv1_schema_match=headers == specs[table]["columns"], multiline_records=multiline, source_sha256=source_before[table][2], raw_sha256=digest, copy_action=action))
        missing_rows.extend(dict(table=table, column=c, rows=count, missing=missing[c], missing_percent=pct(missing[c], count)) for c in headers)
        for key, counts in key_counts.items():
            key_rows.append(dict(table=table, key=" + ".join(key), comparison="NUMERIC_CANONICAL_IDS_TRIM_TEXT", null_rows=key_nulls[key], distinct=len(counts), duplicate_rows=sum(counts.values()) - len(counts)))
        profiles[table] = dict(rows=count, top_values={c: v.most_common(12) for c, v in values.items()}, observed_values={c: list(v.items()) for c, v in values.items() if c in {"remote_allowed", "formatted_experience_level", "formatted_work_type", "work_type", "currency", "pay_period", "compensation_type", "skill_abr", "industry"}}, numeric_ranges={c: dict(non_missing=len(v), min=str(min(v)) if v else None, max=str(max(v)) if v else None) for c, v in numeric.items()}, timestamps={c: dict(non_missing=len(v), unit="seconds" if c == "time_recorded" else "milliseconds", raw_min=str(min(v)) if v else None, raw_max=str(max(v)) if v else None, min_utc=dt.datetime.fromtimestamp(float(min(v)) / (1 if c == "time_recorded" else 1000), dt.timezone.utc).isoformat() if v else None, max_utc=dt.datetime.fromtimestamp(float(max(v)) / (1 if c == "time_recorded" else 1000), dt.timezone.utc).isoformat() if v else None) for c, v in timestamps.items()}, description_and_skills_desc=both_text if table == "postings" else None, skills_desc_without_description=auxiliary_only if table == "postings" else None)
    relations = []
    for parent, child, pk, fk in RELATIONS:
        parent_keys = {integer_key(r[pk]) if pk.endswith("_id") else text_value(r[pk]) for r in tables[parent]} - {None}
        child_counts = collections.Counter(integer_key(r[fk]) if fk.endswith("_id") else text_value(r[fk]) for r in tables[child])
        nulls = child_counts.pop(None, 0)
        child_keys = set(child_counts)
        matched = parent_keys & child_keys
        orphan = child_keys - parent_keys
        relations.append(dict(parent=parent, child=child, parent_key=pk, child_key=fk, child_rows=len(tables[child]), child_null_rows=nulls, child_distinct_keys=len(child_keys), matched_keys=len(matched), orphan_keys=len(orphan), orphan_rows=sum(child_counts[k] for k in orphan), child_key_coverage_percent=pct(len(matched), len(child_keys)), parent_keys=len(parent_keys), parent_keys_with_child=len(matched), parent_keys_without_child=len(parent_keys - child_keys), parent_coverage_percent=pct(len(matched), len(parent_keys)), comparison="NUMERIC_CANONICAL" if pk.endswith("_id") else "TRIM_TEXT"))
    jobs = set(postings_companies)
    job_links = {t: {integer_key(r["job_id"]) for r in tables[t]} & jobs for t in ["job_skills", "job_industries", "benefits", "salaries"]}
    industries = {integer_key(r["industry_id"]): text_value(r["industry_name"]) for r in tables["industries"]}
    named_jobs = {integer_key(r["job_id"]) for r in tables["job_industries"] if industries.get(integer_key(r["industry_id"])) is not None} & jobs
    labels = {r["skill_abr"]: r["skill_name"] for r in tables["skills"]}
    label_counts = collections.Counter(r["skill_abr"] for r in tables["job_skills"] if integer_key(r["job_id"]) in jobs)
    industry_counts = collections.Counter(integer_key(r["industry_id"]) for r in tables["job_industries"] if integer_key(r["job_id"]) in jobs)
    source_labels = [dict(skill_abr=k, skill_name=labels[k], postings_with_label=n) for k, n in sorted(label_counts.items())]
    source_industries = [dict(industry_id=k, industry_name=industries[k], postings_with_industry=n) for k, n in sorted(industry_counts.items(), key=lambda x: int(x[0]))]
    company_coverage = {}
    for table in ["companies", "company_industries", "company_specialities", "employee_counts"]:
        company_ids = {integer_key(r["company_id"]) for r in tables[table]}
        covered = sum(c in company_ids for c in postings_companies.values())
        company_coverage[table] = dict(postings_with_company_link=covered, denominator=len(jobs), percent=pct(covered, len(jobs)))
    pay_cols = ["min_salary", "max_salary", "med_salary", "currency", "pay_period", "compensation_type"]
    pay = {integer_key(r["job_id"]): r for r in tables["salaries"]}
    differing_pay = []
    for row in tables["postings"]:
        job = integer_key(row["job_id"])
        if job in pay:
            def comparable(r, c):
                value = text_value(r[c])
                return Decimal(value) if value is not None and "salary" in c else value
            if any(comparable(row, c) != comparable(pay[job], c) for c in pay_cols):
                differing_pay.append(job)
    derived = dict(scope="ALL_RAW_POSTINGS_NOT_VALIDATED_IT", postings=len(jobs), skills_industries_intersection=len(job_links["job_skills"] & job_links["job_industries"]), skills_industries_union=len(job_links["job_skills"] | job_links["job_industries"]), industry_named_jobs=len(named_jobs), industry_only_missing_names=len(job_links["job_industries"] - named_jobs), company_coverage=company_coverage, salary_matched_jobs=len(job_links["salaries"]), salary_tuple_differences=len(differing_pay), salary_tuple_difference_sample=differing_pay[:10], skills_mapping_equals_d05=sorted(tables["skills"], key=lambda r: r["skill_abr"]) == sorted(list(csv_rows(ROOT / "data/audit/d05_precheck_skills.csv")), key=lambda r: r["skill_abr"]))
    old_missing = {(r["table"], r["column"]): int(r["missing_count"]) for r in csv_rows(ROOT / "data/audit/missing_profile.csv")}
    missing_differences = [r for r in missing_rows if old_missing[(r["table"], r["column"])] != r["missing"]]
    source_unchanged = all((p.stat().st_size, p.stat().st_mtime_ns, sha256(p)) == source_before[t] for t, p in files.items())
    assert source_unchanged, "Archive changed during verification"
    out = ROOT / "data/audit"
    write_csv(out / "tv2_raw_inventory.csv", inventory, list(inventory[0]))
    write_csv(out / "tv2_raw_missing.csv", missing_rows, list(missing_rows[0]))
    write_csv(out / "tv2_raw_keys.csv", key_rows, list(key_rows[0]))
    write_csv(out / "tv2_raw_join_coverage.csv", relations, list(relations[0]))
    write_csv(out / "tv2_source_labels.csv", source_labels, list(source_labels[0]))
    write_csv(out / "tv2_source_industries.csv", source_industries, list(source_industries[0]))
    write_csv(ROOT / "data/analytics/tv2_validation/posting_examples.csv", examples, list(examples[0]))
    write_json(out / "tv2_raw_profiles.json", dict(profiles=profiles, derived=derived, inventory_all_match=all(r["rows_match"] and r["headers_match"] and r["tv1_schema_match"] for r in inventory), missing_differences_vs_d03=missing_differences, source_unchanged=source_unchanged, archive=str(archive), total_bytes=sum(r["bytes"] for r in inventory), total_mib=sum(r["bytes"] for r in inventory) / 1024**2, parser="Python csv.DictReader(strict=True), UTF-8-sig, newline=''", python=sys.version, verified_date="2026-10-08", source_version_limit="Matching counts/headers is not proof of identical Kaggle release; historical audit has no raw SHA-256."))
    print(json.dumps(dict(inventory_match=all(r["rows_match"] and r["headers_match"] for r in inventory), missing_differences=len(missing_differences), source_unchanged=source_unchanged, derived=derived), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
