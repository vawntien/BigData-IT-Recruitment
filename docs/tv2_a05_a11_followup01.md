# TV2 — Tiếp nhận workbook A05 và hồ sơ sẵn sàng A06–A11

Đồng Viết Dũng — TV2; ngày **19/10/2026**, nhánh `feat/tv2-analysis`. Kế thừa hồ sơ và mã đã chuẩn bị; không làm lại A01–A04, không chạy lại taxonomy/extractor trên toàn tập, không áp quyết định skill, không commit/push/merge.

## A05: phần độc lập với D06 đã thực hiện

File thực tế có tại [A05_Review_661_Evidence.xlsx](../data/analytics/a05_review/A05_Review_661_Evidence.xlsx), SHA-256 `04a03198af3c8130e5e38347c22330348e162bd7bd8cfdfe3b1a20de137d0dea`. Chưa có file đúng tên `a05_skill_review_decisions.xlsx`; đã đọc workbook hiện diện theo nội dung, không đổi tên hoặc tạo workbook thay thế.

- Sheet `Review 661 evidence`: **661 dòng**, evidence_id không trùng và khớp đầy đủ 661 evidence nguồn v0.1.2. Đối chiếu job_id, skill, mention type, accepted cũ, matched text, ranges và quote: **0 sai khác**. Tất cả người duyệt/ngày duyệt để trống.
- Sheet `Bo sot de nghi`: **5 đề nghị** trên 2 job_id, gồm JAVA/KAFKA/SPRING tại `3895868756`, SQL/AWS tại `3891068727`. Quote, raw range và alias khớp raw; mã skill đã có trong dictionary. Người/ngày duyệt đều trống. Có chữ/range hợp lệ **không tự chứng minh cách nhận skill hoặc loại đề cập đã được duyệt**.
- Đã kiểm raw description/hash của **88 job_id liên quan đến evidence/đề nghị**, giữ toàn văn và coordinate nguồn. Đây là đối soát nguồn của mẫu phát triển, không phải trích xuất production hoặc thống kê toàn bộ tập IT.
- Giữ dictionary **v0.1.2** và bridge nguồn **355 cặp job–skill** nguyên byte. Không dùng quyết định đề nghị để sửa bridge, evidence, rule hoặc tính accuracy/precision/recall.

| Quyết định đề nghị trong workbook | Dòng |
| --- | ---: |
| GIU_NHAN | 479 |
| NHAN | 51 |
| LOAI | 45 |
| SUA_LOAI | 66 |
| SUA_KY_NANG | 1 |
| CHUA_RO | 19 |
| Tổng evidence | **661** |

Đây là **số dòng đề nghị**, không phải số tin, nhãn kỹ năng chuẩn hoặc kết quả thị trường. Trạng thái chung **PROPOSED_NOT_APPROVED**, `decisions_applied=false`. Kế thừa nguyên quyết định và lý do; không tạo lại quá trình rà soát hoặc tự điền người/ngày duyệt.

Hiện vật mới:

- [review_audit.json](../data/analytics/tv2_a05_a11_followup01_review/review_audit.json): hash, đối chiếu evidence/raw, đề nghị và trạng thái.
- [existing_review_queue.csv](../data/analytics/tv2_a05_a11_followup01_review/existing_review_queue.csv): chỉ xuất lại quyết định/lý do sẵn có để theo dõi theo evidence_id, không tạo quyết định mới.
- [additional_proposal_checks.csv](../data/analytics/tv2_a05_a11_followup01_review/additional_proposal_checks.csv): kiểm tra nguồn cho 5 đề nghị, chưa đưa vào bridge.
- [src/audit_a05_review.py](../src/audit_a05_review.py), [test](../src/test_a05_review_audit.py): công cụ đọc/đối soát, không có đường áp quyết định hoặc ghi workbook.

## A06–A08: mã, schema và kiểm thử

Tái sử dụng [analyzer PySpark](../src/a06_a08_spark_analysis.py), [input contract](../config/tv2_analysis_inputs.example.json), [adapter A05](../src/a05_spark.py) và [test tích hợp](../src/test_a05_a11_integration.py). Không sửa các mã này trong lượt tiếp nhận workbook.

Bổ sung [schema đầu ra](../config/tv2_analysis_output_schema.json): grain, trường, loại dữ liệu logic và mẫu số của từng bảng Q01–Q08. Schema ở trạng thái **CANDIDATE_NOT_SPARK_VALIDATED**; cần đọc schema Parquet thật khi TV1 bàn giao, không gọi schema tĩnh là Parquet đã chạy.

Các nguyên tắc đã có: A05 dùng `source_status`/`postings.description`, cùng run/dictionary/hash; Q06 gồm successful zero-hit, tách missing/failed/partial; nhánh đa nhãn không nhân bảng nền; Q07 cần D07 có duyệt, tách tiền tệ/kỳ trả/loại thù lao/nguồn; Q08 dùng hai timestamp UTC riêng. Cột D06/D07 thực tế vẫn cần TV1 xác nhận. Không tự chuyển raw hoặc 105 tin phát triển sang Parquet chính thức.

