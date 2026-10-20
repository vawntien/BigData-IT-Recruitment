"""Receipt-gated A05 v0.1.2 local official runner; no raw/D05 fallback."""
import argparse
import json
from pathlib import Path

from tv2_csv import ROOT, sha256
from d06_handoff_validation import receipt_errors, verify_artifacts, validate_frames


def validate_outputs(tables, jobs):
    from pyspark.sql import functions as F
    b,e,s=[tables[k] for k in ('job_skill_technical','technical_skill_evidence','skill_source_processing')]
    def require(condition,message):
        if not condition:raise ValueError(message)
    def empty(frame):return not frame.limit(1).count()
    counts={k:v.count() for k,v in tables.items()}
    n=jobs.count()
    for table in (b,e,s):
        require(empty(table.filter(F.col('job_id').isNull())),'NULL output job_id')
        require(empty(table.select('job_id').join(jobs.select('job_id'),'job_id','left_anti')),'Output orphan')
    require(counts['skill_source_processing']==n and s.select('job_id').distinct().count()==n,'Processing population mismatch')
    require(empty(b.filter(F.col('skill_code').isNull())),'NULL skill_code')
    require(b.select('job_id','skill_code').distinct().count()==counts['job_skill_technical'],'Duplicate job-skill')
    require(empty(e.filter(F.col('evidence_id').isNull())) and e.select('evidence_id').distinct().count()==counts['technical_skill_evidence'],'Duplicate/NULL evidence_id')
    reference=jobs.select('job_id',F.sha2('description',256).alias('_hash'))
    for table in (e,s):
        require(empty(table.join(reference,'job_id').filter(~F.col('source_text_sha256').eqNullSafe(F.col('_hash')))),'Output source hash mismatch')
    allowed=['PROCESSED_WITH_MATCH','PROCESSED_NO_MATCH','SOURCE_MISSING']
    require(empty(s.filter(F.col('source_status').isNull() | ~F.col('source_status').isin(allowed))),'Failed/partial/unknown processing status')
    links=b.select('job_id','skill_code',F.explode('evidence_ids').alias('evidence_id'))
    accepted=e.filter('accepted = true').select('job_id','skill_code','evidence_id')
    require(empty(links.exceptAll(accepted)) and empty(accepted.exceptAll(links)),'Accepted evidence FK mismatch')
    require(empty(b.filter((F.col('evidence_count')!=F.size('evidence_ids')) | (F.col('evidence_count')<=0))),'Bridge evidence_count mismatch')
    per_job=b.groupBy('job_id').agg(F.count('*').alias('_skills'))
    aligned=s.join(per_job,'job_id','left').fillna({'_skills':0})
    require(empty(aligned.filter(F.col('accepted_skill_count')!=F.col('_skills'))),'Processing skill count mismatch')
    require(empty(aligned.filter(((F.col('source_status')=='PROCESSED_WITH_MATCH') & (F.col('_skills')==0)) |
                                ((F.col('source_status')!='PROCESSED_WITH_MATCH') & (F.col('_skills')>0)))),'Processing state/bridge mismatch')
    require(empty(s.filter((F.col('source_status')=='PROCESSED_NO_MATCH') &
                          (F.col('technical_skills').isNull() | (F.size('technical_skills')!=0)))),'Zero-hit must have empty skills')
    return dict(counts=counts,input_jobs=n,jobs_with_skills=b.select('job_id').distinct().count(),
                processing_status_counts={r['source_status']:r['count'] for r in s.groupBy('source_status').count().collect()},
                q06_denominator=s.filter(F.col('source_status').isin('PROCESSED_WITH_MATCH','PROCESSED_NO_MATCH')).count(),
                validation='PASS_KEYS_FK_SOURCE_HASH_STATES')


def run(args):
    output=Path(args.output).resolve()
    if output.exists() or not output.is_relative_to((ROOT/'data/analytics').resolve()):
        raise ValueError('Use a new directory under data/analytics')
    receipt_path=Path(args.receipt)
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    errors=receipt_errors(receipt,purpose='a05')
    if errors:
        print(json.dumps(dict(status='BLOCKED_DEPENDENCY',errors=errors)));return 2
    verify_artifacts(receipt,purpose='a05')
    from a05_spark import extract_frames
    from d05_utils import get_spark_session
    # Pin the stable release; the recommendation candidate is not an extractor.
    release=json.loads((ROOT/'config/a05_release_v0.1.2.json').read_text(encoding='utf-8'))
    for path,digest in release['pinned_files'].items():
        if sha256(ROOT/path)!=digest:raise ValueError('Release file changed: '+path)
    spark=get_spark_session('A05-OFFICIAL-RECEIPT-GATED',ROOT)
    result=None;manifest=None
    try:
        source=spark.read.parquet(receipt['it_jobs'])
        canonical=spark.read.parquet(receipt['canonical_jobs'])
        jobs=validate_frames(source,canonical,receipt)
        tables,result,_=extract_frames(jobs,ROOT/'config/versions/tech_skills_v0.1.2.json',args.run_id,
                                       dependency_mode=args.dependency_mode)
        summary=validate_outputs(tables,jobs)
        output.mkdir(parents=True,exist_ok=False)
        manifest=dict(status='WRITING',run_id=args.run_id,release='0.1.2',dictionary_version='0.1.2',
                      dictionary_sha256=sha256(ROOT/'config/versions/tech_skills_v0.1.2.json'),receipt_sha256=sha256(receipt_path),
                      input=receipt['it_jobs'],input_sha256=receipt['input_sha256'],taxonomy_version=receipt['taxonomy_version'],
                      taxonomy_sha256=receipt['taxonomy_sha256'],source_description_column=receipt['a05_description_column'],
                      dependency_mode=args.dependency_mode,spark_version=spark.version,pinned_files=release['pinned_files'],
                      known_limitations=release['known_limitations'],summary=summary,manual_acceptance_claimed=False)
        def save():
            (output/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        save()
        saved={}
        for name,frame in tables.items():
            frame.write.mode('errorifexists').parquet(str(output/(name+'.parquet')))
            read=spark.read.parquet(str(output/(name+'.parquet')))
            if [(f.name,f.dataType) for f in read.schema]!=[(f.name,f.dataType) for f in frame.schema]:
                raise ValueError('Parquet schema mismatch')
            if frame.exceptAll(read.select(frame.columns)).limit(1).count() or read.exceptAll(frame).limit(1).count():
                raise ValueError('Parquet content mismatch')
            saved[name]=read
        manifest['readback']=validate_outputs(saved,jobs)
        # Detect delivery mutation during extraction/write; do not silently publish it.
        verify_artifacts(receipt,purpose='a05')
        manifest['status']='SUCCESS'
        manifest['technical_validation']='PASS_OFFICIAL_PARQUET_READBACK'
        save();print(json.dumps(manifest,ensure_ascii=False));return 0
    except Exception as error:
        if manifest is not None:
            manifest.update(status='FAILED_PARTIAL_OUTPUT',error=repr(error))
            (output/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        raise
    finally:
        if result is not None:result.unpersist()
        spark.stop()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--receipt',required=True);p.add_argument('--output',required=True);p.add_argument('--run-id',required=True)
    p.add_argument('--dependency-mode',choices=['add_pyfile','shared_local_pythonpath'],default='add_pyfile')
    raise SystemExit(run(p.parse_args()))
