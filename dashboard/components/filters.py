"""Page-local demo consent and compact, unselected-by-default sample filters."""
from typing import Any, Dict
import pandas as pd
import streamlit as st


def render_sample_control() -> bool:
    return st.toggle("Dữ liệu minh họa", value=False,
                       help="Chỉ đọc synthetic sample. Không cấp quyền cho dữ liệu chính thức.")


def render_data_filters(df: pd.DataFrame | None = None) -> Dict[str, Any]:
    selections = {"categories": [], "experience_levels": [], "locations": []}
    if df is None or df.empty:
        return selections
    with st.expander("Bộ lọc minh họa · để trống để xem tất cả", expanded=False):
        for area, (column, label, key) in zip(st.columns(3), (("category", "Nhóm nghề", "categories"),
                                   ("experience_level", "Kinh nghiệm", "experience_levels"),
                                   ("location", "Địa điểm", "locations"))):
            if column in df:
                selections[key] = area.multiselect(label, sorted(df[column].dropna().unique().tolist()), default=[])
    return selections


def render_sidebar_controls(df: pd.DataFrame | None = None) -> Dict[str, Any]:
    return {"sample_mode": render_sample_control(), **render_data_filters(df)}
