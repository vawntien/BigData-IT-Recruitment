# D09 Final Pipeline Validation Report (Template & Scaffold Status)

> [!WARNING]
> **D09 OFFICIAL NOT EXECUTED**
> Báo cáo này phản ánh trạng thái chạy kiểm thử của **D09 VALIDATION SCAFFOLD**.
> Pipeline chính thức chưa thể hoàn thành D09 do các giai đoạn D05 official (chờ A03), D06, D07, và D08 chưa hoàn tất. Mọi mục chưa thực thi đều được đánh dấu rõ ràng là **TODO - D09 OFFICIAL NOT EXECUTED**.

---

## 1. Environment & Execution Metadata

- **Thời gian chạy kiểm thử (UTC):** `2026-10-06T09:42:53Z`
- **Hệ điều hành:** Windows (10 / 11)
- **Python Version:** 3.11 (`.venv`)
- **PySpark Version:** 4.2.0 (`local[*]`, Session TimeZone: UTC)
- **Adapter LocalFS:** `tmp/d04-localfs/d04-localfs-adapter.jar` (`NoPermissionLocalFileSystem`)
- **Git Branch:** `support/tv1-d09-validation-scaffold`
- **Official Execution Flag:** `False`
- **Audit Log Artifact:** `data/audit/d09/validation_scaffold_results.csv`

---

## 2. Dataset Version & Inventory Verified

| Bảng dữ liệu | Thư mục lưu trữ | Số dòng Clean | Trạng thái kiểm tra | Ghi chú |
| :--- | :--- | :---: | :---: | :--- |
| `postings` | `data/processed/clean/postings` | 123,849 | PASS | Khóa chính duy nhất, 0 NULL |
| `companies` | `data/processed/clean/companies` | 24,473 | PASS | Khóa chính duy nhất, 0 NULL |
| `skills` | `data/processed/clean/skills` | 35 | PASS | 35 nhãn Job Function |
| `industries` | `data/processed/clean/industries` | 422 | PASS | Danh mục ngành nghề |
| `company_industries` | `data/processed/clean/company_industries` | 24,375 | PASS | Quan hệ nhiều-nhiều |
| `company_specialities` | `data/processed/clean/company_specialities` | 169,367 | PASS | Khử trùng 20 dòng |
| `employee_counts` | `data/processed/clean/employee_counts` | 35,665 | PASS | Khử trùng 122 dòng |
| `benefits` | `data/processed/clean/benefits` | 67,943 | PASS | Quan hệ nhiều-nhiều |
| `job_industries` | `data/processed/clean/job_industries` | 164,808 | PASS | Quan hệ nhiều-nhiều |
| `job_skills` | `data/processed/clean/job_skills` | 213,768 | PASS | Quan hệ nhiều-nhiều |
| `salaries` | `data/processed/clean/salaries` | 40,785 | PASS | Độ phủ lương 29.13% |

---

## 3. Data Integrity & Reconciliation Verification

- **Nguyên lý bảo toàn:** `raw_rows == clean_rows + rejected_rows`.
- **Tổng số bản ghi đầu vào (Raw):** 865,492 dòng.
- **Tổng số bản ghi đầu ra sạch (Clean):** 865,350 dòng.
- **Tổng số bản ghi loại bỏ (Rejected):** 142 dòng (20 duplicate trong `company_specialities` + 122 duplicate trong `employee_counts`).
- **Kết luận:** Tỷ lệ cân đối đạt **100.00%** (11/11 bảng vượt qua kiểm tra `check_reconciliation`).

---

## 4. Grain Preservation & Join Safety Verification

- **Bảo toàn Grain tin tuyển dụng:**
  - Base `postings`: 123,849 dòng, 123,849 distinct `job_id`.
  - Kết nối LEFT JOIN với `agg_skills`, `agg_industries`, `agg_benefits`: 123,849 dòng, 123,849 distinct `job_id` (Không sinh dòng trùng).
  - Kết nối LEFT JOIN với `salaries`: 123,849 dòng, 123,849 distinct `job_id` (Không sinh dòng trùng).
- **Bảo toàn Grain công ty:**
  - Base `companies`: 24,473 dòng, 24,473 distinct `company_id`.
  - Snapshot `latest_employee_counts`: đúng 24,473 dòng (1 dòng duy nhất cho mỗi công ty).

---

## 5. Scope & Component Status Overview

