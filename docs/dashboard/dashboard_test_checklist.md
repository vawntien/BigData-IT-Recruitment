# Dashboard Test & Integration Checklist

Checklist này phục vụ quy trình kiểm thử và tích hợp giao diện người dùng cho **Thành viên 3 (TV3)**, làm cơ sở nghiệm thu cho nhiệm vụ **V07 (Dashboard integration & testing)**.

Các tiêu chí được phân loại thành 3 mức độ sẵn sàng:
- 🟢 **READY NOW**: Có thể kiểm thử và xác nhận ngay trên môi trường scaffold hiện tại (dùng dữ liệu mẫu).
- 🟡 **WAITING FOR ANALYTICS**: Cần các bảng tổng hợp chính thức từ pipeline Spark (A06–A08 / D07) trước khi kiểm thử.
- 🔵 **FINAL ACCEPTANCE**: Kiểm thử nghiệm thu cuối cùng trước khi đóng gói demo (V09/V11).

---

## A. Khởi động Ứng dụng (Startup)

| ID | Hạng mục kiểm thử | Tiêu chí đạt | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :---: | :---: |
| A.1 | Chạy qua lệnh PowerShell | `streamlit run dashboard\app.py` khởi động không ném lỗi | 🟢 READY NOW | **PASS** |
| A.2 | Thiếu dữ liệu Production | Ứng dụng hiển thị thông báo thân thiện, không crash trang | 🟢 READY NOW | **PASS** |
| A.3 | Bật Sample Mode | Tự động tải dữ liệu mẫu, các trang render đủ component | 🟢 READY NOW | **PASS** |

---

## B. Nguồn dữ liệu & Cảnh báo (Data Source & Indicators)

| ID | Hạng mục kiểm thử | Tiêu chí đạt | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :---: | :---: |
| B.1 | Hiển thị Sample Banner | Banner vàng cảnh báo "DEVELOPMENT SAMPLE MODE" xuất hiện nổi bật | 🟢 READY NOW | **PASS** |
| B.2 | Hiển thị Production Banner | Khi có dữ liệu trong `data/analytics/`, banner xanh "PRODUCTION DATA" xuất hiện | 🟡 WAITING | Chờ analytics |
| B.3 | Cảnh báo nhãn kỹ năng | Trang 2_Skills có cảnh báo rõ ràng rằng nhãn gốc không phải technical skills | 🟢 READY NOW | **PASS** |
| B.4 | Không giả mạo số liệu | Dữ liệu mẫu không bị trình bày như số liệu kết luận thực tế | 🟢 READY NOW | **PASS** |

---

## C. Bộ lọc Dữ liệu (Filters & Interactivity)

| ID | Hạng mục kiểm thử | Tiêu chí đạt | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :---: | :---: |
| C.1 | Lọc Nhóm nghề (Category) | Chọn/bỏ chọn nhóm nghề làm cập nhật tương ứng biểu đồ | 🟢 READY NOW | **PASS** |
| C.2 | Lọc Cấp bậc (Experience) | Thay đổi cấp bậc kinh nghiệm cập nhật đúng số lượng | 🟢 READY NOW | **PASS** |
| C.3 | Lọc Địa điểm (Location) | Lọc địa điểm hoạt động ổn định | 🟢 READY NOW | **PASS** |
| C.4 | Tổ hợp không có kết quả | Khi chọn tổ hợp bộ lọc không có dòng nào, UI hiển thị cảnh báo, không crash | 🟢 READY NOW | **PASS** |

---

## D. Trang Tổng quan (Overview Page)

| ID | Hạng mục kiểm thử | Tiêu chí đạt | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :---: | :---: |
| D.1 | Đồng bộ số liệu KPI | Tổng số tin tuyển dụng (Total Jobs) khớp với tổng trên bảng | 🟢 READY NOW | **PASS** |
| D.2 | Cập nhật Biểu đồ | 4 biểu đồ phản ứng mượt mà khi bộ lọc thay đổi | 🟢 READY NOW | **PASS** |
| D.3 | Xử lý dữ liệu rỗng (0 rows) | Trang dừng hiển thị an toàn với thông báo phù hợp | 🟢 READY NOW | **PASS** |
| D.4 | Kết nối dữ liệu thật A06 | Đọc thành công `overview_analytics.parquet` từ pipeline | 🟡 WAITING | Chờ A06 |

