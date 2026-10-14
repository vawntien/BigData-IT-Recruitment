# A01 – Khảo sát thuộc tính phân tích

- Người thực hiện: **Đồng Viết Dũng – TV2**.
- Ngày khảo sát ban đầu: **07/10/2026**; cập nhật bằng raw thật: **08/10/2026**.
- Nhánh làm việc: `feat/tv2-analysis`; phiên bản nguồn khảo sát: `2386394`.
- Đầu ra: **8 câu hỏi và ma trận câu hỏi – trường dữ liệu**. Đây là hợp đồng phân tích cho các bước sau, chưa phải kết quả thống kê tập CNTT.

## 1. Mục tiêu, phạm vi và mức độ kiểm chứng

Xác định câu hỏi về nghề CNTT, cấp kinh nghiệm, địa điểm, loại việc làm, nhãn chức năng/lĩnh vực, kỹ năng công nghệ, lương và thời gian mà schema hiện có hỗ trợ. Mỗi câu hỏi phải có nguồn, cột đầu vào thực tế, cách đo, mẫu số và điều kiện thực hiện.

Phạm vi là các tin trong bộ **LinkedIn Job Postings (2023–2024)** được pipeline xác nhận thuộc CNTT. **123.849 là tổng tin gốc của mọi lĩnh vực**, không phải số tin CNTT. Chưa có tập CNTT hoặc tổng số tin CNTT được xác nhận trong checkout này. Không suy rộng kết quả thành toàn bộ thị trường Việt Nam hay một quốc gia khác; chưa xác nhận phân bố quốc gia để kết luận dataset đại diện cho địa bàn nào.

### Tình trạng dữ liệu sau kiểm chứng ngày 08/10/2026

| Thành phần | Tình trạng kiểm tra trực tiếp | Cách sử dụng trong A01 |
| --- | --- | --- |
| `data/raw/` | Đã có đủ 11 CSV từ `C:\archive`; đọc thành công bằng Python CSV multiline | Header/số bản ghi khớp D03; SHA-256 bản sao bằng nguồn. Nguồn kiểm chứng mới S7 |
| `data/processed/` | Chỉ có `.gitkeep`; không có `clean/` hoặc Parquet D04 | Ưu tiên báo cáo/schema D04 đã lưu; đường dẫn Parquet dưới đây là đầu ra pipeline được tài liệu mô tả, chưa hiện diện tại máy này |
| `data/analytics/` | Có artifact kiểm chứng raw và dự đoán/mẫu A04; chưa có analytics production | Không dùng dự đoán chưa gán nhãn làm tập CNTT được xác nhận |
| `data/audit/` | Có CSV D03, D04 và D05 pre-check | Đã đọc bằng `Import-Csv -Encoding UTF8`, đối chiếu schema, số dòng, khóa, mẫu văn bản, timestamp và mapping |
| Môi trường dự án | Đã tạo `.venv` bằng Python 3.11.9; dùng thư viện chuẩn CSV/JSON. Chưa cài PySpark; Java mặc định là 8 | Kiểm chứng raw và A04 chạy bằng `.venv`; môi trường Spark Java 21/PySpark 4.2.0 và parity JVM còn chờ |

Các kết quả PASS D04/D05 vẫn là **bằng chứng lịch sử**, chưa đọc lại Parquet. Raw hiện tại được đọc lại độc lập bằng S7, bao gồm ví dụ có `job_id` và các trường của cùng tin; không ghép các excerpt audit cũ thành bản ghi giả. Các ví dụ raw chưa là nhãn chuẩn CNTT.

## 2. Nguồn dữ liệu và tài liệu đối chiếu

| Mã | Nguồn trong repo | Nội dung sử dụng |
| --- | --- | --- |
| S1 | [README](../README.md), [manifest](data_manifest.md), [D02](d02_environment_setup.md), [requirements](../requirements.txt) | Phạm vi dataset, thư mục lưu trữ, môi trường Python/Spark |
| S2 | [data dictionary](data_dictionary.md), [D03](d03_data_quality_report.md), [table inventory](../data/audit/table_inventory.csv), [missing profile](../data/audit/missing_profile.csv), [key profile](../data/audit/key_profile.csv), [referential profile](../data/audit/referential_profile.csv) | Tên cột từ header raw, tính duy nhất, dữ liệu thiếu và độ phủ JOIN |
| S3 | [D04](d04_cleaning_report.md), [schema changes](../data/audit/d04_schema_changes.csv), [ETL summary](../data/audit/d04_etl_summary.csv), [validation](../data/audit/d04_validation.csv), [encoding fixes](../data/audit/d04_encoding_fixes.csv) | Kiểu dữ liệu sạch, quy tắc NULL/boolean/timestamp, đối soát đầu ra và mẫu sửa encoding |
| S4 | [D05 pre-check](d05_precheck.md), [35 nhãn mapping](../data/audit/d05_precheck_skills.csv), [cardinality](../data/audit/d05_precheck_cardinality.csv), [join coverage](../data/audit/d05_precheck_join_coverage.csv) | Mapping thực tế, quan hệ nhiều giá trị và bản ghi mồ côi |
| S5 | [time profile](../data/audit/time_profile.csv), [encoding profile](../data/audit/encoding_profile.csv) | Giá trị mẫu được lưu từ raw và đơn vị epoch |
| S7 | [kiểm chứng raw TV2](tv2_raw_verification.md), [inventory mới](../data/audit/tv2_raw_inventory.csv), [missing mới](../data/audit/tv2_raw_missing.csv), [profile mới](../data/audit/tv2_raw_profiles.json), [script](../src/tv2_verify_raw.py) | Đọc trực tiếp 11 CSV, hash/copy, khóa/độ phủ, mẫu và giá trị thực tế ngày 08/10/2026 |
| S6 | [audit script](../src/audit_data.py), [cleaning script](../src/clean_data.py), [smoke test](../src/smoke_test.py), [D05 utils](../src/d05_utils.py), [D05 validation scaffold](../src/d05_prejoin_validation.py), [handoff](handoff/project_status.md) | Cách đọc CSV, chuyển kiểu, giữ grain và các dependency đang chờ |

