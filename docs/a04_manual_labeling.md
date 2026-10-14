# A04 – Mẫu gán nhãn thủ công bộ lọc CNTT

> **Cập nhật sau áp dụng 93 tin, 13/10/2026:** đã duyệt đủ **176 job_id / 177 dòng nguồn**, reviewer Dũng, reviewed_date 2026-10-13. Giữ nguyên 83 quyết định trước và 4 CHUA_RO; A04-063 CNTT/DATA_AI, A04-124 IT_MANAGEMENT. Metadata thiếu: **0**. Mẫu chính khớp membership khi máy quyết định **127/132 = 96.21%**, độ phủ trên nhãn rõ **132/156 = 84.62%**; mẫu 17 báo riêng trong [báo cáo hiện hành](a04_validation_report.md). Các mục bên dưới là lịch sử chuẩn bị/đối chiếu trước lượt áp dụng này. **A04 chưa tự đánh dấu hoàn thành**; phần nghiệm thu còn lại xem [tiêu chí cập nhật](a04_completion_criteria.md).

Đồng Viết Dũng – TV2; chuẩn bị ngày **08/10/2026**, nhánh `feat/tv2-analysis`. Đã tạo mẫu thật, chưa có nhãn thủ công, chưa hoàn thành đánh giá A04. **Không có accuracy, precision hoặc recall.**

**Cập nhật xử lý mô tả v0.2.0:** xem [chính sách/changelog](a02_a04_changelog.md) và [so sánh với v0.1.0](a04_v020_comparison.md). Mẫu seed42 dưới đây vẫn thuộc **v0.1.0**, không được tạo lại hoặc ghi đè theo dự đoán mới. Bộ lọc hiện hành đọc `config/it_taxonomy.json` v0.2.0; muốn tái lập bản cũ phải chỉ định [snapshot v0.1.0](../config/versions/it_taxonomy_v0.1.0.json).

## Mở file nào để gán nhãn

Mẫu bàn giao chính nằm tại **`data/analytics/a04_manual_seed42/`**:

1. Mở [a04_manual_labels_blind.csv](../data/analytics/a04_manual_seed42/a04_manual_labels_blind.csv) để điền nhãn. Có đúng **160 job_id khác nhau**, title và description **đầy đủ, nguyên bản**, các cột người đọc để trống. CSV UTF-8 BOM có quote/multiline; không tách bằng dấu phẩy hoặc xuống dòng thủ công.
2. Có thể đọc dễ hơn bằng [a04_blind_reader.html](../data/analytics/a04_manual_seed42/a04_blind_reader.html), mở trong trình duyệt, tìm theo `sample_id`/`job_id`, rồi điền CSV. Bản đọc không chứa quyết định/nhóm/rule của máy; không dùng excerpt thay toàn văn description.
3. Sau vòng nhãn tay đầu mới mở `sample_predictions_private.jsonl` để đối chiếu. File này tách riêng dự đoán, nhóm nghề, phân nhóm, candidates, rule IDs, reason codes, hash taxonomy và evidence thật. `sampling_manifest_private.csv` giữ tầng/hash lấy mẫu, cũng để riêng khỏi bản đọc.

Giữ nguyên sample_id, job_id, title và description. Không sắp xếp lại bằng cách làm mất liên kết giữa các cột. Trường trống ban đầu có nghĩa **chưa gán nhãn**, không phải nhãn “chưa rõ”. Các file dữ liệu A04 và dự đoán lớn nằm dưới `data/analytics/`, bị Git ignore; hướng dẫn/script/audit summary vẫn có thể review trên Git. Cần giữ bản local của CSV đã gán nhãn.

## Cách quyết định nhãn

Đọc title trước, sau đó toàn bộ nhiệm vụ trong description. Xác định **nghề của người được tuyển**, theo phạm vi A02; nhắc công nghệ, tên doanh nghiệp phần mềm, nhãn IT hoặc ngành Software Development không tự xác định nghề CNTT. Phân biệt nhiệm vụ của vị trí với giới thiệu công ty, khách hàng, nhóm cộng tác, yêu cầu phủ định và boilerplate.

