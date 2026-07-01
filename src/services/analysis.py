from __future__ import annotations

import json
import re
import time
from typing import Callable, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from src.config import (
    LINES_PER_CHUNK,
    CHUNK_OVERLAP,
    MIN_DELAY_SEC,
    RETRY_DELAYS,
    GROQ_MODEL,
)
from src.types import ClipSuggestion

LogFn = Optional[Callable[[str], None]]


def _chunk_lines(lines: list[str]) -> list[str]:
    chunks: list[str] = []
    i = 0
    if not lines:
        return []
    while i < len(lines):
        chunk_slice = lines[i: i + LINES_PER_CHUNK]
        chunks.append("\n".join(chunk_slice))
        i += LINES_PER_CHUNK - CHUNK_OVERLAP
        if i >= len(lines):
            break
    return chunks


def _parse_clips_from_response(text: str) -> list[ClipSuggestion]:
    text = re.sub(r"```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\s*```", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []
    parsed: list[dict] = []
    try:
        parsed = json.loads(text[start: end + 1])
        if not isinstance(parsed, list):
            return []
    except Exception:
        try:
            objs = re.findall(r'\{[^{}]*\}', text[start:end + 1])
            parsed = [json.loads(o) for o in objs]
        except Exception:
            return []
    return [_dict_to_clip(c) for c in parsed]


def _dict_to_clip(d: dict) -> ClipSuggestion:
    return ClipSuggestion(
        start_time=float(d.get("start_time", d.get("start", 0))),
        end_time=float(d.get("end_time", d.get("end", 0))),
        title=str(d.get("title", "")),
        hook=str(d.get("hook", "")),
        reason=str(d.get("reason", "")),
    )


def _build_chain(api_key: str, custom_context: str = ""):
    user_guidance = f"\nUSER-SPECIFIED STRATEGY:\n{custom_context}" if custom_context else ""

    llm = ChatGroq(
        model=GROQ_MODEL,
        groq_api_key=api_key,
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a master viral video strategist specialized in Instagram Reels.
Your goal is to identify only the ABSOLUTE BEST moments from a transcript. Quality is more important than quantity.

INSTAGRAM ALGORITHM RULES:
1. THE HOOK: The first 2 seconds must be explosive.
2. DURATION: Clips MUST be between {{min_dur}} and {{max_dur}} seconds.
   - Aim for 20-50 seconds as the default.
   - Only exceed 50s if the content is world-class.
3. SELECTIVITY: Do not suggest mediocre clips. Only return segments with "viral" potential.
4. NARRATIVE: Each clip must be a complete micro-story.{user_guidance}

OUTPUT RULES:
- Return ONLY a valid JSON array of objects.
- Return [] if no top-tier moments exist in this chunk."""),

        ("human", """Find the absolute best viral moments from this transcript.
Target duration: {min_dur}–{max_dur} seconds.

Transcript:
{transcript}

Return ONLY this JSON structure:
[
  {{
    "start_time": <int>,
    "end_time": <int>,
    "title": "<punchy title>",
    "hook": "<exact opening phrase>",
    "reason": "<one sentence: why this is one of the BEST moments for Instagram>"
  }}
]""")
    ])
    return prompt | llm


def _parse_retry_after(err: str) -> float:
    m = re.search(r"retry in\s+([\d.]+)\s*s", err, re.IGNORECASE)
    if m:
        return float(m.group(1)) + 2.0
    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)", err)
    if m:
        return float(m.group(1)) + 2.0
    return 0


def _call_with_retry(chain, payload: dict, chunk_idx: int, total: int, log_fn: LogFn = None) -> str:
    last_err = None
    for attempt, wait in enumerate([0] + RETRY_DELAYS):
        if wait:
            if log_fn:
                log_fn(f"Rate limit hit on chunk {chunk_idx}/{total}. Waiting {wait}s...")
            time.sleep(wait)
        try:
            result = chain.invoke(payload)
            return result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            err_str = str(e)
            last_err = e
            if any(x in err_str.lower() for x in ["429", "quota", "resource exhausted", "limit"]):
                server_wait = _parse_retry_after(err_str)
                if server_wait:
                    wait = int(server_wait)
                    if log_fn:
                        log_fn(f"Server suggests retry in {server_wait:.0f}s — waiting...")
                    time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"API Quota Exhausted: {last_err}")


def _deduplicate_clips(clips: list[ClipSuggestion], min_dur: int, max_dur: int, log_fn: LogFn = None) -> list[ClipSuggestion]:
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    if not clips:
        return []

    clips.sort(key=lambda c: (float(c.start_time), -(float(c.end_time) - float(c.start_time))))

    unique: list[ClipSuggestion] = []
    for clip in clips:
        s = float(clip.start_time)
        e = float(clip.end_time)
        dur = e - s
        if dur < min_dur or dur > max_dur:
            log(f"  Rejected: '{clip.title[:40]}' — duration {dur:.0f}s outside [{min_dur}–{max_dur}s]")
            continue
        overlap = False
        for kept in unique:
            ks = float(kept.start_time)
            ke = float(kept.end_time)
            if max(s, ks) < min(e, ke):
                overlap = True
                log(f"  Rejected (overlaps): '{clip.title[:40]}' overlaps '{kept.title[:40]}'")
                break
        if not overlap:
            unique.append(clip)

    return unique


def _run_analysis(
    api_keys: list[str],
    transcript_lines: list[str],
    min_dur: int,
    max_dur: int,
    custom_context: str = "",
    log_fn: LogFn = None,
) -> list[ClipSuggestion]:
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    chunks = _chunk_lines(transcript_lines)
    total = len(chunks)

    all_clips: list[ClipSuggestion] = []

    for idx, chunk in enumerate(chunks, start=1):
        log(f"Analyzing chunk {idx}/{total}...")
        content = _call_with_key_rotation(
            api_keys, custom_context,
            {"min_dur": min_dur, "max_dur": max_dur, "transcript": chunk},
            idx, total, log_fn,
        )
        clips = _parse_clips_from_response(content)
        log(f"Chunk {idx}/{total} → {len(clips)} clips found")
        all_clips.extend(clips)

        if idx < total:
            time.sleep(2.0)

    return all_clips


def _call_with_key_rotation(
    api_keys: list[str],
    custom_context: str,
    payload: dict,
    chunk_idx: int,
    total: int,
    log_fn: LogFn = None,
) -> str:
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    last_err = None
    for ki, key in enumerate(api_keys):
        if ki > 0:
            log(f"Rate limited on key #{ki} — switching to key #{ki + 1}...")
        chain = _build_chain(key, custom_context)
        try:
            return _call_with_retry(chain, payload, chunk_idx, total, log_fn)
        except Exception as e:
            err_str = str(e)
            last_err = e
            is_rate_limit = any(x in err_str.lower() for x in ["429", "quota", "resource exhausted", "limit"])
            if is_rate_limit and ki < len(api_keys) - 1:
                continue
            raise

    raise RuntimeError(f"All {len(api_keys)} Groq API keys exhausted: {last_err}")


def analyze_transcript(
    groq_keys: list[str],
    transcript_text: str,
    min_dur: int,
    max_dur: int,
    custom_context: str = "",
    log_fn: LogFn = None,
    video_id: str = "",
) -> list[ClipSuggestion]:
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    if not groq_keys:
        raise RuntimeError("No Groq API keys available")

    lines = transcript_text.strip().split("\n")
    total_lines = len(lines)
    log(f"Transcript: {total_lines} lines, ~{len(transcript_text.split())} words")
    log(f"Using Groq (LLaMA 3.3 70B) — {len(groq_keys)} key(s) available")

    all_clips = _run_analysis(groq_keys, lines, min_dur, max_dur, custom_context, log_fn)

    if not all_clips:
        log("No clips found in any chunk")
        return []

    log(f"Total candidates before dedup: {len(all_clips)}")
    unique_clips = _deduplicate_clips(all_clips, min_dur, max_dur, log_fn)
    log(f"After dedup: {len(unique_clips)} clips")

    return unique_clips
