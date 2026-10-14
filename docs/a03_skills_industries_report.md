# A03 – Khảo sát skills và industries, bản đồ JOIN và nguồn kỹ năng

- Người thực hiện: **Đồng Viết Dũng – TV2**; ngày khảo sát ban đầu: **07/10/2026**; cập nhật raw: **08/10/2026**.
- Nhánh: `feat/tv2-analysis`; phiên bản mã nguồn tham chiếu: `2386394`.
- Đầu ra: bản đồ JOIN, khảo sát đủ 35 nhãn nguồn và quyết định nguồn kỹ năng; cập nhật từ raw thật. Lượt 08/10 chuẩn bị A04 ở artifact riêng; **không làm A05–A11 hoặc pipeline D05/D06 production**.
- Mức kiểm chứng: **đã đọc trực tiếp cả 11 CSV raw** và đối chiếu audit D03–D05; chưa có/đọc lại Parquet D04.

## 1. Phạm vi, tình trạng dữ liệu và nguồn kiểm chứng

Đã đọc [README](../README.md), [manifest](data_manifest.md), [A01](a01_analysis_questions.md), [A02](a02_it_taxonomy.md), [taxonomy v0.1.0](../config/it_taxonomy.json), dictionary, D03–D05 và các script liên quan. Khi bắt đầu, nhánh đã là `feat/tv2-analysis`; A01, A02 và JSON taxonomy đang là thay đổi chưa commit, được giữ nguyên.

Ngày 08/10/2026 đã bổ sung đủ 11 CSV từ `C:\archive` vào `data/raw/` và đọc bằng `.venv` Python 3.11.9, parser multiline. Nguồn raw mới E09 xác nhận header/số dòng, missing, khóa, mapping, orphan và độ phủ; các số D04/D05 về Parquet vẫn là **bằng chứng lịch sử**, chưa đọc lại. Chưa có Parquet/canonical; Java 21/PySpark 4.2.0/parity còn chờ TV1. **123.849 là tổng tin gốc mọi lĩnh vực**; dự đoán A04 chưa phải tập CNTT đã kiểm chứng.

| Mã bằng chứng | File/tài liệu hiện diện | Nội dung sử dụng |
| --- | --- | --- |
| E01 | [data dictionary](data_dictionary.md), [table inventory](../data/audit/table_inventory.csv), [D03](d03_data_quality_report.md) | Bảng/file, header raw, số dòng và vai trò ứng viên |
| E02 | [key profile](../data/audit/key_profile.csv), [referential profile](../data/audit/referential_profile.csv) | Khóa đơn/ghép, so sánh raw/canonical, matched/unmatched |
| E03 | [D04](d04_cleaning_report.md), [schema changes](../data/audit/d04_schema_changes.csv), [ETL summary](../data/audit/d04_etl_summary.csv), [validation](../data/audit/d04_validation.csv), [post-normalization duplicates](../data/audit/d04_post_normalization_duplicates.csv) | Kiểu sạch, bảo toàn dòng, khử trùng và kiểm tra khóa |
| E04 | [D05 pre-check](d05_precheck.md), [join coverage](../data/audit/d05_precheck_join_coverage.csv) | Độ phủ khóa và số dòng orphan trên dữ liệu sạch đã audit |
| E05 | [35 nhãn skills](../data/audit/d05_precheck_skills.csv), [cardinality](../data/audit/d05_precheck_cardinality.csv) | Mã/tên nhãn đầy đủ và số giá trị trên thực thể |
| E06 | [missing profile](../data/audit/missing_profile.csv) | Mức thiếu của raw, đặc biệt tên ngành và hai trường văn bản |
| E07 | [audit_data.py](../src/audit_data.py), [clean_data.py](../src/clean_data.py), [d05_utils.py](../src/d05_utils.py), [D05 validation](../src/d05_prejoin_validation.py), [D05 scaffold](d05_implementation_scaffold.md) | Parser, chuẩn hóa ID, gom bảng cầu, snapshot và guard giữ grain |
| E09 | [kiểm chứng raw TV2](tv2_raw_verification.md), [inventory/hash](../data/audit/tv2_raw_inventory.csv), [keys](../data/audit/tv2_raw_keys.csv), [join hai chiều](../data/audit/tv2_raw_join_coverage.csv), [nhãn/count](../data/audit/tv2_source_labels.csv), [ngành/count](../data/audit/tv2_source_industries.csv), [profiles](../data/audit/tv2_raw_profiles.json) | Đọc trực tiếp raw ngày 08/10, khóa số canonical/trim text cho so sánh; không sửa raw hoặc chạy ETL |
| E08 | [handoff](handoff/project_status.md), [time profile](../data/audit/time_profile.csv) | Dependency nhóm và đơn vị timestamp dùng cho snapshot |

CSV audit đã đọc bằng `Import-Csv -Encoding UTF8`; trường JSON bên trong đọc bằng `ConvertFrom-Json`. Raw E09 đã được đọc bằng `csv.DictReader(strict=True)`/UTF-8-sig/`newline=""`; phải dùng parser CSV có quote/escape và multiline như E07, không dùng `split(',')`. Môi trường pipeline theo README là Python 3.11, Java 21, PySpark 4.2.0, Spark local/UTC; Lượt cập nhật đã tạo `.venv` Python 3.11.9; không chạy lại ETL hay cài dependency Spark chưa cần dùng.

## 2. Bảng, file nguồn, cột và khóa

Đường dẫn CSV trong bảng đã **hiện diện và được E09 đọc trực tiếp**, khớp inventory D03. Đầu ra D04 được tài liệu mô tả theo mẫu `data/processed/clean/<tên_bảng>/`; ưu tiên đọc các bảng sạch đó khi có dữ liệu. Cột “raw → D04”: số raw đã đếm lại bằng E09, số D04 vẫn từ E03 lịch sử, chưa đọc lại Parquet.

