"""Inventory, tests, dependency-gated analysis and A09-A11 candidates in a new run.

No extractor/classifier edits, skill decisions, raw/workbook writes or ETL.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import a06_a08_spark_analysis as analysis
from render_tv2_analysis import render
from tv2_csv import ROOT, sha256, write_csv, write_json
from tech_skill_extractor import EXTRACTOR_VERSION


def assignment(path):
    ns = {"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    result = []
    with zipfile.ZipFile(path) as z:
        strings = ["".join(x.itertext()) for x in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si",ns)]
        for name in z.namelist():
            if not name.startswith("xl/worksheets/sheet") or not name.endswith(".xml"):continue
            for row in ET.fromstring(z.read(name)).findall(".//m:sheetData/m:row",ns):
                cells = {}
                for cell in row.findall("m:c",ns):
                    value = cell.find("m:v",ns)
                    text = (strings[int(value.text)] if cell.get("t")=="s" else value.text) if value is not None else "".join(cell.itertext())
                    cells[cell.get("r")] = text
                if any(v in ["A05","A06","A07","A08","A09","A10","A11","D05","D06","D07"] for v in cells.values()):
                    result.append(dict(sheet_xml=name,cells=cells))
    return dict(path=str(path),sha256=sha256(path),rows=result,macros_executed=False)


def skill_workbook(path=None):
    if path is None:
        places = [ROOT,Path.home()/"Downloads",Path.home()/"Desktop",Path.home()/"Documents"]
        found = [p for base in places if base.exists() for p in base.rglob("a05_skill_review_decisions.xlsx")]
        path = found[0] if found else None
    if not path or not Path(path).is_file():
        return dict(status="NOT_FOUND",reviewer_empty_verified=False,approval_date_empty_verified=False,
                    expected_role="QUYET_DINH_DE_NGHI",decisions_applied=False,
                    note="Cannot verify blank reviewer/date without the actual workbook; package README alone is not evidence of approval.")
    from apply_a04_decisions import read_sheet
    # Do not save or change workbook. Existing XML reader supplies cell values.
    with zipfile.ZipFile(path) as z:
        ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        names=[e.get("name") for e in ET.fromstring(z.read("xl/workbook.xml")).findall("m:sheets/m:sheet",ns)]
    stats=[]
    for name in names:
        rows=read_sheet(Path(path),name)["rows"]
        keys={str(k).lower():k for row in rows for k in row}
        reviewers=[keys[k] for k in ["reviewer","approved_by","người duyệt"] if k in keys]
        dates=[keys[k] for k in ["reviewed_date","approved_on","approval_date","ngày duyệt"] if k in keys]
        if reviewers and dates:
            stats.append(dict(sheet=name,rows=len(rows),reviewer_nonempty=sum(any(str(r.get(k,"")).strip() for k in reviewers) for r in rows),
                              date_nonempty=sum(any(str(r.get(k,"")).strip() for k in dates) for r in rows)))
    pending=bool(stats) and all(r["reviewer_nonempty"]==r["date_nonempty"]==0 for r in stats)
    return dict(path=str(path),sha256=sha256(path),status="PROPOSED_NOT_APPROVED" if pending else "FOUND_NEEDS_REVIEW",
                reviewer_empty_verified=pending,approval_date_empty_verified=pending,sheets=stats,decisions_applied=False)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True)
    p.add_argument("--contract",default=str(ROOT/"config/tv2_analysis_inputs.example.json"))
    p.add_argument("--skill-review-workbook")
    a=p.parse_args(argv)
    out=Path(a.output).resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError("New repository output directory required")
    config=json.loads(Path(a.contract).read_text(encoding="utf-8"))
    deps,_=analysis.preflight(config)
    env=analysis.runtime()
    inventory=[dict(item=key,state="CO_DA_XAC_NHAN" if value else "CHUA_CO_HOAC_CHUA_XAC_NHAN",depends_on="TV1" if key!="A05" else "TV1 D06 + TV2 A05 approval") for key,value in deps.items()]
    inventory += [dict(item="Java/PySpark",state=env["java"]+"; PySpark="+str(env["pyspark_available"]),depends_on="Runtime Java 21/PySpark 4.2.0"),
                  dict(item="A06-A11 official outputs",state="CHUA_CO" if not list((ROOT/"data").rglob("q01_role_groups.parquet")) else "FOUND_VERIFY_MANIFEST",depends_on="D06/D05/A05/D07"),
                  dict(item="Working branch",state=subprocess.check_output(["git","branch","--show-current"],text=True).strip(),depends_on="Keep current branch")]
    if inventory[-1]["state"]!="feat/tv2-analysis":raise ValueError("Unexpected branch; do not switch it automatically")
    workbook=skill_workbook(a.skill_review_workbook)
    out.mkdir(parents=True,exist_ok=False)
    write_csv(out/"dependency_inventory.csv",inventory,["item","state","depends_on"],exclusive=True,bom=True)
    write_json(out/"dependency_inventory.json",dict(date="2026-10-19",inventory=inventory,environment=env,
        parquet_artifacts_found=[str(path) for path in (ROOT/"data").rglob("*.parquet")],skill_review_workbook=workbook,
        git_status_before=subprocess.check_output(["git","status","--short"],text=True),
        dictionary_version="0.1.2",extractor_version=EXTRACTOR_VERSION,dictionary_sha256=sha256(ROOT/"config/tech_skills.json")),exclusive=True)
    source=Path("C:/Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsm")
    write_json(out/"assignment_context.json",assignment(source),exclusive=True)
    # Runs existing A05 tests, new contract/report tests; never A01-A04 tests.
    suite=unittest.defaultTestLoader.discover(str(ROOT/"src"),pattern="test_a05*.py")
    stream=io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()):
        results=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/"test_results.txt").write_text(stream.getvalue(),encoding="utf-8")
    tests=dict(total=results.testsRun,passed=results.testsRun-len(results.failures)-len(results.errors)-len(results.skipped),
        failures=len(results.failures),errors=len(results.errors),skipped=len(results.skipped),skip_reasons=[reason for _,reason in results.skipped],
        spark_parity="SKIP" if not env["pyspark_available"] else "SEE_TEST_LOG",real_d06="SKIP" if not deps["D06"] else "SEE_RUN_MANIFEST")
    write_json(out/"test_results.json",tests,exclusive=True)
    if results.failures or results.errors:raise AssertionError("Tests failed; inspect new test log before analysis")
    analysis.main(["--contract",a.contract,"--output",str(out/"analysis"),"--run-id",out.name])
    render(out/"analysis/manifest.json",out/"reports")
    manifest=json.loads((out/"analysis/manifest.json").read_text(encoding="utf-8"))
    write_json(out/"delivery_manifest.json",dict(date="2026-10-19",status=manifest["status"],tests=tests,
        official_analytics_success=manifest["status"]=="SUCCESS",workbook=workbook,
        preserved_A01_A04=True,taxonomy_executed=False,skill_decisions_applied=False,
        files={str(f.relative_to(out)):sha256(f) for f in out.rglob("*") if f.is_file()}),exclusive=True)
    print(json.dumps(dict(output=str(out),status=manifest["status"],tests=tests,workbook=workbook),ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
