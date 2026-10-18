"""D05 official: audited, grain-preserving clean staging -> canonical Parquet.

Run with .venv/Scripts/python.exe src/build_canonical_jobs.py.
No taxonomy imports, IT filtering, technical-skill extraction or salary conversion.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from pyspark import StorageLevel
from pyspark.sql import functions as F
from pyspark.sql.types import LongType, StringType, StructField, StructType

from clean_data import TABLE_SPECS, ensure_windows_localfs_adapter
from d05_utils import aggregate_bridge, assert_unique_key, check_grain_preserved, get_spark_session
from d05_prejoin_validation import validate_latest_employee_counts

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / 'data/processed/clean'
OUTPUT = ROOT / 'data/processed/canonical/jobs'
AUDIT = ROOT / 'data/audit'
TV2_COMMIT = 'e437dcc11dda61f847673b9cc8c5801886c1996d'
EXPECTED = {k: v['expected_rows'] for k, v in TABLE_SPECS.items()}
EXPECTED.update(company_specialities=169367, employee_counts=35665)
KEYS = {k: v['unique_key'] for k, v in TABLE_SPECS.items()}
RELATIONS = [
    ('companies', 'postings', 'company_id'),
    ('postings', 'job_skills', 'job_id'),
    ('postings', 'job_industries', 'job_id'),
    ('postings', 'benefits', 'job_id'),
    ('postings', 'salaries', 'job_id'),
    ('skills', 'job_skills', 'skill_abr'),
    ('industries', 'job_industries', 'industry_id'),
    ('companies', 'company_industries', 'company_id'),
    ('companies', 'company_specialities', 'company_id'),
    ('companies', 'employee_counts', 'company_id'),
]


def snapshot():
    """Read-only inventory of raw/clean bytes and mtimes; excludes all D05 output."""
    return {
        str(p.relative_to(ROOT)).replace('\\', '/'):
        (p.stat().st_size, p.stat().st_mtime_ns)
        for folder in (ROOT / 'data/raw', CLEAN)
        for p in sorted(folder.rglob('*')) if p.is_file()
    }


def save_csv(name, rows):
    path = AUDIT / name
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def checksum(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def canonical_id(value):
    if not re.fullmatch(r'[+-]?\d+(?:\.0+)?', value.strip()):
        raise ValueError(f'Non-integral raw job_id: {value!r}')
    result = int(value.strip().split('.')[0])
    if not -(2**63) <= result < 2**63:
        raise ValueError('Raw job_id outside bigint')
    return result


def inspect_inputs(spark, checks):
    frames, inventory = {}, []
    schema_rules = list(csv.DictReader((AUDIT / 'd04_schema_changes.csv').open(encoding='utf-8')))
    for name in TABLE_SPECS:
        df = spark.read.parquet(str(CLEAN / name))
        frames[name] = df
        count = df.count()
        checks.append((f'input_rows:{name}', count == EXPECTED[name], str(count)))
        assert_unique_key(df, KEYS[name], name)
        if name == 'salaries':
            assert_unique_key(df, 'job_id', name)
        expected_types = {r['column']: r['clean_type'] for r in schema_rules if r['table'] == name}
        actual_types = {f.name: f.dataType.simpleString() for f in df.schema.fields}
        checks.append((f'input_schema:{name}', actual_types == expected_types, json.dumps(actual_types)))
        inventory.append(dict(table=name, rows=count, columns=len(df.columns),
                              keys='+'.join(KEYS[name]), key_nulls=0, duplicate_keys=0))
        print(f'INPUT {name}: {count} rows; schema/key PASS', flush=True)
    for parent, child, key in RELATIONS:
        checks.append((f'key_type:{parent}:{child}:{key}',
                       frames[parent].schema[key].dataType == frames[child].schema[key].dataType,
                       frames[child].schema[key].dataType.simpleString()))
    require_checks(checks)
    return frames, inventory


def referential_profile(frames):
    rows = []
    for parent, child, key in RELATIONS:
        parent_keys = frames[parent].select(key).distinct()
        counts = frames[child].groupBy(key).count().persist(StorageLevel.MEMORY_AND_DISK)
        try:
            nonnull = counts.where(F.col(key).isNotNull())
            orphan = nonnull.join(parent_keys, key, 'left_anti')
            total = counts.agg(F.sum('count')).first()[0]
            nonnull_rows = nonnull.agg(F.sum('count')).first()[0] or 0
            orphan_stats = orphan.agg(F.count('*'), F.sum('count')).first()
            distinct = nonnull.count()
            missing_keys = orphan_stats[0]
            rows.append(dict(parent=parent, child=child, key=key, child_rows=total,
                null_key_rows=total - nonnull_rows, child_distinct_keys=distinct,
                matched_keys=distinct-missing_keys, orphan_keys=missing_keys,
                orphan_rows=orphan_stats[1] or 0,
                orphan_key_sample=json.dumps([r[key] for r in orphan.orderBy(key).limit(10).collect()]),
                coverage_percent=100*(distinct-missing_keys)/distinct if distinct else None))
        finally:
            counts.unpersist()
    return rows


def raw_source(spark, postings, checks):
    columns = TABLE_SPECS['postings']['columns']
    path = ROOT / 'data/raw/postings.csv'
    with path.open(encoding='utf-8', newline='') as stream:
        reader = csv.reader(stream, strict=True)
        if next(reader) != columns:
            raise ValueError('Raw CSV header differs from the known 31 source columns')
    # Preserve empty strings, sentinels, quoted leading/trailing spaces and newlines.
    raw = (spark.read.schema(StructType([StructField(c, StringType()) for c in columns]))
        .option('header', True).option('enforceSchema', False).option('multiLine', True)
        .option('quote', '"').option('escape', '"').option('encoding', 'UTF-8')
        .option('ignoreLeadingWhiteSpace', False).option('ignoreTrailingWhiteSpace', False)
        .option('nullValue', '\u0000D05_NO_NULL_SENTINEL\u0000').option('emptyValue', '')
        .option('mode', 'FAILFAST').csv(str(path)))
    job = F.trim(F.col('job_id'))
    parsed_id = F.when(job.rlike(r'^[+-]?\d+(?:\.0+)?$'),
                       F.regexp_replace(job, r'\.0+$', '').try_cast('bigint'))
    # Univocity represents unquoted empty CSV fields as NULL even with a custom
    # nullValue. Python CSV's original parsed representation is an empty string.
    # FAILFAST and the verified header exclude short/malformed rows here.
    source = raw.select(parsed_id.alias('job_id'),
                        F.coalesce('title', F.lit('')).alias('source_title'),
                        F.coalesce('description', F.lit('')).alias('source_description'))
    source = (source.withColumn('source_title_sha256', F.sha2('source_title', 256))
              .withColumn('source_description_sha256', F.sha2('source_description', 256))
              .persist(StorageLevel.DISK_ONLY))
    assert_unique_key(source, 'job_id', 'raw text source')
    n = source.count()
    checks.append(('raw_source_rows', n == EXPECTED['postings'], str(n)))
    a = source.select('job_id').exceptAll(postings.select('job_id')).count()
    b = postings.select('job_id').exceptAll(source.select('job_id')).count()
    checks.append(('source_clean_key_bijection', a == b == 0, f'raw_only={a};clean_only={b}'))

    # Independent parser check for every record, collecting hashes only, never text.
    csv.field_size_limit(32 * 1024 * 1024)
    expected_hashes = {}
    with path.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream, strict=True):
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Malformed raw CSV record')
            key = canonical_id(row['job_id'])
            if key in expected_hashes:
                raise ValueError('Duplicate raw job_id in independent CSV parser')
            expected_hashes[key] = (checksum(row['title']), checksum(row['description']))
    mismatches = 0
    for row in source.select('job_id', 'source_title_sha256', 'source_description_sha256').toLocalIterator():
        mismatches += expected_hashes.pop(row.job_id, None) != tuple(row)[1:]
    checks.append(('all_source_text_python_csv_sha256', mismatches == 0 and not expected_hashes,
                   f'mismatches={mismatches};unseen={len(expected_hashes)};rows={n}'))
    require_checks(checks)
    print(f'SOURCE text: {n} rows; every Python CSV/Spark SHA-256 matched', flush=True)
    return source


def mapped_bridge(child, dimension, code, label, output, frames):
    # Dimension keys have already been checked unique/non-null.
    joined = frames[child].join(frames[dimension], code, 'left')
    value = F.struct(F.col(code), F.col(label),
                     F.when(F.col(label).isNull(), F.lit('MISSING_LABEL'))
                     .otherwise(F.lit('MAPPED')).alias('mapping_status'))
    return aggregate_bridge(joined.withColumn('_value', value), 'job_id', '_value', output)


def build_dimensions(frames, spark, checks):
    bridges = {
        'job_functions': mapped_bridge('job_skills', 'skills', 'skill_abr', 'skill_name', 'job_functions', frames),
        'job_industries': mapped_bridge('job_industries', 'industries', 'industry_id', 'industry_name', 'job_industries', frames),
        'benefits': aggregate_bridge(frames['benefits'].withColumn('_value', F.struct('type', 'inferred')),
                                    'job_id', '_value', 'benefits'),
        'company_industries': aggregate_bridge(frames['company_industries'], 'company_id', 'industry', 'company_industries'),
        'company_specialities': aggregate_bridge(frames['company_specialities'], 'company_id', 'speciality', 'company_specialities'),
    }
    # Reuse the scaffold's real-data snapshot and key validation.
    latest = validate_latest_employee_counts(CLEAN, spark)
    latest_count = latest.count()
    checks.append(('latest_employee_companies', latest_count == EXPECTED['companies'], str(latest_count)))
    company = frames['companies']
    for key in ('company_industries', 'company_specialities'):
        company = company.join(bridges[key], 'company_id', 'left')
    employee_fields = [c for c in latest.columns if c != 'company_id']
    company = company.join(latest.select('company_id', F.struct(*employee_fields).alias('latest_employee_snapshot')),
                           'company_id', 'left')
    assert_unique_key(company, 'company_id', 'company dimension')
    company = company.select('company_id', F.struct(*[F.col(c) for c in company.columns if c != 'company_id']).alias('company'))
    salary = frames['salaries'].select('job_id', F.struct(*[F.col(c) for c in frames['salaries'].columns if c != 'job_id']).alias('salary_record'))
    return bridges, company, salary


def job_grain(df):
    row = df.agg(F.count('*').alias('rows'), F.countDistinct('job_id').alias('distinct'),
                 F.sum(F.when(F.col('job_id').isNull(), 1).otherwise(0)).alias('nulls')).first()
    return row.rows, row.distinct, row.nulls or 0


def require_checks(checks):
    failed = [x for x in checks if not x[1]]
    if failed:
        raise AssertionError(f'Validation failed: {failed}')


def validate_content(actual, expected, checks, label):
    # Exact row-set comparison is done on compact SHA-256 fingerprints retaining
    # every field, nested value, NULL and ordered array; no driver text collection.
    def hashes(df):
        return df.select('job_id', F.sha2(F.to_json(F.struct(*df.columns),
            options={'ignoreNullFields': 'false'}), 256).alias('row_sha256'))
    forward = hashes(actual).exceptAll(hashes(expected)).count()
    backward = hashes(expected).exceptAll(hashes(actual)).count()
    checks.append((label, forward == backward == 0, f'forward={forward};backward={backward}'))


def write_report(manifest, inventory, relations, joins, checks, schemas):
    def table(headers, rows):
        def cell(v):
            return str(v).replace('|', '\\|').replace('\n', ' ')
        return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |'] +
                         ['| '+' | '.join(cell(v) for v in row)+' |' for row in rows])
    text = f'''# D05 Official Implementation Report

Status: **IMPLEMENTATION PASS — READY FOR ACCEPTANCE REVIEW**.
Official acceptance: **PENDING GROUP REVIEW**. D06: **NOT EXECUTED**.

Run UTC: {manifest['run_utc']}; branch `{manifest['branch']}`; base commit `{manifest['git_head']}`.

## A03 readiness

Technical readiness PASS; see d05_a03_readiness_review.md. Source commit
`{TV2_COMMIT}`; report SHA-256 `{manifest['a03_sha256']}`.
This does not assert formal acceptance of A03 by the team leader.

## Environment and output

Python {manifest['python']}; PySpark {manifest['spark']}; Java {manifest['java']}.
Spark local[*], SQL session timezone UTC. Output: `data/processed/canonical/jobs/`.
Output directories use overwrite only for this pipeline's canonical output.
The Windows local filesystem adapter is reused from D04; raw and clean inputs are read-only.
The process defaults to a 3 GB driver heap (unless PYSPARK_SUBMIT_ARGS is supplied
externally). Automatic and adaptive broadcast joins are disabled for this session
because the source-text relation is too large for the default local heap.

## Inputs and key validation

{table(['Table','Rows','Columns','Key','NULL keys','Duplicate keys'], [[r[k] for k in ['table','rows','columns','keys','key_nulls','duplicate_keys']] for r in inventory])}

All schemas are checked against D04's schema_changes evidence; relationship key types
must match. Salaries.job_id is additionally checked unique.

## JOIN design and reconciliation

Base: all clean postings, retaining their 35 columns. Restore raw source text with
a validated 1:1 LEFT JOIN; attach three pre-aggregated job bridges, the 0..1 salary
record and a pre-aggregated company dimension. Every right-side entity key is unique.

{table(['Step','Before','Right','After','Distinct job_id','NULL job_id'], [[r[k] for k in ['step','before_rows','right_rows','after_rows','distinct_job_id','null_job_id']] for r in joins])}

## Canonical schema and NULL policy

{table(['Column','Spark type','Nullable'], [[s['name'],s['type'],s['nullable']] for s in schemas])}

Full nested schema is in `data/audit/d05_canonical_schema.json`. The original 35
clean postings columns keep their names and types. `title`/`description` mean D04
clean text; `source_title`/`source_description` mean original parsed CSV text.
Parquet readback exposes nullable=true, including job_id; the non-null/unique
job_id requirement is an enforced runtime invariant rather than a storage guarantee.
`job_functions` contains sorted distinct structs(skill_abr,skill_name,mapping_status).
`job_industries` contains sorted distinct structs(industry_id,industry_name,mapping_status).
`benefits` contains sorted distinct structs(type,inferred), preserving inferred flags.
`salary_record` preserves the salaries source separately from postings salary columns.
`company` contains company attributes, arrays and latest_employee_snapshot.
Absent bridge links remain NULL (not an assertion that the real job has no skills).
No-link status flags make this explicit. Present industries with NULL names retain
their IDs and MISSING_LABEL. No technical_skills output is created.

## Referential coverage

{table(['Parent','Child','Key','Child rows','NULL rows','Orphan keys','Orphan rows'], [[r[k] for k in ['parent','child','key','child_rows','null_key_rows','orphan_keys','orphan_rows']] for r in relations])}

All orphan counts remain in the audit; no input table is modified. Unreferenced
bridge records remain in clean staging. Canonical grain is postings, so child-only
job IDs do not introduce new jobs. Company missing/orphan status is distinguished.

## Source-text provenance

Raw reader: UTF-8, multiline, quote/escape double quote, no leading/trailing trim,
FAILFAST, source empty strings retained, no sentinel/encoding repair. Only job_id
is strictly canonicalized to bigint without float. Every raw title/description hash
was cross-checked against Python csv.DictReader on {EXPECTED['postings']} rows.
Source hashes are UTF-8 SHA-256 of the parsed fields, not of CSV escaped bytes.
Source text and hashes survive Parquet round-trip; clean postings fields are also
fingerprint-checked against D04. No A04 parity claim is made.

## Salary and snapshots

No imputation, annualization, currency or pay-period conversion. Preserve both
postings salary fields and salary_record. Latest employee snapshot is selected by
time_recorded descending, then employee_count/follower_count ascending. Clean
(company_id,time_recorded) is unique, making the latest selection deterministic.
Latest means latest in this source dataset, not as-of the posting date.

## Timezone

Spark TimestampType uses session UTC; no epoch is shifted. Time evidence is emitted
as explicit UTC strings with a Z suffix. Employee epoch 1712346173 equals
2024-04-05T19:42:53Z, or 2024-04-06T02:42:53+07:00 in Asia/Bangkok.
The older D05 pre-check labeled the latter local display as UTC; that historical
report is left unchanged. See d05_time_coverage.csv for runtime UTC values.

## Runtime validation

{table(['Check','Status','Details'], [[n,'PASS' if ok else 'FAIL',d] for n,ok,d in checks])}

Raw and D04 clean file sizes/mtimes remained unchanged. Canonical write/read and
full content fingerprints passed. Validation includes sorted distinct bridge arrays,
repeat aggregation under different partitioning, source-key bijection and no row loss.
Small Spark regressions can be run with `.venv/Scripts/python.exe -B src/test_d05_official.py`;
their independently recorded results are in `data/audit/d05_official_regression_tests.csv`.

## Limitations and D06 handoff

No IT classification, A04 execution, skill extraction, salary analytics or D08/D09
official run. D06 must explicitly select source versus clean text, retain exact text
for evidence offsets, convert bigint IDs to the classifier's canonical string API,
distribute Python modules/config and preserve REVIEW. Taxonomy active is unchanged.
Frozen 176-job A04 inputs/predictions/manifests are still required for exact parity.
This report records implementation validation, not an automatic team acceptance.
'''
    (ROOT / 'docs/d05_official_report.md').write_text(text, encoding='utf-8')


def main():
    started = time.monotonic()
    before = snapshot()
    if OUTPUT.exists():
        marker = ROOT / 'data/processed/canonical/d05_run_manifest.json'
        if not marker.exists():
            raise RuntimeError('Canonical output exists without this pipeline manifest; refusing overwrite')
    a03 = subprocess.check_output(['git', 'show', f'{TV2_COMMIT}:docs/a03_skills_industries_report.md'], cwd=ROOT)
    if os.name == 'nt':
        ensure_windows_localfs_adapter(ROOT)
    # Raw and clean text together are large; never broadcast the source-text
    # relation based on misleading CSV/cache size estimates. Settings are local
    # to this process/session, not machine-wide environment configuration.
    os.environ.setdefault('PYSPARK_SUBMIT_ARGS', '--driver-memory 3g pyspark-shell')
    spark = get_spark_session('BigDataITRecruitment-D05-Official', ROOT)
    spark.conf.set('spark.sql.shuffle.partitions', '12')
    spark.conf.set('spark.sql.autoBroadcastJoinThreshold', '-1')
    spark.conf.set('spark.sql.adaptive.autoBroadcastJoinThreshold', '-1')
    checks, joins, persisted = [], [], []
    try:
        frames, inventory = inspect_inputs(spark, checks)
        relations = referential_profile(frames)
        historical = list(csv.DictReader((AUDIT/'d05_precheck_join_coverage.csv').open(encoding='utf-8')))
        for current, old in zip(relations, historical):
            ok = (current['parent'], current['child'], current['key'], current['child_rows'],
                  current['null_key_rows'], current['matched_keys'], current['orphan_keys'], current['orphan_rows']) == (
                  old['parent_table'], old['child_table'], old['child_key'], int(old['child_total_rows']),
                  int(old['child_null_rows']), int(old['matched_keys']), int(old['unmatched_keys']), int(old['orphan_child_rows']))
            checks.append((f'referential_reconciliation:{current["child"]}:{current["key"]}', ok, json.dumps(current)))
        checks.append(('referential_relationship_count', len(relations) == len(historical) == 10, str(len(relations))))
        require_checks(checks)
        source = raw_source(spark, frames['postings'], checks)
        persisted.append(source)
        bridges, company, salary = build_dimensions(frames, spark, checks)
        cardinality = []
        for name in ['job_skills','job_industries','benefits','company_industries','company_specialities']:
            key = 'company_id' if name.startswith('company_') else 'job_id'
            counts = frames[name].groupBy(key).count()
            stats = counts.agg(F.count('*'), F.max('count'), F.sum(F.when(F.col('count') > 1, 1).otherwise(0))).first()
            cardinality.append(dict(table=name, entity_key=key, entities=stats[0], max_values=stats[1], multi_value_entities=stats[2]))

        # Check aggregation order, de-duplication and determinism independently.
        for name, original in bridges.items():
            key = 'company_id' if name.startswith('company_') else 'job_id'
            assert_unique_key(original, key, name)
            array_col = next(c for c in original.columns if c != key)
            bad = original.where(~F.col(array_col).eqNullSafe(F.array_sort(F.array_distinct(array_col)))).count()
            checks.append((f'sorted_distinct_array:{name}', bad == 0, f'bad_rows={bad}'))
        a = aggregate_bridge(frames['job_skills'].repartition(3), 'job_id', 'skill_abr', 'v')
        b = aggregate_bridge(frames['job_skills'].repartition(7), 'job_id', 'skill_abr', 'v')
        differences = a.exceptAll(b).count() + b.exceptAll(a).count()
        checks.append(('aggregation_repartition_determinism', differences == 0, str(differences)))
        require_checks(checks)

        jobs = frames['postings']
        right_frames = [('source_text', source, 'job_id'),
            ('job_functions', bridges['job_functions'], 'job_id'),
            ('job_industries', bridges['job_industries'], 'job_id'),
            ('benefits', bridges['benefits'], 'job_id'),
            ('salary', salary, 'job_id'), ('company', company, 'company_id')]
        for name, right, key in right_frames:
            assert_unique_key(right, key, name)
            # Keep cache compact: grain checks do not materialize description text.
            rows_before, distinct_before, _ = job_grain(jobs)
            right_count = right.count()
            jobs = jobs.join(right, key, 'left')
            rows_after, distinct_after, nulls = job_grain(jobs)
            ok = check_grain_preserved(rows_before, rows_after, distinct_before, distinct_after)
            checks.append((f'left_join_grain:{name}', ok and nulls == 0, f'rows={rows_after};distinct={distinct_after}'))
            joins.append(dict(step=name, before_rows=rows_before, right_rows=right_count,
                              after_rows=rows_after, distinct_job_id=distinct_after, null_job_id=nulls))
            require_checks(checks)
            print(f'JOIN {name}: {rows_before} -> {rows_after}; distinct={distinct_after}', flush=True)

        jobs = jobs.select(*frames['postings'].columns,
            'source_title','source_description','source_title_sha256','source_description_sha256',
            'job_functions','job_industries','benefits','salary_record','company')
        jobs = (jobs.withColumn('source_text_file', F.lit('data/raw/postings.csv'))
            .withColumn('canonical_schema_version', F.lit('d05-v1'))
            .withColumn('has_job_function_links', F.col('job_functions').isNotNull())
            .withColumn('has_job_industry_links', F.col('job_industries').isNotNull())
            .withColumn('has_benefit_links', F.col('benefits').isNotNull())
            .withColumn('company_lookup_status', F.when(F.col('company_id').isNull(), 'MISSING_COMPANY_ID')
                .when(F.col('company').isNull(), 'ORPHAN_COMPANY_ID').otherwise('MATCHED'))
            .persist(StorageLevel.DISK_ONLY))
        persisted.append(jobs)
        n, distinct, nulls = job_grain(jobs)
        checks.append(('canonical_final_grain', (n, distinct, nulls) == (123849,123849,0), str((n,distinct,nulls))))
        require_checks(checks)
        jobs.coalesce(4).write.mode('overwrite').parquet(str(OUTPUT))
        restored = spark.read.parquet(str(OUTPUT)).persist(StorageLevel.DISK_ONLY)
        persisted.append(restored)
        checks.append(('roundtrip_grain', job_grain(restored) == (123849,123849,0), str(job_grain(restored))))
        checks.append(('roundtrip_data_types', jobs.schema.simpleString() == restored.schema.simpleString(), restored.schema.simpleString()))
        validate_content(restored, jobs, checks, 'full_nested_content_roundtrip_sha256')
        validate_content(restored.select(*frames['postings'].columns), frames['postings'], checks, 'all_D04_postings_fields_preserved')
        for col in ['title','description']:
            invalid = restored.where(~F.sha2(f'source_{col}',256).eqNullSafe(F.col(f'source_{col}_sha256'))).count()
            checks.append((f'source_hash_roundtrip:{col}', invalid == 0, str(invalid)))
        times = []
        for name, col in [('postings','original_listed_time'),('postings','listed_time'),
                           ('postings','expiry'),('postings','closed_time'),('employee_counts','time_recorded')]:
            epoch = F.regexp_replace(F.col(f'{col}_raw'), r'\.0+$', '').try_cast('bigint')
            typed_epoch = F.unix_seconds(col) if name == 'employee_counts' else F.unix_millis(col)
            bad = frames[name].where(~typed_epoch.eqNullSafe(epoch)).count()
            checks.append((f'UTC_epoch_unchanged:{name}:{col}', bad == 0, f'mismatches={bad}'))
            row = frames[name].agg(F.date_format(F.min(col), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"),
                                   F.date_format(F.max(col), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")).first()
            times.append(dict(table=name,column=col,min_utc=row[0],max_utc=row[1],timezone='UTC'))
        checks.append(('immutable_raw_clean_size_mtime', before == snapshot(), f'files={len(before)}'))
        require_checks(checks)
        manifest = dict(run_utc=datetime.now(timezone.utc).isoformat(), branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
            git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            a03_commit=TV2_COMMIT, a03_sha256=hashlib.sha256(a03).hexdigest(),
            python=platform.python_version(), spark=spark.version,
            java=spark.sparkContext._jvm.java.lang.System.getProperty('java.version'),
            timezone='UTC', output=str(OUTPUT.relative_to(ROOT)), output_rows=n,
            validation_checks=len(checks), elapsed_seconds=round(time.monotonic()-started,3),
            raw_clean_unchanged=True, a04_parity='NOT_EXECUTED_REFERENCE_MISSING')
        save_csv('d05_official_input_inventory.csv',inventory)
        save_csv('d05_official_referential_coverage.csv',relations)
        save_csv('d05_official_bridge_cardinality.csv',cardinality)
        save_csv('d05_official_join_reconciliation.csv',joins)
        save_csv('d05_official_validation.csv',[dict(check=a,status='PASS' if b else 'FAIL',details=c) for a,b,c in checks])
        save_csv('d05_time_coverage.csv',times)
        (AUDIT/'d05_canonical_schema.json').write_text(restored.schema.json(),encoding='utf-8')
        (AUDIT/'d05_official_run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        (OUTPUT.parent/'d05_run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        schemas=[dict(name=f.name,type=f.dataType.simpleString(),nullable=f.nullable) for f in restored.schema]
        write_report(manifest,inventory,relations,joins,checks,schemas)
        print(json.dumps(manifest,indent=2),flush=True)
        print('D05 IMPLEMENTATION VALIDATION PASS; formal team acceptance is separate.',flush=True)
    finally:
        for df in reversed(persisted):
            df.unpersist()
        spark.stop()


if __name__ == '__main__':
    main()
