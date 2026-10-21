# D10–D11 — Status, dependencies và QA Phase 1

**21/10/2026, Asia/Bangkok.** Available evidence only; không human acceptance.
[D10](d10_technical_report.md) · [D11](d11_handoff_reproducibility.md) ·
[Evidence index](d10_d11_evidence_index.md).

## 1. Completed vs pending

| Hạng mục | Hiện trạng có evidence | Phần chưa được phép tuyên bố |
| --- | --- | --- |
| D05 | Canonical released;123849 unique jobs/50 fields | Business acceptance toàn nhóm không tự suy từ release |
| D06 | Parity/Pilot PASS;runner/schema technically ready | Full dataset NOT EXECUTED; IT counts chưa có |
| D07 | ALL-JOBS staging released;123849/28;36059 USABLE | Official IT salary/point estimate/outlier policy chưa duyệt |
| D08 | Available W1–W5 benchmark released;45 measured/15 warmups | Full-pipeline/multi-node benchmark NOT EXECUTED |
| D09 | Available validation released;22P/0F/9B/2NA | Full-pipeline validation BLOCKED |
| D10 | Phase1 technical report và bảng/hình có nguồn | Final integrated report chưa được nhóm accepted |
| D11 | Local handoff/reproducibility/evidence guide | Delivery receipt/cross-machine signoff/final package chưa có |
| TV2 | A05/Q07 implementation evidence/candidates | A05 official/A06–A08 IT production phụ thuộc Full và approvals |
| TV3 | Development UI/sample/draft contracts | Final IT dashboard chờ official analytics + contract acceptance |

## 2. Gate/owner matrix

| Gate | Trạng thái | Loại dependency | Người/vai trò cần hành động | Điều kiện đóng gate |
| --- | --- | --- | --- | --- |
| Main A04 workbook160 | MISSING tại TV1 audit gần nhất | Missing upstream artifact/private delivery | TV2/người giữ workbook → TV1 | Nhận file đúng tên/identity;verify exact SHA/160 labels |
| A04 business acceptance | PENDING | Human decision | Người nghiệm thu A04 được nhóm giao quyền | Record thật chấp nhận/giải quyết5FN/33REVIEW/3group/9subgroup/4CHUA_RO |
| D06 schema approval | PENDING | Human contract decision | Người duyệt schema cùng TV1/TV2/TV3 | APPROVED d06-official-v1/27 fields/hash |
| D06 Full authorization | NOT GRANTED | Human execution decision | Người có quyền cấp run + operator TV1 | Bind NEW run_id/input/package/output/approval hashes |
| D06 Full output/seal | NOT AVAILABLE | Missing upstream runtime artifact | TV1, chỉ sau đủ approvals | Full SUCCEEDED + keys/source/nested/schema/inventory validation |
| Full resource budget | Chưa xác minh production-scale | Technical readiness/resource decision | TV1/operator | Chốt RAM/heap/workers/disk/skew/failure plan, không ngoại suy Pilot |
| Q07 business contract | PENDING | Human business/UI decision | TV1/TV2/TV3 và người nghiệm thu | Chốt5 policies ở mục3, exact input digest,consumer contract |
| A05 official/A06–A08 IT production | DEPENDENT ON D06 FULL | Missing upstream + human policy | TV2 | Receive Full provenance, source/ACCEPT view,approve queries |
| TV3 final IT dashboard | PENDING | Missing accepted analytics/contract | TV3 cùng TV2/TV1 | Output tables/run/table hashes,denominators,filters + team signoff |
| D08 full-pipeline benchmark | NOT EXECUTED | Missing workload authorization/artifact | TV1/nhóm nếu yêu cầu | Run/evidence mới gồm D06 thật, không relabel W1–W5 |
| ZIP external delivery | Chưa có upload/ack evidence | Coordination/permissions | Người gửi + người nhận | Kênh được phép,hash verification và receipt |

Không coi tất cả pending là lỗi engineering. Không đưa tên người ký giả hoặc
tự suy thẩm quyền từ author commit/reviewer nhãn.

## 3. Q07 decisions và source gaps

