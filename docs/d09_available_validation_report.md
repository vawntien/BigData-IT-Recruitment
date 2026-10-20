# D09 — Kiểm định thực tế các artifact hiện có

Ngày 20/10/2026, Asia/Bangkok. Run `d09_20261020_01`, 06:11:28–06:12:21 UTC
(13:11:28–13:12:21 giờ Bangkok). Thời gian validator 52.964 giây, gồm kiểm tra IO,
ZIP và Spark startup; **không phải runtime benchmark pipeline**.

## 1. Kết luận và phạm vi

| Trạng thái kiểm tra | Số lượng |
| --- | ---: |
| PASS | 22 |
| FAIL | 0 |
| BLOCKED | 9 |
| NOT APPLICABLE | 2 |
| Tổng | 33 |

**D09 AVAILABLE ARTIFACT VALIDATION: PASS.**
**D09 FULL PIPELINE VALIDATION: BLOCKED – D06 FULL.**
**D06 FULL: NOT EXECUTED.** A04/Q07 acceptance vẫn PENDING.

Không dùng tỷ lệ PASS để gọi toàn pipeline hoàn tất. 7 unit test validator PASS
được báo riêng, không cộng vào 33 kiểm tra dữ liệu/evidence; các test D07/D08 lịch
sử cũng không phải kiểm tra dữ liệu mới hay approval nghiệp vụ.

Phạm vi thật: D05 canonical, D07 ALL-JOBS staging, D08 D05/D07 workloads và ZIP
bàn giao hiện có. Không D06 Full, không classifier, không chạy lại benchmark,
không ghi normalization/Parquet, không sửa raw/canonical/audit D05–D08.

## 2. Git và baseline

Working tree ban đầu sạch tại D08 HEAD, sau đó tạo branch
`feat/tv1-d09-validation` từ `ff721bcf7988841a2b80e3f263f3ef8a69188278`.
HEAD vẫn giữ nguyên; không stage, commit, push, merge, rebase hoặc reset.

| Release | SHA exact |
| --- | --- |
| D05 | `457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b` |
| D06 Runner | `5fda1789b84494a856743c087d10fc511d013d93` |
| D07 | `479d3d83ff3194a5556ce29884c92478c90a969c` |
| D08 | `ff721bcf7988841a2b80e3f263f3ef8a69188278` |

Ancestor/source-byte checks PASS; remote `git ls-remote` khớp cả bốn release.
`release_refs.json` là observation bổ sung cho kiểm tra Git, không thêm số kiểm tra.
`git_head` trong manifest D05/D07 là HEAD lúc chạy trước release commit, không phải
lỗi release identity; đối chiếu source/policy SHA và completion seal riêng.

## 3. Tái sử dụng scaffold có giới hạn

Đã đọc scaffold branch `support/tv1-d09-validation-scaffold`, commit
`9a598b9076a5272834283cbe856ef19de22322db`: runner, unit tests, validation plan và
reusable validation rules. Không checkout/copy scaffold hoặc coi kết quả smoke
là official evidence. Tái sử dụng logic non-null/unique key, row/grain preservation,
reconciliation, NULL preservation và trạng thái phụ thuộc trong validator thực tế.

Các kỳ vọng cũ không được kế thừa máy móc:

- D05/D07/D08 không còn là placeholder PENDING; đã kiểm trực tiếp.
- Không ép D07 về USD: policy thật là NO FX và giữ từng currency.
- Không yêu cầu các field giả `is_it_job`/`it_category`; D06 có contract riêng,
  nhưng chưa có Full output nên các kiểm tra phụ thuộc bị BLOCKED.
- Không dùng boolean `official=True` hoặc nhãn nguồn hardcode làm bằng chứng
  authentic data. D09 bind Git bytes, manifests, fingerprints và raw source hashes.

## 4. Kết quả thực tế

### D05/D07

| Kiểm tra trực tiếp | D05 | D07 |
| --- | ---: | ---: |
| Rows | 123849 | 123849 |
| Unique job_id | 123849 | 123849 |
| NULL keys | 0 | 0 |
| Duplicate keys | 0 | 0 |
| Top-level fields | 50 | 28 |
| Schema name/type/order/nullable/nested | EXACT | EXACT |

Hai chiều `exceptAll` của key sets đều rỗng. JOIN job_id giữ 123849 rows/unique,
không mất hoặc nhân grain. Nullability trong schema đọc Parquet được đối chiếu
đúng schema audit readback; non-null job_id còn được kiểm trên giá trị thật.

D05 source_title/source_description được kiểm SHA256 UTF-8 trong Spark, source
path `data/raw/postings.csv` và schema version `d05-v1`. Đọc lại raw bằng Python
CSV strict/multiline độc lập, đối chiếu 123849 key/hash tuples với canonical:
0 mismatch/0 missing. Chỉ stream key/hash về driver; không ghi raw text vào audit.

