"""Dedicated synthetic Q01 page; no legacy loader or real-artifact discovery."""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from components.q01_demo import run_q01_demo
from components.ui_helpers import page_setup, render_header, horizontal_bar


page_setup("Q01 — Synthetic Demo")
render_header("Q01 · Minh họa")
st.warning("SYNTHETIC DEMO ONLY · Dữ liệu giả lập, không phải kết quả thực tế.")


enabled = st.toggle("Dữ liệu Q01 minh họa", value=False, key="q01_synthetic_demo_enabled")
if not enabled:
    st.caption("Chọn Dữ liệu Q01 minh họa để khám phá phân bố nhóm nghề giả lập.")
    with st.expander("Trạng thái nguồn"):
        st.caption("DEMO_DISABLED · Chưa đọc dữ liệu minh họa.")
    st.stop()

presentation = run_q01_demo(enabled)
if not presentation.passed:
    st.error(f"{presentation.status}: {', '.join(presentation.issue_codes)}")
    st.stop()

st.metric("Mẫu số giả lập B", presentation.population_count)
st.caption("Nhóm có thể chồng lặp: tổng tỷ lệ có thể vượt 100%. Không chuẩn hóa thành phân hoạch.")

# Only guarded curated values cross the final chart/table conversion boundary.
chart = pd.DataFrame({"Category": [row.category_id for row in presentation.rows],
                      "Share %": [float(row.share_percent) for row in presentation.rows]})
horizontal_bar(chart, "Category", "Share %", value_title="Tỷ lệ (%)", tooltip=[{"field": "Category"}, {"field": "Share %", "format": ".2f"}])
table = pd.DataFrame({"Category": [row.category_id for row in presentation.rows],
                      "Count": [row.count for row in presentation.rows],
                      "Share %": [f"{float(row.share_percent):.2f}" for row in presentation.rows]})
with st.expander("Chi tiết minh họa"):
    st.dataframe(table, hide_index=True, use_container_width=True, column_config={"Category": "Nhóm giả lập", "Count": "Số tin mẫu", "Share %": "Tỷ lệ (%)"})
with st.expander("Nguồn và giới hạn"):
    st.caption("Không phải kết quả tuyển dụng IT thực tế. Nhóm giả lập, không có lineage tin đã nghiệm thu.")
    st.caption("Ngữ cảnh giả lập (run / population / filter): " + " / ".join(presentation.context))
    st.caption("Taxonomy giả lập: " + presentation.taxonomy_id)
    st.caption("Share % = Fraction đã xác minh × 100 một lần; bảng làm tròn 2 chữ số thập phân.")
