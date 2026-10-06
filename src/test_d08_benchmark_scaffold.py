"""Lightweight unit test suite for D08 benchmark utilities and harness."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Force UTF-8 output
sys.stdout.reconfigure(encoding="utf-8")

from benchmark_utils import (
    BenchmarkTimer,
    create_benchmark_record,
    write_benchmark_results,
    BENCHMARK_CSV_FIELDS,
)


def test_benchmark_timer():
    """Verify timer produces valid, non-negative elapsed wall-clock seconds."""
    with BenchmarkTimer() as timer:
        time.sleep(0.05)
    assert timer.elapsed_seconds >= 0.04, f"Timer undercounted: {timer.elapsed_seconds}s"
    assert timer.elapsed_seconds < 1.0, f"Timer overcounted: {timer.elapsed_seconds}s"
    print("  [PASS] test_benchmark_timer passed.")


def test_create_benchmark_record_fields():
    """Verify benchmark record contains all required fields and correct default flags."""
    record = create_benchmark_record(
        benchmark_id="TEST_01",
        operation="TEST_OP",
        dataset="test_data",
        elapsed_seconds=1.23456,
        input_rows=1000,
        output_rows=500,
        input_partitions=4,
        output_partitions=2,
        spark_config={
            "spark_version": "4.2.0",
            "spark_master": "local[*]",
            "shuffle_partitions": "200",
        },
        dev_smoke_only=True,
        official=False,
        notes="unit test note",
    )

    for field in BENCHMARK_CSV_FIELDS:
        assert field in record, f"Missing required field: {field}"

    assert record["benchmark_id"] == "TEST_01"
    assert record["elapsed_seconds"] == 1.2346
    assert record["dev_smoke_only"] == "true", "dev_smoke_only must be 'true'"
    assert record["official"] == "false", "official must be 'false'"
    assert record["spark_version"] == "4.2.0"
    assert record["spark_master"] == "local[*]"
    assert record["shuffle_partitions"] == "200"
    print("  [PASS] test_create_benchmark_record_fields passed.")


def test_write_benchmark_results(tmp_path: Path | None = None):
    """Verify write_benchmark_results generates a valid CSV file with proper headers."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_csv = Path(tmpdir) / "test_benchmark.csv"
        rec = create_benchmark_record(
            benchmark_id="T1",
            operation="OP",
            dataset="DS",
            elapsed_seconds=0.5,
            dev_smoke_only=True,
            official=False,
        )
        write_benchmark_results(test_csv, [rec])
        assert test_csv.exists(), "CSV file should be created"
        content = test_csv.read_text(encoding="utf-8")
        assert "benchmark_id" in content, "Header should contain benchmark_id"
        assert "T1" in content, "Content should contain record data"
        assert "true" in content, "Content should contain dev_smoke_only flag"
        assert "false" in content, "Content should contain official=false flag"
    print("  [PASS] test_write_benchmark_results passed.")


def main():
    print("Running test_d08_benchmark_scaffold.py...")
    test_benchmark_timer()
    test_create_benchmark_record_fields()
    test_write_benchmark_results()
    print("All D08 benchmark scaffold unit tests PASSED successfully.")


if __name__ == "__main__":
    main()