Không chỉnh sửa `data/raw/`. Lượt 08/10 đã dùng `csv.DictReader(strict=True)`, `encoding="utf-8-sig"`, `newline=""` trong `.venv` để đọc raw. Khi dùng Spark, đọc CSV bằng parser hỗ trợ trường có dấu phẩy, dấu ngoặc kép và xuống dòng: Spark cấu hình `header=true`, `inferSchema=false`, `multiLine=true` cho `postings`/`companies`, `quote='"'`, `escape='"'`, `encoding=UTF-8` như S6; hoặc Python `csv.DictReader` với file mở `encoding='utf-8', newline=''` trong môi trường dự án. **Không dùng `split(',')` hoặc coi mỗi dòng vật lý là một tin.** Các CSV audit ở A01 đã được đọc bằng parser `Import-Csv`; trường JSON lồng bên trong được đọc bằng `ConvertFrom-Json`.

### Tên bảng và đường dẫn nguồn cho ma trận

| Ký hiệu | Bảng | Nguồn CSV gốc | Đầu ra D04 cần ưu tiên khi có dữ liệu |
| --- | --- | --- | --- |
| P | `postings` | `data/raw/postings.csv` | `data/processed/clean/postings/` |
| JS | `job_skills` | `data/raw/jobs/job_skills.csv` | `data/processed/clean/job_skills/` |
| SK | `skills` | `data/raw/mappings/skills.csv` | `data/processed/clean/skills/` |
| JI | `job_industries` | `data/raw/jobs/job_industries.csv` | `data/processed/clean/job_industries/` |
| IN | `industries` | `data/raw/mappings/industries.csv` | `data/processed/clean/industries/` |
| SA | `salaries` | `data/raw/jobs/salaries.csv` | `data/processed/clean/salaries/` |

## 3. Các thuộc tính đã khảo sát

Kiểu raw của các trường dưới đây là `string` theo D03 (`inferSchema=false`). Kiểu sạch đối chiếu từ `d04_schema_changes.csv` và quy tắc trong `clean_data.py`; chưa đọc lại schema Parquet trực tiếp. Các mẫu/giá trị dưới đây cập nhật từ raw S7; kiểu D04 chỉ là hợp đồng lịch sử, không phải schema Parquet đã đọc lại.

