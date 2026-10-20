"""Synthetic Q07 regression; real tests opt in and never infer an IT population."""
import os, unittest, json
from decimal import Decimal as D
from pathlib import Path
from pyspark.sql import functions as F
from q07_salary import salary_tables

SCHEMA='job_id long, selected_salary struct<min_salary:decimal(20,4),med_salary:decimal(20,4),max_salary:decimal(20,4)>, canonical_currency string, canonical_pay_period string, canonical_compensation_type string, salary_source string, normalization_status string'

def fixture(spark):
    specs=[(1,10,None,100),(2,20,None,None),(3,30,None,200),(4,None,50,None),
           (5,None,None,None),(6,0,None,2),(7,None,None,300),(8,1,None,2),
           (9,5,None,10),(10,1,None,2),(11,1,None,3)]
    rows=[]
    for i,lo,med,hi in specs:
        rows.append((i,tuple(None if v is None else D(v) for v in (lo,med,hi)),
                     'EUR' if i==8 else 'USD','HOURLY' if i==9 else 'YEARLY','BASE_SALARY',
                     'SALARIES' if i==10 else 'BOTH_AGREE','MISSING' if i==5 else 'INVALID' if i==6 else 'USABLE'))
    salary=spark.createDataFrame(rows,SCHEMA)
    pop=spark.createDataFrame([(r[0],None if r[0]==11 else 'G','E') for r in rows],
                              'job_id long, a02_group string, formatted_experience_level string')
    return pop,salary


class SalaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from d05_utils import get_spark_session
        cls.spark=get_spark_session('TV2-Q07-CONTRACT-V2-TESTS',Path.cwd())
        cls.spark.conf.set('spark.sql.shuffle.partitions','2')
        cls.pop,cls.salary=fixture(cls.spark)
        cls.tables=salary_tables(cls.pop,cls.salary,scope_id='SYNTHETIC_NOT_IT')
        cls.rows=cls.tables['q07_salary_separate_units'].collect()

    def test_independent_samples_quantiles_and_coverage(self):
        r=next(r for r in self.rows if r.a02_group=='G' and r.currency=='USD' and r.pay_period=='YEARLY' and r.salary_source=='BOTH_AGREE')
        self.assertEqual((r.n_min,r.n_max,r.eligible_bundle_n,r.population_n),(3,3,5,10))
        self.assertEqual((r.min_salary_q1,r.min_salary_median,r.min_salary_q3,r.min_salary_iqr),(15.,20.,25.,10.))
        self.assertEqual((r.max_salary_q1,r.max_salary_median,r.max_salary_q3,r.max_salary_iqr),(150.,200.,250.,100.))
        self.assertEqual((r.coverage_min,r.coverage_max,r.eligible_coverage),(.3,.3,.5))
        self.assertIsNone(r.adequate_min)
        self.assertEqual(len(self.rows),5)
        self.assertTrue(any(r.a02_group is None and r.population_n==1 for r in self.rows))
        self.assertEqual(sum(r.job_count for r in self.tables['q07_quality_status'].collect()),11)

    def test_min_only_max_only_med_only_and_missing_context(self):
        pop=self.pop.withColumn('a02_group',F.col('job_id').cast('string'))
        tables=salary_tables(pop,self.salary,scope_id='SYNTHETIC_NOT_IT',minimum_n=2)
        rows={int(r.a02_group):r for r in tables['q07_salary_separate_units'].collect()}
        self.assertEqual((rows[2].n_min,rows[2].n_max),(1,0))
        self.assertIsNone(rows[2].max_salary_median)
        self.assertEqual((rows[7].n_min,rows[7].n_max),(0,1))
        self.assertEqual((rows[4].n_min,rows[4].n_max,rows[4].eligible_bundle_n),(0,0,1))
        self.assertIsNone(rows[4].min_salary_iqr)
        self.assertFalse(rows[2].adequate_min)
        self.assertNotIn(5,rows);self.assertNotIn(6,rows)
        summaries={int(r.a02_group):r for r in tables['q07_population_summary'].collect()}
        self.assertEqual((summaries[5].population_n,summaries[5].eligible_bundle_n),(1,0))

    def test_fail_closed_duplicate_missing_record_and_invalid_usable(self):
        for salary in [self.salary.unionByName(self.salary.limit(1)),self.salary.filter('job_id != 1'),
                       self.salary.withColumn('normalization_status',F.when(F.col('job_id')==6,'USABLE').otherwise(F.col('normalization_status')))]:
            with self.assertRaises(ValueError):salary_tables(self.pop,salary,scope_id='SYNTHETIC_NOT_IT')

    @unittest.skipUnless(os.environ.get('TV2_Q07_REAL')=='1','Opt-in ALL JOBS staging validation')
    def test_real_d07_and_d05_schema_grain(self):
        base=Path('data/handoff/tv1/TV1_Handoff_D05_D07')
        salary=self.spark.read.parquet(str(base/'D07_Salary/salaries.parquet')).cache()
        jobs=self.spark.read.parquet(str(base/'D05_Canonical/jobs'))
        # Context is an audit constant, never a manufactured IT category.
        population=jobs.select('job_id').withColumn('a02_group',F.lit(None).cast('string')).withColumn('formatted_experience_level',F.lit(None).cast('string'))
        tables=salary_tables(population,salary,scope_id='ALL_JOBS_STAGING_NOT_IT')
        rows=tables['q07_salary_separate_units'].collect()
        contract=json.loads(Path('config/q07_salary_contract_v2.json').read_text(encoding='utf-8'))
        for name,table in tables.items():
            self.assertEqual(set(table.columns),set(contract['tables'][name]['fields']))
            for field in table.schema:
                self.assertEqual(field.dataType.simpleString(),contract['tables'][name]['fields'][field.name].rstrip('?'))
        self.assertEqual(sum(r.n_min for r in rows),29793);self.assertEqual(sum(r.n_max for r in rows),29793)
        self.assertEqual(sum(r.eligible_bundle_n for r in rows),36059)
        for r in rows:
            self.assertEqual(r.population_n,123849)
            for c in ['min_salary','max_salary']:
                q=[r[c+s] for s in ['_q1','_median','_q3']]
                if q[0] is not None:self.assertLessEqual(q[0],q[1]);self.assertLessEqual(q[1],q[2]);self.assertAlmostEqual(r[c+'_iqr'],q[2]-q[0])
        factors={'YEARLY':1,'MONTHLY':12,'WEEKLY':52,'BIWEEKLY':26,'HOURLY':2080}
        factor=F.create_map(*[x for k,v in factors.items() for x in (F.lit(k),F.lit(v))])[F.col('canonical_pay_period')]
        for c in ['min_salary','med_salary','max_salary']:
            bad=salary.filter((F.col('normalization_status')=='USABLE') & ~F.col('normalized_'+c).eqNullSafe((F.col('selected_salary.'+c)*factor).cast('decimal(38,4)'))).count()
            self.assertEqual(bad,0)
        from d05_job_functions_adapter import project_job_functions
        bridge,mapping=project_job_functions(jobs,jobs.select('job_id'))
        self.assertEqual(bridge.count(),bridge.dropDuplicates(['job_id','skill_abr']).count())
        self.assertEqual(bridge.select('job_id').join(jobs.select('job_id'),'job_id','left_anti').count(),0)
        for c in ['original_listed_time','listed_time']:
            self.assertEqual(jobs.schema[c].dataType.simpleString(),'timestamp')
            valid=jobs.filter(F.col(c).isNotNull())
            groups=valid.groupBy(F.date_trunc('month',F.col(c))).agg(F.countDistinct('job_id').alias('n'))
            self.assertEqual(groups.agg(F.sum('n')).first()[0],valid.count())
        salary.unpersist()


