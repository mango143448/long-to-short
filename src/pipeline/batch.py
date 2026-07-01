from __future__ import annotations

from typing import Optional

from src.pipeline.single import run_single
from src.types import AnalysisConfig, JobResult


def run_batch(
    urls: list[str],
    groq_keys: list[str],
    analysis_cfg: AnalysisConfig,
    pasted_transcript: str = "",
    manual_video_url: str = "",
    cookie_path: Optional[str] = None,
    auto_adjust: bool = True,
) -> dict[str, JobResult]:
    results: dict[str, JobResult] = {}

    for url in urls:
        result = run_single(
            url=url,
            groq_keys=groq_keys,
            analysis_cfg=analysis_cfg,
            pasted_transcript=pasted_transcript,
            manual_video_url=manual_video_url,
            cookie_path=cookie_path,
            auto_adjust=auto_adjust,
        )
        results[url] = result

    return results
