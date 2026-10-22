"""Materialize verified D05 x D06 ACCEPT only; no extraction/analysis/approval creation."""
import ctypes
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.stdout.reconfigure(encoding='utf-8')
from a06_a08_spark_analysis import artifact_digest, preflight, load_spark, validate_d06
from d06_handoff_validation import REQUIRED_TYPES, validate_frames, receipt_errors

RUN = 'tv2_enriched_d06_accept_20261022_01'
OUT = ROOT / 'data/processed/tv2/enriched' / RUN
HANDOFF = ROOT / 'data/handoff/tv1/receiving_20261022'
CANONICAL = ROOT / 'data/processed/canonical/jobs'
AUDIT = ROOT / 'data/audit/tv2_enriched_validation_20261022.json'
EXPECTED_TAX = '1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874'
result = {'run_id': RUN, 'status': 'STARTED', 'scope': 'INPUT_MATERIALIZATION_ONLY',
          'started_utc': datetime.now(timezone.utc).isoformat(), 'checks': {},
          'production_analytics_executed': False, 'business_approval_claimed': False}
spark = None

def sha(p):
    h = hashlib.sha256()
    with pathlib.Path(p).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''): h.update(block)
    return h.hexdigest()

def read(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def write(p, obj): pathlib.Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def check(name, passed, detail=None):
    result['checks'][name] = {'pass': bool(passed), 'detail': detail}
    write(AUDIT, result)
    print(name, 'PASS' if passed else 'FAIL', flush=True)
    if not passed: raise ValueError(name)

def normalized(x):
    if isinstance(x, dict): return {k: normalized(v) for k,v in x.items() if k not in ('nullable','containsNull','valueContainsNull')}
    if isinstance(x, list): return [normalized(v) for v in x]
    return x

def resources():
    class Memory(ctypes.Structure):
        _fields_ = [('length',ctypes.c_ulong),('load',ctypes.c_ulong)] + [(n,ctypes.c_ulonglong) for n in ['total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended']]
    m=Memory();m.length=ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)): raise RuntimeError('Cannot measure RAM')
    return {'captured_utc':datetime.now(timezone.utc).isoformat(), 'total_ram_bytes':m.total_phys,
            'available_ram_bytes':m.avail_phys,'available_commit_bytes':m.avail_page,
            'disk_free_bytes':shutil.disk_usage(ROOT).free}

