# D04 Data Cleaning Report

## 1. Environment

- Python: 3.11.0
- Java: 21.0.12.1
- PySpark: 4.2.0
- Spark master: `local[*]`
- Spark SQL session timezone: `UTC`
- Output format: Parquet
- Windows local write adapter: project-local Java adapter; no Hadoop/winutils installation

## 2. Cleaning Principles

- Raw CSV files are immutable and were verified by size and mtime before/after.
- Missing numeric/boolean values remain NULL; they are never replaced with zero or false.
- Cleaning and duplicate resolution are deterministic.
- No JOIN, IT filtering, salary conversion, annualization, or business aggregation is performed.
- Orphan foreign keys identified by D03 are preserved.

## 3. Schema Normalization

| Table | Column | Raw Type | Clean Type | Rule |
| --- | --- | --- | --- | --- |
| postings | job_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| postings | company_name | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | title | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | description | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | max_salary | string | decimal(20,4) | Trim; missing→NULL; try-cast to decimal(20,4); no salary business normalization |
| postings | pay_period | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | location | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | company_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| postings | views | string | bigint | Trim; missing→NULL; strict integral cast; failures logged |
| postings | med_salary | string | decimal(20,4) | Trim; missing→NULL; try-cast to decimal(20,4); no salary business normalization |
| postings | min_salary | string | decimal(20,4) | Trim; missing→NULL; try-cast to decimal(20,4); no salary business normalization |
| postings | formatted_work_type | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | applies | string | bigint | Trim; missing→NULL; strict integral cast; failures logged |
| postings | original_listed_time | string | timestamp | Preserve *_raw; strict integer epoch milliseconds→UTC timestamp |
| postings | original_listed_time_raw | derived copy | string | Preserved normalized raw value for auditability of original_listed_time |
| postings | remote_allowed | string | boolean | Explicit true/1/1.0 and false/0/0.0 mapping; failures logged |
| postings | job_posting_url | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | application_url | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | application_type | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | expiry | string | timestamp | Preserve *_raw; strict integer epoch milliseconds→UTC timestamp |
| postings | expiry_raw | derived copy | string | Preserved normalized raw value for auditability of expiry |
| postings | closed_time | string | timestamp | Preserve *_raw; strict integer epoch milliseconds→UTC timestamp |
| postings | closed_time_raw | derived copy | string | Preserved normalized raw value for auditability of closed_time |
| postings | formatted_experience_level | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | skills_desc | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | listed_time | string | timestamp | Preserve *_raw; strict integer epoch milliseconds→UTC timestamp |
| postings | listed_time_raw | derived copy | string | Preserved normalized raw value for auditability of listed_time |
| postings | posting_domain | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | sponsored | string | boolean | Explicit true/1/1.0 and false/0/0.0 mapping; failures logged |
| postings | work_type | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | currency | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | compensation_type | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | normalized_salary | string | decimal(20,4) | Trim; missing→NULL; try-cast to decimal(20,4); no salary business normalization |
| postings | zip_code | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| postings | fips | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| companies | company_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| companies | name | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| companies | description | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| companies | company_size | string | bigint | Trim; missing→NULL; strict integral cast; failures logged |
| companies | state | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| companies | country | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| companies | city | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| companies | zip_code | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| companies | address | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| companies | url | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| company_industries | company_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| company_industries | industry | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| company_specialities | company_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| company_specialities | speciality | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| employee_counts | company_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| employee_counts | employee_count | string | bigint | Trim; missing→NULL; strict integral cast; failures logged |
| employee_counts | follower_count | string | bigint | Trim; missing→NULL; strict integral cast; failures logged |
| employee_counts | time_recorded | string | timestamp | Preserve *_raw; strict integer epoch seconds→UTC timestamp |
| employee_counts | time_recorded_raw | derived copy | string | Preserved normalized raw value for auditability of time_recorded |
| benefits | job_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| benefits | inferred | string | boolean | Explicit true/1/1.0 and false/0/0.0 mapping; failures logged |
| benefits | type | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| job_industries | job_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| job_industries | industry_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| job_skills | job_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| job_skills | skill_abr | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| salaries | salary_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| salaries | job_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| salaries | max_salary | string | decimal(20,4) | Trim; missing→NULL; try-cast to decimal(20,4); no salary business normalization |
| salaries | med_salary | string | decimal(20,4) | Trim; missing→NULL; try-cast to decimal(20,4); no salary business normalization |
| salaries | min_salary | string | decimal(20,4) | Trim; missing→NULL; try-cast to decimal(20,4); no salary business normalization |
| salaries | pay_period | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| salaries | currency | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| salaries | compensation_type | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| industries | industry_id | string | bigint | Trim; missing→NULL; accept integral numeric syntax including .0; cast to bigint |
| industries | industry_name | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| skills | skill_abr | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |
| skills | skill_name | string | string | Trim leading/trailing whitespace; missing sentinel→NULL; otherwise preserve text |

