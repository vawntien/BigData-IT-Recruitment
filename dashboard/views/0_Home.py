"""Landing page derived only from session-verified real aggregates."""
from pathlib import Path
import sys
import streamlit as st
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.preview_manager import STATE_KEY, QUERIES
from components.ui_helpers import navigation_link, page_setup, render_header, source_strip, horizontal_bar
import pandas as pd

page_setup('Tổng quan')
render_header('IT Recruitment Analytics', 'Phân tích tuyển dụng IT từ các nguồn aggregate đã xác minh.')
source_strip('REAL DATA — TECHNICAL PREVIEW · Localhost / nội bộ · Production Gate CLOSED')
sources = st.session_state.get(STATE_KEY, {})
q01 = sources.get('Q01', {})
if q01.get('status') == 'READY':
    result = q01['result']
    for col, title, value in zip(st.columns(3), ('Tin tuyển dụng IT', 'Nhóm nghề', 'Nguồn sẵn sàng'),
                                (f'{result.rows[0].denominator_all_it:,}', str(len(result.rows)),
                                 str(sum(sources.get(q, {}).get('status') == 'READY' for q in QUERIES)) + '/6')):
        col.metric(title, value)
    st.subheader('Cơ cấu nhóm nghề IT')
    horizontal_bar(pd.DataFrame([{'Nhóm nghề': row.category, 'Số tin': row.job_count} for row in result.rows]),
                   'Nhóm nghề', 'Số tin', value_title='Số tin ACCEPT')
else:
    st.error('Q01 không khả dụng · ' + q01.get('issue', 'LOCAL_DEMO_NOT_ENABLED'))
    st.caption('Không hiển thị KPI population khi nguồn Q01 chưa được xác minh.')

st.subheader('Khám phá dữ liệu thật')
destinations = [('Q01', 'Nhóm nghề', '5_Q01_Real_Preview.py'),
                ('Q02', 'Kinh nghiệm', '8_Experience.py'), ('Q03', 'Địa điểm', '9_Locations.py'),
                ('Q04', 'Hình thức làm việc', '10_Work_Type.py'), ('Q06', 'Kỹ năng', '2_Skills.py'),
                ('Q08', 'Xu hướng thời gian', '11_Time_Trends.py')]
for offset in range(0, len(destinations), 2):
    for col, (query, title, view) in zip(st.columns(2), destinations[offset:offset+2]):
        with col, st.container(border=True):
            st.subheader(query + ' · ' + title)
            entry = sources.get(query, {})
            st.caption('READY · Đã xác minh' if entry.get('status') == 'READY'
                       else 'ERROR · ' + entry.get('issue', 'LOCAL_DEMO_NOT_ENABLED'))
            navigation_link('views/' + view, label='Xem ' + title.lower() + ' →')
if st.button('Kiểm tra lại nguồn'):
    st.session_state.pop(STATE_KEY, None)
    st.rerun()
with st.expander('Nguồn & phạm vi sử dụng'):
    st.caption('Mỗi phiên mới kiểm SHA-256, manifest, schema và lineage của sáu gói pinned. Chuyển trang giữ kết quả đã xác minh; nguồn thay đổi sẽ bị kiểm lại và lỗi sẽ loại kết quả cũ. Không cộng population giữa các query.')
    st.caption('Q01/Q02/Q03/Q04/Q08 aggregates APPROVED WITH CONDITIONS. Q06 VALIDATED — NOT BUSINESS ACCEPTED. Q05/Q07 chưa có dữ liệu Official trên Dashboard. Dashboard final pending; Production Gate CLOSED.')
