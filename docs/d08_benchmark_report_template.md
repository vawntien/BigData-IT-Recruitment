# D08 Spark Benchmark Report (Mẫu Báo cáo Đánh giá Hiệu năng)

> [!WARNING]
> **TÀI LIỆU NÀY LÀ KHUNG MẪU BÁO CÁO (REPORT TEMPLATE) PHỤC VỤ NHIỆM VỤ D08.**  
> Trạng thái hiện tại: **TODO – OFFICIAL D08 NOT EXECUTED**.  
> Toàn bộ các bảng số liệu đo lường, kết quả phân vùng và so sánh CSV vs Parquet bên dưới đang ở trạng thái giữ chỗ (placeholder) và sẽ được điền đầy đủ sau khi pipeline phân tích hoàn tất và kịch bản benchmark chính thức được kích hoạt.

---

## 1. Environment (Môi trường Thử nghiệm)

- **Hệ điều hành:** Windows
- **Bộ vi xử lý (CPU):** `[TODO: Ghi rõ thông số CPU, số Cores, số Threads]`
- **Bộ nhớ trong (RAM):** `[TODO: Ghi rõ dung lượng RAM vật lý]`
- **Phiên bản Python:** Python 3.11.0 (Virtual environment `.venv`)
- **Phiên bản Java:** OpenJDK 21.0.12.1 LTS (Eclipse Temurin)
- **Phiên bản Spark:** Apache Spark / PySpark 4.2.0
- **Chế độ thực thi:** Spark `local[*]`
- **Session Timezone:** UTC

---

## 2. Dataset (Bộ Dữ liệu Đo lường)

- **Tên dataset:** LinkedIn Job Postings (2023–2024)
- **Quy mô tệp thô:** 11 tệp CSV (~530.72 MB), 123,849 tin tuyển dụng
- **Quy mô tệp sạch:** 11 bảng Parquet tại `data/processed/clean/`
- **Tình trạng:** Cố định, không chỉnh sửa trong suốt quá trình đo

---

## 3. Methodology (Phương pháp luận Đo lường)

- Đo lường thời gian thực tế bằng đồng hồ đơn vị giây (`time.perf_counter()`).
- Mỗi phép đo thực hiện qua 4 lượt: 1 lượt khởi động JVM (Warm-up) và 3 lượt đo chính thức (`run_1`, `run_2`, `run_3`).
- Chỉ số công bố là giá trị **Trung vị (Median)** của 3 lượt đo.
- Phân lập rõ ràng giữa kịch bản Cold (chưa có đệm) và Cached (đã lưu bộ nhớ đệm).

---

## 4. Benchmark Scenarios (Các Kịch bản Thử nghiệm)

Mô tả 6 kịch bản theo kế hoạch [d08_benchmark_plan.md](file:///d:/Learning/Bigdata/BigData-IT-Recruitment/docs/d08_benchmark_plan.md):
- **B1:** Quét dữ liệu nguồn (Source Scan)
- **B2:** Lọc tin tuyển dụng (Filtering)
- **B3:** Gom nhóm mảng xác định (Aggregation)
- **B4:** Kết hợp bảng an toàn bảo toàn grain (Safe Join)
- **B5:** Ghi tệp Parquet và nén dữ liệu (Parquet Write)
- **B6:** Toàn bộ giai đoạn pipeline đầu-cuối (End-to-End Analytics Stage)

---

## 5. Results (Bảng Kết quả Đo lường Chính thức)

| Kịch bản | Thao tác | Số dòng vào | Số dòng ra | Run 1 (s) | Run 2 (s) | Run 3 (s) | Trung vị (Median) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **B1** | Đọc tệp postings | 123,849 | 123,849 | `TODO` | `TODO` | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **B2** | Lọc tin tuyển dụng CNTT | 123,849 | `TODO` | `TODO` | `TODO` | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **B3** | Gom nhóm skills bridge | 213,768 | 126,807 | `TODO` | `TODO` | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **B4** | Safe Join quan hệ postings | 123,849 | 123,849 | `TODO` | `TODO` | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **B5** | Ghi tệp Parquet chuẩn hóa | 123,849 | 123,849 | `TODO` | `TODO` | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **B6** | Pipeline ETL đầu-cuối | 11 bảng | `TODO` | `TODO` | `TODO` | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |

---

## 6. CSV vs. Parquet (So sánh Hiệu năng Định dạng Lưu trữ)

| Tiêu chí | CSV thô (`postings.csv`) | Clean Parquet (`clean/postings`) | Mức độ chênh lệch |
| :--- | :---: | :---: | :---: |
| **Dung lượng trên đĩa** | 492.90 MB | `TODO` MB | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **Thời gian Full Scan (`count`)** | `TODO` s | `TODO` s | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **Thời gian quét có chọn cột (Projection)**| `TODO` s | `TODO` s | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **Chi phí ép kiểu dữ liệu** | Phải parse chuỗi tại runtime | Đã định kiểu sẵn trong metadata | Tiết kiệm chi phí parse CPU |

---

## 7. Partition Study (Nghiên cứu Cấu hình Phân vùng Xáo trộn)

| Cấu hình `spark.sql.shuffle.partitions` | Số phân vùng | Thời gian Shuffle Aggregation (s) | Nhận xét chi phí điều phối |
| :---: | :---: | :---: | :--- |
| **200 (Default)** | 200 | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **16** | 16 | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **8** | 8 | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |
| **4** | 4 | `TODO` | `TODO – OFFICIAL D08 NOT EXECUTED` |

---

## 8. Spark UI Evidence (Minh chứng Giao diện Spark UI)

- **Ảnh chụp Jobs Tab:** `[TODO: Chèn ảnh chụp giao diện Jobs tab sau khi chạy]`
- **Ảnh chụp Stages Tab:** `[TODO: Chèn ảnh chụp giao diện Stages tab]`
- **Biểu đồ DAG Kế hoạch Thực thi:** `[TODO: Chèn biểu đồ DAG minh họa các điểm shuffle]`
- **Thống kê Shuffle Read / Write:** `[TODO: Ghi nhận dung lượng shuffle bytes]`

---

## 9. Interpretation (Phân tích & Diễn giải Kết quả)

- `TODO – OFFICIAL D08 NOT EXECUTED`: Phân tích tác động của cấu hình phân vùng đến chi phí điều phối trên CPU máy đơn.
- `TODO – OFFICIAL D08 NOT EXECUTED`: Diễn giải lợi thế đọc dạng cột của Parquet đối với các truy vấn tổng hợp lọc trường.

---

## 10. Limitations (Các Giới hạn của Thử nghiệm)

- Thử nghiệm được thực hiện trên môi trường máy đơn (`local[*]`), chưa phản ánh chi phí truyền tải mạng thực tế trên cụm phân tán nhiều nút vật lý (Distributed Cluster).
- Khối lượng dữ liệu thử nghiệm (~530 MB) nằm trọn trong dung lượng RAM máy trạm, chưa kích hoạt cơ chế tràn đĩa (disk spill) quy mô lớn.

---

## 11. Reproducibility (Xác minh Khả năng Tái lập)

- Lệnh chạy lại toàn bộ benchmark:
  ```powershell
  .\.venv\Scripts\python.exe src\d08_benchmark_scaffold.py --official
  ```
- Dữ liệu kết quả được lưu tự động tại: `data/audit/d08/benchmark_runs.csv`.

---

## 12. Conclusion (Kết luận Đánh giá Hiệu năng)

`TODO – OFFICIAL D08 NOT EXECUTED`: Kết luận chính thức sẽ được đưa ra sau khi thực hiện đầy đủ các lượt đo nghiệm thu.
