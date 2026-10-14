# A04 – Bàn giao candidate v0.2.2 cho TV1 trước D06

Ngày lập **14/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`. Candidate bàn giao **v0.2.2**, `schema_version=1`, processor `structured-source-v1`; **active vẫn v0.2.0**. Chưa chuyển candidate thành mặc định, chưa xác minh parity Spark/JVM hoặc tích hợp D06. A04 được đề nghị **“Sẵn sàng rà soát nghiệm thu”**, chưa tự ghi hoàn thành/100%, người/ngày nghiệm thu.

Kết quả, mẫu số, đối chiếu tiêu chí và toàn bộ hàng đợi theo job_id nằm trong [a04_final_report.md](a04_final_report.md). Các giới hạn bàn giao: 5 FN, 33 REVIEW duy nhất (17 CNTT/16 NGOAI_CNTT), 3 bất đồng nhóm, 9 bất đồng subgroup; 4 CHUA_RO đã duyệt giữ riêng. Không coi REVIEW là FN/ngoài CNTT và không áp dụng nhãn thủ công làm override classifier.

## 1. Bộ hiện vật và định danh bằng SHA-256

Hash dưới đây là SHA-256 **exact bytes**, đã đối chiếu với file hiện hành và [run_manifest.json](../data/analytics/a04_taxonomy_v0_2_2_20261014/run_manifest.json). Hash config không phải hash JSON sau parse/reserialize.

[.gitattributes TV2](../.gitattributes) giữ exact bytes bằng `-text` cho các hiện vật TV2, tránh `core.autocrlf` đổi CRLF/LF làm lệch hash khi stage/checkout. Quy tắc whitespace nhận CRLF là line ending và vẫn kiểm tra khoảng trắng thừa; riêng `src/it_taxonomy.py` giữ một dòng trắng cuối file đã có để bảo toàn hash interpreter. Khi chuyển hiện vật cho TV1 cần giữ nguyên bytes thay vì tự đổi newline.

| Config | Vai trò | SHA-256 |
| --- | --- | --- |
| [config/versions/it_taxonomy_v0.2.2.json](../config/versions/it_taxonomy_v0.2.2.json) | Candidate phải chỉ định rõ | `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874` |
| [config/it_taxonomy.json](../config/it_taxonomy.json) | Active v0.2.0 | `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d` |
| [config/versions/it_taxonomy_v0.2.0.json](../config/versions/it_taxonomy_v0.2.0.json) | Snapshot v0.2.0 | `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d` |
| [config/versions/it_taxonomy_v0.2.1.json](../config/versions/it_taxonomy_v0.2.1.json) | Candidate baseline round 2 | `efedfeeeb090808923f3ad47a27988f90436153f6e5f70610d48ff19c14773b9` |

Code/test dùng cho kết quả candidate, tất cả trong `src/`:

| Đường dẫn | Vai trò | SHA-256 |
| --- | --- | --- |
| [it_taxonomy.py](../src/it_taxonomy.py) | Interpreter/API v0.2, nhận v0.2.0/0.2.1/0.2.2 | `841231033c546cc2bedf141386038104c0a0f1cf9f5a01b80535457c8b42312f` |
| [description_processing.py](../src/description_processing.py) | Parser, section/actor, source mapping, long-unit windows | `ad579397753f2de115faad3bf9ff4d1c8dfebf5ce76eb898f3368ca02a6fec78` |
| [it_taxonomy_v010.py](../src/it_taxonomy_v010.py) | Lớp nền normalization/schema và implementation v0.1.0 đóng băng | `453bb6bcd22d4cdf866c670f3634b8f1e42a233eb086b650e579b4b1d429dc86` |
| [tv2_csv.py](../src/tv2_csv.py) | Khóa integral canonical/CSV/hash | `7839763017c281c36126b8ece9c2015da41b54cccdfca0f365ac4feb48beb903` |
| [a04_filter_fix_round2.py](../src/a04_filter_fix_round2.py) | Runner stage/controls/delta round 2 đã lưu | `339f475b561f481f03a31da190abb5997f2899bf75aae14bb89a35a44de1c508` |
| [a04_filter_fix_round1.py](../src/a04_filter_fix_round1.py) | Runner/controls/helpers round 1 được round 2 dùng | `47364d4a60b11eaf07894fd02603725684e1c33626cc52814982f0f3aee49433` |
| [test_a04_round2.py](../src/test_a04_round2.py) | Fixture integration/migration/IT delivery và provenance | `cd6866d6c278a9106f2528fdce9bac75c4ad4732d96599e40cab82317edbca65` |
| [test_a04_round1.py](../src/test_a04_round1.py) | Fixture heading/P2, priority/blockers | `4a3b5711ba278ff52ebdcbfc9df2fd7b34f36caa125fe1e9651ac1a3118dc556` |
| [compare_a04_versions.py](../src/compare_a04_versions.py) | Helpers đối chiếu/evidence, runner lịch sử | `14d60b2bd9a3ec17d0a3e6a196ab0b4d24e8ca55df13540bafdbc45bad88504c` |
| [prepare_a04.py](../src/prepare_a04.py) | Helpers và runner lấy mẫu lịch sử | `57e0886673643fece40bfa0b9ab26a178f914eaa8f7d4f045d7254a85bc81427` |
| [apply_a04_decisions.py](../src/apply_a04_decisions.py) | Helpers đọc workbook, nguồn nhãn đã duyệt | `bd4d918bed2568f58cadd5347bfba56f38469fabd7151bf87e60ee545cd57676` |

Fixture nền bổ sung: [test_a04_v020.py](../src/test_a04_v020.py), hash `e1955f4456d0aaa8be276bd0343146763eb1da5655e02c3338f5815381a84a15`; [test_tv2_a04.py](../src/test_tv2_a04.py), hash `4e6372138d88bed81da42ad6c8529bfeb02f0771b1732bf2152dfd83b4ab7117`. [test_a04_segmentation.py](../src/test_a04_segmentation.py), hash `6341dfdce2ecd2790fa4c5cd4f77216819a3a8b78c676c6774c3a068560e5a8e`, mô tả hành vi **legacy v0.1.0**, không dùng kỳ vọng “bỏ đoạn dài” đó làm hợp đồng candidate structured.

Hiện vật đầu ra dưới `data/analytics/a04_taxonomy_v0_2_2_20261014/`:

| Hiện vật | Nội dung | SHA-256 |
| --- | --- | --- |
| [all_predictions.jsonl](../data/analytics/a04_taxonomy_v0_2_2_20261014/all_predictions.jsonl) | 176 job_id duy nhất, prediction candidate đầy đủ | `1c4c8b8d3ab00238e908e834ca615ba4188b6d03858cb5e38648f1565d03266d` |
| [seed42_v022_predictions_private.jsonl](../data/analytics/a04_taxonomy_v0_2_2_20261014/seed42_v022_predictions_private.jsonl) | 160 tin chính, thêm sample_id | `4350bfcd4b479fee226a450e0ee6fa7456f854b910577cf99ac6cd598b229295` |
| [supplement17_v022_predictions_private.jsonl](../data/analytics/a04_taxonomy_v0_2_2_20261014/supplement17_v022_predictions_private.jsonl) | 17 bổ sung, có một ca chung với mẫu chính | `b4cdb7515a40b9f77eb78ded7b20b7ad6d76778418e3b39ba4925d7a84fe9691` |
| [baseline/source_rows.json](../data/analytics/a04_taxonomy_v0_2_2_20261014/baseline/source_rows.json) | Full text + nhãn/metadata 160/17 đóng băng | `4fa5a35a5e06f1bb676833ba698cb6b2a96c5f2ff6a49b99f2e3214e216b0c14` |
| [run_manifest.json](../data/analytics/a04_taxonomy_v0_2_2_20261014/run_manifest.json) | Hash code/output/stage, Python, phạm vi và bảo toàn | `4d4aac5d52c1f98e656b0a2fb376712aabc580cbdb75bedf6d4c34df4ca3d3e8` |

Nguồn nhãn hiện hành: [workbook 160](../data/analytics/a04_manual_seed42/a04_manual_labels_filled.xlsx), hash `bbe53db071a75478705c8be3b692356c896018bd20dfac40aebc489d97d305a2`; [workbook 17](../data/analytics/a04_taxonomy_v0_2_0_20261008/accept_downgrades_for_review_blind.xlsx), hash `7951c40d59271b58e1ca8d33e0e97c8f83a29c069be39cc6813826e6897cfe09`. Các workbook khớp snapshot source_rows; ca chung `3905848702` khớp nhãn và prediction.

Giữ cả [baseline manifest](../data/analytics/a04_taxonomy_v0_2_2_20261014/baseline/manifest.json), [comparison_summary](../data/analytics/a04_taxonomy_v0_2_2_20261014/comparison_summary.json), [job_comparison.csv](../data/analytics/a04_taxonomy_v0_2_2_20261014/job_comparison.csv), [stages](../data/analytics/a04_taxonomy_v0_2_2_20261014/stages/) và audit [tv2_a04_filter_fix_round2_20261014.json](../data/audit/tv2_a04_filter_fix_round2_20261014.json). Nhiều hiện vật `data/analytics/` bị Git ignore; TV1 cần nhận chúng cùng manifest, không chỉ hai file Markdown. Không dùng một commit hash làm định danh đủ cho các hiện vật local này.

## 2. Cách sử dụng và tái lập có giới hạn

Môi trường đã tạo kết quả: `.venv/Scripts/python.exe`, **Python 3.11.9**, thư viện chuẩn. API là `it_taxonomy.Taxonomy(config_path).classify(title, description, job_id=None)`; trong Spark/Python có thể nạp một instance mỗi worker với đường dẫn candidate/version/hash đã xác minh. Chỉ truyền title/description và job_id để định danh; không truyền nhãn, ngành, company hoặc skills làm quyết định. Job_id đổi không được đổi prediction nghề.

Đọc kết quả hiện có là đủ cho lượt bàn giao này. Khi TV1 cần tái lập 176 khóa để làm mốc parity, chạy ví dụ sau **tại root repository bằng PowerShell**, dùng frozen source và tạo output riêng trong `tmp/`. Ví dụ này là hướng dẫn cho lần kiểm tra của TV1; **không được thực thi trong lượt tổng hợp hồ sơ**:

```powershell
@'
import hashlib
import json
import sys
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root / "src"))
from it_taxonomy import Taxonomy

