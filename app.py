import threading
import time

import streamlit as st

from src.config import MAX_BATCH_URLS
from src.pipeline.single import run_single
from src.state.manager import (
    init_defaults,
    init_steps,
    live_clear,
    sync_live_to_session,
)
from src.types import AnalysisConfig, JobResult
from src.ui.styles import inject_css
from src.ui.sidebar import render_sidebar
from src.ui.dashboard import render_dashboard
from src.ui.results import render_results
from src.ui.landing import render_landing

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

# ── Button handler ──────────────────────────────────────────────────────────────
if sidebar["analyze_btn"]:
    if not sidebar["active_groq_keys"]:
        st.error("Please provide at least one Groq API key.")
        st.stop()

    urls_to_process: list[str] = []
    if sidebar["is_youtube"]:
        if sidebar["batch_mode"]:
            raw = sidebar.get("yt_urls_raw", "")
            urls_to_process = [u.strip() for u in raw.split("\n") if u.strip()][:MAX_BATCH_URLS]
            if not urls_to_process:
                st.error("Please enter at least one YouTube URL.")
                st.stop()
        else:
            if not sidebar["yt_url"].strip():
                st.error("Please enter a YouTube URL.")
                st.stop()
            urls_to_process = [sidebar["yt_url"].strip()]
    else:
        if not sidebar["pasted_transcript"].strip():
            st.error("Please paste a transcript.")
            st.stop()
        urls_to_process = ["__manual__"]

    for k in list(st.session_state.keys()):
        if k.startswith("_"):
            del st.session_state[k]

    live_clear()
    st.session_state.results = {}
    st.session_state.logs = {}
    st.session_state.steps = {}
    st.session_state.batch_queue = urls_to_process
    st.session_state.batch_index = 0

    for url in urls_to_process:
        init_steps(url)

    st.rerun()

# ── Processing loop (background thread + polling) ──────────────────────────────
batch_queue = st.session_state.get("batch_queue", [])
batch_index = st.session_state.get("batch_index", -1)
processing = 0 <= batch_index < len(batch_queue)

if processing:
    url = batch_queue[batch_index]
    thread_key = f"_thread_{url}"

    if thread_key not in st.session_state:
        st.session_state[f"_started_{url}"] = time.time()

        analysis_cfg = AnalysisConfig(
            min_dur=sidebar["min_dur"],
            max_dur=sidebar["max_dur"],
            custom_context=sidebar["custom_prompt"],
            auto_adjust=sidebar["auto_adjust"],
        )

        t = threading.Thread(
            target=run_single,
            args=(url, sidebar["active_groq_keys"], analysis_cfg),
            kwargs={
                "pasted_transcript": sidebar["pasted_transcript"],
                "manual_video_url": sidebar["manual_video_url"],
                "cookie_path": sidebar["cookie_path"],
                "auto_adjust": sidebar["auto_adjust"],
            },
            daemon=True,
        )
        st.session_state[thread_key] = t
        t.start()

    sync_live_to_session(url)
    render_dashboard(active_url=url)

    if url in st.session_state.get("results", {}):
        for k in [thread_key, f"_started_{url}"]:
            st.session_state.pop(k, None)
        st.session_state.batch_index += 1
        if st.session_state.batch_index >= len(st.session_state.batch_queue):
            st.session_state.batch_index = -1
        st.rerun()
    else:
        time.sleep(1)
        st.rerun()

# ── Results / Landing ───────────────────────────────────────────────────────────
results = st.session_state.get("results", {})
has_any_result = bool(results) and any(
    isinstance(v, JobResult) for v in results.values()
)

if not processing and has_any_result:
    render_dashboard()
    render_results()
elif not processing and not sidebar["analyze_btn"]:
    render_landing()
