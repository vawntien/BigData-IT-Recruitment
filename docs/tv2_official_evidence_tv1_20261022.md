# TV2 → TV1: Enriched / Q01 actual evidence — 22/10/2026

**Technical evidence PASS; Git synchronization BLOCKED; nghiệm thu TV1 PENDING.** Q01/Q02/Q03/Q04/Q08 vẫn VALIDATED — NOT ACCEPTED.

## Kết quả kiểm tra

| Evidence | Kết quả |
|---|---|
| Enriched actual Parquet/schema/receipt/manifest/completion | PASS: 5.206 rows/distinct IDs, 39 fields, 47/47 evidence checks |
| Q01 CSV/Parquet/schema/manifest/independent validation/completion | PASS: N=K5.206, missing0, 10 groups, sum job_count5.206; shares khớp1 theo tolerance gốc |
| Original independent validation | PASS 94/94 shared checks; không gọi94 checks Q01-only |
| D06 ACCEPT reconciliation | PASS: thiếu0/thừa0, 27 trường D06 giữ nguyên |
| D05 exact source inventory/selected values | PASS |
| Taxonomy/classifier reference pins | PASS v0.2.2 và receipt-pinned snapshot hash |
| Gói lineage57 files đã giao TV3 | PASS CRC/inventory/read-back/exact contract binding |
| Gói Q01 Official22 files | PASS CRC/all22 member hashes/inventory; CSV/Parquet giống core đã read-back |
| Q02/Q03/Q04/Q08 từ Downloads | PASS checksum/CRC/inventory/schema/read-back và đối chiếu exact Enriched |
| ZIP tổng inventory/CRC/membership/extracted read-back | PASS |

Digest Enriched tính lại: `17ae5383e848f7323b99800bd3d79a72e84e2bca62844f66dd00aaa06e80a9b2`. Thuật toán sort toàn bộ files trong jobs.parquet, JSON compact các tuple [relative POSIX path, bytes, SHA file], UTF-8 rồi SHA256; gồm marker thực có. Không phải ZIP SHA/part SHA/fingerprint D05. Code recompute và verifier portable có trong README_TV1.md.

Exact Q01 input proof: manifest nhúng contract object, contract SHA `70b0df1fe4e0e6d18cf27dc016c34eceabc9f7df284ba6c58563884bbccdf02c`, path/digest, analyzer SHA; đối chiếu receipt và Enriched metadata seal, taxonomy và bytes payload. Không chỉ so population. Không giả định analyzer đọc riêng input_receipt/source_binding trực tiếp.

## Git và exact provenance

Live remote được kiểm bằng `git ls-remote origin refs/heads/feat/tv2-analysis`. Local HEAD, tracking ref và GitHub đều `3c7c6285a59af8ae9eebfdc2d3667f3fcff92180`; do đó TV1 chỉ thấy commit này là đúng trạng thái remote.

Hai báo cáo `docs/tv2_enriched_input_20261022.md`, `docs/q01_official_validation_20261022.md` **có local nhưng untracked/chưa committed/chưa trên remote branch HEAD**.

| Code | Historical branch/checkout ghi nhận | Commit thực của script |
|---|---|---|
| Materializer Enriched | feat/tv2-analysis / 3c7c6285a59af8ae9eebfdc2d3667f3fcff92180, trong producer manifest | NOT FOUND: untracked; bind snapshot SHA6f0a6b9360a7d3049dfe824231122cc912ec08a94ba28c57aa92f432820b37c2 |
| Q01 analyzer | feat/tv2-analysis / 3c7c6285… trong handoff manifest; main manifest chỉ code hash | Tracked, last-change8323b5b9f4025ec4909ead912aafbef6c5825e6c, có trong checkout3c7c6285…; LF/CRLF phân biệt dưới đây |
| Independent validator | feat/tv2-analysis / 3c7c6285… trong validation | NOT FOUND: untracked; bind SHA3064fc323b48dc57e8f5c8eb2ef89e77f68fc592f60965de4e21f5db59b8ffee |

