# D06 Phase 2 – Controlled Pilot (18/10/2026)

D06 PARITY: **PASS**. D06 PILOT IMPLEMENTATION: **PASS**.
D06 PILOT RUNTIME: **PASS**. D06 FULL DATASET READINESS: **BLOCKED**.
A04 BUSINESS ACCEPTANCE: **PENDING**. D06 FULL DATASET: **NOT EXECUTED**.

Đây là kiểm chứng kỹ thuật Pilot, không phải nghiệm thu D06 Official hoặc chất
lượng classifier toàn dataset. Không promote candidate hoặc thay taxonomy active.

## A. Git status

Ban đầu sạch trên `feat/tv1-d06-parity`, HEAD
`1c365741f0e3dcad9064473ae2c0c6b9f507ae25`.
Tạo `feat/tv1-d06-pilot` từ đúng commit này; HEAD giữ nguyên. Không add, commit,
push, merge/cherry-pick TV2/main, reset, hoặc xóa dữ liệu/evidence có sẵn.

Tạo mới 8 file: bốn source/test dưới đây, báo cáo này và ba audit metadata.
Chỉ sửa một file hiện hữu `src/d06_parity_validation.py`: guard cho phép chạy
regression trên đúng branch Pilot kế thừa parity commit, vẫn bảo vệ D01–D05.
Adapter Phase1 và evidence Phase1 committed giữ nguyên; không sửa D01–D05/TV2.

- `src/d06_classification_runner.py`
- `src/d06_pilot_packaging.py`
- `src/d06_pilot_runtime.py`
- `src/test_d06_pilot.py`
- `data/audit/d06/pilot_review_keys.json`
- `data/audit/d06/pilot_spark_schema.json`
- `data/audit/d06/pilot_validation_summary.json`

Hash/size/mtime **131 file được bảo vệ** (D05 tracked + raw/processed) không đổi.
Output/sample/package chỉ trong tmp được Git ignore; audit không có full source,
reference prediction, private workbook hoặc credentials.

## B. Code/config version

TV2 pinned commit: `e437dcc11dda61f847673b9cc8c5801886c1996d`.
Candidate chỉ định rõ **v0.2.2**:
`1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874`.
Builder luôn đọc exact Git blobs của bốn module, không import bản tùy ý trong tmp:

| Module | SHA-256 exact bytes MATCH |
| --- | --- |
| it_taxonomy.py | `841231033c546cc2bedf141386038104c0a0f1cf9f5a01b80535457c8b42312f` |
| description_processing.py | `ad579397753f2de115faad3bf9ff4d1c8dfebf5ce76eb898f3368ca02a6fec78` |
| it_taxonomy_v010.py | `453bb6bcd22d4cdf866c670f3634b8f1e42a233eb086b650e579b4b1d429dc86` |
| tv2_csv.py | `7839763017c281c36126b8ece9c2015da41b54cccdfca0f365ac4feb48beb903` |

Config mặc định lấy từ cùng pinned Git commit; `--taxonomy-config` external path
chỉ được chấp nhận khi exact bytes/hash/version giống pinned config. Không dùng
active v0.2.0 ngầm định. Không viết lại classifier/rules hoặc feed manual labels.
Phase1 adapter nguyên trạng hash:
`d79ee515ada7c2cdb96764244fa35e4c9c90b093480d8940dee5326f29019f49`.

## C. Packaging design

**A – Runtime Pilot:** ZIP reproducible (fixed entry timestamps, sorted members)
gồm bốn TV2 module, config, adapter Phase1, helper Pilot, parity schema và manifest.
Tám content files + một manifest. ZIP cuối:
`09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59`.

Driver kiểm SHA mọi dependency/config/ZIP trước Spark execution. Spark broadcast
phân phối **bytes ZIP**, không truyền đường dẫn tuyệt đối của driver/máy TV2.
Worker kiểm toàn ZIP trước import, kiểm từng member và nạp vào cache riêng theo
checksum/PID ở worker-local tempfile. Không overwrite file cache khác bytes.
Adapter kiểm lại hash/version bốn module/config; model tạo một lần mỗi partition.
Không cần driver src/tmp filesystem xuất hiện trên máy executor.