| Cột | Giá trị cần điền |
| --- | --- |
| manual_label | `CNTT`, `NGOAI_CNTT`, hoặc `CHUA_RO` |
| manual_is_it | `true` khi CNTT; `false` khi NGOAI_CNTT; để trống khi CHUA_RO |
| manual_primary_group_code | Một mã nhóm bên dưới khi CNTT; để trống khi NGOAI_CNTT/CHUA_RO |
| manual_subgroup_code | Chỉ khi nhóm SOFTWARE: SOFTWARE_MOBILE, SOFTWARE_WEB, SOFTWARE_OTHER; nhóm khác để trống |
| manual_reason | Lý do ngắn giải thích nghề/nhiệm vụ, phạm vi loại trừ hoặc thông tin còn thiếu; không chép lý do dự đoán làm nhãn chuẩn |
| manual_evidence | Trích một hoặc vài câu thật trong title/description làm căn cứ; nếu chưa rõ, nêu phần thông tin cần bổ sung |
| reviewer | Tên người đọc, ví dụ Đồng Viết Dũng |
| reviewed_date | Ngày thực tế đọc, dạng YYYY-MM-DD |

`CHUA_RO` dùng khi thiếu nhiệm vụ, nghề mơ hồ, thông tin mâu thuẫn hoặc ranh giới phạm vi chưa thống nhất. Không ép thành NGOAI_CNTT chỉ vì không thấy alias, hoặc thành CNTT vì có Python/SQL. Với CNTT rõ nhưng chưa phân nhóm chuyên môn được, dùng **IT_OTHER**, thay vì dùng nhóm này cho mọi ca chưa rõ membership.

| Nhóm nghề | Phạm vi tham chiếu A02 |
| --- | --- |
| SECURITY | An toàn thông tin, an ninh mạng; không gồm bảo vệ vật lý |
| DATA_AI | Dữ liệu, AI, CSDL, BI kỹ thuật; data analyst chung cần nhiệm vụ kỹ thuật |
| DEVOPS_CLOUD | DevOps, cloud, SRE, nền tảng triển khai/vận hành phần mềm |
| QA_TESTING | Kiểm thử/chất lượng phần mềm; không gồm QA sản xuất |
| NETWORK_SYSTEMS | Mạng máy tính, máy chủ, hệ điều hành |
| SOFTWARE | Lập trình/phát triển phần mềm, gồm Web/Mobile/firmware software |
| IT_SUPPORT | Hỗ trợ máy tính/phần mềm/người dùng hệ thống CNTT |
| IT_BUSINESS | Nghiệp vụ/sản phẩm/dự án có đối tượng phần mềm/hệ thống thông tin |
| IT_MANAGEMENT | Quản lý chức năng CNTT, đội phần mềm, kiến trúc giải pháp CNTT |
| IT_OTHER | Nghề CNTT rõ nhưng không đủ bằng chứng nhóm chuyên môn |

Giữ ranh giới thiết kế A02 để so sánh nhất quán: hardware/PLC thuần, UI/UX/graphic design thuần, giảng dạy và bán hàng kỹ thuật không tự vào CNTT. Nếu không đồng ý với phạm vi IT_BUSINESS hoặc ca ranh giới, ghi rõ trong manual_reason để nhóm chốt; không tự sao dự đoán. Nếu nhiều nghề đồng thời rõ, áp dụng ưu tiên theo tầng bằng chứng rồi priority trong A02/JSON; ghi các ứng viên và lý do phân xử trong manual_reason. Mobile/Web là phân nhóm của Software.

Nên nhờ TV1 hoặc người đọc thứ hai kiểm tra các ca CHUA_RO/tranh chấp và một phần ca rõ. Lưu nhãn độc lập, người/ngày đọc và quyết định thống nhất ở bản đối soát riêng; **không ghi đè nhãn đầu tiên bằng dự đoán của máy**.

## Bộ lọc v0.1.0 đã tạo mẫu seed42 và nguồn dùng chung

