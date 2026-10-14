# A02 – Thiết kế taxonomy CNTT

- Người thực hiện: **Đồng Viết Dũng – TV2**; ngày thiết kế: **07/10/2026**.
- Nhánh: `feat/tv2-analysis`; phiên bản nguồn tham chiếu: `2386394`.
- Cấu hình hiện hành: [config/it_taxonomy.json](../config/it_taxonomy.json), phiên bản **0.2.0**, cập nhật xử lý mô tả ngày **08/10/2026**. [Snapshot v0.1.0](../config/versions/it_taxonomy_v0.1.0.json) giữ exact bytes.
- Trạng thái: **đã kiểm tra implementation Python trên raw ở A04; chưa có đánh giá bằng nhãn tay, chưa xác minh parity Spark/JVM**. Nhóm nghề, alias, gate fallback, priority, include/exclusion và thiết kế seed42 giữ nguyên. Xem [changelog A02–A04](a02_a04_changelog.md) và [so sánh hai phiên bản](a04_v020_comparison.md).

## 1. Mục tiêu, nguồn và lựa chọn định dạng

Thiết kế bộ quy tắc nhận diện **nghề CNTT của tin tuyển dụng**, gán **một nhóm nghề chính** cho mỗi tin được xác định thuộc CNTT và giữ bằng chứng để TV1/TV2 kiểm tra. Mobile và Web là phân nhóm của Software. Kỹ năng công nghệ có thể đa nhãn nhưng do A05 cung cấp riêng.

Đã đọc [README](../README.md), [A01](a01_analysis_questions.md), [manifest](data_manifest.md), [data dictionary](data_dictionary.md), [D03](d03_data_quality_report.md), [D04](d04_cleaning_report.md), [D05 pre-check](d05_precheck.md), [D05 scaffold](d05_implementation_scaffold.md), [handoff](handoff/project_status.md), cùng các script reader/cast/JOIN. Bằng chứng schema và mapping được đối chiếu từ [inventory](../data/audit/table_inventory.csv), [missing profile](../data/audit/missing_profile.csv), [D04 schema](../data/audit/d04_schema_changes.csv), [35 nhãn nguồn](../data/audit/d05_precheck_skills.csv), [cardinality](../data/audit/d05_precheck_cardinality.csv) và [join coverage](../data/audit/d05_precheck_join_coverage.csv).

Khi thiết kế v0.1.0 ngày 07/10 checkout chưa có raw hoặc `.venv`. Hiện đã đọc thành công đủ 11 CSV trong `data/raw/`, có `.venv` Python 3.11.9 và trace A04; xem [kiểm chứng raw](tv2_raw_verification.md). Chưa có Parquet D04/canonical D05 và chưa có nhãn tay để báo precision, recall hoặc accuracy. **123.849 là tổng tin gốc, không phải số tin CNTT.**

Repo chưa có thư mục hay chuẩn cấu hình taxonomy. Chọn **JSON tại `config/`** vì Python của TV1 đọc được bằng thư viện chuẩn và dễ chuyển điều kiện thành biểu thức Spark; dùng **Markdown tại `docs/`** theo quy ước tài liệu hiện có để mô tả ngữ nghĩa và hợp đồng. JSON chứa danh sách alias/quy tắc đầy đủ và là nguồn cấu hình chuẩn; tài liệu này giải thích cách diễn giải, không có bảng từ khóa độc lập ghi đè JSON.

Các alias tiếng Anh/Việt là **đề xuất thiết kế**, chưa chứng minh đã xuất hiện trong dataset. Mẫu title `Medical Assistant` trong audit D04 chỉ xác nhận có tin ngoài CNTT, không chứng minh bộ lọc đạt chất lượng. Toàn bộ 57 ca trong `illustrative_cases` là **ví dụ minh họa tự tạo**, không phải mẫu dữ liệu thật hay kết quả A04.

## 2. Các khái niệm phải giữ riêng

| Khái niệm | Quy tắc A02 | Ví dụ minh họa |
| --- | --- | --- |
| Nhóm nghề chính | Một mã duy nhất cho tin `ACCEPT`, lựa chọn theo thứ tự ở mục 4 | `SOFTWARE`, `DATA_AI` |
| Phân nhóm | Một mã phụ chỉ khi nhóm chính là `SOFTWARE`; không đưa Mobile/Web lên thành nhóm chính | `SOFTWARE_MOBILE`, `SOFTWARE_WEB` |
| Kỹ năng công nghệ | Có thể nhiều nhãn; trích từ văn bản theo A05, chưa triển khai ở A02 | Một lập trình viên có thể nhắc Java, SQL, Docker |
| Nhãn chức năng nguồn | Giữ nguyên ý nghĩa/mã nguồn; không đổi thành nhóm nghề hoặc kỹ năng kỹ thuật | Audit thực có `IT` → `Information Technology`, `ENG` → `Engineering`, `ANLS` → `Analyst`, `QA` → `Quality Assurance` |
| Ngành nghề nguồn | Phân loại ngành của tin/doanh nghiệp; không tự xác định nghề của người được tuyển | Mapping raw đã kiểm chứng `4` → `Software Development` trong A03 |

