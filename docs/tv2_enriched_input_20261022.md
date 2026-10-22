# TV2 enriched D05 × D06 ACCEPT — 22/10/2026

**Cập nhật sau Q01 official:** lỗi mã hóa tên người xác nhận trong metadata đã được sửa theo xác nhận gốc, giữ lịch sử và đóng lại seal; digest Parquet không đổi. Các hash receipt/manifest trong báo cáo này là snapshot trước correction. Hash metadata hiện tại và Q01 VALIDATED được ghi tại [báo cáo Q01 official](q01_official_validation_20261022.md).

**Enriched receiving: PASS. Q01 readiness: READY ở mức input/schema/technical receipt.** Chưa chạy A05 hoặc analyzer A06–A08, chưa tạo Q01–Q08 output, không ghi BUSINESS ACCEPTED hoặc phê duyệt nghiệp vụ cho bất kỳ câu nào.

Run riêng TV2: `tv2_enriched_d06_accept_20261022_01`. Branch `feat/tv2-analysis`, commit `3c7c6285a59af8ae9eebfdc2d3667f3fcff92180`. Materialization 14:19:15–14:20:56 ngày 22/10/2026 +07; Python exit **0**. Không sửa nguồn D05/D06, schema/validator/pipeline hiện có; không commit/push/merge.

## 1. Artifact thật

Root tuyệt đối:

`C:/Users/dongv/BigData-IT-Recruitment/data/processed/tv2/enriched/tv2_enriched_d06_accept_20261022_01/`

`git check-ignore` xác nhận output dưới rule `data/processed/*`.

| Artifact (tương đối với root) | Nội dung |
|---|---|
| `jobs.parquet/` | Enriched input thật: **5.206 jobs**, 2 part, 41.908.458 bytes payload Parquet; có `_SUCCESS` |
| `schema.json` | Physical read-back schema: **39 fields** |
| `writer_schema.json` | Schema trước ghi; đối chiếu physical read-back PASS |
| `manifest.json` | SUCCESS, run/branch/commit/count/hash/runtime/readiness, không business accepted |
| `output_inventory.json` | Từng file relative path/size/SHA và digest cả directory |
| `lineage.json` | D05/D06 references, producer run/seal/package/approval hashes, mapping JOIN và protected-source hashes |
| `validation.json` | **47/47 kiểm tra PASS**, trước ghi và sau read-back |
| `source_binding.json` | Nguồn từng description/title và raw-text binding của A05 |
| `input_receipt.json` | **TECHNICAL_RECEIPT_CONFIRMED**, exact input/canonical/config/classifier/validation hashes |
| `analysis_contract.json` | OFFICIAL contract cho analyzer; D06 confirmation gắn đúng enriched digest |
| `readiness.json` | Q01 READY; các dependency riêng Q05/Q06/Q07 chưa xác nhận |
| `technical_receipt_confirmation.json` | Ghi nhận xác nhận trực tiếp của người dùng, chỉ scope technical receipt |
| `completion.json` | SUCCEEDED, đóng hash manifest/validation/inventory và receipt confirmation |
| `receipt_history/pending_20261022/` | Giữ nguyên các metadata PENDING trước khi người dùng xác nhận; không thay dữ liệu |

Hashes sau xác nhận receipt:

| Đối tượng | SHA-256 |
|---|---|
| **Parquet directory — TV2 artifact_digest** | `17ae5383e848f7323b99800bd3d79a72e84e2bca62844f66dd00aaa06e80a9b2` |
| Physical `schema.json` | `e4e6c2bf979d7a5e3f5700079a523ecdfdd98947d912d012406b3420ef7bab0d` |
| Final `manifest.json` | `546e28f330dcdd31c4a89b2c0dc9f6b21415b1fa5acab159e5c496f425c430da` |
| Final `input_receipt.json` | `5032f982db0c5bbd52ca573f078b7424b09c862f766bc96764bfa78a8128adc2` |

`artifact_digest` đúng implementation analyzer: recursive files sort theo path, gồm marker/CRC nếu có, mỗi mục `[relative_path, bytes, sha256]`, serialize JSON compact UTF-8 rồi SHA-256. Inventory output thực tế có `_SUCCESS` và hai part, không có CRC. Không nhầm digest này với producer fingerprint D05/D06 hoặc với hash file manifest.

## 2. Nguồn, JOIN và xử lý tên trùng

