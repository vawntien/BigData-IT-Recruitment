# A04 – Round 2: ba phần P3, candidate v0.2.2

Ngày **14/10/2026**, múi giờ `Asia/Bangkok`, nhánh `feat/tv2-analysis`. **Candidate trên mẫu phát triển; chưa xác nhận nghiệm thu A04.**

Đã đọc [kế hoạch](a04_filter_fix_plan.md), [kết quả round 1](a04_filter_fix_round1_report.md), [tiêu chí nghiệm thu](a04_completion_criteria.md) và candidate v0.2.1. Candidate mới [it_taxonomy_v0.2.2.json](../config/versions/it_taxonomy_v0.2.2.json), SHA-256 `1de2908a4a8da3e7f811c0d87928d05f857f5bd78ec243cc57c07ef9ec933874`. Active `config/it_taxonomy.json` vẫn v0.2.0. Chỉ triển khai integration/coding, application maintenance/migration và IT project delivery; không P1b/P4/P5/PACS/ECC.

## Baseline và bảo toàn

[Baseline v0.2.1](../data/analytics/a04_taxonomy_v0_2_2_20261014/baseline/manifest.json) giữ exact config/code/test và ba trace đã lưu của round 1, hash trước sửa, source rows đã duyệt và Git state. Baseline config SHA-256 `efedfeeeb090808923f3ad47a27988f90436153f6e5f70610d48ff19c14773b9`. Replay **176/176 prediction khớp toàn bộ trường**, kể cả evidence/segments/processing. Mẫu chính 160, bổ sung 17, ca chung `3905848702` được deduplicate theo job_id; không JOIN bằng STT.

Raw, workbook, reviewer Dũng/ngày 2026-10-13, active config, config/trace/báo cáo/đầu ra cũ giữ nguyên. Hai chỉnh sửa nhỏ ở file có sẵn: interpreter chấp nhận thêm version v0.2.2; fixture unknown-version chuyển từ v0.2.2 sang v0.2.3 vì v0.2.2 nay được hỗ trợ, giữ nguyên ý nghĩa fail-closed. Bản code/test trước sửa đã snapshot; không đổi logic actor/section/negation/tier/priority/conflict. Config/trace/báo cáo/audit round 1 và v0.2.1 không được ghi đè.

## Sửa đổi thực tế và giới hạn

1. **P3_INTEGRATION**: SOFTWARE_CONTEXT là ANY của nhánh cũ và nhánh title software hint/integration contextual hint + SAME_SEGMENT(task workflow thiết kế/phát triển/test/deploy, object integration, context software/application). Catalog workflow dùng literal cụ thể, không verb integrate chung. `workday platform` là object ứng dụng cùng task, không tín hiệu employer; tên Workday/SAP hoặc integration đơn lẻ không đủ. Fixture dùng cả software applications không phụ thuộc sản phẩm. HR/accounting sử dụng phần mềm không tự ACCEPT.
2. **P3_APPLICATION_MAINTENANCE_MIGRATION**: thêm nhánh software hint + coding-role hint programmer/developer + task maintenance/support hoặc maintenance/upgrade cùng object ứng dụng và software environment. Migration cần cả task `migrate and upgrade`, object systems/applications, origin client/server và target Web-based **cùng unit**. Programmer vẫn không direct-title. SOFTWARE_WEB_CONTEXT có thêm đúng nhánh migration này để lấy Web từ nhiệm vụ chuyển ứng dụng, giữ tier/priority cũ; không lấy technology/profile ở QUALIFICATIONS. Maintenance đơn lẻ chưa đủ Web.
3. **P3_IT_DELIVERY**: IT_BUSINESS_CONTEXT giữ business title hint và thêm nhánh action project ownership/delivery + object `IT epics`/information-system projects + planning/deployment/system-implementation context cùng unit. Không dùng IT token rời rạc, Scrum, backlog hay Product Owner đơn lẻ. Nhóm là IT_BUSINESS, không đổi IT_MANAGEMENT.

Chỉ schema 1 hiện có (all/any/match/same_segment); không thêm operator/rule ID hoặc thay priority. Các nhánh cũ là nhánh đầu nguyên vẹn; term sets v0.2.1 nguyên vẹn. Predicate mới tiếp tục qua eligible unit, actor, company/qualification, negation/collaboration và source mapping/cửa sổ 500. Không dùng job_id, sample_id, employer hoặc whitelist mẫu trong classifier. Khóa trong báo cáo chỉ phục vụ đối chiếu.

