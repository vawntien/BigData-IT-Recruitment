# D11 — Bàn giao TV1 và hướng dẫn kiểm chứng/tái lập

**21/10/2026 — PHASE 1: AVAILABLE EVIDENCE.** Không phải nghiệm thu final integration.
D06 Full NOT EXECUTED, A04/Q07 business acceptance PENDING. Tài liệu này không cấp
quyền chạy pipeline hay ký nhận thay TV2/TV3. [Status matrix](d10_d11_status_matrix.md).

## 1. Đọc nhanh cho nhóm ba người

1. Đọc [D10 technical report](d10_technical_report.md) cho nội dung báo cáo môn học.
2. Dùng [evidence index](d10_d11_evidence_index.md) để lấy exact source/run/commit.
3. Nhận package D05/D07 và kiểm SHA trước mở dữ liệu.
4. Không lấy Pilot, sample dashboard hoặc ALL-JOBS salary làm official IT results.
5. Chốt các human gates, rồi mở lượt D06 Full riêng khi thực sự được cho phép.

TV1 phụ trách storage/schema/keys/provenance/Spark; TV2 nhận dữ liệu, chốt semantics
và analytics; TV3 nhận approved aggregates/contract và giao diện. Người ký từng
gate phải được nhóm giao quyền, không suy từ tên người commit hoặc metadata nhãn.

## 2. Repository và version inventory