[Inventory cập nhật](../data/analytics/tv2_a05_a11_followup01/dependency_inventory.json) và [manifest phân tích](../data/analytics/tv2_a05_a11_followup01/analysis/manifest.json): vẫn **không có Parquet D05/D06/D07**, không có xác nhận path/nghiệm thu. Java PATH `1.8.0_51`, venv chưa có PySpark; runtime yêu cầu Java 21/PySpark theo README.

## A09–A11: bộ nội dung kế thừa đã cập nhật

| Hạng mục | Phần đã làm | Phần BLOCKED |
| --- | --- | --- |
| A05 | Hoàn thành kiểm tra nguồn workbook đang có; chưa áp đề nghị | Người duyệt và D06/runtime để tạo official Parquet |
| A06 | Mã/schema/test Q01–Q05 candidate | D06; D05 cho Q05 |
| A07 | Mã/schema/test Q06 global/nhóm/kinh nghiệm candidate | A05 official bridge/status cùng run trên D06 |
| A08 | Mã/schema/test Q07/Q08 candidate | D07 duyệt và D06 có timestamp |
| A09 | [8 mục nhận xét chờ input](../data/analytics/tv2_a05_a11_followup01/reports/a09_insights.md), nguồn/mẫu số/giới hạn | Chưa có run OFFICIAL SUCCESS, chưa có 5–8 kết luận định lượng để nghiệm thu |
| A10 | [Chương phân tích](../data/analytics/tv2_a05_a11_followup01/reports/a10_analysis_report.md), phương pháp và giới hạn | Kết quả số liệu chính thức |
| A11 | [10 slide HTML](../data/analytics/tv2_a05_a11_followup01/reports/a11_slides.html), [nội dung và speaker notes](../data/analytics/tv2_a05_a11_followup01/reports/a11_slide_content.md) | Biểu đồ kết quả và đối soát V10/TV3 |

Slide có sơ đồ phương pháp/phối hợp; phần biểu đồ thống kê ghi **CHỜ INPUT**, không vẽ số giả. Workbook mới không làm thay đổi quyền sử dụng mẫu phát triển thành kết quả toàn tập. Bộ hồ sơ cũ `tv2_a05_a11_20261019` được giữ nguyên; hồ sơ mới nằm trong `tv2_a05_a11_followup01` và `tv2_a05_a11_followup01_review`.

## Kiểm thử và bảo toàn

[Kết quả test mới](../data/analytics/tv2_a05_a11_followup01/test_results.json): **62 test, 55 PASS, 0 FAIL/error, 7 SKIP**. Bao gồm 37 test extractor cũ, 13 test contract/report và 5 test đối soát workbook. 7 Spark synthetic/real/parity/Parquet vẫn SKIP do thiếu môi trường/đầu vào. Không báo Spark PASS hoặc hoàn thành 100%.

Audit độc lập đọc workbook thật và raw đã PASS nguồn, không gọi extractor hoặc classifier. Các đề nghị chưa duyệt không được biến thành expected gold để đánh giá bộ trích.

[Snapshot trước lượt này](../data/audit/tv2_a05_a11_followup01_before.json) và [kiểm tra cuối](../data/audit/tv2_a05_a11_followup01_result.json) kiểm tra hash/kích thước/mtime các file có sẵn. Giữ raw/workbooks, code A01–A05, mã phân tích candidate và output cũ; chỉ thêm file mới. Không stage/reset/switch hoặc commit/push/merge.

## File cần TV1 bàn giao

1. **D05 canonical** và bảng cầu `job_skills`/mapping `skills` cần cho Q05: đường dẫn Parquet, schema, dataset version/hash, kiểm tra grain/JOIN và xác nhận bàn giao.
2. **D06 `it_jobs` chính thức**: một job_id bigint duy nhất, ACCEPT/true, cột nhóm nghề thực tế, description nguyên bản, taxonomy version/hash, các thuộc tính và hai timestamp D04; manifest/path/hash và xác nhận chọn phiên bản taxonomy. Không dùng trace/mẫu phát triển làm D06.
3. **D07 `salary_clean`**: schema thật và tên cột nguồn, valid/invalid/coverage, policy đã duyệt cho currency/pay_period/compensation/source, phạm vi và đơn vị; path/hash/manifest.
4. Runtime và bằng chứng **Java 21/PySpark**, parity/canonical/Parquet của pipeline. TV2 chạy tiếp adapter A05 hiện có trên D06 rồi xác nhận bridge/status/evidence cùng run; workbook skill vẫn cần người duyệt thực tế, không phải TV1 path tự biến thành approval nhãn.

Chạy lại đối soát vào **thư mục mới**:

```powershell
.\.venv\Scripts\python.exe src/audit_a05_review.py --workbook data/analytics/a05_review/A05_Review_661_Evidence.xlsx --output data/analytics/a05_review_audit_next01
.\.venv\Scripts\python.exe src/prepare_tv2_a05_a11.py --output data/analytics/tv2_a05_a11_next01 --skill-review-workbook data/analytics/a05_review/A05_Review_661_Evidence.xlsx
```

Khi đủ input chính thức, dùng [lệnh A05/Spark/renderer đã bàn giao](tv2_a05_a11_status_20261019.md), điền contract từ xác nhận thật và chọn output mới. Ưu tiên bàn giao D06/runtime, chốt review skill/D07, rồi chạy analytics và điền số liệu A09–A11 sau SUCCESS.
