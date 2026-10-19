# D07 — All-jobs salary normalization staging

Ngày: 19/10/2026, Asia/Bangkok. Phạm vi **ALL-JOBS NORMALIZATION STAGING**, không
phải OFFICIAL IT SALARY ANALYSIS, không phải D06 Full Classification.

Baseline D05 `457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b`; branch D07 tạo từ
D06 Official Runner `5fda1789b84494a856743c087d10fc511d013d93`.
Không sửa D01–D06, raw/canonical, taxonomy hoặc manual labels; không commit/push.

## A. Input / output / reproducibility

Input: `data/processed/canonical/jobs`, D05 `d05-v1`,50 columns.
Pipeline: `src/normalize_salary.py`; policy: `config/d07_salary_policy_v1.json`.
Output versioned: `data/processed/d07/staging/<run_id>/salaries.parquet`.
Audit: `data/audit/d07/<run_id>/`.

Chỉ cho phép branch D07 có D06 Official Runner ancestor; mọi file tracked tại
baseline được bảo vệ. Input/output riêng, không overwrite hoặc append. Existing
run/audit bị từ chối; linked/junction output bị chặn. Run lỗi giữ partial evidence,
rerun dùng NEW run_id. Không gọi hoặc import classifier TV2/D06 trong pipeline.

Lệnh chạy thật (Java21 chỉ process này, không đổi cấu hình hệ thống):

```powershell
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -B src/normalize_salary.py --run-id d07_20261019_01 --master "local[4]" --partitions 4 --windows-fs-jar tmp/d04-localfs/d04-localfs-adapter.jar
```

## B. Actual source and output schema

Đã đọc committed `data/audit/d05_canonical_schema.json` và inspect bằng Spark.
Runner kiểm toàn schema D05 thực tế khớp schema này trước ghi output.

| Source | Actual fields | Types |
| --- | --- | --- |
| postings, top-level | min_salary, med_salary, max_salary | decimal(20,4), nullable |
| postings, top-level | currency, pay_period, compensation_type | string, nullable |
| postings, top-level | normalized_salary | decimal(20,4), nullable; giữ raw, KHÔNG dùng fallback |
| salaries | salary_record.salary_id | bigint, nullable |
| salaries | salary_record.min_salary, med_salary, max_salary | decimal(20,4), nullable |
| salaries | salary_record.currency, pay_period, compensation_type | string, nullable |
| provenance | job_id; source_text_file; canonical_schema_version | bigint; string; string |

D07 giữ `raw_postings` struct gồm6 source fields; `raw_salary_record` giữ cả7 fields
và null struct; `raw_postings_normalized_salary` lưu riêng. Source raw ở đây là
**giá trị canonical D05 đã typed**, không tuyên bố khôi phục chuỗi lexical raw CSV.

Output thêm salary_source, selected_salary (whole source), source/canonical currency,
pay_period/compensation_type, source presence/conflict flags, normalization_status,
reason_codes, conversion_factor decimal(10,0), normalized_currency/unit,
normalized_min/med/max_salary decimal(38,4), policy version/SHA, population_scope.
Output thực tế **28 top-level fields**. Full machine-readable schema:
`data/audit/d07/d07_20261019_01/output_schema.json`.

## C. Actual salary coverage

Mẫu số là **123849 canonical jobs**, không phải IT jobs. Discovery Spark thực tế:

| Measure | Postings | salary_record |
| --- | ---: | ---: |
| Jobs có salary amounts | 36073 | 36073 |
| min_salary non-null | 29793 | 29793 |
| med_salary non-null | 6280 | 6280 |
| max_salary non-null | 29793 | 29793 |
| currency/period/compensation non-null | 36073 mỗi field | 36073 mỗi field |

salary_record struct có ở36073 jobs. Hai nguồn không độc lập: actual salary tuple
khớp toàn bộ trên dữ liệu đã inspect, conflict0. Không diễn giải là hai phép đo lương.
Upstream normalized_salary có36073 values (min0, max535600000); không biết đủ policy
để tái sử dụng như output D07, nên chỉ bảo toàn provenance.

## D. Currency / pay-period distribution

Hai nguồn có cùng phân phối. Mẫu số123849; NULL không được biến thành currency/unit:

