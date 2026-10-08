"""Salary and Data Quality page: Compensation metrics and dataset health."""

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
from components.data_loader import load_salary_quality_data, STATUS_MISSING
from components.contract_validator import validate_salary_quality_schema
from components.ui_helpers import render_header, render_data_status_banner, render_todo_placeholder
from components.filters import render_sidebar_controls

st.set_page_config(page_title="Salary & Quality - IT Recruitment", page_icon="💰", layout="wide")

render_header(
    title="💰 Lương & Chất lượng Dữ liệu (Salary & Data Quality)",
    subtitle="Khảo sát thông tin mức lương tuyển dụng và bảng điều khiển sức khỏe dữ liệu",
)

# Sidebar controls
controls = render_sidebar_controls()
sample_mode = controls["sample_mode"]

tab_salary, tab_quality = st.tabs(["💵 Phân tích Mức lương (Salary)", "🛡️ Sức khỏe Dữ liệu (Data Quality)"])

# ==============================================================================
# TAB 1: SALARY ANALYSIS
# ==============================================================================
with tab_salary:
    st.info("""
    📌 **Nguyên tắc phân tích lương:**  
    Không tự ý quy đổi tỷ giá ngoại tệ hoặc gộp chung các kỳ trả lương khác nhau (YEARLY vs HOURLY). Mọi so sánh chỉ được thực hiện trong cùng phân nhóm tiền tệ và kỳ hạn trả lương. Các kết quả phân tích mức lương chính thức sẽ do task **D07 & A08** cung cấp.
    """)

    df, status, message = load_salary_quality_data(enable_sample_mode=sample_mode)
    render_data_status_banner(status, message)

    if status != STATUS_MISSING and df is not None:
        is_valid, missing_cols, extra_cols, schema_msg = validate_salary_quality_schema(df)
        if not is_valid:
            st.error(f"⚠️ **Lỗi hợp đồng dữ liệu lương (Schema Mismatch):** {schema_msg}")
            if missing_cols:
                st.markdown(f"Các cột còn thiếu: `{missing_cols}`")
        else:
            col_pay1, col_pay2 = st.columns([1, 1])

            # Yearly salary view
            yearly_df = df[df["pay_period"] == "YEARLY"] if "pay_period" in df.columns else df

            with col_pay1:
                st.markdown("#### 1. Mức lương Trung vị theo Nhóm nghề (USD / Năm)")
                if "category" in yearly_df.columns and "median_salary" in yearly_df.columns and not yearly_df.empty:
                    chart_data = yearly_df.sort_values(by="median_salary", ascending=False)
                    st.bar_chart(chart_data.set_index("category")[["median_salary"]], height=320)
                else:
                    st.info("Chưa có bản ghi lương YEARLY hợp lệ để vẽ biểu đồ.")

            with col_pay2:
                st.markdown("#### 2. Dải lương Tuyển dụng (Min - Median - Max)")
                display_cols = [c for c in ["category", "min_salary", "median_salary", "max_salary", "job_count_with_salary"] if c in yearly_df.columns]
                if not yearly_df.empty and display_cols:
                    st.dataframe(
                        yearly_df[display_cols],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Chưa đủ dữ liệu hiển thị dải lương chi tiết.")

            st.markdown("---")
            render_todo_placeholder(
                section_name="Quantile Salary Distribution (Boxplot/Violin)",
                requirement_desc="Cần phân phối phân vị lương (P25, Median, P75) từ task A08/D07.",
            )
    else:
        st.warning("Dữ liệu phân tích lương chưa sẵn sàng.")

# ==============================================================================
# TAB 2: DATA QUALITY & PIPELINE HEALTH
# ==============================================================================
with tab_quality:
    st.subheader("📊 Hồ sơ Chất lượng Dữ liệu Thực tế (Audit & Clean Pipeline)")

    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    q_col1.metric("Tổng tin thô ban đầu", "123,849", "100% tệp đọc được")
    q_col2.metric("Độ phủ thông tin lương", "29.13%", "36,073 tin có lương")
    q_col3.metric("Bản ghi cách ly (Rejected)", "142 dòng", "122 nhân sự + 20 chuyên môn")
    q_col4.metric("Lỗi Mojibake UTF-8", "83 bản ghi", "Đã sửa thành công 100%")

    st.markdown("---")
    st.markdown("#### 1. Tỷ lệ khuyết thiếu dữ liệu (Missingness Profile)")
    st.markdown("""
    Theo kết quả kiểm kê **D03** (`data/audit/missing_profile.csv`), có **16 trường** có tỷ lệ khuyết thiếu $\ge 20\%$. Các trường quan trọng có tỷ lệ thiếu cao:
    """)

    missing_summary = pd.DataFrame([
        {"Tên cột": "closed_time", "Bảng": "postings", "Tỷ lệ thiếu": "99.13%", "Đánh giá": "Gần như toàn bộ là NULL"},
        {"Tên cột": "skills_desc", "Bảng": "postings", "Tỷ lệ thiếu": "98.03%", "Đánh giá": "Không thể dùng làm nguồn kỹ năng chính"},
        {"Tên cột": "med_salary", "Bảng": "postings", "Tỷ lệ thiếu": "94.93%", "Đánh giá": "Chỉ có min/max lương là chủ yếu"},
        {"Tên cột": "remote_allowed", "Bảng": "postings", "Tỷ lệ thiếu": "87.69%", "Đánh giá": "NULL không đồng nghĩa với on-site"},
        {"Tên cột": "applies", "Bảng": "postings", "Tỷ lệ thiếu": "81.17%", "Đánh giá": "Không đại diện số ứng viên nộp đơn"},
        {"Tên cột": "min_salary / max_salary", "Bảng": "postings", "Tỷ lệ thiếu": "75.94%", "Đánh giá": "Chỉ 24.06% có khoảng lương trực tiếp"},
        {"Tên cột": "formatted_experience_level", "Bảng": "postings", "Tỷ lệ thiếu": "23.75%", "Đánh giá": "Cần nhóm 'Unknown' cho tin thiếu"},
    ])
    st.dataframe(missing_summary, use_container_width=True, hide_index=True)

    st.markdown("#### 2. Tính toàn vẹn của Khóa ngoại và Dữ liệu mồ côi (Referential Coverage)")
    st.markdown("""
    Theo kiểm định **D05 Pre-check** (`data/audit/d05_precheck_join_coverage.csv`), các bảng con đều có một lượng bản ghi có `job_id` không tồn tại trong `postings`:
    - `salaries`: **4,712** dòng mồ côi (độ phủ khóa 88.45%).
    - `job_skills`: **7,990** dòng mồ côi (độ phủ khóa 96.28%).
    - `job_industries`: **5,845** dòng mồ côi (độ phủ khóa 96.29%).
    - `benefits`: **2,550** dòng mồ côi (độ phủ khóa 95.71%).
    """)