| Bảng | File nguồn trong data/raw | Cột thực tế liên quan hoặc đầy đủ | Khóa và grain | Số dòng raw → D04; ý nghĩa sử dụng |
| --- | --- | --- | --- | --- |
| postings | `postings.csv` | Các trường cần cho A03: `job_id`, `company_id`, `title`, `description`, `skills_desc`; bảng có 31 cột raw, 35 cột D04 | `job_id` duy nhất, không NULL; một tin | 123.849 → 123.849; tập nền tin tuyển dụng |
| job_skills | `jobs/job_skills.csv` | `job_id`, `skill_abr` | Cặp `(job_id, skill_abr)`; một liên kết tin–nhãn nguồn | 213.768 → 213.768; nhiều nhãn/tin, không phải danh sách công nghệ cụ thể |
| skills | `mappings/skills.csv` | `skill_abr`, `skill_name` | `skill_abr` duy nhất; một mã mapping | 35 → 35; từ điển tên nhãn nguồn |
| job_industries | `jobs/job_industries.csv` | `job_id`, `industry_id` | Cặp `(job_id, industry_id)`; một liên kết tin–ngành | 164.808 → 164.808; ngành được gắn với **tin** |
| industries | `mappings/industries.csv` | `industry_id`, `industry_name` | `industry_id` duy nhất; một mã ngành | 422 → 422; mapping mã ngành, tên có thiếu |
| companies | `companies/companies.csv` | `company_id`, `name`, `description`, `company_size`, `state`, `country`, `city`, `zip_code`, `address`, `url` | `company_id` duy nhất; một doanh nghiệp | 24.473 → 24.473; hồ sơ doanh nghiệp, không thay thế địa điểm/nhiệm vụ của tin |
| company_industries | `companies/company_industries.csv` | `company_id`, `industry` | Cặp `(company_id, industry)`; một thuộc tính ngành/doanh nghiệp | 24.375 → 24.375; ngành gắn với **doanh nghiệp**, không có cột `industry_id` |
| company_specialities | `companies/company_specialities.csv` | `company_id`, `speciality` | Cặp `(company_id, speciality)` sau D04 | 169.387 → 169.367; chuyên môn doanh nghiệp, không tự chứng minh kỹ năng của vị trí |
| employee_counts | `companies/employee_counts.csv` | `company_id`, `employee_count`, `follower_count`, `time_recorded`; D04 thêm `time_recorded_raw` | Cặp `(company_id, time_recorded)` sau D04; một snapshot | 35.787 → 35.665; nhiều snapshot/doanh nghiệp, cần chọn trước JOIN |
| benefits | `jobs/benefits.csv` | `job_id`, `inferred`, `type` | Cặp `(job_id, type)`; một loại benefit/tin | 67.943 → 67.943; bảng phụ nhiều giá trị, không phải kỹ năng |
| salaries | `jobs/salaries.csv` | `salary_id`, `job_id`, `max_salary`, `med_salary`, `min_salary`, `pay_period`, `currency`, `compensation_type` | Cả `salary_id` và `job_id` duy nhất; tối đa một bản ghi/tin trong bản audit | 40.785 → 40.785; nguồn lương riêng, chỉ dùng trên grain một tin |

E02 ghi các khóa ghép JS/JI/company_industries/benefits là duy nhất ở raw. E03 ghi 20 dòng `company_specialities` trùng khóa sau trim bị cách ly và 122 dòng `employee_counts` trùng `(company_id, time_recorded)` bị cách ly; không lấy đánh giá khóa raw thay cho khóa sạch. CSV validation D04 lưu **67 kiểm tra PASS, 0 thất bại**, gồm các khóa sạch nêu trên.

ID số `job_id`, `company_id`, `industry_id` và `salary_id` chuyển sang bigint theo D04; `skill_abr`, `skill_name`, `industry_name`, `industry`, `speciality` vẫn là string. `employee_counts.time_recorded` là timestamp UTC từ epoch **seconds**, bản sao raw giữ riêng. Không ép mã nhãn chữ sang số.

### Ngành của tin và ngành của doanh nghiệp

- `job_industries.industry_id` liên kết tin theo `job_id` và có mapping sang `industries.industry_id` được audit trực tiếp.
- `company_industries.industry` gắn với `company_id`, là string theo schema. E09 xác nhận giá trị là tên ngành, ví dụ `Software Development`, `IT Services and IT Consulting`, `Book and Periodical Publishing`; trường này không chứa cột mã ngành. **Không tự JOIN trường này với industry_id/industry_name**, không cast sang số hoặc đối chiếu tên gần đúng khi chưa có bằng chứng.
- `company_specialities.speciality` là thông tin chuyên môn của doanh nghiệp, không phải kỹ năng được yêu cầu trong từng tin. `companies.description` là mô tả công ty, không dùng thay `postings.description` để trích kỹ năng tuyển dụng.
- E09 đã đọc mapping raw xác nhận `4 → Software Development`, `6 → Technology, Information and Internet`; Parquet mapping chưa có để đọc lại. Không dùng ngành đó hoặc nhãn IT làm bằng chứng duy nhất chọn nghề CNTT.

## 3. Bản đồ JOIN và cardinality

Cardinality dưới đây mô tả quan hệ theo khóa, không phải tích hợp đã chạy trong A03. Với bảng cầu, cardinality tổng quát là 0..n; max quan sát lấy E05 và có thể bao gồm khóa ngoài postings. Khóa ghép là khóa của **bảng cầu**, không phải khóa JOIN với postings.

~~~mermaid
flowchart LR
    P["postings: job_id"] -->|"job_id: 0..n"| JS["job_skills: job_id + skill_abr"]
    JS -->|"skill_abr: n:1 đã audit"| SK["skills: skill_abr"]
    P -->|"job_id: 0..n"| JI["job_industries: job_id + industry_id"]
    JI -->|"industry_id: n:1 đã audit"| IN["industries: industry_id"]
    P -->|"company_id: n:0..1"| C["companies: company_id"]
    C -->|"company_id: 0..n"| CI["company_industries: company_id + industry"]
    C -->|"company_id: 0..n"| CS["company_specialities: company_id + speciality"]
    C -->|"company_id: 0..n, chọn latest"| EC["employee_counts: company_id + time_recorded"]
    P -->|"job_id: 0..n"| B["benefits: job_id + type"]
    P -->|"job_id: 0..1"| SA["salaries: job_id"]
~~~

