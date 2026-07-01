from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from src.types import TranscriptSegment

_LANG_PRIORITY = ["en", "en-US", "en-GB", "en-CA", "en-AU", "en-IN"]


def extract_video_id(url: str) -> Optional[str]:
    for pat in [
        r'(?:v=|/v/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})',
        r'^([A-Za-z0-9_-]{11})$',
    ]:
        m = re.search(pat, url.strip())
        if m:
            return m.group(1)
    return None


def mmss(s: float) -> str:
    m = int(s) // 60
    sec = int(s) % 60
    return f"{m:02d}:{sec:02d}"


def _ts_to_seconds(ts: str) -> float:
    parts = ts.replace(",", ".").split(":")
    try:
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except ValueError:
        return 0.0


def hhmmss_to_seconds(ts: str) -> float:
    return _ts_to_seconds(ts)


def parse_pasted_transcript(raw: str) -> list[TranscriptSegment]:
    lines = raw.strip().splitlines()
    segments: list[TranscriptSegment] = []
    ts_pattern = r"\[?(\d{1,2}:\d{2}(?::\d{2})?(\.\d+)?)\]?"
    bare_ts_re = re.compile(f"^{ts_pattern}\\s*$")
    inline_ts_re = re.compile(f"^{ts_pattern}\\s+(.+)$")

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue

        m_bare = bare_ts_re.match(line)
        if m_bare:
            start = hhmmss_to_seconds(m_bare.group(1))
            text_parts = []
            i += 1
            while i < len(lines) and not bare_ts_re.match(lines[i].strip()) and not inline_ts_re.match(lines[i].strip()):
                t = lines[i].strip()
                if t and not t.startswith("#"):
                    text_parts.append(t)
                i += 1
            text = " ".join(text_parts)
            if text:
                segments.append(TranscriptSegment(text=text, start=start, duration=0))
            continue

        m_inline = inline_ts_re.match(line)
        if m_inline:
            start = hhmmss_to_seconds(m_inline.group(1))
            text = m_inline.group(3).strip()
            if text:
                segments.append(TranscriptSegment(text=text, start=start, duration=0))
            i += 1
            continue

        i += 1

    if not segments:
        raise ValueError(
            "Could not parse any transcript segments.\n"
            "Supported formats:\n00:00:00 Text\n[00:00:00] Text\n00:00:00\nText"
        )

    segments.sort(key=lambda x: x.start)
    for idx in range(len(segments) - 1):
        segments[idx].duration = max(0.1, segments[idx + 1].start - segments[idx].start)
    if segments:
        segments[-1].duration = 30
    return segments


def _parse_vtt_content(vtt_text: str) -> list[TranscriptSegment]:
    import webvtt

    result: list[TranscriptSegment] = []
    try:
        for caption in webvtt.from_string(vtt_text):
            start = _ts_to_seconds(caption.start)
            end = _ts_to_seconds(caption.end)
            text = caption.text.replace("\n", " ").strip()
            if text:
                result.append(TranscriptSegment(
                    text=text,
                    start=start,
                    duration=max(0.1, end - start),
                ))
    except Exception:
        pass
    return result


def fetch_transcript_yt_dlp(video_id: str, cookies_path: Optional[str] = None) -> list[TranscriptSegment]:
    import yt_dlp

    tmp_dir = tempfile.mkdtemp(prefix="subs_")
    out_template = os.path.join(tmp_dir, "%(id)s.%(ext)s")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "vtt",
        "subtitleslangs": ["en"],
        "skip_download": True,
        "outtmpl": out_template,
        "socket_timeout": 30,
        "extract_flat": False,
        "extractor_retries": 3,
        "file_access_retries": 3,
    }
    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path

    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        vtt_files = sorted(Path(tmp_dir).glob("*.vtt"))
        if vtt_files:
            vtt_content = vtt_files[0].read_text(encoding="utf-8")
            segments = _parse_vtt_content(vtt_content)
            if segments:
                return segments

        return []

    except yt_dlp.utils.DownloadError as e:
        err_str = str(e)
        print(f"[transcript] yt-dlp error for {video_id}: {err_str[:200]}", file=sys.stderr)

        if "SSL" in err_str or "UNEXPECTED_EOF" in err_str:
            return _fetch_transcript_yt_dlp_fallback(video_id, cookies_path)

        return []
    except Exception as e:
        print(f"[transcript] yt-dlp unexpected error for {video_id}: {e}", file=sys.stderr)
        return []
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _fetch_transcript_yt_dlp_fallback(video_id: str, cookies_path: Optional[str] = None) -> list[TranscriptSegment]:
    """Fallback that patches SSL context for HF Spaces environments."""
    import ssl

    import yt_dlp

    original_context = ssl._create_default_https_context
    ssl._create_default_https_context = ssl._create_unverified_context

    tmp_dir = tempfile.mkdtemp(prefix="subs_")
    out_template = os.path.join(tmp_dir, "%(id)s.%(ext)s")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "vtt",
        "subtitleslangs": ["en"],
        "skip_download": True,
        "outtmpl": out_template,
        "socket_timeout": 30,
        "extract_flat": False,
        "extractor_retries": 3,
        "file_access_retries": 3,
    }
    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path

    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        vtt_files = sorted(Path(tmp_dir).glob("*.vtt"))
        if vtt_files:
            vtt_content = vtt_files[0].read_text(encoding="utf-8")
            segments = _parse_vtt_content(vtt_content)
            if segments:
                return segments
        return []
    except Exception as e:
        print(f"[transcript] fallback also failed for {video_id}: {e}", file=sys.stderr)
        return []
    finally:
        ssl._create_default_https_context = original_context
        shutil.rmtree(tmp_dir, ignore_errors=True)


def fetch_transcript(video_id: str, cookies_path: Optional[str] = None) -> list[TranscriptSegment]:
    result = fetch_transcript_yt_dlp(video_id, cookies_path)
    if result:
        return result

    from youtube_transcript_api import YouTubeTranscriptApi
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(["en", "en-US", "en-GB", "en-CA", "en-AU"])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(["en", "en-US", "en-GB", "en-CA", "en-AU"])
            except Exception:
                raise ValueError("No English captions found via standard API")
        fetched = transcript.fetch()
        return [TranscriptSegment(text=item["text"], start=item["start"], duration=item["duration"]) for item in fetched]
    except Exception:
        raise ValueError(
            "No English captions found. "
            "If the video has captions, try uploading a cookies.txt file in Advanced settings."
        )


def build_transcript_text(transcript: list[TranscriptSegment]) -> str:
    if not transcript:
        return ""
    compressed: list[str] = []
    current_seg = {"start": transcript[0].start, "text": []}
    for i, item in enumerate(transcript):
        current_seg["text"].append(item.text)
        if i < len(transcript) - 1:
            next_start = transcript[i + 1].start
            if (next_start - item.start < 3.0) and len(" ".join(current_seg["text"]).split()) < 20:
                continue
        time_str = mmss(current_seg["start"])
        combined_text = " ".join(current_seg["text"])
        compressed.append(f"[{time_str}] {combined_text}")
        if i < len(transcript) - 1:
            current_seg = {"start": transcript[i + 1].start, "text": []}
    return "\n".join(compressed)


def get_clip_transcript_text(transcript: list[TranscriptSegment], start: float, end: float) -> str:
    return " ".join(
        item.text for item in transcript
        if start <= item.start <= end
    ).strip()
