# Q01 Candidate Receiving Contract — Design Draft

> **DESIGN DRAFT**
> **NOT APPROVED**
> **NOT PRODUCTION READY**

Task: TV3-DR03C-05-02-00. Ngày: 21/10/2026, Asia/Bangkok. Owner bản thiết kế: TV3.
Đây là tài liệu receiving candidate độc lập để review; không thay Data Contract hiện có,
không sửa producer, không triển khai receiver và không cấp quyền đọc dữ liệu thật.
**Production Gate CLOSED.** Không có accepted Q01 output; D06 Full **NOT EXECUTED**.

## 1. Phạm vi, trạng thái và nguồn ghim

| Nhãn | Nghĩa dùng trong tài liệu |
|---|---|
| VERIFIED IN SOURCE | Đã đọc source/metadata tại đúng commit; không đồng nghĩa đã chạy |
| CANDIDATE BEHAVIOR | Behavior suy ra trực tiếp từ implementation candidate |
| REPORTED BY TV1/TV2 | Trạng thái được bàn giao hoặc report mô tả; chưa kiểm chứng artifact riêng |
| DESIGN PROPOSAL | Yêu cầu receiving/presentation được đề xuất trong tài liệu này, chưa implement/approve |
| PENDING APPROVAL | Cần owner/người có thẩm quyền xác nhận và bind evidence |
| NOT EXECUTED | Không có execution trong task này; D06 Full cũng chưa được chạy theo handoff |

Không sử dụng synthetic/sample/raw/staging làm kết quả IT. Baseline 439 PASS thuộc
phần TV3 synthetic đã publish; không chạy lại và không dùng để chứng minh official readiness.

| Pin | Commit đầy đủ | Artifact và dòng source đã đối chiếu |
|---|---|---|
| TV1 | `5fda1789b84494a856743c087d10fc511d013d93` | `src/d06_official_contract.py:14–15,75–136`; `src/d06_taxonomy_adapter.py:15–16,75–79`; `docs/d06_official_readiness.md`; `data/audit/d06/pilot_spark_schema.json` |
| TV2 | `3c7c6285a59af8ae9eebfdc2d3667f3fcff92180` | `docs/q01_data_contract_inventory_tv3.md`; `config/tv2_analysis_output_schema.json:1–20`; `src/a06_a08_spark_analysis.py:49–158,216–226,278–343` |
| TV2 receiving/tests | Cùng pin TV2 | `src/d06_handoff_validation.py:7–66`; `config/d06_handoff_contract.example.json`; `config/tv2_analysis_inputs.example.json`; `src/test_a05_a11_integration.py:153–165,185–195`; `data/audit/tv2_publication_20261020.json` |
| TV2 taxonomy | Cùng pin TV2 | `config/it_taxonomy.json`; `config/versions/it_taxonomy_v0.2.2.json`; `src/it_taxonomy.py:170–211` |
| TV3 | `54fa2b5a56cd44b32db5d67d73fa2ac7e69b9708` | Các interface mục 10; `docs/dashboard/dashboard_data_contract_draft.md:178–199` |

Các path upstream là path trong tree của SHA tương ứng, không mặc định có trong checkout TV3.
Report TV2 ghi snapshot kiểm kê `8323b5b…`; commit publish report là pin TV2 bên trên.
Manifest/data-only logs dưới `data/analytics/`, `tmp/` và handoff riêng được report nhắc tới
không có trong Git tree upstream đã kiểm tra; chỉ ghi REPORTED, không truy cập private files.

## 2. Physical candidate table: q01_role_groups

VERIFIED IN SOURCE: TV2 analyzer `categorical():150–158`, gọi cho Q01 tại `216–226`.
Chỉ có đúng sáu cột dưới đây, đúng thứ tự. Schema tĩnh vẫn
`CANDIDATE_NOT_SPARK_VALIDATED`. Kiểu/nullability dưới đây được suy từ biểu thức Spark;
chưa có Q01 production schema/readback để xác nhận metadata lưu trữ.

