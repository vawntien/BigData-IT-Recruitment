"""Product landing page. No dataset discovery or implicit receiving."""
from pathlib import Path
import sys
import streamlit as st
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from components.ui_helpers import navigation_link, page_setup, render_header, source_strip

page_setup("Tổng quan")
render_header("IT Recruitment Analytics", "Khám phá cơ cấu tuyển dụng, kỹ năng và thu nhập.")
source_strip("Q01: VALIDATED / NOT ACCEPTED · Phân tích khác: chờ tích hợp · Production Gate CLOSED")
st.subheader("Không gian phân tích")
left, right = st.columns(2)
with left, st.container(border=True):
    st.markdown('<span class="nav-card-marker"></span>', unsafe_allow_html=True)
    st.subheader("Tuyển dụng IT · Q01")
    st.caption("Phân bố nhóm nghề từ ZIP thật đã xác minh; chưa nghiệm thu nghiệp vụ.")
    navigation_link("views/5_Q01_Real_Preview.py", label="Xem tuyển dụng IT →")
with right, st.container(border=True):
    st.markdown('<span class="nav-card-marker"></span>', unsafe_allow_html=True)
    st.subheader("Chất lượng dữ liệu")
    st.caption("Kiểm kê lịch sử RAW/CLEAN: khuyết thiếu và độ phủ khóa.")
    navigation_link("views/6_Data_Quality.py", label="Xem chất lượng dữ liệu →")
left, right = st.columns(2)
with left, st.container(border=True):
    st.markdown('<span class="nav-card-marker"></span>', unsafe_allow_html=True)
    st.subheader("Kỹ năng & thu nhập")
    st.caption("Theo dõi trạng thái nguồn của các phân tích chính thức.")
    c1, c2 = st.columns(2)
    with c1:
        navigation_link("views/2_Skills.py", label="Kỹ năng →")
    with c2:
        navigation_link("views/3_Salary_Quality.py", label="Thu nhập →")
with right, st.container(border=True):
    st.markdown('<span class="nav-card-marker"></span>', unsafe_allow_html=True)
    st.subheader("Khu vực minh họa")
    st.caption("Khám phá biểu đồ tuyển dụng bằng dữ liệu SYNTHETIC.")
    navigation_link("views/1_Overview.py", label="Khám phá bản minh họa →")
with st.expander("Nguồn & phạm vi sử dụng"):
    st.markdown("- Trang chủ không tự tải dữ liệu.\n- Q01 chỉ xem toàn bộ snapshot sau xác nhận quyền đọc.\n- Dữ liệu SYNTHETIC và kiểm kê HISTORICAL không phải kết quả IT production.\n- Nghiệm thu nghiệp vụ vẫn PENDING; Production Gate CLOSED.")
