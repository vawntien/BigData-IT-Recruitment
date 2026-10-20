# A06–A11 — kế hoạch kết quả theo tám câu hỏi A01

Ngày 19/10/2026. Đây là phương pháp/cấu trúc candidate, không phải kết luận thị trường. Kế thừa A01; không đổi câu hỏi, taxonomy hoặc nhãn A04. D05 canonical đã được TV2 đọc bằng Spark: 123.849 job, 50 cột. **N của IT vẫn CHƯA XÁC NHẬN**, vì D06 chưa Full. D07 chưa có output chính thức.

| Câu hỏi | Chuẩn bị mã/nguồn | Mẫu số và độ phủ | Biểu đồ/tài liệu cần xuất khi có run được xác minh |
| --- | --- | --- | --- |
| Q01 Nhóm nghề | D06.primary_group_code; `analyze_frames` | N IT, distinct job_id; giữ nhóm thiếu riêng | Cột ngang số tin/tỷ trọng từng nhóm, ghi N và taxonomy hash |
| Q02 Kinh nghiệm | formatted_experience_level string | N có mục thiếu; tỷ trọng có nhãn thêm mẫu số known | Cột ngang nhãn nguồn + thiếu; không đổi thành số năm |
| Q03 Địa điểm | location string | distinct tin có location hợp lệ; coverage known/N | Top-k chuỗi location; ghi phần còn lại và thiếu; chưa dựng bản đồ quốc gia khi chưa parse được xác nhận |
| Q04 Việc làm/remote | formatted_work_type/work_type; nullable boolean remote_allowed | N, true/false/NULL riêng | Cột loại việc, đối chiếu hai nhãn; panel remote ba giá trị, không suy hybrid/onsite |
| Q05 Chức năng nguồn | D05.job_functions hoặc clean bridge được TV1 chốt | distinct tin có nhãn mapping dùng được; coverage/N | Cột đa nhãn, tổng % có thể vượt 100%; bảng unmapped riêng, không gọi nhãn LinkedIn là kỹ năng công nghệ |
| Q06 Kỹ năng | A05 bridge + source processing cùng run/dictionary | PROCESSED_WITH_MATCH + PROCESSED_NO_MATCH; mẫu số từng nhóm/level cũng gồm zero-hit | Cột kỹ năng toàn tập, heatmap theo nhóm/kinh nghiệm khi đủ dữ liệu; panel source statuses; missing/failed/partial không biến thành zero-hit |
| Q07 Lương | D07.salary_clean + chính sách duyệt | n hợp lệ theo nhóm/level/currency/pay_period/compensation_type/source; coverage/N | Bảng n và Q1/median/Q3 của **min riêng, max riêng**; panel tách đơn vị/nguồn. Không dùng chúng như phân phối lương thực trả hoặc lấy trung điểm |
| Q08 Thời gian | original_listed_time và listed_time TimestampType UTC | số tin có từng timestamp; coverage/N | Hai chuỗi cột theo tháng/tuần UTC riêng; ghi kỳ biên, missing, phạm vi nguồn. Không suy tăng trưởng thị trường |

Mã truy vấn hiện hữu: [a06_a08_spark_analysis.py](../src/a06_a08_spark_analysis.py). Trước official: kiểm một dòng/job_id, schema, receipts/hash, taxonomy provenance; chỉ JOIN bridge trên nhánh riêng. Không tạo nhãn IT từ canonical hoặc bỏ gate D06. Phân tích lương không dùng các cột D05 thay D07 chỉ vì chúng đã có kiểu decimal.

## Chuẩn bị Q05 từ schema D05

[Adapter candidate](../src/d05_job_functions_adapter.py) nhận canonical và danh sách job_id đã được caller xác nhận. Semi-JOIN giữ job grain; explode chỉ trong nhánh chức năng; distinct job_id/skill_abr; mapping duy nhất theo code. Giữ missing-label code, bỏ NULL array khỏi nhánh bridge (không khẳng định tin không cần kỹ năng); từ chối ID null/trùng/orphan, mapping mâu thuẫn hoặc trạng thái không hợp lệ. Không sửa canonical.

Adapter chưa gắn vào preflight official. TV1 cần chốt `job_functions` là nguồn authoritative hoặc giao clean job_skills/skills có checksum; xác nhận selected IDs là D06 official. Không tự điền approval. Bộ kiểm tra D05 dùng 105 job_id phát triển chỉ để đối chiếu source hash/schema/JOIN, không tính Q05 toàn IT.

## A09 — khuôn nhận xét

Mỗi Q01–Q08 có một đoạn: câu hỏi → bảng/manifest/hash → tử số/mẫu số/coverage → nhận xét mô tả → giới hạn. Khi có số liệu, chọn 5–8 nhận xét có căn cứ, tránh diễn giải nhân quả. Hiện tất cả giá trị IT/lương ghi **CHỜ INPUT CHÍNH THỨC**. Không lấy 355/661/105 từ parity làm số liệu kỹ năng thị trường.

## A10 — cấu trúc báo cáo

1. Phạm vi dataset và các câu hỏi A01.
2. Provenance D05/D06/D07, grain, schema, timestamp và text nguồn.
3. Phương pháp: mẫu số, missing/zero-hit, nhánh JOIN, kỹ năng có evidence, lương tách đơn vị.
4. Kết quả Q01–Q08: mỗi mục có bảng/biểu đồ đã lưu, run ID và kiểm tra coverage.
5. Thảo luận: chỉ số mô tả, giới hạn đại diện/thiếu/mapping/nhãn, không suy toàn thị trường.
6. Phụ lục schema, receipts, phiên bản code/dictionary, log và truy vấn tái chạy.

## A11 — storyboard 10 slide và ghi chú nói

| Slide | Nội dung | Hình dự kiến / ghi chú |
| --- | --- | --- |
| 1 | Mục tiêu và tám câu hỏi | Sơ đồ dữ liệu → câu hỏi → phân tích; giới hạn dataset |
| 2 | D05 đã tiếp nhận; D06/D07 chờ | Pipeline có trạng thái; 123.849 là canonical, không là N IT |
| 3 | Xác định tập IT | Hồ sơ taxonomy đã có; không chạy lại A04 hoặc tự promote candidate |
| 4 | Kỹ năng có bằng chứng | Mô tả nguồn → alias/context → evidence → bridge; workbook skill còn là đề nghị |
| 5 | Tổng quan IT và chất lượng | N/coverage/source statuses: CHƯA XÁC NHẬN |
| 6 | Q01 Nhóm nghề | Cột ngang; taxonomy hash và mẫu số |
| 7 | Q02–Q04 | Ba panel kinh nghiệm/địa điểm/việc làm, remote NULL riêng |
| 8 | Q05 và Q06 | Hai panel chức năng nguồn/kỹ năng công nghệ; không lẫn hai namespace |
| 9 | Q07 và Q08 | Lương cùng đơn vị/nguồn; hai thời điểm UTC; chờ D07/D06 |
| 10 | Kết luận và giới hạn | 3 ý chỉ điền sau số liệu đã kiểm; hỏi đáp zero-hit, coverage, đại diện |

[Bộ A09/A10/10 slide HTML và ghi chú mới](../data/analytics/tv2_a06_a11_prepared_20261019/reports/a11_slides.html) dùng lại renderer, bổ sung Q05 và bỏ câu trạng thái canonical thiếu đã lỗi thời. Chưa vẽ biểu đồ số giả. Gate công bố vẫn yêu cầu OFFICIAL SUCCESS và hash bảng đã lưu; người duyệt/V10 của TV3 còn cần đối soát.
