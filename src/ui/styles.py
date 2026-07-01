import streamlit as st


def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

[data-testid="stSidebar"] {
    background: #0d0d0d !important;
    border-right: 1px solid #222;
}
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }

.app-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.4rem;
    font-weight: 700;
    background: linear-gradient(135deg, #fff 30%, #888);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
}
.app-sub { color: #666; font-size: 0.95rem; margin-top: 2px; margin-bottom: 28px; }

.clip-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #555;
    text-transform: uppercase;
}
.clip-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.25rem;
    font-weight: 700;
    color: #f0f0f0;
    margin: 2px 0 10px;
}
.clip-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #aaa;
    background: #111;
    border: 1px solid #2a2a2a;
    padding: 4px 10px;
    border-radius: 6px;
    display: inline-block;
    margin-bottom: 10px;
}
.hook-label { font-size: 0.75rem; font-weight: 600; color: #555; text-transform: uppercase; letter-spacing: 0.07em; }
.hook-text { color: #ccc; font-size: 0.9rem; font-style: italic; margin: 2px 0 8px; }
.reason-text { color: #666; font-size: 0.85rem; line-height: 1.5; }

.batch-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #ccc;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}
.batch-subtext {
    font-size: 0.8rem;
    color: #444;
    margin-bottom: 16px;
}

.job-card {
    background: #0f0f0f;
    border: 1px solid #1e1e1e;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
    transition: border-color 0.2s;
}
.job-card.active  { border-color: #2a4a7f; background: #0a0f1a; }
.job-card.done    { border-color: #1a3a2a; background: #0a120d; }
.job-card.failed  { border-color: #3a1a1a; background: #120a0a; }
.job-card.queued  { border-color: #1e1e1e; opacity: 0.6; }

.job-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}
.job-id {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.85rem;
    font-weight: 700;
    color: #ccc;
    letter-spacing: 0.04em;
}
.job-badge {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 3px 9px;
    border-radius: 20px;
}
.job-badge.queued   { background: #1a1a1a; color: #555; border: 1px solid #333; }
.job-badge.active   { background: #0d1f3c; color: #4a9eff; border: 1px solid #1a3a6a; }
.job-badge.done     { background: #0a2016; color: #3d9970; border: 1px solid #1a4a30; }
.job-badge.failed   { background: #200a0a; color: #cc4444; border: 1px solid #4a1a1a; }

.job-step {
    font-size: 0.78rem;
    color: #555;
    margin-top: 4px;
    min-height: 18px;
}
.job-step.active { color: #aaa; }
.job-step.done   { color: #3d9970; }
.job-step.failed { color: #cc4444; }

.step-trail {
    display: flex;
    gap: 6px;
    margin-top: 8px;
    flex-wrap: wrap;
}
.step-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #222;
    border: 1px solid #333;
    display: inline-block;
}
.step-dot.done   { background: #3d9970; border-color: #3d9970; }
.step-dot.active { background: #4a9eff; border-color: #4a9eff; }
.step-dot.failed { background: #cc4444; border-color: #cc4444; }

.step-label {
    font-size: 0.68rem;
    color: #333;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    display: flex;
    align-items: center;
    gap: 4px;
}
.step-label.done   { color: #3d9970; }
.step-label.active { color: #4a9eff; }
.step-label.failed { color: #cc4444; }

.clip-progress {
    font-size: 0.75rem;
    color: #4a9eff;
    margin-top: 4px;
    font-variant-numeric: tabular-nums;
}

.how-to { background: #0d0d0d; border: 1px solid #1e1e1e; border-radius: 12px; padding: 28px 32px; }
.how-to h3 { font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; color: #ccc; margin-bottom: 16px; }
.how-to ol { padding-left: 20px; color: #777; line-height: 2; font-size: 0.9rem; }
.how-to ol li span { color: #ccc; }
.req-block { background: #111; border: 1px solid #1e1e1e; border-radius: 8px; padding: 14px 18px; margin-top: 16px; font-size: 0.82rem; color: #555; }
.req-block code { background: #1a1a1a; color: #aaa; padding: 2px 6px; border-radius: 4px; font-size: 0.82rem; }

/* ── Queue header ──────────────────────────────────────── */

.queue-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #999;
    letter-spacing: 0.04em;
    margin-bottom: 10px;
}

/* ── Card ──────────────────────────────────────────────── */

.card {
    background: #0f0f0f;
    border: 1px solid #1e1e1e;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: border-color 0.25s;
}
.card-active { border-color: #2a4a7f; background: #0a0f1a; }
.card-done   { border-color: #1a3a2a; background: #0a120d; }
.card-failed { border-color: #3a1a1a; background: #120a0a; }
.card-queued { border-color: #1e1e1e; opacity: 0.55; }

.card-top {
    display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;
}
.card-id {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.85rem; font-weight: 700; color: #ccc;
}
.card-badge {
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; padding: 2px 10px; border-radius: 20px;
}
.card-badge-queued   { background: #1a1a1a; color: #555; border: 1px solid #333; }
.card-badge-active   { background: #0d1f3c; color: #4a9eff; border: 1px solid #1a3a6a; }
.card-badge-done     { background: #0a2016; color: #3d9970; border: 1px solid #1a4a30; }
.card-badge-failed   { background: #200a0a; color: #cc4444; border: 1px solid #4a1a1a; }

.card-foot {
    font-size: 0.72rem; color: #555; margin-top: 8px;
}

/* ── Step Bar ──────────────────────────────────────────── */

.step-bar {
    display: flex; align-items: center; gap: 4px;
    padding: 8px 0; margin-bottom: 10px;
}
.step-dot {
    font-size: 0.7rem; font-weight: 700;
    width: 18px; height: 18px;
    display: inline-flex; align-items: center; justify-content: center;
    border-radius: 50%; flex-shrink: 0;
}
.step-dot.step-done   { color: #3d9970; background: #0a2016; border: 1px solid #1a4a30; }
.step-dot.step-active { color: #4a9eff; background: #0d1f3c; border: 1px solid #1a3a6a; animation: dot-pulse 1.2s ease-in-out infinite; }
.step-dot.step-failed { color: #cc4444; background: #200a0a; border: 1px solid #4a1a1a; }
.step-dot.step-queued { color: #333; background: #0a0a0a; border: 1px solid #1a1a1a; }

@keyframes dot-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(74, 158, 255, 0.4); }
    50% { box-shadow: 0 0 0 6px rgba(74, 158, 255, 0); }
}

.step-label {
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.04em;
    text-transform: uppercase; margin-right: 2px;
}
.step-label.step-done   { color: #3d9970; }
.step-label.step-active { color: #4a9eff; }
.step-label.step-failed { color: #cc4444; }
.step-label.step-queued { color: #333; }

.step-connector {
    width: 16px; height: 2px; border-radius: 1px; flex-shrink: 0;
}
.step-connector.step-done   { background: #3d9970; }
.step-connector.step-active { background: #4a9eff; }
.step-connector.step-queued { background: #1a1a1a; }
.step-connector.step-failed { background: #cc4444; }

/* ── Stage Card ────────────────────────────────────────── */

.stage-card {
    display: flex; gap: 14px;
    padding: 14px 16px;
    border-radius: 12px;
    margin-bottom: 8px;
    align-items: flex-start;
    position: relative;
    overflow: hidden;
}
.stage-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    border-radius: 12px;
    opacity: 0.06;
    pointer-events: none;
}
.stage-transcript {
    background: linear-gradient(135deg, #0a0a1a, #0d0d20);
    border: 1px solid #1a1a3a;
}
.stage-transcript::before { background: linear-gradient(135deg, #4a9eff, #6ab0ff); }
.stage-analysis {
    background: linear-gradient(135deg, #0a0f1a, #0d1220);
    border: 1px solid #1a2a4a;
}
.stage-analysis::before { background: linear-gradient(135deg, #a855f7, #7c3aed); }
.stage-download {
    background: linear-gradient(135deg, #0a0a14, #0d0d1a);
    border: 1px solid #1a1a3a;
}
.stage-download::before { background: linear-gradient(135deg, #4a9eff, #3b82f6); }
.stage-cutting {
    background: linear-gradient(135deg, #0f0a0a, #1a0d0d);
    border: 1px solid #2a1a1a;
}
.stage-cutting::before { background: linear-gradient(135deg, #f97316, #ea580c); }
.stage-done {
    background: linear-gradient(135deg, #0a120d, #0d1a10);
    border: 1px solid #1a3a2a;
}
.stage-done::before { background: linear-gradient(135deg, #3d9970, #2d7a55); }
.stage-failed {
    background: linear-gradient(135deg, #120a0a, #1a0d0d);
    border: 1px solid #3a1a1a;
}
.stage-failed::before { background: linear-gradient(135deg, #cc4444, #aa3333); }

.stage-icon { font-size: 1.5rem; line-height: 1; position: relative; z-index: 1; }
.stage-body { flex: 1; min-width: 0; position: relative; z-index: 1; }
.stage-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.95rem; font-weight: 700; color: #e0e0e0; margin-bottom: 4px;
    display: flex; align-items: center; gap: 8px;
}
.stage-sub {
    font-size: 0.75rem; color: #777; margin-bottom: 6px;
}

.stage-status {
    font-size: 0.78rem;
    color: #888;
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
}

.stage-metric {
    font-size: 0.78rem;
    color: #aaa;
    display: flex;
    align-items: center;
    gap: 5px;
    margin-bottom: 3px;
    font-variant-numeric: tabular-nums;
}

.metric-icon { font-size: 0.85rem; }

.live-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #4a9eff;
    display: inline-block;
    animation: live-pulse 1.2s ease-in-out infinite;
    flex-shrink: 0;
}

@keyframes live-pulse {
    0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 0 0 rgba(74, 158, 255, 0.6); }
    50% { opacity: 0.6; transform: scale(0.85); box-shadow: 0 0 0 6px rgba(74, 158, 255, 0); }
}

.provider-badge {
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    padding: 2px 8px;
    border-radius: 20px;
    text-transform: uppercase;
    display: inline-block;
    vertical-align: middle;
}
.provider-groq {
    background: #1a0a1a;
    color: #f97316;
    border: 1px solid #3a1a0a;
}

.stage-spinner {
    width: 16px; height: 16px;
    border: 2px solid #2a2a4a; border-top-color: #4a9eff;
    border-radius: 50%; margin-top: 4px;
    animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Progress bar ─────────────────────────────────────── */

.prog {
    width: 100%; height: 5px;
    background: #1a1a1a; border-radius: 3px; overflow: hidden;
    margin-top: 4px;
}
.prog-fill {
    height: 100%; border-radius: 3px;
    background: linear-gradient(90deg, #4a9eff, #6ab0ff);
    transition: width 0.35s ease;
}
.prog-indeterminate {
    width: 30%; animation: prog-shimmer 1.5s ease-in-out infinite;
}
@keyframes prog-shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
}

/* ── Clip queue ───────────────────────────────────────── */

.clip-queue {
    display: flex; gap: 5px; flex-wrap: wrap; margin: 6px 0;
}
.clip-queue-item {
    font-size: 1rem; transition: transform 0.2s;
    display: inline-flex; align-items: center; justify-content: center;
    width: 24px; height: 24px;
}
.clip-queue-active { animation: clip-pop 0.8s ease-in-out infinite; }
@keyframes clip-pop {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.25); }
}
.clip-queue-done   { opacity: 1; filter: none; }
.clip-queue-failed { opacity: 0.5; filter: grayscale(0.5); }
.clip-queue-queued { opacity: 0.3; filter: grayscale(0.7); }

/* ── Timer ────────────────────────────────────────────── */

.timer {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem; color: #555;
    font-variant-numeric: tabular-nums; margin: 4px 0;
}

/* ── Log details (post-completion only) ────────────────── */

.log-details { margin-top: 6px; }
.log-summary {
    font-size: 0.7rem; color: #555; cursor: pointer;
    user-select: none; display: inline-block;
    padding: 3px 10px; border-radius: 12px;
    border: 1px solid #222; background: #0a0a0a;
    transition: all 0.2s;
}
.log-summary:hover { color: #aaa; border-color: #444; background: #111; }
.log-box {
    background: #080808; border: 1px solid #1a1a1a;
    border-radius: 6px; padding: 8px 10px; margin-top: 6px;
    max-height: 220px; overflow-y: auto;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 0.68rem; line-height: 1.5;
}
.log-box::-webkit-scrollbar { width: 3px; }
.log-box::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 2px; }
.log-line { color: #666; white-space: pre-wrap; word-break: break-all; }
.log-ok  { color: #3d9970; }
.log-err { color: #cc4444; }

</style>
""", unsafe_allow_html=True)
