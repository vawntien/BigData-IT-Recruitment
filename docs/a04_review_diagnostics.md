# A04 – Chẩn đoán REVIEW và bằng chứng mô tả bị bỏ

Đồng Viết Dũng – TV2; kiểm tra ngày **08/10/2026**, nhánh `feat/tv2-analysis`. Đây là chẩn đoán trace **taxonomy v0.1.0**, không phải nhãn chuẩn hoặc đánh giá chất lượng nghề. Không đổi taxonomy, interpreter, phạm vi nghề, ngưỡng 500, trace cũ, mẫu seed42 hay nhãn người đọc. Không chạy ETL hoặc tạo phiên bản dự đoán mới.

## Kết luận và nguồn kiểm tra

**Chưa phát hiện lỗi implementation so với JSON trong các điều kiện được kiểm tra.** Nguyên nhân chính của REVIEW nhiều là thiết kế: bỏ nguyên đoạn vượt 500 ký tự rồi chuyển tin không có rule đưa vào/loại trừ sang REVIEW, kể cả đoạn đó là lương, quyền lợi hoặc công việc ngoài CNTT. Zero `DESCRIPTION_ROLE_TASK` là vấn đề riêng: gate title rất hẹp và yêu cầu bốn bộ từ cùng đoạn rất khó đáp ứng. Không thể giải quyết zero này chỉ bằng tăng ngưỡng độ dài.

Đã kiểm tra **123.849 dự đoán** trong `data/analytics/a04_taxonomy_v0_1_0_seed42/all_predictions.jsonl.gz`; đọc toàn văn **20 tin thật**, gồm **19 tin mang cờ** (13 REVIEW, 3 ACCEPT, 3 REJECT) và một ACCEPT không mang cờ để đối chứng. Title/description của cả 20 tin được đối chiếu lại CSV raw bằng parser multiline. Các nhận xét về nội dung bên dưới giải thích đường đi của rule, **không gán nhãn CNTT/ngoài CNTT hoặc nhóm chuẩn**.

Nguồn và hiện vật:

- [JSON A02](../config/it_taxonomy.json), [interpreter](../src/it_taxonomy.py), [hướng dẫn A04](a04_manual_labeling.md).
- [Script chẩn đoán](../src/diagnose_a04.py): đo đoạn trên trace hiện có, kiểm tra điều kiện fallback ở mọi tin qua gate; không viết vào mẫu cũ. Phiên bản chẩn đoán trong lần này: `a04-review-diagnostics-20261008.1`.
- [Summary kiểm tra toàn trace](../data/audit/tv2_a04_review_diagnostics.json).
- Thư mục riêng `data/analytics/a04_diagnostics_v0_1_0_20261008/`: `per_job_diagnostics.csv`, `real_job_specimens.json` (18 tin), `description_gate_task_examples.json` (2 tin), `diagnostics_summary.json`, `protected_before.json`. JSON specimens giữ **toàn văn**, offset nguồn `[raw_start, raw_end)`, segment index tính từ 0, số ký tự/từ, alias khớp, trạng thái bỏ/chặn, gate và rule; không điền nhãn người đọc.
- [Kiểm tra hồi quy](../src/test_a04_segmentation.py) và [kiểm tra A04 hiện có](../src/test_tv2_a04.py); [kết quả bảo toàn hiện vật/kiểm thử](../data/audit/tv2_a04_diagnostics_validation.json).

Hash exact bytes để xác định đúng nguồn, không suy phiên bản từ tên file:

| Hiện vật | SHA-256 |
| --- | --- |
| Taxonomy v0.1.0 | `99523fff775fc302507638b532491275c3bec54d2d38354ce329f574943c8278` |
| `src/it_taxonomy.py` | `453bb6bcd22d4cdf866c670f3634b8f1e42a233eb086b650e579b4b1d429dc86` |
| Trace gzip đầy đủ | `8bccbf9ed92db4105f4539d1ca6eb0d7a069d60d717545697b07f1666be221d5` |

## Ngưỡng 500 và tách đoạn đang hoạt động thế nào

