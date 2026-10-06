# Data and Methodology Draft (Bản thảo Chương Dữ liệu và Phương pháp)

> [!NOTE]
> **TÀI LIỆU NÀY LÀ BẢN THẢO (DRAFT) CHUẨN BỊ CHO D10.**  
> Trạng thái hiện tại: **D10 OFFICIAL NOT EXECUTED**. Tài liệu này chỉ tổng hợp các phương pháp và bằng chứng thực nghiệm đã hoàn thành từ D01 đến D04 và tiền kiểm D05, các phần tiếp theo được đánh dấu bằng các mục `[TODO]` rõ ràng.

---

## 1. Dataset Source and Scope (Nguồn và Phạm vi Dữ liệu)

- **Nguồn dữ liệu:** Bộ dữ liệu *LinkedIn Job Postings (2023–2024)* được thu thập và xuất bản bởi Arsh Koneru trên Kaggle dưới giấy phép mở CC BY-SA 4.0.
- **Ngày tiếp nhận:** 04/10/2026.
- **Quy mô tổng thể:** 11 tệp CSV với tổng dung lượng xấp xỉ 530.72 MB.
- **Phạm vi và giới hạn:** Bộ dữ liệu phản ánh các tin tuyển dụng được thu thập trên nền tảng LinkedIn trong khoảng thời gian từ cuối năm 2023 đến đầu năm 2024 (chủ yếu là thị trường Hoa Kỳ và toàn cầu). Kết quả phân tích không được suy rộng thành toàn bộ thị trường lao động Việt Nam hoặc bất kỳ thị trường quốc gia cụ thể nào ngoài phạm vi thu thập.

---

## 2. Dataset Structure (Cấu trúc Bộ dữ liệu)

11 tệp CSV gốc được chia thành 4 nhóm logic:

1. **Bảng trung tâm tin tuyển dụng (Core Postings):**
   - `postings.csv` (123,849 dòng, 31 cột): Chứa thông tin chính về tiêu đề công việc, mô tả chi tiết, địa điểm, công ty, hình thức làm việc, dải lương cơ bản và mốc thời gian đăng tuyển.
2. **Nhóm dữ liệu doanh nghiệp (Company Profiles):**
   - `companies/companies.csv` (24,473 dòng, 10 cột): Thông tin tổng quan về doanh nghiệp (tên, quy mô, trụ sở, mô tả).
   - `companies/company_industries.csv` (24,375 dòng, 2 cột): Ngành nghề hoạt động của doanh nghiệp.
   - `companies/company_specialities.csv` (169,387 dòng, 2 cột): Lĩnh vực chuyên môn chi tiết của doanh nghiệp.
   - `companies/employee_counts.csv` (35,787 dòng, 4 cột): Số lượng nhân sự và người theo dõi của công ty theo các mốc thời gian.
3. **Nhóm dữ liệu chi tiết công việc (Job Attributes):**
   - `jobs/benefits.csv` (67,943 dòng, 3 cột): Các chế độ đãi ngộ (bảo hiểm, thưởng, nghỉ phép).
   - `jobs/job_industries.csv` (164,808 dòng, 2 cột): Ngành nghề liên quan đến vị trí công việc.
   - `jobs/job_skills.csv` (213,768 dòng, 2 cột): Nhóm chức năng nghề nghiệp của vị trí công việc.
   - `jobs/salaries.csv` (40,785 dòng, 8 cột): Chi tiết dải lương cấu trúc, kỳ trả lương và loại hình thù lao.
4. **Nhóm bảng tra cứu chuẩn hóa (Mapping Dictionaries):**
   - `mappings/industries.csv` (422 dòng, 2 cột): Bảng ánh xạ mã ngành sang tên ngành chuẩn hóa của LinkedIn.
   - `mappings/skills.csv` (35 dòng, 2 cột): Bảng ánh xạ mã viết tắt của 35 nhóm chức năng nghề nghiệp.

---

## 3. Big Data Processing Environment (Môi trường Xử lý Dữ liệu)