| Thuộc tính | Tên bảng/cột thực tế | Kiểu D04 | Ví dụ thực tế và mức kiểm chứng | Ý nghĩa sử dụng / giới hạn |
| --- | --- | --- | --- | --- |
| Mã tin | `postings.job_id`; `job_skills.job_id`; `job_industries.job_id`; `salaries.job_id` | `bigint` | S7 đọc `job_id=921716`; postings có 0 thiếu, 123.849 distinct, 0 trùng | Grain 1 tin; khóa số chuẩn hóa integral không qua float; bảng con có orphan |
| Tên vị trí | `postings.title` | `string` | S7: `921716` → `Marketing Coordinator`; raw còn giữ lỗi encoding đã ghi trong D03 | Giữ title gốc; A02 có taxonomy, A04 mới là dự đoán chờ gán nhãn |
| Mô tả | `postings.description` | `string` | S7, job `921716`: `Job descriptionA leading real estate firm in New Jersey is seeking an administrative Marketing Coordinator...`; mẫu đầy đủ lưu theo job_id | 7 tin thiếu; mô tả nhiều dòng được parser giữ nguyên; excerpt không thay toàn văn để gán nhãn |
| Kinh nghiệm/cấp bậc | `postings.formatted_experience_level` | `string` | S7 thấy `Entry level`, `Mid-Senior level`, `Associate`, `Director`, `Internship`, `Executive`; thiếu 29.409 | Nhãn nguồn không tương đương số năm kinh nghiệm |
| Địa điểm | `postings.location`, `zip_code`, `fips` | `string` | S7: job `921716` → `Princeton, NJ`; còn thấy `United States`, `New York, NY`, `Chicago, IL` | Chuỗi địa điểm tin, chưa parse quốc gia; không thay bằng địa chỉ công ty |
| Loại việc làm | `postings.formatted_work_type`, `work_type` | `string` | S7 kiểm tra 7 cặp, ví dụ `Full-time` ↔ `FULL_TIME`, `Part-time` ↔ `PART_TIME`; chi tiết ở mục 9 | Loại việc làm riêng với cờ remote; không có cột hybrid/onsite được xác nhận |
| Cờ làm từ xa | `postings.remote_allowed` | `boolean` | S7 chỉ thấy raw `1.0`: 15.246 tin; thiếu 108.603 (87,689848%); không thấy `0`, `false` hoặc giá trị khác | D04 map 1.0 thành true; NULL vẫn NULL, không suy onsite/hybrid hoặc 87,69% không remote |
| Văn bản kỹ năng phụ | `postings.skills_desc` | `string` | S7: job `921716` bắt đầu `Requirements:`; 2.439 tin có giá trị, tất cả cũng có description; không bù được 7 description thiếu | Nguồn phụ, chưa đánh giá chất lượng hoặc trích kỹ năng A05 |
| Nhãn gắn với tin | `job_skills.skill_abr`; `skills.skill_abr`, `skill_name` | `string` | Đọc đủ 35 dòng S4: `IT` → `Information Technology`, `ENG` → `Engineering`, `ANLS` → `Analyst`, `QA` → `Quality Assurance` | Giá trị quan sát mang dạng nhãn chức năng/lĩnh vực. Diễn giải nghiệp vụ chính thức chờ A03; không đồng nhất với kỹ năng công nghệ hoặc nhóm nghề CNTT |
| Ngành gắn với tin | `job_industries.industry_id`; `industries.industry_id`, `industry_name` | `industry_id`: `bigint`; tên: `string` | S7 đọc trực tiếp `4` → `Software Development`, `6` → `Technology, Information and Internet`; 34/422 tên thiếu | Mã mapping hợp lệ không bảo đảm có tên; ngành không tự chứng minh nghề CNTT |
| Lương cấu trúc | `postings.min_salary`, `max_salary`, `med_salary`, `normalized_salary`; `salaries.min_salary`, `max_salary`, `med_salary` | `decimal(20,4)` | S7, job `921716`: min=17.0, max=20.0, med thiếu, normalized=38480.0; job `10998357`: min=45000.0, max=65000.0 (YEARLY) | Giá trị raw quan sát, chưa xác nhận semantics normalized/med hoặc quy đổi D07 |
| Tiền tệ, kỳ trả, loại thù lao | `postings.currency`, `pay_period`, `compensation_type`; các cột cùng tên ở `salaries` | `string` | S7, job `921716`: `USD`, `HOURLY`, `BASE_SALARY`; quan sát 6 tiền tệ, 5 kỳ trả (mục 9) | Giữ bộ đơn vị/nguồn và NULL; chưa annualize, quy đổi hoặc trộn cột |
| Thời gian đăng gốc | `postings.original_listed_time`; D04 thêm `original_listed_time_raw` | `timestamp` UTC; bản sao: `string` | S5 có `1713397508000.0` (milliseconds); đổi độc lập được `2024-04-17T23:45:08Z` | Mốc đăng gốc theo tên cột/tài liệu; ưu tiên cho Q08, vẫn cần xác nhận định nghĩa nghiệp vụ nguồn |
| Mốc niêm yết còn lại | `postings.listed_time`; D04 thêm `listed_time_raw` | `timestamp` UTC; bản sao: `string` | S5 cũng có mẫu `1713397508000.0`; phạm vi toàn cột khác `original_listed_time` | Phân tích đối chiếu riêng; không khẳng định là thời điểm đăng lại hoặc thu thập khi chưa có định nghĩa |

### Các bằng chứng ảnh hưởng trực tiếp đến cách đo

- S2/S3: `postings` có **31 cột raw, 35 cột D04** do thêm bản sao bốn timestamp; giữ **123.849 tin gốc**, chưa JOIN hay lọc CNTT. CSV validation D04 lưu **67 kiểm tra PASS, 0 thất bại**.
- S2 ghi tỷ lệ thiếu **trên toàn bộ raw postings**: `description` **0,005652%** (7 tin), `skills_desc` **98,030666%**, `formatted_experience_level` **23,745852%**, `remote_allowed` **87,689848%**, `min_salary`/`max_salary` **75,944093%**, `med_salary` **94,929309%**, `currency`/`pay_period` **70,873402%**. Các tỷ lệ này chỉ là cảnh báo thiết kế; **phải tính lại trên tập CNTT**, không sử dụng làm tỷ lệ CNTT.
- Đọc toàn bộ S4 xác nhận **35 mã và 35 mã duy nhất**; không có `skill_name` bằng **Python, Java hoặc SQL**. Q05 đo các nhãn thực tế; Q06 cần `description` và kết quả A05. Không khẳng định một công nghệ xuất hiện trong tập CNTT trước khi trích và kiểm tra mẫu.
- S4: `job_skills` có **213.768 dòng / 126.807 job_id**, `job_industries` có **164.808 dòng / 127.125 job_id**, tối đa **3 nhãn** và **3 ngành** cho một mã tin trong từng bảng. Các số này tính trên bảng con, bao gồm orphan; không phải số tin CNTT.
- S4: **4.711 job_id** trong `job_skills` và **4.712 job_id** trong `job_industries` không khớp `postings`. `salaries.job_id` duy nhất trên **40.785 dòng**, nhưng chỉ **36.073 job_id** khớp `postings`, còn **4.712** orphan. Không lấy 40.785 làm số tin có lương trong bảng chính hoặc trong tập CNTT.

