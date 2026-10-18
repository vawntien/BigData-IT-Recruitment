# D06 – Phase 1: Python ↔ Spark parity validation

Ngày kiểm chứng: 18/10/2026, Asia/Bangkok.

**D06 PARITY: PASS.** Chỉ kiểm chứng frozen 176 job_id của A04 candidate v0.2.2.
**A04 ACCEPTANCE: PENDING GROUP REVIEW.**
**D06 OFFICIAL FULL DATASET: NOT EXECUTED.**

## A. Git branch/status

Ban đầu working tree sạch trên `feat/tv1-d05-official`, HEAD
`457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b`.
Đã tạo `feat/tv1-d06-parity` từ đúng HEAD đó. Không merge TV2; không add,
commit, push hoặc sửa remote. HEAD vẫn là D05. Các file D06 mới còn untracked.
Không sửa file D01–D05. Không chỉnh/promote active taxonomy v0.2.0.

## B. ZIP integrity

Nhận file thật tại `tmp/tv2(1).zip`: 44 file, CRC PASS, root `tv2_04/`.
SHA-256 ZIP: `11cccd285cabc6dbc430598e8275becb26b68dc989d424786f4577ae52db7123`.

Đã kiểm tra mọi entry trước giải nén: traversal, đường dẫn tuyệt đối/backslash,
Windows devices/ADS, control characters, tên có trailing dot/space, duplicate
case-insensitive, symlink/reparse point, kiểu entry, giới hạn kích thước và CRC.
Giải nén exact bytes vào `tmp/tv2_a04_handoff_extract/`; không chạy script trong ZIP.
Không overwrite; chạy lại chỉ tái sử dụng file đã có nếu bytes giống hệt.
Không giải nén vào source, config, raw hoặc processed.

**Chưa nhận `a04_manual_labels_filled.xlsx`.** Workbook này không cần cho parity
frozen input/prediction và không được giả định đã kiểm tra nhãn gốc.

## C. Manifest/hash results

Hash tính trực tiếp trên bytes, không parse/reserialize để tính hash.

| Hiện vật | Kết quả | SHA-256 |
| --- | --- | --- |
| Candidate config v0.2.2 | MATCH | `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874` |
| all_predictions.jsonl | MATCH | `1c4c8b8d3ab00238e908e834ca615ba4188b6d03858cb5e38648f1565d03266d` |
| baseline/source_rows.json | MATCH | `4fa5a35a5e06f1bb676833ba698cb6b2a96c5f2ff6a49b99f2e3214e216b0c14` |
| run_manifest.json | MATCH | `4d4aac5d52c1f98e656b0a2fb376712aabc580cbdb75bedf6d4c34df4ca3d3e8` |

Đã xác minh cả 24 entry trong `output_sha256`, baseline manifest và bốn module
runtime. Tổng cộng 33 phép kiểm hash/32 path riêng biệt, tất cả MATCH;
`all_predictions.jsonl` được kiểm cả digest pin và digest trong manifest.
Version/count/config/source digest trong manifest nhất quán với yêu cầu.
Chi tiết expected/actual trong `data/audit/d06/hash_verification.csv`.
Đây không phải xác nhận lại toàn bộ test/runner lịch sử của A04.

## D. TV2 code/config integrity

Xuất exact bytes bằng `git show` từ commit
`e437dcc11dda61f847673b9cc8c5801886c1996d` vào
`tmp/d06_tv2_snapshot/e437dcc11dda61f847673b9cc8c5801886c1996d/`.
Không dùng implementation v0.2.1 trong ZIP baseline.

| Module runtime | SHA-256 MATCH |
| --- | --- |
| it_taxonomy.py | `841231033c546cc2bedf141386038104c0a0f1cf9f5a01b80535457c8b42312f` |
| description_processing.py | `ad579397753f2de115faad3bf9ff4d1c8dfebf5ce76eb898f3368ca02a6fec78` |
| it_taxonomy_v010.py | `453bb6bcd22d4cdf866c670f3634b8f1e42a233eb086b650e579b4b1d429dc86` |
| tv2_csv.py | `7839763017c281c36126b8ece9c2015da41b54cccdfca0f365ac4feb48beb903` |

Candidate config cũng lấy từ commit trên và MATCH hash mục C.
Driver và mỗi partition đều kiểm hash bốn module/config trước khi import.
Module đã import từ đường dẫn khác bị từ chối. Không sửa classifier/rules,
không thay active config. Hai tài liệu handoff/final report cũng được xuất riêng
để tham chiếu, không đưa TV2 code vào working tree source/config.

## E. Python replay 176 jobs

