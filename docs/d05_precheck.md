# D05 Pre-Check Report

## 1. Mục đích và phạm vi

Báo cáo này tổng hợp kết quả tiền kiểm (**D05 PRE-CHECK**) trước khi tiến hành bước JOIN và lưu Parquet chuẩn hóa (D05).
Toàn bộ kết luận trong báo cáo dựa trên dữ liệu runtime và tệp Parquet thực tế tại `data/processed/clean/` và các bảng audit tại `data/audit/`.

> [!IMPORTANT]
> **Trạng thái thực thi D05:** **BLOCKED BY A03**  
> D05 official không được thực hiện do dependency task **A03** ("Khảo sát skills và industries / Bản đồ JOIN và nguồn kỹ năng" của Thành viên 2) chưa tồn tại trong repository. Báo cáo này không thực hiện JOIN tạo canonical dataset và không chỉnh sửa bất kỳ tệp dữ liệu raw/clean nào.

---

## 2. Kiểm kê Parquet sạch (`data/processed/clean/`)

Toàn bộ 11 bảng Parquet sạch được đọc và đối soát bằng PySpark:

| Bảng | Số dòng thực tế | Kỳ vọng (D04 Report) | Số cột | Trạng thái |
| :--- | :---: | :---: | :---: | :---: |
| `postings` | 123,849 | 123,849 | 35 | **PASS** |
| `companies` | 24,473 | 24,473 | 10 | **PASS** |
| `company_industries` | 24,375 | 24,375 | 2 | **PASS** |
| `company_specialities` | 169,367 | 169,367 | 2 | **PASS** |
| `employee_counts` | 35,665 | 35,665 | 5 | **PASS** |
| `benefits` | 67,943 | 67,943 | 3 | **PASS** |
| `job_industries` | 164,808 | 164,808 | 2 | **PASS** |
| `job_skills` | 213,768 | 213,768 | 2 | **PASS** |
| `salaries` | 40,785 | 40,785 | 8 | **PASS** |
| `industries` | 422 | 422 | 2 | **PASS** |
| `skills` | 35 | 35 | 2 | **PASS** |

**Dữ liệu rejected / quarantined đối soát khớp 100%:**
- `data/processed/rejected/company_specialities_duplicate_keys/company_id__speciality`: 20 dòng.
- `data/processed/rejected/employee_counts_duplicate_keys`: 122 dòng.
- Không có bất kỳ sai lệch nào (0 discrepancies) so với báo cáo D03 và D04.

---

## 3. Khảo sát Cardinality quan hệ Many-to-Many

Chi tiết xuất tại: `data/audit/d05_precheck_cardinality.csv`.

| Bảng quan hệ | Khóa thực thể | Số thực thể duy nhất | Tổng số dòng | Trung bình / thực thể | Median | Max / thực thể | Số thực thể có >1 giá trị |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `job_skills` | `job_id` | 126,807 | 213,768 | 1.6858 | 2 | 3 | 71,658 |
| `job_industries` | `job_id` | 127,125 | 164,808 | 1.2964 | 1 | 3 | 24,406 |
| `benefits` | `job_id` | 30,023 | 67,943 | 2.2630 | 2 | 12 | 16,101 |
| `company_specialities` | `company_id` | 17,780 | 169,367 | 9.5257 | 8 | 84 | 16,970 |
| `company_industries` | `company_id` | 24,365 | 24,375 | 1.0004 | 1 | 2 | 10 |

### Cảnh báo nguy cơ Row Explosion khi JOIN trực tiếp:
Nếu thực hiện phép JOIN phẳng (flat/direct join) giữa `postings` và các bảng quan hệ nhiều-nhiều:
- Một tin tuyển dụng có thể có tới **3 skills**, **3 industries**, và **12 benefits**.
- Doanh nghiệp đăng tuyển có thể có tới **84 specialities** và **2 industries**.
- Tích đề-các (Cartesian product) đối với một tin tuyển dụng ở trường hợp cực đại sẽ tạo ra:
  $$3 \times 3 \times 12 \times 84 \times 2 = 18,144 \text{ dòng cho DUY NHẤT một job posting!}$$