## 4. Quy ước mẫu số và kiểm soát JOIN

Gọi **T** là tập tin CNTT sau khi TV1 áp dụng bộ lọc đã được TV2 kiểm tra mẫu, mỗi `job_id` không NULL xuất hiện đúng một lần; **N = countDistinct(T.job_id)**. T và N là ký hiệu toán học, không phải tên bảng/cột đã tồn tại. Mọi câu hỏi dưới đây đều cần T; A01 chưa tính N.

- Đếm tin bằng `countDistinct(job_id)`, không đếm dòng sau khi explode/JOIN. Bảng nền cho lương và các thuộc tính đơn trị phải giữ một dòng/tin.
- Khóa đã có bằng chứng S2/S4: `P.job_id = JS.job_id = JI.job_id = SA.job_id`; `JS.skill_abr = SK.skill_abr`; `JI.industry_id = IN.industry_id`. Không JOIN `skill_name` với `industry_name` và không coi hai nhóm nhãn là tương đương.
- Quan hệ P → JS/JI là 0..n; JS → SK và JI → IN là nhiều → một; P → SA là 0..1 trong dữ liệu đã audit. D04 chuyển mã số về `bigint`; nếu dùng raw phải tuân theo chuẩn hóa định danh S3, không ép số qua float tùy tiện.
- Giữ bảng cầu riêng hoặc gom `collect_set` theo `job_id` bằng `aggregate_bridge` trước LEFT JOIN. Nếu cần explode để đếm một nhãn/ngành/kỹ năng, tạo nhánh phân tích riêng và khử trùng cặp `(job_id, giá trị)`; không dùng nhánh đó để tính lương. Đối soát trước/sau JOIN bằng `assert_unique_key` và `check_grain_preserved` của `src/d05_utils.py`.
- Dùng T/P làm tập nền, tách orphan khỏi phép đo, không INNER JOIN mọi bảng con làm mất tin thiếu thông tin. Những khóa JOIN này là bằng chứng phục vụ A01; **chưa thay thế bản đồ JOIN và hợp đồng nghiệp vụ A03**.
- NULL/chuỗi thiếu không được gán thành 0, false hoặc một nhãn thật. Bảng trình bày có thể có mục **“Chưa xác định/Thiếu”** nhưng giữ dữ liệu nguồn NULL. Mẫu số bằng 0 thì tỷ lệ để NULL/“Không đủ dữ liệu”.
- Với thuộc tính nhiều giá trị, mỗi tin được tính một lần cho từng giá trị; tổng các tỷ lệ có thể vượt 100%. Với mọi mẫu số là tập có thông tin, báo thêm độ phủ so với N hoặc số tin nhóm nghề tương ứng.

## 5. Ma trận 8 câu hỏi – trường dữ liệu

Ký hiệu P, JS, SK, JI, IN, SA trỏ đến bảng và **file nguồn cụ thể ở mục 2**. “Nhóm nghề” và “kỹ năng trích xuất” dưới đây là đầu ra nghiệp vụ tương lai, **chưa có tên bảng/cột được xác nhận**; cột đầu vào chỉ liệt kê tên thực tế. Q01–Q05, Q08 có cách đo từ thuộc tính cấu trúc sau khi có T; Q06 cần A05; Q07 cần quy tắc lương D07. Không câu nào có kết quả CNTT ở A01.

