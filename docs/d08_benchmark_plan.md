# D08 Spark Performance Benchmark Plan (Kế hoạch Đánh giá Hiệu năng Spark)

> [!IMPORTANT]
> **KẾ HOẠCH ĐÁNH GIÁ HIỆU NĂNG CHUẨN BỊ CHO NHIỆM VỤ D08 CHÍNH THỨC.**  
> Trạng thái hiện tại: **D08 OFFICIAL NOT EXECUTED**.  
> Tài liệu này thiết lập phương pháp luận, các kịch bản đo lường thực nghiệm, cơ chế kiểm soát khả năng tái lập (reproducibility) và chính sách bộ nhớ đệm (caching). Tuyệt đối không tự suy diễn các kết luận hiệu năng trước khi thực thi benchmark chính thức.

---

## 1. Mục tiêu Đánh giá (Benchmark Objective)

Đo lường định lượng hiệu năng thực thi của Apache Spark 4.2.0 trên môi trường máy đơn (`local[*]`) đối với pipeline xử lý dữ liệu lớn LinkedIn Job Postings (123,849 tin tuyển dụng, 11 bảng dữ liệu).  
Các tiêu chí đo lường chính bao gồm:
- Thời gian thực thi thực tế (Wall-clock elapsed time, tính bằng giây).
- Tác động của cơ chế nén và định dạng lưu trữ dạng cột (CSV thô vs. Parquet Snappy).
- Tác động của cấu hình phân vùng xáo trộn (`spark.sql.shuffle.partitions`).
- Tác động của cơ chế lưu vào bộ nhớ đệm (`DataFrame.cache()`).
- Phân tích biểu đồ DAG và các giai đoạn thực thi (Stages/Tasks) thông qua Spark UI.

---

## 2. Kiểm soát Khả năng Tái lập (Reproducibility Controls)

Mọi phép đo chính thức bắt buộc phải tuân thủ nghiêm ngặt các điều kiện môi trường cố định:
1. **Phần cứng:** Cùng một máy tính vật lý thử nghiệm (ghi nhận CPU, số core/threads, dung lượng RAM).
2. **Hệ điều hành & Môi trường:** Windows, Python 3.11.0 trong virtual environment `.venv`, OpenJDK 21.0.12.1 LTS.
3. **Phiên bản Spark:** Apache Spark / PySpark 4.2.0 chạy ở chế độ **`local[*]`** (không suy diễn thành cụm phân tán nhiều máy).
4. **Bộ dữ liệu:** Bản snapshot cố định LinkedIn Job Postings 2023–2024 (11 tệp CSV thô ~530.72 MB, không thay đổi mtime và dung lượng).
5. **Session Timezone:** Cố định `UTC` cho toàn bộ các phép toán thời gian.
6. **Mã nguồn & Commit Hash:** Ghi nhận chính xác Git commit hash tại thời điểm đo lường.

---

## 3. Chính sách Lặp lại và Khởi động (Warm-up & Repetitions Policy)

### Quy trình Đo lường:
Mỗi kịch bản đo lường được thực hiện qua **4 lượt**:
- **Lượt 0 (Warm-up run):** Chạy khởi động để tải thư viện JVM, khởi tạo các luồng executor và biên dịch JIT (Just-In-Time) của Java. Kết quả lượt này **không được tính vào kết quả phân tích**.
- **Lượt 1, 2, 3 (Measured runs):** Chạy đo lường thực tế, ghi nhận `run_1`, `run_2`, `run_3`.
- **Chỉ số đại diện:** Sử dụng giá trị **Trung vị (Median elapsed time)** của 3 lượt đo làm chỉ số chính.

$$\text{Reported Metric} = \text{median}(\text{run\_1}, \text{run\_2}, \text{run\_3})$$

### Vì sao sử dụng Median thay vì Mean hoặc chạy 1 lần?
- Tránh các đột biến bất thường do hệ điều hành Windows điều phối tác vụ nền (I/O jitter, virus scanning).
- Khử nhiễu phát sinh từ các chu kỳ gom rác (Garbage Collection - GC) ngẫu nhiên của JVM.
- Đảm bảo tính vững (robustness) vượt trội so với việc chỉ lấy một lần chạy đơn lẻ.

---

## 4. Chính sách Bộ nhớ đệm (Cache Policy)

Để tránh ngụy biện về tốc độ xử lý, các phép đo **Không dùng đệm (Cold / Uncached)** và **Có dùng đệm (Warm / Cached)** phải được phân lập tách bạch:

### Quy trình Đo đạc khi có Cache:
1. Gọi lệnh lưu đệm: `df.persist(StorageLevel.MEMORY_AND_DISK)`.
2. **Kích hoạt nạp bộ nhớ (Materialization action):** Thực hiện một action (ví dụ: `df.count()`) để Spark thực sự tính toán và lưu dữ liệu vào RAM/đĩa. Lượt kích hoạt này được đo lường và ghi nhận riêng.
3. **Đo lường thao tác phân tích hạ nguồn:** Thực hiện action phân tích cần kiểm thử và đo thời gian.
4. **Giải phóng đệm (Unpersist):** Gọi `df.unpersist()` và kiểm tra giải phóng bộ nhớ trước khi chuyển sang kịch bản tiếp theo.
> *Nguyên tắc:* Tuyệt đối không công bố kết luận cải thiện tốc độ từ Cache khi chưa có số liệu đo lường tách bạch hai pha trước và sau.

---

## 5. Ma trận 6 Kịch bản Đo lường Chính thức (Official Benchmark Matrix)

