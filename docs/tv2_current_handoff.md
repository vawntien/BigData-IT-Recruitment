# TV2 — Căn cứ hiện hành và tiếp nối A05–A11

**Cập nhật để bàn giao mã nguồn ngày 20/10/2026:** D05/D07 ALL JOBS đã được kiểm tra trực tiếp PASS; xem [hồ sơ tích hợp hiện hành](tv2_d05_d07_integration_20261020.md) và [Q07 contract v2](../config/q07_salary_contract_v2.json). A05 v0.1.2 vẫn stable. Q07 đã triển khai/kiểm thử, còn PENDING xác nhận nghiệp vụ TV1/TV3. D06 Full chưa có; A05 official và A06–A08 IT production chưa chạy. Các mô tả thiếu Parquet/runtime/D07 trong snapshot 19/10 bên dưới là lịch sử, không thay trạng thái cập nhật này. Dữ liệu raw/handoff, workbook riêng tư và outputs tạm chỉ giữ local, không thuộc gói mã nguồn GitHub.

Đồng Viết Dũng, `feat/tv2-analysis`, **19/10/2026**. Tài liệu này làm rõ trạng thái kế thừa; không thay báo cáo lịch sử hoặc nghiệm thu A04. Không chạy classifier, sửa rule, sửa nhãn hoặc tái tối ưu A01–A04.

## Căn cứ A04 đã kiểm tra trực tiếp

[Audit đọc-only phục vụ A05](../data/audit/tv2_a04_lineage_for_a05_20261019.json) xác nhận:

| Hiện vật | Kiểm tra trong lượt này | Phạm vi |
| --- | --- | --- |
| A04 v0.2.0 ngày 08/10 | Giữ làm lịch sử; không chạy lại | Không dùng kết quả toàn raw lịch sử thay D06 chính thức |
| v0.2.1 ngày 14/10 | 30 hash đầu ra khớp manifest; config snapshot đúng hash; trace đủ 176 khóa | Candidate round 1 trên mẫu phát triển |
| v0.2.2 ngày 14/10 | 24 hash đầu ra khớp manifest; config snapshot đúng hash; trace đủ 176 khóa | Candidate round 2 bàn giao TV1, chưa promote/nghiệm thu |
| Workbook chính | 160 dòng: 90 CNTT, 66 NGOAI_CNTT, 4 CHUA_RO; text/nhãn/metadata khớp snapshot round 2 | Nhãn nghề đã duyệt, mẫu phát triển seed42 |
| Workbook bổ sung | 17 dòng: 16 CNTT, 1 NGOAI_CNTT; khớp snapshot round 2 | Mẫu ca rời ACCEPT, không ngẫu nhiên |
| Hợp hai workbook | 177 dòng nguồn, **176 job_id**, ca chung `3905848702` khớp mọi trường | **105 CNTT, 67 NGOAI_CNTT, 4 CHUA_RO** |

Active config vẫn **v0.2.0**, candidate bàn giao vẫn **v0.2.2**. Không đổi active chỉ vì có candidate mới. Báo cáo ngày 14/10 đề nghị “Sẵn sàng rà soát nghiệm thu”, không tự ghi A04 hoàn thành 100%, người/ngày nghiệm thu hoặc đã tích hợp D06. Tiếp tục dùng [hồ sơ cuối A04](a04_final_report.md) và [handoff TV1](a04_handoff_tv1.md); không dùng báo cáo v0.2.0 ngày 08/10 làm trạng thái mới nhất của toàn quá trình A04.

Các hash xác minh là của hiện vật đã lưu; không gọi lại classifier, tính lại chỉ số đánh giá hoặc thực hiện vòng sửa A04. Không có lỗi nguồn/hash/nhãn cụ thể phát hiện được để mở lại A04.

## A05 — ưu tiên và phần đã hoàn thiện độc lập

Đã kiểm tra **tập 105 job_id của A05 v0.1.2 bằng đúng tập CNTT đã duyệt trong hai workbook**, không phải 105 machine ACCEPT. Hash workbook trong input manifest A05 khớp file hiện tại; processing đủ đúng 105 khóa. Đây vẫn là tập phát triển đã dùng rà soát, không là toàn tập IT production hay tập đánh giá độc lập.

Đã tiếp nhận workbook thực tế `data/analytics/a05_review/A05_Review_661_Evidence.xlsx`; chưa có file đúng tên `a05_skill_review_decisions.xlsx`. [Audit review A05](../data/analytics/tv2_a05_a11_followup01_review/review_audit.json) xác nhận 661 evidence khớp nguồn v0.1.2, 5 đề nghị bổ sung khớp quote/range raw, **người/ngày duyệt đều trống**. Trạng thái `PROPOSED_NOT_APPROVED`. Không tạo lại rà soát, không áp đề nghị hoặc sửa dictionary/extractor/bridge 355 cặp.

Phân biệt hai loại phê duyệt:

