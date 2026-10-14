"""Stage the three authorized P3 families on the frozen 176-job A04 sample.

No raw-row/ETL/full-dataset runner, label writes, active-config promotion or
overwrite of prior runs. --prepare builds cumulative schema-1 configs; default
runs controls, exact baseline replay and per-stage/sample comparisons.
"""
from __future__ import annotations

import argparse
import copy
import json
import platform
import subprocess
import sys

import apply_a04_decisions as a
import a04_filter_fix_round1 as r1
from it_taxonomy import Taxonomy
from tv2_csv import ROOT, sha256, write_csv, write_json

RUN = ROOT / "data/analytics/a04_taxonomy_v0_2_2_20261014"
CANDIDATE = ROOT / "config/versions/it_taxonomy_v0.2.2.json"
VERSION, DATE = "0.2.2", "2026-10-14"
STAGES = ["P3_INTEGRATION", "P3_APPLICATION_MAINTENANCE_MIGRATION", "P3_IT_DELIVERY"]
read_json, checked_prediction, metrics, compare, write_trace, fmt = (
    r1.read_json, r1.checked_prediction, r1.metrics, r1.compare, r1.write_trace, r1.fmt)


def match_title(term_set):
    return {"match": {"field": "title", "term_set": term_set}}


def same(*term_sets):
    return {"same_segment": {"field": "description", "all_term_sets": list(term_sets)}}


def app_role():
    # A software hint is retained; a programmer/developer hint makes support
    # and maintenance duties specific to application code rather than helpdesk.
    return {"all": [match_title("software_hints"), match_title("application_code_role_hints")]}


def migration():
    return {"all": [app_role(), same("application_migration_tasks", "application_migration_objects",
                                    "application_migration_origin", "application_migration_target")]}


def append_or(rule, branches):
    old = rule["condition"]
    if "any" not in old:
        rule["condition"] = {"any": [old]}
    rule["condition"]["any"].extend(branches)


def add_terms(config, values):
    assert set(values).isdisjoint(config["term_sets"])
    for name, (purpose, aliases) in values.items():
        config["term_sets"][name] = dict(purpose=purpose, aliases=aliases)


def patch(config, stage):
    software = next(r for r in config["include_rules"] if r["id"] == "SOFTWARE_CONTEXT")
    if stage == "P3_INTEGRATION":
        add_terms(config, {
            "software_integration_title_hints": ("Integration is only a contextual role hint, never a direct IT title.", ["integration", "integrations"]),
            "software_integration_tasks": ("Explicit design/develop/test/deploy integration workflow, not use or coordination alone.", [
                "design, develop, test, deploy, and manage integration", "design, develop, test, and deploy integrations",
                "design, develop, test and deploy integrations", "design, develop, test, and deploy integration",
                "design, develop, test and deploy integration"]),
            "software_integration_objects": ("Integration artifact in the same duty unit.", ["integration", "integrations"]),
            "software_integration_context": ("Explicit software/application object; named product is a software-platform object, never employer evidence.", [
                "software applications", "software systems", "application systems", "application platform", "workday platform"]),
        })
        append_or(software, [{"all": [
            {"any": [match_title("software_hints"), match_title("software_integration_title_hints")]},
            same("software_integration_tasks", "software_integration_objects", "software_integration_context")]}])
    elif stage == "P3_APPLICATION_MAINTENANCE_MIGRATION":
        add_terms(config, {
            "application_code_role_hints": ("Coding occupation hint; Programmer is not a direct-title inclusion.", ["programmer", "developer"]),
            "application_maintenance_tasks": ("Explicit maintenance/support or maintenance/upgrade duty, not tool usage.", ["provide maintenance and support", "maintain and upgrade"]),
            "application_maintenance_objects": ("Application/system artifact; software typing is additionally required.", ["application", "applications", "systems"]),
            "application_maintenance_context": ("Software/application environment, not equipment maintenance.", [
                "software applications", "software systems", "web based systems", "web applications", "client server applications"]),
            "application_migration_tasks": ("Migration and upgrade duty owned by a coding role.", ["migrate and upgrade"]),
            "application_migration_objects": ("Migrated application/system artifact.", ["application", "applications", "systems"]),
            "application_migration_origin": ("Explicit client/server origin in the same migration unit.", ["client server environment"]),
            "application_migration_target": ("Explicit Web-based destination in the same migration unit.", ["web based environment"]),
        })
        append_or(software, [
            {"all": [app_role(), same("application_maintenance_tasks", "application_maintenance_objects", "application_maintenance_context")]},
            migration(),
        ])
        web = next(r for g in config["subgroups"] if g["code"] == "SOFTWARE_WEB" for r in g["rules"] if r["id"] == "SOFTWARE_WEB_CONTEXT")
        # Web comes from the owned migration duty, not qualification or a vendor.
        append_or(web, [migration()])
    elif stage == "P3_IT_DELIVERY":
        add_terms(config, {
            "it_project_delivery_tasks": ("Project ownership/delivery action, not Scrum ceremonies or backlog mentions.", [
                "manages all aspects", "manage all aspects", "successful execution of delivery", "manage project delivery"]),
            "it_project_delivery_objects": ("Explicit IT epic or information-system project, not generic IT or product backlog.", [
                "it epics", "it related epics", "information system projects", "information systems projects"]),
            "it_project_delivery_context": ("Planning/deployment/delivery context in the same owned duty unit.", [
                "planning to deployment", "planning the schedule", "project deployment", "system implementation"]),
        })
        business = next(r for r in config["include_rules"] if r["id"] == "IT_BUSINESS_CONTEXT")
        append_or(business, [{"all": [match_title("business_hints"),
                                     same("it_project_delivery_tasks", "it_project_delivery_objects", "it_project_delivery_context")]}])
    else:
        raise ValueError(stage)


