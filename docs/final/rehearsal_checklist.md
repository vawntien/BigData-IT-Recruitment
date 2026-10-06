# Rehearsal & Dry-Run Checklist (Kế hoạch Tổng duyệt & Phòng ngừa Sự cố)

Tài liệu này hướng dẫn quy trình tổng duyệt 2 lượt (**2 Rehearsal Rounds**) trước buổi thuyết trình chính thức, đồng thời thiết lập phương án ứng phó cho các sự cố kỹ thuật thường gặp.

---

## 1. Lượt Tổng duyệt 1: Tính Chính xác Kỹ thuật (Round 1: Technical Correctness)

*Mục tiêu: Đảm bảo số liệu và diễn giải kỹ thuật của 3 thành viên khớp nhau 100%, không mâu thuẫn.*

- [ ] **Kiểm tra tính nhất quán của số liệu:**  
  Đối soát chéo mọi con số trong slide và lời nói của TV1, TV2, TV3 với bảng chuẩn `final_metrics_registry.md`.
  - Số lượng tin thô: 123,849 tin.
  - Số lượng doanh nghiệp: 24,473 công ty.
  - Tỷ lệ có dữ liệu lương: 29.13% (36,073 tin).
  - Số bản ghi cách ly: 142 dòng (122 employee_counts + 20 company_specialities).
- [ ] **Khớp nối thuật ngữ:**  
  Thống nhất cách gọi: Bảng `skills.csv` là *Job Functions*, không gọi là kỹ năng kỹ thuật; kỹ năng kỹ thuật là từ khóa trích xuất từ văn bản mô tả.
- [ ] **Rà soát câu hỏi phản biện:**  
  Từng thành viên đặt câu hỏi chất vấn chéo cho phần trình bày của hai thành viên còn lại theo bảng phân công Q&A.

---

## 2. Lượt Tổng duyệt 2: Thời lượng & Chuyển giao Phần nói (Round 2: Timing & Transitions)

*Mục tiêu: Đảm bảo tổng thời lượng thuyết trình trong khung 12–15 phút và chuyển giao trơn tru giữa 3 người.*

- [ ] **Khung thời gian TV1 (Mở đầu & Spark):** Bấm giờ chính xác $\le 5$ phút. Chuyển giao tự nhiên sang TV2 khi nhắc đến bước phân loại tin CNTT.
- [ ] **Khung thời gian TV2 (Taxonomy & Phân tích):** Bấm giờ chính xác $\le 5$ phút. Chuyển giao sang TV3 để trực quan hóa các kết quả phân tích trên giao diện.
- [ ] **Khung thời gian TV3 (Dashboard Demo & Kết luận):** Bấm giờ chính xác $\le 4$ phút. Thao tác chuột dứt khoát, nói tới đâu trỏ chuột tới đó.
- [ ] **Chuyển giao micro/màn hình:** Thao tác chuyển quyền chia sẻ màn hình (hoặc đứng lên bục thuyết trình) không làm gián đoạn quá 15 giây.

---

## 3. Kịch bản Xử lý Sự cố Kỹ thuật (Failure Recovery Protocol)

| Tình huống sự cố | Mức độ rủi ro | Biện pháp xử lý ngay lập tức |
| :--- | :---: | :--- |
| **1. Spark không chạy được trên máy hội đồng (Lỗi Java/Memory)** | Trung bình | **Giải pháp:** Dashboard Streamlit chỉ đọc các bảng tổng hợp sẵn (`data/analytics/`), **KHÔNG CẦN CHẠY SPARK** trong lúc demo. TV1 sử dụng ảnh chụp Spark UI và bảng benchmark đã đo trước để giải thích hiệu năng. |
| **2. Tệp Analytics bị mất hoặc lỗi đường dẫn** | Cao | **Giải pháp:** Bật ngay tùy chọn **"Enable Development Sample Mode"** tại thanh bên của Dashboard. Hệ thống sẽ tiếp tục hiển thị giao diện với dữ liệu mẫu nhỏ dự phòng. Người thuyết trình giải thích rõ đây là chế độ fallback dự phòng. |
| **3. Không có kết nối Internet tại phòng chấm** | Thấp | **Giải pháp:** Toàn bộ hệ thống chạy hoàn toàn ở chế độ ngoại tuyến (Localhost:8501). Bộ dữ liệu, thư viện Python và mã nguồn đều nằm cục bộ trên máy, không phụ thuộc cloud API. |
| **4. Máy tính khác bị lệch đường dẫn tuyệt đối** | Trung bình | **Giải pháp:** Mọi script và mô-đun trong dự án đều sử dụng đường dẫn tương đối tính từ `PROJECT_ROOT = Path(__file__).resolve().parent.parent`. Không hard-code đường dẫn ổ đĩa cố định. |
| **5. Máy tính hỏng đột xuất / Màn hình chiếu lỗi** | Rất cao | **Giải pháp Fallback cuối cùng:** Sử dụng thư mục ảnh chụp màn hình độ phân giải cao (`artifacts_backup/screenshots/`) đã chèn sẵn vào Slide hoặc phát video quay sẵn toàn bộ thao tác (`demo_recording.mp4`) từ điện thoại/máy phụ. |
