"""Skills availability; synthetic exploration lives in the Demo workspace."""
from pathlib import Path
import sys
import streamlit as st
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from components.ui_helpers import navigation_link, page_setup, render_header, source_strip, empty_state
page_setup("Kỹ năng")
render_header("Phân tích kỹ năng", "Kỹ năng kỹ thuật được trích xuất từ mô tả tuyển dụng.")
source_strip("Nguồn thật · A05 / A07: chờ tích hợp và nghiệm thu")
empty_state("Chưa có nguồn kỹ năng đã nghiệm thu", "Chưa có biểu đồ kỹ năng chính thức. Bạn có thể xem bố cục bằng dữ liệu SYNTHETIC tại khu vực minh họa.")
with st.expander("Nguồn & cách diễn giải", expanded=False):
    st.info("Q05 job functions khác Q06 technical skills. Không dùng skills.csv làm nguồn kỹ năng kỹ thuật. Mẫu số Q06 cần gồm mọi tin có description xử lý hợp lệ, kể cả không trích ra skill. Chưa có analytics chính thức tại đây.")
if st.session_state.get("_analytics_shell", False):
    navigation_link("views/7_Demo_Analytics.py", label="Xem minh họa kỹ năng →")
