# Video → Shorts Generator

Turn any long YouTube video into punchy 9:16 short clips using Gemini AI.

## Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

> Recommended: use Python 3.12 on Windows for the pinned NumPy/langchain stack.

### 2. Install ffmpeg (system dependency)
```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# Windows — download from https://ffmpeg.org/download.html and add to PATH
```

### 3. Run the app
```bash
streamlit run app.py
```

---

## How to use

1. **Paste a YouTube URL** — any public video that has captions (auto-generated or manual)
2. **Enter your Groq API key(s)** — get one at https://console.groq.com/keys
3. **Choose your settings:**
   - Number of clips (1–8)
   - Approximate duration per clip (20–90 seconds)
4. Click **Analyze Video** — Groq reads the transcript and suggests the best moments
5. Click **✂️ Cut Clip** on any suggestion — the source video is downloaded once, then the clip is trimmed
6. **Download** your 9:16 MP4 shorts

---

## Output format

- Resolution: **1080 × 1920** (9:16 portrait)
- Codec: H.264 / AAC
- Ready for: YouTube Shorts, TikTok, Instagram Reels

Landscape videos are centre-cropped to 9:16. Portrait videos are padded if needed.

---

## Notes

- The source video is downloaded once and reused for all clips in a session
- Temp files are stored in a system temp directory and cleaned up on reset
- Groq model used: `llama-3.3-70b-versatile`
- Up to 5 API keys supported with automatic rate-limit rotation
- Videos without captions will fail at the transcript step
