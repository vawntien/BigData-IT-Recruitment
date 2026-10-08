# Presentation Slide Outline (Đề cương Slide Báo cáo Bảo vệ Đồ án)

> [!IMPORTANT]
> **ĐỀ CƯƠNG SLIDE CHUẨN BỊ CHO NHIỆM VỤ V10 & V11 (DÀNH CHO CẢ 3 THÀNH VIÊN).**  
> Toàn bộ các chỉ số phân tích nghiệp vụ chưa có số liệu chính thức được ghi nhận bằng các biến giữ chỗ `[FINAL VALUE FROM ...]`. Tuyệt đối không dùng các giá trị từ tập dữ liệu mẫu (synthetic sample) để điền vào slide báo cáo.

---

## Danh mục 14 Slides Thuyết trình (Thời lượng dự kiến: 12–15 phút)

### Slide 1: Trang Tiêu đề (Project Title & Team)
- **Tiêu đề đồ án:** Xây Dựng Pipeline Big Data Phân Tích Dữ Liệu Tuyển Dụng Công Nghệ Thông Tin Sử Dụng Apache Spark.
- **Bộ dữ liệu:** LinkedIn Job Postings (2023–2024).
- **Thành viên thực hiện:**
  - TV1: Kỹ thuật Dữ liệu, Pipeline Apache Spark & Tích hợp Hệ thống.
  - TV2: Phân loại Nghề nghiệp (Taxonomy), Trích xuất Kỹ năng & Phân tích Nghiệp vụ.
  - TV3: Trực quan hóa Giao diện, Streamlit Dashboard & Kiểm thử Đóng gói.

---

### Slide 2: Bài toán & Mục tiêu Đồ án (Problem Statement & Goals)
- **Bài toán:** Thị trường tuyển dụng CNTT biến động nhanh; dữ liệu tuyển dụng trực tuyến lớn, phi cấu trúc, thiếu chuẩn hóa và chứa nhiều nhiễu.
- **Mục tiêu kỹ thuật:** Xây dựng pipeline xử lý dữ liệu lớn bằng Apache Spark đảm bảo tính tất định, bảo toàn tính toàn vẹn của grain và ngăn chặn bùng nổ dữ liệu.
- **Mục tiêu nghiệp vụ:** Phân tích 4 khía cạnh trọng tâm: Cơ cấu nghề nghiệp, Kỹ năng công nghệ, Mức lương thực tế và Thông tin doanh nghiệp.

---

### Slide 3: Tổng quan Bộ dữ liệu (Dataset Overview & Ingestion)
- **Nguồn:** Kaggle — LinkedIn Job Postings 2023–2024 (Arsh Koneru, CC BY-SA 4.0).
- **Quy mô dữ liệu thô:** 11 tệp CSV (~530.72 MB).
- **Bảng trung tâm:** `postings.csv` gồm **123,849 dòng** và 31 cột thô.
- **Bảng phụ trợ:** 4 bảng doanh nghiệp, 4 bảng thuộc tính công việc, 2 bảng tra cứu chuẩn hóa.
- **Quy tắc bất biến:** Toàn bộ dữ liệu gốc `data/raw/` được giữ nguyên vẹn 100%, không lưu trên Git.

---

### Slide 4: Kiến trúc Pipeline Big Data (System Architecture)
- **Môi trường:** Apache Spark / PySpark 4.2.0 (`local[*]`), OpenJDK 21 LTS, Python 3.11, UTC session.
- **Sơ đồ luồng dữ liệu:**
  $$\text{Raw CSVs} \xrightarrow{\text{Audit (D03)}} \text{Cleaning (D04)} \xrightarrow{\text{Parquet Sạch}} \text{Safe Join (D05)} \xrightarrow{\text{IT Filter (D06)}} \text{Analytics} \xrightarrow{\text{UI}} \text{Streamlit (TV3)}$$
- **Lưu trữ chuẩn hóa:** Chuyển đổi toàn bộ sang định dạng Apache Parquet dạng cột (Columnar format, Snappy compression).

---

