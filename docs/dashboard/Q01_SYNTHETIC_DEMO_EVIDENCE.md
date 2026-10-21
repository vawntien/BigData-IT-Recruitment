# Q01 Synthetic Demo — Evidence bàn giao

Task `TV3-DR03C-04E-01`; kiểm tra mới ngày **2026-10-21**, timezone **UTC+07:00**.
Phạm vi: documentation + local demo evidence; không sửa source/tests, không
commit/push. Đây là evidence synthetic, không official analytics acceptance.

Quy ước: **VERIFIED** = đối chiếu source/Git/environment; **TESTED** = đã chạy
automated tests; **OBSERVED** = kết quả thực thu được; **NOT RUN** = chưa thực hiện;
**PENDING** = còn chờ evidence hoặc quyết định upstream.

## A. Exact Git baseline

VERIFIED: branch `feat/tv3-dashboard`, HEAD
`570bbd6101e8eef006b0650fff9af132058f6090`.
Precheck `git status --short` và `git diff --cached --name-only` đều rỗng.
Published N01/N02 test hardening nằm ở baseline này; không phải thay đổi mới của
task evidence. Hai tài liệu bàn giao mới chưa được commit.

## B. Published component inventory

| Repository-relative path | Vai trò đã đối chiếu |
|---|---|
| `dashboard/app.py` | Streamlit entrypoint, navigation qua thư mục pages |
| `dashboard/pages/4_Q01_Synthetic_Demo.py` | Checkbox riêng mặc định OFF, render curated synthetic findings |
| `dashboard/components/q01_demo.py` | Fresh fixed fixture/spec/plan/mapping, published adapter, presentation guard |
| `dashboard/components/q01_adapter.py` | Q01 synthetic logical checks và curated result |
| `dashboard/components/validation_orchestrator.py` | Required synthetic validation plan execution |
| `dashboard/components/consumer_adapter.py` | Synthetic origin/schema boundary; không production authorization |
| `dashboard/components/artifact_gate.py` | Readable real artifact vẫn BLOCKED |
| `dashboard/tests/test_q01_demo_page.py` | 37 AppTests, gồm N01/N02 hardening |
| `dashboard/tests/test_q01_demo.py` | 31 demo unit tests |

Luồng: Page ON → helper tạo fresh in-memory inputs → Q01 Adapter → Orchestrator
→ Consumer Envelope/schema validation rồi metric validation → Q01 result checks
→ helper presentation guard → bar chart/table. UI không tự cấp quyền từ envelope.

## C. Published source SHA-256

VERIFIED bằng PowerShell `Get-FileHash -Algorithm SHA256` tại baseline:

| File | SHA-256 |
|---|---|
| `dashboard/pages/4_Q01_Synthetic_Demo.py` | `73DCF380F0DF41C305B4443FE8F48C6AE7E083103B6D29674CA5E5178AAC2A4D` |
| `dashboard/components/q01_demo.py` | `F50A3EC642F0CBDB3C51453BEDCA15DC4EB60E686D9A58BCEA30DDBB1CE12466` |
| `dashboard/components/q01_adapter.py` | `7D391C60B0C8EDC034F090CA54871A3EA12FB210762386E9B26A99F23B50DE81` |
| `dashboard/components/validation_orchestrator.py` | `CCFE4579697A9D7C5E63E0566E024D9743808BDC4A804F66AF07EDF1BE572465` |
| `dashboard/components/consumer_adapter.py` | `19EF09C9E2A4964686A1F5E0AB9AC50E813FFA10C72BD25B520BA55ECE7FB4A4` |
| `dashboard/components/artifact_gate.py` | `F3032F95606AD8020135DB1BD80FD60598805B55F1AE60E94C76F3C095C17949` |
| `dashboard/tests/test_q01_demo_page.py` | `148465DB9EE5DFE5D14BC6857AA6E84E8F9528CBA68365DCD6F09428468B487E` |
| `dashboard/tests/test_q01_demo.py` | `555215DD09223FDCA670307DFFEDE3909FC29CED827F4FDED8EB3C1FD0B18EEC` |

Các hash nhận diện đúng file đã publish; không chứng minh nghiệp vụ đã được phê duyệt.