| Cặp JOIN theo cột thực tế | Cardinality và khóa cần bảo đảm | Orphan / NULL được audit | Nguồn |
| --- | --- | --- | --- |
| `postings.job_id = job_skills.job_id` | Một tin → 0..n nhãn; JS duy nhất trên `(job_id, skill_abr)`, max 3 nhãn/mã tin ở JS | 4.711 job_id orphan, 7.990 dòng JS orphan | E02/E04/E05 |
| `job_skills.skill_abr = skills.skill_abr` | Nhiều liên kết → một mã mapping; SK duy nhất trên skill_abr | 0 mã/dòng orphan; tất cả 35 mã JS ánh xạ được | E02/E04/E05 |
| `postings.job_id = job_industries.job_id` | Một tin → 0..n ngành; JI duy nhất trên `(job_id, industry_id)`, max 3 ngành/mã tin ở JI | 4.712 job_id orphan, 5.845 dòng JI orphan | E02/E04/E05 |
| `job_industries.industry_id = industries.industry_id` | Nhiều liên kết → một mã mapping; IN duy nhất trên industry_id | 0 mã/dòng orphan; 422/422 mã khớp, nhưng 34 tên ngành raw thiếu | E02/E04/E06 |
| `postings.company_id = companies.company_id` | Nhiều tin → 0..1 hồ sơ công ty; companies duy nhất trên company_id | 1.717 tin có company_id NULL; một mã company_id không khớp, xuất hiện trên một dòng postings | E02/E04 |
| `companies.company_id = company_industries.company_id` | Một công ty → 0..n ngành công ty; cặp company_id/industry duy nhất, max 2 giá trị | 0 khóa/dòng orphan | E02/E03/E04/E05 |
| `companies.company_id = company_specialities.company_id` | Một công ty → 0..n chuyên môn; cặp company_id/speciality duy nhất sau D04, max 84 giá trị | 0 khóa/dòng orphan; D04 cách ly 20 dòng trùng | E03/E04/E05 |
| `companies.company_id = employee_counts.company_id` | Một công ty → nhiều snapshot; cặp company_id/time_recorded duy nhất sau D04; chọn một snapshot trước JOIN | 0 khóa/dòng orphan; D04 cách ly 122 dòng trùng; D05 báo cáo max 13 snapshot/công ty | E03/E04/E08 |
| `postings.job_id = benefits.job_id` | Một tin → 0..n benefit; cặp job_id/type duy nhất, max 12 giá trị | 1.288 job_id orphan, 2.550 dòng benefits orphan | E02/E04/E05 |
| `postings.job_id = salaries.job_id` | Một tin → 0..1 bản ghi; salaries.job_id duy nhất | 4.712 job_id và 4.712 dòng salaries orphan | E02/E03/E04 |

**Cảnh báo JOIN raw company_id:** E02 ghi `companies → postings` có **0 khóa khớp khi so sánh chuỗi raw nguyên dạng**, nhưng **24.473/24.474 khóa khớp khi NUMERIC_CANONICAL**. D04 chuẩn hóa định danh số nguyên, bao gồm cú pháp `123.0 → 123`, sang bigint. Vì vậy phải dùng bảng sạch/đúng quy tắc D04; không JOIN chuỗi raw trực tiếp, không chuyển qua float rồi làm mất chính xác ID. Đây là quy tắc kiểu dữ liệu, không phải tự sửa khóa nguồn.

### Mức nhiều giá trị đã quan sát

| Bảng con sạch đã audit | Khóa thực thể | Dòng | Thực thể distinct | Max giá trị/thực thể | Thực thể có >1 giá trị |
| --- | --- | --- | --- | --- | --- |
| job_skills | `job_id` | 213.768 | 126.807 | 3 | 71.658 |
| job_industries | `job_id` | 164.808 | 127.125 | 3 | 24.406 |
| benefits | `job_id` | 67.943 | 30.023 | 12 | 16.101 |
| company_specialities | `company_id` | 169.367 | 17.780 | 84 | 16.970 |
| company_industries | `company_id` | 24.375 | 24.365 | 2 | 10 |

Các số E05 này thuộc **toàn bảng con**, không phải riêng tin có trong postings hoặc riêng CNTT. Không nhân các max rồi tuyên bố đã quan sát một tin có đồng thời tất cả giá trị cực đại.

## 4. Khảo sát đủ 35 nhãn skills

### Nội dung quan sát trực tiếp

Bảng sau đã đối chiếu trực tiếp toàn bộ `data/raw/mappings/skills.csv` với `d05_precheck_skills.csv`: cùng đủ 35 mã/tên, theo hai cột nguyên gốc. Có **35 dòng, 35 skill_abr duy nhất**; E06 ghi skill_abr/skill_name không thiếu. E04 ghi JS tham chiếu đủ 35 mã và tất cả mã đều khớp SK. Số tin theo từng mã trên raw postings đã tính ở E09; chưa có số trên tập CNTT được xác nhận.

| skill_abr | skill_name quan sát được |
| --- | --- |
| `ACCT` | Accounting/Auditing |
| `ADM` | Administrative |
| `ADVR` | Advertising |
| `ANLS` | Analyst |
| `ART` | Art/Creative |
| `BD` | Business Development |
| `CNSL` | Consulting |
| `CUST` | Customer Service |
| `DIST` | Distribution |
| `DSGN` | Design |
| `EDU` | Education |
| `ENG` | Engineering |
| `FIN` | Finance |
| `GENB` | General Business |
| `HCPR` | Health Care Provider |
| `HR` | Human Resources |
| `IT` | Information Technology |
| `LGL` | Legal |
| `MGMT` | Management |
| `MNFC` | Manufacturing |
| `MRKT` | Marketing |
| `OTHR` | Other |
| `PR` | Public Relations |
| `PRCH` | Purchasing |
| `PRDM` | Product Management |
| `PRJM` | Project Management |
| `PROD` | Production |
| `QA` | Quality Assurance |
| `RSCH` | Research |
| `SALE` | Sales |
| `SCI` | Science |
| `STRA` | Strategy/Planning |
| `SUPL` | Supply Chain |
| `TRNG` | Training |
| `WRT` | Writing/Editing |

**Không có skill_name bằng Python, Java hoặc SQL** trong 35 giá trị này. Danh sách đầy đủ trên cũng không chứa các tên công nghệ cụ thể như Spark/Docker/AWS. Đây là kết luận về **từ điển nhãn gốc**, không phải kết luận dataset không nhắc công nghệ trong mô tả.

### Diễn giải nghiệp vụ và quyết định sử dụng

- Quan sát: các tên Accounting/Auditing, Administrative, Engineering, Information Technology, Sales, Quality Assurance... là nhãn rộng. File không chứa định nghĩa chuyên môn, độ thành thạo, từ khóa lập trình hay bằng chứng văn bản cho từng tin.
- Diễn giải từ tên và tài liệu D05: các giá trị **mang dạng chức năng/lĩnh vực công việc**, phù hợp lưu như “nhãn chức năng nguồn”. Đây là cách dùng nghiệp vụ của dự án; chưa có tài liệu gốc xác nhận chính thức mọi định nghĩa của hệ thống nhãn LinkedIn hoặc cách nhãn được gán.
- Không đồng nhất `ENG` với Software, `ANLS` với Data/AI, `QA` với kiểm thử phần mềm, `IT` với tất cả tin CNTT. Không suy một nhãn cụ thể là kỹ năng bắt buộc.
- Giữ `skill_abr` và `skill_name` nguyên nghĩa nguồn, không đổi thành Python/SQL hoặc gom trực tiếp vào taxonomy A02. Dùng riêng cho câu hỏi A01 Q05; kỹ năng công nghệ Q06 phải từ A05.
- E09 đã đếm distinct postings theo skill_abr ở `tv2_source_labels.csv`, gồm IT/ENG/QA; đây là count trên toàn raw và đã loại orphan khỏi mẫu số tin. Chưa công bố phân bố trên tập CNTT được xác nhận hoặc đồng nhất nhãn chức năng với nhóm nghề.
- Taxonomy A02 v0.1.0 vẫn có `metadata_policy.enabled_for_decision=false`; A03 giữ nguyên cấu hình. Không coi riêng source label/ngành là bằng chứng nghề CNTT.

