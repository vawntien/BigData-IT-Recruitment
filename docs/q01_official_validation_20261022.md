# TV2 — Q01 Official validated, 22/10/2026

**Q01: EXECUTED → VALIDATED; chưa ACCEPTED.** Đã chạy runner hiện có trên đúng 5.206 D06 ACCEPT jobs, tạo output thật và kiểm tra độc lập Parquet/CSV. **94/94 kiểm tra PASS** cho Q01 và các output Q02–Q04/Q08. Có thể bàn giao Q01 cho TV3 để tích hợp và review kỹ thuật ngay; còn thiếu quyết định nghiệm thu của người có thẩm quyền để ghi ACCEPTED.

Không chạy A05 official/Q06 hoặc Q07; không thay classifier/taxonomy/validator để ép PASS, không thay D05/D06/enriched Parquet, không commit/push/merge. Không tạo business approval hoặc gửi tin nhắn ra ngoài.

## 1. Run và preflight

- Run ID: `tv2_q01_q04_q08_official_20261022_01`.
- Branch/commit thực thi: `feat/tv2-analysis` / `3c7c6285a59af8ae9eebfdc2d3667f3fcff92180`. Code SHA thực tế nằm trong runner manifest, được kiểm lại khi validation.
- Runner: `src/a06_a08_spark_analysis.py`; tham số đúng `--contract`, `--output`, `--run-id`. Không có chế độ Q01-only.
- Input: `data/processed/tv2/enriched/tv2_enriched_d06_accept_20261022_01/jobs.parquet/`, **39 physical fields**, digest `17ae5383e848f7323b99800bd3d79a72e84e2bca62844f66dd00aaa06e80a9b2`.
- Receipt: Đồng Viết Dũng (TV2), `2026-10-22T14:23:24+07:00`, scope technical receipt 5.206 jobs; không business acceptance.
- D06 upstream: `official_20261021_a9dddfe4`, ACCEPT=true; taxonomy version/hash đúng nguồn đã receiving PASS.
- Metadata seal/sidecar hashes, source hashes và technical receipt được đối chiếu lại trước khi chạy. Output directory chưa tồn tại. Optional paths job_skills/skill_map/A05/salary đều NULL, không fallback sang dữ liệu khác.
- Preflight dependency: D06=true; D05/A05/D07=false. D05=false ở đây là Q05 bridge/mapping chưa xác nhận, không phải thiếu canonical D05.
- RAM free ~4,52GiB, virtual headroom ~4,50GiB, disk free ~183,36GiB trước chạy. Python3.11.9/PySpark4.2.0/Java21.0.12.1; heap2GiB, UTC. Dùng JDK/Windows filesystem adapter local đã kiểm chứng. Runner helper đặt local[*], parallelism2/shuffle4; không sửa helper.

**Sửa lỗi transcription trước chạy:** phát hiện `approved_by` của metadata lượt trước chứa `??ng Vi?t D?ng (TV2)` vì PowerShell stdin làm mất Unicode. Đã sửa đúng tên theo xác nhận trực tiếp đã có của người dùng, giữ nguyên approved_on/scope/digest, lưu exact metadata cũ tại `receipt_history/encoding_correction_20261022/`, tạo correction record và đóng lại manifest/seal. Không tạo approval mới. Parquet không đổi. Chỉ tiếp tục sau khi receipt identity và hashes PASS.

Metadata enriched hiện tại sau correction: manifest SHA `2ddfb6c22888a00667c46bde3f95bd32587afa3e4513f47d9aca4bb5a66273e9`; receipt SHA `8eef3d1c45736d2a17b3b5a15b4b8fe02b8b5181d6eff406d823c5d5a5a4d810`; contract SHA `70b0df1fe4e0e6d18cf27dc016c34eceabc9f7df284ba6c58563884bbccdf02c`. Các hash metadata cũ trong báo cáo enriched trước đó là lịch sử trước correction; artifact digest input vẫn không đổi.

Runner created_utc `2026-10-22T07:31:02.494793+00:00` = 14:31:02 +07; runner exit được lưu lúc 14:31:27 +07. **Python exit 2**, overall `PARTIAL_SUCCESS`, vì Q05/Q06/Q07 BLOCKED; Q01–Q04/Q08 đều query-level SUCCESS. Không xem exit2 này là Q01 FAIL và không nâng overall thành SUCCESS.

