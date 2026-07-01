import time

import streamlit as st

from src.services.transcript import extract_video_id, mmss
from src.services.zip_utils import create_zip_of_results
from src.types import JobResult


def render_results():
    results: dict[str, JobResult] = st.session_state.get("results", {})
    if not results:
        return

    st.markdown("---")
    any_success = any(r.success for r in results.values())

    if any_success:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### \U0001f4e6 Results \u2014 {len(results)} video(s)")
        with col2:
            zip_buf = create_zip_of_results(results)
            st.download_button(
                label="\u2b07\ufe0f Download All as ZIP",
                data=zip_buf,
                file_name=f"shorts_{int(time.time())}.zip",
                mime="application/zip",
                use_container_width=True,
                type="primary",
            )

    logs_dict = st.session_state.get("logs", {})

    for url, data in results.items():
        vid_id = data.vid_id or extract_video_id(url) or "Video"

        if not data.success:
            with st.expander(f"\u274c {vid_id} \u2014 Failed", expanded=True):
                st.error(data.error)
                logs = logs_dict.get(url, [])
                if logs:
                    st.caption("Full log:")
                    st.code("\n".join(logs), language=None)
            continue

        with st.expander(f"\U0001f3ac {vid_id} \u2014 {len(data.clips)} clips", expanded=True):
            for i, clip in enumerate(data.clips):
                dur = clip.end_time - clip.start_time

                with st.container(border=True):
                    lcol, rcol = st.columns([5, 2])
                    with lcol:
                        st.markdown(f'<div class="clip-num">Clip {i + 1} of {len(data.clips)}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="clip-title">{clip.title or "Untitled"}</div>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="clip-time">\u23f1 {mmss(clip.start_time)} \u2192 {mmss(clip.end_time)} &nbsp;\u00b7&nbsp; {dur:.0f}s</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="hook-label">Hook</div>'
                            f'<div class="hook-text">"{clip.hook or "\u2014"}"</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(f'<div class="reason-text">\U0001f4a1 {clip.reason}</div>', unsafe_allow_html=True)
                    with rcol:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if i in data.generated:
                            title_safe = clip.title[:20].replace(" ", "_") if clip.title else "clip"
                            st.download_button(
                                label="\u2b07\ufe0f Download MP4",
                                data=data.generated[i],
                                file_name=f"short_{vid_id}_{i + 1}_{title_safe}.mp4",
                                mime="video/mp4",
                                key=f"dl_{vid_id}_{i}",
                                use_container_width=True,
                                type="primary",
                            )
                        if i in data.clip_transcripts:
                            st.download_button(
                                label="\U0001f4c4 Transcript",
                                data=data.clip_transcripts[i],
                                file_name=f"transcript_{vid_id}_{i + 1}.txt",
                                mime="text/plain",
                                key=f"dl_txt_{vid_id}_{i}",
                                use_container_width=True,
                            )

            logs = logs_dict.get(url, [])
            if logs:
                st.markdown("#### \U0001f4cb Processing Log")
                st.code("\n".join(logs[-40:]), language=None)
