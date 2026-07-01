import threading
import time

import streamlit as st

from src.settings import MAX_BATCH_URLS
from src.pipeline.single import run_single
from src.session import init_steps, live_clear
from src.types import AnalysisConfig


def handle_start(sidebar: dict) -> None:
    if not sidebar["active_groq_keys"]:
        st.error("Please provide at least one Groq API key.")
        st.stop()

    urls = _resolve_urls(sidebar)

    for k in list(st.session_state.keys()):
        if k.startswith("_"):
            del st.session_state[k]

    live_clear()
    st.session_state.results = {}
    st.session_state.logs = {}
    st.session_state.steps = {}
    st.session_state.batch_queue = urls
    st.session_state.batch_index = 0

    for url in urls:
        init_steps(url)

    st.rerun()


def get_active_url() -> str | None:
    queue = st.session_state.get("batch_queue", [])
    idx = st.session_state.get("batch_index", -1)
    if 0 <= idx < len(queue):
        return queue[idx]
    return None


def ensure_thread(sidebar: dict, url: str) -> None:
    thread_key = f"_thread_{url}"
    if thread_key in st.session_state:
        return

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


def advance_if_done(url: str) -> bool:
    if url not in st.session_state.get("results", {}):
        return False

    thread_key = f"_thread_{url}"
    for k in [thread_key, f"_started_{url}"]:
        st.session_state.pop(k, None)

    st.session_state.batch_index += 1
    if st.session_state.batch_index >= len(st.session_state.batch_queue):
        st.session_state.batch_index = -1

    return True


def _resolve_urls(sidebar: dict) -> list[str]:
    if sidebar["is_youtube"]:
        if sidebar["batch_mode"]:
            raw = sidebar.get("yt_urls_raw", "")
            urls = [u.strip() for u in raw.split("\n") if u.strip()][:MAX_BATCH_URLS]
            if not urls:
                st.error("Please enter at least one YouTube URL.")
                st.stop()
            return urls
        if not sidebar["yt_url"].strip():
            st.error("Please enter a YouTube URL.")
            st.stop()
        return [sidebar["yt_url"].strip()]

    if not sidebar["pasted_transcript"].strip():
        st.error("Please paste a transcript.")
        st.stop()
    return ["__manual__"]