| Mã kịch bản | Thao tác (Operation) | Dữ liệu đầu vào (Input) | Grain kỳ vọng | Tiêu chí đo lường | Chính sách Cache | Đầu ra ghi nhận |
| :--- | :--- | :--- | :---: | :--- | :---: | :--- |
| **B1** | Đọc dữ liệu nguồn (Source Scan) | `data/raw/postings.csv`<br>vs `clean/postings` | 123,849 dòng | Thời gian đọc & schema scan | COLD | Số dòng, số partition, thời gian |
| **B2** | Lọc dữ liệu (Filtering) | `postings` (toàn bộ 123,849 tin) | Các tin thỏa mãn điều kiện lọc | Thời gian quét & lọc bản ghi | COLD & CACHED | Số tin được chọn, thời gian |
| **B3** | Gom nhóm (Aggregation) | `job_skills` (213,768 dòng) | 126,807 tin duy nhất | Thời gian group by & array_sort | COLD | Số nhóm, số partition sau shuffle |
| **B4** | Kết hợp bảng (JOIN) | `postings` (123,849) $\times$ `job_skills` (213,768) | Safe Join (123,849 dòng)<br>vs Flat Join | Thời gian thực thi JOIN và bảo toàn grain | COLD | Số dòng sau JOIN, số duplicate key |
| **B5** | Ghi tệp đĩa (Parquet Write) | DataFrame kết quả sau chuẩn hóa | 123,849 dòng | Thời gian ghi & kích thước đĩa | COLD | Dung lượng bytes, số tệp part-* |
| **B6** | Giai đoạn ETL đầu-cuối (End-to-End) | 11 bảng Parquet sạch $\rightarrow$ Canonical Analytics | 1 dòng / tin CNTT | Toàn bộ thời gian pipeline D05/D06 | COLD | Tổng thời gian, tổng bộ nhớ shuffle |

---

## 6. Kế hoạch Nghiên cứu Cấu hình Phân vùng (Partition Study Plan)

Mặc định Spark SQL thiết lập `spark.sql.shuffle.partitions = 200`. Với tập dữ liệu trung bình (~530 MB) trên máy cá nhân, 200 partition có thể gây phân mảnh và chi phí điều phối tác vụ (task scheduling overhead) quá mức.

### Các cấu hình đối chiếu dự kiến:
- **Cấu hình P1 (Spark Default):** `spark.sql.shuffle.partitions = 200`
- **Cấu hình P2 (1x CPU Cores):** `spark.sql.shuffle.partitions = 4` hoặc `8` (khớp với số luồng CPU vật lý)
- **Cấu hình P3 (2x CPU Cores):** `spark.sql.shuffle.partitions = 16`
- **Cấu hình P4 (Phân vùng tối thiểu):** `spark.sql.shuffle.partitions = 2`

> *Nguyên tắc:* Ghi nhận khách quan thời gian của từng cấu hình; không kết luận cấu hình nào là "tối ưu nhất" trước khi có bảng dữ liệu thực nghiệm so sánh.

---

## 7. Kế hoạch So sánh CSV vs. Parquet (CSV vs. Parquet Study Plan)

So sánh hiệu năng giữa hai định dạng lưu trữ trên cùng một khối lượng dữ liệu (123,849 tin tuyển dụng):

| Tiêu chí đối chiếu | Tệp CSV thô (`postings.csv`) | Bảng Parquet sạch (`clean/postings`) |
| :--- | :--- | :--- |
| **Dung lượng lưu trữ trên đĩa** | 492.90 MB (dạng văn bản thô) | Ghi nhận dung lượng tệp `.snappy.parquet` thực tế |
| **Chi phí ép kiểu dữ liệu** | Phải parse chuỗi sang số/ngày tại runtime | Schema định kiểu sẵn (bigint, timestamp, decimal) |
| **Hiệu năng quét toàn bộ dòng (`count`)** | Đo bằng Median 3 lượt chạy | Đo bằng Median 3 lượt chạy |
| **Hiệu năng quét có chọn lọc cột (Projection)** | Buộc phải đọc qua toàn bộ dòng ký tự | Chỉ đọc cột cần thiết nhờ cấu trúc dạng cột |

> *Nguyên tắc:* Không khẳng định "Parquet nhanh hơn X lần" bằng lý thuyết suông; toàn bộ kết luận phải đi kèm bảng số liệu đo lường cụ thể tại D08.

---

## 8. Kế hoạch Thu thập Minh chứng Spark UI (Spark UI Evidence Plan)

Khi chạy benchmark chính thức, các minh chứng sau sẽ được chụp lại trực tiếp từ giao diện giám sát Spark UI (`http://localhost:4040`):
1. **Trang Jobs:** Thời gian thực thi của từng Action lớn (`count`, `saveAsParquet`).
2. **Trang Stages:** Danh sách các Stage, tỷ lệ thời gian giữa tính toán (Executor computing) và điều phối (Task deserialization/scheduler).
3. **Biểu đồ DAG (Directed Acyclic Graph):** Trực quan hóa kế hoạch thực thi phân tán, các điểm Shuffle Exchange và Broadcast Hash Join.
4. **Thông số Shuffle I/O:** Khối lượng dữ liệu đọc/ghi qua mạng/đĩa (`Shuffle Read Size`, `Shuffle Write Size`).
5. **Biểu đồ Task Duration Distribution:** Đánh giá độ lệch tải (Data Skew) giữa các phân vùng nhiệm vụ.
