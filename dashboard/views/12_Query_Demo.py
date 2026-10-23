"""Explicitly synthetic query lab. No upload, package reader or real fallback."""
from pathlib import Path
import sys
import streamlit as st
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.analytics_views import QUERIES, render_demo
from components.ui_helpers import page_setup, render_header
page_setup("Phòng demo Q02–Q08")
render_header("Phòng demo Q02–Q08", "SYNTHETIC · minh họa cách đọc biểu đồ, không phải kết quả analytics thật.")
query = st.selectbox("Câu hỏi minh họa", tuple(QUERIES), format_func=lambda q: q + " · " + QUERIES[q])
render_demo(query)