Đã đọc đủ 35 nhãn audit; không có `skill_name` bằng Python, Java hoặc SQL. `job_skills` là bảng nhiều nhãn, không phải đầu ra trích kỹ năng công nghệ. Một kế toán hoặc recruiter tại doanh nghiệp phần mềm vẫn có thể là nghề ngoài CNTT. Vì vậy `metadata_policy.enabled_for_decision=false`: **nhãn `IT` hoặc ngành `Software Development` không đủ để đưa tin vào CNTT, và không được nối vào title/description để tạo bằng chứng giả**. A03 sẽ quyết định bản đồ JOIN và ngữ nghĩa nguồn; A02 không làm thay bước đó.

## 3. Nhóm nghề, phạm vi và từ khóa

Có **9 nhóm nghề chính** và **1 nhóm dự phòng `IT_OTHER`**. Số `priority` nhỏ hơn được ưu tiên khi cùng tầng bằng chứng. Mỗi nhóm có định nghĩa, phạm vi, `search_fields`, bộ alias title/hint, bộ hành động nghề và bộ ngữ cảnh trong JSON.

| Mã | Tên và phạm vi | Alias/ví dụ dấu hiệu đề xuất | Ưu tiên |
| --- | --- | --- | --- |
| `SECURITY` | An toàn thông tin và an ninh mạng: bảo vệ phần mềm/mạng/hạ tầng số, điều tra sự cố, kiểm thử xâm nhập; loại bảo vệ vật lý | `cybersecurity analyst`, `information security engineer`, `penetration tester`; `security analyst` cần nhiệm vụ cyber/SIEM | 10 |
| `DATA_AI` | Dữ liệu, AI và CSDL: pipeline/kho dữ liệu, quản trị CSDL, BI kỹ thuật, mô hình ML/AI | `data engineer`, `data scientist`, `machine learning engineer`, `database administrator`, `SQL developer`; data/BI analyst cần hành động kỹ thuật | 20 |
| `DEVOPS_CLOUD` | DevOps, cloud, độ tin cậy dịch vụ và nền tảng phần mềm | `devops engineer`, `site reliability engineer`, `cloud engineer`; `SRE`/`platform engineer` cần nhiệm vụ vận hành/triển khai | 30 |
| `QA_TESTING` | Kiểm thử/chất lượng phần mềm và API, thủ công hoặc tự động; loại QA sản xuất | `software tester`, `software test engineer`, `test automation engineer`, `SDET`; `QA engineer` cần nhiệm vụ kiểm thử phần mềm | 40 |
| `NETWORK_SYSTEMS` | Mạng máy tính, máy chủ, hệ điều hành và trung tâm dữ liệu | `network engineer`, `systems administrator`, `linux administrator`; `systems engineer` cần nhiệm vụ máy chủ/mạng | 50 |
| `SOFTWARE` | Thiết kế/lập trình/bảo trì phần mềm, gồm ứng dụng, Web, Mobile, firmware và embedded software | `software engineer`, `software developer`, `firmware engineer`, `lập trình viên`; developer/engineer chung cần hành động phát triển phần mềm | 60 |
| `IT_SUPPORT` | Hỗ trợ người dùng, thiết bị máy tính và sự cố phần mềm/hệ điều hành | `IT support specialist`, `desktop support engineer`; `technical support` cần nhiệm vụ máy tính/phần mềm | 70 |
| `IT_BUSINESS` | Phân tích yêu cầu, sản phẩm và quản lý dự án có đối tượng phần mềm/hệ thống thông tin | `IT business analyst`, `software product owner`, `software project manager`; product/project manager chung cần ngữ cảnh | 80 |
| `IT_MANAGEMENT` | Quản lý chức năng CNTT, đội phần mềm và kiến trúc giải pháp doanh nghiệp | `IT manager`, `software engineering manager`, `chief information officer`; engineering manager/architect/CTO chung cần ngữ cảnh | 90 |
| `IT_OTHER` | Nghề CNTT rõ nhưng chưa đủ bằng chứng phân nhóm chuyên môn; không phải nhóm cho mọi tin chưa hiểu | `IT specialist`, `information technology consultant`, `chuyên viên công nghệ thông tin` | 999, chỉ dự phòng |

`IT_BUSINESS` là phạm vi CNTT mở rộng đề xuất, cần TV2 xác nhận. Firmware/embedded **software** thuộc Software; thiết kế phần cứng, điều khiển công nghiệp thuần, UI/UX/graphic design thuần, giảng dạy, bán hàng công nghệ không mặc định được đưa vào tập. Các ranh giới này cần kiểm tra lại ở A04 và xác nhận trước tích hợp chính thức.

### Phân nhóm Software