## 5. Độ phủ hai hướng: công thức, mẫu số và điều kiện hợp lệ

Gọi **P** là tập `job_id` duy nhất trong postings sạch; **|P| = 123.849** theo E03. Với bảng con C gắn job_id, gọi **K(C)** là tập job_id không NULL distinct ở bảng con.

- **Khóa bảng con khớp postings:** `100 × |K(C) ∩ P| / |K(C)|`. Mẫu số là khóa distinct **bảng con**, có thể bao gồm orphan.
- **Tin trong postings có ít nhất một liên kết:** `100 × |P ∩ K(C)| / |P|`. Mẫu số là **tin gốc**, không phải dòng bảng con hoặc khóa công ty.
- **Tin có nhãn/ngành hợp lệ:** phải thêm điều kiện mapping tồn tại, và nếu yêu cầu tên thì phải kiểm tra tên không thiếu. Mapping khớp theo ID và mapping có tên đầy đủ là hai tiêu chí khác nhau.
- **Dòng bảng con khớp:** `child_non_null_rows - orphan_child_rows`; không dùng số dòng này làm số tin có nhãn.
- Mẫu số 0 khi áp dụng bản dữ liệu khác/tập con thì tỷ lệ để NULL/“Không đủ dữ liệu”, không gán 0 hoặc lấy quy ước mặc định 100%.

### 5.1. Hướng bảng con → bảng cha

Đọc các tử số/mẫu số/orphan từ E04; phần trăm dưới đây **tính lại** với sáu chữ số thập phân. “Khóa” thay đổi theo cột FK; ví dụ companies → postings đang đếm company_id, không đếm job_id.

| Bảng cha → bảng con | Khóa con so sánh | Khóa khớp / khóa con distinct không NULL | Độ phủ khóa con | Khóa orphan / dòng orphan |
| --- | --- | --- | --- | --- |
| companies → postings | `company_id` | 24.473 / 24.474 | 99,995914% | 1 / 1 |
| postings → job_skills | `job_id` | 122.096 / 126.807 | 96,284905% | 4.711 / 7.990 |
| postings → job_industries | `job_id` | 122.413 / 127.125 | 96,293412% | 4.712 / 5.845 |
| postings → benefits | `job_id` | 28.735 / 30.023 | 95,709956% | 1.288 / 2.550 |
| postings → salaries | `job_id` | 36.073 / 40.785 | 88,446733% | 4.712 / 4.712 |
| skills → job_skills | `skill_abr` | 35 / 35 | 100,000000% | 0 / 0 |
| industries → job_industries | `industry_id` | 422 / 422 | 100,000000% | 0 / 0 |
| companies → company_industries | `company_id` | 24.365 / 24.365 | 100,000000% | 0 / 0 |
| companies → company_specialities | `company_id` | 17.780 / 17.780 | 100,000000% | 0 / 0 |
| companies → employee_counts | `company_id` | 24.473 / 24.473 | 100,000000% | 0 / 0 |

Không cộng các số orphan giữa JS/JI/salaries để suy ra tổng job_id orphan chung: có thể trùng khóa giữa các bảng, chưa có dữ liệu giao/union.

### 5.2. Hướng postings → bảng con

Vì postings.job_id duy nhất, `matched_keys` của các quan hệ này chính là số tin postings có ít nhất một liên kết tương ứng. Đây là phép suy ra bằng toán tập hợp từ E02/E03/E04, không phải một lần JOIN mới.

| Bảng con | Điều kiện được số liệu hỗ trợ | Tin có liên kết / tổng postings | Độ phủ tin gốc | Tin không có liên kết tương ứng |
| --- | --- | --- | --- | --- |
| job_skills | Có ít nhất một nhãn source ánh xạ được và có tên (theo điều kiện mapping bên dưới) | 122.096 / 123.849 | 98,584567% | 1.753 |
| job_industries | Có ít nhất một mã ngành ánh xạ được; chưa chứng minh tên không thiếu | 122.413 / 123.849 | 98,840524% | 1.436 |
| benefits | Có ít nhất một bản ghi benefit; không suy là có mọi loại benefit | 28.735 / 123.849 | 23,201641% | 95.114 |
| salaries | Có bản ghi salaries; chưa chứng minh bộ lương đủ điều kiện so sánh | 36.073 / 123.849 | 29,126598% | 87.776 |

Với JS, E04 xác nhận **toàn bộ mã** ánh xạ được và E06/SK không thiếu tên; D04 giữ nguyên 35 dòng và chỉ trim trường này, nên **122.096 tin (98,584567%)** có ít nhất một nhãn nguồn hợp lệ theo mã và tên trong bản audit. **1.753 tin** không có liên kết JS khớp; không suy chúng không có kỹ năng công nghệ.

Với JI, **122.413 tin (98,840524%)** có ít nhất một **mã ngành** ánh xạ được. E06 ghi **34/422 industry_name thiếu (8,056872%)**, tương ứng 388 mapping có tên ở raw. E09 đã đo trực tiếp: **122.313 tin có ít nhất một tên ngành không thiếu**, 100 tin chỉ liên kết tới mã thiếu tên; 4.852 tin mang ngành Software Development. Đó là ngành của tin trên toàn raw, không phải số nghề Software/CNTT. **1.436 tin** không có liên kết JI khớp. Không gọi tỷ lệ mapping 100% là độ đầy đủ tên ngành 100%.

Hai độ phủ JS **96,284905%** (khóa bảng con) và **98,584567%** (tin postings) có tử số cùng 122.096 nhưng mẫu số khác nhau; JI tương tự **96,293412%** và **98,840524%**. Không dùng thay thế cho nhau.

### 5.3. Doanh nghiệp và phạm vi CNTT

