"""Existing V2 routes for isolated real previews and opt-in synthetic demos."""
import pandas as pd
import streamlit as st
from .analytics_demo import bucket_label, build_demo, validate_demo
from .ui_helpers import empty_state, horizontal_bar, navigation_link, page_setup, render_header, source_strip

QUERIES = {"Q02": "Kinh nghiệm", "Q03": "Địa điểm", "Q04": "Hình thức làm việc",
           "Q08": "Xu hướng thời gian", "Q06": "Kỹ năng IT"}
SECTIONS = {"Q02": ("Phân bố mức kinh nghiệm",), "Q03": ("Top địa điểm",),
            "Q04": ("Loại việc làm", "Cờ remote"),
            "Q08": ("original_listed_time · UTC", "listed_time · UTC"),
            "Q06": ("Global Top Skills", "Theo nhóm IT", "Theo kinh nghiệm")}


def pending_content(query):
    # Compatibility entry point retained for the existing V2 routes.
    from .technical_preview_views import render_real
    render_real(query)


def pending_page(query):
    page_setup(QUERIES[query])
    render_header(QUERIES[query], "Phân tích snapshot · " + query)
    pending_content(query)


def _metrics(values):
    for col, (label, value) in zip(st.columns(len(values)), values):
        col.metric(label, f"{value:,}" if type(value) is int else value)


def _frame(partition):
    return pd.DataFrame([{"Nhóm": bucket_label(r.key), "Số tin mẫu": r.count,
        "Mẫu số toàn bộ": partition.population, "Mẫu số có giá trị": partition.known,
        "Tỷ lệ toàn bộ (%)": None if r.share_all is None else r.share_all * 100,
        "Tỷ lệ có giá trị (%)": None if r.share_known is None else r.share_known * 100} for r in partition.rows])


def _table(frame, label="Bảng chi tiết & mẫu số"):
    with st.expander(label, expanded=False):
        st.dataframe(frame, hide_index=True, use_container_width=True)


def _partition_view(partition, title):
    _metrics((("Tin trong population mẫu", partition.population), ("Có giá trị", partition.known), ("Không xác định", partition.missing)))
    st.subheader(title)
    frame = _frame(partition)
    horizontal_bar(frame, "Nhóm", "Số tin mẫu", value_title="Số tin · SYNTHETIC", tooltip=[
        {"field": "Nhóm"}, {"field": "Số tin mẫu"}, {"field": "Tỷ lệ toàn bộ (%)", "format": ".2f"}])
    _table(frame)


def _locations(partition):
    _metrics((("Population mẫu", partition.population), ("Có địa điểm", partition.known), ("Thiếu địa điểm", partition.missing)))
    top_n = st.selectbox("Top N địa điểm · chỉ thay trình bày", (3, 5, 10, 15), index=1)
    known = [r for r in partition.rows if r.key is not None]
    frame = _frame(partition)
    selected = {bucket_label(r.key) for r in sorted(known, key=lambda r: (-r.count, r.key))[:top_n]}
    visible = frame[frame["Nhóm"].isin(selected)].copy()
    st.subheader("Địa điểm có nhiều tin nhất · mẫu")
    horizontal_bar(visible, "Nhóm", "Số tin mẫu", value_title="Số tin · raw location", tooltip=[
        {"field": "Nhóm"}, {"field": "Số tin mẫu"}, {"field": "Tỷ lệ có giá trị (%)", "format": ".2f"}])
    st.caption(f"Top N không đổi population {partition.population:,} hoặc mẫu số có địa điểm {partition.known:,}. Hanoi và Ha Noi là hai bucket riêng; Remote là chuỗi địa điểm, không phải cờ remote.")
    _table(frame, "Tất cả địa điểm · gồm NULL")


def _time(demo):
    grain = st.radio("Kỳ quan sát · UTC", ("Tháng", "Tuần"), horizontal=True)
    kind = "month" if grain == "Tháng" else "week"
    for area, basis in zip(st.columns(2), ("original_listed_time", "listed_time")):
        p = next(p for p in demo.partitions if p.name == basis + ":" + kind)
        with area:
            st.subheader(basis)
            _metrics((("Population mẫu", p.population), ("Timestamp hợp lệ", p.known), ("Thiếu timestamp", p.missing)))
            frame = _frame(p).rename(columns={"Nhóm": "Kỳ UTC"})
            st.vega_lite_chart(frame, {"height": 280, "mark": {"type": "bar", "color": "#2563A6"},
                "encoding": {"x": {"field": "Kỳ UTC", "type": "ordinal", "sort": "ascending", "axis": {"labelAngle": -35}},
                             "y": {"field": "Số tin mẫu", "type": "quantitative", "title": "Tin mẫu"},
                             "tooltip": [{"field": "Kỳ UTC"}, {"field": "Số tin mẫu"}]},
                "config": {"view": {"stroke": None}}}, use_container_width=True)
            st.caption("UTC · " + ("Tháng theo lịch" if kind == "month" else "Ngày bắt đầu tuần thứ Hai") + "; chỉ kỳ quan sát, không điền kỳ thiếu. Độ phủ: " + (f"{100 * p.known / p.population:.0f}%" if p.population else "Không đủ dữ liệu"))
            _table(frame, "Bảng kỳ UTC · " + basis)
    st.caption("Hai basis đo cùng population minh họa; không cộng counts giữa hai chart. Đây là phân bố snapshot, không phải tốc độ tăng trưởng thị trường hoặc cửa sổ thu thập đầy đủ.")