| Cột vật lý | Kiểu/NULL theo source | Producer expression và nghĩa | DESIGN PROPOSAL: receiving check / trạng thái |
|---|---|---|---|
| `category` | string, nullable | `category(primary_group_code)` qua alias `a02_group`; `trim`, empty → NULL | Cho phép một NULL bucket; non-NULL cần canonical form và domain được duyệt; PENDING APPROVAL |
| `job_count` | bigint, count không NULL | `F.countDistinct("job_id")` từng bucket quan sát | Integral, finite, không bool, >0; source behavior verified, receiver chưa implement |
| `denominator_all_it` | Literal Spark int/long tùy N, không NULL | `F.lit(n)`; N=`d.count()` sau validate unique input | Integral N>0; mọi row cùng N; khớp external population summary; PENDING binding |
| `denominator_known` | Literal Spark int/long tùy K, không NULL | `F.lit(valid)`; count category không NULL | Integral, 0≤K≤N; mọi row cùng K; PENDING binding |
| `share_all_it` | double, biểu thức có nhánh NULL; successful path N>0 nên giá trị phải có | `ratio(job_count, n)` | Finite fraction [0,1], khớp n/N; tolerance PENDING |
| `share_known` | double nullable | `when(category IS NOT NULL, ratio(job_count, valid))` | Known/K>0 phải finite n/K; missing luôn NULL; tolerance PENDING |

Schema tĩnh ghi `integer` với giải thích int/long; `countDistinct` trả bigint nhưng
hai `F.lit` không cast long. Không hứa denominator luôn bigint hoặc tự cast để giấu sai schema.
Physical type/width/readback compatibility cần producer/consumer ký duyệt trước implementation.

Grain: một dòng trên mỗi normalized category quan sát trong **một table/run/input scope**;
tối đa một NULL bucket. Category là grouping key nullable, không phải SQL primary key NOT NULL.
Không có `orderBy`; không phụ thuộc thứ tự rows. Producer không tạo zero-count rows cho absent categories.
DESIGN PROPOSAL: receiver yêu cầu đúng sáu cột, từ chối duplicate column names/extra/missing columns;
policy schema này chưa phải approved physical receiving contract.

Không có physical `category_id`, `B`, `share`, `run_id`, `population_id` hay `filter_id`.
Context luôn nằm ngoài table; không sửa output producer để khớp demo.

## 3. Population: valid subset khác complete accepted population

TV1 schema `d06-official-v1` có 27 fields; `job_id:long` non-null,
`it_decision:string` non-null, `is_it:boolean` nullable;
`primary_group_code`/`subgroup_code:string` nullable. Schema SHA-256:
`44ee9bcc29f5ace90161b6bea67d6543ced30925944761f56e28c7df76a67a68`.

Decision semantics VERIFIED IN SOURCE TV1: ACCEPT → true; REJECT → false; REVIEW → NULL.
Lỗi/missing classifier output không được tự đổi thành REVIEW.
TV2 `validate_d06():133–147` yêu cầu input không rỗng, `job_id` bigint non-null/unique,
mọi row ACCEPT/true, taxonomy version/hash string không rỗng và chỉ một cặp.
REJECT/REVIEW/NULL status làm fail toàn input; analyzer không tự lọc.

**VALID ACCEPT SUBSET:** các row nhận được đều hợp lệ theo predicate trên.
Một subset bị thiếu ACCEPT jobs vẫn có thể qua checks đó.
**COMPLETE ACCEPTED POPULATION:** key-set input bằng toàn bộ ACCEPT/true key-set của
đúng accepted D06 Full run, với source/version binding và acceptance records.
Predicate correctness, key uniqueness và count bằng nhau không chứng minh set equality.

DESIGN PROPOSAL: evidence trước official acceptance phải có:

1. D06 Full run identity, completion/validation/inventory cùng input/config/package/schema versions.
2. Accepted job key-set dẫn xuất theo predicate đã duyệt; giữ audit REJECT/REVIEW ngoài Q01.
3. Key-set của enriched analyzer input, non-null/unique và không nhân dòng sau JOIN.
4. Đối soát hai chiều: không thiếu accepted keys, không thừa keys; counts và hashes cùng snapshot.
5. Producer validation report bind source/D06/input/Q01 output và người có thẩm quyền nghiệm thu.

Đối soát key-level do upstream hoặc receiving step được cấp quyền sau này thực hiện;
UI chỉ nhận bounded aggregate/evidence, không mặc định tải toàn bộ IDs. Task này không đọc data.
Không biết official IT N; **123849 là ALL JOBS, không phải IT count**.

D06 classification 27 fields không trực tiếp đủ receiver/analyzer TV2.
`analyze_frames` còn dùng description, experience, location, employment, remote và timestamps;
`src/d06_handoff_validation.py:7–66` còn yêu cầu source text/hashes, canonical binding.
Cần approved enriched input hoặc approved join với D05; không tự chọn layout/join policy.

## 4. N, K, rates và conservation

VERIFIED CANDIDATE BEHAVIOR: N=`denominator_all_it` là số row input hợp lệ/unique;
K=`denominator_known` là số received jobs có normalized category khác NULL;
n=`job_count` từng observed bucket. N/K lặp trên rows, **không SUM** để suy population.