Đã tìm `src/`/`tmp/` và không có implementation bộ lọc hiện hữu; chỉ có thiết kế JSON/A02 và scaffold D05. Tạo [src/it_taxonomy.py](../src/it_taxonomy.py), đọc trực tiếp alias/condition/priority từ **cùng JSON A02**, không tạo một danh sách quyết định khác. [src/prepare_a04.py](../src/prepare_a04.py) là runner/lấy mẫu; các acronym dùng cho chọn ca kiểm tra không được dùng làm rule quyết định mới.

Taxonomy **v0.1.0**, SHA-256 exact bytes:

```text
99523fff775fc302507638b532491275c3bec54d2d38354ce329f574943c8278
```

JSON v0.1.0 được giữ exact bytes trong snapshot, implementation cũ tại [src/it_taxonomy_v010.py](../src/it_taxonomy_v010.py). Chính sách cũ thực hiện NFC/lower, sentinel trước replacement, literal Unicode boundary, tách description trước gộp whitespace, bỏ đoạn >500, chặn ngữ cảnh phủ định/cộng tác; thu mọi rule khớp; positive+exclusion→REVIEW; nhóm chuyên môn ưu tiên theo `(tier_rank, group.priority, rule_priority, rule_id)`; general IT chỉ fallback; Software mới xét subgroup. v0.2.0 thay xử lý mô tả theo changelog, giữ các rule nghề và ưu tiên. Cả hai không đưa metadata/skills_desc vào quyết định, không trích kỹ năng A05.

Môi trường chạy là `.venv` **Python 3.11.9**, thư viện chuẩn. Chưa có Parquet D04/canonical D05 để ưu tiên, nên dùng trực tiếp **raw postings**, giữ raw text và hash. Đầu ra một dòng/job_id trong gzip JSONL, có đủ ACCEPT/REJECT/REVIEW, tri-state is_it, primary/subgroup, mọi candidate/rule/reason/evidence. Excerpt là lát cắt nguồn thật gần hit, tối đa 240 ký tự; full text vẫn được giữ. Đây là implementation dùng lại được cho TV1, chưa phải D06 production; parity native JVM/Spark và schema/path canonical cần TV1 xác nhận.

## Quy mô dự đoán v0.1.0 trên toàn raw

| Quyết định máy | Tin | Ý nghĩa |
| --- | ---: | --- |
| ACCEPT | **5.102** | Được quy tắc chọn, có một nhóm chính; chưa là CNTT được gán nhãn chuẩn |
| REJECT | **41.555** | 14.642 do exclusion; 26.913 do chưa tìm thấy bằng chứng theo rule |
| REVIEW | **77.192** | Giữ riêng, is_it NULL, nhóm chính NULL; không tự gộp vào REJECT/ACCEPT |
| Tổng | **123.849** | 123.849 job_id distinct, không thiếu/trùng, giữ grain raw |

Trong ACCEPT, dự đoán nhóm: SOFTWARE 2.299, DATA_AI 1.114, NETWORK_SYSTEMS 555, DEVOPS_CLOUD 440, SECURITY 184, IT_SUPPORT 148, QA_TESTING 104, IT_BUSINESS 91, IT_MANAGEMENT 89, IT_OTHER 78. Đây là **đếm dự đoán trên toàn raw**, không phải cơ cấu CNTT đã được đánh giá hoặc kết quả A06.

REVIEW có 59.831 tin mang cờ bỏ đoạn description quá dài; 47.683 mang lý do title mơ hồ và 13 có positive–exclusion conflict. Các lý do có thể giao nhau, không cộng để thành tổng REVIEW. Trên toàn ba quyết định, cờ đoạn bị bỏ xuất hiện ở 71.150 tin; title rõ/exclusion vẫn có thể đủ quyết định. Không điều chỉnh ngưỡng/alias để làm số đẹp; cần đọc mẫu trước sửa rule.

Nguồn trace đầy đủ: `data/analytics/a04_taxonomy_v0_1_0_seed42/all_predictions.jsonl.gz`. Mẫu bàn giao được lấy lại từ trace đã chạy, có kiểm tra hash nguồn/config và **title/description/job_id từng tin trùng raw**; không chạy lại ETL hay phân loại lại. [run_manifest.json](../data/analytics/a04_manual_seed42/run_manifest.json) lưu hash raw, config, interpreter, runner, trace và thiết kế lấy mẫu; [summary nhỏ](../data/audit/tv2_a04_summary.json) có thể review trên Git. Các bản mẫu thử trong thư mục trace ban đầu không phải mẫu bàn giao chính; chỉ dùng `a04_manual_seed42` để gán nhãn.