Thử addPyFile/SparkFiles thật tại `pilot_20261018_01` bị lỗi Hadoop chmod thiếu
winutils, **trước selection/classification**. Giữ nguyên evidence lỗi, không cài
winutils hoặc sửa D04/D05. Thiết kế cuối dùng broadcast ZIP một cách explicit,
không fallback âm thầm hoặc bỏ qua lỗi. Đã kiểm trên Python workers thực tế.

**B – Git integration Official:** chưa merge/cherry-pick/vendor TV2 vào branch.
Đề xuất review dependency bốn module/config cùng pinned commit/digests, chốt
reviewed integration PR hoặc CI artifact builder có sẵn pinned Git object, publish
immutable package + manifest. Official runtime nên nhận artifact đã kiểm thay vì
đòi Git/source checkout hoặc temporary worktree trên executor. Pilot build cần
Git object TV2 pin hiện có; không tự fetch/merge. Remote cluster smoke test vẫn
chưa thực hiện; local broadcast thành công không thay thế kiểm chứng cluster.

## D. Sample selection

Đọc D05 canonical Parquet, quét features/key để chọn mẫu, **không classify toàn
123849 jobs**. Canonical grain xác minh 123849 rows/unique, null keys 0.

Base **1000**: orderBy `xxhash64(job_id,42), job_id`, limit. Bổ sung deterministic:

| Nhóm | Số membership chọn được |
| --- | ---: |
| 10 description dài nhất (length desc, job_id tie-break) | 10 |
| Empty/whitespace description | 7 |
| HTML/entities | 10 |
| Unicode ngoài ASCII | 10 |
| Known machine REVIEW Phase1 | 33 |
| 20 job-function categories: min job_id mỗi category, sort code | 20 |
| Empty/whitespace title | 0 |

Memberships có giao nhau: **1084 unique jobs** sau dedup, tức 84 khóa thêm ngoài
base. D05 thực tế không có empty title (0), có 7 empty description; không tạo
synthetic job để bù vào Pilot. Empty/missing title được kiểm bằng unit control
riêng, không tính vào kết quả mẫu. Metadata REVIEW chỉ chứa 33 job_ids được rút
từ reference exact-byte hash Phase1; không đưa prediction/reference text vào Git.
Job-function metadata chỉ dùng chọn coverage, không làm classifier input.

Không gọi đây là mẫu đánh giá accuracy/IT rate đại diện, không thay frozen176.

## E. Pilot input count

Run chính cuối: `tmp/d06_pilot/pilot_20261018_03/`.
Input **1084 rows / 1084 unique job_id**, null/duplicate 0.
Chỉ dùng source_title/source_description và job_id; kiểm SHA-256 UTF-8 so D05
trước và trong worker. Không trim/clean/coalesce raw input; empty string có hash
hợp lệ được giữ riêng với null/missing field (lỗi dữ liệu).

## F. Pilot output count

**1084 rows / 1084 unique job_id**, null/duplicate 0, missing/extra keys 0.
Mọi row có `_d06_present=true`. Không silently skip failed jobs.
Full-mode CLI chỉ nhận `pilot`; base-size hard cap1000, total selected hard cap1200
kiểm trước classifier, partitions1..8. Không thể chỉ tăng sample-size thành full.

## G. ACCEPT / REJECT / REVIEW

| Quyết định | Rows | is_it |
| --- | ---: | --- |
| ACCEPT | 49 | true |
| REJECT | 513 | false |
| REVIEW | 522 | null |

Giữ cả ba trạng thái. Missing output không phải REVIEW; runtime/classifier error
không sinh REVIEW. Không suy ra tỷ lệ IT chính thức/accuracy từ phân bố này.

## H. Runtime performance

