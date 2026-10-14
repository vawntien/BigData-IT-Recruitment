# A04 – So sánh xử lý mô tả v0.1.0 và v0.2.0

> **Cập nhật sau áp dụng 93 tin, 13/10/2026:** đã duyệt đủ **176 job_id / 177 dòng nguồn**, reviewer Dũng, reviewed_date 2026-10-13. Giữ nguyên 83 quyết định trước và 4 CHUA_RO; A04-063 CNTT/DATA_AI, A04-124 IT_MANAGEMENT. Metadata thiếu: **0**. Mẫu chính khớp membership khi máy quyết định **127/132 = 96.21%**, độ phủ trên nhãn rõ **132/156 = 84.62%**; mẫu 17 báo riêng trong [báo cáo hiện hành](a04_validation_report.md). Các mục bên dưới là lịch sử chuẩn bị/đối chiếu trước lượt áp dụng này. **A04 chưa tự đánh dấu hoàn thành**; phần nghiệm thu còn lại xem [tiêu chí cập nhật](a04_completion_criteria.md).

Đồng Viết Dũng – TV2; nhánh `feat/tv2-analysis`, **08/10/2026**. Đã chạy **123.849 tin raw** bằng `.venv` Python **3.11.9**, thư viện chuẩn, không ETL hoặc sửa D04/D05. Các số bên dưới là **dự đoán chưa được đánh giá bằng nhãn tay**, không phải cơ cấu CNTT chuẩn hay chỉ số chất lượng.

## Phiên bản, nguồn và bảo toàn

Chính sách mới nằm trong [config/it_taxonomy.json](../config/it_taxonomy.json); [changelog](a02_a04_changelog.md) giải thích đầy đủ parser, scope, cửa sổ, provenance và cách tái lập. Snapshot cũ được lưu **trước khi cập nhật** tại [config/versions/it_taxonomy_v0.1.0.json](../config/versions/it_taxonomy_v0.1.0.json), implementation exact bytes tại [src/it_taxonomy_v010.py](../src/it_taxonomy_v010.py).

| Hiện vật | SHA-256 |
| --- | --- |
| JSON v0.1.0 | `99523fff775fc302507638b532491275c3bec54d2d38354ce329f574943c8278` |
| JSON v0.2.0 | `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d` |
| Trace v0.1.0 | `8bccbf9ed92db4105f4539d1ca6eb0d7a069d60d717545697b07f1666be221d5` |
| Trace v0.2.0 | `436fdb816fdc522bb8ee5a718cc9d095338df9095a0b3fffa3405f8b7d851f45` |

Thư mục mới: **`data/analytics/a04_taxonomy_v0_2_0_20261008/`**. Có full trace, snapshot JSON hai bản, bản sao code đã chạy, SHA/runtime/provenance trong `run_manifest.json`. [Runner](../src/compare_a04_versions.py) kiểm tra trace cũ theo manifest có hash ở mẫu seed42 vì manifest lần chạy ban đầu chưa có trường hash; không suy phiên bản chỉ từ đường dẫn.

Đã đối soát **35 hiện vật** bằng hash/kích thước/mtime trước và sau: 11 raw CSV, mọi file trace/mẫu/nhãn seed42 cũ, bộ chẩn đoán cũ, nguồn runner/CSV và các hiện vật D04/D05 có trong checkout. Không sửa `C:\archive`, không thay file tracked đang có, không commit/push. Các nhãn người đọc vẫn nguyên vẹn; không tự điền nhãn từ máy. Dữ liệu lớn và mọi file mới dưới analytics được Git ignore.

## Tổng tin và chuyển trạng thái

| Dự đoán | v0.1.0 | v0.2.0 | Chênh lệch |
| --- | ---: | ---: | ---: |
| ACCEPT | 5.102 | **5.127** | +25 |
| REJECT | 41.555 | **58.822** | +17.267 |
| REVIEW | 77.192 | **59.900** | −17.292 |
| Tổng / distinct job_id | 123.849 | **123.849** | 0 |

Đối chiếu theo **job_id**, kiểm tra title/description/hash từng tin bằng nguồn cũ và raw, không phụ thuộc thứ tự hai trace:

| v0.1.0 → v0.2.0 | ACCEPT | REJECT | REVIEW | Tổng cũ |
| --- | ---: | ---: | ---: | ---: |
| ACCEPT | 5.085 | **3** | **14** | 5.102 |
| REJECT | 0 | 41.418 | **137** | 41.555 |
| REVIEW | **42** | **17.401** | 59.749 | 77.192 |