| Mã | Phạm vi và điều kiện | Ưu tiên trong cùng tầng |
| --- | --- | --- |
| `SOFTWARE_MOBILE` | Title có vai trò Mobile/Android/iOS/Flutter/React Native, hoặc cùng đoạn mô tả có hành động phát triển ứng dụng di động và ngữ cảnh Mobile | 10 |
| `SOFTWARE_WEB` | Title có vai trò Web/front-end/back-end/full-stack, hoặc cùng đoạn mô tả có hành động phát triển web và ngữ cảnh Web | 20 |
| `SOFTWARE_OTHER` | Software đã được nhận diện nhưng chưa khớp Mobile/Web | 90, chỉ dự phòng |

Chỉ xét phân nhóm **sau khi nhóm chính đã là `SOFTWARE`**. Title có bằng chứng Web trực tiếp thắng nhiệm vụ Mobile chỉ trong mô tả; nếu title trực tiếp khớp cả Mobile và Web thì Mobile thắng theo priority, lưu cả hai quy tắc và cờ `MULTIPLE_SUBGROUP_CANDIDATES`. Đây là thứ tự phân xử đề xuất, không khẳng định Mobile quan trọng hơn Web. Các nhóm khác có `subgroup_code=NULL`.

## 4. Quy tắc quyết định và thứ tự ưu tiên

### 4.1. Tầng bằng chứng

| Tầng | Điều kiện | Mức ưu tiên |
| --- | --- | --- |
| `TITLE_DIRECT` | `title` chứa một **cụm vai trò cụ thể** trong `<nhóm>_titles`, có ranh giới; không cần mô tả khi title đã rõ | 10 |
| `TITLE_CONTEXT` | Title có vai trò/hint trong `<nhóm>_hints` **và** một đoạn description có hành động `<nhóm>_tasks` cùng đối tượng/công nghệ `<nhóm>_context` | 20 |
| `DESCRIPTION_ROLE_TASK` | Title thiếu hoặc **toàn bộ title** khớp `generic_exact_titles`; một đoạn description đồng thời có vai trò cụ thể, hành động, ngữ cảnh kỹ thuật và dấu hiệu vị trí/chủ thể `self_role_cues` | 30 |

Không tìm riêng “IT”, “Python”, “SQL” hay “Engineer” rồi đưa tin vào tập. Tier mô tả dùng điều kiện cùng đoạn để tránh nối nghề trong phần giới thiệu công ty với công nghệ ở phần khác. Nếu title là nghề cụ thể ngoài CNTT, description fallback không được dùng để ghi đè; các rule context vẫn có thể tạo xung đột, nhưng xung đột chuyển sang `REVIEW`.

Ở **v0.2.0**, phủ định được kiểm soát trong câu/mệnh đề; giới thiệu công ty, chủ thể đội khác, lương/quyền lợi/EEO và yêu cầu kiến thức được đánh dấu ngữ cảnh. `collaborate with` sau nhiệm vụ của chính vị trí không tự chặn nhiệm vụ đó; cộng tác đứng trước task cần cue chủ thể rõ, nếu không vẫn bị chặn. Title trực tiếp vẫn độc lập. Ngưỡng **500 Unicode code point sau chuẩn hóa** là giới hạn cửa sổ matching và tín hiệu đoạn chưa phân tách đầy đủ, không còn là ngưỡng xóa đoạn. Chính sách và regex ngữ cảnh nằm trong JSON; không bổ sung alias nghề.

### 4.2. Xử lý chữ viết tắt và từ mơ hồ

| Từ/nhãn | Cách xử lý |
| --- | --- |
| `IT` | Không tìm substring, không dùng token đứng riêng làm positive. `IT support specialist`/`IT manager` là cụm vai trò trong title. Title chỉ có `IT` hoặc `Information Technology` → `REVIEW` khi không có rule khác; đại từ “it” trong title dài không kích hoạt điều kiện này |
| `Engineer`, `Developer`, `Architect` | Cụm nghề cụ thể hoặc nhiệm vụ+đối tượng kỹ thuật. Civil/mechanical/electrical/application engineer chung không tự được nhận là Software |
| `Analyst`, `Data Analyst`, `BI` | Data/BI analyst cần nhiệm vụ pipeline, CSDL, mô hình hoặc BI kỹ thuật. SQL/Excel hoặc “analyze data” riêng lẻ chưa đủ; financial/marketing analyst có quy tắc loại trừ |
| `Support` | Phải là hỗ trợ máy tính/hệ điều hành/phần mềm; customer service và sales support không tự thuộc CNTT |
| `QA` | QA chung cần bằng chứng kiểm thử phần mềm; QA của food/manufacturing có dấu hiệu loại trừ. `SDET` là alias title cụ thể đã khai báo cùng tên đầy đủ `software development engineer in test` |
| `Sales` | Không biến sales engineer thành Software chỉ vì có Engineer/SQL hoặc làm tại doanh nghiệp phần mềm. Nếu còn có nhiệm vụ kỹ thuật đủ mạnh → `REVIEW` vì xung đột phạm vi |
| `SRE`, `DBA`, `CTO`, `CIO` | Token title ngắn này cần ngữ cảnh nhiệm vụ kỹ thuật; tên vai trò đầy đủ được xử lý theo bộ title/hint tương ứng. `chief information officer` là title trực tiếp, `chief technology officer` vẫn cần ngữ cảnh |

