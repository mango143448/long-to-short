from __future__ import annotations

import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Callable, Optional

from src.config import PIPELINE_STEPS
from src.services.transcript import (
    extract_video_id,
    fetch_transcript,
    parse_pasted_transcript,
    build_transcript_text,
    get_clip_transcript_text,
    mmss,
)
from src.services.analysis import analyze_transcript
from src.services.video import (
    check_ffmpeg,
    download_video,
    find_downloaded_file,
    get_person_focus_x,
    make_short,
)
from src.types import (
    AnalysisConfig,
    JobResult,
)

StepCallback = Callable[[str, str], None]
LogCallback = Callable[[str], None]


class PipelineError(Exception):
    pass


def run_pipeline(
    url: str,
    groq_keys: list[str],
    analysis_cfg: AnalysisConfig,
    pasted_transcript: str = "",
    manual_video_url: str = "",
    cookie_path: Optional[str] = None,
    auto_adjust: bool = True,
    on_step: Optional[StepCallback] = None,
    on_log: Optional[LogCallback] = None,
) -> JobResult:
    def log(msg: str):
        if on_log:
            on_log(msg)

    def step(name: str, state: str):
        if on_step:
            on_step(name, state)

    vid_id = ""
    wdir = tempfile.mkdtemp(prefix="shorts_")
    _current_step = "transcript"
    debug_fd = None

    try:
        if url != "__manual__":
            vid_id = extract_video_id(url)
            if not vid_id:
                raise PipelineError(f"Invalid YouTube URL: {url}")

        debug_path = os.path.join(tempfile.gettempdir(), f"pipeline_debug_{vid_id or 'manual'}.log")
        debug_fd = open(debug_path, "w", encoding="utf-8")
        def debug(msg: str):
            if debug_fd:
                debug_fd.write(msg + "\n")
                debug_fd.flush()

        _current_step = "transcript"
        step("transcript", "active")
        log("Fetching transcript\u2026")

        if url != "__manual__":
            transcript = fetch_transcript(vid_id, cookies_path=cookie_path)
        else:
            vid_id = "Manual"
            transcript = parse_pasted_transcript(pasted_transcript)

        if not transcript:
            raise PipelineError("Could not retrieve any English captions")

        seg_count = len(transcript)
        duration_est = transcript[-1].start / 60 if transcript else 0
        log(f"Got {seg_count} segments (~{duration_est:.0f} min of content)")
        step("transcript", "done")

        _current_step = "analysis"
        step("analysis", "active")
        log("Building transcript text for analysis…")
        txt = build_transcript_text(transcript)
        word_count = len(txt.split())
        log(f"Transcript compressed to {word_count:,} words")

        clips = analyze_transcript(
            groq_keys=groq_keys,
            transcript_text=txt,
            min_dur=analysis_cfg.min_dur,
            max_dur=analysis_cfg.max_dur,
            custom_context=analysis_cfg.custom_context,
            log_fn=log,
            video_id=vid_id,
        )

        if not clips:
            raise PipelineError(
                f"No clips found between {analysis_cfg.min_dur}–{analysis_cfg.max_dur}s. "
                "Try widening the duration range."
            )

        log(f"Analysis complete — {len(clips)} clips selected")
        step("analysis", "done")

        generated: dict[int, bytes] = {}
        clip_transcripts: dict[int, str] = {}
        src_video: Optional[str] = None

        video_url = url if url != "__manual__" else manual_video_url

        if video_url:
            _current_step = "download"
            step("download", "active")
            log("Starting video download…")
            expected = os.path.join(wdir, "source.mp4")

            if os.path.exists(video_url):
                src_video = video_url
                log("Using local file, no download needed")
            else:
                download_video(video_url, expected, log_fn=log, cookies_path=cookie_path)
                src_video = find_downloaded_file(wdir, expected)
                size_mb = os.path.getsize(src_video) / (1024 * 1024)
                log(f"Download complete — {size_mb:.0f} MB saved")

            step("download", "done")

            _current_step = "cutting"
            step("cutting", "active")

            if not check_ffmpeg():
                raise PipelineError(
                    "FFmpeg not found. Install FFmpeg and ensure it is in your PATH. "
                    "Download from https://ffmpeg.org/download.html"
                )

            n = len(clips)
            debug(f"=== CUTTING START === n={n}")
            log(f"Cutting {n} clips\u2026")

            def cut_one(i: int, clip):
                s = clip.start_time
                e = clip.end_time
                focus_x = None
                if auto_adjust:
                    try:
                        focus_x = get_person_focus_x(src_video, s, e)
                    except Exception:
                        focus_x = None
                out = os.path.join(wdir, f"short_{i + 1}.mp4")
                make_short(src_video, out, s, e, focus_x=focus_x)
                clip_text = get_clip_transcript_text(transcript, s, e)
                with open(out, "rb") as f:
                    clip_bytes = f.read()
                return clip_bytes, clip_text

            with ThreadPoolExecutor(max_workers=1) as pool:
                for i, clip in enumerate(clips):
                    s = clip.start_time
                    e = clip.end_time
                    debug(f"Iteration {i+1}/{n}: start={s}, end={e}, title={clip.title[:60]}")
                    log(f"Clip {i + 1}/{n}: {mmss(s)} \u2192 {mmss(e)} \u2014 {clip.title[:40]}")

                    fut = pool.submit(cut_one, i, clip)
                    try:
                        generated[i], clip_transcripts[i] = fut.result(timeout=300)
                        log(f"Clip {i + 1}/{n} done")
                    except TimeoutError:
                        log(f"Clip {i + 1}/{n} timed out (5 min)")
                    except Exception as clip_err:
                        log(f"Clip {i + 1}/{n} failed: {clip_err}")

            succeeded = len(generated)
            failed = n - succeeded
            log(f"Cutting done — {succeeded}/{n} clips succeeded" + (f", {failed} failed" if failed else ""))

            step("cutting", "done")

            if clips and not generated:
                log("WARNING: All clips failed during cutting — check FFmpeg installation")
        else:
            log("No video URL provided — skipping download and cutting")
            step("download", "done")
            step("cutting", "done")

        has_clips_bool = bool(generated) if video_url else True
        step("done", "done" if has_clips_bool else "failed")
        log(f"Job complete — {len(generated)} clips ready" if has_clips_bool else "Job failed — no clips were generated")

        return JobResult(
            url=url,
            vid_id=vid_id,
            success=has_clips_bool,
            clips=clips,
            generated=generated,
            clip_transcripts=clip_transcripts,
            transcript=transcript,
            error="" if has_clips_bool else "No clips could be generated. Ensure FFmpeg is installed and working.",
        )

    except Exception as e:
        log(f"ERROR: {e}")
        step(_current_step, "failed")
        return JobResult(
            url=url,
            vid_id=vid_id,
            success=False,
            error=str(e),
        )
    finally:
        try:
            if debug_fd:
                debug_fd.close()
        except Exception:
            pass
        shutil.rmtree(wdir, ignore_errors=True)

