# Demo Design V01.3 — Q01–Q08, khoảng 5 phút

## 1. Nguồn và trạng thái

Ngày: **19/10/2026**. **DECIDED BY TV3:** Chốt bảy bước Home -> Overview -> filters -> Skills -> Salary -> Quality -> Conclusion, giữ flow hữu ích của bản nháp cũ. Nội dung theo A01 TV2 cập nhật 08/10 và [wireframe V01.3](dashboard_wireframe.md); source/version/hash ghi tại mục 1 wireframe.

Đây là **thiết kế demo**, không chứng nhận tất cả section đã chạy. Baseline V02 `60b0bb2` chưa có Q05/Q08, remote riêng hoặc thống kê Q07 mới. Section chưa triển khai chỉ trình bày bằng wireframe, ghi “thiết kế dự kiến”, không nói đã thao tác trong app. Kịch bản V09/V11 chỉ điền findings sau nghiệm thu.

**PENDING TV2:** A02/A03, A05/A06/A07/A08, phép đo và denominator. **PENDING TV1:** D05/D06/D07, T/N/grain, audit, UTC/snapshot và acceptance. **FUTURE IMPLEMENTATION:** V03–V06. PENDING không phải đã ký duyệt.

## 2. Chọn nhánh theo nguồn thực nạp

**DECIDED BY TV3:** Đọc banner/provenance từng section trước khi nói, không suy nguồn từ trạng thái checkbox.

| Nhánh | Điều kiện / lời diễn giải |
| --- | --- |
| UI demo — SYNTHETIC_SAMPLE | Nguồn thực nạp là sample. Nói “Dữ liệu giả định chỉ minh họa giao diện”; count, %, ranking không là findings |
| PRODUCTION analytics | Output/version/scope/denominator/checks được TV1/TV2 bàn giao và xác nhận; chỉ nhận xét trong dataset/run đang trình bày |
| MISSING / dữ liệu không dùng được | Nói section chưa có dữ liệu dùng được và dependency còn chờ; không coi là 0 tin/không có nhu cầu |

**CODE baseline:** Loader ưu tiên production rồi fallback sample; bật Sample không ép dùng sample nếu production nạp được. Enum hiện là SAMPLE kèm banner synthetic; SYNTHETIC_SAMPLE là nhãn provenance thiết kế. Muốn demo MISSING chỉ thực hiện khi thực sự không có production dùng được và không dùng sample; không xóa/đổi tên data để dựng trạng thái.

Audit raw lịch sử có scope/thời điểm riêng, không kế thừa banner Salary. Section chưa có output/implementation thì dùng wireframe, không bịa số. Placeholder [GIÁ TRỊ ĐÃ XÁC NHẬN] chỉ được thay sau nghiệm thu; không lấy từ sample.

## 3. Flow bảy bước

### Bước 1 — Home, 0:00–0:35

- **Thao tác:** Giới thiệu ba pages, sơ đồ `raw -> Spark -> analytics -> Streamlit` và trạng thái bàn giao có nguồn.
- **Mục tiêu:** Giới hạn dataset LinkedIn Job Postings (2023–2024), tập CNTT sau D06. Raw count không phải N.
- **Sample:** “Buổi này minh họa UI bằng dữ liệu giả định, chưa trình bày kết quả tuyển dụng thật.”
- **Production:** “Kết quả thuộc dataset/run [VERSION], taxonomy [VERSION], trong tập tin được xác nhận CNTT.” Chỉ nói khi có bằng chứng.
- **Missing:** “Đầu ra chưa sẵn sàng; hiện trình bày thiết kế và dependency.”
- **Không nói:** Pipeline production hoàn thành hoặc dataset đại diện toàn bộ thị trường Việt Nam/quốc gia khác khi chưa xác minh.

### Bước 2 — Overview: cơ cấu và thời gian, 0:35–1:25