### Slide 5: Kiểm kê Chất lượng Dữ liệu Thô (Data Quality Audit - D03)
- **Độ khuyết thiếu (Missingness):** 16 cột khuyết thiếu $\ge 20\%$ (`closed_time` 99.1%, `skills_desc` 98.0%, `med_salary` 94.9%, `remote_allowed` 87.7%).
- **Lỗi hiển thị ký tự (Mojibake):** Phát hiện 83 bản ghi chứa lỗi mã hóa UTF-8 trong trường mô tả và tiêu đề.
- **Khóa ngoại mồ côi (Orphans):** 4,712 bản ghi lương và 7,990 bản ghi kỹ năng có `job_id` không tồn tại trong bảng tin tuyển dụng.
- **Bản chất nhãn kỹ năng:** 35 nhãn trong `skills.csv` là *Job Functions* (nhóm nghề tổng quát), không phải kỹ năng lập trình.

---

### Slide 6: Chuẩn hóa & Làm sạch Bằng Spark (Data Cleaning - D04)
- **Nguyên tắc bảo toàn dòng:** $\text{Input Rows (123,849)} = \text{Clean Rows (123,849)} + \text{Rejected Rows (0)}$.
- **Ép kiểu định danh:** Chuẩn hóa `job_id` và `company_id` sang kiểu số nguyên `LongType`.
- **Sửa lỗi Mojibake:** Thay thế chính xác các chuỗi ký tự lỗi đã xác minh mà không giải mã mù quáng toàn cục.
- **Cách ly bản ghi trùng lặp (Quarantine):** Loại và lưu trữ riêng 142 dòng trùng lặp khóa luận lý (122 dòng nhân sự + 20 dòng chuyên môn) vào `data/processed/rejected/`.

---

### Slide 7: Cơ chế Safe Join & Kiểm soát Row Explosion (D05)
- **Thách thức:** Quan hệ nhiều-nhiều phức tạp (71,658 tin có $>1$ skill, công ty có tới 84 chuyên môn).
- **Thực nghiệm rủi ro:** Phép JOIN phẳng trực tiếp làm số dòng bùng nổ từ **123,849 lên 207,531 dòng** (+83,682 dòng dư thừa); một tin đơn lẻ có thể bị nhân bản lên tới 18,144 lần.
- **Giải pháp thiết kế:**
  - `aggregate_bridge`: Gom nhóm các bảng nhiều-nhiều thành mảng xác định (`array_sort(collect_set(...))`) trước khi JOIN.
  - `latest_per_key`: Chỉ lấy 1 snapshot nhân sự mới nhất cho mỗi công ty.
  - **Kết quả:** Bảo toàn tuyệt đối grain **1 dòng = 1 tin tuyển dụng** (đúng 123,849 dòng, 0 trùng lặp).

---

### Slide 8: Cơ cấu Tuyển dụng Ngành CNTT (IT Recruitment Overview)
- **Tổng số tin CNTT được nhận diện:** `[FINAL VALUE FROM D06/A06]` tin (chiếm `[FINAL VALUE FROM D06/A06]%` tổng dataset).
- **Phân bố theo nhóm nghề:**
  - Nhóm 1: `[FINAL VALUE FROM A06]` (`[FINAL VALUE FROM A06]%`)
  - Nhóm 2: `[FINAL VALUE FROM A06]` (`[FINAL VALUE FROM A06]%`)
  - Nhóm 3: `[FINAL VALUE FROM A06]` (`[FINAL VALUE FROM A06]%`)
- **Phân bố kinh nghiệm & Địa điểm:** Đa số tuyển dụng ở cấp độ `[FINAL VALUE FROM A06]` tại các trung tâm công nghệ `[FINAL VALUE FROM A06]`.

---

### Slide 9: Nhu cầu Kỹ năng Công nghệ (Technical Skills Analysis)
- **Phương pháp trích xuất:** Khai phá từ khóa kỹ thuật trực tiếp từ văn bản trường `description` bằng Spark Regex Matching (nhiệm vụ A05/A07).
- **Top 5 Kỹ năng được săn đón nhất:**
  1. `[FINAL VALUE FROM A07]`: `[FINAL VALUE FROM A07]%` tin yêu cầu.
  2. `[FINAL VALUE FROM A07]`: `[FINAL VALUE FROM A07]%` tin yêu cầu.
  3. `[FINAL VALUE FROM A07]`: `[FINAL VALUE FROM A07]%` tin yêu cầu.
  4. `[FINAL VALUE FROM A07]`: `[FINAL VALUE FROM A07]%` tin yêu cầu.
  5. `[FINAL VALUE FROM A07]`: `[FINAL VALUE FROM A07]%` tin yêu cầu.