| Mã | Nội dung câu hỏi đã chốt | Nguồn bảng/file | Cột đầu vào thực tế | Cách đo khả thi | Mẫu số | Điều kiện thực hiện | Giới hạn diễn giải |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q01 | **Cơ cấu các nhóm nghề trong tập tin CNTT như thế nào?** | P; JS/SK và JI/IN chỉ hỗ trợ tín hiệu nếu A02/A03 cho phép | `P.job_id`, `P.title`, `P.description`; hỗ trợ: `JS.job_id`, `JS.skill_abr`, `SK.skill_abr`, `SK.skill_name`, `JI.job_id`, `JI.industry_id`, `IN.industry_id`, `IN.industry_name` | Áp dụng taxonomy và quy tắc ưu tiên A02 để mỗi tin có một nhóm nghề chính hoặc “Chưa xác định”; đếm distinct tin từng nhóm và tỷ trọng | N; giữ “Chưa xác định” trong phân bố | A02 chốt taxonomy, quy tắc nhiều nhóm và bộ lọc CNTT; A03 chốt tín hiệu nhãn/ngành; TV1 D05/D06 cung cấp T | Không dùng ngành hoặc nhãn `IT` như nhóm nghề đã phân loại. Nhóm nghề chính là cách đo đề xuất, phải được A02 xác nhận; tỷ trọng phản ánh taxonomy và tập được lọc |
| Q02 | **Các nhãn cấp kinh nghiệm/cấp bậc phân bố thế nào trong tin CNTT?** | P | `job_id`, `formatted_experience_level` | Liệt kê giá trị thực tế, chuẩn hóa nhãn theo quy tắc đã kiểm tra; distinct tin từng nhãn, thêm số/tỷ lệ thiếu; có thể bổ sung tỷ trọng trên tập có nhãn | N cho phân bố có mục thiếu; số distinct tin có nhãn cho tỷ trọng có điều kiện | Có T; khảo sát danh sách nhãn, alias và độ thiếu trên T trước khi gộp | Nhãn cấp bậc không tương đương số năm kinh nghiệm; không suy số năm hoặc gán thiếu thành cấp thấp nhất |
| Q03 | **Tin CNTT tập trung ở những địa điểm đăng tuyển nào?** | P | `job_id`, `location`; `zip_code`, `fips` chỉ đối chiếu khi phù hợp | Trước hết đếm distinct tin theo chuỗi `location` đã trim, xếp hạng Top-k; báo độ phủ. Chỉ gộp thành phố/vùng/quốc gia khi có quy tắc parse và mẫu xác nhận | Số distinct tin có `location` dùng được; độ phủ = số này / N | Có T; kiểm tra giá trị, chuỗi nhiều địa điểm và nhãn từ xa; giữ nhãn nguồn nếu chưa parse được | Chưa chứng minh có đủ địa điểm Việt Nam; không dùng địa chỉ doanh nghiệp thay địa điểm tin. Chuỗi địa điểm không tự xác định địa điểm làm việc thực tế |
| Q04 | **Các loại việc làm được ghi trong tin CNTT phân bố như thế nào?** | P | `job_id`, `formatted_work_type`, `work_type`; `remote_allowed` chỉ khảo sát riêng | CountDistinct tin theo `formatted_work_type`, đối chiếu với `work_type` trước khi chuẩn hóa; báo tỷ trọng và thiếu. Cờ remote có thể báo true/false/NULL riêng nếu định nghĩa được xác minh | N cho loại việc làm có mục thiếu; số tin có cờ hợp lệ nếu báo tỷ trọng remote, kèm độ phủ / N | Có T; khảo sát nhãn/cặp giá trị thực tế và ý nghĩa của cờ | S7 đã quan sát Full-time/Part-time; phải đo lại phân bố trên T. Không suy ba loại tại văn phòng/kết hợp/từ xa từ `remote_allowed`, không đổi NULL thành false |
| Q05 | **Những nhãn chức năng/lĩnh vực nào trong mapping gốc được gắn nhiều nhất cho tin CNTT?** | P + JS + SK | `P.job_id`, `JS.job_id`, `JS.skill_abr`, `SK.skill_abr`, `SK.skill_name` | Giới hạn JS theo T, loại orphan và khử trùng `(job_id, skill_abr)`, JOIN mapping theo mã; xếp hạng số distinct tin và tỷ lệ xuất hiện từng nhãn | Số distinct tin CNTT có ít nhất một nhãn ánh xạ hợp lệ; báo độ phủ / N và số tin không có nhãn | A03 xác nhận cách gọi và cách dùng mapping; TV1 cung cấp dữ liệu JOIN giữ grain; mapping 35 nhãn đã được đối chiếu S4 | Đây là phân bố nhãn gốc, không phải thống kê Python/Java/SQL hay taxonomy nghề CNTT. Tin có nhiều nhãn nên tổng tỷ lệ có thể >100%; thiếu nhãn không chứng minh tin không có kỹ năng |
| Q06 | **Kỹ năng công nghệ nào được nhắc nhiều trong mô tả tin CNTT và khác nhau ra sao giữa các nhóm nghề?** | P + kết quả nhóm nghề A02 + đầu ra trích xuất A05 (chưa có bảng/file đầu ra) | `P.job_id`, `P.description`; `P.skills_desc` chỉ bổ sung sau xác minh; `P.title` dùng cho phân nhóm theo A02 | A05 trích và chuẩn hóa tên kỹ năng bằng từ điển/alias/ranh giới từ đã kiểm tra; lưu bằng chứng văn bản và nguồn. Khử trùng `(job_id, kỹ năng)`, đếm distinct tin từng kỹ năng toàn tập và từng nhóm, xếp hạng tỷ lệ nhắc đến | Số distinct tin có `description` dùng được và đã được xử lý thành công, kể cả không trích ra kỹ năng; theo nhóm dùng tập tương ứng. Báo độ phủ xử lý / N hoặc / tổng tin nhóm | A02 và A05 bàn giao taxonomy, quy tắc trích, trạng thái xử lý và mẫu đánh giá; A03 chốt nguồn kỹ năng. Chỉ công bố kỹ năng thực sự được tìm thấy; nguồn phụ phải có độ phủ riêng | Câu hỏi giữ **có điều kiện** vì nguồn văn bản đã được xác nhận, nhưng chưa có kết quả kỹ năng công nghệ. Nhắc đến không đồng nghĩa bắt buộc hoặc trình độ; không dùng mẫu số chỉ gồm tin trích được ít nhất một kỹ năng. Không tìm thấy từ khóa không chứng minh không yêu cầu kỹ năng |
| Q07 | **Lương được công bố khác nhau thế nào theo nhóm nghề và nhãn kinh nghiệm, trong cùng tiền tệ và kỳ trả lương?** | P; SA là nguồn đối chiếu/bổ sung có điều kiện | `P.job_id`, `P.title`, `P.description`, `P.formatted_experience_level`, `P.min_salary`, `P.max_salary`, `P.med_salary`, `P.currency`, `P.pay_period`, `P.compensation_type`; SA: `job_id`, `min_salary`, `max_salary`, `med_salary`, `currency`, `pay_period`, `compensation_type` | Tách nhóm nghề × kinh nghiệm × `(currency, pay_period, compensation_type)`; báo cỡ mẫu và median/IQR của `min_salary`, `max_salary` riêng. `med_salary` nguồn báo riêng nếu D07 xác nhận. Báo thêm tỷ lệ có bộ lương đủ điều kiện; chỉ so sánh các nhóm có cùng bộ đơn vị | Số distinct tin có giá trị hợp lệ của từng chỉ số trong từng nhóm/đơn vị; tỷ lệ phủ lương dùng tổng distinct tin CNTT của nhóm tương ứng, gồm tin thiếu lương | A02 có nhóm nghề; D07 xác nhận ý nghĩa các trường/đơn vị, quy tắc khoảng lương, giá trị bất thường và nguồn ưu tiên; kiểm tra P–SA bằng `job_id`, alias cột khi JOIN, đối chiếu xung đột trước bổ sung | Không coalesce tùy từng cột khiến trộn bộ lương từ hai nguồn; không gộp tiền tệ/kỳ trả, quy đổi hoặc annualize trong A01. Không dùng `normalized_salary` khi ý nghĩa chưa xác minh; không tự lấy trung điểm min/max hoặc coi `med_salary` là median thống kê. Chỉ phản ánh tập có lương, cỡ mẫu nhỏ/thiếu gây sai lệch |
| Q08 | **Các tin CNTT trong dataset phân bố theo tuần/tháng ra sao khi dùng từng mốc thời gian đăng?** | P; S5 đối chiếu đơn vị | `job_id`, `original_listed_time`, `listed_time`; bản sao D04: `original_listed_time_raw`, `listed_time_raw` | Dùng `original_listed_time` cho phân bố chính, nhóm tuần ISO/tháng theo UTC và đếm distinct tin; biểu đồ `listed_time` riêng để đối chiếu. Báo min/max, mốc thiếu/không hợp lệ và tuần/tháng đầu-cuối không trọn vẹn | Số distinct tin CNTT có timestamp hợp lệ tương ứng; mỗi mốc có mẫu số riêng, báo độ phủ / N | Có T; raw postings là epoch milliseconds, D04 đã là timestamp UTC nên không chia 1.000 lần nữa; xác minh định nghĩa nghiệp vụ hai mốc | Không dùng thay thế hai mốc cho nhau hoặc coi mọi chênh lệch là đăng lại. Phân bố dataset không phải xu hướng nhu cầu toàn thị trường; khoảng lấy mẫu/thời gian biên không đồng đều có thể chi phối số lượng |

