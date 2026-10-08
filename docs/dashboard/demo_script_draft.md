# Demo Script Draft: Kịch bản Thuyết trình Demo (3–5 Phút)

> [!NOTE]
> **KỊCH BẢN THỬ NGHIỆM PHỤC VỤ CHUẨN BỊ BẢO VỆ ĐỒ ÁN (V09/V11)**  
> *Lưu ý quan trọng:* Toàn bộ các con số phân tích chuyên sâu bên dưới được đánh dấu bằng các biến giữ chỗ `[FINAL VALUE FROM ...]`. Tuyệt đối không dùng số liệu từ tệp mẫu giả định (sample data) làm kết luận trong buổi thuyết trình chính thức.

---

## 1. Giới thiệu Mục tiêu & Bối cảnh (0:00 – 0:45)

- **Người nói:** TV3 (hoặc đại diện nhóm).
- **Màn hình hiển thị:** Trang chủ `dashboard/app.py`.
- **Nội dung nói:**
  > *"Kính thưa thầy cô và các bạn, đồ án của nhóm chúng em xây dựng một pipeline Big Data toàn diện sử dụng Apache Spark để xử lý bộ dữ liệu hơn 123,000 tin tuyển dụng từ LinkedIn. Mục tiêu là phân tích chuyên sâu về nhu cầu nhân lực ngành Công nghệ Thông tin: từ cơ cấu nhóm nghề, yêu cầu kỹ năng kỹ thuật, cho đến dải lương tuyển dụng thực tế. Đây là giao diện trực quan hóa tương tác của nhóm, được xây dựng trên nền tảng Streamlit, kết nối trực tiếp với các bảng dữ liệu tổng hợp đã qua xử lý phân tán từ Spark."*

---

## 2. Trang Tổng quan: Cơ cấu Tuyển dụng (0:45 – 1:30)

- **Thao tác:** Bấm chọn trang **`1_Overview`** trên thanh điều hướng.
- **Màn hình hiển thị:** Các thẻ KPI và biểu đồ phân bố việc làm.
- **Nội dung nói:**
  > *"Tại trang Tổng quan, hệ thống cung cấp các chỉ số toàn cảnh về thị trường việc làm CNTT trong tập dữ liệu.  
  > Tổng số tin tuyển dụng hợp lệ trong phân khúc CNTT là `[FINAL VALUE FROM A06]` tin. Trong đó, nhóm ngành dẫn đầu về nhu cầu tuyển dụng là `[FINAL VALUE FROM A06]`, chiếm khoảng `[FINAL VALUE FROM A06]%`.  
  > Phía dưới là các biểu đồ phân bố theo cấp bậc kinh nghiệm: phần lớn các tin tuyển dụng tập trung ở phân khúc `[FINAL VALUE FROM A06]`, và địa điểm tập trung nhiều cơ hội việc làm nhất là `[FINAL VALUE FROM A06]`."*

---

## 3. Thao tác Tương tác với Bộ lọc (1:30 – 2:00)

- **Thao tác:** Trên thanh bên trái (Sidebar), bỏ chọn một số nhóm nghề, chỉ giữ lại `Data & AI` (hoặc `Software Engineering`), sau đó chọn cấp bậc `Entry level`.
- **Màn hình hiển thị:** Các chỉ số KPI và biểu đồ lập tức cập nhật theo thời gian thực.
- **Nội dung nói:**
  > *"Người dùng có thể dễ dàng lọc dữ liệu theo nhu cầu phân tích cụ thể. Ví dụ: Khi chúng ta lọc riêng nhóm ngành Data & AI ở cấp độ Entry level, tổng số tin tuyển dụng còn lại là `[FINAL VALUE FROM A06]` tin. Điều này giúp các ứng viên mới ra trường hoặc các nhà hoạch định đào tạo nắm bắt chính xác cơ hội việc làm thực tế."*

---

## 4. Trang Kỹ năng Tuyển dụng (2:00 – 2:45)

