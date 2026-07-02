import os

try:
    import streamlit as st
except ImportError:
    st = None


def _collect_keys() -> list[str]:
    seen: list[str] = []
    candidates: list[str] = []

    if st is not None:
        for k, v in st.secrets.items():
            if k.startswith("GROQ_API_KEY") and isinstance(v, str) and v.strip():
                candidates.append((k, v.strip()))

    for k in ["GROQ_API_KEY"] + [f"GROQ_API_KEY_{i}" for i in range(1, 6)]:
        v = os.getenv(k, "").strip()
        if v:
            candidates.append((k, v))

    for k, v in candidates:
        if v not in seen:
            seen.append(v)

    return seen


def resolve_api_keys(manual_key: str = "") -> list[str]:
    if manual_key.strip() and manual_key.startswith("gsk_"):
        return [manual_key]
    keys = _collect_keys()
    return list(keys) if keys else []
