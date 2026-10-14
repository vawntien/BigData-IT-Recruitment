# A02–A04 – Version và thay đổi xử lý mô tả

Đồng Viết Dũng – TV2; nhánh `feat/tv2-analysis`, ngày 08/10/2026. Chỉ thay chính sách xử lý mô tả A02–A04; không thay raw, ETL, D04/D05, A05–A11 hoặc ghi nhãn chuẩn từ máy. Không commit/push.

## v0.1.0 – Snapshot để tái lập

- [Cấu hình exact bytes](../config/versions/it_taxonomy_v0.1.0.json), SHA-256 `99523fff775fc302507638b532491275c3bec54d2d38354ce329f574943c8278`.
- [Implementation exact bytes](../src/it_taxonomy_v010.py), SHA-256 `453bb6bcd22d4cdf866c670f3634b8f1e42a233eb086b650e579b4b1d429dc86`.
- Trace gốc `data/analytics/a04_taxonomy_v0_1_0_seed42/all_predictions.jsonl.gz`, SHA-256 `8bccbf9ed92db4105f4539d1ca6eb0d7a069d60d717545697b07f1666be221d5`; mẫu bàn giao `data/analytics/a04_manual_seed42/` và mọi nhãn người đọc được bảo toàn.
- [Interpreter hiện hành](../src/it_taxonomy.py) gọi implementation cũ khi load snapshot v0.1.0. Test cũ được chuyển sang đường dẫn snapshot, giữ nguyên các assertion hợp đồng cũ. Script chẩn đoán v0.1.0 cũng được chỉ định snapshot; báo cáo chẩn đoán lịch sử không sửa.

Tái lập phân loại/lấy mẫu cũ trong thư mục mới, không cần ETL:

```powershell
.\.venv\Scripts\python.exe src/prepare_a04.py --config config/versions/it_taxonomy_v0.1.0.json --output data/analytics/a04_v010_reproduced
```

Tái lập quyết định/evidence theo bản cũ; gzip có thể khác hash do timestamp/container. Manifest của lần tái lập phải lưu SHA nguồn/config/code/output của chính lần đó. Không coi tên thư mục là bằng chứng phiên bản.

## v0.2.0 – structured-source-v1

Nguồn chính sách là [config/it_taxonomy.json](../config/it_taxonomy.json), `normalization.description_segments.mode=structured_source_v1`. [Parser](../src/description_processing.py) dùng thư viện chuẩn Python 3.11; [runner so sánh](../src/compare_a04_versions.py) dùng parser CSV multiline hiện có, từ chối ghi vào thư mục/audit đã tồn tại. Mode hoặc enum ngữ nghĩa không được hỗ trợ sẽ chặn chạy.

**Giữ nguyên** nhóm nghề, subgroup, priority, include/general/exclusion predicates, toàn bộ 54 term sets gồm gate/alias fallback và kế hoạch/quota seed42. Các invariants được test và kiểm tra trước full run; thay đổi nằm ở preprocessing/context/provenance và reason cho xử lý chưa đầy đủ.

| Thành phần | v0.1.0 | v0.2.0 |
| --- | --- | --- |
| Dữ liệu nguồn | Full title/description được giữ | Tiếp tục giữ full raw, hash nguồn và bản dẫn xuất có provenance |
| Newline/list/HTML | Regex dòng/câu đơn giản | HTMLParser, block/list/br, entity; tách LF/CRLF/CR/U+2028/U+2029 và bullet; nội dung script/style chỉ bị bỏ khỏi bản dẫn xuất |
| Câu | Chấm rồi whitespace/cuối chuỗi | Có bảo vệ `.NET`, URL, phiên bản, viết tắt; nhận câu dính khi dấu kết câu theo sau bởi chữ hoa; tách mệnh đề đối lập but/however/yet/nevertheless |
| Heading/section | Không nhận section | Heading có dấu `:` hoặc nguyên dòng, danh sách trong JSON; section giữ đến heading tiếp theo |
| Đoạn >500 | Bỏ toàn bộ khỏi matching | Giữ full unit; cửa sổ matching cục bộ tối đa 500 **Unicode code point sau chuẩn hóa**, quanh task, giữ từ nguyên vẹn; không ghép qua section/câu |
| Đoạn chưa tách chắc chắn | Chỉ cờ bỏ đoạn | `RETAINED_LONG_UNRESOLVED`, `DESCRIPTION_PROCESSING_INCOMPLETE`; nguyên văn unit vẫn có trong trace, có thể dùng cửa sổ task nếu chủ thể đủ rõ |
| REVIEW do dài | Cờ dài đủ REVIEW khi không có rule khác | Đoạn dài đã xử lý đầy đủ không gây REVIEW; chỉ thiếu/mơ hồ/xung đột hoặc xử lý chưa đầy đủ vẫn cần REVIEW khi chưa có quyết định mạnh hơn |
| Cộng tác | Cụm cộng tác chặn toàn đoạn | Nhiệm vụ đứng trước cộng tác hoặc có cue chủ thể trước cộng tác vẫn được xét; chỉ nhắc công việc đội khác/cộng tác chưa có nhiệm vụ của vị trí vẫn bị chặn |
| Phủ định | Chặn toàn đoạn | Giữ chặn trong câu/mệnh đề; blocker/chủ thể trước cửa sổ matching cũng được kiểm tra, không mất vì window |
| Boilerplate | Một số alias chặn toàn đoạn | Company/customer subject, company section, compensation/benefits/EEO/qualifications và prefix yêu cầu kiến thức không cấp evidence nghề; heading responsibilities/role có thể reset section |
| Evidence | Raw excerpt | Raw excerpt exact + raw match ranges; offset normalized và parser text có tên tọa độ riêng; không phát evidence khi chưa ánh xạ về nguồn |