Analyzer executed bytes SHA `58ae37b667b3b31b91739e31357af25a68f434a81eb6adf556b0e9dc9911dc89` (Windows349 CRLF) khác HEAD Git blob SHA `0b5934af1b7278ec673433d931845bbcb17b66ebd9171196ccfd1e16bda2ee53` (LF), nhưng source content bằng nhau sau CRLF→LF. Giữ cả hai snapshot/hash, không normalize lại producer bytes để ép hash match. Historical checkout không chứng minh untracked scripts nằm trong commit đó. Không thay producer checkout bằng commit tài liệu mới.

**Không stage/commit/push:** working tree có A05/Q06 untracked ngoài phạm vi; user yêu cầu dừng Git khi có thay đổi không liên quan. Không có conflict tracked, nhưng điều kiện unrelated-files đã đủ chặn. Danh sách candidate text/code để review riêng nằm trong gói; không commit ZIP/Parquet/descriptions/raw/secrets. Commit bàn giao mới: NONE.

## ZIP tổng và đường dẫn giao

ZIP nguồn: `C:\Users\dongv\BigData-IT-Recruitment\tmp\TV2_OFFICIAL_EVIDENCE_TV1_20261022.zip`.

ZIP giao: `C:\Users\dongv\Downloads\TV2_OFFICIAL_EVIDENCE_TV1_20261022\TV2_OFFICIAL_EVIDENCE_TV1_20261022.zip`.

**36.847.881 bytes; 249 files. SHA-256:**

```text
00398be4308291fa496f55f39d8c3356d7bec71779c2c54d30e3e7fa692a06c2
```

ZIP chứa actual Enriched và Q01, metadata/seals/receipt/47-94 checks/code snapshots/Git evidence/hai báo cáo gốc/D05-D06 lineage, Q02-Q04/Q08 byte-exact evidence, README_TV1 và inventory. Không có full D05/D06123.849 jobs hoặc A05 outputs. Không chạy lại production. Aggregate và nested package inventories đều được kiểm; giải nén mới rồi read-back tất cả các bảng bằng DuckDB1.4.1. Cấu trúc core reuse57 files, archive Q01 cũ22 files và query packages độc lập; không regenerate dữ liệu.

Audit: `data/audit/tv2_official_evidence_tv1_20261022.json`, `data/audit/tv2_tv1_git_provenance_20261022.json`. Gói có verifier receiving riêng, không chạy producer scripts.

## TV1 kiểm định và phần còn thiếu

TV1 kiểm external ZIP SHA/CRC, extract mới, cài requirements-receiving.txt, chạy `python -B verify_evidence.py --report ../tv1_receiving.json`. Để tự đối chiếu upstream, thêm `--d05 <Canonical jobs> --d06 <D06 Full predictions>`; không cấp paths thì kết quả upstream NOT_REQUESTED, không gọi là TV1 đã kiểm lại upstream. Dùng đúng source snapshots; report ngoài immutable package. README trong gói có hướng dẫn recompute digest.

Blockers còn lại: TV1 independent receiving/acceptance; remote review chưa có hai báo cáo/scripts; không thể cung cấp committed revision cho materializer/validator vốn untracked. Snapshot hashes/provenance đủ để kiểm bytes, không bịa Git history. Shared-layout adapter và display mapping approval vẫn PENDING riêng, không tự suy ra từ receiving PASS. Không merge main, không cấp BUSINESS ACCEPTED.

Tin nhắn gửi TV1:

> TV2 gửi bộ actual evidence Enriched/Q01 và Q02–Q04/Q08, 36.847.881 bytes/249 files. SHA-256 00398be4308291fa496f55f39d8c3356d7bec71779c2c54d30e3e7fa692a06c2. TV2 kiểm CRC/inventory/read-back/exact Enriched lineage và D06 ACCEPT reconciliation PASS. Nhờ TV1 chạy verifier theo README để nghiệm thu độc lập. Q01 vẫn VALIDATED, chưa ACCEPTED. GitHub vẫn3c7c6285…; báo cáo và materializer/validator chưa commit, đã ghi rõ snapshot hashes và giới hạn provenance; chưa push vì có unrelated A05/Q06 files.