| Điều kiện | Producer behavior | DESIGN PROPOSAL: presentation |
|---|---|---|
| N>0, K>0, known row | `share_all_it=n/N`, `share_known=n/K` | Giữ riêng hai bases; missing không tham gia panel conditional |
| N>0, missing row | n/N có giá trị; `share_known=NULL` | Missing bucket giữ riêng; NULL hiển thị không áp dụng, không 0% |
| N>0, K=0 | Chỉ missing bucket; toàn `share_known=NULL` | Có all-input distribution; conditional panel không có findings |
| N=0 | `validate_d06` từ chối input | Không suy empty-population rendering support; block |
| Absent category | Không tự tạo row | Ghi absent/not emitted, không tự zero-fill |

Helper ratio có nhánh denominator≤0 → NULL; N=0 vẫn không đi qua successful analyzer.
K chỉ đo category non-NULL, chưa chứng minh code thuộc approved taxonomy.

Với cùng immutable input đã qua validation, source hỗ trợ các hệ quả candidate:

- N≥K≥0; N>0 cho successful Q01; observed counts là số nguyên dương.
- Mỗi input job có đúng một normalized scalar primary bucket, kể cả NULL.
- Tổng `job_count`=N; tổng known `job_count`=K; missing count=N−K.
- Missing count>0 thì cần đúng một NULL bucket; missing count=0 thì không emit NULL zero row.
- Tổng `share_all_it` bằng 1 về toán học; tổng known `share_known` bằng 1 nếu K>0.

Đây là hệ quả code, không phải danh sách assertions producer đã chạy PASS trên Full.
Counts/conservation kiểm bằng integer arithmetic; rates là double, **không yêu cầu floating equality tuyệt đối**.
Production absolute/relative/sum tolerance, rounding và serialization policy: **PENDING APPROVAL** TV2/TV3.
Không lấy zero tolerance của demo hoặc ngưỡng test mặc định làm policy production.
Nếu chưa có policy cần thiết, official receiving fail closed, không tự chọn epsilon.

## 5. Missing-category truth table

Các hàng mô tả producer behavior, không phải approved business normalization/display policy.
Với input job hợp lệ, tất cả trường hợp dưới đều nằm trong N.

| Source group | Normalized category | Trong N? | Trong K? | share_known | Display caution / approval dependency |
|---|---|---|---|---|---|
| NULL | NULL | Có | Không | NULL | Missing bucket; label hiển thị cần TV2/TV3 duyệt |
| Empty string | NULL | Có | Không | NULL | Không đổi thành IT_OTHER |
| Whitespace-only gồm dấu space được Spark `trim` loại | NULL | Có | Không | NULL | Không hứa trim mọi Unicode whitespace/tab; mở rộng normalization cần upstream xác nhận |
| `" SOFTWARE "` | `SOFTWARE` | Có | Có | n/K | Group code, chưa là display label |
| `"Unknown"` | `Unknown` | Có | Có | n/K | Literal known theo code, không đồng nghĩa NULL; domain/display PENDING |
| `"UNKNOWN"` | `UNKNOWN` | Có | Có | n/K | Case-sensitive; không tự gộp với literal khác |
| `"N/A"` | `N/A` | Có | Có | n/K | Không tự coi là missing sentinel |
| `"IT_OTHER"` | `IT_OTHER` | Có | Có | n/K | Nhóm general IT khác missing; label cần duyệt |
| Valid group code khác | Giữ trimmed code | Có | Có | n/K | Cần effective domain/hash được chấp nhận |
| Other nonempty string | Giữ trimmed string | Có | Có | n/K | Producer không validate domain; future receiver quarantine/block nếu chưa được domain chấp nhận |

DESIGN PROPOSAL: không silently sanitize, đổi case, map literal Unknown sang NULL,
hoặc sửa arbitrary string thành approved code. Category của aggregate phải đã normalized;
receiver kiểm canonical form thay vì normalize lại và gộp counts. Policy unexpected code PENDING;
mặc định an toàn là chưa đủ điều kiện official presentation.

## 6. Taxonomy và approvals riêng

SHA-256 tính từ exact Git blob bytes tại pin TV2, không hash text đã đổi newline:

| Cấu hình | Version | SHA-256 |
|---|---|---|
| `config/it_taxonomy.json` | 0.2.0 active | `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d` |
| `config/versions/it_taxonomy_v0.2.2.json` | 0.2.2 candidate | `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874` |

