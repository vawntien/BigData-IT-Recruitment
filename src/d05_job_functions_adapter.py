"""Candidate Q05 projection; caller must confirm D06 membership and TV1 contract."""


def project_job_functions(canonical, selected_job_ids):
    """Return existing analyzer's (job_skills, skills) shapes, without flattening jobs.

    No membership inference, raw fallback, or invocation from official preflight.
    NULL arrays mean no source links. Missing labels retain their source code.
    """
    from pyspark.sql import functions as F, types as T
    if not isinstance(canonical.schema['job_id'].dataType,T.LongType) or not isinstance(selected_job_ids.schema['job_id'].dataType,T.LongType):
        raise ValueError('job_id must be bigint')
    for frame in [canonical, selected_job_ids]:
        if frame.filter(F.col('job_id').isNull()).limit(1).count() or frame.groupBy('job_id').count().filter('count > 1').limit(1).count():
            raise ValueError('One non-null row per job_id required before projection')
    typ=canonical.schema['job_functions'].dataType
    if not isinstance(typ,T.ArrayType) or not isinstance(typ.elementType,T.StructType):
        raise ValueError('Expected canonical job_functions array of structs')
    expected={'skill_abr','skill_name','mapping_status'}
    if set(typ.elementType.fieldNames()) != expected or any(not isinstance(f.dataType,T.StringType) for f in typ.elementType):
        raise ValueError('Unexpected D05 function contract')
    if selected_job_ids.select('job_id').join(canonical.select('job_id'),'job_id','left_anti').limit(1).count():
        raise ValueError('Selected job_id missing from canonical')
    scoped=canonical.join(selected_job_ids.select('job_id'),'job_id','left_semi')
    links=scoped.select('job_id',F.explode('job_functions').alias('v')).select('job_id','v.*')
    if links.filter(F.col('skill_abr').isNull() | (F.trim('skill_abr')=='') | F.col('mapping_status').isNull() |
                    ~F.col('mapping_status').isin('MAPPED','MISSING_LABEL') |
                    ((F.col('mapping_status')=='MAPPED') & (F.col('skill_name').isNull() | (F.trim('skill_name')==''))) |
                    ((F.col('mapping_status')=='MISSING_LABEL') & F.col('skill_name').isNotNull())).limit(1).count():
        raise ValueError('Invalid source mapping status/code/label')
    mapping=links.select('skill_abr','skill_name').distinct()
    if mapping.groupBy('skill_abr').count().filter('count > 1').limit(1).count():
        raise ValueError('Conflicting labels for one skill_abr; do not pick an arbitrary name')
    bridge=links.select('job_id','skill_abr').distinct()
    return bridge,mapping
