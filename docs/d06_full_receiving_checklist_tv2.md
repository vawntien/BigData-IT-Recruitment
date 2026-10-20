# Hợp đồng nhận D06 Full — checklist TV2 gửi TV1

19/10/2026. **Candidate, chờ TV1 xác nhận**; không phải chứng nhận D06 đã chạy. D05 được nhận tại `data/processed/canonical/jobs/`, commit TV1 `457f90ae`; không dùng toàn bộ 123.849 job canonical làm IT. Không chạy lại A04 hoặc tự promote candidate v0.2.2.

## Hiện vật TV1 cần bàn giao

- [ ] Commit producer D06, đường dẫn Parquet IT jobs, schema Spark JSON, số part/byte/checksum từng part và digest cả thư mục.
- [ ] Người/ngày phê duyệt thực tế, run_id, thời gian UTC, phiên bản Python/Java/Spark, timezone, code/config SHA-256 exact bytes.
- [ ] Manifest xử lý Full: 123.849 canonical ID được đối soát đúng một lần; counts ACCEPT/REJECT/REVIEW/errors hoặc trạng thái xử lý khác có định nghĩa, cộng khớp tổng; error không biến thành REJECT. Trace giữ REVIEW riêng; IT jobs chỉ ACCEPT/true, không override bằng nhãn mẫu A04.
- [ ] Taxonomy version + config snapshot/path/hash, classifier implementation/path/hash, input-column bindings và kết quả kiểm tra/parity do TV1 cung cấp. Gói tham chiếu A04 176 ID đã có; TV2 không chạy lại nó trong lượt này.
- [ ] Báo cáo validation/hash: job_id bigint duy nhất/không NULL; số IT đúng số ACCEPT; keys là subset canonical; nguồn text/hash khớp; schema, NULL/coverage, timestamp UTC, không nhân dòng JOIN, source inputs không thay đổi.
- [ ] Xác nhận hai quyết định nguồn text/Q05 dưới đây. Không ký thay hoặc tự điền approval vì đã có code/test.

Mẫu máy đọc: [d06_handoff_contract.example.json](../config/d06_handoff_contract.example.json). Mọi approval/path/hash D06 chưa có giữ NULL. Digest thư mục dùng `artifact_digest`: danh sách file đệ quy sắp xếp theo relative path, mỗi mục `[path,size,sha256]`, JSON compact UTF-8 rồi SHA-256; bao gồm cả marker. TV1 có thể gửi checksum từng part để TV2 tự tính digest theo cùng thuật toán.

## Schema tối thiểu cho A05–A08

Định nghĩa máy đọc tại `REQUIRED_TYPES` trong [d06_handoff_validation.py](../src/d06_handoff_validation.py). Không bắt D06 phải có đúng 50 cột; 50 là schema D05, D06 thêm provenance/decision/group và có thể giữ toàn bộ cột D05.

| Cột | Kiểu Spark | Invariant / cách dùng |
| --- | --- | --- |
| job_id | bigint | Không NULL/trùng; thuộc D05; grain một tin |
| it_decision, is_it | string, boolean | Chỉ ACCEPT/true trong IT jobs; REVIEW/REJECT giữ ở trace riêng |
| taxonomy_version, taxonomy_sha256 | string | Một cặp được duyệt, không NULL/rỗng; khớp snapshot/config và code provenance |
| primary_group_code | string nullable | Q01/Q06/Q07; thiếu báo riêng, không tự ép thành nghề khác |
| description | string nullable | Giữ rõ ý nghĩa clean/source; không âm thầm coi text sạch là nguyên văn |
| source_description, source_title | string nullable | Bản parsed CSV nguyên văn do D05 giữ; không HTML-strip/trim/normalize trước đối chiếu |
| source_description_sha256, source_title_sha256 | string | SHA-256 UTF-8 parsed fields; khớp source columns và D05 theo job_id |
| formatted_experience_level | string nullable | Q02/Q06/Q07; không suy số năm |
| location | string nullable | Q03; không thay bằng địa chỉ công ty |
| formatted_work_type, work_type | string nullable | Q04 và đối chiếu nhãn |
| remote_allowed | boolean nullable | Giữ true/false/NULL; thiếu không phải onsite |
| original_listed_time, listed_time | timestamp nullable | UTC, hai ý nghĩa riêng cho Q08; không tự cast epoch/string lại |