TV1 runner pin v0.2.2/hash thứ hai, classifier source pin
`e437dcc11dda61f847673b9cc8c5801886c1996d` (TV1 adapter:15–16).
Không tự promote active config. Analyzer dùng version/hash từ received input;
chỉ kiểm một cặp không rỗng, không approve SHA format, approved snapshot hay category membership.
Config hash khác classifier code hash/package hash; các binding phải kiểm riêng.

Domain candidate: SECURITY, DATA_AI, DEVOPS_CLOUD, QA_TESTING, NETWORK_SYSTEMS,
SOFTWARE, IT_SUPPORT, IT_BUSINESS, IT_MANAGEMENT; thêm IT_OTHER cho general IT.
SOFTWARE_MOBILE/WEB/OTHER là subgroup, không trộn cùng cấp primary.
Classifier chọn một primary theo evidence tier → group priority → rule priority → rule_id;
candidate groups có thể nhiều nhưng Q01 không explode chúng (`it_taxonomy.py:170–211`).
Đây là disjointness theo representation, không áp `MAY_OVERLAP` của demo.

REPORTED BY TV1/TV2: A04 v0.2.2 ACCEPT WITH CONDITIONS, schema 27 fields được duyệt.
Readiness tại pin TV1 vẫn ghi pending: snapshot cũ không phủ nhận cập nhật bàn giao,
nhưng chưa có approval records mới được xác minh ở đây. Schema approval, conditional A04
acceptance và Full execution là ba trạng thái khác nhau. Full **NOT EXECUTED**.

PENDING APPROVAL riêng: effective taxonomy/version/hash; category domain; IT_OTHER;
missing/literal Unknown; display labels; primary/subgroup hierarchy; complete population scope.
DEMO_A/DEMO_B/DEMO_UNKNOWN không là official domain.

## 7. Manifest/provenance và receiving envelope

Tách bốn lớp; không thêm field vào sáu cột vật lý:

| Lớp | Source-grounded hiện có / DESIGN PROPOSAL |
|---|---|
| Physical Q01 | Sáu cột mục 2; không có run/filter/taxonomy metadata |
| Producer manifest | Source TV2 tạo metadata dưới đây; chưa có accepted successful Q01 manifest |
| Receiving authorization | DESIGN PROPOSAL: quyết định được người có quyền xác nhận, bind artifact/manifest/scope và quyền đọc/presentation; chưa có schema approved |
| Logical dashboard context | DESIGN PROPOSAL: nhận identity/capabilities từ envelope đã kiểm; không fabricate run ID hoặc suy context từ filename |

VERIFIED IN SOURCE TV2 `new_manifest():91–106`, `main():278–343`:

- `schema_version`, `run_id`, `run_kind`, `created_utc`, `status`, `dependencies`, `environment`,
  `queries`, `tables`, `input_contract`; `taxonomy_executed=false`, `etl_executed=false`.
- `provenance.analysis_sha256`, `dictionary_sha256`, Q07 implementation/contract hashes;
  main thêm `provenance.contract_sha256`.
- Sau analyzer: `confirmed_it_jobs`, `spark_version`, `timezone`; `provenance.taxonomy`
  lấy từ input version/hash. Q01 detail có `denominator`, `known_jobs`, `coverage`, `missing_jobs`, `tables`.
- Table entries có `rows`, `parquet`, `parquet_sha256`, `csv`, `csv_sha256`.
- `artifact_digest():31–39` hash directory inventory theo relative filename/size/file SHA;
  manifest lưu digest, không xuất inventory từng partition thành field riêng.
- Main có write/read count và `exceptAll` comparison; đó là source logic, không là readback đã chạy trong task.
- `confirmation():49–52` kiểm approved_by/approved_on và matching digests; không xác thực quyền tổ chức.

DESIGN PROPOSAL: envelope phải bind các yêu cầu còn thiếu sau, tên serialization chưa chốt:

| Metadata cần có | Hiện trạng / yêu cầu xác nhận |
|---|---|
| Producer run ID/code version | Có `run_id`, analysis hash; cần exact producer commit/release binding |
| D06 source run ID/population identity | Không có field chuyên biệt đã xác minh trong Q01 table; cần approved reference đến Full/accepted keys |
| Taxonomy version/hash | Có input pair trong manifest; cần approved config/classifier/package bindings |
| Physical schema version/fingerprint | Manifest `schema_version` là manifest version, không tự là physical Q01 schema version; cần riêng |
| Input/output hashes và partition inventory | Input confirmation/output digests có trong code; cần immutable inventory, canonicalization và verification record |
| Row counts/N/K summaries | Có table rows, confirmed_it_jobs và query details; cần đối soát cùng run/context |
| Validation/readback evidence | Cần report reference/hash và kết quả xác minh thực, không chỉ status string |
| Acceptance/approval record binding | Cần identity, authority, scope, conditions và exact record/manifest/artifact references; PENDING |
| Filter capability/context | Cần khai báo marginal whole-input only; future capability schema/identity PENDING |