`classify()` tách **description gốc trước khi gộp whitespace**; mỗi đoạn được NFC/lower, replacement dấu gạch/slash, gộp whitespace và trim. Điều kiện là `len(value) > max_normalized_characters`, với giá trị JSON bằng **500**. Trong Python, đây là **số Unicode code point của từng đoạn sau chuẩn hóa**, không phải số từ, byte, token hoặc độ dài toàn description. Đúng 500 vẫn được xét; 501 bị bỏ toàn bộ khỏi danh sách đoạn dùng cho `same_segment`. Không cắt giữ 500 ký tự đầu. Raw/full text trong trace và bản đọc thủ công vẫn nguyên vẹn.

NFC có thể gộp ký tự tổ hợp; `lower()` có thể đổi số code point. Python code point khác UTF-16 `String.length()` của JVM khi có emoji/ký tự ngoài BMP. Đây là điểm **cần quy định đơn vị và kiểm tra parity khi TV1 tích hợp JVM**, chưa có bằng chứng implementation Python trái JSON; không tự đổi đơn vị trong lần này.

Regex cấu hình:

```text
(?:\r?\n)+|[.!?;](?:[\p{Z}\s]+|$)
```

| Dạng dữ liệu | Hành vi thực tế và giới hạn |
| --- | --- |
| LF, CRLF, nhiều newline | Tách đúng trước collapse; test xác nhận LF/CRLF tương đương. Trong trace thật: 118.521 description có LF; không thấy CRLF hoặc CR đơn. Vì vậy CRLF được kiểm tra hồi quy, không quy là nguyên nhân dataset này. |
| Dấu `. ! ? ;` | Chỉ tách khi theo sau bởi whitespace hoặc cuối chuỗi. `sentence.Next` không tách; giữ `.NET`, nhưng văn bản bị nối câu/danh sách có thể thành đoạn rất dài. |
| Bullet và heading | `·`, `•`, heading có `:` hoặc các mục nối như `patternsParticipate` không tự tạo ranh giới. Ví dụ `.·` cũng không đáp ứng regex. |
| CR đơn, U+2028/U+2029 | Không tự tách như newline; có thể bị gộp thành khoảng trắng khi normalize. Có 22 tin chứa U+2028/U+2029, 12 mang cờ; không phải nguyên nhân của hàng chục nghìn tin. |
| HTML/entity | Không có HTML parser/entity decode. `<br>`, `<p>`, `<li>` không thành ranh giới; tag/CSS tham gia đếm ký tự, `; ` trong CSS còn có thể tạo các đoạn giả. Regex dò tag tìm 21 tin, 16 mang cờ; dò entity tìm 194 tin, 134 mang cờ. Đây là số dò định dạng, không phải kiểm chứng DOM đầy đủ. |
| Không LF/CR | 5.328 tin; 3.421 mang cờ. Có tin toàn description thành một đoạn vì các câu nối bằng dấu chấm không có whitespace. Tin có LF vẫn có thể có một dòng quá dài: 67.729 tin mang cờ có LF. |

Dò `[.!?;]` ngay trước chữ tìm 92.902 tin, trong đó 60.491 mang cờ. **Không coi tất cả là ranh giới câu bị mất**: cùng mẫu dò cũng có thể là URL, tên công nghệ hoặc viết tắt. Những trường hợp nối nhiệm vụ thực sự được đọc ở bảng job_id bên dưới.

## Cờ dài ảnh hưởng REVIEW ở đâu

Đếm trên **toàn bộ raw**, không phải tập CNTT có nhãn chuẩn:

| Trạng thái dự đoán | Tổng tin | Tin mang cờ bỏ đoạn |
| --- | ---: | ---: |
| ACCEPT | 5.102 | 3.249 |
| REJECT | 41.555 | 8.070 |
| REVIEW | 77.192 | 59.831 |
| Tổng | 123.849 | **71.150** |

Phân rã **59.831 REVIEW mang cờ** thành các tổ hợp không giao nhau:

| Reason codes | Tin |
| --- | ---: |
| Chỉ `DESCRIPTION_SEGMENT_SKIPPED` | **29.496** |
| `AMBIGUOUS_TITLE_WITHOUT_CONTEXT` + cờ | **30.327** |
| `POSITIVE_EXCLUSION_CONFLICT` + cờ | **8** |