`title`, company và các cột D05 khác nên giữ để trace/report; `job_functions` theo contract Q05. Nullable trong Parquet không thay invariant khóa bắt buộc. Tin description missing vẫn thuộc mẫu số nguồn A05 và được báo SOURCE_MISSING, không biến thành zero-hit.

## Cần TV1 chốt nguồn description

D05.description là text D04 đã sạch; D05.source_description là nguyên văn. TV2 **đề xuất giữ nguyên 50 cột D05 trong D06** và chọn `a05_description_column=source_description`. Sau kiểm chứng nhận, `validate_frames()` trả view trong bộ nhớ với cột description của A05 lấy rõ từ cột đã chốt. Không ghi đè Parquet hoặc đổi dictionary/extractor.

Nếu TV1 chọn `description`, phải chứng minh nó bằng D05.source_description cho toàn bộ selected ID; validator từ chối text sạch khác nguồn. Không tự chọn thay TV1. View này dùng với `a05_spark.extract_frames(view, ...)`; CLI A05 hiện đọc description trực tiếp chỉ được dùng khi receipt xác nhận description đã đúng nguồn. Không tự tạo một D06 Parquet giả để đi qua CLI.

Trước official, chạy `verify_artifacts(receipt)` rồi `validate_frames(d06, canonical, receipt)`; kiểm keys, membership/version, hash/path receipt, từng text/hash và orphan. A05 output phải đủ processing cho mọi IT job, kể cả SOURCE_MISSING/zero-hit; evidence/ranges chỉ mô tả nguồn nguyên văn đúng binding. Processing hash khi nguồn không phải string có thể NULL theo contract extractor; không lấy NULL status làm bằng chứng nguồn hợp lệ.

## Cần TV1 chốt job_functions

Chọn một trong hai giá trị `job_functions_contract`:

1. `embedded_job_functions`: mảng D05 `array<struct<skill_abr:string,skill_name:string,mapping_status:string>>` là nguồn authoritative. Sau khi chốt mới nối [project_job_functions](../src/d05_job_functions_adapter.py) vào run official: selected ID D06 → semi-JOIN canonical → explode ở nhánh riêng → distinct job_id/skill_abr → mapping duy nhất. NULL array khác assertion “không có kỹ năng”; giữ code thiếu label trong báo cáo unmapped; mâu thuẫn label phải dừng.
2. `separate_clean_bridges`: TV1 gửi clean job_skills/skills Parquet cùng schema/path/hash/approval. Keys bigint/string, mapping một dòng/code; scoped child links phải đối soát orphan và độ phủ. Không dùng raw fallback.

Hiện analyzer official vẫn nhận hai path bridge/mapping riêng trong `tv2_analysis_inputs.example.json`; projection embedded đã có code/test nhưng **chưa tự bật khi chưa chốt contract**. Biên nhận D06 không ký duyệt thay Q05. Sau xác nhận cần gắn route đã chọn, đối chiếu sample/row counts và chạy validation trước Q05. Nhãn chức năng LinkedIn không thay kỹ năng A05.

## Cách sử dụng và điểm dừng

```powershell
# Chạy với receipt TV1 thật; output phải là thư mục mới.
.\.venv\Scripts\python.exe src/receive_d06_handoff.py --receipt path/to/confirmed_receipt.json --output data/analytics/d06_receiving_NEW
```

Receipt mẫu hiện trả **BLOCKED_DEPENDENCY**, không khởi động Spark. Khi đủ: kiểm hash artifacts → Spark read-only → schema/ID/source/provenance → lưu audit; không chạy taxonomy, không trích A05 và không ghi Parquet. Trạng thái PASS_RECEIVING_CHECKS chỉ là kiểm tra tiếp nhận, không phải nghiệm thu A05/A06–A11 hoặc xác nhận chất lượng nhãn.

Sau tiếp nhận: A05 dùng view nguồn đúng + mode dependency local đã kiểm thử hoặc cluster đã kiểm chứng; output mới, dictionary v0.1.2 không áp review đề nghị. A06 Q01–Q04/Q08 dùng D06; Q05 thêm contract nguồn; A07 Q06 cần A05 bridge/status official cùng run/hash; A08 Q07 chỉ sau **D07 salary_clean + policy approval**, không lấy salary_record D05 thay thế. A09–A11 chỉ điền số từ run official đã đối soát, luôn có mẫu số/coverage/source hash.
