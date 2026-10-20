# A05 — Phiên bản ổn định và lệnh chạy official

## Quyết định phiên bản

Giữ **v0.1.2** làm baseline ổn định đã kiểm chứng Spark local trên 105 mẫu. Hash extractor, adapter, parser và dictionary snapshot được khóa trong [release manifest](../config/a05_release_v0.1.2.json). Đây không phải tuyên bố mọi nhãn đúng hoặc nghiệm thu production.

**Không promote candidate `a05-context-recommendations-0.1.0`.** Nó là hàm audit evidence có sẵn, không phải extractor từ description hay Spark worker. Guard React Native/package, Azure DevOps và role-only có căn cứ từ đối chứng, nhưng chỉ mới nằm trong lớp khuyến nghị. Extractor v0.1.2 chưa được sửa các lỗi đó. Candidate còn thay scope heading rộng, giữ 129 hit vốn được nhận thành chưa rõ; các đề xuất không đủ làm nhãn chuẩn để đánh giá hồi quy. Không áp 146 đề xuất tự động vào bridge hoặc coi 287 cặp audit là bridge mới.

Các ca chưa rõ và 5 chuỗi dính được giữ trong hồ sơ cũ; không phân tích lại, không nới ranh giới, không thêm schema/type. Nếu tích hợp guard ở lượt phát hành sau phải có version mới, regression và full-record Spark parity trên cùng 105 mẫu, giữ nguyên run02. Lượt này chưa có candidate extractor đủ điều kiện chạy parity; không lấy 18 fixture audit PASS làm điều kiện phát hành nó.

## D06 và phạm vi còn chặn

Đã tìm lại `data/processed`, `data/analytics`, `config`, gồm file bị ignore. Chỉ thấy receipt template và receiving preflight cũ, **không có D06 Full/it_jobs Parquet chính thức hoặc receipt đã xác nhận**. [Kiểm kê](../tmp/a05_official_readiness_20261019/dependency_inventory.json): `BLOCKED_DEPENDENCY`.

Không chạy D06 hoặc lấy D05 toàn tập thay IT. Không tạo output official. D06 cần TV1 cung cấp path Parquet, manifest/input hash, validation, commit và xác nhận thật, taxonomy config/version/hash, classifier hash, membership ACCEPT/is_it=true và source description binding. Receipt phải chứng minh description A05 bằng D05.source_description/hash trên đúng job_id; không tự chọn clean description thay raw text.

A05 không phụ thuộc D07 hoặc xác nhận job_functions. Shared receipt validator có tùy chọn `purpose='a05'` bỏ riêng gate Q05; mặc định cho A06–A08 vẫn giữ gate đó. Không tự điền approved_by/approved_on.

## Runner đã chuẩn bị

[run_a05_official.py](../src/run_a05_official.py) tái sử dụng `validate_frames` và `extract_frames`, không thay nghiệp vụ trích v0.1.2. Nó:

- Chặn receipt thiếu trước khi tạo Spark/output; kiểm artifact hashes và taxonomy version.
- Kiểm schema, unique/non-null job_id, membership, canonical FK, source text/hash; bind description bằng view trong memory, không sửa D05/D06.
- Kiểm khóa đầu ra, cặp job–skill, evidence_id, accepted evidence FK, số kỹ năng và trạng thái từng tin, source hash, zero-hit/missing.
- Ghi ba Parquet `errorifexists`, so nội dung hai chiều, kiểu cột, đếm lại và chạy validator trên read-back; kiểm artifact đầu vào không đổi trước khi ghi manifest SUCCESS. Nếu lỗi sau ghi, manifest FAILED_PARTIAL_OUTPUT, không publish.
- Lưu run/version/hash, taxonomy, nguồn text, counts và giới hạn chất lượng. SUCCESS là kiểm chứng kỹ thuật, không tự điền nghiệm thu người đọc.

Các kiểm tra quote/ranges/parser của extractor đã có fixture/parity v0.1.2; runner mới kiểm source hash/FK toàn output, không thay thế đánh giá ngữ nghĩa. Full orchestration/Parquet trên D06 vẫn chưa thể kiểm vì thiếu input.

Sau khi TV1 bàn giao, tạo **receipt thực riêng** dựa vào `config/d06_handoff_contract.example.json`; chỉ điền metadata được TV1 xác nhận. Lệnh single-host Windows dùng môi trường đã PASS run02:

