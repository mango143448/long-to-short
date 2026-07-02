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
        "extractor_retries": 5,
        "file_access_retries": 5,
        "fragment_retries": 5,
        "legacy_server_connect": True,
        "source_address": "0.0.0.0",
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
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
        return []
    except Exception as e:
        print(f"[transcript] yt-dlp unexpected error for {video_id}: {e}", file=sys.stderr)
        return []
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _fetch_youtubetranscript_direct(video_id: str, lang: str = "en") -> list[TranscriptSegment]:
    """Fetch transcript via youtubetranscript.com — different infrastructure, not blocked by YouTube's CDN."""
    import requests

    urls = [
        f"https://youtubetranscript.com/?v={video_id}&lang={lang}",
        f"https://youtubetranscript.com/?v={video_id}",
    ]

    for url in urls:
        try:
            resp = requests.get(
                url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            if resp.status_code != 200:
                continue
            ct = resp.headers.get("content-type", "")
            if "html" in ct:
                print(f"[transcript] youtubetranscript.com returned HTML for {video_id}", file=sys.stderr)
                continue
            if not resp.text.strip():
                continue
            data = resp.json()
            if isinstance(data, list) and data:
                segments = []
                for item in data:
                    text = item.get("text", "").strip()
                    start = float(item.get("start", 0))
                    dur = float(item.get("dur", item.get("duration", 0)))
                    if text:
                        segments.append(TranscriptSegment(text=text, start=start, duration=max(0.1, dur)))
                if segments:
                    return segments
        except Exception as e:
            print(f"[transcript] direct HTTP failed for {video_id}: {e}", file=sys.stderr)
            continue

    return []


def _try_pyopenssl():
    """Inject pyopenssl into urllib3 if available — uses system OpenSSL instead of Python's built-in SSL."""
    try:
        import urllib3.contrib.pyopenssl
        urllib3.contrib.pyopenssl.inject_into_urllib3()
        return True
    except Exception:
        return False


def fetch_transcript(video_id: str, cookies_path: Optional[str] = None) -> list[TranscriptSegment]:
    # Tier 1: youtube_transcript_api — most reliable, no download, works on server IPs
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        try:
            transcript = transcript_list.find_transcript(["en", "en-US", "en-GB", "en-CA", "en-AU"])
            fetched = transcript.fetch()
            result = [TranscriptSegment(text=item["text"], start=item["start"], duration=item["duration"]) for item in fetched]
            if result:
                print(f"[transcript] Got {len(result)} segments via youtube-transcript-api (manual)", file=sys.stderr)
                return result
        except Exception:
            pass

        try:
            transcript = transcript_list.find_generated_transcript(["en", "en-US", "en-GB", "en-CA", "en-AU"])
            fetched = transcript.fetch()
            result = [TranscriptSegment(text=item["text"], start=item["start"], duration=item["duration"]) for item in fetched]
            if result:
                print(f"[transcript] Got {len(result)} segments via youtube-transcript-api (auto)", file=sys.stderr)
                return result
        except Exception:
            pass

        try:
            for t in transcript_list._manually_created_transcripts.values():
                fetched = t.fetch()
                result = [TranscriptSegment(text=item["text"], start=item["start"], duration=item["duration"]) for item in fetched]
                if result:
                    print(f"[transcript] Got {len(result)} segments via youtube-transcript-api (manual {t.language_code})", file=sys.stderr)
                    return result
        except Exception:
            pass

        try:
            for t in transcript_list._generated_transcripts.values():
                fetched = t.fetch()
                result = [TranscriptSegment(text=item["text"], start=item["start"], duration=item["duration"]) for item in fetched]
                if result:
                    print(f"[transcript] Got {len(result)} segments via youtube-transcript-api (auto {t.language_code})", file=sys.stderr)
                    return result
        except Exception:
            pass

    except Exception as e:
        print(f"[transcript] youtube-transcript-api failed for {video_id}: {e}", file=sys.stderr)

    # Tier 2: youtubetranscript.com — different infrastructure
    result = _fetch_youtubetranscript_direct(video_id)
    if result:
        print(f"[transcript] Got {len(result)} segments via youtubetranscript.com", file=sys.stderr)
        return result

    # Tier 3: yt-dlp — slowest, most likely to get 403'd on server
    print(f"[transcript] Trying yt-dlp for {video_id}...", file=sys.stderr)
    result = fetch_transcript_yt_dlp(video_id, cookies_path)
    if result:
        print(f"[transcript] Got {len(result)} segments via yt-dlp", file=sys.stderr)
        return result

    raise ValueError(
        "No captions found. The video may not have captions enabled, "
        "or all fetch methods were blocked. Try uploading a cookies.txt file in Advanced settings."
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
