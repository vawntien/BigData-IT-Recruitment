# D03 Data Quality Report

## 1. Audit Environment

- OS: Windows
- Python: 3.11
- Java: OpenJDK 21 LTS Temurin
- PySpark: 4.2.0
- Spark mode: `local[*]`
- Reader: UTF-8, header enabled, `inferSchema=false`, quote/escape `"`

## 2. Dataset Inventory

| File | Rows | Columns |
| --- | --- | --- |
| data/raw/postings.csv | 123849 | 31 |
| data/raw/companies/companies.csv | 24473 | 10 |
| data/raw/companies/company_industries.csv | 24375 | 2 |
| data/raw/companies/company_specialities.csv | 169387 | 2 |
| data/raw/companies/employee_counts.csv | 35787 | 4 |
| data/raw/jobs/benefits.csv | 67943 | 3 |
| data/raw/jobs/job_industries.csv | 164808 | 2 |
| data/raw/jobs/job_skills.csv | 213768 | 2 |
| data/raw/jobs/salaries.csv | 40785 | 8 |
| data/raw/mappings/industries.csv | 422 | 2 |
| data/raw/mappings/skills.csv | 35 | 2 |

## 3. Candidate Keys

| Table | Candidate Key | Null | Distinct | Duplicate | Assessment |
| --- | --- | --- | --- | --- | --- |
| postings | job_id | 0 | 123849 | 0 | UNIQUE |
| postings | company_id | 1717 | 24474 | 97658 | NON_UNIQUE |
| companies | company_id | 0 | 24473 | 0 | UNIQUE |
| company_industries | company_id | 0 | 24365 | 10 | NON_UNIQUE |
| company_industries | company_id + industry | 0 | 24375 | 0 | UNIQUE |
| company_specialities | company_id | 0 | 17780 | 151607 | NON_UNIQUE |
| company_specialities | company_id + speciality | 0 | 169387 | 0 | UNIQUE |
| employee_counts | company_id | 0 | 24473 | 11314 | NON_UNIQUE |
| employee_counts | company_id + time_recorded | 0 | 35665 | 122 | NON_UNIQUE |
| benefits | job_id | 0 | 30023 | 37920 | NON_UNIQUE |
| benefits | job_id + type | 0 | 67943 | 0 | UNIQUE |
| job_industries | job_id | 0 | 127125 | 37683 | NON_UNIQUE |
| job_industries | job_id + industry_id | 0 | 164808 | 0 | UNIQUE |
| job_skills | job_id | 0 | 126807 | 86961 | NON_UNIQUE |
| job_skills | job_id + skill_abr | 0 | 213768 | 0 | UNIQUE |
| salaries | salary_id | 0 | 40785 | 0 | UNIQUE |
| salaries | job_id | 0 | 40785 | 0 | UNIQUE |
| industries | industry_id | 0 | 422 | 0 | UNIQUE |
| skills | skill_abr | 0 | 35 | 0 | UNIQUE |

Composite keys are evaluated only when every named column exists. A key is 
marked UNIQUE only when it has no missing component and no duplicate among 
non-missing rows.

## 4. Missing Data

Missing includes Spark NULL, blank strings, `null`, `NULL`, `N/A`, and `NA` 
after trimming/case normalization. Columns at or above 20% missing:

| Table | Column | Missing | Missing % |
| --- | --- | --- | --- |
| postings | closed_time | 122776 | 99.133622 |
| postings | skills_desc | 121410 | 98.030666 |
| postings | med_salary | 117569 | 94.929309 |
| postings | remote_allowed | 108603 | 87.689848 |
| salaries | med_salary | 33947 | 83.234032 |
| postings | applies | 100529 | 81.170619 |
| postings | max_salary | 94056 | 75.944093 |
| postings | min_salary | 94056 | 75.944093 |
| postings | compensation_type | 87776 | 70.873402 |
| postings | currency | 87776 | 70.873402 |
| postings | normalized_salary | 87776 | 70.873402 |
| postings | pay_period | 87776 | 70.873402 |
| postings | posting_domain | 39968 | 32.271556 |
| postings | application_url | 36665 | 29.604599 |
| postings | formatted_experience_level | 29409 | 23.745852 |
| postings | fips | 27415 | 22.135827 |

The complete column-level profile is in `data/audit/missing_profile.csv`.

## 5. Duplicate Analysis

Full-row equality is measured with a SHA-256 fingerprint of a JSON 
representation that retains field boundaries and explicit NULL values. This 
keeps the local Spark shuffle bounded for long description text.