run = root / "data/analytics/a04_taxonomy_v0_2_2_20261014"
config = root / "config/versions/it_taxonomy_v0.2.2.json"
model = Taxonomy(config)
assert model.version == "0.2.2"
assert model.sha256 == "1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874"
frozen = json.loads((run / "baseline/source_rows.json").read_text(encoding="utf-8"))
inputs = {}
for rows in frozen.values():
    for row in rows:
        job = row["job_id"]
        pair = (row["title"], row["description"])
        assert job not in inputs or inputs[job] == pair
        inputs[job] = pair
assert len(inputs) == 176
expected = {}
for line in (run / "all_predictions.jsonl").read_text(encoding="utf-8").splitlines():
    record = json.loads(line)
    assert record["job_id"] not in expected
    expected[record["job_id"]] = record
assert set(expected) == set(inputs)
records = []
for job in sorted(inputs, key=int):
    title, description = inputs[job]
    result = model.classify(title, description, job)
    result.update(title=title, description=description,
        source_title_sha256=hashlib.sha256(title.encode("utf-8")).hexdigest(),
        source_description_sha256=hashlib.sha256(description.encode("utf-8")).hexdigest())
    assert result == expected[job], job
    records.append(result)
output = root / "tmp/a04_tv1_v022_parity.jsonl"
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("x", encoding="utf-8", newline="\n") as stream:
    for record in records:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
