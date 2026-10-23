"""Pinned real receiving and fail-closed UI. External packages never enter Git."""
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import pyarrow as pa
import pyarrow.parquet as pq
from streamlit.testing.v1 import AppTest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components import technical_preview as r, artifact_gate
ROOT = Path.home() / 'Desktop/t'
PATHS = {q: ROOT / f'TV2_HANDOFF_TV3_{q}' / f'TV2_{q}_VALIDATED_HANDOFF_TV3_20261022.zip' for q in ('Q02','Q03','Q04','Q08')}
PATHS['Q06'] = ROOT / 'TV2_Q06_OFFICIAL_20261022_01.zip'
VIEWS = {'Q02':'8_Experience.py','Q03':'9_Locations.py','Q04':'10_Work_Type.py','Q08':'11_Time_Trends.py','Q06':'2_Skills.py'}
DASHBOARD = Path(__file__).resolve().parents[1]

class BoundaryTests(unittest.TestCase):
    def test_consent_prevents_any_file_read(self):
        with patch.object(Path,'open',side_effect=AssertionError('read')):
            self.assertEqual(r.load_preview('Q02','anything').issue,'CONFIRMATION_REQUIRED')
    def test_missing_file(self):
        self.assertFalse(r.load_preview('Q02',str(Path.cwd()/'missing.zip'),confirmed=True).passed)
    def test_wrong_hash_and_corrupt(self):
        for data in (b'PK\x03\x04corrupt',b'wrong zip'):
            with tempfile.TemporaryDirectory() as td:
                p=Path(td)/'x.zip';p.write_bytes(data)
                result=r.load_preview('Q02',str(p),confirmed=True)
                self.assertFalse(result.passed);self.assertFalse(result.tables)
    def test_gate_unchanged(self):
        self.assertEqual(artifact_gate.real_artifact_status(exists=True),'BLOCKED')
    def test_unknown_query(self):
        self.assertEqual(r.load_preview('Q07','x',confirmed=True).issue,'QUERY_NOT_ALLOWED')
    def test_navigation_never_reads(self):
        for q,v in VIEWS.items():
            with self.subTest(q=q),patch('components.technical_preview_views.load_preview') as load:
                a=AppTest.from_file(str(DASHBOARD/'views'/v)).run(timeout=20)
                self.assertFalse(a.exception); self.assertFalse(a.metric);self.assertFalse(a.dataframe);load.assert_not_called()

    def test_synthetic_cannot_call_real_receiver(self):
        with patch('components.technical_preview_views.load_preview',side_effect=AssertionError('REAL_READ')) as load:
            a=AppTest.from_file(str(DASHBOARD/'views/12_Query_Demo.py')).run(timeout=20)
            a.toggle[0].set_value(True).run(timeout=20)
            self.assertFalse(a.exception);self.assertTrue(a.metric);load.assert_not_called()

