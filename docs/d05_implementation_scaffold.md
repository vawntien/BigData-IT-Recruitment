# D05 Implementation Scaffold & Reusable Utilities

## 1. Trạng thái thực thi

> [!IMPORTANT]
> **D05 OFFICIAL NOT EXECUTED**  
> Tài liệu này mô tả hạ tầng kỹ thuật (scaffold) và các tiện ích dùng lại (reusable Spark utilities) chuẩn bị cho D05. Không có tệp dữ liệu canonical production nào (như `canonical_jobs.parquet`) được tạo ra, không ghi vào `data/processed/`, và không thực hiện D05 chính thức vì vẫn đang chờ task **A03** từ Thành viên 2.

---

## 2. Vì sao bắt buộc phải Aggregate-Before-Join?

Trong D05 Pre-check, phân tích cardinality trên dữ liệu sạch đã chứng minh nguy cơ bùng nổ dữ liệu (**Row Explosion**) nghiêm trọng nếu thực hiện JOIN trực tiếp (flat join):

- `job_skills` chứa tới 71,658 tin có từ 2 đến 3 skills.
- `job_industries` chứa tới 24,406 tin có từ 2 đến 3 industries.
- `benefits` chứa tới 16,101 tin có từ 2 đến 12 quyền lợi.
- `company_specialities` có tới 16,970 công ty có nhiều chuyên môn (tối đa 84 chuyên môn).
- `employee_counts` có 5,694 công ty có nhiều bản ghi snapshot theo thời gian (tối đa 13 snapshots).

### Minh chứng thực nghiệm từ Test F:
Chỉ riêng phép JOIN phẳng giữa `postings` (123,849 dòng) và `job_skills` đã làm số dòng tăng vọt lên **207,531 dòng** (+83,682 dòng trùng lặp tin tuyển dụng). Nếu kết hợp thêm `benefits` và `specialities`, một tin đơn lẻ có thể bị nhân bản lên tới 18,144 lần.

**Giải pháp:** Mọi quan hệ nhiều-nhiều bắt buộc phải được gom nhóm thành mảng xác định (`aggregate_bridge` với `collect_set` và `array_sort`) hoặc lọc snapshot mới nhất (`latest_per_key`) trước khi thực hiện LEFT JOIN vào bảng thực thể chính.

---

## 3. Các tiện ích đã xây dựng (`src/d05_utils.py`)

1. **`get_spark_session(app_name, project_root)`**:
   Khởi tạo `SparkSession` đồng nhất với cấu hình UTC session timezone và tích hợp bộ adapter phân quyền file cục bộ trên Windows (`d04-localfs-adapter.jar`).

2. **`aggregate_bridge(df, entity_key, value_column, output_column, sort_array=True)`**:
   - Gom nhóm bảng quan hệ nhiều-nhiều về đúng grain 1 dòng / entity key.
   - Tự động loại bỏ giá trị NULL khỏi tập hợp.
   - Loại bỏ giá trị trùng lặp bằng `collect_set`.
   - Sắp xếp mảng (`array_sort`) để đảm bảo kết quả hoàn toàn tất định (deterministic).
   - Không áp đặt hay hardcode ngữ nghĩa nghiệp vụ.

3. **`latest_per_key(df, partition_cols, timestamp_col, tie_break_columns=None)`**:
   - Trích xuất duy nhất 1 snapshot mới nhất cho mỗi entity key bằng `Window.partitionBy().orderBy(timestamp.desc())`.
   - Sử dụng các cột phụ để giải quyết trường hợp hòa điểm (tie-breaking) một cách tất định.
   - Tuyệt đối không dùng `dropDuplicates` ngẫu nhiên.

4. **`assert_unique_key(df, key_cols, label="")`**:
   Kiểm tra nghiêm ngặt tính duy nhất và không chứa NULL của khóa trên DataFrame. Phát hiện lập tức mọi vi phạm về khóa.

5. **`profile_join(left, right, join_keys, join_type="left")`**:
   Đo lường số dòng trước và sau JOIN, phát hiện sự thay đổi grain hoặc số lượng dòng tăng đột biến.

6. **`check_grain_preserved(before_count, after_count, before_distinct_key, after_distinct_key, key_name="key")`**:
   Hàm bảo vệ (guard) xác nhận số lượng dòng và số lượng khóa duy nhất được bảo toàn trọn vẹn 100%.

---

## 4. Kết quả kiểm thử thực nghiệm (`src/test_d05_scaffold.py`)

Bộ test độc lập sử dụng pure Python assertions đã thực thi và **PASS 100%**:

| Kiểm thử | Thao tác | Đầu vào | Đầu ra kỳ vọng | Kết quả thực tế | Trạng thái |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Test A** | Gom nhóm bridge tables | 5 bảng quan hệ | 1 dòng / entity, khóa duy nhất | `agg_skills` (126,807 dòng)<br>`agg_industries` (127,125 dòng)<br>`agg_benefits` (30,023 dòng)<br>`agg_comp_ind` (24,365 dòng)<br>`agg_comp_spec` (17,780 dòng) | **PASS** |
| **Test B** | Trích snapshot mới nhất | 35,665 dòng employee_counts | 24,473 công ty duy nhất | 24,473 dòng, khóa `company_id` duy nhất | **PASS** |
| **Test C** | Safe LEFT JOIN với Postings | 123,849 postings | 123,849 dòng, 123,849 distinct job_id | 123,849 dòng, 123,849 distinct job_id | **PASS** |
| **Test D** | Safe LEFT JOIN với Companies | 24,473 companies | 24,473 dòng, 24,473 distinct company_id | 24,473 dòng, 24,473 distinct company_id | **PASS** |
| **Test E** | Safe LEFT JOIN với Salaries | 123,849 postings + 40,785 salaries | 123,849 dòng, 123,849 distinct job_id | 123,849 dòng, 123,849 distinct job_id | **PASS** |
| **Test F** | Bắt lỗi Flat JOIN không an toàn | Postings + raw job_skills | Phát hiện row explosion | Phát hiện +83,682 dòng dư thừa (tổng 207,531 dòng) | **PASS** |
| **Test G** | Kiểm tra tính nguyên vẹn | Dữ liệu `data/processed/` | 0 file mới được ghi | 0 file ghi vào processed | **PASS** |

---

## 5. Những vấn đề đang chờ Task A03 và Giới hạn quyết định

### A. Những gì đang chờ A03:
1. **Bản đồ JOIN chính thức:** Xác định cách thức kết nối các bảng `skills`, `industries` và phạm vi trường thông tin cần lưu giữ.
2. **Quy tắc giải nghĩa nhãn kỹ năng:** Xác nhận cách sử dụng 35 nhãn trong `skills.csv` (được xác định là *job function codes* chứ không phải technical skills cụ thể).
3. **Chiến lược nguồn kỹ năng:** Thống nhất phương án trích xuất kỹ năng kỹ thuật (Python, SQL, Java...) từ trường văn bản `description` (thuộc A03/A05).

### B. Những gì KHÔNG ĐƯỢC quyết định trước A03:
- **KHÔNG** đổi tên cột `job_skills` thành `technical_skills`. Ở scaffold hiện tại sử dụng tên trung lập là `job_function_codes`.
- **KHÔNG** trích xuất từ khóa lập trình giả định.
- **KHÔNG** thực hiện bất kỳ bộ lọc tin CNTT nào (thuộc D06/A04).
- **KHÔNG** can thiệp vào ngữ nghĩa lương, quy đổi ngoại tệ hay chuẩn hóa kỳ hạn trả lương (thuộc D07).