## Kiểm tra và kết quả từng hạng mục

**46 unittest qua, không skip**; mỗi stage có 40 control round 1, 45 control round 2 và 57 ca minh họa. Positive/negative controls gồm workflow integration/object mềm, HR/accounting, product-only, pure CNC/PLC, qualification-only (cả Develop applications), company/other actor/collaboration, negation, cross-unit, no title hint, thiếu origin/target, generic backlog/project và QA/SDET. Kiểm tra decision/is_it/group/subgroup/reason/rule/evidence/raw ranges và mapping.

| Hạng mục, so với stage trước | Job thay chi tiết | Job đổi trạng thái | Hồi quy FP/mất TP/nhóm/subgroup |
| --- | ---: | ---: | ---: |
| P3_INTEGRATION | 1 | 1 | 0 |
| P3_APPLICATION_MAINTENANCE_MIGRATION | 1 | 1 | 0 |
| P3_IT_DELIVERY | 1 | 1 | 0 |

Từng stage có config/hash, controls, prediction và delta riêng trong [stages](../data/analytics/a04_taxonomy_v0_2_2_20261014/stages/). Không có hồi quy cần thu hồi trên các controls và 176 khóa đã chốt. Các bất đồng nhóm/subgroup có từ baseline không được sửa nhãn hoặc che đi.

## Kết quả v0.2.1 → v0.2.2 tính lại từ nguồn

Tính riêng hai mẫu từ nhãn workbook đóng băng và trace candidate theo job_id. Khớp có điều kiện = `(ACCEPT/CNTT + REJECT/NGOAI_CNTT) / ca nhãn rõ và máy ACCEPT/REJECT`; độ phủ nhãn rõ dùng cùng số ca chia CNTT+NGOAI_CNTT. REVIEW chưa quyết định, không REJECT/FN; CHUA_RO loại khỏi mẫu số nhãn rõ và vẫn hiện riêng. Tỷ lệ quyết định đúng trên nhãn rõ không tính REVIEW là đúng. Group chỉ trên ACCEPT/CNTT; subgroup chỉ khi cả hai nhóm SOFTWARE.

### Mẫu chính 160

| Đại lượng | v0.2.1 | v0.2.2 |
| --- | ---: | ---: |
| TP | 77 | 79 |
| TN | 51 | 51 |
| FP | 0 | 0 |
| FN | 5 | 3 |
| REVIEW | 23 | 23 |
| CHUA_RO | 4 | 4 |

| Tỷ lệ, mẫu số | Trước | Sau |
| --- | --- | --- |
| Khớp khi máy quyết định | 128/133 = 96.24% | 130/133 = 97.74% |
| Độ phủ nhãn rõ | 133/156 = 85.26% | 133/156 = 85.26% |
| Độ phủ toàn mẫu | 137/160 = 85.62% | 137/160 = 85.62% |
| Quyết định đúng trên nhãn rõ | 128/156 = 82.05% | 130/156 = 83.33% |
| Precision trên ACCEPT nhãn rõ | 77/77 = 100.00% | 79/79 = 100.00% |
| Recall có điều kiện ACCEPT/REJECT | 77/82 = 93.90% | 79/82 = 96.34% |
| ACCEPT trên toàn bộ CNTT duyệt | 77/90 = 85.56% | 79/90 = 87.78% |
| Khớp nhóm trên ACCEPT/CNTT | 74/77 = 96.10% | 76/79 = 96.20% |
| Khớp subgroup khi hai nhóm SOFTWARE | 29/38 = 76.32% | 30/39 = 76.92% |

| Máy v0.2.2 | CNTT | NGOAI_CNTT | CHUA_RO | Tổng |
| --- | ---: | ---: | ---: | ---: |
| ACCEPT | 79 | 0 | 3 | 82 |
| REJECT | 3 | 51 | 1 | 55 |
| REVIEW | 8 | 15 | 0 | 23 |
| Tổng | 90 | 66 | 4 | 160 |

### Mẫu bổ sung 17