E04 ghi `postings.company_id` có 122.132 dòng không NULL, một dòng orphan: **122.131/123.849 tin (98,612827%)** khớp hồ sơ companies. Con số **24.473/24.474 company_id (99,995914%)** là độ phủ khóa công ty trong postings, không phải độ phủ tin có hồ sơ.

Độ phủ companies có liên kết ở chiều ngược, tính từ E03/E04: company_industries **24.365/24.473 (99,558697%)**, company_specialities **17.780/24.473 (72,651493%)**, employee_counts **24.473/24.473 (100%)**. Đây là độ phủ **doanh nghiệp**, không phải độ phủ tin; E09 đã tính độ phủ theo tin ở mục 11; không dùng tỷ lệ theo doanh nghiệp thay tỷ lệ theo postings.

Tất cả số liệu trên là của bản dữ liệu **gốc/sạch chưa lọc CNTT**. Sau D06 và kiểm tra A04 phải tính lại cả hai hướng trên phạm vi đã chọn. N của tập CNTT được xác nhận vẫn chưa có; E09 đã bổ sung giao/union nhãn-ngành và số tin theo từng nhãn/ngành trên raw ở mục 11. Các số ACCEPT ở A04 chỉ là dự đoán. Không suy rộng ra thị trường Việt Nam.

## 6. Cách JOIN giữ một dòng/job_id

Bàn giao nguyên tắc sau cho TV1; chưa thực thi JOIN production trong A03:

1. **Bắt đầu từ postings sạch.** Kiểm tra job_id không NULL/duy nhất; ghi số dòng và distinct job_id nền. Không dùng JS hoặc JI làm bảng nền vì chúng có nhiều dòng và orphan.
2. **Kiểm tra khóa dimension** SK.skill_abr, IN.industry_id, companies.company_id trước JOIN. Nếu không duy nhất phải chặn tích hợp và xử lý tất định, không để mapping tự nhân dòng.
3. **Khử trùng cặp bảng cầu sau chuẩn hóa**: JS(job_id, skill_abr), JI(job_id, industry_id), CI(company_id, industry), CS(company_id, speciality), benefits(job_id, type). D04 đã kiểm tra các cặp này; D05 vẫn đối soát. Nếu phát sinh trùng khác nội dung, ghi audit và quy tắc giữ/cách ly, không dropDuplicates ngẫu nhiên.
4. **Tách orphan theo từng quan hệ** bằng kiểm tra tồn tại/left anti, giữ hàng và reason trong bảng audit/cách ly riêng; không sửa/xóa raw hoặc bảng clean. Phân biệt thiếu FK, FK không khớp postings/company và mã không khớp mapping. Giữ tất cả postings khi thuộc tính phụ thiếu.
5. **Giới hạn bridge hợp lệ theo postings** bằng semi-join hoặc nhánh đã tách orphan; JOIN mapping theo mã đã kiểm chứng. Không nối JS với JI trực tiếp để tạo tích số nhãn × ngành.
6. **Gom theo entity trước LEFT JOIN**: collect_set mã hoặc collect_set struct(code, name, mapping_status), sắp xếp tất định; giữ một dòng/job_id cho JS/JI/benefits. Với ngành có tên NULL, giữ industry_id trong struct; không chỉ collect_set(industry_name) vì NULL bị bỏ và sẽ mất dấu vết mã hợp lệ thiếu tên.
7. **Gom thuộc tính doanh nghiệp riêng theo company_id** rồi ghép với companies. Employee_counts chọn latest theo time_recorded, có tie-break tất định và assert company_id duy nhất; không JOIN mọi snapshot. Latest là snapshot mới nhất trong dataset, không mặc định là quy mô doanh nghiệp tại thời điểm đăng tin. Kiểm tra UTC/seconds theo E08; vấn đề nhãn UTC lệch +7 giờ trong D05 đã ghi ở A01 và vẫn cần TV1 xác minh.
8. **JOIN salaries riêng 0..1 theo job_id** vào bảng nền một tin, alias các cột trùng tên hoặc lưu struct nguồn. Không tự coalesce từng cột P/SA làm trộn nguồn lương; D07 phải chốt ưu tiên/ngữ nghĩa/đơn vị. Không dùng bảng explode/JOIN nhiều kỹ năng/ngành để tính mean, median hoặc phân vị lương.
9. **Giữ trạng thái thiếu/mapping**. Không có bridge row chưa đồng nghĩa không có kỹ năng/ngành thực tế; NULL không phải 0/false. Chỉ dùng [] như quy ước “không có liên kết nguồn hợp lệ trong bản dữ liệu” khi có status và đã hoàn tất kiểm tra, không dùng để biểu diễn trích kỹ năng thất bại.
10. **Đối soát mỗi bước:** số dòng và distinct job_id trước/sau không đổi; assert_unique_key đầu ra chính. Dùng aggregate_bridge, latest_per_key, assert_unique_key, profile_join, check_grain_preserved của E07. Cân bằng dòng bảng con theo matched/orphan/null và đối soát khóa mapping, không chỉ so tổng dòng.

Minh chứng tính được từ E04: LEFT JOIN phẳng postings với JS tạo `(213.768 - 7.990) + (123.849 - 122.096) = 207.531` dòng, khớp số được D05 scaffold lưu; tăng 83.682 dòng so với số tin nền. Đây là phép tính trên audit, **không chạy JOIN ở A03**. Đếm distinct job_id có thể cứu số tin, nhưng không tự sửa được trọng số lương bị nhân dòng.

Có thể giữ JS/JI/technical-skills dưới dạng bảng cầu riêng để phân tích đa nhãn. Khi cần lọc tin theo nhãn/kỹ năng rồi tính lương, semi-join tập job_id distinct vào bảng lương một tin; không tính trên bridge đã explode.

## 7. Quyết định nguồn kỹ năng cho A05

### 7.1. Nguồn được chọn và độ thiếu

**Chọn `postings.description` làm nguồn ứng viên chính** để A05 trích kỹ năng công nghệ; **`postings.skills_desc` chỉ là nguồn bổ sung sau đánh giá**. Giữ nhãn JS/SK nguyên gốc trong namespace riêng. Quyết định nguồn không đồng nghĩa đã trích được Python/SQL hoặc chứng minh mọi công nghệ là yêu cầu bắt buộc.