Không tăng 500 để tăng ACCEPT. Không chia văn bản thành các khúc 500 tùy ý. Một đoạn dài chưa rõ cấu trúc có thể vẫn được ACCEPT nhờ title hoặc bằng chứng cục bộ, nhưng cờ xử lý chưa đầy đủ vẫn lưu để người đọc kiểm tra. Ngược lại, đoạn dài trong section boilerplate xác định được là xử lý xong dù không được dùng làm positive evidence.

Raw offsets là index Unicode code point **trong giá trị trường sau khi CSV parser đọc**, `[start,end)`, không phải byte offset trong file CSV. Offset derived thuộc văn bản parser, offset normalized thuộc đoạn chuẩn hóa; chúng không phải raw offsets. HTML/entity có mapping, tag được loại khỏi match ranges; excerpt có thể chứa markup vì là lát cắt raw. Nếu đoạn markup quá dài, `excerpt_covers_all_match_ranges=false`; full raw và mọi ranges vẫn lưu.

## Thực thi, kiểm tra và bàn giao

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s src -p "test*a04*.py" -v
.\.venv\Scripts\python.exe src/compare_a04_versions.py --output data/analytics/a04_v020_reproduced --audit-output data/audit/tv2_a04_v020_reproduced.json
```

Runner so theo **job_id**, kiểm tra grain, full text/hash tương ứng với trace cũ, snapshot/config/rule invariants và raw/nhãn/trace bảo toàn; không dựa vào thứ tự hai trace. Full run lưu snapshot JSON hai phiên bản, code và hash/runtime trong thư mục riêng. Dữ liệu lớn dưới analytics bị ignore; audit nhỏ/script/tài liệu có thể review trên Git.

30 test đã qua, gồm 14 test hợp đồng cũ, 16 test mới và 57 ca minh họa JSON cho cả hai version. Test mới kiểm tra đường đi của rule, ranh giới, blocker, provenance và nguồn 20 tin chẩn đoán; **không dùng nhận xét chẩn đoán làm nhãn chuẩn**. Xem [kết quả và ca cần xác nhận](a04_v020_comparison.md).

**Chưa xác minh parity Spark/JVM.** TV1 cần xác nhận schema evidence/segments và Unicode code point, triển khai parser/context cùng chính sách, chạy cùng test/ca raw để kiểm tra parity trước bàn giao production. Không sửa pipeline D04/D05 trong lần này.

## Đề xuất fallback riêng – chưa áp dụng

Gate exact-title và mọi alias fallback vẫn nguyên v0.1.0. Sau khi có nhãn tay, mới xem xét:

1. Có cho fallback ở title dài chưa được rule khác quyết định không, với điều kiện tránh nghề ngoài CNTT/exclusion.
2. Có cho cue/role ở heading và task ở bullet **cùng section/chủ thể** không; hiện không ghép bằng chứng qua unit.
3. Alias task/role, dạng số nhiều và prefix trách nhiệm có cần bổ sung dựa trên tập phát triển có nhãn hay không.

Các đề xuất này cần version riêng, test đối chứng và nhãn tay; không coi mọi Engineer/Analyst là IT hoặc bật industry/skill metadata làm positive. Mẫu seed42 cùng các job_id chẩn đoán/so sánh đã xem là dữ liệu phát triển; loại khỏi mẫu đánh giá cuối độc lập. Không tính accuracy/precision/recall trước nhãn tay, không suy tỷ lệ toàn dataset từ các ca chọn có chủ đích.