## Kiểm tra REVIEW trước khi gán nhãn đủ 160 (08/10/2026)

Đã kiểm tra toàn trace và đọc 20 tin thật: xem [báo cáo chẩn đoán A04](a04_review_diagnostics.md). Ngưỡng 500 là **Unicode code point của từng đoạn sau chuẩn hóa**, không phải số từ; đoạn vượt ngưỡng bị bỏ toàn bộ khỏi matching. Trong 59.831 REVIEW mang cờ, 29.496 chỉ có cờ dài, 30.327 còn title mơ hồ, 8 còn conflict. DESCRIPTION_ROLE_TASK chỉ được xét cho 205 title exact-generic và không tin nào đủ bốn bộ role/task/context/self cue, kể cả tìm lại trong đoạn dài hoặc bị chặn.

Chưa thấy implementation sai JSON trong các điều kiện đã kiểm tra; đã thêm chẩn đoán và test, **không đổi bộ lọc hoặc dự đoán**. Nên chốt với TV1/TV2 cách giữ đoạn dài, tách bullet/HTML, blocker theo chủ thể và điều kiện fallback trước khi dùng đủ 160 để phát triển phiên bản kế tiếp. Có thể tiếp tục đọc raw và gán nhãn độc lập theo A02; mọi nhãn đã điền vẫn giữ nguyên. Mẫu seed42, quota, full text và các file dự đoán riêng không đổi; không lấy lại mẫu hoặc dùng máy điền nhãn chuẩn. Nếu chạy bộ lọc mới sau khi chốt thiết kế, bắt buộc lưu thư mục mới và version/hash/changelog.

Các job_id đã đọc để chẩn đoán cũng thuộc dữ liệu phát triển và cần loại khỏi mẫu đánh giá cuối độc lập; không suy chỉ số toàn dataset từ mẫu phân tầng hiện tại.

## Lấy mẫu tái lập theo A02

Seed **42**; khóa job_id integral canonical. Tách các tầng không giao nhau: ACCEPT đặc biệt (nhiều ứng viên hoặc Mobile/Web) trước, ACCEPT còn lại, REJECT có exclusion, REJECT không bằng chứng, REVIEW. Sắp xếp trong mỗi tập ứng viên theo SHA-256 UTF-8 của **`42:<job_id>`**, rồi job_id số khi hash bằng nhau. Giữ các ca phủ nghề/ngữ cảnh theo A02 trước, sau đó điền quota theo thứ tự hash; thứ tự bản đọc cũng trộn bằng hash, không nhóm theo quyết định máy.

| Tầng | Quy mô trước mẫu | Mẫu thực tế |
| --- | ---: | ---: |
| ACCEPT một nhóm, không thuộc tầng đặc biệt | 4.423 | 50 |
| ACCEPT nhiều ứng viên hoặc Software Mobile/Web | 679 | 30 |
| REJECT do exclusion | 14.642 | 30 |
| REJECT không tìm thấy bằng chứng | 26.913 | 20 |
| REVIEW | 77.192 | 30 |
| Tổng | 123.849 | **160** |

Không thiếu quota tầng, không chuyển quota, không lặp job_id. Trong 80 ACCEPT: SOFTWARE 41, DATA_AI 8, NETWORK_SYSTEMS 6; sáu nhóm SECURITY/DEVOPS_CLOUD/QA_TESTING/IT_SUPPORT/IT_BUSINESS/IT_MANAGEMENT mỗi nhóm 4, IT_OTHER 1. Software gồm Mobile 6, Web 23, Other 12. Đã cố định ít nhất 4 tin mỗi nhóm chuyên môn, ít nhất 5 Mobile/Web, IT_OTHER, TITLE_CONTEXT, viết tắt và nhiều ứng viên; tầng REJECT_NO_MATCH cố định ít nhất 5 ca có metadata IT/Software Development chỉ để tìm bỏ sót. Exclusion cố gắng phủ mỗi rule ít nhất 3 ca; REVIEW có ít nhất 3 conflict và các lý do khả dụng.