**17.597 tin đổi trạng thái**. Tổng 71.497 tin đổi ít nhất một trường hợp đồng; phần lớn là thay reason cờ bỏ đoạn bằng trạng thái xử lý mới. 119 tin đổi bộ rule khớp; 60 tin đổi primary group (bao gồm chuyển có/không có nhóm do đổi trạng thái). Không dùng số ACCEPT hoặc REVIEW làm mục tiêu tối ưu.

Giảm REVIEW chủ yếu do **17.401 REVIEW→REJECT**: không còn lý do bỏ đoạn dài ở những phần đã tách/xác định scope đầy đủ, và các rule hiện tại chưa tìm được evidence nghề. `NO_IT_ROLE_EVIDENCE` **không phải nhãn chuẩn ngoài CNTT**. 42 REVIEW→ACCEPT là các nhiệm vụ nay được xét trong unit/cửa sổ hợp lệ. 17 tin rời ACCEPT cho thấy chính sách ngữ cảnh có thể hạn chế cả các ca từng được chọn; phải đọc lại, không coi mọi chuyển đổi là sửa đúng.

Các tổ hợp reason cũ/mới và số tin được lưu đầy đủ trong [audit so sánh](../data/audit/tv2_a04_v020_comparison.json); `job_comparison.csv` có **một dòng mỗi job_id**, old/new decision, nhóm/phân nhóm/rule, reasons, các trường đổi và số đoạn dài. Reasons có thể giao nhau, không cộng các tần suất riêng để suy tổng tin.

Ở v0.2.0: `TITLE_DIRECT` 4.958, `TITLE_CONTEXT` 92, `GENERAL_IT_UNCLASSIFIED` 77 trong reason của ACCEPT; **vẫn chưa có DESCRIPTION_ROLE_TASK**. Gate/alias fallback giữ nguyên; không sửa để tạo thêm ACCEPT. `POSITIVE_EXCLUSION_CONFLICT` vẫn 13 tin. `AMBIGUOUS_TITLE_WITHOUT_CONTEXT` 47.658 và `DESCRIPTION_PROCESSING_INCOMPLETE` 29.364 là cờ/reason có thể giao nhau và cờ chưa đầy đủ có thể xuất hiện cả trong ACCEPT/REJECT khi có bằng chứng mạnh hơn.

Một ca ACCEPT giữ trạng thái nhưng đổi nhóm: **3894283986**, `IT_OTHER` / `GENERAL_IT_TITLE` → `IT_SUPPORT` / `IT_SUPPORT_CONTEXT`; hai đoạn dài cũ đã được xử lý. Đây là thứ tự nhóm chuyên môn thắng general IT đã có từ v0.1.0, không phải đổi priority. Cần người đọc xác nhận nhiệm vụ/nhóm mới; tra đúng job_id trong comparison/full trace.

## Nội dung dài được giữ và xử lý ra sao

Ngưỡng 500 vẫn là **Unicode code point của unit sau chuẩn hóa**; không tăng ngưỡng. Nó giới hạn cửa sổ matching, không xóa full unit hoặc full raw description.

| Đơn vị đếm | Số lượng |
| --- | ---: |
| Tin có đoạn dài từng bị bỏ trong v0.1.0 | 71.150 |
| Các đoạn dài từng bị bỏ | **118.943** |
| Đoạn cũ đã xử lý đầy đủ trong v0.2.0 | **81.041** |
| Đoạn cũ còn liên quan unit chưa xử lý đầy đủ | **37.902** |
| Tin có đoạn dài cũ mà tất cả đã xử lý đầy đủ | **42.325** |
| Unit dẫn xuất v0.2.0, gồm text/heading | 4.316.242 |
| Unit mới vẫn >500, được giữ nguyên văn | 57.293 |
| Unit mới chưa xử lý đầy đủ | 39.510 |
| Tin có xử lý mô tả chưa đầy đủ | 29.364 |
| Đoạn vượt ngưỡng bị xóa trong v0.2.0 | **0** |

81.041 nghĩa là đoạn được tách thành unit xử lý được **hoặc xác định được section/actor không cấp evidence**, ví dụ company/compensation/qualifications; không có nghĩa 81.041 đoạn đều là nhiệm vụ CNTT. 37.902 là số **đoạn cũ** còn chứa ít nhất một unit chưa đầy đủ; 39.510 là số **unit mới**, hai mẫu số khác nhau. Unit dài đã xác định là boilerplate có thể được xử lý đầy đủ nhưng vẫn giữ text và raw ranges.

