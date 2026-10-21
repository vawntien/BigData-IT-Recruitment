# Q01 — kiểm kê Data Contract bàn giao TV3

Ngày 21/10/2026; branch `feat/tv2-analysis`, HEAD `8323b5b9f4025ec4909ead912aafbef6c5825e6c`. Chỉ kiểm kê Q01; không chạy D06/analyzer/classifier, không tạo số liệu, không sửa pipeline, không commit/push. PASS bên dưới là bằng chứng log đã lưu, không phải test chạy mới.

**Kết luận: VERIFIED implementation/contract candidate; PENDING production output và taxonomy provenance của population thực.** Tiếp nhận trạng thái người bàn giao cung cấp: A04 v0.2.2 ACCEPT WITH CONDITIONS, D06 schema 27 fields đã duyệt, D06 Full chưa chạy. Tài liệu readiness trong snapshot còn ghi acceptance/schema approval pending; đó là trạng thái cũ, không dùng để phủ nhận cập nhật này và cũng không dùng schema approval làm bằng chứng Full đã chạy.

## 1. File thực tế

- Schema đầu ra Q01 tồn tại: `config/tv2_analysis_output_schema.json:1–18`; Q01 nằm chung entry `q01_role_groups, q02_experience, q03_location, q04_work_type`. Trạng thái file: `CANDIDATE_NOT_SPARK_VALIDATED`. Không có contract Q01 riêng được tìm thấy trong lần kiểm kê.
- Input contract analyzer: `config/tv2_analysis_inputs.example.json:1–16`; `group_column=primary_group_code`, `it_jobs=null`, `d06_confirmation=null`. Đây là template chưa bind input.
- Implementation: `src/a06_a08_spark_analysis.py:124–158,216–226`.
- Schema D06 thực có trong handoff: `data/handoff/tv1/TV1_Handoff_D05_D07/D06_Status/schema.json`. Đây là schema D06, không phải schema aggregate Q01; xem README cùng thư mục:8–13 và `official_readiness.md:69–84`.
- Receipt/receiving contract khác với input analyzer: `config/d06_handoff_contract.example.json`, `src/d06_handoff_validation.py`; checklist `docs/d06_full_receiving_checklist_tv2.md:23–25`. Không coi receipt template là approval đã điền.

## 2. Bảng contract ngắn gửi TV3

Logical table: **`q01_role_groups`**. Schema: `config/tv2_analysis_output_schema.json:8–18`; code chuẩn: `src/a06_a08_spark_analysis.py:150–158,220–226`.

| Cột thực tế, đúng thứ tự | Kiểu code Spark | Ý nghĩa / công thức |
|---|---|---|
| `category` | string nullable | `trim(primary_group_code)` qua alias nội bộ `a02_group`; chuỗi rỗng → NULL; giữ bucket NULL |
| `job_count` | bigint | `countDistinct(job_id)` trong category |
| `denominator_all_it` | literal int hoặc bigint theo giá trị N | N = số dòng D06 đã qua kiểm tra unique job_id và ACCEPT/true; tương ứng B của toàn population hiện có |
| `denominator_known` | literal int hoặc bigint theo giá trị K | K = số job có category khác NULL |
| `share_all_it` | double nullable | `job_count / N`; fraction 0–1, UI nhân 100 đúng một lần |
| `share_known` | double nullable | `job_count / K` chỉ khi category khác NULL và K > 0; bucket NULL luôn NULL |

Schema tĩnh ghi các count/denominator là `integer`, đồng thời giải thích int/long và countDistinct là bigint (`schema:6,12–16`). `F.lit(n)`/`F.lit(valid)` không cast long; không hứa denominator luôn bigint. Physical schema/readback Q01 production vẫn PENDING.

**Grain/key:** một dòng mỗi category quan sát được, kể cả tối đa một bucket NULL. `category` là khóa nhóm nullable trong từng table/run; không phải SQL primary key NOT NULL. Không có run_id/filter_id trong bảng; nếu gộp nhiều run TV3 phải giữ context bên ngoài. Không tự tạo hàng zero cho category vắng mặt.