**Cảnh báo metadata:** runner manifest còn literal `date="2026-10-19"` do code hardcode. Ngày chạy thật là 22/10 theo created_utc, run ID và runner exit evidence. Không sửa runner/manifest gốc để che trường lịch sử này. Đây không phải output cũ chạy ngày 19/10.

## 2. Output và hashes

Root tuyệt đối: `C:/Users/dongv/BigData-IT-Recruitment/data/analytics/tv2_q01_q04_q08_official_20261022_01/`. Output nằm dưới Git-ignore `data/analytics/*`.

| File/path tương đối với root | Kết quả |
|---|---|
| `q01_role_groups.parquet/` | 10 category buckets; đọc lại bằng Spark PASS |
| `q01_role_groups.csv` | UTF-8 BOM, đúng sáu header; chuyển kiểu và đối chiếu mọi row với Parquet PASS |
| `manifest.json` | Runner manifest thật; Q01 SUCCESS, overall PARTIAL_SUCCESS |
| `independent_validation/q01_role_groups_schema.json` | Physical schema từ Parquet đọc lại |
| `independent_validation/validation.json` | 94/94 PASS; query-level VALIDATED, accepted=false; N/K/shares/distribution/population proof |
| `independent_validation/completion.json` | Đóng hash validation và runner manifest, business_accepted=false |
| `q01_handoff_manifest.json` | Q01 VALIDATED handoff metadata, provenance, metrics, hashes và giới hạn filter; không approval |

| Artifact | SHA-256 |
|---|---|
| Q01 Parquet directory artifact_digest | `3c7a70c64b776f72cb9a9d429f12e8fb09956c97d52cd539ca263fa60b6bccf3` |
| Q01 CSV | `b28ca1b6b4b370eebfc6e563bc3a555dc477281ca0e263bb17bc14a77e24a49d` |
| Runner manifest | `5665057f408e279d09c2130d7cb7e59a564d093f1516ddd1e0cf2576931450ac` |
| Independent validation JSON | `8cc17d0e08680709679a2c72f95db7aca21b1865baed0e836eab1e8664611409` |
| Physical Q01 schema JSON | `c9e2283ec9db4a5f1ae8feed99b99598b46a53a4b3e4f022f7786e5caa2d0277` |

Directory digest dùng đúng `artifact_digest` của runner: recursive files sort, gồm markers nếu có, compact JSON `[relative_path,size,sha256]` rồi SHA-256. Không nhầm với hash một part hay hash file manifest. Hash tất cả 10 bảng/csv của run đã được kiểm lại với manifest trước đọc validation và sau validation.

## 3. Physical schema Q01

Đúng sáu cột, đúng thứ tự:

| Cột | Spark physical type sau read-back | Ý nghĩa |
|---|---|---|
| category | string, nullable | Mã primary group sau trim; NULL bucket nếu có observed missing |
| job_count | bigint/long, nullable | Count distinct jobs trong category |
| denominator_all_it | int, nullable | N=5.206, lặp trên mỗi hàng; không SUM |
| denominator_known | int, nullable | K=5.206, lặp trên mỗi hàng; không SUM |
| share_all_it | double, nullable | job_count/N, fraction 0–1 |
| share_known | double, nullable | job_count/K với known category; missing bucket NULL |

Nullable ở đây là schema Parquet reader, không phải phát hiện NULL trong mọi cột. Denominators thực sự là **int**, không tự mô tả thành bigint. TV3 nhân share ×100 đúng một lần để hiển thị phần trăm. Grain/key: một hàng/category trong snapshot/run; không có job_id/filter_id/run_id trong bảng aggregate.

## 4. Kết quả và conservation thật

**N=5.206; K=5.206; missing=N−K=0.**

| category | job_count | share_all_it (%) | share_known (%) |
|---|---:|---:|---:|
| SOFTWARE | 2.393 | 45,97 | 45,97 |
| DATA_AI | 1.115 | 21,42 | 21,42 |
| NETWORK_SYSTEMS | 556 | 10,68 | 10,68 |
| DEVOPS_CLOUD | 441 | 8,47 | 8,47 |
| SECURITY | 187 | 3,59 | 3,59 |
| IT_SUPPORT | 152 | 2,92 | 2,92 |
| QA_TESTING | 103 | 1,98 | 1,98 |
| IT_BUSINESS | 92 | 1,77 | 1,77 |
| IT_MANAGEMENT | 90 | 1,73 | 1,73 |
| IT_OTHER | 77 | 1,48 | 1,48 |
| **Tổng** | **5.206** | **100% trước làm tròn** | **100% trước làm tròn** |