**Không chốt** các câu hỏi về số năm kinh nghiệm, ba chế độ tại văn phòng/kết hợp/từ xa, mức lương quy về VND/năm hoặc xu hướng thị trường Việt Nam: dữ liệu và quy tắc hiện có chưa hỗ trợ những diễn giải đó. Q06/Q07 là câu hỏi có nguồn đầu vào khả thi nhưng phải hoàn thành dependency trước khi công bố kết quả.

## 6. Các bước phụ thuộc và nội dung bàn giao

A02/A03 đã có artifact; lượt 08/10 kiểm chứng A01/A03 và chuẩn bị A04. Các nội dung pipeline/phân tích dưới đây vẫn là dependency, chưa đánh dấu production hoàn thành.

| Bước | Nội dung cần cung cấp/kiểm tra | Câu hỏi phụ thuộc |
| --- | --- | --- |
| A02 – TV2 | Taxonomy CNTT, tiêu chí đưa vào/loại ra, quy tắc nhóm nghề chính và “Chưa xác định”, tên đầu ra và phiên bản quy tắc. Đã có JSON v0.1.0 và docs A02; triển khai dùng chung ở src/it_taxonomy.py, chưa có nhãn tay xác nhận | Q01; tập nền cho cả 8 câu hỏi; nhóm nghề cho Q06/Q07 |
| A03 – TV2 | Bản đồ JOIN và nguồn kỹ năng; xác nhận ngữ nghĩa 35 nhãn, ngành của tin/doanh nghiệp, mapping và orphan. Khóa khảo sát ở mục 4 chỉ là đầu vào cho bước này | Q01, Q05, Q06; điều kiện mở D05 official của TV1 |
| TV1 – D05 | Tích hợp canonical giữ một dòng/job_id, gom bảng cầu trước JOIN, kiểm tra tính duy nhất và chống nhân dòng; giữ nguồn/NULL khi chưa khớp. Scaffold đã có, chưa có canonical production | Toàn bộ khi dùng nguồn tích hợp; đặc biệt Q05/Q07 |
| TV1 – D06, TV2 kiểm tra mẫu A04 | Áp dụng bộ lọc CNTT theo quy tắc đã chốt, kiểm tra mẫu được chọn/bị loại, bàn giao T và N cùng phiên bản bộ lọc | Cả 8 câu hỏi; mọi tỷ lệ thiếu/độ phủ phải đo lại trên T |
| A05 – TV2 | Trích kỹ năng công nghệ từ `description`, xác nhận từ điển/alias và ngữ cảnh, lưu bằng chứng, trạng thái xử lý, khử trùng theo tin và đánh giá mẫu | Q06; chưa triển khai trích xuất ở A01 |
| TV1 – D07 | Chốt ngữ nghĩa lương, bộ đơn vị, đối chiếu P/SA, nguồn ưu tiên, quy tắc giá trị không hợp lệ và cỡ mẫu báo cáo; nếu quy đổi phải có quy tắc riêng được lưu | Q07; có thể phân tích tách đơn vị trước khi có quy tắc quy đổi |
| Bước phân tích sau A01 | Kiểm tra nhãn kinh nghiệm/loại việc làm/địa điểm trên T, độ phủ từng thuộc tính, mốc thời gian và nhóm có mẫu số 0; ghi phiên bản dataset và quy tắc của mỗi bảng kết quả | Q02–Q04, Q08 và kiểm chứng chung |