**Mapping tên TV3:** không có cột `category_id`, `B` hoặc `share`. Nếu TV3 dùng các tên logic đó, mapping là category_id → `category` (code nhóm, không phải label), B → `denominator_all_it`, share → `share_all_it`. Đây là mapping consumer, không phải đổi tên vật lý đã triển khai. Không cộng denominator lặp giữa các hàng.

**Filter context:** aggregate marginal trên toàn D06 input đã xác nhận, trước JOIN bridge tùy chọn. Không có filter experience/location/date/category hoặc các dimension đó trong Q01 output; config `group_column` chọn cột nguồn, không phải filter population. N/B là toàn population input, chưa phải B của giao filter dashboard. Không thể tái tính category × experience × location từ bảng marginal; filter động và denominator theo filter còn PENDING. Bằng chứng `analyze_frames:218–226` và template input.

## 3. Membership, Unknown, overlap/disjoint

VERIFIED từ code/config, chưa xác minh trên D06 Full:

- `validate_d06:133–147` yêu cầu job_id bigint, unique/non-NULL; description/group/version/hash string; is_it boolean; mọi dòng phải `it_decision=ACCEPT` và `is_it=true`, provenance không rỗng và chỉ một cặp version/hash. REVIEW/REJECT trong input làm **fail toàn input**, không được analyzer tự lọc hay đổi thành Unknown. D06 rỗng cũng fail.
- `IT_OTHER` là nhóm IT hợp lệ khi chỉ có bằng chứng general IT; vẫn tính vào N, K và hai share. Không đồng nhất với thiếu nhóm. Config candidate `config/versions/it_taxonomy_v0.2.2.json:311–360`; classifier `src/it_taxonomy.py:185–200`.
- Unknown theo missing bucket: chỉ NULL hoặc chuỗi trim rỗng → NULL (`analyzer:124–126,154–158`). **Literal `Unknown`, `UNKNOWN`, `N/A` không được chuẩn hóa thành NULL**; code hiện coi chúng là category known. Analyzer không kiểm membership category theo danh sách taxonomy; cần upstream bảo đảm code nhóm hợp lệ.
- Overlap trong bằng chứng nghề được classifier giữ ở `candidate_group_codes`, thêm `MULTIPLE_GROUP_CANDIDATES`; chọn đúng một primary theo evidence tier → group priority → rule priority → rule_id. Không explode candidate groups cho Q01 (`it_taxonomy.py:170–187,211`; config candidate:340–346).
- Positive và exclusion cùng khớp → REVIEW, is_it=NULL; không nhập population Q01. REVIEW không là REJECT (`it_taxonomy.py:179–184,211`; config:323–339,360).
- Vì Q01 group một scalar primary trên unique job_id nên các bucket, gồm NULL, **disjoint theo cách biểu diễn**: tổng job_count=N, tổng share_all_it=1 (sai số floating point); tổng nhóm known=K; tổng share_known=1 khi K>0. Đây là hệ quả code, không phải phép kiểm overlap/full-population đã PASS. Không có cột/chế độ `overlap` hoặc `disjoint` trong output.
- Nếu K=0, share_known toàn NULL; N=0 bị validator từ chối. Missing không tự đổi thành IT_OTHER; subtype SOFTWARE_OTHER không được tự dùng thay primary.

## 4. Version/hash thực sự dùng

**VERIFIED:** analyzer không load `config/it_taxonomy.json` hay snapshot v0.2.2, không chạy classifier. Nó dùng nhãn và cặp `taxonomy_version`/`taxonomy_sha256` đã có trong D06 (`analyzer:133–145,305,321`). Manifest sau run ghi chính cặp đó. Validator analyzer chỉ kiểm một cặp không rỗng; không đối chiếu hash với approved snapshot, không kiểm định dạng SHA-256 hoặc classifier code hash. Receiving/approval evidence vẫn cần trước production.

Hash bytes config tính trực tiếp trong lần kiểm kê:

| Artifact | Config version | SHA-256 |
|---|---|---|
| `config/it_taxonomy.json` | 0.2.0 | `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d` |
| `config/versions/it_taxonomy_v0.2.2.json` | 0.2.2 | `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874` |

