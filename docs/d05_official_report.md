# D05 Official Implementation Report

Status: **IMPLEMENTATION PASS — READY FOR ACCEPTANCE REVIEW**.
Official acceptance: **PENDING GROUP REVIEW**. D06: **NOT EXECUTED**.

Run UTC: 2026-10-15T12:33:59.660114+00:00; branch `feat/tv1-d05-official`; base commit `fbfcb59cff2cb93daa2ff087b42d0bf73f14fec9`.

## A03 readiness

Technical readiness PASS; see d05_a03_readiness_review.md. Source commit
`e437dcc11dda61f847673b9cc8c5801886c1996d`; report SHA-256 `371662d8c8ff06a9d3ce89bfc1427ddca96ec9b3dda19d51b8f26e913034f2e9`.
This does not assert formal acceptance of A03 by the team leader.

## Environment and output

Python 3.11.0; PySpark 4.2.0; Java 21.0.12.1.
Spark local[*], SQL session timezone UTC. Output: `data/processed/canonical/jobs/`.
Output directories use overwrite only for this pipeline's canonical output.
The Windows local filesystem adapter is reused from D04; raw and clean inputs are read-only.
The process defaults to a 3 GB driver heap (unless PYSPARK_SUBMIT_ARGS is supplied
externally). Automatic and adaptive broadcast joins are disabled for this session
because the source-text relation is too large for the default local heap.

## Inputs and key validation

| Table | Rows | Columns | Key | NULL keys | Duplicate keys |
| --- | --- | --- | --- | --- | --- |
| postings | 123849 | 35 | job_id | 0 | 0 |
| companies | 24473 | 10 | company_id | 0 | 0 |
| company_industries | 24375 | 2 | company_id+industry | 0 | 0 |
| company_specialities | 169367 | 2 | company_id+speciality | 0 | 0 |
| employee_counts | 35665 | 5 | company_id+time_recorded | 0 | 0 |
| benefits | 67943 | 3 | job_id+type | 0 | 0 |
| job_industries | 164808 | 2 | job_id+industry_id | 0 | 0 |
| job_skills | 213768 | 2 | job_id+skill_abr | 0 | 0 |
| salaries | 40785 | 8 | salary_id | 0 | 0 |
| industries | 422 | 2 | industry_id | 0 | 0 |
| skills | 35 | 2 | skill_abr | 0 | 0 |

All schemas are checked against D04's schema_changes evidence; relationship key types
must match. Salaries.job_id is additionally checked unique.

## JOIN design and reconciliation

Base: all clean postings, retaining their 35 columns. Restore raw source text with
a validated 1:1 LEFT JOIN; attach three pre-aggregated job bridges, the 0..1 salary
record and a pre-aggregated company dimension. Every right-side entity key is unique.

| Step | Before | Right | After | Distinct job_id | NULL job_id |
| --- | --- | --- | --- | --- | --- |
| source_text | 123849 | 123849 | 123849 | 123849 | 0 |
| job_functions | 123849 | 126807 | 123849 | 123849 | 0 |
| job_industries | 123849 | 127125 | 123849 | 123849 | 0 |
| benefits | 123849 | 30023 | 123849 | 123849 | 0 |
| salary | 123849 | 40785 | 123849 | 123849 | 0 |
| company | 123849 | 24473 | 123849 | 123849 | 0 |

## Canonical schema and NULL policy

| Column | Spark type | Nullable |
| --- | --- | --- |
| job_id | bigint | True |
| company_name | string | True |
| title | string | True |
| description | string | True |
| max_salary | decimal(20,4) | True |
| pay_period | string | True |
| location | string | True |
| company_id | bigint | True |
| views | bigint | True |
| med_salary | decimal(20,4) | True |
| min_salary | decimal(20,4) | True |
| formatted_work_type | string | True |
| applies | bigint | True |
| original_listed_time | timestamp | True |
| remote_allowed | boolean | True |
| job_posting_url | string | True |
| application_url | string | True |
| application_type | string | True |
| expiry | timestamp | True |
| closed_time | timestamp | True |
| formatted_experience_level | string | True |
| skills_desc | string | True |
| listed_time | timestamp | True |
| posting_domain | string | True |
| sponsored | boolean | True |
| work_type | string | True |
| currency | string | True |
| compensation_type | string | True |
| normalized_salary | decimal(20,4) | True |
| zip_code | string | True |
| fips | string | True |
| original_listed_time_raw | string | True |
| listed_time_raw | string | True |
| expiry_raw | string | True |
| closed_time_raw | string | True |
| source_title | string | True |
| source_description | string | True |
| source_title_sha256 | string | True |
| source_description_sha256 | string | True |
| job_functions | array<struct<skill_abr:string,skill_name:string,mapping_status:string>> | True |
| job_industries | array<struct<industry_id:bigint,industry_name:string,mapping_status:string>> | True |
| benefits | array<struct<type:string,inferred:boolean>> | True |
| salary_record | struct<salary_id:bigint,max_salary:decimal(20,4),med_salary:decimal(20,4),min_salary:decimal(20,4),pay_period:string,currency:string,compensation_type:string> | True |
| company | struct<name:string,description:string,company_size:bigint,state:string,country:string,city:string,zip_code:string,address:string,url:string,company_industries:array<string>,company_specialities:array<string>,latest_employee_snapshot:struct<employee_count:bigint,follower_count:bigint,time_recorded:timestamp,time_recorded_raw:string>> | True |
| source_text_file | string | True |
| canonical_schema_version | string | True |
| has_job_function_links | boolean | True |
| has_job_industry_links | boolean | True |
| has_benefit_links | boolean | True |
| company_lookup_status | string | True |

