"""Unit test suite for D09 pipeline validation scaffold."""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

# Force utf-8 stdout
sys.stdout.reconfigure(encoding="utf-8")

from validation_utils import (
    ValidationRecord,
    check_file_exists,
    check_no_duplicate_grain,
    check_reconciliation,
    check_synthetic_leakage,
    create_pending_record,
    write_validation_results,
)


def test_validation_record_dataclass() -> None:
    rec = ValidationRecord(
        validation_id="TEST-01",
        stage="TEST",
        status="PASS",
        severity="BLOCKER",
        dataset="test_df",
        check_name="test_check",
        expected="10",
        actual="10",
        message="Test succeeded",
        official=False,
    )
    assert rec.validation_id == "TEST-01"
    assert rec.status == "PASS"
    assert rec.official is False
    assert rec.timestamp != ""
    print("  [PASS] test_validation_record_dataclass")


def test_reconciliation_guard() -> None:
    # Balanced reconciliation
    rec_pass = check_reconciliation(
        raw_count=100,
        clean_count=95,
        rejected_count=5,
        validation_id="TEST-REC-01",
        stage="TEST",
        dataset="table_a",
    )
    assert rec_pass.status == "PASS"

    # Unbalanced reconciliation
    rec_fail = check_reconciliation(
        raw_count=100,
        clean_count=90,
        rejected_count=5,
        validation_id="TEST-REC-02",
        stage="TEST",
        dataset="table_b",
    )
    assert rec_fail.status == "FAIL"
    assert "Reconciliation broken" in rec_fail.message
    print("  [PASS] test_reconciliation_guard")


def test_grain_preservation_guard() -> None:
    # Preserved grain
    g_pass = check_no_duplicate_grain(
        before_count=123849,
        after_count=123849,
        validation_id="TEST-GRN-01",
        stage="TEST",
        dataset="postings",
    )
    assert g_pass.status == "PASS"

    # Exploded grain
    g_fail = check_no_duplicate_grain(
        before_count=123849,
        after_count=213768,
        validation_id="TEST-GRN-02",
        stage="TEST",
        dataset="postings_exploded",
    )
    assert g_fail.status == "FAIL"
    assert "Grain explosion or loss detected" in g_fail.message
    print("  [PASS] test_grain_preservation_guard")


def test_synthetic_leakage_guard() -> None:
    # Production authentic
    l_pass = check_synthetic_leakage(
        data_source_value="AUTHENTIC_LINKEDIN",
        path_checked="data/processed/clean",
        validation_id="TEST-LEAK-01",
    )
    assert l_pass.status == "PASS"

    # Synthetic tag leakage
    l_fail1 = check_synthetic_leakage(
        data_source_value="SYNTHETIC_SAMPLE",
        path_checked="data/processed/clean",
        validation_id="TEST-LEAK-02",
    )
    assert l_fail1.status == "FAIL"

    # Sample path leakage
    l_fail2 = check_synthetic_leakage(
        data_source_value="UNKNOWN",
        path_checked="src/dashboard/sample_data/mock.parquet",
        validation_id="TEST-LEAK-03",
    )
    assert l_fail2.status == "FAIL"
    print("  [PASS] test_synthetic_leakage_guard")


def test_pending_record_generation() -> None:
    rec_pending = create_pending_record(
        validation_id="TEST-PEND-01",
        stage="D06_IT_CLASSIFICATION",
        dataset="it_jobs",
        check_name="it_classification_exists",
        dependency="D06 Pipeline Implementation",
        expected_description="IT tag present on all 123,849 rows",
    )
    assert rec_pending.status == "PENDING"
    assert "BLOCKED" in rec_pending.actual
    assert rec_pending.official is False
    print("  [PASS] test_pending_record_generation")


def test_write_validation_results_csv() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_csv = Path(tmpdir) / "audit" / "test_results.csv"
        records = [
            ValidationRecord(
                validation_id="T1",
                stage="STAGE1",
                status="PASS",
                severity="BLOCKER",
                dataset="ds1",
                check_name="chk1",
                expected="exp1",
                actual="act1",
                message="msg1",
                official=False,
            ),
            ValidationRecord(
                validation_id="T2",
                stage="STAGE2",
                status="PENDING",
                severity="CRITICAL",
                dataset="ds2",
                check_name="chk2",
                expected="exp2",
                actual="act2",
                message="msg2",
                official=False,
            ),
        ]
        write_validation_results(records, tmp_csv)
        assert tmp_csv.exists()

        with open(tmp_csv, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 2
            assert reader[0]["validation_id"] == "T1"
            assert reader[0]["status"] == "PASS"
            assert reader[0]["official"] == "False"
            assert reader[1]["validation_id"] == "T2"
            assert reader[1]["status"] == "PENDING"
    print("  [PASS] test_write_validation_results_csv")


def main() -> None:
    print("==================================================")
    print("RUNNING D09 VALIDATION SCAFFOLD UNIT TESTS")
    print("==================================================")
    test_validation_record_dataclass()
    test_reconciliation_guard()
    test_grain_preservation_guard()
    test_synthetic_leakage_guard()
    test_pending_record_generation()
    test_write_validation_results_csv()
    print("==================================================")
    print("ALL D09 UNIT TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    main()
