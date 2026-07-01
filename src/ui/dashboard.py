import re
import time as time_module
from typing import Optional

import streamlit as st

from src.config import PIPELINE_STEPS, STEP_LABELS
from src.services.transcript import extract_video_id
from src.types import JobResult, StepState

_CLIP_ICONS = {"queued": "⬜", "active": "⟳", "done": "✅", "failed": "❌"}


def _parse_progress(logs: list[str]) -> tuple[Optional[tuple[int, int]], Optional[tuple[int, int]]]:
    chunk_progress: Optional[tuple[int, int]] = None
    clip_progress: Optional[tuple[int, int]] = None
    for line in logs:
        m = re.search(r"chunk\s*(\d+)\s*/\s*(\d+)", line, re.IGNORECASE)
        if m:
            chunk_progress = (int(m.group(1)), int(m.group(2)))
        m = re.search(r"[Cc]lip\s*(\d+)\s*/\s*(\d+)", line)
        if m:
            clip_progress = (int(m.group(1)), int(m.group(2)))
    return chunk_progress, clip_progress


def _get_clip_statuses(logs: list[str], total: int) -> list[str]:
    statuses: list[str] = ["queued"] * total
    for line in logs:
        m = re.search(r"[Cc]lip\s*(\d+)\s*/\s*(\d+)\s*done", line)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < total:
                statuses[idx] = "done"
        m = re.search(r"[Cc]lip\s*(\d+)\s*/\s*(\d+)\s*failed", line)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < total:
                statuses[idx] = "failed"
    for line in logs:
        m = re.search(r"[Cc]lip\s*(\d+)\s*/\s*(\d+)", line)
        if m:
            last = int(m.group(1))
            idx = last - 1
            if 0 <= idx < total and statuses[idx] == "queued":
                statuses[idx] = "active"
    return statuses


def _count_total_clips_found(logs: list[str]) -> int:
    total = 0
    for line in logs:
        m = re.search(r"Chunk\s+\d+/\d+\s*[→➡]\s*(\d+)\s+clips?\s+found", line, re.IGNORECASE)
        if m:
            total += int(m.group(1))
    return total


def _parse_download_pct(logs: list[str]) -> Optional[float]:
    for line in reversed(logs):
        m = re.search(r"(\d+\.?\d*)%", line)
        if m:
            return float(m.group(1))
    return None


def _parse_download_speed(logs: list[str]) -> str:
    for line in reversed(logs):
        m = re.search(r"at\s+([\d.]+)\s*(\w+/s)", line)
        if m:
            return f"{m.group(1)} {m.group(2)}"
    return ""


def _render_step_bar(steps: dict[str, StepState]):
    html = '<div class="step-bar">'
    for i, name in enumerate(PIPELINE_STEPS):
        s = steps.get(name, StepState.queued)
        val = s.value if hasattr(s, "value") else str(s)
        icon = {"done": "✓", "active": "●", "failed": "✗", "queued": "○"}.get(val, "○")
        cls = f"step-dot step-{val}"
        html += f'<span class="{cls}">{icon}</span><span class="step-label step-label-{val}">{STEP_LABELS[name]}</span>'
        if i < len(PIPELINE_STEPS) - 1:
            html += f'<span class="step-connector step-connector-{val}"></span>'
    html += "</div>"
    return html


