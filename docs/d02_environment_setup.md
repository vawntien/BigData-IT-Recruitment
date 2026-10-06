# D02 - Thiết lập môi trường Spark

## Môi trường đã xác minh

| Thành phần | Giá trị |
| --- | --- |
| OS | Windows |
| Python | 3.11.0, chạy từ `.venv` của project |
| Java | OpenJDK 21.0.12.1 LTS, Eclipse Temurin |
| PySpark | 4.2.0 |
| Spark master | `local[*]` |

Không cần activate virtual environment. Các lệnh Python và pip của project được
chạy trực tiếp qua `.venv\Scripts\python.exe`, tránh sử dụng Python global hoặc
Python 3.13 của Laragon.

## Dataset dùng cho smoke test

- Bộ dữ liệu: LinkedIn Job Postings (2023–2024)
- Đường dẫn nguồn trong project: `data/raw/postings.csv`
- Số cột: 31
- Số dòng: 123849

Dataset gốc được ignore khỏi Git và không bị thay đổi trong quá trình thiết lập
môi trường.

## Kết quả xác minh

Spark smoke test tạo `SparkSession` với app name
`BigDataITRecruitment-SmokeTest`, chạy ở `local[*]`, đọc tệp CSV với schema dạng
string, in schema và dữ liệu mẫu, rồi đếm toàn bộ bản ghi.

Trạng thái: **PASS**

Kết quả kỳ vọng và đã xác minh:

```text
Spark version: 4.2.0
Number of columns: 31
Total rows: 123849
Smoke test completed successfully.
```

Trên Windows có thể xuất hiện cảnh báo về `winutils.exe` hoặc native Hadoop.
Cảnh báo này là non-blocking trong local mode hiện tại nếu smoke test vẫn hoàn
thành; chưa cần cài Hadoop/winutils.