def assert_scope(config, applied):
    base = read_json(RUN / "baseline/it_taxonomy_v0.2.1.json")
    expected = copy.deepcopy(base)
    for stage in applied:
        patch(expected, stage)
    metadata = {"version", "status", "revision_date", "changelog", "round2_candidate_stage"}
    assert set(config)-set(expected) <= metadata
    for key in expected:
        if key not in metadata:
            assert config[key] == expected[key], key
    for key in ["normalization", "inputs", "decision_policy", "rule_language", "groups", "general_it_rules", "exclusion_rules"]:
        assert config[key] == base[key], key
    for old,new in zip(base["include_rules"],config["include_rules"]):
        assert all(old[k] == new[k] for k in old if k != "condition")
        if old["id"] not in {"SOFTWARE_CONTEXT", "IT_BUSINESS_CONTEXT"}:
            assert old == new
    for old_group,new_group in zip(base["subgroups"],config["subgroups"]):
        assert all(old_group[k] == new_group[k] for k in old_group if k != "rules")
        for old,new in zip(old_group["rules"],new_group["rules"]):
            assert all(old[k] == new[k] for k in old if k != "condition")
            if old["id"] != "SOFTWARE_WEB_CONTEXT":
                assert old == new
    for name,value in base["term_sets"].items():
        assert config["term_sets"][name] == value, name
    assert config["schema_version"] == 1 and config["version"] == VERSION


def stage_folder(index,name):
    return RUN / "stages" / f"{index:02d}_{name}"


def prepare():
    assert RUN.exists() and not (RUN/"stages").exists() and not CANDIDATE.exists()
    base = read_json(RUN / "baseline/it_taxonomy_v0.2.1.json")
    config = copy.deepcopy(base)
    config.update(version=VERSION,status="round2_candidate_development_sample_only",revision_date=DATE)
    (RUN/"stages").mkdir()
    for index,name in enumerate(STAGES,1):
        patch(config,name)
        config["round2_candidate_stage"] = STAGES[:index]
        config["changelog"] = [dict(version=VERSION,date=DATE,applied=STAGES[:index],
                                    deferred=["P1b","P4","P5","P3_PACS","P3_ECC"],
                                    previous_config="config/versions/it_taxonomy_v0.2.1.json")] + base["changelog"]
        assert_scope(config,STAGES[:index])
        folder = stage_folder(index,name)
        folder.mkdir()
        write_json(folder/"config.json",config,exclusive=True)
    with CANDIDATE.open("xb") as stream:
        stream.write((folder/"config.json").read_bytes())
    print("Prepared three cumulative schema-1 stages; active v0.2.0 and v0.2.1 are unchanged.")


