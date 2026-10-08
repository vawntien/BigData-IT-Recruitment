# Team Contribution Matrix Draft (Ma trận Đóng góp và Phân công Nhiệm vụ)

> [!NOTE]
> **TÀI LIỆU MINH CHỨNG ĐÓNG GÓP THỰC TẾ TRÊN REPOSITORY.**  
> Ma trận này ghi nhận chính xác tiến độ thực tế dựa trên các commit và artifact hiện có trong repository. Các mục chưa hoàn thành được đánh dấu rõ ràng là `PENDING` hoặc `TODO`, không ghi nhận khống kết quả.

---

## 1. Bảng Tổng hợp Nhiệm vụ theo Kế hoạch Đồ án (3 Thành viên)

| Mã Task | Tên nhiệm vụ | Người phụ trách chính | Người hỗ trợ | Sản phẩm bàn giao (Artifact) | Trạng thái thực tế | Bằng chứng kiểm tra trong Repo | Commit / Branch |
| :--- | :--- | :---: | :---: | :--- | :---: | :--- | :--- |
| **D01** | Chốt dữ liệu và phạm vi | **TV1** | TV2 | `README.md`, `docs/data_manifest.md` | ✅ **PASS** | Tệp mô tả 11 CSV, nguồn Kaggle, giấy phép CC BY-SA 4.0 | `main` |
| **D02** | Thiết lập môi trường Spark | **TV1** | TV3 | `docs/d02_environment_setup.md`, `src/smoke_test.py` | ✅ **PASS** | PySpark 4.2.0 local[*], smoke test đếm 123,849 dòng | `main` |
| **D03** | Kiểm kê và đọc dữ liệu | **TV1** | TV2 | `docs/d03_data_quality_report.md`, `data/audit/*.csv` | ✅ **PASS** | Hồ sơ 11 bảng thô, kiểm kê missingness, keys, Mojibake, orphans | `main` |
| **D04** | Làm sạch bằng Spark | **TV1** | TV2 | `docs/d04_cleaning_report.md`, `src/clean_data.py`, `data/processed/clean/` | ✅ **PASS** | 11 bảng Parquet sạch, 142 dòng cách ly tại `data/processed/rejected/` | `main` |
| **D05-Pre** | Tiền kiểm định Join & Scaffold | **TV1** | TV3 | `docs/d05_precheck.md`, `src/d05_utils.py`, `src/test_d05_scaffold.py` | ✅ **PASS** | Đo lường cardinality, guard chống row explosion, test suite 21.7s | `main` |
| **D05-Off** | JOIN tạo Canonical Dataset | **TV1** | TV2 | Bảng Parquet chuẩn hóa 1 dòng = 1 job | ⏸️ **BLOCKED** | Bị chặn do dependency A03 chưa hoàn thành | `main` |
| **D06** | Tích hợp bộ lọc CNTT | **TV1** | TV2 | `it_jobs.parquet` gắn nhãn nhóm nghề | 🔴 **PENDING** | Chờ D05 official và taxonomy từ A02/A04 | — |
| **D07** | Chuẩn hóa mức lương | **TV1** | TV2 | `salary_clean.parquet` | 🔴 **PENDING** | Chờ D06 hoàn thành | — |
| **D08** | Đánh giá hiệu năng Spark | **TV1** | TV3 | Bảng benchmark thời gian, partitions | 🔴 **PENDING** | Chờ hoàn thành toàn bộ pipeline ETL | — |
| **D09** | Kiểm thử dữ liệu đầu ra | **TV1** | TV2, TV3 | Script kiểm tra hồi quy toàn diện | 🔴 **PENDING** | Chờ hoàn thành D07 | — |
| **D10** | Viết phần dữ liệu & phương pháp | **TV1** | TV2, TV3 | `docs/report/data_methodology_draft.md` | 🟡 **DRAFT** | Đã viết bản thảo chi tiết D01–D04 và D05 scaffold | `main` |
| **D11** | Đóng gói pipeline và thuyết trình | **TV1** | TV3 | Kịch bản trình bày phần kỹ thuật dữ liệu | 🔴 **PENDING** | Chờ tổng duyệt cuối kỳ V11 | — |
| **A01** | Khảo sát thuộc tính phân tích | **TV2** | TV1 | Ma trận câu hỏi – trường dữ liệu | ⏳ **TODO** | Đang thực hiện bởi TV2 | — |
| **A02** | Thiết kế taxonomy CNTT | **TV2** | TV1 | Tài liệu quy tắc phân nhóm nghề CNTT | ⏳ **TODO** | Đang thực hiện bởi TV2 | — |
| **A03** | Khảo sát skills & industries | **TV2** | TV1 | Bản đồ JOIN và chiến lược nguồn kỹ năng | ⏳ **CRITICAL** | Đang chờ bàn giao để mở khóa D05 | — |
| **A04** | Kiểm tra bộ lọc CNTT mẫu | **TV2** | TV1 | Mẫu đánh giá 100–200 tin gán nhãn | 🔴 **PENDING** | Chờ A02 & A03 | — |
| **A05** | Trích xuất kỹ năng từ mô tả | **TV2** | TV1 | `job_skill_technical.parquet` | 🔴 **PENDING** | Chờ D06 | — |
| **A06** | Phân tích cơ cấu tuyển dụng | **TV2** | TV3 | Bảng analytics cơ cấu việc làm | 🔴 **PENDING** | Chờ D06 | — |
| **A07** | Phân tích nhu cầu kỹ năng | **TV2** | TV3 | Bảng `skills_analytics` | 🔴 **PENDING** | Chờ A05 | — |
| **A08** | Phân tích lương & thời gian | **TV2** | TV1 | Bảng `salary_analytics` | 🔴 **PENDING** | Chờ D07 | — |
| **A09** | Đối soát & viết nhận xét | **TV2** | TV3 | 5–8 nhận xét phân tích có số liệu | 🔴 **PENDING** | Chờ A07 & A08 | — |
| **A10** | Viết chương phân tích kết quả | **TV2** | TV1 | Chương kết quả phân tích trong báo cáo | 🔴 **PENDING** | Chờ A09 | — |
| **A11** | Chuẩn bị slide phân tích | **TV2** | TV3 | Slide và kịch bản phần nghiệp vụ | 🔴 **PENDING** | Chờ A10 | — |
| **V01** | Thiết kế dashboard & wireframe | **TV3** | TV2 | `docs/dashboard/dashboard_wireframe.md` | 🟡 **SCAFFOLD** | Đã dựng wireframe và bố cục chi tiết 3 trang | `support/tv3-dashboard-scaffold` |
| **V02** | Thiết lập ứng dụng Streamlit | **TV3** | TV1 | `dashboard/app.py`, `dashboard/pages/` | 🟡 **SCAFFOLD** | Đã dựng ứng dụng đa trang và sample mode dự phòng | `support/tv3-dashboard-scaffold` |
| **V03** | Chốt hợp đồng dữ liệu đầu ra | **TV3** | TV1, TV2 | `docs/dashboard/dashboard_data_contract_draft.md` | 🟡 **DRAFT** | Đã định hình cấu trúc dữ liệu dự kiến 3 bảng | `support/tv3-dashboard-scaffold` |
| **V04** | Trang cơ cấu tuyển dụng | **TV3** | TV2 | `dashboard/pages/1_Overview.py` | 🟡 **SCAFFOLD** | Giao diện đã sẵn sàng, đang chờ dữ liệu thật A06 | `support/tv3-dashboard-scaffold` |
| **V05** | Trang phân tích kỹ năng | **TV3** | TV2 | `dashboard/pages/2_Skills.py` | 🟡 **SCAFFOLD** | Giao diện đã sẵn sàng, đang chờ dữ liệu thật A07 | `support/tv3-dashboard-scaffold` |
| **V06** | Trang lương & chất lượng | **TV3** | TV1 | `dashboard/pages/3_Salary_Quality.py` | 🟡 **SCAFFOLD** | Giao diện đã sẵn sàng, đang chờ dữ liệu thật D07 | `support/tv3-dashboard-scaffold` |
| **V07** | Tích hợp và kiểm thử dashboard | **TV3** | TV1 | `dashboard_test_checklist.md`, `dashboard/tests/` | 🟡 **PREPARED** | Đã hoàn thành 2 bộ test tự động và checklist kiểm thử | `support/tv3-dashboard-scaffold` |
| **V08** | Hướng dẫn sử dụng dashboard | **TV3** | TV1 | `docs/dashboard/dashboard_user_guide_draft.md` | 🟡 **DRAFT** | Đã biên soạn bản thảo hướng dẫn chi tiết | `support/tv3-dashboard-scaffold` |
| **V09** | Đóng gói bản demo & kịch bản | **TV3** | TV1 | `demo_package_plan.md`, `demo_script_draft.md` | 🟡 **PREPARED** | Đã hoàn thành kế hoạch đóng gói và kịch bản thuyết trình | `support/tv3-dashboard-scaffold` |
| **V10** | Tổng hợp báo cáo & slide | **TV3** | TV1, TV2 | `report_integration_outline.md`, `presentation_outline.md` | 🟡 **DRAFT** | Đã hoàn thành đề cương 16 chương báo cáo và 14 slide | `support/tv3-dashboard-scaffold` |
| **V11** | Tổng duyệt và nộp bài | **TV3** | TV1, TV2 | `final_submission_checklist.md`, `rehearsal_checklist.md` | 🟡 **PREPARED** | Đã chuẩn bị đầy đủ checklist kiểm tra nộp bài và tổng duyệt | `support/tv3-dashboard-scaffold` |
