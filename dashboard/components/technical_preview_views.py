"""Validated aggregate presentation for local sessions and manual receiver tests."""
import pandas as pd
import streamlit as st
from .technical_preview import PINS, load_preview
from .ui_helpers import horizontal_bar

NOTES = {
 'Q02': 'NULL khác literal Unknown. Nhãn formatted_experience_level không phải số năm kinh nghiệm; không suy luận seniority.',
 'Q03': 'Giữ nguyên raw location sau trim. Không geocode hoặc gộp tên. Top N chỉ giới hạn biểu đồ; mẫu số toàn population giữ nguyên. NULL được giữ nếu có; snapshot này không có NULL (missing=0).',
 'Q04': 'Hai marginal độc lập. Remote TRUE=1.485 / NULL=3.721; không quan sát FALSE. NULL không phải onsite/FALSE. Không suy joint work type × remote. Raw pair chỉ là formatted_work_type × work_type, không normalization hoặc tỷ lệ.',
 'Q08': 'Hai timestamp bases độc lập theo UTC; không cộng counts giữa bases, không điền kỳ thiếu hoặc suy timezone địa phương. Phân bố snapshot không chứng minh tăng trưởng thị trường hoặc cửa sổ thu thập đầy đủ.',
 'Q06': 'NOT BUSINESS ACCEPTED · PASS WITH EXPLICIT EXCLUSIONS. Raw phrase/offset audit NOT VERIFIED. Mẫu số gồm zero-hit. Group và Experience độc lập; không group × experience, ngày hoặc địa điểm. Một tin có nhiều skill nên tổng tỷ lệ có thể vượt 100%.',
}

def label(value):
    if value is None: return 'NULL · thiếu dữ liệu'
    if type(value) is bool: return 'TRUE' if value else 'FALSE'
    return value

def metrics(values):
    for c, (name, value) in zip(st.columns(len(values)), values): c.metric(name, f'{value:,}')

def detail(frame, title):
    with st.expander(title): st.dataframe(frame, hide_index=True, use_container_width=True)

def bar(rows, key, title, top_n=None):
    st.subheader(title)
    frame = pd.DataFrame(rows)
    frame['Nhãn nguồn'] = [label(r[key]) for r in rows]
    visible = frame.sort_values(['job_count', 'Nhãn nguồn'], ascending=[False, True])
    if top_n: visible = visible.head(top_n)
    horizontal_bar(visible, 'Nhãn nguồn', 'job_count', value_title='Số tin', tooltip=[{'field':'Nhãn nguồn'}, {'field':'job_count'}])
    detail(frame, 'Bảng aggregate đầy đủ · ' + title)