| Hạng mục kiểm tra | Số lượng check | PASS | FAIL | PENDING | Trạng thái hiện tại |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **D04 Integrity & Reconciliation** | 12 | 12 | 0 | 0 | Đã nghiệm thu |
| **D04 Clean Key Constraints** | 10 | 10 | 0 | 0 | Đã nghiệm thu |
| **D05 Scaffold Contracts** | 5 | 5 | 0 | 0 | Đã nghiệm thu |
| **Pipeline Guard (Anti-leakage)** | 1 | 1 | 0 | 0 | Đã nghiệm thu |
| **D05 Official Canonical Dataset** | 2 | 0 | 0 | 2 | Chờ A03 & D05 official |
| **D06 IT Classification** | 3 | 0 | 0 | 3 | Chờ D06 pipeline |
| **D07 Salary Normalization** | 3 | 0 | 0 | 3 | Chờ D07 pipeline |
| **D08 Spark Benchmark** | 2 | 0 | 0 | 2 | Chờ D08 benchmark |
| **Analytics Aggregation Views** | 2 | 0 | 0 | 2 | Chờ tạo Golden Views |
| **Dashboard Contract** | 1 | 0 | 0 | 1 | Chờ xuất dữ liệu Dashboard |
| **TỔNG CỘNG** | **41** | **28** | **0** | **13** | **SCAFFOLD PASS (OFFICIAL PENDING)** |

---

## 6. Official Pipeline Sections (TODO)

### 6.1 D05 Official Canonical Dataset
- [ ] *TODO - D09 OFFICIAL NOT EXECUTED*
- Kiểm tra sự tồn tại của `data/processed/canonical/canonical_jobs.parquet`.
- Khẳng định số dòng đạt đúng 123,849 và không có `job_id` trùng lặp sau khi tích hợp phân loại kỹ năng từ TV2 (A03).

### 6.2 D06 IT Classification Validation
- [ ] *TODO - D09 OFFICIAL NOT EXECUTED*
- Kiểm tra schema có trường `is_it_job` hoặc `it_category`.
- Khẳng định các nhãn phân loại thuộc taxonomy hợp lệ.
- Kiểm tra tính bảo toàn grain sau khi phân loại IT.

### 6.3 D07 Salary Normalization Validation
- [ ] *TODO - D09 OFFICIAL NOT EXECUTED*
- Kiểm tra trường lương chuẩn hóa (annualized USD).
- Ràng buộc thứ tự logic: `min_salary <= med_salary <= max_salary`.
- Kiểm tra chính sách missing salary: Giữ nguyên `NULL`, tuyệt đối không thay bằng `0`.

### 6.4 D08 Official Benchmark Verification
- [ ] *TODO - D09 OFFICIAL NOT EXECUTED*
- Kiểm tra kết quả benchmark chính thức có cờ `official=True`.
- Đảm bảo đo lường ít nhất 3 lượt chạy và báo cáo trung vị.

### 6.5 Golden Views & Dashboard Contract
- [ ] *TODO - D09 OFFICIAL NOT EXECUTED*
- Kiểm tra số lượng bản ghi tổng hợp trong Golden Views không âm và đúng quy mô mẫu.
- Xác thực hợp đồng schema của tầng tiêu thụ Dashboard (cột, kiểu dữ liệu).

---

## 7. Synthetic Data Leakage Guard Status

- **Tệp nguồn kiểm tra:** `data/processed/clean`
- **Kết quả kiểm tra:** `PASS`
- **Ghi nhận:** Nguồn dữ liệu hoàn toàn là dữ liệu LinkedIn thu thập thực tế, không chứa tiền tố `SYNTHETIC_SAMPLE` hoặc đường dẫn từ `sample_data/`.

---

## 8. Final Acceptance Sign-off Matrix

| Vai trò | Thành viên | Nhiệm vụ nghiệm thu | Ký duyệt |
| :--- | :--- | :--- | :---: |
| **TV1** | Data Engineer & Benchmark Lead | D01–D04 Clean, D05 Scaffold, D07, D08, D09 Validation | **SCAFFOLD SIGN-OFF** |
| **TV2** | Taxonomy & Business Logic Lead | A03 Skill Semantics, D05 Join, D06 IT Classification | *Pending A03* |
| **TV3** | Analytics & Dashboard Lead | V01–V09 Dashboard, Golden Views, User Guide | *Pending Canonical Data* |
