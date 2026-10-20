import json
import os
import unittest
from pathlib import Path
from d06_handoff_validation import receipt_errors,REQUIRED_TYPES


class ReceiptTests(unittest.TestCase):
    def test_template_is_pending_never_approved(self):
        r=json.loads(Path('config/d06_handoff_contract.example.json').read_text())
        self.assertIn('MISSING_approved_by',receipt_errors(r))
        self.assertIn('TEXT_BINDING_UNCONFIRMED',receipt_errors(r))
        self.assertIn('Q05_CONTRACT_UNCONFIRMED',receipt_errors(r))
    def test_hash_and_timezone_fail_closed(self):
        errors=receipt_errors(dict(input_sha256='not-a-sha',timezone='Asia/Bangkok'))
        self.assertIn('INVALID_HASH_input_sha256',errors)
        self.assertIn('UTC_REQUIRED',errors)
    def test_required_schema_separates_source_and_membership(self):
        for c in ['source_description_sha256','source_title_sha256','taxonomy_version','taxonomy_sha256','is_it']:
            self.assertIn(c,REQUIRED_TYPES)
    def test_non_string_hash_is_reported_without_crashing(self):
        self.assertIn('INVALID_HASH_input_sha256',receipt_errors({'input_sha256':123}))


@unittest.skipUnless(os.environ.get('TV2_READINESS_SPARK')=='1','Opt-in local Spark contract validation')
class SparkReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from d05_utils import get_spark_session
        from tv2_csv import ROOT
        cls.spark=get_spark_session('TV2-READINESS-CONTRACT-TESTS',ROOT)
        cls.spark.conf.set('spark.sql.shuffle.partitions','2')
        import a06_a08_spark_analysis as a
        a.load_spark()
        cls.analysis=a
        cls.config=json.loads((ROOT/'config/tv2_analysis_inputs.example.json').read_text())

    def source_fixture(self):
        import hashlib
        import json
        from datetime import datetime
        r={k:None for k in REQUIRED_TYPES}
        r.update(job_id=1,description='clean text',source_description='Raw Python task.',source_title='Developer',
                 source_description_sha256=hashlib.sha256(b'Raw Python task.').hexdigest(),source_title_sha256=hashlib.sha256(b'Developer').hexdigest(),
                 it_decision='ACCEPT',is_it=True,taxonomy_version='test',taxonomy_sha256='a'*64,
                 primary_group_code='SOFTWARE',original_listed_time=datetime(2024,1,1),listed_time=datetime(2024,1,1))
        schema=', '.join(k+' '+v for k,v in REQUIRED_TYPES.items())
        d=self.spark.createDataFrame([r],schema).cache()
        receipt=dict(a05_description_column='source_description',taxonomy_version='test',taxonomy_sha256='a'*64)
        return d,receipt

    def test_source_projection_is_explicit_readonly_and_rejects_wrong_binding(self):
        from d06_handoff_validation import validate_frames
        d,r=self.source_fixture()
        self.assertEqual(validate_frames(d,d,r).first()['description'],'Raw Python task.')
        self.assertEqual(d.first()['description'],'clean text')
        r['a05_description_column']='description'
        with self.assertRaisesRegex(ValueError,'Source text/hash'):validate_frames(d,d,r)
        d.unpersist()

    def test_source_hash_and_orphan_membership_are_rejected(self):
        from d06_handoff_validation import validate_frames
        from pyspark.sql import functions as F
        d,r=self.source_fixture()
        with self.assertRaises(ValueError):validate_frames(d.withColumn('source_description_sha256',F.lit('b'*64)),d,r)
        with self.assertRaisesRegex(ValueError,'orphan'):validate_frames(d.withColumn('job_id',F.lit(2).cast('long')),d,r)
        d.unpersist()

    def test_blank_taxonomy_and_implicit_join_cast_are_rejected(self):
        from pyspark.sql import functions as F
        d,r=self.source_fixture()
        with self.assertRaises(ValueError):self.analysis.validate_d06(d.withColumn('taxonomy_sha256',F.lit('')),self.config['group_column'])
        # Direct query schema guards are tested with valid source fixture, not D05 as IT.
        js=self.spark.createDataFrame([('1','IT')],'job_id string, skill_abr string')
        sk=self.spark.createDataFrame([('IT','Information Technology')],'skill_abr string, skill_name string')
        with self.assertRaisesRegex(ValueError,'JOIN schema'):self.analysis.analyze_frames(d,self.config,js=js,sk=sk)
        from test_q07_salary import fixture
        _,salary=fixture(self.spark)
        salary=salary.withColumn('job_id',F.col('job_id').cast('string'))
        config=dict(self.config,q07_scope_id='SYNTHETIC_READINESS_NOT_IT')
        with self.assertRaisesRegex(ValueError,'D07.*job_id'):self.analysis.analyze_frames(d,config,salary=salary)
        d.unpersist()