| Đại lượng | v0.2.1 | v0.2.2 |
| --- | ---: | ---: |
| TP | 3 | 4 |
| TN | 0 | 0 |
| FP | 0 | 0 |
| FN | 3 | 2 |
| REVIEW | 11 | 11 |
| CHUA_RO | 0 | 0 |

| Tỷ lệ, mẫu số | Trước | Sau |
| --- | --- | --- |
| Khớp khi máy quyết định | 3/6 = 50.00% | 4/6 = 66.67% |
| Độ phủ nhãn rõ | 6/17 = 35.29% | 6/17 = 35.29% |
| Độ phủ toàn mẫu | 6/17 = 35.29% | 6/17 = 35.29% |
| Quyết định đúng trên nhãn rõ | 3/17 = 17.65% | 4/17 = 23.53% |
| Precision trên ACCEPT nhãn rõ | 3/3 = 100.00% | 4/4 = 100.00% |
| Recall có điều kiện ACCEPT/REJECT | 3/6 = 50.00% | 4/6 = 66.67% |
| ACCEPT trên toàn bộ CNTT duyệt | 3/16 = 18.75% | 4/16 = 25.00% |
| Khớp nhóm trên ACCEPT/CNTT | 3/3 = 100.00% | 4/4 = 100.00% |
| Khớp subgroup khi hai nhóm SOFTWARE | 1/1 = 100.00% | 2/2 = 100.00% |

| Máy v0.2.2 | CNTT | NGOAI_CNTT | CHUA_RO | Tổng |
| --- | ---: | ---: | ---: | ---: |
| ACCEPT | 4 | 0 | 0 | 4 |
| REJECT | 2 | 0 | 0 | 2 |
| REVIEW | 10 | 1 | 0 | 11 |
| Tổng | 16 | 1 | 0 | 17 |

Hợp hai mẫu: REVIEW duy nhất **33 → 33**, FN xác nhận **8 → 5**. 4 CHUA_RO đã duyệt nguyên vẹn. 177 dòng nguồn không là 177 tin độc lập; đây là mẫu phát triển đã dùng sửa quy tắc, không accuracy toàn dataset hoặc đánh giá độc lập.

## Giải thích mọi thay đổi

| job_id | Title | Decision | Group/subgroup trước → sau | Hạng mục | Trường delta ngoài version/hash |
| --- | --- | --- | --- | --- | --- |
| `3884442452` | Workday Integration - C2H | REJECT → ACCEPT | NULL / NULL → SOFTWARE / SOFTWARE_OTHER | P3_INTEGRATION | it_decision, is_it, primary_group_code, subgroup_code, selected_rule_id, reason_codes, matched_rule_ids, candidate_group_codes, match_evidence, description_segments |
| `3887714064` | Junior Scrum Master | REJECT → ACCEPT | NULL / NULL → IT_BUSINESS / NULL | P3_IT_DELIVERY | it_decision, is_it, primary_group_code, selected_rule_id, reason_codes, matched_rule_ids, candidate_group_codes, match_evidence, description_segments |
| `3904949360` | Programmer | REJECT → ACCEPT | NULL / NULL → SOFTWARE / SOFTWARE_WEB | P3_APPLICATION_MAINTENANCE_MIGRATION | it_decision, is_it, primary_group_code, subgroup_code, selected_rule_id, reason_codes, matched_rule_ids, candidate_group_codes, match_evidence, description_segments |

