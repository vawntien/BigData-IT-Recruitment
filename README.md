# Big Data IT Recruitment

## Mục tiêu

Đồ án xây dựng pipeline Big Data sử dụng Apache Spark để xử lý bộ dữ liệu
LinkedIn Job Postings và xác định các tin tuyển dụng liên quan đến lĩnh vực
Công nghệ thông tin.

Trên tập dữ liệu CNTT sau khi được lọc, hệ thống tiến hành phân tích các khía
cạnh:

- nhóm nghề CNTT;
- kỹ năng tuyển dụng;
- yêu cầu kinh nghiệm;
- địa điểm tuyển dụng;
- hình thức làm việc;
- thông tin lương;
- doanh nghiệp tuyển dụng.

Kết quả phân tích chỉ phản ánh các bản ghi xuất hiện trong bộ dữ liệu được sử
dụng và không được suy rộng thành toàn bộ thị trường lao động Việt Nam hoặc thị
trường lao động của một quốc gia cụ thể.

## Environment

Project được kiểm thử với:

- Python 3.11
- Java OpenJDK 21 LTS (Temurin)
- Apache Spark / PySpark 4.2.0

Spark chạy ở local mode (`local[*]`), vì vậy không cần cài Hadoop hoặc
`winutils.exe` cho smoke test hiện tại.

## Chuẩn bị dataset

1. Tải bộ dữ liệu
   [LinkedIn Job Postings (2023–2024)](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings)
   từ Kaggle.
2. Giải nén dữ liệu đúng cấu trúc vào `data/raw/`, trong đó tệp chính là
   `data/raw/postings.csv` và các tệp liên quan nằm trong `companies/`, `jobs/`
   và `mappings/`.

Dataset gốc không được lưu trên Git. Không chỉnh sửa trực tiếp các tệp trong
`data/raw/`.

## Cài đặt trên Windows

### 1. Kiểm tra Java

```powershell
java -version
$env:JAVA_HOME
```

`JAVA_HOME` phải trỏ đến thư mục cài Java 21, ví dụ:

```text
C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\
```

### 2. Tạo virtual environment bằng Python 3.11

```powershell
py -3.11 -m venv .venv
```

Không bắt buộc activate môi trường. Cài dependency trực tiếp bằng Python của
project để tránh dùng nhầm Python global hoặc Python của Laragon:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Nếu muốn activate nhưng `Activate.ps1` bị ExecutionPolicy chặn, chỉ thay đổi
policy cho tiến trình PowerShell hiện tại (tùy chọn):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Không thay đổi ExecutionPolicy ở phạm vi hệ thống.

### 3. Xác minh môi trường

```powershell
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"
.\.venv\Scripts\python.exe -c "import pyspark; print(pyspark.__version__)"
```

### 4. Chạy Spark smoke test

Đảm bảo dataset đã được đặt tại `data/raw/`, sau đó chạy:

```powershell
.\.venv\Scripts\python.exe .\src\smoke_test.py
```

Kết quả kỳ vọng cho phiên bản dataset hiện tại:

```text
Spark version: 4.2.0
Number of columns: 31
Total rows: 123849
Smoke test completed successfully.
```

Cảnh báo về `winutils.exe` hoặc native Hadoop trên Windows là không chặn nếu
smoke test vẫn hoàn thành trong local mode.