D07 recompute transform **trong bộ nhớ** bằng policy release, so `exceptAll` cả
hai chiều trên mọi field với Parquet hiện có. PASS bao gồm selected whole bundle,
raw structs, source metadata, source_conflict, decimal values, NULL, reasons,
conversion factors và provenance. Không chạy lại CLI normalization hoặc ghi output.

| Salary metric | Actual |
| --- | ---: |
| USABLE | 36059 |
| MISSING | 87776 |
| INVALID | 14 |
| AMBIGUOUS / EXCLUDED | 0 / 0 |
| Usable min / max observations | 29793 / 29793 |
| Usable med observations | 6266 |
| Reported coverage | 36073 / 123849 = 29.1266% |
| Usable coverage | 36059 / 123849 = 29.1153% |

14 INVALID đều selected med_salary=0; không biến 0 thành missing. Non-USABLE
normalized values giữ NULL. BOTH_AGREE là một bundle/job, không hai quan sát.
Coverage mẫu số là ALL JOBS, **không phải IT population**.

Policy `d07-salary-v1`, SHA
`3c0e0a9b2c59bddff828d9d423d6659e19a3ceafae480c1cd3e50aa54221382b`.
Currency USD/EUR/CAD/AUD/GBP/BBD giữ riêng, không FX. Annual factors YEARLY=1,
MONTHLY=12, WEEKLY=52, BIWEEKLY=26, HOURLY=2080 là policy assumptions, không bảo đảm
actual annual earnings. Không pool posted native với normalized annual equivalent.

Completion SUCCEEDED, manifest/validation/output inventory hashes, audit copies
và fingerprints đều khớp dữ liệu hiện hành:

- D05: `729db5102bda622eef2f6d3cc0d88b851516ad01f6050f3d0f75debb99e17270`.
- D07: `c43c79ea9113773ae6c5d66b64dc884775efd344888971ecf882c96803318bbd`.

### D08

60 observations = 15 warmups + 45 measured; 5 workloads × 3 masters ×
(1 warmup + 3 measured). Kiểm mỗi repeat ID và summary cell; tính lại min,
median, max, samples và speedup=`median(local[1])/median(target)` từ raw CSV.
Mọi giá trị khớp; kết quả scalar mỗi workload nhất quán giữa repeats/configs.

Parse lại 3 raw event logs, đối chiếu 60 metric groups và hashes; measured task
attempts=585. Config giữ shuffle=4, heap=1GiB và các settings khác đồng nhất,
ngoại trừ master/startup/event log destination. Event logs giữ local, không copy
vào audit D09 hay Git. Không phát sinh benchmark timings mới.

SVG khớp working bytes, D08 committed blobs và receipt:

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| runtime_median.svg | 4790 | `c8f54f08214d2ef4e07b8534fa9cf9c83665ffa72e724927bb8ee669f3aa07da` |
| speedup.svg | 4800 | `772eb09abac8fdd712bdb016251b7938cebf89cf59f8a01a05b8e03f5c47ce1e` |

Stored D07 release tests19/19, D08 original/release tests11/11 khớp source/test SHA.
Chỉ verify evidence lịch sử, không chạy lại các suite dài. D09 unit tests riêng7/7.

Giới hạn được bảo toàn: một máy Spark local, không multi-node, startup đo riêng,
OS cache/JIT/background load không kiểm soát; Spark không chủ động persist cache;
median chỉ3 lượt đo, có repeat drift; không linear-scaling claim và local[4]
không luôn tối ưu. Không D06/full-pipeline timing. Metadata `timing_boundary` trong
runtime summary được kế thừa từ session helper D08, **không mô tả một benchmark
D09 mới**; elapsed_seconds D09 chỉ là thời gian thực thi validator.

### Handoff ZIP

Đọc trực tiếp, không extract/ghi đè:
`D:/Learning/Bigdata/TV1_Handoff_D05_D07.zip` và thư mục cùng tên.

37 ZIP members,35 payload files,36 checksum rows: exact inventory, no duplicate
members/path traversal, CRC, per-member size/SHA256 và SHA sidecar đều PASS.
Payload D05/D07 fingerprints khớp dữ liệu nguồn hiện hành.
ZIP SHA256: `e3269658c1e3ca0031efd6d4249f8389c3d3c41615cb7a18987f37c5635ebc43`.
Các checksum kiểm consistency với receipt local, không thay chữ ký/xác thực tổ chức.
Không upload ZIP hoặc đưa dữ liệu/private text vào Git.

## 5. Chín blocker và hai mục không áp dụng

