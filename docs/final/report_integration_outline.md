# Final Report Integration Outline (Đề cương Báo cáo Tổng hợp Cuối kỳ)

> [!NOTE]
> **TÀI LIỆU CHUẨN BỊ PHỤC VỤ NHIỆM VỤ V10 (BÁO CÁO TỔNG HỢP CUỐI KỲ).**  
> Trạng thái hiện tại: **V10 OFFICIAL NOT EXECUTED**.  
> Đề cương này thiết lập cấu trúc 16 chương của Báo cáo Tổng kết Đồ án. Mỗi phần được gắn nhãn trạng thái mức độ sẵn sàng:
> - 🟢 **READY**: Nội dung và số liệu đã hoàn thành 100%, có bằng chứng thực nghiệm từ repository.
> - 🟡 **PARTIAL**: Đã có khung kỹ thuật hoặc dữ liệu một phần, đang chờ dữ liệu chính thức để hoàn thiện.
> - 🔴 **WAITING**: Chưa có dữ liệu thực nghiệm, đang chờ các nhiệm vụ phân tích phía sau hoàn thành (tuyệt đối không bịa số liệu).

---

## Cấu trúc 16 Chương Báo cáo

| Chương | Tên chương | Mức độ sẵn sàng | Nguồn bằng chứng & Ghi chú |
| :--- | :--- | :---: | :--- |
| **1** | **Introduction (Giới thiệu)** | 🟢 **READY** | Mục tiêu đồ án, bài toán phân tích thị trường tuyển dụng CNTT từ Big Data. Nguồn: `README.md`, `project_status.md`. |
| **2** | **Dataset and Scope (Dữ liệu và Phạm vi)** | 🟢 **READY** | Bộ dữ liệu LinkedIn 2023–2024 (Arsh Koneru, 11 CSV, 530.72 MB, 123,849 tin). Giới hạn phạm vi không suy rộng toàn Việt Nam. Nguồn: `data_manifest.md`. |
| **3** | **System Architecture (Kiến trúc Hệ thống)** | 🟢 **READY** | Sơ đồ luồng xử lý phân tán PySpark 4.2.0 local[*], Java 21, UTC session, Windows adapter và giao diện Streamlit. Nguồn: `data_methodology_draft.md`. |
| **4** | **Data Audit (Kiểm kê & Chất lượng Dữ liệu)** | 🟢 **READY** | Hồ sơ 11 bảng thô: kiểm kê missingness (16 cột $\ge 20\%$), candidate keys, SHA-256 duplicate rows, epoch timestamps, Mojibake, orphan keys. Nguồn: `d03_data_quality_report.md`. |
| **5** | **Data Cleaning (Làm sạch Dữ liệu)** | 🟢 **READY** | Ép kiểu schema tường minh, chuẩn hóa sentinel tokens, sửa 83 lỗi Mojibake, loại và cách ly 142 bản ghi trùng lặp (`data/processed/rejected/`), bảo toàn dòng 100%. Nguồn: `d04_cleaning_report.md`. |
| **6** | **Data Integration (Tích hợp & Khóa)** | 🟡 **PARTIAL** | *Đã có:* Khảo sát cardinality quan hệ nhiều-nhiều, phát hiện nguy cơ bùng nổ dòng (flat join tăng lên 207,531 dòng), cơ chế `aggregate-before-join` và `latest_per_key` (bảo toàn 123,849 dòng).<br>*Đang chờ:* Bảng canonical chính thức sau khi A03 unblock D05. Nguồn: `d05_precheck.md`, `d05_implementation_scaffold.md`. |
| **7** | **IT Recruitment Classification (Phân loại CNTT)** | 🔴 **WAITING** | Phương pháp luận lọc tin CNTT, taxonomy nghề nghiệp, đánh giá mẫu gán nhãn 100–200 tin, và tỷ lệ chọn/loại tin. Chờ nhiệm vụ **D06 & A02/A04**. |
| **8** | **Skills Analysis (Phân tích Kỹ năng Tuyển dụng)** | 🔴 **WAITING** | Bảng xếp hạng Top kỹ năng kỹ thuật (Python, Java, SQL...), trích xuất từ văn bản `description`, kỹ năng theo nhóm nghề và cấp bậc. Chờ nhiệm vụ **A05 & A07**. *(Nhấn mạnh: bảng `skills.csv` gốc chỉ là job functions).* |
| **9** | **Salary Analysis (Phân tích Mức lương Tuyển dụng)** | 🔴 **WAITING** | Phân vị lương (P25, Median, P75) theo nhóm nghề trên cùng đơn vị USD/Năm, độ bao phủ thực tế (29.13%). Chờ nhiệm vụ **D07 & A08**. |
| **10** | **Spark Performance (Hiệu năng Xử lý Spark)** | 🔴 **WAITING** | Đo lường thời gian thực thi ETL, số partition, tối ưu shuffle, bộ nhớ và ảnh chụp Spark UI. Chờ nhiệm vụ **D08**. |
| **11** | **Dashboard (Giao diện Trực quan hóa Tương tác)** | 🟡 **PARTIAL** | *Đã có:* Khung Streamlit multi-page (`app.py`, 3 trang nghiệp vụ, bộ lọc, xử lý lỗi, chế độ sample mode).<br>*Đang chờ:* Kết nối các bảng tổng hợp chính thức `data/analytics/` từ A06–A08. Nguồn: `dashboard/`, `dashboard_wireframe.md`. |
| **12** | **Validation (Kiểm định & Đối soát Toàn vẹn)** | 🟡 **PARTIAL** | *Đã có:* Smoke test môi trường, đối soát 67 kiểm định D04, test suite bảo toàn grain D05 (21.7s), test suite tự động dashboard.<br>*Đang chờ:* Kiểm thử tích hợp toàn diện từ đầu đến cuối pipeline tại **D09 / V07**. |
| **13** | **Limitations (Các Giới hạn & Khuyến nghị)** | 🟢 **READY** | Giới hạn về độ phủ lương (29.13%), nhãn kỹ năng thô không cụ thể, phân bố địa lý không đại diện toàn cầu, giới hạn suy rộng thị trường. Nguồn: `data_methodology_draft.md`. |
| **14** | **Conclusion (Kết luận)** | 🟡 **PARTIAL** | *Đã có:* Kết luận về quy trình kỹ thuật dữ liệu lớn, tính khả thi của Apache Spark trên máy đơn và giải pháp kiểm soát chất lượng.<br>*Đang chờ:* Kết luận tổng thể về xu hướng thị trường lao động CNTT sau khi có kết quả phân tích. |
| **15** | **References (Tài liệu Tham khảo)** | 🟢 **READY** | Bộ dữ liệu LinkedIn Kaggle, Apache Spark 4.2.0 Docs, Streamlit Docs, CC BY-SA 4.0 License. Nguồn: `source_register_draft.md`. |
| **16** | **Team Contributions (Đóng góp của Thành viên)** | 🟡 **PARTIAL** | Bảng phân công trách nhiệm và minh chứng đóng góp theo mã nhiệm vụ của TV1, TV2, TV3. Nguồn: `team_contribution_matrix_draft.md`. |