| Currency | Jobs | Pay period | Jobs |
| --- | ---: | --- | ---: |
| USD | 36058 | YEARLY | 20628 |
| EUR | 6 | HOURLY | 14741 |
| CAD | 3 | MONTHLY | 518 |
| AUD | 2 | WEEKLY | 177 |
| GBP | 2 | BIWEEKLY | 9 |
| BBD | 2 | NULL | 87776 |
| NULL | 87776 | | |

compensation_type: BASE_SALARY36073, NULL87776. Đây là source coverage, chưa trừ
invalid. Không cộng/so sánh monetary values giữa currencies khác nhau.

## E. Normalization policy d07-salary-v1

- Không impute, không missing→0, không min/max average thành median/point estimate.
- Nếu chỉ một nguồn có amount: chọn trọn nguồn đó, không lấy metadata từ nguồn kia.
  Hai nguồn có amounts chỉ chọn BOTH_AGREE khi amounts và metadata chuẩn hóa khớp;
  nếu khác/null-vs-present thì CONFLICT, AMBIGUOUS, không chọn MAX/AVERAGE/coalesce.
- Currency/period/compensation chỉ upper/trim để match; raw strings không đổi.
- Currency whitelist: USD, EUR, CAD, AUD, GBP, BBD. Không FX/live rates, không mặc
  định USD. Currency ngoài policy bị EXCLUDED; thiếu currency là AMBIGUOUS.
- Chỉ BASE_SALARY. Loại compensation khác: EXCLUDED; thiếu type: AMBIGUOUS.
- Any observed amount<=0 là INVALID; kiểm cả min<=med, med<=max, min<=max khi cặp
  tương ứng tồn tại. Không ép đủ ba amounts; missing endpoints vẫn NULL.

| Recognized period | Annual factor | Assumption |
| --- | ---: | --- |
| YEARLY | 1 | Giá trị đã theo năm |
| MONTHLY | 12 | 12 tháng/năm |
| WEEKLY | 52 | 52 tuần/năm |
| BIWEEKLY | 26 | 52 tuần /2 tuần mỗi kỳ; không phải semimonthly |
| HOURLY | 2080 | 40 giờ/tuần ×52 tuần/năm |

Assumptions cấu hình/validate trong JSON, policy exact bytes SHA lưu mỗi row và
manifest. Unknown/missing period không annualize. DAILY/ONCE không tự suy luận.
Annual equivalent không đảm bảo actual annual earnings, paid hours, overtime,
unpaid leave, part-time hoặc bonus; raw source/unit vẫn có để phân tích native.

Input decimal(20,4) ×integer factor dưới8930 → decimal multiplication exact,
cast decimal(38,4), không float/round tiền. ANSI=true, overflow làm run fail.
Full validation chặn converted non-null source thành NULL.

## F. Missing / ambiguous / excluded handling

5 trạng thái phân biệt: MISSING, USABLE, INVALID, AMBIGUOUS, EXCLUDED.
reason_codes là ordered array có thể gồm nhiều lý do; thống kê reasons có overlap.
Priority: không amount→MISSING; source conflict→AMBIGUOUS; numeric/order error→INVALID;
unsupported currency/compensation→EXCLUDED; metadata thiếu/unknown period→AMBIGUOUS;
còn lại→USABLE. Non-USABLE có toàn bộ normalized amounts/unit/currency/factor NULL.
USABLE là hợp lệ **cơ học theo policy**, không là nhãn dữ liệu đã được nghiệm thu.

## G. Invalid values / plausibility limitations

Source discovery ranges cả hai nguồn: min_salary1..85000000; med_salary0..750000;
max_salary1..120000000 (native units/currencies, không so sánh trực tiếp các extrema
như một salary population). Giá trị0 giữ raw và INVALID, không missing.

Không có business threshold để tự loại high salary/outliers. Positive ordered
values vẫn có thể sai source/unit hoặc bất hợp lý về nghiệp vụ. Trước salary charts,
TV2/TV1 phải chốt outlier/robust aggregation policy theo currency và native period,
không tự gọi mọi USABLE là verified compensation. Statistics thực ở validation.

## H. Row-count / write-read validation

Runner preflight exact D05 schema/version,123849 rows/unique,0null/duplicates;
content inventory SHA trước/sau. Mọi jobs, kể cả missing salary, giữ trong output.
Parquet errorifexists. Readback kiểm typed schema, key sets, unique/null, recompute
full output bằng Spark và exceptAll hai chiều trên **mọi field**: raw structs,
NULLs, decimals, selection, policy, reasons, provenance. Kiểm status reconciliation,
conversion null/overflow, no FX, no invalid-period annualization, bounds.
Không collect123849 records về driver; chỉ distributed aggregate tables về driver.

