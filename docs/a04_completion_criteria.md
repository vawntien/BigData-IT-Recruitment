# A04 – Đối chiếu tiêu chí hoàn thành sau áp dụng 93 tin

Ngày **13/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`. **Chưa tự đánh dấu A04 hoàn thành hoặc 100%.**

## Căn cứ phân công

Nguồn đã đọc ở lượt đối chiếu trước: [Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsm](C:/Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsm), SHA-256 `9343cc8b5c17beb343ec98fa57bb00bff6cb4609aa12cbffb0100ef461c3df26`. Trích địa chỉ ô/nội dung tại [assignment_context.json](../data/analytics/a04_remaining93_review_20261013/assignment_context.json); bản tài liệu tiêu chí trước cập nhật được lưu trong [reports_before](../data/analytics/a04_apply_remaining93_20261013/reports_before/a04_completion_criteria.md). Lượt này không sửa file phân công hay chạy macro.

Sheet `Cong viec`, dòng 21, A04, chủ trì TV2, bắt buộc, phụ thuộc A02/A03:

| Ô | Nội dung phân công |
| --- | --- |
| F21 | Kiểm tra bộ lọc CNTT |
| G21 | Gán nhãn thủ công mẫu 100–200 tin gồm được chọn và bị loại. Sửa false positive/negative. |
| H21 | Mẫu gán nhãn và kết quả đánh giá |
| I21 | Có mẫu, tỷ lệ đúng trên mẫu và ví dụ lọc sai. Không chỉ tìm chuỗi IT. |

`Tong quan!D8` yêu cầu chỉ nhập 100% sau khi người rà soát xác nhận đầu ra và tiêu chí đạt.

## Đầu ra hiện có và việc còn thiếu

| Yêu cầu | Hiện trạng kiểm tra từ nguồn cuối | Việc còn thiếu để nghiệm thu |
| --- | --- | --- |
| Mẫu 100–200 tin gồm được chọn/bị loại | Mẫu chính 160 job_id, gồm ACCEPT/REJECT/REVIEW theo thiết kế seed42 đóng băng; 17 ca bổ sung báo riêng | Không thiếu số lượng mẫu; không cần lấy lại mẫu chỉ để đủ số |
| Nhãn thủ công theo nghề, lý do/evidence/metadata | Đã áp dụng 93 bảng chốt; giữ 83 quyết định trước. Đủ 160+17 dòng, 176 job_id duy nhất; metadata thiếu 0, ca chung không xung đột. Reviewer Dũng, ngày 2026-10-13 | Không còn 93 ca chờ duyệt/thiếu metadata. 4 CHUA_RO đã duyệt giữ riêng, thông tin thiếu ghi rõ |
| Tỷ lệ đúng trên mẫu và kết quả đánh giá | Đã tính lại v0.2.0: mẫu 160 khớp khi máy quyết định 127/132 = 96.21%, độ phủ nhãn rõ 132/156 = 84.62%, quyết định đúng trên nhãn rõ 127/156 = 81.41%. Mẫu 17: khớp 0/3 = 0.00%, độ phủ 3/17 = 17.65%. Có ma trận 3 trạng thái và mẫu số tại [báo cáo](a04_validation_report.md) | Người rà soát xác nhận cách tính/phạm vi này đáp ứng tiêu chí mẫu. Các tỷ lệ mô tả mẫu phát triển, không suy accuracy toàn dataset |
| Ví dụ lọc sai, đối soát và sửa FP/FN theo G21 | Mẫu chính FP=0, FN=5; bổ sung FP=0, FN=3. Có ví dụ PACS, Workday, Oracle exclusion và đầy đủ 8 FN; [bảng bất đồng](a04_prediction_disagreements.csv) có 61 khóa, nguyên nhân/đề xuất trong báo cáo | Cần đối soát/chốt nguyên nhân và phương án xử lý FN, sai nhóm/phân nhóm, REVIEW. Chưa triển khai hoặc xác minh sửa classifier trong lượt này; bước sửa FP/FN của G21 chưa được chứng minh hoàn tất |
| Xác nhận đầu ra/tiêu chí bởi người rà soát | Việc duyệt nhãn 93 ca đã được cho phép; chưa có xác nhận nghiệm thu toàn A04 hoặc cập nhật tiến độ | Người rà soát xác nhận đầu ra, kết quả mẫu và cách xử lý lỗi; sau đó mới quyết định nghiệm thu/100% |

CHUA_RO là trạng thái hướng dẫn A04 cho phép: **không phải ép 4 ca đã duyệt thành nhãn nhị phân để đủ 160**. Nhãn này được báo riêng, boolean/nhóm/phân nhóm trống; membership dùng mẫu số nhãn rõ. A04-063 giữ CNTT/DATA_AI theo bảng chốt và yêu cầu hiện hành, không cộng thành CHUA_RO thứ năm; A04-124 chuyển IT_MANAGEMENT.

## Quy ước kết quả mẫu

- JOIN bằng job_id với v0.2.0 đã lưu; tính lại từ nhãn workbook cuối, không sao chép tỷ lệ trong XLSX. Hai mẫu 160/17 có cơ chế chọn khác nhau, không gộp 177 dòng nguồn thành 177 tin độc lập.
- Khớp có điều kiện = `(ACCEPT/CNTT + REJECT/NGOAI_CNTT) / số ca nhãn rõ và máy ACCEPT/REJECT`. Báo đồng thời độ phủ trên nhãn rõ/toàn mẫu và tỷ lệ quyết định đúng trên toàn mẫu nhãn rõ.
- REVIEW giữ is_it=NULL, không ánh xạ thành NGOAI_CNTT/REJECT hoặc FN. CHUA_RO loại khỏi mẫu số membership nhãn rõ; vẫn hiện trong ma trận. Mẫu chính: CHUA_RO 4/160, REVIEW 24/160; bổ sung: CHUA_RO 0/17, REVIEW 14/17.
- Khớp nhóm chính chỉ trên máy ACCEPT/người đọc CNTT; khớp phân nhóm chỉ khi cả hai nhóm chính SOFTWARE. Không cộng khác nhóm thành khác phân nhóm lần nữa. Không bịa FP khi không có ACCEPT/NGOAI_CNTT xác nhận.
- Mẫu seed42 đã dùng phát triển/rà soát, có chọn ca phủ nghề và hỗ trợ đọc; tỷ lệ không là đánh giá độc lập hoặc ước lượng chất lượng toàn tập.

## Phạm vi đánh giá độc lập và D06

Mẫu độc lập seed khác, loại job từng dùng phát triển, cần khi tuyên bố chất lượng độc lập sau đóng băng/sửa rule hoặc ước lượng toàn dataset; không được ghi là đầu ra bắt buộc riêng tại G21–I21. Nếu triển khai sửa rule/alias/priority, phải version/hash/changelog và kiểm tra sau sửa theo A02 mục 7 bước 8. Việc chưa có đánh giá độc lập không thay thế yêu cầu báo tỷ lệ trên mẫu phát triển, và cũng không phải lý do duy nhất giữ A04 chưa nghiệm thu.

Parity Python–Spark/JVM, schema/canonical và mapping evidence phục vụ tích hợp D06 do TV1 chủ trì (`Cong viec!11`), phụ thuộc D05/A02/A04. Dataset CNTT Parquet và mốc M3 (`Moc va nghiem thu!8`) là nghiệm thu chung D05/D06/A04/A05/V04; không đảo thành điều kiện D06/A05 phải hoàn tất trước nghiệm thu riêng A04.

Hiện phần nhãn/metadata, tỷ lệ mẫu và ví dụ lỗi đã có. **Còn chốt đối soát/xử lý lỗi, triển khai/xác minh sửa được phép và xác nhận nghiệm thu của người rà soát.** Không sửa raw/title/description/job_id/taxonomy/classifier, không chạy ETL, không làm A05, không commit/push trong lượt này.
