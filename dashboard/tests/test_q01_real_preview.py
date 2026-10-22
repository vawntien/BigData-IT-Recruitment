"""Synthetic package fixtures and AppTest; no production data stored or opened.

The pinned hash is patched ONLY in tests to exercise downstream rejection paths.
The public receiver has no hash/taxonomy/tolerance override parameter.
"""

from contextlib import ExitStack
import csv
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import warnings
import zipfile

import pyarrow as pa
import pyarrow.parquet as pq
import streamlit as st
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components import q01_real_preview as q
from components import data_loader, q01_candidate_receiver, artifact_gate


def encoded(value):
    return json.dumps(value, separators=(",", ":")).encode()


def rows():
    # Artificial skew, deliberately different from real aggregate findings.
    result = []
    for i, code in enumerate(sorted(q.DOMAIN)):
        count = 5121 if i == 0 else 77 if code == "IT_OTHER" else 1
        result.append(dict(zip(q.COLUMNS, (code, count, 5206, 5206, count / 5206, count / 5206))))
    return result


def fixture(change_rows=None, change_documents=None, change_schema=None,
            entry_change=None, stale_inventory=False, stale_seal=False, csv_change=None):
    data = rows()
    if change_rows:
        change_rows(data)
    schema = pa.schema([pa.field(n, t, nullable=nullable) for n, t, nullable in zip(
        q.COLUMNS, (pa.string(), pa.int64(), pa.int32(), pa.int32(), pa.float64(), pa.float64()),
        (True, False, False, False, True, True))])
    if change_schema:
        schema = change_schema(schema)
    table = pa.Table.from_pylist(data, schema=schema)
    sink = io.BytesIO()
    pq.write_table(table, sink)
    payload = {n: b"{}" for n in q.MEMBERS}
    payload[q.PART] = sink.getvalue()
    payload["q01_role_groups.parquet/_SUCCESS"] = b""
    csv_rows = [dict(r) for r in data]
    if csv_change:
        csv_change(csv_rows)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=q.COLUMNS)
    writer.writeheader()
    writer.writerows(csv_rows)
    payload["q01_role_groups.csv"] = b"\xef\xbb\xbf" + stream.getvalue().encode()
    payload["q01_official_validation_20261022.md"] = ("Synthetic test evidence: " + q.D06_RUN).encode()
    taxonomy = [{"taxonomy_version": "0.2.2", "taxonomy_sha256": q.TAXONOMY_SHA}]
    directory = [[n.split("/", 1)[1], len(payload[n]), q._sha(payload[n])]
                 for n in sorted((q.PART, "q01_role_groups.parquet/_SUCCESS"))]
    digest = q._sha(encoded(directory))
    package = {"run_id": q.RUN_ID, "business_accepted": False, "q01_status": "VALIDATED",
               "business_group_acceptance": "PENDING", "taxonomy_version": "0.2.2",
               "taxonomy_sha256": q.TAXONOMY_SHA, "source_commit": q.SOURCE_COMMIT,
               "N": 5206, "K": 5206, "missing": 0,
               "q01_parquet_artifact_digest": digest,
               "q01_csv_sha256": q._sha(payload["q01_role_groups.csv"])}
    manifest = {"run_id": q.RUN_ID, "provenance": {"taxonomy": taxonomy},
                "input_contract": {"d06_confirmation": {"input_sha256": q.INPUT_DIGEST}},
                "tables": {"q01_role_groups": {"parquet_sha256": digest}}}
    handoff = {"run_id": q.RUN_ID, "business_accepted": False, "status": "VALIDATED",
               "accepted_by": None, "taxonomy": taxonomy, "source_commit": q.SOURCE_COMMIT,
               "confirmed_input_digest": q.INPUT_DIGEST, "N": 5206, "K": 5206, "missing": 0,
               "physical_table": {"parquet_sha256": digest,
                                  "csv_sha256": q._sha(payload["q01_role_groups.csv"])}}
    checks = {"fixture_check_" + str(i): {"pass": True} for i in range(93)}
    checks["exact_d06_accept_population"] = {"pass": True, "detail": {"missing": 0, "extra": 0}}
    validation = {"run_id": q.RUN_ID, "business_accepted": False, "status": "PASS",
                  "q01_status": "VALIDATED", "commit": q.SOURCE_COMMIT, "input_digest": q.INPUT_DIGEST,
                  "checks": checks, "taxonomy_groups": [{"code": x} for x in sorted(q.DOMAIN)],
                  "q01": {"status": "VALIDATED", "accepted": False, "N": 5206, "K": 5206,
                          "missing": 0, "taxonomy_version": "0.2.2", "taxonomy_sha256": q.TAXONOMY_SHA}}
    readback = {"type": "struct", "fields": [{"name": n, "type": t, "nullable": True, "metadata": {}}
                for n, t in zip(q.COLUMNS, ("string", "long", "integer", "integer", "double", "double"))]}
    docs = {"package": package, "manifest": manifest, "handoff": handoff,
            "validation": validation, "readback": readback}
    if change_documents:
        change_documents(docs)
    payload["manifest.json"] = encoded(manifest)
    payload["independent_validation/q01_role_groups_schema.json"] = encoded(readback)
    validation["runner_manifest_sha256"] = q._sha(payload["manifest.json"])
    payload["independent_validation/validation.json"] = encoded(validation)
    seal = {"run_id": q.RUN_ID, "business_accepted": False, "status": "PASS",
            "validation_sha256": q._sha(payload["independent_validation/validation.json"]),
            "runner_manifest_sha256": q._sha(payload["manifest.json"])}
    if stale_seal:
        seal["validation_sha256"] = "0" * 64
    payload["independent_validation/completion.json"] = encoded(seal)
    handoff["evidence"] = {n: q._sha(payload[n]) for n in
                           ("manifest.json", "independent_validation/validation.json",
                            "independent_validation/completion.json",
                            "independent_validation/q01_role_groups_schema.json")}
    payload["q01_handoff_manifest.json"] = encoded(handoff)
    package["original_source_bytes"] = {n: q._sha(payload[n]) for n in q.MEMBERS - {
        "SHA256_INVENTORY.json", "PACKAGE_MANIFEST.json", "README_TV3.md", "DATA_CONTRACT_Q01.md"}}
    payload["PACKAGE_MANIFEST.json"] = encoded(package)
    inventory = {"algorithm": "SHA256", "excludes_self": True, "files": [
        {"path": n, "bytes": len(payload[n]), "sha256": q._sha(payload[n])}
        for n in sorted(q.MEMBERS - {"SHA256_INVENTORY.json"})]}
    if stale_inventory:
        inventory["files"][0]["sha256"] = "0" * 64
    payload["SHA256_INVENTORY.json"] = encoded(inventory)
    target = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
            for name in sorted(payload):
                info = zipfile.ZipInfo(q.ROOT + name)
                if entry_change:
                    entry_change(info, name)
                archive.writestr(info, payload[name])
    return target.getvalue()


class ReceivingTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "synthetic.zip"

    def receive(self, data=None, **kwargs):
        data = fixture(**kwargs) if data is None else data
        self.path.write_bytes(data)
        with patch.object(q, "EXPECTED_SHA256", q._sha(data)):
            return q.load_q01_preview(str(self.path), confirmed=True)

    def reject(self, result, code=None):
        self.assertFalse(result.passed)
        self.assertEqual(result.rows, ())
        if code:
            self.assertEqual(result.issue, code)
        self.assertLess(len(result.issue), 80)

    def test_valid_package_and_immutable_sorted_rows(self):
        result = self.receive()
        self.assertTrue(result.passed, result.issue)
        self.assertEqual(len(result.rows), 10)
        self.assertEqual(sum(r.job_count for r in result.rows), 5206)
        self.assertEqual([r.job_count for r in result.rows], sorted((r.job_count for r in result.rows), reverse=True))
        self.assertFalse(hasattr(result, "production_eligible"))

    def test_no_read_without_confirmation(self):
        with patch.object(Path, "open", side_effect=AssertionError("unexpected read")):
            self.reject(q.load_q01_preview("PRIVATE_PATH"), "CONFIRMATION_REQUIRED")

    def test_invalid_paths_do_not_echo(self):
        for value in (None, "", "relative.zip", "\\\\private\\secret.zip", "//private/secret.zip"):
            with self.subTest(kind=type(value).__name__):
                result = q.load_q01_preview(value, confirmed=True)
                self.reject(result, "INVALID_LOCAL_PATH")
                self.assertNotIn("private", repr(result))

    def test_wrong_sha_prevents_parquet_decode(self):
        self.path.write_bytes(fixture())
        with patch.object(pq, "ParquetFile", side_effect=AssertionError("premature decode")) as spy:
            self.reject(q.load_q01_preview(str(self.path), confirmed=True), "ARCHIVE_HASH_MISMATCH")
        spy.assert_not_called()

    def test_corrupt_zip(self):
        self.reject(self.receive(b"not a ZIP"), "UNREADABLE_OR_INVALID_ARTIFACT")

    def test_crc_damage(self):
        data = bytearray(fixture())
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entry = archive.infolist()[0]
            offset = entry.header_offset + 30 + len(entry.filename.encode()) + len(entry.extra)
        data[offset] ^= 1
        self.reject(self.receive(bytes(data)))

    def test_traversal(self):
        self.reject(self.receive(entry_change=lambda i, n: setattr(i, "filename", "../outside") if n == q.PART else None), "UNSAFE_ARCHIVE")

    def test_duplicate_entry(self):
        self.reject(self.receive(entry_change=lambda i, n: setattr(i, "filename", q.ROOT + "README_TV3.md") if n == q.PART else None), "UNSAFE_ARCHIVE")

    def test_symlink(self):
        def link(info, name):
            if name == q.PART:
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.reject(self.receive(entry_change=link), "UNSAFE_ARCHIVE")

    def test_internal_hash_failure_before_decode(self):
        with patch.object(pq, "ParquetFile", side_effect=AssertionError("premature decode")) as spy:
            self.reject(self.receive(stale_inventory=True), "INVENTORY_MISMATCH")
        spy.assert_not_called()

    def test_wrong_run(self):
        self.reject(self.receive(change_documents=lambda d: d["package"].update(run_id="WRONG")), "RUN_MISMATCH")

    def test_wrong_taxonomy(self):
        self.reject(self.receive(change_documents=lambda d: d["package"].update(taxonomy_sha256="0" * 64)), "TAXONOMY_MISMATCH")

    def test_wrong_input_digest(self):
        self.reject(self.receive(change_documents=lambda d: d["handoff"].update(confirmed_input_digest="0" * 64)), "LINEAGE_MISMATCH")

    def test_stale_completion_seal(self):
        self.reject(self.receive(stale_seal=True), "EVIDENCE_BINDING_MISMATCH")

    def test_failed_validation(self):
        self.reject(self.receive(change_documents=lambda d: d["validation"]["checks"]["fixture_check_0"].update({"pass": False})), "VALIDATION_FAILED")

    def test_validated_not_accepted(self):
        self.reject(self.receive(change_documents=lambda d: d["handoff"].update(business_accepted=True)), "ACCEPTANCE_MISMATCH")

    def test_missing_column(self):
        self.reject(self.receive(change_schema=lambda s: pa.schema(list(s)[:-1])), "INVALID_PHYSICAL_SCHEMA")

    def test_extra_column(self):
        self.reject(self.receive(change_schema=lambda s: s.append(pa.field("extra", pa.string()))), "INVALID_PHYSICAL_SCHEMA")

    def test_wrong_column(self):
        self.reject(self.receive(change_schema=lambda s: pa.schema([pa.field("wrong", s[0].type), *list(s)[1:]])), "INVALID_PHYSICAL_SCHEMA")

    def test_wrong_integer_width(self):
        self.reject(self.receive(change_schema=lambda s: s.set(2, pa.field(q.COLUMNS[2], pa.int64(), nullable=False))), "INVALID_PHYSICAL_SCHEMA")

    def test_unrelated_nullability_not_ignored(self):
        self.reject(self.receive(change_schema=lambda s: s.set(0, pa.field("category", pa.string(), nullable=False))), "INVALID_PHYSICAL_SCHEMA")

    def test_wrong_readback_schema(self):
        self.reject(self.receive(change_documents=lambda d: d["readback"]["fields"][2].update(type="long")), "INVALID_READBACK_SCHEMA")

    def test_wrong_row_count(self):
        self.reject(self.receive(change_rows=lambda r: r.pop()), "INVALID_ROWS")

    def test_duplicate_category(self):
        self.reject(self.receive(change_rows=lambda r: r[1].update(category=r[0]["category"])), "INVALID_CATEGORY")

    def test_missing_bucket_rejected_for_pinned_zero_missing_snapshot(self):
        self.reject(self.receive(change_rows=lambda r: r[1].update(category=None, share_known=None)), "INVALID_CATEGORY")

    def test_unknown_not_relabelled_as_missing(self):
        self.reject(self.receive(change_rows=lambda r: r[1].update(category="Unknown")), "INVALID_CATEGORY")

    def test_blank_category(self):
        self.reject(self.receive(change_rows=lambda r: r[1].update(category=" ")), "INVALID_CATEGORY")

    def test_it_other_is_known_and_has_pinned_count(self):
        result = self.receive()
        row = next(r for r in result.rows if r.category == "IT_OTHER")
        self.assertEqual(row.job_count, 77)
        self.assertEqual(row.share_known, 77 / 5206)

    def test_it_other_wrong_count(self):
        def change(records):
            other = next(r for r in records if r["category"] == "IT_OTHER")
            other.update(job_count=76, share_all_it=76 / 5206, share_known=76 / 5206)
        self.reject(self.receive(change_rows=change), "CONSERVATION_MISMATCH")

    def test_inconsistent_N(self):
        self.reject(self.receive(change_rows=lambda r: r[1].update(denominator_all_it=5207)), "INVALID_COUNTS")

    def test_inconsistent_K(self):
        self.reject(self.receive(change_rows=lambda r: r[1].update(denominator_known=5205)), "INVALID_COUNTS")

    def test_count_conservation(self):
        self.reject(self.receive(change_rows=lambda r: r[1].update(job_count=2, share_all_it=2 / 5206, share_known=2 / 5206)), "CONSERVATION_MISMATCH")

    def test_rate_mismatch(self):
        self.reject(self.receive(change_rows=lambda r: r[1].update(share_all_it=0.9)), "INVALID_RATE")

    def test_nonfinite_rate(self):
        self.reject(self.receive(change_rows=lambda r: r[1].update(share_known=float("nan"))), "INVALID_RATE")

    def test_csv_parquet_disagree(self):
        self.reject(self.receive(csv_change=lambda r: r[1].update(job_count=99)), "CSV_MISMATCH")

    def test_late_failure_never_exposes_partial_rows(self):
        first = self.receive()
        self.assertTrue(first.passed)
        self.reject(self.receive(change_rows=lambda r: r[-1].update(share_known=0.9)), "INVALID_RATE")
        self.assertEqual(first, self.receive())

    def test_no_loader_gate_or_synthetic_receiver_use(self):
        with ExitStack() as stack:
            spies = [stack.enter_context(patch.object(data_loader, name, side_effect=AssertionError("forbidden")))
                     for name in ("load_overview_data", "load_skills_data", "load_salary_quality_data")]
            spies.append(stack.enter_context(patch.object(q01_candidate_receiver, "validate_q01_candidate", side_effect=AssertionError("forbidden"))))
            self.assertTrue(self.receive().passed)
            for spy in spies:
                spy.assert_not_called()
        self.assertEqual(artifact_gate.real_artifact_status(exists=True), "BLOCKED")


