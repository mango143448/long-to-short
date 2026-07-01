import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

LINES_PER_CHUNK = 100
CHUNK_OVERLAP = 20
MIN_DELAY_SEC = 75.0
RETRY_DELAYS = [45, 90, 180, 360]
MAX_BATCH_URLS = 10

PIPELINE_STEPS = ["transcript", "analysis", "download", "cutting", "done"]

STEP_LABELS = {
    "transcript": "Transcript",
    "analysis": "AI Analysis",
    "download": "Download",
    "cutting": "Cutting Clips",
    "done": "Complete",
}

DURATION_MIN = 20
DURATION_MAX = 120

GROQ_MODEL = "llama-3.3-70b-versatile"

GROQ_API_KEYS: list[str] = []
single = os.getenv("GROQ_API_KEY", "").strip()
if single:
    GROQ_API_KEYS.append(single)
for i in range(1, 6):
    key = os.getenv(f"GROQ_API_KEY_{i}", "").strip()
    if key and key not in GROQ_API_KEYS:
        GROQ_API_KEYS.append(key)


def resolve_api_keys(manual_key: str = "") -> list[str]:
    if manual_key.strip() and manual_key.startswith("gsk_"):
        return [manual_key]
    return list(GROQ_API_KEYS) if GROQ_API_KEYS else []


PROJECT_ROOT = Path(__file__).resolve().parent.parent