| Table | Rows | Distinct Full Rows | Duplicate Full Rows |
| --- | --- | --- | --- |
| postings | 123849 | 123849 | 0 |
| companies | 24473 | 24473 | 0 |
| company_industries | 24375 | 24375 | 0 |
| company_specialities | 169387 | 169387 | 0 |
| employee_counts | 35787 | 35787 | 0 |
| benefits | 67943 | 67943 | 0 |
| job_industries | 164808 | 164808 | 0 |
| job_skills | 213768 | 213768 | 0 |
| salaries | 40785 | 40785 | 0 |
| industries | 422 | 422 | 0 |
| skills | 35 | 35 | 0 |

## 6. Time Coverage

| Table | Column | Unit | Raw Min | Raw Max | Interpreted Min UTC | Interpreted Max UTC |
| --- | --- | --- | --- | --- | --- | --- |
| postings | original_listed_time | UNIX_MILLISECONDS | 1701810533000 | 1713572803000 | 2023-12-05T21:08:53Z | 2024-04-20T00:26:43Z |
| postings | listed_time | UNIX_MILLISECONDS | 1711317014000 | 1713572816000 | 2024-03-24T21:50:14Z | 2024-04-20T00:26:56Z |
| postings | expiry | UNIX_MILLISECONDS | 1712903448000 | 1729124796000 | 2024-04-12T06:30:48Z | 2024-10-17T00:26:36Z |
| postings | closed_time | UNIX_MILLISECONDS | 1712345932000 | 1713562107000 | 2024-04-05T19:38:52Z | 2024-04-19T21:28:27Z |
| employee_counts | time_recorded | UNIX_SECONDS | 1712346173 | 1713572859 | 2024-04-05T19:42:53Z | 2024-04-20T00:27:39Z |

## 7. Encoding Findings

Mojibake-like sequences were found in strings decoded by Spark as UTF-8. This confirms that the sequences are present in decoded data and are not only a PowerShell display artifact. No values were changed.

| Table | Column | Affected Records | Affected % |
| --- | --- | --- | --- |
| postings | title | 1 | 0.000807 |
| postings | description | 79 | 0.063787 |
| companies | description | 3 | 0.012258 |

Configured patterns and samples are recorded in 
`data/audit/encoding_profile.csv`.

## 8. Referential Coverage

Comparison uses exact raw strings by default. When both sides contain only 
integral numeric values but differ in representation (for example `123` versus 
`123.0`), the audit additionally uses a numeric canonical form. Exact-raw and 
compared counts are both preserved in `data/audit/referential_profile.csv`; 
raw files are not changed.

| Parent | Child | Key | Child Non-Missing Rows | Comparison | Compared Child Keys | Matched | Unmatched | Coverage % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| companies | postings | company_id → company_id | 122132 | NUMERIC_CANONICAL | 24474 | 24473 | 1 | 99.995914 |
| postings | job_skills | job_id → job_id | 213768 | EXACT_RAW | 126807 | 122096 | 4711 | 96.284905 |
| postings | job_industries | job_id → job_id | 164808 | EXACT_RAW | 127125 | 122413 | 4712 | 96.293412 |
| postings | benefits | job_id → job_id | 67943 | EXACT_RAW | 30023 | 28735 | 1288 | 95.709956 |
| postings | salaries | job_id → job_id | 40785 | EXACT_RAW | 40785 | 36073 | 4712 | 88.446733 |
| skills | job_skills | skill_abr → skill_abr | 213768 | EXACT_RAW | 35 | 35 | 0 | 100.000000 |
| industries | job_industries | industry_id → industry_id | 164808 | EXACT_RAW | 422 | 422 | 0 | 100.000000 |
| companies | company_industries | company_id → company_id | 24375 | EXACT_RAW | 24365 | 24365 | 0 | 100.000000 |
| companies | company_specialities | company_id → company_id | 169387 | EXACT_RAW | 17780 | 17780 | 0 | 100.000000 |
| companies | employee_counts | company_id → company_id | 35787 | EXACT_RAW | 24473 | 24473 | 0 | 100.000000 |

## 9. Important Findings

- All 11 raw CSV files were readable by Spark.
- 16 columns have at least 20% missing values.
- 8 audited candidate/key fields are non-unique or contain missing values.
- 0 tables contain duplicate full rows.
- 5 audited relationships contain unmatched distinct child keys.
- Mojibake-like patterns occur in 3 table/column profiles.

## 10. Implications for D04

D04 will need explicit, documented rules for missing values, duplicates, key 
cardinality, orphan records, timestamp conversion, and any confirmed encoding 
issues. This D03 audit does not clean, drop, replace, join, or otherwise alter 
the raw data.