Python3.11.0 / PySpark4.2.0 / Java21.0.12.1, local[*], 4 partitions,
**4 observed Python workers / 4 classifier instances** cho lượt classify chính.
Java21 chỉ đặt cho process, không thay JAVA_HOME hệ thống.

- Selection + lưu input sample: **12.607s** (không phải classifier throughput).
- Materialized classification + Parquet write hoàn tất: **5.543s**,
  **195.565 jobs/s** cho 1084 jobs. Không dùng lazy count làm bằng chứng thực thi.
- Timed runner block: **36.528s**, gồm session/selection/classification/readback/
  determinism/stop/preservation-after; không gồm CLI startup/package build và
  baseline protected-before hashing.
- Adapter classify-call p50/p95/p99: **2.706 / 6.419 / 13.033ms**; không bao gồm
  mọi chi phí validate/encode/IO. Write timer bao gồm worker bootstrap/serialization.
- Description >=10000 codepoints: 15 jobs, mean classify-call **13.733ms**;
  <10000: 1069 jobs, mean **2.965ms**. Max description 23201 codepoints.

Đây là lượt local **warm cache** sau tests/lượt thử trước, không phải cold benchmark,
không ngoại suy tuyến tính thời gian hay memory cho toàn tập.

## I. Memory / GC observations

Có instrumentation thật, không bịa hoặc suy ra từ count:

- Python WorkingSetSize qua Windows GetProcessMemoryInfo, lấy sau mỗi row:
  observed per-worker min **51089408 bytes**, max **59244544 bytes**
  (~48.72–56.50MiB). Không phải continuous peak, không phải tổng RAM các worker.
- JVM MXBeans trước/sau classify-write: used **1064418168 → 1048983720 bytes**;
  committed **1342177280**; max heap **3221225472 bytes (3GiB)**.
- G1 Young delta: **3 collections / 16ms**; Concurrent GC: **2 / 17ms**;
  Old Generation: **0 / 0ms**. Không cộng hai loại thành một số pause time.

JVM local dùng chung driver/executor, không có số đo remote executor. Không đo
continuous heap peak, spill, tổng OS RSS hoặc tổng retry count độc lập; không
tuyên bố không bao giờ OOM ở full scale. Java heap không bao gồm Python RSS.

## J. Output size

Prediction Parquet data files: **5973763 bytes (~5.70MiB)**, không tính CRC,
_SUCCESS, input snapshot hoặc determinism output. Mọi artifact dưới path tmp run.
Không ghi canonical/production. Error-if-exists, run cũ không bị overwrite/xóa.

## K. Validation results / output contract

PASS: input/output/key reconciliation1084; source text/hash; version/hash v0.2.2;
ba decision/null states; đầy đủ nested arrays/diagnostics/raw/normalized ranges.

Schema Pilot **27 top-level fields**: giữ18 prediction fields (có selected_rule_id
và source wrapper), key-presence metadata, worker provenance, boolean output marker
và các metrics/digest. Full schema: `data/audit/d06/pilot_spark_schema.json`.

**Xử lý khác biệt contract có chủ đích:** Phase1 `_d06_present` là array<string>
cho field-presence ở mỗi struct. Không đổi adapter Phase1. Pilot rename metadata
này thành `_d06_field_keys` ở mọi struct, thêm top-level `_d06_present:boolean`
luôn true cho row đã phân loại. Missing field, explicit null và output missing
không bị trộn. Decoder bridge đảo tên rồi dùng decoder Phase1.

Mỗi prediction được encode → typed decode và strict structural compare ngay trong
worker. Lưu SHA-256 của prediction JSON canonical (object keys sort, arrays giữ
thứ tự); **không lưu JSON backup** để né kiểm nested fields. Sau Parquet, worker
reconstruct từ typed fields, đối chiếu digest cho **1084/1084** rows; kiểm source
hash, raw range bounds theo Unicode codepoint half-open và excerpt đúng lát raw.
Schema field/types khớp khi chuẩn hóa Parquet nullability bằng toNullable(); dữ
liệu runtime vẫn kiểm non-null keys/markers/required version và REVIEW null.

