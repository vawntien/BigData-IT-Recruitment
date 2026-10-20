"""Q07 native posted salary contract v2. No classification or source normalization.

The caller supplies a validated population. This function never defines IT membership.
USABLE is TV1 mechanical eligibility, not business acceptance or an outlier policy.
"""
from pyspark.sql import functions as F, types as T

CONTEXT = ['a02_group', 'formatted_experience_level']
UNITS = ['currency', 'pay_period', 'compensation_type', 'salary_source']
POLICY = 'posted_min_max_separate_currency_period_source'


def unique_key(df, label):
    if df.schema['job_id'].dataType != T.LongType():
        raise ValueError(label + ': job_id must be bigint')
    if df.filter(F.col('job_id').isNull()).limit(1).count() or df.groupBy('job_id').count().filter('count > 1').limit(1).count():
        raise ValueError(label + ': expected one non-null row per job_id')


def salary_tables(population, salary, *, scope_id, minimum_n=None):
    """Return native-unit quantiles, all-population summary and status partition.

    Exact Spark percentile uses continuous linear interpolation and emits double.
    It is an explicit candidate method; no automatic rounding or suppression.
    Coverage fractions use B_g, including jobs missing salary/unit metadata.
    """
    if not isinstance(scope_id, str) or not scope_id.strip():
        raise ValueError('Explicit scope_id required')
    if minimum_n is not None and (type(minimum_n) is not int or minimum_n < 1):
        raise ValueError('minimum_n must be an explicit positive integer or None')
    for col in CONTEXT:
        if population.schema[col].dataType != T.StringType():
            raise ValueError('Population context must be string: ' + col)
    unique_key(population, 'population'); unique_key(salary, 'D07')
    expected = {'normalization_status': T.StringType(), 'salary_source': T.StringType(),
                'canonical_currency': T.StringType(), 'canonical_pay_period': T.StringType(),
                'canonical_compensation_type': T.StringType()}
    for col, typ in expected.items():
        if salary.schema[col].dataType != typ:
            raise ValueError('D07 type mismatch: ' + col)
    for col in ['min_salary', 'med_salary', 'max_salary']:
        if salary.schema['selected_salary'].dataType[col].dataType != T.DecimalType(20, 4):
            raise ValueError('D07 selected amounts must be decimal(20,4)')
    statuses = ['USABLE', 'MISSING', 'INVALID', 'AMBIGUOUS', 'EXCLUDED']
    if salary.filter(F.col('normalization_status').isNull() | ~F.col('normalization_status').isin(statuses)).limit(1).count():
        raise ValueError('Unknown D07 quality status')
    missing = population.select('job_id').join(salary.select('job_id'), 'job_id', 'left_anti')
    if missing.limit(1).count():
        raise ValueError('D07 does not cover supplied population; missing records are not MISSING status')
    fields = [F.col('canonical_' + c).alias(c) for c in ['currency', 'pay_period', 'compensation_type']]
    source = salary.select('job_id', 'normalization_status', 'salary_source', *fields,
                           *[F.col('selected_salary.' + c).alias(c) for c in ['min_salary', 'med_salary', 'max_salary']])
    scoped = population.select('job_id', *CONTEXT).join(source, 'job_id', 'left')
    eligible = F.col('normalization_status') == 'USABLE'
    # Check producer invariants rather than silently repairing/reclassifying rows.
    invalid = F.lit(False)
    for c in UNITS:
        invalid = invalid | F.col(c).isNull() | (F.trim(F.col(c)) == '')
    for c in ['min_salary', 'med_salary', 'max_salary']:
        invalid = invalid | (F.col(c).isNotNull() & (F.col(c) <= 0))
    invalid = invalid | (F.col('min_salary') > F.col('max_salary')) | (F.col('min_salary') > F.col('med_salary')) | (F.col('med_salary') > F.col('max_salary'))
    # coalesce each predicate above through final NULL-safe test; absent endpoints are allowed.
    if scoped.filter(eligible & F.coalesce(invalid, F.lit(False))).limit(1).count():
        raise ValueError('USABLE violates source bundle/amount invariants')
    if scoped.filter(eligible & F.col('min_salary').isNull() & F.col('med_salary').isNull() & F.col('max_salary').isNull()).limit(1).count():
        raise ValueError('USABLE has no amount')
    summary = scoped.groupBy(*CONTEXT).agg(F.countDistinct('job_id').alias('population_n'),
        F.countDistinct(F.when(eligible, F.col('job_id'))).alias('eligible_bundle_n'))
    quality = scoped.groupBy(*CONTEXT, 'normalization_status').agg(F.countDistinct('job_id').alias('job_count'))
    valid = scoped.filter(eligible)
    agg = [F.countDistinct('job_id').alias('eligible_bundle_n')]
    for c, suffix in [('min_salary', 'min'), ('max_salary', 'max')]:
        agg += [F.countDistinct(F.when(F.col(c).isNotNull(), F.col('job_id'))).alias('n_' + suffix),
                F.percentile(c, [0.25, 0.5, 0.75]).alias(c + '_q1_median_q3')]
    detail = valid.groupBy(*CONTEXT, *UNITS).agg(*agg)
    # Null context buckets must reconcile with population summaries too.
    a,b=detail.alias('a'),summary.select(*CONTEXT, 'population_n').alias('b')
    cond=F.lit(True)
    for c in CONTEXT: cond=cond & F.col('a.'+c).eqNullSafe(F.col('b.'+c))
    detail=a.join(b,cond,'left').select('a.*',F.col('b.population_n'))
    for suffix in ['min', 'max']:
        c=suffix+'_salary'; q=F.col(c+'_q1_median_q3')
        # Spark percentile returns NULL for an empty sample; no missing-to-zero.
        detail=detail.withColumn(c+'_q1', q[0]).withColumn(c+'_median', q[1]).withColumn(c+'_q3', q[2])
        detail=detail.withColumn(c+'_iqr',F.col(c+'_q3')-F.col(c+'_q1'))
        detail=detail.withColumn('coverage_'+suffix,F.col('n_'+suffix)/F.col('population_n'))
        detail=detail.withColumn('adequate_'+suffix, F.lit(None).cast('boolean') if minimum_n is None else F.col('n_'+suffix)>=minimum_n)
        detail=detail.drop(c+'_q1_median_q3')
    detail=detail.withColumn('eligible_coverage',F.col('eligible_bundle_n')/F.col('population_n'))
    summary=summary.withColumn('eligible_coverage',F.col('eligible_bundle_n')/F.col('population_n'))
    tables={'q07_salary_separate_units':detail,'q07_population_summary':summary,'q07_quality_status':quality}
    return {name:frame.withColumn('scope_id',F.lit(scope_id)).withColumn('salary_basis',F.lit('POSTED_NATIVE')) for name,frame in tables.items()}
