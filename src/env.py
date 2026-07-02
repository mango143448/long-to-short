import os

_KEYS_CACHE: list[str] | None = None


def resolve_api_keys(manual_key: str = "") -> list[str]:
    if manual_key.strip() and manual_key.startswith("gsk_"):
        return [manual_key]

    global _KEYS_CACHE
    if _KEYS_CACHE is not None:
        return list(_KEYS_CACHE)

    seen: list[str] = []

    try:
        import streamlit as st

        for name in ["GROQ_API_KEY"] + [f"GROQ_API_KEY_{i}" for i in range(1, 6)]:
            val = st.secrets.get(name, "")
            if isinstance(val, str) and val.strip() and val not in seen:
                seen.append(val.strip())
    except Exception:
        pass

    for name in ["GROQ_API_KEY"] + [f"GROQ_API_KEY_{i}" for i in range(1, 6)]:
        val = os.getenv(name, "")
        if val.strip() and val not in seen:
            seen.append(val.strip())

    _KEYS_CACHE = seen
    return list(seen)