- Ngay cả ở mức trung bình, việc nhân các quan hệ nhiều-nhiều sẽ làm bùng nổ số lượng bản ghi từ **123,849** lên hàng chục triệu dòng trùng lặp, phá vỡ tính chính xác của các chỉ số phân tích (số lượng tin, phân bố lương, cấp bậc).
- **Quy tắc thiết kế cho D05:** Phải gom nhóm (pre-aggregate thành mảng `collect_set` / `array` hoặc giữ tách biệt dưới dạng bảng cầu / dimension) trước khi gắn vào grain 1 dòng / tin tuyển dụng.

---

## 4. Khảo sát Skills Mapping (`data/processed/clean/skills/`)

Chi tiết xuất tại: `data/audit/d05_precheck_skills.csv`.  
Bảng gồm đúng 35 bản ghi:

| `skill_abr` | `skill_name` | `skill_abr` | `skill_name` |
| :--- | :--- | :--- | :--- |
| **ACCT** | Accounting/Auditing | **IT** | Information Technology |
| **ADM** | Administrative | **LGL** | Legal |
| **ADVR** | Advertising | **MGMT** | Management |
| **ANLS** | Analyst | **MNFC** | Manufacturing |
| **ART** | Art/Creative | **MRKT** | Marketing |
| **BD** | Business Development | **OTHR** | Other |
| **CNSL** | Consulting | **PR** | Public Relations |
| **CUST** | Customer Service | **PRCH** | Purchasing |
| **DIST** | Distribution | **PRDM** | Product Management |
| **DSGN** | Design | **PRJM** | Project Management |
| **EDU** | Education | **PROD** | Production |
| **ENG** | Engineering | **QA** | Quality Assurance |
| **FIN** | Finance | **RSCH** | Research |
| **GENB** | General Business | **SALE** | Sales |
| **HCPR** | Health Care Provider | **SCI** | Science |
| **HR** | Human Resources | **STRA** | Strategy/Planning |
| **SUPL** | Supply Chain | **TRNG** | Training |
| **WRT** | Writing/Editing | | |

> [!CAUTION]
> **Bản chất thực tế của 35 Skill Labels:**  
> Toàn bộ 35 giá trị trong `skills.csv` là **nhóm ngành / lĩnh vực nghề nghiệp tổng quát (Job Functions / Domains)** như `IT` (Information Technology), `ENG` (Engineering), `FIN` (Finance), `HR` (Human Resources), `SALE` (Sales).  
> **HOÀN TOÀN KHÔNG PHẢI là kỹ năng kỹ thuật cụ thể** (như Python, Java, SQL, Spark, Docker, AWS).  
> Bảng `job_skills` gốc không chứa kỹ năng kỹ thuật chi tiết. Kỹ năng kỹ thuật chỉ có thể được trích xuất từ văn bản trường `description` (hoặc `skills_desc` nếu có, nhưng trường này thiếu tới 98%). Đây là lý do cốt lõi vì sao D05 phụ thuộc vào A03/A05.

---

## 5. Khảo sát Industry Mapping (`data/processed/clean/industries/`)

- **Schema thực tế:**
  - `industry_id`: `bigint` (long)
  - `industry_name`: `string`
- **Tổng số ngành:** 422 ngành duy nhất.
- **Mẫu dữ liệu thực tế:**
  - `1`: Defense and Space Manufacturing
  - `3`: Computer Hardware Manufacturing
  - `4`: Software Development
  - `5`: Computer Networking Products
  - `6`: Technology, Information and Internet
  - `7`: Semiconductor Manufacturing
  - `8`: Telecommunications
  - `9`: Law Practice
  - `10`: Legal Services
  - `11`: Business Consulting and Services
- **Ánh xạ:** Bảng `job_industries.industry_id` map 100% (422/422) sang `industries.industry_id`. Bảng này đóng vai trò quan trọng trong việc hỗ trợ bộ lọc nhận diện tin tuyển dụng ngành CNTT (IT filter) tại D06.

---

## 6. Khảo sát Employee Counts Snapshots (`data/processed/clean/employee_counts/`)

- **Tổng số dòng:** 35,665
- **Số doanh nghiệp duy nhất (`company_id`):** 24,473
- **Số doanh nghiệp có >1 snapshot:** **5,694 doanh nghiệp** (chiếm 23.27%)
- **Số snapshot / doanh nghiệp:**
  - Tối thiểu: 1 snapshot
  - Tối đa: **13 snapshots**
  - Trung bình: 1.4573 snapshots
  - Median: 1 snapshot
