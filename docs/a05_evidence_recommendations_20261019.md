# A05 — Khuyến nghị tự động và điều kiện bàn giao thực tế

Ngày 19/10/2026, nhánh `feat/tv2-analysis`. Báo cáo này thay thế cách diễn đạt trước đây rằng phải duyệt tay toàn bộ 666 mục trước khi chuẩn bị official. Không có điều kiện đó trong hàng phân công A05. Không yêu cầu người dùng phân xử từng dòng.

## Kết quả đã tạo

- [666 khuyến nghị có bằng chứng](../tmp/a05_evidence_recommendations_20261019/final/recommendations_666.csv): 661 evidence_id duy nhất và 5 ứng viên bổ sung riêng. Mỗi dòng có source field/hash, quote gốc, raw ranges, tên kỹ năng, đề xuất, rule/lý do và mức chắc chắn. Không tạo thêm workbook phê duyệt.
- [Các trường hợp chưa rõ](../tmp/a05_evidence_recommendations_20261019/final/unclear_only.csv), [các thay đổi đề xuất](../tmp/a05_evidence_recommendations_20261019/final/proposed_changes.csv), [manifest](../tmp/a05_evidence_recommendations_20261019/final/manifest.json).
- [Quy tắc candidate](../src/a05_recommendation_candidate.py), [script tái lập](../src/build_a05_recommendations.py), [test đối chứng](../src/test_a05_recommendation_candidate.py). Candidate không được import bởi extractor/Spark và chưa là bản phát hành production.

Đã đọc toàn bộ 661 evidence lưu và 5 đề nghị, đối chiếu quote/ranges/hash với description raw của 88 tin. Mỗi description được nạp đầy đủ; quyết định tự động dùng unit đã lưu, cue gần hit và heading trước hit. Đây là phép rà soát bảo thủ theo quy tắc, không phải 666 đánh giá tay hay nhãn chuẩn. Không dùng quyết định cũ làm ground truth. `decision_quote` có thể là ngữ cảnh rút gọn/ghép có dấu “…”, còn `quote` và `raw_ranges` là bằng chứng nguồn nguyên bản đã kiểm tra.

| Khuyến nghị | Số mục |
| --- | ---: |
| GIU_NHAN | 324 |
| SUA_LOAI | 93 |
| NHAN | 5 |
| LOAI mapping tại hit | 48 |
| CHUA_RO | 196 |
| Tổng | 666 |

470 mục có khuyến nghị cụ thể; 196 mục chưa đủ căn cứ theo phép rà soát này. Toàn bộ vẫn là đề xuất máy, không điền final_decision/reviewer/reviewed_date. Không tính accuracy/precision/recall hoặc suy thống kê thị trường từ mẫu phát triển.

## Những gì còn chưa rõ

| Nguyên nhân tự động | Số mục |
| --- | ---: |
| Scope cue trong unit dài chưa chứng minh | 77 |
| Scope cục bộ chưa đủ căn cứ | 52 |
| Alias chưa chứng minh ngữ nghĩa công nghệ | 29 |
| Oracle chưa xác định sản phẩm Database | 16 |
| Unit trộn nhiệm vụ và yêu cầu chưa tách rõ | 12 |
| Chỉ có tên vai trò | 4 |
| Câu giới thiệu working as | 1 |
| Năm bổ sung có ranh giới từ dính | 5 |

Các nhóm là reason đầu tiên của rule, không phải phân nhóm ngữ nghĩa loại trừ hoàn toàn. Tám ca role/intro đã biết vẫn CHUA_RO; một số được ghi vào nhóm scope/alias thay vì nhóm role. Số CHUA_RO tăng so với workbook cũ vì audit không mặc nhiên tin các đề nghị GIU_NHAN: trong đó 129 evidence đang được máy nhận nhưng audit bảo thủ chưa xác lập lại đủ căn cứ. Không kết luận 129 hit đó sai. Không bỏ nội dung dài, không sửa baseline theo kết quả audit.

