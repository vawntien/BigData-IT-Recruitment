# TV2 — hồ sơ A05 và mức sẵn sàng A06–A11

19/10/2026, `feat/tv2-analysis`. Đây là chuẩn bị và kiểm định kỹ thuật, **không nghiệm thu A05 hoặc công bố kết quả IT**. Không chạy lại A04, không sửa D05, dictionary/extractor/schema A05 hoặc đầu ra parity đã PASS.

## A05 — đối soát và chuẩn bị nghiệm thu

File `a05_skill_review_decisions.xlsx` chưa tồn tại trong workspace. Đã đọc và kế thừa workbook thực tế `data/analytics/a05_review/A05_Review_661_Evidence.xlsx`, SHA-256 `04a03198af3c8130e5e38347c22330348e162bd7bd8cfdfe3b1a20de137d0dea`; không đổi tên, tạo workbook thay thế hoặc giả nhận đã có file đúng tên.

[Đối soát nguồn](../data/analytics/tv2_readiness_20261019/a05_acceptance/review_audit.json) kiểm 661 evidence bằng evidence_id/job_id/skill/type/machine flag/quote/raw ranges và hash source processing; 88 tin liên quan được đọc bằng CSV multiline, không chạy extractor. 5 đề nghị bổ sung khớp quote/range và code hiện hữu. Không có mismatch; người/ngày duyệt đều trống. Status **PROPOSED_NOT_APPROVED**.

| Đề nghị | Số evidence | Nghiệm thu |
| --- | ---: | --- |
| GIU_NHAN | 479 | Chờ xác nhận, không tự duyệt |
| NHAN | 51 | Chờ xác nhận |
| LOAI | 45 | Chờ xác nhận |
| SUA_LOAI | 66 | Chờ xác nhận |
| SUA_KY_NANG | 1 | Chờ xác nhận |
| CHUA_RO | 19 | Người đọc cần chốt hoặc giữ chưa rõ |
| Đề nghị bổ sung (ngoài 661) | 5 | Chờ xác nhận |

182 đề nghị khác GIU_NHAN **đã bao gồm** 19 CHUA_RO; không cộng trùng. 19 evidence CHUA_RO thuộc 9 job_id: `3898171523` REACT; `3900947565` AWS; `3900952361` REACT; `3900960573` POWER_BI; `3901346364` NODEJS; `3901347312` ANGULAR/REACT/TYPESCRIPT; `3902369400` REACT; `3903471056` REACT; `3904950108` DOTNET. Đây là đề nghị từ workbook, không phải kết luận TV2 rằng chúng sai/đúng.

Bảng để người duyệt sử dụng, mọi cột quyết định cuối/người/ngày mới giữ trống:

- [Tổng hợp nghiệm thu](../data/analytics/tv2_readiness_20261019/a05_acceptance/acceptance_summary.md), [CSV tổng hợp](../data/analytics/tv2_readiness_20261019/a05_acceptance/acceptance_summary.csv).
- [19 ca CHUA_RO có evidence/ranges/lý do](../data/analytics/tv2_readiness_20261019/a05_acceptance/chua_ro.csv).
- [182 đề nghị cần xác nhận thay đổi](../data/analytics/tv2_readiness_20261019/a05_acceptance/changes_requiring_confirmation.csv), [5 đề nghị bổ sung](../data/analytics/tv2_readiness_20261019/a05_acceptance/additional_mentions_pending.csv).
- [Hàng đợi đầy đủ 661](../data/analytics/tv2_readiness_20261019/a05_acceptance/manual_acceptance_queue.csv), [manifest](../data/analytics/tv2_readiness_20261019/a05_acceptance/acceptance_manifest.json).

Đọc đúng nguồn của job_id/evidence_id; phân biệt REQUIRED/PREFERRED/TASK với loại trừ/chưa rõ; chốt alias/mã kỹ năng và evidence nguyên văn. Không suy nhãn skill từ CNTT đã duyệt ở A04. Chỉ người duyệt điền final_decision/reviewer/reviewed_date; nếu không đủ bằng chứng vẫn giữ CHUA_RO. Các thay đổi dictionary sau phê duyệt phải thành phiên bản mới và test riêng; lượt này không áp bất kỳ đề nghị nào. Không tính accuracy/precision/recall từ các đề nghị chưa duyệt.