Full nested schema is in `data/audit/d05_canonical_schema.json`. The original 35
clean postings columns keep their names and types. `title`/`description` mean D04
clean text; `source_title`/`source_description` mean original parsed CSV text.
Parquet readback exposes nullable=true, including job_id; the non-null/unique
job_id requirement is an enforced runtime invariant rather than a storage guarantee.
`job_functions` contains sorted distinct structs(skill_abr,skill_name,mapping_status).
`job_industries` contains sorted distinct structs(industry_id,industry_name,mapping_status).
`benefits` contains sorted distinct structs(type,inferred), preserving inferred flags.
`salary_record` preserves the salaries source separately from postings salary columns.
`company` contains company attributes, arrays and latest_employee_snapshot.
Absent bridge links remain NULL (not an assertion that the real job has no skills).
No-link status flags make this explicit. Present industries with NULL names retain
their IDs and MISSING_LABEL. No technical_skills output is created.

## Referential coverage

| Parent | Child | Key | Child rows | NULL rows | Orphan keys | Orphan rows |
| --- | --- | --- | --- | --- | --- | --- |
| companies | postings | company_id | 123849 | 1717 | 1 | 1 |
| postings | job_skills | job_id | 213768 | 0 | 4711 | 7990 |
| postings | job_industries | job_id | 164808 | 0 | 4712 | 5845 |
| postings | benefits | job_id | 67943 | 0 | 1288 | 2550 |
| postings | salaries | job_id | 40785 | 0 | 4712 | 4712 |
| skills | job_skills | skill_abr | 213768 | 0 | 0 | 0 |
| industries | job_industries | industry_id | 164808 | 0 | 0 | 0 |
| companies | company_industries | company_id | 24375 | 0 | 0 | 0 |
| companies | company_specialities | company_id | 169367 | 0 | 0 | 0 |
| companies | employee_counts | company_id | 35665 | 0 | 0 | 0 |

All orphan counts remain in the audit; no input table is modified. Unreferenced
bridge records remain in clean staging. Canonical grain is postings, so child-only
job IDs do not introduce new jobs. Company missing/orphan status is distinguished.

## Source-text provenance

Raw reader: UTF-8, multiline, quote/escape double quote, no leading/trailing trim,
FAILFAST, source empty strings retained, no sentinel/encoding repair. Only job_id
is strictly canonicalized to bigint without float. Every raw title/description hash
was cross-checked against Python csv.DictReader on 123849 rows.
Source hashes are UTF-8 SHA-256 of the parsed fields, not of CSV escaped bytes.
Source text and hashes survive Parquet round-trip; clean postings fields are also
fingerprint-checked against D04. No A04 parity claim is made.

## Salary and snapshots

No imputation, annualization, currency or pay-period conversion. Preserve both
postings salary fields and salary_record. Latest employee snapshot is selected by
time_recorded descending, then employee_count/follower_count ascending. Clean
(company_id,time_recorded) is unique, making the latest selection deterministic.
Latest means latest in this source dataset, not as-of the posting date.

## Timezone

Spark TimestampType uses session UTC; no epoch is shifted. Time evidence is emitted
as explicit UTC strings with a Z suffix. Employee epoch 1712346173 equals
2024-04-05T19:42:53Z, or 2024-04-06T02:42:53+07:00 in Asia/Bangkok.
The older D05 pre-check labeled the latter local display as UTC; that historical
report is left unchanged. See d05_time_coverage.csv for runtime UTC values.

## Runtime validation

