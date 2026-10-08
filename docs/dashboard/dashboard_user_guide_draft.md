# Dashboard User Guide (Bản thảo Hướng dẫn Sử dụng)

> [!NOTE]
> **TÀI LIỆU NÀY LÀ BẢN THẢO (DRAFT USER GUIDE) PHỤC VỤ NHIỆM VỤ V08.**  
> Trạng thái: **DRAFT – FINAL V08 PENDING**. Được biên soạn để hướng dẫn các thành viên trong nhóm và người đánh giá cách cài đặt, sử dụng và kiểm soát giao diện trực quan hóa.

---

## 1. Cài đặt Môi trường (Installation)

Dự án sử dụng môi trường ảo Python 3.11 tại thư mục `.venv`.  
Để cài đặt đầy đủ các gói phụ thuộc phục vụ giao diện Streamlit:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 2. Khởi chạy Dashboard (Start Dashboard)

Tại thư mục gốc của repository (`D:\Learning\Bigdata\BigData-IT-Recruitment`), thực hiện một trong hai cách:

### Cách 1: Sử dụng script tự động
```powershell
.\scripts\run_dashboard.ps1
```

### Cách 2: Lệnh trực tiếp qua Python module
```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py
```

Ứng dụng sẽ tự động mở giao diện web tại địa chỉ: `http://localhost:8501`.

---

## 3. Cấu trúc Các Trang (Pages Navigation)

Sử dụng thanh điều hướng bên trái (Sidebar) để chuyển giữa 3 trang phân tích chuyên biệt:
- **`1_Overview`**: Cơ cấu việc làm theo nhóm nghề CNTT, cấp bậc kinh nghiệm, địa điểm và hình thức làm việc.
- **`2_Skills`**: Xếp hạng các kỹ năng kỹ thuật có nhu cầu cao nhất và so sánh nhu cầu kỹ năng giữa các nhóm nghề.
- **`3_Salary_Quality`**: Khảo sát mức lương tuyển dụng (USD/Năm) và theo dõi các chỉ số chất lượng dữ liệu của pipeline.

---

## 4. Hướng dẫn Sử dụng Bộ lọc (Filters)

Thanh bên trái cung cấp các bộ lọc đa lựa chọn (multiselect):
- **Job Category:** Cho phép tập trung vào một hoặc nhiều nhóm nghề cụ thể (`Software Engineering`, `Data & AI`, `Cloud & DevOps`...).
- **Experience Level:** Lọc theo cấp bậc (`Entry level`, `Mid-Senior level`, `Associate`...).
- **Location:** Lọc theo địa điểm làm việc.
- *Lưu ý về tổ hợp rỗng:* Nếu chọn một tổ hợp tiêu chí không có tin tuyển dụng nào, hệ thống sẽ hiển thị thông báo màu vàng hướng dẫn nới lỏng bộ lọc thay vì báo lỗi.

---

## 5. Chế độ Dữ liệu Thật vs Dữ liệu Mẫu (Production vs Sample Mode)

- **Chế độ Mẫu (Sample Development Mode):** Tùy chọn `Enable Development Sample Mode` trong thanh bên cho phép nạp các tệp dữ liệu giả định nhỏ tại `dashboard/sample_data/`. Chế độ này dùng để phát triển và kiểm tra layout UI khi pipeline phía trên chưa xuất xưởng dữ liệu. Banner màu vàng cảnh báo sẽ xuất hiện trên đầu mỗi trang.
- **Chế độ Dữ liệu Thật (Production Mode):** Khi các tệp analytics chính thức xuất hiện tại `data/analytics/`, ứng dụng tự động ưu tiên nạp dữ liệu thật và chuyển banner sang màu xanh lá (`PRODUCTION DATA ACTIVE`).

---

## 6. Đọc và Diễn giải Các Chỉ số KPI (Reading KPIs)

- **Tổng số tin tuyển dụng (Total Jobs):** Phản ánh tổng số lượng tin tuyển dụng thỏa mãn các tiêu chí lọc đang được chọn.
- **Nhóm nghề hàng đầu & Địa điểm nhiều nhất:** Tự động tính toán nhóm nghề và địa điểm chiếm tỷ trọng cao nhất trong tập dữ liệu đang lọc.
- **Độ phủ thông tin lương:** Đo lường tỷ lệ các tin tuyển dụng có công bố thông tin lương cấu trúc (đạt mức chuẩn 29.13% trên toàn bộ tập dữ liệu).

