# D06 Phase3 – Official runner readiness (19/10/2026, Asia/Bangkok)

Implementation/preflight review only. **Không chạy full dataset, không nghiệm thu
A04, không promote taxonomy, không commit/push/merge.**

Baseline: D05 `457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b`, parity
`1c365741f0e3dcad9064473ae2c0c6b9f507ae25`, Pilot
`0ca38ab90a05acfac1f191da45dba7511ab094be`. Branch mới
`feat/tv1-d06-official-runner`, HEAD vẫn Pilot.

## A. Pipeline architecture

Entrypoint `src/d06_classification_runner.py` giữ Pilot nguyên semantics/caps,
dispatch `--mode preflight` / `--mode full` sang `src/d06_official_runner.py`.
Không sao chép rules hoặc classifier. Reuse adapter, runtime encode/decode,
worker ZIP bootstrap và distributed `output_validation` đã PASS.

Full flow thực sự được triển khai:

`external approvals → destination/package/schema checks → canonical preflight →
grant/input binding → exclusive run directory/manifest → mapPartitions → Parquet
→ distributed readback/source/key/nullable/nested validation → input rehash →
output inventory → completion marker`.

Full wrapper chỉ đi vào engine sau approval. Engine dùng DataFrame/RDD theo
partition, không Python list123849 hoặc collect predictions về driver.
Integration engine **TEST** dùng cùng code write/validate/publish, namespace tmp
riêng và cap32; không phải cách bỏ guard FULL. Các test này không tạo approved
records, không gọi positive-authorized FULL entrypoint.

## B. Classifier dependencies / deployment

TV2 pin: `e437dcc11dda61f847673b9cc8c5801886c1996d`. Candidate v0.2.2 hash:
`1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874`.
Active v0.2.0 không bị thay đổi/promote.

Runtime package immutable SHA:
`09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59`.
TV2 bốn module và config lấy exact Git blobs, helper/adapter/schema lấy exact
Pilot commit blobs. Official verifier khóa cả ba helper/schema digests; không
chấp nhận package tự sửa trong tmp dù classifier vẫn đúng hash.

Builder tách khỏi production runtime, không merge/cherry-pick:

```powershell
.\.venv\Scripts\python.exe -B src/d06_pilot_packaging.py --output-dir tmp/d06_official_artifacts
```

Đã chạy builder và tái tạo đúng ZIP09e7... Production runner nhận **explicit
--package + --package-sha256**, không build từ Git/tmp worktree trên executor.
Broadcast exact ZIP bytes, kiểm whole ZIP/member hashes trước import; worker cache
được tạo theo checksum/PID tại tempfile local của worker. Model một lần/partition,
không một lần/job. Không hardcode path máy TV2 hoặc project tmp làm nguồn code.

CI/artifact publisher sau review cần giữ immutable package và manifest. Fresh
runtime cần Python3.11, PySpark4.2.0, Java21, canonical snapshot và package;
không cần frozen reference để chạy Official. Regression tests vẫn cần gói reference
ngoài Git. Windows local IO dùng explicit `--windows-fs-jar`; artifact D04 có thể
build từ tracked Java/helper, không chạy D04 ETL. Không sửa D01–D05.

## C. Input/output contract

Input chính thức: D05 canonical50 cột, schema version `d05-v1`,123849 rows/unique,
null/duplicate keys0. Bắt buộc job_id bigint, source_title/source_description và
hai source SHA strings. Mọi source SHA UTF-8 được kiểm bằng Spark. Không trim,
coalesce raw text hay dùng clean title/description thay source. Empty string hợp
lệ khác null/missing. Worker chuyển bigint thành canonical string qua adapter.

Official schema version **d06-official-v1**, giữ nguyên **27 fields Pilot**;
canonical JSON schema SHA:
`44ee9bcc29f5ace90161b6bea67d6543ced30925944761f56e28c7df76a67a68`.
Được freeze trong `d06_official_contract.py`, nguồn schema là committed
`data/audit/d06/pilot_spark_schema.json`, không infer lại schema từ full data.
Thay schema/hash cần version/review và tests mới; không âm thầm mở rộng/drop.