- **Thao tác:** Đọc banner/scope; giới thiệu Q01 nhóm nghề, Q02 nhãn kinh nghiệm, Q03 Top location, Q04 employment và remote riêng; tab Thời gian Q08. Phần mới chưa có trong UI chỉ trình bày wireframe.
- **Mục tiêu:** Đọc count distinct, denominator, missing/coverage. Q08 dùng original_listed_time chính, listed_time đối chiếu, tuần ISO/tháng UTC, kỳ biên không trọn vẹn.
- **Sample:** “Các giá trị chỉ giúp minh họa cách đọc, không phản ánh phân bố thật.”
- **Production:** “N là [GIÁ TRỊ ĐÃ XÁC NHẬN]; mỗi tỷ lệ có mẫu số tại section; đây là phân bố trong dataset.”
- **Missing:** Nêu section/nguồn thiếu, không đọc giá trị thay thế.
- **Không nói:** Nhãn cấp bậc là số năm; NULL remote là onsite; work type là chế độ remote; Q08 là xu hướng toàn thị trường hoặc chênh lệch hai mốc là đăng lại.

### Bước 3 — Overview: filter / empty / missing, 1:25–1:55

- **Thao tác:** Chọn nhóm trong danh sách thực tế, experience/location nếu aggregate hỗ trợ; đọc lại scope/count/denominator rồi Reset. Chỉ minh họa MISSING khi điều kiện ở mục 2 đúng.
- **Mục tiêu:** Phân biệt filter business đổi tập và Top-k/tuần-tháng chỉ đổi trình bày. Không mặc định state đồng bộ sang Skills/Salary.
- **Sample:** “Ta kiểm tra tương tác UI, không rút kết luận về cơ hội việc làm.”
- **Production:** “Trong [FILTER], count là [GIÁ TRỊ], denominator là [TẬP ĐƯỢC GHI RÕ].” Không dùng KPI lương hard-code của baseline như số sau lọc.
- **Missing:** Chưa có dữ liệu dùng được; empty-result chỉ là không có bản ghi khớp filter trong nguồn này.
- **Không nói:** Mọi tổ hợp filter đều hỗ trợ; hành vi bỏ hết lựa chọn đã giống thiết kế mới khi code chưa triển khai; MISSING nghĩa là không có nhu cầu.

### Bước 4 — Skills: Q05 khác Q06, 1:55–2:50

- **Thao tác:** Tab Nhãn chức năng/lĩnh vực Q05 -> tab Kỹ năng công nghệ Q06; xem ranking/count/denominator/coverage và matrix nhóm. Q05 chưa có thì dùng wireframe.
- **Mục tiêu:** Q05 dùng tin có ít nhất một nhãn mapping hợp lệ làm mẫu số. Q06 dùng description xử lý thành công, **kể cả zero-skill**. Tổng tỷ lệ nhiều nhãn/skill có thể >100%.
- **Sample:** “Tên và thứ hạng kỹ năng mockup không là kết quả trích xuất thật.”
- **Production:** Nêu method/dictionary version, count, denominator và processing coverage đã bàn giao. Dùng “được nhắc đến”, không tự gọi là bắt buộc.
- **Missing:** Trình bày phương pháp dự kiến/dependency; không nhận nhãn IT/ENG thành Python/SQL.
- **Không nói:** A05 parity 105 mẫu phát triển chứng minh production output; skill đứng đầu dataset là skill được săn đón nhất toàn thị trường; pivot baseline đã theo filter khi code dùng toàn df.

### Bước 5 — Salary: Q07, 2:50–3:45

- **Thao tác:** Chọn nhóm nghề, experience, một bộ currency/pay_period/compensation_type được hỗ trợ. Đọc hai panel min_salary/max_salary riêng, P25/P50/P75/IQR/n/coverage. Nếu chưa triển khai thì chỉ wireframe.
- **Mục tiêu:** So sánh cùng đơn vị/strata; P50 là thống kê trên giá trị từng cột. n_min/n_max có thể khác; denominator coverage gồm tin thiếu lương trong nhóm.
- **Sample:** “Đây là cách trình bày phân vị dự kiến, không phải lương thật.”
- **Production:** “Trong [BỘ ĐƠN VỊ] và [NHÓM/EXPERIENCE], min_salary có [n_min], P50 [GIÁ TRỊ], IQR [GIÁ TRỊ]; max_salary có bộ thống kê riêng.” Chỉ đọc output D07/A08 xác nhận, kèm coverage/cỡ mẫu.
- **Missing:** Không tính thay phân vị; nêu output D07/A08 hoặc tổ hợp chưa hỗ trợ.
- **Không nói:** med_salary nguồn là median thống kê; min/max quan sát là IQR; median các median là median toàn tập; tiêu đề USD/Năm chứng minh code đã lọc USD; lương có công bố đại diện mọi tin.

### Bước 6 — Quality, 3:45–4:30

