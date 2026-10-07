# DATA MANIFEST

## 1. Thông tin bộ dữ liệu

Tên bộ dữ liệu:
LinkedIn Job Postings (2023–2024)

Nguồn:
Kaggle

Tác giả:
Arsh Koneru

URL:
https://www.kaggle.com/datasets/arshkon/linkedin-job-postings

Ngày tải:
04/10/2026

License:
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/

---

## 2. Phiên bản dữ liệu sử dụng

Tổng số file CSV: 11

Tổng dung lượng:
530.72 MB

### Danh sách file

| File                               | Dung lượng |
| ---------------------------------- | ---------: |
| postings.csv                       |  492.90 MB |
| companies/companies.csv            |   22.12 MB |
| companies/company_industries.csv   |    0.75 MB |
| companies/company_specialities.csv |    4.23 MB |
| companies/employee_counts.csv      |    1.00 MB |
| jobs/benefits.csv                  |    1.84 MB |
| jobs/job_industries.csv            |    2.39 MB |
| jobs/job_skills.csv                |    3.34 MB |
| jobs/salaries.csv                  |    2.15 MB |
| mappings/industries.csv            |    0.01 MB |
| mappings/skills.csv                |  < 0.01 MB |

Dữ liệu gốc được giữ nguyên tại:

data/raw/

## 2. Cấu trúc dữ liệu tải về

Tổng số file CSV: 11

### Bảng chính

- postings.csv

### Dữ liệu doanh nghiệp

- companies/companies.csv
- companies/company_industries.csv
- companies/company_specialities.csv
- companies/employee_counts.csv

### Dữ liệu liên quan đến tin tuyển dụng

- jobs/benefits.csv
- jobs/job_industries.csv
- jobs/job_skills.csv
- jobs/salaries.csv

### Bảng ánh xạ

- mappings/industries.csv
- mappings/skills.csv

---

## 3. Quy tắc lưu trữ

Dữ liệu gốc được lưu tại:

data/raw/

Không chỉnh sửa trực tiếp dữ liệu trong thư mục raw.

Dữ liệu sau khi được xử lý bằng Apache Spark sẽ được lưu tại:

data/processed/

Các bảng tổng hợp phục vụ phân tích và dashboard sẽ được lưu tại:

data/analytics/

---

## 4. Phạm vi phân tích

Đồ án sử dụng bộ dữ liệu LinkedIn Job Postings để phân tích
các tin tuyển dụng liên quan đến lĩnh vực Công nghệ thông tin.

Các kết quả chỉ phản ánh những bản ghi có trong bộ dữ liệu
được sử dụng và không được suy rộng thành toàn bộ thị trường
lao động của Việt Nam hoặc một quốc gia cụ thể.

Phạm vi địa lý chi tiết sẽ được xác định dựa trên các giá trị
địa điểm thực tế trong dữ liệu sau bước kiểm kê dữ liệu.

---

## 5. Nguyên tắc

- Không thay đổi dữ liệu gốc.
- Không giả định schema trước khi kiểm tra.
- Không giả định khóa JOIN trước khi kiểm tra dữ liệu.
- Không gán giá trị thiếu thành 0 nếu chưa có quy tắc.
- Không suy rộng kết quả ngoài phạm vi dataset.
// Trần Nguyễn Bảo An - Nguyễn Văn Tiến .