Pipeline xử lý dữ liệu được thiết kế hoàn toàn trên nền tảng Big Data Apache Spark để đảm bảo tính mở rộng và khả năng xử lý phân tán:
- **Ngôn ngữ lập trình:** Python 3.11 (PySpark).
- **Môi trường máy ảo Java:** OpenJDK 21 LTS (Eclipse Temurin).
- **Phiên bản tính toán:** Apache Spark / PySpark 4.2.0.
- **Chế độ thực thi:** Spark `local[*]` (tận dụng tối đa các luồng CPU của máy phát triển).
- **Quy chuẩn thời gian:** Session Timezone được ấn định cố định là `UTC` cho toàn bộ các phép toán thời gian.
- **Hệ thống tệp Windows:** Tích hợp bộ Java FileSystem adapter tùy biến (`d04-localfs-adapter.jar`) để loại bỏ hoàn toàn sự phụ thuộc vào tiện ích ngoài `winutils.exe` hoặc cấu hình native Hadoop trên Windows.

---

## 4. Data Audit Method (Phương pháp Kiểm kê và Đánh giá Chất lượng)

Tại pha D03 (`src/audit_data.py`), dữ liệu thô được kiểm kê với nguyên tắc **bất biến (immutable raw data)**:
1. **Đọc dữ liệu thô an toàn:** Đọc toàn bộ 11 tệp với `inferSchema=false` (toàn bộ cột ban đầu là kiểu chuỗi) để tránh suy diễn sai định dạng, xử lý đúng trường nhiều dòng (`multiLine=true`) và ký tự bao chuỗi (`"..."`).
2. **Kiểm kê giá trị thiếu (Missingness Profiling):** Nhận diện không chỉ Spark NULL mà cả chuỗi rỗng và các giá trị sentinel (`null`, `NULL`, `N/A`, `NA`) sau khi trim khoảng trắng.
3. **Kiểm tra tính duy nhất của khóa (Candidate Key Profiling):** Kiểm định khóa chính đơn và khóa tổng hợp (composite keys) trên từng bảng.
4. **Kiểm tra trùng lặp toàn dòng (Duplicate Row Analysis):** Sử dụng hàm băm SHA-256 trên chuỗi JSON tuần tự hóa để đo lường trùng lặp toàn dòng mà không làm tràn bộ nhớ shuffle.
5. **Kiểm định mốc thời gian (Temporal Profiling):** Phân tích giá trị số nguyên thời gian để xác định đơn vị (epoch milliseconds đối với postings vs. epoch seconds đối với employee_counts) và kiểm tra dải ngày thực tế.
6. **Kiểm tra lỗi mã hóa ký tự (Encoding Profiling):** Quét các mẫu ký tự Mojibake UTF-8 bị giải mã sai từ nguồn (Windows-1252 sang UTF-8).
7. **Kiểm định toàn vẹn tham chiếu (Referential Integrity Profiling):** Đối soát khóa ngoại giữa các bảng cha và con, tính tỷ lệ phủ khóa và đếm các bản ghi mồ côi (orphan records).

---

## 5. Important Audit Findings (Kết quả Kiểm kê Thực tế từ D03)

- **Tính toàn vẹn tệp:** Toàn bộ 11 tệp CSV thô đọc thành công, không có bản ghi nào bị gãy cấu trúc CSV toàn dòng (0 duplicate full rows trên cả 11 tệp).
- **Trường thiếu nghiêm trọng:** 16 trường trong dữ liệu có tỷ lệ thiếu trên 20%:
  - `closed_time` (thiếu 99.13%), `skills_desc` (thiếu 98.03%), `med_salary` (thiếu 94.93%), `remote_allowed` (thiếu 87.69%), `applies` (thiếu 81.17%), `min_salary`/`max_salary` (thiếu 75.94%).
- **Trùng lặp khóa luận lý trong bảng thô:**
  - `employee_counts`: Cặp `(company_id, time_recorded)` xuất hiện 122 dòng trùng lặp khóa.
  - `company_specialities`: Cặp `(company_id, speciality)` xuất hiện 20 dòng trùng lặp sau khi chuẩn hóa.
- **Lỗi hiển thị ký tự (Mojibake):**
  - Xuất hiện lỗi ký tự ở 1 dòng trường `title` (postings), 79 dòng trường `description` (postings), và 3 dòng trường `description` (companies).
- **Khóa ngoại mồ côi (Orphans):**
  - Tồn tại khóa ngoại mồ côi ở 5 quan hệ thực tế: `salaries` (độ phủ khóa chỉ đạt 88.45%), `benefits` (95.71%), `job_skills` (96.28%), `job_industries` (96.29%), và `companies` $\rightarrow$ `postings` (99.996%).

---

## 6. Data Cleaning Method (Phương pháp Làm sạch Dữ liệu tại D04)

