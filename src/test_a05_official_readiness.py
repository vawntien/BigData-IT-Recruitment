"""Official validation controls on synthetic fixtures, not IT statistics."""
import copy
import json
import os
import unittest
from pathlib import Path
from d06_handoff_validation import receipt_errors


class ReceiptPurposeTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(Path('config/d06_handoff_contract.example.json').read_text())

    def test_a05_not_blocked_by_q05(self):
        self.assertIn('Q05_CONTRACT_UNCONFIRMED',receipt_errors(self.r))
        self.assertNotIn('Q05_CONTRACT_UNCONFIRMED',receipt_errors(self.r,purpose='a05'))

    def test_a05_still_requires_real_input_and_approval(self):
        errors=receipt_errors(self.r,purpose='a05')
        for key in ['MISSING_it_jobs','MISSING_approved_by','TEXT_BINDING_UNCONFIRMED','MISSING_taxonomy_sha256']:
            self.assertIn(key,errors)


@unittest.skipUnless(os.environ.get('A05_READINESS_SPARK_TESTS')=='1','Opt-in local Spark validation fixtures')
class OutputValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from d05_utils import get_spark_session
        from a05_spark import output_schemas,spark_record
        from tech_skill_extractor import TechSkillExtractor
        from tv2_csv import ROOT
        cls.spark=get_spark_session('A05-OFFICIAL-VALIDATION-FIXTURES',ROOT)
        cls.spark.conf.set('spark.sql.shuffle.partitions','2')
        cls.jobs=cls.spark.createDataFrame([(1,'Required Skills: Python experience.'),(2,'No technology mentioned.'),(3,None)],'job_id long, description string')
        m=TechSkillExtractor(ROOT/'config/tech_skills.json')
        data=[m.extract(r['description'],r['job_id'],run_id='synthetic-validator-only') for r in cls.jobs.collect()]
        schema=output_schemas()
        cls.tables={name:cls.spark.createDataFrame([spark_record(x) for d in data for x in d[key]],schema[name])
                    for name,key in [('job_skill_technical','job_skills'),('technical_skill_evidence','evidence')]}
        cls.tables['skill_source_processing']=cls.spark.createDataFrame([spark_record(d['processing']) for d in data],schema['skill_source_processing'])

    @classmethod
    def tearDownClass(cls):cls.spark.stop()

    def test_zero_hit_missing_and_denominator(self):
        from run_a05_official import validate_outputs
        v=validate_outputs(self.tables,self.jobs)
        self.assertEqual(v['q06_denominator'],2)
        self.assertEqual(v['jobs_with_skills'],1)
        self.assertEqual(v['processing_status_counts'],{'PROCESSED_WITH_MATCH':1,'PROCESSED_NO_MATCH':1,'SOURCE_MISSING':1})

    def test_duplicate_pair_rejected(self):
        from run_a05_official import validate_outputs
        tables=dict(self.tables);b=tables['job_skill_technical'];tables['job_skill_technical']=b.unionByName(b)
        with self.assertRaisesRegex(ValueError,'Duplicate job-skill'):validate_outputs(tables,self.jobs)

    def test_changed_source_hash_rejected(self):
        from run_a05_official import validate_outputs
        from pyspark.sql import functions as F
        tables=dict(self.tables);tables['technical_skill_evidence']=tables['technical_skill_evidence'].withColumn('source_text_sha256',F.lit('bad'))
        with self.assertRaisesRegex(ValueError,'source hash mismatch'):validate_outputs(tables,self.jobs)

    def test_evidence_fk_rejected(self):
        from run_a05_official import validate_outputs
        from pyspark.sql import functions as F
        tables=dict(self.tables);tables['job_skill_technical']=tables['job_skill_technical'].withColumn('evidence_ids',F.array(F.lit('absent')))
        with self.assertRaisesRegex(ValueError,'evidence FK mismatch'):validate_outputs(tables,self.jobs)


if __name__=='__main__':unittest.main()
