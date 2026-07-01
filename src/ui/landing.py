import streamlit as st


def render_landing():
    st.markdown("""
<div class="how-to">
<h3>How it works</h3>
<ol>
  <li><span>Paste a YouTube link</span> — single video or up to 10 URLs in batch mode.</li>
  <li><span>AI finds the moments</span> — transcript is chunked and analyzed for every self-contained, hook-worthy segment.</li>
  <li><span>Video is downloaded and cut</span> — FFmpeg renders each clip at 1080×1920 with auto speaker centering.</li>
  <li><span>Download everything</span> — clips and transcripts ready individually or as a ZIP.</li>
</ol>
<div class="req-block">
  <strong>Tips:</strong><br>
  — Batch mode processes videos <strong>one at a time</strong> — safe for long overnight runs.<br>
  — Full processing log is available per video after completion.<br>
  — Transcripts (no timestamps) are included for every clip — paste into your caption tool.
</div>
</div>
""", unsafe_allow_html=True)