Năm ứng viên có quote/range đúng nhưng nằm trong `SkillsJava`, `MicroservicesKafkaSpring`, `SQLDesign` hoặc `AWSExtensive`. Có tín hiệu yêu cầu/nhiệm vụ/ưu tiên, nhưng ranh giới từ v0.1.2 chưa cho phép nhận trực tiếp. Không tự nới boundary cho một job hay coi các ứng viên này là lỗi chắc chắn. Cần thiết kế phân đoạn có kiểm soát nếu muốn hỗ trợ chuỗi dính; chưa phải điều kiện chặn official hiện tại.

## Lỗi tái hiện được và bản sửa tổng quát đã chuẩn bị

Các phản ví dụ synthetic [được lưu riêng](../tmp/a05_evidence_recommendations_20261019/final/baseline_candidate_counterexamples.json): baseline nhận React trong React Native là REQUIRED, nhận Azure trong Azure DevOps là REQUIRED, và nhận AWS Data Engineer trong ROLE là TASK. Đây là xung đột với nguyên tắc người dùng đã xác nhận. Candidate đưa hai mapping sản phẩm sang EXCLUDE và role-only sang chưa rõ. react-Dom trong đối chứng vốn đã AMBIGUOUS_ALIAS; không gọi đó là lỗi false-positive được nhận của baseline.

Candidate là lớp quyết định đề xuất tổng quát, không tra job_id/evidence_id. Có kiểm soát sản phẩm, no-SQL/Objective-C, predates, title/role, cue optional và heading sau hit; vẫn giữ phủ định/company/benefits và đòi alias context. REQUIRED cần cue/section yêu cầu; TASK cần hành động của vị trí. Không tự mở rộng danh mục hoặc tạo loại title/role mới. Case React trực tiếp thiếu context vẫn có thể CHUA_RO, không bỏ gate alias để tăng nhận.

Lớp audit này chưa phải patch tích hợp vào `_mention_type/_contexts` của extractor. Đặc biệt đề xuất heading/scope rộng cần thêm đánh giá trước khi phát hành, không nên áp đồng loạt 146 thay đổi chỉ vì CSV đã sinh được.

Tác động **nếu giả lập theo các khuyến nghị rõ**, không phải output extractor mới: 146 evidence có đề xuất NHAN/SUA_LOAI/LOAI; 15 hit vốn được nhận bị đề xuất LOAI. Còn 129 hit được nhận chuyển sang chưa rõ trong audit; không tự loại chúng khỏi bridge baseline. Chỉ gom các đề xuất rõ sẽ được 287 cặp job–skill, nhưng đây là lát cắt audit thiếu phần chưa rõ, không được trình bày là bridge thay thế 355 cặp hay kết quả chất lượng. Không thay đổi baseline 355 job–skill/661 evidence hoặc parity đã PASS.

Trước khi dùng bản sửa production: tích hợp riêng các guard lỗi chắc chắn, snapshot/version mới, fixture đối chứng theo quy tắc, kiểm tra schema/evidence/FK/zero-hit và Spark parity của **phiên bản mới**. Parity v0.1.2 cũ chỉ chứng minh hai implementation giống nhau, không chứng minh các nhãn kỹ năng đúng. Không cần duyệt 666 dòng để bắt đầu việc này. Lượt này không chạy lại parity hoặc production.

## Đối chiếu phân công gốc

Đã đọc trực tiếp ZIP/XML của `C:/Ke_hoach_BigData_Tuyen_dung_CNTT_3_nguoi.xlsm`, sheet `Cong viec`, hàng 22; không chạy macro. SHA-256 khớp hồ sơ: `9343cc8b5c17beb343ec98fa57bb00bff6cb4609aa12cbffb0100ef461c3df26`.