177 source rows thuộc mẫu 160/17, một khóa chung có cùng source text → 176 khóa.
Reference cũng có đúng 176 unique job_id, cùng tập khóa. Classifier chỉ nhận
frozen title/description và job_id; không dùng nhãn, company, industry hoặc skills.
Bigint được kiểm signed-64-bit rồi đổi thành canonical numeric string cho API.

Python replay **176/176 exact match**, chạy lại bằng bigint input rồi chuyển
chuỗi cũng **176/176 exact match** (deterministic trên toàn bộ bộ frozen).
Gồm đủ 18 field: output classifier, selected_rule_id và bốn field wrapper
title/description/source hashes. Không normalize/trim lại source text.
Phân bố: **86 ACCEPT / 57 REJECT / 33 REVIEW**.

## F. Spark parity 176 jobs

Runtime thật: Python **3.11.0**, PySpark **4.2.0**, Java **21.0.12.1**,
`local[*]`. Java 21 chỉ đặt cho process chạy lệnh; không sửa JAVA_HOME hệ thống.
Worker dùng đúng venv Python của dự án.

`mapPartitions` thực thi trên bốn partition, bốn worker, bốn classifier instance;
mỗi partition khởi tạo model một lần, không truyền reference prediction cho worker.
Worker tự gọi nguyên classifier đã pin từ source text frozen.

| Kiểm tra | Python | Spark | Parquet readback |
| --- | ---: | ---: | ---: |
| Rows / unique job_id | 176 / 176 | 176 / 176 | 176 / 176 |
| Exact prediction matches | 176 | 176 | 176 |
| Field mismatches | 0 | 0 | 0 |
| Null/duplicate keys | 0 / 0 | 0 / 0 | 0 / 0 |

Đã có hai lượt live Spark thành công: standalone validator và integration tests.
Adapter hiện dùng đường dẫn snapshot chia sẻ trên **cùng máy local**;
chưa tuyên bố đã đóng gói/kiểm chứng remote executors hoặc cluster deployment.

## G. Field-level mismatches

**0 mismatch** ở Python, repeat determinism, Spark và Parquet.
So sánh JSON theo cấu trúc, không phụ thuộc object key order; giữ array order,
phân biệt bool/int, missing/null, empty array/null. So sánh mọi nested field,
không chỉ quyết định hoặc hash của JSON.

Các file `python_mismatches.json`, `determinism_mismatches.json`,
`spark_mismatches.json`, `canonical_mismatches.json`, `roundtrip_mismatches.json`
trong run folder đều là mảng rỗng. Nếu mismatch ở lần chạy sau, diagnostics chứa
job_id, field path và expected/actual trong tmp; validator dừng, không sửa TV2.

## H. D05 source compatibility

Đọc canonical Parquet bằng Spark, project năm cột job_id/source text/hashes,
LEFT JOIN bắt đầu từ 176 frozen keys. Không phân loại 123849 canonical jobs.

- Tìm thấy: **176**; không tìm thấy: **0**; join rows: **176**.
- Cả bốn source text/hash field khớp: **176**; mismatch jobs: **0**.
- Dùng `source_title`/`source_description`, không dùng clean title/description.
- Không sửa/rerun D05 pipeline, không ghi canonical production.

So hash/kích thước/mtime trước–sau trên **131 file được bảo vệ** gồm toàn bộ
file tracked tại D05 HEAD và các file raw/processed hiện hữu: **không thay đổi**.

## I. Spark schema

Schema được union từ toàn bộ output frozen thực tế sau Python replay PASS.
Full machine-readable schema: `data/audit/d06/spark_schema.json`.

- job_id: bigint non-null ở runtime; version/hash/decision: string.
- is_it: boolean nullable; REVIEW giữ null, không đổi thành false/REJECT.
- primary_group_code/subgroup_code/selected_rule_id: string nullable.
- candidate_group_codes/reason_codes/matched_rule_ids: array<string>, giữ thứ tự.
- match_evidence: array<struct>, gồm mọi trường title và description; raw ranges
  là array<array<bigint>>, giữ normalized offsets, derived coordinates và flags.
- description_processing: struct đủ parser/version/source/derived hash,
  coverage/incomplete counters, parser_issues và removed_source_ranges.
- description_segments: array<struct> đủ text, ranges, section/actor, blockers,
  trạng thái, long/explicit_self/mapping flags và window_diagnostics.

Mỗi struct thêm `_d06_present: array<string>` để bảo toàn field absence riêng
với explicit null. Encode từ prediction thật, decode từ **typed nested fields**;
không lưu JSON backup rồi dùng backup để giả định nested parity đã đạt.
Thêm ba field provenance worker `_d06_partition_id`, `_d06_worker_pid`,
`_d06_classifier_instance`. Tổng 22 top-level fields: 18 prediction + 4 transport.