Parser HTML/entity được dùng cho 209 tin; lần chạy không ghi nhận parser issue hoặc mapping unavailable. Đây là kiểm tra đường đi của parser trên dữ liệu hiện có, không chứng minh hiểu đúng mọi HTML/nội dung hoặc chủ thể. Các chuỗi dính kiểu `patternsParticipate`, heading chưa khai báo và câu đa chủ thể vẫn có thể chưa phân tách chắc chắn.

## Các ca thật và bằng chứng đường đi rule

Đã replay 20 tin chẩn đoán; full text cũ vẫn khớp raw, test không dùng nhận xét chẩn đoán làm nhãn chuẩn. `diagnostic_cases_comparison_private.json` lưu old/new prediction, source text, segments, scope, window diagnostics và evidence cho cả 20.

| job_id / title | v0.1.0 → v0.2.0 | Bằng chứng/điểm cần xác nhận |
| --- | --- | --- |
| **3891072754** – Lead Developer (Mobile Apps/Flutter) | REVIEW → ACCEPT | Câu `Analyze the customer needs ... test, and develop software ...` nay thành unit riêng, SOFTWARE_CONTEXT khớp; câu `Collaborating with...` không còn phủ định nhiệm vụ ở câu khác. Hai đoạn dài cũ xử lý đầy đủ. Nhóm Software là dự đoán cần nhãn tay. |
| **3905288395** – Developer | REVIEW → ACCEPT | `Develop applications based on technical requirements...` nằm trong RESPONSIBILITIES, dài 236 code point, khớp SOFTWARE_CONTEXT. Đoạn lương `this role` bị tách scope; không tạo DESCRIPTION fallback từ cue lương. Bốn đoạn dài cũ xử lý đầy đủ. |
| **3891008882** – User Interface Architect | REVIEW → REVIEW | Bullet đã tách; câu `Decent knowledge of .net technologies to implement APIs...` bị đánh dấu QUALIFICATION_SENTENCE, không tự coi yêu cầu kiến thức là nhiệm vụ. Không mở rộng UI/UX thuần. |
| **3903449638** – Privacy Engineer | REVIEW → REVIEW | `We are an engineering-focused team ... build software services` là COMPANY_SUBJECT; giữ nội dung, không dùng làm nhiệm vụ của vị trí. Một trong ba đoạn dài còn chưa đầy đủ. |
| **3902328365** – Principal Application Engineer (CD/CD) | REVIEW → ACCEPT + cờ incomplete | Vẫn có đoạn nhiều mục nối, window chứa `Help project teams build applications...`. Actor heuristic trong mệnh đề dài chưa giải quyết hết ranh giới hỗ trợ đội khác; **ưu tiên người đọc kiểm tra**, không tự coi đây là ca đã sửa đúng hoặc gán DevOps. Hai đoạn dài còn chưa đầy đủ. |
| **3894268653** – Tax Account Manager | REJECT → REJECT | Câu nối bằng dấu chấm đã tách; EX_COMMERCIAL vẫn đủ loại theo title, không lấy phần mềm thuế/Office làm nghề IT. |
| **3902916761** – Registered Nurse… | REJECT → REJECT | EX_HEALTH giữ nguyên, công nghệ là công cụ chưa đủ positive. Đoạn qualification dài cũ xử lý được. |
| **3895536438** – Oncology Account Manager… | REJECT → REJECT | EX_COMMERCIAL giữ nguyên; CRM/khách hàng không tự thành nhiệm vụ IT. Hai đoạn dài vẫn chưa đầy đủ, cờ lưu độc lập với exclusion. |
| **3901946257** – Fitness Specialist | REVIEW → REVIEW | HTML/CSS dẫn xuất đã được xử lý, exercise/member duties vẫn đầy đủ; không dùng membership database làm căn cứ nghề CNTT. Hai đoạn dài cũ xử lý được; còn title mơ hồ theo từ điển cũ. |
| **3900956939** – Support Engineer | ACCEPT → ACCEPT | Đối chứng không mang cờ dài: `Troubleshoot software issues...` vẫn khớp IT_SUPPORT_CONTEXT; không bịa role/cue cho DESCRIPTION. |

