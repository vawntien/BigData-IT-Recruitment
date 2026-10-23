"""Pinned aggregate-only local previews. No production gate API or persistent cache.

Pins are receiver metadata (hashes/schema/grain), never copies of producer data.
Business approval of aggregates is separate from local display authorization.
"""
from dataclasses import dataclass, field
from datetime import date
import csv
import hashlib
import io
import json
import math
import ntpath
from pathlib import Path, PurePosixPath
import stat
import zipfile
import pyarrow as pa
import pyarrow.parquet as pq

PINS = json.loads(Path(__file__).with_name('technical_preview_pins.json').read_text(encoding='utf8'))
MAX_BYTES = 4_000_000
INPUT_DIGEST = '17ae5383e848f7323b99800bd3d79a72e84e2bca62844f66dd00aaa06e80a9b2'

@dataclass(frozen=True)
class Result:
    passed: bool
    issue: str = ''
    tables: dict = field(default_factory=dict)
    run_id: str = ''
    sha256: str = ''

class Rejected(ValueError):
    pass

def require(ok, code):
    if not ok:
        raise Rejected(code)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def same(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float) or isinstance(b, float):
        return math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    return type(a) is type(b) and a == b

def _pairs(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, 'DUPLICATE_JSON_KEY')
        result[k] = v
    return result

def document(raw):
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_pairs,
                      parse_constant=lambda _: require(False, 'NONFINITE_JSON'))