- Nhãn nghề A04 đã duyệt để chọn 105 tin phát triển A05.
- Quyết định kỹ năng A05 **mới là đề nghị**; nhãn nghề không duyệt thay từng skill/type/alias. Reviewer/date A05 vẫn giữ trống, không tạo gold từ máy.

Các phần độc lập đã có: extractor và dictionary v0.1.2, schema Spark A05, evidence/source status/bridge phát triển, đối soát workbook/raw, hàng đợi đề nghị kế thừa và test. Bước tiếp theo của A05 official là chạy adapter hiện hữu trên **D06 được TV1 xác nhận**, parity/Parquet và review run; không lấy CSV mẫu hoặc nhãn A04 làm D06 thay thế.

## Trạng thái D05/D06/D07 và A06–A11

Kiểm tra checkout hiện tại: không có Parquet dưới `data/`; D05 vẫn là scaffold/bằng chứng báo cáo, không phải canonical đang hiện diện. Chưa có path/manifest/xác nhận nghiệm thu chính thức của D06 hoặc D07. Java PATH vẫn 8, venv chưa có PySpark. Không tạo Parquet giả, không đọc raw làm input official.

| Task | Phần có thể kế thừa ngay | Trạng thái phụ thuộc |
| --- | --- | --- |
| A05 | Audit review, extractor/adapter/schema/tests v0.1.2 | **BLOCKED** D06/runtime và người duyệt skill thực tế |
| A06 | PySpark Q01–Q05, grain, mẫu số/coverage | **BLOCKED** D06; Q05 thêm D05 bridge/mapping |
| A07 | Q06 toàn mẫu số successful, gồm zero-hit; theo nhóm và kinh nghiệm | **BLOCKED** A05 official bridge/status cùng run |
| A08 | Q07 gate D07, Q08 hai timestamp UTC | **BLOCKED** D07 đã duyệt/D06 |
| A09 | 8 mục nhận xét, nguồn/mẫu số/giới hạn | Candidate; kết luận số liệu chờ run OFFICIAL SUCCESS |
| A10 | Chương phương pháp, kết quả chờ input, hạn chế | Candidate; không chèn số mẫu như thống kê toàn tập |
| A11 | 10 slide HTML, sơ đồ phương pháp, speaker notes | Candidate; chart kết quả chờ dữ liệu và đối soát V10/TV3 |

Mã PySpark dùng lại [analyzer](../src/a06_a08_spark_analysis.py), [input contract chưa điền approval](../config/tv2_analysis_inputs.example.json), [schema đầu ra candidate](../config/tv2_analysis_output_schema.json). A05 dùng đúng `source_status` và `postings.description`; không đổi thành nhãn chức năng nguồn. Q07 không tự bật từ một cờ boolean, không trộn currency/pay period/source. Schema vẫn cần đối chiếu runtime khi TV1 giao Parquet; chưa có Spark parity được xác minh.

Đầu ra mới nhất đã chuẩn bị: [manifest BLOCKED](../data/analytics/tv2_a05_a11_followup01/analysis/manifest.json), [A09](../data/analytics/tv2_a05_a11_followup01/reports/a09_insights.md), [A10](../data/analytics/tv2_a05_a11_followup01/reports/a10_analysis_report.md), [slide A11](../data/analytics/tv2_a05_a11_followup01/reports/a11_slides.html). Không tạo thêm một bộ output giống nhau chỉ để báo tiến độ; tái sử dụng các hiện vật hợp lệ.

Kiểm thử A05–A11 đã lưu gần nhất: **62 test: 55 PASS, 0 FAIL/error, 7 SKIP**; [log/kết quả](../data/analytics/tv2_a05_a11_followup01/test_results.json). Lượt xác nhận lineage này không sửa code nên không chạy lại suite hoặc taxonomy. SKIP thuộc Spark/parity/Parquet/real D06; không đổi chúng thành PASS. Kiểm tra hash và nhãn nguồn trong lượt này PASS.

## TV1 cần bàn giao để mở phần official

1. D05 canonical và bridge `job_skills`/`skills`, schema/path/hash, grain/JOIN validation và xác nhận bàn giao.
2. D06 `it_jobs` một dòng/job_id bigint, ACCEPT/true, nhóm nghề/description, thuộc tính và timestamp sạch, taxonomy version/hash chính thức, manifest và xác nhận lựa chọn candidate/active. **Không mặc định promote v0.2.2**.
3. D07 `salary_clean`, schema nguồn/đơn vị, valid/invalid/coverage, chính sách được duyệt và manifest/path/hash.
4. Môi trường Java/PySpark và bằng chứng parity/write-read Parquet. TV2 dùng D06 đã xác nhận để chạy tiếp A05, sau đó Q01–Q08; chỉ sau run SUCCESS mới chốt A09–A11.

Lệnh đối soát review và tái chạy phần chuẩn bị trong thư mục mới nằm tại [hồ sơ followup01](tv2_a05_a11_followup01.md); lệnh official dự kiến tại [hồ sơ thực thi A05–A11](tv2_a05_a11_status_20261019.md). Các chỗ thiếu path/approval là dependency thật, không được điền giả để bỏ trạng thái BLOCKED.
