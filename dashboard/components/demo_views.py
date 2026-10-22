"""Presentation of existing bundled samples only; never real analytics."""
import streamlit as st
from . import data_loader
from .data_loader import STATUS_SAMPLE, STATUS_INVALID
from .contract_validator import validate_skills_schema, validate_salary_quality_schema
from .ui_helpers import render_data_status_banner, horizontal_bar, empty_state


def skills_demo():
    df, status, message = data_loader.load_skills_data(enable_sample_mode=True)
    if status != STATUS_SAMPLE or df is None:
        render_data_status_banner(status, message)
        return
    valid, _, _, msg = validate_skills_schema(df)
    if not valid:
        render_data_status_banner(STATUS_INVALID, msg)
        return
    render_data_status_banner(status, message)
    selected = st.selectbox("Nhóm nghề minh họa", ["Tất cả nhóm nghề"] + sorted(df["category"].dropna().unique().tolist()))
    filtered = df.copy() if selected == "Tất cả nhóm nghề" else df[df["category"] == selected].copy()
    if filtered.empty:
        empty_state("Không có dữ liệu minh họa", "Chọn một nhóm nghề khác.")
        return
    ranked = filtered.groupby("technical_skill")["job_count"].sum().sort_values(ascending=False).head(15).reset_index()
    for area, label, value in zip(st.columns(3), ("Kỹ năng hiển thị", "Nhóm nghề", "Nguồn"),
                                  (len(ranked), filtered["category"].nunique(), "SYNTHETIC")):
        area.metric(label, value)
    st.subheader("Kỹ năng nổi bật")
    horizontal_bar(ranked, "technical_skill", "job_count", value_title="Số lượt theo nhóm · minh họa")
    with st.expander("Chi tiết & phân bố theo nhóm", expanded=False):
        columns = ["technical_skill", "category", "job_count", "frequency_pct", "source_method"]
        st.dataframe(filtered[columns].sort_values("job_count", ascending=False), hide_index=True, use_container_width=True,
                     column_config={"technical_skill": "Kỹ năng", "category": "Nhóm nghề", "job_count": "Số lượt",
                                    "frequency_pct": "Tần suất (%)", "source_method": "Phương pháp nguồn"})
        st.caption("frequency_pct là phần trăm có sẵn trong sample; sample_size là mẫu số minh họa từng nhóm, không phải population chung.")
        # Keep the existing pivot's mean aggregation; flatten its column-axis
        # presentation so no named/multilevel headers are passed to the grid.
        pivot = df.pivot_table(index="technical_skill", columns="category", values="job_count", fill_value=0)
        pivot.columns.name = None
        st.dataframe(pivot.reset_index(), hide_index=True, use_container_width=True)
    with st.expander("Phạm vi nguồn", expanded=False):
        st.markdown("- SYNTHETIC SAMPLE, không phải kết quả tuyển dụng thực tế.\n- Tổng lượt theo kỹ năng có thể trùng tin giữa các nhóm; không phải DISTINCT job_id.\n- Job functions khác technical skills. Nguồn thật cần A05/A07 và nghiệm thu riêng.")


def salary_demo():
    df, status, message = data_loader.load_salary_quality_data(enable_sample_mode=True)
    if status != STATUS_SAMPLE or df is None:
        render_data_status_banner(status, message)
        return
    valid, _, _, msg = validate_salary_quality_schema(df)
    if not valid:
        render_data_status_banner(STATUS_INVALID, msg)
        return
    render_data_status_banner(status, message)
    left, right = st.columns(2)
    currency = left.selectbox("Tiền tệ", sorted(df["currency"].dropna().unique().tolist()))
    periods = sorted(df[df["currency"] == currency]["pay_period"].dropna().unique().tolist())
    period = right.selectbox("Kỳ trả lương", periods, index=periods.index("YEARLY") if "YEARLY" in periods else 0)
    filtered = df[(df["currency"] == currency) & (df["pay_period"] == period)].copy()
    for area, label, value in zip(st.columns(3), ("Nhóm nghề hiển thị", "Tiền tệ", "Kỳ trả lương"),
                                  (filtered["category"].nunique(), currency, period)):
        area.metric(label, value)
    st.subheader("Thu nhập theo nhóm nghề")
    horizontal_bar(filtered.sort_values("median_salary", ascending=False), "category", "median_salary", color="#14867D", value_title=currency + " / " + period,
                   tooltip=[{"field": "category"}, {"field": "median_salary"}, {"field": "currency"}, {"field": "pay_period"}])
    with st.expander("Dải thu nhập & độ phủ mẫu", expanded=False):
        st.dataframe(filtered, hide_index=True, use_container_width=True,
                     column_config={"category": "Nhóm nghề", "currency": "Tiền tệ", "pay_period": "Kỳ trả lương",
                                    "median_salary": "Trung vị mẫu", "min_salary": "Thấp nhất", "max_salary": "Cao nhất",
                                    "job_count_with_salary": "Tin có lương", "total_job_count": "Số tin mẫu",
                                    "coverage_pct": "Độ phủ (%)", "data_source": "Nguồn"})
    with st.expander("Nguồn & giới hạn"):
        st.markdown("- Median và dải min/max có sẵn trong sample; không tính lại phân vị.\n- Không FX, không trộn tiền tệ hoặc kỳ trả lương.\n- SYNTHETIC SAMPLE; nghiệm thu nghiệp vụ D07 IT salary vẫn PENDING.")
