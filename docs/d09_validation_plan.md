# D09 Final Pipeline Validation Plan

## 1. Overview and Scope

Kế hoạch kiểm định toàn diện (Pipeline Validation Plan - D09) thiết lập khung kiểm soát chất lượng kỹ thuật, tính toàn vẹn dữ liệu, tính bảo toàn grain, và tính nhất quán giữa các tầng chuyển đổi trong pipeline tuyển dụng LinkedIn Job Postings (2023–2024).

> [!IMPORTANT]
> **Hiện trạng thực thi:** Khung kiểm định hiện tại là **D09 VALIDATION SCAFFOLD**.
> **D09 OFFICIAL CHƯA ĐƯỢC ĐÁNH PASS** do các giai đoạn D05 official (bị chặn bởi A03), D06, D07, và D08 chưa hoàn tất. Toàn bộ các kiểm tra thuộc các giai đoạn này đều được gán nhãn `PENDING` và `official=False`.

---

## 2. Validation Taxonomy & Execution Matrix

Khung kiểm định chia toàn bộ pipeline thành 3 nhóm trạng thái:
1. **READY NOW:** Đã có artifact thực tế trong repo (D01–D04 clean Parquet và D05 scaffold guards). Đã được kiểm thử và đạt `PASS`.
2. **PENDING DEPENDENCY:** Chờ đầu ra chính thức từ các task phụ thuộc (D05 canonical dataset, D06 phân loại CNTT, D07 chuẩn hóa lương, D08 benchmark chính thức).
3. **FINAL ACCEPTANCE:** Kiểm tra tổng hợp trước khi bàn giao đồ án (Golden Views, hợp đồng Dashboard, guard chống rò rỉ dữ liệu tổng hợp).