def _skills(demo):
    for tab, dimension in zip(st.tabs(("Global Top Skills", "Theo nhóm IT", "Theo kinh nghiệm")), ("global", "group", "experience")):
        with tab:
            scopes = [s for s in demo.skills if s.dimension == dimension]
            if dimension == "global":
                scope = scopes[0]
            else:
                index = st.selectbox("Nhóm IT minh họa" if dimension == "group" else "Kinh nghiệm minh họa",
                                     range(len(scopes)), format_func=lambda i, options=scopes: bucket_label(options[i].bucket), key="demo_scope_" + dimension)
                scope = scopes[index]
            _metrics((("Population mẫu · gồm zero-hit", scope.population), ("Có skill", scope.population - scope.zero_hit), ("Zero-hit", scope.zero_hit)))
            top_n = st.selectbox("Top N kỹ năng · chỉ trình bày", (1, 3, 10), index=1, key="demo_skill_top_" + dimension)
            frame = pd.DataFrame([{"Kỹ năng": r.name, "Mã minh họa": r.code, "Số tin mẫu": r.count,
                "Mẫu số scope": scope.population, "Tỷ lệ (%)": None if r.share is None else r.share * 100} for r in scope.rows])
            if not scope.rows:
                empty_state("Không có kỹ năng trong scope mẫu", "Population và zero-hit vẫn được giữ; không tạo skill giả.")
                continue
            visible = frame.sort_values(["Số tin mẫu", "Kỹ năng"], ascending=[False, True]).head(top_n)
            horizontal_bar(visible, "Kỹ năng", "Số tin mẫu", value_title="Tin nhắc skill · SYNTHETIC", tooltip=[
                {"field": "Kỹ năng"}, {"field": "Số tin mẫu"}, {"field": "Mẫu số scope"}, {"field": "Tỷ lệ (%)", "format": ".2f"}])
            _table(frame, "Toàn bộ skills của scope mẫu · " + dimension)
            st.caption("Mẫu số gồm zero-hit, không tính từ Top N. Một tin có thể nhắc nhiều skills, tổng tỷ lệ có thể vượt 100%. Nhắc đến không đồng nghĩa bắt buộc.")
    st.caption("Group và Experience là hai summaries độc lập. Không có group × experience, địa điểm hoặc ngày. NULL kinh nghiệm giữ là không xác định.")


def render_demo(query):
    enabled = st.toggle("Bật minh họa " + query, value=False, key="mvp_demo_" + query)
    st.caption("SYNTHETIC SAMPLE · fixture nhỏ trong bộ nhớ, không lấy từ gói analytics đã receiving.")
    if not enabled:
        empty_state("Chưa bật dữ liệu minh họa", "Bật công tắc để trình diễn biểu đồ. Không đọc artifact thật.")
        return
    try:
        demo = validate_demo(build_demo(query), query)
    except Exception:
        st.error("INVALID_SYNTHETIC_DATA · Không hiển thị số liệu hoặc kết quả lần trước.")
        return
    st.warning("SYNTHETIC MOCKUP DATA — mọi số liệu bên dưới là giả lập, không phải kết quả tuyển dụng thực tế.")
    if query == "Q02":
        _partition_view(demo.partitions[0], "Số tin theo mức kinh nghiệm · mẫu")
        st.caption("NULL là thiếu dữ liệu; literal Unknown là nhãn nguồn riêng. Không suy ra số năm kinh nghiệm từ nhãn. Mẫu số có giá trị không gồm NULL.")
    elif query == "Q03":
        _locations(demo.partitions[0])
    elif query == "Q04":
        for tab, p in zip(st.tabs(("Loại việc làm", "Remote flag")), demo.partitions):
            with tab:
                _partition_view(p, "Loại việc làm · mẫu" if p.name == "work_type" else "Cờ remote · mẫu")
        st.caption("TRUE / FALSE / NULL giữ riêng. NULL không phải FALSE; FALSE không chứng minh onsite. Hai bảng marginal không hỗ trợ joint work type × remote.")
    elif query == "Q08":
        _time(demo)
    elif query == "Q06":
        _skills(demo)