## 4. Missing-value Normalization

Spark NULL, blank strings, and the case-insensitive sentinels `null`, `N/A`, and `NA` 
are normalized to NULL after trimming. Internal free-text whitespace is preserved. 
No missing measure or flag is imputed.

| Table | Sentinel Cells Normalized |
| --- | --- |
| postings | 0 |
| companies | 5 |
| company_industries | 0 |
| company_specialities | 0 |
| employee_counts | 0 |
| benefits | 0 |
| job_industries | 0 |
| job_skills | 0 |
| salaries | 0 |
| industries | 0 |
| skills | 0 |

## 5. Identifier Normalization

Numeric identifiers use a strict integral grammar before `LongType` conversion. 
A value such as `123.0` is accepted only because its fractional portion is entirely 
zero and becomes canonical ID `123`. Non-integral, malformed, or out-of-range values 
become cast failures; required-key failures are quarantined rather than silently dropped.

No cast failure was observed in any configured typed column.

## 6. Timestamp Normalization

The four postings epoch fields are interpreted as Unix milliseconds; 
`employee_counts.time_recorded` is interpreted as Unix seconds. Typed columns are 
Spark `TimestampType` under UTC session timezone. A normalized string copy named 
`*_raw` is retained for auditability.

## 7. Encoding Repairs

Only D03-confirmed mappings are applied; no global encode/decode operation is used.

| Table | Column | Before Cells | After Cells | Fixed | Samples |
| --- | --- | --- | --- | --- | --- |
| postings | title | 1 | 0 | 1 | [{"before": "Medical AssistantÂ", "after": "Medical Assistant"}] |
| postings | description | 79 | 0 | 79 | [{"before": "Description\n\nSalary Estimate: $66705.60 - $100048.00 / year\n\nLearn More About The Benefits Offered For This Job.\n\nThe estimate displayed represents the typical salary range of candidates hired. Factors that may be used to determine your actual salary may include your specific skills, how many years ", "after": "Description\n\nSalary Estimate: $66705.60 - $100048.00 / year\n\nLearn More About The Benefits Offered For This Job.\n\nThe estimate displayed represents the typical salary range of candidates hired. Factors that may be used to determine your actual salary may include your specific skills, how many years "}, {"before": "Description\n\nIntroduction\n\nDo you have the PRN career opportunities as a(an) Patient Support Ambassador PRN you want with your current employer? We have an exciting opportunity for you to join Medical City McKinney which is part of the nation's leading provider of healthcare services, HCA Healthcare", "after": "Description\n\nIntroduction\n\nDo you have the PRN career opportunities as a(an) Patient Support Ambassador PRN you want with your current employer? We have an exciting opportunity for you to join Medical City McKinney which is part of the nation's leading provider of healthcare services, HCA Healthcare"}, {"before": "Description\n\nHourly Wage Estimate: $26.26 - $40.50 / hour\n\nLearn More About The Benefits Offered For This Job.\n\nThe estimate displayed represents the typical wage range of candidates hired. Factors that may be used to determine your actual salary may include your specific skills, how many years of e", "after": "Description\n\nHourly Wage Estimate: $26.26 - $40.50 / hour\n\nLearn More About The Benefits Offered For This Job.\n\nThe estimate displayed represents the typical wage range of candidates hired. Factors that may be used to determine your actual salary may include your specific skills, how many years of e"}] |
| companies | description | 3 | 0 | 3 | [{"before": "The Mount Sinai Hospital is one of the nation's oldest, largest, and most respected hospitals, and a member of the Mount Sinai Health System. \n\nThe Mount Sinai Health System is an integrated health system committed to providing distinguished care, conducting transformative research, and advancing bi", "after": "The Mount Sinai Hospital is one of the nation's oldest, largest, and most respected hospitals, and a member of the Mount Sinai Health System. \n\nThe Mount Sinai Health System is an integrated health system committed to providing distinguished care, conducting transformative research, and advancing bi"}, {"before": "PBS is made up of more than 350 local public noncommercial TV stations serving all 50 states, Puerto Rico, U.S. Virgin Islands, Guam and American Samoa. PBS stations reach more than 120 million people each month through on-air and online content.\n\nPBS is a private, nonprofit corporation, founded in ", "after": "PBS is made up of more than 350 local public noncommercial TV stations serving all 50 states, Puerto Rico, U.S. Virgin Islands, Guam and American Samoa. PBS stations reach more than 120 million people each month through on-air and online content.\n\nPBS is a private, nonprofit corporation, founded in "}, {"before": "At Pro-Tek, our services and business solutions are built around your needs. We deliver projects, processes, infrastructure and technologies that organizations need to effectively align IT with business objectives. We help clients meet business objectives through IT solutions and by providing the ex", "after": "At Pro-Tek, our services and business solutions are built around your needs. We deliver projects, processes, infrastructure and technologies that organizations need to effectively align IT with business objectives. We help clients meet business objectives through IT solutions and by providing the ex"}] |