- **Thao tác:** Phân biệt raw/clean audit lịch sử và IT production quality; đọc scope/artifact/thời điểm từng section.
- **Mục tiêu:** Giải thích missing/orphan/rejected/encoding, grain, description/salary/time coverage. Số dòng bảng con không tự bằng số tin.
- **Sample:** “Analytics đang giả định; audit lịch sử nếu có là nguồn riêng, không phải IT metrics vừa tính.”
- **Production:** Chỉ đọc audit có run/artifact/checks được xác nhận, nêu ảnh hưởng/giới hạn Q01–Q08.
- **Missing:** IT quality chưa có output thì ghi MISSING, không lấp bằng raw hard-code.
- **Không nói:** 123,849 là số tin IT; 29.13% là độ phủ IT hiện tại; mọi JOIN production đã chống nhân dòng chỉ vì có pre-check/scaffold.

### Bước 7 — Conclusion / Home, 4:30–5:00

- **Thao tác:** Quay Home, nhắc tám câu và trạng thái nguồn đã dùng.
- **Sample:** “Đã minh họa thiết kế/tương tác; kết quả thật còn chờ bàn giao và nghiệm thu.”
- **Production:** “Nhận xét chỉ áp dụng cho dataset/run và scope đã nêu, theo phương pháp/coverage công bố.” Chỉ tổng kết findings đã xác nhận, không thêm kết luận mới.
- **Missing:** “Đã trình bày cấu trúc và dữ liệu còn chờ; section thiếu chưa có kết quả.”
- **Không nói:** V01 PASS, mọi task hoàn tất hoặc sample là bằng chứng kết quả đồ án.

## 4. Nội dung nháp cũ giữ / thay thế

| Nội dung cũ | Quyết định V01.3 |
| --- | --- |
| Flow bảy bước, điều hướng/tab, sơ đồ pipeline, cảnh báo sample và placeholder | Giữ — DECIDED BY TV3 |
| FINAL VALUE FROM A06/A07/A08 | Chỉ điền sau acceptance, thêm scope/denominator/version — PENDING TV1/TV2 |
| “Kết nối trực tiếp bảng đã xử lý”, “đã áp dụng Spark Regex”, “đã giải quyết triệt để row explosion” | SUPERSEDED như lời thoại mặc định: chỉ khẳng định phần có bằng chứng, không dùng ở sample/missing |
| “Kỹ năng được săn đón hàng đầu trên thị trường hiện nay”, “nắm bắt chính xác cơ hội việc làm thực tế” | SUPERSEDED: mô tả nhắc đến/phân bố trong dataset theo giới hạn A01 |
| Salary min–median–max chung, mặc định USD/năm | SUPERSEDED: hai bộ phân vị riêng, đơn vị thực được chọn và hỗ trợ |
| Audit hard-code là trạng thái IT hiện tại | SUPERSEDED: audit lịch sử/raw khác IT production, provenance riêng |

## 5. Dependency, V03 và điều kiện tổng duyệt

- **DECIDED BY TV3:** Flow, nhánh sample/production/missing, từ ngữ và thứ tự/bố cục.
- **PENDING TV2:** AWAITING OFFICIAL A02 ARTIFACT (9 nhóm, IT_OTHER, SOFTWARE subgroups), A03 semantics, A05 parity 105 mẫu kèm artifact/version mới; A06/A07/A08 và denominator. A01 08/10 còn ghi A05 chưa triển khai, cần đối soát thời điểm.
- **PENDING TV1:** D05/D06 T/N/grain, D07 lương, timestamp UTC/snapshot, audit và production acceptance.
- **FUTURE IMPLEMENTATION:** V03 contract; V04 Q01–Q04/Q08; V05 Q05/Q06; V06 Q07/Quality. Section chưa có thì không hứa thao tác live.
- **V03 CONTRACT QUESTIONS:** Mục 11 [wireframe](dashboard_wireframe.md): grain/filter capability, numerator/denominator, zero-skill, quantile min/max riêng, remote, UTC, taxonomy/version, provenance và validation. Chưa sửa contract draft.

Trước tổng duyệt, kiểm tra nguồn thực nạp từng section, control/aggregate sẵn có, version/acceptance và lời thoại tương ứng. Demo baseline không là acceptance test cho thiết kế đích. Bản thiết kế: **READY FOR TEAM DESIGN REVIEW**, không tự đánh V01 PASS.
