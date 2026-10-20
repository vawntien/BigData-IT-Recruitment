"""UI helpers and shared presentation components for Streamlit."""

from __future__ import annotations

import streamlit as st
from .artifact_gate import STATUS_BLOCKED, STATUS_INVALID, STATUS_MISSING, STATUS_SAMPLE


def render_header(title: str, subtitle: str = "") -> None:
    """Render standard page header with title and subtitle."""
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.markdown("---")


def render_data_status_banner(status: str, message: str) -> None:
    """Render consumer status; no current status authorizes production display."""
    if status == STATUS_SAMPLE:
        st.warning(
            "⚠️ **DEVELOPMENT SAMPLE MODE ACTIVE**\n\n"
            "Currently displaying **SYNTHETIC MOCKUP DATA / SYNTHETIC_SAMPLE** (`dashboard/sample_data/`).\n"
            "This data is solely for UI development and layout testing. "
            "**DO NOT** use these numbers for project reporting or conclusions!"
        )
    elif status == STATUS_MISSING:
        st.error(
            f"❌ **DATA UNAVAILABLE**\n\n{message}\n\n"
            "Tip: You can enable 'Sample Development Mode' in the sidebar to preview the dashboard UI."
        )
    elif status == STATUS_INVALID:
        st.error(f"❌ **INVALID DATA**\n\n{message}")
    elif status in (STATUS_BLOCKED, "UNVERIFIED_ARTIFACT"):
        st.warning(f"⛔ **DATA BLOCKED — UNVERIFIED_ARTIFACT**\n\n{message}")
    else:
        st.error("⛔ **DATA BLOCKED**: This status cannot authorize production display.")


def render_todo_placeholder(section_name: str, requirement_desc: str) -> None:
    """Render a standardized TODO placeholder box for pending pipeline steps."""
    st.info(
        f"🛠️ **TODO Placeholder: {section_name}**\n\n"
        f"{requirement_desc}\n\n"
        "_This visual component will activate once upstream tasks provide the final analytics schema._"
    )