Determinism bounded: **32 real jobs**, đổi **4 → 2 partitions**, typed prediction
digests đều khớp, mismatch0. Không collect toàn bộ predictions lên driver;
chỉ aggregates/distributions và counts nhỏ. Chỉ unit synthetic riêng dùng first().

## L. Regression / tests

- Phase1 regression **17/17 PASS**, 39.786s, frozen176 Python/Spark/Parquet exact,
  evidence mới `tmp/d06_parity/20261018T134516Z_0945209d/`.
- Pilot suite cuối **17/17 PASS**, 47.190s, không skip. Gồm10 unit controls,
  4 live Spark input/worker guards và3 live bounded runner tests.
- Live test runner base8 + edges: **92 real jobs**, 2 partitions; readback/nullable/
  nested PASS; 32-job determinism đổi **2 → 3**, mismatch0. Evidence
  `tmp/d06_pilot/test_8fd77797a055/`.
- Earlier suite16 tests PASS và earlier1084 Pilot cũng giữ nguyên trong tmp;
  không thay chúng bằng frozen reference hoặc dùng synthetic làm Pilot evidence.

```powershell
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B -m unittest discover -s src -p test_d06_parity.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s src -p test_d06_pilot.py -v
```

## M. Error handling

| Trường hợp | Hành vi / bằng chứng |
| --- | --- |
| Missing package / modified ZIP | Integrity failure trước import; tests PASS |
| Missing config / unsupported version / hash mismatch | Build/preflight fail; tests PASS |
| Invalid/non-bigint/null/duplicate key | Data error trước classify; Spark tests PASS |
| Missing source field hoặc source hash sai | Data error, không coalesce/skip; tests PASS |
| Empty title/description có valid hash | Gọi classifier thật; synthetic control trả REVIEW/null |
| Worker source hash failure | Test cố tình bypass preflight, Spark task abort thật, test expected exception PASS |
| Classifier/runtime unexpected exception | Run/task fail, không tạo REVIEW |
| Python MemoryError / JVM/OS OOM | Runtime failure, giữ incomplete run; MemoryError mô phỏng PASS, không gây OOM thật |
| Existing output hoặc path production | Refuse trước Spark/write; tests PASS |
| FULL mode / base-size >1000 | Hard reject trước đọc/classify; tests PASS |
| Schema/roundtrip/Unicode mismatch | Fail-closed; không drop field hoặc sửa TV2 |

Worker lỗi dữ liệu có marker PilotDataError để driver phân biệt với lỗi runtime/
integrity. Run thất bại giữ summary/partial output, không tự overwrite/retry bằng
runner; lần chạy lại phải chọn run path mới. Có thể còn Spark internal retries
theo engine, không có số đo riêng để tuyên bố retry0. Lỗi test được tiêm có chủ
đích không phải lỗi dữ liệu của Pilot thành công; Pilot có0 invalid output rows.

Ví dụ chạy lại chỉ với **path mới**:

```powershell
.\.venv\Scripts\python.exe -B src/d06_classification_runner.py --mode pilot --sample-size 1000 --partitions 4 --output tmp/d06_pilot/NEW_UNIQUE_RUN --taxonomy-config git:e437dcc11dda61f847673b9cc8c5801886c1996d:config/versions/it_taxonomy_v0.2.2.json
```

## N. Full dataset risks

1. Chưa cho phép full mode; cần explicit authorization/runner path mới, không
   bỏ guard bằng sample-size. Không dùng collect predictions tại full scale.
2. Schema/presence-key/metrics contract cần downstream review/version hóa;
   Pilot không chứng minh mọi parser/diagnostic shape của toàn tập đã được phủ.
3. Chỉ benchmark local warm sample. Cần batch tăng dần được phép, partition/
   concurrency tuning, cold/warm comparison, worker/JVM peak RSS/heap, GC/spill,
   stragglers/skew, storage sizing, retry/restart và reconciliation toàn khóa.
