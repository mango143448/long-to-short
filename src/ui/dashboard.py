import re
import time as time_module
from typing import Optional

import streamlit as st

from src.settings import PIPELINE_STEPS, STEP_LABELS
from src.services.transcript import extract_video_id
from src.types import JobResult, StepState

_STAGE_ICONS = {
    "transcript": "\U0001f3a4",
    "analysis": "\U0001f50d",
    "download": "\U0001f4e5",
    "cutting": "\u2702\ufe0f",
    "done": "\u2705",
}
_STAGE_ORDER = ["transcript", "analysis", "download", "cutting", "done"]


def _state_cls(state: str) -> str:
    mapping = {
        "queued": "step-queued",
        "active": "step-active",
        "done": "step-done",
        "failed": "step-failed",
    }
    return mapping.get(state, "step-queued")


def _step_state(steps: dict, step_name: str) -> str:
    return steps.get(step_name, "queued") if steps else "queued"


def _step_label(step: str) -> str:
    return STEP_LABELS.get(step, step.title())


def _vid_badge(url: str) -> str:
    vid = extract_video_id(url) if url != "__manual__" else ""
    if not vid and url != "__manual__":
        return f"<span class='job-badge failed'>NO ID</span>"
    if url == "__manual__":
        return '<span class="job-badge done">\U0001f4c4 Transcript</span>'
    return f'<span class="job-badge done">{vid}</span>'


def _count_clips_found(logs: list[str]) -> int:
    count = 0
    for line in logs:
        m = re.search(r"(\d+)\s*clips?\s+found", line, re.IGNORECASE)
        if m:
            count += int(m.group(1))
    return count


def _count_total_clips_found(logs: list[str]) -> int:
    total = 0
    for line in logs:
        m = re.search(r"Analysis complete\s*[^\d]*(\d+)\s*clips?", line, re.IGNORECASE)
        if m:
            total += int(m.group(1))
    return total


def _chunk_progress(logs: list[str]) -> Optional[tuple[int, int]]:
    for line in reversed(logs):
        m = re.search(r"Analyzing chunk (\d+)/(\d+)", line)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def _stage_progress(logs: list[str]) -> Optional[tuple[int, int]]:
    for line in reversed(logs):
        m = re.search(r"Clip (\d+)/(\d+)", line)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def _format_timer(start: float) -> str:
    elapsed = time_module.time() - start
    mins, secs = divmod(int(elapsed), 60)
    return f"{mins:02d}:{secs:02d}"


