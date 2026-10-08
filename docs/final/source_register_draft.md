# Source and Citation Register (Danh mục Nguồn Dữ liệu và Tài liệu Tham khảo)

> [!NOTE]
> **DANH MỤC TRÍCH DẪN CHUẨN XÁC THEO TÀI LIỆU DỰ ÁN.**  
> Tuyệt đối không tự suy diễn các liên kết ngoài chưa được khai báo trong repository. Các mục cần bổ sung được đánh dấu `[TODO]`.

---

## 1. Nguồn Dữ liệu Chính (Primary Dataset)

1. **Bộ dữ liệu Tuyển dụng LinkedIn (LinkedIn Job Postings 2023–2024):**
   - **Tác giả:** Arsh Koneru
   - **Nguồn:** Kaggle
   - **URL công bố:** `https://www.kaggle.com/datasets/arshkon/linkedin-job-postings`
   - **Ngày tiếp nhận:** 04/10/2026
   - **Quy mô:** 11 tệp CSV (~530.72 MB), 123,849 tin tuyển dụng
   - **Giấy phép sử dụng:** Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
   - **URL Giấy phép:** `https://creativecommons.org/licenses/by-sa/4.0/`
   - **Bằng chứng trong dự án:** [docs/data_manifest.md](file:///d:/Learning/Bigdata/BigData-IT-Recruitment/docs/data_manifest.md)

---

## 2. Nền tảng Công nghệ & Thư viện (Core Technologies)

2. **Apache Spark:**
   - **Phiên bản sử dụng:** Apache Spark 4.2.0 (PySpark)
   - **Tài liệu tham khảo:** Apache Spark Documentation (Spark SQL, DataFrames and Streaming)
   - **URL:** `https://spark.apache.org/docs/latest/`
   - **Vai trò trong dự án:** Công cụ tính toán phân tán chính để kiểm kê dữ liệu (D03), làm sạch và chuyển đổi schema (D04), và tích hợp khóa bảo toàn grain (D05).

3. **Môi trường Thực thi Java:**
   - **Phiên bản:** Eclipse Temurin OpenJDK 21 LTS (HotSpot)
   - **Vai trò:** Máy ảo Java (JVM) nền tảng để chạy Apache Spark trên Windows.

4. **Nền tảng Trực quan hóa Giao diện (Streamlit):**
   - **Phiên bản sử dụng:** Streamlit 1.38.0
   - **Tài liệu tham khảo:** Streamlit Documentation
   - **URL:** `https://docs.streamlit.io/`
   - **Vai trò trong dự án:** Xây dựng dashboard phân tích đa trang tương tác (TV3).

---

## 3. Các Nguồn Tham khảo Nghiệp vụ & Taxonomy CNTT (Sắp bổ sung)

5. **Phân loại Ngành nghề LinkedIn (LinkedIn Industry Classifications):**
   - **Mô tả:** Bảng ánh xạ 422 mã ngành nghề (`data/processed/clean/industries/`).
   - **URL / Tài liệu gốc:** `[TODO: TV2 bổ sung tài liệu định nghĩa industry taxonomy]`

6. **Hệ thống Phân loại Kỹ năng CNTT (IT Skills Taxonomy):**
   - **Mô tả:** Từ điển từ khóa kỹ năng kỹ thuật (Python, SQL, Java, AWS...) và ranh giới từ phục vụ trích xuất từ văn bản mô tả.
   - **Nguồn tham khảo:** `[TODO: TV2 bổ sung nguồn từ điển chuẩn O*NET hoặc tiêu chuẩn tuyển dụng tại A02]`

7. **Tiêu chuẩn Báo cáo Mức lương Lao động:**
   - **Mô tả:** Phương pháp tính toán phân vị lương (Median, Interquartile Range) trong thống kê thị trường lao động.
   - **Tài liệu:** `[TODO: Bổ sung tài liệu phương pháp thống kê tại D07/A08]`