## A06–A08 — truy vấn và validation

Tái sử dụng PySpark Q01–Q08, không xây pipeline mới. D05 50 cột và source hashes đã kiểm ở lượt parity trước; [schema đầu vào D06 tối thiểu](../src/d06_handoff_validation.py) đối chiếu các trường nền đó, bổ sung membership/version/group. Không coi canonical là tập IT.

Rà soát mẫu số: Q01/Q02/Q04 trên N có mục thiếu; Q03 trên known location và coverage/N; Q05 distinct tin có nhãn mapping và multi-label; Q06 successful WITH_MATCH + NO_MATCH, theo nhóm/level giữ zero-hit; Q07 từng đơn vị/nguồn và n hợp lệ, không trộn; Q08 timestamp UTC riêng và known coverage. Nhánh JOIN nhiều giá trị tách riêng; NULL không thành false/0/nhóm nghề khác.

Đã tăng guard cụ thể trong [analyzer](../src/a06_a08_spark_analysis.py): không nhận taxonomy version/hash rỗng; Q05 buộc key bigint/string và tên nhãn string; Q07 buộc job_id bigint, unit/source string, không để Spark ngầm ép kiểu JOIN. Không đổi công thức hoặc chạm A05 đã PASS. Bộ test kiểm source binding/hash/orphan, taxonomy rỗng và JOIN sai kiểu, cùng các đối chứng Q05/Q06/Q07.

[Kết quả test lượt này](../data/analytics/tv2_readiness_20261019/tests/tests.json): **27 PASS, 0 FAIL/error, 1 real-D06 SKIP**. Log đầy đủ tại [tests.txt](../data/analytics/tv2_readiness_20261019/tests/tests.txt). Sau đó bổ sung một guard cho hash receipt sai kiểu và chạy riêng các test receipt thuần Python; kết quả lưu trong `receipt_unit_followup.json`, không chạy lại Spark hoặc parity đã đạt.

Q05 embedded projection đã có [code/test candidate](../src/d05_job_functions_adapter.py); chưa tự bật thay contract clean bridge. Nếu TV1 chọn embedded, dùng `project_job_functions(canonical, confirmed_d06.select('job_id'))` cung cấp `(js,sk)` cho `analyze_frames(...)` sau receiving validation. CLI analyzer hiện nhận path bridge/mapping riêng; route embedded chỉ dùng API explicit sau khi TV1 chốt, không tự ghi bridge hoặc receipt official giả.

## A09–A11 — nguồn hình, phương pháp và ô chờ

[Bộ báo cáo mới](../data/analytics/tv2_readiness_20261019/report_package/reports/a10_analysis_report.md), [10 slide HTML](../data/analytics/tv2_readiness_20261019/report_package/reports/a11_slides.html), [nội dung/ghi chú](../data/analytics/tv2_readiness_20261019/report_package/reports/a11_slide_content.md). Không ghi đè bộ cũ.

[chart_sources.json](../data/analytics/tv2_readiness_20261019/report_package/reports/chart_sources.json) và [bản dễ đọc](../data/analytics/tv2_readiness_20261019/report_package/reports/chart_sources.md) ghi bảng/công thức/mẫu số/trạng thái/run/manifest hash/table hash cho 8 câu hỏi. Các hình workflow là sơ đồ phương pháp, không có số liệu. Mọi slide có chú thích nguồn; hình thống kê còn chờ, table hash/mẫu số chưa có giữ NULL, không điền 0 hoặc dữ liệu mẫu.

Phương pháp phân loại tham chiếu hồ sơ A04/version D06, không chạy lại classifier. Phần trích kỹ năng nêu dictionary/evidence/ranges/hash và giới hạn nhãn; Spark SQL/PySpark nêu GROUP BY/countDistinct, semi-JOIN, deduplicate và NULL-safe nhóm thiếu. Phần kiểm thử dẫn manifest parity 105 và regression 63 PASS/1 D06 SKIP đã lưu, **tách khỏi số liệu IT chính thức**. Đó là kết quả kỹ thuật lịch sử có hash, không thay kết quả test mới của lượt này hoặc nhãn chuẩn. Chưa xác minh A04 Spark/JVM, multi-node hoặc native Windows permission semantics.