| Nguồn thực tế | Dữ liệu thiếu raw từ E06 | Phần không thiếu tính được | Quyết định A03 |
| --- | --- | --- | --- |
| postings.description | 7/123.849; 0,005652% | 123.842; 99,994348% | Nguồn ứng viên chính; cần đánh giá ngôn ngữ, boilerplate, ngữ cảnh và độ chính xác ở A05 |
| postings.skills_desc | 121.410/123.849; 98,030666% | 2.439; 1,969334% | Chưa bật mặc định; đánh giá chất lượng và phần bổ sung thực sự trước sử dụng |
| job_skills + skills | 35 mã/tên mapping, không có Python/Java/SQL | Đã có raw count mỗi nhãn trong tv2_source_labels.csv; chưa có count CNTT đã xác nhận | Lưu nhãn chức năng/lĩnh vực nguồn, không dùng thay kỹ năng công nghệ |
| companies.description / company_specialities | Nguồn doanh nghiệp | Chưa đo chất lượng làm nguồn kỹ năng vị trí | Không trích thành kỹ năng yêu cầu của job ở A05 theo hợp đồng A03 |

Các tỷ lệ là của **raw toàn bộ lĩnh vực**. E09 đã tính: 2.439 tin có cả description và skills_desc; không có tin skills_desc bù description thiếu. Chưa đánh giá chất lượng nguồn phụ, trích kỹ năng hoặc tỷ lệ trên tập CNTT đã xác nhận. Không suy ra 2.439 tin đều cung cấp kỹ năng hữu ích.

Danh sách từ kỹ thuật trong taxonomy A02 dùng làm **ngữ cảnh phân loại nghề**, không phải từ điển trích kỹ năng A05 đã được kiểm định. A05 phải chốt dictionary/alias, ranh giới và ngữ cảnh riêng; không tạo nhãn kỹ năng chỉ từ nhóm nghề hoặc tự sao toàn bộ term set A02 thành kết quả.

### 7.2. Hợp đồng xử lý, nguồn và bằng chứng đề xuất

Các tên sau là **đề xuất để TV1/TV2 thống nhất**, chưa là bảng/cột hiện có:

| Đầu ra đề xuất | Grain và nội dung |
| --- | --- |
| job_skill_source_processing | Một hàng `(job_id, source_field)` cho mỗi nguồn được cấu hình trong một lần chạy; lưu run_id, dictionary_version, source_text_sha256, source_status và error_code |
| job_technical_skills | Một hàng `(job_id, technical_skill_code)` trong một run/dictionary version; nhiều kỹ năng/tin, khử trùng cặp; evidence và source_fields giữ đa nguồn nếu cùng kỹ năng |
| technical_skill_evidence | Mỗi hit gắn job_id, technical_skill_code, source_field (postings.description hoặc postings.skills_desc), matched_alias/matched_text, excerpt thật, offsets nếu truy vết được, content hash, rule_id và phiên bản |
| Trường trên bảng một tin | `technical_skills` là mảng gom từ bridge, `skill_source_statuses` là mảng/struct trạng thái từng nguồn; source labels giữ ở job_function_codes/source_function_labels, không ghi đè vào technical_skills |

Chọn một run/dictionary version hiện hành trước khi JOIN; nếu giữ lịch sử thì run_id/version phải tham gia khóa. Evidence excerpt phải từ văn bản thật, không sinh lại nội dung. Offset đề xuất đo trên text nguồn, phải thống nhất đơn vị Unicode/code point với TV1; nếu normalization làm mất ánh xạ thì để offset NULL và giữ excerpt/hash, không bịa vị trí. Khi gom kỹ năng trùng, giữ bằng chứng và mọi nguồn đã đóng góp, không chỉ giữ hit đầu.

### 7.3. Trạng thái để phân biệt thiếu, lỗi và không tìm thấy

| source_status đề xuất | Ý nghĩa | Cách diễn giải kết quả |
| --- | --- | --- |
| NOT_ENABLED | Nguồn chưa được bật, mặc định skills_desc ở thiết kế này | Không coi là thiếu văn bản hoặc đã kiểm tra không có kỹ năng |
| NOT_RUN | Nguồn dự kiến dùng nhưng chưa xử lý | Chưa có kết quả |
| SOURCE_MISSING | Text NULL/rỗng/sentinel; với source_field=postings.description nghĩa là **không có mô tả** | Không thay thành “không có kỹ năng” hoặc 0 |
| FAILED | Có text nhưng parser/trích xuất lỗi | Lưu error_code, có thể retry; không biến thành zero-hit |
| PROCESSED_NO_MATCH | Có text, xử lý thành công, không tìm thấy alias theo phiên bản dictionary | Không có từ khóa được nhận diện; không chứng minh không yêu cầu kỹ năng |
| PROCESSED_WITH_MATCH | Xử lý thành công và có ít nhất một hit hợp lệ | Có kỹ năng được nhắc tới theo quy tắc; không tự suy proficiency/bắt buộc |

Bảng trạng thái phải bao gồm cả tin zero-hit và thất bại, không chỉ lưu tin có kỹ năng. Nếu tất cả nguồn được bật/có text đã xử lý thành công và không có hit thì mảng technical_skills có thể là []; nếu chưa chạy, thiếu text hoặc tất cả xử lý thất bại thì kết quả là NULL kèm trạng thái. Nếu một nguồn thành công có hit nhưng nguồn khác lỗi/chưa chạy, có thể giữ hit đã xác nhận và cờ tổng hợp **PARTIAL**, không trình bày như hoàn tất; nếu phần thành công không có hit thì không gộp thành “đã xử lý không có kỹ năng” khi nguồn khác còn lỗi.

Khi skills_desc được bật sau đánh giá, giữ trạng thái từng nguồn: description thiếu vẫn được ghi là SOURCE_MISSING ngay cả khi nguồn phụ trích thành công. Không coalesce mất nguồn hoặc dùng một mảng rỗng chung cho mọi tình trạng.

Cho A01 Q06, mẫu số cơ sở là distinct tin CNTT có description dùng được và **xử lý thành công**, gồm cả PROCESSED_NO_MATCH; báo thêm độ phủ xử lý so với tổng tin CNTT. Các kết quả nguồn phụ/partial cần mẫu số và độ phủ riêng hoặc quy tắc gộp được ghi rõ. Không lấy chỉ các tin PROCESSED_WITH_MATCH làm mẫu số tỷ lệ phổ biến kỹ năng.

## 8. Bàn giao cụ thể cho TV1 D05/D06 và TV3 V03

### TV1 – D05/D06

