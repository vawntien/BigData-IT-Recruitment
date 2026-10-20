# A05 – Trích xuất kỹ năng công nghệ từ description

Ngày **14/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`. Đã có **bản phát triển Python, từ điển v0.1.2, fixture và đầu ra kiểm tra trên 105 tin CNTT đã duyệt**. Chưa có đầu vào canonical/D06, chưa chạy Spark và chưa tạo `job_skill_technical.parquet` chính thức; A05 chưa được ghi nghiệm thu/100%.

Active taxonomy vẫn **v0.2.0**, candidate A04 vẫn **v0.2.2**, trạng thái đề nghị A04 vẫn **“Sẵn sàng rà soát nghiệm thu”** theo [bàn giao A04](a04_handoff_tv1.md). A05 không sửa bộ lọc, nhãn, metadata hoặc quyết định nghề của A04.

## 1. Phân công và kiểm kê trước triển khai

Đã đọc README, A01, A03, bàn giao A04, code/tiện ích CSV, parser và scaffold D05; không tìm thấy AGENTS.md trong repo. Git trước sửa ở đúng `feat/tv2-analysis`, HEAD `e437dcc11dda61f847673b9cc8c5801886c1996d`, tracked/index sạch; hai workbook chốt nhãn untracked được giữ nguyên. Không chuyển/reset nhánh, stage, commit hay push trong lượt A05.

Nguồn phân công: `C:/Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsm`, SHA-256 `9343cc8b5c17beb343ec98fa57bb00bff6cb4609aa12cbffb0100ef461c3df26`, đọc bằng ZIP/XML, không chạy macro hoặc sửa workbook. [Trích phân công A05](../data/analytics/a05_development_v0_1_2_20261014/assignment_context.json) lưu ô nguồn:

| Ô | Yêu cầu |
| --- | --- |
| Cong viec!D22/E22 | TV2 chủ trì, bắt buộc |
| F22 | Trích xuất kỹ năng từ mô tả |
| G22 | Tạo từ điển Python, Java, SQL, cloud… Có ranh giới từ và alias, lưu nguồn trích xuất. |
| H22 | **job_skill_technical.parquet** |
| I22 | Kiểm tra C/C++, Java/JavaScript. Mỗi kỹ năng chỉ đếm một lần/tin. |
| J22 | Phụ thuộc **D06** |

`Tong quan!C19:C20` đặt luồng chung PySpark/Spark SQL/Parquet; A05 không được coi CSV phát triển là đã hoàn thành đầu ra Parquet. [D05 scaffold](d05_implementation_scaffold.md) là bằng chứng hạ tầng, không phải xác nhận canonical production đã chạy.

| Đầu vào/môi trường thực tế | Hiện trạng | Cách dùng ở lượt này |
| --- | --- | --- |
| Raw | Đủ 11 CSV, `data/raw/postings.csv` có description nguyên bản | Chỉ đọc để lấy full text của các job_id đã chọn, không sửa raw/ETL |
| Clean/canonical/it_jobs Parquet | Không có file `.parquet` dưới data; processed chỉ có .gitkeep | Không giả định D05/D06 đã hoàn thành; chờ TV1 cung cấp input chính thức |
| Mẫu nhãn A04 | 160 dòng chính + 17 bổ sung, hợp 176 khóa; 105 CNTT, 67 NGOAI_CNTT, 4 CHUA_RO | Chỉ chọn **105 CNTT đã duyệt**, không dùng machine ACCEPT làm nhãn chuẩn |
| Python | `.venv/Scripts/python.exe`, Python 3.11.9 | Trích thử và chạy unittest bằng thư viện chuẩn |
| Spark/JVM | PySpark chưa có trong venv; Java mặc định 1.8.0_51 | Adapter được chuẩn bị, Spark/DataFrame/Parquet chưa xác minh thực thi |

105 khóa lấy từ [workbook chính](../data/analytics/a04_manual_seed42/a04_manual_labels_filled.xlsx), sheet `A04 manual labels`, và [workbook bổ sung](../data/analytics/a04_taxonomy_v0_2_0_20261008/accept_downgrades_for_review_blind.xlsx), sheet `Review`: **90 + 16 − 1 = 105**. Ca chung `3905848702` được nối bằng job_id canonical, kiểm tra cả 8 trường manual/title/description nhất quán rồi tính một lần. Các tin CNTT mà candidate A04 còn REVIEW/FN vẫn được giữ trong tập kiểm tra này; A05 không tự phân loại lại chúng.

Runner đọc raw CSV quote/multiline để chọn khóa và kiểm tra title/description khớp toàn văn workbook. Nó đọc 123.849 hàng raw để đối soát lựa chọn/khóa, **chỉ gọi bộ trích trên 105 description**; đây không phải lần trích toàn dataset. [input_manifest.json](../data/analytics/a05_development_v0_1_2_20261014/input_manifest.json) giữ nguồn/hash, số dòng, job_id và source_refs.

Mẫu A04 là **mẫu phát triển**, đã dùng kiểm tra/sửa bộ lọc. 105 tin này không là toàn bộ tập CNTT, không là mẫu xác suất đại diện và chưa có nhãn chuẩn kỹ năng công nghệ. Nhãn CNTT xác nhận nghề, không xác nhận từng kết quả skill của A05.

## 2. Nguồn và từ điển

[A01 Q06](a01_analysis_questions.md) hỏi công nghệ được nhắc trong mô tả; [A03 mục 7](a03_skills_industries_report.md) chọn `postings.description` làm nguồn chính. A05 chỉ bật nguồn này. `postings.skills_desc` chưa bật; 35 mã/tên từ `jobs/job_skills`/mapping được giữ ở namespace nhãn chức năng/lĩnh vực, không chuyển thành Python/SQL hoặc suy skill từ nhóm nghề/doanh nghiệp.

Từ điển chính [config/tech_skills.json](../config/tech_skills.json): **schema_version=1, version=0.1.2**, SHA-256 `f571ff4525cf629041a6c4791646eebff4f88ca7fa91a978379741f393afa7aa`. Mỗi skill có `code` ổn định, `name` chuẩn, `group`, aliases; alias dễ nhầm tham chiếu context có patterns/nearby_terms/excluded_patterns và quy tắc danh sách công nghệ. Phiên bản/schema, parser/section policy và ngữ nghĩa overlap cũng nằm trong JSON.

| Nhóm | Số mã | Danh mục khởi đầu |
| --- | ---: | --- |
| LANGUAGE | 14 | Python, Java, JavaScript, TypeScript, C, C++, C#, Go, R, Ruby, PHP, Scala, Swift, Kotlin |
| DATABASE | 6 | SQL, Microsoft SQL Server, PostgreSQL, MySQL, Oracle Database, MongoDB |
| FRAMEWORK_RUNTIME | 7 | .NET, Node.js, React, Angular, Django, Spring, ASP.NET |
| CLOUD | 3 | Amazon Web Services, Microsoft Azure, Google Cloud |
| DEVOPS | 9 | Docker, Kubernetes, Terraform, Jenkins, Git, GitHub, GitLab, Linux, PowerShell |
| DATA_TOOL | 7 | Apache Spark, Apache Hadoop, Apache Kafka, Snowflake, Databricks, Tableau, Microsoft Power BI |
| Tổng | 46 | Tập vừa đủ để phát triển nguồn kỹ năng cho Q06 |

**46/46 mã có ít nhất một bằng chứng được nhận trong description của mẫu đã đối soát raw**, không thêm mục chỉ để tăng độ dài danh mục. [dictionary_coverage.csv](../data/analytics/a05_development_v0_1_2_20261014/dictionary_coverage.csv) giữ số distinct job_id, ví dụ alias/ranges của từng mã; điều này chứng minh có xuất hiện theo rule, không chứng minh danh mục đầy đủ hoặc mọi hit là đúng.

Snapshot exact bytes: [v0.1.0](../config/versions/tech_skills_v0.1.0.json), [v0.1.1](../config/versions/tech_skills_v0.1.1.json), [v0.1.2](../config/versions/tech_skills_v0.1.2.json). V0.1.0 là lần thử đầu; v0.1.1 sửa Objective- C và scope/cue; v0.1.2 bổ sung heading explicit **What You Need** đã thấy trong raw và hoàn thiện phân biệt nhiệm vụ/qualification. Code trước các sửa được giữ tại baseline trong hai thư mục phát triển trước; không ghi đè các đầu ra thử hoặc trace A04.

[.gitattributes](../.gitattributes) được bổ sung đúng các đường A05 để giữ byte/hash trước `core.autocrlf`; các quy tắc A04 có sẵn giữ nguyên. Khi sửa alias/policy/code ở lượt sau, lưu phiên bản/hash/run mới; không lấy kết quả cũ làm kết quả bản sửa.

## 3. Phương pháp matching và phân biệt ngữ cảnh

[TechSkillExtractor](../src/tech_skill_extractor.py) là bộ trích riêng của A05, phiên bản processor `a05-source-mapped-v1.2`. Dùng lại **SourceDocument/MappedHTML/normalized_spans** của parser hiện hữu để map nguồn; không dùng DescriptionProcessor, role gate/qualification/actor blockers hoặc cửa sổ 500 của classifier A04.

1. Giữ description gốc. NFC/lower/collapse whitespace chỉ phục vụ matching; không bỏ dấu, không xóa `+`, `#`, `.` hoặc tự thay nguồn. Alias cùng normalization. NULL/rỗng/sentinel được báo SOURCE_MISSING.
2. Parse HTML/block tags/entities, bỏ nội dung script/style khỏi matching nhưng giữ nguồn. Tách newline/bullet/câu và heading explicit có colon hoặc dòng độc lập; bảo vệ các dấu chấm trong .NET/Node.js/URL/version. Giữ tất cả unit dài, không cắt hoặc bỏ đoạn vì vượt 500 ký tự; cờ long chỉ phục vụ kiểm kê và đối soát unit trộn scope.
3. Literal phrase có ranh giới Unicode word/`+`/`#`. Java không khớp bên trong JavaScript, Git không khớp GitHub, SQL không khớp PostgreSQL. Thu mọi hit rồi chọn **alias dài nhất khi overlap**: SQL Server không tự sinh thêm SQL; ASP.NET không tự sinh .NET. Nếu SQL/.NET xuất hiện riêng ở chỗ khác thì có hit riêng.
4. C/C++/C#, .NET, Node.js được nhận độc lập. C, Go, R, Spark, React/Spring/Angular/Swift và Oracle ngắn cần context phù hợp. C có programming/language hoặc danh sách công nghệ; Go/R không nhận từ go-live/grade/R&D; Spark không nhận spark plug/joy. Danh sách cần nối với công nghệ đã có căn cứ, không cho hai từ mơ hồ như “Go or R” tự xác nhận lẫn nhau. C không khớp Objective- C thành ngôn ngữ C.
5. Heading REQUIREMENTS/**QUALIFICATIONS** là nguồn yêu cầu ứng viên; PREFERRED là ưu tiên; TASK/ROLE cùng task cue là công nghệ dùng cho nhiệm vụ. Cue ứng viên, cue công ty, suffix required/preferred và negation được xét riêng cho hit. “Business requirements” không tự là yêu cầu kỹ năng của ứng viên. Prefix qualification trong TASK vẫn có thể là REQUIRED; “experience” của đội phát triển không tự biến task thành yêu cầu.
6. COMPANY chỉ thu evidence để đối soát nếu không có cue vị trí; BENEFITS/EEO là OUTSIDE_POSITION. Các scope nối liền/mixed mà chưa xác định được được ghi AMBIGUOUS_SCOPE. Alias thiếu ngữ cảnh là AMBIGUOUS_ALIAS. Không tự sửa heading implicit bằng cách chèn text hoặc mở toàn phần giới thiệu công ty.
7. “No experience with Python required”, “Java is not required”, “không yêu cầu Python”, phủ định dùng công nghệ được ghi **NEGATED**, không vào bridge. “Not only”/“no less than” không được hiểu thành phủ định yêu cầu. Các cấu trúc phủ định/phối hợp phức tạp vẫn cần người đọc xác nhận.

`mention_type`: **REQUIRED, PREFERRED, TASK** có thể vào bridge khi alias/context/mapping hợp lệ; COMPANY_ONLY, NEGATED, OUTSIDE_POSITION, AMBIGUOUS_ALIAS/SCOPE/MAPPING chỉ lưu evidence. Đây là phân loại theo quy tắc phát triển, không đo mức thành thạo hoặc xác nhận mọi mention là yêu cầu bắt buộc.

Một skill xuất hiện nhiều lần/qua nhiều alias chỉ tạo **một dòng job–skill**. Dòng này giữ mọi evidence_id và hợp `mention_types`; không giữ duy nhất hit đầu. Không dùng job_id, tên doanh nghiệp, nhóm nghề hoặc label chức năng làm whitelist cho rule; job_id chỉ định danh và chọn tập kiểm tra ngoài extractor.

## 4. Đầu ra và schema

Thư mục kết quả cuối: [a05_development_v0_1_2_20261014](../data/analytics/a05_development_v0_1_2_20261014/). Đây là **CSV/JSONL phát triển**, không đổi đuôi để giả Parquet.

| File/bảng | Grain | Trường chính |
| --- | --- | --- |
| [job_skill_technical.csv](../data/analytics/a05_development_v0_1_2_20261014/job_skill_technical.csv) | Một `(job_id, skill_code)` trong run | skill_name/group, mention_types, evidence_ids/count, source_field, run_id, dictionary_version/hash, extractor_version |
| [technical_skill_evidence.jsonl](../data/analytics/a05_development_v0_1_2_20261014/technical_skill_evidence.jsonl) | Một hit được phân xử overlap, kể cả đề cập bị loại/mơ hồ | evidence_id, alias/matched_text, source hash, raw ranges, excerpt và offsets, section, mention_type, accepted, rule_id, các tọa độ normalized/derived |
| [skill_source_processing.jsonl](../data/analytics/a05_development_v0_1_2_20261014/skill_source_processing.jsonl) | Một `(job_id, source_field)` | status/error, source hash, technical_skills, review_required, số evidence, parser_issues/long units, run/dictionary/processor provenance |
| [review_skill_sample.csv](../data/analytics/a05_development_v0_1_2_20261014/review_skill_sample.csv) | Một evidence, 661 dòng | job_id/title, tên skill, loại/accepted, alias, quote thật, ranges/rule; cột manual_review_decision/note **để trống** |
| [review_jobs.csv](../data/analytics/a05_development_v0_1_2_20261014/review_jobs.csv) | Một job, đủ 105 dòng | title, status, technical_skills, review_required; có cả zero-hit |
| [dictionary_coverage.csv](../data/analytics/a05_development_v0_1_2_20261014/dictionary_coverage.csv) | Một mã skill | distinct tin có literal/hit được nhận, ví dụ nguồn |
| [input_manifest.json](../data/analytics/a05_development_v0_1_2_20261014/input_manifest.json), [run_manifest.json](../data/analytics/a05_development_v0_1_2_20261014/run_manifest.json), [summary.json](../data/analytics/a05_development_v0_1_2_20261014/summary.json) | Metadata run | Nguồn/hash/lựa chọn, code/output hashes, môi trường và phạm vi chạy |

Python dùng job_id là chuỗi số canonical trong phạm vi signed bigint; schema Spark [a05_spark.py](../src/a05_spark.py) chuyển thành **bigint non-null**. `skill_code`, version/hash, run_id/source_field là string; mention_types/evidence_ids là array<string>, evidence_count là bigint. Evidence có accepted boolean, offsets bigint nullable khi không map, raw_match_ranges array<array<bigint>>; các đoạn trích/hash/rule/type là string. Bảng processing dùng technical_skills array<string> nullable và review_required boolean. Nếu giữ nhiều run thì run_id/dictionary version phải tham gia khóa lịch sử; trước JOIN chọn một run, không nhân dòng bảng một tin.

`raw_offset_unit=original_field_unicode_codepoints_half_open`: `[start,end)` trong description **sau CSV parse**, không phải byte offset hoặc vị trí trong file CSV. `raw_match_ranges` có thể nhiều khoảng do markup/entity/NFC. `matched_text` nối các lát nguồn đó; `derived_matched_text` là chữ sau parser. `excerpt == raw[raw_excerpt_start:raw_excerpt_end]`, có thể chứa HTML; sentence_text là derived text riêng, không giả thành quote nguyên văn. Không cắt quote ở 240 ký tự theo A04; unit dài vẫn truy được toàn bộ.

Offset normalized thuộc unit, derived thuộc parser text; chúng không thay raw coordinates. Trên JVM đổi code point boundary thành UTF-16 bằng `String.offsetByCodePoints` trước substring; TV1 kiểm tra emoji/NFC/entities/inline tags để giữ cả nhiều raw ranges. Hit map thất bại được ghi riêng, không tạo bridge dựa trên vị trí bịa.

Trạng thái nguồn:

- **SOURCE_MISSING**: NULL/rỗng/sentinel; technical_skills=NULL, không hiểu là không có kỹ năng.
- **FAILED**: input/parser/trích lỗi, có error_code; NULL, không biến thành zero-hit.
- **PARTIAL**: parser/mapping chưa đầy đủ; giữ skill có bằng chứng hợp lệ và review flag, hoặc NULL nếu chưa có skill xác nhận. Không đưa partial vào mẫu số xử lý thành công.
- **PROCESSED_NO_MATCH**: xử lý thành công, không có hit được nhận theo phiên bản; technical_skills=[], có thể vẫn có đề cập mơ hồ/bị loại cần đọc lại.
- **PROCESSED_WITH_MATCH**: ít nhất một skill được nhận; vẫn có thể review_required vì hit khác mơ hồ. Không tự gọi là hoàn tất gán nhãn kỹ năng.

`skills_desc` là NOT_ENABLED ở metadata run; không coalesce mất nguồn. Khi cần tỷ lệ cho Q06, mẫu số là distinct tin có description dùng được và xử lý thành công **kể cả zero-hit**, báo độ phủ riêng. Không lấy chỉ 78 tin có match hoặc 561 hit làm mẫu số phổ biến công nghệ.

## 5. Cách chạy

Từ root repo, dùng Python của venv. Lần chạy mới phải chọn **thư mục output chưa tồn tại**; runner từ chối ghi đè và chỉ cho output phát triển dưới data/analytics:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s src -p test_a05_skills.py -v
.\.venv\Scripts\python.exe -B src/prepare_a05.py --config config/tech_skills.json --raw data/raw/postings.csv --output data/analytics/a05_development_next_run
```

API cục bộ: `TechSkillExtractor(config_path).extract(description, job_id, run_id=...)`. Chỉ truyền description cho nội dung trích, không title/company/nhóm nghề/nhãn chức năng. Constructor cũng nhận exact config_bytes để broadcast dictionary trên Spark worker.

Lệnh dưới dành cho TV1 **sau khi có môi trường Spark/Java 21 phù hợp và input D06 đã xác nhận**; chưa thực thi ở lượt này. Đường input là ví dụ cần TV1 chốt, không là file đang có:

```powershell
.\.venv\Scripts\python.exe -B src/a05_spark.py --input data/analytics/it_jobs.parquet --config config/tech_skills.json --run-id a05_official_next --output data/analytics/a05_official_next
```

Adapter dùng Spark utilities hiện có, đọc Parquet, kiểm tra grain/schema/membership, broadcast dictionary bytes, nạp extractor mỗi partition và tạo ba DataFrame có schema explicit. Nó viết `job_skill_technical.parquet`, `technical_skill_evidence.parquet`, `skill_source_processing.parquet` bằng errorifexists, kiểm tra đọc lại count/content và ghi run status; không tự fallback sang raw hay chạy ETL. Mã này đã kiểm tra syntax và helper chuyển record bằng unittest; **Spark transforms/schema serialization/read-write Parquet chưa được thực thi hoặc xác minh parity**.

## 6. Kiểm tra và số liệu mẫu phát triển

[Test A05](../src/test_a05_skills.py): **37 test qua, 0 failure/error/skip**; [log thực thi](../data/analytics/a05_development_v0_1_2_20261014/tests.log), [test result](../data/analytics/a05_development_v0_1_2_20261014/tests_result.json), [audit kiểm tra đầu ra](../data/audit/tv2_a05_validation_20261014.json).

Fixture dương/âm kiểm tra Java/JavaScript; C/C++/C#/.NET/Node.js; SQL Server/SQL và ASP.NET/.NET; Go/R/C/danh sách; Spark/React/Spring/Swift mơ hồ; QUALIFICATIONS/What You Need reset; required/preferred/task/company; phủ định tiếng Anh/Việt; HTML/entity/script/style/inline markup, NFC/emoji, mọi newline/bullet, unit dài; khử trùng nhiều alias/hit; missing/failed/partial/zero-hit; input key/text/overwrite; dictionary fail-closed và không whitelist job/employer. Helper Spark record được kiểm tra bằng Python, không phải một test Spark chạy thật.

| Chỉ số mô tả kết quả cuối | Số đếm/tử số–mẫu số |
| --- | --- |
| Tin CNTT đã duyệt được trích | 105 job_id duy nhất |
| Xử lý thành công/đầu vào | 105/105 = 100.00% |
| Tin có ít nhất một skill được nhận | 78/105 = 74.29% |
| Tin xử lý thành công, không skill được nhận | 27/105 = 25.71% |
| Job–skill | 355 dòng = 355 cặp duy nhất |
| Evidence | 661 hit duy nhất, trong đó 561 được nhận |
| REQUIRED / PREFERRED / TASK | 396 / 22 / 143 hit được nhận; không cộng thành số tin độc lập |
| Đề cập mơ hồ | 65 AMBIGUOUS_ALIAS + 31 AMBIGUOUS_SCOPE = 96 hit, thuộc 36/105 = 34.29% tin |
| OUTSIDE_POSITION | 4 hit, ngoài bridge |
| COMPANY_ONLY / NEGATED ở mẫu này | 0 / 0; hai loại có đối chứng trong fixture, không bịa ví dụ thực tế |
| Unit dài giữ lại / bị bỏ | 48 / 0 |
| Mã skill có bằng chứng được nhận | 46/46 = 100.00% của từ điển khởi đầu |

Đã tính lại từ **đầu ra lưu**: bridge unique, evidence_id unique, mọi bridge có accepted evidence tương ứng, tổng evidence_count=561; mọi status đủ 105 job_id. Đã kiểm tra **661/661** matched_text/excerpt/ranges và source hash với description của đúng khóa; input raw/workbook/hash khớp, không lấy excerpt của tin cùng title. Distinct job counts theo skill nằm trong summary/dictionary_coverage; ví dụ Python **24/105**, Java **16/105**, JavaScript **27/105**, SQL **32/105** là thống kê thử nghiệm, không accuracy hoặc phân bố toàn dataset.

36 tin cần đọc lại không là 36 FN hoặc 36 lỗi xử lý. Một tin có thể có cả hit được nhận và mơ hồ; bộ trích đã xử lý xong văn bản nhưng chưa có nhãn chuẩn kỹ năng của người đọc. Không có precision/recall/accuracy trên mẫu được gán nhãn skill, nên **không công bố các chỉ số đó**.

## 7. Ví dụ đúng, sai đã sửa và giới hạn còn lại

Các ví dụ “đúng” dưới đây là đối soát literal/evidence và ngữ cảnh cụ thể, không thay một bộ nhãn chuẩn kỹ năng đầy đủ:

| job_id / ca | Đối soát |
| --- | --- |
| `3895545207` | `C++` trong câu “Strong proficiency…” ở QUALIFICATIONS, raw `[3460,3463)`; nhận CPP và giữ đoạn yêu cầu. R trong cùng danh sách có Java/C++/Python/SQL làm căn cứ công nghệ. |
| `3886896222` | `Microsoft SQL Server` `[1195,1215)` nhận SQL_SERVER; generic SQL chỉ từ lần xuất hiện riêng, không sinh thêm từ alias dài. Câu task develop Java/JavaScript/SQL có “the company” ở phần sau được nhận task, không loại cả câu. |
| `3251984218` | `Node.JS` `[487,494)` trong “...is desired” nhận NODEJS/PREFERRED, không lấy title SAP BTP làm căn cứ skill. |
| `3895563414` | Heading standalone **What You Need** trong raw reset COMPANY→REQUIREMENTS; skill ở các câu Experience/Knowledge sau heading được xử lý như nguồn ứng viên, không chịu blocker A04. |
| `3886895728` | Lần thử đầu nhận C từ `Objective- C`; đã thêm exclusion biến thể hyphen/space và fixture. V0.1.2 không nhận đó là C, vẫn giữ C#/Java nếu có căn cứ. |
| Fixture phủ định | “No experience with Python or Java is required” không tạo bridge; evidence NEGATED. “Python required, Java preferred” giữ đúng loại riêng. Đây là đối chứng tổng hợp, không gọi là lỗi đã thấy trên 105 tin. |
| `3887916439` | SQL trong đoạn “Database and SQL: Capabilities…” thiếu scope ứng viên/nhiệm vụ rõ được giữ AMBIGUOUS_SCOPE, không tự ép thành REQUIRED. |
| `3891068727` | Unit dài nối nhiệm vụ với “Minimum qualifications…” chưa có ranh giới đáng tin; ghi AMBIGUOUS_SCOPE thay vì gán mọi công nghệ trong unit thành yêu cầu. Full text và hit vẫn được giữ. |

Các lượt thử v0.1.0/v0.1.1 được giữ riêng; chỉ v0.1.2 là đầu ra cuối của lượt này. Không tối ưu số match: một sửa có thể giảm hit được nhận vì scope chưa rõ, nhưng không xóa bằng chứng hoặc dùng nhãn CNTT để ép nhận skill.

Giới hạn cần rà soát:

- Dictionary hữu hạn 46 mã: chưa phủ mọi công nghệ (ví dụ công nghệ khác trong các danh sách raw), phiên bản sản phẩm, typo hoặc tên dính chữ. Không tự infer skill không có alias từ nghề hoặc vendor.
- Heading implicit/dính chữ, comma/conjunction và đoạn trộn task/qualification có thể làm scope required/preferred/task chưa chính xác. Quy tắc suffix/cue có giới hạn; ca nhận được cũng cần người đọc kiểm tra, không chỉ 96 hit mơ hồ.
- Ngữ cảnh của C/Go/R/Spark/framework/Oracle là quy tắc hẹp; có thể bỏ sót mention hợp lệ hoặc nhận nhầm trong câu phức tạp. Nhận Oracle Database không đồng nghĩa nhận mọi Oracle ERP/cloud sản phẩm.
- Có thể có false positive/negative kỹ năng ngoài fixture và những ví dụ đã đọc. Bảng hit chỉ giúp rà các đề cập đã nhận diện; để tìm FN cần đọc **toàn văn** cả tin có match và 27 tin zero-hit, bổ sung nhãn skill độc lập trước tính chất lượng.
- Normalization/source mapping đã kiểm tra trên fixture và mẫu; malformed HTML/ngôn ngữ/cấu trúc ngoài mẫu có thể cần PARTIAL/FAILED. Spark/JVM offsets, distributed execution và Parquet chưa xác minh.

Đọc lại bằng [review_skill_sample.csv](../data/analytics/a05_development_v0_1_2_20261014/review_skill_sample.csv): lọc mention_type bắt đầu AMBIGUOUS và review_required trong [review_jobs.csv](../data/analytics/a05_development_v0_1_2_20261014/review_jobs.csv), đối chiếu full description theo job_id, rồi điền manual_review_decision/note ở bản review riêng. Các cột đó hiện trống; chưa tự gán người/ngày duyệt skill hoặc coi bridge là nhãn chuẩn.

## 8. Hợp đồng cần TV1 phối hợp và tiêu chí A05

TV1 cần cung cấp **input D06 đã kiểm tra**, một dòng/job_id bigint non-null duy nhất, description string/null giữ nguyên nguồn hoặc ghi rõ phiên bản làm sạch, cùng it_decision=ACCEPT/is_it=true và taxonomy_version/taxonomy_sha256 string. Adapter từ chối thiếu provenance, duplicate/null key, schema khác hoặc lẫn REVIEW/REJECT; không âm thầm drop những hàng đó. TV1 chốt tên/path input, chính sách snapshot/cleaning, source field/hash và phạm vi CNTT đã xác nhận; A05 không tự xác nhận candidate A04 được nghiệm thu.

Trước lần chính thức: chuẩn bị Java 21/PySpark theo repo, port/run fixture và so kết quả Python–Spark trên cùng 105 khóa/dictionary bytes; xác minh schema/nullability, code point–UTF-16, alias/rule/evidence/mention types và zero-hit/missing/partial. Kiểm tra write/read ba bảng Parquet, grain/evidence FK, run/version, output thử mới; sau đó mới chạy A05 trên input D06 chính thức theo phạm vi được giao. Không dùng schema source function labels thay technical skills hoặc JOIN bridge explode để nhân số tin.

| Yêu cầu phân công A05 | Bằng chứng đã có | Phần còn thiếu |
| --- | --- | --- |
| F22/G22: Trích từ description, từ điển Python/Java/SQL/cloud, alias/ranh giới | Dictionary 46 mã có version/snapshot; extractor source-only, context/overlap; 37 fixture qua và chạy raw của 105 tin đã duyệt | Người rà soát skill xác nhận độ đúng/phạm vi dictionary; hoàn thiện các giới hạn nếu được phép |
| G22: Lưu nguồn trích xuất | source_field/hash, alias/quote/raw ranges/rule, dictionary/run/code hash; 661 evidence đối soát | Xác minh source mapping và bảo toàn evidence sau Spark/Parquet |
| I22: Kiểm tra C/C++, Java/JavaScript | Fixture các biến thể và nguồn thật; Objective- C đã sửa; .NET/Node.js/SQL Server được kiểm tra thêm | Rà thêm ca ngoài mẫu/ngôn ngữ/cấu trúc khác; không tuyên bố không còn FP/FN |
| I22: Mỗi skill chỉ đếm một lần/tin | 355/355 cặp job_id/skill_code duy nhất; giữ 561 accepted evidence; lặp Python vẫn một dòng bridge | Kiểm tra cùng grain/khóa run trên Parquet chính thức |
| H22: job_skill_technical.parquet | Adapter PySpark/schema/lệnh đã có; CSV/JSONL phát triển và helper Python đã kiểm tra | **Chưa có Parquet chính thức, chưa chạy Spark**; cần môi trường/input và xác minh thực thi TV1 |
| J22: D06 | Tách rõ raw/mẫu phát triển với canonical input; không đổi membership/taxonomy | TV1 bàn giao it_jobs/provenance đã xác nhận và chốt hợp đồng trước chạy chính thức |

Trạng thái đề nghị A05: **Đã có bản phát triển kiểm tra cục bộ; chờ D06, xác minh Spark/Parquet và rà soát nhãn skill.** Không ghi A05 100%, người/ngày nghiệm thu. Không thực hiện A06–A11 hoặc báo phân tích production.

Raw, workbook/nhãn/metadata A04, taxonomy active/candidate, trace và báo cáo A04 được giữ nguyên; chỉ tạo hiện vật A05 và bổ sung attributes phục vụ hash A05. Không chạy lại ETL, trích toàn dataset, thay môi trường hệ thống, commit hoặc push.
