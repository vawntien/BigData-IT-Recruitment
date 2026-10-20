"""Explicit runtime checks; enabled only by the development test runner."""
import os
import unittest
from pathlib import Path


@unittest.skipUnless(os.environ.get('TV2_D05_RUNTIME_TESTS')=='1','Opt-in local D05 contract test; not IT statistics')
class D05ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from d05_utils import get_spark_session
        from tv2_csv import ROOT
        cls.root=ROOT
        cls.spark=get_spark_session('TV2-Q05-CANDIDATE-CONTRACT-TEST',ROOT)
        cls.spark.conf.set('spark.sql.shuffle.partitions','2')

    def test_real_d05_declared_schema_and_development_source_projection(self):
        import json
        from pyspark.sql import functions as F
        from d05_job_functions_adapter import project_job_functions
        canonical=self.spark.read.parquet(str(self.root/'data/processed/canonical/jobs'))
        expected=json.loads((self.root/'tmp/tv2_d05_receipt_457f90ae/tv1_snapshot/data/audit/d05_canonical_schema.json').read_text())
        self.assertEqual(canonical.schema.jsonValue(),expected)
        selected=json.loads((self.root/'data/analytics/a05_development_v0_1_2_20261014/input_manifest.json').read_text(encoding='utf-8'))
        wanted=[int(r['job_id']) for r in selected['jobs']]
        scoped=canonical.filter(F.col('job_id').isin(wanted)).select('job_id','source_description_sha256','job_functions').cache()
        self.assertEqual(scoped.count(),105)
        expected_hashes={int(r['job_id']):r['source_text_sha256'] for r in [json.loads(x) for x in (self.root/'data/analytics/a05_development_v0_1_2_20261014/skill_source_processing.jsonl').read_text(encoding='utf-8').splitlines()]}
        self.assertEqual({r['job_id']:r['source_description_sha256'] for r in scoped.collect()},expected_hashes)
        bridge,mapping=project_job_functions(scoped,scoped.select('job_id'))
        self.assertEqual(bridge.count(),bridge.distinct().count())
        self.assertEqual(mapping.count(),mapping.select('skill_abr').distinct().count())
        self.assertEqual(bridge.join(scoped.select('job_id'),'job_id','left_anti').count(),0)
        scoped.unpersist()

    def test_missing_label_null_links_duplicates_and_conflicts(self):
        from d05_job_functions_adapter import project_job_functions
        schema='job_id long, job_functions array<struct<skill_abr:string,skill_name:string,mapping_status:string>>'
        d=self.spark.createDataFrame([(1,[('IT','Information Technology','MAPPED'),('IT','Information Technology','MAPPED')]),
                                     (2,None),(3,[('X',None,'MISSING_LABEL')])],schema).cache()
        bridge,mapping=project_job_functions(d,d.select('job_id'))
        self.assertEqual(bridge.count(),2)
        self.assertIsNone(mapping.filter("skill_abr = 'X'").first()['skill_name'])
        with self.assertRaises(ValueError):project_job_functions(d,d.select('job_id').unionByName(d.select('job_id').limit(1)))
        conflict=self.spark.createDataFrame([(1,[('IT','A','MAPPED'),('IT','B','MAPPED')])],schema)
        with self.assertRaisesRegex(ValueError,'Conflicting'):project_job_functions(conflict,conflict.select('job_id'))
        d.unpersist()