| Nội dung | Quyết định/bàn giao A03 | Phần cần TV1 thống nhất hoặc chạy sau |
| --- | --- | --- |
| Nguồn D05 | 11 bảng D04, trọng tâm postings, JS/SK, JI/IN và bảng doanh nghiệp; ưu tiên khóa/kiểu ở mục 2–3 | Đọc lại Parquet, đối soát schema/key/row count và snapshot |
| Khóa và grain | Dùng các cặp JOIN đã audit; gom bridge trước LEFT JOIN hoặc giữ bridge riêng; giữ orphan/audit và tên ngành thiếu | Physical schema, tên bảng orphan và quy tắc lỗi/mapping status |
| Nhãn chức năng nguồn | Giữ code + tên SK; tên job_function_codes đã có trong DataFrame scaffold, có thể giữ để tương thích | Tên canonical và array<struct> source_function_labels là đề xuất, chưa có Parquet production |
| Ngành của tin | industry_ids hiện là alias DataFrame scaffold lấy từ JI; giữ rõ namespace của tin; đề xuất job_industry_labels chứa industry_id và industry_name nullable | Tên/path output và cách lưu mã hợp lệ thiếu tên, không gộp ngành công ty |
| Hồ sơ doanh nghiệp | Gom company_industries/company_specialities; chọn một snapshot latest; alias/struct để không trùng description/name với postings | Kiểm tra giá trị company_industries.industry và UTC, chính sách snapshot khi dùng phân tích lịch sử |
| D06 | Dùng title/description cùng JSON taxonomy A02; source labels/ngành phục vụ metadata/audit, không bật làm bằng chứng duy nhất | Tích hợp với trace/tri-state, kiểm tra parity và mẫu A04; A03 không chạy hoặc sửa taxonomy |
| Kỹ năng A05 | description là ứng viên chính, skills_desc chỉ bổ sung sau đánh giá, source labels giữ riêng | Dictionary, bộ trích, statuses/evidence/run/version; chưa có kết quả công nghệ trong A03 |
| Lương | Giữ một dòng/job_id, nguồn P/SA riêng, không JOIN nhiều nhãn để tính chỉ số | D07 chốt ý nghĩa trường lương, đơn vị và nguồn ưu tiên |

A03 đã cung cấp artifact JOIN/source để TV1 review dependency; **không tự đánh dấu D05/D06 đã chạy hoặc đạt**. Handoff/D05 pre-check ghi “chờ A03” là trạng thái của tài liệu trước khi artifact này được thêm; lượt A03 không sửa các báo cáo đó. TV1 cần xác nhận hợp đồng và dữ liệu hiện diện trước thực thi.

### TV3 – V03

Theo yêu cầu bàn giao V03, các view/bảng dưới đây là **đề xuất**, chưa triển khai dashboard hoặc xác nhận tên output:

- **Nhãn chức năng nguồn:** dùng dimension SK và liên kết JS đã giới hạn theo tập tin mục tiêu; hiển thị mã/tên source label, đếm distinct job_id cho từng nhãn. Không đặt tiêu đề như “Python/SQL phổ biến” cho bảng này.
- **Ngành của tin:** dùng JI + IN; báo theo mã và tên nullable, giữ mục “Thiếu tên ngành” trong trình bày cùng industry_id. Không sửa NULL thành một tên ngành thật và không bỏ tin chỉ vì thiếu tên.
- **Ngành/chuyên môn công ty:** view riêng từ CI/CS theo company_id; chưa gộp với ngành của tin hoặc kỹ năng vị trí. Phân biệt mẫu số số công ty và số tin có công ty.
- **Kỹ năng công nghệ:** chỉ lấy output A05, evidence và trạng thái xử lý; hiển thị chưa có kết quả khi A05 chưa chạy. Tin thiếu mô tả/lỗi xử lý phải tách khỏi zero-hit; mẫu số và độ phủ theo mục 7.
- **Nhóm nghề:** lấy một primary_group_code của A02/D06, giữ Mobile/Web dưới Software; bộ lọc kỹ năng có thể đa nhãn nhưng số tin dùng distinct job_id.
- **Lương theo bộ lọc:** lọc job_id distinct bằng kỹ năng/nhãn/ngành rồi truy vấn bảng nền một tin. Không tính trên view nhiều dòng/tin; tách currency/pay_period/compensation_type theo quy tắc D07.
- **Thông tin truy vết:** mọi bảng tổng hợp cần phiên bản dataset, taxonomy/dictionary, phạm vi raw/CNTT, điều kiện hợp lệ, mẫu số và số tin được xử lý; các tỷ lệ audit gốc không tự trở thành tỷ lệ CNTT.

Cần TV1/TV3 chốt tên/path bảng hoặc view, kiểu mảng/struct, chính sách snapshot/ngành thiếu tên và thời điểm sẵn sàng. Tài liệu này không tuyên bố V03 đã hoàn thành.

## 9. Kiểm tra tmp/a02_validate_taxonomy.ps1

Kiểm tra trực tiếp ở đầu lượt A03: **file không tồn tại**, `git ls-files -- tmp/a02_validate_taxonomy.ps1` không có kết quả và `git check-ignore` xác nhận đường dẫn thuộc `tmp/` bị ignore. Không có bản hiện diện để đọc lại nội dung hoặc hash.

Trong lượt A02, đây là bộ diễn giải kiểm tra **tạm** cho cấu trúc JSON và các ví dụ minh họa; tôi đã dọn file sau kiểm tra ở lượt đó. Kết quả A02 không thay thế validator JVM/Spark hay kiểm thử dữ liệu thật.

**Đề xuất:** nếu nhóm muốn tái lập các kiểm tra cấu hình/ví dụ thường xuyên, khôi phục thành công cụ được quản lý phiên bản trong `src/` (tên đề xuất `src/validate_it_taxonomy.ps1` hoặc validator tương đương), ghi phạm vi config-only và kiểm tra parity. Không dùng file bị ignore trong tmp làm công cụ bàn giao duy nhất. Việc khôi phục/đổi vị trí cần được thống nhất ở bước riêng; **A03 không tạo lại, xóa hoặc di chuyển công cụ nào**. Nếu file được bổ sung sau này, đọc/đánh giá và báo đề xuất trước mọi xóa/di chuyển.

## 10. Phần đã kiểm chứng và phần còn chờ dữ liệu

Kiểm chứng trong lượt A03 ban đầu ngày 07/10/2026 (trước khi bổ sung raw ở mục 11):

- Inventory/header, schema D04 và khóa đơn/ghép đối chiếu E01–E03 cùng TABLE_SPECS/TYPE_RULES trong clean_data.py; toàn bộ 35 nhãn được đọc từ CSV E05, không suy từ tên file.
- Các matched/unmatched/null/orphan của 10 quan hệ E04; kiểm tra cân bằng `distinct_child_keys = matched_keys + unmatched_keys` và `child_total_rows = child_null_rows + child_non_null_rows`.
- Tính lại tỷ lệ hai hướng với mẫu số khác nhau, số tin thiếu liên kết và số dòng JOIN phẳng có thể suy ra từ audit; phân biệt mã ngành ánh xạ được với tên đầy đủ.
- Kiểm tra liên kết nguồn và nội dung bảng 35 nhãn; kiểm tra A01/A02/taxonomy giữ nguyên bằng SHA-256 so với đầu lượt. Không sửa dữ liệu gốc, audit hoặc script pipeline, không commit/push.

