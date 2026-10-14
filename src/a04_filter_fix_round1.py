"""Build/test staged P1a/P2 candidate, classifying only the 176 frozen A04 jobs.

Baseline is prepared before editing code; --prepare builds cumulative configs.
Default runs fixtures, replays the saved baseline, compares each stage and writes
new traces/reports. Never reads raw rows, runs ETL, writes labels or promotes the
candidate to config/it_taxonomy.json. Existing output paths are never replaced.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import apply_a04_decisions as audit_helpers
from compare_a04_versions import validate_evidence
from it_taxonomy import Taxonomy
from tv2_csv import ROOT, sha256, write_csv, write_json

RUN = ROOT / "data/analytics/a04_taxonomy_v0_2_1_20261014"
CANDIDATE = ROOT / "config/versions/it_taxonomy_v0.2.1.json"
SEED, DOWN = audit_helpers.SEED, audit_helpers.DOWN
VERSION, DATE = "0.2.1", "2026-10-14"
STAGES = ["P1a", "P2_ETL", "P2_CYBER", "P2_SOFTWARE_TITLE", "P2_DATABASE"]
CORE = ["it_decision", "is_it", "primary_group_code", "subgroup_code", "selected_rule_id",
        "reason_codes", "matched_rule_ids", "candidate_group_codes"]
DETAIL = CORE + ["match_evidence", "description_processing", "description_segments"]
HEADINGS = {
    "ROLE": ["role description"],
    "RESPONSIBILITIES": ["essential duties and responsibilities", "job duties and responsibilities"],
    "QUALIFICATIONS": ["qualifications and education requirements", "required skills & experience",
                       "desired skills & experience", "skills"],
    "BENEFITS": ["what we have to offer", "description of benefits", "compensation & benefits details"],
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def patch(config, stage):
    if stage == "P1a":
        headings = config["normalization"]["description_segments"]["context_policy"]["section_headings"]
        for section, values in HEADINGS.items():
            assert not set(values) & set(headings[section])
            headings[section].extend(values)
    elif stage == "P2_ETL":
        config["term_sets"]["data_tasks"]["aliases"].extend(["creating etl pipeline", "create etl pipelines"])
    elif stage == "P2_CYBER":
        config["term_sets"]["security_context"]["aliases"].append("cyber incidents")
    elif stage == "P2_SOFTWARE_TITLE":
        config["term_sets"]["software_titles"]["aliases"].append("software development engineer")
    elif stage == "P2_DATABASE":
        config["term_sets"].update({
            "database_admin_tasks": dict(purpose="Explicit database administration duty, not SQL/reporting use.",
                                         aliases=["oversee database management"]),
            "database_admin_objects": dict(purpose="Database object in the same owned duty unit.",
                                           aliases=["database", "databases"]),
            "database_admin_context": dict(purpose="Storage, retrieval AND security administration; no generic verb/context expansion.",
                                           aliases=["data storage, retrieval, and security", "data storage, retrieval and security"]),
        })
        rule = next(r for r in config["include_rules"] if r["id"] == "DATA_AI_CONTEXT")
        existing = rule["condition"]["all"][1]
        assert "same_segment" in existing
        rule["condition"]["all"][1] = {"any": [existing, {"same_segment": {
            "field": "description", "all_term_sets": ["database_admin_tasks", "database_admin_objects", "database_admin_context"]}}]}
    else:
        raise ValueError(stage)


def assert_scope(config, applied):
    baseline = read_json(RUN / "baseline/it_taxonomy_v0.2.0.json")
    expected = copy.deepcopy(baseline)
    for stage in applied:
        patch(expected, stage)
    # All behavior fields are exact except the explicit catalog/predicate edits.
    metadata = {"version", "status", "revision_date", "changelog", "round1_candidate_stage"}
    assert set(config) - set(expected) <= metadata
    for key in expected:
        if key not in metadata:
            assert config[key] == expected[key], key
    for key in ["groups", "subgroups", "general_it_rules", "exclusion_rules", "decision_policy", "rule_language", "inputs"]:
        assert config[key] == baseline[key], key
    for old, new in zip(baseline["include_rules"], config["include_rules"]):
        assert all(old[k] == new[k] for k in old if k != "condition")
        if old["id"] != "DATA_AI_CONTEXT" or "P2_DATABASE" not in applied:
            assert old == new
    n0, n1 = copy.deepcopy(baseline["normalization"]), copy.deepcopy(config["normalization"])
    n0["description_segments"]["context_policy"].pop("section_headings")
    n1["description_segments"]["context_policy"].pop("section_headings")
    assert n0 == n1  # Includes parser, implicit heading, 500 limit and every blocker.
    assert config["schema_version"] == 1 and config["version"] == VERSION


def stage_folder(index, name):
    return RUN / "stages" / f"{index:02d}_{name}"


def prepare():
    assert RUN.exists() and not (RUN / "stages").exists() and not CANDIDATE.exists()
    baseline = read_json(RUN / "baseline/it_taxonomy_v0.2.0.json")
    config, applied = copy.deepcopy(baseline), []
    config.update(version=VERSION, status="round1_candidate_development_sample_only", revision_date=DATE)
    (RUN / "stages").mkdir()
    for index, stage in enumerate(STAGES, 1):
        patch(config, stage)
        applied.append(stage)
        config["round1_candidate_stage"] = list(applied)
        config["changelog"] = [dict(version=VERSION, date=DATE, scope="P1a_and_P2_only", applied=list(applied),
                                     deferred=["P1b", "P3", "P4", "P5"],
                                     previous_config="config/versions/it_taxonomy_v0.2.0.json")] + baseline["changelog"]
        assert_scope(config, applied)
        folder = stage_folder(index, stage)
        folder.mkdir()
        write_json(folder / "config.json", config, exclusive=True)
    with CANDIDATE.open("xb") as stream:
        stream.write((folder / "config.json").read_bytes())
    assert sha256(CANDIDATE) == sha256(folder / "config.json")
    print(f"Prepared {len(STAGES)} cumulative stage configs; candidate {VERSION} is separate from the active baseline.")


def checked_prediction(model, title, description, job=None):
    p = model.classify(title, description, job)
    p.update(title=title, description=description,
             source_title_sha256=hashlib.sha256(title.encode("utf-8")).hexdigest(),
             source_description_sha256=hashlib.sha256(description.encode("utf-8")).hexdigest())
    assert p["is_it"] is {"ACCEPT": True, "REJECT": False, "REVIEW": None}[p["it_decision"]]
    if p["it_decision"] != "ACCEPT":
        assert p["primary_group_code"] is None and p["subgroup_code"] is None and p["selected_rule_id"] is None
    else:
        assert p["primary_group_code"] in model.groups
        assert p["subgroup_code"] in model.subgroups if p["primary_group_code"] == "SOFTWARE" else p["subgroup_code"] is None
    assert p["description_processing"]["source_sha256"] == p["source_description_sha256"]
    assert p["description_processing"]["dropped_oversize_units"] == 0
    validate_evidence(model, p)
    return p


def controls():
    # Explicit expected occupational behavior, not assertions copied from output.
    # Positive controls activate only once the indicated stage has been applied.
    return [
        ("explicit_role_colon", "Engineer", "About us:\nOur company builds tools.\nRole Description:\nYou will develop software in Java.", "P1a", "SOFTWARE"),
        ("explicit_duties_standalone", "Engineer", "Who we are:\nOur company builds tools.\nEssential Duties And Responsibilities\nYou will develop software in Java.", "P1a", "SOFTWARE"),
        ("etl_create", "BI Analyst", "Responsibilities: You will create etl pipelines using SQL.", "P2_ETL", "DATA_AI"),
        ("etl_creating", "BI Analyst", "Responsibilities: You will be creating etl pipeline using Python.", "P2_ETL", "DATA_AI"),
        ("cyber_context", "Digital Forensics Analyst", "Responsibilities: You will respond to cyber incidents.", "P2_CYBER", "SECURITY"),
        ("software_development_engineer", "Software Development Engineer II", "", "P2_SOFTWARE_TITLE", "SOFTWARE"),
        ("database_admin", "Data Analyst", "Responsibilities: Oversee database management activities including data storage, retrieval, and security.", "P2_DATABASE", "DATA_AI"),
        ("database_admin_no_oxford_comma", "Data Analyst", "Responsibilities: Oversee database management activities including data storage, retrieval and security.", "P2_DATABASE", "DATA_AI"),
        ("sdet_full_title", "Software Development Engineer in Test", "", "always", "QA_TESTING"),
        ("sdet_acronym", "SDET", "", "always", "QA_TESTING"),
        ("sql_business_reporting", "Data Analyst", "Use SQL and Excel to prepare sales reports.", "never", None),
        ("database_admin_weak_context", "Data Analyst", "Oversee database management for data entry and SQL reports.", "never", None),
        ("database_context_without_admin_task", "Data Analyst", "Use a database to report on data storage, retrieval, and security.", "never", None),
        ("database_admin_company", "Data Analyst", "About us:\nWe oversee database management activities including data storage, retrieval, and security.", "never", None),
        ("database_admin_qualification", "Data Analyst", "Qualifications: Oversee database management activities including data storage, retrieval, and security.", "never", None),
        ("database_admin_other_actor", "Data Analyst", "Help engineers who oversee database management activities including data storage, retrieval, and security.", "never", None),
        ("database_admin_negated", "Data Analyst", "You are not responsible for tasks to oversee database management activities including data storage, retrieval, and security.", "never", None),
        ("database_admin_cross_unit", "Data Analyst", "Oversee database management. Data storage, retrieval, and security.", "never", None),
        ("etl_company", "BI Analyst", "About us: We create etl pipelines using SQL.", "never", None),
        ("etl_qualification", "BI Analyst", "Qualifications: You will create etl pipelines using SQL.", "never", None),
        ("etl_other_actor", "BI Analyst", "Help engineers who create etl pipelines using SQL.", "never", None),
        ("etl_collaboration", "BI Analyst", "Work with engineers to create etl pipelines using SQL.", "never", None),
        ("etl_negated", "BI Analyst", "You are not responsible for tasks to create etl pipelines using SQL.", "never", None),
        ("cyber_qualification", "Digital Forensics Analyst", "Qualifications: You will respond to cyber incidents.", "never", None),
        ("cyber_negated", "Digital Forensics Analyst", "You are not responsible for tasks to respond to cyber incidents.", "never", None),
        ("physical_security", "Security Officer II", "Patrol and monitor facility premises.", "never", None),
        ("physical_equipment_testing", "Senior Test Engineer", "Build computer-automated test equipment for manufacturing and calibration.", "never", None),
        ("qualifications_heading_barrier", "Engineer", "About us:\nOur company builds tools.\nRole Description\nPrepare documentation.\nQualifications And Education Requirements\nDevelop software in Java.", "never", None),
        ("required_skills_barrier", "Engineer", "About us:\nOur company builds tools.\nRole Description:\nPrepare documentation.\nRequired Skills & Experience:\nDevelop software in Java.", "never", None),
        ("desired_skills_barrier", "Engineer", "About us:\nOur company builds tools.\nRole Description\nPrepare documentation.\nDesired Skills & Experience\nDevelop software in Java.", "never", None),
        ("benefits_heading_barrier", "Engineer", "About us:\nOur company builds tools.\nRole Description\nPrepare documentation.\nDescription Of Benefits\nDevelop software in Java.", "never", None),
        ("implicit_heading_colon_not_enabled", "Engineer", "Qualifications:\nExperience with Java skillsResponsibilities: Develop software in Java.", "never", None),
        ("implicit_job_description_not_enabled", "Engineer", "About us:\nOur company builds tools.\nThe OpportunityJob Description: Develop software in Java.", "never", None),
        ("implicit_duties_not_enabled", "Engineer", "About us:\nOur company builds tools.\nDaily ResponsibilitiesDevelop software in Java.", "never", None),
        ("running_text_not_heading", "Engineer", "About us:\nOur company describes the role description of our clients who develop software in Java.", "never", None),
    ]


def run_controls(model, applied):
    results = []
    for name, title, description, activation, group in controls():
        p = checked_prediction(model, title, description)
        active = activation == "always" or activation in applied
        expected = ("ACCEPT", group) if active else ("REVIEW", None)
        assert (p["it_decision"], p["primary_group_code"]) == expected, (name, applied, p)
        if group == "SOFTWARE" and active:
            assert p["subgroup_code"] == "SOFTWARE_OTHER"
        results.append(dict(name=name, activation=activation, expected=expected, prediction=p))
    # Hard exclusions, conflict, and the closed fallback remain separate controls.
    for title, desc, expected in [
        ("Financial Analyst", "Use SQL and Oracle reports for budgets.", "REJECT"),
        ("CNC Programmer", "Operate manufacturing equipment.", "REJECT"),
        ("Security Guard", "Patrol the premises.", "REJECT"),
        ("Software Engineer / Financial Analyst", "", "REVIEW"),
        ("Mystery Operator", "You will create etl pipelines using SQL.", "REJECT"),
    ]:
        p = checked_prediction(model, title, desc)
        assert p["it_decision"] == expected, (title, applied, p)
        results.append(dict(name=title, expected=expected, prediction=p))
    assert model.check_illustrative_cases() == 57
    return results


def load_sources():
    frozen = read_json(RUN / "baseline/source_rows.json")
    by_source = {rel: audit_helpers.keyed(rows) for rel, rows in frozen.items()}
    assert len(by_source[SEED]) == 160 and len(by_source[DOWN]) == 17
    for rel, (sheet, _) in audit_helpers.SOURCES.items():
        assert audit_helpers.read_sheet(ROOT / rel, sheet)["rows"] == frozen[rel]
    shared = set(by_source[SEED]) & set(by_source[DOWN])
    assert shared == {"3905848702"}
    assert all(all(by_source[SEED][j][f] == by_source[DOWN][j][f] for f in audit_helpers.MANUAL) for j in shared)
    union = dict(by_source[SEED])
    union.update(by_source[DOWN])
    assert len(union) == 176
    return by_source, union


def baseline_predictions(union):
    def load(name):
        with (RUN / "baseline/predictions" / name).open(encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]
    main = audit_helpers.keyed(load("seed42_v020_predictions_private.jsonl"))
    extra = audit_helpers.keyed([r["new_prediction"] for r in load("accept_downgrade_predictions_private.jsonl")])
    assert len(main) == 160 and len(extra) == 17
    pred = dict(main)
    for j, p in extra.items():
        if j in pred:
            assert all(pred[j][k] == v for k, v in p.items())
        pred[j] = p
    assert set(pred) == set(union)
    for j, row in union.items():
        assert all(row[f] == pred[j][f] for f in ["title", "description"])
        assert pred[j]["taxonomy_version"] == "0.2.0"
        assert pred[j]["taxonomy_sha256"] == sha256(RUN / "baseline/it_taxonomy_v0.2.0.json")
    return pred


def fraction(n, d):
    return dict(numerator=n, denominator=d, rate=n/d if d else None)


def metrics(data, pred):
    c = collections.Counter((r["manual_label"], pred[j]["it_decision"]) for j, r in data.items())
    matrix = {s: {l: c[(l,s)] for l in ["CNTT", "NGOAI_CNTT", "CHUA_RO"]} for s in ["ACCEPT", "REJECT", "REVIEW"]}
    tp, tn, fp, fn = c[("CNTT", "ACCEPT")], c[("NGOAI_CNTT", "REJECT")], c[("NGOAI_CNTT", "ACCEPT")], c[("CNTT", "REJECT")]
    clear = sum(r["manual_label"] != "CHUA_RO" for r in data.values())
    decided = sum(r["manual_label"] != "CHUA_RO" and pred[j]["it_decision"] != "REVIEW" for j, r in data.items())
    accepted = {j:r for j,r in data.items() if r["manual_label"] == "CNTT" and pred[j]["it_decision"] == "ACCEPT"}
    software = {j:r for j,r in accepted.items() if r["manual_primary_group_code"] == pred[j]["primary_group_code"] == "SOFTWARE"}
    return dict(rows=len(data), matrix=matrix, tp=tp, tn=tn, fp=fp, fn=fn, chua_ro=len(data)-clear,
                review=sum(pred[j]["it_decision"] == "REVIEW" for j in data),
                membership_on_decided=fraction(tp+tn, decided), decision_coverage_clear=fraction(decided, clear),
                decision_coverage_all=fraction(sum(pred[j]["it_decision"] != "REVIEW" for j in data), len(data)),
                correct_decisions_on_clear=fraction(tp+tn, clear), precision_decided=fraction(tp, tp+fp),
                recall_decided=fraction(tp, tp+fn), accept_capture_all_manual_it=fraction(tp, sum(r["manual_label"] == "CNTT" for r in data.values())),
                primary_group=fraction(sum(r["manual_primary_group_code"] == pred[j]["primary_group_code"] for j,r in accepted.items()),len(accepted)),
                software_subgroup=fraction(sum(r["manual_subgroup_code"] == pred[j]["subgroup_code"] for j,r in software.items()),len(software)))


def compare(old, new, union):
    changes = []
    regressions = []
    for j in sorted(union, key=int):
        row, a, b = union[j], old[j], new[j]
        fields = [f for f in DETAIL if a[f] != b[f]]
        if fields:
            changes.append(dict(job_id=j, title=row["title"], manual_label=row["manual_label"],
                                manual_group=row["manual_primary_group_code"], manual_subgroup=row["manual_subgroup_code"],
                                changed_fields=fields, before={f:a[f] for f in fields}, after={f:b[f] for f in fields}))
        if row["manual_label"] == "NGOAI_CNTT" and a["it_decision"] != "ACCEPT" and b["it_decision"] == "ACCEPT":
            regressions.append(dict(job_id=j, type="NEW_FALSE_POSITIVE"))
        if row["manual_label"] == "CNTT" and b["it_decision"] == "ACCEPT":
            # A newly accepted case must not introduce a wrong primary group.
            if b["primary_group_code"] != row["manual_primary_group_code"] and (a["it_decision"] != "ACCEPT" or a["primary_group_code"] != b["primary_group_code"]):
                regressions.append(dict(job_id=j, type="NEW_WRONG_PRIMARY_GROUP"))
            if b["primary_group_code"] == row["manual_primary_group_code"] == "SOFTWARE" and b["subgroup_code"] != row["manual_subgroup_code"] and (a["it_decision"] != "ACCEPT" or a["subgroup_code"] != b["subgroup_code"]):
                regressions.append(dict(job_id=j, type="NEW_WRONG_SUBGROUP"))
        if row["manual_label"] == "CNTT" and a["it_decision"] == "ACCEPT" and b["it_decision"] != "ACCEPT":
            regressions.append(dict(job_id=j, type="LOST_TRUE_POSITIVE"))
    return changes, regressions


def write_trace(path, pred):
    with path.open("x", encoding="utf-8") as stream:
        for j in sorted(pred, key=int):
            stream.write(json.dumps(pred[j], ensure_ascii=False) + "\n")


def preservation():
    before = read_json(RUN / "protected_before.json")
    audit_helpers.RUN = RUN
    after = audit_helpers.inventory()
    allowed = {"src/it_taxonomy.py"}  # Only the allowlisted candidate version changes existing code.
    changed = [p for p,v in before.items() if after.get(p) != v]
    assert set(changed) <= allowed, changed
    git = audit_helpers.git_state()
    old = read_json(RUN / "git_before.json")
    assert git == {k:old[k] for k in git}
    status = subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=ROOT).decode("utf-8")
    assert set(old["status_porcelain"].splitlines()) <= set(status.splitlines())
    return dict(existing_artifacts=len(before), protected_existing_artifacts=len(before)-len(allowed),
                protected_hash_size_mtime_unchanged=True, existing_modified_paths=changed,
                added_paths=sorted(set(after)-set(before)), git_head_index_tracked_diff_unchanged=True,
                preexisting_git_status_preserved=True, old_active_config_sha256=sha256(ROOT / "config/it_taxonomy.json"))


def run():
    assert not (RUN / "comparison_summary.json").exists()
    preservation()
    source, union = load_sources()
    baseline = baseline_predictions(union)
    original_model = Taxonomy(RUN / "baseline/it_taxonomy_v0.2.0.json")
    for j,row in union.items():
        replay = checked_prediction(original_model,row["title"],row["description"],j)
        assert all(baseline[j][k] == v for k,v in replay.items()), (j,"Baseline replay changed")
    run_controls(original_model, [])
    previous, stage_results = baseline, []
    for index, name in enumerate(STAGES,1):
        folder = stage_folder(index,name)
        config = read_json(folder / "config.json")
        applied = STAGES[:index]
        assert_scope(config,applied)
        model = Taxonomy(folder / "config.json")
        fixtures = run_controls(model,applied)
        candidate = {j:checked_prediction(model,r["title"],r["description"],j) for j,r in union.items()}
        changes, regressions = compare(previous,candidate,union)
        stage_result = dict(stage=name, applied=applied, config_sha256=model.sha256, jobs_classified=len(candidate),
                            fixture_cases=len(fixtures), illustrative_cases=57, changes=changes, regressions=regressions,
                            sources={rel:metrics(data,candidate) for rel,data in source.items()})
        write_json(folder / "fixture_results.json",fixtures,exclusive=True)
        write_json(folder / "delta.json",stage_result,exclusive=True)
        write_trace(folder / "predictions.jsonl",candidate)
        if regressions:
            raise RuntimeError(f"Stage {name} regressed: {regressions}; candidate not finalized")
        print(json.dumps(dict(stage=name,changed_jobs=len(changes),changed_states=sum("it_decision" in c["changed_fields"] for c in changes),
                              regressions=regressions),ensure_ascii=False),flush=True)
        stage_results.append(stage_result)
        previous = candidate
    assert sha256(CANDIDATE) == stage_results[-1]["config_sha256"]
    final, changes = previous, compare(baseline,previous,union)[0]
    write_trace(RUN / "all_predictions.jsonl",final)
    for rel,name in [(SEED,"seed42_v021_predictions_private.jsonl"),(DOWN,"supplement17_v021_predictions_private.jsonl")]:
        records = {j:dict(final[j], **({"sample_id":r["sample_id"]} if "sample_id" in r else {})) for j,r in source[rel].items()}
        write_trace(RUN / name,records)
    csv_changes = []
    for j,row in sorted(union.items(),key=lambda pair:int(pair[0])):
        a,b = baseline[j],final[j]
        fields = [f for f in DETAIL if a[f]!=b[f]]
        csv_changes.append(dict(job_id=j,title=row["title"],sources=";".join(n for rel,n in [(SEED,"seed42"),(DOWN,"supplement17")] if j in source[rel]),
                                manual_label=row["manual_label"],manual_group=row["manual_primary_group_code"],manual_subgroup=row["manual_subgroup_code"],
                                before_decision=a["it_decision"],after_decision=b["it_decision"],before_group=a["primary_group_code"],after_group=b["primary_group_code"],
                                before_subgroup=a["subgroup_code"],after_subgroup=b["subgroup_code"],changed_fields=";".join(fields),
                                changed_stages=";".join(s["stage"] for s in stage_results if any(c["job_id"]==j for c in s["changes"])),
                                before_rules=";".join(a["matched_rule_ids"]),after_rules=";".join(b["matched_rule_ids"]),
                                before_reasons=";".join(a["reason_codes"]),after_reasons=";".join(b["reason_codes"])))
    write_csv(RUN / "job_comparison.csv",csv_changes,list(csv_changes[0]),exclusive=True,bom=True)
    remaining_fn = [dict(job_id=j,title=r["title"],sources=[rel for rel in source if j in source[rel]],group=r["manual_primary_group_code"],
                         manual_reason=r["manual_reason"],manual_evidence=r["manual_evidence"],reason_codes=final[j]["reason_codes"],
                         matched_rule_ids=final[j]["matched_rule_ids"]) for j,r in union.items() if r["manual_label"]=="CNTT" and final[j]["it_decision"]=="REJECT"]
    summary = dict(date=DATE,timezone="Asia/Bangkok",candidate_version=VERSION,candidate_config=str(CANDIDATE.relative_to(ROOT)),
                   candidate_config_sha256=sha256(CANDIDATE),status="ROUND1_CANDIDATE_NOT_A04_ACCEPTANCE",
                   scope=STAGES,deferred=["P1b","P3","P4","P5"],source_rows=177,unique_jobs=176,common_job="3905848702",
                   baseline_replay_exact=True,sources={rel:dict(before=metrics(data,baseline),after=metrics(data,final)) for rel,data in source.items()},
                   stages=[{k:v for k,v in s.items() if k not in {"changes","sources"}} | dict(changed_jobs=len(s["changes"]),
                           state_changed_jobs=[c["job_id"] for c in s["changes"] if "it_decision" in c["changed_fields"]]) for s in stage_results],
                   cumulative_changes=changes,remaining_fn=remaining_fn,
                   review_unique_before=sum(p["it_decision"]=="REVIEW" for p in baseline.values()),
                   review_unique_after=sum(p["it_decision"]=="REVIEW" for p in final.values()),
                   tests=read_json(RUN / "tests_result.json"),preservation=preservation(),
                   classifier_data_scope="176 frozen jobs; synthetic/design/existing diagnostic fixtures only",etl_rerun=False,
                   full_dataset_classification=False,a05_performed=False,commit_performed=False,push_performed=False,
                   evaluation="RULE_DEVELOPMENT_SAMPLE_NOT_INDEPENDENT_EVALUATION",spark_jvm_parity="NOT_VERIFIED")
    assert summary["tests"]["successful"]
    write_json(RUN / "comparison_summary.json",summary,exclusive=True)
    render_report(summary,stage_results,baseline,final,union)
    outputs = {str(p.relative_to(RUN)):sha256(p) for p in RUN.rglob("*") if p.is_file() and "baseline" not in p.relative_to(RUN).parts and p.name!="run_manifest.json"}
    implementation = {str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/"src"/name for name in [
        "it_taxonomy.py", "description_processing.py", "it_taxonomy_v010.py", "tv2_csv.py", "compare_a04_versions.py",
        "prepare_a04.py", "apply_a04_decisions.py", "test_a04_round1.py", "a04_filter_fix_round1.py"]]}
    manifest = dict(date=DATE,version=VERSION,purpose=summary["evaluation"],candidate_config_sha256=sha256(CANDIDATE),
                    baseline_manifest="baseline/manifest.json",implementation_sha256=implementation,output_sha256=outputs,
                    python=platform.python_version(),python_executable=sys.executable,source_rows=177,unique_jobs=176,
                    full_dataset_classification=False,etl_rerun=False,preservation=preservation(),
                    report_sha256=sha256(ROOT/"docs/a04_filter_fix_round1_report.md"))
    write_json(RUN / "run_manifest.json",manifest,exclusive=True)
    write_json(ROOT/"data/audit/tv2_a04_filter_fix_round1_20261014.json",manifest,exclusive=True)
    print(json.dumps({k:summary[k] for k in ["source_rows","unique_jobs","review_unique_before","review_unique_after","sources"]},ensure_ascii=False,indent=2))


def fmt(v):
    n,d,rate = v["numerator"],v["denominator"],v["rate"]
    return f"{n}/{d} = {rate*100:.2f}%" if rate is not None else f"{n}/{d}: không xác định"


def render_report(summary,stages,old,new,union,*,overwrite=False):
    sections = []
    for rel,title in [(SEED,"Mẫu chính 160"),(DOWN,"Mẫu bổ sung 17")]:
        before,after = summary["sources"][rel]["before"],summary["sources"][rel]["after"]
        table = "\n".join(f"| {label} | {fmt(before[k])} | {fmt(after[k])} |" for label,k in [
            ("Khớp membership khi máy quyết định","membership_on_decided"),("Độ phủ trên nhãn rõ","decision_coverage_clear"),
            ("Độ phủ trên toàn mẫu","decision_coverage_all"),("Quyết định đúng trên nhãn rõ","correct_decisions_on_clear"),
            ("Precision trên ACCEPT nhãn rõ","precision_decided"),("Recall có điều kiện trên ACCEPT/REJECT","recall_decided"),
            ("ACCEPT trên tất cả CNTT duyệt","accept_capture_all_manual_it"),("Khớp nhóm trên ACCEPT/CNTT","primary_group"),
            ("Khớp subgroup khi cả hai nhóm SOFTWARE","software_subgroup")])
        sections.append(f"### {title}\n\n| Đại lượng | v0.2.0 | v0.2.1 candidate |\n| --- | --- | --- |\n"
                        + "\n".join(f"| {k.upper()} | {before[k]} | {after[k]} |" for k in ["tp","tn","fp","fn","review","chua_ro"])
                        + f"\n\n| Tỷ lệ, mẫu số | Trước | Sau |\n| --- | --- | --- |\n{table}\n\n"
                        + "**Ma trận candidate**\n\n" + audit_helpers.matrix_md(after["matrix"]).replace("Máy v0.2.0","Máy candidate") + "\n")
    stage_table = "\n".join(f"| {s['stage']} | {len(s['changes'])} | {sum('it_decision' in c['changed_fields'] for c in s['changes'])} | {len(s['regressions'])} |" for s in stages)
    changes = []
    for c in summary["cumulative_changes"]:
        j = c["job_id"]
        phases = ", ".join(s["stage"] for s in stages if any(d["job_id"]==j for d in s["changes"]))
        a,b = old[j],new[j]
        changes.append(f"| `{j}` | {c['title'].replace('|',' / ')} | {a['it_decision']} → {b['it_decision']} | {a['primary_group_code'] or 'NULL'} → {b['primary_group_code'] or 'NULL'} | {phases} | {', '.join(c['changed_fields'])} |")
    fn = "\n".join(f"| `{e['job_id']}` | {e['title'].replace('|',' / ')} | {e['group']} | {'; '.join(e['reason_codes'])} |" for e in summary["remaining_fn"])
    total_new_accept = sum(old[j]["it_decision"]!="ACCEPT" and new[j]["it_decision"]=="ACCEPT" for j in union)
    state_explanations = []
    evidence_sets = {"P2_ETL": {"data_tasks"}, "P2_CYBER": {"security_tasks", "security_context"},
                     "P2_SOFTWARE_TITLE": {"software_titles"},
                     "P2_DATABASE": {"database_admin_tasks", "database_admin_objects", "database_admin_context"}}
    for change in summary["cumulative_changes"]:
        if "it_decision" not in change["changed_fields"]:
            continue
        job = change["job_id"]
        phase = next(s["stage"] for s in stages if any(c["job_id"]==job and "it_decision" in c["changed_fields"] for c in s["changes"]))
        record = new[job]
        quotes = []
        for evidence in record["match_evidence"]:
            if evidence["term_set_id"] in evidence_sets[phase]:
                ranges = ", ".join(f"[{a},{b})" for a,b in evidence["raw_match_ranges"])
                location = evidence["field"]
                if evidence["field"] == "description":
                    location += f" s{evidence['segment_index']} / {evidence['section']}"
                quotes.append(f"`{evidence['matched_alias']}` ({location}, {ranges})")
        state_explanations.append(f"| `{job}` | {phase} | {record['selected_rule_id']}; {'; '.join(record['reason_codes'])} | "
                                  f"{record['primary_group_code']} / {record['subgroup_code'] or 'NULL'} | {'; '.join(quotes)} |")
    text = f"""# A04 – Báo cáo đợt sửa 1: P1a/P2, candidate v0.2.1

