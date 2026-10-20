# TV2 — tiếp nhận D05 và tiếp nối A05–A11

Ngày 19/10/2026; nhánh giữ nguyên `feat/tv2-analysis`. Hồ sơ này cập nhật tình trạng D05 so với [bàn giao trước](tv2_current_handoff.md), không sửa hồ sơ A01–A04 hoặc quyết định người đọc.

## D05 đã kiểm tra trực tiếp

Đã fetch `origin/feat/tv1-d05-official`, xác nhận commit **457f90ae4c8074a468ec6ac8f410dd31bbbb4a6b**, không merge/cherry-pick/switch. Snapshot 23 file báo cáo, schema, manifest, validation, reconciliation, regression và code nằm tại `tmp/tv2_d05_receipt_457f90ae/tv1_snapshot/`; checksum nằm trong `snapshot_manifest.json` cùng thư mục.

Người dùng xác nhận đây là bàn giao D05 chính thức. Báo cáo trong commit vẫn ghi `IMPLEMENTATION PASS — READY FOR ACCEPTANCE REVIEW`, nghiệm thu nhóm `PENDING GROUP REVIEW`. Run manifest ghi base HEAD `fbfcb59c...`, khác commit đóng gói `457f90ae...`; không sửa lịch sử để hai giá trị giống nhau. 72 kiểm tra validation và 5 regression của TV1 báo PASS; đây là bằng chứng do TV1 lưu, khác kiểm tra readback TV2 dưới đây. Trong cây commit được bàn giao chưa có code D06; trạng thái D06 có code/test nhưng chưa Full là thông tin người dùng cung cấp, chưa được kiểm tra từ một commit D06 riêng.

Người dùng đã xác nhận trực tiếp đường dẫn bàn giao **`C:\Users\dongv\BigData-IT-Recruitment\data\processed\jobs`**, chính là bộ đã kiểm tra: 4 part Snappy Parquet và `_SUCCESS`, tổng 397.164.694 byte. Tiếp nhận dưới dạng thư mục đã giải nén; không cần ZIP để mở khóa readback. Không tạo ZIP thay thế hoặc giả nhận đã kiểm CRC archive.

| Kiểm tra TV2 bằng Spark 4.2.0 | Kết quả |
| --- | --- |
| Số dòng / job_id duy nhất | 123.849 / 123.849 |
| job_id null | 0 |
| Số cột | 50 |
| Schema đầy đủ, kể cả nested/type/nullability | Khớp `d05_canonical_schema.json` tại commit TV1 |
| canonical_schema_version | Chỉ `d05-v1` |
| SHA-256 UTF-8 của source_title/source_description | 0 sai lệch so với cột hash lưu trong Parquet |
| Sao chép và checksum từng part | PASS; nguồn không thay đổi |

Đích đã đặt: **`data/processed/canonical/jobs/`**, gồm đúng 4 part gốc và `_SUCCESS`. Đích chưa tồn tại trước khi tạo; không ghi đè hoặc di chuyển bộ `data/processed/jobs/`. Dữ liệu processed tiếp tục bị Git ignore.

[Audit tiếp nhận](../data/audit/tv2_d05_receipt_457f90ae.json) lưu checksum từng file, snapshot TV1, schema compatibility và đối soát A04. Readback gốc và schema thực tế: `tmp/tv2_d05_receipt_457f90ae/readback01/`.

Giới hạn provenance: manifest TV1 không có checksum part/ZIP. CRC archive không áp dụng cho đầu vào thư mục người dùng xác nhận; chưa chứng minh exact bytes trùng output lần chạy TV1 chỉ bằng số dòng/schema. Việc đọc hash text ở đây xác minh tính nhất quán nội bộ Parquet; không chạy lại kiểm tra toàn raw hoặc ETL của TV1. Audit readback đầu tiên ghi trạng thái chưa có phản hồi về ZIP; [kết quả cuối](../data/audit/tv2_d05_final_457f90ae.json) bổ sung xác nhận thư mục này, giữ nguyên audit trước.