Code khởi tạo `reasons` với cờ dài; sau khi không có rule đưa vào/loại trừ, dùng `REVIEW if reasons else REJECT`. Điều này đúng thứ tự quyết định trong JSON. **29.496 là số tin được REVIEW chỉ bởi chính sách này**, không phải số CNTT bỏ sót. 30.327 tin còn có title mơ hồ; 8 tin còn có xung đột. Không thể cộng các reason độc lập hay quy toàn bộ REVIEW cho việc mất nhiệm vụ.

Có 3.522.729 đoạn chuẩn hóa không rỗng, trong đó **118.943** vượt ngưỡng. Những đoạn bị bỏ chứa tổng **101.426.742 code point chuẩn hóa**; tổng các đoạn là 457.917.954. Đoạn dài: min 501, median 726, p90 1.333, max 8.051. Đây là độ dài đoạn, không phải bản ghi hoặc dòng vật lý CSV.

Đối với `TITLE_CONTEXT`, tìm lại các bộ task/context trong đoạn bị bỏ, đồng thời kiểm tra title hint của đúng rule: **133 tin** có bộ từ cùng đoạn dài; **61** còn không bị blocker; **30** trong 61 đang REVIEW. Những số này chỉ nhận diện bằng chứng literal bị bỏ theo rule hiện hành, **không phải 30 nhãn CNTT, cũng không bao quát mọi cách diễn đạt nhiệm vụ kỹ thuật**. Không tạo dự đoán thay thế hay suy chỉ số từ phép dò này.

## Vì sao không có DESCRIPTION_ROLE_TASK

Chín rule `*_DESCRIPTION` đều yêu cầu:

1. Title thiếu **hoặc toàn bộ title chuẩn hóa** nằm trong `generic_exact_titles` (16 alias). Chứa riêng chữ Engineer/Analyst/Developer trong title dài không đủ.
2. Cùng một đoạn có cả **alias nghề cụ thể + alias hành động + ngữ cảnh kỹ thuật + self_role_cues**.
3. Đoạn không quá 500 và không khớp bất kỳ alias `negation_or_collaboration`.

Không có title thiếu. Chỉ **205/123.849** tin qua gate exact-title; 107 mang cờ dài. Trong 205: REVIEW 159, REJECT 45, ACCEPT 1 (ACCEPT này dùng `IT_SUPPORT_CONTEXT`).

Đã tìm cả trong các đoạn dài/bị chặn. Kết quả từng rule dưới đây là **số tin**, không phải số hit; cột nghề/task/context cho phép hit ở bất kỳ đoạn nào. Self-role cue có ở 90/205 tin. Vẫn không tin nào đủ bốn bộ ngay cả khi cho chúng nằm ở các đoạn khác nhau.

| Rule DESCRIPTION | Có alias nghề | Có alias task | Có context | Đủ cả bốn ở bất kỳ đoạn nào | Đủ cùng đoạn trước length/block |
| --- | ---: | ---: | ---: | ---: | ---: |
| SECURITY | 0 | 0 | 4 | 0 | 0 |
| DATA_AI | 3 | 0 | 51 | 0 | 0 |
| DEVOPS_CLOUD | 0 | 0 | 27 | 0 | 0 |
| QA_TESTING | 0 | 0 | 88 | 0 | 0 |
| NETWORK_SYSTEMS | 0 | 0 | 14 | 0 | 0 |
| SOFTWARE | 4 | 1 | 96 | 0 | 0 |
| IT_SUPPORT | 0 | 1 | 56 | 0 | 0 |
| IT_BUSINESS | 0 | 0 | 57 | 0 | 0 |
| IT_MANAGEMENT | 1 | 0 | 48 | 0 | 0 |

Trace lưu **mọi rule khớp**, không chỉ rule thắng. Không có rule DESCRIPTION khớp rồi bị ưu tiên title che mất hoặc bị conflict đổi thành REVIEW. Đối chiếu điều kiện trên mọi tin qua gate đều nhất quán với `matched_rule_ids` của trace. Test tổng hợp với title `Specialist` và câu “We are seeking a software engineer to develop software in Java.” đi được tới `SOFTWARE_DESCRIPTION`, nên nhánh code vẫn chạy được.

