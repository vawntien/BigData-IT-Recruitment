# A04 – Đề nghị quyết định cho 93 tin còn thiếu metadata

> **Trạng thái hiện hành sau áp dụng bảng chốt 93 tin (13/10/2026):** đủ 160 + 17 dòng nguồn, 176 job_id duy nhất; 93 quyết định được áp dụng theo job_id, metadata thiếu 0; 83 quyết định trước và 4 CHUA_RO giữ nguyên. A04-063 giữ CNTT/DATA_AI, A04-124 chuyển IT_MANAGEMENT. Tỷ lệ và FP/FN đã tính lại từ v0.2.0 lưu sẵn, mẫu chính và bổ sung riêng tại [báo cáo hiện hành](a04_validation_report.md). Còn đối soát/chốt xử lý FN, bất đồng và REVIEW; triển khai/xác minh sửa bộ lọc trong lượt được phép; người rà soát xác nhận tiêu chí nghiệm thu. Chưa tự đánh dấu A04 hoàn thành. Đánh giá độc lập phục vụ tuyên bố chất lượng; parity thuộc tích hợp D06, không là tiêu chí riêng của A04. Phần bên dưới ghi lại trạng thái **trước áp dụng**; thông tin 93 ca chưa duyệt hoặc A04-063 đề nghị CHUA_RO đã được thay thế bằng trạng thái cập nhật này.

Ngày lập bảng: **13/10/2026**, múi giờ `Asia/Bangkok`; nhánh **`feat/tv2-analysis`**, HEAD `2386394def3e95a14cb35c36c96787fa9e7562af`. Ngày lập tài liệu không phải ngày người phụ trách duyệt từng tin.

**Đã đọc title và toàn bộ description của đúng 93 job_id trong danh sách thiếu metadata. Kết quả: 80 GIU_NGUYEN, 12 DE_NGHI_SUA, 1 CHUA_RO. Đây là đề nghị chờ người duyệt; chưa sửa workbook hoặc điền reviewer/ngày duyệt.**

| Kết luận đề nghị | job_id duy nhất | Ý nghĩa |
| --- | ---: | --- |
| GIU_NGUYEN | 80 | Giữ nhãn, boolean, nhóm/phân nhóm, lý do và evidence hiện tại; vẫn có phân tích và trích dẫn bổ sung để người duyệt kiểm tra |
| DE_NGHI_SUA | 12 | 1 ca đổi nhóm; 11 ca chỉ sửa lý do và/hoặc evidence, giữ nhãn/nhóm/phân nhóm |
| CHUA_RO | 1 | Đề nghị chuyển CNTT/DATA_AI sang CHUA_RO vì ranh giới điều khiển công nghiệp và công việc dữ liệu/ML chưa đủ rõ |
| Tổng | 93 | Một bản ghi/job_id, không JOIN theo STT hoặc dòng Excel |

Nhãn **nguồn** của 93 ca vẫn là **44 CNTT, 49 NGOAI_CNTT**. Nhãn **đề nghị** là **43 CNTT, 49 NGOAI_CNTT, 1 CHUA_RO**. Không có đề nghị tự đổi CNTT thành NGOAI_CNTT hoặc ngược lại. CHUA_RO là nhãn người đọc chưa xác định, không là NGOAI_CNTT; REVIEW của máy giữ is_it=NULL và được lưu riêng.

## Bảng đề nghị và nguồn dùng để đọc

- [Bảng quyết định đề nghị 93 tin](a04_review_decisions_remaining93.csv): CSV UTF-8 BOM, quote/multiline đúng, 93 job_id duy nhất. `review_no` và `source_excel_row` chỉ để tìm lại hiện vật; khóa đối chiếu là `job_id`.
- [Danh sách thiếu metadata](a04_missing_review_metadata.csv) và [báo cáo kiểm tra hiện hành](a04_validation_report.md) được đọc và giữ nguyên. Sau lượt này danh sách vẫn có 93 ca, vì đề nghị không thay thế việc duyệt thực tế.
- [Workbook nguồn 160 tin](../data/analytics/a04_manual_seed42/a04_manual_labels_filled.xlsx), sheet `A04 manual labels`: đọc đủ mọi trường hiện tại của 93 ca, 344.279 ký tự description; không dùng excerpt máy thay toàn văn. Các mô tả ngắn cũng được đọc hết và ghi giới hạn cụ thể.
- [Hướng dẫn A04](a04_manual_labeling.md), [taxonomy A02 hiện hành](a02_it_taxonomy.md), JSON v0.2.0 và [83 quyết định đã chốt](a04_review_decisions_chot.xlsx) là căn cứ áp dụng phạm vi/ưu tiên; không lấy nhãn máy làm quyết định người đọc.
- [Dự đoán v0.2.0 đã lưu](../data/analytics/a04_taxonomy_v0_2_0_20261008/seed42_v020_predictions_private.jsonl) chỉ được đọc để kiểm tra nguồn và bổ sung cột đối chiếu sau khi ghi các đề nghị riêng từng ca; không gọi classifier hoặc chạy ETL.