| Check | Status | Details |
| --- | --- | --- |
| input_rows:postings | PASS | 123849 |
| input_schema:postings | PASS | {"job_id": "bigint", "company_name": "string", "title": "string", "description": "string", "max_salary": "decimal(20,4)", "pay_period": "string", "location": "string", "company_id": "bigint", "views": "bigint", "med_salary": "decimal(20,4)", "min_salary": "decimal(20,4)", "formatted_work_type": "string", "applies": "bigint", "original_listed_time": "timestamp", "remote_allowed": "boolean", "job_posting_url": "string", "application_url": "string", "application_type": "string", "expiry": "timestamp", "closed_time": "timestamp", "formatted_experience_level": "string", "skills_desc": "string", "listed_time": "timestamp", "posting_domain": "string", "sponsored": "boolean", "work_type": "string", "currency": "string", "compensation_type": "string", "normalized_salary": "decimal(20,4)", "zip_code": "string", "fips": "string", "original_listed_time_raw": "string", "listed_time_raw": "string", "expiry_raw": "string", "closed_time_raw": "string"} |
| input_rows:companies | PASS | 24473 |
| input_schema:companies | PASS | {"company_id": "bigint", "name": "string", "description": "string", "company_size": "bigint", "state": "string", "country": "string", "city": "string", "zip_code": "string", "address": "string", "url": "string"} |
| input_rows:company_industries | PASS | 24375 |
| input_schema:company_industries | PASS | {"company_id": "bigint", "industry": "string"} |
| input_rows:company_specialities | PASS | 169367 |
| input_schema:company_specialities | PASS | {"company_id": "bigint", "speciality": "string"} |
| input_rows:employee_counts | PASS | 35665 |
| input_schema:employee_counts | PASS | {"company_id": "bigint", "employee_count": "bigint", "follower_count": "bigint", "time_recorded": "timestamp", "time_recorded_raw": "string"} |
| input_rows:benefits | PASS | 67943 |
| input_schema:benefits | PASS | {"job_id": "bigint", "inferred": "boolean", "type": "string"} |
| input_rows:job_industries | PASS | 164808 |
| input_schema:job_industries | PASS | {"job_id": "bigint", "industry_id": "bigint"} |
| input_rows:job_skills | PASS | 213768 |
| input_schema:job_skills | PASS | {"job_id": "bigint", "skill_abr": "string"} |
| input_rows:salaries | PASS | 40785 |
| input_schema:salaries | PASS | {"salary_id": "bigint", "job_id": "bigint", "max_salary": "decimal(20,4)", "med_salary": "decimal(20,4)", "min_salary": "decimal(20,4)", "pay_period": "string", "currency": "string", "compensation_type": "string"} |
| input_rows:industries | PASS | 422 |
| input_schema:industries | PASS | {"industry_id": "bigint", "industry_name": "string"} |
| input_rows:skills | PASS | 35 |
| input_schema:skills | PASS | {"skill_abr": "string", "skill_name": "string"} |
| key_type:companies:postings:company_id | PASS | bigint |
| key_type:postings:job_skills:job_id | PASS | bigint |
| key_type:postings:job_industries:job_id | PASS | bigint |
| key_type:postings:benefits:job_id | PASS | bigint |
| key_type:postings:salaries:job_id | PASS | bigint |
| key_type:skills:job_skills:skill_abr | PASS | string |
| key_type:industries:job_industries:industry_id | PASS | bigint |
| key_type:companies:company_industries:company_id | PASS | bigint |
| key_type:companies:company_specialities:company_id | PASS | bigint |
| key_type:companies:employee_counts:company_id | PASS | bigint |
| referential_reconciliation:postings:company_id | PASS | {"parent": "companies", "child": "postings", "key": "company_id", "child_rows": 123849, "null_key_rows": 1717, "child_distinct_keys": 24474, "matched_keys": 24473, "orphan_keys": 1, "orphan_rows": 1, "orphan_key_sample": "[23729571]", "coverage_percent": 99.9959140312168} |
| referential_reconciliation:job_skills:job_id | PASS | {"parent": "postings", "child": "job_skills", "key": "job_id", "child_rows": 213768, "null_key_rows": 0, "child_distinct_keys": 126807, "matched_keys": 122096, "orphan_keys": 4711, "orphan_rows": 7990, "orphan_key_sample": "[3079304796, 3884426997, 3884429730, 3884429847, 3884430610, 3884430835, 3884431661, 3884431673, 3884432447, 3884432560]", "coverage_percent": 96.28490540743019} |
| referential_reconciliation:job_industries:job_id | PASS | {"parent": "postings", "child": "job_industries", "key": "job_id", "child_rows": 164808, "null_key_rows": 0, "child_distinct_keys": 127125, "matched_keys": 122413, "orphan_keys": 4712, "orphan_rows": 5845, "orphan_key_sample": "[3079304796, 3884426997, 3884429730, 3884429847, 3884430610, 3884430835, 3884431661, 3884431673, 3884432447, 3884432560]", "coverage_percent": 96.29341199606687} |
| referential_reconciliation:benefits:job_id | PASS | {"parent": "postings", "child": "benefits", "key": "job_id", "child_rows": 67943, "null_key_rows": 0, "child_distinct_keys": 30023, "matched_keys": 28735, "orphan_keys": 1288, "orphan_rows": 2550, "orphan_key_sample": "[3884426997, 3884435133, 3884440276, 3884440738, 3884450335, 3884812706, 3884824095, 3884910775, 3884912975, 3884926003]", "coverage_percent": 95.70995570062952} |
| referential_reconciliation:salaries:job_id | PASS | {"parent": "postings", "child": "salaries", "key": "job_id", "child_rows": 40785, "null_key_rows": 0, "child_distinct_keys": 40785, "matched_keys": 36073, "orphan_keys": 4712, "orphan_rows": 4712, "orphan_key_sample": "[3079304796, 3884426997, 3884429730, 3884429847, 3884430610, 3884430835, 3884431661, 3884431673, 3884432447, 3884432560]", "coverage_percent": 88.44673286747579} |
| referential_reconciliation:job_skills:skill_abr | PASS | {"parent": "skills", "child": "job_skills", "key": "skill_abr", "child_rows": 213768, "null_key_rows": 0, "child_distinct_keys": 35, "matched_keys": 35, "orphan_keys": 0, "orphan_rows": 0, "orphan_key_sample": "[]", "coverage_percent": 100.0} |
| referential_reconciliation:job_industries:industry_id | PASS | {"parent": "industries", "child": "job_industries", "key": "industry_id", "child_rows": 164808, "null_key_rows": 0, "child_distinct_keys": 422, "matched_keys": 422, "orphan_keys": 0, "orphan_rows": 0, "orphan_key_sample": "[]", "coverage_percent": 100.0} |
| referential_reconciliation:company_industries:company_id | PASS | {"parent": "companies", "child": "company_industries", "key": "company_id", "child_rows": 24375, "null_key_rows": 0, "child_distinct_keys": 24365, "matched_keys": 24365, "orphan_keys": 0, "orphan_rows": 0, "orphan_key_sample": "[]", "coverage_percent": 100.0} |
| referential_reconciliation:company_specialities:company_id | PASS | {"parent": "companies", "child": "company_specialities", "key": "company_id", "child_rows": 169367, "null_key_rows": 0, "child_distinct_keys": 17780, "matched_keys": 17780, "orphan_keys": 0, "orphan_rows": 0, "orphan_key_sample": "[]", "coverage_percent": 100.0} |
| referential_reconciliation:employee_counts:company_id | PASS | {"parent": "companies", "child": "employee_counts", "key": "company_id", "child_rows": 35665, "null_key_rows": 0, "child_distinct_keys": 24473, "matched_keys": 24473, "orphan_keys": 0, "orphan_rows": 0, "orphan_key_sample": "[]", "coverage_percent": 100.0} |
| referential_relationship_count | PASS | 10 |
| raw_source_rows | PASS | 123849 |
| source_clean_key_bijection | PASS | raw_only=0;clean_only=0 |
| all_source_text_python_csv_sha256 | PASS | mismatches=0;unseen=0;rows=123849 |
| latest_employee_companies | PASS | 24473 |
| sorted_distinct_array:job_functions | PASS | bad_rows=0 |
| sorted_distinct_array:job_industries | PASS | bad_rows=0 |
| sorted_distinct_array:benefits | PASS | bad_rows=0 |
| sorted_distinct_array:company_industries | PASS | bad_rows=0 |
| sorted_distinct_array:company_specialities | PASS | bad_rows=0 |
| aggregation_repartition_determinism | PASS | 0 |
| left_join_grain:source_text | PASS | rows=123849;distinct=123849 |
| left_join_grain:job_functions | PASS | rows=123849;distinct=123849 |
| left_join_grain:job_industries | PASS | rows=123849;distinct=123849 |
| left_join_grain:benefits | PASS | rows=123849;distinct=123849 |
| left_join_grain:salary | PASS | rows=123849;distinct=123849 |
| left_join_grain:company | PASS | rows=123849;distinct=123849 |
| canonical_final_grain | PASS | (123849, 123849, 0) |
| roundtrip_grain | PASS | (123849, 123849, 0) |
| roundtrip_data_types | PASS | struct<job_id:bigint,company_name:string,title:string,description:string,max_salary:decimal(20,4),pay_period:string,location:string,company_id:bigint,views:bigint,med_salary:decimal(20,4),min_salary:decimal(20,4),formatted_work_type:string,applies:bigint,original_listed_time:timestamp,remote_allowed:boolean,job_posting_url:string,application_url:string,application_type:string,expiry:timestamp,closed_time:timestamp,formatted_experience_level:string,skills_desc:string,listed_time:timestamp,posting_domain:string,sponsored:boolean,work_type:string,currency:string,compensation_type:string,normalized_salary:decimal(20,4),zip_code:string,fips:string,original_listed_time_raw:string,listed_time_raw:string,expiry_raw:string,closed_time_raw:string,source_title:string,source_description:string,source_title_sha256:string,source_description_sha256:string,job_functions:array<struct<skill_abr:string,skill_name:string,mapping_status:string>>,job_industries:array<struct<industry_id:bigint,industry_name:string,mapping_status:string>>,benefits:array<struct<type:string,inferred:boolean>>,salary_record:struct<salary_id:bigint,max_salary:decimal(20,4),med_salary:decimal(20,4),min_salary:decimal(20,4),pay_period:string,currency:string,compensation_type:string>,company:struct<name:string,description:string,company_size:bigint,state:string,country:string,city:string,zip_code:string,address:string,url:string,company_industries:array<string>,company_specialities:array<string>,latest_employee_snapshot:struct<employee_count:bigint,follower_count:bigint,time_recorded:timestamp,time_recorded_raw:string>>,source_text_file:string,canonical_schema_version:string,has_job_function_links:boolean,has_job_industry_links:boolean,has_benefit_links:boolean,company_lookup_status:string> |
| full_nested_content_roundtrip_sha256 | PASS | forward=0;backward=0 |
| all_D04_postings_fields_preserved | PASS | forward=0;backward=0 |
| source_hash_roundtrip:title | PASS | 0 |
| source_hash_roundtrip:description | PASS | 0 |
| UTC_epoch_unchanged:postings:original_listed_time | PASS | mismatches=0 |
| UTC_epoch_unchanged:postings:listed_time | PASS | mismatches=0 |
| UTC_epoch_unchanged:postings:expiry | PASS | mismatches=0 |
| UTC_epoch_unchanged:postings:closed_time | PASS | mismatches=0 |
| UTC_epoch_unchanged:employee_counts:time_recorded | PASS | mismatches=0 |
| immutable_raw_clean_size_mtime | PASS | files=37 |

