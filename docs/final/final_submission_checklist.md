# Final Submission Checklist (Bảng Kiểm tra Nghiệm thu Gói Nộp Bài)

Bảng kiểm tra toàn diện này phục vụ quá trình tổng duyệt cuối kỳ và đóng gói hồ sơ nộp bài (**Nhiệm vụ V11**).

---

## Danh mục Kiểm tra Chi tiết (Comprehensive Checklist)

| Nhóm kiểm tra | Tiêu chí kiểm tra | Hướng dẫn kiểm chứng | Trạng thái hiện tại |
| :--- | :--- | :--- | :---: |
| **1. Quản lý Git & Mã nguồn** | Không commit tệp dữ liệu thô | Kiểm tra `git status`: `data/raw/` không xuất hiện trên Git | ✅ **ĐẠT** |
| | Không commit môi trường ảo | Kiểm tra `git status`: `.venv/` không xuất hiện trên Git | ✅ **ĐẠT** |
| | Cây thư mục sạch (Working tree clean) | Không có tệp thừa ngoài ý muốn trước khi đóng gói | ⏳ Chờ tổng duyệt |
| | Ghi nhận Commit Hash chính thức | Lưu mã băm Git commit cuối cùng vào gói nộp bài | ⏳ Chờ commit cuối |
| **2. Dữ liệu & Môi trường** | Hướng dẫn tải và cấu trúc dataset | `README.md` và `data_manifest.md` mô tả rõ 11 tệp CSV | ✅ **ĐẠT** |
| | Môi trường ảo Python chuẩn hóa | `requirements.txt` ghi rõ `pyspark==4.2.0` và `streamlit==1.38.0` | ✅ **ĐẠT** |
| | Không phụ thuộc `winutils.exe` | Đã tích hợp adapter Java `d04-localfs-adapter.jar` trong mã nguồn | ✅ **ĐẠT** |
| | Kiểm thử trên máy tính độc lập | Đã chạy thử nghiệm trên máy của thành viên khác theo README | ⏳ Chờ tổng duyệt V11 |
| **3. Pipeline Spark & Dữ liệu sạch** | Kiểm kê dữ liệu thô D03 | Có báo cáo `d03_data_quality_report.md` và hồ sơ audit CSV | ✅ **ĐẠT** |
| | Làm sạch và chuẩn hóa D04 | Bảng Parquet sạch tại `data/processed/clean/` khớp 100% số dòng | ✅ **ĐẠT** |
| | Không nhân bản dòng D05 | Đã áp dụng `aggregate-before-join` và `latest_per_key` | ✅ **ĐẠT** |
| | Phân loại tin tuyển dụng CNTT D06 | Đã áp dụng bộ lọc CNTT và lưu trữ nhãn nghề nghiệp | 🔴 Chờ TV2 (A03/D06) |
| | Chuẩn hóa lương D07 | Đã chuẩn hóa kỳ lương và xử lý đơn vị tiền tệ hợp lệ | 🔴 Chờ D07 |
| | Đánh giá hiệu năng D08 | Có bảng benchmark và thời gian thực thi Spark | 🔴 Chờ D08 |
| **4. Dữ liệu Đầu ra Analytics** | Thư mục `data/analytics/` | Chứa đầy đủ 3 bảng tổng hợp (`overview`, `skills`, `salary`) | 🔴 Chờ A06–A08 |
| | Không dùng số liệu giả làm kết luận | Tuyệt đối không đưa số liệu từ `sample_data/` vào báo cáo chính thức | ✅ **ĐẠT** (Đã cấm triệt để) |
| | Đối soát số liệu nhất quán (Reconciliation) | Mọi số liệu trong báo cáo, slide và dashboard phải khớp 100% | ⏳ Chờ điền metrics |
| **5. Giao diện Dashboard (TV3)** | Khởi chạy 1 lệnh duy nhất | Chạy thành công qua `.\scripts\run_dashboard.ps1` | ✅ **ĐẠT** |
| | Không crash khi thiếu dữ liệu | Có cơ chế bắt lỗi thân thiện và tự động kiểm tra contract | ✅ **ĐẠT** |
| | Có đủ 3 trang phân tích | Trang Overview, Trang Kỹ năng, Trang Mức lương & Chất lượng | ✅ **ĐẠT** |
| | Bộ lọc hoạt động ổn định | Đã xử lý trường hợp tổ hợp bộ lọc không có dữ liệu giao thoa | ✅ **ĐẠT** |
| **6. Kiểm thử Tự động (Tests)** | Kiểm thử Spark Scaffold | `src/test_d05_scaffold.py` chạy đạt 100% (21.7s) | ✅ **ĐẠT** |
| | Kiểm thử Dashboard Components | `test_data_loader.py` & `test_sample_contracts.py` đạt 100% | ✅ **ĐẠT** |
| | Kiểm thử Môi trường hệ thống | `scripts\check_dashboard_env.ps1` báo cáo ALL CHECKS PASSED | ✅ **ĐẠT** |
| **7. Tài liệu & Slide Báo cáo** | Báo cáo Tổng kết Đồ án (Report) | Đầy đủ 16 chương theo `report_integration_outline.md` | ⏳ Chờ tổng hợp V10 |
| | Slide Thuyết trình (Presentation) | Đầy đủ 14 slide theo `presentation_outline.md` | ⏳ Chờ tổng hợp V10 |
| | Trích dẫn nguồn và bản quyền | Ghi rõ nguồn Kaggle, giấy phép CC BY-SA 4.0 và tài liệu Spark | ✅ **ĐẠT** |
| | Minh chứng đóng góp của nhóm | Có bảng ma trận đóng góp phân chia rõ ràng trách nhiệm 3 người | ✅ **ĐẠT** |
| **8. Gói Demo & Phương án Dự phòng** | Kịch bản thuyết trình demo | Có kịch bản 3–5 phút chi tiết từng bước (`demo_script_draft.md`) | ✅ **ĐẠT** |
| | Ảnh chụp màn hình dự phòng | Có thư mục ảnh chụp màn hình các trang giao diện | ⏳ Chờ chụp UI thật |
| | Video ghi hình dự phòng | Có video chạy demo dự phòng khi máy gặp sự cố kết nối | ⏳ Chờ quay video V09 |
| | Quy chuẩn đặt tên tệp gói nộp | Tệp nộp đặt tên đúng quy định: `NhomXX_BigData_IT_Recruitment.zip` | ⏳ Chờ đóng gói V11 |