Ngày **14/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`. **Chưa nghiệm thu A04, chưa đánh giá độc lập.**

Đã triển khai đúng P1a và bốn entry P2 theo [phương án](a04_filter_fix_plan.md). Candidate ở [config/versions/it_taxonomy_v0.2.1.json](../config/versions/it_taxonomy_v0.2.1.json), SHA-256 `{summary['candidate_config_sha256']}`; `config/it_taxonomy.json` vẫn v0.2.0. P1b/P3/P4/P5 chưa triển khai. Không nhận heading implicit dính chữ, không mở fallback, không đổi tier/priority/conflict/blocker.

## Baseline và bảo toàn

- [Snapshot baseline](../data/analytics/a04_taxonomy_v0_2_1_20261014/baseline/manifest.json) giữ exact config/code và bản sao các dự đoán 160/17 đã lưu; [snapshot v0.2.0 trong config/versions](../config/versions/it_taxonomy_v0.2.0.json) SHA-256 `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d`. Full trace cũ chỉ đọc hash, giữ nguyên; không chạy toàn dataset.
- Frozen nguồn đủ **160 + 17 dòng / 176 job_id**, JOIN theo job_id; ca chung `3905848702` giữ một prediction chung và nhãn hai nguồn khớp. Reviewer Dũng, ngày 2026-10-13, raw/workbook/trace/báo cáo và mọi thay đổi có sẵn giữ nguyên.
- Replay v0.2.0 trên 176 khóa khớp toàn bộ trường trả về của trace lưu, gồm decision/group/subgroup/reason/evidence/segments/processing. Code cũ được snapshot trước chỉnh sửa; file có sẵn duy nhất được sửa là `src/it_taxonomy.py`, thêm v0.2.1 vào allowlist version cho cùng processor structured-source-v1.

## Sửa đổi thực tế theo thứ tự

1. **P1a**: ROLE thêm `role description`; RESPONSIBILITIES thêm `essential duties and responsibilities`, `job duties and responsibilities`; QUALIFICATIONS thêm `qualifications and education requirements`, `required skills & experience`, `desired skills & experience`, `skills`; BENEFITS thêm `what we have to offer`, `description of benefits`, `compensation & benefits details`. Chỉ dạng explicit hiện được parser hỗ trợ (standalone/colon với boundary hợp lệ), không sửa parser. Qualification/benefits barriers được kiểm tra cùng role reset để tránh biến yêu cầu năng lực thành task.
2. **P2_ETL**: thêm đúng hai literal `creating etl pipeline`, `create etl pipelines` vào data_tasks, giữ title hint và same-unit context của DATA_AI_CONTEXT. Không thêm verb chung, không stemming và không dùng SQL/Excel đơn lẻ.
3. **P2_CYBER**: thêm `cyber incidents` vào security_context, chỉ hữu ích khi cùng task bảo mật hiện có và eligible actor/unit. Không thêm security officer/clearance làm nghề cyber.
4. **P2_SOFTWARE_TITLE**: thêm phrase `software development engineer` vào software_titles; tier/priority vẫn cũ, SDET/Software Development Engineer in Test giữ QA_TESTING.
5. **P2_DATABASE**: không thêm `oversee database management` vào data_tasks chung. DATA_AI_CONTEXT giữ title hint, còn nhánh context là ANY của nhánh cũ và SAME_SEGMENT gồm `database_admin_tasks`=`oversee database management`, object `database/databases`, context cụ thể `data storage, retrieval, and security` hoặc dạng không Oxford comma. Cả ba phải cùng eligible unit/cửa sổ với blockers cũ. Chỉ dùng schema 1 hiện có (all/any/same_segment), không thêm rule ID, tier/priority hoặc nới context chung. Weak context, reporting, company, qualification, actor khác và negation đều có đối chứng.

## Kiểm tra và delta riêng

**{summary['tests']['tests_run']} test unittest đã qua**, gồm bộ hiện hữu và fixture mới; mỗi stage có **{stages[0]['fixture_cases']} control** và **57 ca minh họa**. Kiểm tra decision/is_it/group/subgroup/reason, rule candidates, raw excerpt/ranges và normalized alias, mapping và blockers. Baseline replay không đổi. Dữ liệu mỗi stage giới hạn 176 job; fixture/test là ca tổng quát và các specimen kiểm tra hiện hữu, không phải lần chạy toàn dataset.

| Stage tích lũy, so với stage trước | Job thay bất kỳ chi tiết | Job đổi trạng thái | Hồi quy FP/nhóm/subgroup/TP |
| --- | ---: | ---: | ---: |
{stage_table}

Các delta lưu riêng dưới [stages](../data/analytics/a04_taxonomy_v0_2_1_20261014/stages/), mỗi thư mục có config/hash, fixtures, predictions và delta; không dùng một tỷ lệ tổng để che tác động entry riêng. Tổng cộng **{total_new_accept} job mới ACCEPT**; không phát hiện FP mới/đổi nhóm sai/subgroup sai hoặc mất TP trên 176 ca và controls. Không cần thu hồi hạng mục. Số bất đồng nhóm/subgroup cũ vẫn được báo theo nhãn đã duyệt, không sửa nhãn để khớp máy.

## Kết quả tính lại trước/sau

JOIN từng workbook với prediction theo job_id, tính từ dữ liệu; CHUA_RO giữ riêng, REVIEW không biến thành REJECT/FN. Tỷ lệ khớp khi máy quyết định dùng nhãn rõ và ACCEPT/REJECT; độ phủ nhãn rõ dùng cùng số ca chia CNTT+NGOAI_CNTT. Tỷ lệ quyết định đúng trên nhãn rõ tính REVIEW là chưa tạo quyết định đúng; precision/recall có điều kiện loại REVIEW/CHUA_RO. Đây là **mẫu phát triển đã dùng sửa/rà soát**, không accuracy toàn dataset hoặc đánh giá độc lập.

{chr(10).join(sections)}
Hợp hai mẫu: REVIEW **{summary['review_unique_before']} → {summary['review_unique_after']} job_id duy nhất**; không cộng trùng ca chung. 4 CHUA_RO đã duyệt giữ nguyên, không dùng làm negative gold.

## Giải thích mọi delta

**Bốn chuyển REVIEW → ACCEPT**, đều khớp nhóm người duyệt; subgroup SOFTWARE_OTHER của Software Development Engineer cũng khớp nhãn. Trước sửa cả bốn có reason AMBIGUOUS_TITLE_WITHOUT_CONTEXT, không rule/evidence positive. Sau sửa có predicate và nguồn cụ thể dưới đây; UNKNOWN là section eligible theo chính sách cũ, không phải qualification/company được mở chặn.

| job_id | Entry | Rule thắng; reason mới | Nhóm / subgroup sau | Alias chứng cứ và raw ranges |
| --- | --- | --- | --- | --- |
{chr(10).join(state_explanations)}

P2_ETL giữ data/BI title hint và context ETL/SQL/Python trong cùng s2; P2_CYBER ghép task bảo mật hiện có với context cyber incidents cùng s2. P2_SOFTWARE_TITLE dùng đúng occupational phrase ở title, không đổi DATA_AI theo tên đội. P2_DATABASE giữ title Data Analyst và cả ba task/object/context trong s17 RESPONSIBILITIES; SQL/ML ở qualification không cấp evidence. Không có chuyển REJECT → ACCEPT, không đổi nhóm/subgroup của ca đã ACCEPT trước đợt sửa, không thay 4 nhãn CHUA_RO.

**Toàn bộ {len(summary['cumulative_changes'])} ca có delta chi tiết** ({len(stages[0]['changes'])} cấu trúc P1a và {total_new_accept} trạng thái P2) được liệt kê dưới đây. Các ca khác không đổi trường quyết định hoặc chi tiết ngoài version/hash.

| job_id | Title | Trạng thái trước → sau | Nhóm trước → sau | Entry gây delta | Trường khác (không tính version/hash) |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(changes)}

[job_comparison.csv](../data/analytics/a04_taxonomy_v0_2_1_20261014/job_comparison.csv) có đủ **176 khóa**, gồm cả ca không đổi; [comparison_summary.json](../data/analytics/a04_taxonomy_v0_2_1_20261014/comparison_summary.json) và từng stage delta giữ giá trị trước/sau đầy đủ cho cả metadata xử lý, section/actor, evidence và raw ranges. Mẫu riêng 160/17 giữ đủ 177 dòng nguồn trong hai trace mới. Heading P1a có thể đổi section/index/blocked reasons ở ca vẫn REVIEW/REJECT/ACCEPT; những thay đổi này được liệt kê, không gọi chúng là sửa membership. Các ca nhận mới bởi P2 có task/phrase cụ thể và rule tương ứng trong delta, không dựa job_id/doanh nghiệp.

## FN còn lại và bước P3 để lựa chọn

| job_id | Title | Nhóm người duyệt | Reason candidate |
| --- | --- | --- | --- |
{fn}

Đợt P1a/P2 xử lý độ phủ nhỏ; không cam kết chữa hết FN. Đề xuất bước tiếp theo để chốt: P3 task integration/coding/maintenance cho Workday/Programmer; IT delivery cho Scrum Master; support task/object cho PACS (heading đã mở nhưng hint/task còn thiếu); vận hành OS/network/backup cho ECC với kiểm tra nhóm. Oracle cần cả P3 positive functional ERP và P4 exclusion, không xử lý bằng alias chung. SAP BTP/Lead Research Scientist vẫn cần P5 về profile/nhiệm vụ; không mở qualification để nhận họ. Chưa triển khai các đề xuất này trong round 1.

Các REVIEW còn lại, nhất là Privacy/implicit heading, domain conflict, UI/application support và 16 ca ngoài CNTT, không bị ép ACCEPT. Tiêu chí vẫn theo [a04_completion_criteria.md](a04_completion_criteria.md): còn chốt xử lý phần lỗi còn lại và xác nhận nghiệm thu. TV1 cần đối soát cùng candidate JSON/code/fixture trên Spark/JVM, nhất là heading, Unicode code point/UTF-16, source mapping/raw ranges, nullability và tier/priority; parity chưa được xác minh, thuộc tích hợp D06.

## Hiện vật và phạm vi chạy

[Runner](../src/a04_filter_fix_round1.py), [fixture tests](../src/test_a04_round1.py), [run manifest](../data/analytics/a04_taxonomy_v0_2_1_20261014/run_manifest.json) và [audit](../data/audit/tv2_a04_filter_fix_round1_20261014.json) lưu nguồn/hash/kiểm tra. Dùng runner `--prepare` trên baseline đã đóng băng rồi chạy unittest và runner trong output mới; runner từ chối ghi đè output. Active config/trace cũ vẫn phục vụ v0.2.0, candidate phải được chỉ định bằng đường dẫn version riêng.

Không chạy ETL/toàn dataset, không làm A05, không commit/push, không tự đánh dấu A04 hoàn thành. Không sửa raw/job_id/title/description/nhãn/reviewer/ngày duyệt hoặc quyết định phạm vi P5.
"""
    target = ROOT / "docs/a04_filter_fix_round1_report.md"
    with target.open("w" if overwrite else "x",encoding="utf-8") as stream:
        stream.write(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare",action="store_true")
    args = parser.parse_args()
    prepare() if args.prepare else run()