Classifier/release A04 v0.2.2 không đồng nghĩa active config đã đổi sang 0.2.2. `taxonomy_version` lấy từ JSON và `taxonomy_sha256` là hash bytes JSON (`src/it_taxonomy_v010.py:25–30`, được interpreter mới kế thừa); chúng không phải hash code classifier/runtime package. `docs/a04_filter_fix_round2_report.md:5` cũng phân biệt active với candidate. D06 readiness mô tả candidate 0.2.2 (`D06_Status/README.md:9`), nhưng **cặp taxonomy thực tế của Q01 production vẫn PENDING**: chưa có Full input/output/receipt và manifest Q01 thành công. Không suy từ tên release hoặc schema đã duyệt.

## 5. Test nào đã PASS; giới hạn bằng chứng

| Trường hợp Q01 liên quan | Trạng thái và bằng chứng |
|---|---|
| Bảo toàn tổng job_count Q01 | PASS lịch sử: `tmp/tv2_d05_receipt_457f90ae/data_only_tests01/tests.txt:2`; test `tmp/tv2_d05_receipt_457f90ae/test_data_only.py:37–44`, chỉ assert N và tổng count; fixture ba dòng có SOFTWARE/DATA_AI tại:23–27 |
| Duplicate input job_id bị từ chối | PASS lịch sử: cùng log:3; implementation test `src/test_a05_a11_integration.py:163–165`, được alias tại data-only test:33 |
| Suite integration cũ | `data/analytics/tv2_a05_a11_followup01/test_results.json:8–17` ghi SKIP real D06 và Spark fixtures; không đổi SKIP này thành PASS vì có log data-only về sau |
| Full end-to-end | PENDING/SKIP; `src/test_a05_a11_integration.py:185–195` cần TV2_OFFICIAL_CONTRACT; chưa có bằng chứng chạy với D06 Full |

Không tuyên bố suite data-only toàn bộ PASS: log ghi 5 tests, 1 FAIL ở A05 nested array nullability (không phải Q01). Giữ nguyên sự khác nhau giữa PASS từng ca và kết quả toàn suite.

Chưa tìm thấy bằng chứng test Q01 chuyên biệt PASS cho: NULL/blank/literal Unknown, IT_OTHER, K=0, shares từng bucket, exact output schema/Parquet readback Q01, category invalid, taxonomy approved-hash mismatch/mixed versions, REVIEW/REJECT và overlap/disjoint trên Full, giao filter và đổi mẫu số B. Các nhánh có code guard không tự được coi là test PASS. Lần kiểm kê này không chạy fixture hay tạo số liệu IT.

## 6. Artifact/output và việc còn chờ

**VERIFIED:** manifest thật tồn tại tại `data/analytics/tv2_a05_a11_followup01/analysis/manifest.json:20–27,96`: Q01 `BLOCKED_DEPENDENCY`, denominator/coverage NULL, tables rỗng; environment spark_executed=false tại:17. Hai manifest `data/analytics/tv2_a05_a11_20261019/analysis/manifest.json` và `data/analytics/tv2_a06_a11_prepared_20261019/manifest.json` cũng blocked. Tìm đệ quy file `q01*` trong data không thấy bảng Q01 thực.

Code dự định ghi `<--output>/q01_role_groups.parquet` và `<--output>/q01_role_groups.csv`, kèm `<--output>/manifest.json` có row counts/hash (`analyzer:322–335`). Đây là quy tắc đặt tên **chưa phải artifact đã bàn giao**; không có đường dẫn production cụ thể để giao TV3 hiện tại. Manifest có run_kind OFFICIAL nhưng status BLOCKED không phải production SUCCESS.

**PENDING trước bàn giao physical contract:** D06 Full + reconciliation/receipt/approved provenance thực; xác nhận nối D06 classification schema với các thuộc tính job mà analyzer cần; khóa taxonomy config/hash và classifier code/package provenance; chạy Q01 trên input đã nhận; kiểm physical schema/hash/readback và invariants; chốt capability filter/denominator với TV3. A04 conditional acceptance và schema approval không thay thế các bằng chứng này.
