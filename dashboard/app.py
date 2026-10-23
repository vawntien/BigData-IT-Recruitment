"""Native grouped navigation; pages own presentation, readers own data gates."""
from pathlib import Path
import sys
import streamlit as st

DASHBOARD_DIR = Path(__file__).resolve().parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from components.ui_helpers import STYLE

st.set_page_config(page_title="IT Recruitment Analytics", layout="wide", initial_sidebar_state="auto")
st.session_state["_analytics_shell"] = True
st.session_state["_real_only"] = True
from components.preview_manager import initialize_session
initialize_session()
st.markdown(STYLE, unsafe_allow_html=True)
pages = {
    "Khám phá": [st.Page("views/0_Home.py", title="Tổng quan", default=True),
                 st.Page("views/6_Data_Quality.py", title="Chất lượng dữ liệu")],
    "Phân tích tuyển dụng IT": [st.Page("views/5_Q01_Real_Preview.py", title="Q01 — Nhóm nghề", url_path="Q01_Real_Preview"),
                  st.Page("views/8_Experience.py", title="Q02 — Kinh nghiệm", url_path="Experience"),
                  st.Page("views/9_Locations.py", title="Q03 — Địa điểm", url_path="Locations"),
                  st.Page("views/10_Work_Type.py", title="Q04 — Hình thức làm việc", url_path="Work_Type"),
                  st.Page("views/2_Skills.py", title="Q06 — Kỹ năng", url_path="Skills"),
                  st.Page("views/11_Time_Trends.py", title="Q08 — Xu hướng thời gian", url_path="Time_Trends")],
}
page = st.navigation(pages, position="hidden")
with st.sidebar:
    st.markdown("### IT Recruitment")
    st.caption("KHÔNG GIAN PHÂN TÍCH")
    for group, destinations in pages.items():
        st.markdown("**" + group + "**")
        for destination in destinations:
            st.page_link(destination, label=destination.title, use_container_width=True)
    st.caption("Production Gate CLOSED")
page.run()
