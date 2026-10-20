"""Candidate receiving checks; never classify canonical or synthesize D06 output."""
import json
from pathlib import Path
from a06_a08_spark_analysis import artifact_digest
from tv2_csv import sha256

REQUIRED_TYPES={
    'job_id':'bigint','description':'string','source_description':'string','source_description_sha256':'string',
    'source_title':'string','source_title_sha256':'string','it_decision':'string','is_it':'boolean',
    'taxonomy_version':'string','taxonomy_sha256':'string','primary_group_code':'string',
    'formatted_experience_level':'string','location':'string','formatted_work_type':'string',
    'work_type':'string','remote_allowed':'boolean','original_listed_time':'timestamp','listed_time':'timestamp'}


def receipt_errors(receipt, *, purpose='analysis'):
    if purpose not in {'analysis','a05'}:raise ValueError('Unknown receipt validation purpose')
    errors=[]
    for key in ['it_jobs','input_sha256','canonical_jobs','canonical_sha256','approved_by','approved_on',
                'producer_commit','taxonomy_version','taxonomy_sha256','taxonomy_config','classifier_sha256','classifier_path',
                'validation_report','validation_report_sha256']:
        if not isinstance(receipt.get(key),str) or not receipt[key].strip():errors.append('MISSING_'+key)
    if receipt.get('schema_version')!=1:errors.append('SCHEMA_VERSION')
    if receipt.get('timezone')!='UTC':errors.append('UTC_REQUIRED')
    if receipt.get('a05_description_column') not in ['description','source_description']:errors.append('TEXT_BINDING_UNCONFIRMED')
    if purpose=='analysis' and receipt.get('job_functions_contract') not in ['embedded_job_functions','separate_clean_bridges']:errors.append('Q05_CONTRACT_UNCONFIRMED')
    for key in ['input_sha256','canonical_sha256','taxonomy_sha256','classifier_sha256','validation_report_sha256']:
        value=receipt.get(key)
        if value and (not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value)):errors.append('INVALID_HASH_'+key)
    return errors


def verify_artifacts(receipt, *, purpose='analysis'):
    errors=receipt_errors(receipt,purpose=purpose)
    if errors:raise ValueError(';'.join(errors))
    for path_key,hash_key in [('it_jobs','input_sha256'),('canonical_jobs','canonical_sha256'),
                              ('taxonomy_config','taxonomy_sha256'),('classifier_path','classifier_sha256'),('validation_report','validation_report_sha256')]:
        path=Path(receipt[path_key])
        if not path.exists() or artifact_digest(path)!=receipt[hash_key]:raise ValueError('Missing/changed artifact '+path_key)
    config=json.loads(Path(receipt['taxonomy_config']).read_text(encoding='utf-8'))
    if config.get('version')!=receipt['taxonomy_version']:raise ValueError('Taxonomy version/hash disagreement')


def validate_frames(d,canonical,receipt):
    """All-row source/key/provenance checks; return an explicit in-memory A05 view."""
    from pyspark.sql import functions as F
    if receipt.get('a05_description_column') not in ['description','source_description']:raise ValueError('Confirm text binding first')
    if d.sparkSession.conf.get('spark.sql.session.timeZone')!='UTC':raise ValueError('UTC required')
    actual={f.name:f.dataType.simpleString() for f in d.schema}
    if any(actual.get(k)!=v for k,v in REQUIRED_TYPES.items()):raise ValueError('D06 required schema mismatch')
    for frame in [d,canonical]:
        if frame.filter(F.col('job_id').isNull()).limit(1).count() or frame.groupBy('job_id').count().filter('count > 1').limit(1).count():raise ValueError('NULL/duplicate job_id')
    if not d.count():raise ValueError('Empty D06 not an accepted production population')
    if d.filter(F.col('it_decision').isNull() | (F.col('it_decision')!='ACCEPT') | F.col('is_it').isNull() | ~F.col('is_it') |
                ~F.col('taxonomy_version').eqNullSafe(F.lit(receipt['taxonomy_version'])) |
                ~F.col('taxonomy_sha256').eqNullSafe(F.lit(receipt['taxonomy_sha256']))).limit(1).count():raise ValueError('D06 membership/taxonomy mismatch')
    reference=canonical.select('job_id',*[F.col(c).alias('_ref_'+c) for c in ['source_description','source_description_sha256','source_title','source_title_sha256']])
    if d.select('job_id').join(reference.select('job_id'),'job_id','left_anti').limit(1).count():raise ValueError('D06 orphan outside D05')
    joined=d.join(reference,'job_id')
    bad=~F.col(receipt['a05_description_column']).eqNullSafe(F.col('_ref_source_description'))
    for col in ['source_description','source_description_sha256','source_title','source_title_sha256']:
        bad=bad | ~F.col(col).eqNullSafe(F.col('_ref_'+col))
    for field in ['description','title']:
        bad=bad | ~F.sha2(F.col('source_'+field),256).eqNullSafe(F.col('source_'+field+'_sha256'))
    if joined.filter(bad).limit(1).count():raise ValueError('Source text/hash differs from canonical or selected A05 binding')
    # Never rewrite canonical/D06 Parquet. Preserve clean D06.description in storage.
    return d.withColumn('description',F.col(receipt['a05_description_column']))