Tại pha D04 (`src/clean_data.py`), dữ liệu được làm sạch theo các quy tắc nghiêm ngặt và tất định:
1. **Chuẩn hóa giá trị thiếu:** Trim khoảng trắng thừa; chuyển đổi thống nhất chuỗi rỗng và các sentinel token (`NULL`, `N/A`, `NA`) thành giá trị `NULL` chuẩn của Spark. Tuyệt đối không tự ý gán số 0 cho số thiếu hoặc gán `false` cho boolean thiếu.
2. **Chuẩn hóa định danh (Identifier Normalization):** Nhận diện các định danh số nguyên (cho phép cú pháp dạng `123.0` từ nguồn số thực) chuyển đổi chính xác sang kiểu `LongType` (bigint).
3. **Chuẩn hóa kiểu dữ liệu (Schema Typing):** Ép kiểu tường minh cho từng cột: tiền tệ/lương dạng `DecimalType(20,4)`, số đếm dạng `LongType`, cờ boolean dạng `BooleanType`.
4. **Chuẩn hóa mốc thời gian:** Quy đổi epoch milliseconds (cho postings) và epoch seconds (cho employee_counts) thành kiểu `TimestampType` trên múi giờ chuẩn UTC, đồng thời lưu giữ một cột bản sao `*_raw` để phục vụ đối soát.
5. **Sửa lỗi Encoding xác thực:** Áp dụng ánh xạ sửa lỗi có mục tiêu cho các ký tự Mojibake đã xác nhận tại D03 (`â€™` $\rightarrow$ `’`, `â€œ` $\rightarrow$ `“`, `â€“` $\rightarrow$ `–`, v.v.), không dùng hàm decode mù quáng toàn cục.
6. **Xử lý trùng lặp và cách ly bản ghi (Quarantine / Rejection):**
   - Khi phát hiện trùng lặp khóa luận lý trong `employee_counts` và `company_specialities`, pipeline áp dụng thuật toán xếp hạng nội dung (ưu tiên bản ghi có nhiều trường kinh doanh không null nhất, sau đó dùng giá trị băm SHA-256 để chọn tất định).
   - Các bản ghi bị loại bỏ **không bị xóa bỏ âm thầm** mà được lưu trữ cách ly tại thư mục `data/processed/rejected/` để đảm bảo khả năng kiểm toán truy vết.

---

## 7. Row Reconciliation (Đối soát Cân bằng Dòng từ D04)

Pipeline đảm bảo nguyên tắc bảo toàn dòng tuyệt đối: `Input Rows (Raw) = Output Rows (Clean) + Rejected Rows`.

| Bảng | Dòng vào (Raw) | Dòng sạch (Clean) | Dòng cách ly (Rejected) | Ghi chú xử lý |
| :--- | :---: | :---: | :---: | :--- |
| `postings` | 123,849 | 123,849 | 0 | Giữ trọn vẹn 100% |
| `companies` | 24,473 | 24,473 | 0 | Giữ trọn vẹn 100% |
| `company_industries` | 24,375 | 24,375 | 0 | Giữ trọn vẹn 100% |
| `company_specialities` | 169,387 | 169,367 | 20 | Loại 20 dòng trùng cặp khóa `(company_id, speciality)` |
| `employee_counts` | 35,787 | 35,665 | 122 | Loại 122 dòng trùng cặp khóa `(company_id, time_recorded)` |
| `benefits` | 67,943 | 67,943 | 0 | Giữ trọn vẹn 100% |
| `job_industries` | 164,808 | 164,808 | 0 | Giữ trọn vẹn 100% |
| `job_skills` | 213,768 | 213,768 | 0 | Giữ trọn vẹn 100% |
| `salaries` | 40,785 | 40,785 | 0 | Giữ trọn vẹn 100% |
| `industries` | 422 | 422 | 0 | Giữ trọn vẹn 100% |
| `skills` | 35 | 35 | 0 | Giữ trọn vẹn 100% |

---

## 8. Parquet Storage (Lưu trữ Dạng Cột Chuẩn hóa)

