"""Standard sidebar filters and user controls for the dashboard."""

from __future__ import annotations

from typing import Any, Dict
import pandas as pd
import streamlit as st


def render_sample_control() -> bool:
    """Render the sample toggle once, before loading data."""
    st.sidebar.header("⚙️ Dashboard Controls")

    # Development mode toggle
    return st.sidebar.checkbox(
        "Enable Development Sample Mode",
        value=False,
        help="Explicitly select bundled synthetic demo data. Real analytics remain blocked pending acceptance.",
    )


def render_data_filters(df: pd.DataFrame | None = None) -> Dict[str, Any]:
    """Render filters after data has been loaded and validated."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filters")

    selected_categories = []
    selected_exp = []
    selected_locations = []

    if df is not None and not df.empty:
        # Category filter
        if "category" in df.columns:
            categories = sorted(df["category"].dropna().unique().tolist())
            selected_categories = st.sidebar.multiselect(
                "Job Category",
                options=categories,
                default=categories,
            )

        # Experience level filter
        if "experience_level" in df.columns:
            exp_levels = sorted(df["experience_level"].dropna().unique().tolist())
            selected_exp = st.sidebar.multiselect(
                "Experience Level",
                options=exp_levels,
                default=exp_levels,
            )

        # Location filter
        if "location" in df.columns:
            locations = sorted(df["location"].dropna().unique().tolist())
            selected_locations = st.sidebar.multiselect(
                "Location",
                options=locations,
                default=locations,
            )

    return {
        "categories": selected_categories,
        "experience_levels": selected_exp,
        "locations": selected_locations,
    }


def render_sidebar_controls(df: pd.DataFrame | None = None) -> Dict[str, Any]:
    """Render the complete sidebar for existing callers."""
    sample_mode = render_sample_control()
    return {"sample_mode": sample_mode, **render_data_filters(df)}