try:
    if OUT.exists() or AUDIT.exists(): raise ValueError('Choose a new run/output/audit; never overwrite')
    r=resources();result['resources_before']=r
    check('resources_before_write',r['available_ram_bytes']>2.5*1024**3 and r['available_commit_bytes']>3*1024**3 and r['disk_free_bytes']>3*1024**3,r)
    check('output_git_ignored',subprocess.run(['git','check-ignore',str(OUT/'jobs.parquet/_SUCCESS')],cwd=ROOT,capture_output=True).returncode==0)
    d6=HANDOFF/'d06'; ap=HANDOFF/'approval'
    m=read(d6/'D06/run_manifest.json'); seal=read(d6/'D06/completion.json'); contract=read(d6/'contract.json')
    protected={}
    def protect(path):
        path=path.resolve();protected[str(path)]=sha(path)
    for folder in ['d06','approval','d07']:
        b=HANDOFF/folder; inv=read(b/'SHA256_INVENTORY.json')
        expected={e['path'] for e in inv['files']}|{'SHA256_INVENTORY.json'}
        actual={p.relative_to(b).as_posix() for p in b.rglob('*') if p.is_file()}
        check(folder+'_source_payload',actual==expected and all((b/e['path']).stat().st_size==e['bytes'] and sha(b/e['path'])==e['sha256'] for e in inv['files']))
        for p in b.rglob('*'):
            if p.is_file(): protect(p)
    for e in m['input_inventory']['files']:
        p=CANONICAL/e['path']
        check('d05_part_'+e['path'],p.stat().st_size==e['bytes'] and sha(p)==e['sha256'])
    for p in CANONICAL.rglob('*'):
        if p.is_file():protect(p)
    check('d06_completion_binding',seal['status']=='SUCCEEDED' and seal['scope']=='FULL' and seal['run_id']==m['run_id']=='official_20261021_a9dddfe4' and all(sha(d6/'D06'/p)==seal[k] for p,k in [('run_manifest.json','manifest_sha256'),('validation.json','validation_sha256'),('output_inventory.json','inventory_sha256')]))
    binding=read(ap/'binding.json')
    for kind,entry in binding['records'].items():
        key={'A04_BUSINESS':'a04','D06_SCHEMA':'schema','D06_FULL_RUN':'run'}[kind]
        a=read(ap/entry['path'])
        check('approval_binding_'+kind,sha(ap/entry['path'])==m['approvals'][key]==entry['sha256'] and a['kind']==kind and a['status']=='APPROVED')
    taxonomy=ROOT/'config/versions/it_taxonomy_v0.2.2.json'
    check('taxonomy_snapshot',sha(taxonomy)==m['taxonomy_sha256']==EXPECTED_TAX and m['taxonomy_version']=='0.2.2')
    release=read(ROOT/'config/a05_release_v0.1.2.json')
    check('a05_release_pins',all(sha(ROOT/p)==h for p,h in release['pinned_files'].items()))
    classifier=ROOT/'tmp/tv2_a04_handoff_v0.2.2/staging/src/it_taxonomy.py'
    classifier_expected=read(ROOT/'data/analytics/a04_taxonomy_v0_2_2_20261014/run_manifest.json')['implementation_sha256']['src/it_taxonomy.py']
    check('classifier_frozen_local_reference',sha(classifier)==classifier_expected)
    for path in ['src/a06_a08_spark_analysis.py','src/d06_handoff_validation.py','src/run_a05_official.py','config/tv2_analysis_output_schema.json','config/a05_release_v0.1.2.json','config/d06_handoff_contract.example.json','config/tv2_analysis_inputs.example.json','config/versions/it_taxonomy_v0.2.2.json']+list(release['pinned_files']):protect(ROOT/path)
    protect(classifier)
    OUT.mkdir(parents=True,exist_ok=False)
    from pyspark.sql import SparkSession, functions as F, types as T
    jar=str(ROOT/'tmp/d04-localfs/d04-localfs-adapter.jar')
    spark=(SparkSession.builder.master('local[2]').appName(RUN).config('spark.ui.enabled','false')
           .config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','4')
           .config('spark.speculation','false').config('spark.driver.extraClassPath',jar)
           .config('spark.executor.extraClassPath',jar).config('spark.hadoop.fs.file.impl','d04.localfs.NoPermissionLocalFileSystem')
           .config('spark.hadoop.fs.file.impl.disable.cache','true').getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    result['runtime']={'spark':spark.version,'java':spark.sparkContext._jvm.java.lang.System.getProperty('java.version'),
                       'python':sys.version,'master':spark.sparkContext.master,'timezone':spark.conf.get('spark.sql.session.timeZone'),
                       'driver_max_heap_bytes':spark.sparkContext._jvm.java.lang.Runtime.getRuntime().maxMemory()}
    d=spark.read.parquet(str(d6/'D06/predictions')); c=spark.read.parquet(str(CANONICAL))
    check('d06_schema',len(d.columns)==27 and normalized(d.schema.jsonValue())==normalized(read(d6/'schema/official_schema.json')))
    def keys(frame):
        return frame.agg(F.count('*').alias('rows'),F.countDistinct('job_id').alias('distinct_job_id'),F.sum(F.col('job_id').isNull().cast('int')).alias('null_job_id')).first().asDict()
    for label,frame,n in [('d05',c,123849),('d06',d,123849)]:
        stats=keys(frame);check(label+'_unique_keys',stats=={'rows':n,'distinct_job_id':n,'null_job_id':0},stats)
    mapping=[r.asDict() for r in d.groupBy('it_decision','is_it').count().collect()]
    check('full_decision_mapping',len(mapping)==3 and all(r['is_it']=={'ACCEPT':True,'REJECT':False,'REVIEW':None}.get(r['it_decision']) and r['count']=={'ACCEPT':5206,'REJECT':58953,'REVIEW':59690}.get(r['it_decision']) for r in mapping),mapping)
    accepted=d.filter((F.col('it_decision')=='ACCEPT') & (F.col('is_it')==True))
    def keydiff(left,right): return left.select('job_id').exceptAll(right.select('job_id')).count()
    check('full_d05_keyset',keydiff(d,c)==0 and keydiff(c,d)==0)
    additions=['source_description','source_title','formatted_experience_level','location','formatted_work_type','work_type','remote_allowed','original_listed_time','listed_time','job_functions']
    check('explicit_projection_fields',all(x in c.columns and x not in d.columns for x in additions) and all(x in c.columns for x in ['description','title','source_description_sha256','source_title_sha256']))
    enrich=accepted.alias('d').join(c.alias('c'),'job_id','inner').select(*[F.col('d.'+x).alias(x) for x in d.columns],*[F.col('c.'+x).alias(x) for x in additions],F.col('c.description').alias('d05_description'),F.col('c.title').alias('d05_title'))
    check('no_ambiguous_columns',len(enrich.columns)==len(set(enrich.columns)))
    source_binding={'a05_description_column':'source_description','stored_description':'D06.description unchanged',
                    'source_description':'D05.source_description unchanged; SHA UTF-8 verified',
                    'd05_description':'D05.description unchanged (clean text)', 'source_title':'D05.source_title unchanged',
                    'd05_title':'D05.title unchanged', 'a05_view':'validate_frames replaces description IN MEMORY only',
                    'human_binding_confirmation':'PENDING; no approval fabricated'}
    write(OUT/'source_binding.json',source_binding)
    def validate(frame,label):
        stats=keys(frame);check(label+'_population',stats=={'rows':5206,'distinct_job_id':5206,'null_job_id':0},stats)
        missing,extra=keydiff(accepted,frame),keydiff(frame,accepted)
        check(label+'_exact_accept_keyset',missing==0 and extra==0,{'missing':missing,'extra':extra})
        a=frame.select(*d.columns)
        check(label+'_all_d06_fields_preserved',a.exceptAll(accepted).count()==0 and accepted.exceptAll(a).count()==0,27)
        check(label+'_single_scalar_primary_group',isinstance(frame.schema['primary_group_code'].dataType,T.StringType) and frame.groupBy('job_id').agg(F.countDistinct('primary_group_code').alias('n')).filter('n>1').count()==0)
        check(label+'_taxonomy',frame.filter(~F.col('taxonomy_version').eqNullSafe(F.lit('0.2.2')) | ~F.col('taxonomy_sha256').eqNullSafe(F.lit(EXPECTED_TAX))).count()==0)
        reference=c.join(accepted.select('job_id'),'job_id','left_semi').select('job_id',*additions,F.col('description').alias('d05_description'),F.col('title').alias('d05_title'))
        fields=reference.columns; projected=frame.select(*fields)
        check(label+'_all_d05_values_preserved',projected.exceptAll(reference).count()==0 and reference.exceptAll(projected).count()==0)
        hashes=frame.alias('e').join(c.select('job_id','source_description_sha256','source_title_sha256').alias('c'),'job_id')
        bad=F.lit(False)
        for fld in ['description','title']:
            bad=bad|~F.col('e.source_'+fld+'_sha256').eqNullSafe(F.col('c.source_'+fld+'_sha256'))|~F.sha2(F.col('e.source_'+fld),256).eqNullSafe(F.col('e.source_'+fld+'_sha256'))
        check(label+'_source_hashes',hashes.filter(bad).count()==0)
        actual={f.name:f.dataType.simpleString() for f in frame.schema}
        check(label+'_required_runner_types',all(actual.get(k)==v for k,v in REQUIRED_TYPES.items()),{k:actual.get(k) for k in REQUIRED_TYPES})
        load_spark();validate_d06(frame,'primary_group_code')
        check(label+'_analyzer_input_validator',True)
        view=validate_frames(frame,c,{'a05_description_column':'source_description','taxonomy_version':'0.2.2','taxonomy_sha256':EXPECTED_TAX})
        check(label+'_a05_input_validator_and_raw_view',view.filter(~F.col('description').eqNullSafe(F.col('source_description'))).count()==0)
    validate(enrich,'prewrite')
    write(OUT/'writer_schema.json',enrich.schema.jsonValue())
    destination=OUT/'jobs.parquet'
    enrich.coalesce(2).write.mode('errorifexists').parquet(str(destination))
    saved=spark.read.parquet(str(destination))
    write(OUT/'schema.json',saved.schema.jsonValue())
    check('readback_schema',normalized(saved.schema.jsonValue())==normalized(enrich.schema.jsonValue()))
    check('readback_all_fields_exact',enrich.exceptAll(saved.select(enrich.columns)).count()==0 and saved.select(enrich.columns).exceptAll(enrich).count()==0)
    validate(saved,'readback')
    files=[{'path':p.relative_to(destination).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(destination.rglob('*')) if p.is_file()]
    input_digest=artifact_digest(destination)
    inventory={'algorithm':'TV2 artifact_digest: sorted recursive files INCLUDING markers/CRC; JSON compact [relative_path,size,sha256] rows, UTF-8 then SHA256',
               'artifact_sha256':input_digest,'files':files,'bytes':sum(x['bytes'] for x in files)}
    write(OUT/'output_inventory.json',inventory)
    check('output_inventory_digest',input_digest==artifact_digest(destination),input_digest)
    check('sources_and_implementation_unchanged',all(sha(p)==h for p,h in protected.items()),len(protected))
    result['resources_after']=resources()
    result['input_artifact_sha256']=input_digest
    result['status']='PASS'
    result['finished_utc']=datetime.now(timezone.utc).isoformat()
    write(OUT/'validation.json',result)
    receipt=read(ROOT/'config/d06_handoff_contract.example.json')
    receipt.update(status='TECHNICAL_VALIDATION_PASS_PENDING_INPUT_CONFIRMATION',run_id=RUN,it_jobs=str(destination),input_sha256=input_digest,
                   canonical_jobs=str(CANONICAL),canonical_sha256=artifact_digest(CANONICAL),approved_by=None,approved_on=None,
                   producer_commit=contract['commit'],taxonomy_version='0.2.2',taxonomy_sha256=EXPECTED_TAX,taxonomy_config=str(taxonomy),
                   classifier_sha256=sha(classifier),classifier_path=str(classifier),validation_report=str(OUT/'validation.json'),
                   validation_report_sha256=sha(OUT/'validation.json'),a05_description_column='source_description',job_functions_contract=None,timezone='UTC',
                   materializer_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                   original_d06_run_id=m['run_id'],a05_source_binding=str(OUT/'source_binding.json'),
                   note='Technical receipt only. No downstream input confirmation or Q05 route approval invented; upstream producer approvals retained separately.')
    write(OUT/'input_receipt.json',receipt)
    config=read(ROOT/'config/tv2_analysis_inputs.example.json')
    config.update(it_jobs=str(destination),d06_confirmation={'approved_by':None,'approved_on':None,'input_sha256':input_digest},
                  note='Real verified enriched input. Pending explicit input confirmation; no production analytics executed. Q05/A05/D07 optional dependencies intentionally unconfirmed.')
    write(OUT/'analysis_contract.json',config)
    deps,_=preflight(config)
    readiness={'enriched_receiving':'PASS','schema_ready_Q01_Q02_Q03_Q04_Q08':True,'q01_readiness':'READY' if deps['D06'] else 'BLOCKED',
               'dependencies':deps,'blocker':'d06_confirmation.approved_by/approved_on not supplied for the new enriched hash',
               'a05_receipt_errors':receipt_errors(receipt,purpose='a05'),'analysis_receipt_errors':receipt_errors(receipt,purpose='analysis'),
               'q01_only_cli':False,'after_confirmation_expected':'Q01-Q04/Q08 can execute; Q05/Q06/Q07 blocked; overall PARTIAL_SUCCESS, exit 2',
               'no_business_approval_created':True}
    write(OUT/'readiness.json',readiness)
    lineage={'d05':{'path':str(CANONICAL),'producer_input_inventory':m['input_inventory'],'tv2_artifact_sha256':receipt['canonical_sha256']},
             'd06':{'path':str(d6/'D06/predictions'),'run_id':m['run_id'],'schema_version':m['schema_version'],'schema_sha256':m['schema_sha256'],
                    'producer_output_fingerprint':seal['data_fingerprint'],'completion_sha256':sha(d6/'D06/completion.json'),
                    'manifest_sha256':sha(d6/'D06/run_manifest.json'),'runner_commit':contract['commit'],'classifier_tv2_commit':m['tv2_commit'],
                    'package_sha256':m['package_sha256'],'approval_hashes':m['approvals']},
             'join_contract':{'source':str(d6/'README_VI.md'),'sha256':sha(d6/'README_VI.md'),'standalone_join_contract':'NOT FOUND in local handoff/tmp',
                              'join':'D06 ACCEPT and is_it=true INNER JOIN unique D05 ON bigint job_id','null_imputation':False,'source_priority':'D06 fields unchanged; D05 additions and d05_description/d05_title aliases',
                              'added_d05_columns':additions,'job_functions_route_enabled':False},
             'protected_source_sha256':protected}
    write(OUT/'lineage.json',lineage)
    manifest={'run_id':RUN,'status':'SUCCESS','scope':'VERIFIED_ENRICHED_INPUT_NOT_ANALYTICS_OUTPUT','business_accepted':False,
              'started_utc':result['started_utc'],'finished_utc':result['finished_utc'],'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
              'commit':receipt['materializer_commit'],'materializer_path':str(pathlib.Path(__file__).resolve()),'materializer_sha256':sha(__file__),
              'rows':5206,'distinct_job_id':5206,'null_keys':0,'duplicate_keys':0,'missing_accept_keys':0,'extra_keys':0,
              'parquet':str(destination),'input_artifact_sha256':input_digest,'schema_fields':len(saved.columns),'schema_file':'schema.json',
              'writer_schema_file':'writer_schema.json','taxonomy_version':'0.2.2','taxonomy_sha256':EXPECTED_TAX,'lineage_file':'lineage.json',
              'validation_file':'validation.json','source_binding_file':'source_binding.json','receipt_file':'input_receipt.json','analysis_contract_file':'analysis_contract.json',
              'readiness':readiness,'runtime':result['runtime'],
              'artifact_sha256':{p.name:sha(p) for p in OUT.iterdir() if p.is_file()}}
    write(OUT/'manifest.json',manifest)
    write(OUT/'completion.json',{'run_id':RUN,'status':'SUCCEEDED','scope':'INPUT_MATERIALIZATION_ONLY','manifest_sha256':sha(OUT/'manifest.json'),
                                'validation_sha256':sha(OUT/'validation.json'),'inventory_sha256':sha(OUT/'output_inventory.json'),
                                'input_artifact_sha256':input_digest,'business_approved':False})
    print(json.dumps({'status':'PASS','output':str(destination),'sha256':input_digest,'q01_readiness':readiness['q01_readiness']}),flush=True)
except Exception as e:
    result.update(status='FAIL',error=repr(e),finished_utc=datetime.now(timezone.utc).isoformat())
    traceback.print_exc()
    if OUT.exists():write(OUT/'FAILED_validation.json',result)
finally:
    if spark:spark.stop()
    write(AUDIT,result)
sys.exit(0 if result['status']=='PASS' else 1)