Hai ca truy vết đủ task trong gate:

- **3905288395 – Developer, REVIEW**: đoạn 14 đúng **501 code point, 68 từ**, có `Develop applications`, `Work with` và `Collaborate with`. Bị loại do dài và, nếu chỉ nới độ dài, vẫn bị blocker. Toàn description không có alias `software_titles`; cue `this role` nằm ở đoạn lương 18, không phải đoạn nhiệm vụ. Vì vậy bỏ ngưỡng/blocker riêng lẻ vẫn không làm rule DESCRIPTION đạt đủ điều kiện. `SOFTWARE_CONTEXT` cũng mất đoạn task này.
- **3900956939 – Support Engineer, ACCEPT TITLE_CONTEXT**, ca đối chứng không có cờ: đoạn 13 dài **337**, có `Troubleshoot software issues` và software context; `IT_SUPPORT_CONTEXT` khớp. Không có alias `support_titles` trong mô tả. `you will` nằm ở đoạn giới thiệu 5, cách đoạn task; nhắc đội “Software Developers, Data Engineers, and System Engineers” không đồng nghĩa nghề của người được tuyển, và dạng số nhiều không tự khớp alias singular bounded. Zero DESCRIPTION trong ca này do yêu cầu nghề/cue, không do độ dài.

## Những tin mang cờ đã đọc

`sN` là segment index từ 0; độ dài là code point **sau normalize**. ACCEPT/REJECT/REVIEW là dự đoán cũ. Bảng lưu chẩn đoán, không phải nhãn chuẩn hoặc khuyến nghị tự chấp nhận tin.