class PreviewPageTests(unittest.TestCase):
    PAGE = Path(__file__).resolve().parent.parent / "pages" / "5_Q01_Real_Preview.py"

    def page(self):
        app = AppTest.from_file(str(self.PAGE)).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        return app

    def load(self, app):
        app.text_input[0].set_value("C:/explicit/synthetic.zip")
        app.checkbox[0].set_value(True)
        app.button[0].click().run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        return app

    def no_findings(self, app):
        self.assertEqual(len(app.metric), 0)
        self.assertEqual(len(app.dataframe), 0)
        self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)

    def test_open_does_not_read(self):
        with patch.object(q, "load_q01_preview", side_effect=AssertionError("unexpected read")) as spy:
            app = self.page()
            self.no_findings(app)
            self.assertEqual(app.text_input[0].value, "")
        spy.assert_not_called()

    def test_failed_load_no_findings(self):
        with patch.object(q, "load_q01_preview", return_value=q.PreviewResult(False, "ARCHIVE_HASH_MISMATCH")):
            app = self.load(self.page())
            self.no_findings(app)
            self.assertIn("ARCHIVE_HASH_MISMATCH", app.error[0].value)

    def test_success_chart_table_kpis_and_status(self):
        result = q.PreviewResult(True, "", tuple(q.PreviewRow(**r) for r in sorted(rows(), key=lambda r: -r["job_count"])))
        with patch.object(q, "load_q01_preview", return_value=result) as spy:
            app = self.load(self.page())
            spy.assert_called_once_with("C:/explicit/synthetic.zip", confirmed=True)
            self.assertEqual(len(app.metric), 4)
            self.assertEqual([x.value for x in app.metric], ["5206", "5206", "0", "10"])
            self.assertEqual(tuple(app.dataframe[0].value.columns), q.COLUMNS)
            self.assertEqual(len(app.get("arrow_vega_lite_chart")), 1)
            self.assertEqual(len(app.multiselect), 0)
            text = "\n".join(x.value for name in ("warning", "caption", "info") for x in getattr(app, name))
            for required in ("VALIDATED / NOT ACCEPTED", "Production Gate CLOSED", "key-set", "REVIEW", "1e-12"):
                self.assertIn(required, text)

    def test_failure_after_success_clears_findings(self):
        result = q.PreviewResult(True, "", tuple(q.PreviewRow(**r) for r in rows()))
        with patch.object(q, "load_q01_preview", side_effect=[result, q.PreviewResult(False, "INVALID_RATE")]):
            app = self.load(self.page())
            self.assertEqual(len(app.metric), 4)
            app.button[0].click().run(timeout=20)
            self.no_findings(app)
            self.assertEqual(len(app.exception), 0)

    def test_unconfirmed_submit_no_read(self):
        with patch.object(q, "load_q01_preview", wraps=q.load_q01_preview) as receiver:
            app = self.page()
            app.button[0].click().run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.no_findings(app)
            receiver.assert_called_once_with("", confirmed=False)
            self.assertIn("CONFIRMATION_REQUIRED", app.error[0].value)

    def test_chart_uses_counts_sort_and_stored_percentage_once(self):
        result = q.PreviewResult(True, "", tuple(q.PreviewRow(**r) for r in sorted(rows(), key=lambda r: -r["job_count"])))
        with patch.object(q, "load_q01_preview", return_value=result), \
                patch.object(st, "vega_lite_chart", wraps=st.vega_lite_chart) as chart:
            self.load(self.page())
            data, spec = chart.call_args.args
            self.assertEqual(data["job_count"].tolist(), [r.job_count for r in result.rows])
            self.assertEqual(data["Share %"].tolist(), [r.share_all_it * 100 for r in result.rows])
            self.assertEqual(spec["encoding"]["x"]["field"], "job_count")
            self.assertEqual(spec["encoding"]["y"]["sort"], "-x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