def fixtures():
    # Each row is a semantic control: expected outcome activates with its stage.
    wf = "design, develop, test, deploy, and manage integration"
    mig = "migrate and upgrade selected systems from a client/server environment to a Web-based environment"
    delivery = "manages all aspects of IT Epics from planning to deployment"
    return [
        ("integration_workflow", "Integration Developer", "Role Description: You will "+wf+" in Workday platform.", STAGES[0], "SOFTWARE", "SOFTWARE_OTHER", "REVIEW"),
        ("integration_general_software", "Integration Engineer", "Responsibilities: Design, develop, test, and deploy integrations between software applications.", STAGES[0], "SOFTWARE", "SOFTWARE_OTHER", "REVIEW"),
        ("integration_plural_hint", "Application Integrations Consultant", "Responsibilities: Design, develop, test, and deploy integrations between software applications.", STAGES[0], "SOFTWARE", "SOFTWARE_OTHER", "REVIEW"),
        ("migration_owned_role", "Programmer", "Role Description: This position will also "+mig+".", STAGES[1], "SOFTWARE", "SOFTWARE_WEB", "REJECT"),
        ("maintenance_owned_role", "Programmer", "Role Description: This position will provide maintenance and support for software applications.", STAGES[1], "SOFTWARE", "SOFTWARE_OTHER", "REJECT"),
        ("upgrade_owned_role", "Application Developer", "Role Description: You will maintain and upgrade software applications.", "always", "SOFTWARE", "SOFTWARE_OTHER", "ACCEPT"),
        ("it_epic_delivery", "Junior Scrum Master", "Responsibilities: The Scrum Master "+delivery+".", STAGES[2], "IT_BUSINESS", None, "REJECT"),
        ("information_system_delivery", "Project Manager", "Responsibilities: You manage project delivery for information system projects through system implementation.", STAGES[2], "IT_BUSINESS", None, "REVIEW"),
        ("product_only", "Workday Integration", "Use Workday platform for employee recruitment.", "never", None, None, "REJECT"),
        ("sap_product_only", "SAP Integration", "Use SAP for accounting reports.", "never", None, None, "REJECT"),
        ("hr_user", "Human Resources Specialist", "Use Workday platform to recruit and onboard employees.", "never", None, None, "REJECT"),
        ("accounting_user", "Financial Analyst", "Use Workday and SAP to prepare accounting reports.", "never", None, None, "REJECT"),
        ("integration_only", "Integration Engineer", "Coordinate integration activities.", "never", None, None, "REVIEW"),
        ("integration_no_software_object", "Integration Engineer", "You will "+wf+" between connected industrial systems.", "never", None, None, "REVIEW"),
        ("integration_qualification", "Integration Engineer", "Qualifications: You will "+wf+" in Workday platform.", "never", None, None, "REVIEW"),
        ("integration_company", "Integration Engineer", "Our clients "+wf+" in Workday platform.", "never", None, None, "REVIEW"),
        ("integration_other_actor", "Integration Engineer", "Help engineers who "+wf+" in Workday platform.", "never", None, None, "REVIEW"),
        ("integration_collaboration", "Integration Engineer", "Work with engineers to "+wf+" in Workday platform.", "never", None, None, "REVIEW"),
        ("integration_negated", "Integration Engineer", "You are not responsible for tasks to "+wf+" in Workday platform.", "never", None, None, "REVIEW"),
        ("integration_split_object", "Integration Engineer", "You will "+wf+". Workday platform.", "never", None, None, "REVIEW"),
        ("integration_missing_hint", "Operations Coordinator", "You will "+wf+" in Workday platform.", "never", None, None, "REJECT"),
        ("programmer_not_direct", "Programmer", "", "never", None, None, "REJECT"),
        ("qualification_only_programmer", "Programmer", "Qualifications: Develop applications in C#, .NET, Java, and JavaScript.", "never", None, None, "REJECT"),
        ("migration_qualification", "Programmer", "Qualifications: This position will "+mig+".", "never", None, None, "REJECT"),
        ("migration_company", "Programmer", "Our clients "+mig+".", "never", None, None, "REJECT"),
        ("migration_other_actor", "Programmer", "Help engineers who "+mig+".", "never", None, None, "REJECT"),
        ("migration_negated", "Programmer", "You are not responsible for tasks to "+mig+".", "never", None, None, "REJECT"),
        ("migration_no_origin", "Programmer", "You will migrate and upgrade selected systems to a Web-based environment.", "never", None, None, "REJECT"),
        ("migration_no_target", "Programmer", "You will migrate and upgrade selected systems from a client/server environment.", "never", None, None, "REJECT"),
        ("migration_split_target", "Programmer", "You will migrate and upgrade selected systems from a client/server environment. Web-based environment.", "never", None, None, "REJECT"),
        ("maintenance_equipment", "Programmer", "Provide maintenance and support for manufacturing equipment.", "never", None, None, "REJECT"),
        ("support_not_coding_role", "Support Engineer", "Provide maintenance and support for software applications.", "never", None, None, "REVIEW"),
        ("cnc_programmer", "CNC Programmer", "Maintain and upgrade CNC manufacturing equipment.", "never", None, None, "REJECT"),
        ("plc_programmer", "PLC Programmer", "Maintain and upgrade PLC control equipment.", "never", None, None, "REJECT"),
        ("scrum_only", "Scrum Master", "Facilitate Scrum ceremonies and keep the product backlog current.", "never", None, None, "REJECT"),
        ("generic_delivery", "Project Manager", "Manage project delivery through planning and deployment of construction projects.", "never", None, None, "REVIEW"),
        ("backlog_only", "Product Owner", "Manage the product backlog and prioritize work.", "never", None, None, "REJECT"),
        ("it_object_only", "Scrum Master", "Attend meetings about IT epics and software.", "never", None, None, "REJECT"),
        ("epic_no_deployment", "Scrum Master", "Manages all aspects of IT epics.", "never", None, None, "REJECT"),
        ("delivery_qualification", "Scrum Master", "Qualifications: The Scrum Master "+delivery+".", "never", None, None, "REJECT"),
        ("delivery_company", "Scrum Master", "Our clients manage all aspects of IT epics from planning to deployment.", "never", None, None, "REJECT"),
        ("delivery_other_actor", "Scrum Master", "Help teams who manage all aspects of IT epics from planning to deployment.", "never", None, None, "REJECT"),
        ("delivery_negated", "Scrum Master", "You are not responsible for tasks to manage all aspects of IT epics from planning to deployment.", "never", None, None, "REJECT"),
        ("delivery_split_scope", "Scrum Master", "Manages all aspects of IT epics. Planning to deployment.", "never", None, None, "REJECT"),
        ("sdet", "Software Development Engineer in Test", "", "always", "QA_TESTING", None, "ACCEPT"),
    ]


def run_controls(model,applied):
    previous_controls = r1.run_controls(model,r1.STAGES)
    results = []
    for name,title,desc,activation,group,subgroup,before in fixtures():
        active = activation == "always" or activation in applied
        expected = ("ACCEPT",group,subgroup) if active else (before,None,None)
        p = checked_prediction(model,title,desc)
        assert (p["it_decision"],p["primary_group_code"],p["subgroup_code"]) == expected, (name,applied,p)
        results.append(dict(name=name,activation=activation,expected=expected,prediction=p))
    return dict(round1=previous_controls,round2=results,design_cases=57)


def sources():
    frozen = read_json(RUN/"baseline/source_rows.json")
    by_source = {rel:a.keyed(rows) for rel,rows in frozen.items()}
    for rel,(sheet,count) in a.SOURCES.items():
        assert a.read_sheet(ROOT/rel,sheet)["rows"] == frozen[rel] and len(by_source[rel]) == count
    assert set(by_source[a.SEED]) & set(by_source[a.DOWN]) == {"3905848702"}
    assert all(by_source[a.SEED]["3905848702"][f] == by_source[a.DOWN]["3905848702"][f] for f in a.MANUAL)
    union = dict(by_source[a.SEED]); union.update(by_source[a.DOWN])
    assert len(union) == 176
    return by_source,union