Giữ đủ job_id, taxonomy version/hash, it_decision, nullable is_it, nullable group/
subgroup/selected rule, ordered candidate/reason/rule arrays, match_evidence,
description_processing/segments, raw/normalized ranges và source wrappers/hashes.
`_d06_present=true` cho output thành công. `_d06_field_keys` giữ missing-vs-null
ở mọi struct; không đổi codec Phase1. Worker metrics/digest vẫn giữ để parity
không bị thay schema. Không thay đổi cấu trúc Pilot nên không có migration dữ liệu.

ACCEPT=true, REJECT=false, REVIEW=null. Lỗi classifier hoặc missing output không
được biến thành REVIEW. Bảng ACCEPT dẫn xuất sau này không được làm mất REVIEW.

## D. Production output path / manifest

Namespace local filesystem được chọn:
`data/processed/d06/v0.2.2/<run_id>/`.
run_id chỉ ASCII letters/digits/underscore/hyphen, tối đa80 ký tự. Không override
namespace bằng canonical/Pilot/đường dẫn ngoài root. Từ chối symlink/reparse points
và target resolve ra ngoài workspace. Existing run (kể cả failed/partial) bị từ
chối trước classify; không overwrite, không append. Preflight không mkdir path này.

Run layout:

```text
<run_id>/
  run_manifest.json       immutable intent: scope, input inventory, schema/config/code
  events/0001_RUNNING.json ... WRITTEN ... VALIDATED
  predictions/           Spark Parquet + _SUCCESS
  validation.json        actual distributed checks + counts + measured metrics
  output_inventory.json  per-Parquet SHA/size + combined fingerprint
  completion.json        final publication seal, only after ALL checks
  failure.json           present on caught error; never success
```

Manifest có run_id, taxonomy version/hash, TV2 commit, package SHA, input fingerprint,
schema version/hash, approvals SHA, expected rows, start timestamp và runtime config.
Completion có end timestamp + SHA manifest/validation/inventory/data fingerprint.
Metadata ghi exclusive, flush/fsync, không rename thư mục. Reader `inspect_run`
chỉ trả SUCCEEDED khi JSON marker hoàn chỉnh, metadata/data hashes và reconciliation
khớp. `_SUCCESS` đơn độc KHÔNG là success. Partial marker bị coi incomplete/corrupt.
`scope=TEST` không được dùng như Official success.

## E. Preflight checks và lần chạy thật

Đã thực thi CLI preflight, không full:

```powershell
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B src/d06_classification_runner.py --mode preflight --run-id readiness_20261019 --package tmp/d06_official_artifacts/d06_runtime_09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59.zip --package-sha256 09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59 --partitions 4 --master "local[4]" --windows-fs-jar tmp/d04-localfs/d04-localfs-adapter.jar --report tmp/d06_official_preflight/readiness_20261019_01.json
```

Kết quả **PASS**: canonical123849 rows/unique,50 columns, source text/hashes và
schema version đúng,0null/duplicate.4 Parquet files397164694 bytes; input fingerprint:
`729db5102bda622eef2f6d3cc0d88b851516ad01f6050f3d0f75debb99e17270`.
Worker probe4/4 nạp constructor/config đúng; operation probe không gọi classify,
không nhận source records. **classified_jobs=0**, destination_created=false,
full_execution_authorized=false. Model constructor validation không phải full run.
Report mới dưới tmp, không ghi production. Không overwrite report có sẵn.

## F. Full mode guard / exact human requirements

`--execute-full` **không đủ**. Cần ba file human decision ngoài Git cùng SHA exact
file của từng file. Code không tạo hoặc tự điền APPROVED record.

| Record kind | Nội dung cần cung cấp |
| --- | --- |
| A04_BUSINESS | status APPROVED, approved_by (người có trách nhiệm), decision_id, timezone-aware approved_at không ở tương lai; taxonomy_version/hash; TV2 commit; accepted_v022_limitations=true; manual_review_completed=true; main_workbook.path + SHA của workbook nhãn chính đã review |
| D06_SCHEMA | cùng identity/time/version/hash fields; schema_version=d06-official-v1 và schema_sha256=44ee9... đầy đủ |
| D06_FULL_RUN | người dùng có thẩm quyền cho phép run_id cụ thể; expected_rows123849; input_fingerprint, package SHA, schema SHA, output_relative; SHA của A04/schema approval files; các identity/time/version/hash fields như trên |