Đã đọc lại receiving report, README/contract/manifest các gói đã giải nén, output schema analyzer và runner/contract A05 v0.1.2. Không tìm thấy `TV1_TV2_TV3_JOIN_CONTRACT.md` riêng trong local handoff/tmp; dùng phần Population and join contract của README D06, cho phép JOIN 1:1 theo job_id sau xác minh unique/key-set/lineage.

- D05: `data/processed/canonical/jobs/`, đúng bốn part trong input inventory D06, fingerprint producer `729db5102bda622eef2f6d3cc0d88b851516ad01f6050f3d0f75debb99e17270`.
- D06: `data/handoff/tv1/receiving_20261022/d06/D06/predictions/`, Full run `official_20261021_a9dddfe4`, producer commit `5fda1789b84494a856743c087d10fc511d013d93`.
- D06 source output fingerprint `34e8370e56fd8d9eb3f931a5db029dc7d6244d31a67642c5bfdeeb5150fd50ec`; completion SHA `6c5a8d0b2bef63d5c0d3499901b4edbee845c2c0772329796f61a113d0f2de45`.
- Filter đúng `(it_decision = 'ACCEPT') AND (is_it = true)`, INNER JOIN D05 unique/non-NULL bigint job_id. Không explode evidence/job_functions, không impute/cast/sửa nhãn.
- Ba gói D06/approval/D07 được kiểm lại exact payload membership/size/hash trước materialization. D05 part hashes, D06 seal/approval binding, taxonomy và A05 release pins được kiểm lại. Sau ghi, hash của **60 protected files** (source/metadata/implementation) được kiểm không thay đổi.

Source priority cụ thể, không `SELECT *` cả hai phía:

| Trường | Nguồn và cách bảo toàn |
|---|---|
| Toàn bộ 27 trường D06, gồm job_id, decisions, group/subgroup, taxonomy, evidence/parser/diagnostics/digests | Giữ nguyên tên/type/value/null; so exceptAll hai chiều trước ghi và read-back với D06 ACCEPT |
| `description`, `title` | Giữ D06 nguyên bản, không ghi đè text gắn với classification evidence |
| `source_description`, `source_title` | Bổ sung nguyên bản parsed-source từ D05; hashes tính lại khớp D06 và D05 |
| `source_description_sha256`, `source_title_sha256` | Giữ D06; chứng minh equality với D05 trước/sau ghi |
| `d05_description`, `d05_title` | Alias nguyên giá trị D05.description/title, giữ cả khi khác D06 |
| experience/location/work type/remote/timestamps | Lấy D05 đúng tên/type, giữ NULL, so value/null hai chiều sau ghi |
| `job_functions` | Giữ nguyên array D05 cho lineage/adapter tương lai; **chưa bật route Q05** hoặc coi functional labels là technical skills |

39 fields = 27 D06 + 10 D05 additions + 2 aliases. Các additions thực tế: source_description, source_title, formatted_experience_level, location, formatted_work_type, work_type, remote_allowed, original_listed_time, listed_time, job_functions.

## 3. Validation và read-back

| Kiểm tra | Kết quả |
|---|---|
| D05/D06 nguồn | Mỗi nguồn rows=distinct job_id=123.849, NULL=0; Full key-set hai chiều trùng |
| Quyết định Full nguồn | ACCEPT/true=5.206; REJECT/false=58.953; REVIEW/NULL=59.690; không đổi REVIEW thành ACCEPT |
| Enriched trước ghi | **5.206 rows = 5.206 distinct**, NULL=0, duplicate=0 |
| Enriched sau đọc Parquet | **5.206 rows = 5.206 distinct**, NULL=0, duplicate=0 |
| Key-set với D06 ACCEPT | missing=0, extra=0, kiểm exceptAll hai chiều cả trước/sau ghi |
| Classification | Toàn bộ 27 fields D06 giữ nguyên, bao gồm nested; primary_group_code vẫn một string nullable/job, không tạo membership đa nhóm |
| Dimensions/source D05 | Mọi selected field/alias value và NULL giữ nguyên; không làm thay đổi decisions |
| Taxonomy | Đúng một cặp **0.2.2** / `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874`, snapshot local cùng hash |
| Source text/hash | SHA-256 UTF-8 source_description/source_title khớp D05 và D06 trên toàn selected population |
| Physical schema | Đúng tên/thứ tự/types và nested types sau read-back; reader có thể mở rộng nullability, không đổi scalar/struct/array types |
| Read-back content | exceptAll hai chiều tất cả **39 fields**, không chỉ count; PASS |
| Analyzer input validator | `validate_d06` PASS trước/sau ghi; không gọi `analyze_frames`/main |
| A05 input validator | `validate_frames` PASS trước/sau ghi; view description=source_description nguyên bản đúng D05, không gọi extractor |
| Output hash | Inventory và artifact_digest tính lại khớp; seal/manifest sidecar hashes PASS |
| Source preservation | Các source/contract/implementation protected không thay đổi trước/sau materialization; recheck lại khi ghi technical receipt |