Raw and D04 clean file sizes/mtimes remained unchanged. Canonical write/read and
full content fingerprints passed. Validation includes sorted distinct bridge arrays,
repeat aggregation under different partitioning, source-key bijection and no row loss.
Small Spark regressions can be run with `.venv/Scripts/python.exe -B src/test_d05_official.py`;
their independently recorded results are in `data/audit/d05_official_regression_tests.csv`.

Independent regression run on 2026-10-15: **5 tests PASS**, 0 failures, 0 errors,
0 skipped. Tests cover exact large integral IDs, missing industry labels, sorted
deduplicated aggregation/no-link preservation, deterministic latest snapshots and
grain guards. This run does not rewrite canonical data.

Release revalidation on 2026-10-18 (Asia/Bangkok): the existing canonical Parquet
was read without running the builder. Rows=123849, distinct job_id=123849,
NULL job_id=0, duplicate job_id=0, columns=50; both source text hash checks had
zero mismatches. All 5 regression tests were rerun through unittest and passed
without invoking the test script's metadata-writing entry point. Raw/processed
file sizes and mtimes, and SHA-256 of all 4 canonical Parquet parts, were unchanged.
The 72-check audit remains evidence from the original 2026-10-15 implementation
run; it was reconciled during release review, not represented as a new full run.

The shell's default Java had changed to Java 8. Release runtime checks used the
installed Java 21 selected only for the verification process; system JAVA_HOME
was not modified. Future runs must select the documented Java 21 environment.

## Limitations and D06 handoff

No IT classification, A04 execution, skill extraction, salary analytics or D08/D09
official run. D06 must explicitly select source versus clean text, retain exact text
for evidence offsets, convert bigint IDs to the classifier's canonical string API,
distribute Python modules/config and preserve REVIEW. Taxonomy active is unchanged.
Frozen 176-job A04 inputs/predictions/manifests are still required for exact parity.
This report records implementation validation, not an automatic team acceptance.