CSV giữ toàn bộ `current_*` và `proposed_*` của nhãn/boolean/nhóm/phân nhóm/lý do/evidence. `specific_reason` giải thích đề nghị; `proposed_fields_to_change` chỉ liệt kê những trường thực sự khác nguồn. `confirmation_needed` và `evidence_limitations` nêu việc cần hỏi lại hoặc giới hạn hồ sơ. Bằng chứng dùng để kiểm tra đề nghị nằm trong `verbatim_evidence`, `evidence_quotes_json`, `evidence_offsets_json`; mỗi offset có `field=title/description`, tọa độ Unicode `[start,end)` trong đúng văn bản nguồn và hash title/description.

Ở GIU_NGUYEN, `proposed_manual_reason` và `proposed_manual_evidence` giữ nguyên nguồn; các câu trích đầy đủ bổ sung không tự trở thành đề nghị thay evidence. Ở DE_NGHI_SUA, chỉ các trường được liệt kê mới khác nguồn. Mọi cột reviewer/reviewed_date hiện tại và đề nghị của cả 93 ca đều trống. `proposal_status=DE_NGHI_CHO_NGUOI_DUYET`; không coi lượt rà soát hỗ trợ này là phê duyệt của Dũng.

## Các ca đề nghị sửa hoặc chưa rõ

| Sample | job_id | Đề nghị | Nội dung cần duyệt |
| --- | --- | --- | --- |
| A04-051 | `3901379229` | DE_NGHI_SUA | Giữ ngoài CNTT; thay evidence chương trình đào tạo B2B bằng task phát triển tài khoản và mục tiêu doanh số |
| A04-063 | `3904568619` | CHUA_RO | Chưa xác định nghề chính là data/ML software hay điều khiển công nghiệp; bỏ boolean và nhóm nếu chấp thuận CHUA_RO |
| A04-072 | `3899519477` | DE_NGHI_SUA | Giữ ngoài CNTT; thay yêu cầu kinh nghiệm marketing bằng task quản lý creative/campaigns |
| A04-098 | `3901944307` | DE_NGHI_SUA | Giữ DATA_AI; thay câu expertise Power BI bằng task xây large-scale BI solutions và complex T-SQL |
| A04-102 | `3900979722` | DE_NGHI_SUA | Giữ ngoài CNTT; bỏ khẳng định đã được giao lập trình CNC, vì JD chỉ nêu kinh nghiệm CNC/CAD-CAM và nhiệm vụ manufacturing |
| A04-114 | `3900947565` | DE_NGHI_SUA | Giữ DATA_AI; ghi rõ data solutions là yêu cầu kinh nghiệm, trích cả prefix TechnicalExperience để không gọi qualification là task |
| A04-117 | `3895521585` | DE_NGHI_SUA | Giữ SOFTWARE_WEB; sửa lý do để ghi mô tả 173 ký tự chỉ có profile React/định hướng HubSpot, chưa có danh sách nhiệm vụ |
| A04-120 | `3901387816` | DE_NGHI_SUA | Giữ QA_TESTING; thay Well-versed bằng trách nhiệm QA strategy/Definition of Done cho Mobile PR |
| A04-124 | `3884430597` | DE_NGHI_SUA | IT_SUPPORT → IT_MANAGEMENT theo nhiệm vụ quản lý 25–30 kỹ thuật viên, SLA, ca trực, năng suất và đào tạo; cần xác nhận không phải template JD chung |
| A04-130 | `3891077174` | DE_NGHI_SUA | Giữ QA_TESTING; thay tên role bằng task data validation và xây test automation framework |
| A04-144 | `3884446141` | DE_NGHI_SUA | Giữ SECURITY; phân biệt yêu cầu policy-writing với task phối hợp pentest, phân tích kết quả và chuyển findings thành thay đổi hệ thống |
| A04-147 | `3722423668` | DE_NGHI_SUA | Giữ SOFTWARE_WEB; sửa lý do theo ưu tiên Web trực tiếp ở title hơn Mobile ở description, bỏ điều kiện tự thêm rằng Mobile phải native |
| A04-151 | `3887916439` | DE_NGHI_SUA | Giữ SOFTWARE_WEB; thay strong background PHP/frontend bằng task chuyển thiết kế/requirements thành coded website enhancements |

