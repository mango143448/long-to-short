import streamlit as st

from src.session import init_defaults, sync_live_to_session
from src.ui.components import inject_css
from src.ui.sidebar import render_sidebar
from src.ui.dashboard import render_dashboard
from src.ui.results import render_results
from src.ui.landing import render_landing
from src.controller import handle_start, get_active_url, ensure_thread, advance_if_done
from src.types import JobResult

st.set_page_config(
    page_title="Video \u2192 Shorts",
    page_icon="\u2702\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_defaults()
inject_css()

st.markdown('<p class="app-title">Long Video \u2192 Shorts</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="app-sub">Paste a YouTube link \u00b7 AI picks the best moments \u00b7 Download 9:16 clips</p>',
    unsafe_allow_html=True,
)

sidebar = render_sidebar()

if sidebar["analyze_btn"]:
    handle_start(sidebar)

active_url = get_active_url()

if active_url:
    ensure_thread(sidebar, active_url)
    sync_live_to_session(active_url)
    render_dashboard(active_url=active_url)
    if advance_if_done(active_url):
        st.rerun()
    else:
        st.rerun()

results = st.session_state.get("results", {})
has_any_result = bool(results) and any(
    isinstance(v, JobResult) for v in results.values()
)

if not active_url and has_any_result:
    render_dashboard()
    render_results()
elif not active_url and not sidebar["analyze_btn"]:
    render_landing()
