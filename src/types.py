from __future__ import annotations

import io
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    youtube = "youtube"
    manual = "manual"


class JobStep(str, Enum):
    transcript = "transcript"
    analysis = "analysis"
    download = "download"
    cutting = "cutting"
    done = "done"


class StepState(str, Enum):
    queued = "queued"
    active = "active"
    done = "done"
    failed = "failed"


class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float = 0.0


class ClipSuggestion(BaseModel):
    start_time: float
    end_time: float
    title: str = ""
    hook: str = ""
    reason: str = ""


class AnalysisConfig(BaseModel):
    min_dur: int = Field(default=20, ge=10, le=600)
    max_dur: int = Field(default=120, ge=10, le=600)
    custom_context: str = ""
    auto_adjust: bool = True


class AppConfig(BaseModel):
    groq_keys: list[str] = Field(default_factory=list)
    cookie_path: Optional[str] = None
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)


class JobResult(BaseModel):
    url: str
    vid_id: str = ""
    success: bool = False
    clips: list[ClipSuggestion] = Field(default_factory=list)
    generated: dict[int, bytes] = Field(default_factory=dict)
    clip_transcripts: dict[int, str] = Field(default_factory=dict)
    transcript: list[TranscriptSegment] = Field(default_factory=list)
    error: str = ""


class BatchState(BaseModel):
    queue: list[str] = Field(default_factory=list)
    index: int = -1
    results: dict[str, JobResult] = Field(default_factory=dict)
    steps: dict[str, dict[str, StepState]] = Field(default_factory=dict)
    logs: dict[str, list[str]] = Field(default_factory=dict)
    mode: bool = False
    input_mode: SourceType = SourceType.youtube
    cookie_path: Optional[str] = None