**Không có ứng viên ACCEPT DESCRIPTION_ROLE_TASK và không có REVIEW do thiếu title trong lần chạy**, nên không bịa hoặc nhân bản các ca này. Manifest ghi requested/available/achieved từng phần phủ; quota chung vẫn đủ 160. Coverage reservations có tính chủ đích: không coi mọi tin trong tầng có xác suất chọn bằng n/N, không dùng các tỷ lệ mẫu để suy ra toàn dataset khi chưa có thiết kế/trọng số phù hợp.

## Mẫu sửa quy tắc và mẫu đánh giá cuối

160 tin này là **mẫu phát hiện lỗi/sửa quy tắc**, toàn bộ cột manual hiện trống. Sau gán nhãn, đối chiếu để tìm alias thiếu, sai ngữ cảnh/boilerplate, exclusion, ưu tiên, lỗi nhóm và ca cần người đọc thứ hai. Có thể ghi số lỗi trên mẫu có nhãn rõ với mẫu số cụ thể; chưa tính chỉ số khi chưa có nhãn.

Mẫu đánh giá cuối **chưa tạo**. Sau khi chốt phạm vi và đóng băng rule/version mới, lấy một mẫu độc lập bằng seed khác (đề xuất 43), loại toàn bộ job_id từng dùng phát triển, cân nhắc tránh mô tả/tin trùng nội dung; người đọc gán nhãn độc lập trước xem máy. Chọn thiết kế ngẫu nhiên hoặc phân tầng có xác suất/trọng số được định nghĩa trước nếu mục tiêu là ước lượng toàn dataset; làm rõ REVIEW/CHUA_RO và mẫu số. Không đánh giá bản sửa trên chính 160 tin dùng sửa rồi gọi đó là chất lượng cuối. Mọi chỉ số tương lai chỉ phản ánh dataset và thiết kế đánh giá, không suy rộng ra thị trường lao động.

## Tái lập và phần còn chờ

Chạy lại từ raw vào **thư mục mới** (runner từ chối đích đã tồn tại để bảo vệ nhãn người đọc):

```powershell
.\.venv\Scripts\python.exe src/prepare_a04.py --config config/versions/it_taxonomy_v0.1.0.json --output data/analytics/a04_reproduced_seed42
.\.venv\Scripts\python.exe -m unittest discover -s src -p test_tv2_a04.py -v
```

Có thể tái lập riêng lấy mẫu từ trace đã có, kiểm tra nguồn/hash/text, không chạy lại phân loại:

```powershell
.\.venv\Scripts\python.exe src/prepare_a04.py --config config/versions/it_taxonomy_v0.1.0.json --output data/analytics/a04_resampled_seed42 --reuse-predictions data/analytics/a04_taxonomy_v0_1_0_seed42/all_predictions.jsonl.gz
```

57 ca minh họa JSON và 8 test hợp đồng đã qua; chúng kiểm tra implementation/CSV/evidence/ưu tiên/lấy mẫu, **không đo chất lượng phân loại nghề trên dataset**. [Kiểm tra bàn giao](../data/audit/tv2_delivery_validation.json) xác nhận đủ 123.849 dự đoán, 23.616 evidence là excerpt thật có alias khớp, 160 bản đọc giữ full text raw và nhãn trống; mẫu tái lập đúng khi đảo thứ tự đầu vào, hash raw/nguồn khớp, JSON/A02 và file tracked cũ giữ nguyên. Chờ anh gán nhãn; TV1 bàn giao/đối soát Parquet D04 và canonical D05, Java 21/PySpark 4.2.0, kiểm tra cùng các ca trên JVM/Spark và parity trên dữ liệu thực trước D06. Vẫn giữ ghi chú UTC snapshot và semantics lương D07 trong A01/A03. Không làm A05–A11, không chạy lại ETL, không sửa nghiệp vụ TV1, không commit/push.