| Tiêu chí thực sự trong phân công | Hiện trạng |
| --- | --- |
| F22: Trích kỹ năng từ mô tả | Đã có implementation/source-only trên mẫu phát triển; chưa full D06 |
| G22: Dictionary Python/Java/SQL/cloud, alias và ranh giới từ | Có v0.1.2 và tests; đã phát hiện hạn chế sản phẩm/role cần xử lý trước phát hành bản sửa |
| G22: Lưu nguồn trích | Đạt kiểm tra nguồn cho mẫu: field, quote, ranges, hash, rule/version |
| H22: job_skill_technical.parquet | Spark local/write-read mẫu đã PASS theo hồ sơ; chưa có output official D06 |
| I22: Kiểm tra C/C++, Java/JavaScript | Test hiện hữu PASS |
| I22: Một kỹ năng chỉ đếm một lần/tin | Bridge baseline 355 cặp duy nhất; cần kiểm lại trên run full |
| J22: D06 | BLOCKED: chưa nhận D06 Full chính thức |

Rà soát 661+5, workbook nhãn tay, danh sách CHUA_RO, mức chắc chắn và phép kiểm candidate là **kiểm định bổ sung**; không có yêu cầu hàng 22 phải có reviewer/ngày duyệt ở mọi evidence. Không tự đặt ngưỡng accuracy hoặc điều kiện 666 nhãn. Nếu nhóm có quy chế nghiệm thu khác chưa bàn giao, chỉ áp khi có nguồn quy định thực tế.

A01 Q06/A03 mục 7/A05 v0.1.2 nhất quán: nguồn là `postings.description`; title riêng chỉ hỗ trợ ngữ cảnh đọc. Không bật skills_desc hoặc nhãn chức năng làm kỹ năng công nghệ.

## Việc bắt buộc còn lại trước bàn giao official

1. Nhận D06 Full từ TV1: Parquet/path, khóa job_id duy nhất/non-null, chỉ IT ACCEPT, description và chính sách giữ/clean nguồn cùng hash/provenance, taxonomy version/hash, manifest/validation. D05 toàn bộ không thay thế D06. Checklist và receiver đã có ở `docs/d06_full_receiving_checklist_tv2.md` và `src/receive_d06_handoff.py`.
2. Chốt phiên bản kỹ thuật sẽ phát hành, xử lý các guard sai chắc chắn theo nguyên tắc đã nêu. Nếu dùng candidate mới, kiểm thử tích hợp và Spark parity mới trước official; không ghi kết quả v0.1.2 là parity của candidate. Đây là xác minh code, không yêu cầu người dùng chọn từng dòng.
3. Chạy A05 trên D06 hợp lệ, ghi ba bảng Parquet vào thư mục run mới; kiểm read-back, schema, distinct job–skill, evidence FK, source hash, zero-hit/missing/failed, manifest/version và độ phủ. Chỉ khi đó mới báo output official hoàn thành. D07/job_functions không phải dependency trích description của A05.

CHUA_RO giữ riêng với giới hạn công bố; không phải lý do dừng chuẩn bị official. Có thể kiểm định theo mẫu rủi ro sau chạy, không biến thành yêu cầu duyệt toàn bộ dữ liệu.

## Kiểm thử và tái lập

- 37 test `test_a05_skills.py`: PASS; 18 test candidate: PASS. Đây là test code/fixtures, không nhãn chuẩn.
- 666 kiểm tra nguồn/khóa và bảo toàn đầu vào: PASS; mọi final fields và reviewer/date trống.
- Windows PowerShell bọc stderr của unittest thành NativeCommandError trong log Tee-Object; cả hai summary unittest đều OK (37/18), không có failure. Không diễn giải mã wrapper thành lỗi assertion.
- Không chạy lại Spark parity; không kiểm parity candidate, không chạy D06.

```powershell
python -m unittest discover -s src -p test_a05_recommendation_candidate.py -v
python -m unittest discover -s src -p test_a05_skills.py -v
python src/build_a05_recommendations.py --output tmp/a05_recommendations_new_run
```

Output không ghi đè nếu thư mục đã tồn tại. Bản kết quả sử dụng là `tmp/a05_evidence_recommendations_20261019/final/`; các CSV ở thư mục cha là bản chẩn đoán trung gian trước sửa scope, không dùng làm khuyến nghị cuối. Không commit/push/merge, không sửa dictionary/extractor/D05/A04 hay kết quả parity cũ.
