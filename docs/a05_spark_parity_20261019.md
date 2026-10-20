# A05 — sửa dependency Spark local và kiểm chứng phát triển

Đồng Viết Dũng – TV2, 19/10/2026, `feat/tv2-analysis`. Không chạy lại A01–A04, D04/D05/D06 hoặc A05 production. Dictionary/extractor **v0.1.2 giữ nguyên**; workbook review 661 evidence vẫn là quyết định đề nghị, không áp nhãn kỹ năng hoặc điền người/ngày duyệt.

## Nguyên nhân và phương án

Đã đọc trọn 12 log lịch sử trong `tmp/tv2_d05_receipt_457f90ae/`; kích thước/hash từng log, kết quả đọc file nguồn và ACL được lưu tại [runtime_diagnostics.json](../data/analytics/a05_spark_parity_20261019/runtime_diagnostics.json).

Môi trường chạy: `.venv` Python 3.11.9; PySpark 4.2.0; Temurin Java 21.0.12.1 portable; Hadoop client 3.5.0. Java trên PATH hệ thống vẫn 8, nên wrapper đặt JAVA_HOME/PATH chỉ cho tiến trình. Các file `src/tech_skill_extractor.py`, `description_processing.py`, `tv2_csv.py` đọc được, ACL người dùng có quyền; không đổi ACL. WSL hiện chưa cài, không tự cài thành phần hệ thống.

Lỗi chặn gốc: đường dẫn `.py` tuyệt đối được `SparkContext.addPyFile → addFile → Utils.fetchFile` sao chép vào SparkFiles; tiếp theo Spark gọi trực tiếp **Hadoop FileUtil.chmod(a+x), rồi u+r trên Windows**. Hadoop tra HADOOP_HOME/hadoop.home.dir để tìm winutils, nhưng không có. Đây không phải lỗi phân tách mô tả, scope kỹ năng hoặc quyền đọc `.py`. Lỗi classpath adapter ở lần thử cũ đã được giải quyết riêng. Không tăng quyền đọc nguồn để chữa lỗi executable bị thiếu.

Căn cứ chính thức:

- [Spark Python packaging](https://spark.apache.org/docs/latest/api/python/tutorial/python_packaging.html): `.py/.zip/.egg` qua addPyFile, --py-files hoặc spark.submit.pyFiles; đổi kiểu gói không loại bỏ nhu cầu fetch.
- [Spark 4.2.0 Utils.scala](https://github.com/apache/spark/blob/v4.2.0/core/src/main/scala/org/apache/spark/util/Utils.scala): fetchFile gọi FileUtil.chmod trực tiếp.
- [Spark 4.2.0 SparkContext.scala](https://github.com/apache/spark/blob/v4.2.0/core/src/main/scala/org/apache/spark/SparkContext.scala): addFile fetch tại driver; local: không được add vào file server, vì đã phải có trên từng node. Không dùng local: URI như một cách tự động phân phối Python.
- [Spark configuration](https://spark.apache.org/docs/latest/configuration.html): executorEnv/Python executable và PYTHONPATH là môi trường cần cung cấp rõ cho worker. Nguồn [PythonRunner](https://github.com/apache/spark/blob/v4.2.0/core/src/main/scala/org/apache/spark/api/python/PythonRunner.scala) mô tả chạy Python worker riêng.

Không tải winutils từ nguồn bên ngoài, không tạo executable giả, không monkey-patch chmod hoặc bỏ test. Không sửa adapter filesystem D05 của repo. Session Parquet tái sử dụng **adapter D05 hiện hữu**, có hành vi bỏ các thao tác quyền POSIX trên Windows; vì vậy readback chỉ chứng minh trong môi trường local của repo, không chứng minh native Hadoop Windows permission semantics. Giải pháp dependency mới không sửa hoặc gọi giả FileUtil.chmod.

## Thay đổi adapter, không thay đổi nghiệp vụ v0.1.2

[a05_spark.py](../src/a05_spark.py) thêm hai mode tường minh:

- `add_pyfile` vẫn là mặc định, dành cho môi trường có file distribution hoạt động. Bổ sung cả module `a05_spark.py` vì closure/record conversion cũng cần module này ở worker. Chưa chứng minh đường này hoạt động trên Windows thiếu winutils hoặc trên cluster.
- `shared_local_pythonpath`: chỉ chấp nhận master `local`/`local[...]`; từ chối remote và local-cluster. Worker phải import được bốn module từ **đúng đường dẫn, đúng SHA-256 như driver**; probe chạy bằng Spark RDD trước trích. Không có fallback âm thầm. Wrapper khai báo PYTHONPATH=repo/src và đúng venv executable trước khi tạo context. Đây là môi trường Python dùng chung trên một máy, **không phải cơ chế ship code đa node**.

Snapshot adapter cũ và hash đầu vào nằm tại `data/analytics/a05_spark_parity_20261019/a05_spark_before.py` và `protected_before.json`. Không đổi schema output, alias, rule hoặc dictionary. Hash code mới và bảo toàn đầu vào được ghi trong audit cuối.

## Phạm vi parity và lịch sử chạy

[Runner phát triển](../src/verify_a05_spark_parity.py) lấy đúng 105 ID từ input manifest A05 đã có, text từ snapshot A04 đóng băng; kiểm hash workbook và từng description so với processing v0.1.2. Không đọc toàn canonical để tự chọn IT. Các cột membership cần cho adapter chỉ được tạo **trong memory fixture phát triển**, ghi rõ `DEV_MANUAL_MEMBERSHIP_FIXTURE/NOT_D06`, không xuất D06 giả.

Python được so trước với evidence/processing đóng băng. Spark được so **toàn bộ record**, gồm job_id/skill_code, danh sách mention_types, mention_type, accepted/excluded/ambiguous, evidence_id/quote, source ranges, mọi offset, hash, processing status/provenance và danh sách kỹ năng. Run_id evidence giữ giá trị baseline để so exact ID; thư mục/manifest lần kiểm chứng mới tách biệt. Sau đó ghi/đọc cả ba Parquet và so nội dung exact với Python; kiểm bridge khớp 355 cặp đóng băng. Không dùng các dự đoán kỹ năng làm gold label hoặc tính accuracy.

Lượt `run01`: 355 bridge, 661 evidence, 105 processing đều full-record parity và Parquet PASS. Hai controls bổ sung sau đó gặp Python worker EOF/host socket aborted khi input mặc định 12 partitions, nên manifest tổng **FAIL** được giữ nguyên. Chưa xác định nguyên nhân sâu của lỗi socket bằng stack này. Không kết luận lỗi skill hoặc đã sửa mọi lỗi Windows. Lần sau dùng default.parallelism=2, shuffle=2 và bật faulthandler; regression kiểm lại missing/zero-hit/Parquet.

Regression [tests.txt](../data/analytics/a05_spark_parity_20261019/regression01/tests.txt): **64 case, 63 PASS, 0 FAIL/error, 1 real-D06 SKIP**. Bao gồm guard dependency remote/unknown mode, unit extractor/review/contract/report, D05 thật schema 50 và source hashes 105 ID, Q05 synthetic missing/NULL/duplicate/conflict, A05 synthetic distributed parity/Parquet và Q06 zero-hit denominator. Không chạy lại ba test truy vấn đã PASS lượt trước chỉ để lặp số kiểm thử.

**Lượt run02 PASS trọn vẹn**, dùng default.parallelism=2, shuffle=2; [manifest](../data/analytics/a05_spark_parity_20261019/run02/parity_manifest.json), log `tmp/tv2_a05_parity_20261019/run02.log`. Không ghi đè run01.

| Kiểm chứng trên mẫu phát triển | Kết quả |
| --- | --- |
| Tập ID thủ công đã duyệt / text nguồn | 105 ID; đúng hash workbook và description baseline |
| job_skill_technical | 355 record, full-record Python parity + Parquet readback PASS |
| technical_skill_evidence | 661 record, full-record Python parity + Parquet readback PASS |
| skill_source_processing | 105 record, full-record Python parity + Parquet readback PASS |
| Trạng thái mẫu phát triển | 78 WITH_MATCH, 27 NO_MATCH; không phải thống kê toàn IT |
| Controls bổ sung, tách khỏi 105 | SOURCE_MISSING và PROCESSED_NO_MATCH đúng Python |

Lỗi socket run01 không tái hiện với cấu hình run02 và regression, nhưng chưa có chẩn đoán sâu để khẳng định Windows ổn định với mọi concurrency. Không chuyển kết quả local thành tuyên bố multi-node parity, nghiệm thu extractor hoặc accuracy kỹ năng. [Audit cuối](../data/audit/tv2_a05_spark_parity_20261019.json) lưu version/hash, thay đổi được phép và bảo toàn nguồn.

## Tái chạy và phụ thuộc

Chỉ tái chạy khi có thay đổi/runtime hoặc lỗi cần kiểm, luôn dùng output/log mới:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tmp/tv2_a05_parity_20261019/run.ps1 -OutputDirectory data/analytics/a05_spark_parity_20261019/next_run -LogPath tmp/tv2_a05_parity_20261019/next_run.log
```

Wrapper dùng JDK portable đã có, PYSPARK_PYTHON/PYSPARK_DRIVER_PYTHON của venv và PYTHONPATH rõ ràng. Nó không thay Java hoặc biến môi trường hệ thống. Lệnh regression đã lưu tại `tmp/tv2_a05_parity_20261019/tests.ps1`; muốn chạy lại phải chọn tên output/log mới trong wrapper trước, không ghi đè regression01.

A05 official vẫn **BLOCKED D06 Full + nguồn text/provenance được TV1 xác nhận + review skill thực tế**. Chọn mode shared local cho production cũng cần ghi rõ phạm vi single-host; cluster cần môi trường cài dependency đồng nhất hoặc packaging được kiểm tra riêng. Không tự promote taxonomy candidate hoặc chuyển 105 mẫu thành production. Chưa xác minh parity A04 Spark/JVM, multi-node Spark, hoặc native Windows Hadoop permission behavior.

A06–A11 kế thừa [kế hoạch Q01–Q08](tv2_q01_q08_publication_plan.md), [adapter Q05 candidate](../src/d05_job_functions_adapter.py) và [bộ báo cáo/slide chuẩn bị mới](../data/analytics/tv2_a06_a11_prepared_20261019/reports/a11_slides.html). D06 cần xác nhận `description` đưa vào A05 tương ứng D05.source_description/hash nguồn; Q05 cần chốt embedded job_functions hoặc bridge/mapping riêng; Q07 chờ D07 đã duyệt. Không công bố số liệu IT/lương từ các kiểm thử này.