class IntegrationTests(unittest.TestCase):
    def test_analyzer_native_schema_and_approval_gate(self):
        from d05_utils import get_spark_session
        import a06_a08_spark_analysis as a
        from tempfile import TemporaryDirectory
        spark=get_spark_session('TV2-Q07-INTEGRATION-SYNTHETIC',Path.cwd())
        pop,salary=fixture(spark)
        for col,value in [('description','SYNTHETIC'),('it_decision','ACCEPT'),('is_it',True),
                          ('taxonomy_version','SYNTHETIC_NOT_D06'),('taxonomy_sha256','SYNTHETIC'),
                          ('location','X'),('formatted_work_type','Full-time')]:
            pop=pop.withColumn(col,F.lit(value))
        pop=pop.withColumn('remote_allowed',F.lit(None).cast('boolean'))
        for col in ['original_listed_time','listed_time']:pop=pop.withColumn(col,F.lit('2024-01-01').cast('timestamp'))
        config=json.loads(Path('config/tv2_analysis_inputs.example.json').read_text(encoding='utf-8'))
        config.update(group_column='a02_group',q07_scope_id='SYNTHETIC_NOT_IT')
        tables,metadata,n=a.analyze_frames(pop,config,salary=salary)
        contract=json.loads(Path('config/q07_salary_contract_v2.json').read_text(encoding='utf-8'))
        for name,definition in contract['tables'].items():
            self.assertEqual(set(tables[name].columns),set(definition['fields']))
            for field in tables[name].schema:
                self.assertEqual(field.dataType.simpleString(),definition['fields'][field.name].rstrip('?'))
        self.assertEqual(metadata['Q07']['contract_version'],2)
        self.assertIsNone(metadata['Q07']['denominator'])
        self.assertEqual(n,11)
        with TemporaryDirectory(dir='tmp') as folder:
            path=Path(folder)/'fixture';path.write_text('synthetic digest gate, not parquet')
            config['salary_clean']=str(path)
            approval=dict(approved_by='SYNTHETIC',approved_on='2026-10-20',input_sha256=a.artifact_digest(path),
                policy='posted_min_max_separate_currency_period_source')
            config['d07_approval']=approval
            self.assertFalse(a.preflight(config)[0]['D07'])
            approval.update(q07_contract_version=2,quantile_method='exact_continuous_linear_interpolation_double',
                eligibility='D07_USABLE_WHOLE_SELECTED_BUNDLE',source_grain='salary_source',
                outlier_policy='NO_ADDITIONAL_FILTER',minimum_salary_group_n=None)
            self.assertTrue(a.preflight(config)[0]['D07'])
            self.assertFalse(a.preflight(config)[0]['D06'])
            approval['minimum_salary_group_n']=5
            self.assertFalse(a.preflight(config)[0]['D07'])


if __name__=='__main__':unittest.main()