- **Thao tác:** Chuyển sang trang **`2_Skills`**.
- **Màn hình hiển thị:** Biểu đồ Top 15 kỹ năng kỹ thuật và bảng ma trận kỹ năng.
- **Nội dung nói:**
  > *"Bước sang trang Phân tích Kỹ năng: Nhóm xin nhấn mạnh một phát hiện quan trọng trong dữ liệu gốc là trường `job_skills` chỉ chứa các nhóm chức năng nghề nghiệp tổng quát, chứ không có tên kỹ năng lập trình cụ thể. Vì vậy, nhóm chúng em đã áp dụng phương pháp trích xuất từ khóa kỹ thuật trực tiếp từ văn bản mô tả công việc (Job Description) bằng thuật toán Spark Regex Matching.  
  > Kết quả cho thấy: Kỹ năng kỹ thuật được săn đón hàng đầu trên thị trường hiện nay là `[FINAL VALUE FROM A07]`, xuất hiện trong `[FINAL VALUE FROM A07]%` các tin tuyển dụng, tiếp theo là `[FINAL VALUE FROM A07]` và `[FINAL VALUE FROM A07]`."*

---

## 5. Phân tích Mức lương Tuyển dụng (2:45 – 3:30)

- **Thao tác:** Chuyển sang trang **`3_Salary_Quality`**, mở Tab **"Phân tích Mức lương"**.
- **Màn hình hiển thị:** Biểu đồ mức lương trung vị theo nhóm nghề và dải lương min-median-max.
- **Nội dung nói:**
  > *"Về khía cạnh mức lương: Để đảm bảo tính chính xác và khoa học, hệ thống tuân thủ nguyên tắc không quy đổi mù quáng giữa các loại tiền tệ và không gộp chung lương theo giờ với lương theo năm.  
  > Xét riêng trên phân nhóm tiền tệ USD và kỳ trả lương theo năm: Nhóm nghề có mức lương trung vị cao nhất là `[FINAL VALUE FROM A08]` với mức trung vị đạt `[FINAL VALUE FROM A08] USD/năm`. Dải lương phổ biến dao động từ `[FINAL VALUE FROM A08] USD` đến `[FINAL VALUE FROM A08] USD`."*

---

## 6. Sức khỏe Dữ liệu & Quy trình Xử lý Big Data (3:30 – 4:15)

- **Thao tác:** Chuyển sang Tab **"Sức khỏe Dữ liệu (Data Quality)"**.
- **Màn hình hiển thị:** 4 thẻ chỉ số audit, bảng missingness và referential integrity.
- **Nội dung nói:**
  > *"Một điểm nổi bật trong đồ án của nhóm là sự minh bạch tuyệt đối về chất lượng dữ liệu. Bộ dữ liệu thô ban đầu gồm 123,849 tin tuyển dụng, nhưng chỉ có 29.13% tin có công bố lương, và có 16 trường dữ liệu có tỷ lệ khuyết thiếu trên 20%.  
  > Nhóm đã xây dựng pipeline làm sạch tự động bằng Spark: Sửa chữa 83 lỗi mã hóa ký tự Mojibake, loại bỏ và cách ly 142 bản ghi trùng lặp khóa luận lý mà không làm mất mát dữ liệu. Đặc biệt, hệ thống áp dụng cơ chế 'Aggregate-Before-Join' để giải quyết triệt để vấn đề nhân bản dòng (Row Explosion) khi kết hợp các quan hệ nhiều-nhiều."*

---

## 7. Kết luận & Mở phiên Hỏi đáp (4:15 – 4:45)

- **Thao tác:** Quay về trang chủ `app.py`.
- **Nội dung nói:**
  > *"Tóm lại, ứng dụng không chỉ cung cấp góc nhìn trực quan sâu sắc về thị trường tuyển dụng CNTT mà còn minh chứng cho năng lực xử lý dữ liệu lớn mạnh mẽ, chuẩn hóa và đáng tin cậy của Apache Spark. Chúng em xin chân thành cảm ơn thầy cô và sẵn sàng tiếp nhận các câu hỏi phản biện."*
