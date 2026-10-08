"""Main entry point for the Big Data IT Recruitment Dashboard.

Designed for Streamlit multi-page architecture.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add dashboard folder and project root to sys.path
DASHBOARD_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DASHBOARD_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

import streamlit as st
from components.ui_helpers import render_header

st.set_page_config(
    page_title="IT Recruitment Analytics Dashboard",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_header(
    title="💼 Big Data IT Recruitment Dashboard",
    subtitle="Interactive visual analytics powered by Apache Spark and Streamlit",
)

st.markdown("""
### 📌 Chào mừng đến với Dashboard Scaffold (Dành cho TV3)

Đây là khung phát triển ứng dụng (**Dashboard Development Kit**) được chuẩn bị sẵn nhằm hỗ trợ **Thành viên 3 (TV3)** tiếp quản và phát triển giao diện nhanh chóng, an toàn và đồng bộ với pipeline dữ liệu Big Data.
""")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🧭 Cấu trúc các trang phân tích")
    st.markdown("""
    Sử dụng thanh điều hướng bên trái (Sidebar) để chuyển đổi giữa các trang:

    1. **📊 1_Overview**:
       - Thống kê tổng quan cơ cấu tuyển dụng theo nhóm nghề (Job Category).
       - Cơ cấu kinh nghiệm (Experience Level), địa điểm (Location), hình thức làm việc.
       - *Phụ thuộc pipeline:* Chờ bảng `overview_analytics` từ task **A06**.

    2. **⚡ 2_Skills**:
       - Bảng xếp hạng các kỹ năng kỹ thuật hàng đầu (Top Technical Skills).
       - Nhu cầu kỹ năng theo từng nhóm nghề và độ bao phủ.
       - *Lưu ý quan trọng:* Dữ liệu thô `skills.csv` gốc chỉ là nhóm ngành (Job Functions). Trang này hiển thị mockup và sẽ nhận dữ liệu thật sau khi hoàn thành trích xuất kỹ năng tại task **A05 / A07**.

    3. **💰 3_Salary_Quality**:
       - Phân bố mức lương theo nhóm nghề, kỳ trả lương (Pay Period) và đơn vị tiền tệ.
       - Trang giám sát chất lượng dữ liệu (Data Quality & Pipeline Health): Tỷ lệ thiếu, hồ sơ bản ghi bị cách ly (rejected records), và độ phủ lương thực tế.
       - *Phụ thuộc pipeline:* Chờ chuẩn hóa lương tại task **D07 / A08**.
    """)

with col2:
    st.subheader("📋 Trạng thái tích hợp")
    st.info("""
    - **D01–D04 (Làm sạch dữ liệu):** ✅ PASS (123,849 tin sạch)
    - **D05 Pre-check & Scaffold:** ✅ PASS (Bảo toàn grain)
    - **A03 (Bản đồ JOIN & Kỹ năng):** ⏳ Pending (Chờ TV2)
    - **D05 Official:** ⏸️ Blocked bởi A03
    - **V01–V03 (Dashboard Official):** 🛠️ Scaffold Only
    """)

    st.warning("""
    **💡 Chế độ Development Sample Mode:**
    Hiện tại, dữ liệu analytics chính thức chưa xuất xưởng từ pipeline. Hệ thống được tích hợp chế độ đọc dữ liệu mẫu giả định (`dashboard/sample_data/`) để TV3 có thể xây dựng và căn chỉnh UI ngay lập tức mà không bị lỗi crash.
    """)

st.markdown("---")
st.caption("Big Data IT Recruitment Project • Apache Spark 4.2.0 & Streamlit Scaffold")