Trước Spark: kiểm explicit flag + cả ba records/bytes/workbook/bindings. Sau
preflight thực tế, trước write/classify: grant phải khớp input/package/run_id/
relative output đúng namespace. Nếu input/package/schema thay thì cần review và
authorization mới. Không có --force/skip-approval/expected-rows override.

Đây là consistency gate cho trusted human records; JSON name+hash **không phải
chữ ký số hay xác thực quyền tổ chức**. Nhóm phải xác minh người ký/quyền và bảo vệ
approval files ngoài Git. Codex không có thẩm quyền tạo/nghiệm thu các records này.
Chưa có workbook nhãn chính/quyết định chấp nhận giới hạn: A04 vẫn **PENDING**.

## G. Retry / idempotence

Exclusive run directory ngăn hai writer dùng cùng run_id. Không resume/append vào
failed hoặc success run; chọn run_id mới và authorization mới (bound run_id).
Spark task retry dùng cùng classifier/config/input, `_d06_prediction_sha256`
không chứa PID/timing nên giữ deterministic. Speculation=false, worker reuse=true.
Task maxFailures config4, nhưng local master có retry semantics riêng (local[4]
có thể fail task sau1 attempt); không khẳng định đã kiểm cluster retry4 lần.
Spark Parquet committer được dùng, rồi unique/set/roundtrip validation chặn duplicate
hoặc incomplete output trước publication. TEST kiểm rerun mới3 rows, đổi partitions
2→1 không đổi prediction digests; reuse run_id cũ bị từ chối, không nhân đôi.

## H. Validation / errors

Distributed Spark actions sau write/read: input/output count và key sets (anti-joins),
null/unique keys, marker-present, đúng version/hash, đủ3 decisions và sum=rows,
decision/is_it mapping, source text/hashes, frozen schema types và full typed nested
decode/digest/raw Unicode offsets. Parquet nullability được normalize bằng
toNullable() nhưng runtime constraints vẫn kiểm. Không collect all predictions.
Input file fingerprint rechecked sau execution, trước completion.

Job/classifier/worker/storage exception → run failed, không skip/REVIEW thay thế;
failure.json ghi stage/type/category/timestamp và trỏ protected execution logs,
không chép raw text/full traceback vào publish metadata. OS kill có thể không ghi
failure.json; thiếu completion hợp lệ vẫn là incomplete, không accepted success.

## I. Performance monitoring / distributed risks

Configurable partitions/master/worker-python. Default local[4],3GiB JVM process
heap nếu chưa có override; Windows requires explicit filesystem jar artifact.
Worker namespace không phụ thuộc driver tmp/source checkout. Remote mode đòi
explicit worker-python environment và shared accessible filesystem paths;
local-path implementation chưa là HDFS/object-store transactional backend.

Manifest/validation có actual write duration, jobs/s, per-worker observed RSS max,
model instances/PIDs, max description chars, classify p50/p95/p99 và JVM heap/GC
snapshots. Đây không phải continuous peak/total system RAM. Cần authorized batches,
long/HTML/Unicode stress, skew/partition tuning, cold/warm measurements, RSS/heap/
spill/disk sizing và cluster fault/retry tests nếu deploy cluster. Không ngoại suy
full runtime từ Pilot warm5.54s. Output SHA inventory cần thêm streaming IO.

## J. Recovery procedure

1. Dùng inspect_run, không coi _SUCCESS hoặc directory tồn tại là nghiệm thu.
2. Nếu FAILED/INCOMPLETE, giữ nguyên data/events và protected logs; không xóa,
   overwrite hoặc append để che lỗi. Thu thập input/package/schema/approval digests.
3. Sửa nguyên nhân trong phạm vi được cho phép, kiểm lại preflight; nếu lỗi thuộc
   classifier TV2 thì dừng, không sửa rules để ép pass.
4. Human cấp run authorization mới cho run_id mới; package/input/schema thay phải
   có approvals phù hợp. Run lại dưới namespace mới, đối chiếu keys/digests.
5. Consumer chỉ mở SUCCEEDED đúng scope FULL sau completion/inventory checks.
   Cleanup/retention là thao tác riêng cần được cho phép, không thực hiện ở đây.

