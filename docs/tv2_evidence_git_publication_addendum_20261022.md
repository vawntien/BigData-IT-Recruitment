# TV2 → TV1: Git publication addendum — 22/10/2026

Phạm vi: công bố chọn lọc báo cáo và code/audit Enriched/Q01 lên `origin/feat/tv2-analysis`. Đây là **commit bàn giao tài liệu và snapshot**, không phải producer commit hoặc lần chạy production mới. Q01 vẫn **VALIDATED — NOT ACCEPTED**. Không cấp business acceptance A05 và không thay đổi công việc A05/Q06.

## Evidence và hồ sơ lịch sử

ZIP đã gửi TV1 giữ nguyên:

```text
TV2_OFFICIAL_EVIDENCE_TV1_20261022.zip
36.847.881 bytes / 249 files
SHA-256: 00398be4308291fa496f55f39d8c3356d7bec71779c2c54d30e3e7fa692a06c2
```

Bản giao ở `C:/Users/dongv/Downloads/TV2_OFFICIAL_EVIDENCE_TV1_20261022/`; bản nguồn trong `tmp/`. Không sửa hoặc đóng gói lại ZIP. Các báo cáo và audit trước đây ghi Git synchronization BLOCKED/untracked/chưa push là **trạng thái tại thời điểm tạo evidence trước publication**; giữ nguyên để không viết lại lịch sử. Addendum này mô tả bước publication tiếp theo do người dùng cho phép commit chọn lọc mà vẫn giữ các file ngoài phạm vi. Không đọc trạng thái Git cũ trong ZIP thành kết luận remote hiện tại.

Commit chính xác của bước publication là commit **introduce addendum này**, tra bằng:

```text
git log -1 --format=%H -- docs/tv2_evidence_git_publication_addendum_20261022.md
```

Full SHA sau push được đối chiếu với live `git ls-remote origin refs/heads/feat/tv2-analysis` và ghi trong addendum vận chuyển **ngoài ZIP**. Không ghi SHA tự tham chiếu vào nội dung commit, không sửa producer manifest.

## Producer / validator provenance

Historical branch là `feat/tv2-analysis`, checkout ghi nhận trong Enriched manifest, Q01 handoff manifest và independent validation là `3c7c6285a59af8ae9eebfdc2d3667f3fcff92180`. Main Q01 runner manifest chỉ ghi code/contract hashes, không có trường producer branch/commit; không bịa thêm.

| Artifact code | SHA-256 bytes lúc chạy | Version-control provenance |
|---|---|---|
| `data/audit/tv2_materialize_enriched_20261022.py` | `6f0a6b9360a7d3049dfe824231122cc912ec08a94ba28c57aa92f432820b37c2` | Untracked lúc chạy; được công bố lần đầu ở commit publication này. Không chứng minh script đã nằm trong checkout lịch sử. |
| `data/audit/tv2_validate_q01_official_20261022.py` | `3064fc323b48dc57e8f5c8eb2ef89e77f68fc592f60965de4e21f5db59b8ffee` | Untracked lúc kiểm định; được công bố lần đầu ở commit publication này, không retroactive producer revision. |
| `src/a06_a08_spark_analysis.py` | `58ae37b667b3b31b91739e31357af25a68f434a81eb6adf556b0e9dc9911dc89` | Đã tracked; không sửa hoặc stage lại. Tracked last-change commit `8323b5b9f4025ec4909ead912aafbef6c5825e6c`, có trong historical checkout3c7c6285… |

Analyzer Windows snapshot có349 CRLF, Git blob có LF, SHA Git blob `0b5934af1b7278ec673433d931845bbcb17b66ebd9171196ccfd1e16bda2ee53`. Đã kiểm nội dung bằng nhau sau CRLF→LF, nhưng không tuyên bố bytes/hash giống nhau. ZIP có cả runtime snapshot và Git LF snapshot. Hai historical scripts giữ đúng bytes/hash, được bảo vệ bởi `.gitattributes` hiện hữu `data/audit/tv2_* -text`; không đổi logic hoặc thêm approval.

## Files công bố

- `docs/tv2_enriched_input_20261022.md`: báo cáo input/47 checks và receipt lịch sử; mở đầu đã chỉ rõ metadata hashes trước encoding correction.
- `docs/q01_official_validation_20261022.md`: kết quả official/94 shared checks và metadata hashes sau correction.
- `docs/tv2_official_evidence_tv1_20261022.md`: evidence tổng/Git snapshot trước publication.
- `docs/tv2_q02_q03_q04_q08_handoffs_20261022.md`: inventory, schemas và hashes các gói liên quan.
- Hai historical scripts ở bảng trên.
- `data/audit/tv2_enriched_validation_20261022.json`: 47/47 PASS, không có descriptions hoặc job-level raw dataset.
- `data/audit/tv2_q01_official_validation_20261022.json`: 94/94 PASS, aggregates/taxonomy/provenance; bytes khớp original validation trong gói.
- `data/audit/tv2_enriched_q01_exact_lineage_verification_20261022.json`: read-only receiving audit, exact D05/D06 reconciliation và actual input digest.
- `data/audit/tv2_official_evidence_tv1_20261022.json`: kết quả đóng gói/hash; trường Git BLOCKED/new_commit=null là snapshot trước publication.
- Addendum này.

Chỉ stage các đường dẫn cụ thể; không `git add .`, `git add -A`, `git commit -a`. Không stage các file A05/Q06, ZIP, Parquet, raw dataset, credentials hoặc ignored outputs. Local paths trong audit phục vụ provenance, không phải yêu cầu các path đó tồn tại trên máy TV1.

## Cách review và tái kiểm định an toàn

Đối chiếu code/audit bằng SHA-256 và Git blob của commit publication. AST parse scripts chỉ kiểm cú pháp, không được gọi là tái chạy hoặc validation production mới. Trạng thái 47/94 checks là evidence của lần chạy cũ, đã đối chiếu hash.

**Không chạy hoặc import hai historical scripts** để receiving: chúng có top-level execution và ghi audit; không dùng chúng để tự ghi lại official evidence. Muốn thực thi một run mới phải có nhiệm vụ/namespace/receipt và runtime preflight riêng, ngoài phạm vi publication.

Để TV1 receiving độc lập, dùng `verify_evidence.py` **đã có trong ZIP** theo README_TV1.md: stdlib checksum/inventory + DuckDB1.4.1 read-back, không Spark/production. Có thể cấp `--d05` và `--d06` cho exact upstream comparison; report mới đặt ngoài immutable package. Không cấp upstream thì ghi NOT_REQUESTED, không nhận vơ upstream PASS.

Physical nullability: schema Q01 trong report/audit gốc là Spark read-back (cả sáu nullable); Parquet writer/footer có job_count và hai denominator REQUIRED. ZIP có writer schema riêng. Không sửa physical schema hoặc numbers trong publication. Original manifest date literal2026-10-19 vẫn giữ nguyên; ngày chạy thực theo created_utc/run ID2026-10-22.

Các giới hạn chưa được publication giải quyết: TV1 independent receiving/acceptance, display mapping approval và shared classification namespace adapter. Không tự cấp ACCEPTED từ việc có commit hoặc push. Publication không thể chứng minh materializer/validator đã được commit tại thời điểm production; chỉ công bố exact historical snapshots ở thời điểm hiện tại.