print("176/176 exact Python predictions matched; output:", output)
'@ | .\.venv\Scripts\python.exe -B -
```

Output dùng chế độ `x` để từ chối ghi đè; nếu đã có file đó, TV1 chọn tên output mới. So nội dung theo job_id, không yêu cầu hash JSONL mới bằng trace vì thứ tự/serialization có thể khác. Hash nguồn và config vẫn phải exact. Các runner round 1/2 là bằng chứng lịch sử, dùng đường dẫn cố định và từ chối ghi đè; chúng **không có tham số `--output`**. Không chạy `--prepare`/main của chúng trên thư mục kết quả đã lưu. `prepare_a04.py` có đường chạy toàn tập/lấy mẫu, không dùng đường chạy đó để làm parity bộ 176 khóa này.

## 3. Hợp đồng output và nullability

Grain đề xuất D06: **một dòng/mỗi job_id non-null duy nhất**. Python trả job_id dạng chuỗi số canonical, kiểm tra phạm vi signed 64-bit qua `tv2_csv.integer_key`; Spark chuyển sang `bigint` có kiểm tra lỗi/null/duplicate. Đọc CSV bằng parser hỗ trợ quote/multiline, không split thủ công. Giữ nguyên title/description sau CSV parse và hash UTF-8; không trim/normalize lại raw để lưu.

`proposed_output_contract` trong JSON vẫn ghi `proposal_pending_TV1_confirmation`: bảng sau là hợp đồng hành vi Python hiện có và kiểu Spark **đề xuất**, TV1 phải chốt schema nested/storage/canonical trước D06.

| Trường | Kiểu Spark đề xuất | Nullable và ý nghĩa |
| --- | --- | --- |
| job_id | bigint | Không null; khóa chuẩn từ input. API chỉ thêm trường khi được truyền job_id. |
| taxonomy_version, taxonomy_sha256 | string | Không null; `0.2.2` và exact config hash cho candidate. |
| it_decision | string | Không null; ACCEPT/REJECT/REVIEW. |
| is_it | boolean | Nullable; ACCEPT=true, REJECT=false, REVIEW=NULL. |
| primary_group_code | string | Nullable; một nhóm khi ACCEPT (có thể IT_OTHER); NULL khi REJECT/REVIEW. |
| subgroup_code | string | Nullable; chỉ có một subgroup khi ACCEPT/SOFTWARE, còn lại NULL; fallback SOFTWARE_OTHER. |
| candidate_group_codes | array<string> | Mảng không null, có thể rỗng; nhóm chuyên môn distinct theo thứ tự chọn, vẫn lưu khi conflict REVIEW. |
| selected_rule_id | string | Nullable; include/general thắng khi ACCEPT, NULL khi REJECT/REVIEW. |
| reason_codes | array<string> | Không null; thứ tự có ý nghĩa, unique theo lần xuất hiện; lý do chính và cờ diagnostic. |
| matched_rule_ids | array<string> | Không null, có thể rỗng; mọi rule include/general/exclusion/subgroup khớp, sort theo rule_id. |
| match_evidence | array<struct> | Không null, có thể rỗng; giữ đầy đủ provenance ở mục 5, không chỉ sáu field của struct sơ bộ trong JSON. |
| description_processing | struct | Không null; phiên bản parser, source/derived hash, coverage và incomplete diagnostics. |
| description_segments | array<struct> | Không null; giữ full derived units cùng section/actor/status/raw_ranges. |

Trace lưu còn có `title`, `description`, `source_title_sha256`, `source_description_sha256` do wrapper thêm; trace chính 160 thêm `sample_id`. Các trường này không phải rule input phụ hoặc nhãn nghề. REJECT có thể có exclusion evidence; REVIEW do conflict vẫn có candidates/rules/evidence dù nhóm thắng và is_it là NULL. Arrays rỗng `[]`, NULL và chuỗi rỗng không được trộn trong Spark; manual_is_it trống của CHUA_RO là trạng thái nhãn riêng, không phải output machine REVIEW.

`DESCRIPTION_PROCESSING_INCOMPLETE` có thể đi kèm ACCEPT/REJECT nếu đã có bằng chứng/rule đủ mạnh. Không ép mọi incomplete thành REVIEW hoặc mọi REVIEW thành false. Giữ hàng REVIEW riêng để đối soát; TV1 cần chốt chính sách lưu chúng và phạm vi bảng CNTT được chọn, không âm thầm tính chúng là REJECT.

## 4. Rule language, ngữ cảnh và ưu tiên

Schema 1 dùng `all`, `any`, `match`, `full_match`, `same_segment`, `is_missing`; dùng cùng term_sets/conditions trong candidate JSON. `any` thu evidence từ **mọi nhánh đúng**, không dừng sau nhánh đầu; `all` đòi đủ mọi điều kiện. Không dùng keyword list riêng trên JVM.

Normalization: NFC → lower, nhận missing tokens trước replacement, không bỏ dấu; dash/slash thay bằng space, collapse whitespace theo config, giữ punctuation `+`, `#`, `.`. Literal phrase có Unicode token boundary chữ/số/underscore, không substring tùy ý, không stemming hoặc chèn từ giữa phrase. Standalone IT, ngành/skills/company metadata không cấp membership.

