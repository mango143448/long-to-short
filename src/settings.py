from pathlib import Path

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
