"""Execute D09 against existing D05/D07/D08. No ETL writes or classification.

Reuses scaffold rules (keys, grain, reconciliation, NULL preservation), not its
smoke results or obsolete USD/placeholder expectations. Writes NEW D09 audit only.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import statistics
import subprocess
import time
import xml.etree.ElementTree as ET
import zipfile

from normalize_salary import ROOT, file_sha, inventory, load_policy, validate, key_stats, write_new
import d08_benchmark as benchmark

BASELINES = {
    'D05': '457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b',
    'D06': '5fda1789b84494a856743c087d10fc511d013d93',
    'D07': '479d3d83ff3194a5556ce29884c92478c90a969c',
    'D08': 'ff721bcf7988841a2b80e3f263f3ef8a69188278',
}
STATES = ('PASS', 'FAIL', 'BLOCKED', 'NOT APPLICABLE')
A07 = ROOT / 'data/audit/d07/d07_20261019_01'
A08 = ROOT / 'data/audit/d08/d08_20261020_01'
RUN07 = ROOT / 'data/processed/d07/staging/d07_20261019_01'
D05 = ROOT / 'data/processed/canonical/jobs'


def read_json(p):
    return json.loads(Path(p).read_text(encoding='utf8'))


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_member(name):
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and '\\' not in name
            and ':' not in name and bool(p.parts), 'Unsafe manifest/ZIP path')
    return p


def tally(records):
    counts = dict.fromkeys(STATES, 0)
    for r in records:
        require(r['status'] in STATES, 'Unknown validation status')
        counts[r['status']] += 1
    return {'TOTAL': len(records), **counts}


def verify_statistics(rows, summary):
    require(len(rows) == 60 and len(summary) == 15, 'Observation/summary inventory')
    require(Counter(r['phase'] for r in rows) == {'warmup': 15, 'measured': 45}, 'Phases')
    require({(r['master'], r['workload']) for r in summary}
            == {(m, w) for m in benchmark.MASTERS for w in benchmark.WORKLOADS}, 'Summary cells')
    for s in summary:
        cell = [r for r in rows if r['master'] == s['master'] and r['workload'] == s['workload']]
        require(sorted((r['phase'], int(r['repeat'])) for r in cell)
                == [('measured', 1), ('measured', 2), ('measured', 3), ('warmup', 0)], 'Repeats')
        values = [float(r['elapsed_seconds']) for r in cell if r['phase'] == 'measured']
        require(all(math.isfinite(v) and v > 0 for v in values), 'Invalid timing')
        for field, expected in [('min_seconds', min(values)), ('median_seconds', statistics.median(values)), ('max_seconds', max(values))]:
            require(math.isclose(float(s[field]), expected, rel_tol=1e-12), field)
        baseline = next(t for t in summary if t['workload'] == s['workload'] and t['master'] == 'local[1]')
        require(int(s['samples']) == 3 and math.isclose(float(s['speedup_vs_local1']),
                float(baseline['median_seconds']) / float(s['median_seconds']), rel_tol=1e-12), 'Speedup')
    require(all(r['correctness'] == 'PASS' for r in rows), 'Correctness flag')
    for w in benchmark.WORKLOADS:
        require(len({r['result_json'] for r in rows if r['workload'] == w}) == 1, 'Result drift')
    return {'observations': 60, 'measured': 45, 'warmup': 15, 'summary_cells': 15,
            'median_min_max_speedup': 'RECOMPUTED_FROM_RAW_CSV'}


def snapshot():
    paths = {ROOT / n for n in git('ls-tree', '-r', '--name-only', BASELINES['D08']).splitlines()}
    for folder in ('data/raw', 'data/processed'):
        paths.update(p for p in (ROOT / folder).rglob('*') if p.is_file())
    return {p.relative_to(ROOT).as_posix(): [p.stat().st_size, p.stat().st_mtime_ns, file_sha(p)]
            for p in sorted(paths) if p.is_file()}


class Audit:
    def __init__(self):
        self.records = []

    def record(self, name, status, evidence):
        require(name not in {r['check'] for r in self.records}, 'Duplicate check ID')
        require(status in STATES, 'Unknown status')
        self.records.append({'check': name, 'status': status, 'evidence': evidence,
                             'at_utc': datetime.now(timezone.utc).isoformat()})
        print(name, status, flush=True)

    def check(self, name, fn):
        try:
            value = fn()
            self.record(name, 'PASS', value)
        except Exception as exc:
            self.record(name, 'FAIL', {'error_type': type(exc).__name__, 'message': str(exc)[:1000]})


def equal(actual, expected):
    require(actual == expected, 'Expected and actual differ')
    return {'actual': actual, 'expected': expected}


def git_releases():
    require(git('branch', '--show-current') == 'feat/tv1-d09-validation', 'Wrong branch')
    equal(git('rev-parse', 'HEAD'), BASELINES['D08'])
    require(not git('diff', '--name-only') and not git('diff', '--cached', '--name-only'), 'Tracked/index modifications')
    for c in BASELINES.values():
        subprocess.run(['git', 'merge-base', '--is-ancestor', c, 'HEAD'], cwd=ROOT, check=True)
    bindings = {'src/build_canonical_jobs.py': 'D05', 'src/d06_official_runner.py': 'D06',
                'src/d06_official_contract.py': 'D06', 'src/normalize_salary.py': 'D07',
                'config/d07_salary_policy_v1.json': 'D07', 'src/d08_benchmark.py': 'D08',
                'src/test_d08_benchmark.py': 'D08'}
    for path, stage in bindings.items():
        require((ROOT / path).read_bytes() == subprocess.check_output(['git', 'show', BASELINES[stage] + ':' + path], cwd=ROOT), path)
    return {'HEAD': git('rev-parse', 'HEAD'), 'baselines': BASELINES, 'exact_source_bindings': bindings}


def stored_identity():
    m05 = read_json(ROOT / 'data/audit/d05_official_run_manifest.json')
    equal(m05, read_json(ROOT / 'data/processed/canonical/d05_run_manifest.json'))
    equal(m05['output_rows'], 123849)
    m07 = read_json(A07 / 'run_manifest.json'); seal = read_json(A07 / 'completion.json')
    equal(seal, read_json(RUN07 / 'completion.json'))
    require(seal['status'] == 'SUCCEEDED' and not (RUN07 / 'failure.json').exists(), 'D07 completion')
    for name, field in [('run_manifest.json', 'manifest_sha256'), ('validation_summary.json', 'validation_sha256'), ('output_inventory.json', 'output_inventory_sha256')]:
        equal(file_sha(RUN07 / name), seal[field])
        if (A07 / name).exists():
            require((A07 / name).read_bytes() == (RUN07 / name).read_bytes(), name)
    equal(inventory(D05), m07['input_inventory'])
    equal(inventory(RUN07 / 'salaries.parquet')['fingerprint'], seal['output_fingerprint'])
    equal(file_sha(ROOT / 'src/normalize_salary.py'), m07['source_sha256'])
    equal(file_sha(ROOT / 'config/d07_salary_policy_v1.json'), m07['policy']['sha256'])
    m08 = read_json(A08 / 'benchmark_manifest.json')
    equal(inventory(D05), m08['inputs']['D05'])
    equal(inventory(RUN07 / 'salaries.parquet'), m08['inputs']['D07'])
    return {'D05': m05, 'D07_scope': seal['scope'], 'D07_run_id': seal['run_id'],
            'D05_fingerprint': m07['input_inventory']['fingerprint'], 'D07_fingerprint': seal['output_fingerprint'],
            'D07_policy_sha256': m07['policy']['sha256'], 'note': 'Manifest git_head is execution parent, not later release commit'}


def d08_events():
    m = read_json(A08 / 'benchmark_manifest.json')
    rows = list(csv.DictReader((A08 / 'benchmark_results.csv').open(encoding='utf8')))
    fixed = []
    for c in m['configs']:
        cfg = c['config']; master = cfg['master']
        fixed.append({k: v for k, v in cfg.items() if k not in ('master', 'startup_seconds', 'spark.eventLog.dir')})
        directory = ROOT / 'tmp/d08_benchmark/d08_20261020_01' / master.replace('[', '_').replace(']', '') / 'events'
        metrics, files = benchmark.event_metrics(directory)
        equal(files, c['event_files'])
        for r in (r for r in rows if r['master'] == master):
            for k, v in metrics[r['job_group']].items():
                equal(int(r[k]), v)
            equal(json.loads(r['result_json']), c['references'][r['workload']])
    require(len(fixed) == 3 and fixed[0] == fixed[1] == fixed[2], 'Config drift')
    tasks = sum(int(r['task_attempts']) for r in rows if r['phase'] == 'measured')
    equal(tasks, 585)
    return {'measured_task_attempts': tasks, 'all_60_groups_reparsed': True,
            'shuffle_partitions': fixed[0]['spark.sql.shuffle.partitions'], 'heap_bytes': fixed[0]['java_max_heap_bytes']}


def d08_receipts():
    receipt = read_json(A08 / 'post_run_verification.json')
    for name, expected in receipt['artifacts'].items():
        p = A08 / name
        equal(p.stat().st_size, expected['bytes']); equal(file_sha(p), expected['sha256'])
        require(p.read_bytes() == subprocess.check_output(['git', 'show', BASELINES['D08'] + ':' + p.relative_to(ROOT).as_posix()], cwd=ROOT), name)
    for name in ('runtime_median.svg', 'speedup.svg'):
        equal(len(ET.parse(A08 / name).getroot().findall('{http://www.w3.org/2000/svg}rect')), 19)
    equal(file_sha(ROOT / 'src/d08_benchmark.py'), read_json(A08 / 'benchmark_manifest.json')['source_sha256'])
    return receipt


def test_evidence():
    checks = []
    for stage, path, count, source, test, sourcekey, testkey in [
        ('D07', ROOT / 'data/audit/d07/tests_summary.json', 19, 'src/normalize_salary.py', 'src/test_d07_salary.py', 'pipeline_sha256', 'test_sha256'),
        ('D08', A08 / 'tests_summary.json', 11, 'src/d08_benchmark.py', 'src/test_d08_benchmark.py', 'source_sha256', 'tests_sha256'),
        ('D08_RELEASE', ROOT / 'tmp/d08_tests/release_5795200c61/summary.json', 11, 'src/d08_benchmark.py', 'src/test_d08_benchmark.py', 'source_sha256', 'tests_sha256')]:
        t = read_json(path)
        if stage == 'D07':
            t = t['release_verification']
        require(t['status'] == 'PASS' and t['tests'] == count and t['failures'] == t['errors'] == t['skips'] == 0, stage)
        equal(file_sha(ROOT / source), t[sourcekey]); equal(file_sha(ROOT / test), t[testkey])
        checks.append({'stage': stage, 'tests': count, 'scope': 'HISTORICAL_SYNTHETIC_TESTS_NOT_D09_COUNTS'})
    return checks


def limitations():
    m = read_json(A08 / 'benchmark_manifest.json'); text = (ROOT / 'docs/d08_benchmark_report.md').read_text(encoding='utf8')
    require(m['scope'] == 'OFFICIAL_D05_D07_AVAILABLE_WORKLOADS_ONLY'
            and m['full_pipeline'] == 'PENDING_D06_FULL' and m['d06_full'] == 'NOT_EXECUTED', 'Overclaim scope')
    joined = ' '.join(m['limitations']).lower()
    for token in ('local', 'os cache', 'jit', '3 timing', 'no d06', 'not multi-node'):
        require(token in joined, 'Missing limitation ' + token)
    require('startup' in text.lower() and 'cache' in text.lower(), 'Report limitations')
    return {'limitations': m['limitations'], 'startup_seconds': {c['config']['master']: c['config']['startup_seconds'] for c in m['configs']},
            'not_claimed': ['linear scaling', 'local[4] always optimal', 'full-pipeline benchmark']}


def handoff_check(folder, archive):
    require(folder.is_dir() and archive.is_file(), 'Handoff folder/archive missing')
    m = read_json(folder / 'HANDOFF_MANIFEST.json')
    rows = list(csv.DictReader((folder / 'SHA256SUMS.csv').open(encoding='utf8')))
    require(len(rows) == len({r['path'] for r in rows}) == 36, 'Checksum inventory')
    checks = {r['path']: r for r in rows}
    equal({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}, set(checks) | {'SHA256SUMS.csv'})
    for row in rows:
        safe_member(row['path']); p = folder / row['path']
        equal(p.stat().st_size, int(row['bytes'])); equal(file_sha(p), row['sha256'])
    equal(len(m['files']), 35)
    require(len({r['path'] for r in m['files']}) == 35, 'Duplicate payload')
    equal({r['path'] for r in m['files']}, set(checks) - {'HANDOFF_MANIFEST.json'})
    for row in m['files']:
        for k in ('bytes', 'sha256'):
            equal(str(row[k]), str(checks[row['path']][k]))
    sidecar = Path(str(archive) + '.sha256')
    equal(file_sha(archive), sidecar.read_text(encoding='ascii').split()[0])
    expected = {folder.name + '/' + n for n in checks} | {folder.name + '/SHA256SUMS.csv'}
    with zipfile.ZipFile(archive) as z:
        equal(len(z.namelist()), len(set(z.namelist())))
        equal(set(z.namelist()), expected)
        require(z.testzip() is None, 'ZIP CRC failure')
        for info in z.infolist():
            safe_member(info.filename); rel = PurePosixPath(info.filename).relative_to(folder.name).as_posix()
            p = folder / rel; equal(info.file_size, p.stat().st_size)
            with z.open(info) as stream:
                h = hashlib.file_digest(stream, 'sha256').hexdigest()
            equal(h, file_sha(p))
    equal(inventory(folder / 'D05_Canonical/jobs'), inventory(D05))
    equal(inventory(folder / 'D07_Salary/salaries.parquet'), inventory(RUN07 / 'salaries.parquet'))
    return {'folder': str(folder), 'zip': str(archive), 'zip_sha256': file_sha(archive),
            'members': 37, 'payload_files': 35, 'checksum_rows': 36, 'CRC': 'PASS', 'all_member_sha256': 'PASS'}


def spark_checks(audit, args):
    from pyspark.sql import functions as F, types as T
    from types import SimpleNamespace
    spark, config = benchmark.create_session(SimpleNamespace(run_id=args.run_id, master='local[2]', repeats=3,
                                                            partitions=4, windows_fs_jar=args.windows_fs_jar))
    try:
        jobs = spark.read.parquet(str(D05)); salary = spark.read.parquet(str(RUN07 / 'salaries.parquet'))
        audit.check('D05_KEYS', lambda: key_stats(jobs, 123849))
        audit.check('D07_KEYS', lambda: key_stats(salary, 123849))
        for label, frame, schemafile, fields in [('D05', jobs, ROOT / 'data/audit/d05_canonical_schema.json', 50),
                                                ('D07', salary, A07 / 'output_schema.json', 28)]:
            def schema_check(frame=frame, schemafile=schemafile, fields=fields):
                require(len(frame.columns) == fields, 'Field count')
                expected = T.StructType.fromJson(read_json(schemafile))
                equal(frame.schema.jsonValue(), expected.jsonValue())
                return {'fields': fields, 'schema_names_types_order_nullable_nested': 'EXACT',
                        'runtime_non_null_key_checked_separately': True}
            audit.check(label + '_SCHEMA', schema_check)
        audit.check('D05_D07_KEYSETS', lambda: equal([
            jobs.select('job_id').exceptAll(salary.select('job_id')).count(),
            salary.select('job_id').exceptAll(jobs.select('job_id')).count()], [0, 0]))
        audit.check('D05_D07_JOIN_GRAIN', lambda: key_stats(jobs.select('job_id').join(salary.select('job_id'), 'job_id'), 123849))
        def provenance():
            bad = F.lit(False)
            for f in ('source_title', 'source_description'):
                bad = bad | F.col(f).isNull() | ~F.sha2(F.col(f), 256).eqNullSafe(F.col(f + '_sha256'))
            bad = bad | ~F.col('source_text_file').eqNullSafe('data/raw/postings.csv') | ~F.col('canonical_schema_version').eqNullSafe('d05-v1')
            return equal(jobs.filter(bad).count(), 0)
        audit.check('D05_SOURCE_PROVENANCE', provenance)
        def raw_binding():
            # Independent Python CSV parser; retain only key+SHA, never text in audit.
            csv.field_size_limit(32 * 1024 * 1024); expected = {}
            with (ROOT / 'data/raw/postings.csv').open(encoding='utf8', newline='') as stream:
                for row in csv.DictReader(stream, strict=True):
                    require(None not in row and all(v is not None for v in row.values()), 'Malformed CSV')
                    value = Decimal(row['job_id']); require(value.is_finite() and value == value.to_integral_value(), 'Nonintegral key')
                    key = int(value); require(key not in expected, 'Raw duplicate key')
                    expected[key] = tuple(hashlib.sha256(row[f].encode('utf8')).hexdigest() for f in ('title', 'description'))
            require(len(expected) == 123849, 'Raw count')
            mismatch = 0
            for row in jobs.select('job_id', 'source_title_sha256', 'source_description_sha256').toLocalIterator():
                mismatch += expected.pop(row.job_id, None) != tuple(row)[1:]
            require(mismatch == 0 and not expected, 'Raw/canonical source mismatch')
            return {'rows': 123849, 'mismatches': 0, 'method': 'Independent strict multiline CSV parse, UTF8 SHA256, streamed canonical key/hash comparison'}
        audit.check('D05_RAW_SOURCE_BINDING', raw_binding)
        policy = load_policy()
        audit.check('D07_ALL_FIELDS_RECOMPUTATION', lambda: validate(jobs, salary, policy, 123849))
        audit.check('D07_STATUS_COUNTS', lambda: equal({r.normalization_status: r['count'] for r in salary.groupBy('normalization_status').count().collect()},
                                                    {'USABLE': 36059, 'MISSING': 87776, 'INVALID': 14}))
        def salary_identity():
            bad = (~F.col('conversion_policy_version').eqNullSafe(policy['version'])
                   | ~F.col('conversion_policy_sha256').eqNullSafe(policy['sha256'])
                   | ~F.col('population_scope').eqNullSafe(policy['scope']))
            equal(salary.filter(bad).count(), 0)
            usable = salary.filter("normalization_status = 'USABLE'")
            equal(usable.filter('source_conflict').count(), 0)
            require(usable.filter(~F.col('canonical_currency').isin(policy['currencies'])
                    | ~F.col('normalized_currency').eqNullSafe(F.col('canonical_currency'))
                    | ~F.col('normalized_unit').eqNullSafe('ANNUAL_EQUIVALENT')).count() == 0, 'Currency/units')
            return {'policy': policy, 'currency_counts': [r.asDict() for r in usable.groupBy('canonical_currency', 'canonical_pay_period').count().collect()], 'FX': 'NONE'}
        audit.check('D07_POLICY_CURRENCY', salary_identity)
        def samples():
            usable = salary.filter("normalization_status = 'USABLE'")
            counts = usable.agg(*[F.count('selected_salary.' + f).alias(f) for f in ('min_salary', 'med_salary', 'max_salary')]).first().asDict()
            equal(counts, {'min_salary': 29793, 'med_salary': 6266, 'max_salary': 29793})
            invalid = salary.filter("normalization_status = 'INVALID'")
            equal(invalid.filter(~F.col('selected_salary.med_salary').eqNullSafe(0)).count(), 0)
            return {'usable_samples': counts, 'reported_coverage': 36073 / 123849, 'usable_coverage': 36059 / 123849,
                    'denominator': 123849, 'scope': 'ALL_JOBS_NOT_IT', 'invalid14_all_med_zero': True}
        audit.check('D07_SAMPLES_COVERAGE_INVALID', samples)
        return config
    finally:
        spark.stop()


def main(args):
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', args.run_id), 'Invalid run_id')
    output = ROOT / 'data/audit/d09' / args.run_id
    require(not output.exists() and not output.is_symlink(), 'New run_id required; never overwrite')
    require(not output.parent.is_symlink(), 'Linked audit directory refused')
    require(output.resolve().is_relative_to(ROOT.resolve()), 'Audit escaped workspace')
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat(); start = time.perf_counter(); a = Audit()
    before = snapshot(); write_new(output / 'protected_before.json', before)
    a.check('GIT_RELEASES', git_releases)
    a.check('MANIFESTS_HASH_BINDINGS', stored_identity)
    a.check('D08_MEASUREMENT_STATISTICS', lambda: verify_statistics(
        list(csv.DictReader((A08 / 'benchmark_results.csv').open(encoding='utf8'))),
        list(csv.DictReader((A08 / 'benchmark_summary.csv').open(encoding='utf8')))))
    a.check('D08_RECEIPTS_SVG_BYTES', d08_receipts)
    a.check('D08_EVENT_METRICS_CONFIG', d08_events)
    a.check('D07_D08_HISTORICAL_TEST_EVIDENCE', test_evidence)
    a.check('D08_SCIENTIFIC_LIMITATIONS', limitations)
    if args.handoff_folder.exists() or args.handoff_zip.exists():
        a.check('HANDOFF_ZIP_MANIFEST_CHECKSUMS', lambda: handoff_check(args.handoff_folder, args.handoff_zip))
    else:
        a.record('HANDOFF_ZIP_MANIFEST_CHECKSUMS', 'NOT APPLICABLE', 'Neither handoff folder nor ZIP present locally')
    runtime = None
    try:
        runtime = spark_checks(a, args)
    except Exception as exc:
        a.record('SPARK_EXECUTION_COMPLETENESS', 'FAIL', {'error_type': type(exc).__name__, 'message': str(exc)[:1000],
                                                       'note': 'Some Spark checks may not have executed; never infer PASS'})
    for name, reason in {
        'A04_BUSINESS_ACCEPTANCE': 'No formal human acceptance supplied; technical parity/docs are not approval',
        'D06_SCHEMA_APPROVAL': 'Frozen schema is not external human approval',
        'D06_FULL_AUTHORIZATION': 'No run-specific human grant supplied; no approvals generated',
        'D06_FULL_KEYS_SCHEMA_NESTED': 'D06 Full not executed; no Pilot substitution',
        'D06_FULL_DECISIONS_SOURCE_PARQUET': 'D06 Full output/seal/key/source reconciliation unavailable',
        'D07_OFFICIAL_IT_SALARY_JOIN': 'Depends on validated D06 Full and human ACCEPT population policy',
        'Q07_BUSINESS_SIGNOFF_AND_IT_ANALYTICS': 'Five policy decisions/signoff and official D06 population pending',
        'D08_FULL_PIPELINE_BENCHMARK': 'Only D05/D07 workloads benchmarked; no D06 classification timing',
        'FINAL_IT_DASHBOARD_ACCEPTANCE': 'Official analytics/export and human dashboard acceptance unavailable',
    }.items():
        a.record(name, 'BLOCKED', reason)
    a.record('FX_USD_CONVERSION', 'NOT APPLICABLE', 'D07 policy forbids FX; currencies remain separate, not forced USD')
    a.record('MULTINODE_BENCHMARK', 'NOT APPLICABLE', 'Available D08 scope is one-machine Spark local mode')
    a.check('D06_NOT_EXECUTED_BOUNDARY', lambda: equal((ROOT / 'data/processed/d06').exists(), False))
    after = snapshot(); a.check('PROTECTED_INPUTS_ARTIFACTS_UNCHANGED', lambda: equal(after, before))
    write_new(output / 'validation_results.json', a.records)
    with (output / 'validation_results.csv').open('x', encoding='utf8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['check', 'status', 'evidence', 'at_utc']); w.writeheader()
        for r in a.records:
            w.writerow({**r, 'evidence': json.dumps(r['evidence'], ensure_ascii=False, default=str)})
    summary = {'run_id': args.run_id, 'scope': 'D09_AVAILABLE_D05_D07_D08_NOT_FULL_PIPELINE',
        'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': time.perf_counter() - start,
        'counts': tally(a.records), 'available_artifacts': 'FAIL' if any(r['status'] == 'FAIL' for r in a.records) else 'PASS',
        'full_pipeline': 'BLOCKED_D06_FULL', 'd06_full': 'NOT_EXECUTED', 'a04_acceptance': 'PENDING',
        'q07_acceptance': 'PENDING', 'baselines': BASELINES, 'runtime': runtime,
        'code_sha256': file_sha(__file__), 'protected_files': len(before),
        'scaffold_commit': git('rev-parse', 'support/tv1-d09-validation-scaffold'),
        'command': ['.venv/Scripts/python.exe', '-B', 'src/d09_validate_available.py', '--run-id', args.run_id,
                    '--windows-fs-jar', str(args.windows_fs_jar), '--handoff-folder', str(args.handoff_folder), '--handoff-zip', str(args.handoff_zip)],
        'writes': 'NEW_D09_AUDIT_ONLY', 'benchmark_rerun': False, 'salary_normalization_written': False,
        'note': 'D07 transform recomputed in memory for all-field comparison, never writes normalization output; historical test totals not added to D09 checks'}
    write_new(output / 'validation_summary.json', summary)
    inventory_rows = {p.name: {'bytes': p.stat().st_size, 'sha256': file_sha(p)} for p in output.iterdir() if p.is_file()}
    write_new(output / 'evidence_inventory.json', inventory_rows)
    print('D09_RESULT', json.dumps(summary, ensure_ascii=False), flush=True)
    return 1 if summary['available_artifacts'] == 'FAIL' else 0


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-id', required=True)
    p.add_argument('--windows-fs-jar', type=Path, required=True)
    p.add_argument('--handoff-folder', type=Path, default=ROOT.parent / 'TV1_Handoff_D05_D07')
    p.add_argument('--handoff-zip', type=Path, default=ROOT.parent / 'TV1_Handoff_D05_D07.zip')
    raise SystemExit(main(p.parse_args()))