- **Khoảng thời gian ghi nhận (`time_recorded` UTC):**
  - Min: `2024-04-06 02:42:53 UTC`
  - Max: `2024-04-20 07:27:39 UTC`

> [!WARNING]
> **Quy tắc JOIN cho D05:**  
> D05 **KHÔNG ĐƯỢC JOIN trực tiếp** toàn bộ các dòng của `employee_counts` vào `postings` nếu grain mục tiêu là 1 dòng / tin tuyển dụng. Nếu JOIN trực tiếp, các tin tuyển dụng thuộc 5,694 công ty có nhiều snapshot sẽ bị nhân bản từ 2 đến 13 lần.  
> D05 bắt buộc phải lọc lấy snapshot mới nhất (`latest snapshot` theo `time_recorded`) trước khi kết hợp.

---

## 7. Khảo sát Khóa và Quan hệ Salaries (`data/processed/clean/salaries/`)

- **Tổng số dòng:** 40,785
- **Số `job_id` duy nhất:** 40,785
- **Số `job_id` trùng lặp:** 0 (Khóa `job_id` là duy nhất trong bảng `salaries`).
- **Quan hệ với `postings`:**
  - Trong phạm vi `postings`, quan hệ là **0..1** (tối đa 1 bản ghi lương cho mỗi tin tuyển dụng).
  - Chỉ có **36,073** tin trong `postings` có bản ghi lương tương ứng trong `salaries` (đạt tỷ lệ **29.13%**).
  - Có **4,712 dòng lương mồ côi (orphan rows)** có `job_id` không hề tồn tại trong bảng `postings`.
- Không xử lý hay suy diễn về quy đổi lương (currency/pay_period) ở bước này.

---

## 8. Độ phủ khóa và Khóa ngoại mồ côi (Referential Join Coverage)

Chi tiết xuất tại: `data/audit/d05_precheck_join_coverage.csv`.

| Bảng cha $\rightarrow$ con | Khóa | Dòng con | Distinct Keys con | Matched Keys | Unmatched Keys | Orphan Rows | Tỷ lệ phủ (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `companies` $\rightarrow$ `postings` | `company_id` | 122,132 | 24,474 | 24,473 | 1 | 1 | 99.9959% |
| `postings` $\rightarrow$ `job_skills` | `job_id` | 213,768 | 126,807 | 122,096 | 4,711 | 7,990 | 96.2849% |
| `postings` $\rightarrow$ `job_industries` | `job_id` | 164,808 | 127,125 | 122,413 | 4,712 | 5,845 | 96.2934% |
| `postings` $\rightarrow$ `benefits` | `job_id` | 67,943 | 30,023 | 28,735 | 1,288 | 2,550 | 95.7100% |
| `postings` $\rightarrow$ `salaries` | `job_id` | 40,785 | 40,785 | 36,073 | 4,712 | 4,712 | 88.4467% |
| `skills` $\rightarrow$ `job_skills` | `skill_abr` | 213,768 | 35 | 35 | 0 | 0 | 100.0000% |
| `industries` $\rightarrow$ `job_industries` | `industry_id` | 164,808 | 422 | 422 | 0 | 0 | 100.0000% |
| `companies` $\rightarrow$ `company_industries` | `company_id` | 24,375 | 24,365 | 24,365 | 0 | 0 | 100.0000% |
| `companies` $\rightarrow$ `company_specialities` | `company_id` | 169,367 | 17,780 | 17,780 | 0 | 0 | 100.0000% |
| `companies` $\rightarrow$ `employee_counts` | `company_id` | 35,665 | 24,473 | 24,473 | 0 | 0 | 100.0000% |

---

## 9. Tình trạng Dependency A03 và Kết luận

- **Tình trạng A03:**
  - Quét hệ thống xác nhận: **Chưa có artifact / tài liệu A03** ("Bản đồ JOIN và nguồn kỹ năng").
  - Kế hoạch phân công dự án (`Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsx`) chỉ rõ D05 phụ thuộc vào `[D04, A03]`.
- **Đánh giá D05 PRE-CHECK:** **PASS** (dữ liệu sạch hoàn toàn sẵn sàng, các rủi ro cardinality và khóa mồ côi đã được định lượng chính xác).
- **Quyết định thực thi D05 chính thức:** **BLOCKED BY A03**. Không triển khai code và pipeline D05 chính thức cho đến khi A03 được bàn giao.