## A04 — gói bàn giao nhãn đã chốt

Đã đọc workbook nguồn chính 160 dòng, bổ sung 17 dòng và hai workbook quyết định `docs/a04_review_decisions_chot.xlsx` (83), `docs/a04_remaining93_chot.xlsx` (93), header ở dòng 6. Không chọn workbook chỉ dựa vào tên hoặc thời gian sửa.

Đã xác minh nhãn, nhóm/subgroup, lý do, evidence nguyên văn, người duyệt và ngày duyệt khớp **176 quyết định duy nhất**. Từng quote evidence tồn tại trong trường title/description được chỉ định. Hai nguồn trùng một job_id và khớp metadata. Người duyệt nguồn là Dũng, ngày 13/10/2026; không tự điền ngày/người mới. Tổng hợp hợp hai nguồn: 105 CNTT, 67 NGOAI_CNTT, 4 CHUA_RO, chỉ là mẫu phát triển/rà soát.

Gói để người dùng chuyển TV1, chưa gửi qua ứng dụng bên ngoài:

- [ZIP hiện vật đã có](../tmp/tv2_d05_receipt_457f90ae/a04_verified_handoff_v2/a04_tv1_verified_existing_artifacts.zip).
- [Manifest checksum](../tmp/tv2_d05_receipt_457f90ae/a04_verified_handoff_v2/manifest.json) và [bảng nhãn đối chiếu](../tmp/tv2_d05_receipt_457f90ae/a04_verified_handoff_v2/manual_labels_verified.csv).

ZIP giữ bytes workbook, hai bảng chốt, code/config candidate v0.2.2, source snapshot, trace, stages và báo cáo bàn giao hiện có. Đây là gói tiếp nhận/parity reference, không phải chạy lại classifier hoặc tuyên bố nghiệm thu A04. Active v0.2.0 và candidate v0.2.2 giữ nguyên. Không áp lại quyết định, tính lại accuracy hoặc dùng 176 nhãn làm D06 production. Thư mục đóng gói lần đầu còn trống do thiếu `sample_id` ở mẫu bổ sung; bản v2 đã xử lý đúng metadata có sẵn, không sửa workbook.

## A05–A11 và hợp đồng D06 cần chốt

Giữ nguyên extractor/dictionary v0.1.2, bridge phát triển 355 cặp, workbook 661 evidence và 5 đề nghị bổ sung. Audit review trước vẫn hợp lệ, workbook không đổi. Reviewer/ngày duyệt skill vẫn trống: **PROPOSED_NOT_APPROVED**, không áp đề nghị. A05 official **BLOCKED D06**, không chạy trên 123.849 canonical hoặc thay bằng 105 tin phát triển.

Đối chiếu schema D05: 12 trường nền cần cho adapter/phân tích đều có đúng kiểu, gồm bigint job_id, nullable boolean remote_allowed, UTC TimestampType, location/work type/experience. Hai điểm chưa được tự quyết:

1. D05 `description` là text D04 sạch, `source_description` là nguyên văn đã parse CSV. A05 hiện nhận `D06.description` nhưng ghi evidence nguồn `postings.description`; TV1 phải bảo đảm description đưa vào A05 chính là `source_description` với hash nguồn tương ứng, hoặc duyệt adapter mới rõ ràng. Không âm thầm gán offset nguyên văn cho text đã làm sạch. A04 parity cũng cần title/description nguồn đúng candidate.
2. D05 canonical chứa `job_functions: array<struct<skill_abr,skill_name,mapping_status>>`, trong khi Q05 hiện nhận bridge job_skills và mapping skills riêng. Chưa có các clean bridge chính thức tại máy. TV1 cần bàn giao chúng kèm hash, hoặc chốt projection từ mảng canonical, deduplicate job_id/skill_abr và kiểm mapping trước khi tích hợp. Không lấy raw thay contract và không suy job_functions thành kỹ năng kỹ thuật.