## 7. Những điểm còn chờ

1. **Parquet/canonical và Spark:** raw đã có đủ; `data/processed/clean/` và canonical D05 vẫn chưa có. Chưa đọc lại schema/cast/sửa encoding D04; không chạy lại ETL. TV1 cần bàn giao đầu ra và kiểm tra Java 21/PySpark 4.2.0, parity của implementation trên JVM/Spark.
2. **Tập CNTT đã xác nhận:** A02/A03 và dự đoán A04 đã có; T và N sau kiểm tra nhãn tay/D06 chưa có. Dự đoán ACCEPT không phải nhãn chuẩn. Các tỷ lệ ở đây là toàn raw.
3. **Kỹ năng/ngành:** mapping raw đã đọc trực tiếp; A05 chưa có dictionary, kỹ năng trích xuất hoặc kiểm định ngôn ngữ/boilerplate. Không dùng các nhãn nguồn làm Python/SQL.
4. **Lương:** đã đối chiếu sáu trường P/SA trên 36.073 tin khớp, không thấy khác biệt theo giá trị số. Ý nghĩa `med_salary`/`normalized_salary`, đơn vị, ngoại lệ, cỡ mẫu và nguồn ưu tiên còn chờ D07; quan sát cùng giá trị không chứng minh semantics đúng.
5. **Thời gian:** raw milliseconds/seconds và min/max UTC đã tính lại (mục 9). Cần TV1 xác nhận ý nghĩa hai mốc đăng và chính sách snapshot. D05 đang ghi employee_counts min `2024-04-06 02:42:53 UTC`, max `2024-04-20 07:27:39 UTC`, lệch +7 giờ so với epoch thật `2024-04-05T19:42:53Z` và `2024-04-20T00:27:39Z`; không tự sửa báo cáo TV1.
6. **Mẫu số CNTT:** sau nhãn tay và D06 phải đo lại thiếu/độ phủ trên T và theo nhóm. Không sao chép các tỷ lệ raw hoặc tỷ lệ mẫu phân tầng sang kết quả CNTT/toàn dataset.

## 8. Kiểm chứng trong lượt A01 ban đầu ngày 07/10/2026

- Đọc hướng dẫn README, manifest, D02, dictionary, D03/D04, D05 pre-check/scaffold, handoff, các script reader/cast/JOIN; kiểm tra nhánh và trạng thái Git. Khi bắt đầu, repo đã ở `feat/tv2-analysis` và working tree sạch; không cần tạo/chuyển nhánh.
- Kiểm kê file hiện diện, đọc CSV audit bằng parser; đối chiếu tên cột giữa `table_inventory.csv`, dictionary và `d04_schema_changes.csv`, cùng quy tắc `TABLE_SPECS`/`TYPE_RULES` của `clean_data.py`.
- Đối chiếu khóa/cardinality/orphan từ S2/S4, số dòng và 67 kiểm tra D04 đã lưu; đọc đủ 35 nhãn S4 và kiểm tra không có tên Python/Java/SQL.
- Đọc mẫu văn bản trong encoding audit, mẫu raw timestamp trong time audit; quy đổi epoch độc lập bằng `DateTimeOffset` để kiểm tra milliseconds/seconds và UTC.
- Kiểm tra tài liệu có đúng 8 dòng câu hỏi và đủ 8 cột ma trận, 27 liên kết nguồn trong repo đều tồn tại; các cột đầu vào có định danh bảng được đối chiếu với inventory, toàn bộ 11 schema raw có trường tương ứng trong schema D04 đã lưu.
- Chưa chạy Spark, JOIN production, bộ lọc CNTT, trích kỹ năng, phân tích lương hoặc ETL trong A01. Đầu ra duy nhất là tài liệu này; không sửa raw, không commit hoặc push.