Các ca rời ACCEPT cần xem trước khi bàn giao: **3904949360 – Programmer**, **3906223537 – ECC Designer/Programmer** có câu task kỹ thuật trong section QUALIFICATIONS nên hiện REJECT_NO_IT_ROLE_EVIDENCE; **3903458524 – MS Dynamics CRM Developer…** chuyển REVIEW do section qualifications; **3895563414 – Data Platform Engineer…** chuyển REVIEW khi scope COMPANY kéo dài vì không có heading reset được nhận ra. Đây là dấu hiệu **chính sách scope có thể chặn nhiệm vụ hợp lệ**, không phải bằng chứng bốn tin ngoài CNTT. Full text được giữ; cần người đọc xác nhận và ghi rõ heading/chủ thể trước khi chỉnh policy phiên bản sau.

## File để người đọc xác nhận

Tất cả nằm **riêng trong thư mục v0.2.0**, không đụng mẫu seed42:

1. [46 ca thay đổi để đọc độc lập](../data/analytics/a04_taxonomy_v0_2_0_20261008/changed_cases_for_review_blind.csv): job_id, title, full description, cột manual để trống. Chọn tối đa 5 ca mỗi chuyển trạng thái theo SHA-256 `a04-v020-review:<job_id>`, 5 ca chỉ đổi chi tiết và các ca chẩn đoán đã đổi; deduplicate. Đây là ca phát triển có chủ đích, không đại diện dataset. Dự đoán để riêng trong `changed_case_predictions_private.jsonl`.
2. [Toàn bộ 17 ca rời ACCEPT](../data/analytics/a04_taxonomy_v0_2_0_20261008/accept_downgrades_for_review_blind.csv): ưu tiên xem để xác định nhiệm vụ thật và tình trạng scope. Có thể trùng với 46 ca; nối theo job_id, không gán nhãn trùng thành hai quan sát độc lập. Dự đoán riêng tại `accept_downgrade_predictions_private.jsonl`.
3. Mẫu **160 seed42 cũ vẫn là bản gán nhãn chính**. Có bản dự đoán v0.2 riêng cho đúng 160 job_id tại `seed42_v020_predictions_private.jsonl`, giữ sample_id cũ. Chỉ mở sau vòng nhãn tay; không ghép dự đoán vào bản đọc hoặc điền vào nhãn chuẩn.

Tiếp tục quy ước [hướng dẫn A04](a04_manual_labeling.md): CNTT/NGOAI_CNTT/CHUA_RO, nhóm nghề trong A02, lý do và câu evidence, người/ngày đọc. Không bắt người đọc đồng ý với dự đoán. Ca chưa rõ section/actor hoặc phạm vi cần ghi CHUA_RO/lý do và đối soát TV1/TV2.

Mẫu đánh giá cuối vẫn **chưa tạo**. Ngoài seed42, loại các job_id phát triển đã đọc trong `changed_case_review.development_job_ids` của audit so sánh, `additional_development_exclusion_ids` của audit validation, các ca chẩn đoán và ca **3894283986** được nêu riêng ở báo cáo này. Các file này phục vụ sửa quy tắc, không đo chất lượng cuối. Không dùng dự đoán làm nhãn chuẩn; không báo accuracy/precision/recall hoặc suy tỷ lệ toàn dataset từ các ca chọn có chủ đích.

## Kiểm tra đã đạt và giới hạn còn lại

[Audit validation](../data/audit/tv2_a04_v020_validation.json) xác nhận đọc lại gzip đến EOF, đủ 123.849 job_id duy nhất, matrix/tổng processing khớp CSV/trace đã ghi; kiểm tra lại **23.835 evidence** là lát cắt raw và raw match ranges decode/normalize đúng alias. Offset derived/normalized tách rõ khỏi raw, không dùng chúng như byte offset CSV. SHA snapshot/code của đúng lần chạy cũng khớp.

**30 test qua**, gồm 14 test hợp đồng v0.1.0 và 16 test v0.2.0; 57 ca minh họa JSON qua cho cả hai version. Test kiểm tra code/context/provenance, không đánh giá nhãn nghề. Tách câu bảo vệ `.NET`, URL, phiên bản, viết tắt; có test LF/CRLF/CR/Unicode newline, bullet/HTML, script/style/entity/NFC, tác vụ kèm cộng tác, phủ định ngoài window, company profile, y tế/bán hàng chỉ dùng công nghệ, không ghép lương/quyền lợi/câu khác vào task.

Giới hạn còn lại:

