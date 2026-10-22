"""Opt-in technical preview; isolated from production and synthetic flows."""

from dataclasses import asdict
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from components.q01_real_preview import load_q01_preview, RUN_ID, D06_RUN


st.set_page_config(page_title="Q01 — Real Data Preview", page_icon="🔎", layout="wide")
st.title("Q01 — Real Data Integration Preview")
st.warning("Q01 REAL DATA — VALIDATED / NOT ACCEPTED")
st.caption("Technical preview only. Q01 group acceptance PENDING; official Dashboard NOT AUTHORIZED. Production Gate CLOSED.")

with st.form("q01_real_preview_load"):
    local_path = st.text_input("Local Q01 handoff ZIP path", value="")
    confirmed = st.checkbox("I confirm this local artifact may be read for technical preview", value=False)
    submitted = st.form_submit_button("Load and verify Q01 preview")

if not submitted:
    st.info("Enter the local ZIP path, confirm technical read permission, then load. No artifact is read on page open.")
    st.stop()

result = load_q01_preview(local_path, confirmed=confirmed)
if not result.passed:
    st.error("Preview unavailable: " + result.issue)
    st.stop()

table = pd.DataFrame([asdict(row) for row in result.rows])
for column, label, value in zip(st.columns(4),
                                ("Total ACCEPT jobs", "Known category jobs", "Missing category jobs", "Number of groups"),
                                (result.rows[0].denominator_all_it, result.rows[0].denominator_known,
                                 result.rows[0].denominator_all_it - result.rows[0].denominator_known, len(result.rows))):
    column.metric(label, value)

st.subheader("Category distribution")
chart = table[["category", "job_count", "share_all_it"]].copy()
chart["Share %"] = chart.pop("share_all_it") * 100
st.vega_lite_chart(chart, {
    "mark": "bar",
    "encoding": {
        "y": {"field": "category", "type": "nominal", "sort": "-x"},
        "x": {"field": "job_count", "type": "quantitative", "title": "ACCEPT jobs"},
        "tooltip": [{"field": "category"}, {"field": "job_count"}, {"field": "Share %", "format": ".4f"}],
    },
}, use_container_width=True)
st.caption("Share % = stored share_all_it × 100 once. Counts sorted descending; category codes retained from source.")

st.subheader("Six-column Q01 detail")
st.dataframe(table, hide_index=True, use_container_width=True)
st.caption("denominator_all_it = all classifier ACCEPT jobs; denominator_known = ACCEPT jobs with known category. Equal in this snapshot, different definitions.")

st.subheader("Provenance")
st.write({"TV2 run": RUN_ID, "D06 upstream (source evidence)": D06_RUN,
          "Taxonomy": "v0.2.2", "Population": "5,206 classifier ACCEPT jobs; whole snapshot",
          "Validation": "VALIDATED — technical receiving checks PASS", "Acceptance": "NOT ACCEPTED / PENDING"})
st.info("5,206 is the classifier ACCEPT population. REVIEW is separate from REJECT. This snapshot does not establish coverage of the whole IT recruitment market. No experience, location or date cross-filter is supported. Exact analyzer-input key-set remains source evidence, not independently verified from the original enriched snapshot. Numeric tolerance 1e-12 is a technical comparison policy, not production-approved tolerance.")