- **Ma trận kỹ năng:** Ngôn ngữ lập trình và công nghệ đám mây phổ biến nhất theo từng nhóm nghề.

---

### Slide 10: Phân tích Mức lương Tuyển dụng (Salary Insights)
- **Độ phủ dữ liệu lương:** **29.13%** tin có thông tin lương cấu trúc.
- **Nguyên tắc phân tích:** Không gộp kỳ trả lương, chỉ phân tích trên phân khúc chuẩn **USD / Năm**.
- **Mức lương trung vị theo nhóm nghề:**
  - Nhóm cao nhất: `[FINAL VALUE FROM D07/A08]` với trung vị `[FINAL VALUE FROM D07/A08] USD/năm`.
  - Nhóm phổ biến: `[FINAL VALUE FROM D07/A08]` với trung vị `[FINAL VALUE FROM D07/A08] USD/năm`.
- **Dải lương (P25 - Median - P75):** `[FINAL VALUE FROM D07/A08]`.

---

### Slide 11: Demo Dashboard Trực quan hóa Tương tác (TV3 Streamlit App)
- **Kiến trúc UI:** Streamlit Multi-page App (`app.py`, `1_Overview`, `2_Skills`, `3_Salary_Quality`).
- **Tính năng nổi bật:**
  - Bộ lọc động đa chiều (Category, Experience, Location).
  - Tự động chuyển đổi giữa Production Mode và Sample Development Mode.
  - Tab giám sát chất lượng dữ liệu và kiểm tra hợp đồng tự động (`contract_validator.py`).
- **Trình chiếu trực tiếp:** Chạy demo 3 phút theo kịch bản chuẩn bị sẵn.

---

### Slide 12: Đánh giá Hiệu năng Pipeline Apache Spark (Benchmark - D08)
- **Thời gian thực thi pipeline ETL:** `[FINAL VALUE FROM D08]` giây.
- **Cấu hình Spark Partition:** `[FINAL VALUE FROM D08]` partitions tối ưu cho shuffle.
- **So sánh định dạng lưu trữ:** Parquet nén Snappy tiết kiệm `[FINAL VALUE FROM D08]%` dung lượng đĩa so với CSV thô và tăng tốc độ đọc truy vấn lên `[FINAL VALUE FROM D08]x`.
- **Spark UI:** Tối ưu hóa DAG execution và loại bỏ các bước tính toán lặp.

---

### Slide 13: Giới hạn của Đồ án & Bài học Kinh nghiệm (Limitations & Lessons)
- **Giới hạn dữ liệu:** Dữ liệu chỉ phản ánh tin tuyển dụng LinkedIn thu thập trong giai đoạn 2023–2024, không phản ánh toàn bộ thị trường lao động Việt Nam; tỷ lệ tin có lương chỉ đạt 29.13%.
- **Giới hạn kỹ thuật:** Kỹ năng kỹ thuật trích xuất từ regex phụ thuộc vào từ điển từ khóa; bảng `skills.csv` gốc không chứa kỹ năng chi tiết.
- **Bài học kinh nghiệm:** Tầm quan trọng của việc kiểm kê dữ liệu trước khi xử lý, cơ chế kiểm soát grain trong hệ thống phân tán, và phân định rõ ràng hợp đồng dữ liệu giữa Spark và UI.

---

### Slide 14: Kết luận & Phiên Hỏi đáp (Conclusion & Q&A)
- **Tổng kết:** Xây dựng thành công pipeline Big Data hoàn chỉnh từ tiếp nhận, làm sạch, tích hợp an toàn đến trực quan hóa tương tác cho 123,849 tin tuyển dụng.
- **Hướng phát triển:** Mở rộng pipeline lên cụm phân tán nhiều máy (Spark Cluster / HDFS) và áp dụng mô hình NLP tiên tiến để phân loại ngữ cảnh công việc.
- **Lời cảm ơn & Khởi động phiên Q&A.**