Không dựng run IDs hoặc production paths. Quy tắc source `<output>/q01_role_groups.parquet`
và CSV chỉ là naming template, không là output đã có. Không coi run_kind OFFICIAL hoặc SUCCESS
đơn lẻ là acceptance. Không chạy `preflight`/`verify_artifacts` hiện hữu: chúng đọc/hash data.

## 8. Logical mapping và presentation đề xuất

Tất cả logical names dưới đây là **DESIGN PROPOSAL**, không thêm physical columns hoặc API mới.

| Input | Verified meaning | Proposed logical representation | Validation/NULL | Display / approvals |
|---|---|---|---|---|
| `category` | Normalized primary bucket | Nullable category code + is_missing flag, tách display label | Một bucket/key; NULL vẫn missing, không cast thành official code | Label/domain PENDING |
| `job_count` | Distinct jobs/bucket | Category count | Integral >0, no bool/null; conservation | Count nguyên; không SUM joined rows |
| `denominator_all_it` | N toàn received input | Population N riêng | Repeated constant, khớp accepted summary | Card N; không đổi theo visible bars |
| `denominator_known` | K normalized non-NULL | Known population K riêng | Repeated constant; 0≤K≤N | Card K; không gọi K là toàn IT |
| `share_all_it` | Stored fraction n/N | All-input share fraction riêng | Finite [0,1], verify against counts/tolerance | Percent=100×stored fraction đúng một lần |
| `share_known` | Stored fraction n/K hoặc NULL | Known-only share fraction riêng | Finite ở known/K>0; NULL ở missing | Panel riêng ghi denominator K; NULL không 0 |
| External envelope | Provenance/context/eligibility | Immutable context và validation evidence | Binding đã được cấp quyền/approve | Caption run/source/filter scope, không synthesize identity |

UI không tính lại stored rate để thay producer output; counts chỉ dùng kiểm độc lập.
Không normalize bars về 100%, không lấy phần trăm đã round để reconcile.
Không dùng direct synthetic permission/envelope như production access.

DESIGN PROPOSAL: future official page chỉ render sau receiving eligibility được phê duyệt:

- Header nêu exact population/run và whole-input scope; cards N, K, missing count=N−K.
- Panel all-input: counts và n/N gồm missing bucket; caption denominator N.
- Panel known-only: chỉ known categories, n/K; caption conditional denominator K.
- K=0: giữ all-input panel hợp lệ nếu mọi approval/check đã đạt; panel known-only không có chart/rate.
- Missing bucket có label riêng được duyệt; literal Unknown không tự gộp. Absent category không zero-fill.
- Không có unsupported experience/location/date filters. Presentation-only subset phải giữ denominator,
  mô tả subset, không biến thành population filter. Sorting cần policy xác định, không dùng thứ tự producer.
- Invalid schema/metrics/domain, unverified manifest, missing approval hoặc unsupported filter request:
  fail closed, không chart/KPI/count findings, không sample fallback; chỉ bounded status/issue codes.

Chưa có accepted output nên không trình bày số liệu có vẻ official. Tài liệu không kích hoạt page.

## 9. Receiving safety sequence — DESIGN ONLY

```text
Artifact reference
  -> Manifest identity
  -> Provenance verification (metadata-only)
  -> Approval verification
  -> Read authorization
  -> Authorized artifact hash/schema inspection
  -> Physical schema validation
  -> Population/metric checks
  -> Logical mapping
  -> Presentation eligibility
  -> Dashboard
```

Trước **mọi protected artifact byte read**, kể cả hash, Parquet footer/schema scan,
discovery sampling hoặc readback: chỉ xử lý reference và metadata đã được phép đọc;
xác minh manifest identity, trusted producer/provenance claims, acceptance record/authority/scope,
và cấp read authorization bind đúng artifact. Nếu metadata cũng protected thì phải có quyền đọc
metadata riêng trước đó; không dùng thao tác này để lách data gate.

Actual file hash, inventory và provenance chain liên quan data chỉ kiểm **sau read authorization**;
trước đó mới kiểm metadata claims/references. Hash mismatch/revoked/stale binding làm dừng,
không render; presentation eligibility là quyết định riêng sau toàn bộ checks.
DESIGN PROPOSAL: bound immutable snapshot hoặc recheck trước use để tránh artifact đổi sau kiểm tra.
Approval record names/hash không tự chứng minh organizational authority.

