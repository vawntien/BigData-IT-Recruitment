"""Consumer-only states; not an upstream physical status contract.

Official acceptance is pending. No metadata, filename or flag can open the
production gate in this implementation.
"""

STATUS_SAMPLE = "SYNTHETIC_SAMPLE"
STATUS_MISSING = "MISSING"
STATUS_INVALID = "INVALID"
STATUS_BLOCKED = "BLOCKED"


def real_artifact_status(*, exists: bool, read_failed: bool = False) -> str:
    """Readable real artifacts remain blocked pending an approved contract."""
    if not exists:
        return STATUS_MISSING
    if read_failed:
        return STATUS_INVALID
    return STATUS_BLOCKED
