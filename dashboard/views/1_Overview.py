"""Synthetic recruitment explorer; no official population claims."""
from pathlib import Path
import sys
import streamlit as st
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from components.data_loader import load_overview_data, STATUS_SAMPLE, STATUS_INVALID
from components.contract_validator import validate_overview_schema
from components.filters import render_sample_control, render_data_filters
from components.ui_helpers import page_setup, render_header, render_data_status_banner, horizontal_bar, empty_state, source_strip

page_setup("Cơ cấu tuyển dụng · Demo")
render_header("Cơ cấu tuyển dụng · Minh họa")
sample_mode = render_sample_control()
if not sample_mode:
    source_strip("SYNTHETIC · Bản minh họa cơ cấu tuyển dụng")
    empty_state("Khám phá cơ cấu tuyển dụng", "Chọn Dữ liệu minh họa để xem KPI và biểu đồ từ mẫu SYNTHETIC.")
    st.stop()
# Preserve the existing loader's explicit opt-in and fail-closed status checks.
df, status, message = load_overview_data(enable_sample_mode=sample_mode)
if status != STATUS_SAMPLE or df is None:
    render_data_status_banner(status, message)
    st.stop()
is_valid, missing_cols, extra_cols, schema_msg = validate_overview_schema(df)
if not is_valid:
    render_data_status_banner(STATUS_INVALID, schema_msg)
    st.stop()
render_data_status_banner(status, message)
controls = render_data_filters(df)
filtered_df = df.copy()
for column, key in (("category", "categories"), ("experience_level", "experience_levels"), ("location", "locations")):
    if controls[key]:
        filtered_df = filtered_df[filtered_df[column].isin(controls[key])]
if filtered_df.empty:
    empty_state("Không có kết quả phù hợp", "Thử bỏ bớt lựa chọn trong bộ lọc minh họa.")
    st.stop()
total_jobs = int(filtered_df["job_count"].fillna(0).sum())
category_counts = filtered_df.groupby("category")["job_count"].sum().sort_values(ascending=False).reset_index()
location_counts = filtered_df.groupby("location")["job_count"].sum().sort_values(ascending=False).reset_index()
for col, label, value in zip(st.columns(4), ("Tin tuyển dụng mẫu", "Nhóm nghề dẫn đầu", "Địa điểm dẫn đầu", "Nhóm nghề hiển thị"),
                            (f"{total_jobs:,}", category_counts.iloc[0]["category"], location_counts.iloc[0]["location"], len(category_counts))):
    col.metric(label, value)
left, right = st.columns(2)
with left:
    st.subheader("Nhóm nghề")
    horizontal_bar(category_counts, "category", "job_count", value_title="Số tin minh họa")
with right:
    st.subheader("Kinh nghiệm")
    horizontal_bar(filtered_df.groupby("experience_level")["job_count"].sum().reset_index(), "experience_level", "job_count", color="#14867D", value_title="Số tin minh họa")
left, right = st.columns(2)
with left:
    st.subheader("Địa điểm")
    horizontal_bar(location_counts.head(10), "location", "job_count", value_title="Số tin minh họa")
with right:
    st.subheader("Hình thức việc làm")
    horizontal_bar(filtered_df.groupby("work_type")["job_count"].sum().reset_index(), "work_type", "job_count", color="#14867D", value_title="Số tin minh họa")
with st.expander("Bảng chi tiết & cách đọc"):
    st.caption("work_type là hình thức việc làm, không phải chế độ remote. Số liệu SYNTHETIC theo bộ lọc đang chọn.")
    st.dataframe(filtered_df, hide_index=True, use_container_width=True,
                 column_config={"category": "Nhóm nghề", "experience_level": "Kinh nghiệm", "location": "Địa điểm",
                                "work_type": "Hình thức việc làm", "job_count": "Số tin mẫu", "data_source": "Nguồn"})