Số % hiển thị làm tròn 2 chữ số, không thay fraction lưu trong output. Hai share bằng nhau ở snapshot này vì K=N; không đồng nhất hai denominator trong các population khác.

| Điều kiện bắt buộc Q01 | Kết quả fresh validation |
|---|---|
| Distinct/non-NULL/unique input job_id | PASS 5.206/5.206; NULL=0, duplicate=0 |
| Exact population với D06 ACCEPT | PASS missing=0, extra=0, đối chiếu hai tập ID; input không chứa REVIEW/REJECT |
| Một primary category/job | PASS một scalar primary/job, giữ nguyên primary/subgroup/taxonomy theo D06; không explode candidate groups |
| Duplicate category buckets | PASS 0; đúng 10 buckets |
| Tổng job_count | PASS **5.206=N** |
| Tổng job_count known | PASS **5.206=K** |
| Tổng share_all_it | PASS **1,0** |
| Tổng share_known | PASS **1,0** |
| Từng share và denominator | PASS recompute từ input bằng Python Counter, đối chiếu mọi bucket; rel_tol=abs_tol=1e-12 |
| NULL/blank/literal Unknown | PASS observed đều 0; không silently remap |
| IT_OTHER | PASS **77 jobs**, thuộc known population và cả hai share |
| Category membership | PASS mọi observed code thuộc taxonomy v0.2.2 đã duyệt |
| Taxonomy/input/code/contract provenance | PASS exact hashes và manifest, không classify lại |
| Physical schema/CSV/Parquet/hash read-back | PASS mọi header/field/type/row/key/share/hash |

Independent validator không gọi analyzer để tái tạo output: đọc 5.206 scalar input records, dùng Python Counter tính category counts và denominator/share expectations; đọc lại từng Parquet/CSV và đối chiếu. Population proof dựa source job_ids + confirmed input digest; không giả vờ kiểm job_id trong aggregate vì aggregate không có cột đó.

Chỉ policy được triển khai và quan sát: trim space/blank→NULL; NULL missing giữ riêng, không thành IT_OTHER. Literal Unknown (case-insensitive quan sát trong validation) hiện **0 jobs**, nhưng code hiện sẽ coi literal đó là known nếu xuất hiện, không tự chuyển NULL. IT_OTHER là category known hợp lệ. N=0 bị input validator từ chối; K=0 guard trả share_known NULL theo code, nhưng case K=0 không xuất hiện trong production snapshot này và không được gọi là fresh production test riêng.

Taxonomy v0.2.2 SHA `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874`; classifier TV2 commit `e437dcc11dda61f847673b9cc8c5801886c1996d`; D06 runner commit `5fda1789b84494a856743c087d10fc511d013d93`. Analyzer dùng nhãn và provenance D06, không chạy classifier hoặc promote active taxonomy. Label mapping lấy từ `config/versions/it_taxonomy_v0.2.2.json` theo code category, không sửa cột aggregate thành category_id/B/share.

## 5. Trạng thái riêng từng câu

Tất cả tên bảng dưới nằm thật trong output root, mỗi bảng có `.parquet/` và `.csv`; hashes/row counts trong runner manifest, physical schema và independent checks trong independent_validation.

| Câu | Trạng thái hiện tại | Output thật và kết quả kiểm |
|---|---|---|
| Q01 | **VALIDATED**, chưa ACCEPTED | q01_role_groups; 10 rows; N=K=5.206, missing0; conservation/shares/CSV-Parquet PASS |
| Q02 | **VALIDATED kỹ thuật**, chưa ACCEPTED | q02_experience; 7 rows gồm missing bucket; N=5.206, K=3.722, missing=1.484; denominator/shares/conservation PASS; nhãn cấp bậc không phải số năm |
| Q03 | **VALIDATED kỹ thuật**, chưa ACCEPTED | q03_location; 845 rows; N=K=5.206, missing0; known-location denominator và input counters PASS; location string không phải chuẩn hóa địa lý |
| Q04 | **VALIDATED kỹ thuật**, chưa ACCEPTED | q04_work_type 7 rows; q04_remote_flag 2 rows; q04_work_type_crosscheck 7 rows; counts, shares, source crosscheck và CSV/Parquet PASS; không suy remote NULL thành onsite |
| Q05 | **BLOCKED** | Không có output; thiếu Q05 bridge/mapping route confirmation (manifest dependency D05=false) |
| Q06 | **BLOCKED**, chưa chạy | Không có output; A05 official chưa chạy, không có bridge/status official |
| Q07 | **BLOCKED / PENDING BUSINESS APPROVAL** | Không có output; D07 technical staging có thật nhưng không có Q07/D07 policy approval trong contract |
| Q08 | **VALIDATED kỹ thuật**, chưa ACCEPTED | q08_original_month 3 rows, original_week_start_utc 9 rows; listed_month 1 row, listed_week_start_utc 3 rows. Mỗi timestamp valid5.206/missing0; độc lập kiểm UTC months/Monday week starts từ epoch, counts/shares/coverage/CSV-Parquet PASS |