Parser structured hỗ trợ HTML/block tags/entities, loại script/style, newline/bullet, bảo vệ URL/.NET/version/abbreviation. Heading chỉ explicit được cấu hình, standalone hoặc colon với boundary hợp lệ; không bật heading implicit dính chữ. Eligible sections UNKNOWN/ROLE/RESPONSIBILITIES vẫn qua actor checks; COMPANY/QUALIFICATIONS/COMPENSATION/BENEFITS/EEO không cấp task positive. Không tách comma/and hoặc nối task/object từ unit/section khác nhau.

`same_segment` cần đủ term_sets cùng một unit/cửa sổ eligible, giữ actor, negation, collaboration trước task và chủ thể công ty/đội khác. Unit dài được giữ toàn văn; cửa sổ **500 Unicode code point sau normalization**, task anchor và self cue/task-led clause theo policy. 500 không phải byte/word/UTF-16 length; không chia cứng hoặc xóa phần dài. Không có automatic evidence nếu không map được raw.

Thứ tự quyết định:

1. Thu include/general và exclusion; có positive + exclusion → REVIEW/POSITIVE_EXCLUSION_CONFLICT, chỉ exclusion → REJECT/OUTSIDE_IT_ROLE.
2. Có nhóm chuyên môn → ACCEPT và chọn theo `(evidence_tier_rank, group.priority, rule_priority, rule_id)` tăng dần; nhiều ứng viên không tự thành REVIEW, giữ cờ MULTIPLE_GROUP_CANDIDATES.
3. Chỉ general IT → ACCEPT/IT_OTHER. Không general fallback khi đã có nhóm chuyên môn.
4. Không có positive/exclusion: title missing/ambiguous hoặc xử lý mô tả incomplete → REVIEW; còn lại REJECT/NO_IT_ROLE_EVIDENCE.
5. Chỉ sau khi nhóm thắng SOFTWARE mới xét subgroup, sort `(tier_rank, subgroup.priority, rule_priority, rule_id)`; không có subgroup match → SOFTWARE_OTHER.