def baseline_predictions(union):
    with (RUN/"baseline/predictions/all_predictions.jsonl").open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    pred = a.keyed(rows)
    assert len(pred) == 176 and set(pred) == set(union)
    for job,row in union.items():
        assert all(row[f] == pred[job][f] for f in ["title","description"])
        assert pred[job]["taxonomy_version"] == "0.2.1"
        assert pred[job]["taxonomy_sha256"] == sha256(RUN/"baseline/it_taxonomy_v0.2.1.json")
    return pred


def preservation():
    before = read_json(RUN/"protected_before.json")
    a.RUN = RUN
    after = a.inventory()
    mutable = {"src/it_taxonomy.py","src/test_a04_round1.py"}
    changed = [p for p,old in before.items() if after.get(p) != old]
    assert set(changed) <= mutable,changed
    frozen = (RUN/"baseline/implementation/it_taxonomy.py").read_text(encoding="utf-8")
    assert (ROOT/"src/it_taxonomy.py").read_text(encoding="utf-8") == frozen.replace('{"0.2.0", "0.2.1"}','{"0.2.0", "0.2.1", "0.2.2"}',1)
    frozen_test = (RUN/"baseline/implementation/test_a04_round1.py").read_text(encoding="utf-8")
    assert (ROOT/"src/test_a04_round1.py").read_text(encoding="utf-8") == frozen_test.replace('config["version"] = "0.2.2"','config["version"] = "0.2.3"',1)
    state = a.git_state(); old_state = read_json(RUN/"git_before.json")
    assert state == {k:old_state[k] for k in state}
    status = subprocess.check_output(["git","status","--porcelain=v1","--untracked-files=all"],cwd=ROOT).decode("utf-8")
    assert set(old_state["status_porcelain"].splitlines()) <= set(status.splitlines())
    return dict(existing_artifacts=len(before),protected_existing_artifacts=len(before)-len(mutable),
                protected_hash_size_mtime_unchanged=True,modified_existing_paths=changed,
                preexisting_git_status_preserved=True,git_head_index_tracked_diff_unchanged=True,
                active_config_sha256=sha256(ROOT/"config/it_taxonomy.json"))


def read_trace(path):
    with path.open(encoding="utf-8") as stream:
        return a.keyed([json.loads(line) for line in stream])


def verify_saved_run():
    summary = read_json(RUN/"comparison_summary.json")
    source,union = sources(); old = baseline_predictions(union); new = read_trace(RUN/"all_predictions.jsonl")
    assert set(new) == set(union)
    for rel,rows in source.items():
        assert metrics(rows,old) == summary["sources"][rel]["before"]
        assert metrics(rows,new) == summary["sources"][rel]["after"]
    assert not compare(old,new,union)[1]
    main = read_trace(RUN/"seed42_v022_predictions_private.jsonl")
    extra = read_trace(RUN/"supplement17_v022_predictions_private.jsonl")
    assert len(main) == 160 and len(extra) == 17 and set(main)&set(extra) == {"3905848702"}
    assert {k:v for k,v in main["3905848702"].items() if k!="sample_id"} == extra["3905848702"]
    for table in [main,extra]:
        for job,record in table.items():
            assert {k:v for k,v in record.items() if k!="sample_id"} == new[job]
    previous = old
    for index,name in enumerate(STAGES,1):
        folder = stage_folder(index,name)
        stage = read_trace(folder/"predictions.jsonl")
        assert_scope(read_json(folder/"config.json"),STAGES[:index])
        changes,regressions = compare(previous,stage,union)
        stored = read_json(folder/"delta.json")
        assert changes == stored["changes"] and regressions == stored["regressions"] == []
        previous = stage
    assert previous == new
    return dict(status="PASS",sources=[160,17],unique_jobs=176,common_source_conflict=False,
                all_sample_metrics_recomputed=True,all_stage_deltas_rechecked=True,regressions=[],preservation=preservation())


