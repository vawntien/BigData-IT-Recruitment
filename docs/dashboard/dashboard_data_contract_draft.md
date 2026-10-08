# Draft Data Contract: Dashboard Analytics Outputs

> [!WARNING]
> **TÀI LIỆU NÀY LÀ BẢN THẢO (DRAFT CONTRACT), KHÔNG PHẢI HỢP ĐỒNG CUỐI CÙNG (V03 FINAL).**  
> Bản thảo này dùng để định hình cấu trúc dữ liệu đầu ra mà tầng Big Data Spark (`data/analytics/`) sẽ cung cấp cho giao diện Streamlit Dashboard của Thành viên 3 (TV3).  
> **Trạng thái:** DRAFT — Tùy thuộc vào kết quả của các nhiệm vụ A03, D05, D06, và A05–A08.

---

## 1. Nguyên tắc Giao tiếp Dữ liệu giữa Spark và UI

1. **Tách biệt tầng tính toán và tầng hiển thị:** Streamlit **KHÔNG** đọc trực tiếp các tệp Parquet sạch hàng trăm nghìn dòng từ `data/processed/clean/` để tính toán aggregate tại runtime. Toàn bộ phép tính toán nặng (group by, count distinct, quantile) được Spark thực hiện và lưu sẵn thành các bảng tổng hợp tại `data/analytics/`.
2. **Định dạng trao đổi:** Các bảng tổng hợp được lưu dưới dạng Parquet (hoặc CSV song song) trong `data/analytics/`.
3. **Minh bạch cỡ mẫu (Sample Size Transparency):** Mọi bảng tổng hợp bắt buộc phải có cột thể hiện cỡ mẫu (`sample_size` hoặc `job_count`) để UI luôn hiển thị số lượng tin tương ứng làm mẫu số thống kê.

---

## 2. Bảng 1: `overview_analytics` (Dự kiến cho Trang 1_Overview)

- **Mục đích:** Cung cấp số liệu phân bố cơ cấu tin tuyển dụng CNTT theo nhóm nghề, kinh nghiệm, địa điểm và hình thức làm việc.
- **Grain:** 1 dòng / kết hợp giữa `(category, experience_level, location, work_type)`.
- **Cấu trúc trường dự kiến:**

| Tên trường | Kiểu dữ liệu | Mô tả | Ràng buộc |
| :--- | :--- | :--- | :--- |
| `category` | `string` | Tên nhóm nghề CNTT chuẩn hóa (ví dụ: `Software Engineering`, `Data & AI`) | Không NULL (từ taxonomy TV2) |
| `experience_level` | `string` | Cấp bậc kinh nghiệm (`Entry level`, `Mid-Senior level`, `Associate`, `Unknown`) | Đã chuẩn hóa NULL $\rightarrow$ `Unknown` |
| `location` | `string` | Địa điểm làm việc chuẩn hóa | Chuỗi ký tự |
| `work_type` | `string` | Hình thức làm việc (`Full-time`, `Contract`, `Part-time`, `Remote`) | Kết hợp work_type & remote |
| `job_count` | `long` | Số lượng tin tuyển dụng duy nhất | $\ge 1$ |
| `sample_size` | `long` | Tổng số tin tuyển dụng làm mẫu số | Cỡ mẫu toàn nhóm |

---

## 3. Bảng 2: `skills_analytics` (Dự kiến cho Trang 2_Skills)

- **Mục đích:** Cung cấp tần suất và độ phổ biến của các kỹ năng kỹ thuật theo từng nhóm nghề.
- **Grain:** 1 dòng / kết hợp giữa `(category, technical_skill)`.
- **Cấu trúc trường dự kiến:**

| Tên trường | Kiểu dữ liệu | Mô tả | Ràng buộc |
| :--- | :--- | :--- | :--- |
| `category` | `string` | Tên nhóm nghề CNTT | Khớp với taxonomy của TV2 |
| `technical_skill` | `string` | Tên kỹ năng kỹ thuật chuẩn hóa (ví dụ: `Python`, `SQL`, `AWS`, `Docker`) | Trích xuất từ `description` (A05) |
| `job_count` | `long` | Số tin tuyển dụng yêu cầu kỹ năng này | Mỗi tin chỉ tính tối đa 1 lần |
| `sample_size` | `long` | Tổng số tin tuyển dụng trong nhóm nghề tương ứng | Dùng làm mẫu số tính tỷ lệ |
| `frequency_pct` | `double` | Tỷ lệ phần trăm tin tuyển dụng yêu cầu kỹ năng | $\frac{\text{job\_count}}{\text{sample\_size}} \times 100$ |
| `source_method` | `string` | Phương pháp trích xuất (`DESCRIPTION_REGEX` / `TITLE_MATCH`) | Minh bạch phương pháp |

---

## 4. Bảng 3: `salary_quality_analytics` (Dự kiến cho Trang 3_Salary_Quality)

- **Mục đích:** Cung cấp các chỉ số phân vị lương theo phân nhóm tương thích và hồ sơ chất lượng dữ liệu.
- **Grain:** 1 dòng / kết hợp giữa `(category, currency, pay_period)`.
- **Cấu trúc trường dự kiến:**

| Tên trường | Kiểu dữ liệu | Mô tả | Ràng buộc |
| :--- | :--- | :--- | :--- |
| `category` | `string` | Tên nhóm nghề CNTT | Khớp với taxonomy của TV2 |
| `currency` | `string` | Đơn vị tiền tệ (ví dụ: `USD`) | Không gộp các tiền tệ khác nhau |
| `pay_period` | `string` | Kỳ trả lương (`YEARLY`, `HOURLY`) | Không gộp năm với giờ |
| `job_count_with_salary` | `long` | Số lượng tin có dữ liệu lương hợp lệ | Cỡ mẫu có lương |
| `total_job_count` | `long` | Tổng số tin trong phân nhóm | Mẫu số |
| `coverage_pct` | `double` | Tỷ lệ độ phủ thông tin lương trong phân nhóm | $\frac{\text{job\_count\_with\_salary}}{\text{total\_job\_count}} \times 100$ |
| `median_salary` | `decimal` | Mức lương trung vị (Median / P50) | Tính trên Spark SQL |
| `min_salary` | `decimal` | Mức lương tối thiểu quan sát được | Loại bỏ outlier |
| `max_salary` | `decimal` | Mức lương tối đa quan sát được | Loại bỏ outlier |

---

## 5. Quy trình Chốt Hợp đồng Dữ liệu Chính thức (V03 Protocol)

Khi các task A03, D05, D06, và A05–A08 hoàn tất:
1. TV1 và TV2 xác nhận danh sách cột và kiểu dữ liệu thực tế xuất ra từ Spark.
2. TV3 xác nhận các component Streamlit có thể tiêu thụ trực tiếp schema mà không cần chuyển đổi phức tạp.
3. Cả 3 thành viên thống nhất ký duyệt và nâng cấp tài liệu này thành `docs/dashboard/data_contract_v03.md`.