## D. Test command et environment

VERIFIED: Windows PowerShell, existing `.venv`, Python **3.11.9**, Streamlit
**1.38.0**, pandas **2.3.3**, pyarrow **25.0.1**. Không cài thêm package.
Mỗi suite chạy bằng:

```powershell
.\.venv\Scripts\python.exe -B dashboard/tests/test_q01_demo_page.py
```

Thay basename bằng từng suite trong mục E; script đủ 13 suite đã có tại mục O
của `Q01_SYNTHETIC_DEMO_RUNBOOK.md`. Các unittest files dùng direct runner;
data_loader/sample_contracts dùng script assertions. Không dùng pytest hoặc Spark.

## E. Actual regression results

**TESTED mới trong task này**, không sao chép historical PASS thành execution mới:

| File trong `dashboard/tests/` | PASS | FAIL | SKIP |
|---|---:|---:|---:|
| `test_q01_demo_page.py` | 37 | 0 | 0 |
| `test_q01_demo.py` | 31 | 0 | 0 |
| `test_q01_adapter.py` | 73 | 0 | 0 |
| `test_validation_orchestrator.py` | 58 | 0 | 0 |
| `test_consumer_adapter.py` | 57 | 0 | 0 |
| `test_partition_summary_validator.py` | 46 | 0 | 0 |
| `test_cross_table_validator.py` | 43 | 0 | 0 |
| `test_metric_validator.py` | 38 | 0 | 0 |
| `test_contract_validator_foundation.py` | 31 | 0 | 0 |
| `test_data_loader.py` | 3 | 0 | 0 |
| `test_sample_contracts.py` | 4 | 0 | 0 |
| `test_overview_page.py` | 2 | 0 | 0 |
| `test_artifact_gate.py` | 16 | 0 | 0 |
| **Tổng thực chạy** | **439** | **0** | **0** |

Tất cả suite exit code 0; unittest báo OK, hai script assertion báo PASSED.
Không sửa test để đạt PASS. AppTest không phải browser capture.

## F. Streamlit launch evidence

**OBSERVED mới:** Lệnh dưới khởi động thành công, terminal báo
`You can now view your Streamlit app in your browser.` và URL
`http://127.0.0.1:8517`:

```powershell
.\.venv\Scripts\python.exe -B -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8517 --server.headless true --browser.gatherUsageStats false --server.fileWatcherType none
```

Đã dừng server bằng Ctrl+C sau khi browser tool không khả dụng. Kiểm tra
`Get-NetTCPConnection -LocalPort 8517 -State Listen -ErrorAction SilentlyContinue`
cho **0 listeners**. Không public bind/deploy hoặc background server để lại.

## G. Initial OFF observation

**TESTED bằng AppTest; browser OBSERVATION NOT RUN trong task này.**
Test xác nhận checkbox default False, permanent label, disabled explanation,
không fixture/adapter call, chart/table/B/context findings.
Không dùng browser smoke lịch sử để tuyên bố đã quan sát lại.

## H. Explicit ON observation

**TESTED bằng AppTest; browser OBSERVATION NOT RUN.**
Real published adapter positive control PASS. AppTest kiểm tra actual rendered
chart element, curated table, B=10 và context/taxonomy. Đây là automated evidence.

## I. Expected chart/table values

| Synthetic category | Count | B | Chart Share % | Table Share % |
|---|---:|---:|---:|---:|
| DEMO_A | 8 | 10 | 80.0 | 80.00 |
| DEMO_B | 7 | 10 | 70.0 | 70.00 |
| DEMO_UNKNOWN | 1 | 10 | 10.0 | 10.00 |

**TESTED:** Named Arrow payload được giải mã theo dataset name trong actual
Vega-Lite spec; mark bar, quantitative Share %, đúng mapping và tổng 160%.
Table được kiểm tra độc lập. Stored-Fraction variant có chart 80.0123 và table
80.01, dùng probe-only tolerance; không thay đổi production policy.

Fixture không có DISTINCT-job lineage. Overlap được khai báo, nên không cộng
counts thành B hoặc normalize tỷ lệ. Unknown được giữ nguyên. Context cố định:
`DEMO_RUN / DEMO_POP / DEMO_ALL`, taxonomy `DEMO_TAXONOMY`.