Published Artifact Gate vẫn CLOSED; flow này chưa implement và không cho phép đọc thật.
Không mở gate bằng demo flag, origin marker, tên file, schema PASS hoặc saved tests PASS.

## 10. Reusable interfaces và giới hạn thực tế

TV3 tại pin mục 1; line numbers dưới đây thuộc source hiện hành:

| Interface | Có thể tái sử dụng trong thiết kế | Giới hạn cần giữ |
|---|---|---|
| `contract_validator.py:22–46,101`: FieldSpec/ValidationSpec/validate_dataset_contract | Required/extra columns, logical types, finite/count checks | Logical value type không chứng minh Spark physical width; unique_key từ chối NULL, không direct-bind nullable category key |
| `metric_validator.py:13,88`: MetricValidationSpec/validate_metric_contract | Stored fraction/count consistency, range, zero policy, caller tolerance | Positive denominator yêu cầu rate finite; chỉ n=d=0 cho NULL policy. Missing-row n/K không thể dùng cùng spec với known rows |
| `cross_table_validator.py:17,84`: CrossTableValidationSpec/validate_cross_table_contract | Same-grain exact key-set/count reconciliation khi input tương thích | Không aggregate/kiểm authenticity; non-null typed keys/context. Không tự chứng minh accepted population hoặc NULL bucket policy |
| `partition_summary_validator.py:15,78`: PartitionSummaryValidationSpec/validate_partition_summary_contract | Explicit additive/disjoint/exhaustive count sums | Fixed nonempty domain; NULL partition không hợp lệ; không implicit zero/missing partitions, không dynamic observed-domain support |
| `consumer_adapter.py:48`: build_synthetic_consumer_envelope | Mẫu boundaries/diagnostics để tham khảo | SYNTHETIC_SAMPLE + opt-in; không dùng làm official authorization |
| `validation_orchestrator.py:34,52,313`: DatasetBinding/ValidationPlan/run_synthetic_validation_plan | SCHEMA/METRIC/SAME_GRAIN/PARTITION_SUMMARY patterns | Orchestrator hiện synthetic-only; PASS không cấp production |
| `q01_adapter.py:44,116–142,373–440` | Một count/denominator/fraction/context mapping | Một denominator, non-null string domain, MAY_OVERLAP, chặn PARTITION_SUMMARY; không nhận physical Q01 thẳng |
| `q01_demo.py:67–88,99–156` | Curated rendering và percent formatting tham khảo | Hardcoded demo domain/B/context; không phải official presentation model |
| `artifact_gate.py:13` | MISSING/INVALID/BLOCKED boundary | Real artifact đọc được vẫn BLOCKED; không có production bypass |

Thiết kế còn thiếu nullable bucket identity, N/K relations/constants, dynamic observed-bucket
conservation và conditional rate applicability. Có thể thiết kế internal tagged identity
cho NULL để kiểm uniqueness, nhưng chỉ DESIGN PROPOSAL: không sửa category vật lý,
không coi token đó là taxonomy code, và không auto-fill absent domain rows.
Không mặc định đổi generic validator API hoặc Q01 demo để phục vụ official.

## 11. Validation design matrix

Mọi check dưới đây là DESIGN PROPOSAL; mức BLOCKER áp dụng official eligibility,
không hàm ý đã implement/test. Mọi thiếu policy quan trọng đều fail closed.

