"""CSV/provenance helpers for TV2; never modify source datasets."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MISSING = {"", "null", "n/a", "na"}
csv.field_size_limit(32 * 1024 * 1024)


def text_value(value):
    if value is None or value.strip().lower() in MISSING:
        return None
    return value.strip()


def integer_key(value):
    value = text_value(value)
    if value is None:
        return None
    if not re.fullmatch(r"[+-]?\d+(?:\.0+)?", value):
        raise ValueError(f"Non-integral identifier: {value!r}")
    result = int(value.split(".")[0])
    if not -(2**63) <= result < 2**63:
        raise ValueError(f"Identifier outside bigint: {value!r}")
    return str(result)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"Missing/duplicate CSV header: {path}")
        for index, row in enumerate(reader, 1):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed CSV record {index}: {path}")
            yield row


def csv_header(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return next(csv.reader(stream, strict=True))


def write_csv(path, rows, fields, *, exclusive=False, bom=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value, *, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