---

## E. Trang Kỹ năng (Skills Page)

| ID | Hạng mục kiểm thử | Tiêu chí đạt | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :---: | :---: |
| E.1 | Bảng xếp hạng Top Skills | Biểu đồ cột ngang hiển thị danh sách kỹ năng giảm dần | 🟢 READY NOW | **PASS** |
| E.2 | Minh bạch phương pháp | Hiển thị cột `source_method` và `sample_size` trong bảng | 🟢 READY NOW | **PASS** |
| E.3 | Phân tách Kỹ năng theo Nghề | Bảng ma trận pivot phân bố kỹ năng theo ngành hoạt động đúng | 🟢 READY NOW | **PASS** |
| E.4 | Kết nối dữ liệu thật A07 | Hiển thị kỹ năng trích xuất từ `description` thật của pipeline | 🟡 WAITING | Chờ A05/A07 |

---

## F. Trang Mức lương (Salary Page)

| ID | Hạng mục kiểm thử | Tiêu chí đạt | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :--- | :---: |
| F.1 | Phân lập Tiền tệ & Kỳ lương | Chỉ so sánh nhóm cùng currency (`USD`) và kỳ hạn (`YEARLY`) | 🟢 READY NOW | **PASS** |
| F.2 | Phân biệt thiếu và 0 | Giá trị thiếu không bị coi là mức lương 0 đồng | 🟢 READY NOW | **PASS** |
| F.3 | Hiển thị Cỡ mẫu lương | Hiển thị rõ số lượng tin có lương (`job_count_with_salary`) | 🟢 READY NOW | **PASS** |
| F.4 | Kết nối dữ liệu thật D07/A08 | Đọc thành công `salary_quality_analytics.parquet` | 🟡 WAITING | Chờ D07/A08 |

---

## G. Trang Chất lượng Dữ liệu (Quality Page)

| ID | Hạng mục kiểm thử | Tiêu chí đạt | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :---: | :---: |
| G.1 | 4 Thẻ chỉ số Audit thực tế | 123,849 tin thô, 29.13% độ phủ, 142 rejected, 83 sửa Mojibake | 🟢 READY NOW | **PASS** |
| G.2 | Bảng Missingness Profile | Hiển thị bảng tổng hợp 16 cột khuyết thiếu cao nhất từ D03 | 🟢 READY NOW | **PASS** |
| G.3 | Bảng Referential Coverage | Hiển thị thống kê các bản ghi mồ côi (orphans) từ D05 Precheck | 🟢 READY NOW | **PASS** |

---

## H. Tính bền vững Tệp & Lỗi Ngoại lệ (Files & Exceptions)

| ID | Hạng mục kiểm thử | Tiêu chí đạt | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :---: | :---: |
| H.1 | Tệp Analytics trống (0 bytes) | Contract validator phát hiện và báo lỗi schema, không crash | 🟢 READY NOW | **PASS** |
| H.2 | Tệp Analytics thiếu cột | Contract validator liệt kê chính xác các cột bị thiếu | 🟢 READY NOW | **PASS** |
| H.3 | Không đọc `data/raw/` | Không có lời gọi đọc trực tiếp thư mục `data/raw/` từ UI | 🟢 READY NOW | **PASS** |

---

## I. Kiểm thử Hồi quy & Nghiệm thu (Regression & Final Acceptance)

| ID | Hạng mục kiểm thử | Tiêu chí đạt | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :---: | :---: |
| I.1 | Tải lại trang (F5 Reload) | Trạng thái UI được bảo toàn, không lỗi session state | 🟢 READY NOW | **PASS** |
| I.2 | Chuyển đổi dữ liệu nóng | Chuyển từ Sample sang Production không cần khởi động lại app | 🔵 FINAL | Chờ V07 |
| I.3 | Demo kịch bản 3–5 phút | Chạy thông suốt toàn bộ kịch bản thuyết trình trên dữ liệu thật | 🔵 FINAL | Chờ V09 |