def _archive(data, pin):
    require(sha(data) == pin['sha256'], 'ARCHIVE_HASH_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries = z.infolist()
        expected = {pin['root'] + n for n in pin['members']}
        require(len(entries) == len(expected) and {e.filename for e in entries} == expected, 'INVENTORY_MISMATCH')
        seen = set()
        for e in entries:
            n = e.filename
            require(not e.is_dir() and not n.startswith(('/', '\\')) and '\\' not in n
                    and not ntpath.splitdrive(n)[0] and ':' not in n
                    and '..' not in PurePosixPath(n).parts and n.casefold() not in seen
                    and stat.S_IFMT(e.external_attr >> 16) in (0, stat.S_IFREG)
                    and not e.flag_bits & 1 and e.compress_type in (0, 8)
                    and e.file_size <= MAX_BYTES, 'UNSAFE_ARCHIVE')
            seen.add(n.casefold())
        require(sum(e.file_size for e in entries) <= MAX_BYTES, 'ARCHIVE_TOO_LARGE')
        require(z.testzip() is None, 'ARCHIVE_CRC_FAILED')
        payload = {n: z.read(pin['root'] + n) for n in pin['members']}
    require(all(sha(payload[n]) == digest for n, digest in pin['members'].items()), 'MEMBER_HASH_MISMATCH')
    inv_name = 'SHA256SUMS.json' if not pin['root'] else 'SHA256_INVENTORY.json'
    inv = document(payload[inv_name])
    if inv_name == 'SHA256SUMS.json':
        require(set(inv) == set(payload) - {inv_name} and all(sha(payload[n]) == digest for n, digest in inv.items()), 'INVENTORY_MISMATCH')
    else:
        items = inv['files']
        require(len(items) == len({e['path'] for e in items})
                and {e['path'] for e in items} == set(payload) - {inv_name}, 'INVENTORY_MISMATCH')
        require(all(sha(payload[e['path']]) == e['sha256'] and len(payload[e['path']]) == e['bytes'] for e in items), 'INVENTORY_MISMATCH')
    return payload

def _validate_rows(name, rows, info):
    require(len(rows) == info['rows'], 'ROW_COUNT_MISMATCH')
    keys = info['keys']
    require(len({tuple(r[k] for k in keys) for r in rows}) == len(rows), 'DUPLICATE_GRAIN')
    for r in rows:
        n = r['job_count']
        require(type(n) is int and 0 < n <= 5206, 'INVALID_COUNT')
        for col in ('denominator_all_it', 'denominator_known', 'processed_n', 'valid_timestamp_n'):
            if col not in r:
                continue
            if col in info:
                expected = info[col]
            else:
                dim = keys[0]
                expected = next(s[col] for s in info['scope_denominators'] if s['scope'] == r[dim])
            require(type(r[col]) is int and r[col] == expected and n <= r[col], 'DENOMINATOR_MISMATCH')
        for rate, denom in [('share_all_it', 'denominator_all_it'), ('share_known', 'denominator_known'),
                            ('share_of_processed', 'processed_n'), ('share_of_processed_group', 'processed_n'),
                            ('share_of_valid', 'valid_timestamp_n')]:
            if rate in r:
                expected = None if rate == 'share_known' and r['category'] is None else n / r[denom]
                require(same(r[rate], expected), 'INVALID_FRACTION')
    if name.startswith(('q02_', 'q03_', 'q04_')):
        require(sum(r['job_count'] for r in rows) == 5206, 'POPULATION_MISMATCH')
        if 'denominator_known' in info:
            require(sum(r['job_count'] for r in rows if r['category'] is not None) == info['denominator_known'], 'KNOWN_MISMATCH')
    if name.startswith('q08_'):
        require(sum(r['job_count'] for r in rows) == info['valid_timestamp_n'], 'TIME_POPULATION_MISMATCH')
        for r in rows:
            value = r['period']
            if name.endswith('_month'):
                require(len(value) == 7 and date.fromisoformat(value + '-01').day == 1, 'INVALID_UTC_MONTH')
            else:
                require(len(value) == 10 and date.fromisoformat(value).weekday() == 0, 'INVALID_UTC_WEEK')
    if name == 'q04_remote_flag':
        require({r['remote_allowed']: r['job_count'] for r in rows} == {None: 3721, True: 1485}, 'REMOTE_NULL_MISMATCH')

def _table(payload, name, info):
    prefix = info['prefix']
    parts = sorted(n for n in payload if n.startswith(prefix + '.parquet/') and n.endswith('.parquet'))
    require(bool(parts), 'MISSING_TABLE')
    records = []
    for part in parts:
        pf = pq.ParquetFile(io.BytesIO(payload[part]))
        fields = [{'name': f.name, 'type': str(f.type), 'nullable': f.nullable} for f in pf.schema_arrow]
        require(fields == info['fields'], 'PHYSICAL_SCHEMA_MISMATCH')
        require(document(pf.schema_arrow.metadata[b'org.apache.spark.sql.parquet.row.metadata']) == info['writer_schema'], 'WRITER_SCHEMA_MISMATCH')
        records.extend(pf.read().to_pylist())
    _validate_rows(name, records, info)
    csvrows = list(csv.DictReader(io.StringIO(payload[prefix + '.csv'].decode('utf-8-sig'))))
    columns = [f['name'] for f in info['fields']]
    require(len(csvrows) == len(records) and list(csvrows[0]) == columns, 'CSV_PARQUET_MISMATCH')
    parsed = []
    for row in csvrows:
        converted = {}
        for f in info['fields']:
            v = row[f['name']]
            if v == '': v = None
            elif f['type'].startswith('int'): v = int(v)
            elif f['type'] == 'double': v = float(v)
            elif f['type'] == 'bool':
                require(v in ('true', 'false', 'True', 'False'), 'INVALID_CSV_BOOLEAN')
                v = v.lower() == 'true'
            converted[f['name']] = v
        parsed.append(converted)
    key = lambda r: tuple(r[k] for k in info['keys'])
    indexed = {key(r): r for r in parsed}
    require(len(indexed) == len(records) and all(key(r) in indexed and all(same(v, indexed[key(r)][k]) for k, v in r.items()) for r in records), 'CSV_PARQUET_MISMATCH')
    return tuple(records)

def _receive(data, query):
    pin = PINS[query]
    payload = _archive(data, pin)
    manifest = document(payload[pin['manifest']])
    require(manifest['run_id'] == pin['run_id'], 'RUN_MISMATCH')
    require(manifest['input_contract']['d06_confirmation']['input_sha256'] == INPUT_DIGEST, 'LINEAGE_MISMATCH')
    require(manifest['queries'][query]['status'] == 'SUCCESS'
            and set(manifest['queries'][query]['tables']) == set(pin['tables']), 'TABLE_SET_MISMATCH')
    if query == 'Q06':
        require(sha(payload['runner_manifest.json']) == 'b50c0aaf9d72d891c11da1471b29935a73f5795a26f2e4ecb08871a45c820804', 'MANIFEST_MISMATCH')
        require(manifest['input_contract']['a05_confirmation']['run_manifest_sha256'] == 'bfa838315c9beff1af76cb2d8a87a066b5c1a322eb02e06b50e21f3fc830dc1f'
                and manifest['queries']['Q06']['zero_hit_jobs'] == 1124
                and manifest['queries']['Q06']['denominator'] == 5206, 'A05_SCOPE_MISMATCH')
    else:
        h = document(payload['HANDOFF.json'])
        require(h['query'] == query and h['run_id'] == pin['run_id'] and h['enriched_digest'] == INPUT_DIGEST
                and set(h['tables']) == set(pin['tables']), 'HANDOFF_MISMATCH')
        v = document(payload['run/independent_validation.json'])
        require(v['status'] == 'PASS' and v['runner_manifest_sha256'] == sha(payload[pin['manifest']]), 'VALIDATION_BINDING_MISMATCH')
    tables = {n: _table(payload, n, info) for n, info in pin['tables'].items()}
    if query == 'Q06':
        global_counts = {r['skill_code']: r['job_count'] for r in tables['q06_skills_global']}
        for name in ('q06_skills_by_group', 'q06_skills_by_experience'):
            totals = {}
            for r in tables[name]: totals[r['skill_code']] = totals.get(r['skill_code'], 0) + r['job_count']
            require(totals == global_counts, 'SKILL_SCOPE_CONSERVATION')
            require(sum(s['processed_n'] for s in pin['tables'][name]['scope_denominators']) == 5206, 'SKILL_DENOMINATOR_CONSERVATION')
    return Result(True, tables=tables, run_id=pin['run_id'], sha256=pin['sha256'])

def load_preview(query, local_path, *, confirmed=False):
    if confirmed is not True:
        return Result(False, 'CONFIRMATION_REQUIRED')
    try:
        require(query in PINS, 'QUERY_NOT_ALLOWED')
        require(type(local_path) is str and not local_path.startswith(('\\\\', '//')), 'INVALID_LOCAL_PATH')
        path = Path(local_path)
        require(path.is_absolute() and path.suffix.lower() == '.zip' and not path.is_symlink() and path.is_file(), 'INVALID_LOCAL_PATH')
        require(path.stat().st_size <= MAX_BYTES, 'ARCHIVE_TOO_LARGE')
        with path.open('rb') as f: data = f.read(MAX_BYTES + 1)
        require(len(data) <= MAX_BYTES, 'ARCHIVE_TOO_LARGE')
        return _receive(data, query)
    except Rejected as e:
        return Result(False, str(e))
    except Exception:
        return Result(False, 'UNREADABLE_OR_INVALID_ARTIFACT')
