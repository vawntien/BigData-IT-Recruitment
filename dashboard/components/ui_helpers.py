"""Shared presentation system. No artifact access or authorization decisions."""
from html import escape
import streamlit as st
from .artifact_gate import STATUS_BLOCKED, STATUS_INVALID, STATUS_MISSING, STATUS_SAMPLE

NAVY = "#17324F"
BLUE = "#2563A6"
TEAL = "#14867D"

STYLE = """<style>
:root { --navy:#17324F; --blue:#2563A6; --teal:#14867D; --canvas:#F2F5F9; --border:#E1E7EF; }
.stApp { background:var(--canvas); color:var(--navy); font-family:Arial, sans-serif; }
.block-container { max-width:1440px; padding-top:1.25rem; padding-bottom:3rem; }
[data-testid="stHeader"] { background:#F2F5F9; }
[data-testid="stDecoration"] { display:none; }
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] { gap:.35rem; }
[data-testid="stSidebarUserContent"] { padding-top:.5rem; }
[data-testid="stSidebar"] [data-testid="stPageLink"] a { border-radius:8px; padding:6px 10px; }
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover { background:#EAF1F8; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong { color:#64748B; font-size:.78rem; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--border)!important; border-radius:12px!important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > .element-container .nav-card-marker) { background:white; min-height:170px; }
.element-container:has(.nav-card-marker) { display:none; }
h1 { font-size:clamp(1.65rem,3vw,2.2rem)!important; letter-spacing:-.035em; color:var(--navy); }
h2,h3 { color:var(--navy); letter-spacing:-.02em; }
h3 { font-size:1.15rem!important; }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--border); }
[data-testid="stMetric"] { background:white; border:1px solid var(--border); border-top:3px solid var(--teal); border-radius:10px; padding:12px 16px; min-height:108px; height:100%; }
[data-testid="stMetricLabel"] p { font-size:.8rem; color:#52667D; white-space:normal; }
[data-testid="stMetricValue"] { font-size:clamp(1.2rem,2.1vw,1.7rem); color:var(--navy); }
[data-testid="stMetricValue"] > div { white-space:normal; overflow-wrap:anywhere; text-overflow:clip; }
[data-testid="stAlert"] { border-radius:8px; font-size:.9rem; }
[data-testid="stForm"] { background:white; border-color:var(--border); border-radius:10px; }
[data-testid="stDataFrame"], [data-testid="stArrowVegaLiteChart"] { background:white; border-radius:10px; }
.card { background:white; border:1px solid var(--border); border-radius:12px; padding:18px; margin:0 0 4px; }
.card h3 { margin:0 0 10px; font-size:1.05rem; }
.card p { color:#52667D; line-height:1.5; font-size:.92rem; margin:0; }
.eyebrow { color:var(--teal); font-size:.7rem; letter-spacing:.16em; font-weight:700; margin-bottom:8px; text-transform:uppercase; }
.source-strip { background:#EAF1F8; border-left:3px solid var(--blue); border-radius:6px; padding:8px 12px; font-size:.82rem; margin:0 0 8px; }
@media(max-width:640px) { .block-container { padding:1rem 1rem 2rem; } .card { padding:16px; } [data-testid="stMetric"] { min-height:92px; } }
</style>"""

def page_setup(title):
    # st.navigation owns page configuration in the full app; standalone page
    # execution remains supported for the existing AppTest commands.
    if not st.session_state.get("_analytics_shell", False):
        st.set_page_config(page_title=title + " | IT Recruitment", layout="wide")
    st.markdown(STYLE, unsafe_allow_html=True)


def render_header(title, subtitle="", eyebrow=""):
    if eyebrow:
        st.markdown('<div class="eyebrow">' + escape(eyebrow) + '</div>', unsafe_allow_html=True)
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def card(title, text):
    st.markdown('<div class="card"><h3>' + escape(title) + '</h3><p>' + escape(text) + '</p></div>', unsafe_allow_html=True)


def source_strip(text):
    st.markdown('<div class="source-strip">' + escape(text) + '</div>', unsafe_allow_html=True)


def empty_state(title, description):
    card(title, description)


def horizontal_bar(data, category, value, *, color=BLUE, tooltip=None, height=None, value_title=None, number_format=",.0f"):
    """Presentation only: values and units are supplied unchanged by the caller."""
    axis = {"gridColor": "#E1E7EF", "domain": False, "tickCount": 4, "tickMinStep": 1,
            "labelFlush": True, "labelBound": True, "format": number_format}
    # Explicit integer ticks avoid duplicate rounded labels on tiny demo counts,
    # including frontends which do not honor Vega-Lite's tickMinStep hint.
    maximum = float(data[value].max()) if len(data) else 0
    if number_format == ",.0f" and 0 < maximum < 4 and maximum.is_integer():
        axis["values"] = list(range(int(maximum) + 1))
    spec = {
        "height": height or max(240, len(data) * 30),
        "mark": {"type": "bar", "color": color, "cornerRadiusEnd": 3, "size": 16},
        "encoding": {
            "y": {"field": category, "type": "nominal", "sort": "-x",
                  "axis": {"title": None, "labelLimit": 230, "labelFontSize": 12,
                           "labelPadding": 10, "ticks": False, "domain": False}},
            "x": {"field": value, "type": "quantitative", "title": value_title or value,
                  "axis": axis},
            "tooltip": tooltip or [{"field": category}, {"field": value}],
        },
        "config": {"view": {"stroke": None}, "font": "Arial", "background": "white"},
    }
    st.vega_lite_chart(data, spec, use_container_width=True, theme=None)


def render_data_status_banner(status, message):
    if status == STATUS_SAMPLE:
        st.warning("SYNTHETIC MOCKUP DATA — dữ liệu minh họa, không phải kết quả thực tế.")
    elif status == STATUS_MISSING:
        st.error("DATA UNAVAILABLE — chưa có nguồn analytics đủ điều kiện cho nội dung này.")
    elif status == STATUS_INVALID:
        st.error("INVALID DATA — dữ liệu không đáp ứng hợp đồng hiển thị.")
    elif status == STATUS_BLOCKED:
        st.warning("DATA BLOCKED — nguồn chưa được nghiệm thu; không hiển thị kết quả chính thức.")
    else:
        st.error("DATA BLOCKED — trạng thái nguồn chưa được xác nhận.")


def render_todo_placeholder(section_name, requirement_desc):
    empty_state("Nội dung chưa sẵn sàng", requirement_desc)


def navigation_link(path, *, label):
    # Streamlit 1.38's string page_link serializes the page title as its href
    # under st.navigation. A native Page supplies the actual stable URL path.
    from pathlib import Path
    route = Path(path).stem.split("_", 1)[1]
    st.page_link(st.Page(path, url_path=route), label=label)
