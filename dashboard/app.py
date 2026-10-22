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
st.markdown(STYLE, unsafe_allow_html=True)
pages = {
    "Khám phá": [st.Page("views/0_Home.py", title="Tổng quan", default=True),
                 st.Page("views/6_Data_Quality.py", title="Chất lượng dữ liệu")],
    "Phân tích": [st.Page("views/5_Q01_Real_Preview.py", title="Tuyển dụng IT · Q01", url_path="Q01_Real_Preview"),
                  st.Page("views/2_Skills.py", title="Kỹ năng", url_path="Skills"),
                  st.Page("views/3_Salary_Quality.py", title="Thu nhập", url_path="Salary_Quality")],
    "Minh họa · Synthetic": [st.Page("views/1_Overview.py", title="Cơ cấu tuyển dụng", url_path="Overview"),
                          st.Page("views/7_Demo_Analytics.py", title="Kỹ năng & thu nhập mẫu", url_path="Demo_Analytics"),
                          st.Page("views/4_Q01_Synthetic_Demo.py", title="Q01 · Minh họa", url_path="Q01_Synthetic_Demo")],
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