## I. Runtime / manifest / evidence

Mỗi run có immutable run_manifest.json (intent RUNNING), validation_summary.json,
output_inventory.json, completion.json; audit có manifest/profile/schema/validation/
completion. Completion SUCCEEDED ghi cuối với hashes và runtime; _SUCCESS đơn độc
không phải D07 nghiệm thu. failure.json nếu caught error; OS kill/partial completion
phải coi incomplete. Không dùng directory rename như một atomic transaction.

Run thật `d07_20261019_01` **SUCCEEDED**, completion seal và file hashes đã kiểm
lại độc lập. Python3.11.0/PySpark4.2.0/Java21.0.12.1, local[4],4 partitions.
Execution22.349s (từ sau Spark session startup), Parquet write3.444s; đây là đo
thực tế D07, không suy diễn từ D06. Output4 Parquet files,2846357 bytes.

| Validation | Actual result |
| --- | ---: |
| Input rows / unique | 123849 /123849 |
| Output rows / unique | 123849 /123849 |
| NULL keys / duplicate keys | 0 /0 |
| MISSING | 87776 |
| USABLE | 36059 |
| INVALID | 14 |
| AMBIGUOUS / EXCLUDED | 0 /0 |
| Source conflicts / invalid ordering | 0 /0 |
| Overflow / invalid-period annualized / FX | 0 /0 /0 |
| All-field Parquet roundtrip | PASS |

14 INVALID đều có med_salary=0.0000, kiểm lại bằng batch read Parquet độc lập;
raw0 được giữ và normalized values NULL. Salary amount coverage36073/123849
=29.1266%; USABLE36059/123849=29.1153%. Không dùng mẫu số36059 để nói coverage100%.
Reason counts: NO_SALARY_AMOUNT87776, NONPOSITIVE_SALARY14; không có reason khác.
Hai nguồn BOTH_AGREE36073, NONE87776; không có source ưu tiên âm thầm.

Input fingerprint không đổi:
`729db5102bda622eef2f6d3cc0d88b851516ad01f6050f3d0f75debb99e17270`.
Output fingerprint:
`c43c79ea9113773ae6c5d66b64dc884775efd344888971ecf882c96803318bbd`.
Policy exact SHA:
`3c0e0a9b2c59bddff828d9d423d6659e19a3ceafae480c1cd3e50aa54221382b`.

Evidence files:

- `data/audit/d07/d07_20261019_01/run_manifest.json`
- `data/audit/d07/d07_20261019_01/source_profile.json`
- `data/audit/d07/d07_20261019_01/validation_summary.json`
- `data/audit/d07/d07_20261019_01/output_schema.json`
- `data/audit/d07/d07_20261019_01/completion.json`
- `data/audit/d07/tests_summary.json`
- `data/audit/d07/handoff_summary.json`

Manifest status RUNNING là immutable start intent, trạng thái kết thúc nằm ở
completion SUCCEEDED; phải kiểm hashes/validation, không chỉ đọc start manifest.
Không claim completion là business acceptance. D05/raw131 protected files không đổi;
D06 production output không tồn tại. Không commit/push/merge hoặc stage dữ liệu.

## J. Tests

`src/test_d07_salary.py`: fixtures synthetic, live Spark. Bao phủ missing/NULL,
5 periods thật, unknown periods (DAILY/ONCE synthetic), missing/unsupported currency,
6 currencies không FX, negative/zero,3 bounds pairs, conflict amount/currency/period/
compensation, whole-source selection, decimal max-domain/fraction precision,
determinism/repartition, unique/null/schema guard, Parquet roundtrip/tamper,
existing output/path traversal, policy validation và future3-way classification join.
Classification fixture chỉ contract3 rows, không classifier/approval/D06 FULL.

Lần test đầu có18 PASS và1 ERROR ở validation: Spark4.2 không nhận tuple truyền
vào `Column.isin` như danh sách literals. Đã đổi sang splat arguments, không sửa
data/policy để ép PASS; giữ evidence cũ `tmp/d07_tests/suite_ed49400069/summary.json`.
Phải dùng kết quả rerun sau sửa để kết luận, không đánh lần lỗi là PASS.

Final rerun: **19/19 PASS**,0failures/errors/skips,170.894s. Evidence
`tmp/d07_tests/suite_b1dcb07531/summary.json`, bản tóm tắt ở
`data/audit/d07/tests_summary.json`. Code SHA thực thi khớp tests và run manifest.