Các ca không xuất hiện trong bảng trên vẫn có một dòng riêng trong CSV với kết luận, lý do và bằng chứng; không chỉ rà soát các ca sửa.

### A04-063: đề nghị CHUA_RO mới, chưa áp dụng

`3904568619` – **Controls/ Data Analytics Engineer (Senior - Advisor)** hiện là CNTT/DATA_AI. Responsibilities pha nghiên cứu modeling/control/data analytics và thiết kế/prototyping hệ thống điều khiển. Machine learning cụ thể nằm ở yêu cầu chuyên môn và định hướng của nhóm; chưa đủ xác định nhiệm vụ/sản phẩm chính của người tuyển thuộc công việc CNTT hay điều khiển công nghiệp thuần ngoài A02.

Hai đoạn nhiệm vụ nguyên văn:

> Conducting research and development in modeling, control, and data analytics for solving challenging problems in the oil & gas industry

> Participating in control system design, control system prototyping, and implementation

Đề nghị CHUA_RO, `manual_is_it`, nhóm và phân nhóm trống; cần xác nhận công việc/sản phẩm thực tế và tỷ trọng xây mô hình ML/phần mềm/data pipeline so với điều khiển công nghiệp. Nếu membership CNTT được xác nhận nhưng chưa phân nhóm chuyên môn được, mới cân nhắc IT_OTHER; không dùng nhóm này để che sự chưa rõ membership.

### A04-124: đề nghị đổi nhóm quản lý đội hỗ trợ IT

`3884430597` – **Desktop Support Technician** có title frontline nhưng phần đầu Responsibilities giao quản lý nhóm kỹ thuật viên, ca trực, SLA và phát triển nhân viên. Đề nghị IT_MANAGEMENT theo chức năng quản lý đội IT, thay vì chỉ lấy break-fix làm nghề chính. Cần Dũng xác nhận đây là nhiệm vụ thực của vị trí, không phải đoạn template dùng chung; nếu vị trí chỉ hỗ trợ frontline thì giữ IT_SUPPORT. CNTT vẫn rõ trong cả hai phương án.

> Manage a team of 25-30 technicians across locations

> Enable the team with training and development

## Nhất quán với 83 quyết định đã chốt

| Quy ước đã chốt | Áp dụng trong 93 ca |
| --- | --- |
| Phân biệt quản lý chức năng/đội IT với PM delivery thuộc IT_BUSINESS | A04-078, 109, 131, 135 có quản lý đội/chức năng IT rõ, giữ IT_MANAGEMENT; A04-129 là BA/system requirements, giữ IT_BUSINESS; A04-124 đề nghị quản lý đội IT theo task |
| Title/profile nghề cụ thể và nhất quán có thể làm căn cứ; qualification không tự trở thành nhiệm vụ | A04-044/049/082 giữ ngoài CNTT với giới hạn mô tả; A04-114/117 giữ nghề CNTT nhưng sửa lý do/context evidence theo cách chốt A04-092/111/115/145/158 |
| Code và task thật quyết định Software; tên công nghệ hoặc công ty không đủ | A04-068/073/076/095/104 giữ Software, không chuyển Data/DevOps chỉ vì stack/team; A04-126/151 có backend/plugin hoặc coded website enhancements, khác A04-149 CHUA_RO chưa rõ custom code |
| SDET/QA vẫn là QA, không thành nhóm khác vì data/cloud/mobile | A04-093/120/130 giữ QA_TESTING, không tạo phân nhóm Software; nhất quán A04-100 |
| Chưa có nhiệm vụ kỹ thuật support thì giữ CHUA_RO | A04-127/137 có hỗ trợ máy tính/phần mềm/người dùng rõ nên giữ IT_SUPPORT, khác A04-128 đã duyệt CHUA_RO |
| Web/Mobile theo nghề và tầng bằng chứng, không suy Mobile từ React/Flutter | A04-119 Mobile React Native, A04-156 Web Flutter; A04-147 ưu tiên title Web trực tiếp theo A02, không thêm điều kiện native |
| Khi không đủ căn cứ xác định membership, không ép true/false | A04-063 đề nghị CHUA_RO; 4 CHUA_RO đã duyệt giữ nguyên và nằm ngoài danh sách 93 |