| ID Kiểm tra | Giai đoạn | Đối tượng | Nội dung kiểm tra | Tiêu chuẩn chấp nhận | Phân loại | Trạng thái hiện tại |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **D09-AUDIT-01** | D04 Integrity | `data/audit/d04_etl_summary.csv` | Tồn tại tệp audit log | Tệp tồn tại, đúng schema | READY NOW | **PASS** |
| **D09-RECON-POST**| D04 Reconciliation | `postings` | Cân đối dòng vào - ra | 123,849 = 123,849 + 0 | READY NOW | **PASS** |
| **D09-RECON-COMP**| D04 Reconciliation | `companies` | Cân đối dòng vào - ra | 24,473 = 24,473 + 0 | READY NOW | **PASS** |
| **D09-RECON-IND1**| D04 Reconciliation | `company_industries` | Cân đối dòng vào - ra | 24,375 = 24,375 + 0 | READY NOW | **PASS** |
| **D09-RECON-SPEC**| D04 Reconciliation | `company_specialities`| Cân đối dòng vào - ra | 169,387 = 169,367 + 20 (20 trùng)| READY NOW | **PASS** |
| **D09-RECON-EMPL**| D04 Reconciliation | `employee_counts` | Cân đối dòng vào - ra | 35,787 = 35,665 + 122 (122 trùng)| READY NOW | **PASS** |
| **D09-RECON-BENE**| D04 Reconciliation | `benefits` | Cân đối dòng vào - ra | 67,943 = 67,943 + 0 | READY NOW | **PASS** |
| **D09-RECON-JIND**| D04 Reconciliation | `job_industries` | Cân đối dòng vào - ra | 164,808 = 164,808 + 0 | READY NOW | **PASS** |
| **D09-RECON-JSKL**| D04 Reconciliation | `job_skills` | Cân đối dòng vào - ra | 213,768 = 213,768 + 0 | READY NOW | **PASS** |
| **D09-RECON-SALA**| D04 Reconciliation | `salaries` | Cân đối dòng vào - ra | 40,785 = 40,785 + 0 | READY NOW | **PASS** |
| **D09-RECON-INDU**| D04 Reconciliation | `industries` | Cân đối dòng vào - ra | 422 = 422 + 0 | READY NOW | **PASS** |
| **D09-RECON-SKIL**| D04 Reconciliation | `skills` | Cân đối dòng vào - ra | 35 = 35 + 0 | READY NOW | **PASS** |
| **D09-POST-01** | D04 Clean Parquet | `clean/postings` | Kiểm tra tồn tại thư mục | Tồn tại thư mục parquet | READY NOW | **PASS** |
| **D09-POST-02** | D04 Clean Parquet | `clean/postings` | Tổng số dòng bảng chính | Đúng 123,849 dòng | READY NOW | **PASS** |
| **D09-POST-03** | D04 Clean Parquet | `clean/postings.job_id` | Ràng buộc non-null | 0 giá trị NULL | READY NOW | **PASS** |
| **D09-POST-04** | D04 Clean Parquet | `clean/postings.job_id` | Ràng buộc duy nhất (Unique) | 123,849 khóa phân biệt (0 trùng) | READY NOW | **PASS** |
| **D09-COMP-01** | D04 Clean Parquet | `clean/companies` | Kiểm tra tồn tại thư mục | Tồn tại thư mục parquet | READY NOW | **PASS** |
| **D09-COMP-02** | D04 Clean Parquet | `clean/companies` | Tổng số dòng công ty | Đúng 24,473 dòng | READY NOW | **PASS** |
| **D09-COMP-03** | D04 Clean Parquet | `clean/companies.company_id` | Ràng buộc non-null | 0 giá trị NULL | READY NOW | **PASS** |
| **D09-COMP-04** | D04 Clean Parquet | `clean/companies.company_id` | Ràng buộc duy nhất (Unique) | 24,473 khóa phân biệt (0 trùng) | READY NOW | **PASS** |
| **D09-SKIL-01** | D04 Clean Parquet | `clean/skills` | Kiểm tra tồn tại danh mục | Tồn tại thư mục parquet | READY NOW | **PASS** |
| **D09-SKIL-02** | D04 Clean Parquet | `clean/skills` | Tổng số phân loại nghề | Đúng 35 nhãn chức danh | READY NOW | **PASS** |
| **D09-SCAF-01** | D05 Scaffold | `agg_skills` | Khử trùng Many-to-Many | Duy nhất trên `job_id` (126,807 keys) | READY NOW | **PASS** |
| **D09-SCAF-02** | D05 Scaffold | `latest_employee_counts` | Snapshot nhân sự mới nhất | Đúng 24,473 dòng (1 dòng/công ty) | READY NOW | **PASS** |
| **D09-SCAF-03** | D05 Scaffold | `latest_employee_counts` | Duy nhất `company_id` | Duy nhất tuyệt đối trên `company_id` | READY NOW | **PASS** |
| **D09-SCAF-04** | D05 Scaffold | `postings_bridge_join` | Bảo toàn Grain (LEFT JOIN) | 123,849 dòng (không nổ/mất dòng) | READY NOW | **PASS** |
| **D09-SCAF-05** | D05 Scaffold | `postings_salary_join` | Bảo toàn Grain (LEFT JOIN) | 123,849 dòng (không nổ/mất dòng) | READY NOW | **PASS** |
| **D09-LEAK-01** | Pipeline Guard | Dữ liệu đầu vào sạch | Guard chống rò rỉ sample data | Không chứa `SYNTHETIC_SAMPLE` | READY NOW | **PASS** |
| **D09-CANON-01**| D05 Official | `canonical_jobs` | Tổng số dòng bảng canonical | Đúng 123,849 dòng | PENDING DEP | **PENDING** |
| **D09-CANON-02**| D05 Official | `canonical_jobs.job_id` | Khóa duy nhất canonical | Duy nhất và không null (123,849 keys) | PENDING DEP | **PENDING** |
| **D09-D06-01** | D06 IT Classification | `canonical_jobs` | Cột phân loại IT | Tồn tại trường `is_it_job` hoặc `it_category` | PENDING DEP | **PENDING** |
| **D09-D06-02** | D06 IT Classification | Nhãn phân loại IT | Miền giá trị cho phép | Nằm trong taxonomy thống nhất | PENDING DEP | **PENDING** |
| **D09-D06-03** | D06 IT Classification | Bảo toàn Grain | Bảo toàn 1 dòng / tin | Đúng 123,849 dòng, 0 duplicate | PENDING DEP | **PENDING** |
| **D09-D07-01** | D07 Salary Normalization | Cột lương chuẩn hóa | Chuẩn hóa kỳ hạn & đơn vị | Đưa về chuẩn hóa USD năm/tháng | PENDING DEP | **PENDING** |
| **D09-D07-02** | D07 Salary Normalization | Tính đơn điệu min/med/max | Kiểm tra logic dải lương | min_salary <= med_salary <= max_salary | PENDING DEP | **PENDING** |
| **D09-D07-03** | D07 Salary Normalization | Xử lý tin khuyết lương | Chính sách giá trị thiếu | Giữ `NULL`, tuyệt đối không gán `0` | PENDING DEP | **PENDING** |
| **D09-D08-01** | D08 Benchmark | Audit Benchmark | Cờ ghi nhận chính thức | `official = True` và gắn commit SHA | PENDING DEP | **PENDING** |
| **D09-D08-02** | D08 Benchmark | Độ ổn định đo lường | Số lượt chạy tối thiểu | >= 3 lần đo, ghi nhận độ trễ trung vị | PENDING DEP | **PENDING** |
| **D09-ANLY-01**| Final Analytics | Golden Aggregations | Quy mô mẫu hợp lệ | Tổng số tin phân tích khớp dân số chính thức | FINAL ACCEPT | **PENDING** |
| **D09-ANLY-02**| Final Analytics | Tính phi âm chỉ số | Chỉ số thống kê hợp lệ | Mọi số lượng, mức lương trung bình >= 0 | FINAL ACCEPT | **PENDING** |
| **D09-DASH-01**| Dashboard Contract | Consumption Layer | Hợp đồng schema Dashboard | Đúng tên trường, đúng kiểu dữ liệu cam kết | FINAL ACCEPT | **PENDING** |