## Nhận D06 Full và các phụ thuộc

[Checklist gửi TV1](d06_full_receiving_checklist_tv2.md), [receipt mẫu chưa ký](../config/d06_handoff_contract.example.json), [validator/API](../src/d06_handoff_validation.py), [CLI read-only](../src/receive_d06_handoff.py).

Đã chạy receipt mẫu: [BLOCKED_DEPENDENCY](../data/analytics/tv2_readiness_20261019/d06_receiving_preflight/receiving_validation.json); không khởi động Spark, không trích A05 hoặc viết Parquet. Khi có receipt thật, kiểm hash artifacts/code/config, schema, khóa, source text/hash theo mọi selected ID, membership/taxonomy/UTC trước khi tạo view A05. Kiểm tra máy không tự xác nhận chất lượng nghề, độ đầy đủ D06 Full hoặc phê duyệt nhóm; manifest Full/trace/approval vẫn cần TV1 đối soát theo checklist.

| Phần | Mức sẵn sàng | Còn chờ |
| --- | --- | --- |
| A05 hồ sơ phát triển/parity | Đã đối soát, có hàng đợi nghiệm thu | Người duyệt skill; D06 Full và binding text cho official |
| A06 Q01–Q05 | Code/guards/test candidate | D06; Q05 contract/route được xác nhận |
| A07 Q06 | Code/mẫu số/zero-hit đã kiểm | A05 official bridge/status cùng run, approval |
| A08 Q07/Q08 | Code/validation candidate | D07 policy+salary_clean; D06 cho thời gian |
| A09–A11 | Khung, nguồn hình, phương pháp và slide đã chuẩn bị | Run official được đối soát + người duyệt/V10 TV3 |

Không sửa D05 hoặc workbook, không chạy lại A04/105 parity, không tự commit/push/merge. Nhánh giữ nguyên và các thay đổi có sẵn được bảo toàn; audit cuối ghi đúng các file nguồn được phép cập nhật trong lượt này.

## Danh mục thay đổi

Hai file hiện hữu cập nhật: `src/a06_a08_spark_analysis.py` (guard), `src/render_tv2_analysis.py` (nguồn/cách tính hình, phương pháp và ghi chú).

File mới: `src/prepare_a05_acceptance.py`, `src/d06_handoff_validation.py`, `src/receive_d06_handoff.py`, `src/test_tv2_readiness.py`, `config/d06_handoff_contract.example.json`, tài liệu checklist D06 và tài liệu tổng hợp này. Mọi bảng review, receipt preflight, log/test và báo cáo/slide mới đặt dưới `data/analytics/tv2_readiness_20261019/`; không thay workbook hoặc output cũ.

[Audit hoàn tất và checksum](../data/audit/tv2_readiness_acceptance_20261019.json) ghi nguồn/đầu ra, thay đổi được phép, bảo toàn A01–A05/D05 và các giới hạn còn chờ. Không gộp test thuần Python chạy lại với suite Spark thành số ca độc lập mới.

## Tái chạy phần chuẩn bị

```powershell
.\.venv\Scripts\python.exe src/prepare_a05_acceptance.py --workbook data/analytics/a05_review/A05_Review_661_Evidence.xlsx --output data/analytics/a05_acceptance_NEW
.\.venv\Scripts\python.exe src/receive_d06_handoff.py --receipt config/d06_handoff_contract.example.json --output data/analytics/d06_receiving_NEW
```

Chọn output mới; receipt mẫu sẽ tiếp tục BLOCKED. Test runner/log được lưu tại `tmp/tv2_readiness_tests_20261019.py`, `.ps1`, `.log`; cần đổi tên output/log trước khi tái chạy để không ghi đè. Chỉ chạy test lại khi có thay đổi hoặc lỗi mới, không chạy lại taxonomy/ETL.
