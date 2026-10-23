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
source_strip("Demo Big Data · Q01 preview thật · Q02/Q03/Q04/Q06/Q08: real technical preview · Production Gate CLOSED")
st.subheader("Không gian phân tích")
left, right = st.columns(2)
with left, st.container(border=True):
    st.markdown('<span class="nav-card-marker"></span>', unsafe_allow_html=True)
    st.subheader("Tuyển dụng IT · Q01")
    st.caption("Aggregate có approval kèm điều kiện; display mapping và Dashboard final vẫn pending.")
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
st.subheader("Khám phá theo câu hỏi")
left, right = st.columns(2)
with left, st.container(border=True):
    st.subheader("Kinh nghiệm, địa điểm & việc làm")
    st.caption("Preview thật tại localhost sau consent và kiểm ZIP. Có phòng demo SYNTHETIC riêng.")
    navigation_link("views/8_Experience.py", label="Kinh nghiệm · Q02 →")
    navigation_link("views/9_Locations.py", label="Địa điểm · Q03 →")
    navigation_link("views/10_Work_Type.py", label="Việc làm & remote · Q04 →")
with right, st.container(border=True):
    st.subheader("Xu hướng & phòng demo")
    st.caption("Hai mốc thời gian UTC riêng. Demo giữ NULL, mẫu số và zero-hit rõ ràng.")
    navigation_link("views/11_Time_Trends.py", label="Xu hướng thời gian · Q08 →")
    navigation_link("views/12_Query_Demo.py", label="Trình diễn Q02–Q08 · SYNTHETIC →")
with st.expander("Nguồn & phạm vi sử dụng"):
    st.markdown("- Trang chủ không tự tải dữ liệu.\n- Q01 chỉ xem toàn bộ snapshot sau xác nhận quyền đọc.\n- Dữ liệu SYNTHETIC và kiểm kê HISTORICAL không phải kết quả IT production.\n- Q01–Q04/Q08 aggregates APPROVED WITH CONDITIONS; Q06 NOT BUSINESS ACCEPTED; Dashboard final pending, Production Gate CLOSED.")