Các alias cụm như `BI developer`, `SQL developer`, `IT manager` được giới hạn trong title và coi là vai trò cụ thể theo thiết kế. Đây là quyết định từ điển của v0.1.0, cần kiểm tra A04; không suy ý nghĩa mọi chữ viết tắt mới gặp.

### 4.3. Quy tắc loại trừ

JSON khai báo `EX_HEALTH`, `EX_PHYSICAL`, `EX_COMMERCIAL`, `EX_EDUCATION` theo cụm title; `EX_PHYSICAL_CONTEXT` yêu cầu **cả** vai trò Engineer/QA/Architect **và** lĩnh vực vật lý/sản xuất trong cùng title. Các bộ từ chứa ví dụ medical assistant, nurse, civil/mechanical engineer, security guard, CNC/PLC programmer, recruiter, financial analyst, sales engineer, customer service representative và teacher/instructor.

Không dùng một câu phủ định như “no experience required”, từ “sales” trong description, tên ngành doanh nghiệp hoặc công nghệ công ty như quy tắc loại toàn bộ tin. Quy tắc loại trừ tìm vai trò của **title**, không quét rộng description. Tin giáo dục/bán hàng mang vai trò software rõ có thể đồng thời khớp positive và exclusion; khi đó phải review, không tự ép về một phía.

### 4.4. Thuật toán phân xử bắt buộc

1. Kiểm tra có các cột đầu vào, `job_id` không NULL và duy nhất; đây là điều kiện grain, không phải rule nhận diện nghề. Chuẩn hóa bản sao title/description và tạo đoạn, giữ nguyên trường nguồn.
2. Đánh giá **tất cả** rule đưa vào của nhóm, rule CNTT chung và rule loại trừ; lưu rule/alias/trường/đoạn đã khớp. Không chọn nhóm theo vị trí đầu tiên của keyword trong câu hoặc thứ tự mảng JSON.
3. Nếu có positive **và** exclusion → **`REVIEW`, `is_it=NULL`**, chưa có nhóm chính. Giữ ứng viên và bằng chứng hai phía với lý do `POSITIVE_EXCLUSION_CONFLICT`.
4. Nếu chỉ có exclusion → **`REJECT`, `is_it=false`**, lý do `OUTSIDE_IT_ROLE`, không có mã nhóm CNTT.
5. Nếu có nhóm chuyên môn → **`ACCEPT`, `is_it=true`**; chọn đúng một rule theo tuple tăng dần **`(tier_rank, group.priority, rule_priority, rule_id)`**. Lưu mọi nhóm ứng viên; nếu nhiều nhóm, thêm `MULTIPLE_GROUP_CANDIDATES`. Bằng chứng title rõ thắng description dù nhóm description có priority nhỏ hơn.
6. Nếu không có nhóm chuyên môn nhưng có `GENERAL_IT_TITLE` → **`ACCEPT`, nhóm `IT_OTHER`**. Nhóm này chỉ dành cho nghề CNTT đã rõ, không cho trường hợp membership chưa xác định. Không để rule CNTT chung thắng nhóm chuyên môn chỉ vì tier title cao hơn.
7. Nếu vẫn chưa có quyết định mà title thiếu, chứa hint mơ hồ, toàn bộ title là nhãn lĩnh vực, hoặc xử lý mô tả còn chưa đầy đủ → **`REVIEW`** với lý do tương ứng. Đoạn dài đã xử lý đầy đủ không tự gây REVIEW. Đoạn chưa rõ cấu trúc được giữ toàn văn và ghi `DESCRIPTION_PROCESSING_INCOMPLETE`; không coi thiếu là false.
8. Còn lại → **`REJECT` với `NO_IT_ROLE_EVIDENCE`**. Đây là “quy tắc hiện tại chưa tìm được bằng chứng nghề”, không phải kết luận chắc chắn ngoài CNTT; A04 phải lấy mẫu ở nhóm này để tìm bỏ sót.
9. Chỉ khi nhóm thắng là Software, chọn một phân nhóm theo **`(tier_rank, subgroup.priority, rule_priority, rule_id)`**; nếu không có rule phân nhóm thì dùng `SOFTWARE_OTHER`.

`REVIEW` được giữ riêng, chưa nằm trong tập CNTT đưa vào analytics và chưa âm thầm gộp với `REJECT`. Tin `ACCEPT` luôn có **một** nhóm chính; tin `REJECT`/`REVIEW` có mã nhóm NULL vì chưa thuộc tập nghề CNTT đã xác nhận. Kỹ năng đa nhãn không làm thay đổi quy tắc một nhóm chính.

Không tạo điểm confidence hoặc gắn số 0,9/0,95 cho tầng bằng chứng. Các priority là lựa chọn phân xử nghiệp vụ, không phải xác suất.

