import io
import re
import zipfile

from src.types import JobResult
from src.services.transcript import extract_video_id


def create_zip_of_results(batch_results: dict[str, JobResult]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for url, data in batch_results.items():
            if not data.success:
                continue
            vid_id = data.vid_id or extract_video_id(url) or "manual"
            folder = f"video_{vid_id}"
            for i, clip_bytes in data.generated.items():
                clip = data.clips[i]
                title = re.sub(r'[^\w\-_\. ]', '_', clip.title or f'clip_{i + 1}')
                z.writestr(f"{folder}/short_{i + 1}_{title}.mp4", clip_bytes)
                if i in data.clip_transcripts:
                    z.writestr(f"{folder}/transcript_{i + 1}.txt", data.clip_transcripts[i])
    buf.seek(0)
    return buf