| job_id / title | Dự đoán | Đoạn bị bỏ và nội dung đọc được | Vị trí trong đường đi rule |
| --- | --- | --- | --- |
| **3891072754** – Lead Developer (Mobile Apps/Flutter) | REVIEW | s2 **1.204**, 153 từ: `test, and develop software`, Flutter/C#/React; nhiệm vụ nối bằng `team.Collaborating`, `features.Analyze`. | Có task/context của SOFTWARE_CONTEXT trong đoạn bị bỏ, nhưng còn blocker `collaborating with`. Gate DESCRIPTION không qua title dài. Mô tả nhiệm vụ thực sự bị bỏ khỏi matcher. |
| **3902328365** – Principal Application Engineer (CD/CD) | REVIEW | s15 **1.179**: `Help project teams build applications`, pipeline/CI/CD; các mục nối `patternsParticipate`, `qualityEnable`. s16 831 cũng bị bỏ. | SOFTWARE_CONTEXT có task/context trong s15 nhưng bị dài và `working with`/`collaborate with`. Title không qua gate DESCRIPTION. Cần phân biệt hỗ trợ đội khác với nhiệm vụ của vị trí; không tự gán DevOps. |
| **3891008882** – User Interface Architect | REVIEW | s2 **541**, 81 từ: `Decent knowledge of .net technologies to implement APIs and deploy them in azure cloud`; `.·` và bullet không tách. | SOFTWARE_CONTEXT có `implement APIs` + `.NET`/APIs, không blocker; bằng chứng kỹ thuật này bị bỏ. Đoạn viết dưới dạng yêu cầu kiến thức, cần người đọc xác định vai trò; không tự mở rộng UI/UX thuần. Gate DESCRIPTION không qua. |
| **3903449638** – Privacy Engineer | REVIEW | s1 **515**, 78 từ: đội `seeks to build software services` rồi `In this role you will...`; `landscape.In` nối câu. | SOFTWARE_CONTEXT đủ task/context literal trong đoạn dài, không blocker; actor của `build software` là đội trong phần giới thiệu nên phải đọc ngữ cảnh. Có phần khác nói `What this position is not:Security engineering...`; không suy SECURITY. Gate DESCRIPTION không qua. |
| **3905674215** – Associate | REVIEW | s7 **833**, 103 từ: thư từ/điện thoại/onboarding/tablet/công việc văn phòng. | Qua gate generic nhưng không có bộ role/task CNTT. Lý do REVIEW chỉ là cờ dài; dùng tablet không xác định nghề IT. |
| **3900080548** – Consultant | REVIEW | s2 **992**: code reviews, UI/system design; s4 **1.088**: Tableau/database design/thu thập dữ liệu. | Có phần kỹ thuật bị bỏ, nhưng không đủ alias role/task/self cue hiện tại. s4 còn `work with`/`working with`. Qua title gate nhưng tăng 500 riêng lẻ không cứu được fallback. |
| **3901950685** – Associate | REVIEW | s4 **575**: underwriting đầu tư bất động sản; s7 **681**: ARGUS/Excel và yêu cầu chuyên môn. | Gate generic đúng, thiếu role/task CNTT. Cờ dài duy nhất; công cụ không đủ xác định nghề. |
| **3906203084** – Director Of Nursing ( RN ) | REVIEW | s9 **691**: license RN, chăm sóc dementia, ngân sách điều dưỡng; `working with`. | Cờ dài duy nhất. `nursing` không tự khớp alias literal `nurse` nên EX_HEALTH không bắt title này. Đây là hạn chế coverage alias, không phải lỗi boundary; không tự thêm alias hoặc điền nhãn. |
| **3905305242** – Community Mortgage Bank Sales Consultant | REVIEW | s8 **516**: xử lý khoản vay; s17 **1.042**: yêu cầu kinh nghiệm vay/bán hàng. | Consultant gây ambiguous title; không full-match generic. Không thấy bộ task/context CNTT trong đoạn bị bỏ. |
| **3906224755** – Senior Visualization Engineer | REVIEW | s19 **1.270**, 195 từ: analytics, dashboards, thu thập dữ liệu; s22 **824**: SQL/Tableau queries. | Có nội dung kỹ thuật bị bỏ nhưng không đủ cụm task hiện tại; Engineer trong title dài không qua gate DESCRIPTION. Không tự gán DATA_AI. |
| **3901349949** – Crisis Program Manager | REVIEW | s8 **1.163**: chăm sóc trị liệu/tuân thủ mental health; s12 **1.159**: giấy phép chuyên môn lâm sàng. | Cờ dài duy nhất. Nhắc EMR không biến nhiệm vụ thành CNTT; đoạn dài có thể là nghiệp vụ khác. |
| **3901934857** – Systems Administrator | ACCEPT | s5 **1.079**: servers/network/virtualization/AD/backups; s6 **591**: qualifications. | Nhiệm vụ bị bỏ thật nhưng `NETWORK_SYSTEMS_TITLE` đủ ACCEPT; không phải mọi cờ dài đều đổi quyết định sang REVIEW. |
| **3901348414** – Mainframe/COBOL Software Engineer | ACCEPT | s8 **550**: COBOL/JCL/VSAM/DB2/IMS và kỹ năng giao tiếp. | `SOFTWARE_TITLE` thắng. Đoạn dài chủ yếu yêu cầu kỹ năng; các nhiệm vụ ngắn đầu mô tả vẫn còn. |
| **3895547790** – Database Administrator 4 | ACCEPT | s4 **646**: production database/data lake/SQL Server; s8 **509**: qualifications. | Nhiệm vụ bị bỏ nhưng `DATA_AI_TITLE` đủ quyết định. |
| **3902916761** – Virtual Critical Care Registered Nurse - Pulse Center - Full Time - Nights | REJECT | s11 **507**: license RN/BSN/BLS. | `EX_HEALTH` khớp title; bỏ đoạn qualification không chặn exclusion. Nhắc kỹ năng công nghệ ở nơi khác chưa phải nghề CNTT. |
| **3895536438** – Oncology Account Manager - West Region (Remote) - 24-126 | REJECT | s13 **909**, s14 **770**: nhiệm vụ khách hàng oncology; s17 **1.305**: yêu cầu sales/marketing. | `EX_COMMERCIAL` khớp title; CRM không đủ nghề CNTT. Có `our company`/`working with` trong đoạn dài. |
| **3894268653** – Tax Account Manager | REJECT | s0 **1.027**, 118 từ: toàn mô tả thuế/CPA bị bỏ, câu nối `manner.Developing`, `tax-compliant.Identifying`. | `EX_COMMERCIAL` vẫn khớp title. Đây là ví dụ rõ không có newline và mất toàn nội dung khỏi matching đoạn. |
| **3901946257** – Fitness Specialist - FT: Eaton, Cleveland, OH | REVIEW | s72 **999**: `Essential Functions`, exercise prescriptions/member fitness, trộn `text-decoration-color: initial;">`; s76 **589**: qualifications. | `<br style=...>` không tách đúng HTML, CSS tạo nhiều segment giả. `working with ... membership database` là công cụ hành chính; không đủ kết luận CNTT. Đây là gap xử lý HTML, số tin có tag nhỏ. |
| **3905288395** – Developer | REVIEW | s14 **501**: `Develop applications`; s15 777, s17 594 cũng bị bỏ. | Ca gate/task đã truy vết chi tiết ở trên; thiếu role alias và self cue trong nhiệm vụ, còn blocker. |