@unittest.skipUnless(all(p.is_file() for p in PATHS.values()), 'Exact external ZIPs required')
class RealTests(unittest.TestCase):
    def load(self,q):
        x=r.load_preview(q,str(PATHS[q]),confirmed=True);self.assertTrue(x.passed,x.issue);return x
    def test_all_actual_packages(self):
        for q,p in r.PINS.items():
            with self.subTest(q=q):
                x=self.load(q);self.assertEqual(set(x.tables),set(p['tables']))
                self.assertEqual({n:len(t) for n,t in x.tables.items()},{n:i['rows'] for n,i in p['tables'].items()})
    def payload(self,q):
        z=zipfile.ZipFile(PATHS[q]);root=r.PINS[q]['root'];return {n[len(root):]:z.read(n) for n in z.namelist()}
    def test_schema_mismatch(self):
        p=self.payload('Q02');info=r.PINS['Q02']['tables']['q02_experience'];bad=deepcopy(info);bad['fields'][0]['type']='bool'
        with self.assertRaisesRegex(r.Rejected,'SCHEMA'):r._table(p,'q02_experience',bad)
    def test_missing_extra_table_and_traversal(self):
        q='Q02';z=zipfile.ZipFile(PATHS[q]);original={n:z.read(n) for n in z.namelist()}
        for mode in ['missing','extra','traversal']:
            content=dict(original)
            if mode=='missing':content.pop(next(n for n in content if n.endswith('.csv')))
            else:content['../escape' if mode=='traversal' else 'extra.csv']=b'x'
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,'w') as dest:
                for n,b in content.items():dest.writestr(n,b)
            pin=deepcopy(r.PINS[q]);pin['sha256']=r.sha(buf.getvalue())
            with self.assertRaises(r.Rejected):r._archive(buf.getvalue(),pin)
    def test_corrupt_after_hash_check(self):
        pin=deepcopy(r.PINS['Q02']);pin['sha256']=r.sha(b'invalid')
        with self.assertRaises(zipfile.BadZipFile):r._archive(b'invalid',pin)
    def test_denominator_grain_fraction_conservation(self):
        x=self.load('Q02');name='q02_experience';info=r.PINS['Q02']['tables'][name]
        for key,value in [('denominator_known',5206),('share_all_it',.9),('job_count',5206)]:
            rows=deepcopy(list(x.tables[name]));rows[0][key]=value
            with self.assertRaises(r.Rejected):r._validate_rows(name,rows,info)
        rows=deepcopy(list(x.tables[name]));rows[0]=rows[1]
        with self.assertRaises(r.Rejected):r._validate_rows(name,rows,info)

    def test_run_and_lineage_mismatch(self):
        payload=self.payload('Q02')
        for field in ['run_id','input_contract']:
            changed=deepcopy(payload);manifest=json.loads(changed['run/manifest.json'])
            if field=='run_id':manifest[field]='wrong_run'
            else:manifest[field]['d06_confirmation']['input_sha256']='0'*64
            changed['run/manifest.json']=json.dumps(manifest).encode()
            with patch.object(r,'_archive',return_value=changed),self.assertRaises(r.Rejected):r._receive(b'ignored','Q02')
    def test_csv_parity_mismatch(self):
        payload=self.payload('Q02');name='data/q02_experience.csv'
        payload[name]=payload[name].replace(b'Executive,9,',b'Executive,8,')
        with self.assertRaisesRegex(r.Rejected,'CSV_PARQUET_MISMATCH'):
            r._table(payload,'q02_experience',r.PINS['Q02']['tables']['q02_experience'])
    def test_q02_null(self):
        rows=self.load('Q02').tables['q02_experience'];missing=next(x for x in rows if x['category'] is None)
        self.assertEqual(missing['job_count'],1484);self.assertIsNone(missing['share_known'])
    def test_q04_remote_null(self):
        self.assertEqual({x['remote_allowed']:x['job_count'] for x in self.load('Q04').tables['q04_remote_flag']},{None:3721,True:1485})
    def test_q06_zero_hit_and_null_scope(self):
        x=self.load('Q06');self.assertEqual(len(x.tables['q06_skills_global']),46)
        self.assertTrue(all(v['processed_n']==5206 for v in x.tables['q06_skills_global']))
        self.assertTrue(any(v['formatted_experience_level'] is None for v in x.tables['q06_skills_by_experience']))
    def test_q08_bases_separate(self):
        x=self.load('Q08');self.assertEqual([sum(v['job_count'] for v in rows) for rows in x.tables.values()],[5206]*4)
        self.assertEqual(len(x.tables['q08_original_month']),3);self.assertEqual(len(x.tables['q08_listed_month']),1)
    def test_ui_parity_and_valid_then_invalid(self):
        for q,v in VIEWS.items():
            with self.subTest(q=q):
                a=AppTest.from_file(str(DASHBOARD/'views'/v)).run(timeout=20)
                a.text_input[0].set_value(str(PATHS[q]));a.checkbox[0].check();a.button[0].click().run(timeout=20)
                self.assertFalse(a.exception);self.assertTrue(a.metric);self.assertTrue(a.dataframe)
                self.assertEqual(a.metric[0].value,'5,206')
                for chart in a.get('arrow_vega_lite_chart'):
                    with pa.ipc.open_stream(pa.BufferReader(chart.proto.data.data)) as reader: frame=reader.read_all().to_pandas()
                    self.assertTrue(any(set(frame.job_count).issubset(set(t.value.job_count)) for t in a.dataframe))
                a.text_input[0].set_value(str(PATHS[q])+'.missing');a.button[0].click().run(timeout=20)
                self.assertFalse(a.metric);self.assertFalse(a.dataframe);self.assertFalse(a.get('arrow_vega_lite_chart'))
                a.text_input[0].set_value(str(PATHS[q]));a.checkbox[0].uncheck();a.button[0].click().run(timeout=20)
                self.assertFalse(a.metric);self.assertIn('CONFIRMATION_REQUIRED',a.error[0].value)

if __name__=='__main__':unittest.main(verbosity=2)