| Hạng mục | Trạng thái sau tiếp nhận |
| --- | --- |
| D05 canonical | Readback PASS, đã đặt đúng đích; provenance archive còn giới hạn trên |
| A05 | Mã/schema/test sẵn có; official BLOCKED D06 và review skill |
| A06 Q01–Q05 | Candidate; schema nền phù hợp; BLOCKED D06, Q05 thêm contract bridge |
| A07 Q06 | Candidate; mẫu số gồm successful zero-hit; BLOCKED A05 official bridge/status cùng run |
| A08 Q07/Q08 | BLOCKED D07/D06; D05 salary_record không thay salary_clean đã duyệt |
| A09–A11 | Giữ khung báo cáo/10 slide ở followup01; số liệu IT/lương chờ run official SUCCESS |

Không tạo thêm dữ liệu giả hoặc báo cáo thị trường từ fixture. Tái sử dụng [analyzer](../src/a06_a08_spark_analysis.py), [A05 adapter](../src/a05_spark.py), [schema candidate](../config/tv2_analysis_output_schema.json), [input contract](../config/tv2_analysis_inputs.example.json) và [bộ báo cáo đã chuẩn bị](../data/analytics/tv2_a05_a11_followup01/reports/a10_analysis_report.md). Chưa điền approval/path D06/D07 giả để đổi trạng thái.

## Môi trường, kiểm thử và bước tiếp theo

Đã cài đúng `pyspark==4.2.0` từ requirements vào `.venv`; JDK Temurin 21 portable trong `tmp/tv2_d05_receipt_457f90ae/runtime/`. Chỉ đặt JAVA_HOME/PATH cho tiến trình chạy, không đổi Java hệ thống. Windows adapter dùng source TV1 tại commit bàn giao, build trong `tmp/d04-localfs/`. Không sửa mã ETL/TV1 hoặc taxonomy.

Suite hiện hữu: **55 test case PASS, 1 real-D06 test SKIP, 1 lỗi setUpClass** làm 6 phương thức synthetic chưa thực thi. Lỗi tại `SparkContext.addPyFile → FileUtil.chmod`: Windows thiếu HADOOP_HOME/winutils.exe. Không phải lỗi rule hoặc bằng chứng để sửa extractor. Windows filesystem adapter của D05 không chặn đường chmod trực tiếp này. Không đổi lỗi thành SKIP/PASS. Wrapper lần đầu dừng do PowerShell coi warning stderr là lỗi; lần tiếp theo thiếu classpath adapter; cả log lỗi được giữ, bản sau dùng đúng session helper của repo và xác định blocker chmod nêu trên.

[Tóm tắt đếm test đúng](../tmp/tv2_d05_receipt_457f90ae/a05_tests03_summary.json), [log suite](../tmp/tv2_d05_receipt_457f90ae/a05_tests03/tests.txt), lệnh tại `tmp/tv2_d05_receipt_457f90ae/run_tests.ps1`. Lưu ý bộ đếm sơ bộ trong `a05_tests03/tests.json` ghi 54 pass vì trừ cả lỗi setUpClass khỏi testsRun; lỗi class setup không thuộc test case đã chạy. Tóm tắt riêng đối chiếu 55 dòng `... ok`, không ghi đè log sơ bộ.

Chạy riêng các kiểm tra không gọi extractor để tiếp tục công việc độc lập tại `run_data_only.ps1`: fixtures truy vấn/grain/multilabel/lương tách đơn vị và smoke schema A05 Parquet rỗng. Đây không thay thế parity A05 có dữ liệu. Real D06 không được thay thế bằng fixture. Python/Spark parity A05 khác với parity taxonomy A04/JVM: chưa xác minh parity A04 Spark/JVM.