Full text của các tin được lưu riêng để người kiểm tra đọc đúng nguồn; không thay bằng các đoạn trích ở bảng. Không dùng 20 tin lựa chọn chẩn đoán này làm tập đánh giá cuối, cũng không suy tỷ lệ lỗi toàn dataset.

## Phân biệt implementation với thiết kế

**Đã kiểm tra implementation:** ngưỡng dùng `>` nên 500/501 đúng; LF/CRLF tách trước collapse; không vô tình gọi normalize trước splitter; điều kiện all/same_segment/title full_match hoạt động; mọi rule được lưu; blocker áp dụng toàn đoạn theo JSON; thứ tự conflict/exclusion/include/review đúng. Replay 20 tin cho decision/group/rule/reasons bằng trace cũ. Bộ hồi quy gồm **14 test**, trong đó test hiện có chạy **57 illustrative cases** JSON, đã qua. Các test xác minh hợp đồng code, **không xác minh nghề chuẩn**.

**Giới hạn thiết kế được chứng minh:** discard nguyên đoạn dài; cờ dài có thể đủ REVIEW mà không liên quan nghề; regex không hiểu bullet/HTML/các mục nối; blocker cộng tác phủ cả đoạn, kể cả đoạn có nhiệm vụ của chính vị trí; gate exact-title và alias role/task/cue rất hẹp. Những hành vi này được JSON quy định hoặc chưa được JSON hỗ trợ. Vì chưa thấy bug rõ, **không sửa `src/it_taxonomy.py` hoặc config chỉ để tăng ACCEPT**; chỉ thêm công cụ chẩn đoán và test hồi quy.

## Phương án giữ mô tả và kiểm soát boilerplate cần chốt