Hai mảng parser_issues/removed_source_ranges rỗng ở cả 176 jobs: element types
được đọc từ pinned description_processing.py, không suy đoán bằng StringType.
Có unit control synthetic riêng để kiểm nội dung diagnostics không rỗng;
control này không được tính vào mẫu frozen hoặc thay thế Spark parity.
Unknown field/type mới bị từ chối, không âm thầm drop.

## J. Parquet roundtrip

Chỉ ghi sau Python/Spark/canonical checks PASS, dùng error-if-exists tại:
`tmp/d06_parity/20261018T110206Z_637eede4/predictions.parquet/`.
Readback thực tế: **176/176 exact**, schema types/field structure không đổi,
33 REVIEW vẫn null is_it; version/hash và toàn bộ nested arrays/structs khớp.

Spark Parquet reader nới physical nullability thành nullable; đối chiếu schema
bằng `toNullable()` ở hai phía, đồng thời kiểm ràng buộc dữ liệu thực tế.
Không tuyên bố metadata non-null của input schema được Parquet giữ nguyên.
Output chính thức D06/canonical production không được tạo.

## K. Tests executed

Lệnh đã chạy từ root, Java 21 process-scoped:

```powershell
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B -m unittest discover -s src -p test_d06_parity.py -v
```

**17 tests / 17 PASS**, 42.567 giây; không skip, không failure.

- 5 adapter unit tests: bigint canonical/boundaries, invalid IDs, JSON comparison,
  ZIP path protection, refusal to overwrite bytes.
- 7 frozen-adapter tests: frozen keys/hashes, all-176 replay/determinism,
  version/hash, ba quyết định/null boolean, all-field typed serialization,
  synthetic diagnostic control riêng, unknown-field rejection.
- 5 live Spark integration tests: Python/Spark full parity, key grain/model loading,
  canonical LEFT JOIN, typed Parquet/schema/null roundtrip, runtime/scope/preservation.

Không tuyên bố chạy lại toàn bộ regression D01–D05 hoặc test A04 của TV2.

## L. New files created

Các file mới dự kiến review/stage sau này, hiện chưa git add:

1. `src/d06_taxonomy_adapter.py`
2. `src/d06_parity_validation.py`
3. `src/test_d06_parity.py`
4. `docs/d06_parity_report.md`
5. `data/audit/d06/validation_summary.json`
6. `data/audit/d06/hash_verification.csv`
7. `data/audit/d06/spark_schema.json`

Audit chỉ chứa metadata/hash/schema, không chứa full source text/reference.
ZIP, extracted 44 files, pinned TV2 snapshot, prediction Parquet và diagnostics
đều ở tmp, đã xác minh được `.gitignore` bỏ qua.

## M. Blockers / giới hạn

Không còn blocker cho **D06 Phase 1 local parity**.
Lượt đầu trong sandbox gặp `JAVA_GATEWAY_EXITED` do Java không ghi được file
kết nối tạm; chưa có Spark prediction. Giữ nguyên lịch sử tại
`tmp/d06_parity/20261018T110011Z_537215fc/summary.json` (validator ban đầu gắn
FAIL cho runtime này, không phải prediction mismatch). Chạy ngoài sandbox
đã thành công hai lượt. Validator hiện phân biệt runtime BLOCKED và parity FAIL.
Cảnh báo winutils/native Hadoop không ngăn run thành công; dùng local filesystem
adapter D04 hiện hữu cho Windows, không sửa helper D04/D05.

Thiếu workbook nhãn chính không chặn parity nhưng chưa kiểm lại nguồn nhãn gốc;
A04 formal acceptance vẫn pending. PASS parity không là chứng nhận accuracy
toàn dataset hoặc nghiệm thu A04; không tự xử lý các FN/REVIEW của TV2.

## N. Recommended next action

Review bảy file mới và schema/presence contract này; nhóm xác nhận A04 acceptance
và cho phép phạm vi D06 tiếp theo trước khi tích hợp/chạy full dataset.
Nếu cần cluster deployment, đóng gói code/config và kiểm lại trên executors từ xa.
Không tự chạy tiếp, promote, commit/push hoặc merge trong lượt này.

Evidence chính: `data/audit/d06/validation_summary.json`, liên kết đến live run
`tmp/d06_parity/20261018T110206Z_637eede4/summary.json`.

**VERDICT: D06 PARITY = PASS; A04 ACCEPTANCE = PENDING GROUP REVIEW;
D06 OFFICIAL FULL DATASET = NOT EXECUTED.**

## Release review – 18/10/2026

