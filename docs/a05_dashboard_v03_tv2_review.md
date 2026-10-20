# TV2 review Data Contract Dashboard V03.1

Ngày 19/10/2026 (Asia/Bangkok), hỗ trợ Đồng Viết Dũng — TV2. Chỉ review và tạo báo cáo; không sửa tài liệu TV3, A01–A05, taxonomy/dictionary hoặc pipeline. Không chạy production, checkout, merge, commit hoặc push.

**Cập nhật Q07 ngày 20/10/2026:** các mô tả paired `salary_n` và thiếu D07 bên dưới là snapshot review 19/10. D07 staging đã kiểm PASS; analyzer hiện dùng [contract Q07 v2](../config/q07_salary_contract_v2.json) và [implementation native posted salary](../src/q07_salary.py): n_min/n_max độc lập, scalar Q1/median/Q3/IQR, B_g summary và quality partition. [Hồ sơ tích hợp hiện hành](tv2_d05_d07_integration_20261020.md#q07--cập-nhật-implementation-tiếp-nối-ngày-2010) ghi giới hạn và câu hỏi TV1. Contract v2 là candidate có implementation, chưa phải signoff TV1/TV3 hoặc output IT production; D06 Full vẫn thiếu. Không sửa nội dung contract TV3.

## Nguồn đã đọc và cách xác minh

Branch trước/sau: `feat/tv2-analysis`. Đã đọc `git status --short`: có sẵn `.gitattributes` modified cùng nhiều artifact TV2 untracked. Không nhận các thay đổi đó là của lượt review.

Đã chạy `git fetch origin feat/tv3-dashboard`. Lần đầu lỗi `error: cannot open '.git/FETCH_HEAD': Permission denied`; chạy lại với quyền sandbox phù hợp thành công, commit **ba57c728d56e887c7555e545032e93a762b77801**. Đã đọc trực tiếp bằng `git show FETCH_HEAD:docs/dashboard/dashboard_data_contract_draft.md`, không checkout/merge. Không phải dùng remote-tracking cũ làm fallback.

Bản thực tế mới nhất là **V03.1 — DISCUSSION DRAFT / NOT APPROVED / NOT PRODUCTION READY**. Không review V03.0 bằng suy đoán. Đã đọc cả V01.3 wireframe cùng commit. [V03 cố định theo commit](https://github.com/vawntien/BigData-IT-Recruitment/blob/ba57c728d56e887c7555e545032e93a762b77801/docs/dashboard/dashboard_data_contract_draft.md), [V01 cố định](https://github.com/vawntien/BigData-IT-Recruitment/blob/ba57c728d56e887c7555e545032e93a762b77801/docs/dashboard/dashboard_wireframe.md).

Quy ước bằng chứng: `V03:L…` là dòng trong file contract tại commit trên; `V01:L…` là dòng wireframe cùng commit. `analyzer` = `src/a06_a08_spark_analysis.py`; `schema` = `config/tv2_analysis_output_schema.json`; `readiness` = `docs/a05_official_readiness_20261019.md`. Dòng local trỏ file hiện tại. Schema đang có `schema_version=1`, `status=CANDIDATE_NOT_SPARK_VALIDATED`, không được coi là schema production đã chốt.

Đã đọc artifact/code/schema/manifests và kiểm kê file local gồm dữ liệu bị ignore. Lượt này kiểm SHA-256 D05 và release A05, không khởi chạy Spark/test suite. Kết quả tests/readback nêu dưới đây là bằng chứng đã lưu, không phải tái chạy hôm nay. Báo cáo giữ ranh giới requirements, code candidate, development output và production.

**Kết luận:** Có thể chốt các nguyên tắc thiết kế Q01–Q08 của V03.1. Physical contract, production và filter capabilities vẫn PENDING. Bản mới đã sửa các lỗi semantics cũ; không yêu cầu TV3 sửa lại điều V03.1 đã sửa. Cần cập nhật evidence TV2 mới, mapping fraction→percent, Q07 source policy và các gap giữa thiết kế với implementation/output.

## Bảng review năm nội dung TV3 yêu cầu

Chỉ dùng OK, CẦN SỬA, PENDING. OK về design/semantics không thay formal sign-off của TV2 hoặc nghiệm thu output.

| Mục V03 | Trạng thái | Vấn đề hoặc xác nhận | Bằng chứng file/dòng | Đề nghị xử lý |
| ------- | ---------- | -------------------- | -------------------- | ------------- |
| 1. V01: ba trang và Q01–Q08 | OK | Overview Q01–Q04/Q08; Skills Q05/Q06; Salary & Quality Q07 và audit. Đủ A01, Quality không thêm câu business. | V03:L38; V01:L198–209; `docs/a01_analysis_questions.md:96–105` | Chốt phạm vi thiết kế; formal sign-off V01 do người phụ trách xác nhận riêng. |
| 1. KPI Overview | OK | B=distinct tin IT trong filter; top group/location và L/B đúng nghĩa. 123849 là ALL JOBS, không phải N IT. | V01:L79–87; A01:L82–90 | B=0 không có thứ hạng; ghi đồng hạng. Chỉ bật khi có output đúng context. |
| 1. KPI Skills/Salary/Time/Quality | OK | Q05 K, K/B, B−K; Q06 D, D/B, zero-hit; Q07 phân vị/n riêng; Q08 V riêng từng basis. Raw audit khác IT quality. | V01:L108,116–120,140–155; V03:L224,247,268–313 | Giữ đúng nhãn và denominator; không gọi skill mention là skill bắt buộc. |
| 1. UI baseline và design | PENDING | Wireframe ghi baseline thiếu Q05/Q08, median_salary chung, KPI cứng. Đủ design chưa có nghĩa app đã triển khai. | V01:L89,100,110,146,157,200–207; V03:L384,433 | TV3 cập nhật UI/validator sau khi nhận contract/output; không coi V04–V06 đã hoàn thành. |
| 2. A02/A04 versions | PENDING | Active local 0.2.0; candidate bàn giao 0.2.2. Không có D06 Full/receipt chứng minh version D06 thực dùng. | `docs/a04_handoff_tv1.md:3–18`; `docs/a04_filter_fix_round2_report.md:3–9`; V03:L408 | TV1 giao actual config/version/hash/classifier/run; TV2 đối chiếu. Không tự promote candidate. |
| 2. A03 nhãn và ngành | OK | 35 source labels không phải Python/Java/SQL; ngành khác nhãn chức năng và taxonomy nghề. Mapping bằng mã, không JOIN tên giữa hai hệ. | `docs/a03_skills_industries_report.md:34–38,76–88,106–155,216–224`; V03:L210–231 | Chốt thuật ngữ Q05; phiên bản source theo checksum/snapshot, không bịa semver A03. |
| 2. A05 stable/candidate | OK | Stable v0.1.2 có pinned release và local Spark parity 105 development PASS. Context recommendations chưa vào extractor/bridge. | readiness:L5–9,45–49; `config/a05_release_v0.1.2.json:2–17` | Chốt baseline cùng giới hạn; không promote bằng audit fixtures, không nhận production. |
| 2. Upstream readiness evidence | CẦN SỬA | V03 “chỉ .gitkeep” và chưa có A02/A03/A05 mới là scope checkout TV3. TV2 hiện có D05 Parquet, artifacts mới và analyzer. | V03:L83–105; `docs/tv2_d05_receipt_457f90ae.md:7–27`; readiness:L13–29 | Giữ lịch sử TV3 kèm scope/time; bổ sung evidence TV2. TV3 chỉ ghi VERIFIED sau khi trực tiếp đọc artifact. |
| 3. A06 Q01–Q03 | PENDING | Có runner/fixtures và marginal tables, không có production IT tables hoặc category×experience×location. | analyzer:L140–148,206–216; schema:L8–11 | PENDING production; joint aggregate hoặc upstream tính từ job-level đã nghiệm thu mới hỗ trợ giao filter. |
| 3. A06 Q04 remote | PENDING | Employment/remote tách đúng. Code remote mới share_all_it; chưa xuất R, n_true/R, n_false/R, R/B. | analyzer:L217–224; schema:L13–14; V03:L198–207 | Giữ thiết kế conditional rates; bổ sung summary/output trong implementation, không coi đã có. |
| 3. A07 Q06 denominator | OK | Thành công gồm WITH_MATCH + NO_MATCH; SOURCE_MISSING/FAILED/PARTIAL ngoài mẫu số. Bridge dedup và khớp skills trong processing; có global coverage/status/zero-hit. | analyzer:L20,151–203; V03:L241–249; readiness:L57–63 | D=countDistinct hai trạng thái thành công; coverage=D/B; không lấy bridge/evidence rows làm denominator. |
| 3. A07 summaries | PENDING | by_group/by_experience là hai marginal. Nhóm chỉ zero-skill không có skill detail row; D_g summary đầy đủ/coverage nhóm chưa là table độc lập. | analyzer:L190–203; schema:L17–18; V03:L243 | Xuất processing summary mọi nhóm kể cả D_g=0/zero-skill-only; không suy từ positive rows. |
| 3. A08 Q07 population/schema | PENDING | V03 min/max riêng đúng. Code bắt cả hai >0, finite, max≥min, đủ units/source; chung salary_n, chưa n_min/n_max/B_g/IQR output. | analyzer:L242–266; schema:L19; V03:L264–277 | TV1 chốt validity; TV2 làm tập riêng từng chỉ số hoặc ghi rõ paired subset được duyệt. Không đổi tên salary_n để giả đáp ứng. |
| 3. Q07 source/quantile | PENDING | Code thêm salary_source vào grain, percentile_approx accuracy=10000, ngưỡng 5 candidate. V03 cần khóa source key hoặc selection policy. | analyzer:L262–265; `config/tv2_analysis_inputs.example.json:14–23`; V03:L266–277 | Chọn authoritative source hoặc giữ source dimension; không pool median nguồn. Duyệt tolerance/precision/ngưỡng mẫu nhỏ. |
| 4. Q05 runner | OK | Có nhánh Q05 trong analyzer và CLI. Projection embedded job_functions có candidate, chưa tích hợp official. | analyzer:L225–237,314–315; `src/d05_job_functions_adapter.py:4–35` | Ghi có runner/fixtures; production vẫn PENDING bridge/projection được xác nhận và D06. |
| 4. Q08 runner | OK | Có original/listed tách riêng, month/week_start_utc, distinct job_id, CLI đặt UTC. Không phải chưa có runner. | analyzer:L123–137,267–278,307–309 | Giữ semantics; category/time summaries/window/partial periods còn thiếu. |
| 4. Q05/Q08 owners | PENDING | Owners trong V03 mới PROPOSED; chưa có assignment chính thức kiểm chứng. | V03:L215,284,409,414; `docs/tv2_q01_q08_publication_plan.md` | Đề nghị TV1 source/grain/UTC/manifest, TV2 analytics Q05/Q08, TV3 UI/consumer; nhóm xác nhận. |
| 5. Overview filters | PENDING | Không dựng giao category×experience×location từ marginal counts. | analyzer:L212–224; V03:L321–325,340 | Disable/ẩn filter chéo tới khi có output đúng context và summaries. |
| 5. Skills/Time category | PENDING | Q05/Q08 hiện toàn scope; Q06 có group nhưng thiếu summary đầy đủ. Top-k không đổi mẫu số. | analyzer:L192–203,235–237,267–278; V03:L326–331 | Khóa capability theo actual table/run; không suy từ sample UI. |
| 5. Salary filter | PENDING | Grain code category×experience×currency×pay_period×compensation_type×source đủ hướng so sánh hàng, nhưng chưa output/B_g/ALL pooled. | analyzer:L262–266; V03:L332–340 | Chọn bộ units/source đúng, giữ thiếu trong B_g; không median-of-medians. |
| 5. Rate encoding | CẦN SỬA | V03 rate=100*n/d; share_* code=n/d (0–1). Chưa có physical→logical mapping rõ. | V03:L71–75; analyzer:L119–120,148,193,200,220,235,277 | Ghi share_* là fraction; UI format % đúng một lần. Field percent mới cần version/schema riêng. |
| 5. NULL/JOIN/zero | OK | Giữ NULL; d=0→NULL; missing file không là 0; bridge riêng, orphan audit, không dùng exploded rows tính lương. | V03:L68–77,369–381; analyzer:L105–111,155–187,231–250 | Chốt nguyên tắc; validation production chờ run thực. |

## A02/A03/A05: artifact và phiên bản

A01 `docs/a01_analysis_questions.md` exact hash khớp V03. A01 là requirements; trạng thái môi trường/output ngày 08/10 là lịch sử, không thay readiness 19/10.

A02 có `docs/a02_it_taxonomy.md`, active `config/it_taxonomy.json` v0.2.0 và snapshots 0.1.0/0.2.0/0.2.1/0.2.2. Hồ sơ A04 mới: `docs/a04_filter_fix_round2_report.md`, `docs/a04_final_report.md`, `docs/a04_handoff_tv1.md`, `data/analytics/a04_taxonomy_v0_2_2_20261014/run_manifest.json`, `data/audit/tv2_a04_lineage_for_a05_20261019.json`. Candidate v0.2.2 SHA `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874`; active v0.2.0 SHA `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d`. D06 thực dùng version nào: **PENDING TV1**, không suy từ config active hoặc tên ZIP handoff. Mẫu phát triển 176 job duy nhất/177 dòng nguồn không là Full population; REVIEW không là REJECT/FN.

A03 `docs/a03_skills_industries_report.md`; raw mappings `data/raw/mappings/skills.csv` (35 mã), `data/raw/mappings/industries.csv` (422 mã, 34 tên thiếu); bridges `data/raw/jobs/job_skills.csv`, `data/raw/jobs/job_industries.csv`. Không có semver A03 riêng đã chốt: dùng checksum/snapshot. Không lấy raw làm clean official. D05 `job_functions` là array<struct<skill_abr:string,skill_name:string,mapping_status:string>>; adapter candidate `src/d05_job_functions_adapter.py:4–35` kiểm schema/unique selected IDs/FK/status/mapping conflict và dedup pairs, chưa được CLI official dùng.

A05 phát triển `docs/a05_skill_extraction.md` có mô tả runtime cũ; bản cập nhật là `docs/a05_spark_parity_20261019.md`, `docs/a05_official_readiness_20261019.md`. Stable dictionary v0.1.2 gồm 46 mã; `config/tech_skills.json` bằng bytes `config/versions/tech_skills_v0.1.2.json`, SHA `f571ff4525cf629041a6c4791646eebff4f88ca7fa91a978379741f393afa7aa`. Code `src/tech_skill_extractor.py`, Spark `src/a05_spark.py`, official `src/run_a05_official.py` + `src/run_a05_official_local.ps1`; pinned release `config/a05_release_v0.1.2.json`.

Candidate `src/a05_recommendation_candidate.py` / `a05-context-recommendations-0.1.0` là audit evidence, chưa tích hợp extractor/Spark. Không áp 146 đề xuất hoặc gọi 287 audit pairs là bridge mới. Stable còn giới hạn React Native/package, Azure DevOps, ROLE-only→TASK; xem readiness:L5–9. Không promote bằng 18 audit fixtures.

A06/A07/A08 implementation cùng analyzer, config input example và schema candidate. Tests hiện có `src/test_a05_a11_integration.py`, `src/test_a05_projection_runtime.py`, `src/test_tv2_readiness.py`, official runner tests `src/test_a05_official_readiness.py`. Việc file test tồn tại không chứng minh execution PASS.

## Truy vết Q01–Q08 tới code/schema/output

Tất cả tám câu **PENDING production**. Tên sau có thật trong code; CLI dự định ghi `<name>.parquet` và `<name>.csv` (analyzer:L326–337). Chưa có các bảng IT production này trên máy. Dtype dưới đây từ code/schema candidate, không giả coi đã đọc physical schema của output IT. countDistinct là bigint; denominator F.lit Python integer có thể int/long, chưa khóa width. share_* là fraction; NULL khi denominator=0 theo biểu thức.

| Q | Tên code thực | Grain, fields, datatype, công thức | Gap/filter thực tế |
| --- | --- | --- | --- |
| Q01 | q01_role_groups | category:string? từ primary_group_code→a02_group; job_count:bigint; denominator_all_it=N; denominator_known; share_all_it=n/N; share_known=n/known. Một dòng/category gồm NULL. | Marginal; chưa joint filters; taxonomy provenance chờ D06. IT_OTHER khác unknown. |
| Q02 | q02_experience | Cùng categorical schema; category là trimmed source experience; N/known riêng; NULL row share_known=NULL. | Không suy số năm, chưa alias normalization được duyệt hoặc joint context. |
| Q03 | q03_location | category trimmed source location; denominator_known=L; share_known=n/L; coverage L/N trong metadata; vẫn giữ missing row. | Top-k không đổi L; chưa parse geography được duyệt. |
| Q04 | q04_work_type; q04_remote_flag; q04_work_type_crosscheck | Employment categorical; remote_allowed:boolean? × job_count, denominator_all_it, share_all_it=n/N; crosscheck hai string? work-type labels × count. | Chưa R/conditional rates/coverage; raw mapping check chưa là alias policy. |
| Q05 | q05_functional_labels; q05_unmapped_labels | skill_abr/skill_name:string × job_count; labeled_n=K; share_of_labeled_jobs=n/K. Unmapped skill_abr:string? × count. K=distinct tin có mapping name dùng được; coverage K/N metadata. | Pair dedup rồi join map unique; chưa category, B−K table hoặc orphan summary độc lập; CLI cần clean bridge/map. |
| Q06 | q06_skills_global; q06_skills_by_group; q06_skills_by_experience | skill_code/name:string × job_count; processed_n=D; share_of_processed=n/D. Detail group/experience thêm dimension:string?, processed_n=D_g, share_of_processed_group=n/D_g. | Group và experience riêng, không joint. Metadata global có zero_hit_jobs/status counts/coverage; chưa summary mọi nhóm. |
| Q07 | q07_salary_separate_units | a02_group/experience:string? × currency/pay_period/compensation_type/salary_source:string. salary_n:bigint; min_salary_q1_median_q3 và max_salary_q1_median_q3:array<numeric>; adequate_sample:boolean. percentile_approx([.25,.5,.75],10000). | Cùng paired bundle population; chưa n_min/n_max/B_g/IQR fields hoặc ALL aggregate. Numeric precision chưa physical-verified; code require NumericType. |
| Q08 | q08_original_month; q08_original_week_start_utc; q08_listed_month; q08_listed_week_start_utc | period:string yyyy-MM hoặc yyyy-MM-dd Monday UTC week start; job_count:bigint; valid_timestamp_n=V_basis; share_of_valid=n/V_basis. | Hai TimestampType inputs/basis độc lập; chưa category, minmax/window/partial/missing-invalid summary. Week-start date phân biệt qua năm, chưa ISO week-year/week số riêng. |

Q01–Q04 code tại analyzer:L140–148,206–224; Q05:L225–237; Q06:L151–203; Q07:L242–266; Q08:L267–278. Schema candidate:L8–20 đối chiếu các tên trên.

Input D06 code yêu cầu job_id bigint unique/non-null; description string; it_decision string=ACCEPT; is_it boolean=true; taxonomy_version/hash và group string. Đây là yêu cầu validator TV2, chưa chứng minh schema Full TV1 đã giao. Structured inputs được kiểm dtype khi dùng. Nhánh salary độc lập bridge/explode.

Q06: SUCCESS_STATES=(PROCESSED_WITH_MATCH, PROCESSED_NO_MATCH). SOURCE_MISSING/FAILED/PARTIAL ngoài D; báo riêng source statuses/coverage. `source_status` là tên cột thực, không phải `status`. Processing có một job_id/source_field cho mọi tin, bridge unique job_id/skill_code; kiểm bridge khớp technical_skills successful. Nhóm chỉ zero-hit không có detail skill row, nên chưa dùng detail thay D_g summary.

A05 source binding: D05.description là clean text; source_description là raw parsed text. A05 ghi source_field=postings.description và raw codepoint evidence, nên receipt phải chứng minh text dùng đúng source_description/hash theo job_id. Không dùng clean description/title/skills_desc thay âm thầm. Chỉ accepted=true evidence vào bridge; drill-down evidence không làm tăng số tin.

Q07 code hiện dùng min/max cùng >0, finite, max≥min và đủ currency/pay_period/compensation_type/source. Vì vậy salary_n là giao hai tập, không phải n_min/n_max riêng toàn population. Không đổi tên salary_n hai lần rồi tuyên bố đáp ứng V03. IQR mỗi chỉ số=P75−P25 trong đúng cell; không max_salary−min_salary hoặc extrema giữa hàng. B_g phải lấy toàn D06 theo nhóm/experience gồm thiếu lương/units, không suy từ valid salary table. Ngưỡng minimum_salary_group_n=5 và approximate accuracy=10000 chưa là policy đã duyệt. Cần source selection hoặc source dimension/key rõ; không pool quantiles nguồn/hàng bằng median-of-medians.

## Output thực có so với tên đề xuất

| Loại | Tên/đường dẫn | Thực trạng |
| --- | --- | --- |
| D05 data thực | data/processed/jobs/; data/processed/canonical/jobs/ | Mỗi bộ 4 part Snappy Parquet + _SUCCESS; không phải it_jobs. Hash hiện tại cả hai bộ khớp receipt. Readback lưu: 123849 rows/distinct, 50 columns, 0 null ID, d05-v1. |
| A05 development data thực | data/analytics/a05_development_v0_1_2_20261014/job_skill_technical.csv; run_manifest.json cùng thư mục | Development, không official IT. Các bản v0.1.0/v0.1.1 cũ cũng còn, không dùng lẫn version. |
| A05 parity data thực | data/analytics/a05_spark_parity_20261019/run02/{job_skill_technical,technical_skill_evidence,skill_source_processing}.parquet và .jsonl; parity_manifest.json | Đã kiểm kê đường dẫn. Manifest PASS_DEVELOPMENT_LOCAL_WORKER_PARITY: 355 bridge/661 evidence/105 processing; 78 WITH_MATCH + 27 NO_MATCH. Không production. |
| Hồ sơ A06–A11 thực | data/analytics/tv2_a06_a11_prepared_20261019/manifest.json; reports/publication_manifest.json; reports/a09_insights.md, a10_analysis_report.md, a11_slides.html | BLOCKED_DEPENDENCY, tables={}, spark_executed=false. run_kind=OFFICIAL là ý định, không SUCCESS. Bộ tv2_a05_a11_followup01 cũng blocked. |
| Tên code chuẩn bị xuất | Các q01_*…q08_* trong bảng truy vết | Không tìm thấy file bảng q01…q08 trong data/analytics. Không giao như production output. |
| Logical aliases V03 | Q01_CATEGORY_DISTRIBUTION/POPULATION_SUMMARY; Q02_EXPERIENCE_DISTRIBUTION/EXPERIENCE_COVERAGE_SUMMARY; Q03_LOCATION_DISTRIBUTION/LOCATION_COVERAGE_SUMMARY; Q04_EMPLOYMENT_DISTRIBUTION/Q04_REMOTE_DISTRIBUTION/Q04_COVERAGE_SUMMARY; Q05_JOB_FUNCTION_DISTRIBUTION/JOB_FUNCTION_COVERAGE_SUMMARY; Q06_TECHNICAL_SKILL_DISTRIBUTION/DESCRIPTION_PROCESSING_SUMMARY; Q07_SALARY_QUANTILES/SALARY_POPULATION_COVERAGE_SUMMARY; Q08_TIME_DISTRIBUTION/TIMESTAMP_COVERAGE_SUMMARY; RAW_CLEAN_AUDIT_PROFILE/IT_ACCEPTED_QUALITY_PROFILE | Tất cả PROPOSED, không phải filenames/physical schemas đã giao (V03:L18,110–313). |
| Scaffold cũ | overview_analytics; skills_analytics; salary_quality_analytics; data_contract_v03.md | V03:L424–431 tự supersede hoặc ghi tên dự kiến; không coi final và không sửa sample để ép khớp. |

## D05, D06 Full, D07 và A05 official

**D05:** Evidence tiếp nhận có giới hạn. Commit TV1 `457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b`; schema/manifest snapshot ở `tmp/tv2_d05_receipt_457f90ae/tv1_snapshot/data/audit/d05_canonical_schema.json` và `d05_official_run_manifest.json`. Audit `data/audit/tv2_d05_receipt_457f90ae.json`, xác nhận cuối `tv2_d05_final_457f90ae.json`, báo cáo `docs/tv2_d05_receipt_457f90ae.md:7–27`. Run TV1 ghi READY FOR ACCEPTANCE REVIEW/PENDING GROUP REVIEW; việc người dùng xác nhận thư mục bàn giao không thay group acceptance. Manifest TV1 thiếu hash parts: hash local chứng minh bytes receipt/copy không đổi, chưa chứng minh exact bytes run TV1 bằng manifest gốc. Không tái chạy ETL/readback Spark trong review.

**D06 Full:** PENDING TV1. Kiểm kê data/processed có 11 file (hai bộ D05 + .gitkeep), không it_jobs; data/receipts không tồn tại. Tìm docs/data/tmp/config gồm ignored files thấy checklist/template/receiving preflight, không Full được xác nhận. `tmp/a05_official_readiness_20261019/dependency_inventory.json` cũng BLOCKED_DEPENDENCY. Không có T/N IT hoặc taxonomy D06 thực dùng đã xác minh. Runner/parity/pilot/preflight D06 PASS ở V03 vẫn TEAM REPORTED, không suy Full PASS.

**D07:** PENDING TV1. Không tìm thấy salary_clean hay manifest/báo cáo bàn giao D07 thực ở local. 36059 USABLE + 87776 MISSING + 14 INVALID trong V03 là TEAM REPORTED ALL JOBS, chưa xác minh run/schema/source/validity, không phải numerator IT. D05 salary_record hoặc decimal cast D04 không thay D07. TV1 cần giao actual path/schema/dtypes/units/source-bundle policy/reasons/coverage/hash/run/acceptance.

**A05 official:** PENDING D06 Full + source contract + official execution/readback. Runner chặn receipt trước Spark/output (src/run_a05_official.py:L47–62), pin stable rồi ghi/readback ba bảng, chỉ SUCCESS khi qua checks (:66–99). Chưa có official run. A05 riêng không phụ thuộc D07 hoặc xác nhận job_functions: receipt purpose='a05' bỏ gate Q05, readiness:L17. Không cần chờ D07 mới mở A05. “Chưa Spark”/BLOCKED_RUNTIME của hồ sơ cũ đã được bổ sung bằng run02 local parity, chưa chứng minh multi-node/addPyFile Windows hoặc nghiệm thu nhãn skill.

Bằng chứng tests lưu: 4 synthetic query fixtures PASS + 1 schema smoke PASS trong hồ sơ D05; regression parity 63 PASS/1 real-D06 SKIP và run02 105 mẫu PASS (`docs/a05_spark_parity_20261019.md:39–52`). Readiness:L45–49 ghi 6 PASS (4 Spark synthetic + 2 receipt unit), 4 receipt regression PASS. Không cộng các scope khác thành suite mới; real-D06 SKIP không là PASS. Không chạy lại tests trong review tài liệu.

## Phân công và điều kiện đóng PENDING

Chưa có assignment chính thức được kiểm chứng. Đề nghị sau đây để nhóm xác nhận, không tự nhận đã chốt:

| Phần | TV1 | TV2 | TV3 | Điều kiện đóng |
| --- | --- | --- | --- | --- |
| Q05 | Clean job_skills/skills hoặc duyệt projection job_functions; checksums/grain/orphan và D06 membership | Valid labels A03; dedup pairs, K/B/counts; category và summaries | Consumer/UI Q05, Top-k/coverage/capability | Source contract/receipt, owner, actual run và checks |
| Q08 | D06/time UTC, source semantics, missing/invalid, snapshot/window | Distinct tuần ISO/tháng mỗi basis, category và coverage/time summaries | Hai basis riêng; week/month, minmax/partial/coverage | Time policy, owner, output đủ grain và evidence |
| Q01–Q04/Q06/Q07 | Population/D07/source đúng run | B/L/R/D/D_g/B_g và joint contexts; quantile/source policy | Chỉ bật capabilities từ output nghiệm thu, không cộng summary lặp | Schema/grain/rate mapping/version/validation và acceptance |

## Nội dung chốt được, nội dung cần chỉnh

Có thể chốt ngay **semantics/design**: đủ Q01–Q08 và phân trang; Q05 source job-function labels khác Q06 technical mentions; Q06 denominator gồm NO_MATCH và coverage riêng; Q07 Q1/median/Q3/IQR min/max riêng, giữ units/source policy; Q08 original chính/listed đối chiếu UTC, distinct job_id; NULL/zero/missing và JOIN đúng grain. Formal sign-off V01:T2-09 vẫn do người phụ trách xác nhận, báo cáo không ký thay.

Cần chỉnh nội dung/mapping: cập nhật evidence TV2 mới và scope/time “chỉ .gitkeep” của checkout TV3; ghi share_* là fraction và đổi sang % một lần; khóa Q07 source selection hoặc dimension/key. Các schema cũ sample_size=mọi tin nhóm, median_salary chung, work_type có Remote đã được V03.1 sửa/supersede, không gán lỗi này cho bản mới.

Code chưa đáp ứng yêu cầu đúng phải ghi PENDING implementation: remote share_all_it không là n_true/R; paired salary_n không là n_min/n_max toàn tập; marginal tables không là joint filters; skill-positive rows không thay D_g summary. Không tự tạo schema để coi đã chốt. Cần TV1 giao D06/D07/bridge, TV2 chạy A05 official và analytics có summary đúng grain, TV3 mapping/validator/consumer sau bàn giao; owners Q05/Q08 do nhóm xác nhận.

## Tin nhắn hoàn chỉnh để gửi TV3

> Mình đã fetch và đọc đúng bản mới nhất nhánh `feat/tv3-dashboard`, commit `ba57c728d56e887c7555e545032e93a762b77801`; file hiện là V03.1 DISCUSSION DRAFT. TV2 xác nhận phạm vi thiết kế ba trang đủ Q01–Q08 và đồng ý nguyên tắc: Q05 là nhãn chức năng mapping; Q06 là kỹ năng được nhắc trong description, denominator gồm PROCESSED_WITH_MATCH + PROCESSED_NO_MATCH, loại SOURCE_MISSING/FAILED/PARTIAL và báo coverage riêng. Q07 min/max có Q1/median/Q3/IQR và n riêng, giữ bộ đơn vị. Q08 original_listed_time chính/listed_time đối chiếu, tuần/tháng UTC và distinct job_id. NULL không thành 0/FALSE, không nhân dòng JOIN, không cộng median/percentage/denominator lặp.
>
> Evidence TV2 mới: D05 canonical đã readback 123849 jobs/50 cột, hiện có 4 part + _SUCCESS tại `data/processed/canonical/jobs/`; đây là ALL JOBS. Taxonomy active local vẫn v0.2.0, A04 candidate bàn giao v0.2.2 chưa tự promote; version D06 thực dùng vẫn PENDING vì chưa Full/receipt. A05 stable v0.1.2 có release hashes và local Spark parity 105 development PASS; candidate context recommendations chưa tích hợp. Không coi parity là production.
>
> Runner `src/a06_a08_spark_analysis.py` đã có Q05 và Q08. Q05 nhận clean bridge/map; projection D05.job_functions mới candidate, chưa nối official. Q08 có hai basis/tháng/week_start_utc, còn thiếu category và time summaries/window/partial periods. Đề nghị TV1 source/grain/UTC/manifest, TV2 analytics Q05/Q08, TV3 UI/consumer; assignment chính thức vẫn cần nhóm xác nhận.
>
> Chưa khóa physical contract/filter: Q01–Q04 đang marginal, chưa category×experience×location; Q06 thiếu summary mọi nhóm zero-skill; Q07 code dùng paired min/max chung salary_n, thêm salary_source trong grain, chưa n_min/n_max/B_g riêng; remote chưa R/conditional rates. Xin giữ yêu cầu đúng của V03 và ghi PENDING implementation. Field share_* TV2 là fraction 0–1, UI chuyển % một lần; Q07 cần khóa source-selection hoặc dimension/key và không pool median nguồn/hàng.
>
> Máy TV2 chưa có D06 Full/D07 salary_clean; A05 official chưa chạy; manifest A06–A08 BLOCKED_DEPENDENCY/tables={}. D07 36059/87776/14 vẫn TEAM REPORTED ALL JOBS, không phải IT. A05 có thể dùng stable sau D06/source binding, không cần chờ D07/job_functions. Các alias Q01_CATEGORY_DISTRIBUTION… trong V03 vẫn proposed, không phải file đã giao. Tên code/output thật, schema candidate, evidence file/dòng và hash nằm trong `docs/a05_dashboard_v03_tv2_review.md`.
>
> Có thể chốt semantics/design có điều kiện; final physical/production giữ PENDING tới khi có outputs/summaries đúng grain, manifests/hash, owner, checks và acceptance. Mình chưa xác nhận V03 PASS hoặc ký thay nghiệm thu nhóm. TV2 đề nghị owners xử lý các dependency/gap trên rồi bàn giao bằng chứng để TV3 khóa contract.

## Phụ lục hash đã kiểm trực tiếp

SHA-256 exact bytes hiện tại; Git blob V03/V01 đúng commit fetch. Không dùng JSON reserialize. Bảng D05 dưới đây kiểm bytes với receipt, không tái chạy Spark.

| Artifact | SHA-256 hiện tại |
| --- | --- |
| `docs/a01_analysis_questions.md` | `30ca76e433492f0aca52cf2c0d05cf178552cb2cc8aeedf4d4f6593bea3b7f22` |
| `docs/a02_it_taxonomy.md` | `cdd53bf1b4dac947be25c2d8496eccb5f46d6f5c103ecc5cafae43c6fcf505e0` |
| `docs/a03_skills_industries_report.md` | `371662d8c8ff06a9d3ce89bfc1427ddca96ec9b3dda19d51b8f26e913034f2e9` |
| `docs/a04_handoff_tv1.md` | `13588744f77862b67eec0f8d04f1950a572a5b54bf0c429afe8719907fb42972` |
| `docs/a04_final_report.md` | `b04b1221a8a024ea246716ef30bd05db530f3bec28c8db36073d2faec812c01c` |
| `docs/a04_filter_fix_round2_report.md` | `2b8057601aa829f21a8c8d9510232333ec053fa6778013bdba183e185266a205` |
| `config/it_taxonomy.json` | `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d` |
| `config/versions/it_taxonomy_v0.2.2.json` | `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874` |
| `config/tech_skills.json` | `f571ff4525cf629041a6c4791646eebff4f88ca7fa91a978379741f393afa7aa` |
| `config/versions/tech_skills_v0.1.2.json` | `f571ff4525cf629041a6c4791646eebff4f88ca7fa91a978379741f393afa7aa` |
| `data/raw/mappings/skills.csv` | `1732c4cb6a8b43696d708caf74fc85bdd45e8527b64163c9a4e7c257c631e1d5` |
| `data/raw/mappings/industries.csv` | `4efdb86cc87a2bb380eb6c3eed95879b287ffc22863a9c1be633a49c0552ecd4` |
| `docs/a05_skill_extraction.md` | `2c1e72d9f7bab4bf081a5900ac6f9eb10698f7894a68131043117a7d7e353e07` |
| `docs/a05_official_readiness_20261019.md` | `0d83348e50a18f74e1d753479d4dffaedc0f9be373a02eac3a4eb53596e82a9c` |
| `config/a05_release_v0.1.2.json` | `949755462c70ecfa16e119290fc3a29a6c02ee9c62928fcf50cdb0f10de822ae` |
| `src/a05_spark.py` | `d010566568f13e391efcd64430ddd45e6175747998f15981eacea3fe80bc22da` |
| `src/tech_skill_extractor.py` | `462b8216981d3e2447f4131d75d378682cff1bd51faabb33be3c7cc23128f52e` |
| `src/run_a05_official.py` | `d20129b7ceda17154c14d98fc7e2c081ba5638f30cfda4aed972de9c0285b1a8` |
| `src/run_a05_official_local.ps1` | `54ca4f3c40e6339a57af1e596a29b95fbe75c291632999e09b75eb69fc2f1773` |
| `src/d05_job_functions_adapter.py` | `7ef749c9321158a8688b0c1d4da5524b3b7887d5b21a08d2e26f496995ace8fa` |
| `src/a06_a08_spark_analysis.py` | `531898d274e72f1aa265f87d4c4cfab54b89d062c4cd754bac0a7c22b5c7aa62` |
| `config/tv2_analysis_output_schema.json` | `65ef96ddaece5cfb1e8e885b997f3f9a362f6d215f1d85279873287c93b25bfc` |
| `data/analytics/a05_spark_parity_20261019/run02/parity_manifest.json` | `639ae302ee045aa87b1b610a7f41c25526ca6586bc1e9724b4b22bc2ef6abe81` |
| `data/analytics/tv2_a06_a11_prepared_20261019/manifest.json` | `077c2aa05c9ab7ba23b1e4b742e4d57a61a9ff2bc2c098c2de0ff5cbc6625b1f` |
| `data/audit/tv2_d05_receipt_457f90ae.json` | `a2303d11837a21545fbfd80496dd2429286ffffd63a33b4b12aa1466f390f9ab` |
| TV3 Git blob `docs/dashboard/dashboard_data_contract_draft.md` | `9ad9df2c9f0f16ee1b00b855c6b0fc19e49f773c8623c57761d051fb31ed6a53` |
| TV3 Git blob `docs/dashboard/dashboard_wireframe.md` | `5b72316970ca8efd004e124a1060f7bc5277ca00f87a81b5a2869c8f3b76e115` |

Kiểm SHA-256 D05 hiện tại với receipt, không khởi chạy Spark:

| File | Nguồn jobs/ | Canonical jobs/ | SHA-256 receipt |
| --- | --- | --- | --- |
| `_SUCCESS` | khớp | khớp | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `part-00000-aa2ea6ea-1536-4b08-95fe-0d515a780603-c000.snappy.parquet` | khớp | khớp | `ba5ac532c16e390ad1c0667735f4f36851c2fe37835b6ed4e797cc0f2490ff7c` |
| `part-00001-aa2ea6ea-1536-4b08-95fe-0d515a780603-c000.snappy.parquet` | khớp | khớp | `0bafd55861113f08de4a5e714a16e26f3aa6b30cc93fbf10e95f575565398a49` |
| `part-00002-aa2ea6ea-1536-4b08-95fe-0d515a780603-c000.snappy.parquet` | khớp | khớp | `71e935e2ff2a29afcc2480bc6a40cf69f6863a5212cf7eee8400c4a0d5a68420` |
| `part-00003-aa2ea6ea-1536-4b08-95fe-0d515a780603-c000.snappy.parquet` | khớp | khớp | `0a5fca3885193beec1ec1603de4e2e9ef3d4b4b65e75ca512b836dbb92f9d46a` |

Pinned release v0.1.2: tất cả 4 file và parity_manifest SHA khớp release manifest. D05 cả 5 file mỗi bộ khớp receipt. Đây là kiểm bytes, không tái chạy ETL/production hoặc tính accuracy.