| Decision | Candidate TV2 | Điểm cần human chốt |
| --- | --- | --- |
| Eligibility | D07_USABLE_WHOLE_SELECTED_BUNDLE;partial/med-only allowed | Có bổ sung điều kiện business không;không tự thay source status |
| Grain/source/basis | 1 job_id/bundle,POSTED_NATIVE,source là chiều | Giữ source riêng hay authoritative selection;không pool/native+annual |
| Outliers | NO_ADDITIONAL_FILTER | Chấp nhận plausibility limitation hay flag/exclusion version mới |
| Quantiles | Exact continuous interpolation,double output | Tolerance/rounding;test fractional/ties;không có approx accuracy parameter |
| Minimum sample | No default;adequate flags,không suppress | n_min/n_max threshold riêng;đề xuất≥30 chưa approved;giữ count/coverage |

TV2 hash caveat ở pin8323b5b: audit hashes của `src/a06_a08_spark_analysis.py`,
`src/render_tv2_analysis.py`, `src/test_a05_a11_integration.py`,
`config/tv2_analysis_inputs.example.json`, `config/tv2_analysis_output_schema.json`
khớp CRLF representation chứ không exact LF Git blobs. TV2 cần follow-up immutable
identity/test provenance. Không sửa TV2 files/audit trong Phase1 docs.

TV3 local draft có proposed flat salary median và các giả định unit/NULL/remote
khác actual Q07/D05 contracts; phải review/adapt, không tự coi proposed fields tồn
tại. Không tổng hợp lại marginal tables để giả hỗ trợ cross-filter/ALL/pooled median.

Legacy `docs/handoff/project_status.md` và methodology/metrics/submission drafts
còn TODO D05/D07/D08 trước release. Chỉ reuse outline/phần đã đúng, giữ mốc version;
không sửa tài liệu TV3 hoặc nâng checklist legacy thành signoff mới.

## 4. QA tài liệu

QA Phase1 kiểm tự động relative links/images tới file có thật, balanced code fences,
heading/table shape, commit existence, run IDs, table arithmetic/rounding, schema
field counts, metric statuses và protected artifacts. Không khởi động UI, render
PDF/Word, rerun ETL/benchmark hoặc kiểm remote website trong lượt này.

| Nhóm QA | Kết quả Phase1 | Boundary |
| --- | --- | --- |
| Markdown/local links và SVG refs | PASS | Local paths resolved;GitHub links là pinned blobs đã inspect |
| Commits/run IDs/schemas | PASS | D05–D09 baselines và artifact identities đối chiếu nguồn |
| Metrics/arithmetic | PASS | D07 sum/coverage;D08 medians/speedup rounding;D09 sum33 |
| Scope/labels | PASS | Không invent IT counts;Full NOT EXECUTED;A04/Q07 PENDING |
| Evidence integrity | PASS | D09 receipts,old protected snapshot,ZIP size/SHA/member count khớp |
| Reproduction safety | PASS với giới hạn đã ghi | D05 overwrite;D09 exact-HEAD guard;new run IDs/isolated checkout |
| Team/production acceptance | PENDING | Không thuộc QA tự động của tài liệu |

## 5. Nộp ngay và phần phải chờ

Nộp ngay được: chương source/cleaning/canonical, schema/grain/provenance, D07
ALL-JOBS staging, D08 local experiment/charts, D09 available validation và appendix
source/hash. Dùng captions đúng scope; không đổi available PASS thành final PASS.

Phải chờ: workbook/approvals, Full predictions và business metrics IT, A05 official,
Q07 publication policy, official analytics/dashboard, full-pipeline timing nếu yêu
cầu, delivery acknowledgement và nghiệm thu nhóm. Chưa ký D10/D11 hoàn tất100%.

Next safe step: nhóm review4 tài liệu → thống nhất người ký và cung cấp workbook/
approvals → mở task thực thi D06 Full riêng khi được phép → bổ sung evidence mới
theo D11. Không commit/push hoặc chạy Full trong lượt Phase1 này.

**D10 AVAILABLE TECHNICAL DOCS: PASS.**
**D11 AVAILABLE HANDOFF DOCS: PASS.**
**D10–D11 FINAL INTEGRATION: PENDING D06 FULL AND TEAM ACCEPTANCE.**
**D06 FULL: NOT EXECUTED.**