[Bốn ca truy vấn độc lập PASS](../tmp/tv2_d05_receipt_457f90ae/data_only_tests01/tests.txt): Q01/Q02/Q03/Q04/Q08 mẫu số/độ thiếu/thời gian; từ chối job_id trùng; Q05 multilabel giữ grain; Q07 giữ riêng currency/pay period/source. Đây là fixtures synthetic có kiểm soát, không có ý nghĩa thống kê IT. Bộ 5 ca lần đầu có 1 FAIL tại smoke schema A05 vì test so cả `containsNull=False` của schema tạo DataFrame với `containsNull=True` sau Parquet. Đã sửa kỳ vọng test theo chính sách readback nới nullability (so `simpleString`, vẫn kiểm tên/thứ tự/kiểu), giữ nguyên schema/extractor v0.1.2 và log thất bại; chỉ chạy lại ca schema, không chạy lại 4 ca truy vấn đã PASS.

[Ca schema chạy lại PASS](../tmp/tv2_d05_receipt_457f90ae/schema_only_tests02/tests.txt): cả ba schema A05 ghi/đọc Parquet rỗng đúng tên/thứ tự/kiểu, 0 dòng. Kết quả cuối cho kiểm tra độc lập: **4 ca truy vấn PASS + 1 ca schema PASS**. Không đồng nghĩa A05 distributed extraction/parity đã PASS; đường `addPyFile` vẫn lỗi runtime. Không chạy lại các test đã đạt.

[Kiểm tra bảo toàn](../data/audit/tv2_d05_receipt_preservation_457f90ae.json): 138 đầu vào ghi nhận trong lượt này và 172 file bảo vệ từ lượt trước vẫn khớp hash, gồm raw/workbook/code/config/hồ sơ cũ; branch không đổi, index không có thay đổi staged.

Ưu tiên tiếp theo: TV1 giao D06 Full + manifest/hash/schema + xác nhận text/candidate; xử lý runtime phân phối mã A05 và chốt contract Q05 (checksum part D05 từ TV1 bổ sung provenance nếu có); bàn giao D07 salary_clean cùng chính sách/coverage trước Q07. Sau D06 mới chạy A05 official, kiểm Parquet và source provenance, rồi phân tích/report bằng mã hiện có. Không commit/push/merge.

Lệnh tái kiểm tra, luôn chọn thư mục output mới (không chạy lại chỉ để đổi trạng thái):

```powershell
$env:JAVA_HOME = (Resolve-Path 'tmp/tv2_d05_receipt_457f90ae/runtime/jdk-21.0.12.1+1').Path
$env:PATH = "$env:JAVA_HOME/bin;$env:PATH"
$env:SPARK_LOCAL_IP = '127.0.0.1'
.\.venv\Scripts\python.exe tmp/tv2_d05_receipt_457f90ae/verify_delivery.py --input data/processed/canonical/jobs --output tmp/tv2_d05_receipt_457f90ae/readback02
powershell -NoProfile -ExecutionPolicy Bypass -File tmp/tv2_d05_receipt_457f90ae/run_data_only.ps1 -OutputDirectory tmp/tv2_d05_receipt_457f90ae/data_only_tests02
# Sau khi xử lý runtime phân phối source; chưa phải lệnh A05 official:
powershell -NoProfile -ExecutionPolicy Bypass -File tmp/tv2_d05_receipt_457f90ae/run_tests.ps1 -OutputDirectory tmp/tv2_d05_receipt_457f90ae/a05_tests04
```

Verifier cũng nhận `--input <jobs.zip>` để kiểm CRC, chặn path traversal/symlink, giải nén vào output mới rồi kiểm Spark. Không dùng `--publish` khi canonical hiện đã tồn tại; verifier từ chối ghi đè. Gói A04 hiện tại dùng để bàn giao, không cần chạy lại script đóng gói.