Còn chờ Parquet, nhãn tay hoặc xác nhận:

1. Đọc lại schema/key/cast/encoding và cardinality trên đúng bản Parquet D04; raw đã có và được kiểm tra. Chưa tạo canonical production.
2. Định nghĩa chính thức nhãn chức năng, chính sách xử lý mapping thiếu tên và snapshot UTC; dữ liệu raw ngành/nhãn đã đọc đầy đủ và đếm theo postings.
3. Nhãn thủ công A04, phạm vi CNTT đã xác nhận T/N và parity Spark/JVM trước D06; dự đoán chưa thay đánh giá.
4. Chất lượng/ngôn ngữ/boilerplate của description/skills_desc, dictionary/quy tắc A05; chưa trích kỹ năng hoặc tính chỉ số chất lượng bộ lọc.
5. Physical output, statuses/evidence và tên/path canonical/bridge/analytics cho TV1/TV3; semantics lương D07 còn chờ dù bộ giá trị P/SA khớp trên các tin giao nhau.

Kết luận bàn giao A03: **JOIN theo mã/khóa đã audit, gom quan hệ nhiều giá trị trước JOIN, giữ ngành của tin/doanh nghiệp riêng; nguồn kỹ năng công nghệ ứng viên chính là postings.description, nhãn skills gốc được giữ ở namespace riêng.** Các giới hạn kiểm chứng trên đi kèm hợp đồng, không được bỏ khi tích hợp.

## 11. Bổ sung kiểm chứng raw thật ngày 08/10/2026

Nguồn E09: [inventory](../data/audit/tv2_raw_inventory.csv), [keys](../data/audit/tv2_raw_keys.csv), [join hai chiều](../data/audit/tv2_raw_join_coverage.csv), [profiles/derived](../data/audit/tv2_raw_profiles.json), [count 35 nhãn](../data/audit/tv2_source_labels.csv), [count 422 ngành](../data/audit/tv2_source_industries.csv). Các audit cũ được giữ nguyên. Header/số dòng và toàn bộ missing khớp D03; chưa chứng minh cùng release Kaggle vì audit cũ không có hash raw.

Khóa số được chuẩn hóa integral dạng `123`/`123.0` không qua float; chuỗi được trim/sentinel→missing trên bản sao để so sánh. `postings.job_id`, `companies.company_id`, `skills.skill_abr`, `industries.industry_id`, salaries.job_id/salary_id không thiếu và duy nhất. Cặp JS/JI/CI/benefits duy nhất. Sau trim, company_specialities có 20 dòng trùng cặp; employee_counts có 122 dòng trùng `(company_id,time_recorded)`, đúng vấn đề D04 đã ghi. E09 không drop, sửa encoding hay ghi đè dữ liệu; không lấy profile sau trim này làm bằng chứng đã chạy D04.

Các orphan, matched và độ phủ hai chiều ở mục 5 đã được **đo lại từ raw**, khớp số D03/D05 cho các khóa so sánh. Riêng company_specialities và employee_counts tổng dòng raw lần lượt 169.387 và 35.787; số dòng D04 sau cách ly vẫn chỉ là audit lịch sử. JOIN companies–postings cần canonical numeric: raw company_id ở postings có `.0`, không dùng raw string equality để kết luận orphan hàng loạt.

| Bảng con của postings | Matched/distinct khóa con | Orphan khóa/dòng | Postings có liên kết / 123.849 |
| --- | --- | --- | --- |
| job_skills | 122.096 / 126.807 (96,284905%) | 4.711 / 7.990 | 122.096 (98,584567%) |
| job_industries | 122.413 / 127.125 (96,293412%) | 4.712 / 5.845 | 122.413 (98,840524%) |
| benefits | 28.735 / 30.023 (95,709956%) | 1.288 / 2.550 | 28.735 (23,201641%) |
| salaries | 36.073 / 40.785 (88,446733%) | 4.712 / 4.712 | 36.073 (29,126598%) |

35/35 mã skills và 422/422 mã industry trong bridge đều ánh xạ được; 34 tên ngành thiếu vẫn được giữ bằng mã. **122.313/123.849 tin có ít nhất một tên ngành không thiếu**; 100 tin có liên kết JI nhưng mọi tên đều thiếu, 1.436 tin không có JI khớp. Trong raw postings: nhãn IT 25.256 tin, ENG 12.530, ANLS 3.775, QA 1.752; ngành 4 Software Development 4.852 tin, ngành 6 Technology, Information and Internet 1.503 tin. Các bảng đầy đủ E09 đếm distinct job_id mỗi mã; một tin có nhiều mã nên tổng theo mã có thể lớn hơn số tin.

JS và JI cùng phủ 120.874 tin, union phủ 123.635 tin; còn 214 tin không có cả hai liên kết. Không cộng orphan giữa các bảng để suy ra tổng orphan duy nhất. Ngành gắn với công ty đã thấy là tên chuỗi; vẫn chưa tạo phép JOIN CI→industry mapping theo tên hoặc đổi grain ngành công ty thành ngành của job.

Độ phủ **theo tin** khi đối chiếu company_id: companies 122.131 (98,612827%), company_industries 121.974 (98,486060%), company_specialities 96.006 (77,518591%), employee_counts 122.131 (98,612827%). Có 1.717 tin thiếu company_id và 1 tin có khóa không khớp companies. Phân biệt các tỷ lệ này với tỷ lệ **theo doanh nghiệp** ở mục 5.3.

`description` thiếu 7; `skills_desc` có 2.439 tin, tất cả cũng có description. Nguồn phụ không bù được description thiếu trong dataset hiện tại; không suy 2.439 đoạn là kỹ năng hữu ích. Đọc toàn bộ nhãn mapping không có Python/Java/SQL; chưa chạy trích kỹ năng A05.

Các số mục này là **toàn raw, mọi lĩnh vực**. A04 áp dụng JSON bằng [implementation dùng chung](../src/it_taxonomy.py) và tạo mẫu gán nhãn theo [hướng dẫn A04](a04_manual_labeling.md); không tự đánh dấu D05/D06 production hoặc tập CNTT đã đạt. Giữ nguyên JSON/hash và các quy tắc A02 trong lượt này.