def render_real(query):
    st.warning('REAL DATA — TECHNICAL PREVIEW · Localhost / nội bộ · Production Gate CLOSED')
    st.caption(NOTES[query])
    result_area = st.container()
    pin = PINS[query]
    if st.session_state.get('_real_only', False):
        from .preview_manager import current_result
        result = current_result(query)
        if result is None:
            return
        top_n = 10
        selected = {}
        if query in ('Q03', 'Q06'):
            top_n = st.selectbox('Top N · chỉ thay trình bày', (5, 10, 15, 30), index=1, key=query + '_top_n')
        if query == 'Q06':
            for suffix, dim, title in [('group','a02_group','Nhóm IT'), ('experience','formatted_experience_level','Kinh nghiệm')]:
                scopes = [s['scope'] for s in pin['tables']['q06_skills_by_' + suffix]['scope_denominators']]
                index = st.selectbox(title + ' · scope độc lập', range(len(scopes)), format_func=lambda i, s=scopes: label(s[i]), key=query + suffix)
                selected[suffix] = scopes[index]
    else:
        with st.expander('Tải / đổi tệp ' + query, expanded=True):
            with st.form('technical_preview_' + query):
                path = st.text_input('Đường dẫn ZIP ' + query + ' trên máy', value='')
                consent = st.checkbox('Tôi xác nhận quyền đọc và hiển thị technical preview ' + query, value=False)
                top_n = 10
                selected = {}
                if query in ('Q03', 'Q06'):
                    top_n = st.selectbox('Top N · chỉ thay trình bày', (5, 10, 15, 30), index=1)
                if query == 'Q06':
                    for suffix, dim, title in [('group','a02_group','Nhóm IT'), ('experience','formatted_experience_level','Kinh nghiệm')]:
                        scopes = [s['scope'] for s in pin['tables']['q06_skills_by_' + suffix]['scope_denominators']]
                        index = st.selectbox(title + ' · scope độc lập', range(len(scopes)), format_func=lambda i, s=scopes: label(s[i]))
                        selected[suffix] = scopes[index]
                submitted = st.form_submit_button('Tải và xác minh', type='primary')
            st.caption('Đổi Top N / scope rồi bấm Tải và xác minh. Không tự đọc khi điều hướng; mỗi lần tải đều kiểm lại toàn bộ gói.')
        if not submitted:
            st.info('Chọn ZIP và bật consent để xem dữ liệu thật. Chưa đọc artifact.')
            return
        result = load_preview(query, path, confirmed=consent)
        if not result.passed:
            st.error('Không thể tải ' + query + ' · ' + result.issue)
            st.caption('Đã xóa toàn bộ KPI, biểu đồ và bảng của lần tải trước.')
            return
    with result_area:
        if query in ('Q02','Q03'):
            rows = next(iter(result.tables.values()))
            N, K = rows[0]['denominator_all_it'], rows[0]['denominator_known']
            metrics([('Tổng tin ACCEPT', N), ('Có giá trị', K), ('Thiếu dữ liệu', N-K)] + ([('Raw buckets',len(rows))] if query == 'Q03' else []))
            bar(rows, 'category', 'Phân bố kinh nghiệm' if query == 'Q02' else 'Top địa điểm nguyên gốc', top_n if query == 'Q03' else None)
            st.caption(f'Mẫu số toàn bộ {N:,}; mẫu số có giá trị {K:,}. share_all_it / share_known là fraction [0,1]; không cộng mẫu số lặp theo dòng.')
        elif query == 'Q04':
            for tab, name, key, title in zip(st.tabs(['Loại việc làm','Remote flag','Raw pair crosscheck']), ['q04_work_type','q04_remote_flag','q04_work_type_crosscheck'], ['category','remote_allowed',None], ['Loại việc làm','Cờ remote','Raw pair']):
                with tab:
                    rows = result.tables[name]
                    if key:
                        if key == 'category': metrics([('Tổng tin ACCEPT',rows[0]['denominator_all_it']),('Có giá trị',rows[0]['denominator_known']),('Thiếu dữ liệu',rows[0]['denominator_all_it']-rows[0]['denominator_known'])])
                        else: metrics([('Tổng tin ACCEPT',rows[0]['denominator_all_it']),('TRUE',sum(r['job_count'] for r in rows if r['remote_allowed'] is True)),('NULL',sum(r['job_count'] for r in rows if r['remote_allowed'] is None))])
                        bar(rows,key,title)
                    else: detail(pd.DataFrame(rows), 'Raw formatted_work_type × work_type · không phải remote joint')
        elif query == 'Q08':
            names = ['q08_original_month','q08_original_week_start_utc','q08_listed_month','q08_listed_week_start_utc']
            titles = ['Original listed time / tháng · UTC','Original listed time / tuần · UTC','Listed time / tháng · UTC','Listed time / tuần · UTC']
            for tab, name, title in zip(st.tabs(titles),names,titles):
                with tab:
                    rows = result.tables[name]; valid = rows[0]['valid_timestamp_n']
                    metrics([('Population',result.summary['denominator']),('Timestamp hợp lệ',valid),('Thiếu timestamp',result.summary['denominator']-valid)])
                    st.subheader(title)
                    frame = pd.DataFrame(rows).sort_values('period')
                    st.vega_lite_chart(frame, {'height':280, 'mark':{'type':'bar','color':'#2563A6'},
                        'encoding':{'x':{'field':'period','type':'ordinal','sort':'ascending','title':'Kỳ UTC','axis':{'labelAngle':-35}},
                                    'y':{'field':'job_count','type':'quantitative','title':'Số tin','axis':{'format':',.0f','tickMinStep':1}},
                                    'tooltip':[{'field':'period','title':'Kỳ UTC'},{'field':'job_count','title':'Số tin'}]},
                        'config':{'view':{'stroke':None}}}, use_container_width=True)
                    detail(frame, 'Bảng aggregate đầy đủ · ' + title)
                    st.caption('UTC · chỉ kỳ quan sát. Tuần bắt đầu thứ Hai. Không thêm kỳ có count=0.')
        else:
            metrics([('Population · gồm zero-hit',result.summary['denominator']),('Có skill',result.summary['denominator']-result.summary['zero_hit_jobs']),('Zero-hit',result.summary['zero_hit_jobs'])])
            for tab,suffix in zip(st.tabs(['Global Top Skills','Theo nhóm IT','Theo kinh nghiệm']), ['global','group','experience']):
                with tab:
                    name = 'q06_skills_' + ('global' if suffix == 'global' else 'by_' + suffix)
                    rows = result.tables[name]
                    if suffix != 'global':
                        dim = 'a02_group' if suffix == 'group' else 'formatted_experience_level'
                        rows = tuple(r for r in rows if r[dim] == selected[suffix])
                        st.caption('Scope: ' + label(selected[suffix]))
                    metrics([('Mẫu số scope · processed_n',rows[0]['processed_n'])])
                    bar(rows,'skill_name','Kỹ năng · ' + suffix,top_n)
                    st.caption('Giữ nguyên job_count, processed_n và fraction. Không tính mẫu số từ các skill đang hiển thị; zero-hit theo từng scope chưa có riêng trong aggregate này.')
        with st.expander('Nguồn & phạm vi · ' + query):
            st.code('ZIP SHA-256: ' + result.sha256 + '\nManifest SHA-256: ' + pin['members'][pin['manifest']] + '\nRun: ' + result.run_id + '\nD06: official_20261021_a9dddfe4\nEnriched: 17ae5383e848f7323b99800bd3d79a72e84e2bca62844f66dd00aaa06e80a9b2')
            st.caption('Business: ' + ('NOT BUSINESS ACCEPTED; Authorization V05 có giới hạn.' if query == 'Q06' else 'APPROVED WITH CONDITIONS cho aggregate; Dashboard final chưa nghiệm thu. Decision: ' + pin['approval']['decision_id']))
            st.caption('Population chỉ D06 ACCEPT, không đại diện toàn thị trường IT; REVIEW/REJECT nằm ngoài mẫu số. Taxonomy v0.2.2. Không arbitrary cross-filter. Shared-layout adapter NOT_IMPLEMENTED; không claim production compliance.')
            st.caption('Provenance hash-bound không phải signed process-I/O attestation. Producer PARTIAL_SUCCESS không phải full-pipeline PASS. Metadata literal date 2026-10-19 khác actual run 2026-10-22; historical checkout 3c7c628 khác publication 36a2624. Schema kiểm physical footer, không thay bằng reader nullability. Numeric tolerance 1e-12 cho preview kỹ thuật. Không mở D09/Q07/Production Gate.')