Không tính lại prediction classifier, không đo accuracy Full, không chạy A05/A06–A08 production. NULL group vẫn được bảo toàn, không ép thành IT_OTHER/Unknown. A04 ACCEPT WITH CONDITIONS còn hiệu lực; phải công bố ACCEPT population và REVIEW 59.690/123.849 (~48,20%), không suy population accuracy từ development reference.

## 4. Technical receipt được xác nhận

Sau khi materialization và 47 kiểm tra PASS, người dùng xác nhận trực tiếp trong cuộc hội thoại:

- `approved_by = Đồng Viết Dũng (TV2)`.
- `approved_on = 2026-10-22T14:23:24+07:00`, thời điểm ghi nhận xác nhận thực tế theo UTC clock; không dùng ngày D06 run ID để backdate.
- Scope: **TECHNICAL RECEIPT của enriched input 5.206 jobs**, bound digest `17ae5383…e80a9b2`.
- Không BUSINESS ACCEPTED, không tạo approval Q01–Q08, không cho chạy production trong lượt này.

Trước ghi receipt đã đối chiếu lại artifact digest với manifest/completion và hash mọi sidecar, 47 validation checks PASS, protected source hashes không đổi. Sau ghi receipt tiếp tục kiểm digest, manifest hashes và thực thi read-only `verify_artifacts(receipt, purpose='a05')`: **PASS**. `receipt_errors(..., purpose='a05')=[]`.

Analyzer `preflight(analysis_contract.json)` thực tế:

```json
{"D06": true, "D05": false, "A05": false, "D07": false}
```

Ở đây dependency `D05=false` là **Q05 bridge/mapping confirmation** chưa có, không phải D05 canonical vắng mặt. Technical receipt không tự xác nhận route Q05. `purpose='analysis'` receipt hiện chỉ còn `Q05_CONTRACT_UNCONFIRMED`; Q01 dùng analysis_contract riêng nên không bị gate Q05 này chặn.

Classifier path receipt trỏ snapshot `tmp/tv2_a04_handoff_v0.2.2/staging/src/it_taxonomy.py`; SHA `841231033c546cc2bedf141386038104c0a0f1cf9f5a01b80535457c8b42312f`, khớp v0.2.2 implementation manifest local. Đây là reference code hash; upstream package identity `09e7ee9c1ee2126338a6f20accaf8d38a5bbc0d97a69c905e973745d90025d59` được giữ riêng trong lineage. Không đồng nhất file code hash với package hash.

## 5. Readiness Q01 và A05–A08

**Q01 READY cho lượt thực thi tiếp theo**, ở mức schema/integrity/receipt gate. Chưa có Q01 official output hay nghiệm thu kết quả.

Các type cần cho batch analyzer đều có thực: job_id bigint; description/group/decision/taxonomy string; is_it/remote_allowed boolean; experience/location/formatted_work_type/work_type string; original_listed_time/listed_time timestamp, session UTC. Không còn thiếu adapter input schema cho Q01–Q04/Q08.

CLI chưa có Q01-only: runner sẽ chạy **Q01–Q04 và Q08** cùng lượt. Nếu giữ optional dependencies như contract hiện tại:

| Câu/bước | Trạng thái dự kiến khi chạy lượt sau |
|---|---|
| Q01–Q04/Q08 | Đủ input + technical receipt, có thể chạy batch và validate từng query |
| Q05 | BLOCKED bridge/mapping route confirmation, dù job_functions gốc được giữ trong enriched |
| A05 official | Input validator + artifact/receipt verification PASS; chưa chạy extractor/official output; stable v0.1.2 pins không đổi |
| Q06 | BLOCKED A05 official bridge/status, không lấy source labels làm technical skills |
| Q07 | BLOCKED D07/Q07 business signoff/policy confirmation; technical salary staging không thay business acceptance |
| Overall analyzer | Có thể PARTIAL_SUCCESS/exit 2 khi Q01–Q04/Q08 SUCCESS nhưng Q05/Q06/Q07 BLOCKED; đây không tự động là Q01 thất bại |