4. Broadcast packaging đã reproducible/local-workers PASS; cluster environment,
   Python version/resources và executor cache lifecycle chưa smoke-test từ xa.
5. Failure leaves partial run; Official cần staging/publish/manifest-completion
   và idempotence policy được review, không lẫn partial output với REVIEW.
6. REVIEW được lưu đầy đủ. Nhóm phải chốt consumption/queue và bảng ACCEPT dẫn
   xuất riêng, không mặc định null là false hoặc thống kê Pilot thành IT rate.

## O. Remaining dependencies / verdict

**BLOCKED cho Official**, không blocked cho controlled Pilot đã kiểm:
A04 business acceptance còn pending; cần nhóm chốt candidate/Git integration/
schema contract, cho phép full và kiểm operational readiness phù hợp môi trường.
Chưa nhận workbook nhãn chính; không tự xác nhận nhãn hoặc accuracy toàn tập.

Audit nhỏ và code fingerprints: `data/audit/d06/pilot_validation_summary.json`.
Original references/full text/Parquet chỉ ở tmp. Không commit/push/merge trong lượt
này; không chạy D06 Official hoặc promote taxonomy.

**D06 PARITY = PASS; D06 PILOT IMPLEMENTATION = PASS; D06 PILOT RUNTIME = PASS;
D06 FULL DATASET READINESS = BLOCKED; A04 BUSINESS ACCEPTANCE = PENDING;
D06 FULL DATASET = NOT EXECUTED.**

## Release / GitHub handoff review – 19/10/2026

Các mục A–O phía trên là snapshot implementation ngày18/10, trước khi được phép
commit/push. Lượt19/10 được người dùng cho phép release đúng8 file mới +1 guard
modification; không thêm FULL implementation, merge hoặc promote taxonomy.

Guard Phase1 chỉ thêm branch Pilot khi parity commit là ancestor; nhánh parity
cũ vẫn được chấp nhận, D05 ancestry và kiểm path D01–D05 trong working tree/index
vẫn giữ nguyên. Classifier semantics, version/hash validation, mẫu frozen176 và
hard caps Pilot1000/1200 không đổi. Code SHA đối chiếu audit implementation trước
test release; không sửa source để ép test PASS.

### Fresh clone và artifacts ngoài Git

**Không tái lập đầy đủ chỉ bằng clone Git trống dữ liệu.** Không upload reference,
workbooks, raw/processed, venv hoặc output Parquet để làm repository tự chứa.

| Nhu cầu | Điều kiện/artifact và kiểm integrity |
| --- | --- |
| Build classifier package | Có Git object TV2 `e437dcc11dda61f847673b9cc8c5801886c1996d`; shallow/single-branch clone có thể cần được cấp/fetch object này riêng. Builder không tự fetch/merge, luôn kiểm bốn module và config hash ở mục B. |
| Chạy Pilot trên dữ liệu thực | Bàn giao D05 `data/processed/canonical/jobs` và matching run manifest/inventory ngoài Git; kiểm từng file SHA so inventory/protected_before của snapshot, grain123849 và source SHA trong runner. Raw CSV không bắt buộc nếu đã có đúng canonical. |
| Chạy lại34 tests | Ngoài canonical, nhận `tmp/tv2(1).zip` exact bytes: SHA `11cccd285cabc6dbc430598e8275becb26b68dc989d424786f4577ae52db7123`. Parity prepare kiểm CRC/44 files/path/hash và giải nén an toàn; Pilot tests dùng prediction reference đã xác minh từ gói này. Không cần workbook nhãn chính để chạy tests. |
| Đối chiếu evidence Pilot đã lưu | Bàn giao riêng run `pilot_20261018_03` gồm input sample, predictions/determinism Parquet, schema, summary và protected_before; không đưa full text này vào Git. Kiểm code/schema/package digests và read-only output_validation, không overwrite run. |
| ZIP runtime byte-identical với evidence | Có thể bàn giao riêng immutable `d06_runtime_09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59.zip`; whole ZIP SHA là phần09e7... đầy đủ trong tên/manifest audit. Worker kiểm whole ZIP trước import rồi từng member. |
| Python/Spark/Java/Windows IO | Tạo môi trường Python3.11 + PySpark4.2.0, Java21 process-scoped. Windows cần local-FS adapter D04 ignored jar, có thể build lại từ tracked source bằng `clean_data.ensure_windows_localfs_adapter(project_root)`; chỉ gọi helper, không chạy D04 ETL/main. JDK javac/jar và PATH đúng version là prerequisite. |

