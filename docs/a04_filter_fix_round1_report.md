# A04 – Báo cáo đợt sửa 1: P1a/P2, candidate v0.2.1

Ngày **14/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`. **Chưa nghiệm thu A04, chưa đánh giá độc lập.**

Đã triển khai đúng P1a và bốn entry P2 theo [phương án](a04_filter_fix_plan.md). Candidate ở [config/versions/it_taxonomy_v0.2.1.json](../config/versions/it_taxonomy_v0.2.1.json), SHA-256 `efedfeeeb090808923f3ad47a27988f90436153f6e5f70610d48ff19c14773b9`; `config/it_taxonomy.json` vẫn v0.2.0. P1b/P3/P4/P5 chưa triển khai. Không nhận heading implicit dính chữ, không mở fallback, không đổi tier/priority/conflict/blocker.

## Baseline và bảo toàn

- [Snapshot baseline](../data/analytics/a04_taxonomy_v0_2_1_20261014/baseline/manifest.json) giữ exact config/code và bản sao các dự đoán 160/17 đã lưu; [snapshot v0.2.0 trong config/versions](../config/versions/it_taxonomy_v0.2.0.json) SHA-256 `086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d`. Full trace cũ chỉ đọc hash, giữ nguyên; không chạy toàn dataset.
- Frozen nguồn đủ **160 + 17 dòng / 176 job_id**, JOIN theo job_id; ca chung `3905848702` giữ một prediction chung và nhãn hai nguồn khớp. Reviewer Dũng, ngày 2026-10-13, raw/workbook/trace/báo cáo và mọi thay đổi có sẵn giữ nguyên.
- Replay v0.2.0 trên 176 khóa khớp toàn bộ trường trả về của trace lưu, gồm decision/group/subgroup/reason/evidence/segments/processing. Code cũ được snapshot trước chỉnh sửa; file có sẵn duy nhất được sửa là `src/it_taxonomy.py`, thêm v0.2.1 vào allowlist version cho cùng processor structured-source-v1.

## Sửa đổi thực tế theo thứ tự

1. **P1a**: ROLE thêm `role description`; RESPONSIBILITIES thêm `essential duties and responsibilities`, `job duties and responsibilities`; QUALIFICATIONS thêm `qualifications and education requirements`, `required skills & experience`, `desired skills & experience`, `skills`; BENEFITS thêm `what we have to offer`, `description of benefits`, `compensation & benefits details`. Chỉ dạng explicit hiện được parser hỗ trợ (standalone/colon với boundary hợp lệ), không sửa parser. Qualification/benefits barriers được kiểm tra cùng role reset để tránh biến yêu cầu năng lực thành task.
2. **P2_ETL**: thêm đúng hai literal `creating etl pipeline`, `create etl pipelines` vào data_tasks, giữ title hint và same-unit context của DATA_AI_CONTEXT. Không thêm verb chung, không stemming và không dùng SQL/Excel đơn lẻ.
3. **P2_CYBER**: thêm `cyber incidents` vào security_context, chỉ hữu ích khi cùng task bảo mật hiện có và eligible actor/unit. Không thêm security officer/clearance làm nghề cyber.
4. **P2_SOFTWARE_TITLE**: thêm phrase `software development engineer` vào software_titles; tier/priority vẫn cũ, SDET/Software Development Engineer in Test giữ QA_TESTING.
5. **P2_DATABASE**: không thêm `oversee database management` vào data_tasks chung. DATA_AI_CONTEXT giữ title hint, còn nhánh context là ANY của nhánh cũ và SAME_SEGMENT gồm `database_admin_tasks`=`oversee database management`, object `database/databases`, context cụ thể `data storage, retrieval, and security` hoặc dạng không Oxford comma. Cả ba phải cùng eligible unit/cửa sổ với blockers cũ. Chỉ dùng schema 1 hiện có (all/any/same_segment), không thêm rule ID, tier/priority hoặc nới context chung. Weak context, reporting, company, qualification, actor khác và negation đều có đối chứng.

## Kiểm tra và delta riêng

**38 test unittest đã qua**, gồm bộ hiện hữu và fixture mới; mỗi stage có **40 control** và **57 ca minh họa**. Kiểm tra decision/is_it/group/subgroup/reason, rule candidates, raw excerpt/ranges và normalized alias, mapping và blockers. Baseline replay không đổi. Dữ liệu mỗi stage giới hạn 176 job; fixture/test là ca tổng quát và các specimen kiểm tra hiện hữu, không phải lần chạy toàn dataset.

| Stage tích lũy, so với stage trước | Job thay bất kỳ chi tiết | Job đổi trạng thái | Hồi quy FP/nhóm/subgroup/TP |
| --- | ---: | ---: | ---: |
| P1a | 22 | 0 | 0 |
| P2_ETL | 1 | 1 | 0 |
| P2_CYBER | 1 | 1 | 0 |
| P2_SOFTWARE_TITLE | 1 | 1 | 0 |
| P2_DATABASE | 1 | 1 | 0 |

Các delta lưu riêng dưới [stages](../data/analytics/a04_taxonomy_v0_2_1_20261014/stages/), mỗi thư mục có config/hash, fixtures, predictions và delta; không dùng một tỷ lệ tổng để che tác động entry riêng. Tổng cộng **4 job mới ACCEPT**; không phát hiện FP mới/đổi nhóm sai/subgroup sai hoặc mất TP trên 176 ca và controls. Không cần thu hồi hạng mục. Số bất đồng nhóm/subgroup cũ vẫn được báo theo nhãn đã duyệt, không sửa nhãn để khớp máy.

## Kết quả tính lại trước/sau

JOIN từng workbook với prediction theo job_id, tính từ dữ liệu; CHUA_RO giữ riêng, REVIEW không biến thành REJECT/FN. Tỷ lệ khớp khi máy quyết định dùng nhãn rõ và ACCEPT/REJECT; độ phủ nhãn rõ dùng cùng số ca chia CNTT+NGOAI_CNTT. Tỷ lệ quyết định đúng trên nhãn rõ tính REVIEW là chưa tạo quyết định đúng; precision/recall có điều kiện loại REVIEW/CHUA_RO. Đây là **mẫu phát triển đã dùng sửa/rà soát**, không accuracy toàn dataset hoặc đánh giá độc lập.

### Mẫu chính 160

| Đại lượng | v0.2.0 | v0.2.1 candidate |
| --- | --- | --- |
| TP | 76 | 77 |
| TN | 51 | 51 |
| FP | 0 | 0 |
| FN | 5 | 5 |
| REVIEW | 24 | 23 |
| CHUA_RO | 4 | 4 |

| Tỷ lệ, mẫu số | Trước | Sau |
| --- | --- | --- |
| Khớp membership khi máy quyết định | 127/132 = 96.21% | 128/133 = 96.24% |
| Độ phủ trên nhãn rõ | 132/156 = 84.62% | 133/156 = 85.26% |
| Độ phủ trên toàn mẫu | 136/160 = 85.00% | 137/160 = 85.62% |
| Quyết định đúng trên nhãn rõ | 127/156 = 81.41% | 128/156 = 82.05% |
| Precision trên ACCEPT nhãn rõ | 76/76 = 100.00% | 77/77 = 100.00% |
| Recall có điều kiện trên ACCEPT/REJECT | 76/81 = 93.83% | 77/82 = 93.90% |
| ACCEPT trên tất cả CNTT duyệt | 76/90 = 84.44% | 77/90 = 85.56% |
| Khớp nhóm trên ACCEPT/CNTT | 73/76 = 96.05% | 74/77 = 96.10% |
| Khớp subgroup khi cả hai nhóm SOFTWARE | 29/38 = 76.32% | 29/38 = 76.32% |

**Ma trận candidate**

| Máy candidate | CNTT | NGOAI_CNTT | CHUA_RO | Tổng |
| --- | ---: | ---: | ---: | ---: |
| ACCEPT | 77 | 0 | 3 | 80 |
| REJECT | 5 | 51 | 1 | 57 |
| REVIEW | 8 | 15 | 0 | 23 |
| Tổng | 90 | 66 | 4 | 160 |

### Mẫu bổ sung 17

| Đại lượng | v0.2.0 | v0.2.1 candidate |
| --- | --- | --- |
| TP | 0 | 3 |
| TN | 0 | 0 |
| FP | 0 | 0 |
| FN | 3 | 3 |
| REVIEW | 14 | 11 |
| CHUA_RO | 0 | 0 |

| Tỷ lệ, mẫu số | Trước | Sau |
| --- | --- | --- |
| Khớp membership khi máy quyết định | 0/3 = 0.00% | 3/6 = 50.00% |
| Độ phủ trên nhãn rõ | 3/17 = 17.65% | 6/17 = 35.29% |
| Độ phủ trên toàn mẫu | 3/17 = 17.65% | 6/17 = 35.29% |
| Quyết định đúng trên nhãn rõ | 0/17 = 0.00% | 3/17 = 17.65% |
| Precision trên ACCEPT nhãn rõ | 0/0: không xác định | 3/3 = 100.00% |
| Recall có điều kiện trên ACCEPT/REJECT | 0/3 = 0.00% | 3/6 = 50.00% |
| ACCEPT trên tất cả CNTT duyệt | 0/16 = 0.00% | 3/16 = 18.75% |
| Khớp nhóm trên ACCEPT/CNTT | 0/0: không xác định | 3/3 = 100.00% |
| Khớp subgroup khi cả hai nhóm SOFTWARE | 0/0: không xác định | 1/1 = 100.00% |

**Ma trận candidate**

| Máy candidate | CNTT | NGOAI_CNTT | CHUA_RO | Tổng |
| --- | ---: | ---: | ---: | ---: |
| ACCEPT | 3 | 0 | 0 | 3 |
| REJECT | 3 | 0 | 0 | 3 |
| REVIEW | 10 | 1 | 0 | 11 |
| Tổng | 16 | 1 | 0 | 17 |

Hợp hai mẫu: REVIEW **37 → 33 job_id duy nhất**; không cộng trùng ca chung. 4 CHUA_RO đã duyệt giữ nguyên, không dùng làm negative gold.

## Giải thích mọi delta

**Bốn chuyển REVIEW → ACCEPT**, đều khớp nhóm người duyệt; subgroup SOFTWARE_OTHER của Software Development Engineer cũng khớp nhãn. Trước sửa cả bốn có reason AMBIGUOUS_TITLE_WITHOUT_CONTEXT, không rule/evidence positive. Sau sửa có predicate và nguồn cụ thể dưới đây; UNKNOWN là section eligible theo chính sách cũ, không phải qualification/company được mở chặn.

| job_id | Entry | Rule thắng; reason mới | Nhóm / subgroup sau | Alias chứng cứ và raw ranges |
| --- | --- | --- | --- | --- |
| `3902872004` | P2_ETL | DATA_AI_CONTEXT; TITLE_CONTEXT | DATA_AI / NULL | `creating etl pipeline` (description s2 / UNKNOWN, [216,237)) |
| `3904090041` | P2_SOFTWARE_TITLE | SOFTWARE_TITLE; TITLE_DIRECT | SOFTWARE / SOFTWARE_OTHER | `software development engineer` (title, [0,29)) |
| `3904392069` | P2_CYBER | SECURITY_CONTEXT; TITLE_CONTEXT | SECURITY / NULL | `respond to cyber incidents` (description s2 / UNKNOWN, [442,468)); `cyber incidents` (description s2 / UNKNOWN, [453,468)) |
| `3906230754` | P2_DATABASE | DATA_AI_CONTEXT; TITLE_CONTEXT | DATA_AI / NULL | `oversee database management` (description s17 / RESPONSIBILITIES, [1884,1911)); `database` (description s17 / RESPONSIBILITIES, [1892,1900)); `data storage, retrieval, and security` (description s17 / RESPONSIBILITIES, [1933,1970)) |

P2_ETL giữ data/BI title hint và context ETL/SQL/Python trong cùng s2; P2_CYBER ghép task bảo mật hiện có với context cyber incidents cùng s2. P2_SOFTWARE_TITLE dùng đúng occupational phrase ở title, không đổi DATA_AI theo tên đội. P2_DATABASE giữ title Data Analyst và cả ba task/object/context trong s17 RESPONSIBILITIES; SQL/ML ở qualification không cấp evidence. Không có chuyển REJECT → ACCEPT, không đổi nhóm/subgroup của ca đã ACCEPT trước đợt sửa, không thay 4 nhãn CHUA_RO.

**Toàn bộ 26 ca có delta chi tiết** (22 cấu trúc P1a và 4 trạng thái P2) được liệt kê dưới đây. Các ca khác không đổi trường quyết định hoặc chi tiết ngoài version/hash.

| job_id | Title | Trạng thái trước → sau | Nhóm trước → sau | Entry gây delta | Trường khác (không tính version/hash) |
| --- | --- | --- | --- | --- | --- |
| `3886819981` | Senior Software Engineer | ACCEPT → ACCEPT | SOFTWARE → SOFTWARE | P1a | description_processing, description_segments |
| `3888484807` | Tech Support Engineer (US) | REVIEW → REVIEW | NULL → NULL | P1a | description_processing, description_segments |
| `3889128520` | Interoperability Engineer III | REVIEW → REVIEW | NULL → NULL | P1a | description_segments |
| `3889720090` | Interoperability Engineer III | REVIEW → REVIEW | NULL → NULL | P1a | description_segments |
| `3891075360` | W2 position - AEM Developer | ACCEPT → ACCEPT | SOFTWARE → SOFTWARE | P1a | description_processing, description_segments |
| `3891078124` | Technical Program Manager - Cyber Security | REVIEW → REVIEW | NULL → NULL | P1a | description_processing, description_segments |
| `3895545207` | Manufacturing Data Architect | REVIEW → REVIEW | NULL → NULL | P1a | description_segments |
| `3895563414` | Data Platform Engineer Data Mesh/Virtualization | REVIEW → REVIEW | NULL → NULL | P1a | description_segments |
| `3895598798` | Network Engineer II | ACCEPT → ACCEPT | NETWORK_SYSTEMS → NETWORK_SYSTEMS | P1a | description_processing, description_segments |
| `3899522608` | Philips or Carestream PACS solutions | REJECT → REJECT | NULL → NULL | P1a | description_segments |
| `3902357961` | Full Stack Engineer | ACCEPT → ACCEPT | SOFTWARE → SOFTWARE | P1a | description_processing, description_segments |
| `3902752565` | Accountant | REJECT → REJECT | NULL → NULL | P1a | description_segments |
| `3902872004` | BI Analyst | REVIEW → ACCEPT | NULL → DATA_AI | P2_ETL | it_decision, is_it, primary_group_code, selected_rule_id, reason_codes, matched_rule_ids, candidate_group_codes, match_evidence, description_segments |
| `3903468471` | Programmer Analyst | ACCEPT → ACCEPT | SOFTWARE → SOFTWARE | P1a | description_processing, description_segments |
| `3903822524` | Cleaner | REJECT → REJECT | NULL → NULL | P1a | description_segments |
| `3903845232` | Data Engineer | ACCEPT → ACCEPT | DATA_AI → DATA_AI | P1a | description_segments |
| `3903891231` | Lead Research Scientist | REJECT → REJECT | NULL → NULL | P1a | description_segments |
| `3904090041` | Software Development Engineer II, CIA Data Services | REVIEW → ACCEPT | NULL → SOFTWARE | P2_SOFTWARE_TITLE | it_decision, is_it, primary_group_code, subgroup_code, selected_rule_id, reason_codes, matched_rule_ids, candidate_group_codes, match_evidence |
| `3904392069` | Senior Digital Forensics Analyst | REVIEW → ACCEPT | NULL → SECURITY | P2_CYBER | it_decision, is_it, primary_group_code, selected_rule_id, reason_codes, matched_rule_ids, candidate_group_codes, match_evidence, description_segments |
| `3904925156` | Full Stack Engineer | ACCEPT → ACCEPT | SOFTWARE → SOFTWARE | P1a | description_processing, description_segments |
| `3904949360` | Programmer | REJECT → REJECT | NULL → NULL | P1a | description_processing, description_segments |
| `3905664532` | Senior Network Engineer - TS/SCI required | ACCEPT → ACCEPT | NETWORK_SYSTEMS → NETWORK_SYSTEMS | P1a | description_segments |
| `3905877226` | Senior Test Engineer | REVIEW → REVIEW | NULL → NULL | P1a | description_segments |
| `3906230754` | Data Analyst | REVIEW → ACCEPT | NULL → DATA_AI | P2_DATABASE | it_decision, is_it, primary_group_code, selected_rule_id, reason_codes, matched_rule_ids, candidate_group_codes, match_evidence, description_segments |
| `3906259481` | Physician Assistant- Surgical- CV Surgery- Humble | REJECT → REJECT | NULL → NULL | P1a | description_processing, description_segments |
| `3906260689` | iOS Developer | ACCEPT → ACCEPT | SOFTWARE → SOFTWARE | P1a | description_segments |

[job_comparison.csv](../data/analytics/a04_taxonomy_v0_2_1_20261014/job_comparison.csv) có đủ **176 khóa**, gồm cả ca không đổi; [comparison_summary.json](../data/analytics/a04_taxonomy_v0_2_1_20261014/comparison_summary.json) và từng stage delta giữ giá trị trước/sau đầy đủ cho cả metadata xử lý, section/actor, evidence và raw ranges. Mẫu riêng 160/17 giữ đủ 177 dòng nguồn trong hai trace mới. Heading P1a có thể đổi section/index/blocked reasons ở ca vẫn REVIEW/REJECT/ACCEPT; những thay đổi này được liệt kê, không gọi chúng là sửa membership. Các ca nhận mới bởi P2 có task/phrase cụ thể và rule tương ứng trong delta, không dựa job_id/doanh nghiệp.

## FN còn lại và bước P3 để lựa chọn

| job_id | Title | Nhóm người duyệt | Reason candidate |
| --- | --- | --- | --- |
| `3899522608` | Philips or Carestream PACS solutions | IT_SUPPORT | NO_IT_ROLE_EVIDENCE |
| `3884442452` | Workday Integration - C2H | SOFTWARE | NO_IT_ROLE_EVIDENCE |
| `3887714064` | Junior Scrum Master | IT_BUSINESS | NO_IT_ROLE_EVIDENCE |
| `3251984218` | SAP BTP | SOFTWARE | NO_IT_ROLE_EVIDENCE |
| `3904363315` | Senior Oracle Cloud Financial Analyst - Fusion, PaaS, ERP, SAP (Hybrid LA / Houston) | IT_BUSINESS | OUTSIDE_IT_ROLE |
| `3903891231` | Lead Research Scientist | DATA_AI | NO_IT_ROLE_EVIDENCE |
| `3904949360` | Programmer | SOFTWARE | NO_IT_ROLE_EVIDENCE |
| `3906223537` | ECC Designer/Programmer | NETWORK_SYSTEMS | NO_IT_ROLE_EVIDENCE |

Đợt P1a/P2 xử lý độ phủ nhỏ; không cam kết chữa hết FN. Đề xuất bước tiếp theo để chốt: P3 task integration/coding/maintenance cho Workday/Programmer; IT delivery cho Scrum Master; support task/object cho PACS (heading đã mở nhưng hint/task còn thiếu); vận hành OS/network/backup cho ECC với kiểm tra nhóm. Oracle cần cả P3 positive functional ERP và P4 exclusion, không xử lý bằng alias chung. SAP BTP/Lead Research Scientist vẫn cần P5 về profile/nhiệm vụ; không mở qualification để nhận họ. Chưa triển khai các đề xuất này trong round 1.

Các REVIEW còn lại, nhất là Privacy/implicit heading, domain conflict, UI/application support và 16 ca ngoài CNTT, không bị ép ACCEPT. Tiêu chí vẫn theo [a04_completion_criteria.md](a04_completion_criteria.md): còn chốt xử lý phần lỗi còn lại và xác nhận nghiệm thu. TV1 cần đối soát cùng candidate JSON/code/fixture trên Spark/JVM, nhất là heading, Unicode code point/UTF-16, source mapping/raw ranges, nullability và tier/priority; parity chưa được xác minh, thuộc tích hợp D06.

## Hiện vật và phạm vi chạy

[Runner](../src/a04_filter_fix_round1.py), [fixture tests](../src/test_a04_round1.py), [run manifest](../data/analytics/a04_taxonomy_v0_2_1_20261014/run_manifest.json) và [audit](../data/audit/tv2_a04_filter_fix_round1_20261014.json) lưu nguồn/hash/kiểm tra. Dùng runner `--prepare` trên baseline đã đóng băng rồi chạy unittest và runner trong output mới; runner từ chối ghi đè output. Active config/trace cũ vẫn phục vụ v0.2.0, candidate phải được chỉ định bằng đường dẫn version riêng.

Không chạy ETL/toàn dataset, không làm A05, không commit/push, không tự đánh dấu A04 hoàn thành. Không sửa raw/job_id/title/description/nhãn/reviewer/ngày duyệt hoặc quyết định phạm vi P5.
