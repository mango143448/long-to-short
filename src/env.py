import os

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
