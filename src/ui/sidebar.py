import atexit
import os
import tempfile
from typing import Optional

import streamlit as st

from src.env import resolve_api_keys
from src.services.video import check_ffmpeg
from src.types import AnalysisConfig, SourceType

_TEMP_FILES: list[str] = []


def _cleanup_temp_files():
    for p in _TEMP_FILES:
        try:
            os.unlink(p)
        except Exception:
            pass


atexit.register(_cleanup_temp_files)


def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("### \u2702\ufe0f Video \u2192 Shorts")
        st.divider()

        st.markdown("**Input source**")
        input_mode = st.radio(
            "input_mode_radio",
            options=["\U0001f3ac YouTube URL", "\U0001f4cb Paste Transcript"],
            index=0 if st.session_state.get("input_mode", "youtube") == "youtube" else 1,
            label_visibility="collapsed",
            horizontal=True,
        )
        is_youtube = input_mode == "\U0001f3ac YouTube URL"
        st.session_state.input_mode = "youtube" if is_youtube else "manual"

        st.markdown("")

        yt_url = ""
        yt_urls_raw = ""
        pasted_transcript = ""
        manual_video_url = ""

        if is_youtube:
            batch_mode = st.toggle("\U0001f517 Batch Mode (up to 10 URLs)", value=st.session_state.get("batch_mode", False))
            st.session_state.batch_mode = batch_mode
            if batch_mode:
                yt_urls_raw = st.text_area(
                    "YouTube URLs \u2014 one per line, max 10",
                    placeholder="https://youtube.com/watch?v=\u2026\nhttps://youtube.com/watch?v=\u2026",
                    key="yt_urls_input",
                    height=150,
                )
                yt_url = ""
            else:
                yt_url = st.text_input("\U0001f517 YouTube URL", placeholder="https://youtube.com/watch?v=\u2026", key="yt_url_input")
                yt_urls_raw = ""
            manual_video_url = st.text_input(
                "\U0001f3a5 Video URL or path (optional)",
                placeholder="Direct video URL or local path",
                key="manual_video_url_yt",
            )
        else:
            st.session_state.batch_mode = False
            pasted_transcript = st.text_area(
                "\U0001f4cb Transcript",
                height=220,
                placeholder="00:00:00\nYour transcript text here...",
                label_visibility="collapsed",
                key="pasted_transcript_input",
            )
            manual_video_url = st.text_input(
                "\U0001f3a5 Video URL or local path",
                placeholder="https://\u2026 or /path/to/video.mp4",
                key="manual_video_url_manual",
            )

        st.divider()
        custom_prompt = st.text_area(
            "\U0001f3af Custom Strategy Prompt (Optional)",
            placeholder="e.g., Focus only on actionable coding tips.",
            key="custom_strategy_input",
        )

        sidebar_key = st.text_input("\U0001f511 Groq API Key (Optional)", type="password", placeholder="Overrides all .env keys", key="sidebar_api_key_input")
        active_groq_keys = resolve_api_keys(sidebar_key)

        if active_groq_keys:
            st.success(f"\u26a1 Groq: {len(active_groq_keys)} key(s) active")
        if not active_groq_keys:
            st.warning("\u26a0\ufe0f No Groq API keys found.")

        st.divider()
        auto_adjust = st.checkbox("\u2728 Auto-Adjust Focus", value=True)
        dur_range = st.slider("Clip duration range (s)", min_value=20, max_value=120, value=(20, 120), step=5, key="dur_range_slider")

        with st.expander("\U0001f6e0\ufe0f Advanced"):
            st.caption("Upload cookies.txt if YouTube blocks your IP.")
            uploaded_cookie = st.file_uploader("cookies.txt", type=["txt"], key="cookie_file_input")
            cookie_path: Optional[str] = st.session_state.get("cookie_path")
            if uploaded_cookie:
                tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
                tmp.write(uploaded_cookie.getbuffer())
                tmp.close()
                _TEMP_FILES.append(tmp.name)
                cookie_path = tmp.name
                st.session_state.cookie_path = tmp.name

        st.divider()
        analyze_btn = st.button("\U0001f680 Analyze & Build", type="primary", use_container_width=True)

        if st.button("\u21ba Reset", use_container_width=True):
            for k in ["batch_queue", "batch_index", "results", "steps", "logs", "batch_mode", "input_mode", "cookie_path"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

        st.divider()
        st.caption("Requires `ffmpeg` on PATH.")
        if not check_ffmpeg():
            st.warning("\u26a0\ufe0f `ffmpeg` not found!")

    return {
        "is_youtube": is_youtube,
        "yt_url": yt_url,
        "yt_urls_raw": yt_urls_raw,
        "pasted_transcript": pasted_transcript,
        "manual_video_url": manual_video_url,
        "custom_prompt": custom_prompt,
        "active_groq_keys": active_groq_keys,
        "auto_adjust": auto_adjust,
        "min_dur": dur_range[0],
        "max_dur": dur_range[1],
        "analyze_btn": analyze_btn,
        "cookie_path": st.session_state.get("cookie_path"),
        "batch_mode": st.session_state.get("batch_mode", False),
    }
