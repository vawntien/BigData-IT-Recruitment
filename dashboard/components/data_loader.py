"""Load explicitly selected demo data; keep real analytics fail-closed."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from .artifact_gate import (
    STATUS_BLOCKED,
    STATUS_INVALID,
    STATUS_MISSING,
    STATUS_SAMPLE,
    real_artifact_status,
)
from .contract_validator import (
    validate_overview_schema,
    validate_salary_quality_schema,
    validate_skills_schema,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ANALYTICS_DIR = PROJECT_ROOT / "data" / "analytics"
SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"

# Import compatibility only: no loader path returns this legacy status.
STATUS_PRODUCTION = "PRODUCTION"

MISSING_MSG = (
    "Analytics data is not available yet. "
    "Explicitly enable sample development mode to preview synthetic demo data."
)

_VALIDATORS = {
    "overview_analytics": validate_overview_schema,
    "skills_analytics": validate_skills_schema,
    "salary_quality_analytics": validate_salary_quality_schema,
}


def _load_table(
    table_name: str,
    sample_file_name: str,
    enable_sample_mode: bool,
) -> Tuple[Optional[pd.DataFrame], str, str]:
    """Return a DataFrame only for validated bundled demo; retain the tuple API.

    Demo selection never consults analytics. Otherwise only fixed basenames are
    checked for readability, and their contents never reach pages. A broken
    Parquet does not silently select CSV or demo instead.
    """
    if enable_sample_mode:
        sample_path = SAMPLE_DIR / sample_file_name
        if not sample_path.exists():
            return None, STATUS_MISSING, "Bundled demo data is not available."
        try:
            df = pd.read_csv(sample_path)
        except (PermissionError, ImportError, OSError):
            return None, STATUS_BLOCKED, "Bundled demo data could not be accessed."
        except Exception as error:
            return None, STATUS_INVALID, f"Bundled demo read failed ({type(error).__name__})."
        valid, _, _, message = _VALIDATORS[table_name](df)
        if not valid:
            return None, STATUS_INVALID, message
        if "data_source" not in df or not df["data_source"].eq(STATUS_SAMPLE).all():
            return None, STATUS_INVALID, "Bundled demo must contain only SYNTHETIC_SAMPLE rows."
        return df, STATUS_SAMPLE, f"Validated synthetic demo: {sample_file_name}"

    for suffix in ("parquet", "csv"):
        artifact = ANALYTICS_DIR / f"{table_name}.{suffix}"
        if not artifact.exists():
            continue
        try:
            # Readability diagnoses corruption; it never establishes acceptance.
            if suffix == "parquet":
                pd.read_parquet(artifact)
            else:
                pd.read_csv(artifact)
        except FileNotFoundError:
            return None, STATUS_MISSING, MISSING_MSG
        except (PermissionError, ImportError, OSError):
            return None, STATUS_BLOCKED, "Analytics artifact could not be accessed or its reader is unavailable."
        except Exception as error:
            return None, real_artifact_status(exists=True, read_failed=True), (
                f"Analytics read failed ({type(error).__name__}); no fallback was selected."
            )
        return None, real_artifact_status(exists=True), (
            "UNVERIFIED_ARTIFACT: readable analytics is blocked. "
            "Population, provenance and official acceptance are not verified; "
            "production eligibility remains closed. Select demo explicitly if needed."
        )
    return None, real_artifact_status(exists=False), MISSING_MSG


def load_overview_data(enable_sample_mode: bool = False) -> Tuple[Optional[pd.DataFrame], str, str]:
    return _load_table("overview_analytics", "overview_sample.csv", enable_sample_mode)


def load_skills_data(enable_sample_mode: bool = False) -> Tuple[Optional[pd.DataFrame], str, str]:
    return _load_table("skills_analytics", "skills_sample.csv", enable_sample_mode)


def load_salary_quality_data(enable_sample_mode: bool = False) -> Tuple[Optional[pd.DataFrame], str, str]:
    return _load_table("salary_quality_analytics", "salary_quality_sample.csv", enable_sample_mode)
