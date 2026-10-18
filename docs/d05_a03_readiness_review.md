# D05 — A03 technical readiness review

Review date: 2026-10-15 (Asia/Bangkok).

Technical readiness: **PASS**. This is TV1's dependency/design review, not formal
team-leader acceptance of A03. D05 implementation is authorized by the current
request. A04 and D06 are outside this implementation.

Source: `origin/feat/tv2-analysis`, pinned commit
`e437dcc11dda61f847673b9cc8c5801886c1996d`,
`docs/a03_skills_industries_report.md` and its `data/audit/tv2_raw_*`,
`tv2_source_labels.csv`, `tv2_source_industries.csv` evidence. TV2 is not merged.

The report was compared with the TV1 data dictionary, D03/D04 reports, D05
pre-check and implementation scaffold. The preceding handoff review independently
confirmed that all 11 TV1 raw-file SHA-256 values match TV2's raw inventory.
D05 rechecks the actual clean Parquet inputs rather than treating historical
reports as runtime validation.

| Topic | Accepted design evidence / D05 rule |
| --- | --- |
| Base grain | Clean postings; one non-null unique bigint job_id; 123849 rows |
| Numeric keys | Use D04 bigint keys; raw job_id is strictly integral, without float conversion |
| Job functions | 35 source labels; preserve code and name; they are not technical skills |
| Job industries | 422 mapping IDs; preserve IDs even when industry_name is NULL (34 labels missing) |
| Company industries | String names by company_id; do not join these names to industry_id |
| Bridges | Validate composite keys, aggregate sorted distinct values before joining |
| Orphans | Quantify distinct keys and rows for all ten relationships; keep all base postings |
| Employee snapshots | Latest timestamp per company, deterministic count tie-break; not an as-of-posting snapshot |
| Technical skills | description is the future primary source; skills_desc is supplementary pending evaluation; no extraction in D05 |
| Salary | Retain postings and salaries sources separately, without annualization, imputation or conversion |
| Text provenance | Preserve parsed raw title/description and UTF-8 hashes separately from D04 clean text; verify against Python's CSV parser |
| Timezone | UTC for Spark timestamps; old pre-check's +7-hour display is not a source epoch correction |

The historical statement “A03 does not exist” in the D05 pre-check/scaffold is
superseded by this review; those historical files remain unchanged.

Remaining integration decisions: D06 must select the input text explicitly,
preserve REVIEW, distribute the Python classifier/config, and adapt bigint job_id
to its canonical string API. Candidate v0.2.2 is not promoted here. Exact A04
parity remains blocked by the missing frozen 176-job reference package.
