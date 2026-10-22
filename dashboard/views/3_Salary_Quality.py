"""Income availability. Historical audits have their own navigation destination."""
from pathlib import Path
import sys
import streamlit as st
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from components.ui_helpers import navigation_link, page_setup, render_header, source_strip, empty_state
page_setup("Thu nhập")
render_header("Phân tích thu nhập", "So sánh thu nhập trong cùng tiền tệ, kỳ trả lương và phạm vi nghề nghiệp.")
source_strip("Nguồn thật · Q07: PENDING · D07 staging chưa phải kết quả đã nghiệm thu")
empty_state("Chờ dữ liệu thu nhập được phê duyệt", "Chưa có biểu đồ thu nhập chính thức. Bản minh họa dùng SYNTHETIC; kiểm kê lịch sử nằm ở Chất lượng dữ liệu.")
with st.expander("Đơn vị & giới hạn phân tích", expanded=False):
    st.info("Không trộn currency, pay_period hoặc compensation_type. Native posted compensation khác annual equivalent. Median/IQR của min_salary và max_salary cần tính riêng với n_min/n_max; med_salary raw không phải median thống kê. Không impute missing thành 0. Q07 source/quantile/outlier policy vẫn cần nghiệm thu.")
if st.session_state.get("_analytics_shell", False):
    navigation_link("views/7_Demo_Analytics.py", label="Xem bản minh họa thu nhập →")
    navigation_link("views/6_Data_Quality.py", label="Xem chất lượng dữ liệu →")