1. A04 formal business acceptance chưa được cung cấp; docs/parity không là approval.
2. External approval schema D06 chưa được cung cấp.
3. Run-specific D06 Full authorization chưa được cung cấp.
4. D06 Full key/schema/nested evidence validation chưa có output để kiểm.
5. D06 Full decisions/source/Parquet/completion validation chưa thực thi.
6. Official IT salary JOIN chờ validated D06 Full và ACCEPT population policy.
7. Q07 business signoff và IT analytics còn chờ5 business decisions/D06 population.
8. D08 full-pipeline benchmark chưa có D06 classification workload.
9. Final IT dashboard/export/acceptance chưa có official analytics được duyệt.

NOT APPLICABLE: FX/USD conversion (policy cấm FX), multi-node benchmark (ngoài
phạm vi local D08). Không ghi hai mục này thành PASS.

Không dùng Pilot thay Full, không tự tạo approval. D09 kiểm production
`data/processed/d06` không tồn tại. Schema/code readiness không tự mở Full gate.

## 6. Commands và khả năng tái lập

Commands thực thi ở root repo (các git show/inspection bổ sung nằm trong transcript):

```powershell
git status -sb
git rev-parse HEAD
git branch --list feat/tv1-d09-validation
git switch -c feat/tv1-d09-validation ff721bcf7988841a2b80e3f263f3ef8a69188278
git show support/tv1-d09-validation-scaffold:src/d09_validation_scaffold.py
git show support/tv1-d09-validation-scaffold:src/test_d09_validation_scaffold.py
git show support/tv1-d09-validation-scaffold:docs/d09_validation_plan.md
git show support/tv1-d09-validation-scaffold:src/validation_utils.py
git ls-remote origin refs/heads/feat/tv1-d05-official refs/heads/feat/tv1-d06-official-runner refs/heads/feat/tv1-d07-salary refs/heads/feat/tv1-d08-benchmark
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B -m unittest discover -s src -p test_d09_validate_available.py -v
.\.venv\Scripts\python.exe -B src/d09_validate_available.py --run-id d09_20261020_01 --windows-fs-jar tmp/d04-localfs/d04-localfs-adapter.jar
```

Unit suite còn chạy một lần qua unittest API để ghi `validator_tests.json`,7/7
PASS; không cộng hai lần chạy thành14 test. Dòng `bad FAIL` trong unit log là
negative-control kiểm validator ghi FAIL khi có lỗi, không phải FAIL dữ liệu thật.

Rerun phải dùng NEW run_id; code từ chối overwrite audit đã có. Không cần rerun
để nộp báo cáo này. Java chỉ process-scoped, không thay config hệ thống. Runtime
Python3.11.0, PySpark4.2.0, Java21.0.12.1, local[2], UTC, heap1GiB. Windows filesystem
JAR là dependency có sẵn; không cài runtime hoặc chạy ETL. Không claim cluster QA.

## 7. File mới và evidence

- `src/d09_validate_available.py`: executable validator trên dữ liệu thật.
- `src/test_d09_validate_available.py`:7 unit tests cho count/status, raw timing
  statistics, tampered statistics, repeat/missing/NaN/result drift, archive paths.
- `docs/d09_available_validation_report.md`: báo cáo này.
- Audit root `data/audit/d09/d09_20261020_01/`:
  - `protected_before.json`:184 protected file size/mtime/SHA, gồm old tracked files
    và raw/processed data; snapshot cuối khớp tuyệt đối.
  - `validation_results.json` / `.csv`:33 rows, từng status và actual evidence.
  - `validation_summary.json`:counts, runtime, command, source SHA và verdict scope.
  - `evidence_inventory.json`:inventory tại thời điểm runner kết thúc; không tự hash.
  - `validator_tests.json`:unit log, results và source/test SHA.
  - `release_refs.json`:remote baseline observations.
  - `final_verification.json`:receipt cuối, hashes của report/code/audits bổ sung,
    kiểm lại counts/status/source identity và Git safety; không tự hash.

Không sửa/ghi đè evidence cũ. Toàn bộ file D09 mới giữ untracked/unstaged để người
dùng review; không commit/push trong lượt này. Git diff --check trên tracked files
vốn rỗng; file mới được kiểm whitespace riêng trước bàn giao.

## 8. Readiness cho báo cáo nộp môn

**Sẵn sàng** dùng kết quả D05 canonical, D07 ALL-JOBS staging, benchmark D08 có
giới hạn và evidence D09 available-artifacts trong báo cáo kỹ thuật. Luôn ghi
scope, denominators, limitations và9 blockers; không tuyên bố complete IT pipeline,
A04/Q07 accepted, D06 Full PASS hoặc kết quả thị trường IT chính thức.

Next action tối giản: review D09 files/evidence → human chốt A04/workbook, schema
và run authorization → chỉ sau đó chạy/validate D06 Full theo quy trình riêng →
kiểm official salary join/analytics/dashboard và các gate còn BLOCKED. Q07 policy
signoff có thể xử lý song song; không tự biến nó thành approval D06.
