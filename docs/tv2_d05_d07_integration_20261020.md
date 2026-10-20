# Kiểm tra và chuẩn bị tích hợp D05/D07 — 20/10/2026

Branch thực tế: `feat/tv2-analysis`. Dữ liệu đã giải nén được đọc trực tiếp, không giải nén ZIP, không chạy classifier hoặc A05 official, không công bố thống kê CNTT, không commit/push/merge. Các thay đổi có sẵn được giữ nguyên; chỉ bổ sung báo cáo này, rule ignore và hồ sơ kiểm tra trong `tmp/`.

## Dữ liệu và kết quả trực tiếp

Gốc: `data/handoff/tv1/TV1_Handoff_D05_D07/`.

| Kiểm tra | Kết quả thực tế |
| --- | --- |
| SHA256SUMS.csv | PASS: 36 file khớp SHA-256 và kích thước, gồm HANDOFF_MANIFEST.json |
| HANDOFF_MANIFEST.json | PASS: 35 payload khớp SHA-256 và kích thước; không thiếu/thừa file ngoài hai file điều khiển checksum/manifest |
| D07 completion seal | PASS: SUCCEEDED; hash run_manifest, output_inventory và validation_summary khớp completion.json |
| ZIP gốc | Không tìm thấy `TV1_Handoff_D05_D07.zip` trong dự án; không kiểm CRC ZIP |
| D05 `D05_Canonical/jobs` | PASS PySpark: 123.849 dòng, 50 cột, 123.849 job_id duy nhất, 0 NULL |
| D07 `D07_Salary/salaries.parquet` | PASS PySpark: 123.849 dòng, 28 cột, 123.849 job_id duy nhất, 0 NULL |
| Schema | PASS cả hai schema.json: đúng tên/thứ tự/kiểu nested và nullable khi readback; job_id bigint |
| Khóa và JOIN | PASS: hai left-anti JOIN đều rỗng; JOIN namespace d07_* giữ 123.849 dòng/77 cột |
| Trạng thái D07 | PASS: USABLE 36.059, MISSING 87.776, INVALID 14 |
| NULL lương normalized | PASS: MISSING/INVALID không có normalized min/med/max |
| Text binding | PASS: SHA-256 source_description khớp source_description_sha256 trên dữ liệu thực |
| Thời gian | PASS: original_listed_time/listed_time là timestamp; tổng distinct jobs theo tuần UTC bằng số jobs có timestamp tương ứng |
| D06 | Chỉ 4 file tài liệu/readiness/schema; summary ghi FULL NOT_EXECUTED, acceptance NOT_GRANTED. Không thấy D06 Full Parquet dưới data/ |

Runtime cục bộ: PySpark 4.2.0, Java 21 từ runtime đã có trong `tmp/tv2_d05_receipt_457f90ae/runtime/`; session UTC. Không cài đặt/đổi config hệ thống. Cảnh báo native Hadoop không làm hỏng các phép đọc/kiểm dữ liệu đã PASS.

Các số trên chỉ là kiểm tra ALL JOBS staging, không phải thống kê CNTT. Reported coverage kiểm tra `(USABLE+INVALID)/123849`, usable coverage `USABLE/123849`; không lấy tập USABLE làm mẫu số coverage. Có 29.793 normalized min, 29.793 normalized max và 6.266 normalized med; không tự tạo median bằng trung bình hai cận, không missing→0.

## Tương thích A05 v0.1.2, A06–A08 và Dashboard V03.1

Đã đọc release `config/a05_release_v0.1.2.json`, các schema/runtime adapter hiện tại và contract V03.1 trực tiếp từ Git object `ba57c728d56e887c7555e545032e93a762b77801:docs/dashboard/dashboard_data_contract_draft.md`. Đây vẫn là DISCUSSION DRAFT / NOT APPROVED / NOT PRODUCTION READY.