Tier: TITLE_DIRECT=10, TITLE_CONTEXT=20, DESCRIPTION_ROLE_TASK=30. Group priority: SECURITY=10, DATA_AI=20, DEVOPS_CLOUD=30, QA_TESTING=40, NETWORK_SYSTEMS=50, SOFTWARE=60, IT_SUPPORT=70, IT_BUSINESS=80, IT_MANAGEMENT=90, IT_OTHER=999. Tier đứng trước group priority. Subgroup priority: MOBILE=10, WEB=20, OTHER=90; giữ rule_priority/rule_id theo JSON, không theo thứ tự array/partition.

`*_CONTEXT` giữ title hint + task/context cùng unit. `*_DESCRIPTION` chỉ mở khi title thiếu hoặc **toàn title** khớp generic_exact_titles, rồi cần role/task/context/self cue cùng unit; không là fallback tự do cho mọi title. P3 integration cần workflow và software object; maintenance cần coding-role hint và software environment; migration Web cần cả client/server origin và Web target cùng unit; IT delivery cần IT epic/information-system object và planning/deployment context. Programmer không direct-title; product-only/qualification/general Scrum chưa đủ ACCEPT. Candidate giữ P1b/P4/P5/PACS/ECC ngoài phạm vi sửa đã triển khai.

