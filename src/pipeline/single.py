from __future__ import annotations

from typing import Optional

from src.pipeline.base import run_pipeline
from src.state.manager import live_append_log, live_set_result, live_set_step
from src.types import AnalysisConfig, JobResult


def run_single(
    url: str,
    groq_keys: list[str],
    analysis_cfg: AnalysisConfig,
    pasted_transcript: str = "",
    manual_video_url: str = "",
    cookie_path: Optional[str] = None,
    auto_adjust: bool = True,
) -> JobResult:
    def on_step(name: str, state: str):
        live_set_step(url, name, state)

    def on_log(msg: str):
        live_append_log(url, msg)

    try:
        result = run_pipeline(
            url=url,
            groq_keys=groq_keys,
            analysis_cfg=analysis_cfg,
            pasted_transcript=pasted_transcript,
            manual_video_url=manual_video_url,
            cookie_path=cookie_path,
            auto_adjust=auto_adjust,
            on_step=on_step,
            on_log=on_log,
        )
        live_set_result(url, result)
        return result
    except Exception as exc:
        live_append_log(url, f"Pipeline crashed: {exc}")
        result = JobResult(url=url, success=False, error=str(exc))
        live_set_result(url, result)
        return result