## 5. Chuẩn hóa, ranh giới và ngôn ngữ quy tắc

### Chuẩn hóa đồng nhất

- Kiểm tra missing sentinel sau trim/lower **trước** thay dấu `/`: NULL, chuỗi rỗng, `null`, `N/A`, `NA` là thiếu theo D03/D04. Giữ trạng thái thiếu; chỉ dùng chuỗi rỗng tạm thời nếu biểu thức Spark cần và phải giữ cờ missing riêng.
- Chuẩn hóa **Unicode NFC**, chuyển chữ thường, giữ dấu tiếng Việt; không bỏ dấu hoặc dùng fuzzy match ở phiên bản này. Title và alias phải qua cùng quy trình.
- Đổi dấu gạch nối Unicode/ASCII và `/` thành khoảng trắng; gộp whitespace Unicode bằng `whitespace_regex`. Vì vậy `Front-end`, `front end`, `CI/CD` được xử lý theo alias tương ứng. Giữ `+`, `#`, `.` để không biến C++, C#, .NET thành token khác.
- Description phải **tách cấu trúc trước khi gộp whitespace**. Mode `structured_source_v1` dùng HTMLParser, decode entity, bỏ nội dung script/style khỏi bản dẫn xuất; tách block/list/br, LF/CRLF/CR/U+2028/U+2029, bullet, heading có cấu trúc, câu và mệnh đề đối lập. Regex bảo vệ `.NET`, URL, phiên bản và viết tắt được ghi trong JSON. Câu dính bằng dấu chấm rồi chữ hoa có thể tách; chuỗi như `patternsParticipate` không tự suy ranh giới.
- **Giữ mọi đoạn text dẫn xuất**, bao gồm đoạn vượt 500. Đoạn dài chưa phân tách rõ có trạng thái `RETAINED_LONG_UNRESOLVED`, có thể xét cửa sổ cục bộ tối đa 500 code point quanh alias task nếu có cue chủ thể hoặc task dẫn đầu. Không nối qua câu/section hoặc dùng từ ở đoạn lương/quyền lợi. Phủ định và chủ thể trước cửa sổ vẫn được kiểm tra trong cùng mệnh đề để không mất blocker khi cắt cửa sổ.
- Section lương/quyền lợi/EEO/giới thiệu công ty/qualifications đã xác định được coi là xử lý đầy đủ nhưng không dùng làm evidence nghề tự động. Nếu còn đoạn chưa rõ hoặc parser/mapping có lỗi, ghi trạng thái chưa đầy đủ; không xóa nguồn. `split_pattern`/`blocked_term_sets` cũ chỉ còn vai trò tham chiếu thống kê v0.1.0 trong mode mới; `parser`, `context_policy`, `long_unit_policy`, `provenance` là chính sách hiện hành.

### Literal phrase có ranh giới

Mỗi alias được match như cụm literal, không phải regex do người nhập tùy ý. Tạo mẫu Java regex cho từng alias: ranh giới trái **`(?<![\p{L}\p{N}_])`**, các token escape bằng `java.util.regex.Pattern.quote` và nối bằng `\s+`, ranh giới phải **`(?![\p{L}\p{N}_])`**. Không dùng `contains('IT')`, `contains('java')` hoặc ghép alias chưa escape vào regex. Alias C++/C#/.NET phải được escape đúng.

`SoftwareEngineer` không khớp `software engineer`; `it` không khớp bên trong `digital`; `java` không khớp phần đầu `javascript` nhưng `javascript` có thể có alias riêng. Regex có ranh giới Unicode; TV1 cần kiểm tra parity trên JVM/Spark, nhất là dấu tiếng Việt, whitespace, dấu câu và NULL.

### Cấu trúc điều kiện JSON

| Operator | Ngữ nghĩa để TV1 chuyển thành biểu thức Spark |
| --- | --- |
| `any` | OR danh sách predicate không rỗng |
| `all` | AND danh sách predicate không rỗng |
| `match` | Trường chỉ định khớp ít nhất một alias trong `term_set` |
| `full_match` | Toàn bộ trường sau chuẩn hóa bằng một alias; dùng cho title chung, không chỉ tìm một từ trong title cụ thể |
| `is_missing` | Trường nguồn thiếu theo chính sách trên |
| `same_segment` | Trong cùng câu/mệnh đề/section hợp lệ hoặc cửa sổ cục bộ của một đoạn dài được giữ lại, mỗi bộ `all_term_sets` có ít nhất một alias; áp dụng actor/blocker theo `context_policy`, không ghép đoạn xa nhau |

`condition` chứa đúng một operator; operator lồng nhau có ngữ nghĩa rõ. Các term set, mã nhóm, parent và tier đều phải tồn tại; lỗi cấu hình phải chặn chạy, không tự bỏ qua rule. Các cấu trúc `match_shape`/`same_segment_shape` trong `rule_language` là mô tả schema, không phải rule được đánh giá.

