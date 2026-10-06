# Team Presentation Roles Draft (Kế hoạch Phân công Thuyết trình)

> [!NOTE]
> **TÀI LIỆU BẢN THẢO (DRAFT) CHUẨN BỊ CHO BUỔI BẢO VỆ ĐỒ ÁN V10 & V11.**  
> Kế hoạch này phân chia phần trình bày và chuẩn bị câu hỏi phản biện dựa trên ranh giới trách nhiệm cốt lõi của 3 thành viên trong nhóm.

---

## 1. Phân định Trách nhiệm Thuyết trình Chính

| Thành viên | Trách nhiệm chuyên môn | Các Slide phụ trách | Nội dung thuyết trình chính |
| :--- | :--- | :---: | :--- |
| **TV1** | **Kỹ thuật Dữ liệu, Pipeline Apache Spark & Tích hợp** | **Slides 1, 3, 4, 5, 6, 7, 12** | - Giới thiệu đồ án, bộ dữ liệu và cấu trúc 11 tệp thô.<br>- Kiến trúc xử lý PySpark, Java adapter và lưu trữ Parquet.<br>- Báo cáo kết quả kiểm kê D03 (Missingness, Mojibake, Orphans).<br>- Quy trình làm sạch dữ liệu D04 và bảo toàn dòng 100%.<br>- Thách thức quan hệ nhiều-nhiều, nguy cơ Row Explosion và giải pháp `aggregate-before-join` D05.<br>- Đánh giá hiệu năng Spark (Benchmark D08). |
| **TV2** | **Taxonomy Nghề nghiệp, Trích xuất Kỹ năng & Phân tích Nghiệp vụ** | **Slides 2, 8, 9, 10, 13** | - Bài toán thực tế và mục tiêu phân tích thị trường lao động CNTT.<br>- Phương pháp phân loại tin tuyển dụng CNTT và taxonomy nghề nghiệp.<br>- Thuật toán trích xuất kỹ năng kỹ thuật từ văn bản `description` (A05).<br>- Phân tích kết quả Top kỹ năng, ma trận kỹ năng theo nhóm nghề (A07).<br>- Phân tích mức lương theo nhóm nghề, giải thích độ phủ lương 29.13% và nguyên tắc phân nhóm tiền tệ USD/Năm (D07/A08).<br>- Trình bày các giới hạn dữ liệu và khuyến nghị. |
| **TV3** | **Trực quan hóa Giao diện, Dashboard & Đóng gói Demo** | **Slides 11, 14 & Điều phối Demo** | - Trình bày kiến trúc giao diện Streamlit Multi-page App.<br>- Trực tiếp thao tác điều khiển Demo 3–5 phút theo kịch bản chuẩn bị sẵn.<br>- Minh họa tính năng lọc tương tác đa chiều (Category, Experience, Location).<br>- Trình diễn bảng giám sát chất lượng dữ liệu (Data Quality Dashboard).<br>- Trình bày kết luận tổng kết và điều phối phiên trả lời câu hỏi phản biện. |

---

## 2. Kế hoạch Thời lượng Dự kiến (Khung Thuyết trình 15 Phút)

- **Phần 1: Mở đầu & Kỹ thuật Dữ liệu lớn Spark (TV1)** — *Khoảng 5–6 phút*
  - Giới thiệu, kiến trúc, kiểm kê, làm sạch và cơ chế Safe Join giải quyết Row Explosion.
- **Phần 2: Phương pháp Luận & Kết quả Phân tích Nghiệp vụ (TV2)** — *Khoảng 4–5 phút*
  - Bộ lọc CNTT, kết quả trích xuất kỹ năng công nghệ và dải lương tuyển dụng.
- **Phần 3: Trực quan hóa Giao diện, Trình diễn Demo & Kết luận (TV3)** — *Khoảng 4–5 phút*
  - Trình chiếu Dashboard trực tiếp, tương tác bộ lọc, tab chất lượng dữ liệu và kết luận.
- **Phần 4: Phiên Trả lời Câu hỏi Phản biện (Cả 3 thành viên)** — *Theo yêu cầu của Hội đồng*.

---

## 3. Phân chia Chuẩn bị Câu hỏi Phản biện (Q&A Preparation)

| Thành viên | Lĩnh vực câu hỏi dự kiến | Hướng trả lời & Minh chứng |
| :--- | :--- | :--- |
| **TV1** | - Tại sao Spark chạy local mà không dùng Hadoop cluster?<br>- Làm thế nào để chứng minh không bị nhân bản tin khi JOIN?<br>- Quy tắc xử lý trùng lặp trong employee_counts là gì? | - Dẫn chứng cấu hình `local[*]`, kích thước 530 MB tối ưu trong RAM.<br>- Dẫn chứng số liệu test F (flat join tăng 207,531 vs safe join giữ 123,849 dòng).<br>- Dẫn chứng quy tắc chọn snapshot mới nhất theo `time_recorded`. |
| **TV2** | - Tại sao bảng `skills.csv` có 35 nhãn mà không thấy Python/Java?<br>- Độ chính xác của thuật toán trích xuất kỹ năng từ mô tả là bao nhiêu?<br>- Tại sao không quy đổi mức lương theo giờ sang lương năm? | - Dẫn chứng kiểm kê D03 chứng minh 35 nhãn là Job Functions.<br>- Dẫn chứng mẫu gán nhãn đánh giá 100–200 tin tại nhiệm vụ A04.<br>- Dẫn chứng sự khác biệt về bản chất hợp đồng (Full-time vs Freelance) và độ phủ lương 29.13%. |
| **TV3** | - Dashboard có bị chậm khi lượng dữ liệu lớn không?<br>- Xử lý ra sao nếu người dùng chọn bộ lọc không có dữ liệu?<br>- Làm thế nào ứng dụng hoạt động nếu pipeline ETL chưa chạy? | - Giải thích nguyên tắc tách biệt: Streamlit chỉ đọc bảng tổng hợp từ `data/analytics/` do Spark tính sẵn.<br>- Dẫn chứng cơ chế bắt lỗi Empty-state an toàn.<br>- Trình diễn chế độ Sample Development Mode dự phòng. |