| job_id | Rule thắng và reason candidate | Alias evidence, field/unit/section, raw ranges |
| --- | --- | --- |
| `3884442452` | SOFTWARE_CONTEXT; TITLE_CONTEXT | `integration` (title, [8,19)); `design, develop, test, deploy, and manage integration` (description s2 / ROLE, [182,235)); `integration` (description s2 / ROLE, [224,235)); `workday platform` (description s2 / ROLE, [239,255)) |
| `3887714064` | IT_BUSINESS_CONTEXT; TITLE_CONTEXT | `scrum master` (title, [7,19)); `successful execution of delivery` (description s5 / ROLE, [627,659)); `it related epics` (description s5 / ROLE, [667,683)); `planning the schedule` (description s5 / ROLE, [601,622)); `manages all aspects` (description s14 / RESPONSIBILITIES, [1760,1779)); `it epics` (description s14 / RESPONSIBILITIES, [1796,1804)); `planning to deployment` (description s14 / RESPONSIBILITIES, [1810,1832)) |
| `3904949360` | SOFTWARE_CONTEXT; TITLE_CONTEXT | `programmer` (title, [0,10)); `programmer` (title, [0,10)); `provide maintenance and support` (description s11 / ROLE, [919,950)); `systems` (description s11 / ROLE, [989,996)); `web based systems` (description s11 / ROLE, [979,996)); `programmer` (title, [0,10)); `programmer` (title, [0,10)); `migrate and upgrade` (description s13 / ROLE, [1202,1221)); `systems` (description s13 / ROLE, [1231,1238)); `client server environment` (description s13 / ROLE, [1246,1271)); `web based environment` (description s13 / ROLE, [1277,1298)); `programmer` (title, [0,10)); `programmer` (title, [0,10)); `migrate and upgrade` (description s13 / ROLE, [1202,1221)); `systems` (description s13 / ROLE, [1231,1238)); `client server environment` (description s13 / ROLE, [1246,1271)); `web based environment` (description s13 / ROLE, [1277,1298)) |

Raw ranges là Unicode code point `[start,end)` trong trường sau CSV parse; quote đầy đủ và toàn bộ before/after nằm trong [comparison_summary](../data/analytics/a04_taxonomy_v0_2_2_20261014/comparison_summary.json) và từng stage delta. `job_comparison.csv` có đủ 176 khóa, kể cả không đổi; trace riêng có đủ 160/17 và common prediction khớp. Các nhiệm vụ mới được nhận từ ROLE/RESPONSIBILITIES/UNKNOWN eligible và task sở hữu vị trí; qualification/actor bị chặn giữ nguyên. Không lấy Web từ câu Develop applications ở QUALIFICATIONS.

## Lỗi còn lại và phương án xử lý

| job_id | Title | Nhóm người duyệt | Reason candidate |
| --- | --- | --- | --- |
| `3899522608` | Philips or Carestream PACS solutions | IT_SUPPORT | NO_IT_ROLE_EVIDENCE |
| `3251984218` | SAP BTP | SOFTWARE | NO_IT_ROLE_EVIDENCE |
| `3904363315` | Senior Oracle Cloud Financial Analyst - Fusion, PaaS, ERP, SAP (Hybrid LA / Houston) | IT_BUSINESS | OUTSIDE_IT_ROLE |
| `3903891231` | Lead Research Scientist | DATA_AI | NO_IT_ROLE_EVIDENCE |
| `3906223537` | ECC Designer/Programmer | NETWORK_SYSTEMS | NO_IT_ROLE_EVIDENCE |

Các FN còn lại cần xử lý theo quyền hạn riêng: PACS cần task/object/hint support sau heading, ECC cần phân xử nghề vận hành OS/network/backup với software phụ, Oracle cần positive functional ERP và P4 exclusion, SAP BTP/Lead Research Scientist cần P5 về profile/nhiệm vụ. Chưa triển khai các phần này hoặc thêm ngoại lệ để ép chúng thành ACCEPT.

REVIEW còn lại giữ rõ: mẫu chính 8 CNTT + 15 NGOAI_CNTT; bổ sung 10 CNTT + 1 NGOAI_CNTT; hợp duy nhất 17 CNTT + 16 NGOAI_CNTT do ca chung là CNTT/REVIEW. Conflict domain software/data thuộc P4, implicit heading/Privacy thuộc P1b và phạm vi P5, UI/application-support/data-platform thiếu task/hint hoặc cần chốt nhóm. 16 REVIEW ngoài CNTT không bị coi là FN. Không yêu cầu tất cả REVIEW phải ACCEPT; không thay nhãn CHUA_RO để làm tỷ lệ tốt hơn.

**Bất đồng nhóm còn từ baseline (3 ca, đều ở mẫu chính):**

| job_id | Title | Nhóm candidate | Nhóm đã duyệt |
| --- | --- | --- | --- |
| `3905291167` | Software Engineer | SOFTWARE | DATA_AI |
| `3900944795` | IT Technician | IT_OTHER | IT_SUPPORT |
| `3884430597` | Desktop Support Technician | IT_SUPPORT | IT_MANAGEMENT |

