# Handoff Guide: Dashboard Development Kit (Dành cho TV3)

Tài liệu này là chỉ dẫn kỹ thuật trực tiếp dành cho **Thành viên 3 (TV3 - Phụ trách Dashboard & Trực quan hóa)** để bắt đầu phát triển giao diện người dùng mà không bị nghẽn bởi tiến độ của pipeline dữ liệu lớn.

---

## 1. TV3 Bắt đầu từ đâu?

1. **Khởi động môi trường:** Dự án sử dụng môi trường ảo Python 3.11 tại `.venv`. Thư viện `streamlit==1.38.0` đã được cài đặt sẵn.
2. **Khám phá mã nguồn:**
   - Điểm bắt đầu: [dashboard/app.py](file:///d:/Learning/Bigdata/BigData-IT-Recruitment/dashboard/app.py)
   - Thư mục trang: [dashboard/pages/](file:///d:/Learning/Bigdata/BigData-IT-Recruitment/dashboard/pages/)
   - Thư mục component: [dashboard/components/](file:///d:/Learning/Bigdata/BigData-IT-Recruitment/dashboard/components/)
   - Dữ liệu mẫu thử nghiệm: [dashboard/sample_data/](file:///d:/Learning/Bigdata/BigData-IT-Recruitment/dashboard/sample_data/)

---

## 2. Lệnh Chạy Ứng dụng (Run Command)

Mở terminal PowerShell tại thư mục gốc của repository (`d:\Learning\Bigdata\BigData-IT-Recruitment`) và chạy:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py
```

Ứng dụng sẽ tự động mở tại trình duyệt tại địa chỉ cục bộ: `http://localhost:8501`.

---

## 3. Chế độ Phát triển Dữ liệu Mẫu (Sample Development Mode)

- **Tại sao cần Sample Mode?** Hiện tại, các bảng tính toán chính thức chưa được tạo ra bởi pipeline Big Data (do đang chờ TV2 hoàn thành task A03 để mở khóa D05). Để TV3 không phải chờ đợi, hệ thống đã cung cấp các tệp dữ liệu giả định nhỏ tại `dashboard/sample_data/`.
- **Cơ chế hoạt động:**
  - Trong thanh Sidebar bên trái có tùy chọn **"Enable Development Sample Mode"** (mặc định bật).
  - Khi bật, bộ nạp dữ liệu (`data_loader.py`) sẽ đọc các tệp mẫu nhỏ (15–25 dòng) để render đầy đủ KPI và biểu đồ.
  - Khi tắt (hoặc khi chưa có dữ liệu thật), màn hình sẽ thông báo trạng thái thiếu dữ liệu một cách an toàn mà **KHÔNG BỊ CRASH**.

---

## 4. Dữ liệu Sản xuất (Production Data) sau này nằm ở đâu?

Khi pipeline của TV1 và TV2 chạy xong, các tệp dữ liệu tổng hợp chính thức sẽ được ghi tự động vào thư mục:

```text
data/analytics/
    overview_analytics.parquet (hoặc .csv)
    skills_analytics.parquet (hoặc .csv)
    salary_quality_analytics.parquet (hoặc .csv)
```

Bộ nạp dữ liệu `dashboard/components/data_loader.py` đã được lập trình sẵn để tự động ưu tiên nhận diện và đọc dữ liệu từ `data/analytics/` ngay khi tệp xuất hiện. Khi đó, banner cảnh báo trên giao diện sẽ tự động chuyển từ màu vàng (Sample Mode) sang màu xanh lá (**Production Data Active**).

---

## 5. Phân định Quyền chỉnh sửa Tệp (File Permission & Responsibilities)

### ✅ Các tệp TV3 ĐƯỢC PHÉP và NÊN chỉnh sửa:
- Toàn bộ thư mục `dashboard/pages/`:
  - `1_Overview.py` (tùy biến biểu đồ, bố cục màu sắc, cách hiển thị KPI).
  - `2_Skills.py` (thêm bộ lọc tìm kiếm kỹ năng, biểu đồ mạng lưới hoặc bảng ma trận).
  - `3_Salary_Quality.py` (bổ sung boxplot, so sánh kỳ lương).
- `dashboard/app.py`: Tùy chỉnh thông điệp chào mừng và thông tin nhóm.
- `dashboard/components/filters.py` & `ui_helpers.py`: Tối ưu hóa giao diện người dùng.
- `docs/dashboard/`: Đề xuất cập nhật wireframe hoặc phản hồi về hợp đồng dữ liệu.

### ⛔ Các tệp TV3 KHÔNG NÊN chỉnh sửa (Tránh gây xung đột Git):
- `src/`: Thư mục mã nguồn pipeline PySpark của TV1 (`clean_data.py`, `d05_utils.py`, v.v.).
- `data/raw/` & `data/processed/`: Dữ liệu gốc và dữ liệu sạch của hệ thống Big Data.
- `docs/d02_*.md`, `docs/d03_*.md`, `docs/d04_*.md`, `docs/d05_*.md`: Các báo cáo kỹ thuật đã được nghiệm thu của TV1.

---

## 6. Các Phụ thuộc Đang chờ (Pending Dependencies)

| Trang Dashboard | Dữ liệu chính thức cần nhận | Task phụ thuộc | Thành viên phụ trách |
| :--- | :--- | :---: | :---: |
| **1_Overview** | `overview_analytics` | **A06** (Phân tích cơ cấu) | TV2 |
| **2_Skills** | `skills_analytics` | **A05 & A07** (Trích xuất & phân tích kỹ năng) | TV2 |
| **3_Salary_Quality** | `salary_quality_analytics` | **D07 & A08** (Chuẩn hóa lương) | TV1 & TV2 |

---

## 7. Khuyến nghị cho TV3

1. Không cần chờ dữ liệu thật, TV3 có thể tập trung thiết kế các biểu đồ đẹp mắt, chọn bảng màu phù hợp và hoàn thiện trải nghiệm lọc dữ liệu trên Streamlit ngay bây giờ bằng tập dữ liệu mẫu.
2. Đọc bản thảo hợp đồng dữ liệu tại [dashboard_data_contract_draft.md](file:///d:/Learning/Bigdata/BigData-IT-Recruitment/docs/dashboard/dashboard_data_contract_draft.md) để nắm được các cột dữ liệu sắp tới mà TV1 và TV2 sẽ cung cấp.