| Phần | Tương thích | Còn thiếu hoặc chưa tương thích |
| --- | --- | --- |
| A05 | job_id bigint; description/source_description và source hashes là string; nguồn raw có hash đã kiểm tra | D05 không có is_it, it_decision, taxonomy_version/hash, primary_group_code. Chờ D06 Full và xác nhận source binding; không tự đổi description clean thành raw trong pipeline |
| A06 Q01–Q04 | location, formatted_experience_level, formatted_work_type, work_type string; remote_allowed boolean; giữ NULL | Chưa có IT population/group; Q04 còn thiếu mẫu số known remote và coverage summary theo V03.1 |
| A06 Q05 | job_functions array struct có skill_abr, skill_name, mapping_status phù hợp schema candidate project_job_functions | Gói không có separate job_skills/skill_map. Projection là candidate, chưa nối official/chưa có xác nhận membership/contract; không coi job_functions là technical skills |
| A07 Q06 | Stable dictionary v0.1.2 giữ nguyên; kiểm thử denominator phải gồm WITH_MATCH + NO_MATCH, không chỉ bridge positive | Chờ A05 official bridge/processing cùng run với D06; còn thiếu summary mọi nhóm kể cả zero-hit-only |
| A08 Q07 | Khóa bigint, normalized_* decimal(38,4), provenance/status/source/unit rõ ràng | Template đang đòi min_salary/max_salary/currency/pay_period/compensation_type ở top-level; D07 dùng selected_salary struct, canonical_* và normalized_*. Không plug-and-play |
| Q07 semantics | Có thể chuẩn bị mapping normalized min/max→normalized_min/max_salary, currency→normalized_currency, period→normalized_unit, compensation→canonical_compensation_type, source→salary_source | Cần chọn posted selected_salary.* hoặc normalized ANNUAL_EQUIVALENT có chủ đích. Code hiện lấy paired min/max subset và một salary_n; V03.1 cần min/max sample và n riêng, B_g/IQR/tolerance. Không đổi nhãn USABLE thành invalid vì med-only |
| A08 Q08 | Cả hai timestamp basis UTC đã kiểm tra được trên ALL JOBS | Chờ population D06; thiếu category/time summaries, window/snapshot/partial-period evidence |
| Dashboard | Distinct grain, NULL, source/currency separation và scope staging rõ | share_* hiện là fraction 0..1; contract dùng percent 0..100, cần convert đúng một lần. Marginal aggregates không hỗ trợ tự suy filter chéo; chưa có bảng IT production hoặc formal acceptance |

Annualization D07 là giả định policy, không phải FX hoặc actual earnings. Không cộng/trộn các currency/source/units, không tự lọc outlier hoặc duyệt ngưỡng mẫu nhỏ.

## Công việc thực hiện và hồ sơ

- Kiểm checksum bytes trực tiếp cả CSV và manifest; kiểm seal D07, đọc README/schema/validation/manifests và readiness D06.
- Chạy PySpark trên Parquet thực: grain/schema/khóa/JOIN, status và normalized NULL, source hash, công thức coverage và conservation theo tuần UTC.
- Chạy regression receipt/source binding, gate official/publication và fixture analytics. Chi tiết từng lần chạy giữ trong hồ sơ, không thay lỗi/SKIP bằng PASS.
- Chuẩn bị `schema_compatibility.csv`, `integration_inventory.json` và `analysis_inputs.pending.json` dưới `tmp/tv2_d05_d07_20261020/`. File pending không điền approval/membership giả và không phải contract chạy official.
- Thêm `/data/handoff/` vào `.gitignore`; `git check-ignore` xác nhận rule hiệu lực, `git ls-files data/handoff` rỗng. Không đưa dữ liệu lớn vào Git. `.gitattributes` đã thay đổi trước lượt này và được giữ nguyên.

Evidence chính: `tmp/tv2_d05_d07_20261020/{verification.json,manifest_check.json,completion_seal_check.json,tests.txt,run.log,synthetic_retry.json,synthetic_retry.txt,schema_compatibility.csv,integration_inventory.json}`. Script tái hiện nằm cùng thư mục; không chạy A05 official khi tái kiểm dữ liệu.

