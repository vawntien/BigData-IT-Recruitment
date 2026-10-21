# D10–D11 — Evidence index, identities và nguồn trích dẫn

Ngày21/10/2026, Asia/Bangkok. **Phase 1, available evidence only**.
Điểm vào: [D10](d10_technical_report.md), [D11](d11_handoff_reproducibility.md),
[status matrix](d10_d11_status_matrix.md). Không có official IT metrics trong index.

## Quy tắc đọc nguồn

Paths Markdown tương đối từ `docs/`; root thực tế là
`D:/Learning/Bigdata/BigData-IT-Recruitment`. Files dưới tmp/processed hoặc package
ngoài repo chỉ có local, không kỳ vọng GitHub resolve. Git blob URLs dùng pinned
commit cho TV2 source không hiện diện trong branch TV1. Không dùng branch tip mutable
thay release hash. SHA256 khác Git commit SHA; schema canonical-JSON SHA khác exact
file SHA. Không parse/reserialize policy để xác minh exact-byte identity.

## Evidence matrix

| ID / Claim hoặc result | Source file | Version / commit | Run ID | Validation evidence | Status | Known limitation |
| --- | --- | --- | --- | --- | --- | --- |
| E01 Dataset/source11 CSV | [manifest](data_manifest.md),[README](../README.md) | D09 docs baseline b668c763 | Ngày nhận04/10/2026 | [dictionary](data_dictionary.md) | DOCUMENTED | Dataset license/source theo manifest; không fetch lại website |
| E02 Raw→clean/rejected | [D04 report](d04_cleaning_report.md) | D09 inherited evidence | D04 historical | [D04 validation](../data/audit/d04_validation.csv) | TECHNICAL PASS | Không tái chạy D04 trong lượt docs |
| E03 D05 canonical123849 unique/50 fields | [D05 report](d05_official_report.md),[builder](../src/build_canonical_jobs.py) | 457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b | UTC2026-10-15T12:33:59.660114+00:00 | [72 checks](../data/audit/d05_official_validation.csv) | AVAILABLE/RELEASED | Implementation/release không tự nghiệm thu nhóm |
| E04 Schema/source/JOIN D05 | [schema](../data/audit/d05_canonical_schema.json),[manifest](../data/audit/d05_official_run_manifest.json) | d05-v1 /457f90ae | Như E03 | [JOIN](../data/audit/d05_official_join_reconciliation.csv),[referential](../data/audit/d05_official_referential_coverage.csv),[tests](../data/audit/d05_official_regression_tests.csv) | PASS | Nullable readback khác runtime non-null key; orphan không bị xóa |
| E05 Python/Spark176/176 parity | [parity report](d06_parity_report.md) | 1c365741f0e3dcad9064473ae2c0c6b9f507ae25 | 20261018T110206Z_637eede4 | [parity summary](../data/audit/d06/validation_summary.json) | TECHNICAL PASS | Development/reference set, không independent Full evaluation |
| E06 Pilot không official population | [Pilot report](d06_pilot_report.md) | 0ca38ab90a05acfac1f191da45dba7511ab094be | pilot_20261018_03 | [Pilot summary](../data/audit/d06/pilot_validation_summary.json) | PILOT PASS | Không suy IT count toàn tập hoặc dùng Pilot làm Full |
| E07 Schema27/Official runner/preflight | [readiness](d06_official_readiness.md),[contract](../src/d06_official_contract.py),[runner](../src/d06_official_runner.py),[schema](../data/audit/d06/pilot_spark_schema.json) | d06-official-v1 /5fda1789b84494a856743c087d10fc511d013d93 | readiness_20261019;report readiness_20261019_01.json | [readiness summary](../data/audit/d06/official_readiness_summary.json) | READY TECHNICALLY | Full NOT EXECUTED; approvals pending; preflight classified0 |
| E08 Salary selection/policy | [policy](../config/d07_salary_policy_v1.json),[source](../src/normalize_salary.py) | d07-salary-v1 /479d3d83ff3194a5556ce29884c92478c90a969c | d07_20261019_01 | [manifest](../data/audit/d07/d07_20261019_01/run_manifest.json) | RELEASED | USABLE chỉ mechanical eligibility; không FX |
| E09 D07 metrics/schema/seal | [report](d07_salary_report.md),[schema](../data/audit/d07/d07_20261019_01/output_schema.json) | 479d3d83 | d07_20261019_01 | [validation](../data/audit/d07/d07_20261019_01/validation_summary.json),[completion](../data/audit/d07/d07_20261019_01/completion.json),[tests](../data/audit/d07/tests_summary.json) | STAGING PASS | ALL JOBS, không IT salary hoặc business acceptance |
| E10 D08 measured45/warmup15/W1–W5 | [raw](../data/audit/d08/d08_20261020_01/benchmark_results.csv),[summary](../data/audit/d08/d08_20261020_01/benchmark_summary.csv) | ff721bcf7988841a2b80e3f263f3ef8a69188278 | d08_20261020_01 | [validation](../data/audit/d08/d08_20261020_01/benchmark_validation.json) | AVAILABLE BENCHMARK PASS | Local,3 measured repeats; startup riêng |
| E11 D08 config/events/tests | [manifest](../data/audit/d08/d08_20261020_01/benchmark_manifest.json),[report](d08_benchmark_report.md) | ff721bcf | d08_20261020_01 | [tests11/11](../data/audit/d08/d08_20261020_01/tests_summary.json),[receipt](../data/audit/d08/d08_20261020_01/post_run_verification.json) | PASS |585 task attempts không phải system CPU/RAM telemetry |
| E12 D08 figures có sẵn | [runtime SVG](../data/audit/d08/d08_20261020_01/runtime_median.svg),[speedup SVG](../data/audit/d08/d08_20261020_01/speedup.svg) | ff721bcf | d08_20261020_01 | Receipt E11 bind exact sizes/SHA | PASS | Không error bars/cluster/full-pipeline claim |
| E13 D09 22P/0F/9B/2NA=33 | [D09 report](d09_available_validation_report.md),[results JSON](../data/audit/d09/d09_20261020_01/validation_results.json),[CSV](../data/audit/d09/d09_20261020_01/validation_results.csv) | b668c763a3d7bf10a604a11b61a9e7b2f9e9edf5 | d09_20261020_01 | [summary](../data/audit/d09/d09_20261020_01/validation_summary.json) | AVAILABLE PASS / FULL BLOCKED | Không dùng PASS ratio che9 blockers |
| E14 D09 tests7 riêng/integrity | [tests](../data/audit/d09/d09_20261020_01/validator_tests.json),[validator](../src/d09_validate_available.py) | b668c763 | d09_20261020_01 | [inventory](../data/audit/d09/d09_20261020_01/evidence_inventory.json),[final receipt](../data/audit/d09/d09_20261020_01/final_verification.json),[refs](../data/audit/d09/d09_20261020_01/release_refs.json) | PASS | Receipt là historical pre-release; D09 runner HEAD guard cần isolated reproduction |
| E15 A04 limits/workbook gate | [TV2 A04 handoff](https://github.com/vawntien/BigData-IT-Recruitment/blob/e437dcc11dda61f847673b9cc8c5801886c1996d/docs/a04_handoff_tv1.md),[final report](https://github.com/vawntien/BigData-IT-Recruitment/blob/e437dcc11dda61f847673b9cc8c5801886c1996d/docs/a04_final_report.md) | TV2 e437dcc11dda61f847673b9cc8c5801886c1996d | Candidate20261014 | Frozen references + E05/E07;workbook status ở readiness | BUSINESS PENDING |5FN/33REVIEW/3group/9subgroup/4CHUA_RO; main workbook MISSING tại TV1 audit |
| E16 Q07 v2 candidate | [contract](https://github.com/vawntien/BigData-IT-Recruitment/blob/8323b5b9f4025ec4909ead912aafbef6c5825e6c/config/q07_salary_contract_v2.json),[implementation](https://github.com/vawntien/BigData-IT-Recruitment/blob/8323b5b9f4025ec4909ead912aafbef6c5825e6c/src/q07_salary.py) | TV2 8323b5b9f4025ec4909ead912aafbef6c5825e6c | q07_contract_v2 historical | [TV2 audit](https://github.com/vawntien/BigData-IT-Recruitment/blob/8323b5b9f4025ec4909ead912aafbef6c5825e6c/data/audit/tv2_q07_contract_v2_20261020.json) | IMPLEMENTED CANDIDATE/PENDING | Five decisions,precision/small-n,source hash caveat below |
| E17 TV2/TV3 receiving contract | [TV2 handoff](https://github.com/vawntien/BigData-IT-Recruitment/blob/8323b5b9f4025ec4909ead912aafbef6c5825e6c/docs/tv2_current_handoff.md),[receiving checklist](https://github.com/vawntien/BigData-IT-Recruitment/blob/8323b5b9f4025ec4909ead912aafbef6c5825e6c/docs/d06_full_receiving_checklist_tv2.md),[TV3 local draft](dashboard/dashboard_data_contract_draft.md) | TV2 pin above /TV3 draft inherited at b668c763 | Không official IT run | [dashboard handoff](dashboard/dashboard_handoff.md) | PENDING FULL/TEAM ACCEPTANCE | Draft physical tables/filters chưa final; không sửa TV2/TV3 files |
| E18 ZIP handoff inventory | `D:/Learning/Bigdata/TV1_Handoff_D05_D07/HANDOFF_MANIFEST.json` và SHA256SUMS.csv | Package source D07 479d3d83 | created2026-10-20T00:06:10.313013+07:00 | D09 HANDOFF_ZIP_MANIFEST_CHECKSUMS PASS | LOCAL AVAILABLE |35 payload/36 checksum rows/37 members; không uploaded claim |
| E19 Package whole ZIP identity | `D:/Learning/Bigdata/TV1_Handoff_D05_D07.zip` và `.zip.sha256` | D07 handoff | Như E18 | `tmp/handoff_build_20261020/result.json`, D09 receipt và Phase1 docs read-only SHA check | PASS |400169176 bytes;private data distribution restricted |
| E20 Legacy drafts để ghép báo cáo | [methodology](report/data_methodology_draft.md),[outline](final/report_integration_outline.md),[metric registry](final/final_metrics_registry.md),[old status](handoff/project_status.md) | Snapshot inherited at D09 | Historical drafts | Đối chiếu E03–E17 | REUSED AS OUTLINE | Nhiều TODO/status cũ; không dùng thay actual release evidence |

## Exact identity register

| Identity | SHA256 / value |
| --- | --- |
| D05 fingerprint | `729db5102bda622eef2f6d3cc0d88b851516ad01f6050f3d0f75debb99e17270` |
| D07 fingerprint | `c43c79ea9113773ae6c5d66b64dc884775efd344888971ecf882c96803318bbd` |
| D07 exact policy bytes | `3c0e0a9b2c59bddff828d9d423d6659e19a3ceafae480c1cd3e50aa54221382b` |
| D06 taxonomy v0.2.2 exact config | `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874` |
| D06 runtime package | `09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59` |
| D06 schema canonical JSON,version d06-official-v1 | `44ee9bcc29f5ace90161b6bea67d6543ced30925944761f56e28c7df76a67a68` |
| Main workbook160 EXPECTED,not locally verified | `bbe53db071a75478705c8be3b692356c896018bd20dfac40aebc489d97d305a2` |
| Handoff ZIP | `e3269658c1e3ca0031efd6d4249f8389c3d3c41615cb7a18987f37c5635ebc43` |
| D08 runtime SVG,4790 bytes | `c8f54f08214d2ef4e07b8534fa9cf9c83665ffa72e724927bb8ee669f3aa07da` |
| D08 speedup SVG,4800 bytes | `772eb09abac8fdd712bdb016251b7938cebf89cf59f8a01a05b8e03f5c47ce1e` |

Không có SHA của APPROVED records vì chưa nhận records hợp lệ. Không điền placeholder
vào bảng như thể approval đã tồn tại. Expected workbook hash không phải proof file có.

## Source gaps và lịch sử không được diễn giải sai

- Một số reports ghi “không commit/push”, manifest HEAD parent, receipt staged0:
  đó là trạng thái lúc chạy trước release. Release inventory D11 ghi commits sau đó.
- D05 report nói D08/D09 chưa chạy tại thời điểm D05: historical, không phủ nhận
  evidence D08/D09 sau này. Giữ report cũ, không sửa để làm lịch sử đồng nhất giả.
- TV2 Q07 audit8 implementation hashes:3 file Q07 implementation/test/contract khớp
  exact Git blobs;5 file tích hợp khác khớp bản CRLF nhưng pinned blobs LF tại review
  TV1 trước đó. Cần TV2 follow-up về byte provenance; không đổi audit cũ hoặc gọi
 18 tests đã ghi là mới được rerun trên mọi Git blob. Chi tiết file ở status matrix.
- A04 gate audit nonclassifying ngày20/10 đã in ra chat (4/4 probes,classified0),
  không tạo report file mới. Nguồn file có thể đưa vào package là E07 readiness
  ngày19/10 và D09 ngày20/10; không invent một gate-audit JSON trên disk.
- Lượt docs chỉ hash/inventory/package verification, không rerun D05–D09 hoặc
  benchmarks. Các số runtime/tests lấy historical evidence đúng scope tương ứng.

## Attribution và nguồn ngoài

[Dataset URL theo manifest](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings)
và [license URL được manifest ghi](https://creativecommons.org/licenses/by-sa/4.0/)
là attribution của dự án; không claim đã kiểm bản website hiện tại trong Phase1.
Mô tả implementation/Spark experiment dựa trên code và artifacts pin của repo,
không gán performance claims cho tài liệu nhà cung cấp. Không tự tạo citation cho
papers, cluster benchmark hoặc external delivery không có trong evidence.
