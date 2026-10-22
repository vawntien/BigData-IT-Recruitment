"""Single opt-in workspace for the existing skills and salary samples."""
from pathlib import Path
import sys
import streamlit as st
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from components.ui_helpers import page_setup, render_header, empty_state
from components.demo_views import skills_demo, salary_demo
page_setup("Kỹ năng & thu nhập · Minh họa")
render_header("Kỹ năng & thu nhập mẫu")
skills, salary = st.tabs(["Kỹ năng", "Thu nhập"])
with skills:
    if st.toggle("Dữ liệu kỹ năng minh họa", value=False, key="demo_analytics_skills"):
        skills_demo()
    else:
        empty_state("Bản minh họa kỹ năng", "Bật dữ liệu SYNTHETIC để xem biểu đồ và bảng theo nhóm nghề.")
with salary:
    if st.toggle("Dữ liệu thu nhập minh họa", value=False, key="demo_analytics_salary"):
        salary_demo()
    else:
        empty_state("Bản minh họa thu nhập", "Bật dữ liệu SYNTHETIC để so sánh trong cùng tiền tệ và kỳ trả lương.")