Các mục A–N phía trên ghi lại lượt implementation trước khi được phép commit/push.
Lượt release này được người dùng cho phép stage đúng bảy file D06, tạo commit mới
và push branch; không merge/promote/chạy D06 Official. Evidence tmp cũ được giữ nguyên.

Review code phát hiện guard yêu cầu HEAD đúng bằng D05, khiến tests không chạy lại
sau commit D06. Đã sửa riêng validator D06: chấp nhận D06 HEAD kế thừa D05, nhưng
từ chối sai branch/base hoặc thay đổi bất kỳ path tracked D01–D05 trong committed
tree, index hay working tree. Không sửa D01–D05 hoặc TV2. Test runtime xác nhận
đúng D05 base; guard sẽ được kiểm tra lại trên commit release thực tế.

Đã chạy lại **17/17 tests PASS**, không skip, 43.105 giây, vào run mới:
`tmp/d06_parity/20261018T123730Z_f2932437/`.
Python/determinism/Spark/Parquet đều 176/176 exact; canonical 176/176 source/hash
khớp; null/duplicate keys 0; REVIEW null 33; 4 partition/4 model instance.
131 protected files vẫn không đổi hash/size/mtime. Đã tính lại độc lập 33 hash
audit và so original bytes của cả 44 extracted files với ZIP, tất cả khớp.

`validation_summary.json` giữ kết quả/hashes implementation ban đầu; object
`release_verification` bổ sung run, code hashes và tests cho code sau sửa guard.
CSV hash reference và schema JSON không thay đổi. Không đưa source/reference
text, prediction Parquet, workbook, venv hoặc credentials vào bảy file release.

### Readiness chỉ đọc trước full dataset

1. **Schema đủ cho frozen176, chưa chứng nhận full dataset.** Cần chốt schema
   contract cố định/version hóa, nullability và `_d06_present`; kiểu/field mới
   ngoài mẫu hiện bị từ chối, không tự mở rộng hay drop. Hai diagnostics arrays
   chưa có phần tử trong frozen176 mới được kiểm non-empty ở adapter unit test,
   cần thêm edge-case Spark/Parquet tests trước production.
2. **Nested evidence không mất trong mẫu.** Full typed decode và Parquet exact
   đã kiểm, không dùng JSON backup. Cần chốt downstream lưu full diagnostics,
   ranges, parser segments và chi phí storage/presence/worker metadata.
3. **Grain giữ nguyên trên mẫu.** Production phải kiểm 123849 input/output keys,
   null/duplicate/missing/extra IDs bằng distributed aggregates/anti-joins;
   không mang hard-coded count176 hoặc collect toàn bộ predictions lên driver.
4. **REVIEW không bị loại.** Cần chốt lưu cả ba quyết định và bảng ACCEPT dẫn xuất
   riêng; không lọc `is_it = true` rồi mất REVIEW/REJECT hoặc ép null thành false.
5. **Source policy đúng trên mẫu.** Dùng source_title/source_description cùng
   UTF-8 hashes của D05, không clean/trim; chốt policy missing/empty source và
   version/snapshot canonical cho run toàn tập.
6. **Config chỉ định rõ v0.2.2/hash pin.** Active v0.2.0 không bị thay. Cần nhóm
   cho phép candidate dùng cho run toàn tập và xác nhận A04 business acceptance;
   parity không chứng nhận chất lượng classifier, không tự sửa FN/REVIEW.
7. **Runner hiện là local parity harness.** Full classification cần runner riêng,
   resource packaging cho remote executors, manifest/code/config provenance,
   output path riêng/error-if-exists, retry/idempotence và policy malformed job.
8. **Benchmark/memory phải được cho phép riêng.** Đề xuất tăng dần batch có kiểm
   soát (không chạy trong lượt này), gồm descriptions dài/HTML/unresolved units;
   đo jobs/s, p50/p95/p99 latency, worker RSS, driver/executor heap/GC, spill,
   shuffle/serialization, straggler/skew, model-init/reuse, output bytes và disk.
   So cấu hình partition/concurrency, giới hạn cache/collect, thử retry/restart,
   full nested Parquet đọc lại và reconciliation đủ khóa. Không ngoại suy tuyến
   tính hiệu năng/accuracy từ mẫu176; Java heap3g không bao gồm Python worker RSS.

Remote main trước release ở `fbfcb59cff2cb93daa2ff087b42d0bf73f14fec9`,
D05 remote ở `457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b`, chưa merge main.
Đề xuất **stacked PR D06 → feat/tv1-d05-official**, không D06 → main ở thời điểm này;
khi D05 merge cần review lại base/diff theo quy trình nhóm. Không tự merge/rebase.