| Nhóm | Proposed check | Existing validator candidate | Missing capability | Approval cần | Suggested negative test | Severity |
|---|---|---|---|---|---|---|
| Schema | Đúng 6 names/order/types/null rules | ValidationSpec | Physical width/readback binding, order policy | TV2/TV3 physical schema | Extra column, string count | BLOCKER |
| Keys/grain | Unique observed category, tối đa 1 NULL bucket | Schema validator một phần | Nullable-key identity, no zero-fill | Bucket/domain policy | Duplicate NULL/category | BLOCKER |
| N consistency | N>0 constant, khớp external summary | Count checks | Cross-row constant và authenticated summary | Population scope | N khác giữa rows | BLOCKER |
| K consistency | K constant, khớp known sum/summary | Count checks | Known predicate và cross-row constant | Known definition | K khác giữa rows | BLOCKER |
| N/K bounds | Integral 0≤K≤N | Count checks một phần | Cross-column inequality | N/K contract | K>N, bool denominator | BLOCKER |
| Normalization | Aggregate category canonical theo producer | Không direct | Nullable/blank/space checking, không sửa input | TV2 trim/domain | Aggregate category blank | BLOCKER |
| Known/missing | Known=non-NULL; missing share_known=NULL | Nullable FieldSpec | Conditional applicability | Unknown/missing policy | Missing row có n/K | BLOCKER |
| Conservation | Σn=N; Σknown n=K; missing=N−K | Partition-summary một phần | Observed nullable domain, không require absent rows | Partition policy | Lost bucket/count | BLOCKER |
| Rate applicability | Known/K>0 finite; missing NULL | Metric validator trên known-only view | Safe selection + separate missing checks | Applicability policy | Known rate NULL | BLOCKER |
| Fraction range | 0≤stored rate≤1 khi applicable | MetricValidationSpec | Bind cả hai bases | Rate-unit contract | 80 thay 0.8 | BLOCKER |
| Finite numeric | Counts finite/integral/no bool; applicable rates finite | FieldSpec/Metric validator | Physical NaN vs decoded NULL provenance | Serialization policy | Infinity/NaN known rate | BLOCKER |
| Stored-rate consistency | Independently compare stored n/N, n/K; không replace | Metric validator | Approved tolerance + sum policy | Tolerance PENDING | Wrong stored fraction | BLOCKER |
| Taxonomy provenance | Approved version/hash/config/code và category domain | Không có official binding | Manifest/domain authorization | TV1/TV2 effective release | Different hash/code | BLOCKER |
| Population equality | Exact accepted keys=input keys cùng Full snapshot | Same-grain pattern một phần | Authoritative complete set, authorized upstream reconciliation | TV1/TV2 receipt | Valid ACCEPT subset thiếu job | BLOCKER |
| Artifact hashes | Manifest/data/inventory binding đúng snapshot | Không có official verifier | Read authorization + post-auth digest checks | Artifact/manifest contract | Changed output partition | BLOCKER |
| Manifest acceptance | Query/output success + responsible acceptance | Gate đóng hiện tại | Trusted authority/record binding, không suy từ string | Team approval | SUCCESS nhưng approval thiếu | BLOCKER |
| Filter capability | Chỉ whole-input marginal được chấp nhận | Không có official capability checker | Explicit capability/context contract | TV2/TV3 filter policy | Experience/location request | BLOCKER |

Nullable pandas numeric fields có thể dùng NaN làm decoded NULL sentinel; generic schema validator
không tự phân biệt physical NaN với legitimate physical NULL. Receiving design phải giữ null mask/
serialization evidence: reject physical nonfinite numeric rates, chỉ cho decoded missing ở vị trí
rate không áp dụng. Không convert mọi NaN thành zero hoặc dùng nullable rule để bỏ qua known rate lỗi.

## 12. Test plan — DESIGN ONLY, chưa tạo hoặc chạy fixtures

Tất cả dữ liệu và metadata trong tests tương lai là fully synthetic; approvals là test doubles
trong harness riêng, không cấp quyền production, không nhập dữ liệu thật vào demo.
Các fixture hợp lệ dùng expected policy/config được khai báo trong test harness;
không biến policy đó thành approved production defaults.

| Ca synthetic tương lai | Expected behavior của candidate receiver design |
|---|---|
| Normal known categories | Checks pass theo declared fixture policy; giữ stored shares và hai bases |
| One missing category | Giữ 1 NULL bucket, n/N; share_known NULL; known sum=K |
| All categories missing, K=0 | N>0, 1 missing bucket count=N, all share=1; không known-only findings |
| N=0 | Reject unsupported successful population; không render empty-success |
| Repeated N inconsistent | Reject toàn result |
| Repeated K inconsistent | Reject toàn result |
| K>N | Reject |
| Negative job_count | Reject |
| Null job_count | Reject; không impute |
| Duplicate category hoặc duplicate NULL | Reject, không group/merge lại để che lỗi |
| Unexpected category code | Producer hiện giữ; receiver không map/sanitize, block khi chưa có approved domain |
| Literal Unknown versus NULL | Giữ phân biệt; literal thuộc K theo producer; domain/display policy quyết định eligibility |
| IT_OTHER | Known group nếu declared domain chấp nhận; không missing |
| Known row thiếu share_known | Reject khi K>0 |
| Missing row share_known không NULL | Reject kể cả giá trị 0 |
| NaN/Infinity | Reject ở required/applicable values; missing decoded sentinel chỉ theo verified null mask |
| Incorrect stored share | Reject theo fixture tolerance; không recompute rồi thay giá trị |
| Different/mixed taxonomy hash | Block dù counts/shares đúng |
| Missing approval metadata | Block trước protected reads; mocked reader call count=0 |
| Wrong artifact binding | Identity mismatch block trước read; actual hash mismatch sau authorized read block trước render |
| Unsupported filter request | Block; không suy intersection hoặc đổi N/K |
| Absent category và zero-fill | Absent row được giữ absent; zero-count row tự thêm phải bị phát hiện, không là producer output |
| Recomputed share replacing producer share | Tampered stored rate phải fail; presentation không sửa để qua kiểm tra |
| Valid ACCEPT subset nhưng incomplete set | Predicate pass nhưng official population check block |
| REJECT/REVIEW/NULL status/duplicate job ID | Upstream validation fail, không tự lọc |
| Row order thay đổi | Semantic checks không phụ thuộc order; presentation sort theo approved policy |
| Artifact đổi sau verification | Binding/snapshot guard block; không dùng stale eligibility |