ZIP builder tái tạo ổn định trong môi trường build đã kiểm. Git autocrlf hoặc
Python/zlib khác có thể đổi bytes helper/schema hay archive SHA khi rebuild;
không gán SHA09e7... cho một ZIP mới chưa đối chiếu. Với rebuild, kiểm nguyên
TV2/config pinned digests, tạo/kiểm manifest và ghi whole-ZIP SHA mới cho run mới.
Để tái hiện chính xác evidence cũ, dùng immutable ZIP có đúng SHA đã bàn giao.
Runtime workers không đòi Git checkout, reference tmp hoặc đường dẫn máy TV2.

### Read-only Official readiness checklist

1. Schema27 fields/presence boolean/field-key metadata đã kiểm Pilot nhưng **chưa
   chốt production contract/version và downstream approval**.
2. Production output path **chưa chốt/chưa tạo**. Đề xuất namespace riêng versioned
   theo taxonomy/run_id dưới data/processed/d06, không canonical và không reuse
   tmp Pilot; cần phê duyệt trước khi thực hiện.
3. Pilot refuse existing run, giữ partial failure. Official cần run states,
   staging→publish/completion manifest, retry/idempotence và recovery policy.
4. Broadcast ZIP đã chạy workers local thật; cần chốt dependency/artifact CI/Git
   integration. Remote-executor smoke test cần nếu chọn cluster deployment.
5. Lưu đủ ACCEPT=true, REJECT=false, REVIEW=null và marker output-present riêng;
   bảng ACCEPT dẫn xuất không được làm mất queue REVIEW hoặc coi missing là REVIEW.
6. Long-description samples cho thấy chi phí tăng; WorkingSet snapshots không
   chứng minh peak memory full-scale. Cần edge/stress được phép, không gây OOM thật
   trong release này.
7. Partitions4 có evidence local; Official cần tuning concurrency/skew/model-init
   theo tài nguyên, không suy ra full benchmark từ5.54s.
8. Cần observability cho throughput/latency, driver+worker RSS/heap/GC peaks,
   spill, retries/errors và disk; số đo Pilot warm-cache không đại diện toàn tập.
9. A04 business acceptance vẫn **PENDING**; workbook nhãn chính chưa được nhận.
   Handoff kỹ thuật không tự nghiệm thu A04 hoặc promote v0.2.2.
10. Official audit cần immutable input/code/config/schema digests, run manifest,
    distributed key anti-joins/grain/null/decision/nested/source validation và
    output-completion gate; không collect toàn bộ predictions về driver.

Stacked review base: **feat/tv1-d06-parity**, không main khi parent chưa merge.
Chi tiết test rerun/read-only Parquet release nằm trong object `release_review`
của `pilot_validation_summary.json`; toàn bộ evidence tmp cũ được giữ nguyên.

Kết quả release19/10: **34/34 tests PASS**, 0 failures/errors/skips; parity17
trong42.003s và Pilot17 trong38.476s. Evidence mới:
`tmp/d06_pilot_release/20261019_9708b3cef0/release_result.json`.
Đọc lại Parquet Pilot cũ (không classify lại1084):1084 rows/unique, null/duplicate/
missing/extra0;49 ACCEPT/513 REJECT/522 REVIEW; typed nested/source/hash/version/
nullable validation PASS1084. Prediction data files vẫn5973763 bytes; ZIP SHA09e7...
khớp;131 protected files hash/size/mtime không đổi. Không sửa source trong release.