```powershell
powershell -NoProfile -File src/run_a05_official_local.ps1 `
  -Receipt data/receipts/d06_full_confirmed.json `
  -OutputDirectory data/analytics/a05_official_v0_1_2_RUN_ID `
  -RunId a05-official-v0.1.2-RUN_ID `
  -LogPath tmp/a05_official_RUN_ID.log
```

Tên receipt/run trên là placeholder chưa tồn tại, không phải dữ liệu giả. Chọn RUN_ID mới. Wrapper chỉ đặt env của process con, không đổi Java hệ thống. `shared_local_pythonpath` chỉ dành một máy; worker kiểm đúng module path/hash. Chưa xác minh multi-node hoặc addPyFile Windows; cluster cần kiểm dependency riêng.

## Kiểm thử

- Kế thừa v0.1.2: regression **63 PASS, 1 D06 SKIP**, full-record Spark local parity 105 mẫu và write/read ba Parquet **PASS** theo `docs/a05_spark_parity_20261019.md`/run02. Không chạy lại vì không thay extractor/dictionary/adapter.
- Lượt mới: **6 PASS** trong `test_a05_official_readiness.py`, gồm 4 Spark synthetic và 2 receipt unit; **4 PASS** regression receipt hiện hữu. [Log](../tmp/a05_official_readiness_20261019/validation_tests.log), [receipt regression](../tmp/a05_official_readiness_20261019/receipt_regression.log).
- Preflight receipt template: exit 2/BLOCKED_DEPENDENCY, không tạo Spark hoặc output; [kết quả](../tmp/a05_official_readiness_20261019/blocked_preflight.json).
- Spark test process exit 0, summary 6 OK; cuối log có Windows `ERROR: Access denied` khi cleanup JVM, không gây test failure. Chưa kết luận cleanup Windows hoàn toàn ổn định.
- Không chạy lại 666 audit, A04, ETL hoặc production; không tạo workbook.

## Hợp đồng Q06 và Dashboard Skills TV3

Chỉ tiêu thụ run có `run_manifest.json.status=SUCCESS` và input D06 đã nhận đúng. Đường dẫn official chỉ được xác nhận sau run, không dùng run development:

| Đầu ra | Grain / cách dùng |
| --- | --- |
| job_skill_technical.parquet | Một `(job_id bigint, skill_code string)` trong run; skill_name/group, mention_types, evidence_ids/count và provenance. JOIN với D06 theo job_id; đếm distinct job_id, không cộng số evidence thành số tin. |
| technical_skill_evidence.parquet | Một evidence_id; giữ source_field, source_text_sha256, alias, quote/ranges Unicode codepoints, mention_type, accepted, rule/version. Dùng drill-down; không explode để làm mẫu số. |
| skill_source_processing.parquet | Một job_id/source_field cho mọi tin D06, gồm zero-hit và missing. Dùng tính mẫu số/độ phủ. |

Q06/Skills: mẫu số là distinct tin có `PROCESSED_WITH_MATCH` **hoặc `PROCESSED_NO_MATCH`**. SOURCE_MISSING không phải zero-hit; hiển thị độ phủ thành công/tổng D06 và số thiếu riêng. Một kỹ năng đếm một lần/tin. Tỷ lệ nhiều kỹ năng không bắt buộc cộng thành 100%. Chỉ dùng `accepted=true` evidence; không nhập đề xuất review vào bảng chính.

Runner lưu top-level `run_id`, `dictionary_version`, `dictionary_sha256`, status SUCCESS tương thích guard A06–A08 hiện có. Cấu hình `a05_confirmation` cần trỏ đúng hash manifest của run đã kiểm; không tự điền xác nhận nhóm. Không gửi tin nhắn cho TV3; tài liệu này là gói bàn giao chuẩn bị.

**Còn thực sự chặn:** D06 Full + xác nhận contract nguồn; tiếp đó là chạy official và kiểm output thật. Candidate không đủ điều kiện phát hành, nhưng không chặn việc chuẩn bị/chạy bằng baseline ổn định theo phạm vi yêu cầu này. 666 nhãn tay, D07 và job_functions không phải điều kiện chặn A05.
