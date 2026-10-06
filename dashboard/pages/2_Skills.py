"""Skills analysis page: Technical skills demand and category breakdown."""

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
from components.data_loader import load_skills_data, STATUS_MISSING
from components.contract_validator import validate_skills_schema
from components.ui_helpers import render_header, render_data_status_banner, render_todo_placeholder
from components.filters import render_sidebar_controls

st.set_page_config(page_title="Skills - IT Recruitment", page_icon="⚡", layout="wide")

render_header(
    title="⚡ Phân tích Kỹ năng Tuyển dụng (Skills Analysis)",
    subtitle="Thống kê nhu cầu kỹ năng công nghệ hàng đầu và phân bố theo từng nhóm ngành nghề",
)

# --- CRITICAL NOTICE REGARDING RAW SKILLS VS TECHNICAL SKILLS ---
st.warning("""
🚨 **LƯU Ý NGHIỆP VỤ QUAN TRỌNG (Dành cho Nhóm phát triển & TV3):**
- Bảng dữ liệu gốc `skills.csv` (và `job_skills.csv`) **HOÀN TOÀN KHÔNG CHỨA kỹ năng kỹ thuật cụ thể** (như Python, Java, SQL, AWS, Docker). 35 nhãn trong dữ liệu gốc thực chất là các mã chức năng nghề nghiệp tổng quát (*Job Functions* như `IT`, `ENG`, `FIN`, `HR`).
- Toàn bộ danh mục kỹ năng lập trình cụ thể hiển thị tại trang này (nếu ở chế độ Sample Mode) là **DỮ LIỆU GIẢ ĐỊNH (MOCKUP)** phục vụ dựng khung giao diện.
- **Trang kỹ năng chính thức** sẽ chỉ được kết nối sau khi **Thành viên 2** hoàn thành trích xuất kỹ năng từ văn bản mô tả (`description`) tại các nhiệm vụ **A05 & A07**.
""")

# Sidebar controls
controls = render_sidebar_controls()
sample_mode = controls["sample_mode"]

# Load data
df, status, message = load_skills_data(enable_sample_mode=sample_mode)
render_data_status_banner(status, message)

if status == STATUS_MISSING or df is None:
    st.stop()

# Schema contract validation
is_valid, missing_cols, extra_cols, schema_msg = validate_skills_schema(df)
if not is_valid:
    st.error(f"⚠️ **Lỗi hợp đồng dữ liệu (Schema Mismatch):** {schema_msg}")
    if missing_cols:
        st.markdown(f"Các cột còn thiếu: `{missing_cols}`")
    st.stop()

# Category filter
categories = sorted(df["category"].dropna().unique().tolist()) if "category" in df.columns else []
selected_cat = st.sidebar.selectbox("Lọc theo nhóm nghề cụ thể", options=["Tất cả nhóm nghề"] + categories)

filtered_df = df.copy()
if selected_cat != "Tất cả nhóm nghề" and "category" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["category"] == selected_cat]

if filtered_df.empty:
    st.warning("⚠️ **Không tìm thấy kỹ năng nào cho nhóm nghề đã chọn.** Vui lòng chọn lại tiêu chí.")
    st.stop()

# --- SECTION 1: TOP TECHNICAL SKILLS ---
st.subheader("🏆 Top Kỹ năng Kỹ thuật được Yêu cầu Nhiều nhất")

col_top, col_detail = st.columns([3, 2])

with col_top:
    if "technical_skill" in filtered_df.columns and "job_count" in filtered_df.columns:
        skill_agg = filtered_df.groupby("technical_skill")["job_count"].sum().reset_index()
        skill_agg = skill_agg.sort_values(by="job_count", ascending=False).head(15)
        st.bar_chart(skill_agg.set_index("technical_skill"), height=420)
    else:
        st.info("Trường 'technical_skill' chưa có trong analytics schema.")

with col_detail:
    st.markdown("#### 📋 Bảng chỉ số tần suất xuất hiện")
    if "technical_skill" in filtered_df.columns:
        display_cols = [c for c in ["technical_skill", "category", "job_count", "frequency_pct", "source_method"] if c in filtered_df.columns]
        st.dataframe(
            filtered_df[display_cols].sort_values(by="job_count", ascending=False).head(15),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Chưa có dữ liệu bảng chi tiết.")

st.markdown("---")

# --- SECTION 2: SKILLS BY JOB CATEGORY ---
st.subheader("🧩 Kỹ năng Phổ biến theo Từng Nhóm nghề")

if "category" in df.columns and "technical_skill" in df.columns and "job_count" in df.columns:
    pivot_df = df.pivot_table(index="technical_skill", columns="category", values="job_count", fill_value=0)
    st.dataframe(pivot_df, use_container_width=True)
else:
    render_todo_placeholder(
        section_name="Category vs Skills Matrix",
        requirement_desc="Cần bảng analytics `skills_analytics` tổng hợp ma trận chéo từ task A07.",
    )

# --- SECTION 3: UPSTREAM DATA SOURCE TRANSPARENCY ---
with st.expander("ℹ️ Minh bạch phương pháp trích xuất kỹ năng"):
    st.markdown("""
    - **Nguồn trích xuất dự kiến:** Văn bản trường `description` trong bảng `postings`.
    - **Phương pháp dự kiến:** Đối sánh từ điển từ khóa kỹ thuật (Regex boundaries) tại task A05.
    - **Mẫu số thống kê:** Chỉ tính trên tập tin tuyển dụng đã xác định là CNTT (IT postings) tại D06.
    """)