## K. A04 approval dependency

Parity/Pilot PASS là technical evidence, không business acceptance. Các FN/REVIEW/
group/subgroup limitations của v0.2.2 cần người chịu trách nhiệm chấp nhận, không
Codex tự duyệt. Không tạo fake APPROVED records để mở full hoặc để test positive
full path. Chưa nghiệm thu A04 → full từ chối thực thi trước Spark/classification.

## L. Exact future FULL command — DOCUMENTATION ONLY, NOT EXECUTED

Chỉ sau khi human đã cấp các files thực và chốt artifact paths. `$A04_SHA`,
`$SCHEMA_APPROVAL_SHA`, `$RUN_AUTH_SHA` phải là SHA exact file do operator cung cấp,
không placeholders được agent tự thay bằng approval giả. Records phải bind run_id
và output_relative `data/processed/d06/v0.2.2/official_20261019_01`.

```powershell
.\.venv\Scripts\python.exe -B src/d06_classification_runner.py --mode full --run-id official_20261019_01 --package artifacts/d06/d06_runtime_09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59.zip --package-sha256 09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59 --partitions 4 --master "local[4]" --windows-fs-jar artifacts/d06/d04-localfs-adapter.jar --execute-full --a04-approval approvals/a04_business.json --a04-approval-sha256 $A04_SHA --schema-approval approvals/d06_schema.json --schema-approval-sha256 $SCHEMA_APPROVAL_SHA --run-authorization approvals/d06_full_run.json --run-authorization-sha256 $RUN_AUTH_SHA
```

Các thư mục artifacts/approvals trên là deployment paths dự kiến, không được tạo
hoặc cấp approval trong lượt này. Java21/Python environment chuẩn bị process-scoped.

## M. Verification boundary / tests / remaining blockers

Tests mới dùng3 real frozen records chọn coverage ACCEPT/REJECT/REVIEW, không feed
machine labels vào classifier. TEST output dưới tmp có cap32 và scope TEST rõ;
đã thực thi writer, reader, distributed validator, completion, failed write evidence,
incomplete detection, schema/source/null/key guards, retry-new-run/idempotence.
Full authorization tests chỉ negative/missing/pending cases; không có positive
full execution/approval giả. Fixture ban đầu đoán retail-title là REJECT nhưng model
trả REVIEW; đã giữ đúng output và sửa fixture dùng frozen inputs, không sửa TV2.

Lượt này có rerun Official tests và parity/Pilot regression; kết quả/mốc evidence
chi tiết ở `data/audit/d06/official_readiness_summary.json`.
Không chạy full classification hay full validation, chưa kiểm production-scale
memory/latency/fault recovery hoặc remote executors. Production schema đã freeze
về code, external schema approval vẫn pending. Positive approved FULL entrypoint
chưa được thực thi có chủ đích theo boundary. Không tự đánh D06 Official PASS.

Mốc bàn giao: D06 PARITY/PILOT PASS; Official runner implementation và preflight
đánh giá theo tests/evidence thực, A04 ACCEPTANCE PENDING; FULL DATASET NOT EXECUTED.

### Final verification evidence

- Official final: **16/16 PASS**, failures/errors/skips=0,45.854s,
  `tmp/d06_official_tests/final_394e49aa07/summary.json`.
- Parity regression: **17/17 PASS**,32.650s; Pilot regression: **17/17 PASS**,
  38.560s; evidence `tmp/d06_official_tests/suite_e667f5d1a2/summary.json`.
  Total latest Official + regressions: **50/50 PASS**. Final Official rerun includes
  destination ancestor/junction escape guard; classifier/schema/regression code
  did not change after the regression run.
- Source compilation PASS; git diff --check PASS; staged files0; HEAD/main unchanged.
- All131 protected files match Pilot protected snapshot (including content/mtime/
  size); production `data/processed/d06` does not exist. Old evidence preserved.
- Runtime package reproducible SHA09e7...; schema27 fields unchanged; preflight
  performed0 classifications. Full approvals created0; full executions0.

Official runner **implementation PASS**, preflight **PASS** are not Official
business/production execution acceptance. Approval and scale blockers above remain.
