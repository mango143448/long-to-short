from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

LogFn = Optional[Callable[[str], None]]


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def get_free_space_gb() -> float:
    total, used, free = shutil.disk_usage(".")
    return free / (1024 ** 3)


def probe_video(path: str) -> tuple[int, int]:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", path],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(r.stdout)
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                return int(s["width"]), int(s["height"])
    except Exception:
        pass
    return 1920, 1080


def download_video(url: str, out_path: str, log_fn: LogFn = None, cookies_path: Optional[str] = None) -> None:
    import yt_dlp

    def log(msg: str):
        if log_fn:
            log_fn(msg)

    if os.path.exists(out_path):
        log("Source video already cached, skipping download")
        return

    if get_free_space_gb() < 2.0:
        log("Low disk space — download may fail")

    class Hook:
        def __call__(self, d):
            if d["status"] == "downloading":
                pct = d.get("_percent_str", "?").strip()
                speed = d.get("_speed_str", "?").strip()
                eta = d.get("_eta_str", "?").strip()
                log(f"Downloading… {pct} at {speed} — ETA {eta}")
            elif d["status"] == "finished":
                log("Download complete, merging streams…")

    opts = {
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best",
        "outtmpl": out_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [Hook()],
        "socket_timeout": 30,
        "retries": 3,
    }
    if cookies_path:
        opts["cookiefile"] = cookies_path
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


def find_downloaded_file(work_dir: str, expected: str) -> str:
    if os.path.exists(expected):
        return expected
    base = os.path.splitext(expected)[0]
    for ext in [".mp4", ".mkv", ".webm", ".m4v"]:
        if os.path.exists(base + ext):
            return base + ext
    mp4s = sorted(Path(work_dir).glob("*.mp4"))
    if mp4s:
        return str(mp4s[0])
    for ext in ["*.mkv", "*.webm"]:
        others = sorted(Path(work_dir).glob(ext))
        if others:
            return str(others[0])
    raise FileNotFoundError(f"Could not locate downloaded video in {work_dir}")


def get_person_focus_x(video_path: str, start: float, end: float) -> Optional[float]:
    try:
        import cv2
        import numpy as np
        from mediapipe.solutions import face_detection as mp_face
    except ImportError:
        return None

    duration = end - start
    num_samples = 8
    if duration <= num_samples:
        timestamps = [start + i for i in range(int(duration))]
    else:
        step = duration / (num_samples - 1)
        timestamps = [start + i * step for i in range(num_samples)]
    if not timestamps:
        timestamps = [start]

    centers: list[float] = []
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as detector:
        for ts in timestamps:
            cmd = ["ffmpeg", "-y", "-fflags", "+genpts+igndts", "-ss", str(ts), "-i", video_path, "-avoid_negative_ts", "make_zero", "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"]
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=30)
            except subprocess.TimeoutExpired:
                continue
            if r.returncode != 0 or not r.stdout:
                continue
            nparr = np.frombuffer(r.stdout, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                continue
            h, w = frame.shape[:2]
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = detector.process(rgb_frame)
            if results.detections:
                best_d = max(results.detections, key=lambda d: d.location_data.relative_bounding_box.width)
                bbox = best_d.location_data.relative_bounding_box
                centers.append(bbox.xmin + (bbox.width / 2))

    if not centers:
        return None
    centers.sort()
    return centers[len(centers) // 2]


def format_ass_time(s: float) -> str:
    ms = int(s * 1000)
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    centiseconds = (ms % 1000) // 10
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def generate_ass(words: list[dict], style: dict, start_offset: float) -> str:
    font = style.get("font", "Montserrat Black")
    size = style.get("size", 24)
    primary = style.get("primary_color", "&H00FFFFFF")
    highlight = style.get("highlight_color", "&H0000FFFF")
    outline_color = style.get("outline_color", "&H00000000")
    back_color = style.get("back_color", "&H00000000")
    outline = style.get("outline", 2)
    shadow = style.get("shadow", 0)
    border_style = style.get("border_style", 1)
    uppercase = style.get("uppercase", False)
    words_per_frame = style.get("words_per_frame", 3)
    position = style.get("position", "middle")

    if position == "top":
        alignment = 8
        margin_v = 150
    elif position == "middle":
        alignment = 5
        margin_v = 0
    else:
        alignment = 2
        margin_v = 150

    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColor, SecondaryColor, OutlineColor, BackColor, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font},{size * 3.5},{primary},{highlight},{outline_color},{back_color},1,0,0,0,100,100,0,0,{border_style},{outline * 2},{shadow * 2},{alignment},50,50,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    events = []
    clip_words = [w for w in words if w["start"] >= start_offset]

    for i in range(0, len(clip_words), words_per_frame):
        chunk = clip_words[i: i + words_per_frame]
        if not chunk:
            continue

        start_time = max(0, chunk[0]["start"] - start_offset)
        end_time = max(0, chunk[-1]["end"] - start_offset)

        text_parts = []
        total_chars = 0
        for w in chunk:
            word_text = w["text"]
            if uppercase:
                word_text = word_text.upper()
            total_chars += len(word_text) + 1
            w_dur_ms = (w["end"] - w["start"]) * 1000
            k_dur = max(1, math.floor(w_dur_ms / 10))
            text_parts.append(f"{{\\k{k_dur}}}{word_text}")

        if total_chars > 45:
            mid = len(text_parts) // 2
            text_parts.insert(mid, "\\N")

        line_text = " ".join(text_parts).replace(" \\N ", "\\N")
        events.append(f"Dialogue: 0,{format_ass_time(start_time)},{format_ass_time(end_time)},Default,,0,0,0,,{line_text}")

    return "\n".join(header + events)


def make_short(src: str, dst: str, start: float, end: float, focus_x: Optional[float] = None, ass_path: Optional[str] = None) -> None:
    dur = end - start
    w, h = probe_video(src)
    target_w = h * (9 / 16)

    if focus_x is not None:
        center_px = focus_x * w
        x_offset = center_px - (target_w / 2)
        x_offset = max(0, min(x_offset, w - target_w))
    else:
        x_offset = (w - target_w) / 2

    vf = f"crop={target_w}:{h}:{x_offset}:0,scale=1080:1920:flags=lanczos"
    if ass_path:
        clean_path = os.path.abspath(ass_path).replace('\\', '/').replace(':', '\\:')
        vf += f",ass='{clean_path}':shaping=complex"

    cmd = [
        "ffmpeg", "-y",
        "-fflags", "+genpts+igndts",
        "-ss", str(start),
        "-t", str(dur),
        "-i", src,
        "-avoid_negative_ts", "make_zero",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        dst,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {r.stderr[-500:]}")