VERIFIED existing evidence: TV2 `src/test_a05_a11_integration.py:153–161` chỉ có Q01 sum=3
trong test Q06; `163–165` assert duplicate input raises ValueError; `185–195` Full E2E có skip guard.
Saved `data/audit/tv2_publication_20261020.json`: 102 PASS, 1 SKIP; Full test SKIP.
Không thấy Q01-specific assertions đủ cho N/K/Unknown/taxonomy/readback edge cases bên trên.
Data-only suite/log dưới tmp được report nhắc là evidence lịch sử ngoài Git; không gọi đã đọc/rerun.

## 13. Upstream acceptance gaps và sign-off matrix

| Item | Owner | Technical state | Business approval state | Evidence cần | Impact TV3 |
|---|---|---|---|---|---|
| D06 Full | TV1 | NOT EXECUTED | Run-specific authorization/acceptance chưa xác minh | Full completion/validation/inventory đúng schema/package | BLOCKER official |
| Complete ACCEPT population | TV1/TV2 | Predicate code verified, completeness chưa có | PENDING APPROVAL | Exact two-way key reconciliation, T/N và Full binding | BLOCKER official |
| Enriched input/join | TV1/TV2 | Receiving template/source candidate | PENDING APPROVAL | Schema, source hashes, FK/grain, approved join/layout | BLOCKER analyzer integration |
| Official Q01 output | TV2 | VERIFIED candidate implementation, output chưa được nghiệm thu | PENDING APPROVAL | Accepted input, run/table/output hashes | BLOCKER official |
| Manifest/readback | TV2 | Writer/readback code có; actual accepted evidence chưa có | PENDING APPROVAL | Manifest, physical schema, readback/validation, inventory | BLOCKER receiving |
| Taxonomy | TV1/TV2 | v0.2.2 pin khớp, active vẫn v0.2.0 | Conditional A04 acceptance REPORTED; Q01 policy riêng pending | Effective config/code/package hash và conditions | BLOCKER domain |
| Unknown/display policy | TV2/TV3 | Candidate NULL/blank/literal behavior verified | PENDING APPROVAL | Domain, missing/IT_OTHER/literal/display labels | BLOCKER official presentation |
| N/K definitions | TV2/TV3 | Candidate formulas verified | PENDING APPROVAL cho official scope | Complete-population mapping, applicability/coverage sign-off | BLOCKER denominators |
| Rate tolerance | TV2/TV3 | Double producer; không production tolerance | PENDING APPROVAL | Explicit numeric/serialization/sum comparison policy | BLOCKER validation |
| Filter capability | TV2/TV3 | Whole-input marginal, không joint filters | Capability/display sign-off pending | Approved scope/capability declaration | BLOCKER unsupported requests |
| Artifact authorization | Nhóm/TV3 | Gate CLOSED, receiver chưa implement | PENDING APPROVAL | Trusted metadata/read/presentation authority bound artifacts | BLOCKER protected reads |

## 14. Assumptions và review exit

Các invariant giả định một immutable input snapshot, group_column=`primary_group_code`,
không JOIN nhân dòng trước Q01; producer source được giữ đúng pins. Các assumption phải bind
trong future run evidence, không suy từ tên release/file. Whitespace ngoài Spark space-trim,
physical nullability sau readback, schema widths, serialization/tolerance, approval authority,
labels và capability envelope vẫn còn quyết định mở.

Đủ evidence để review **candidate receiving design**; không phải official integration acceptance.
Review cần xác nhận semantics/validation gaps và gửi các decision pending đến đúng owner;
không âm thầm finalize upstream policy. Tài liệu này không thay
`docs/dashboard/dashboard_data_contract_draft.md`, không sửa API, không tạo test/data,
không chạy Spark và không cho phép real artifact reads. **Production Gate CLOSED.**