## 9. Kiểm chứng trực tiếp raw ngày 08/10/2026

Nguồn S7: đủ 11 CSV tại `C:\archive` đã sao chép nguyên byte vào `data/raw/`; [inventory/hash](../data/audit/tv2_raw_inventory.csv), [missing](../data/audit/tv2_raw_missing.csv), [profiles](../data/audit/tv2_raw_profiles.json). Số dòng/header và toàn bộ missing count khớp audit D03; không đủ bằng chứng kết luận cùng release Kaggle vì audit lịch sử không có SHA-256 raw. 118.612 bản ghi postings và 16.689 bản ghi companies chứa xuống dòng trong trường; không đếm dòng vật lý.

Tất cả số dưới đây có phạm vi **123.849 raw postings, mọi lĩnh vực**, không phải tập CNTT đã xác nhận. Ví dụ cùng tin đầy đủ nằm ở `data/analytics/tv2_validation/posting_examples.csv` (bị Git ignore).

| formatted_work_type ↔ work_type | Tin raw |
| --- | ---: |
| Full-time ↔ FULL_TIME | 98.814 |
| Contract ↔ CONTRACT | 12.117 |
| Part-time ↔ PART_TIME | 9.696 |
| Temporary ↔ TEMPORARY | 1.190 |
| Internship ↔ INTERNSHIP | 983 |
| Volunteer ↔ VOLUNTEER | 562 |
| Other ↔ OTHER | 487 |

Không thiếu hai cột loại việc làm; [kiểm tra từng bản ghi](../data/audit/tv2_work_type_pairs.csv) xác nhận đúng 7 cặp một-một. Nhãn kinh nghiệm: Entry level 36.708, Mid-Senior level 41.489, Associate 9.826, Director 3.746, Internship 1.449, Executive 1.222; thiếu 29.409. Đây là nhãn cấp bậc nguồn.

`remote_allowed` raw chỉ có `1.0` (15.246; 12,310152%) và thiếu (108.603; 87,689848%); không có giá trị false quan sát được. NULL không là onsite hoặc hybrid. `description` thiếu 7, `skills_desc` thiếu 121.410; cả 2.439 skills_desc có giá trị đều cùng có description, nên nguồn phụ không bù trường description thiếu trong bản này.

Tiền tệ trong postings: USD 36.058, EUR 6, CAD 3, BBD 2, AUD 2, GBP 2; thiếu 87.776. Kỳ trả: YEARLY 20.628, HOURLY 14.741, MONTHLY 518, WEEKLY 177, BIWEEKLY 9; thiếu 87.776. Compensation chỉ có BASE_SALARY 36.073, còn thiếu 87.776. Bảng salaries có 40.785 dòng kể cả 4.712 orphan; phân bố của bảng này không dùng thay phân bố postings (xem profile nguồn riêng).

Quan sát cột lương raw có giá trị: min/max 29.793 tin, med 6.280, normalized 36.073. Giá trị min_salary từ 1 đến 85.000.000; max_salary từ 1 đến 120.000.000; med_salary có 0 và cao nhất 750.000; normalized_salary có 0 và cao nhất 535.600.000. Các khoảng trộn đơn vị chỉ dùng phát hiện nhu cầu kiểm tra D07, không phải thống kê lương CNTT hoặc lương so sánh được. Không thay NULL, suy công thức normalized, lấy trung điểm hay quy đổi.

| Trường raw | Đơn vị | Min UTC | Max UTC | Có giá trị |
| --- | --- | --- | --- | ---: |
| original_listed_time | milliseconds | 2023-12-05T21:08:53Z | 2024-04-20T00:26:43Z | 123.849 |
| listed_time | milliseconds | 2024-03-24T21:50:14Z | 2024-04-20T00:26:56Z | 123.849 |
| expiry | milliseconds | 2024-04-12T06:30:48Z | 2024-10-17T00:26:36Z | 123.849 |
| closed_time | milliseconds | 2024-04-05T19:38:52Z | 2024-04-19T21:28:27Z | 1.073 |
| employee_counts.time_recorded | seconds | 2024-04-05T19:42:53Z | 2024-04-20T00:27:39Z | 35.787 snapshots |

Ví dụ job `921716`: `original_listed_time=1713397508000.0` → `2024-04-17T23:45:08Z`. Đã đọc/tính lại raw, chưa đọc lại các timestamp Parquet. Dự đoán và mẫu A04 được mô tả ở [hướng dẫn A04](a04_manual_labeling.md); không chạy A05–A11 trong lượt này.
