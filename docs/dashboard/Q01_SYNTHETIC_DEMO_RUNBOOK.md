# Q01 Synthetic Demo — Hướng dẫn chạy và trình bày

## A. Mục đích và phạm vi

Demo giúp nhóm quan sát luồng kiểm tra dữ liệu trước khi trực quan hóa Q01.
Trạng thái luôn là **SYNTHETIC DEMO ONLY**: dữ liệu giả định, tạo trong bộ nhớ,
không phải thống kê tin tuyển dụng CNTT thực tế trên LinkedIn.

Tài liệu bàn giao dạng text đã hoàn tất. Browser walkthrough và ảnh mới của
đợt evidence này chưa thực hiện được; xem `Q01_SYNTHETIC_DEMO_EVIDENCE.md`.

## B. Điều kiện môi trường

Mở PowerShell tại thư mục gốc repository, nơi có `dashboard/app.py`.
Dùng môi trường `.venv` đã chuẩn bị cho project, không cần activate hoặc đổi
ExecutionPolicy. Không cần nạp dataset, chạy Java/Spark hay pipeline để demo.

Môi trường đã kiểm tra: Python 3.11.9, Streamlit 1.38.0, pandas 2.3.3,
pyarrow 25.0.1. Kiểm tra Python và Streamlit bằng:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -B -c "import streamlit; print(streamlit.__version__)"
```

Nếu thiếu `.venv` hoặc dependency, nhờ người phụ trách chuẩn bị môi trường theo
README; không đổi dependencies trong lúc trình bày. Không dùng Python global
thay cho interpreter của project.

## C. Branch và commit bàn giao

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
```

Baseline: branch `feat/tv3-dashboard`, published commit
`570bbd6101e8eef006b0650fff9af132058f6090`.
Các lệnh trên chỉ đọc trạng thái. Nếu checkout khác baseline, đối chiếu với nhóm;
không tự reset, merge hoặc đổi branch để chạy theo hướng dẫn này.

## D. Khởi động Streamlit trên Windows

Tại repository root, chạy lệnh đã được xác minh khởi động thành công:

```powershell
.\.venv\Scripts\python.exe -B -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8517 --server.headless true --browser.gatherUsageStats false --server.fileWatcherType none
```

Lệnh dùng entrypoint hiện tại, bind loopback, tắt usage statistics và file watcher.
`-B` tránh tạo Python bytecode. Giữ cửa sổ PowerShell mở khi trình bày.
Không đổi bind address thành `0.0.0.0`, không bấm Deploy hoặc dùng public tunnel.

## E. Mở Dashboard

