"""Overview page: Recruitment structure and high-level distribution."""

from __future__ import annotations

import sys
from pathlib import Path

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DASHBOARD_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

import streamlit as st
import pandas as pd
from components.data_loader import load_overview_data, STATUS_MISSING
from components.contract_validator import validate_overview_schema
from components.ui_helpers import render_header, render_data_status_banner, render_todo_placeholder
from components.filters import render_sample_control, render_data_filters

st.set_page_config(page_title="Overview - IT Recruitment", page_icon="📊", layout="wide")

render_header(
    title="📊 Cơ cấu Tuyển dụng (Overview)",
    subtitle="Phân tích cơ cấu việc làm theo nhóm nghề, kinh nghiệm, địa điểm và hình thức làm việc",
)

# Sidebar controls
sample_mode = render_sample_control()

# Load data
df, status, message = load_overview_data(enable_sample_mode=sample_mode)
render_data_status_banner(status, message)

if status == STATUS_MISSING or df is None:
    st.stop()

# Schema contract validation
is_valid, missing_cols, extra_cols, schema_msg = validate_overview_schema(df)
if not is_valid:
    st.error(f"⚠️ **Lỗi hợp đồng dữ liệu (Schema Mismatch):** {schema_msg}")
    if missing_cols:
        st.markdown(f"Các cột còn thiếu: `{missing_cols}`")
    st.stop()

# Populate filters with validated dataframe
controls = render_data_filters(df)
selected_cats = controls["categories"]
selected_exps = controls["experience_levels"]
selected_locs = controls["locations"]

# Apply filters safely
filtered_df = df.copy()
if selected_cats and "category" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["category"].isin(selected_cats)]
if selected_exps and "experience_level" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["experience_level"].isin(selected_exps)]
if selected_locs and "location" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["location"].isin(selected_locs)]

# Handle empty filter result (no-match combination)
if filtered_df.empty:
    st.warning("⚠️ **Không tìm thấy bản ghi nào phù hợp với bộ lọc hiện tại.** Vui lòng nới lỏng hoặc chọn lại các tiêu chí lọc ở thanh bên trái.")
    st.stop()

# --- SECTION 1: KEY PERFORMANCE INDICATORS (KPIs) ---
st.subheader("📌 Chỉ số Tổng quan")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_jobs = int(filtered_df["job_count"].fillna(0).sum()) if "job_count" in filtered_df.columns else len(filtered_df)
kpi1.metric("Tổng số tin tuyển dụng", f"{total_jobs:,}")

top_cat_series = filtered_df.groupby("category")["job_count"].sum()
top_cat = top_cat_series.idxmax() if not top_cat_series.empty else "N/A"
kpi2.metric("Nhóm nghề hàng đầu", str(top_cat))

top_loc_series = filtered_df.groupby("location")["job_count"].sum()
top_loc = top_loc_series.idxmax() if not top_loc_series.empty else "N/A"
kpi3.metric("Địa điểm nhiều nhất", str(top_loc))

# Actual audited salary coverage baseline
kpi4.metric("Độ phủ thông tin lương", "29.13%", help="Đo lường từ dữ liệu sạch thực tế tại D03/D04")

st.markdown("---")

# --- SECTION 2: CHARTS & VISUALIZATIONS ---
st.subheader("📈 Phân bố Cơ cấu Tuyển dụng")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 1. Nhu cầu tuyển dụng theo Nhóm nghề")
    if "category" in filtered_df.columns and "job_count" in filtered_df.columns:
        cat_counts = filtered_df.groupby("category")["job_count"].sum().reset_index()
        cat_counts = cat_counts.sort_values(by="job_count", ascending=False)
        st.bar_chart(cat_counts.set_index("category"), height=320)

with col_chart2:
    st.markdown("#### 2. Phân bố theo Cấp bậc Kinh nghiệm")
    if "experience_level" in filtered_df.columns and "job_count" in filtered_df.columns:
        exp_counts = filtered_df.groupby("experience_level")["job_count"].sum().reset_index()
        exp_counts = exp_counts.sort_values(by="job_count", ascending=False)
        st.bar_chart(exp_counts.set_index("experience_level"), height=320)

col_chart3, col_chart4 = st.columns(2)

with col_chart3:
    st.markdown("#### 3. Phân bố theo Địa điểm tuyển dụng")
    if "location" in filtered_df.columns and "job_count" in filtered_df.columns:
        loc_counts = filtered_df.groupby("location")["job_count"].sum().reset_index()
        loc_counts = loc_counts.sort_values(by="job_count", ascending=False).head(10)
        st.bar_chart(loc_counts.set_index("location"), height=320)

with col_chart4:
    st.markdown("#### 4. Hình thức làm việc & Remote Indicator")
    if "work_type" in filtered_df.columns and "job_count" in filtered_df.columns:
        wt_counts = filtered_df.groupby("work_type")["job_count"].sum().reset_index()
        wt_counts = wt_counts.sort_values(by="job_count", ascending=False)
        st.bar_chart(wt_counts.set_index("work_type"), height=320)
    else:
        render_todo_placeholder(
            section_name="Work Type & Remote Classification",
            requirement_desc="Cần kết hợp trường 'work_type' và 'remote_allowed' từ bảng analytics A06.",
        )

# --- SECTION 3: RAW DATA TABLE & EXPORT ---
with st.expander("📄 Xem dữ liệu bảng tổng hợp"):
    st.dataframe(filtered_df, use_container_width=True)
