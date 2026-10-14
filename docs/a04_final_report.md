# A04 – Hồ sơ tổng kết để rà soát nghiệm thu

Ngày lập hồ sơ **14/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`. **Đề nghị trạng thái: “Sẵn sàng rà soát nghiệm thu”.** Đây là đề nghị để người rà soát xác nhận đầu ra và giới hạn chấp nhận; chưa ghi A04 hoàn thành/100%, người nghiệm thu hoặc ngày nghiệm thu.

## 1. Mục tiêu, phạm vi và nguồn bằng chứng

A04 kiểm tra bộ lọc CNTT theo nghề/nhiệm vụ, trên mẫu có cả tin được chọn và bị loại; đối chiếu nhãn thủ công, membership, nhóm/phân nhóm, FP/FN và các ca máy chưa quyết định. Hồ sơ tổng hợp nhãn đã duyệt và đầu ra **đã lưu** của v0.2.0 → v0.2.1 → candidate v0.2.2. Active vẫn v0.2.0; thông tin kỹ thuật bàn giao tại [a04_handoff_tv1.md](a04_handoff_tv1.md).

Nguồn chính:

- [Tiêu chí A04](a04_completion_criteria.md): phân công `Cong viec!F21:I21`, đầu ra H21 và yêu cầu xác nhận tại `Tong quan!D8`; [trích ngữ cảnh phân công](../data/analytics/a04_remaining93_review_20261013/assignment_context.json).
- [Kiểm tra nhãn cuối và baseline v0.2.0](a04_validation_report.md), [báo cáo round 1/v0.2.1](a04_filter_fix_round1_report.md), [báo cáo round 2/v0.2.2](a04_filter_fix_round2_report.md).
- [Workbook chính 160](../data/analytics/a04_manual_seed42/a04_manual_labels_filled.xlsx), sheet `A04 manual labels`; [workbook bổ sung 17](../data/analytics/a04_taxonomy_v0_2_0_20261008/accept_downgrades_for_review_blind.xlsx), sheet `Review`; [snapshot nguồn đã duyệt](../data/analytics/a04_taxonomy_v0_2_2_20261014/baseline/source_rows.json).
- [Đối chiếu round 1](../data/analytics/a04_taxonomy_v0_2_1_20261014/comparison_summary.json), [đối chiếu round 2](../data/analytics/a04_taxonomy_v0_2_2_20261014/comparison_summary.json), [176 prediction candidate](../data/analytics/a04_taxonomy_v0_2_2_20261014/all_predictions.jsonl), [bảng delta 176 khóa](../data/analytics/a04_taxonomy_v0_2_2_20261014/job_comparison.csv).

Các tài liệu ngày 13/10 và [CSV bất đồng cũ](a04_prediction_disagreements.csv) mô tả **v0.2.0**, gồm 61 khóa bất đồng/CHUA_RO. Chúng được giữ nguyên làm lịch sử; hàng đợi candidate hiện hành ở mục 6 dưới đây, không lấy số cũ làm số v0.2.2. [Phương án sửa](a04_filter_fix_plan.md) cung cấp chẩn đoán ban đầu; các nguyên nhân còn lại được đối chiếu với trace candidate, không coi mọi đề xuất trong phương án là đã triển khai.

Lượt tổng hợp này chỉ đọc dữ liệu và tạo hai tài liệu. Không sửa raw, title/description/job_id, nhãn/metadata, classifier/config hoặc trace cũ; không thêm quy tắc, chạy classifier/ETL/toàn dataset, làm A05, commit hoặc push.

## 2. Cách chọn mẫu và tình trạng nhãn

**160 tin chính + 17 tin bổ sung = 177 dòng nguồn, 176 job_id duy nhất.** `3905848702` (Privacy Engineer) xuất hiện ở cả hai nguồn, khớp cả 8 trường manual và prediction; chỉ tính một lần khi tổng hợp hàng đợi. JOIN bằng job_id canonical, không bằng STT/sample_id/dòng Excel.

Mẫu chính đóng băng theo **seed42 trên dự đoán v0.1.0**: các tầng không giao nhau, giữ ca phủ nghề/ngữ cảnh trước rồi điền quota theo SHA-256 UTF-8 của `42:<job_id>`, tie-break bằng job_id số; trộn thứ tự bản đọc theo cùng hash. [Manifest lấy mẫu](../data/analytics/a04_manual_seed42/run_manifest.json) và [hướng dẫn lấy mẫu](a04_manual_labeling.md) lưu requested/available/achieved của từng phần phủ.

| Tầng khi chọn mẫu, v0.1.0 | Số tin chính |
| --- | ---: |
| ACCEPT một nhóm, ngoài tầng đặc biệt | 50 |
| ACCEPT nhiều ứng viên hoặc Software Mobile/Web | 30 |
| REJECT có exclusion | 30 |
| REJECT không có bằng chứng | 20 |
| REVIEW | 30 |
| Tổng | 160 |

Có chọn chủ đích để phủ nhóm nghề, Mobile/Web, acronym, nhiều ứng viên, exclusion và ca có metadata IT nhưng không có bằng chứng nghề. Không có ca khả dụng ACCEPT/DESCRIPTION_ROLE_TASK hoặc REVIEW do thiếu title trong lần chọn mẫu này. Quota 80 ACCEPT/50 REJECT/30 REVIEW là **thiết kế ban đầu**, không phải ma trận v0.2.2.

17 tin bổ sung là **toàn bộ các ca rời ACCEPT khi đổi v0.1.0 → v0.2.0**, lấy để rà tác động chính sách mô tả, theo [báo cáo so sánh v0.2.0](a04_v020_comparison.md). Đây là tập ca khó theo chuyển đổi, không phải mẫu ngẫu nhiên mới. Hai mẫu được báo tỷ lệ riêng; không gộp 177 dòng thành 177 quan sát độc lập.

| Nguồn nhãn đã duyệt | CNTT | NGOAI_CNTT | CHUA_RO | Tổng |
| --- | ---: | ---: | ---: | ---: |
| Chính | 90 | 66 | 4 | 160 |
| Bổ sung | 16 | 1 | 0 | 17 |
| Hợp theo job_id | 105 | 67 | 4 | 176 |

Nhãn/lý do/evidence/reviewer/ngày duyệt đã đủ **177/177 dòng nguồn, 176/176 khóa**; thiếu metadata **0 dòng / 0 khóa**. 83 quyết định trước được giữ, 93 quyết định còn lại đã áp dụng. Metadata duyệt nhãn lưu reviewer `Dũng`, reviewed_date `2026-10-13`; đây là metadata nhãn, **không phải xác nhận người/ngày nghiệm thu A04**. Workbook hiện hành khớp toàn bộ snapshot nguồn round 2. Audit [áp dụng 93 tin](../data/analytics/a04_apply_remaining93_20261013/application_validation.json) và [báo cáo nhãn](a04_validation_report.md) lưu kiểm tra bảo toàn, nguồn và 265 đoạn evidence trên 177 dòng.

A04-063 (`3904568619`) giữ CNTT/DATA_AI; A04-124 (`3884430597`) đã duyệt IT_MANAGEMENT. Không đổi nhãn để tăng mức khớp máy.

**4 CHUA_RO đã duyệt** nằm trong mẫu chính; manual_is_it/nhóm/phân nhóm đều trống. CHUA_RO không phải nhãn ngoài CNTT và không được dùng làm negative gold:

| job_id | Sample | Máy v0.2.2 | Thông tin còn thiếu theo quyết định duyệt |
| --- | --- | --- | --- |
| `3904090413` | A04-089 | REJECT | Tuyển nhiều chức năng, chưa xác định nghề của người được tuyển. |
| `3884811465` | A04-128 | ACCEPT | Vận chuyển thiết bị/cover tech/go-live; chưa rõ cài đặt, xử lý sự cố hoặc hỗ trợ người dùng. |
| `3901929980` | A04-149 | ACCEPT | Graphic/marketing/WordPress pha trộn; chưa rõ nhiệm vụ phát triển web và nghề chính. |
| `3905824874` | A04-153 | ACCEPT | Đào tạo kỹ thuật/hành chính; chưa xác định đủ nhiệm vụ delivery dự án IT. |

## 3. Quy ước đánh giá và nguồn dự đoán

Tính lại từ workbook cuối và các trace đã lưu; không đọc tỷ lệ từ sheet XLSX và không gọi classifier trong lượt này:

| Phiên bản | Trace mẫu chính 160 | Trace bổ sung 17 |
| --- | --- | --- |
| v0.2.0 | [seed42_v020_predictions_private.jsonl](../data/analytics/a04_taxonomy_v0_2_0_20261008/seed42_v020_predictions_private.jsonl) | [accept_downgrade_predictions_private.jsonl](../data/analytics/a04_taxonomy_v0_2_0_20261008/accept_downgrade_predictions_private.jsonl) |
| v0.2.1 | [seed42_v021_predictions_private.jsonl](../data/analytics/a04_taxonomy_v0_2_1_20261014/seed42_v021_predictions_private.jsonl) | [supplement17_v021_predictions_private.jsonl](../data/analytics/a04_taxonomy_v0_2_1_20261014/supplement17_v021_predictions_private.jsonl) |
| v0.2.2 | [seed42_v022_predictions_private.jsonl](../data/analytics/a04_taxonomy_v0_2_2_20261014/seed42_v022_predictions_private.jsonl) | [supplement17_v022_predictions_private.jsonl](../data/analytics/a04_taxonomy_v0_2_2_20261014/supplement17_v022_predictions_private.jsonl) |

V0.2.0 lưu prediction trong `new_prediction`; hai candidate lưu trực tiếp. Với nhãn rõ: TP=ACCEPT/CNTT, TN=REJECT/NGOAI_CNTT, FP=ACCEPT/NGOAI_CNTT, FN=REJECT/CNTT. Gọi D=TP+TN+FP+FN, C=CNTT+NGOAI_CNTT và N=toàn mẫu:

- Khớp khi máy quyết định = `(TP+TN)/D`; độ phủ nhãn rõ = `D/C`; độ phủ toàn mẫu = số ACCEPT+REJECT trên mọi nhãn / N.
- Quyết định đúng trên nhãn rõ = `(TP+TN)/C`; REVIEW chưa tạo quyết định đúng nhưng **không chuyển thành REJECT/FN**. CHUA_RO loại khỏi C/D, vẫn giữ trong ma trận và độ phủ toàn mẫu.
- Precision = `TP/(TP+FP)`; recall có điều kiện = `TP/(TP+FN)`, chỉ trên ca máy quyết định và nhãn rõ. Báo thêm ACCEPT/tất cả CNTT để thấy phần abstain. Mẫu số 0 là không xác định, không ghi 0% hoặc 100%.
- Khớp nhóm chỉ trên máy ACCEPT/người duyệt CNTT. Khớp subgroup chỉ khi **cả hai nhóm chính SOFTWARE**; khác nhóm không đếm thêm thành lỗi subgroup.

## 4. So sánh v0.2.0 → v0.2.1 → v0.2.2

### Mẫu chính 160

| Đại lượng | v0.2.0 | v0.2.1 | v0.2.2 |
| --- | ---: | ---: | ---: |
| TP | 76 | 77 | 79 |
| TN | 51 | 51 | 51 |
| FP | 0 | 0 | 0 |
| FN | 5 | 5 | 3 |
| CHUA_RO | 4 | 4 | 4 |
| REVIEW/toàn mẫu | 24/160 = 15.00% | 23/160 = 14.38% | 23/160 = 14.38% |
| Khớp membership khi máy quyết định | 127/132 = 96.21% | 128/133 = 96.24% | 130/133 = 97.74% |
| Độ phủ quyết định trên nhãn rõ | 132/156 = 84.62% | 133/156 = 85.26% | 133/156 = 85.26% |
| Độ phủ quyết định trên toàn mẫu | 136/160 = 85.00% | 137/160 = 85.62% | 137/160 = 85.62% |
| Quyết định đúng trên nhãn rõ | 127/156 = 81.41% | 128/156 = 82.05% | 130/156 = 83.33% |
| Precision trên ACCEPT có nhãn rõ | 76/76 = 100.00% | 77/77 = 100.00% | 79/79 = 100.00% |
| Recall có điều kiện ACCEPT/REJECT | 76/81 = 93.83% | 77/82 = 93.90% | 79/82 = 96.34% |
| ACCEPT/tất cả CNTT đã duyệt | 76/90 = 84.44% | 77/90 = 85.56% | 79/90 = 87.78% |
| Khớp nhóm trên ACCEPT/CNTT | 73/76 = 96.05% | 74/77 = 96.10% | 76/79 = 96.20% |
| Khớp subgroup khi hai nhóm SOFTWARE | 29/38 = 76.32% | 29/38 = 76.32% | 30/39 = 76.92% |

### Mẫu bổ sung 17

| Đại lượng | v0.2.0 | v0.2.1 | v0.2.2 |
| --- | ---: | ---: | ---: |
| TP | 0 | 3 | 4 |
| TN | 0 | 0 | 0 |
| FP | 0 | 0 | 0 |
| FN | 3 | 3 | 2 |
| CHUA_RO | 0 | 0 | 0 |
| REVIEW/toàn mẫu | 14/17 = 82.35% | 11/17 = 64.71% | 11/17 = 64.71% |
| Khớp membership khi máy quyết định | 0/3 = 0.00% | 3/6 = 50.00% | 4/6 = 66.67% |
| Độ phủ quyết định trên nhãn rõ | 3/17 = 17.65% | 6/17 = 35.29% | 6/17 = 35.29% |
| Độ phủ quyết định trên toàn mẫu | 3/17 = 17.65% | 6/17 = 35.29% | 6/17 = 35.29% |
| Quyết định đúng trên nhãn rõ | 0/17 = 0.00% | 3/17 = 17.65% | 4/17 = 23.53% |
| Precision trên ACCEPT có nhãn rõ | 0/0: không xác định | 3/3 = 100.00% | 4/4 = 100.00% |
| Recall có điều kiện ACCEPT/REJECT | 0/3 = 0.00% | 3/6 = 50.00% | 4/6 = 66.67% |
| ACCEPT/tất cả CNTT đã duyệt | 0/16 = 0.00% | 3/16 = 18.75% | 4/16 = 25.00% |
| Khớp nhóm trên ACCEPT/CNTT | 0/0: không xác định | 3/3 = 100.00% | 4/4 = 100.00% |
| Khớp subgroup khi hai nhóm SOFTWARE | 0/0: không xác định | 1/1 = 100.00% | 2/2 = 100.00% |

FP trên nhãn ngoài CNTT là 0/66 ở mẫu chính và 0/1 ở mẫu bổ sung trong cả ba phiên bản. REJECT trên tất cả CNTT (FN/CNTT, tách REVIEW) ở mẫu chính: 5/90 = 5.56% → 5/90 = 5.56% → 3/90 = 3.33%; bổ sung: 3/16 = 18.75% → 3/16 = 18.75% → 2/16 = 12.50%. Đây là các tỷ lệ mô tả mẫu, không ước lượng FP/FN toàn tập.

### Ma trận candidate v0.2.2

| Mẫu | Máy | CNTT | NGOAI_CNTT | CHUA_RO | Tổng |
| --- | --- | ---: | ---: | ---: | ---: |
| 160 | ACCEPT | 79 | 0 | 3 | 82 |
| 160 | REJECT | 3 | 51 | 1 | 55 |
| 160 | REVIEW | 8 | 15 | 0 | 23 |
| 160 | Tổng | 90 | 66 | 4 | 160 |
| 17 | ACCEPT | 4 | 0 | 0 | 4 |
| 17 | REJECT | 2 | 0 | 0 | 2 |
| 17 | REVIEW | 10 | 1 | 0 | 11 |
| 17 | Tổng | 16 | 1 | 0 | 17 |

Hợp theo job_id: FN **8 → 8 → 5**, REVIEW **37 → 33 → 33**. V0.2.2 có 23+11=34 dòng REVIEW nhưng **33 khóa**, gồm **17 CNTT + 16 NGOAI_CNTT** vì ca chung là CNTT/REVIEW. Bất đồng nhóm 3 và subgroup 9 giữ nguyên qua hai round.

## 5. Sửa đã có, bằng chứng kiểm tra và giới hạn

Round 1 triển khai P1a heading explicit và bốn entry P2; P1a đổi cấu trúc/diagnostics ở 22 khóa nhưng không đổi membership, P2 chuyển 4 REVIEW thành ACCEPT. Round 2 chỉ triển khai ba họ P3 được phép, chuyển 3 REJECT thành ACCEPT. Không thay tier/priority/conflict/actor/blocker hoặc nhãn để giải quyết bất đồng. Chi tiết trước/sau, rule, evidence/offset nằm trong hai báo cáo round và từng [stage round 1](../data/analytics/a04_taxonomy_v0_2_1_20261014/stages/), [stage round 2](../data/analytics/a04_taxonomy_v0_2_2_20261014/stages/).

| job_id | Sửa đã xác minh trên mẫu | Kết quả sau sửa |
| --- | --- | --- |
| `3902872004` | P2_ETL: task `creating etl pipeline` ở description s2 UNKNOWN `[216,237)`, có title hint/context cùng unit. | REVIEW → ACCEPT/DATA_AI |
| `3904090041` | P2_SOFTWARE_TITLE: phrase `software development engineer` ở title `[0,29)`; giữ ưu tiên QA cho SDET. | REVIEW → ACCEPT/SOFTWARE/OTHER |
| `3904392069` | P2_CYBER: `respond to cyber incidents` `[442,468)` + context `cyber incidents` `[453,468)`, cùng s2 UNKNOWN. | REVIEW → ACCEPT/SECURITY |
| `3906230754` | P2_DATABASE: task quản trị DB + database + storage/retrieval/security cùng s17 RESPONSIBILITIES; không lấy ML qualification. | REVIEW → ACCEPT/DATA_AI |
| `3884442452` | P3_INTEGRATION: workflow `design, develop, test, deploy, and manage integration` s2 ROLE `[182,235)` + Workday platform `[239,255)` và title hint. | FN → ACCEPT/SOFTWARE/OTHER |
| `3887714064` | P3_IT_DELIVERY: `manages all aspects` `[1760,1779)` + `it epics` `[1796,1804)` + `planning to deployment` `[1810,1832)`, cùng s14 RESPONSIBILITIES. | FN → ACCEPT/IT_BUSINESS |
| `3904949360` | P3_APPLICATION_MAINTENANCE_MIGRATION: `migrate and upgrade` `[1202,1221)`, origin client/server `[1246,1271)`, target Web-based `[1277,1298)`, cùng s13 ROLE. | FN → ACCEPT/SOFTWARE/WEB |

Ranges là Unicode code point `[start,end)` trong trường nguyên bản sau CSV parse. Qualification “Develop applications” của Programmer vẫn bị chặn; Web lấy từ nhiệm vụ migration. Không có FP xác nhận trong hai mẫu, nên không tạo ví dụ “FP đã sửa”.

Bằng chứng test **đã lưu**, không chạy lại trong lượt chỉ sửa tài liệu: round 1 **38 test qua**; round 2 **46 test qua, 0 failure/error/skip**. Mỗi stage round 2 có 40 control round 1, 45 control round 2 và 57 ca minh họa. Baseline replay round 2 khớp **176/176** prediction toàn bộ trường; không phát hiện hồi quy mới trên mẫu/controls. [tests_result.json](../data/analytics/a04_taxonomy_v0_2_2_20261014/tests_result.json), [log test](../data/analytics/a04_taxonomy_v0_2_2_20261014/tests_round2.log), [saved_output_verification.json](../data/analytics/a04_taxonomy_v0_2_2_20261014/saved_output_verification.json) và [independent_verification.json](../data/analytics/a04_taxonomy_v0_2_2_20261014/independent_verification.json) là bằng chứng. Tên `independent_verification` ở đây chỉ kiểm tra phép tính/evidence từ đầu ra lưu, **không phải đánh giá bằng mẫu độc lập**.

Catalog còn hẹp: workflow integration cần chuỗi action rõ; migration cần origin/target cùng unit; title sản phẩm/profile, heading implicit dính chữ và domain exclusion chưa được xử lý hết. Không có FP mới trong mẫu/controls không chứng minh ngoài mẫu không có FP. Chưa xác minh parity Spark/JVM hoặc tích hợp canonical D05/D06.

## 6. Hàng đợi còn lại của candidate theo job_id

Bốn loại được giữ riêng: **5 FN, 33 REVIEW duy nhất, 3 bất đồng nhóm, 9 bất đồng subgroup**. Các tập job_id này không giao nhau, tổng **50 khóa cần đối soát kỹ thuật**; 4 CHUA_RO ở mục 2 là hàng đợi thông tin riêng. Nhiều reason/đề xuất trên một khóa không tạo thêm một ca. REVIEW là trạng thái abstain, không mặc định FN hay ngoài CNTT; chỉ FN là REJECT/CNTT.

Các hướng xử lý dưới đây là đề nghị cho lượt được phép tiếp theo, **chưa triển khai**. Chẩn đoán ban đầu từ [phương án](a04_filter_fix_plan.md) được cập nhật theo candidate; đặc biệt heading P1a đã có, nên không còn ghi thiếu heading explicit đó là nguyên nhân chưa sửa.

### 6.1. FN xác nhận – 5 khóa

| job_id | Mẫu; nghề đã duyệt | Reason v0.2.2 | Nguyên nhân còn lại | Hướng xử lý/chốt |
| --- | --- | --- | --- | --- |
| `3899522608` | 160; PACS, IT_SUPPORT | NO_IT_ROLE_EVIDENCE | Role Description đã được P1a nhận; title sản phẩm chưa có support hint, task cấu hình/support và object chưa đạt predicate hiện tại. | P3 hỗ trợ hệ thống: task/object/hint hẹp, kiểm tra ranh giới unit; không ACCEPT chỉ từ PACS/nhà cung cấp. |
| `3251984218` | 160; SAP BTP, SOFTWARE/OTHER | NO_IT_ROLE_EVIDENCE | Title sản phẩm không mở role gate; nhiều câu profile/qualification, task chưa phủ. | P5 chốt loại bằng chứng profile có thể dùng; giữ nhãn, không mở qualification hoặc direct-title sản phẩm. |
| `3904363315` | 160; Oracle Cloud Financial Analyst, IT_BUSINESS | OUTSIDE_IT_ROLE | EX_COMMERCIAL khớp financial analyst; positive functional ERP còn thiếu hint/task/object. | P3/P4 cùng xử lý positive ERP và scope exclusion; thêm positive đơn lẻ chỉ có thể chuyển về conflict REVIEW. |
| `3903891231` | 17; Lead Research Scientist, DATA_AI | NO_IT_ROLE_EVIDENCE | Scientist hint có nhưng thiếu task/context eligible; build predictive models thuộc QUALIFICATIONS. | P5 chốt nhiệm vụ nghiên cứu/data; bổ sung task nếu có căn cứ, không nhận từ scientist/SQL/ML qualification. |
| `3906223537` | 17; ECC Designer/Programmer, NETWORK_SYSTEMS | NO_IT_ROLE_EVIDENCE | Hint/task vận hành OS/network/backup chưa đạt; có software task phụ, nguy cơ nhận sai SOFTWARE. | P3/P5 chốt nghề vận hành hệ thống và task chính; đối chứng power network/PLC, kiểm tra nhóm trước nhận. |

### 6.2. REVIEW – 33 khóa, mỗi khóa một dòng

Ký hiệu reason lấy từ trace candidate: **A**=`AMBIGUOUS_TITLE_WITHOUT_CONTEXT`, **I**=`DESCRIPTION_PROCESSING_INCOMPLETE`, **X**=`POSITIVE_EXCLUSION_CONFLICT`. A có 16 khóa, I có 5, A+I có 9, X có 3. I/A+I vẫn giữ full unit và diagnostics; không tự tăng ngưỡng 500 hay bỏ cờ incomplete. Khi có P1a, section/index có thể khác chẩn đoán v0.2.0; dùng trace v0.2.2 để xác nhận offsets.

| job_id | Nhãn đã duyệt; reason | Nguyên nhân còn lại | Hướng xử lý/chốt |
| --- | --- | --- | --- |
| `3885822304` | NGOAI_CNTT; I | Fabricator: đoạn pay/benefits dính chữ còn unresolved, task kim loại không phải IT. | P1b cấu trúc phúc lợi nếu đủ chắc; giữ REVIEW hoặc REJECT sau xử lý đầy đủ, không nhận máy gia công. |
| `3886863634` | NGOAI_CNTT; A | Service Technician sửa tools/equipment ngành wind; chưa có task/object IT hay exclusion hẹp. | Chốt cơ khí; giữ REVIEW, chỉ thêm exclusion có đối chứng nếu được phép. |
| `3888484807` | CNTT/IT_SUPPORT; A | Tech Support: hint có, task technical implementation/application configuration chưa đạt support predicate; AWS qualification bị chặn. | P3 task hỗ trợ ứng dụng theo role; không chuyển DEVOPS_CLOUD từ qualification. |
| `3889128520` | CNTT/SOFTWARE; A | Interoperability: heading Duties explicit đã phủ, code/test/programming task eligible vẫn chưa đủ alias/context. | P3 phủ coding/task-object tại Duties; kiểm tra nguồn riêng, không mở toàn COMPANY. |
| `3889720090` | CNTT/SOFTWARE; A | Interoperability có cơ chế coverage tương tự khóa trên nhưng nguồn/offset riêng. | Đối soát task coding và ranges của chính khóa này; không sao nhãn theo title. |
| `3891078124` | CNTT/IT_BUSINESS; A | Program Manager: thiếu business hint/task; heading `The OpportunityJob Description:` dính chữ chưa reset. | P1b/P3 cho IT delivery; phân biệt quản lý delivery với SECURITY/IT_MANAGEMENT. |
| `3895545207` | CNTT/DATA_AI; X | DATA_AI_TITLE và EX_PHYSICAL_CONTEXT cùng khớp manufacturing/data architect; domain bị dùng như nghề loại trừ. | P4 thu hẹp domain exclusion bằng bằng chứng nghề; giữ conflict policy thật. |
| `3895563414` | CNTT/DATA_AI; A | Data Platform: task code/debug bị scope COMPANY, thiếu data task; title/profile Data Mesh chưa đủ chốt nhóm. | P1b/P5 chốt role reset và căn cứ DATA_AI; không direct-title Platform Engineer rộng. |
| `3899525341` | NGOAI_CNTT; A | Security Officer patrol cơ sở; thiếu exclusion physical-security, không có cyber task. | Giữ REVIEW; nếu thêm exclusion dùng patrol/access object, bảo vệ information security officer. |
| `3900952361` | CNTT/SOFTWARE/WEB; A | UI Architect: reusable components/library/cross-app chưa phủ; implement APIs trong câu qualification bị chặn. | P3 dùng task role, kiểm chứng Web riêng; không nhận UI/UX thuần hoặc mở qualification. |
| `3901356518` | CNTT/IT_SUPPORT; A | Applications Analyst thiếu support hint/task cho tier 1/2, tickets và production support. | P3 application-support hẹp; giữ nhóm theo nhiệm vụ hỗ trợ. |
| `3901667306` | CNTT/SOFTWARE/WEB; X | Full Stack Engineer/Civil Process: SOFTWARE_TITLE + EX_PHYSICAL_CONTEXT do civil/engineer. | P4 tách domain sản phẩm khỏi civil engineering; giữ đối chứng Civil Engineer thật. |
| `3902346478` | NGOAI_CNTT; A+I | BCBA/ABA trị liệu; benefit/referral dài unresolved, analyst ambiguity vẫn có. | P1b hoặc exclusion nghề trị liệu có context; không coi programs là applications. |
| `3902369400` | CNTT/SOFTWARE/WEB; A | UI Architect: task components/library chưa phủ, API/.NET qualification bị chặn. | P3 kiểm tra task và evidence nguồn riêng, subgroup Web riêng. |
| `3902734709` | NGOAI_CNTT; A+I | Lab Technician: isotope/batch testing, unit dài; không software QA task. | P1b ranh giới nguồn; giữ ngoài CNTT đã duyệt, không nhận QA từ batch quality testing. |
| `3902763033` | NGOAI_CNTT; A | Pest Control Technician: ambiguous technician, không IT object/exclusion cụ thể. | Giữ REVIEW hoặc exclusion pest-control hẹp; handheld computer không là nghề IT. |
| `3902786571` | NGOAI_CNTT; A | Maintenance Technician: brakes/suspension/automotive electrical, không IT task. | Đối chứng cho alias support/maintenance; không nới thành IT_SUPPORT. |
| `3902946311` | NGOAI_CNTT; A+I | Customer Success: renewal/upsell/cross-sell và profile dài; SaaS/team engineering không task IT. | Giữ REVIEW; xử lý cấu trúc không gỡ actor/collaboration guard. |
| `3903458524` | CNTT/SOFTWARE/WEB; A | Dynamics CRM: `skillsResponsibilities:` dính chữ khiến build applications vẫn bị QUALIFICATIONS. | P1b boundary hẹp có provenance/negative controls; xác minh Web riêng sau membership. |
| `3903476131` | NGOAI_CNTT; I | Store Associate: merchandising/stocking/cashiering dài, không IT evidence. | P1b cấu trúc nếu rõ; REVIEW hoặc REJECT khi đầy đủ, không nhận inventory/security. |
| `3903827844` | NGOAI_CNTT; I | Grocery business assistant: pricing/data entry/category reports dài, không task BI kỹ thuật. | Xử lý cấu trúc; reporting/data entry không cấp DATA_AI. |
| `3904369338` | NGOAI_CNTT; A | Quality Manager: sản phẩm xây dựng/manufacturing, không software testing task. | Giữ REVIEW hoặc exclusion nghề hẹp; không broaden Quality Manager thành QA_TESTING. |
| `3904396085` | CNTT/SOFTWARE; A+I | Privacy: duties dài thiếu task/anchor đủ; build software ở COMPANY, có câu loại security engineering. | P1b/P3/P5 task role và actor; không chuyển SECURITY/DEVOPS từ profile. |
| `3904398002` | CNTT/SOFTWARE; A+I | Privacy: heading skills/duties implicit dính chữ và task dài chưa giải quyết; P1a không đủ. | P1b phải chặn qualification đồng thời reset Duties; chỉ bỏ I không đủ nhận. |
| `3904420774` | CNTT/SOFTWARE; X | Software/Manufacturing Surgical Robotics: positive software và exclusion manufacturing/engineer xung đột. | P4 phân biệt nghề software với hardware/điều khiển thuần, không tắt exclusion toàn cục. |
| `3904501888` | NGOAI_CNTT; A | Advertising campaign/revenue, không software task; SQL/Tableau/campaign QA không xác định nghề IT. | Giữ REVIEW; dùng làm đối chứng business/QA/task alias. |
| `3904933805` | CNTT/SOFTWARE; A+I | Privacy: features/services/investigations dài thiếu task/anchor; nguồn này không có câu phủ định security như hai ca trước. | P1b/P3/P5 theo nguồn riêng, không chép negation của tin cùng title. |
| `3905280731` | NGOAI_CNTT; I | RN/patient care, nhiều unit unresolved, chưa có exclusion acronym phù hợp. | P1b hoặc RN exclusion có nursing context; giữ REVIEW nếu chưa xử lý đủ. |
| `3905338213` | NGOAI_CNTT; I | Mental Health Therapist: treatment/discharge, đoạn credentials dài unresolved. | P1b/exclusion nghề y tế có căn cứ; plans hoặc phần mềm quản lý bệnh nhân không là positive. |
| `3905660962` | NGOAI_CNTT; A+I | Subcontracts Administrator: procurement/RFP dài; security clearance gây ambiguity, cyber chỉ ở company. | Giữ REVIEW; clearance không là nghề SECURITY, xử lý scope riêng. |
| `3905848702` | CNTT/SOFTWARE; A+I | Privacy: duties dài thiếu task/anchor, build software ở COMPANY; ca chung hai nguồn. | P1b/P3/P5; kiểm tra nguồn riêng và tính một khóa, không chép negation của tin khác. |
| `3905852501` | CNTT/IT_BUSINESS; A+I | Finance Technology: hint/task ERP thiếu; liaison/testing Oracle dài thiếu anchor đủ. | P3/P5 triển khai hệ thống theo task/object; không nhận mọi finance analyst dùng phần mềm. |
| `3905877226` | NGOAI_CNTT; A | Test Engineer: thiết bị/manufacturing/calibration, không qa_tasks+software context. | Giữ REVIEW hoặc physical-testing exclusion hẹp; computer-automated test chưa đủ software QA. |

### 6.3. Bất đồng nhóm chính – 3 khóa

Đều máy ACCEPT/người duyệt CNTT ở mẫu chính, không phải FP/FN. Rule/nhóm máy dưới đây lấy từ trace; phần phân xử chính sách cần người phụ trách chốt.

| job_id | Nhóm máy → nhãn | Nguyên nhân đối chiếu | Hướng xử lý/chốt |
| --- | --- | --- | --- |
| `3905291167` | SOFTWARE → DATA_AI | SOFTWARE_TITLE thắng từ title Software Engineer; manual evidence định danh Data Engineer migrate model sang GCP, chưa có rule DATA_AI khớp. | Chốt role cụ thể trong body so với title chung và tier; không đảo ưu tiên toàn cục cho một ca. |
| `3900944795` | IT_OTHER → IT_SUPPORT | Chỉ GENERAL_IT_TITLE khớp IT Technician; task desktop/laptop/user/helpdesk đã duyệt chưa được support predicate nhận. | P3 phủ support task/context, kiểm tra fallback chỉ dùng khi không có nhóm chuyên môn. |
| `3884430597` | IT_SUPPORT → IT_MANAGEMENT | IT_SUPPORT_TITLE thắng Desktop Support Technician; body quản lý 25–30 kỹ thuật viên/SLA/ca trực, chưa có management rule khớp. | Chốt nhiệm vụ quản lý đội so với title support và coverage/tier; giữ nhãn A04-124 đã duyệt. |

### 6.4. Bất đồng subgroup – 9 khóa

Đều ở mẫu chính và **hai nhóm chính SOFTWARE**. Bốn ca OTHER→WEB của nhãn có task Web chưa được subgroup rule nhận; năm ca WEB→OTHER của nhãn là code annotation/evaluation với Web title. Không đếm lại ba bất đồng nhóm ở mục 6.3.

| job_id | Subgroup máy → nhãn | Nguyên nhân đối chiếu | Hướng xử lý/chốt |
| --- | --- | --- | --- |
| `3886819981` | SOFTWARE_OTHER → SOFTWARE_WEB | SOFTWARE_TITLE khớp, không subgroup rule; Magento ecommerce website/theme/layout task đã duyệt. | Phủ Web task/object hẹp trong role, không dùng skill HTML/PHP đơn lẻ. |
| `3905328583` | SOFTWARE_OTHER → SOFTWARE_WEB | Không subgroup rule; body design/implement web applications/APIs cho simulation, có incomplete diagnostic. | Kiểm tra unit/task coverage và source scope; simulation/DevOps phụ không đổi nhóm. |
| `3901379461` | SOFTWARE_OTHER → SOFTWARE_WEB | Không subgroup rule; body integration frontend/backend web application, có incomplete diagnostic. | Phủ task Web từ unit eligible và mapping, không chỉ bỏ cờ incomplete. |
| `3891075360` | SOFTWARE_OTHER → SOFTWARE_WEB | SOFTWARE_CONTEXT nhận develop applications, không Web rule; manual evidence giao web applications/sites AEM. | Chốt Web task coverage/actor; câu Web and Mobile solutions chưa đủ nhiệm vụ Mobile riêng. |
| `3901389270` | SOFTWARE_WEB → SOFTWARE_OTHER | SOFTWARE_WEB_TITLE khớp Back End Developer; nhiệm vụ coding chatbot/write/evaluate code, chưa có task backend web. | Chốt chính sách subgroup title so với nhiệm vụ code evaluation, giữ membership SOFTWARE. |
| `3901935934` | SOFTWARE_WEB → SOFTWARE_OTHER | SOFTWARE_WEB_TITLE khớp Web Developer; body train chatbot/evaluate code, không sản phẩm Web cụ thể. | Đối soát role/task và scope subgroup title, không sửa nhãn cho khớp máy. |
| `3901938023` | SOFTWARE_WEB → SOFTWARE_OTHER | SOFTWARE_WEB_TITLE khớp Frontend Developer; code snippets/evaluation không xác nhận frontend application. | Chốt Web vs OTHER theo nhiệm vụ với đối chứng frontend thật. |
| `3901394183` | SOFTWARE_WEB → SOFTWARE_OTHER | SOFTWARE_WEB_TITLE khớp Web Developer; body viết/đánh giá code, chưa có task website. | Xác nhận chính sách code annotation và subgroup title theo nguồn riêng. |
| `3901394507` | SOFTWARE_WEB → SOFTWARE_OTHER | SOFTWARE_WEB_TITLE khớp Frontend Developer; code snippets/correctness/performance, chưa task Web. | Cùng chính sách cần chốt, giữ một bản ghi riêng theo job_id. |

## 7. Đối chiếu từng tiêu chí A04

Căn cứ [tiêu chí](a04_completion_criteria.md) và trích phân công đã lưu. Tình trạng cũ “chưa triển khai sửa” ở tài liệu 13/10 đã được bổ sung bằng bằng chứng round 1/2, nhưng chưa có xác nhận nghiệm thu toàn A04.

| Tiêu chí/ô phân công | Bằng chứng hiện có | Phần cần người rà soát xác nhận |
| --- | --- | --- |
| F21: Kiểm tra bộ lọc CNTT; phụ thuộc A02/A03 | Quy tắc theo JSON A02, nhiệm vụ/section/actor; không dùng ngành/skills metadata làm membership. Ba phiên bản, hash và trace truy được tại hồ sơ này/[bàn giao TV1](a04_handoff_tv1.md). | Phạm vi nghề và các giới hạn còn lại phù hợp mục tiêu kiểm tra bộ lọc. |
| G21: Mẫu thủ công 100–200 tin, có được chọn/bị loại | 160 tin chính với thiết kế 80 ACCEPT/50 REJECT/30 REVIEW v0.1.0; 17 bổ sung báo riêng; 176 khóa duy nhất. Workbook cuối và manifest ở mục 1–2. | Chấp nhận thiết kế mẫu phát triển có ca phủ nghề và 4 CHUA_RO giữ riêng; không cần ép nhãn để đủ số. |
| Nhãn/lý do/evidence/metadata phục vụ mẫu đánh giá | Đủ 177 dòng nguồn/176 khóa; metadata thiếu 0, ca chung khớp; nguồn hiện hành khớp snapshot round 2. | Xác nhận bộ nhãn đã duyệt là căn cứ mẫu và cách giữ CHUA_RO; duyệt nhãn không thay xác nhận nghiệm thu. |
| G21: Sửa false positive/negative | Không FP xác nhận; round 1 sửa 4 abstain, round 2 sửa 3 FN có task evidence, delta và hồi quy theo stage. Còn 5 FN, 33 REVIEW, 3 nhóm, 9 subgroup có hướng xử lý riêng. | Kết quả sửa đã thực hiện đáp ứng G21, cùng giới hạn chấp nhận/lượt xử lý riêng của phần còn lại. Không coi bảng đề xuất là đã sửa hết. |
| H21: Mẫu gán nhãn và kết quả đánh giá | Hai workbook, trace 160/17, ma trận, tỷ lệ/phân số, bảng delta, hồ sơ cuối và bàn giao. | Xác nhận đầu ra đủ, truy cập được và có thể bàn giao; các file data/analytics bị Git ignore cần được chuyển cùng manifest khi tích hợp. |
| I21: Có mẫu, tỷ lệ đúng trên mẫu và ví dụ lọc sai | Mục 2–5: đủ mẫu; báo khớp có điều kiện cùng độ phủ, REVIEW, FP/FN, nhóm/subgroup; ví dụ Workday/Scrum/Programmer và lỗi còn lại truy bằng job_id. | Cách tính/mẫu số và ví dụ đáp ứng tiêu chí; không gọi khớp khi máy quyết định là accuracy toàn dataset. |
| I21: Không chỉ tìm chuỗi IT | Title phrase + task/object/context SAME_SEGMENT, heading/actor/blockers, conflict/priority; controls product-only, qualification, company, CNC/PLC, Scrum chung. | Chấp nhận bằng chứng nghề/ngữ cảnh và ranh giới ngoài CNTT; không bật metadata hoặc dùng IT token đơn lẻ. |
| Tong quan!D8: Người rà soát xác nhận trước khi nhập 100% | Hồ sơ đủ để đề nghị **“Sẵn sàng rà soát nghiệm thu”**; chưa có xác nhận nghiệm thu toàn A04. | Người rà soát xác nhận đầu ra/tiêu chí và quyết định nghiệm thu sau đối soát; hồ sơ này không tự ghi tiến độ, tên hoặc ngày nghiệm thu. |

Không có tiêu chí mặc định FN=0/REVIEW=0; việc chấp nhận lỗi/abstain còn lại cần được xác nhận rõ. Đánh giá độc lập cần khi tuyên bố chất lượng độc lập/toàn tập sau đóng băng quy tắc: seed khác, loại các job từng dùng phát triển/chẩn đoán, nhãn trước xem máy và thiết kế xác suất/trọng số phù hợp. **Hiện đây là mẫu phát triển đã dùng sửa quy tắc; chưa đánh giá độc lập toàn dataset.**

Parity Spark/JVM, canonical/schema và tích hợp D06 là phần TV1 kiểm tra theo [hồ sơ bàn giao](a04_handoff_tv1.md), không tự biến D06/A05 hay mốc nghiệm thu chung M3 thành điều kiện phải hoàn tất trước nghiệm thu riêng A04.

## 8. Kiểm tra hồ sơ trong lượt tổng hợp

Đã đọc hai workbook hiện hành, so toàn bộ hàng với snapshot round 2; JOIN theo job_id và tính lại số đếm/phân số của cả ba phiên bản bằng các prediction đã lưu. Ca chung được kiểm tra nhãn/prediction nhất quán; hàng đợi được phân loại lại theo candidate và kiểm tra không trùng khóa giữa bốn loại. Đã kiểm tra hash config/code/test/output với run manifest và các liên kết local trong hai tài liệu mới.

Không sửa code và không phát hiện vấn đề mới cần chạy hồi quy, nên dùng bằng chứng test đã qua. Các file có sẵn được đối chiếu hash/kích thước/mtime trước và sau lượt tổng hợp; chỉ thêm hồ sơ cuối và hồ sơ bàn giao, giữ nguyên tài liệu/CSV lịch sử và các hiện vật nguồn.