Sau khi terminal báo URL, tự mở [Dashboard local](http://127.0.0.1:8517/)
trên cùng máy. `headless=true` có nghĩa là server không tự mở browser.
Trang chủ là scaffold; các trạng thái pipeline trên trang chủ không phải evidence
nghiệm thu Q01 hiện tại. Không cần mở các trang analytics legacy.

## F–H. Mở trang Q01 và bật demo có chủ đích

1. Khởi động server theo mục D.
2. Chọn **Q01 Synthetic Demo** ở navigation bên trái. Nếu sidebar thu gọn,
   mở sidebar trước. Trang nguồn là `dashboard/pages/4_Q01_Synthetic_Demo.py`.
3. Trong session mới, xác nhận checkbox **Enable Q01 synthetic demo** đang OFF.
4. Xác nhận nhãn **SYNTHETIC DEMO ONLY**, dòng **No real IT recruitment findings**
   và thông báo `DEMO_DISABLED`. Không được có chart, table, B hoặc validated context.
5. Tick checkbox để opt-in. Không có upload, chọn file hoặc cấu hình nguồn thật.
6. Xác nhận **Declared synthetic denominator B = 10**.
7. Xác nhận bar chart, bảng curated và các giá trị tại mục I.
8. Giải thích overlap và tổng 160% theo mục J–K.
9. Bỏ tick checkbox.
10. Xác nhận chart, table, B, context và taxonomy findings biến mất; banner demo vẫn còn.

Các bước trên là quy trình mong đợi dựa trên source và AppTest đã PASS.
Đợt bàn giao này chưa quan sát browser mới do local browser tool bị tắt.

## I. Dữ liệu synthetic mong đợi

| Category | Count | Share % |
|---|---:|---:|
| DEMO_A | 8 | 80.00 |
| DEMO_B | 7 | 70.00 |
| DEMO_UNKNOWN | 1 | 10.00 |

B chung = 10; context `DEMO_RUN / DEMO_POP / DEMO_ALL`;
taxonomy demo `DEMO_TAXONOMY`. Các ID là nhãn giả định, không phải tên nghề hoặc
taxonomy chính thức. B không được suy ra bằng cộng 8 + 7 + 1.

## J. Đọc bar chart

Trục category dùng các ID synthetic; trục định lượng là **Share %**.
Table có Count để đối chiếu, nhưng bar chart đang biểu diễn tỷ lệ, không phải Count.
Share được lấy từ stored Fraction đã qua validation rồi nhân 100 tại presentation;
không tính lại từ Count/B. Table làm tròn hai chữ số thập phân.
Thứ tự hiển thị không phải thứ hạng nghề chính thức.

## K. Vì sao tổng là 160%?

Demo khai báo `MAY_OVERLAP`: một phần tử giả định có thể thuộc nhiều nhóm.
Vì vậy 80% + 70% + 10% = 160% không phải partition rời nhau.
Không normalize về 100%, không dùng pie/donut và không coi tổng Count=16 là B.
Khai báo overlap này chỉ dành cho demo, không quyết định taxonomy nghiệp vụ của nhóm.

## L. Vì sao giữ Unknown?

`DEMO_UNKNOWN` được khai báo trong domain và có count/share riêng. Giữ nhãn này
giúp người xem không bỏ qua nhóm chưa xác định. Policy là `KEEP_IF_PRESENT`;
không tự bịa Unknown nếu nguồn hợp lệ không có nó.

## M. Failure và an toàn

Khi ON, helper tạo fresh DataFrame/spec/plan/mapping, gọi Q01 Adapter đã publish.
Adapter gọi Orchestrator; schema boundary dùng Consumer Envelope và generic
schema validator, sau đó chạy metric check. Presentation guard kiểm tra toàn bộ
result trước khi chart/table được tạo.

Nếu schema/metric không hợp lệ hoặc dependency trả result sai, UI chỉ hiển thị
controlled status/code; không có partial findings, B/context cũ hoặc fallback
sang CSV/real data. Ví dụ `ORCHESTRATION_FAILED`, `INVALID_Q01_RESULT`,
`DEMO_EXECUTION_EXCEPTION`. Không sửa code/dữ liệu để cố tạo failure trên sân khấu;
các tình huống này đã có regression tests.

Checkbox Q01 dùng state riêng. Không cache DataFrame/plan/result/findings.
OFF không tạo fixture hoặc gọi adapter. Chỉ Q01 page/helper nằm trong phạm vi
synthetic isolation đã test; không khẳng định legacy loaders không đọc file thật.

## N. Dừng Streamlit

Quay về PowerShell đã chạy server, nhấn **Ctrl+C** và chờ process kết thúc.
Kiểm tra listener bằng lệnh chỉ đọc:

```powershell
Get-NetTCPConnection -LocalPort 8517 -State Listen -ErrorAction SilentlyContinue
```

Không có kết quả nghĩa là không còn TCP listener trên port đó. Nếu còn listener,
kiểm tra terminal/process mình vừa khởi động; không tùy tiện kill process khác.

## O. Chạy regression

Chạy tại repository root. Script chạy tuần tự 13 suite, dừng ở suite lỗi và in
kết quả thật; không tạo log file. Baseline hiện tại: 439 PASS / 0 FAIL / 0 SKIP.

```powershell
$suites = @(
    'test_q01_demo_page.py',
    'test_q01_demo.py',
    'test_q01_adapter.py',
    'test_validation_orchestrator.py',
    'test_consumer_adapter.py',
    'test_partition_summary_validator.py',
    'test_cross_table_validator.py',
    'test_metric_validator.py',
    'test_contract_validator_foundation.py',
    'test_data_loader.py',
    'test_sample_contracts.py',
    'test_overview_page.py',
    'test_artifact_gate.py'
)
foreach ($suite in $suites) {
    Write-Output $suite
    & .\.venv\Scripts\python.exe -B "dashboard\tests\$suite"
    if ($LASTEXITCODE -ne 0) { throw "Test suite failed: $suite" }
}
```

AppTest là automated UI execution, không thay thế quan sát browser trực tiếp.
Tests của gate/loader có thể dùng synthetic temporary fixtures ngoài repository;
không cần cung cấp dataset thật. N01/N02 đã có permanent tests: chart Arrow payload,
stored-Fraction variant và bảy success-to-failure reruns.

## P. Xử lý lỗi thường gặp

| Triệu chứng | Kiểm tra tối thiểu |
|---|---|
| Không tìm thấy Python/entrypoint | Đang ở repository root? Có `.venv/Scripts/python.exe` và `dashboard/app.py`? |
| Thiếu Streamlit/module | Xác nhận interpreter `.venv`; nhờ nhóm chuẩn bị environment, không cài ngẫu nhiên lúc demo. |
| Port 8517 đang dùng | Kiểm tra listener; dừng server cũ của mình hoặc thống nhất port loopback khác với nhóm. Lệnh evidence chỉ xác minh port 8517. |
| Browser không kết nối | Terminal đã báo URL và còn chạy? Mở đúng `127.0.0.1:8517` trên cùng máy. |
| Không thấy trang Q01 | Kiểm tra branch/commit và filename trong `dashboard/pages/`; không cần mở analytics legacy. |
| Không có chart khi OFF | Đây là behavior đúng. Tick riêng checkbox Q01 để opt-in. |
| ON báo controlled error | Ghi code và commit để báo TV3; không đổi gate, schema hoặc dùng dữ liệu thật làm fallback. |
| AppTest có ScriptRunContext/Altair warnings | Xem exit code và tổng PASS/FAIL; warning không tự chứng minh test thất bại hoặc thành công. |

Nếu muốn bổ sung ảnh thủ công: chỉ chụp cửa sổ/browser Q01, tránh desktop và dữ
liệu cá nhân. Chụp OFF rồi ON, bảo đảm ON thấy B/chart/table/Unknown/overlap note;
có thể tăng chiều cao cửa sổ. Không ghép hoặc vẽ thêm thành phần còn thiếu.
Hai đường dẫn dự kiến là `docs/dashboard/evidence/q01_demo_off.png` và
`docs/dashboard/evidence/q01_demo_on.png`; hiện chưa có các file này.

## Q. Giới hạn và phụ thuộc

Fixed in-memory fixture, single analytical context; không official physical Q01
mapping, approved occupational taxonomy hoặc accepted DISTINCT-job lineage.
Chưa accepted D06 Full IT dataset, official A05 release, accepted TV2 analytics
handoff và approved production metric tolerance policy. Zero tolerance của demo
không phải policy production. Q02–Q08 không được triển khai trong bàn giao này.

## R. Cảnh báo production và lời dẫn 2–3 phút

**Production Gate CLOSED. Data Contract: DISCUSSION DRAFT / NOT APPROVED /
NOT PRODUCTION READY.** Chạy demo hoặc 439 tests PASS không đáp ứng official
business acceptance. Không suy ra ALL JOBS = IT jobs, không công bố tỷ lệ demo
như kết quả đồ án và không deploy publicly.

Gợi ý lời dẫn, kết hợp thao tác và chỉ vào từng thành phần:

> **0:00–0:30:** Đây là demo Q01 để minh họa cơ cấu category và luồng kiểm tra
> trước trực quan hóa. Nhãn SYNTHETIC DEMO ONLY luôn hiện vì các con số đều giả
> định. Session mới đang OFF nên chưa có kết quả phân tích nào.
>
> **0:30–1:10:** Tôi chủ động bật checkbox. Ứng dụng tạo fixture trong bộ nhớ,
> đưa qua schema/metric validation và Q01 Adapter đã publish. Chỉ result hợp lệ
> mới qua presentation guard để tạo chart và bảng. B=10 là mẫu số được khai báo,
> không phải tổng Count của ba hàng.
>
> **1:10–1:50:** Bar chart thể hiện 80%, 70% và 10%; bảng còn cho biết counts
> 8, 7, 1. DEMO_UNKNOWN vẫn được giữ lại. Các nhóm demo được phép overlap nên
> tổng là 160%; ta không normalize về 100% hay dùng pie chart. Đây không phải
> taxonomy nghề được nhóm phê duyệt hoặc kết quả tuyển dụng LinkedIn thực tế.
>
> **1:50–2:30:** Tôi tắt demo: chart, bảng, B và context phải biến mất. Nếu lần
> chạy bị lỗi validation, hệ thống cũng chỉ trả code an toàn và không giữ kết quả
> cũ. Regression đã kiểm tra các chuyển trạng thái lỗi, nhưng không cần sửa code
> để diễn lỗi ở đây. Nguồn analytics thật, taxonomy, lineage và acceptance vẫn
> chờ TV1/TV2; Production Gate đang đóng.
