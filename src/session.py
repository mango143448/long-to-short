import threading
from typing import Optional

import streamlit as st

from src.settings import PROJECT_ROOT
from src.types import JobResult, JobStep, StepState

_live_lock = threading.Lock()
_live_logs: dict[str, list[str]] = {}
_live_steps: dict[str, dict[str, str]] = {}
_live_results: dict[str, JobResult] = {}
_live_done: set[str] = set()


def live_append_log(url: str, msg: str):
    import time
    ts = time.strftime("%H:%M:%S")
    with _live_lock:
        lst = _live_logs.setdefault(url, [])
        lst.append(f"[{ts}] {msg}")
        _live_logs[url] = lst[-200:]


def live_set_step(url: str, step: str, state: str):
    with _live_lock:
        _live_steps.setdefault(url, {})[step] = state


def live_clear():
    with _live_lock:
        _live_logs.clear()
        _live_steps.clear()
        _live_results.clear()
        _live_done.clear()


def live_set_result(url: str, result: JobResult):
    with _live_lock:
        _live_results[url] = result
        _live_done.add(url)


def sync_live_to_session(url: str):
    with _live_lock:
        if url in _live_logs:
            st.session_state.logs[url] = _live_logs[url].copy()
        if url in _live_steps:
            steps = st.session_state.steps.get(url, {})
            for step, state in _live_steps[url].items():
                steps[step] = StepState(state)
            st.session_state.steps[url] = steps
        if url in _live_done and url in _live_results:
            st.session_state.results[url] = _live_results[url]
            _live_done.discard(url)

COOKIE_PATH: Optional[str] = (
    str(PROJECT_ROOT / "cookies.txt") if (PROJECT_ROOT / "cookies.txt").exists() else None
)


def init_defaults():
    defaults = dict(
        batch_queue=[],
        batch_index=-1,
        results={},
        steps={},
        logs={},
        batch_mode=False,
        input_mode="youtube",
        cookie_path=COOKIE_PATH,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def init_steps(url: str):
    if "steps" not in st.session_state:
        st.session_state.steps = {}
    st.session_state.steps[url] = {s: StepState.queued for s in [e.value for e in JobStep]}
    if "logs" not in st.session_state:
        st.session_state.logs = {}
    st.session_state.logs[url] = []


def set_step(url: str, step: str, state: StepState):
    steps = st.session_state.steps.get(url)
    if steps and step in steps:
        steps[step] = state


def append_log(url: str, msg: str):
    import time
    if "logs" not in st.session_state:
        st.session_state.logs = {}
    logs = st.session_state.logs
    if url not in logs:
        logs[url] = []
    ts = time.strftime("%H:%M:%S")
    logs[url].append(f"[{ts}] {msg}")
    logs[url] = logs[url][-60:]


def reset():
    for k in ["batch_queue", "batch_index", "results", "steps", "logs", "batch_mode", "input_mode", "cookie_path"]:
        if k in st.session_state:
            del st.session_state[k]