## 5. Evidence, raw ranges và nested schema cần giữ

Mọi hit có `rule_id`, `field`, `term_set_id`, `matched_alias`, `segment_index`, `excerpt`, `raw_excerpt_start/end`, `raw_match_ranges`, `raw_offset_unit`, `normalized_start/end`, `normalized_coordinate_space`, `mapping_status`, `excerpt_covers_all_match_ranges`. Description hit còn có `derived_start/end`, `derived_coordinate_space`, `derived_matched_text`, `section`, `actor`; title không có các field derived/section/actor này và segment_index=NULL. Nested Spark struct phải cho phép các field chỉ có ở description là nullable; index/range dùng integer, ranges là danh sách cặp `[start,end]`.

- `raw_offset_unit=original_field_unicode_codepoints_half_open`: `[start,end)` trong **title hoặc description gốc sau CSV parse**, không phải offset trong file CSV/bytes/chuỗi HTML đã parse. `raw_match_ranges` có thể nhiều khoảng do HTML/entity/NFC/source mapping; giữ mọi khoảng theo thứ tự.
- `excerpt == raw[raw_excerpt_start:raw_excerpt_end]`, tối đa 240 code point; excerpt là lát nguồn thật và có thể chứa HTML/entity. Không đòi alias normalized xuất hiện nguyên văn trong excerpt. Nếu `excerpt_covers_all_match_ranges=false`, tra full raw theo ranges, không bỏ các hit ngoài excerpt.
- `normalized_coordinate_space` là normalized_title hoặc normalized_segment; với description normalized offsets thuộc unit, derived offsets thuộc parser_text. Không dùng chúng thay raw offsets. `mapping_status=MAPPED_TO_RAW` là bằng chứng map hit, không suy diễn raw từ text đã collapse.
- Python đếm code point; JVM `String`/regex offsets dùng UTF-16 code unit. Đổi mỗi raw code point boundary sang UTF-16 bằng `raw.offsetByCodePoints(0, boundary)` trước `substring`; khi xuất so với Python cần chuyển ngược về code point. Emoji/non-BMP, dấu tổ hợp NFC, HTML `&#47;`/`&amp;` phải giữ mapping nhiều bước.

`description_segments` giữ `index`, `text`, `derived_start/end`, `raw_ranges`, `normalized_characters`, `section`, `actor`, `blocked_reasons`, `kind`, `long`, `explicit_self`, `status`, `mapping_available`; `window_diagnostics` có thể xuất hiện tùy đường evaluate. `text` là derived unit, không nhất thiết nguyên một lát raw liên tục. Không lưu normalized unit thay full text; không bỏ window/blocker diagnostics khi chúng có trong trace.