Không tuyên bố Q01–Q08 đều hoàn thành từ overall runner. Không có A05 production output mới. Q05/Q06/Q07 không được bật bằng boolean hoặc approval giả.

## 6. Filter, acceptance và bàn giao

Q01 là marginal distribution trên toàn snapshot **5.206 ACCEPT**. Chưa có giao category×experience×location×date hoặc denominator tính lại theo cross-filter. Chọn/ẩn category rows trên UI không biến N=5.206 thành filtered denominator. Không dùng aggregate này để suy chart cross-filter đã hỗ trợ. Không cộng các denominator lặp trên hàng. Nếu cần cross-filter, phải có job-level backend hoặc cube/output phù hợp và validation riêng.

Giới hạn upstream cần giữ khi công bố: Full có 123.849 jobs, gồm ACCEPT5.206/REJECT58.953/REVIEW59.690. REVIEW (~48,20%) giữ riêng, không coi là REJECT. A04 ACCEPT WITH CONDITIONS có limitations development reference; các thống kê này chỉ mô tả ACCEPT snapshot theo taxonomy, không bảo đảm recall/accuracy toàn thị trường.

**Đủ để bàn giao kỹ thuật Q01 cho TV3 ngay:** gửi q01_role_groups.csv, nguyên thư mục q01_role_groups.parquet, manifest, q01_handoff_manifest, schema và validation/completion. Đây là artifact local, chưa tự upload hoặc gửi cho TV3. Khi copy sang máy TV3 cần kiểm lại hashes.

**Còn thiếu để ACCEPTED:** người có thẩm quyền nghiệm thu Q01 và TV3 xác nhận tích hợp/display/denominator theo scope filter hiện có. Không có business acceptance nào được ghi từ việc runner hoặc validation PASS. Integration consumer chưa được chạy trong lượt này.

Tin nhắn gợi ý gửi TV3:

> TV2 đã chạy Q01 Official trên toàn bộ 5.206 D06 ACCEPT, run tv2_q01_q04_q08_official_20261022_01. Q01 hiện VALIDATED, N=K=5.206, missing=0, 10 nhóm; conservation/shares và Parquet/CSV/hash/provenance PASS. Output tại data/analytics/tv2_q01_q04_q08_official_20261022_01/ gồm q01_role_groups, manifest, q01_handoff_manifest và independent_validation. Có thể tiếp nhận kỹ thuật để tích hợp; chờ nghiệm thu để ACCEPTED. Q01 hiện là marginal toàn snapshot, chưa hỗ trợ cross-filter experience/location/date. Q05/Q06 còn BLOCKED, Q07 chờ business approval.

## 7. Bằng chứng audit

- `data/audit/tv2_q01_preflight_metadata_20261022.json`: source/digest/receipt identity và metadata correction.
- `data/audit/tv2_q01_resources_20261022.json`: RAM/virtual/disk trước official run.
- `data/audit/tv2_q01_runner_exit_20261022.json`: Python exit2 tương ứng PARTIAL_SUCCESS.
- `data/audit/tv2_validate_q01_official_20261022.py`: independent validator; không production execution.
- `data/audit/tv2_q01_official_validation_20261022.json`: bản audit của 94 checks, query statuses và Q01 result; validator Python exit0.
- Console runner và validator lưu trong `data/audit/tv2_q01_official_runner_20261022.log`, `tv2_q01_independent_validation_20261022.log`, Git-ignore *.log.

Chỉ thêm output/validation/report và sửa transcription metadata receipt có lưu lịch sử; không sửa tracked pipeline/classifier/taxonomy, không sửa dữ liệu nguồn, không commit/push/merge.
