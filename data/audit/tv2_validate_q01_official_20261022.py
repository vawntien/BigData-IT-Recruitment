"""Independent read-only validation of official marginal outputs; never executes analyzer."""
import csv, hashlib, json, math, pathlib, subprocess, sys, traceback
from collections import Counter
from datetime import datetime, timezone, timedelta

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.stdout.reconfigure(encoding='utf-8')
from a06_a08_spark_analysis import artifact_digest
from d06_handoff_validation import verify_artifacts
OUT=ROOT/'data/analytics/tv2_q01_q04_q08_official_20261022_01'
INPUT=ROOT/'data/processed/tv2/enriched/tv2_enriched_d06_accept_20261022_01'
VALID=OUT/'independent_validation'
AUDIT=ROOT/'data/audit/tv2_q01_official_validation_20261022.json'
result={'status':'STARTED','run_id':OUT.name,'checks':{},'queries':{},'started_utc':datetime.now(timezone.utc).isoformat(),
        'business_accepted':False,'validator_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
spark=None
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def write(p,x):pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=True,indent=2,default=str),encoding='utf-8')
def check(name,ok,detail=None):
    result['checks'][name]={'pass':bool(ok),'detail':detail};write(AUDIT,result)
    print(name,'PASS' if ok else 'FAIL',flush=True)
    if not ok:raise AssertionError(name)
def cat(value):
    if value is None:return None
    value=value.strip(' ')
    return value if value else None
def close(a,b):
    if a is None or b is None:return a is None and b is None
    if isinstance(a,float) or isinstance(b,float):return math.isfinite(float(a)) and math.isfinite(float(b)) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
    return a==b
