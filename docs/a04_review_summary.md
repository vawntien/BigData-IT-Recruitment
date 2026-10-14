# A04 – Áp dụng bảng chốt 93 tin và đối chiếu v0.2.0

Ngày **13/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`.

**Đã áp dụng 93/93 job_id** từ [a04_remaining93_chot.xlsx](a04_remaining93_chot.xlsx), sheet `Chot 93 tin`, đối chiếu bằng job_id. Cột H → manual_label; I tách đúng ` / ` → nhóm/phân nhóm; J → manual_reason; K → manual_evidence. Reviewer **Dũng**, reviewed_date **2026-10-13**. manual_is_it là boolean Excel true/false theo CNTT/NGOAI_CNTT; CHUA_RO để ô trống.

Đã giữ nguyên tất cả 8 trường manual của **83 quyết định trước** và **4 CHUA_RO đã duyệt**. A04-063 (`3904568619`) giữ **CNTT/DATA_AI**, cập nhật lý do phân biệt task data analytics với qualification ML; A04-124 (`3884430597`) chuyển **IT_MANAGEMENT** theo task quản lý đội hỗ trợ IT. Bảng chốt có 80 giữ nguyên nội dung và 13 sửa lý do/evidence/nhóm. Số ca bỏ qua: **0**; không phát hiện nguồn khác snapshot bảng quyết định hoặc evidence sai nguyên văn/ngữ cảnh.

## Sao lưu, nguồn và kiểm tra

- Hai workbook đã sao lưu trước ghi tại [backups](../data/analytics/a04_apply_remaining93_20261013/backups/), kèm [manifest SHA-256](../data/analytics/a04_apply_remaining93_20261013/backup_manifest.json); sao lưu cả báo cáo/CSV trước sửa.
- Workbook chính đủ **160 dòng / 160 job_id**; workbook bổ sung đủ **17 dòng / 17 job_id**; hợp **177 dòng nguồn / 176 job_id duy nhất**. Ca chung `3905848702` khớp cả 8 trường manual, không xung đột.
- Metadata/lý do/evidence không thiếu: **0 dòng / 0 job_id**; [danh sách thiếu metadata](a04_missing_review_metadata.csv) giữ header, không còn bản ghi.
- Title/description của 176 khóa khớp workbook, CSV blind, raw và dự đoán lưu theo job_id; 11 raw CSV khớp manifest. Cả 93 snapshot current_* và hash nguồn khớp trước sửa; mỗi đoạn evidence được kiểm tra field/offset/ngữ cảnh riêng. Sau ghi kiểm tra **265 đoạn evidence** trên 177 dòng nguồn.
- Chỉ sửa ô manual của 93 ca trong workbook chính, giữ nguyên mọi ô khác và nội dung mọi ZIP entry ngoài worksheet đó. Workbook bổ sung giữ nguyên byte. [Script](../src/apply_a04_remaining93.py), [plan/context trước ghi](../data/analytics/a04_apply_remaining93_20261013/checked_plan.json) và [audit sau ghi](../data/analytics/a04_apply_remaining93_20261013/application_validation.json) lưu bằng chứng bảo toàn.

## Kết quả tính lại từ dữ liệu

JOIN nhãn nguồn cuối với [dự đoán 160 đã lưu](../data/analytics/a04_taxonomy_v0_2_0_20261008/seed42_v020_predictions_private.jsonl) và [dự đoán 17 đã lưu](../data/analytics/a04_taxonomy_v0_2_0_20261008/accept_downgrade_predictions_private.jsonl); taxonomy **v0.2.0**, SHA-256 `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d`. Không đọc sheet tỷ lệ trong XLSX để tính kết quả, không chạy classifier hoặc ETL.

Đây là tỷ lệ mô tả **mẫu phát triển** seed42 có chọn ca phủ nghề/ngữ cảnh, đã được dùng khi hỗ trợ rà soát; không là đánh giá độc lập hoặc accuracy toàn dataset. Hai mẫu có cơ chế chọn khác nhau và được báo riêng, không gộp 177 dòng thành mẫu độc lập.

### Mẫu chính 160

| Máy v0.2.0 | CNTT | NGOAI_CNTT | CHUA_RO | Tổng |
| --- | ---: | ---: | ---: | ---: |
| ACCEPT | 76 | 0 | 3 | 79 |
| REJECT | 5 | 51 | 1 | 57 |
| REVIEW | 9 | 15 | 0 | 24 |
| Tổng | 90 | 66 | 4 | 160 |

CHUA_RO: **4/160**; máy REVIEW: **24/160**, trong đó **24** có nhãn người đọc rõ. TP=76, TN=51, FP=0, FN=5.

| Chỉ số và mẫu số | Tử số/mẫu số, kết quả |
| --- | --- |
| Khớp membership khi máy quyết định | 127/132 = 96.21% |
| Độ phủ quyết định trên nhãn rõ | 132/156 = 84.62% |
| Độ phủ quyết định trên toàn mẫu | 136/160 = 85.00% |
| Quyết định đúng trên toàn mẫu nhãn rõ | 127/156 = 81.41% |
| Precision trên ca máy ACCEPT có nhãn rõ | 76/76 = 100.00% |
| Recall có điều kiện trên ca máy ACCEPT/REJECT | 76/81 = 93.83% |
| Máy ACCEPT trên tất cả CNTT đã duyệt | 76/90 = 84.44% |
| Khớp nhóm chính: máy ACCEPT/người đọc CNTT | 73/76 = 96.05% |
| Khớp phân nhóm: cả hai nhóm chính SOFTWARE | 29/38 = 76.32% |

### Mẫu bổ sung 17

| Máy v0.2.0 | CNTT | NGOAI_CNTT | CHUA_RO | Tổng |
| --- | ---: | ---: | ---: | ---: |
| ACCEPT | 0 | 0 | 0 | 0 |
| REJECT | 3 | 0 | 0 | 3 |
| REVIEW | 13 | 1 | 0 | 14 |
| Tổng | 16 | 1 | 0 | 17 |

CHUA_RO: **0/17**; máy REVIEW: **14/17**, trong đó **14** có nhãn người đọc rõ. TP=0, TN=0, FP=0, FN=3.

| Chỉ số và mẫu số | Tử số/mẫu số, kết quả |
| --- | --- |
| Khớp membership khi máy quyết định | 0/3 = 0.00% |
| Độ phủ quyết định trên nhãn rõ | 3/17 = 17.65% |
| Độ phủ quyết định trên toàn mẫu | 3/17 = 17.65% |
| Quyết định đúng trên toàn mẫu nhãn rõ | 0/17 = 0.00% |
| Precision trên ca máy ACCEPT có nhãn rõ | 0/0: không xác định (mẫu số 0) |
| Recall có điều kiện trên ca máy ACCEPT/REJECT | 0/3 = 0.00% |
| Máy ACCEPT trên tất cả CNTT đã duyệt | 0/16 = 0.00% |
| Khớp nhóm chính: máy ACCEPT/người đọc CNTT | 0/0: không xác định (mẫu số 0) |
| Khớp phân nhóm: cả hai nhóm chính SOFTWARE | 0/0: không xác định (mẫu số 0) |

Tỷ lệ khớp khi máy quyết định dùng `(ACCEPT/CNTT + REJECT/NGOAI_CNTT) / ca nhãn rõ và máy ACCEPT/REJECT`. Độ phủ trên nhãn rõ dùng cùng số ca máy quyết định chia tổng CNTT+NGOAI_CNTT. Tỷ lệ quyết định đúng trên toàn mẫu nhãn rõ tính REVIEW là chưa tạo quyết định đúng, không ánh xạ thành REJECT. Precision/recall có điều kiện không bao gồm CHUA_RO/REVIEW; vì vậy báo thêm ACCEPT trên tất cả CNTT đã duyệt để thể hiện phần máy chưa quyết định.

## Bất đồng và CHUA_RO

[Bảng bất đồng](a04_prediction_disagreements.csv) có **61 job_id duy nhất**: GROUP_MISMATCH=3, MACHINE_REVIEW=37, MANUAL_CHUA_RO=4, MEMBERSHIP_MISMATCH=8, SUBGROUP_MISMATCH=9. Máy REVIEW có **37 khóa duy nhất** trong hợp hai mẫu; ca chung REVIEW chỉ tính một lần. Khác subgroup chỉ so khi cả hai nhóm chính SOFTWARE, không đếm lại ca khác nhóm. Ca REVIEW/CHUA_RO giữ các trạng thái gốc trong ma trận.

**4 CHUA_RO** đều đã duyệt; boolean/nhóm/phân nhóm trống, vẫn cần thông tin nếu muốn nhãn rõ. Không tạo CHUA_RO thứ năm từ đề nghị cũ A04-063.

| Sample | job_id | Máy | Thông tin còn thiếu / lý do đã duyệt |
| --- | --- | --- | --- |
| A04-089 | `3904090413` | REJECT | Giữ CHUA_RO: tuyển nhiều chức năng, không chỉ định nghề của người được tuyển. |
| A04-128 | `3884811465` | ACCEPT | Mô tả chủ yếu vận chuyển thiết bị, cover tech và go-live; chưa xác định cài đặt, xử lý sự cố hay hỗ trợ người dùng. Chốt CHUA_RO; boolean và nhóm phải để trống. |
| A04-149 | `3901929980` | ACCEPT | Giữ CHUA_RO: graphic/marketing và WordPress pha trộn; chưa rõ phần phát triển web và nghề chính. |
| A04-153 | `3905824874` | ACCEPT | Vai trò gồm đào tạo kỹ thuật và hành chính, chưa xác định nhiệm vụ delivery dự án IT đủ rõ. Chốt CHUA_RO, không giữ IT_MANAGEMENT chỉ từ chức danh. |

## FP/FN và đề xuất xử lý

Mẫu chính có **FP=0, FN=5**; mẫu bổ sung có **FP=0, FN=3**. FP là ACCEPT/NGOAI_CNTT, FN là REJECT/CNTT. Không có FP xác nhận trong hai mẫu, nên không tạo ví dụ FP. REVIEW chưa quyết định và CHUA_RO không được tính thành FP/FN. Sai nhóm/phân nhóm được báo riêng.

| Mẫu | Sample | job_id | Title của FN | Nhóm người duyệt | Reason code máy đã lưu |
| --- | --- | --- | --- | --- | --- |
| 160 | A04-030 | `3899522608` | Philips or Carestream PACS solutions | IT_SUPPORT | NO_IT_ROLE_EVIDENCE |
| 160 | A04-036 | `3884442452` | Workday Integration - C2H | SOFTWARE | NO_IT_ROLE_EVIDENCE |
| 160 | A04-037 | `3887714064` | Junior Scrum Master | IT_BUSINESS | NO_IT_ROLE_EVIDENCE |
| 160 | A04-066 | `3251984218` | SAP BTP | SOFTWARE | NO_IT_ROLE_EVIDENCE |
| 160 | A04-081 | `3904363315` | Senior Oracle Cloud Financial Analyst - Fusion, PaaS, ERP, SAP (Hybrid LA / Houston) | IT_BUSINESS | OUTSIDE_IT_ROLE |
| 17 | bổ sung | `3903891231` | Lead Research Scientist | DATA_AI | NO_IT_ROLE_EVIDENCE |
| 17 | bổ sung | `3904949360` | Programmer | SOFTWARE | NO_IT_ROLE_EVIDENCE |
| 17 | bổ sung | `3906223537` | ECC Designer/Programmer | NETWORK_SYSTEMS | NO_IT_ROLE_EVIDENCE |

Ví dụ `3899522608` có nhiệm vụ cấu hình/hỗ trợ Philips và Carestream PACS; `3884442452` có tích hợp Workday. Hai ca là CNTT theo nhiệm vụ hệ thống, máy REJECT. Lý do/bằng chứng nguyên văn của từng ca, rule/reason/evidence máy nằm trong [bảng bất đồng](a04_prediction_disagreements.csv) và [JSON đối chiếu](../data/analytics/a04_apply_remaining93_20261013/comparison_summary.json).

Bảy FN mang NO_IT_ROLE_EVIDENCE: rule hiện tại chưa thu được bằng chứng nghề IT, dù người duyệt xác định có nhiệm vụ IT. Riêng `3904363315` (Oracle Cloud Financial Analyst) mang OUTSIDE_IT_ROLE: cần đối soát exclusion nghề tài chính với task triển khai/cấu hình Oracle Financials đã duyệt IT_BUSINESS. Cần đối soát task/title/evidence để phân biệt thiếu alias nghề với gate ngữ cảnh hoặc ưu tiên; không coi riêng reason code là chứng minh nguyên nhân gốc. Đề xuất cho lượt sửa được phép: bổ sung hoặc điều chỉnh rule theo nhiệm vụ PACS, Workday, exclusion Oracle và các ca trong bảng; kiểm tra ca đối chứng ngoài CNTT, giữ ranh giới qualification/công ty/cộng tác, tăng version/hash/changelog và xác minh lại sau sửa. Lượt này chỉ ghi nhận và đề xuất, chưa triển khai hoặc xác minh sửa bộ lọc.

## Nội dung nhãn thay đổi trong 93 ca

Các ca dưới đây thay lý do/evidence hoặc nhóm; mọi ca trong 93 đều được ghi metadata. Chỉ **A04-124** đổi core field (nhóm), không đổi membership hoặc subgroup của ca nào. Các cột H/J/K được giữ đúng nguyên văn bảng chốt, không tự thay bằng đoạn trích bổ sung của CSV đề nghị.

| Sample | job_id | Trường thay đổi so với workbook sao lưu |
| --- | --- | --- |
| A04-051 | `3901379229` | manual_evidence, reviewer, reviewed_date |
| A04-063 | `3904568619` | manual_reason, reviewer, reviewed_date |
| A04-072 | `3899519477` | manual_evidence, reviewer, reviewed_date |
| A04-098 | `3901944307` | manual_evidence, reviewer, reviewed_date |
| A04-102 | `3900979722` | manual_reason, reviewer, reviewed_date |
| A04-114 | `3900947565` | manual_reason, manual_evidence, reviewer, reviewed_date |
| A04-117 | `3895521585` | manual_reason, reviewer, reviewed_date |
| A04-120 | `3901387816` | manual_evidence, reviewer, reviewed_date |
| A04-124 | `3884430597` | manual_primary_group_code, manual_reason, manual_evidence, reviewer, reviewed_date |
| A04-130 | `3891077174` | manual_evidence, reviewer, reviewed_date |
| A04-144 | `3884446141` | manual_reason, manual_evidence, reviewer, reviewed_date |
| A04-147 | `3722423668` | manual_reason, reviewer, reviewed_date |
| A04-151 | `3887916439` | manual_evidence, reviewer, reviewed_date |

## Đối chiếu nghiệm thu A04

Theo [a04_completion_criteria.md](a04_completion_criteria.md), phần mẫu 100–200 tin, nhãn/metadata, tỷ lệ có tử số/mẫu số và ví dụ lọc sai đã có đầu ra cập nhật. Mẫu chính vẫn 160 tin, 4 CHUA_RO được giữ riêng theo hướng dẫn; không bắt buộc ép thành nhãn nhị phân để đủ số. Việc còn lại:

1. Đối soát nguyên nhân và chốt cách xử lý các FN/bất đồng/REVIEW với người phụ trách.
2. Triển khai và xác minh sửa FP/FN nếu được phê duyệt; lượt này không sửa classifier.
3. Người rà soát xác nhận đầu ra và tiêu chí A04; chưa tự đánh dấu hoàn thành/100%.

Mẫu đánh giá độc lập cần khi tuyên bố chất lượng sau sửa/toàn dataset; parity Spark/JVM và canonical phục vụ D06/TV1, không phải hai tiêu chí riêng của I21/A04. Lượt này **chưa tự đánh dấu A04 hoàn thành**, không cập nhật tiến độ workbook phân công. Không sửa raw/title/description/job_id/taxonomy/classifier, không chạy ETL, không làm A05, không commit/push.