Explicit mapping: `â€™→’`, `â€œ→“`, `â€→”`, `â€“→–`, `â€”→—`, and stray `Â→` empty.

Remaining configured mojibake cells after repair: 0.

## 8. Duplicate Handling

`employee_counts` before rows: 35787; duplicate logical-key groups: 
122; removed rows: 122; 
after rows: 35665.

Keep rule for `(company_id, time_recorded)`: highest count of non-null business fields, 
then presence of `employee_count`, then presence of `follower_count`, then ascending 
SHA-256 fingerprint of the complete typed row. Removed rows are preserved under 
`data/processed/rejected/employee_counts_duplicate_keys/`.

Detailed duplicate groups recorded: 122.

Other candidate-key collisions introduced or exposed by missing/trim/type 
normalization are not silently deleted. Extra rows are content-ranked, written 
under `data/processed/rejected/<table>_duplicate_keys/`, and listed below.

## 9. Rejected / Quarantined Records

| Table | Candidate Key | Groups | Removed | Keep Rule |
| --- | --- | --- | --- | --- |
| company_specialities | company_id + speciality | 20 | 20 | most non-null non-key fields, then ascending SHA-256 typed-row fingerprint |

| Table | Malformed | Invalid Required Key | Duplicate Removed | Total Rejected |
| --- | --- | --- | --- | --- |
| postings | 0 | 0 | 0 | 0 |
| companies | 0 | 0 | 0 | 0 |
| company_industries | 0 | 0 | 0 | 0 |
| company_specialities | 0 | 0 | 20 | 20 |
| employee_counts | 0 | 0 | 122 | 122 |
| benefits | 0 | 0 | 0 | 0 |
| job_industries | 0 | 0 | 0 | 0 |
| job_skills | 0 | 0 | 0 | 0 |
| salaries | 0 | 0 | 0 | 0 |
| industries | 0 | 0 | 0 | 0 |
| skills | 0 | 0 | 0 | 0 |

## 10. Row Reconciliation

| Table | Input | Output | Rejected | Duplicate Removed |
| --- | --- | --- | --- | --- |
| postings | 123849 | 123849 | 0 | 0 |
| companies | 24473 | 24473 | 0 | 0 |
| company_industries | 24375 | 24375 | 0 | 0 |
| company_specialities | 169387 | 169367 | 20 | 20 |
| employee_counts | 35787 | 35665 | 122 | 122 |
| benefits | 67943 | 67943 | 0 | 0 |
| job_industries | 164808 | 164808 | 0 | 0 |
| job_skills | 213768 | 213768 | 0 | 0 |
| salaries | 40785 | 40785 | 0 | 0 |
| industries | 422 | 422 | 0 | 0 |
| skills | 35 | 35 | 0 | 0 |

For every table: `input_rows = output_rows + rejected_rows`.

## 11. Validation

Validation checks executed: 67; failures: 0.