try:
    if VALID.exists() or AUDIT.exists():raise ValueError('Use new validation paths; preserve prior evidence')
    VALID.mkdir()
    m=read(OUT/'manifest.json');contract=read(INPUT/'analysis_contract.json');receipt=read(INPUT/'input_receipt.json')
    input_manifest=read(INPUT/'manifest.json');input_seal=read(INPUT/'completion.json')
    input_digest=artifact_digest(INPUT/'jobs.parquet')
    check('confirmed_input_digest',input_digest==contract['d06_confirmation']['input_sha256']==receipt['input_sha256']==input_manifest['input_artifact_sha256']=='17ae5383e848f7323b99800bd3d79a72e84e2bca62844f66dd00aaa06e80a9b2')
    check('input_metadata_seal',sha(INPUT/'manifest.json')==input_seal['manifest_sha256'] and all(sha(INPUT/p)==h for p,h in input_manifest['artifact_sha256'].items()))
    verify_artifacts(receipt,purpose='a05')
    check('source_artifact_receipt_verification',True)
    check('correct_technical_receipt_identity',receipt['approved_by']=='\u0110\u1ed3ng Vi\u1ebft D\u0169ng (TV2)' and contract['d06_confirmation']['approved_by']==receipt['approved_by'])
    check('official_run_manifest',m['run_kind']=='OFFICIAL' and m['run_id']==OUT.name and m['status']=='PARTIAL_SUCCESS' and m['environment']['spark_executed'])
    check('manifest_input_code_taxonomy_provenance',m['provenance']['contract_sha256']==sha(INPUT/'analysis_contract.json') and m['provenance']['analysis_sha256']==sha(ROOT/'src/a06_a08_spark_analysis.py') and m['provenance']['dictionary_sha256']==sha(ROOT/'config/tech_skills.json') and m['provenance']['taxonomy']==[{'taxonomy_version':'0.2.2','taxonomy_sha256':receipt['taxonomy_sha256']}])
    result['runner_manifest_sha256']=sha(OUT/'manifest.json');result['input_digest']=input_digest
    result['manifest_date_note']={'literal_date':m['date'],'created_utc':m['created_utc'],'note':'Runner date field is hardcoded historical metadata; actual execution is created_utc and runner exit evidence, not literal date.'}
    from pyspark.sql import SparkSession,functions as F,types as T
    jar=str(ROOT/'tmp/d04-localfs/d04-localfs-adapter.jar')
    spark=(SparkSession.builder.master('local[2]').appName('TV2-Q01-Independent-Validation').config('spark.ui.enabled','false')
           .config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','4')
           .config('spark.driver.extraClassPath',jar).config('spark.executor.extraClassPath',jar)
           .config('spark.hadoop.fs.file.impl','d04.localfs.NoPermissionLocalFileSystem').config('spark.hadoop.fs.file.impl.disable.cache','true').getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    d=spark.read.parquet(str(INPUT/'jobs.parquet'))
    check('input_39_fields_physical_schema',len(d.columns)==39 and d.schema.jsonValue()==read(INPUT/'schema.json'))
    dims=['primary_group_code','formatted_experience_level','location','formatted_work_type','work_type','remote_allowed','it_decision','is_it','taxonomy_version','taxonomy_sha256']
    rows=[r.asDict() for r in d.select('job_id',*dims,F.col('original_listed_time').cast('long').alias('original_epoch'),F.col('listed_time').cast('long').alias('listed_epoch')).collect()]
    ids=[r['job_id'] for r in rows];N=len(ids);K=sum(cat(r['primary_group_code']) is not None for r in rows)
    check('input_population_unique_nonnull',N==5206 and len(set(ids))==N and None not in ids)
    check('input_accept_and_taxonomy',all(r['it_decision']=='ACCEPT' and r['is_it'] is True and r['taxonomy_version']=='0.2.2' and r['taxonomy_sha256']==receipt['taxonomy_sha256'] for r in rows))
    original=spark.read.parquet(str(ROOT/'data/handoff/tv1/receiving_20261022/d06/D06/predictions'))
    accepted=[r.asDict() for r in original.filter("it_decision='ACCEPT' AND is_it=true").select('job_id','primary_group_code','subgroup_code','taxonomy_version','taxonomy_sha256').collect()]
    accepted_by_id={r['job_id']:r for r in accepted}
    check('exact_d06_accept_population',len(accepted)==len(accepted_by_id)==5206 and set(ids)==set(accepted_by_id),{'missing':len(set(accepted_by_id)-set(ids)),'extra':len(set(ids)-set(accepted_by_id))})
    selected=d.select('job_id','primary_group_code','subgroup_code','taxonomy_version','taxonomy_sha256').collect()
    check('primary_category_and_provenance_unchanged',all(r.asDict()==accepted_by_id[r['job_id']] for r in selected))
    taxonomy=read(ROOT/'config/versions/it_taxonomy_v0.2.2.json')
    result['taxonomy_groups']=taxonomy['groups']
    expected_tables={'q01_role_groups','q02_experience','q03_location','q04_work_type','q04_remote_flag','q04_work_type_crosscheck','q08_original_month','q08_original_week_start_utc','q08_listed_month','q08_listed_week_start_utc'}
    check('exact_expected_outputs',set(m['tables'])==expected_tables)
    loaded={}
    def table(name,columns,keycols):
        entry=m['tables'][name];pq=pathlib.Path(entry['parquet']);csvp=OUT/entry['csv']
        check(name+'_hashes',pq.resolve()==(OUT/(name+'.parquet')).resolve() and csvp.resolve()==(OUT/(name+'.csv')).resolve() and artifact_digest(pq)==entry['parquet_sha256'] and sha(csvp)==entry['csv_sha256'])
        frame=spark.read.parquet(str(pq));schema=frame.schema
        write(VALID/(name+'_schema.json'),schema.jsonValue())
        check(name+'_physical_columns',frame.columns==columns)
        records=[r.asDict() for r in frame.collect()]
        check(name+'_rowcount_and_unique_grain',len(records)==entry['rows'] and len({tuple(r[k] for k in keycols) for r in records})==len(records),len(records))
        def convert(s,typ):
            if s=='':return None
            if isinstance(typ,(T.LongType,T.IntegerType)):return int(s)
            if isinstance(typ,T.DoubleType):return float(s)
            if isinstance(typ,T.BooleanType):
                if s not in ['True','False','true','false']:raise ValueError('Invalid CSV boolean')
                return s.lower()=='true'
            return s
        with csvp.open(encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream);check(name+'_csv_header',reader.fieldnames==columns)
            csvrows=[{f.name:convert(r[f.name],f.dataType) for f in schema} for r in reader]
        keyed={tuple(r[k] for k in keycols):r for r in records};csvkeyed={tuple(r[k] for k in keycols):r for r in csvrows}
        check(name+'_csv_parquet_readback',len(csvrows)==len(records) and len(csvkeyed)==len(csvrows) and set(csvkeyed)==set(keyed) and all(all(close(r[k],csvkeyed[key][k]) for k in columns) for key,r in keyed.items()))
        loaded[name]=(records,schema)
        return records,schema
    six=['category','job_count','denominator_all_it','denominator_known','share_all_it','share_known']
    for query,col,name in [('Q01','primary_group_code','q01_role_groups'),('Q02','formatted_experience_level','q02_experience'),('Q03','location','q03_location'),('Q04','formatted_work_type','q04_work_type')]:
        data,schema=table(name,six,['category']);counter=Counter(cat(r[col]) for r in rows);known=N-counter[None]
        check(name+'_physical_types',isinstance(schema['category'].dataType,T.StringType) and isinstance(schema['job_count'].dataType,T.LongType) and all(isinstance(schema[x].dataType,(T.IntegerType,T.LongType)) for x in six[2:4]) and all(isinstance(schema[x].dataType,T.DoubleType) for x in six[4:]))
        check(name+'_independent_counts_denominators_shares',set(r['category'] for r in data)==set(counter) and all(r['job_count']==counter[r['category']] and r['denominator_all_it']==N and r['denominator_known']==known and close(r['share_all_it'],r['job_count']/N) and close(r['share_known'],r['job_count']/known if known>0 and r['category'] is not None else None) for r in data))
        check(name+'_conservation',sum(r['job_count'] for r in data)==N and sum(r['job_count'] for r in data if r['category'] is not None)==known and close(sum(r['share_all_it'] for r in data),1.0) and (known==0 or close(sum(r['share_known'] for r in data if r['category'] is not None),1.0)))
        meta=m['queries'][query]
        check(query+'_manifest_metadata',meta['status']=='SUCCESS' and meta['known_jobs']==known and meta['missing_jobs']==N-known and close(meta['coverage'],known/N) and meta['denominator']==(known if query=='Q03' else N))
        result['queries'][query]={'status':'VALIDATED','N':N,'K':known,'missing':N-known,'tables':meta['tables'],'accepted':False}
    q1,_=loaded['q01_role_groups'];counter=Counter(cat(r['primary_group_code']) for r in rows)
    literal_unknown=Counter(cat(r['primary_group_code']) for r in rows if cat(r['primary_group_code']) is not None and cat(r['primary_group_code']).casefold()=='unknown')
    missing_raw={'null_jobs':sum(r['primary_group_code'] is None for r in rows),'blank_jobs':sum(r['primary_group_code'] is not None and cat(r['primary_group_code']) is None for r in rows),'literal_unknown_jobs':sum(literal_unknown.values()),'literal_unknown_values':dict(literal_unknown),'it_other_jobs':counter['IT_OTHER']}
    check('q01_it_other_known_policy',all(r['share_known'] is not None and r['denominator_known']==K for r in q1 if r['category']=='IT_OTHER') and counter['IT_OTHER']==sum(r['job_count'] for r in q1 if r['category']=='IT_OTHER'))
    groups=taxonomy['groups'];valid_codes={g['code'] for g in groups}
    check('q01_codes_in_approved_taxonomy',set(counter)-{None} <= valid_codes)
    result['q01']={'status':'VALIDATED','accepted':False,'N':N,'K':K,'missing':N-K,'sum_job_count':sum(r['job_count'] for r in q1),'sum_known_job_count':sum(r['job_count'] for r in q1 if r['category'] is not None),'sum_share_all_it':sum(r['share_all_it'] for r in q1),'sum_share_known':sum(r['share_known'] or 0 for r in q1),'distribution':sorted(q1,key=lambda r:-r['job_count']),'missing_unknown_policy_observed':missing_raw,'tolerance':{'rel':1e-12,'abs':1e-12},'physical_schema':loaded['q01_role_groups'][1].jsonValue(),'taxonomy_version':'0.2.2','taxonomy_sha256':receipt['taxonomy_sha256']}
    data,schema=table('q04_remote_flag',['remote_allowed','job_count','denominator_all_it','share_all_it'],['remote_allowed']);expected=Counter(r['remote_allowed'] for r in rows)
    check('q04_remote_independent_values',set(r['remote_allowed'] for r in data)==set(expected) and all(r['job_count']==expected[r['remote_allowed']] and r['denominator_all_it']==N and close(r['share_all_it'],r['job_count']/N) for r in data) and sum(r['job_count'] for r in data)==N)
    data,schema=table('q04_work_type_crosscheck',['formatted_work_type','work_type','job_count'],['formatted_work_type','work_type']);expected=Counter((r['formatted_work_type'],r['work_type']) for r in rows)
    check('q04_crosscheck_independent_values',set((r['formatted_work_type'],r['work_type']) for r in data)==set(expected) and all(r['job_count']==expected[(r['formatted_work_type'],r['work_type'])] for r in data) and sum(r['job_count'] for r in data)==N)
    result['queries']['Q08']={'status':'VALIDATED','N':N,'tables':m['queries']['Q08']['tables'],'timestamp_coverage':{},'accepted':False}
    for epoch,prefix,source in [('original_epoch','q08_original','original_listed_time'),('listed_epoch','q08_listed','listed_time')]:
        times=[datetime.fromtimestamp(r[epoch],timezone.utc) for r in rows if r[epoch] is not None];valid=len(times)
        result['queries']['Q08']['timestamp_coverage'][source]={'valid':valid,'missing':N-valid}
        for suffix in ['month','week_start_utc']:
            name=prefix+'_'+suffix;data,schema=table(name,['period','job_count','valid_timestamp_n','share_of_valid'],['period'])
            expected=Counter(t.strftime('%Y-%m') if suffix=='month' else (t-timedelta(days=t.weekday())).strftime('%Y-%m-%d') for t in times)
            check(name+'_independent_utc_counts_and_shares',set(r['period'] for r in data)==set(expected) and all(r['job_count']==expected[r['period']] and r['valid_timestamp_n']==valid and close(r['share_of_valid'],r['job_count']/valid if valid else None) for r in data) and sum(r['job_count'] for r in data)==valid and (not valid or close(sum(r['share_of_valid'] for r in data),1.0)))
        meta=m['queries']['Q08']['coverage'][source]
        check(source+'_manifest_coverage',meta['valid_jobs']==valid and meta['all_it']==N and close(meta['share'],valid/N))
    check('q08_manifest_success',m['queries']['Q08']['status']=='SUCCESS' and m['queries']['Q08']['denominator']==N)
    for q,dep in [('Q05','D05'),('Q06','A05'),('Q07','D07')]:
        meta=m['queries'][q];check(q+'_blocked_no_fake_outputs',meta['status']=='BLOCKED_DEPENDENCY' and meta['missing']==[dep] and meta['tables']==[] and meta['denominator'] is None)
        result['queries'][q]={'status':'BLOCKED','missing':dep,'business_approval':'PENDING' if q=='Q07' else None,'tables':[]}
    check('runner_exit_expected_partial',read(ROOT/'data/audit/tv2_q01_runner_exit_20261022.json')['python_exit_code']==2)
    check('input_and_runner_manifest_unchanged_after_validation',artifact_digest(INPUT/'jobs.parquet')==input_digest and sha(OUT/'manifest.json')==result['runner_manifest_sha256'])
    result['runtime']={'spark':spark.version,'java':spark.sparkContext._jvm.java.lang.System.getProperty('java.version'),'timezone':'UTC'}
    result['status']='PASS';result['q01_status']='VALIDATED';result['finished_utc']=datetime.now(timezone.utc).isoformat()
except Exception as e:
    result.update(status='FAIL',error=repr(e),q01_status='FAIL');traceback.print_exc()
finally:
    if spark:spark.stop()
    write(AUDIT,result);write(VALID/'validation.json',result)
    write(VALID/'completion.json',{'status':result['status'],'run_id':OUT.name,'validation_sha256':sha(VALID/'validation.json'),'runner_manifest_sha256':sha(OUT/'manifest.json'),'business_accepted':False})
print(json.dumps({'status':result['status'],'q01_status':result['q01_status'],'checks':len(result['checks'])}),flush=True)
sys.exit(0 if result['status']=='PASS' else 1)
