# TV2 – Đối chiếu dữ liệu gốc ngày 08/10/2026

Thực hiện cho Đồng Viết Dũng – TV2, trên nhánh `feat/tv2-analysis`. Đã đọc README, manifest, D03–D05, A01–A03, JSON taxonomy và các script hiện có. Repo không có AGENTS.md trong cây làm việc. A01/A02/A03/config là thay đổi chưa commit từ đầu lượt, được giữ lại; không chuyển nhánh, commit hay push.

## Nguồn, parser và bản sao

Thư mục **`C:\archive`** chứa đủ đúng 11 CSV theo cấu trúc manifest. Nguồn chính duy nhất là bộ gốc này, không dùng `data/selected`. Đã sao chép vào `data/raw/` cùng đường dẫn tương đối, không sửa/xóa dữ liệu trong archive. Script [tv2_verify_raw.py](../src/tv2_verify_raw.py) đọc UTF-8-sig bằng `csv.DictReader(strict=True)` với `newline=''`, hỗ trợ dấu phẩy, quote và mô tả nhiều dòng; kiểm tra đủ số trường từng record. Không split dấu phẩy hoặc đếm dòng vật lý.

Trước mọi copy, script kiểm tra tất cả đích hiện có bằng SHA-256: file giống thì bỏ qua, khác thì dừng và không ghi đè. Đích mới mở bằng `xb`; hash sau copy bằng nguồn. Size, mtime và SHA-256 của cả 11 file archive trước/sau không đổi. [Inventory](../data/audit/tv2_raw_inventory.csv) giữ byte size, header đầy đủ theo thứ tự, count, số record có xuống dòng, hash nguồn/đích và copy action.

| Đường dẫn trong data/raw | Record CSV | Cột | Đối chiếu header/count D03 |
| --- | ---: | ---: | --- |
| postings.csv | 123.849 | 31 | Khớp |
| companies/companies.csv | 24.473 | 10 | Khớp |
| companies/company_industries.csv | 24.375 | 2 | Khớp |
| companies/company_specialities.csv | 169.387 | 2 | Khớp |
| companies/employee_counts.csv | 35.787 | 4 | Khớp |
| jobs/benefits.csv | 67.943 | 3 | Khớp |
| jobs/job_industries.csv | 164.808 | 2 | Khớp |
| jobs/job_skills.csv | 213.768 | 2 | Khớp |
| jobs/salaries.csv | 40.785 | 8 | Khớp |
| mappings/industries.csv | 422 | 2 | Khớp |
| mappings/skills.csv | 35 | 2 | Khớp |

Header còn khớp `TABLE_SPECS` của TV1 trong `src/clean_data.py`; script đọc constants bằng AST, không import Spark hoặc đổi ETL. **118.612 records postings và 16.689 records companies chứa xuống dòng trong trường.**

## Những khác biệt và giới hạn cần giữ

- Tổng dung lượng thực: **556.502.912 byte = 530,722534 MiB = 556,502912 MB thập phân**. Manifest ghi 530,72 “MB”, nhưng giá trị khớp cách tính MiB và các dung lượng làm tròn từng file; ghi nhận khác đơn vị, giữ nguyên manifest của TV1.
- Không khác tên, header hoặc count so với D03. Toàn bộ missing count tính lại khớp `missing_profile.csv`, theo trim/sentinel thiếu của D03.
- Matching tên/count/header/missing **không chứng minh cùng release Kaggle**. Audit cũ không có hash raw hoặc release ID để so sánh bytes lịch sử. Chỉ xác nhận các bản sao hiện tại bằng đúng bytes trong archive; hash của lượt này là mốc truy vết mới.
- [Keys mới](../data/audit/tv2_raw_keys.csv) dùng ID integral canonical và trim text trên bản sao khi so sánh. Company_specialities có **20** dòng trùng cặp sau trim; raw D03 kiểm tra chuỗi nguyên gốc ghi 0. Đây là khác điều kiện so sánh đã phù hợp findings D04, không phải đã chạy ETL. Employee_counts có **122** dòng trùng cặp company_id/time_recorded. Giữ nguyên tất cả raw.
- Các độ phủ mới so sánh numeric canonical để xử lý company_id dạng `123.0` ở postings và `123` ở companies. Độ phủ có mẫu số theo khóa con, khóa cha và theo tin được tách rõ; xem [JOIN hai chiều](../data/audit/tv2_raw_join_coverage.csv) và [A03](a03_skills_industries_report.md).
- Employee_counts epoch seconds cho min/max UTC đúng `2024-04-05T19:42:53Z` / `2024-04-20T00:27:39Z`; D05 pre-check gắn nhãn UTC cho giờ lệch +7. Giữ ghi chú, chờ TV1 đối chiếu hiển thị/timestamp Parquet.

## Đầu ra và môi trường

- Đã cập nhật [A01](a01_analysis_questions.md): ví dụ cùng job_id, kinh nghiệm, location, cặp loại việc làm, remote và missing, lương/tiền tệ/kỳ trả, timestamp UTC; giữ tám câu hỏi và mẫu số/dependency.
- Đã cập nhật [A03](a03_skills_industries_report.md): đọc đủ nhãn/mapping, ngành doanh nghiệp, khóa/orphan và độ phủ hai chiều, số tin có tên ngành, giao/union nguồn và độ phủ theo tin.
- Audit mới có prefix `tv2_`; **không sửa audit/script D03–D05**. [Profiles](../data/audit/tv2_raw_profiles.json) giữ các giá trị, missing, numeric range, timestamp và derived counts. Mẫu cùng tin đầy đủ ở `data/analytics/tv2_validation/posting_examples.csv`, bị Git ignore.
- Đã tạo `.venv` bằng Python **3.11.9** đã có trên máy; chạy CSV, JSON và taxonomy bằng `.venv\Scripts\python.exe`, chỉ dùng thư viện chuẩn. PySpark chưa cài trong venv; Java trên PATH hiện là **1.8.0_51**, không phải Java 21 trong README. Không dùng Python global 3.13 để chạy công việc.
- Checkout không có Parquet trong `data/processed/clean/` hoặc canonical D05. Không chạy lại ETL hoặc sửa nghiệp vụ TV1. Bộ áp dụng taxonomy dùng chung và mẫu A04 mô tả ở [hướng dẫn A04](a04_manual_labeling.md); Spark/JVM parity và đầu ra production còn chờ TV1.
- `git check-ignore` xác nhận đủ 11 raw, `.venv` và artifact A04 trong `data/analytics/` bị ignore theo `.gitignore` hiện có. Không cần thay ignore; các audit mới nhỏ có thể review trên Git. Không đưa CSV gốc, mô tả đầy đủ hoặc file dự đoán lớn lên Git.

Tái lập kiểm chứng raw, không chạy ETL:

```powershell
.\.venv\Scripts\python.exe src/tv2_verify_raw.py --archive C:\archive
```

Script này có thể cập nhật audit TV2 của lượt kiểm chứng; không overwrite raw khác và không tác động các file nhãn tay A04. Các số kiểm chứng là **toàn dataset raw mọi lĩnh vực**, không phải các phân tích A05–A11 hay tập CNTT được xác nhận.