Root thực tế: `D:/Learning/Bigdata/BigData-IT-Recruitment`.
Remote: [GitHub repository](https://github.com/vawntien/BigData-IT-Recruitment).

```text
BigData-IT-Recruitment/
  src/                    Spark ETL, D05–D09 runners/validators/tests
  config/                 D07 policy và các config thuộc checkout này
  docs/                   reports, handoff, dashboard/final drafts
  data/raw/               local CSV nguồn — ignored
  data/processed/clean/   local clean Parquet — ignored
  data/processed/canonical/ local D05 — ignored
  data/processed/d07/     local D07 ALL-JOBS staging — ignored
  data/audit/             tracked selected evidence, không mặc định mọi audit đều accepted
  data/analytics/         generated analytics — ignored trừ .gitkeep
  dashboard/             UI/development sample, không official analytics
  tmp/                   packages, filesystem JAR, raw Spark logs/tests — ignored
  .venv/                 local runtime — ignored
```

| Stage | Branch release | Exact commit |
| --- | --- | --- |
| D05 | feat/tv1-d05-official | `457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b` |
| D06 runner | feat/tv1-d06-official-runner | `5fda1789b84494a856743c087d10fc511d013d93` |
| D07 | feat/tv1-d07-salary | `479d3d83ff3194a5556ce29884c92478c90a969c` |
| D08 | feat/tv1-d08-benchmark | `ff721bcf7988841a2b80e3f263f3ef8a69188278` |
| D09 | feat/tv1-d09-validation | `b668c763a3d7bf10a604a11b61a9e7b2f9e9edf5` |
| D10/D11 Phase 1 | feat/tv1-d10-d11-docs | Chưa commit; parent=D09 ở trên |
| TV2 classifier pin | feat/tv2-analysis, lịch sử | `e437dcc11dda61f847673b9cc8c5801886c1996d` |
| TV2 Q07 review pin | feat/tv2-analysis, snapshot review | `8323b5b9f4025ec4909ead912aafbef6c5825e6c` |

Không tự merge các stacked branches vào main. Hash release khác `git_head` trong
execution manifest vì artifacts thường tạo trước release commit. TV2 files không
có trong branch TV1 phải đọc bằng `git show <pin>:<path>`, không invent local path.

## 3. Artifacts thật hiện có

Các paths tương đối trong bảng lấy root trên làm gốc. Dữ liệu Parquet không nằm
trong Git; clone source đơn thuần không tạo ra chúng. E03–E14,E18.

| Artifact | Path thực tế | Scope / identity |
| --- | --- | --- |
| D05 | `data/processed/canonical/jobs/` | 123849 jobs,50 fields,d05-v1;4 parts397164694 bytes |
| D05 runtime manifest | `data/processed/canonical/d05_run_manifest.json` | Bản local đối chiếu manifest audit |
| D07 | `data/processed/d07/staging/d07_20261019_01/salaries.parquet/` | 123849 jobs,28 fields,ALL-JOBS;4 parts2846357 bytes |
| D07 run metadata | `data/processed/d07/staging/d07_20261019_01/` | run_manifest,validation_summary,output_inventory,completion |
| D08 audit | `data/audit/d08/d08_20261020_01/` | CSVs,manifest,validation,tests,SVG,receipt |
| D08 raw evidence | `tmp/d08_benchmark/d08_20261020_01/` | per-master events,result.json,query_plans; không Git |
| D09 audit | `data/audit/d09/d09_20261020_01/` | 8 files,33 checks;unit tests tách riêng |
| D06 immutable package | `tmp/d06_official_artifacts/d06_runtime_09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59.zip` | Package ready, không output classification |
| Windows FS adapter | `tmp/d04-localfs/d04-localfs-adapter.jar` | Local IO dependency; tmp không được clone cùng source |
| A04 frozen references | `tmp/tv2_a04_handoff_extract/tv2_04/a04_taxonomy_v0_2_2_20261014/` | Private development/reference data, không official population |
| D06 Full Parquet | **NOT AVAILABLE** | Namespace dự kiến `data/processed/d06/v0.2.2/<run_id>/predictions/` |
| Main workbook160 | **MISSING tại audit TV1 gần nhất** | Không tạo workbook thay thế từ snapshot |

Kiểm tracked/ignored bằng `git ls-files`, `git check-ignore -v <path>`, không suy từ
thư mục tồn tại. [Gitignore](../.gitignore) áp dụng generated data/raw/tmp/venv;
[attributes root](../.gitattributes) bảo toàn D09 exact bytes và
[attributes D08](../data/audit/d08/d08_20261020_01/.gitattributes) bảo toàn SVG D08.
D05/D07 chưa có cùng mức eol pinning: xem cảnh báo reproduction bên dưới.

## 4. Package D05/D07 gửi nhóm

| Thuộc tính | Giá trị đã kiểm |
| --- | --- |
| ZIP local | `D:/Learning/Bigdata/TV1_Handoff_D05_D07.zip` |
| Folder local | `D:/Learning/Bigdata/TV1_Handoff_D05_D07/` |
| Size | 400169176 bytes |
| Members | 37 files;35 payload + manifest + checksum CSV |
| SHA256 | `e3269658c1e3ca0031efd6d4249f8389c3d3c41615cb7a18987f37c5635ebc43` |
| Sidecar | `D:/Learning/Bigdata/TV1_Handoff_D05_D07.zip.sha256` |
| Payload | D05_Canonical15 files,D07_Salary15,D06_Status4,README1 |

Đã kiểm tồn tại/size/SHA/member count khi soạn Phase 1. CRC và all-member SHA,
manifest/payload completeness có evidence D09; không diễn giải thành rerun CRC mới
trong lượt docs. Package chỉ có D06 status/readiness, **không có Full predictions**.
Không chứa runtime/venv/raw/private main workbook hoặc final IT analytics.

Manifest kiểm35 payload files, không tự hash. SHA256SUMS.csv kiểm payload+manifest
(36 rows), không tự hash. ZIP sidecar bind whole archive khi đối chiếu hash qua
kênh tin cậy; hash consistency không thay xác thực người gửi. E18–E19.

**Delivery status:** local package available; chưa có bằng chứng upload Drive hoặc
delivery acknowledgement. Không ghi đã gửi/đã nhận nếu chưa có receipt của nhóm.
Job descriptions/URLs cần phân phối trong phạm vi được phép; không commit ZIP/data.

## 5. Kiểm chứng không chạy pipeline

Commands sau là hướng dẫn cho người nhận, không yêu cầu rerun trong lượt docs:

```powershell
git status -sb
git rev-parse HEAD
Get-Item -LiteralPath 'D:\Learning\Bigdata\TV1_Handoff_D05_D07.zip' | Select-Object Length
Get-FileHash -Algorithm SHA256 -LiteralPath 'D:\Learning\Bigdata\TV1_Handoff_D05_D07.zip'
```

Không hash qua PowerShell text pipeline. Đọc binary Git blob bằng Python
`subprocess.check_output`, không `.decode()` trước hash. Ví dụ audit read-only:

```python
# Chạy Python ở repository root; không sửa evidence.
from pathlib import Path
import hashlib, json, subprocess
root = Path.cwd()
receipt = json.loads((root / "data/audit/d09/d09_20261020_01/final_verification.json").read_text(encoding="utf8"))
pin = "b668c763a3d7bf10a604a11b61a9e7b2f9e9edf5"
for name, expected in receipt["artifacts"].items():
    local = (root / name).read_bytes()
    blob = subprocess.check_output(["git", "show", pin + ":" + name])
    assert local == blob
    assert len(local) == expected["bytes"]
    assert hashlib.sha256(local).hexdigest() == expected["sha256"]
```

`final_verification.json` không tự hash; root receipt cần nhận từ trusted release.
Các flags commits0/staged0 trong D09 receipt mô tả lúc validation trước release,
không phủ nhận commit D09 đã tạo sau đó. Không sửa audit lịch sử để phản ánh Git mới.

Trước mở Parquet, xác minh inventory fingerprint với D07 seal và D08 manifest:
D05 `729db5102bda622eef2f6d3cc0d88b851516ad01f6050f3d0f75debb99e17270`,
D07 `c43c79ea9113773ae6c5d66b64dc884775efd344888971ecf882c96803318bbd`.
Có thể dùng `normalize_salary.inventory` ở Python và so stored value; không tự
đổi serialization fingerprint. Seal SUCCEEDED phải bind manifest/validation/
inventory hashes; `_SUCCESS` đơn độc không đủ.

## 6. Reproducibility: kiểm chứng trước, rerun sau

**Không thực thi các lệnh tái lập dưới đây trên workspace chứa output đã release.**
Ưu tiên kiểm artifacts hiện có. Rerun là công việc riêng, được phép rõ, trong
clone/checkout mới có đủ dependencies và disk; giữ audit/log gốc. Không reset,
clean hoặc đổi Git global config để chạy. Không có script all-in-one được tạo.

### 6.1 Runtime và exact bytes

Theo [README](../README.md): Python3.11, PySpark4.2.0, Java21. Chọn Java process-only:

```powershell
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -c "import sys,pyspark;print(sys.version);print(pyspark.__version__)"
& "$env:JAVA_HOME\bin\java.exe" -version
```

Fresh clone cần tải dataset đúng source snapshot, cài dependencies theo README,
nhận/rebuild filesystem JAR theo code D04 và verify hashes; không copy .venv giữa
máy. Phải tính cả JVM+Python workers+OS khi chọn heap/concurrency. Local successful
preflight không chứng minh Full-scale RAM hoặc remote-cluster deployment.

Hash policy/source là exact bytes. D05/D07 ở checkout khác có thể LF→CRLF khi
core.autocrlf=true; clone riêng dùng cấu hình **repo-local/clone-scoped giữ bytes**,
hoặc xuất exact Git blobs bằng binary API rồi kiểm SHA trước chạy. Không thay
Git global settings hoặc parse/reserialize JSON để làm hash trông khớp.

### 6.2 D05 — chỉ trong checkout/output riêng

Instruction/source gốc: [D05 report](d05_official_report.md),
[builder](../src/build_canonical_jobs.py). Checkout baseline D05 và đảm bảo D04
clean inputs, raw source, pinned A03 object/JAR có sẵn. Lệnh lịch sử:

```powershell
.\.venv\Scripts\python.exe -B src/build_canonical_jobs.py
```

**Cảnh báo:** builder có `write.mode('overwrite')` và ghi canonical/audit/report.
Guard manifest không làm thao tác này thành read-only. Không chạy trên canonical
hiện có hoặc root đang soạn tài liệu; dùng clone riêng và output namespace riêng
theo root clone. So schema50,keys123849,72-check audit, source hashes và manifests;
metadata/time/Parquet file UUID mới có thể khác, không mong whole-run bytes giống
lịch sử. Phân biệt semantic reproduction với exact artifact verification.

### 6.3 D07 — new run ID, không overwrite

Instruction: [D07 report](d07_salary_report.md). Cần branch tên
`feat/tv1-d07-salary`, D06 runner ancestor, D05 exact fingerprint và nguyên D01–D06
tracked baseline. Không gọi D06 để chạy D07 staging.

```powershell
.\.venv\Scripts\python.exe -B src/normalize_salary.py --run-id d07_REPRO_NEW --master "local[4]" --partitions 4 --windows-fs-jar tmp/d04-localfs/d04-localfs-adapter.jar
```

`d07_REPRO_NEW` chỉ là tên ví dụ: xác minh chưa tồn tại ở cả processed/audit. Kiểm
whole-source,USABLE/MISSING/INVALID,decimal/NULL/FX0,typed roundtrip và completion.
New run không được thay seal/evidence `d07_20261019_01`.

### 6.4 D08 — workload rerun độc lập, không ETL

Instruction: [D08 report](d08_benchmark_report.md), branch
`feat/tv1-d08-benchmark`, D07 ancestor và exact D05/D07 fingerprints. Cần không có
production D06 namespace theo guard scope của benchmark hiện tại.

```powershell
.\.venv\Scripts\python.exe -B src/d08_benchmark.py --run-id d08_REPRO_NEW --partitions 4 --repeats 3 --seed 42 --windows-fs-jar tmp/d04-localfs/d04-localfs-adapter.jar
```

Giữ run ID mới, logs cũ và cùng query/settings. Timings mới **không phải** số đo
run cũ; không ghi đè bảng/figure lịch sử hoặc mong khớp milliseconds. So correctness,
measurement inventory và methodology, báo drift thật. Không chạy để hoàn thiện docs.

### 6.5 D09 — lưu ý guard Git cụ thể

Instruction: [D09 report](d09_available_validation_report.md),
[validator](../src/d09_validate_available.py). Read existing JSON/CSV và kiểm receipt
là đường an toàn nhất; unit suite7 checks có thể chạy độc lập không Full validation:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s src -p test_d09_validate_available.py -v
```

**Giới hạn tái lập hiện hữu:** `git_releases()` của validator yêu cầu branch
`feat/tv1-d09-validation` và HEAD **bằng D08 commit**, không chỉ D08 ancestor.
Do đó chạy runner nguyên trạng trên D09 release hoặc branch docs sẽ ghi FAIL Git
baseline; NEW run_id riêng không giải quyết guard này. Không sửa code hoặc bỏ gate.

Muốn tái lập toàn bộ lịch sử trong lượt riêng: dùng clone cô lập ở đúng D08 HEAD,
tạo branch D09 đúng tên, cung cấp exact **untracked** validator/test blobs từ D09
release bằng binary copy, chuẩn bị datasets/package/logs/test evidence/handoff đúng
paths rồi dùng NEW run_id. Không checkout/reset workspace đang giữ dữ liệu release.
Raw D08 events và các test summaries dưới tmp là dependency local, không được clone
tự động; thiếu chúng cần báo thiếu, không giả PASS.

```powershell
# Chỉ trong môi trường cô lập đã đáp ứng guard/dependencies; không chạy lượt docs.
.\.venv\Scripts\python.exe -B src/d09_validate_available.py --run-id d09_REPRO_NEW --windows-fs-jar tmp/d04-localfs/d04-localfs-adapter.jar
```

Stage-one runner evidence không tự tạo tất cả release receipts bổ sung. Unit-test
receipt, release refs và final verification của lượt gốc là các bước kiểm bổ sung,
không tự sao chép để đại diện một run mới. E13–E14.

## 7. Data contracts giao TV2/TV3

| Consumer | Nhận ngay | Chưa có / điều kiện |
| --- | --- | --- |
| TV2 schema/source review | D05/D07 package + hashes,schemas,policies,audits | Không có IT membership Full |
| TV2 A05 official | Code candidate/stable evidence trong TV2 pin | D06 FULL seal + source view/binding và approvals |
| TV2 A06–A08 | Q07 v2 candidate và D05 structural attributes | Official IT population, semantics và query approvals |
| TV3 development | Existing UI/mock modes, D08 SVG, technical D09 quality evidence | Không dùng sample làm official metrics |
| TV3 final dashboard | Chưa có official IT analytics export | TV2 accepted run/tables/hashes/filter capabilities |

D05/D07 grain1 job_id/row, key bigint; dictionary schemas là nguồn chuẩn, không
invent flat aliases. Join D06 sau này cần exact key sets/scope FULL; khi tạo ACCEPT
view vẫn giữ REVIEW/REJECT trong classification audit. Explode job_functions/
industries/benefits riêng trước aggregate; `countDistinct(job_id)` chống many-to-many
duplication nhưng không tự cứu được monetary aggregation hoặc sai denominator.

TV3 [local draft contract](dashboard/dashboard_data_contract_draft.md) chưa ký;
UI table names là proposed, không khẳng định physical files tồn tại. Schema/source
adapter phải explicit sau khi TV2/TV3 duyệt. Không gộp remote với work_type hoặc
NULL→Unknown ngầm nếu source contract không quy định. UTC timestamps giữ hai basis.

## 8. Q07 và A04 gates

Q07 v2 ở TV2 pin, không phải file config có sẵn trong checkout TV1.3 candidate
tables: `q07_salary_separate_units`, `q07_population_summary`, `q07_quality_status`.
Source native `selected_salary.min/max`, canonical units, salary_source; eligible
USABLE bundle có thể min-only/max-only/med-only. n_min/n_max độc lập; Q1/P50/Q3/IQR
không lấy từ source med_salary; B_g gồm cả jobs không salary. Small-n adequate flags
không suppress quantiles.5 decisions và human signoff còn PENDING. E16.

Đọc [D06 readiness](d06_official_readiness.md) và
[contract approval gate](../src/d06_official_contract.py) trước bất kỳ Full command.
Cần workbook chính160 exact SHA, A04 business acceptance chấp nhận limits v0.2.2,
D06 schema approval và run authorization có binding input/package/output/approval
hashes. Expected workbook SHA và runtime/schema identities nằm trong evidence index.
Không dùng frozen labels hoặc workbook17 để giả có workbook160.

## 9. Update sau khi D06 Full được phép và đã chạy thật

1. Human cấp đủ3 records ngoài Git; operator kiểm identity/thẩm quyền và SHA.
2. Chạy preflight gần thời điểm thực thi, chốt memory/disk/concurrency và NEW run_id.
3. Chạy guarded Full trong lượt riêng, không override/reuse existing output.
4. Chỉ ghi SUCCEEDED khi seal bind manifests/inventory/validation và reconciliation.
5. Bổ sung D10/D11 bằng run ID, exact output path/schema/taxonomy/package/source
   identities,123849 input/output checks và counts ACCEPT/REVIEW/REJECT thực tế.
6. TV2 nhận bằng receiving validator/receipt, chạy official A05/analytics khi đủ gate;
   TV3 nhận table contracts, run/table SHA, denominators và filter support.
7. Update status/evidence index bằng evidence mới; giữ Phase 1 và D09 historical
   blockers như mốc thời gian. Không sửa audit cũ để biến PENDING thành APPROVED.

## 10. Checklist delivery

- [x] Source/release commits, schema/grain và available metrics có evidence.
- [x] ZIP local có size/SHA/member inventory; không tự claim uploaded.
- [x] Không Parquet/raw/private workbook trong thay đổi docs.
- [x] Giữ scope staging/benchmark/local và blockers rõ ràng.
- [ ] Nhóm review nội dung D10/D11 và thống nhất người ký gate.
- [ ] Người giữ dữ liệu cấp kênh delivery được phép; người nhận kiểm hash/acknowledge.
- [ ] Kiểm reproduction trên máy người nhận, giữ log và runtime identities riêng.
- [ ] Cấp approvals, chạy/validate D06 Full trong lượt được phép.
- [ ] TV2/TV3 nghiệm thu official analytics/contract/dashboard và final submission.

Checklist đã tick chỉ mô tả nội dung available evidence, không phải chữ ký nhóm.
Không tạo ZIP nộp bài mới, external upload, screenshots hoặc video trong Phase 1.

**D11 AVAILABLE HANDOFF DOCS: PASS (Phase 1, chờ nhóm review).**
**D10–D11 FINAL INTEGRATION: PENDING D06 FULL AND TEAM ACCEPTANCE.**
**D06 FULL: NOT EXECUTED.**