def run():
    assert not (RUN/"comparison_summary.json").exists()
    preservation()
    source,union = sources(); baseline = baseline_predictions(union)
    model = Taxonomy(RUN/"baseline/it_taxonomy_v0.2.1.json")
    for job,row in union.items():
        replay = checked_prediction(model,row["title"],row["description"],job)
        assert replay == baseline[job],(job,"Baseline replay changed")
    run_controls(model,[])
    previous,stages = baseline,[]
    for index,name in enumerate(STAGES,1):
        folder = stage_folder(index,name); config = read_json(folder/"config.json")
        assert_scope(config,STAGES[:index])
        model = Taxonomy(folder/"config.json"); controls = run_controls(model,STAGES[:index])
        pred = {job:checked_prediction(model,row["title"],row["description"],job) for job,row in union.items()}
        changes,regressions = compare(previous,pred,union)
        stage = dict(stage=name,config_sha256=model.sha256,classified_jobs=len(pred),changes=changes,regressions=regressions,
                     controls_round1=len(controls["round1"]),controls_round2=len(controls["round2"]),design_cases=57,
                     sources={rel:metrics(rows,pred) for rel,rows in source.items()})
        write_json(folder/"controls.json",controls,exclusive=True)
        write_json(folder/"delta.json",stage,exclusive=True)
        write_trace(folder/"predictions.jsonl",pred)
        if regressions:
            raise RuntimeError(f"Stage {name} regressed: {regressions}; not finalized")
        print(json.dumps(dict(stage=name,changed_jobs=len(changes),state_changes=sum("it_decision" in c["changed_fields"] for c in changes),regressions=regressions)),flush=True)
        stages.append(stage); previous = pred
    final = previous
    assert sha256(CANDIDATE) == stages[-1]["config_sha256"]
    write_trace(RUN/"all_predictions.jsonl",final)
    for rel,name in [(a.SEED,"seed42_v022_predictions_private.jsonl"),(a.DOWN,"supplement17_v022_predictions_private.jsonl")]:
        records = {job:dict(final[job],**({"sample_id":row["sample_id"]} if "sample_id" in row else {})) for job,row in source[rel].items()}
        write_trace(RUN/name,records)
    changes,regressions = compare(baseline,final,union)
    assert not regressions
    table = []
    for job,row in sorted(union.items(),key=lambda item:int(item[0])):
        b,n = baseline[job],final[job]
        table.append(dict(job_id=job,title=row["title"],sources=";".join(name for rel,name in [(a.SEED,"seed42"),(a.DOWN,"supplement17")] if job in source[rel]),
                          manual_label=row["manual_label"],manual_group=row["manual_primary_group_code"],manual_subgroup=row["manual_subgroup_code"],
                          before_decision=b["it_decision"],after_decision=n["it_decision"],before_group=b["primary_group_code"],after_group=n["primary_group_code"],
                          before_subgroup=b["subgroup_code"],after_subgroup=n["subgroup_code"],
                          changed_fields=";".join(k for k in r1.DETAIL if b[k]!=n[k]),
                          changed_stages=";".join(s["stage"] for s in stages if any(c["job_id"]==job for c in s["changes"])),
                          before_rules=";".join(b["matched_rule_ids"]),after_rules=";".join(n["matched_rule_ids"]),
                          before_reasons=";".join(b["reason_codes"]),after_reasons=";".join(n["reason_codes"])))
    write_csv(RUN/"job_comparison.csv",table,list(table[0]),exclusive=True,bom=True)
    remaining = [dict(job_id=job,title=row["title"],sources=[rel for rel in source if job in source[rel]],manual_group=row["manual_primary_group_code"],
                      reason_codes=final[job]["reason_codes"],matched_rule_ids=final[job]["matched_rule_ids"],manual_reason=row["manual_reason"],manual_evidence=row["manual_evidence"])
                 for job,row in union.items() if row["manual_label"]=="CNTT" and final[job]["it_decision"]=="REJECT"]
    summary = dict(date=DATE,timezone="Asia/Bangkok",status="ROUND2_CANDIDATE_ACCEPTANCE_NOT_CONFIRMED",version=VERSION,
                   candidate_config_sha256=sha256(CANDIDATE),baseline_version="0.2.1",baseline_replay_exact=True,
                   scope=STAGES,deferred=["P1b","P4","P5","P3_PACS","P3_ECC"],source_rows=177,unique_jobs=176,overlap="3905848702",
                   sources={rel:dict(before=metrics(rows,baseline),after=metrics(rows,final)) for rel,rows in source.items()},
                   stages=[{k:v for k,v in s.items() if k not in {"changes","sources"}} | dict(changed_jobs=len(s["changes"]),
                           state_changes=[c["job_id"] for c in s["changes"] if "it_decision" in c["changed_fields"]]) for s in stages],
                   cumulative_changes=changes,regressions=regressions,remaining_fn=remaining,
                   review_unique_before=sum(p["it_decision"]=="REVIEW" for p in baseline.values()),
                   review_unique_after=sum(p["it_decision"]=="REVIEW" for p in final.values()),
                   tests=read_json(RUN/"tests_result.json"),preservation=preservation(),evaluation="DEVELOPMENT_SAMPLE_NOT_INDEPENDENT",
                   full_dataset_classification=False,etl_rerun=False,a05_performed=False,commit=False,push=False,spark_jvm_parity="NOT_VERIFIED")
    assert summary["tests"]["successful"]
    write_json(RUN/"comparison_summary.json",summary,exclusive=True)
    write_json(RUN/"saved_output_verification.json",verify_saved_run(),exclusive=True)
    render_report(summary,stages,baseline,final,union)
    manifest = dict(date=DATE,version=VERSION,baseline_manifest="baseline/manifest.json",candidate_config_sha256=sha256(CANDIDATE),
                    source_rows=177,unique_jobs=176,implementation_sha256={f"src/{name}":sha256(ROOT/"src"/name) for name in [
                        "it_taxonomy.py","description_processing.py","it_taxonomy_v010.py","tv2_csv.py","a04_filter_fix_round1.py",
                        "compare_a04_versions.py","prepare_a04.py","apply_a04_decisions.py","test_a04_round1.py","test_a04_round2.py","a04_filter_fix_round2.py"]},
                    output_sha256={p.relative_to(RUN).as_posix():sha256(p) for p in RUN.rglob("*") if p.is_file() and "baseline" not in p.relative_to(RUN).parts},
                    report_sha256=sha256(ROOT/"docs/a04_filter_fix_round2_report.md"),preservation=preservation(),
                    python=platform.python_version(),python_executable=sys.executable,full_dataset_classification=False,etl_rerun=False)
    write_json(RUN/"run_manifest.json",manifest,exclusive=True)
    write_json(ROOT/"data/audit/tv2_a04_filter_fix_round2_20261014.json",manifest,exclusive=True)
    print(json.dumps({k:summary[k] for k in ["source_rows","unique_jobs","review_unique_before","review_unique_after","sources"]},ensure_ascii=False,indent=2))