---

## 3. Các Rào Cản Kỹ Thuật (Safety Guards)

1. **Synthetic Data Leakage Guard (`check_synthetic_leakage`):**
   - Chặn tuyệt đối việc nạp dữ liệu từ thư mục `dashboard/sample_data/` hoặc mang cờ nguồn `SYNTHETIC_SAMPLE` vào các bảng golden view hoặc báo cáo nghiệm thu chính thức.
2. **Grain Explosion Guard (`check_no_duplicate_grain`):**
   - Đảm bảo các phép kết nối với bảng quan hệ nhiều-nhiều (`job_skills`, `job_industries`, `benefits`) và bảng lịch sử (`employee_counts`) đã được gom nhóm tiền kết nối (bridge aggregation / latest snapshot), giữ nguyên số dòng bảng gốc là 123,849 dòng.
3. **Missing Value Policy Guard (`missing_salary_null_policy`):**
   - Nghiêm cấm thay thế lương thiếu bằng giá trị 0 vì sẽ làm sai lệch nghiêm trọng các phân vị lương và mức lương trung bình.
4. **Reconciliation Guard (`check_reconciliation`):**
   - Khẳng định tính toán vẹn: `Raw Rows = Clean Output + Rejected Output`.

---

## 4. Quy Trình Kích Hoạt Kiểm Định Chính Thức (D09 Official Trigger)

Khi các thành viên trong nhóm hoàn thành các task tương ứng:
1. TV2 hoàn thành A03 -> Chạy D05 Official JOIN -> Kích hoạt `D09-CANON-*`.
2. TV2 hoàn thành D06 -> Kích hoạt `D09-D06-*`.
3. TV1 hoàn thành D07 -> Kích hoạt `D09-D07-*`.
4. TV1 hoàn thành D08 -> Kích hoạt `D09-D08-*`.
5. Tạo Golden Views và kiểm tra Dashboard contract -> Kích hoạt `D09-ANLY-*` và `D09-DASH-01`.
6. Chỉ khi **41/41 kiểm tra đạt PASS** và `official=True`, D09 mới được xác nhận hoàn thành chính thức.