Bất đồng subgroup còn từ baseline (9 ca, đều ở mẫu chính): `3886819981` (SOFTWARE_OTHER → nhãn SOFTWARE_WEB); `3905328583` (SOFTWARE_OTHER → nhãn SOFTWARE_WEB); `3901379461` (SOFTWARE_OTHER → nhãn SOFTWARE_WEB); `3891075360` (SOFTWARE_OTHER → nhãn SOFTWARE_WEB); `3901389270` (SOFTWARE_WEB → nhãn SOFTWARE_OTHER); `3901935934` (SOFTWARE_WEB → nhãn SOFTWARE_OTHER); `3901938023` (SOFTWARE_WEB → nhãn SOFTWARE_OTHER); `3901394183` (SOFTWARE_WEB → nhãn SOFTWARE_OTHER); `3901394507` (SOFTWARE_WEB → nhãn SOFTWARE_OTHER). Cần đối soát evidence nghề và quy tắc ưu tiên/chính sách Web so với OTHER trong phạm vi được chốt tiếp theo. Round 2 không đổi priority hoặc nhãn đã duyệt để giải quyết các bất đồng này. Bất đồng nhóm không được đếm thêm như lỗi subgroup.

Catalog mới cố ý hẹp: workflow integration phải có chuỗi action rõ; migration phải có cả origin và target trong một unit. Những cách diễn đạt tương tự chưa có alias vẫn có thể bị bỏ sót; chưa có bằng chứng để nới động từ/context hoặc nối qua unit. Rủi ro nhận người dùng sản phẩm, việc của công ty/người khác và nghiệp vụ Scrum được kiểm tra bằng negative controls; kết quả không có FP mới trên mẫu này không chứng minh không có FP ngoài mẫu.

## Đối chiếu nghiệm thu A04

Theo [a04_completion_criteria.md](a04_completion_criteria.md), mẫu 100–200 tin, nhãn/metadata, tỷ lệ có tử số/mẫu số và ví dụ lọc sai đã có. Round 2 bổ sung sửa và kiểm tra hồi quy cho ba họ được phép. **Không có tiêu chí mặc định FN=0/REVIEW=0**; nhãn CHUA_RO và máy abstain được phép khi báo rõ nguồn, phạm vi/mẫu số và phương án đối soát.

Phần cần người phụ trách xác nhận để nghiệm thu: kết quả và cách xử lý lỗi đã thực hiện đáp ứng G21/I21; chốt cách xử lý/giới hạn chấp nhận đối với FN/REVIEW/bất đồng còn lại, không coi chỉ có bảng đề xuất là đã sửa tất cả bộ lọc; người rà soát xác nhận đầu ra/tiêu chí trước cập nhật 100%. Không tự đánh dấu hoàn thành. Mẫu độc lập phục vụ tuyên bố chất lượng độc lập/toàn tập; parity Spark/JVM/canonical thuộc D06/TV1, không tự biến thành hai điều kiện riêng của I21.

TV1 cần chạy cùng candidate/config/fixture, giữ SAME_SEGMENT/actor/blocker, sort tier/priority, Web migration chỉ sau SOFTWARE, is_it/nhóm NULL cho REVIEW và mapping code point–UTF-16/raw ranges; không bật metadata/skills cho membership. Parity chưa xác minh trong lượt này.

## Hiện vật và phạm vi

[Runner](../src/a04_filter_fix_round2.py), [test mới](../src/test_a04_round2.py), [manifest](../data/analytics/a04_taxonomy_v0_2_2_20261014/run_manifest.json), [kiểm tra đầu ra](../data/analytics/a04_taxonomy_v0_2_2_20261014/saved_output_verification.json), [đối chiếu cuối](../data/analytics/a04_taxonomy_v0_2_2_20261014/independent_verification.json), [audit](../data/audit/tv2_a04_filter_fix_round2_20261014.json). Đối chiếu cuối tính lại ma trận/tỷ lệ bằng Counter và phân số từ trace đã lưu; đây là kiểm tra phép tính, không là mẫu đánh giá độc lập. Runner từ chối ghi đè output, chỉ đọc source/trace mẫu đã khóa; config candidate phải chỉ định riêng. Không ETL/toàn dataset, không A05, commit/push; raw/workbook/metadata/trace/active config và đầu ra cũ nguyên vẹn.