## 6. Hợp đồng đầu vào/đầu ra bàn giao TV1

### Đầu vào đã có bằng chứng schema

Nguồn nền là `postings`: `job_id`, `title`, `description`. Ưu tiên `data/processed/clean/postings/` khi có D04; `job_id` là bigint, hai trường text là string theo audit. Không tìm nghề từ `companies.description`, toàn bộ title của bảng con hay tên ngành để thay title của tin.

Nếu đọc raw, dùng parser CSV hỗ trợ quote, dấu phẩy và newline như `src/audit_data.py`/`src/clean_data.py`; không dùng split dấu phẩy. Runtime dự án theo README: Python 3.11, Java 21, PySpark 4.2.0, local mode. A02 không cài môi trường hoặc chạy lại ETL.

Không cần JOIN skills/industries để chạy quy tắc text v0.1.0. Nếu TV1 bổ sung metadata phục vụ audit ở bước sau, phải theo A03, gom bảng cầu trước JOIN hoặc giữ bảng cầu riêng; không nhân số dòng. Giữ kiểm tra `assert_unique_key` và `check_grain_preserved` từ [d05_utils.py](../src/d05_utils.py).

### Các trường đầu ra **đề xuất**, chưa được TV1 thống nhất

Ngoài `job_id` nguồn, các trường sau là **tên/kiểu đề xuất**, không phải cột canonical đã tồn tại. Cấu hình lưu đầy đủ tại `proposed_output_contract`; chưa chốt đường dẫn Parquet.

| Trường đề xuất | Kiểu Spark đề xuất | Nội dung và invariant |
| --- | --- | --- |
| `job_id` | bigint, không NULL | Khóa nguồn; đúng một dòng/tin |
| `taxonomy_version`, `taxonomy_sha256` | string | Phiên bản và SHA-256 của chính bytes UTF-8 cấu hình để truy vết |
| `it_decision` | string | Chỉ `ACCEPT`, `REJECT`, `REVIEW` |
| `is_it` | boolean, nullable | true/false/NULL tương ứng ba quyết định; không biến NULL thành false |
| `primary_group_code` | string, nullable | Một mã hợp lệ, kể cả `IT_OTHER`, cho ACCEPT; NULL với REJECT/REVIEW |
| `subgroup_code` | string, nullable | Một trong ba phân nhóm Software nếu nhóm chính là Software; NULL ở nhóm khác |
| `candidate_group_codes` | array<string> | Các nhóm chuyên môn distinct đã khớp, theo thứ tự phân xử; có thể rỗng ở IT_OTHER/REJECT/REVIEW |
| `selected_rule_id` | string, nullable | Rule thắng cho ACCEPT; NULL với REJECT/REVIEW |
| `reason_codes` | array<string> | Lý do quyết định và cờ cần review; phân biệt thiếu, mơ hồ, xung đột và không tìm thấy bằng chứng |
| `matched_rule_ids` | array<string> | Toàn bộ rule positive/general/exclusion đã khớp; rule phân nhóm chỉ xét cho Software |
| `match_evidence` | array<struct> | `rule_id`, `field`, `term_set_id`, `matched_alias`, `segment_index`, `excerpt`; chi tiết struct trong JSON |

`matched_alias` là alias thực sự đã khớp sau chuẩn hóa, không chỉ tên bộ từ. Với predicate AND/same_segment phải ghi bằng chứng cho từng bộ từ thành phần. `segment_index` bắt đầu từ 0 trên `description_segments` của **đúng phiên bản**, NULL cho title; không so trực tiếp index giữa hai phiên bản. v0.2 thêm section/actor/status, `description_processing`, `raw_match_ranges`, offset excerpt raw và tọa độ normalized/derived được đặt tên riêng. HTML/entity/NFC/whitespace đều có ánh xạ về raw; nếu không ánh xạ được thì không phát evidence tự động hoặc nhận offset derived là raw. `excerpt` là lát cắt raw tối đa 240 code point; `excerpt_covers_all_match_ranges=false` nếu markup dài khiến excerpt không chứa hết hit; full raw và toàn bộ match ranges vẫn được giữ. Struct Spark mới vẫn là đề xuất chờ TV1.

Giữ nguyên `title` và `description` nguồn. Không explode kỹ năng trên bảng kết quả phân loại; A05 sẽ bàn giao kỹ năng đa nhãn riêng. Không đổi `job_skills.skill_abr` thành `technical_skills` hoặc suy ra kỹ năng từ nhóm nghề. Nhãn/ngành nguồn giữ tên riêng theo A03.

### Điều kiện tích hợp

TV1 load JSON một lần, xác minh phiên bản/tham chiếu, chuẩn hóa alias một lần và chuyển predicate thành biểu thức Spark; không hardcode lại bảng alias khác. Kết quả phải giữ số dòng và distinct job_id của đầu vào, đủ cả ba quyết định. Chỉ tạo tập analytics từ ACCEPT sau khi TV2 kiểm tra A04; giữ REVIEW và REJECT để đối soát.