## J. ON → OFF observation

**TESTED bằng AppTest; browser OBSERVATION NOT RUN.**
OFF loại bỏ chart/table/B. Các test hardening còn xác nhận bảy chuyển trạng thái
success→schema failure / metric failure / malformed result / adapter exception /
empty findings / missing checks / invalid denominator trên cùng AppTest instance.
Không findings cũ, validated context/taxonomy hoặc canary leakage.

## K. Browser screenshot inventory

**SCREENSHOTS NOT CAPTURED.** Browser tool trả:
`Local browser use is disabled in Work settings`.
Vì không có actual browser capture an toàn, không tạo ảnh giả, placeholder hoặc
file PNG; không đổi setting hoặc tìm đường vòng để chụp desktop.

| Đường dẫn dự kiến | Trạng thái |
|---|---|
| `docs/dashboard/evidence/q01_demo_off.png` | NOT CAPTURED; file không tồn tại |
| `docs/dashboard/evidence/q01_demo_on.png` | NOT CAPTURED; file không tồn tại |

Nhóm có thể chạy runbook, mở riêng browser Q01 và chụp thủ công OFF rồi ON.
Ảnh OFF cần page identity/banner/disabled state, không findings; ảnh ON cần
identity/banner/B=10/chart/table/Unknown/overlap note. Chỉ chụp Q01, không desktop,
secrets hoặc app khác; không chỉnh sửa ảnh để bịa phần thiếu. Sau đó tắt demo,
kiểm tra findings biến mất, dừng server và ghi nhận ngày thực quan sát.

## L. Data access isolation scope

**VERIFIED / TESTED:** Q01 page/helper dùng fresh in-memory synthetic data;
không legacy loader, CSV/Parquet source reads, private ZIPs hoặc analytics discovery.
Tests dùng reader/loader spies và synthetic fault injections.
Không đọc D05/D07 handoff, chạy D06/A05 official, TV2 analytics hoặc Spark.

Giới hạn xác nhận isolation này chỉ dành Q01 page/helper và các tests nêu trên.
Legacy loader có thể đọc thử analytics khi Sample OFF trước khi chặn hiển thị;
không khẳng định mọi legacy page không bao giờ đọc real files.

## M. Known technical limitations

- SYNTHETIC DEMO ONLY; fixed fixture, single context, không real analytics integration.
- Không official physical Q01 mapping, approved occupational taxonomy hay accepted
  DISTINCT-job provenance; không dùng ALL JOBS làm accepted IT population.
- Không Q02–Q08 adapters, joint filters, real-data authorization hoặc public deployment.
- N01/N02: TEST COVERAGE COMPLETED tại baseline published; không business acceptance.
- Deferred: mutable schema dictionaries trong frozen plans; direct ConsumerEnvelope
  constructor invariants; cross-table issue ordering; assertion-helper strictness;
  production metric tolerance policy cần được duyệt.

## N. Pending upstream dependencies

**PENDING PRODUCTION:** accepted D06 Full IT dataset; official A05 dictionary/release;
accepted official TV2 analytics handoff; approved Q01 physical mapping; accepted
job population và DISTINCT-job lineage; approved occupational taxonomy và
business-approved metric policy.

**Production Gate CLOSED.** Data Contract giữ **DISCUSSION DRAFT / NOT APPROVED /
NOT PRODUCTION READY**. Không thay contract/gate/source/tests/sample data.

## O. Final handoff assessment

**DOCUMENTED:** Runbook tiếng Việt, walkthrough, script 2–3 phút, verified launch/test
commands, expected values và limitations đã đủ cho text-only handoff.
**TESTED:** 439 PASS / 0 FAIL / 0 SKIP thực chạy mới.
**OBSERVED:** Local server start thành công và listener cleanup hoàn tất.
**NOT RUN:** Browser OFF/ON/OFF walkthrough mới.
**PENDING:** Hai actual screenshot và visual evidence mới khi browser khả dụng.

Text-only handoff hoàn tất, sẵn sàng team review; visual evidence chưa hoàn tất.
Không tuyên bố screenshot/browser PASS hoặc official Q01 acceptance.