Validation riêng Q01 ở lượt sau cần kiểm: query Q01 SUCCESS; đúng sáu cột physical; N=5.206 từ confirmed source; K=distinct jobs có trim(primary_group_code) khác NULL/blank; missing=N−K; tổng count=N, tổng known count=K; shares và zero-denominator policy đúng; NULL/IT_OTHER/literal Unknown không bị tự remap; schema/readback/CSV-Parquet/output hashes và taxonomy manifest khớp. Q01 aggregate không chứa job_id: population proof phải dựa đúng digest/input receipt và source key-set, không giả vờ đối soát job_id trực tiếp từ bảng category. Không yêu cầu Q05–Q07 SUCCESS để công nhận technical validation riêng Q01, nhưng cũng không nâng toàn pipeline thành SUCCESS/ACCEPTED.

### Lệnh chính xác cho lượt tiếp theo — chưa thực thi

Từ repository root, sau recheck tài nguyên; output dưới đây hiện chưa tồn tại:

```powershell
$env:JAVA_HOME = (Resolve-Path 'tmp/tv2_d05_receipt_457f90ae/runtime/jdk-21.0.12.1+1').Path
$env:PATH = "$env:JAVA_HOME/bin;$env:PATH"
$env:PYSPARK_PYTHON = (Resolve-Path '.venv/Scripts/python.exe').Path
$env:PYSPARK_DRIVER_PYTHON = $env:PYSPARK_PYTHON
$env:SPARK_LOCAL_IP = '127.0.0.1'
$env:PYSPARK_SUBMIT_ARGS = '--driver-memory 2g --conf spark.default.parallelism=2 --conf spark.sql.shuffle.partitions=4 --conf spark.ui.enabled=false pyspark-shell'
.\.venv\Scripts\python.exe -B src/a06_a08_spark_analysis.py `
  --contract data/processed/tv2/enriched/tv2_enriched_d06_accept_20261022_01/analysis_contract.json `
  --output data/analytics/tv2_q01_q04_q08_official_20261022_01 `
  --run-id tv2_q01_q04_q08_official_20261022_01
```

Đây là batch runner hiện có, không Q01-only. `get_spark_session` của CLI đặt master local[*]; các settings parallelism/shuffle trên giới hạn số partitions, không đổi helper thành local[2]. Không tự sửa helper/validator trong lượt này. Nếu đường dẫn output đã tồn tại ở thời điểm chạy, chọn run/output mới, không ghi đè. Không dùng full input mixed decisions hoặc đổi confirmation sang hash khác.

## 6. Tài nguyên và bằng chứng

Materializer thực chạy Spark **4.2.0**, Java **21.0.12.1**, Python **3.11.9**, local[2], driver heap2GiB, timezone UTC; dùng JDK/Windows filesystem adapter sẵn có trong project. Chạy với quyền runtime phù hợp, clean Python exit **0**, không có cleanup Access denied như wrapper sandbox trước đó. Warning winutils/native Hadoop vẫn có; adapter read/write/read-back thành công.

Trước Spark: available RAM ~**4,04GiB**, commit headroom ~**4,50GiB**, disk free ~**183,62GiB**. Cuối materialization khi Spark còn chạy: RAM available ~**1,75GiB**, commit headroom ~**1,86GiB**, disk free ~**183,36GiB**. Các số đo nằm trong validation JSON. Đủ cho lượt input materialization đã thực hiện; phải recheck trước analyzer/A05 và chạy tuần tự, không coi đây là bảo đảm mọi workload production đủ RAM.

Bằng chứng bổ sung ngoài output Git-ignore:

- `data/audit/tv2_materialize_enriched_20261022.py`: script materialize/validation, không gọi extractor/analyzer production.
- `data/audit/tv2_enriched_validation_20261022.json`: 47/47 PASS, runtime/resources/source preservation.
- `data/audit/tv2_enriched_receipt_confirmation_20261022.json`: receipt transition, digest/seal checks, preflight READY, không production execution.
- `data/audit/tv2_enriched_materialization_20261022.log`: console nguyên bản, Git-ignore *.log.

Tiếp theo: recheck tài nguyên/digest, chạy batch ưu tiên Q01 ở lượt được yêu cầu riêng; validate và bàn giao Q01 thật trước. A05/Q06, Q05 route và Q07 business signoff xử lý theo gate riêng. Chưa tạo hoặc công bố output analytics trong lượt này.