def _render_stage_card(stage: str, state: str, icon: str, title: str, sub: str, status: str):
    state_cls = _state_cls(state)
    active = state == "active"
    done = state == "done"

    if active:
        status_html = f'<div class="stage-status"><span class="live-dot"></span> {status}</div>'
    elif done:
        status_html = f'<div class="stage-status" style="color:#3d9970;">\u2705 {status}</div>'
    else:
        status_html = ""

    st.markdown(
        f'<div class="stage-card stage-{stage}">'
        f'  <div class="stage-icon">{icon}</div>'
        f'  <div class="stage-body">'
        f'    <div class="stage-title">{title}</div>'
        f'    <div class="stage-sub">{sub}</div>'
        f'    {status_html}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_dashboard(active_url: Optional[str] = None):
    if active_url:
        _render_active(active_url)
    else:
        _render_summary()


def _render_active(url: str):
    steps: dict = st.session_state.get("steps", {}).get(url, {})
    logs: list = st.session_state.get("logs", {}).get(url, [])
    started = st.session_state.get(f"_started_{url}", time_module.time())
    timer = _format_timer(started)

    active_step = None
    for s in PIPELINE_STEPS:
        if steps.get(s) == "active":
            active_step = s
            break
    if not active_step:
        for s in reversed(PIPELINE_STEPS):
            if steps.get(s) == "done":
                active_step = s
                break

    job_status = "active" if active_step else "queued"

    st.markdown(
        f'<div class="card card-{job_status}">'
        f'  <div class="card-top">'
        f'    <span class="card-id">{_vid_badge(url)}</span>'
        f'    <span class="timer">{timer}</span>'
        f'  </div>'
        f'  <div class="step-bar">',
        unsafe_allow_html=True,
    )

    cols = st.columns([1] * len(PIPELINE_STEPS))
    for i, step in enumerate(PIPELINE_STEPS):
        state = _state_cls(_step_state(steps, step))
        label = _step_label(step)
        icon = _STAGE_ICONS.get(step, "")
        with cols[i]:
            st.markdown(
                f'<div class="step-dot {state}">{icon}</div>'
                f'<div class="step-label {state}">{label}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

    stage = active_step or PIPELINE_STEPS[-1]
    sub = f"Step {PIPELINE_STEPS.index(stage) + 1} of {len(PIPELINE_STEPS)}"
    status = "Processing\u2026"
    icon = _STAGE_ICONS.get(stage, "")

    chunk_progress = _chunk_progress(logs)
    clip_progress = _stage_progress(logs)

    if stage == "transcript":
        seg_info = ""
        for line in logs:
            m = re.search(r"Got (\d+) segments", line)
            if m:
                seg_info = f'<div class="stage-metric"><span class="metric-icon">\U0001f4ac</span> {m.group(1)} captions found</div>'
        st.markdown(
            f'<div class="stage-card stage-transcript">'
            f'  <div class="stage-icon">{icon}</div>'
            f'  <div class="stage-body">'
            f'    <div class="stage-title">Transcript</div>'
            f'    <div class="stage-sub">{sub}</div>'
            f'    <div class="stage-status"><span class="live-dot"></span> Extracting captions from video\u2026</div>'
            f'    {seg_info}'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if stage == "analysis":
        clips_found = _count_total_clips_found(logs)
        provider = "Groq"
        provider_badge = f'<span class="provider-badge provider-groq">{provider}</span>'

        if chunk_progress:
            cur, total = chunk_progress
            pct = min(cur / max(total, 1), 1.0)
            bar = '<div class="prog"><div class="prog-fill" style="width:{:.0f}%"></div></div>'.format(pct * 100)
            label = f'<div class="stage-metric"><span class="metric-icon">\U0001f50d</span> Analyzing chunk {cur} of {total}</div>'
        else:
            bar = '<div class="prog"><div class="prog-fill prog-indeterminate"></div></div>'
            label = '<div class="stage-status"><span class="live-dot"></span> Processing transcript\u2026</div>'

        st.markdown(
            f'<div class="stage-card stage-analysis">'
            f'  <div class="stage-icon">{icon}</div>'
            f'  <div class="stage-body">'
            f'    <div class="stage-title">AI Analysis {provider_badge}</div>'
            f'    <div class="stage-sub">{sub}</div>'
            f'    {label}'
            f'    {bar}'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if stage == "download":
        st.markdown(
            f'<div class="stage-card stage-download">'
            f'  <div class="stage-icon">{icon}</div>'
            f'  <div class="stage-body">'
            f'    <div class="stage-title">Download Video</div>'
            f'    <div class="stage-sub">{sub}</div>'
            f'    <div class="stage-status"><span class="live-dot"></span> Downloading source video\u2026</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if stage == "cutting":
        if clip_progress:
            cur, total = clip_progress
            pct = min(cur / max(total, 1), 1.0)
            bar = '<div class="prog"><div class="prog-fill" style="width:{:.0f}%"></div></div>'.format(pct * 100)
            status = f'Cutting clip {cur} of {total}'
        else:
            bar = '<div class="prog"><div class="prog-fill prog-indeterminate"></div></div>'
            status = 'Starting cuts\u2026'

        st.markdown(
            f'<div class="stage-card stage-cutting">'
            f'  <div class="stage-icon">{icon}</div>'
            f'  <div class="stage-body">'
            f'    <div class="stage-title">Cutting Clips</div>'
            f'    <div class="stage-sub">{sub}</div>'
            f'    <div class="stage-status"><span class="live-dot"></span> {status}</div>'
            f'    {bar}'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if stage == "done":
        st.markdown(
            f'<div class="stage-card stage-done">'
            f'  <div class="stage-icon">{icon}</div>'
            f'  <div class="stage-body">'
            f'    <div class="stage-title">Complete</div>'
            f'    <div class="stage-sub">{sub}</div>'
            f'    <div class="stage-status" style="color:#3d9970;">\u2705 Ready</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if url in st.session_state.get("results", {}):
        result = st.session_state.results[url]
        if not result.success:
            st.markdown(
                f'<div class="stage-card stage-failed">'
                f'  <div class="stage-icon">\u274c</div>'
                f'  <div class="stage-body">'
                f'    <div class="stage-title">Failed</div>'
                f'    <div class="stage-sub">{result.error[:200]}</div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)


def _render_summary():
    results = st.session_state.get("results", {})
    steps = st.session_state.get("steps", {})
    logs = st.session_state.get("logs", {})
    done_count = sum(1 for r in results.values() if isinstance(r, JobResult) and r.success)
    fail_count = sum(1 for r in results.values() if isinstance(r, JobResult) and not r.success)

    if not results and not steps:
        return

    st.markdown(
        f'<div class="queue-header">Batch Summary \u2014 {done_count} done, {fail_count} failed</div>',
        unsafe_allow_html=True,
    )

    for url, result in results.items():
        if not isinstance(result, JobResult):
            continue
        url_steps = steps.get(url, {})
        url_logs = logs.get(url, [])
        state = "done" if result.success else "failed"

        vid_id = result.vid_id or extract_video_id(url) or "Manual"
        st.markdown(
            f'<div class="job-card {state}">'
            f'  <div class="job-top">'
            f'    <span class="job-id">{vid_id}</span>'
            f'    <span class="job-badge {state}">{"\u2705 Done" if result.success else "\u274c Failed"}</span>'
            f'  </div>'
            f'  <div class="step-trail">',
            unsafe_allow_html=True,
        )

        for step in PIPELINE_STEPS:
            s = _step_state(url_steps, step)
            label = _step_label(step)
            state_cls = _state_cls(s)
            dot = s == "done" and "\u2713" or s == "failed" and "\u2717" or "\u2022"
            st.markdown(
                f'<span class="step-label {state_cls}">'
                f'  <span class="step-dot {state_cls}">{dot}</span> {label}'
                f'</span>',
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)

        if not result.success and result.error:
            st.markdown(
                f'<div class="card-foot" style="color:#cc4444;">{result.error[:200]}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)