def render_report(s,stages,old,new,union):
    sections = []
    for rel,title in [(a.SEED,"Mẫu chính 160"),(a.DOWN,"Mẫu bổ sung 17")]:
        before,after = s["sources"][rel]["before"],s["sources"][rel]["after"]
        counts = "\n".join(f"| {key.upper()} | {before[key]} | {after[key]} |" for key in ["tp","tn","fp","fn","review","chua_ro"])
        rates = "\n".join(f"| {title} | {fmt(before[key])} | {fmt(after[key])} |" for title,key in [
            ("Khớp khi máy quyết định","membership_on_decided"),("Độ phủ nhãn rõ","decision_coverage_clear"),
            ("Độ phủ toàn mẫu","decision_coverage_all"),("Quyết định đúng trên nhãn rõ","correct_decisions_on_clear"),
            ("Precision trên ACCEPT nhãn rõ","precision_decided"),("Recall có điều kiện ACCEPT/REJECT","recall_decided"),
            ("ACCEPT trên toàn bộ CNTT duyệt","accept_capture_all_manual_it"),("Khớp nhóm trên ACCEPT/CNTT","primary_group"),
            ("Khớp subgroup khi hai nhóm SOFTWARE","software_subgroup")])
        sections.append(f"### {title}\n\n| Đại lượng | v0.2.1 | v0.2.2 |\n| --- | ---: | ---: |\n{counts}\n\n"
                        f"| Tỷ lệ, mẫu số | Trước | Sau |\n| --- | --- | --- |\n{rates}\n\n"
                        + a.matrix_md(after["matrix"]).replace("Máy v0.2.0","Máy v0.2.2") + "\n")
    deltas,explanations = [],[]
    for c in s["cumulative_changes"]:
        job = c["job_id"]; b,n = old[job],new[job]
        phase = ", ".join(st["stage"] for st in stages if any(ch["job_id"]==job for ch in st["changes"]))
        deltas.append(f"| `{job}` | {c['title'].replace('|',' / ')} | {b['it_decision']} → {n['it_decision']} | {b['primary_group_code'] or 'NULL'} / {b['subgroup_code'] or 'NULL'} → {n['primary_group_code'] or 'NULL'} / {n['subgroup_code'] or 'NULL'} | {phase} | {', '.join(c['changed_fields'])} |")
        evidence = []
        for e in n["match_evidence"]:
            if e["term_set_id"] in ["software_hints","business_hints"] or e["term_set_id"].startswith(("software_integration_","application_","it_project_delivery_")):
                where = e["field"] + (f" s{e['segment_index']} / {e['section']}" if e["field"]=="description" else "")
                ranges = ", ".join(f"[{start},{end})" for start,end in e["raw_match_ranges"])
                evidence.append(f"`{e['matched_alias']}` ({where}, {ranges})")
        explanations.append(f"| `{job}` | {n['selected_rule_id'] or 'NULL'}; {'; '.join(n['reason_codes'])} | {'; '.join(evidence) or 'Không có evidence mới'} |")
    stage_rows = "\n".join(f"| {st['stage']} | {len(st['changes'])} | {sum('it_decision' in c['changed_fields'] for c in st['changes'])} | {len(st['regressions'])} |" for st in stages)
    fn_rows = "\n".join(f"| `{e['job_id']}` | {e['title'].replace('|',' / ')} | {e['manual_group']} | {'; '.join(e['reason_codes'])} |" for e in s["remaining_fn"])
    group_errors, subgroup_errors = [], []
    for job,row in union.items():
        p = new[job]
        if row["manual_label"] != "CNTT" or p["it_decision"] != "ACCEPT":
            continue
        if row["manual_primary_group_code"] != p["primary_group_code"]:
            group_errors.append(f"| `{job}` | {row['title'].replace('|',' / ')} | {p['primary_group_code']} | {row['manual_primary_group_code']} |")
        elif p["primary_group_code"] == "SOFTWARE" and row["manual_subgroup_code"] != p["subgroup_code"]:
            subgroup_errors.append(f"`{job}` ({p['subgroup_code']} → nhãn {row['manual_subgroup_code']})")
    old_fn = sum(row["manual_label"]=="CNTT" and old[job]["it_decision"]=="REJECT" for job,row in union.items())
    text = f"""# A04 – Round 2: ba phần P3, candidate v0.2.2

Ngày **14/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`. **Candidate trên mẫu phát triển; chưa xác nhận nghiệm thu A04.**

Đã đọc [kế hoạch](a04_filter_fix_plan.md), [kết quả round 1](a04_filter_fix_round1_report.md), [tiêu chí nghiệm thu](a04_completion_criteria.md) và candidate v0.2.1. Candidate mới [it_taxonomy_v0.2.2.json](../config/versions/it_taxonomy_v0.2.2.json), SHA-256 `{s['candidate_config_sha256']}`. Active `config/it_taxonomy.json` vẫn v0.2.0. Chỉ triển khai integration/coding, application maintenance/migration và IT project delivery; không P1b/P4/P5/PACS/ECC.

## Baseline và bảo toàn

[Baseline v0.2.1](../data/analytics/a04_taxonomy_v0_2_2_20261014/baseline/manifest.json) giữ exact config/code/test và ba trace đã lưu của round 1, hash trước sửa, source rows đã duyệt và Git state. Baseline config SHA-256 `efedfeeeb090808923f3ad47a27988f90436153f6e5f70610d48ff19c14773b9`. Replay **176/176 prediction khớp toàn bộ trường**, kể cả evidence/segments/processing. Mẫu chính 160, bổ sung 17, ca chung `3905848702` được deduplicate theo job_id; không JOIN bằng STT.

Raw, workbook, reviewer Dũng/ngày 2026-10-13, active config, config/trace/báo cáo/đầu ra cũ giữ nguyên. Hai chỉnh sửa nhỏ ở file có sẵn: interpreter chấp nhận thêm version v0.2.2; fixture unknown-version chuyển từ v0.2.2 sang v0.2.3 vì v0.2.2 nay được hỗ trợ, giữ nguyên ý nghĩa fail-closed. Bản code/test trước sửa đã snapshot; không đổi logic actor/section/negation/tier/priority/conflict. Config/trace/báo cáo/audit round 1 và v0.2.1 không được ghi đè.

## Sửa đổi thực tế và giới hạn

1. **P3_INTEGRATION**: SOFTWARE_CONTEXT là ANY của nhánh cũ và nhánh title software hint/integration contextual hint + SAME_SEGMENT(task workflow thiết kế/phát triển/test/deploy, object integration, context software/application). Catalog workflow dùng literal cụ thể, không verb integrate chung. `workday platform` là object ứng dụng cùng task, không tín hiệu employer; tên Workday/SAP hoặc integration đơn lẻ không đủ. Fixture dùng cả software applications không phụ thuộc sản phẩm. HR/accounting sử dụng phần mềm không tự ACCEPT.
2. **P3_APPLICATION_MAINTENANCE_MIGRATION**: thêm nhánh software hint + coding-role hint programmer/developer + task maintenance/support hoặc maintenance/upgrade cùng object ứng dụng và software environment. Migration cần cả task `migrate and upgrade`, object systems/applications, origin client/server và target Web-based **cùng unit**. Programmer vẫn không direct-title. SOFTWARE_WEB_CONTEXT có thêm đúng nhánh migration này để lấy Web từ nhiệm vụ chuyển ứng dụng, giữ tier/priority cũ; không lấy technology/profile ở QUALIFICATIONS. Maintenance đơn lẻ chưa đủ Web.
3. **P3_IT_DELIVERY**: IT_BUSINESS_CONTEXT giữ business title hint và thêm nhánh action project ownership/delivery + object `IT epics`/information-system projects + planning/deployment/system-implementation context cùng unit. Không dùng IT token rời rạc, Scrum, backlog hay Product Owner đơn lẻ. Nhóm là IT_BUSINESS, không đổi IT_MANAGEMENT.

Chỉ schema 1 hiện có (all/any/match/same_segment); không thêm operator/rule ID hoặc thay priority. Các nhánh cũ là nhánh đầu nguyên vẹn; term sets v0.2.1 nguyên vẹn. Predicate mới tiếp tục qua eligible unit, actor, company/qualification, negation/collaboration và source mapping/cửa sổ 500. Không dùng job_id, sample_id, employer hoặc whitelist mẫu trong classifier. Khóa trong báo cáo chỉ phục vụ đối chiếu.

## Kiểm tra và kết quả từng hạng mục

**{s['tests']['tests_run']} unittest qua, không skip**; mỗi stage có {stages[0]['controls_round1']} control round 1, {stages[0]['controls_round2']} control round 2 và 57 ca minh họa. Positive/negative controls gồm workflow integration/object mềm, HR/accounting, product-only, pure CNC/PLC, qualification-only (cả Develop applications), company/other actor/collaboration, negation, cross-unit, no title hint, thiếu origin/target, generic backlog/project và QA/SDET. Kiểm tra decision/is_it/group/subgroup/reason/rule/evidence/raw ranges và mapping.

| Hạng mục, so với stage trước | Job thay chi tiết | Job đổi trạng thái | Hồi quy FP/mất TP/nhóm/subgroup |
| --- | ---: | ---: | ---: |
{stage_rows}

Từng stage có config/hash, controls, prediction và delta riêng trong [stages](../data/analytics/a04_taxonomy_v0_2_2_20261014/stages/). Không có hồi quy cần thu hồi trên các controls và 176 khóa đã chốt. Các bất đồng nhóm/subgroup có từ baseline không được sửa nhãn hoặc che đi.

## Kết quả v0.2.1 → v0.2.2 tính lại từ nguồn

Tính riêng hai mẫu từ nhãn workbook đóng băng và trace candidate theo job_id. Khớp có điều kiện = `(ACCEPT/CNTT + REJECT/NGOAI_CNTT) / ca nhãn rõ và máy ACCEPT/REJECT`; độ phủ nhãn rõ dùng cùng số ca chia CNTT+NGOAI_CNTT. REVIEW chưa quyết định, không REJECT/FN; CHUA_RO loại khỏi mẫu số nhãn rõ và vẫn hiện riêng. Tỷ lệ quyết định đúng trên nhãn rõ không tính REVIEW là đúng. Group chỉ trên ACCEPT/CNTT; subgroup chỉ khi cả hai nhóm SOFTWARE.

{chr(10).join(sections)}
Hợp hai mẫu: REVIEW duy nhất **{s['review_unique_before']} → {s['review_unique_after']}**, FN xác nhận **{old_fn} → {len(s['remaining_fn'])}**. 4 CHUA_RO đã duyệt nguyên vẹn. 177 dòng nguồn không là 177 tin độc lập; đây là mẫu phát triển đã dùng sửa quy tắc, không accuracy toàn dataset hoặc đánh giá độc lập.

## Giải thích mọi thay đổi

| job_id | Title | Decision | Group/subgroup trước → sau | Hạng mục | Trường delta ngoài version/hash |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(deltas)}

| job_id | Rule thắng và reason candidate | Alias evidence, field/unit/section, raw ranges |
| --- | --- | --- |
{chr(10).join(explanations)}

Raw ranges là Unicode code point `[start,end)` trong trường sau CSV parse; quote đầy đủ và toàn bộ before/after nằm trong [comparison_summary](../data/analytics/a04_taxonomy_v0_2_2_20261014/comparison_summary.json) và từng stage delta. `job_comparison.csv` có đủ 176 khóa, kể cả không đổi; trace riêng có đủ 160/17 và common prediction khớp. Các nhiệm vụ mới được nhận từ ROLE/RESPONSIBILITIES/UNKNOWN eligible và task sở hữu vị trí; qualification/actor bị chặn giữ nguyên. Không lấy Web từ câu Develop applications ở QUALIFICATIONS.

## Lỗi còn lại và phương án xử lý

| job_id | Title | Nhóm người duyệt | Reason candidate |
| --- | --- | --- | --- |
{fn_rows}

Các FN còn lại cần xử lý theo quyền hạn riêng: PACS cần task/object/hint support sau heading, ECC cần phân xử nghề vận hành OS/network/backup với software phụ, Oracle cần positive functional ERP và P4 exclusion, SAP BTP/Lead Research Scientist cần P5 về profile/nhiệm vụ. Chưa triển khai các phần này hoặc thêm ngoại lệ để ép chúng thành ACCEPT.

REVIEW còn lại giữ rõ: mẫu chính 8 CNTT + 15 NGOAI_CNTT; bổ sung 10 CNTT + 1 NGOAI_CNTT; hợp duy nhất 17 CNTT + 16 NGOAI_CNTT do ca chung là CNTT/REVIEW. Conflict domain software/data thuộc P4, implicit heading/Privacy thuộc P1b và phạm vi P5, UI/application-support/data-platform thiếu task/hint hoặc cần chốt nhóm. 16 REVIEW ngoài CNTT không bị coi là FN. Không yêu cầu tất cả REVIEW phải ACCEPT; không thay nhãn CHUA_RO để làm tỷ lệ tốt hơn.

**Bất đồng nhóm còn từ baseline ({len(group_errors)} ca, đều ở mẫu chính):**

| job_id | Title | Nhóm candidate | Nhóm đã duyệt |
| --- | --- | --- | --- |
{chr(10).join(group_errors)}

Bất đồng subgroup còn từ baseline ({len(subgroup_errors)} ca, đều ở mẫu chính): {"; ".join(subgroup_errors)}. Cần đối soát evidence nghề và quy tắc ưu tiên/chính sách Web so với OTHER trong phạm vi được chốt tiếp theo. Round 2 không đổi priority hoặc nhãn đã duyệt để giải quyết các bất đồng này. Bất đồng nhóm không được đếm thêm như lỗi subgroup.

Catalog mới cố ý hẹp: workflow integration phải có chuỗi action rõ; migration phải có cả origin và target trong một unit. Những cách diễn đạt tương tự chưa có alias vẫn có thể bị bỏ sót; chưa có bằng chứng để nới động từ/context hoặc nối qua unit. Rủi ro nhận người dùng sản phẩm, việc của công ty/người khác và nghiệp vụ Scrum được kiểm tra bằng negative controls; kết quả không có FP mới trên mẫu này không chứng minh không có FP ngoài mẫu.

## Đối chiếu nghiệm thu A04

Theo [a04_completion_criteria.md](a04_completion_criteria.md), mẫu 100–200 tin, nhãn/metadata, tỷ lệ có tử số/mẫu số và ví dụ lọc sai đã có. Round 2 bổ sung sửa và kiểm tra hồi quy cho ba họ được phép. **Không có tiêu chí mặc định FN=0/REVIEW=0**; nhãn CHUA_RO và máy abstain được phép khi báo rõ nguồn, phạm vi/mẫu số và phương án đối soát.

Phần cần người phụ trách xác nhận để nghiệm thu: kết quả và cách xử lý lỗi đã thực hiện đáp ứng G21/I21; chốt cách xử lý/giới hạn chấp nhận đối với FN/REVIEW/bất đồng còn lại, không coi chỉ có bảng đề xuất là đã sửa tất cả bộ lọc; người rà soát xác nhận đầu ra/tiêu chí trước cập nhật 100%. Không tự đánh dấu hoàn thành. Mẫu độc lập phục vụ tuyên bố chất lượng độc lập/toàn tập; parity Spark/JVM/canonical thuộc D06/TV1, không tự biến thành hai điều kiện riêng của I21.

TV1 cần chạy cùng candidate/config/fixture, giữ SAME_SEGMENT/actor/blocker, sort tier/priority, Web migration chỉ sau SOFTWARE, is_it/nhóm NULL cho REVIEW và mapping code point–UTF-16/raw ranges; không bật metadata/skills cho membership. Parity chưa xác minh trong lượt này.

## Hiện vật và phạm vi

[Runner](../src/a04_filter_fix_round2.py), [test mới](../src/test_a04_round2.py), [manifest](../data/analytics/a04_taxonomy_v0_2_2_20261014/run_manifest.json), [kiểm tra đầu ra](../data/analytics/a04_taxonomy_v0_2_2_20261014/saved_output_verification.json), [đối chiếu cuối](../data/analytics/a04_taxonomy_v0_2_2_20261014/independent_verification.json), [audit](../data/audit/tv2_a04_filter_fix_round2_20261014.json). Đối chiếu cuối tính lại ma trận/tỷ lệ bằng Counter và phân số từ trace đã lưu; đây là kiểm tra phép tính, không là mẫu đánh giá độc lập. Runner từ chối ghi đè output, chỉ đọc source/trace mẫu đã khóa; config candidate phải chỉ định riêng. Không ETL/toàn dataset, không A05, commit/push; raw/workbook/metadata/trace/active config và đầu ra cũ nguyên vẹn.
"""
    with (ROOT/"docs/a04_filter_fix_round2_report.md").open("x",encoding="utf-8") as stream:
        stream.write(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare",action="store_true")
    args = parser.parse_args()
    prepare() if args.prepare else run()