def _render_stage_card(stage: str, logs: list[str], result: Optional[JobResult], clip_progress: Optional[tuple[int, int]], chunk_progress: Optional[tuple[int, int]]):
    if stage == "done":
        if result and result.success:
            return (
                '<div class="stage-card stage-done">'
                '  <div class="stage-icon">🎉</div>'
                '  <div class="stage-body">'
                f'    <div class="stage-title">Complete — {len(result.clips)} clips ready</div>'
                f'    <div class="stage-sub">{len(result.generated)} clips downloaded, {len(result.clips)} total found</div>'
                '  </div>'
                '</div>'
            )
        else:
            err = (result.error[:200] if result and result.error else "Unknown error")
            return (
                '<div class="stage-card stage-failed">'
                '  <div class="stage-icon">❌</div>'
                '  <div class="stage-body">'
                f'    <div class="stage-title">Pipeline Failed</div>'
                f'    <div class="stage-sub">{err}</div>'
                '  </div>'
                '</div>'
            )

    if stage == "transcript":
        seg_count = 0
        for line in logs:
            m = re.search(r"Got (\d+) segments", line)
            if m:
                seg_count = int(m.group(1))
        seg_info = f'<div class="stage-metric"><span class="metric-icon">📊</span> {seg_count} segments</div>' if seg_count else ''
        return (
            '<div class="stage-card stage-transcript">'
            '  <div class="stage-icon">📝</div>'
            '  <div class="stage-body">'
            '    <div class="stage-title">Fetching transcript</div>'
            f'    <div class="stage-status"><span class="live-dot"></span> Extracting captions from video…</div>'
            f'    {seg_info}'
            '  </div>'
            '</div>'
        )

    if stage == "analysis":
        clips_found = _count_total_clips_found(logs)
        provider = "Groq"
        provider_badge = f'<span class="provider-badge provider-groq">{provider}</span>'

        if chunk_progress:
            cur, total = chunk_progress
            pct = min(cur / max(total, 1), 1.0)
            bar = '<div class="prog"><div class="prog-fill" style="width:{:.0f}%"></div></div>'.format(pct * 100)
            label = f'<div class="stage-metric"><span class="metric-icon">🔍</span> Analyzing chunk {cur} of {total}</div>'
        else:
            bar = '<div class="prog"><div class="prog-fill prog-indeterminate"></div></div>'
            label = '<div class="stage-status"><span class="live-dot"></span> Processing transcript…</div>'

        clips_info = f'<div class="stage-metric"><span class="metric-icon">🎬</span> {clips_found} clips found</div>' if clips_found else ''

        return (
            '<div class="stage-card stage-analysis">'
            '  <div class="stage-icon">🧠</div>'
            '  <div class="stage-body">'
            f'    <div class="stage-title">AI Analysis {provider_badge}</div>'
            f'    {label}'
            f'    {clips_info}'
            f'    {bar}'
            '  </div>'
            '</div>'
        )

    if stage == "download":
        pct = _parse_download_pct(logs)
        speed = _parse_download_speed(logs)
        pct_str = f"{pct:.0f}%" if pct is not None else ""
        speed_str = f" · {speed}" if speed else ""

        if pct is not None:
            bar = '<div class="prog"><div class="prog-fill" style="width:{:.0f}%"></div></div>'.format(pct)
        else:
            bar = '<div class="prog"><div class="prog-fill prog-indeterminate"></div></div>'

        return (
            '<div class="stage-card stage-download">'
            '  <div class="stage-icon">⬇️</div>'
            '  <div class="stage-body">'
            f'    <div class="stage-title">Downloading video</div>'
            f'    <div class="stage-status"><span class="live-dot"></span> {pct_str}{speed_str}</div>'
            f'    {bar}'
            '  </div>'
            '</div>'
        )

    if stage == "cutting":
        n = clip_progress[1] if clip_progress else 0
        statuses = _get_clip_statuses(logs, n) if n > 0 else []
        clip_html = ""
        for i, clip in enumerate(statuses):
            icon = _CLIP_ICONS.get(clip, "⬜")
            clip_html += f'<span class="clip-queue-item clip-queue-{clip}" title="Clip {i+1}: {clip}">{icon}</span>'

        if clip_progress:
            cur, total = clip_progress
            pct = min(cur / max(total, 1), 1.0)
            bar = '<div class="prog"><div class="prog-fill" style="width:{:.0f}%"></div></div>'.format(pct * 100)
            label = f'<div class="stage-metric"><span class="metric-icon">✂️</span> Clip {cur} of {total}</div>'
        else:
            bar = '<div class="prog"><div class="prog-fill prog-indeterminate"></div></div>'
            label = '<div class="stage-status"><span class="live-dot"></span> Preparing clips…</div>'

        return (
            '<div class="stage-card stage-cutting">'
            '  <div class="stage-icon">✂️</div>'
            '  <div class="stage-body">'
            '    <div class="stage-title">Cutting clips</div>'
            f'    {label}'
            f'    <div class="clip-queue">{clip_html}</div>'
            f'    {bar}'
            '  </div>'
            '</div>'
        )

    return ""


def render_dashboard(active_url: Optional[str] = None):
    queue = st.session_state.get("batch_queue", [])
    if not queue:
        return

    total = len(queue)
    steps_dict: dict[str, dict[str, StepState]] = st.session_state.get("steps", {})
    results_dict: dict[str, JobResult] = st.session_state.get("results", {})
    logs_dict: dict[str, list[str]] = st.session_state.get("logs", {})

    done_count = sum(
        1 for u in queue
        if steps_dict.get(u, {}).get("done") == StepState.done
    )

    st.markdown(
        f'<div class="queue-header">Queue: {done_count}/{total} complete</div>',
        unsafe_allow_html=True,
    )

    for url in queue:
        vid_id = extract_video_id(url) if url != "__manual__" else "Manual"
        steps = steps_dict.get(url, {})
        logs = logs_dict.get(url, [])
        result = results_dict.get(url)
        is_active = url == active_url

        if result:
            card_state = "done" if result.success else "failed"
        elif is_active:
            card_state = "active"
        else:
            card_state = "queued"

        current_step = "queued"
        for sn in PIPELINE_STEPS:
            ss = steps.get(sn, StepState.queued)
            sv = ss.value if hasattr(ss, "value") else str(ss)
            if sv == "active":
                current_step = sn
                break

        chunk_progress, clip_progress = _parse_progress(logs)

        timer_html = ""
        if is_active:
            started = st.session_state.get(f"_started_{url}")
            if started:
                elapsed = int(time_module.time() - started)
                timer_html = f'<div class="timer">⏱ {elapsed // 60:02d}:{elapsed % 60:02d}</div>'

        card = f'<div class="card card-{card_state}">'
        card += f'<div class="card-top"><span class="card-id">{vid_id}</span><span class="card-badge card-badge-{card_state}">{card_state.title()}</span></div>'
        card += _render_step_bar(steps)

        if is_active:
            card += _render_stage_card(current_step, logs, result, clip_progress, chunk_progress)

        card += timer_html

        if result:
            summary = f'{len(result.generated)} clips · {len(result.clips)} found'
            if result.error:
                summary += f' · Error: {result.error[:80]}'
            card += f'<div class="card-foot">{summary}</div>'
            if logs:
                card += (
                    '<details class="log-details" style="margin-top:6px">'
                    f'<summary class="log-summary">📋 Processing Log ({len(logs)} entries)</summary>'
                )
                log_entries = ""
                for line in logs[-30:]:
                    css = "log-line"
                    if "error" in line.lower() or "failed" in line.lower() or "✗" in line:
                        css += " log-err"
                    elif "complete" in line.lower() or "✓" in line or "done" in line.lower():
                        css += " log-ok"
                    log_entries += f'<div class="{css}">{line}</div>'
                card += f'<div class="log-box">{log_entries}</div>'
                card += '</details>'

        card += "</div>"
        st.markdown(card, unsafe_allow_html=True)
