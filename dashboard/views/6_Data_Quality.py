"""Historical RAW/CLEAN audit presentation; no live datasets or IT KPI claims."""
from pathlib import Path
import sys
import pandas as pd
import streamlit as st
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from components.ui_helpers import page_setup, render_header, source_strip, horizontal_bar
page_setup("Chất lượng dữ liệu")
render_header("Chất lượng dữ liệu", "Độ phủ, khuyết thiếu và kiểm tra quan hệ từ kiểm kê lịch sử.")
source_strip("HISTORICAL RAW/CLEAN · ALL JOBS · không phải accepted IT production")
for col, label, value in zip(st.columns(4), ("Tin thô đã kiểm kê", "Có thông tin lương", "Bản ghi cách ly", "Mojibake đã xử lý"), ("123,849", "29.13%", "142", "83")):
    col.metric(label, value)

missing = pd.DataFrame([
    ("closed_time", 99.13, "Gần như toàn bộ NULL"), ("skills_desc", 98.03, "Không dùng làm nguồn kỹ năng chính"),
    ("med_salary", 94.93, "Không phải median thống kê"), ("remote_allowed", 87.69, "NULL không phải onsite"),
    ("applies", 81.17, "Không đại diện số ứng viên"), ("min_salary / max_salary", 75.94, "Khoảng lương nguồn"),
    ("formatted_experience_level", 23.75, "Giữ missing khi phân tích")], columns=["Field", "Missing %", "Diễn giải"])
st.subheader("Khuyết thiếu trong postings")
horizontal_bar(missing, "Field", "Missing %", color="#14867D", value_title="Tỷ lệ thiếu (%)", number_format=".0f", tooltip=[{"field": "Field"}, {"field": "Missing %"}, {"field": "Diễn giải"}])
with st.expander("Bảng kiểm kê & nguồn dữ liệu", expanded=False):
    st.caption("36.073 tin có thông tin lương. 142 dòng cách ly: employee_counts (122), company_specialities (20); không phải 142 tin IT classifier REJECT.")
    st.caption("D03: 16 trường thiếu từ 20%. Giữ orphan trong audit, không thêm chúng vào population postings khi JOIN.")
    st.dataframe(missing, hide_index=True, use_container_width=True, column_config={"Field": "Trường dữ liệu", "Missing %": "Tỷ lệ thiếu (%)"})
    st.dataframe(pd.DataFrame([("salaries", 4712, "88.45%"), ("job_skills", 7990, "96.28%"), ("job_industries", 5845, "96.29%"), ("benefits", 2550, "95.71%")], columns=["Bảng con", "Dòng mồ côi", "Độ phủ khóa"]), hide_index=True, use_container_width=True)
    st.caption("Nguồn: D03/D04 missingness & cleaning audit; D05 pre-check referential coverage. Giá trị historical đã có trên Dashboard cũ; không phải kiểm kê live hoặc quyết định nghiệm thu mới.")
