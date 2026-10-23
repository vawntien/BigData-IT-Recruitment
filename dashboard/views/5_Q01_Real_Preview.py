"""Opt-in technical preview; isolated from production and synthetic flows."""

from dataclasses import asdict
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from components.q01_real_preview import load_q01_preview, RUN_ID, D06_RUN
from components.ui_helpers import page_setup, render_header, horizontal_bar


page_setup("Tuyển dụng IT · Q01")
render_header("Tuyển dụng IT · Q01")
real_only = st.session_state.get('_real_only', False)
st.warning("REAL DATA — TECHNICAL PREVIEW · Production Gate CLOSED" if real_only else "VALIDATED / NOT ACCEPTED · Xem trước dữ liệu thật · Production Gate CLOSED")
results_area = st.container()
if real_only:
    from components.preview_manager import current_result
    result = current_result('Q01')
    if result is None:
        st.stop()
else:
    with st.expander("Tải / đổi tệp Q01", expanded=True):
        with st.form("q01_real_preview_load"):
            local_path = st.text_input("Đường dẫn ZIP Q01 trên máy", value="")
            confirmed = st.checkbox("Tôi xác nhận quyền đọc tệp để xem trước", value=False)
            submitted = st.form_submit_button("Tải và xác minh", type="primary")

    if not submitted:
        st.caption("Chọn ZIP và xác nhận quyền đọc. Không tự tải dữ liệu khi mở trang.")
        st.stop()

    result = load_q01_preview(local_path, confirmed=confirmed)
    if not result.passed:
        st.error("Không thể tải Q01 · " + result.issue)
        st.caption("Kiểm tra tệp ZIP và quyền đọc, rồi thử lại. Không hiển thị kết quả của lần tải trước.")
        st.stop()

with results_area:
    table = pd.DataFrame([asdict(row) for row in result.rows])
    for column, label, value in zip(st.columns(4),
                                    ("Tổng tin ACCEPT", "Có phân loại", "Thiếu nhóm", "Số nhóm"),
                                    (f"{result.rows[0].denominator_all_it:,}", f"{result.rows[0].denominator_known:,}",
                                     f"{result.rows[0].denominator_all_it - result.rows[0].denominator_known:,}", f"{len(result.rows):,}")):
        column.metric(label, value)
    st.subheader("Phân bố nhóm nghề")
    chart = table[["category", "job_count", "share_all_it"]].copy()
    chart["Share %"] = chart.pop("share_all_it") * 100
    horizontal_bar(chart, "category", "job_count", value_title="Số tin ACCEPT", tooltip=[
        {"field": "category", "title": "Nhóm nghề"}, {"field": "job_count", "title": "Số tin"}, {"field": "Share %", "title": "Tỷ lệ (%)", "format": ".4f"}])
    with st.expander("Bảng chi tiết · 6 cột"):
        st.dataframe(table, hide_index=True, use_container_width=True,
                     column_config={"category": "Nhóm nghề", "job_count": "Số tin ACCEPT",
                                    "denominator_all_it": "Mẫu số toàn bộ", "denominator_known": "Mẫu số có nhóm",
                                    "share_all_it": st.column_config.NumberColumn("Tỷ phần toàn bộ", format="%.6f"),
                                    "share_known": st.column_config.NumberColumn("Tỷ phần có nhóm", format="%.6f")})
        st.caption("share_all_it / share_known là fraction [0,1]; tooltip phần trăm = fraction × 100 một lần. denominator_all_it: mọi tin ACCEPT; denominator_known: tin ACCEPT có nhóm. Không cộng mẫu số lặp giữa các dòng.")
    with st.expander("Nguồn dữ liệu & giới hạn"):
        st.markdown("**Run TV2:** `" + RUN_ID + "`  \n**Nguồn D06:** `" + D06_RUN + "`  \n**Taxonomy:** `v0.2.2` · **Aggregate:** APPROVED WITH CONDITIONS; display mapping / Dashboard final PENDING")
        st.markdown("- Metadata VALIDATED / NOT ACCEPTED là lịch sử gói; TV1 đã ACCEPT WITH CONDITIONS cho aggregate Q01. Auto-load local read-only được TV1 cho phép; Production Gate CLOSED.\n- Toàn snapshot 5.206 tin classifier ACCEPT; REVIEW giữ riêng với REJECT. Không đại diện toàn thị trường IT.\n- Không hỗ trợ bộ lọc kinh nghiệm, địa điểm hoặc thời gian.\n- Preview loader không tự đối chiếu exact input key-set với Enriched; audit tiếp nhận độc lập là evidence riêng, không nâng quyền hiển thị.\n- Numeric tolerance 1e-12 là chính sách so sánh kỹ thuật, chưa phải tolerance production đã duyệt.")