Tên hàm chuẩn hóa, cách dùng biểu thức/UDF, vị trí lưu output và cấu trúc trace cần TV1 xác nhận. A02 bàn giao thiết kế; **không thay thế A03 để mở D05 official**, không khẳng định canonical hoặc bộ lọc production đã được tạo.

## 7. Hướng dẫn kiểm tra A04 bằng 100–200 tin

Mẫu phát triển **160 `job_id` duy nhất**, seed **42**, đã được tạo bằng v0.1.0 trong A04 tại `data/analytics/a04_manual_seed42/`; giữ nguyên mẫu và mọi nhãn người đọc. Không lấy lại mẫu theo v0.2.0. Bảng dưới là kế hoạch/quota cũ được giữ để đối soát. Các ca thay đổi v0.2 có bản đọc bổ sung riêng, không phải mẫu đánh giá cuối.

| Tầng mẫu không giao nhau | Mục tiêu | Nội dung cần kiểm tra |
| --- | --- | --- |
| ACCEPT một nhóm, không thuộc tầng đặc biệt bên dưới | 50 | Title trực tiếp, title có ngữ cảnh và description fallback; phủ các nhóm nghề |
| ACCEPT nhiều ứng viên hoặc Software Mobile/Web | 30 | Ưu tiên giữa nhóm, Software có phân nhóm, title/mô tả khác nhau; gồm IT_OTHER ở phần accepted nếu có |
| REJECT do exclusion | 30 | QA sản xuất, kỹ sư vật lý, bán hàng, tài chính, support/HR/y tế/giáo dục; có tin nhắc công nghệ |
| REJECT do không tìm thấy bằng chứng | 20 | Lấy ngẫu nhiên theo hash để tìm bỏ sót alias/ngôn ngữ/vai trò mới; nếu metadata sau A03 có IT/Software Development thì đưa một phần vào kiểm tra |
| REVIEW | 30 | Title mơ hồ, title thiếu, positive–exclusion xung đột, đoạn quá dài, chỉ có chữ IT hoặc công nghệ |

Phân tầng theo thứ tự: xác định ACCEPT đặc biệt trước; phần ACCEPT còn lại là tầng một nhóm; REJECT chia theo lý do; REVIEW riêng. Nếu IT_OTHER không có ứng viên nhóm chuyên môn thì vẫn thuộc ACCEPT còn lại. Mỗi tin chỉ vào một tầng. Không lấy cùng tin nhiều lần do một tin có nhiều kỹ năng/ngành hoặc nhiều rule.

Các bước đề xuất cho A04:

1. Khóa phiên bản/hash JSON và phiên bản dữ liệu. Lưu quy mô từng tầng trước lấy mẫu; kiểm tra các tầng không giao nhau và toàn bộ khóa mẫu distinct.
2. Trong từng tầng, sắp xếp bằng SHA-256 của chuỗi `42:<job_id đã chuẩn hóa>`, sau đó `job_id` để phân xử; chọn theo quota. Không phụ thuộc thứ tự file/partition. Hướng dẫn này là cơ chế lấy mẫu đề xuất, chưa phải script A04.
3. Trong 80 tin ACCEPT, cố gắng có ít nhất 4 tin cho mỗi nhóm chuyên môn và ít nhất 5 tin cho mỗi phân nhóm Mobile/Web nếu có đủ dữ liệu; cố gắng có IT_OTHER, description-only, acronym và ca nhiều nhóm. Nếu tầng/nhóm hiếm không đủ quota, ghi số thực tế và chuyển phần thiếu có lý do; tổng mục tiêu vẫn 100–200 khi dữ liệu cho phép, không nhân bản để đủ mẫu.
4. Tạo bảng nhãn tay **đề xuất** gồm `job_id`, title, description đủ nội dung, quyết định máy/nhóm/rule/evidence, `manual_is_it` (true/false/NULL), `manual_primary_group_code`, `manual_subgroup_code`, `manual_reason`, người/ngày review. Vòng nhãn tay đầu nên ẩn quyết định máy để giảm thiên lệch. Dùng nguyên bản mô tả khi quyết định; excerpt không thay thế nội dung đầy đủ.
5. TV2 xác định nghề thực dựa trên title và nhiệm vụ, ghi câu bằng chứng. Với ca không đủ thông tin, giữ nhãn tay chưa xác định thay vì ép true/false. Nhờ TV1 hoặc một reviewer thứ hai đối chiếu các ca tranh chấp và một phần mẫu; ghi cách thống nhất nhãn.
6. Lập bảng đối soát theo decision và nhóm: false positive ở ACCEPT, tin CNTT bị bỏ sót trong REJECT, sai nhóm chính/phân nhóm, ca unresolved. Ghi lỗi do alias, ranh giới, ngữ cảnh, boilerplate, exclusion hoặc ưu tiên để sửa đúng rule.
7. Nếu báo precision/recall trên mẫu sau khi có nhãn tay, ghi rõ mẫu số và các ca chưa xác định. Mẫu phân tầng này phục vụ tìm lỗi và không đại diện ngẫu nhiên cho toàn dataset; không báo accuracy/toàn thị trường từ tỷ lệ trên 160 tin. Muốn ước lượng toàn tập cần thiết kế lấy mẫu/trọng số và nhãn bổ sung.
8. Tách mẫu phát hiện lỗi và mẫu đối soát sau sửa; tăng phiên bản cấu hình khi thay đổi rule/alias/priority. Không tuyên bố đã đạt chỉ từ việc các ví dụ minh họa vẫn khớp.

