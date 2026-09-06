"""
app.py
------
Entry point for NetSight — AI-Based Network Attack Forecaster (SIH26153).

Cyber Defence OS shell:
  1. Home            — intelligence overview (product story, system telemetry)
  2. SOC Command Center — the command center (workflow centers in tabs)

Design language: restrained dark command center. Cyan = dataflow/active,
amber = elevated, red = critical (rare), green = healthy.

Everything runs offline on the committed models; no data leaves the machine.
"""

import json

import streamlit as st

st.set_page_config(
    page_title="NetSight — Threat Command Center",
    page_icon="🛰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

:root {
    --bg:        #05070a;
    --bg-2:      #07090d;
    --surface-1: #0b1017;
    --surface-2: #0e141c;
    --surface-3: #111821;
    --border:    #1a2230;
    --border-hi: #263244;
    --accent:    #22d3ee;
    --accent-2:  #38bdf8;
    --accent-dim:#164e63;
    --amber:     #f59e0b;
    --red:       #ef4444;
    --green:     #34d399;
    --text:      #d7e1ec;
    --muted:     #8494a6;
    --dim:       #5d6b7c;
    --radius:    10px;
    --mono:      'JetBrains Mono', ui-monospace, monospace;
}

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }

.stApp {
    isolation: isolate;
    background: radial-gradient(1200px 700px at 80% -10%, rgba(14,116,144,.10), transparent 55%),
                radial-gradient(900px 600px at -5% 60%, rgba(33,64,102,.12), transparent 50%),
                var(--bg);
}

/* faint cyber grid — much quieter than before */
.stApp::before {
    content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
    background-image:
        linear-gradient(rgba(147,197,253,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(147,197,253,.035) 1px, transparent 1px);
    background-size: 52px 52px;
    mask-image: radial-gradient(ellipse 85% 65% at 50% 0%, black 35%, transparent 100%);
    -webkit-mask-image: radial-gradient(ellipse 85% 65% at 50% 0%, black 35%, transparent 100%);
    animation: gridDrift 120s linear infinite;
}
@keyframes gridDrift { to { background-position: 104px 104px, 104px 104px; } }

/* one slow scanline sweep — subtle */
.stApp::after {
    content:""; position:fixed; left:0; right:0; height:120px; pointer-events:none;
    z-index:1; top:-120px;
    background: linear-gradient(180deg, transparent, rgba(56,189,248,.04), transparent);
    animation: scan 12s linear infinite;
}
@keyframes scan { to { transform: translateY(130vh); } }

/* ---------- shell: top command bar ---------- */
.topbar {
    position:fixed; top:0; left:0; right:0; z-index:80; height:48px;
    display:flex; align-items:center; justify-content:space-between;
    padding:0 18px 0 22px;
    background: rgba(5,7,10,.92); backdrop-filter: blur(10px) saturate(130%);
    border-bottom:1px solid var(--border);
    font-family: var(--mono);
}
.topbar .tb-brand { display:flex; align-items:baseline; gap:12px; }
.topbar .tb-name { font-size:1.02rem; font-weight:700; letter-spacing:.24em; color:var(--text); }
.topbar .tb-name b { color:var(--accent); font-weight:700; }
.topbar .tb-sub { font-size:.62rem; letter-spacing:.28em; color:var(--dim); text-transform:uppercase; }
.topbar .tb-right { display:flex; align-items:center; gap:14px; }
.topbar .syschip {
    display:inline-flex; align-items:center; gap:7px; font-size:.6rem;
    letter-spacing:.14em; color:var(--muted); text-transform:uppercase;
    padding:3px 10px; border:1px solid var(--border); border-radius:6px;
    background: var(--surface-1);
}
.topbar .syschip.ok i { width:6px; height:6px; border-radius:50%; background:var(--green);
    box-shadow:0 0 6px rgba(52,211,153,.6); }
.topbar .syschip b { color:var(--text); font-weight:600; }

/* ---------- SOC ticker ---------- */
#soc-ticker {
    position:fixed; top:48px; left:0; right:0; z-index:75; height:34px;
    display:flex; align-items:center; overflow:hidden;
    background: rgba(5,7,10,.88); backdrop-filter: blur(8px);
    border-bottom:1px solid var(--border);
    font-family: var(--mono);
}
#soc-ticker .tk-label {
    flex:none; display:flex; align-items:center; gap:8px;
    padding:0 15px; height:100%;
    font-size:.62rem; font-weight:700; letter-spacing:.22em; color:#7fd8e8;
    text-transform:uppercase;
    background: linear-gradient(90deg, rgba(34,211,238,.13), transparent);
    border-right:1px solid var(--border);
}
#soc-ticker .tk-label i { width:6px; height:6px; border-radius:50%; background:var(--accent);
    box-shadow:0 0 6px rgba(34,211,238,.7); animation: pulseDot 1.4s ease-in-out infinite; }