Kết quả regression cuối: **26 test khác nhau PASS, 1 test D06 thật SKIP** do chưa có contract D06 được TV1 xác nhận. Lần đầu có 20 PASS, 1 SKIP và 1 lỗi setUpClass của nhóm synthetic vì Spark addPyFile gọi Windows chmod khi thiếu HADOOP_HOME/winutils. Chạy lại đúng 6 test synthetic bằng chế độ đã hỗ trợ `shared_local_pythonpath`: **6 PASS, 0 FAIL/error/SKIP** (408 giây). Các test này xác minh distributed extractor parity, Parquet readback, duplicate rejection, Q05 multilabel không nhân population, Q06 denominator có successful zero-hit và Q07 tách currency/period/source. Đây là fixture synthetic, không phải A05 official hoặc kết quả CNTT thực. Giới hạn deployment addPyFile mặc định trên Windows vẫn còn, không được coi đã sửa.

## Phần chờ và thứ tự tiếp theo

1. TV1 hoàn tất điều kiện nghiệm thu/ủy quyền upstream và bàn giao D06 Full thật: Parquet, schema, manifest/hash, reconciliation, taxonomy/classifier version/hash, source binding và receipt. Không tự promote taxonomy candidate v0.2.2.
2. Nhận D06 bằng validator hiện hữu, đối chiếu membership/text với D05 đã xác minh; sau khi đủ điều kiện mới chạy A05 official v0.1.2, parity/roundtrip và review. A05 không cần chờ Q07 hoàn thiện.
3. Chốt Q05 embedded projection hoặc separate bridge contract; chốt Q07 posted/normalized/source policy, mẫu riêng min/max, precision/quantile/outlier/small-n và mapping phần trăm cùng TV1/TV3.
4. Khi D06/A05/approval đủ: chạy A06–A08 với denominator đúng IT scope, hoàn thiện summaries/filter capabilities, kiểm contract/output rồi mới công bố. D05/D07 ALL JOBS không thay thế tập IT.

Các tài liệu trạng thái ngày 19/10 còn mô tả D07 chưa có là bằng chứng lịch sử. Báo cáo ngày 20/10 này cập nhật việc đã nhận và xác minh D07 staging; không nâng thành nghiệm thu IT production.

## Q07 — cập nhật implementation tiếp nối ngày 20/10

Các mô tả paired `salary_n` ở phần kiểm tra ban đầu phía trên là trạng thái trước sửa. Implementation hiện dùng [q07_salary.py](../src/q07_salary.py), được nối vào analyzer A06–A08; schema vật lý và công thức nằm trong [contract v2](../config/q07_salary_contract_v2.json), regression trong [test_q07_salary.py](../src/test_q07_salary.py). Không tạo lại bộ báo cáo A05–A11.

- **Nguồn:** posted min/max từ `selected_salary` decimal(20,4), đơn vị canonical gốc và `salary_source`; không lấy `raw_postings_normalized_salary` làm fallback, không annualize lại. `raw_postings`/`raw_salary_record` bảo toàn provenance typed D05. `normalized_*` decimal(38,4) là ANNUAL_EQUIVALENT theo policy D07, không phải lương native hay FX. `selected_salary.med_salary` không là median thống kê.
- **Eligibility candidate:** giữ nguyên D07 `USABLE`, không ép đủ cả ba amounts và không tự thay status. Min-only/max-only/med-only đều có thể là eligible bundle; chỉ min non-null vào n_min, chỉ max non-null vào n_max. Nếu USABLE vi phạm amount/order/unit invariants, dừng thay vì âm thầm sửa hoặc loại hàng.
- **Metric:** continuous exact percentile 25/50/75, Spark trả double; IQR=P75−P25 riêng mỗi endpoint. `n_min/n_max` là mẫu phân vị; coverage dùng `population_n=B_g` trước lọc salary/unit/source. Có summary riêng cho nhóm thiếu toàn bộ lương và status partition. `scope_id` và `salary_basis` nằm trong khóa; source vẫn là chiều riêng. NULL context join null-safe, không đồng nghĩa ALL. Không median-of-medians hoặc SUM B_g lặp ở detail.
- **Official gate:** vẫn đòi D06 thật; D07 approval phải bind digest và contract v2, eligibility/source-grain, quantile method, outlier decision và ngưỡng mẫu. Không có approval nào được điền. `minimum_salary_group_n=null` không tự chọn ngưỡng; adequate flags NULL. Không suppress kết quả bằng ngưỡng tự nghĩ.
- **TV3:** có thể implement consumer theo 3 schema trong contract v2. `share/coverage` là fraction; UI nhân 100 đúng một lần. Không trộn bảng v1 paired salary_n với v2; không bật pooled/ALL/filter không được sản xuất. Signoff và production vẫn PENDING.

