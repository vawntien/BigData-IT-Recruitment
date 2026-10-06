# Demo Package Plan (Kế hoạch Đóng gói Demo V09)

Tài liệu này xác định cấu trúc đóng gói sản phẩm chuyển giao (demo package) phục vụ nghiệm thu nhiệm vụ **V09** và bảo vệ đồ án **V11**.

---

## 1. Mục tiêu Gói Demo (Demo Package Goal)

Đảm bảo bất kỳ thành viên nào trong hội đồng chấm hoặc người đánh giá độc lập có thể:
1. Giải nén gói mã nguồn trên một máy tính Windows mới.
2. Cài đặt môi trường chỉ với một lệnh.
3. Khởi chạy dashboard phân tích và xem đầy đủ kết quả thực tế mà không gặp lỗi thiếu phụ thuộc hay lỗi đường dẫn.

---

## 2. Thành phần Cấu thành Gói Đóng gói (Package Contents)

Gói demo cuối kỳ (`release_demo_bundle.zip`) sẽ bao gồm các thành phần sau:

```text
release_demo_bundle/
├── README_DEMO.md                  # Hướng dẫn khởi chạy nhanh 1 bước
├── requirements.txt                # Danh sách thư viện Python chuẩn (pyspark, streamlit, v.v.)
├── scripts/
│   ├── run_dashboard.ps1           # Script PowerShell khởi chạy tự động
│   └── check_dashboard_env.ps1     # Script kiểm tra nhanh môi trường
├── dashboard/                      # Toàn bộ mã nguồn ứng dụng Streamlit
│   ├── app.py
│   ├── pages/
│   ├── components/
│   └── sample_data/                # Dữ liệu dự phòng nếu mất kết nối
├── data/
│   └── analytics/                  # Các tệp Parquet/CSV tổng hợp chính thức từ Spark
│       ├── overview_analytics.parquet
│       ├── skills_analytics.parquet
│       └── salary_quality_analytics.parquet
├── docs/
│   ├── dashboard/
│   │   ├── dashboard_user_guide_draft.md
│   │   └── demo_script_draft.md
│   └── report/
│       └── data_methodology_draft.md
└── artifacts_backup/               # Minh chứng dự phòng (Backup Media)
    ├── screenshots/                # Ảnh chụp màn hình từng trang ứng dụng
    └── demo_recording.mp4          # Video ghi hình buổi chạy thử dự phòng
```

---

## 3. Metadata và Định danh Phiên bản (Version & Provenance)

Mỗi gói demo xuất xưởng phải kèm theo tệp `VERSION.json` ghi nhận chính xác nguồn gốc:

| Thông số | Giá trị định danh dự kiến | Ghi chú |
| :--- | :--- | :--- |
| **Project Name** | BigData-IT-Recruitment | Đồ án Big Data Tuyển dụng CNTT |
| **Pipeline Version** | 1.0.0-release | Phiên bản pipeline ổn định |
| **Git Commit Hash** | `[COMMIT_HASH_TAI_THOI_DIEM_DONG_GOI]` | Mã băm commit của Git |
| **Dataset Version** | LinkedIn Job Postings 2023-2024 (Arsh Koneru) | 123,849 tin tuyển dụng |
| **Spark Engine** | Apache Spark / PySpark 4.2.0 | Chế độ `local[*]` |
| **Python / Java** | Python 3.11 / OpenJDK 21 LTS | Phiên bản môi trường chuẩn |

---

## 4. Phương án Dự phòng Rủi ro (Risk Mitigation Strategy)

1. **Rủi ro máy hội đồng chấm không có Java/Spark:**  
   Dashboard Streamlit được thiết kế để đọc các bảng tổng hợp sẵn (`data/analytics/`) mà **KHÔNG CẦN CHẠY LẠI SPARK**. Do đó máy demo chỉ cần Python 3.11 và Streamlit.
2. **Rủi ro hỏng tệp analytics hoặc lỗi hiển thị đột xuất:**  
   Bật ngay tùy chọn **"Enable Development Sample Mode"** tại thanh bên để ứng dụng tiếp tục trình diễn giao diện với dữ liệu mẫu nhỏ dự phòng.
3. **Rủi ro lỗi máy tính không thể bật ứng dụng:**  
   Chuẩn bị sẵn thư mục `artifacts_backup/screenshots/` và video quay lại toàn bộ thao tác (`demo_recording.mp4`) để trình chiếu qua Slide.