Dữ liệu sạch sau D04 được lưu trữ dưới định dạng Apache Parquet tại `data/processed/clean/`:
- **Định dạng dạng cột (Columnar Format):** Tối ưu hóa cho các truy vấn phân tích (OLAP) và Spark SQL chỉ đọc những cột cần thiết thay vì đọc toàn bộ hàng dữ liệu.
- **Bảo toàn kiểu dữ liệu mạnh:** Lưu trữ trực tiếp schema định kiểu (bigint, timestamp, decimal, boolean), loại bỏ hoàn toàn chi phí parse chuỗi ở các pha phân tích tiếp theo.
- **Nén Snappy tích hợp:** Giảm thiểu dung lượng lưu trữ trên đĩa mà vẫn duy trì tốc độ giải nén cao khi xử lý song song.
*(Các chỉ số đo lường hiệu năng đọc/ghi chi tiết sẽ được thực hiện và công bố tại D08).*

---

## 9. Join Safety Preparation (Chuẩn bị An toàn Khóa và Grain cho D05)

Tại D05 Pre-check và Scaffold (`src/d05_utils.py`, `src/d05_prejoin_validation.py`):
1. **Quy tắc Grain:** Bảng chuẩn hóa chính phải đảm bảo nghiêm ngặt grain **1 dòng = 1 tin tuyển dụng (`job_id`)**.
2. **Cơ chế Aggregate-Before-Join:**
   - Thực nghiệm đã chỉ ra việc JOIN phẳng các bảng quan hệ nhiều-nhiều (`job_skills`, `job_industries`, `benefits`, `company_specialities`) sẽ gây bùng nổ dữ liệu (Row Explosion) làm nhân bản một tin tuyển dụng lên từ hàng chục đến hàng nghìn lần (ví dụ: postings + raw job_skills tăng từ 123,849 lên 207,531 dòng).
   - Tiện ích `aggregate_bridge` gom nhóm các bảng này thành mảng định kiểu (`array_sort(collect_set(...))`) trước khi thực hiện phép LEFT JOIN.
   - Tiện ích `latest_per_key` trích xuất đúng 1 snapshot mới nhất của `employee_counts` cho mỗi công ty.
3. **Bộ bảo vệ an toàn (Safety Guards):** Các hàm kiểm định `assert_unique_key` và `check_grain_preserved` đảm bảo tuyệt đối không có sự biến đổi số dòng sau JOIN.

---

## 10. Current Limitations (Các Giới hạn Hiện tại)

1. **Phụ thuộc Task A03 chưa hoàn thành:** Bản đồ JOIN chính thức và phương án giải nghĩa 35 nhãn chức năng công việc trong `skills.csv` chưa được chốt bởi Thành viên 2.
2. **Kỹ năng kỹ thuật chưa được trích xuất:** Bảng `job_skills` chỉ chứa các nhóm ngành chung chung; kỹ năng kỹ thuật cụ thể (Python, Java, SQL...) bắt buộc phải trích xuất từ văn bản mô tả (`description`) tại các bước tiếp theo.
3. **Độ bao phủ dữ liệu lương hạn chế:** Chỉ 29.13% tin tuyển dụng có cấu trúc lương tại bảng `salaries`, đòi hỏi cẩn trọng khi diễn giải số liệu thống kê để tránh sai lệch mẫu.
4. **Chưa lọc phạm vi CNTT:** Pipeline hiện tại lưu trữ toàn bộ tin tuyển dụng của mọi ngành nghề; bộ lọc CNTT sẽ được áp dụng tại D06.

---

## 11. TODO For Final D10 (Các Mục Chờ Hoàn Thiện Báo Cáo Cuối)

Các phần dưới đây được giữ ở trạng thái giữ chỗ (placeholder) và sẽ được viết chi tiết khi các task liên quan hoàn thành:

- `[TODO D05]`: **Canonical Integration** — Mô tả chi tiết quá trình JOIN tạo bảng canonical hoàn chỉnh sau khi A03 unblock D05.
- `[TODO D06]`: **IT Filtering** — Mô tả phương pháp luận và kết quả phân loại tin tuyển dụng CNTT dựa trên taxonomy của TV2.
- `[TODO D07]`: **Salary Normalization** — Mô tả quy chuẩn xử lý đa tiền tệ, quy đổi kỳ hạn trả lương và tính toán phân vị lương.
- `[TODO D08]`: **Spark Benchmark & Performance Evaluation** — Báo cáo các chỉ số đo lường hiệu năng ETL Spark, số lượng partitions, và thời gian thực thi trên môi trường thực tế.
- `[TODO D09]`: **Final Pipeline Validation** — Kiểm tra hồi quy toàn diện trên pipeline từ đầu đến cuối trước khi đóng gói sản phẩm.
