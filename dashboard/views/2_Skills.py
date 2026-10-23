"""Skills availability; synthetic exploration lives in the Demo workspace."""
from pathlib import Path
import sys
import streamlit as st
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from components.ui_helpers import navigation_link, page_setup, render_header, source_strip, empty_state
from components.analytics_views import pending_content
page_setup("Kỹ năng")
render_header("Phân tích kỹ năng", "Kỹ năng kỹ thuật được trích xuất từ mô tả tuyển dụng.")
pending_content("Q06")
with st.expander("Nguồn dữ liệu và giới hạn", expanded=False):
    st.caption("Q05 · Nhãn chức năng nguồn chưa được tích hợp trên Dashboard; consumer signoff và Q05 Official còn chờ. Q06 Technical Preview hoạt động độc lập với Q05.")
    st.info("Q05 job functions khác Q06 technical skills. Không dùng skills.csv làm nguồn kỹ năng kỹ thuật. Mẫu số Q06 cần gồm mọi tin có description xử lý hợp lệ, kể cả không trích ra skill. Q06 technical preview nằm riêng bên trên; Q05 chưa được tích hợp.")
if st.session_state.get("_analytics_shell", False) and not st.session_state.get("_real_only", False):
    navigation_link("views/7_Demo_Analytics.py", label="Xem minh họa kỹ năng →")
