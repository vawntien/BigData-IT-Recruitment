"""Standard sidebar filters and user controls for the dashboard."""

from __future__ import annotations

from typing import Any, Dict
import pandas as pd
import streamlit as st


def render_sidebar_controls(df: pd.DataFrame | None = None) -> Dict[str, Any]:
    """Render global sidebar filters and configuration switches."""
    st.sidebar.header("⚙️ Dashboard Controls")

    # Development mode toggle
    sample_mode = st.sidebar.checkbox(
        "Enable Development Sample Mode",
        value=True,
        help="When enabled, loads small synthetic mockup data if production analytics tables are not found.",
    )

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
        "sample_mode": sample_mode,
        "categories": selected_categories,
        "experience_levels": selected_exp,
        "locations": selected_locations,
    }