A04 phải kiểm tra các ca **bị loại**, không chỉ các tin được chọn. Các chuỗi title/description dài, thiếu hoặc chỉ nhắc công nghệ cần được kiểm tra dù cấu hình trả về REJECT/REVIEW. Không suy rộng kết quả mẫu ra thị trường Việt Nam.

## 8. Kiểm tra thiết kế đã thực hiện

- JSON được parse thành công; có **9 nhóm chuyên môn + IT_OTHER**, **3 phân nhóm Software**, **37 rule**, **54 bộ từ**. Mã nhóm/phân nhóm/rule và priority tương ứng không trùng; parent, tier, trường và term set tham chiếu hợp lệ. Các alias không trùng sau chuẩn hóa trong từng bộ từ.
- Đầu vào `job_id`, `title`, `description` đối chiếu với inventory thực đã lưu. Không giả định tên cột mới hoặc khóa JOIN chưa khảo sát.
- **57 ví dụ minh họa tự tạo** trong JSON đã được đối chiếu bằng bộ diễn giải kiểm tra tạm thời trên PowerShell/.NET; các quyết định/nhóm/phân nhóm khớp hợp đồng thiết kế. Việc này kiểm tra tính nhất quán của quy tắc và ưu tiên, **không đo accuracy** và không chứng minh hiệu quả trên dataset.
- v0.2 đã có test Python và chạy trên raw trong A04; **chưa xác minh parity JVM/Spark**. TV1 cần chạy ca minh họa, ca ngữ cảnh, parser và ánh xạ nguồn trên runtime tích hợp; đặc biệt thống nhất Unicode code point với UTF-16, không dùng kết quả Python thay cho kiểm tra tích hợp.
- Không thay đổi A01, data/raw, các script ETL hoặc audit D03–D05. Không chạy Spark/ETL, tạo canonical, commit hay push trong A02.

Có thể kiểm tra nhanh cấu trúc mà không khởi động Spark bằng PowerShell:

```powershell
$taxonomy = Get-Content -LiteralPath config/it_taxonomy.json -Raw -Encoding UTF8 | ConvertFrom-Json
$taxonomy.groups | Select-Object code, priority, name_vi
$taxonomy.subgroups | Select-Object code, parent_code, priority
$taxonomy.groups | Group-Object code | Where-Object Count -GT 1
$taxonomy.groups | Group-Object priority | Where-Object Count -GT 1
```

Hai lệnh cuối phải không có kết quả. Khi có `.venv`, TV1 cũng có thể dùng `json.load` của Python 3.11 để load, xác minh tham chiếu/priority và chạy các ví dụ bằng bộ diễn giải Spark của mình; không cần chạy lại ETL để kiểm tra JSON.

## 9. Những điểm TV2/TV1 cần xác nhận

1. **Phạm vi nghề:** có giữ IT_BUSINESS, BI/data analyst kỹ thuật và firmware/embedded software trong CNTT không; ranh giới UI/UX thuần, phần cứng/PLC, giảng dạy, bán hàng kỹ thuật và các vai trò chưa phủ.
2. **Phân xử:** thứ tự 9 nhóm khi cùng tầng, Mobile trước Web khi title cùng khớp, nhóm IT_OTHER và việc đưa xung đột vào REVIEW. Đây là lựa chọn rõ ràng của thiết kế v0.1.0 nhưng chưa có kiểm tra trên dữ liệu thật.
3. **Hợp đồng kỹ thuật:** tên/kiểu/path đầu ra, lưu evidence/segment index, hash và phiên bản; cách chuẩn hóa NFC/Unicode và chuyển điều kiện thành Spark với cùng ngữ nghĩa.
4. **Dữ liệu/A04:** cung cấp raw hoặc ưu tiên Parquet D04, xác nhận ngôn ngữ và các alias thực gặp; kiểm tra boilerplate, phủ định, ngưỡng 500 ký tự, thiếu dữ liệu và các nhóm hiếm bằng mẫu 100–200 tin.
5. **Metadata/kỹ năng:** A03 còn phải xác nhận ngữ nghĩa và JOIN; A05 còn phải trích kỹ năng đa nhãn. Không bật metadata như bằng chứng duy nhất hoặc tự công bố chất lượng bộ lọc trước các bước kiểm tra.

Thiết kế này bàn giao được để review và chuẩn bị tích hợp; các xác nhận trên không được coi là đã hoàn thành hoặc phê duyệt production chỉ vì JSON hợp lệ.