---

## 7. Hướng dẫn Đọc Trang Kỹ năng (Reading Skills Page)

- **Cảnh báo nguồn dữ liệu:** Kỹ năng kỹ thuật cụ thể (như Python, SQL, AWS) được trích xuất từ văn bản trường `description`. Các mã 2-4 ký tự trong dữ liệu gốc (`skills.csv`) chỉ là nhóm nghề tổng quát.
- **Biểu đồ Top Skills:** Thể hiện 15 kỹ năng được yêu cầu nhiều nhất.
- **Bảng tần suất:** Hiển thị rõ số lượng tin yêu cầu và tỷ lệ phần trăm tương ứng trên tổng số tin của nhóm nghề làm mẫu số (`sample_size`).

---

## 8. Hướng dẫn Đọc Trang Lương (Reading Salary Page)

- **Nguyên tắc phân nhóm:** Để đảm bảo tính chính xác khoa học, dashboard chỉ so sánh mức lương trong cùng đơn vị tiền tệ (`USD`) và cùng kỳ trả lương (`YEARLY`).
- **Mức lương trung vị (Median):** Sử dụng giá trị trung vị thay vì trung bình để tránh ảnh hưởng bởi các giá trị ngoại lai (outliers).
- **Dải lương:** Cung cấp khoảng dải từ mức lương tối thiểu (Min) đến tối đa (Max).

---

## 9. Trang Giám sát Chất lượng Dữ liệu (Data Quality Page)

Phục vụ việc chứng minh tính minh bạch và độ tin cậy của quy trình xử lý Big Data:
- Thống kê tỷ lệ khuyết thiếu của 16 trường dữ liệu có tỷ lệ thiếu $\ge 20\%$.
- Thống kê 142 bản ghi bị cách ly (quarantined records) khỏi tập dữ liệu sạch để đảm bảo tính duy nhất của khóa.
- Thống kê các khóa ngoại mồ côi (orphan records) giữa các bảng con và bảng cha.

---

## 10. Các Lỗi Thường Gặp và Cách Xử lý (Common Errors)

| Hiện tượng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| `Analytics data is not available yet` | Chưa có dữ liệu thật trong `data/analytics/` và Sample Mode đang tắt | Bật tùy chọn `Enable Development Sample Mode` ở sidebar hoặc chạy pipeline ETL. |
| `ModuleNotFoundError: No module named 'streamlit'` | Chưa cài đặt gói Streamlit trong môi trường ảo | Chạy lệnh `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. |
| Cảnh báo `Không tìm thấy bản ghi nào...` | Tổ hợp bộ lọc người dùng chọn không có dữ liệu giao thoa | Bấm chọn lại các ô lọc ở thanh bên trái hoặc bấm F5 để reset. |
| Banner vàng xuất hiện liên tục | Đang hiển thị dữ liệu giả định | Đây là hành vi bình thường trong giai đoạn phát triển scaffold. |

---

## 11. Hướng dẫn Dành cho Người Phát triển (Developer Mode)

- Mã nguồn các trang nằm tại `dashboard/pages/`.
- Mã nguồn bộ nạp dữ liệu nằm tại `dashboard/components/data_loader.py`.
- Bộ kiểm tra hợp đồng dữ liệu nằm tại `dashboard/components/contract_validator.py`.
- Bộ test tự động có thể chạy qua:
  ```powershell
  .\.venv\Scripts\python.exe dashboard\tests\test_data_loader.py
  .\.venv\Scripts\python.exe dashboard\tests\test_sample_contracts.py
  ```

---

## 12. Ghi chú Phục vụ Buổi Thuyết trình / Demo Cuối kỳ (Final Demo Notes)

- Luôn kiểm tra môi trường bằng `.\scripts\check_dashboard_env.ps1` trước giờ demo.
- Khi thuyết trình, chuyển qua Tab Data Quality để giải thích cách Spark làm sạch dữ liệu trước khi đi sâu vào phân tích các biểu đồ tuyển dụng.