| Table | Check | Status | Details |
| --- | --- | --- | --- |
| postings | unique(job_id) | PASS | duplicate_groups=0 |
| postings | required_non_null(job_id) | PASS | null_rows=0 |
| postings | parquet_readback_row_count | PASS | expected=123849;actual=123849 |
| postings | type(job_id) | PASS | expected=bigint;actual=bigint |
| postings | type(company_id) | PASS | expected=bigint;actual=bigint |
| postings | type(max_salary) | PASS | expected=decimal(20,4);actual=decimal(20,4) |
| postings | type(med_salary) | PASS | expected=decimal(20,4);actual=decimal(20,4) |
| postings | type(min_salary) | PASS | expected=decimal(20,4);actual=decimal(20,4) |
| postings | type(normalized_salary) | PASS | expected=decimal(20,4);actual=decimal(20,4) |
| postings | type(views) | PASS | expected=bigint;actual=bigint |
| postings | type(applies) | PASS | expected=bigint;actual=bigint |
| postings | type(remote_allowed) | PASS | expected=boolean;actual=boolean |
| postings | type(sponsored) | PASS | expected=boolean;actual=boolean |
| postings | type(original_listed_time) | PASS | expected=timestamp;actual=timestamp |
| postings | type(listed_time) | PASS | expected=timestamp;actual=timestamp |
| postings | type(expiry) | PASS | expected=timestamp;actual=timestamp |
| postings | type(closed_time) | PASS | expected=timestamp;actual=timestamp |
| companies | unique(company_id) | PASS | duplicate_groups=0 |
| companies | required_non_null(company_id) | PASS | null_rows=0 |
| companies | parquet_readback_row_count | PASS | expected=24473;actual=24473 |
| companies | type(company_id) | PASS | expected=bigint;actual=bigint |
| companies | type(company_size) | PASS | expected=bigint;actual=bigint |
| company_industries | unique(company_id, industry) | PASS | duplicate_groups=0 |
| company_industries | required_non_null(company_id, industry) | PASS | null_rows=0 |
| company_industries | parquet_readback_row_count | PASS | expected=24375;actual=24375 |
| company_industries | type(company_id) | PASS | expected=bigint;actual=bigint |
| company_specialities | unique(company_id, speciality) | PASS | duplicate_groups=0 |
| company_specialities | required_non_null(company_id, speciality) | PASS | null_rows=0 |
| company_specialities | parquet_readback_row_count | PASS | expected=169367;actual=169367 |
| company_specialities | type(company_id) | PASS | expected=bigint;actual=bigint |
| employee_counts | unique(company_id, time_recorded) | PASS | duplicate_groups=0 |
| employee_counts | required_non_null(company_id, time_recorded) | PASS | null_rows=0 |
| employee_counts | parquet_readback_row_count | PASS | expected=35665;actual=35665 |
| employee_counts | type(company_id) | PASS | expected=bigint;actual=bigint |
| employee_counts | type(employee_count) | PASS | expected=bigint;actual=bigint |
| employee_counts | type(follower_count) | PASS | expected=bigint;actual=bigint |
| employee_counts | type(time_recorded) | PASS | expected=timestamp;actual=timestamp |
| benefits | unique(job_id, type) | PASS | duplicate_groups=0 |
| benefits | required_non_null(job_id, type) | PASS | null_rows=0 |
| benefits | parquet_readback_row_count | PASS | expected=67943;actual=67943 |
| benefits | type(job_id) | PASS | expected=bigint;actual=bigint |
| benefits | type(inferred) | PASS | expected=boolean;actual=boolean |
| job_industries | unique(job_id, industry_id) | PASS | duplicate_groups=0 |
| job_industries | required_non_null(job_id, industry_id) | PASS | null_rows=0 |
| job_industries | parquet_readback_row_count | PASS | expected=164808;actual=164808 |
| job_industries | type(job_id) | PASS | expected=bigint;actual=bigint |
| job_industries | type(industry_id) | PASS | expected=bigint;actual=bigint |
| job_skills | unique(job_id, skill_abr) | PASS | duplicate_groups=0 |
| job_skills | required_non_null(job_id, skill_abr) | PASS | null_rows=0 |
| job_skills | parquet_readback_row_count | PASS | expected=213768;actual=213768 |
| job_skills | type(job_id) | PASS | expected=bigint;actual=bigint |
| salaries | unique(salary_id) | PASS | duplicate_groups=0 |
| salaries | unique(job_id) | PASS | duplicate_groups=0 |
| salaries | required_non_null(salary_id, job_id) | PASS | null_rows=0 |
| salaries | parquet_readback_row_count | PASS | expected=40785;actual=40785 |
| salaries | type(salary_id) | PASS | expected=bigint;actual=bigint |
| salaries | type(job_id) | PASS | expected=bigint;actual=bigint |
| salaries | type(max_salary) | PASS | expected=decimal(20,4);actual=decimal(20,4) |
| salaries | type(med_salary) | PASS | expected=decimal(20,4);actual=decimal(20,4) |
| salaries | type(min_salary) | PASS | expected=decimal(20,4);actual=decimal(20,4) |
| industries | unique(industry_id) | PASS | duplicate_groups=0 |
| industries | required_non_null(industry_id) | PASS | null_rows=0 |
| industries | parquet_readback_row_count | PASS | expected=422;actual=422 |
| industries | type(industry_id) | PASS | expected=bigint;actual=bigint |
| skills | unique(skill_abr) | PASS | duplicate_groups=0 |
| skills | required_non_null(skill_abr) | PASS | null_rows=0 |
| skills | parquet_readback_row_count | PASS | expected=35;actual=35 |

## 12. Remaining Issues for Later Tasks

- D05: decide JOIN scope and treatment of orphan foreign keys.
- D06: identify and filter IT-related postings.
- D07: define salary semantics, currency conversion, pay-period normalization, and analytics.

D04 does not implement any of those downstream decisions.
