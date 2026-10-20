"""Development-only Spark/Python parity on the frozen 105 manually approved jobs."""
import argparse
import collections
import csv
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

from a05_spark import extract_frames, prepare_dependencies, spark_record
from tech_skill_extractor import TechSkillExtractor
from tv2_csv import ROOT, sha256


def canonical(rows):
    return sorted(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)


def run(output):
    out = Path(output).resolve()
    if not out.is_relative_to(ROOT / 'data/analytics'):
        raise ValueError('Use a new development directory within data/analytics')
    out.mkdir(parents=True, exist_ok=False)
    base = ROOT / 'data/analytics/a05_development_v0_1_2_20261014'
    selection = json.loads((base/'input_manifest.json').read_text(encoding='utf-8'))
    wanted = {str(r['job_id']) for r in selection['jobs']}
    source_path = ROOT/'data/analytics/a04_taxonomy_v0_2_2_20261014/baseline/source_rows.json'
    source = json.loads(source_path.read_text(encoding='utf-8'))
    records = {}
    for rows in source.values():
        for r in rows:
            if str(r['job_id']) in wanted:
                assert r['manual_label'] == 'CNTT'
                if str(r['job_id']) in records:
                    assert records[str(r['job_id'])] == r['description']
                records[str(r['job_id'])] = r['description']
    assert set(records) == wanted and len(wanted) == 105
    for r in selection['labels']:
        assert sha256(Path(r['path'])) == r['sha256']
    old_states = [json.loads(x) for x in (base/'skill_source_processing.jsonl').read_text(encoding='utf-8').splitlines()]
    old_evidence = [json.loads(x) for x in (base/'technical_skill_evidence.jsonl').read_text(encoding='utf-8').splitlines()]
    for r in old_states:
        assert hashlib.sha256(records[str(r['job_id'])].encode()).hexdigest() == r['source_text_sha256']
    run_id = old_states[0]['run_id']  # Exact comparison to frozen ids; output directory is new.
    model = TechSkillExtractor(ROOT/'config/tech_skills.json')
    expected_results = [model.extract(records[j], j, run_id=run_id) for j in sorted(wanted)]
    assert canonical([x['processing'] for x in expected_results]) == canonical(old_states)
    assert canonical([e for x in expected_results for e in x['evidence']]) == canonical(old_evidence)
    from pyspark.sql import SparkSession
    from d05_utils import get_spark_session
    spark = get_spark_session('TV2-A05-105-DEVELOPMENT-PARITY', ROOT)
    spark.conf.set('spark.sql.shuffle.partitions','2')
    result = dict(status='RUNNING', scope='DEVELOPMENT_105_NOT_D06_NOT_MARKET_STATISTICS',
                  input_jobs=105, production_executed=False, classification_executed=False,
                  dictionary_version=model.version, dictionary_sha256=model.sha256,
                  source_snapshot_sha256=sha256(source_path), input_manifest_sha256=sha256(base/'input_manifest.json'))
    cache = None
    try:
        result['environment'] = dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
            spark=spark.version, java=spark.sparkContext._jvm.java.lang.System.getProperty('java.version'),
            hadoop=spark.sparkContext._jvm.org.apache.hadoop.util.VersionInfo.getVersion(),
            master=spark.sparkContext.master, pythonpath=os.environ.get('PYTHONPATH'))
        result['dependencies'] = prepare_dependencies(spark.sparkContext, 'shared_local_pythonpath')
        schema = 'job_id long, description string, it_decision string, is_it boolean, taxonomy_version string, taxonomy_sha256 string'
        rows = [(int(j), records[j], 'ACCEPT', True, 'DEV_MANUAL_MEMBERSHIP_FIXTURE', 'NOT_D06') for j in sorted(wanted)]
        frame = spark.createDataFrame(rows, schema).cache()
        tables, cache, n = extract_frames(frame, ROOT/'config/tech_skills.json', run_id,
                                          dependency_mode='shared_local_pythonpath')
        expected = {'job_skill_technical':[spark_record(e) for x in expected_results for e in x['job_skills']],
                    'technical_skill_evidence':[spark_record(e) for x in expected_results for e in x['evidence']],
                    'skill_source_processing':[spark_record(x['processing']) for x in expected_results]}
        result['tables'] = {}
        for name, table in tables.items():
            actual = [r.asDict(recursive=True) for r in table.collect()]
            assert canonical(actual) == canonical(expected[name]), name
            path = out/(name+'.parquet')
            table.coalesce(2).write.mode('errorifexists').parquet(str(path))
            restored = [r.asDict(recursive=True) for r in spark.read.parquet(str(path)).collect()]
            assert canonical(restored) == canonical(actual), name+' parquet'
            (out/(name+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in actual),encoding='utf-8')
            result['tables'][name] = dict(rows=len(actual), full_record_parity=True, parquet_readback=True)
        actual_pairs = {(r['job_id'], r['skill_code']) for r in expected['job_skill_technical']}
        with (base/'job_skill_technical.csv').open(encoding='utf-8-sig',newline='') as f:
            assert actual_pairs == {(int(r['job_id']),r['skill_code']) for r in csv.DictReader(f)}
        # Controlled missing and zero-hit cases supplement, never replace, the real 105.
        controls = [(900000000000000001,None), (900000000000000002,'Maintain office records.')]
        control_frame = spark.createDataFrame([(j,t,'ACCEPT',True,'SYNTHETIC_CONTROL','NOT_D06') for j,t in controls],schema)
        control_tables, control_cache, _ = extract_frames(control_frame, ROOT/'config/tech_skills.json','SYNTHETIC_CONTROLS_ONLY',dependency_mode='shared_local_pythonpath')
        try:
            actual = [r.asDict(recursive=True) for r in control_tables['skill_source_processing'].collect()]
            expected_control = [spark_record(model.extract(t,j,run_id='SYNTHETIC_CONTROLS_ONLY')['processing']) for j,t in controls]
            assert canonical(actual) == canonical(expected_control)
            result['synthetic_controls'] = [dict(job_id=r['job_id'],source_status=r['source_status']) for r in actual]
            assert {r['source_status'] for r in actual} == {'SOURCE_MISSING','PROCESSED_NO_MATCH'}
        finally:
            control_cache.unpersist()
        result['development_source_status_counts'] = dict(collections.Counter(r['source_status'] for r in expected['skill_source_processing']))
        result['status'] = 'PASS_DEVELOPMENT_LOCAL_WORKER_PARITY'
    except Exception as e:
        result.update(status='FAIL',error=repr(e))
        raise
    finally:
        if cache is not None: cache.unpersist()
        spark.stop()
        (out/'parity_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',required=True)
    run(p.parse_args().output)