## Bốn CHUA_RO đã duyệt vẫn nguyên vẹn

| Sample | job_id | Trạng thái nguồn |
| --- | --- | --- |
| A04-089 | `3904090413` | CHUA_RO; Dũng, 2026-10-13; boolean/nhóm/phân nhóm trống |
| A04-128 | `3884811465` | CHUA_RO; Dũng, 2026-10-13; boolean/nhóm/phân nhóm trống |
| A04-149 | `3901929980` | CHUA_RO; Dũng, 2026-10-13; boolean/nhóm/phân nhóm trống |
| A04-153 | `3905824874` | CHUA_RO; Dũng, 2026-10-13; boolean/nhóm/phân nhóm trống |

Workbook hiện tại vẫn có **4 CHUA_RO**. Chỉ nếu đề nghị A04-063 được người duyệt chấp thuận và áp dụng trong một lượt sau, số này mới thành 5; không cộng đề nghị mới vào số nhãn đã duyệt.

## Kiểm tra đầu ra và bảo toàn

- Đủ 93/93 khóa, khớp chính xác danh sách metadata thiếu; không giao 83 khóa đã chốt. Bộ khóa workbook vẫn 160/17 dòng nguồn.
- Đọc hết 21 tập mô tả, 344.279 ký tự, 93 full descriptions. Đối chiếu title/description theo job_id với CSV blind, raw postings và dự đoán v0.2.0 lưu sẵn; tất cả khớp.
- **93/93 evidence nguồn** có thật trong trường được chỉ định. **141/141 đoạn trích bổ sung/đề nghị** khớp nguyên văn nguồn, được kiểm tra offset và hash; hai đoạn dùng title được ghi rõ field, không giả làm description. Nguyên văn tồn tại không tự chứng minh qualification là task, nên context được kiểm tra riêng cho từng ca.
- `80 + 12 + 1 = 93`; đúng 2 ca đề nghị đổi core fields: CHUA_RO A04-063 và nhóm A04-124. 11 ca còn lại chỉ sửa lý do/evidence. Mã nhóm/phân nhóm dùng taxonomy hiện có; boolean trống với CHUA_RO, nhóm ngoài CNTT trống, subgroup chỉ dành cho SOFTWARE.
- SHA-256/kích thước/mtime mọi hiện vật có sẵn khớp trước/sau, gồm cả workbook, raw, taxonomy/classifier, dự đoán và các báo cáo cũ. HEAD/index/diff tracked giữ nguyên. File phân công tại C:\ được đọc bằng ZIP/XML, không chạy macro và không sửa.
- [Audit và vật liệu đọc](../data/analytics/a04_remaining93_review_20261013/) lưu full text, đề nghị riêng từng batch, evidence offsets và [kết quả kiểm tra](../data/analytics/a04_remaining93_review_20261013/review_validation.json). Các dữ liệu lớn nằm trong analytics bị Git ignore; CSV/tài liệu đề nghị mới có thể review trong workspace.

Không sửa workbook nguồn, không điền reviewer/reviewed_date, không sửa raw/taxonomy/classifier, không chạy ETL, không làm A05, không commit/push.

## Nghiệm thu A04 và bước tiếp theo

Đã đối chiếu file phân công **C:\Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsm**, sheet `Cong viec`, dòng **21**. Xem [đối chiếu tiêu chí hoàn thành A04](a04_completion_criteria.md) để phân biệt việc bắt buộc của A04, đánh giá độc lập và parity phối hợp TV1.

Lượt này hoàn thành **rà soát và tạo đề nghị**, chưa hoàn thành **duyệt nguồn hoặc nghiệm thu A04**. Người phụ trách cần quyết định 93 đề nghị, ghi metadata thực tế trong lượt áp dụng được cho phép sau này, rồi lập kết quả tỷ lệ đúng trên mẫu với mẫu số và ca chưa xác định rõ ràng. Ví dụ bỏ sót/lọc sai và kế hoạch sửa FP/FN phải được đối soát; sửa classifier/rule không nằm trong quyền hạn của lượt này.