#soc-ticker .tk-track { flex:1; min-width:0; overflow:hidden; height:100%;
    display:flex; align-items:center;
    mask-image: linear-gradient(90deg, transparent, #000 5%, #000 95%, transparent);
    -webkit-mask-image: linear-gradient(90deg, transparent, #000 5%, #000 95%, transparent); }
#soc-ticker .tk-inner { display:inline-flex; align-items:center; white-space:nowrap;
    padding-left:8px; animation: tkScroll 70s linear infinite; }
#soc-ticker .tk-inner span { color:#8494a6; font-size:.66rem; letter-spacing:.05em; }
#soc-ticker .tk-inner em { font-style:normal; color:#67e8f9; font-weight:600; }
#soc-ticker .tk-inner b { color:#42536e; font-weight:600; }
@keyframes tkScroll { from { transform:translateX(0);} to { transform:translateX(-50%);} }

/* ---------- layout ---------- */
.block-container { padding-top: 98px; padding-bottom: 3rem; max-width: 1400px; }

/* ---------- typography ---------- */
h1, h2, h3, h4 { font-family:'Inter', sans-serif; color:var(--text); letter-spacing:-.01em; }
h1 { font-weight:800; } h2 { font-weight:700; } h3 { font-weight:600; }

/* ---------- section headers ---------- */
.sec-title { display:flex; align-items:center; gap:10px; margin:26px 0 12px; }
.sec-title::before { content:""; width:3px; height:16px; border-radius:2px;
    background:var(--accent); box-shadow:0 0 8px rgba(34,211,238,.5); }
.sec-title h3 { margin:0; font-size:1rem; letter-spacing:.02em; }
.sec-title h4 { margin:0; font-size:.86rem; color:var(--muted); font-weight:600; }

.csec { display:flex; align-items:center; gap:14px; margin:42px 0 18px; position:relative; }
.csec::before { content:""; width:3px; height:18px; border-radius:2px;
    background:var(--accent-2); box-shadow:0 0 8px rgba(56,189,248,.45); }
.csec h3 { margin:0; font-size:1.05rem; letter-spacing:.01em; }
.csec .secno { font-family:var(--mono); font-size:.62rem; letter-spacing:.18em; color:#42536e;
    border:1px solid var(--border-hi); background:rgba(15,20,30,.6); padding:2px 8px; border-radius:5px; }
.csec .csec-line { flex:1; height:1px; background:linear-gradient(90deg, var(--border-hi), transparent); }

/* small technical label */
.tlabel { font-family:var(--mono); font-size:.58rem; letter-spacing:.18em;
    color:var(--dim); text-transform:uppercase; }

/* ---------- hero (editorial) ---------- */
.hero {
    position:relative; overflow:hidden;
    background:
        radial-gradient(900px 380px at 85% -25%, rgba(14,116,144,.28), transparent 60%),
        radial-gradient(640px 320px at 0% 118%, rgba(38,64,110,.24), transparent 55%),
        linear-gradient(150deg,#0b1119 0%, #06080d 100%);
    border:1px solid var(--border-hi); border-radius:18px; padding:44px 46px 40px; margin-bottom:16px;
    box-shadow: 0 24px 60px -26px rgba(0,0,0,.85), inset 0 1px 0 rgba(148,163,184,.07);
}
.hero::before { content:""; position:absolute; inset:0; pointer-events:none; opacity:.55;
    background-image: linear-gradient(rgba(148,163,184,.05) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(148,163,184,.05) 1px, transparent 1px);
    background-size: 44px 44px;
    -webkit-mask-image: radial-gradient(80% 72% at 32% 30%, #000 28%, transparent 80%);
            mask-image: radial-gradient(80% 72% at 32% 30%, #000 28%, transparent 80%); }
.hero::after { content:""; position:absolute; top:0; left:0; right:0; height:1px;
    background: linear-gradient(90deg, transparent, rgba(34,211,238,.55), transparent); }
.hero .glass-inner { position:relative; }
.hero .hero-meta { display:flex; align-items:center; justify-content:space-between;
    gap:12px; flex-wrap:wrap; margin-bottom:24px;
    padding-bottom:14px; border-bottom:1px solid rgba(26,34,48,.9); }
.hero .hero-meta .sys { font-family:var(--mono); font-size:.6rem; letter-spacing:.22em;
    color:var(--dim); text-transform:uppercase; }
.hero .hero-meta .sys b { color:#8aa0bb; }
.hero .hero-meta .status { display:inline-flex; align-items:center; gap:8px;
    font-family:var(--mono); font-size:.6rem; letter-spacing:.18em; color:#86efac;
    background:rgba(52,211,153,.08); border:1px solid rgba(52,211,153,.28);
    padding:4px 11px; border-radius:999px; text-transform:uppercase; }
.hero .hero-meta .status i { width:6px; height:6px; border-radius:50%; background:#34d399;
    animation:pulseDot 1.6s ease-in-out infinite; }
.hero .kicker { color:#67d9ea; letter-spacing:.30em; font-weight:700; font-size:.66rem;
    text-transform:uppercase; position:relative; }
.hero h1 { font-size:3.1rem; margin:.55rem 0 .7rem; line-height:1.02; position:relative;
    color:#eef6ff; font-weight:800; letter-spacing:-.015em; }
.hero h1 .cy {
    background: linear-gradient(100deg,#22d3ee 0%, #38bdf8 55%, #818cf8 100%);
    -webkit-background-clip:text; background-clip:text; color:transparent;
    filter: drop-shadow(0 0 16px rgba(34,211,238,.28)); }
.hero .sub { color:#9db1c5; font-size:1.02rem; max-width:760px; line-height:1.66; position:relative; }
.hero .sub b { color:#d7e5f2; font-weight:600; }
.hero .hk { display:flex; align-items:center; gap:10px; margin-top:26px; flex-wrap:wrap; position:relative; }
.hero .hk .hlab { font-family:var(--mono); font-size:.6rem; letter-spacing:.16em;
    color:var(--dim); text-transform:uppercase; margin-right:6px; }
.hero .hk .chip { margin-right:0; }

/* ---------- typography metrics row ---------- */
.metro { display:grid; grid-template-columns: repeat(6,1fr); gap:1px;
    margin:14px 0 8px; border:1px solid var(--border-hi); border-radius:14px;
    background:var(--surface-1); overflow:hidden;
    box-shadow: 0 18px 40px -24px rgba(0,0,0,.7); }
.metro .mi { position:relative; padding:16px 16px 14px; background:
    linear-gradient(180deg, rgba(255,255,255,.02), transparent 72%); }
.metro .mi::before { content:""; position:absolute; top:0; left:14px; right:14px; height:2px;
    border-radius:0 0 2px 2px; background:var(--dim); opacity:.35; }
.metro .mi.g::before { background:var(--green); opacity:.85; box-shadow:0 0 10px rgba(52,211,153,.5); }
.metro .mi.b::before { background:var(--accent-2); opacity:.85; box-shadow:0 0 10px rgba(56,189,248,.5); }
.metro .mi.v::before { background:#a78bfa; opacity:.85; box-shadow:0 0 10px rgba(167,139,250,.5); }
.metro .mi.o::before { background:var(--amber); opacity:.85; box-shadow:0 0 10px rgba(245,158,11,.5); }
.metro .mi .nv { font-family:var(--mono); font-weight:700; font-size:1.72rem;
    color:var(--text); letter-spacing:-.02em; line-height:1.05; }
.metro .mi .nv.g { color:var(--green); } .metro .mi .nv.b { color:var(--accent-2); }
.metro .mi .nv.v { color:#a78bfa; } .metro .mi .nv.o { color:var(--amber); }
.metro .mi .nl { display:flex; align-items:center; gap:6px; font-size:.6rem; letter-spacing:.14em;
    color:var(--dim); text-transform:uppercase; margin-top:7px; font-family:var(--mono); }
.metro .mi .nl i { width:5px; height:5px; border-radius:50%; background:currentColor; opacity:.75; }
.metro .mi .spark { display:flex; gap:3px; margin-top:11px; height:16px; align-items:flex-end; }
.metro .mi .spark s { display:block; width:4px; border-radius:1px; background:
    linear-gradient(180deg, rgba(148,163,184,.55), rgba(148,163,184,.10)); }

/* ---------- badges & status ---------- */
.badge { display:inline-block; padding:2px 9px; border-radius:4px; font-size:.64rem;
    font-weight:700; letter-spacing:.08em; text-transform:uppercase;
    border:1px solid transparent; font-family:var(--mono); }
.badge.crit { background:rgba(239,68,68,.12); color:#fca5a5; border-color:rgba(239,68,68,.45); }
.badge.high { background:rgba(245,158,11,.12); color:#fcd34d; border-color:rgba(245,158,11,.4); }
.badge.med  { background:rgba(245,158,11,.10); color:#fbbf24; border-color:rgba(245,158,11,.32); }
.badge.low  { background:rgba(52,211,153,.10); color:#6ee7b7; border-color:rgba(52,211,153,.35); }
.badge.safe { background:rgba(52,211,153,.10); color:#6ee7b7; border-color:rgba(52,211,153,.35); }
.badge.info { background:rgba(34,211,238,.10); color:#67e8f9; border-color:rgba(34,211,238,.38); }
.badge.warn { background:rgba(245,158,11,.12); color:#fde047; border-color:rgba(245,158,11,.4); }
.badge.none { background:rgba(148,163,184,.10); color:#94a3b8; border-color:rgba(148,163,184,.32); }

.chip { display:inline-block; background:linear-gradient(180deg, rgba(148,163,184,.06), transparent),
    var(--surface-3); border:1px solid var(--border-hi); color:#c6d4e3; font-family:var(--mono);
    font-size:.7rem; padding:3px 10px; border-radius:6px; margin:2px 6px 2px 0;
    transition: border-color .15s ease, transform .15s ease; }
.chip:hover { border-color:#3a4a66; transform:translateY(-1px); }
.chip.r { color:#fca5a5; border-color:rgba(239,68,68,.4); background:rgba(239,68,68,.06); }
.chip.o { color:#fdba74; border-color:rgba(245,158,11,.4); background:rgba(245,158,11,.06); }
.chip.g { color:#86efac; border-color:rgba(52,211,153,.38); background:rgba(52,211,153,.06); }
.chip i { display:inline-block; width:5px; height:5px; border-radius:50%; margin-right:6px;
    vertical-align:middle; background:currentColor; opacity:.9; }

.dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:7px; }
.dot.pulse { animation: pulseDot 1.6s ease-in-out infinite; }
.dot.g { background:var(--green); } .dot.r { background:var(--red); }
.dot.y { background:var(--amber); } .dot.b { background:var(--accent); }
@keyframes pulseDot { 0%,100%{ box-shadow:0 0 0 0 rgba(239,68,68,.4);} 50%{ box-shadow:0 0 0 5px rgba(239,68,68,0);} }
@keyframes pulse { 0%,100%{ box-shadow:0 0 0 0 rgba(52,211,153,.5);} 50%{ box-shadow:0 0 0 5px rgba(52,211,153,0);} }

/* ---------- alert / threat cards ---------- */
.alert-card {
    background: linear-gradient(160deg,#10141c 0%, #0b0f16 100%);
    border:1px solid var(--border); border-left:3px solid var(--red);
    border-radius:8px; padding:10px 14px; margin:6px 0;
    box-shadow: 0 3px 10px -6px rgba(0,0,0,.6);
}
.alert-card .row { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
.alert-card .who { font-weight:600; color:var(--text); font-size:.85rem; }

/* ---------- context bar ---------- */
.ctxbar {
    display:flex; gap:12px; flex-wrap:wrap; align-items:center;
    background: var(--surface-1); border:1px solid var(--border); border-radius:8px;
    padding:7px 13px; margin:8px 0 14px; font-family:var(--mono); font-size:.72rem;
}
.ctxbar .k { color:var(--dim); text-transform:uppercase; letter-spacing:.1em; font-size:.6rem; }
.ctxbar .v { color:#bcd0e2; }
.ctxbar .sep { color:#2a3a4e; }

/* ---------- metric overrides (flat, dense) ---------- */
[data-testid="stMetric"] {
    background: var(--surface-1); border:1px solid var(--border); border-radius:10px;
    padding:12px 14px; box-shadow: inset 0 1px 0 rgba(148,163,184,.05);
}
[data-testid="stMetric"]:hover { border-color: var(--accent-dim); }
[data-testid="stMetricLabel"] { color: var(--dim); font-size:.66rem; letter-spacing:.1em; text-transform:uppercase; }
[data-testid="stMetricValue"] { color: var(--text); font-family:var(--mono); font-weight:700; }

.metric-card {
    background: var(--surface-1); border:1px solid var(--border); border-radius:10px;
    padding:13px 15px; box-shadow: inset 0 1px 0 rgba(148,163,184,.04);
}
.metric-card b { color:var(--text); font-size:.86rem; }

/* generic framed surface (home cards / judges panel) */
.glass { background:var(--surface-1); border:1px solid var(--border); border-radius:12px; }

/* detection-quality grid (reused by dashboard) */
.metric-grid { display:grid; grid-template-columns: repeat(6,1fr); gap:10px;
    padding:14px 16px; margin-bottom:8px; background:var(--surface-1); border:1px solid var(--border); border-radius:10px; }
.mq { display:flex; flex-direction:column; gap:3px; }
.mq .mile { font-size:.58rem; text-transform:uppercase; letter-spacing:.1em; color:var(--dim); }
.mq .miv { font-family:var(--mono); font-weight:700; font-size:1.1rem; }
.mq .miv.g { color:var(--green); } .mq .miv.c { color:var(--accent); }
.mq .miv.v { color:#a78bfa; } .mq .miv.r { color:#f87171; }
.mq .miv.o { color:var(--amber); } .mq .miv.b { color:#60a5fa; }

/* ---------- feeds ---------- */
.feed-window { width:100%; max-width:640px; }
.feed-row { display:grid; grid-template-columns: 52px 1fr 84px 72px; gap:12px;
    align-items:center; padding:6px 0; border-bottom:1px dashed rgba(148,163,184,.10);
    font-size:.78rem; }
.feed-row .fw { font-family:var(--mono); color:var(--dim); }
.feed-row .fam { font-family:var(--mono); color:var(--text); }
.feed-row .risk { font-family:var(--mono); color:var(--amber); text-align:right; }
.feed-row .truth { font-family:var(--mono); text-align:right; text-transform:uppercase;
    font-size:.62rem; letter-spacing:.05em; }

/* incident rows */
.incident-window { max-width:820px; overflow:hidden; }
.incident-row { display:grid; grid-template-columns: 42px 1fr 1fr 1.5fr 84px 60px; gap:14px;
    align-items:center; padding:8px 14px; background:var(--surface-1); }
.incident-row:not(:last-child) { border-bottom:1px dashed rgba(148,163,184,.10); }
.incident-row .iid { width:22px; height:22px; border-radius:50%; display:flex; align-items:center;
    justify-content:center; font-family:var(--mono); font-weight:700; font-size:.62rem;
    color:#04131a; background:var(--accent); }
.incident-row .iwin { font-family:var(--mono); color:#b9c9da; font-size:.78rem; white-space:nowrap; }
.incident-row .iwin b { color:#f87171; }
.incident-row .ifam { font-family:var(--mono); text-transform:uppercase; font-size:.66rem;
    letter-spacing:.06em; color:var(--accent); }
.incident-row .istage { font-size:.7rem; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.incident-row .ipri { font-family:var(--mono); font-size:.58rem; letter-spacing:.08em;
    padding:2px 8px; border-radius:4px; text-align:center; text-transform:uppercase; }
.incident-row .ipri.pri-critical { color:#fecaca; background:rgba(239,68,68,.14); border:1px solid rgba(239,68,68,.4); }
.incident-row .ipri.pri-high { color:#fed7aa; background:rgba(245,158,11,.12); border:1px solid rgba(245,158,11,.38); }
.incident-row .ipri.pri-medium { color:#fde68a; background:rgba(250,204,21,.10); border:1px solid rgba(250,204,21,.32); }
.incident-row .ipri.pri-low { color:#a7f3d0; background:rgba(52,211,153,.10); border:1px solid rgba(52,211,153,.32); }
.incident-row .ipeak { font-family:var(--mono); font-weight:700; color:var(--amber); text-align:right; }

/* ---------- kill chain ---------- */
.killchain { display:flex; align-items:center; flex-wrap:nowrap; overflow-x:auto;
    gap:2px; padding-bottom:4px; }
.killchain .kn { flex:none; font-size:.64rem; letter-spacing:.05em; padding:5px 9px;
    border-radius:6px; border:1px solid var(--border-hi); color:#6f7f92; white-space:nowrap; }
.killchain .kn-done { color:#5a6a7c; background:rgba(20,28,40,.6); }
.killchain .kn-cur { color:#03141a; font-weight:700; border-color:var(--accent);
    background:var(--accent); box-shadow:0 0 14px rgba(34,211,238,.35); }
.killchain .kchev { color:var(--accent); font-size:.9rem; flex:none; padding:0 2px; }

/* ---------- pipeline (thin, operational) ---------- */
.pipeline { position:relative; display:grid; grid-template-columns: repeat(5,1fr); gap:26px; margin:14px 0 8px; }
.pipe-node { position:relative; text-align:center; padding:22px 12px 18px;
    background:linear-gradient(180deg, rgba(148,163,184,.05), transparent 65%), var(--surface-1);
    border:1px solid var(--border); border-radius:12px;
    box-shadow: 0 16px 32px -20px rgba(0,0,0,.65);
    transition: transform .18s ease, border-color .18s ease; }
.pipe-node:hover { transform:translateY(-3px); border-color:var(--border-hi); }
.pipe-node .stage { position:absolute; top:10px; right:12px; font-family:var(--mono);
    font-size:.56rem; letter-spacing:.14em; color:#42536e; }
.pipe-node .ico { width:46px; height:46px; margin:0 auto 12px; border-radius:12px;
    display:flex; align-items:center; justify-content:center; font-size:1.25rem;
    background: linear-gradient(160deg, rgba(34,211,238,.14), rgba(14,30,50,.4));
    border:1px solid rgba(34,211,238,.32); color:#bff3fb;
    transition: box-shadow .2s ease; }
.pipe-node:hover .ico { box-shadow:0 0 18px -2px rgba(34,211,238,.45); }
.pipe-node .ico.i2 { background:linear-gradient(160deg, rgba(245,158,11,.14), rgba(30,20,6,.4));
    border-color:rgba(245,158,11,.3); color:#fde68a; }
.pipe-node:hover .ico.i2 { box-shadow:0 0 18px -2px rgba(245,158,11,.4); }
.pipe-node .ico.i3 { background:linear-gradient(160deg, rgba(167,139,250,.14), rgba(26,18,44,.4));
    border-color:rgba(167,139,250,.32); color:#ddd6fe; }
.pipe-node:hover .ico.i3 { box-shadow:0 0 18px -2px rgba(167,139,250,.45); }
.pipe-node .ico.i4 { background:linear-gradient(160deg, rgba(52,211,153,.13), rgba(10,28,22,.4));
    border-color:rgba(52,211,153,.3); color:#a7f3d0; }
.pipe-node:hover .ico.i4 { box-shadow:0 0 18px -2px rgba(52,211,153,.4); }
.pipe-node .name { font-weight:700; font-size:.88rem; letter-spacing:.05em; color:#e7eef7; }
.pipe-node .det { color:var(--dim); font-size:.66rem; margin-top:5px; line-height:1.5; font-family:var(--mono); }
.pipe-node .tag { display:inline-flex; align-items:center; gap:6px; margin-top:10px;
    font-family:var(--mono); font-size:.6rem; letter-spacing:.12em; color:#67e8f9;
    background:rgba(7,15,30,.6); border:1px solid rgba(34,211,238,.22); padding:3px 8px; border-radius:999px; }
.pipe-node .tag i { width:5px; height:5px; border-radius:50%; background:var(--green); animation: blink 1.6s steps(2,start) infinite; }
@keyframes blink { to { visibility:hidden; } }
.pipe-link { position:absolute; top:44px; height:1px;
    background: linear-gradient(90deg, rgba(34,211,238,.12), rgba(34,211,238,.42) 55%, rgba(34,211,238,.1));
    z-index:0; }
.pipe-link::before { content:""; position:absolute; top:50%; right:0; width:8px; height:8px;
    margin-top:-4px; background:#67e8f9; clip-path: polygon(100% 50%, 0 0, 0 100%); }
.pipe-link::after { content:""; position:absolute; top:50%; left:0; width:14px; height:14px; margin-top:-7px;
    border-radius:50%; background:radial-gradient(circle, #e0f2fe 0%, rgba(103,232,249,.4) 40%, transparent 70%);
    animation:dataFlow 1.5s linear infinite; }
@keyframes dataFlow { from { left:0; opacity:.9;} to { left:100%; opacity:0;} }

/* ---------- feature grid / journey ---------- */
.feat-grid { display:grid; grid-template-columns: repeat(3,1fr); gap:18px; position:relative; }
.journey { display:grid; grid-template-columns: repeat(3,1fr); gap:16px; position:relative; }
.jcard { text-align:center; padding:24px 18px 20px; background:
    linear-gradient(180deg, rgba(148,163,184,.04), transparent 60%), var(--surface-1);
    border:1px solid var(--border); border-radius:14px;
    box-shadow:0 16px 34px -22px rgba(0,0,0,.65); transition: transform .18s ease, border-color .18s ease; }
.jcard:hover { transform: translateY(-3px); border-color: var(--border-hi); }
.jnum { width:40px; height:40px; margin:0 auto 12px; border-radius:10px; display:flex; align-items:center;
    justify-content:center; font-family:var(--mono); font-weight:700; font-size:1rem; color:#04131a;
    background:var(--accent); box-shadow:0 0 16px rgba(34,211,238,.25); }
.ficon { width:46px; height:46px; margin:0 0 12px; border-radius:12px; position:relative;
    display:flex; align-items:center; justify-content:center; font-size:1.25rem;
    background: linear-gradient(160deg, rgba(34,211,238,.12), rgba(14,30,50,.4));
    border:1px solid rgba(34,211,238,.3); color:#bff3fb; transition: box-shadow .2s ease; }
.ficon.green { color:var(--green); border-color:rgba(52,211,153,.32); background:linear-gradient(160deg, rgba(52,211,153,.12), rgba(10,28,22,.4)); }
.ficon.violet { color:#a78bfa; border-color:rgba(167,139,250,.32); background:linear-gradient(160deg, rgba(167,139,250,.12), rgba(26,18,44,.4)); }
.glass.hover:hover { border-color: var(--border-hi); box-shadow: 0 16px 38px -20px rgba(34,211,238,.28); transform: translateY(-2px); }

/* ---------- system console ---------- */
.terminal { border-radius:10px; overflow:hidden; border:1px solid var(--border);
    background: linear-gradient(180deg,#0a0d14, #07090d); }
.term-bar { display:flex; align-items:center; gap:8px; padding:8px 13px;
    background: var(--surface-2); border-bottom:1px solid var(--border);
    font-family:var(--mono); font-size:.64rem; color:var(--dim); letter-spacing:.12em; }
.term-bar .tb { width:9px; height:9px; border-radius:50%; }
.term-bar .tb.r { background:#b91c1c; } .term-bar .tb.y { background:#a16207; }
.term-bar .tb.g { background:#059669; }
.term-title { margin-left:8px; font-weight:600; color:#7dd3fc; }
.term-body { padding:12px 16px 16px; font-family:var(--mono); font-size:.72rem; line-height:1.8; }
.tline { white-space:pre-wrap; word-break:break-word; }
.tline .t { color:#45546a; margin-right:10px; }
.tline .tok { color:var(--green); } .tline .tokw { color:var(--amber); }
.tline .tokr { color:var(--red); } .tline .tokb { color:#7dd3fc; } .tline .toki { color:#a78bfa; }
.cursor { display:inline-block; width:7px; height:12px; background:#7dd3fc;
    vertical-align:-2px; animation: caret 1s steps(2,start) infinite; }
@keyframes caret { 50%{ opacity:0; } }

/* event-level console column for the event console */
.con { font-family:var(--mono); }
.con .cl { display:flex; gap:14px; padding:3px 0; font-size:.72rem; }
.con .cl .tl { color:#45546a; width:74px; flex:none; }
.con .cl .lv { width:64px; flex:none; letter-spacing:.1em; font-size:.62rem; padding-top:2px; }
.con .cl .lv-sys { color:#7dd3fc; } .con .cl .lv-fc { color:#67e8f9; }
.con .cl .lv-al { color:var(--red); } .con .cl .lv-xai { color:var(--amber); }
.con .cl .lv-mt { color:#a78bfa; } .con .cl .lv-au { color:var(--green); }
.con .cl .msg { color:#8fa3b5; } .con .cl .msg b { color:#d7e5f2; font-weight:600; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #07090d, #05070a);
    border-right:1px solid var(--border);
}
[data-testid="stSidebar"] .block-container { padding-top: 64px; }
[data-testid="stSidebarNav"] li a { border-radius:6px; font-size:.82rem; font-weight:500;
    color:var(--muted); padding:.42rem .7rem; transition:.12s ease; }
[data-testid="stSidebarNav"] li a:hover { background:rgba(34,211,238,.06); color:var(--text); }
[data-testid="stSidebarNav"] li a[aria-current="page"] {
    color:var(--accent); background:rgba(34,211,238,.08);
    border-left:2px solid var(--accent); padding-left:calc(.7rem - 2px);
}
.sb-brand { display:flex; align-items:center; gap:10px; padding:2px 2px 8px; }
.sb-mark { position:relative; width:30px; height:30px; border-radius:8px; flex:none;
    display:grid; place-items:center; background:linear-gradient(135deg,#0e7490,#0b1017);
    border:1px solid rgba(34,211,238,.5); }
.sb-mark::after { content:""; position:absolute; inset:4px; border-radius:5px;
    border:1px dashed rgba(103,232,249,.5); animation: spin 12s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.sb-mark span { color:#67e8f9; font-size:1rem; font-weight:800; }
.sb-t { line-height:1.2; }
.sb-t b { color:#d7e5f2; font-size:.88rem; letter-spacing:.18em; display:block; }
.sb-t i { font-style:normal; color:#46546a; font-size:.58rem; letter-spacing:.22em; text-transform:uppercase; }

.sb-status { padding:6px 12px; border:1px solid var(--border); border-radius:8px;
    background:var(--surface-1); font-family:var(--mono); }
.sb-status .sb-row { font-size:.66rem; }
.sb-status .k { color:#46546a; letter-spacing:.1em; font-size:.56rem; text-transform:uppercase; }
.sb-status .v { color:#aec2d4; font-weight:600; float:right; }
.sb-status .v.g { color:var(--green); }
.sb-status .v.c { color:var(--accent); }

/* ---------- tabs -> workflow rail ---------- */
.stTabs [data-baseweb="tab-list"] { gap:2px; border-bottom:1px solid var(--border); }
.stTabs [data-baseweb="tab"] {
    background:transparent; border-radius:0; padding:.5rem 1rem; color:var(--muted);
    font-weight:600; font-size:.78rem; letter-spacing:.06em; text-transform:uppercase;
    border-bottom:2px solid transparent; transition:.12s ease;
}
.stTabs [data-baseweb="tab"]:hover { color:var(--text); }
.stTabs [aria-selected="true"] {
    color:var(--accent) !important; border-bottom:2px solid var(--accent);
    background:rgba(34,211,238,.05);
}

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button {
    border-radius:7px; font-weight:600; border:1px solid var(--border-hi);
    background:var(--surface-2); color:var(--text); font-size:.8rem; transition:.12s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color:var(--accent-dim); background:var(--surface-3); color:#fff;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background:linear-gradient(90deg,#0e7490,#155e75); border:1px solid rgba(34,211,238,.35);
    color:#eefcfe; box-shadow: 0 4px 14px -8px rgba(34,211,238,.5);
}
.stButton > button[kind="primary"]:hover { filter:brightness(1.12); }

/* ---------- inputs ---------- */
[data-testid="stSlider"] [data-baseweb="slider"] > div > div > div { color:var(--accent); background:var(--accent); }
[data-testid="stRadio"] label, [data-testid="stSelectbox"] label,
[data-testid="stNumberInput"] label, [data-testid="stToggle"] label { color:var(--muted); font-size:.8rem; }

/* ---------- expander ---------- */
[data-testid="stExpander"] { border:1px solid var(--border); border-radius:8px;
    background:var(--surface-1); }
[data-testid="stExpander"]:hover { border-color: var(--border-hi); }
[data-testid="stExpander"] [data-testid="stExpanderDetails"] { border-top:1px solid var(--border); }

/* ---------- iframe (home globe) ---------- */
[data-testid="stIFrame"] { margin-top:4px; animation: fadeUp .5s ease backwards; }

/* ---------- dataframes / code ---------- */
[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:8px; overflow:hidden; }
pre, code, [class*="codeCell"] { font-family:var(--mono); font-size:.72rem !important; }

/* ---------- network activity map (command) ---------- */
.netwrap { background:var(--surface-1); border:1px solid var(--border); border-radius:10px;
    padding:10px 12px 8px; position:relative; }
.netwrap .net-label { font-family:var(--mono); font-size:.58rem; letter-spacing:.16em;
    color:var(--dim); text-transform:uppercase; padding:2px 2px 6px; display:flex; justify-content:space-between; }
.netwrap svg text { font-family:var(--mono); }
.netnode { animation: fadeUp .5s ease backwards; }
.netcore { filter: drop-shadow(0 0 6px rgba(34,211,238,.5)); }
.netedge { stroke-dasharray:2 3; animation: dashmove 6s linear infinite; }
@keyframes dashmove { to { stroke-dashoffset:-20; } }

/* ---------- globe placeholder radar (home) ---------- */
.radar { position:relative; width:236px; height:236px; margin:14px auto 16px;
    border-radius:50%; border:1px solid rgba(34,211,238,.28); overflow:hidden;
    background: radial-gradient(circle at 50% 50%, rgba(34,211,238,.10), rgba(6,10,20,.55) 72%); }
.radar::before { content:""; position:absolute; inset:0; border-radius:50%;
    background: conic-gradient(from 0deg, rgba(34,211,238,.40), transparent 24%);
    animation: radarSpin 3.4s linear infinite; }
.radar .ring { position:absolute; border-radius:50%; border:1px solid rgba(34,211,238,.16); }
.radar .ring.r1 { inset:20px; } .radar .ring.r2 { inset:54px; opacity:.8; }
.radar .ring.r3 { inset:88px; opacity:.6; }
.radar .hub { position:absolute; left:50%; top:50%; width:10px; height:10px; margin:-5px 0 0 -5px;
    border-radius:50%; background:#22d3ee; box-shadow:0 0 0 0 rgba(34,211,238,.5);
    animation: radarPing 2s ease-out infinite; }
.radar .blip { position:absolute; width:6px; height:6px; border-radius:50%;
    box-shadow:0 0 6px 1px currentColor; animation: blink 2.4s steps(2,start) infinite; }
@keyframes radarSpin { to { transform:rotate(360deg); } }
@keyframes radarPing { 0% { box-shadow:0 0 0 0 rgba(34,211,238,.45);} 100% { box-shadow:0 0 0 28px rgba(34,211,238,0);} }

/* ---------- live/offline mode pill ---------- */
.modepill { display:inline-flex; align-items:center; gap:7px; padding:2px 10px; border-radius:4px;
    font-family:var(--mono); font-size:.62rem; letter-spacing:.14em; font-weight:700; text-transform:uppercase;
    border:1px solid var(--border-hi); }
.modepill i { width:6px; height:6px; border-radius:50%; }
.modepill.live { color:#67e8f9; border-color:rgba(34,211,238,.45); background:rgba(34,211,238,.08); }
.modepill.live i { background:var(--red); animation: pulseDot 1.4s ease-in-out infinite; }
.modepill.replay { color:#fcd34d; border-color:rgba(245,158,11,.4); background:rgba(245,158,11,.08); }
.modepill.replay i { background:var(--amber); }
.modepill.idle { color:#8494a6; }
.modepill.idle i { background:#8494a6; }

/* ---------- event workflow timeline (command) ---------- */
.evflow { display:flex; align-items:center; gap:0; overflow-x:auto; padding:10px 4px 6px; }
.evflow .ef { flex:none; display:flex; align-items:center; gap:0; }
.evflow .efstep { padding:7px 14px; border:1px solid var(--border); border-radius:7px;
    background:var(--surface-1); font-family:var(--mono); font-size:.64rem; letter-spacing:.1em;
    color:var(--dim); text-transform:uppercase; white-space:nowrap; }
.evflow .efstep.ef-done { color:#7fd8e8; border-color:rgba(34,211,238,.3); }
.evflow .efstep.ef-cur { color:#04131a; font-weight:700; background:var(--accent);
    border-color:var(--accent); box-shadow:0 0 16px rgba(34,211,238,.35); }
.evflow .efstep.ef-pend { opacity:.55; }
.evflow .efarrow { color:var(--accent); font-size:.9rem; padding:0 7px; flex:none; }

/* ---------- threat/incident queues (command) ---------- */
.queue { background:var(--surface-1); border:1px solid var(--border); border-radius:10px; overflow:hidden; }
.queue .qhead { display:flex; align-items:center; justify-content:space-between;
    padding:8px 14px; border-bottom:1px solid var(--border);
    font-family:var(--mono); font-size:.6rem; letter-spacing:.16em; color:var(--dim); text-transform:uppercase; }
.queue .qhead b { color:#9fb4c8; letter-spacing:.12em; }
.queue .qrow { display:grid; grid-template-columns: 1fr auto auto; gap:10px; align-items:center;
    padding:8px 14px; border-bottom:1px dashed rgba(148,163,184,.08); font-size:.76rem; }
.queue .qrow:last-child { border-bottom:none; }
.queue .qrow .qid { font-family:var(--mono); color:#9fb4c8; }
.queue .qrow .qid b { color:#d7e5f2; font-weight:600; }
.queue .qrow .qfam { font-family:var(--mono); font-size:.64rem; text-transform:uppercase;
    letter-spacing:.05em; color:var(--text); }
.queue .qrisk { font-family:var(--mono); font-weight:700; color:var(--text); text-align:right; }
.queue .qdrv { color:var(--dim); font-size:.64rem; font-family:var(--mono); }

/* ---------- telemetry (command) ---------- */
.telem { display:grid; grid-template-columns: repeat(5,1fr); gap:0; margin:0 0 14px;
    border:1px solid var(--border); border-radius:10px; background:var(--surface-1); overflow:hidden; }
.telem .tm { padding:14px 16px; border-right:1px solid var(--border); position:relative; }
.telem .tm:last-child { border-right:none; }
.telem .tm .ev { font-family:var(--mono); font-size:.66rem; letter-spacing:.08em;
    color:var(--dim); text-transform:uppercase; display:flex; align-items:center; gap:7px; }
.telem .tm .ev i { width:6px; height:6px; border-radius:50%; }
.telem .tm .ev i.t-r { background:var(--red); box-shadow:0 0 6px rgba(239,68,68,.5); }
.telem .tm .ev i.t-a { background:var(--amber); }
.telem .tm .ev i.t-g { background:var(--green); }
.telem .tm .ev i.t-b { background:var(--accent); }
.telem .tm .num { font-family:var(--mono); font-weight:700; font-size:1.55rem; color:var(--text); margin-top:4px; letter-spacing:-.01em; }
.telem .tm .num.re { color:#f87171; } .telem .tm .num.am { color:var(--amber); }
.telem .tm .num.gd { color:var(--green); } .telem .tm .num.cy { color:var(--accent); }

/* ---------- investigation / war room ---------- */
.inv-head { display:flex; align-items:center; gap:16px; padding:16px 18px;
    background:var(--surface-1); border:1px solid var(--border); border-left:3px solid var(--accent);
    border-radius:10px; margin-bottom:12px; }
.inv-head .tag { font-family:var(--mono); font-size:.62rem; letter-spacing:.14em;
    color:var(--dim); text-transform:uppercase; }
.inv-head .ttl { font-size:1.05rem; font-weight:700; color:var(--text); }
.attrbar { display:flex; align-items:center; gap:12px; }
.attrbar .ab-label { width:160px; font-family:var(--mono); font-size:.68rem; color:var(--muted);
    text-transform:uppercase; letter-spacing:.06em; }
.attrbar .ab-track { flex:1; height:6px; border-radius:3px; background:#10161f; overflow:hidden; }
.attrbar .ab-fill { height:100%; border-radius:3px; }
.attrbar .ab-val { width:52px; font-family:var(--mono); font-size:.7rem; color:var(--text); text-align:right; }

/* ---------- export console (reports) ---------- */
.exp-console { border:1px solid var(--border); border-radius:10px; overflow:hidden; }
.ec-row { display:flex; align-items:center; justify-content:space-between;
    padding:12px 16px; border-bottom:1px dashed rgba(148,163,184,.10); }
.ec-row:last-child { border-bottom:none; }
.ec-row .ec-name { font-size:.84rem; color:var(--text); font-weight:600; }
.ec-row .ec-name small { display:block; color:var(--dim); font-weight:400; font-size:.7rem; margin-top:2px; }
.ec-row .ec-file { font-family:var(--mono); font-size:.66rem; color:var(--dim); }
.ec-actions { display:flex; gap:8px; align-items:center; }

/* ---------- judges panel ---------- */
.jpanel { padding:0; }
.jpanel .jp-head { text-align:center; margin-bottom:24px; }
.jpanel .jp-head h2 { font-size:.9rem; letter-spacing:.24em; color:#d7e5f2; text-transform:uppercase; margin:0 0 4px; }
.jpanel .jp-head p { color:var(--dim); font-size:.7rem; letter-spacing:.08em; margin:0; }
.jpanel .jp-grid { display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-bottom:18px; }
.jpanel .jp-card { background:var(--surface-1); border:1px solid var(--border); border-radius:10px;
    padding:14px 14px; }
.jpanel .jp-card .jp-val { font-family:var(--mono); font-weight:700; font-size:1.5rem; color:var(--text); margin-bottom:3px; }
.jpanel .jp-card .jp-label { font-size:.58rem; text-transform:uppercase; letter-spacing:.1em; color:var(--dim); }
.jpanel .jp-card .jp-sub { font-size:.64rem; color:#5b6a7c; margin-top:5px; line-height:1.45; }
.jpanel .jp-rows { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin-bottom:18px; }
.jpanel .jp-row { display:flex; align-items:flex-start; gap:12px; padding:12px 14px;
    background:var(--surface-1); border:1px solid var(--border); border-radius:10px; }
.jpanel .jp-row .jpr-icon { flex:none; width:30px; height:30px; border-radius:8px;
    display:flex; align-items:center; justify-content:center; font-size:.95rem; background:rgba(34,211,238,.08); }
.jpanel .jp-row .jpr-text b { display:block; font-size:.78rem; color:var(--text); margin-bottom:2px; }
.jpanel .jp-row .jpr-text span { font-size:.7rem; color:var(--dim); line-height:1.5; }
.jpanel .jp-honest { padding:12px 16px; border:1px solid rgba(245,158,11,.3); border-radius:10px;
    background:rgba(245,158,11,.04); }
.jpanel .jp-honest b { color:var(--amber); font-size:.72rem; }
.jpanel .jp-honest span { color:var(--muted); font-size:.7rem; line-height:1.55; display:block; margin-top:3px; }

/* ---------- animations ---------- */
@keyframes fadeUp { from { opacity:0; transform: translateY(6px);} to { opacity:1; transform:none;} }
.fadeup { animation: fadeUp .4s ease backwards; }
.anim-in { animation: fadeUp .5s cubic-bezier(.16,.84,.44,1) backwards; }
.d1 { animation-delay:.05s } .d2 { animation-delay:.10s } .d3 { animation-delay:.15s }
.d4 { animation-delay:.20s } .d5 { animation-delay:.25s } .d6 { animation-delay:.30s }
.levitate { animation: fadeUp .6s ease backwards; }

/* ---------- scrollbars / selection ---------- */
::-webkit-scrollbar { width:9px; height:9px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#1a2434; border-radius:5px; }
::-webkit-scrollbar-thumb:hover { background:#22304a; }
::selection { background:rgba(34,211,238,.4); color:#03141a; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# COMMAND SHELL — top bar + quiet ambient layer
# ============================================================

st.markdown(
    """
<div class="topbar">
  <div class="tb-brand">
    <span class="tb-name">NET<b>SIGHT</b></span>
    <span class="tb-sub">Threat Command Center</span>
  </div>
  <div class="tb-right">
    <span class="syschip ok"><i></i> System operational · offline analytics</span>
    <span class="syschip">SYS // REAL-TIME</span>
    <span class="syschip">BUILD // 1.0</span>
    <span class="syschip">ENGINE // <b>RF · LSTM</b></span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

_particles = "".join(
    f"<i class='fdot' style='left:{pct:.1f}%;width:{2+(i%4)*.3:.1f}px;"
    f"height:{2+(i%4)*.3:.1f}px;animation-duration:{14+(i%6)*3:.1f}s;"
    f"animation-delay:{-i*1.4:.1f}s;--drift:{(i%7-3)*12}px'></i>"
    for i, pct in enumerate([(i * 61.8 + 17.7) % 100 for i in range(18)])
)

_ticker_entries = [
    ("forecast", "risk timeline updated · 358 alert windows"),
    ("incident", "2 correlated · 1 CRITICAL (357w DDoS)"),
    ("mitre", "Impact stage (TA0040) active"),
    ("ledger", "sealed block · SHA-256"),
    ("xai", "top driver attributed per window"),
    ("novelty", "callout advisory · analyst review"),
    ("engine", "RandomForest @ 76-dim rolling"),
    ("telemetry", "CICIDS2017 · offline"),
]


def _live_ticker_entries():
    """Real-run telemetry where available; classic static entries otherwise."""
    entries = []
    det = st.session_state.get("det_metrics")
    if isinstance(det, dict) and det.get("windows_evaluated"):
        entries.append(("forecast", f"risk timeline · {int(det['windows_evaluated'])} windows evaluated"))
    else:
        entries.append(("forecast", "risk timeline updated · 452-window demo ready"))

    inc = st.session_state.get("incident_export")
    try:
        incidents = json.loads(inc) if isinstance(inc, str) else None
    except Exception:
        incidents = None
    if isinstance(incidents, (list, tuple)) and incidents:
        peak = max((float(i.get("severity", 0)) for i in incidents), default=0.0)
        entries.append(("incident", f"{len(incidents)} correlated · peak severity {peak:.3f}"))
        entries.append(("ledger", "sealed block · SHA-256 · audit trail"))
    else:
        entries.append(("incident", "2 correlated · 1 CRITICAL (357w DDoS) · demo"))
        entries.append(("ledger", "sealed block · SHA-256"))

    entries.append(("mitre", "Impact stage (TA0040) active"))
    entries.append(("xai", "top driver attributed per window"))
    entries.append(("novelty", "callout advisory · analyst review"))
    entries.append(("engine", "RandomForest @ 76-dim rolling"))

    src = st.session_state.get("_live_source") or st.session_state.get("src_ingest")
    entries.append(("telemetry", f"{src} · offline" if src else "CICIDS2017 · offline"))
    return entries

st.markdown(
    f"""
<div id="bgfx" aria-hidden="true">{_particles}</div>
<div id="soc-ticker" aria-hidden="true">
  <div class="tk-label"><i></i>NETSIGHT</div>
  <div class="tk-track"><div class="tk-inner">
    {''.join(f'<span><em>[{k}]</em> {d} <b>·</b> </span>' for k, d in _live_ticker_entries())}
    {''.join(f'<span><em>[{k}]</em> {d} <b>·</b> </span>' for k, d in _live_ticker_entries())}
  </div></div>
</div>
""",
    unsafe_allow_html=True,
)

pg = st.navigation([
    st.Page("home.py", title="Home", icon="🏠", default=True),
    st.Page("dashboard.py", title="SOC Command Center", icon="🛡"),
])
pg.run()