1. **Giữ raw/full text và provenance.** Tạo lớp segment dẫn xuất có offset nguồn, section, actor, hash text, phiên bản parser, lý do loại khỏi evidence; không xóa đoạn dài. Tách cờ cần xem lại khỏi quyết định membership, nhưng mọi thay đổi chính sách REVIEW phải được ghi trong JSON phiên bản mới.
2. **Tách theo cấu trúc thật.** Với HTML, dùng parser, chuyển `br`/block/list thành ranh giới, decode entity, loại script/style khỏi text dẫn xuất và giữ ánh xạ nguồn. Chuẩn hóa LF/CRLF/CR/U+2028/U+2029; nhận heading/bullet khi có cấu trúc chắc chắn. Không chia mọi dấu chấm vì `.NET`, URL, phiên bản; không cắt tùy ý mỗi 500 ký tự làm đứt action/object.
3. **Giữ đoạn dài chưa phân tách được.** Có thể dùng cửa sổ mệnh đề action + object trong cùng section/actor để giới hạn matching. Quy tắc nối cue/role/task chỉ trong phạm vi có chủ thể vị trí rõ ràng; không nối từ giới thiệu công ty sang nhiệm vụ hoặc từ đoạn lương sang task. Nếu không xác định được ranh giới/actor, giữ nguyên và REVIEW kèm evidence chưa dùng. 500 hiện tại có thể giữ như giới hạn cửa sổ sau thiết kế lại, không tăng ngưỡng để đạt quota ACCEPT.
4. **Kiểm soát phủ định/cộng tác ở mệnh đề và chủ thể.** Phân biệt “you develop software and collaborate with users” với “assist/work with a software team” thuần hỗ trợ đội khác; phân biệt company profile, compensation/benefits, EEO với nhiệm vụ. Đừng gỡ toàn bộ blocker hoặc đơn giản thêm `you will` vào mọi đoạn. Cần bổ sung ca dương/âm cho câu đa mệnh đề và yêu cầu kiến thức so với trách nhiệm.
5. **Rà soát fallback riêng với TV1/TV2.** Gate chỉ 205 tin và task alias rất ít hit là vấn đề độc lập với segmentation. Chốt có cho fallback ở title dài chưa được rule quyết định không; chốt role có thể ở heading và task ở bullet cùng section không; rà alias theo mẫu phát triển có nhãn tay. Không coi mọi Engineer/Analyst là IT, không dùng industry/skill metadata làm positive, không mở rộng phạm vi nghề A02 trong bước sửa parser.
6. **Đóng băng, kiểm thử rồi chạy so sánh riêng.** Nếu thống nhất thay đổi, cập nhật version/hash/changelog, test hợp đồng mới cùng ca tổng hợp, ca đối chứng/boilerplate và 20 job_id này; chạy phiên bản mới vào **thư mục mới**, lưu cả evidence/trạng thái/quy tắc. So theo job_id với trace cũ, không viết lại seed42, không dùng dự đoán mới làm nhãn chuẩn. Bổ sung kiểm tra JVM/Spark khi TV1 bàn giao; không cần chạy lại ETL raw cho việc này.

## Trước khi tiếp tục gán nhãn đủ 160

**Nên chốt thiết kế segmentation, phạm vi blocker và điều kiện fallback trước khi dùng cả 160 tin để sửa/đánh giá phiên bản kế tiếp.** Hiện bản đọc seed42 vẫn có full raw description, nên các nhãn anh đã điền vẫn hợp lệ để đối soát và được giữ nguyên. Có thể đọc/gán nhãn độc lập tiếp theo phạm vi A02, không cần tạo lại mẫu; chưa nên coi trace v0.1.0 là bộ lọc đã đánh giá hoặc dùng số ACCEPT làm mục tiêu sửa.

160 tin seed42 là tập phát triển quy tắc. 20 tin chẩn đoán này cũng đã được đọc để phát triển, phải loại khỏi mẫu đánh giá cuối độc lập cùng các job_id phát triển khác. Chưa có nhãn chuẩn cho chẩn đoán; không báo accuracy/precision/recall, không suy chỉ số dataset từ mẫu phân tầng có reservations.

Tái lập chẩn đoán trong `.venv` hiện có, luôn chọn output chưa tồn tại (không tạo dự đoán mới):

```powershell
.\.venv\Scripts\python.exe src/diagnose_a04.py --output data/analytics/a04_diagnostics_v0_1_0_repeat
.\.venv\Scripts\python.exe -m unittest discover -s src -p "test*a04*.py" -v
```

Chạy lại script sẽ tái lập 18 tin theo hash `a04-diagnostics-20261008:<job_id>`, theo quota 4 REVIEW có context/task trong đoạn bỏ, 3 REVIEW title generic, 4 REVIEW không có bộ context/task đang hoạt động trong đoạn bỏ, 3 ACCEPT, 3 REJECT, 1 HTML; bỏ job_id đã lấy ở tầng trước. Hai ca bổ sung là mọi tin qua gate DESCRIPTION có literal task alias bất kỳ trong description (kể cả đoạn dài), theo job_id tăng dần. Đây là cách chọn ca chẩn đoán, **không phải lấy mẫu ngẫu nhiên đại diện hoặc seed42**. File chẩn đoán lớn bị ignore; tài liệu/script/audit nhỏ vẫn review được. Không commit/push.