### Các câu hỏi cụ thể cần TV1/nhóm xác nhận

1. Chấp nhận `D07_USABLE_WHOLE_SELECTED_BUNDLE` làm eligible bundle cho Q07 native, bao gồm med-only và một cận, hay cần tiêu chí nghiệp vụ bổ sung? Phần bổ sung phải được version hóa riêng, không thay status nguồn.
2. Chốt Q07 A01 dùng posted native `selected_salary` + canonical units và giữ `salary_source` trong key? Nếu muốn một nguồn authoritative, cung cấp source-selection contract thay vì pool hai nguồn. Normalized annual equivalent cần một basis/chart riêng nếu sau này được yêu cầu.
3. Có policy xử lý high positive ordered outliers theo currency/period không? Nếu chưa, chấp nhận NO_ADDITIONAL_FILTER và giới hạn plausibility, hay tiếp tục chặn chart production?
4. Chấp nhận exact continuous interpolation với output double và tolerance/rounding nào? Nếu cần decimal-exact hoặc approximate, phải đổi method/schema có phiên bản, không đổi ngầm.
5. Ngưỡng small-n và quy tắc hiển thị/suppress cụ thể là gì? Ngưỡng áp dụng riêng n_min/n_max; không dùng eligible count hoặc B_g thay sample size.
6. Bàn giao source `src/normalize_salary.py` đúng release `479d3d83ff3194a5556ce29884c92478c90a969c` và hash để TV2 đối chiếu executable rules. Gói hiện chỉ có schema/policy/report/manifests, không có code. Git object này chưa có local; thử fetch không ghi được FETCH_HEAD trong sandbox và truy cập raw URL không thành công. Hiện chưa tuyên bố đã review code nguồn TV1; kiểm được policy/report và invariants dữ liệu thật.

Q05/Q08 chỉ bổ sung kiểm thử trên D05 ALL JOBS: embedded projection unique job_id/skill_abr và không orphan; timestamp types và monthly distinct-count conservation hai basis. Không tạo IT membership hoặc xuất official aggregates.

**Kết quả thực thi Q07 v2:** 18 test khác nhau PASS cuối cùng: 4 test Q07 synthetic/real D07–D05, 8 contract gates, 5 report/publication regressions và 1 analyzer/schema/approval integration. Lượt đầu 17 test có 16 PASS/1 FAIL do encoding assertion tiếng Việt bị đổi khi chỉnh file test; đã phục hồi encoding và chạy lại toàn bộ 5 report tests cùng integration: 6/6 PASS, 0 FAIL/error/SKIP. Test schema đối chiếu đủ tên/kiểu cột của cả ba bảng v2 qua analyzer; approval v1 bị chặn, contract v2 đúng điều kiện được nhận ở D07 nhưng D06 vẫn BLOCKED. Real D07 ALL JOBS có n_min=n_max=29.793 và eligible=36.059; equality posted×factor=normalized được kiểm cả min/med/max. Không ghi quantile tables production. Checksum payload D05/D07 sau thực thi vẫn PASS; pinned files A05 v0.1.2 khớp release. [Audit kiểm thử](../data/audit/tv2_q07_contract_v2_20261020.json); log chi tiết tại `tmp/q07_contract_v2/{tests.txt,integration_tests.txt}`.