`description_processing` giữ `version`, `parser`, source_sha256/derived_sha256, units/retained_long_units/unresolved_units, legacy_oversize_* diagnostics, parser_issues, removed_source_ranges, source_mapping_available, incomplete, dropped_oversize_units và raw_offset_unit. Source hash phải khớp description nguyên bản UTF-8; `dropped_oversize_units=0` trong processor hiện tại. Phần struct sơ bộ trong JSON chưa diễn tả hết các field này; TV1 chốt nested schema từ JSONL thực tế, kiểm tra cast/nullability và giữ provenance khi viết canonical/Parquet.

## 6. Fixture và mốc parity Spark/JVM

Bằng chứng Python đã lưu: [tests_result.json](../data/analytics/a04_taxonomy_v0_2_2_20261014/tests_result.json) **46 test qua, 0 failure/error/skip**, [log](../data/analytics/a04_taxonomy_v0_2_2_20261014/tests_round2.log); round 1 có 38 test qua. [saved_output_verification](../data/analytics/a04_taxonomy_v0_2_2_20261014/saved_output_verification.json) và [independent_verification](../data/analytics/a04_taxonomy_v0_2_2_20261014/independent_verification.json) kiểm tra đầu ra/phép tính, không là đánh giá trên mẫu độc lập. Không chạy lại trong lượt chỉ tổng hợp này.

| Fixture cần chuyển/kiểm tra | Nguồn | Kỳ vọng parity cần xác nhận |
| --- | --- | --- |
| Heading explicit, barrier qualification/benefits, role reset; implicit heading không bật | test_a04_round1.py; controls round 1 trong [runner](../src/a04_filter_fix_round1.py) | Cùng unit/section/actor/blocker; không nhận task ở qualification/company. |
| ETL/cyber/SDE/database task-object-context | test_a04_round1.py; [stages round 1](../data/analytics/a04_taxonomy_v0_2_1_20261014/stages/) | Chỉ nhận positive đủ title hint/SAME_SEGMENT; weak context/reporting/product-only không ACCEPT. |
| Integration workflow + software object, HR/accounting/product-only/qualification/company/collaboration/negation/cross-unit/no hint | test_a04_round2.py; run_controls/controls trong [runner round 2](../src/a04_filter_fix_round2.py) và [stage integration](../data/analytics/a04_taxonomy_v0_2_2_20261014/stages/01_P3_INTEGRATION/controls.json) | Cùng decision/is_it/group/subgroup/reason/rules/candidates/evidence. |
| Maintenance và migration đủ origin/target; thiếu một phía/cross-unit/qualification Develop applications | test_a04_round2.py; [stage migration](../data/analytics/a04_taxonomy_v0_2_2_20261014/stages/02_P3_APPLICATION_MAINTENANCE_MIGRATION/controls.json) | Programmer vẫn cần task; Web từ migration role, không qualification. |
| IT epic delivery vs generic backlog/Scrum/project | test_a04_round2.py; [stage delivery](../data/analytics/a04_taxonomy_v0_2_2_20261014/stages/03_P3_IT_DELIVERY/controls.json) | IT_BUSINESS khi đủ object/context; generic Scrum không tự ACCEPT. |
| SDET/QA, Mobile trước Web, positive+exclusion CNC, group/subgroup priority không phụ thuộc array | test_a04_round1.py, test_a04_round2.py, test_tv2_a04.py | QA_TESTING/MOBILE giữ ưu tiên; conflict REVIEW và primary/is_it NULL. |
| 499/500/501 code point với emoji, NFC dấu tổ hợp, entity/client&#47;server, HTML/newline/bullets/URL/.NET | test_a04_round1.py, test_a04_round2.py, test_a04_v020.py | Cùng windows/incomplete, raw excerpts/ranges, derived/normalized coordinates; không lệch UTF-16. |
| Other actor/collaboration/negation trước task, adversative clause, retained unresolved long unit | test_a04_v020.py | Không mất blocker ở ngoài cửa sổ; không bỏ raw/long unit; không ép mọi incomplete thành REVIEW. |
| Missing tokens/schema/version không hỗ trợ; job_id khác/employer khác | test_a04_round1.py, test_a04_round2.py, test_tv2_a04.py | Fail-closed; input định danh/metadata không đổi nghề; NULL đúng hợp đồng. |
| Tất cả 176 khóa thực tế và hai trace 160/17 | frozen source_rows + all_predictions + trace mẫu ở mục 1 | Cùng mọi field prediction và source hash theo job_id; ca chung khớp; giữ 5 FN/33 REVIEW/3 nhóm/9 subgroup hiện có. |