- Section/actor là heuristic theo regex/heading JSON, chưa phân tích ngữ nghĩa đầy đủ. Heading không chuẩn và nội dung liền nhau có thể kéo dài COMPANY/QUALIFICATIONS sai phạm vi; các ca rời ACCEPT là ưu tiên kiểm tra. Mệnh đề dài có “help teams…” cùng cue vị trí cũng có thể vẫn tạo ACCEPT cần xem lại.
- Long window chỉ dùng evidence gần nhau trong một unit; nguyên văn được giữ nhưng các task không có alias hoặc chủ thể chưa đủ rõ vẫn chưa khớp. 37.902 đoạn dài cũ còn chưa xử lý đầy đủ; không khẳng định đã đọc tự động hoàn hảo.
- Gate exact-title, alias role/task/cue fallback chưa đổi; zero DESCRIPTION vẫn là hạn chế từ điển/gate đã chẩn đoán. Đề xuất riêng trong changelog, chỉ cân nhắc sau nhãn tay.
- Parser stdlib không phải browser DOM, bảo vệ viết tắt/URL theo danh sách có thể giữ gộp một số câu; marker section và phủ định chỉ bao phủ mẫu đã khai báo. Chưa đánh giá độ đúng ngữ nghĩa trên nhãn tay.
- **Chưa xác minh parity Spark/JVM**, chưa có Parquet/canonical TV1 để đối soát production. Cần thống nhất Unicode code point/UTF-16, schema trace và parser/context tương đương trước tích hợp; không sửa D04/D05 trong lượt này.

Trước bàn giao bộ lọc cho TV1, cần gán nhãn độc lập, ưu tiên 17 ca rời ACCEPT và các ca incomplete/actor phức tạp; đối soát phạm vi/ngữ cảnh trên nhãn người đọc rồi mới quyết định thay policy. Không đổi alias/gate chỉ để tạo DESCRIPTION hoặc tăng ACCEPT.

## File thay đổi trong lượt này

| File | Thay đổi |
| --- | --- |
| [config/it_taxonomy.json](../config/it_taxonomy.json) | Chính sách description/context/provenance v0.2.0, version/changelog; rule nghề và aliases giữ nguyên |
| [config/versions/it_taxonomy_v0.1.0.json](../config/versions/it_taxonomy_v0.1.0.json) | Snapshot exact bytes mới, dùng tái lập bản cũ |
| [src/it_taxonomy.py](../src/it_taxonomy.py) | Dispatcher hai version, interpreter v0.2 và validation policy |
| [src/it_taxonomy_v010.py](../src/it_taxonomy_v010.py) | Archive implementation v0.1 exact bytes |
| [src/description_processing.py](../src/description_processing.py) | Parser cấu trúc, actor/section/blocker, giữ unit dài, window và mapping nguồn |
| [src/compare_a04_versions.py](../src/compare_a04_versions.py) | Full run và JOIN comparison theo job_id, file review riêng |
| [src/validate_a04_v020.py](../src/validate_a04_v020.py) | Đọc lại trace đã ghi, evidence/CRC/grain/matrix/protection checks; xuất dự đoán riêng cho 160 seed42 và 17 ca rời ACCEPT |
| [src/test_a04_v020.py](../src/test_a04_v020.py) | 16 test behavior/provenance mới |
| [src/test_tv2_a04.py](../src/test_tv2_a04.py), [src/test_a04_segmentation.py](../src/test_a04_segmentation.py) | Test hợp đồng cũ chuyển sang snapshot config, không đổi assertion cũ |
| [src/diagnose_a04.py](../src/diagnose_a04.py) | Chỉ định config/implementation v0.1 snapshot để chẩn đoán cũ vẫn tái lập được |
| [A02](a02_it_taxonomy.md), [hướng dẫn A04](a04_manual_labeling.md) | Ghi semantics hiện hành và xác định rõ mẫu/command v0.1 đã đóng băng |
| [Changelog](a02_a04_changelog.md), báo cáo này | Version, chính sách, thực thi, kết quả và giới hạn |
| `data/audit/tv2_a04_v020_protected_before.json`, [comparison audit](../data/audit/tv2_a04_v020_comparison.json), [validation audit](../data/audit/tv2_a04_v020_validation.json) | Snapshot bảo toàn và kết quả mới; không ghi đè audit cũ |
| `data/analytics/a04_taxonomy_v0_2_0_20261008/` | Toàn bộ dữ liệu sinh mới, Git ignore; không lấy lại/ghi đè mẫu seed42 |