## K. Limitations

- Không phục hồi precision đã mất trước D05; bảo toàn đúng4 decimal places canonical.
- Whitelist currency không phải FX policy; thêm currency cần policy version/review.
- Annual factors là giả định chung, không suy từ giờ làm việc từng job.
- Source duplicates không bổ sung accuracy; conflict future phải đối soát riêng.
- Chưa xác minh remote cluster; runtime giới hạn local[1/2/4]. Không có resume.
- Không phân tích salary IT hoặc công bố business acceptance trong lượt này.

## L. D06 dependency / downstream integration

D06 FULL **NOT EXECUTED**. D07 staging giữ ALL jobs, không dùng Pilot làm population.
Hàm `join_classification` chuẩn bị key-set/unique/decision/null-preserving join1:1;
mặc định từ chối nếu chưa acknowledge human ACCEPT policy. Đây là DataFrame
contract helper, **không tự xác minh seal/thẩm quyền**. Caller phải kiểm Official
completion scope FULL, package/taxonomy version/SHA và schema trước truyền frame;
boolean không thay authorization. Không gọi helper với data thật trong lượt này.

Giữ ACCEPT/REVIEW/REJECT riêng; chỉ ACCEPT theo policy đã duyệt mới vào official IT
salary population. Chỉ USABLE mới có annual monetary values, nhóm riêng từng currency;
mẫu số salary coverage phải là IT ACCEPT population, không bỏ missing rồi gọi
coverage100%. REVIEW không phải outside IT; không nhân dòng qua job relationships.

## M. Required downstream output for TV2

TV2 nhận manifest, policy/schema/hash, salary frame1job/row, all raw/selected/source/
status/reasons/annual equivalent fields và distribution/validation report. Không
commit Parquet/private datasets. Sau D06 được chạy/duyệt, cung cấp classification
FULL path+seal và exact version/hash cùng key-set audit. Analytics cần công khai
scope/currency/unit, missing/invalid/ambiguous exclusions, annualization/outlier
policy và sample denominators; không gọi staging là official IT results.

## Verdict / next action

D07 IMPLEMENTATION **PASS**; D07 ALL-JOBS STAGING **PASS**.
D07 OFFICIAL IT SALARY **PENDING D06 FULL**; D06 FULL **NOT EXECUTED**.
Đây là technical staging handoff, không tự nghiệm thu chính thức.

Review code/policy assumptions và outlier treatment; giữ staging/manifest để phục
vụ báo cáo all-jobs. Chỉ sau khi A04/schema/run authorization được human chốt và
D06 Official FULL chạy/validate/được duyệt mới JOIN official IT salary population.

## GitHub release review — separate from staging execution

Các phát biểu "không commit/push", baseline HEAD và số commits0 trong evidence
phía trên mô tả lượt implementation/staging ban đầu. Lượt release sau đó được
người dùng cho phép review, rerun tests an toàn, commit/push đúng11 files D07;
không chạy lại staging, không D06 Full và không business acceptance.

Review read-only đã kiểm lại123849 unique keys,28-field schema,14 INVALID đều raw
med_salary=0.0000/normalized NULL, policy/source/input/output fingerprints và final
completion seal.131 protected baseline files không đổi. Release test evidence được
ghi riêng trong `tests_summary.json` phần release_verification; không thay kết quả
staging lịch sử hoặc ghi đè Parquet. Compare base là `feat/tv1-d06-official-runner`.

Release rerun **19/19 PASS**,0failures/errors/skips,183.554s; evidence mới
`tmp/d07_tests/release_bd46bd40d1/summary.json`. Pipeline/test SHA khớp bản đã chạy
staging. Không có code hoặc policy change trong lượt release.

Reproduction trên Windows: policy và source identity là SHA exact bytes, bao gồm
line endings. Repo hiện có core.autocrlf=true và chưa có tracked eol attributes cho
D07; checkout khác có thể chuyển LF thành CRLF và tạo SHA khác dù JSON semantics
không đổi. Khi tái lập exact run, dùng checkout giữ LF/exact Git blob bytes
(core.autocrlf=false cho clone/checkout đó), rồi kiểm policy/source SHA với manifest.
Không dùng hash của JSON parse/reserialize thay exact-byte policy hash. Lượt release
này không thay global Git config hoặc JAVA_HOME và không đổi policy bytes.
