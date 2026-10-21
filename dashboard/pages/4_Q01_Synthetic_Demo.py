"""Dedicated synthetic Q01 page; no legacy loader or real-artifact discovery."""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from components.q01_demo import run_q01_demo


st.set_page_config(page_title="Q01 — Synthetic Demo", page_icon="🧪", layout="wide")
st.title("Q01 — Synthetic Demo")
st.warning("SYNTHETIC DEMO ONLY")
st.caption("No real IT recruitment findings. Artificial categories; no accepted job lineage.")

enabled = st.checkbox("Enable Q01 synthetic demo", value=False, key="q01_synthetic_demo_enabled")
if not enabled:
    st.info("DEMO_DISABLED — Enable the checkbox to run the in-memory synthetic demo.")
    st.stop()

presentation = run_q01_demo(enabled)
if not presentation.passed:
    st.error(f"{presentation.status}: {', '.join(presentation.issue_codes)}")
    st.stop()

st.metric("Declared synthetic denominator B", presentation.population_count)
st.caption("Synthetic context (run / population / filter): " + " / ".join(presentation.context))
st.caption("Synthetic taxonomy: " + presentation.taxonomy_id)
st.info("Overlapping groups: shares may sum above 100%. No normalization or disjoint partition is implied.")
st.caption("Share % displays the validated stored Fraction × 100, rounded to 2 decimal places in the table.")

# Only guarded curated values cross the final chart/table conversion boundary.
chart = pd.DataFrame({"Category": [row.category_id for row in presentation.rows],
                      "Share %": [float(row.share_percent) for row in presentation.rows]})
st.bar_chart(chart.set_index("Category"), y="Share %")
table = pd.DataFrame({"Category": [row.category_id for row in presentation.rows],
                      "Count": [row.count for row in presentation.rows],
                      "Share %": [f"{float(row.share_percent):.2f}" for row in presentation.rows]})
st.dataframe(table, hide_index=True, use_container_width=True)