Mỗi stage round 2 đã kiểm tra 40 control round 1, 45 control round 2 và 57 ca minh họa; fixture/code có expected semantics, controls.json lưu kết quả theo stage. TV1 cần chuyển chính xác input/expected, không chỉ so tổng ACCEPT hoặc tỷ lệ. So thứ tự arrays theo hợp đồng, exact excerpt/ranges và diagnostics; kiểu job_id được chuẩn hóa khi so Python string với Spark bigint. Không gọi lỗi nghề đã biết là lỗi parity nếu JVM khớp candidate; giữ hàng đợi nghề riêng để TV2/người rà soát chốt.

## 7. Các bước TV1 cần kiểm tra trước tích hợp D06

1. Nhận đủ config/code/test/frozen source/trace/stage/manifest; kiểm tra exact hash và version, xác nhận active v0.2.0. Ghi nhận candidate là bộ được thử riêng, việc chọn cấu hình D06/cập nhật mặc định cần quyết định tích hợp riêng.
2. Xác nhận mapping D04/D05 canonical: job_id bigint duy nhất/non-null, title/description nguyên bản, chính sách missing/CSV multiline và nguồn hash. Chốt đường input/output/storage với TV1; không dùng metadata/skills cho membership, không ghi thêm đầu ra A05.
3. Chốt schema nested ở mục 3/5, nullable fields của REVIEW/REJECT/non-SOFTWARE và các field evidence chỉ có ở description; kiểm tra arrays rỗng, missing vs NULL và giữ nguyên raw/source ranges.
4. Chạy/port fixture trong môi trường tích hợp Spark/JVM, cùng config/hash; so toàn bộ 176 prediction với đầu ra Python đã lưu. Kiểm tra tier/priority/SAME_SEGMENT/actor/blocker và Unicode code point–UTF-16; ghi mismatch theo job_id/field, input/hash/runtime, không sửa nhãn để che mismatch.
5. Kiểm tra write/read canonical/Parquet trong output thử riêng: grain/duplicate keys, schema/nullability, version/hash, reason/candidate order, nested evidence và raw hashes không mất sau serialization. Chốt chính sách bảng ACCEPT và nơi lưu REVIEW/REJECT/diagnostics; không âm thầm coi REVIEW là ngoài CNTT.
6. Ghi kết quả parity, schema/path và giới hạn nghề còn lại thành bằng chứng tích hợp cho D06; chuyển [hàng đợi A04](a04_final_report.md) để người phụ trách xác nhận cách xử lý/chấp nhận. Sau các kiểm tra, TV1 quyết định tích hợp candidate theo quy trình D06; hồ sơ này không tự triển khai hoặc promote.

Parity/canonical thuộc D06 do TV1 chủ trì, không đồng nghĩa nghiệm thu A04 hoặc đánh giá độc lập toàn tập. Mẫu hiện tại là **mẫu phát triển đã dùng sửa/rà soát**; chưa có đánh giá độc lập toàn dataset. Người rà soát A04 vẫn cần xác nhận tiêu chí, kết quả sửa và giới hạn còn lại theo hồ sơ cuối.

Lượt bàn giao chỉ tạo hai tài liệu và kiểm tra dữ liệu/hash/liên kết. Giữ nguyên raw, nhãn/metadata, classifier/config, trace và mọi báo cáo trước; không chạy ETL/toàn dataset, không làm A05, không commit/push, không tự đổi active.
