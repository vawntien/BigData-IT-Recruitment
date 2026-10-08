"""UI helpers and shared presentation components for Streamlit."""

from __future__ import annotations

import streamlit as st


def render_header(title: str, subtitle: str = "") -> None:
    """Render standard page header with title and subtitle."""
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.markdown("---")


def render_data_status_banner(status: str, message: str) -> None:
    """Render a prominent banner indicating whether production or synthetic data is displayed."""
    if status == "PRODUCTION":
        st.success(f"🟢 **PRODUCTION DATA ACTIVE**: {message}")
    elif status == "SAMPLE":
        st.warning(
            "⚠️ **DEVELOPMENT SAMPLE MODE ACTIVE**\n\n"
            "Currently displaying **SYNTHETIC MOCKUP DATA** (`dashboard/sample_data/`).\n"
            "This data is solely for UI development and layout testing. "
            "**DO NOT** use these numbers for project reporting or conclusions!"
        )
    elif status == "MISSING":
        st.error(
            f"❌ **DATA UNAVAILABLE**\n\n{message}\n\n"
            "Tip: You can enable 'Sample Development Mode' in the sidebar to preview the dashboard UI."
        )


def render_todo_placeholder(section_name: str, requirement_desc: str) -> None:
    """Render a standardized TODO placeholder box for pending pipeline steps."""
    st.info(
        f"🛠️ **TODO Placeholder: {section_name}**\n\n"
        f"{requirement_desc}\n\n"
        "_This visual component will activate once upstream tasks provide the final analytics schema._"
    )
