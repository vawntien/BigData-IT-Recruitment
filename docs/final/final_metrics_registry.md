# Final Metrics Registry (Sổ bộ Đo lường và Thống nhất Số liệu)

> [!IMPORTANT]
> **NGUỒN SỰ THẬT DUY NHẤT (SINGLE SOURCE OF TRUTH) CHO TOÀN BỘ SỐ LIỆU.**  
> Bảng này quản lý tập trung mọi chỉ số định lượng được phép sử dụng trong Báo cáo cuối kỳ, Slide thuyết trình và Streamlit Dashboard.  
> - **Chỉ những chỉ số có `allowed_in_final = YES` mới được phép đưa vào nội dung chính thức.**  
> - **Các chỉ số `allowed_in_final = NO` (đang là `TODO` hoặc dữ liệu mẫu `SYNTHETIC_SAMPLE`) tuyệt đối không được dùng làm kết luận.**

---

## Bảng Tra cứu Số liệu Chuẩn hóa Toàn dự án

| metric_id | metric_name | value | unit | source_artifact | source_task | status | allowed_in_final | notes |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **M01** | raw_postings_count | 123,849 | rows | `d03_data_quality_report.md` | D03 | VERIFIED | **YES** | Số dòng thô ban đầu của postings.csv |
| **M02** | raw_companies_count | 24,473 | rows | `d03_data_quality_report.md` | D03 | VERIFIED | **YES** | Số dòng thô của companies.csv |
| **M03** | raw_total_files | 11 | files | `data_manifest.md` | D01 | VERIFIED | **YES** | Tổng số tệp CSV trong bộ dữ liệu gốc |
| **M04** | raw_dataset_size | 530.72 | MB | `data_manifest.md` | D01 | VERIFIED | **YES** | Tổng dung lượng tệp thô trên đĩa |
| **M05** | postings_distinct_job_id | 123,849 | keys | `d03_data_quality_report.md` | D03 | VERIFIED | **YES** | Khóa chính job_id duy nhất tuyệt đối |
| **M06** | postings_candidate_key_nulls | 0 | nulls | `d03_data_quality_report.md` | D03 | VERIFIED | **YES** | Không có NULL trong khóa chính job_id |
| **M07** | clean_postings_count | 123,849 | rows | `d04_cleaning_report.md` | D04 | VERIFIED | **YES** | Bảo toàn trọn vẹn 100% sau làm sạch |
| **M08** | employee_counts_rejected_rows | 122 | rows | `d04_cleaning_report.md` | D04 | VERIFIED | **YES** | Trùng lặp (company_id, time_recorded) |
| **M09** | company_specialities_rejected_rows | 20 | rows | `d04_cleaning_report.md` | D04 | VERIFIED | **YES** | Trùng lặp (company_id, speciality) |
| **M10** | total_quarantined_rejected_rows | 142 | rows | `d04_cleaning_report.md` | D04 | VERIFIED | **YES** | Lưu trữ tại data/processed/rejected/ |
| **M11** | mojibake_cells_repaired | 83 | cells | `d04_cleaning_report.md` | D04 | VERIFIED | **YES** | 1 title, 79 post_desc, 3 comp_desc |
| **M12** | clean_salaries_rows | 40,785 | rows | `d04_cleaning_report.md` | D04 | VERIFIED | **YES** | Tổng số dòng bảng salaries sạch |
| **M13** | postings_with_salary_count | 36,073 | postings | `d05_precheck.md` | D05-Pre | VERIFIED | **YES** | Tin có bản ghi lương trong salaries |
| **M14** | postings_salary_coverage_rate | 29.13 | % | `d05_precheck.md` | D05-Pre | VERIFIED | **YES** | 36,073 / 123,849 tin tuyển dụng |
| **M15** | orphan_salaries_rows | 4,712 | rows | `d05_precheck.md` | D05-Pre | VERIFIED | **YES** | job_id trong salaries không có ở postings |
| **M16** | orphan_job_skills_rows | 7,990 | rows | `d05_precheck.md` | D05-Pre | VERIFIED | **YES** | job_id trong job_skills không có ở postings |
| **M17** | orphan_job_industries_rows | 5,845 | rows | `d05_precheck.md` | D05-Pre | VERIFIED | **YES** | job_id trong job_industries mồ côi |
| **M18** | orphan_benefits_rows | 2,550 | rows | `d05_precheck.md` | D05-Pre | VERIFIED | **YES** | job_id trong benefits mồ côi |
| **M19** | clean_skills_categories_count | 35 | categories | `d05_precheck.md` | D05-Pre | VERIFIED | **YES** | 35 nhãn chức năng công việc (Job Functions) |
| **M20** | clean_industries_count | 422 | industries | `d05_precheck.md` | D05-Pre | VERIFIED | **YES** | 422 mã ngành LinkedIn chuẩn hóa |
| **M21** | companies_with_multi_snapshots | 5,694 | companies | `d05_precheck.md` | D05-Pre | VERIFIED | **YES** | Công ty có >1 snapshot nhân sự (tối đa 13) |
| **M22** | latest_employee_counts_rows | 24,473 | rows | `test_d05_scaffold.py` | D05-Scaffold | VERIFIED | **YES** | Đúng 1 snapshot mới nhất cho mỗi công ty |
| **M23** | flat_unaggregated_join_rows | 207,531 | rows | `test_d05_scaffold.py` | D05-Scaffold | VERIFIED | **YES** | Kết quả thực nghiệm row explosion |
| **M24** | flat_join_row_inflation | +83,682 | rows | `test_d05_scaffold.py` | D05-Scaffold | VERIFIED | **YES** | Số dòng bị nhân bản do flat join |
| **M25** | safe_join_postings_rows | 123,849 | rows | `test_d05_scaffold.py` | D05-Scaffold | VERIFIED | **YES** | Bảo toàn tuyệt đối 1 dòng = 1 job |
| **M26** | safe_join_distinct_job_id | 123,849 | keys | `test_d05_scaffold.py` | D05-Scaffold | VERIFIED | **YES** | 0 trùng lặp, 0 mất mát khóa chính |
| **M27** | it_postings_total_count | `TODO` | rows | *Chờ D06* | D06 | PENDING | **NO** | Chưa lọc tin CNTT chính thức |
| **M28** | it_postings_ratio | `TODO` | % | *Chờ D06* | D06 | PENDING | **NO** | Tỷ lệ tin CNTT trên tổng tập dữ liệu |
| **M29** | top_skill_1_name | `TODO` | name | *Chờ A07* | A07 | PENDING | **NO** | Tên kỹ năng kỹ thuật xếp thứ 1 |
| **M30** | top_skill_1_frequency | `TODO` | % | *Chờ A07* | A07 | PENDING | **NO** | Tỷ lệ tin yêu cầu kỹ năng thứ 1 |
| **M31** | median_it_salary_usd_yearly | `TODO` | USD | *Chờ D07/A08* | D07/A08 | PENDING | **NO** | Mức lương trung vị CNTT (USD/Năm) |
| **M32** | spark_pipeline_execution_time | `TODO` | seconds | *Chờ D08* | D08 | PENDING | **NO** | Thời gian chạy pipeline benchmark |
