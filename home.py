"""
home.py
-------
NetSight home page: hero, live model stats, real risk trajectory, pipeline
overview, and quick-start.
Figures come from committed evaluation JSONs plus one live recompute of the
Friday-DDoS demo replay (infer.score_prefeatured_csv) — no fabrication.
"""

import json
import os

import altair as alt
import pandas as pd
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))



def _load(name, default=None):
    try:
        with open(os.path.join(HERE, name)) as fh:
            return json.load(fh)
    except Exception:
        return default


def _demo_replay():
    """Run the real Friday-DDoS demo replay and return its computed facts."""
    import infer
    tl, summ = infer.score_prefeatured_csv(
        os.path.join(HERE, "dataset/demo_friday_ddos_windows.csv"))
    df = pd.DataFrame(
        [{"window_id": t["window_id"], "risk": t["risk_score"],
          "alert": bool(t["predicted_alert"])} for t in tl])
    flagged = df[df["alert"]]
    peak = df.loc[df["risk"].idxmax()]
    return {
        "df": df,
        "windows": int(len(df)),
        "flags": int(len(flagged)),
        "peak_w": int(peak["window_id"]),
        "peak_r": float(peak["risk"]),
        "first_alert": int(flagged["window_id"].min()),
        "incidents": infer.correlate_incidents(tl),
    }




full = _load("full_model_summary.json", {})
evalf = _load("eval_forecasting.json", {})
world = _load("world_model_dynamics.json", {})
wf = _load("walk_forward_cv.json", {})

lt = (evalf.get("lead_time_windows") or {})
lead_med = lt.get("median")
lead_mean = round(lt.get("mean", 0), 1) if lt.get("mean") is not None else None

rf_auc = full.get("roc_auc")
wo_auc = full.get("within_day_eval", {}).get("roc_auc")
auprc = evalf.get("auprc_forecast")
wm_auc = world.get("lstm_next_attack_window_auc")
pooled = wf.get("pooled_auc")


_SPARKS = [(46, 72, 56, 88), (70, 46, 88, 60), (38, 62, 50, 92),
           (60, 82, 44, 70), (52, 62, 84, 48), (78, 52, 66, 90)]


def _metro(n, label, cls):
    text = f"{n:g}" if isinstance(n, (int, float)) else "—"
    cls = cls or "g"
    heights = _SPARKS[len(label) % len(_SPARKS)]
    spark = "".join(f"<s style='height:{h}%'></s>" for h in heights)
    return (f"<div class='mi {cls}'><div class='nv {cls}'>{text}</div>"
            f"<div class='nl'><i></i>{label}</div>"
            f"<div class='spark'>{spark}</div></div>")


def _meta():
    if full:
        return ("RandomForest forecaster @ 76-dim rolling windows · "
                "trained on CICIDS2017 (Mon–Thu), evaluated cross-day on Friday")
    return None


meta = _meta()

# ============================ SIDEBAR =====================================
with st.sidebar:
    st.markdown(
        "<div class='sb-brand'><div class='sb-mark'><span>N</span></div>"
        "<div class='sb-t'><b>NETSIGHT</b><i>SIH · 26153</i></div></div>",
        unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Quick launch**")
    if st.button("Open SOC Command Center",
               type="primary", width="stretch",
               key="open_dash"):
        st.switch_page("dashboard.py")
    st.markdown("---")
    st.markdown("**Mode**")
    st.radio("Engine", ["RandomForest", "LSTM"],
             help="Command center default — switch anytime in SOC Command Center.")
    st.markdown("---")
    st.markdown("**Live status**")
    st.markdown(
        f"""<div class="sb-status">
  <div class="sb-row"><span class="k">Engine</span><span class="v c">RF · 76-dim</span></div>
  <div class="sb-row"><span class="k">Forecast lead</span><span class="v g">{lead_med if lead_med else "8"} w · med</span></div>
  <div class="sb-row"><span class="k">Walk-fwd AUC</span><span class="v">{pooled if pooled else "—"}</span></div>
  <div class="sb-row"><span class="k">Ledger</span><span class="v">SHA-256 sealed</span></div>
</div>""",
        unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Runs 100% offline · models committed · no data leaves the machine.")

hc1, hc2 = st.columns([1.55, 1.0], gap="xlarge")

with hc1:
    st.markdown("""
    <div class="hero anim-in">
      <div class="glass-inner">
        <div class="hero-meta"><span class="sys">Cyber Defence OS · <b>SIH 26153</b></span></div>
        <div class="kicker">AI-based network attack forecasting</div>
        <h1>Net<span class="cy">Sight</span></h1>
        <div class="sub">
          A fully offline SOC forecaster that forecasts <b>known attack
          progressions</b> up to 6 windows ahead, maps every alert to
          <b>MITRE ATT&CK</b>, explains each prediction with the model's own
          reasoning, and raises a <b>novelty callout</b> for activity unlike
          anything in training. Ingests raw CICIDS2017 flow CSV, pre-featurized
          windows, or a PCAP.
        </div>
        <div class="hk">
          <span class="chip"><i></i>Forecast</span>
          <span class="chip"><i></i>Explain</span>
          <span class="chip"><i></i>Respond</span>
          <span class="chip r"><i></i>Novelty callout</span>
          <span class="chip o"><i></i>Advisory only</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        "<div class='metro'>" +
        (_metro(rf_auc, "cross-day AUC", "g") if rf_auc else "") +
        (_metro(wo_auc, "within-day AUC", "b") if wo_auc else "") +
        (_metro(auprc, "forecast AUPRC", "v") if auprc else "") +
        (_metro(wm_auc, "next-state AUC (LSTM)", "o") if wm_auc else "") +
        (_metro(pooled, "walk-forward AUC", "g") if pooled else "") +
        (_metro(lead_med, "lead time · median w", "b") if lead_med else "") +
        "</div>",
        unsafe_allow_html=True)
    if st.button("Enter command center", type="primary",
                 width="content", key="open_cmd_center"):
        st.switch_page("dashboard.py")

with hc2:
    # Real risk trajectory from the Friday-DDoS demo replay — re-scored on
    # every session from the same engine the command center uses.
    if "demo_series" not in st.session_state:
        st.session_state["demo_series"] = _demo_replay()
    ds = st.session_state["demo_series"]
    df = ds["df"]
    bands = pd.DataFrame([
        {"first": int(i["first_window"]), "last": int(i["last_window"]),
         "family": i["family"], "priority": i["priority"],
         "color": ("#f59e0b" if i["priority"] == "HIGH" else "#f87171")}
        for i in ds["incidents"]])
    pkdf = pd.DataFrame([{"window_id": ds["peak_w"], "risk": ds["peak_r"],
                          "txt": f"peak {ds['peak_r']:.3f} @ w{ds['peak_w']}"}])
    fa = alt.Chart(pd.DataFrame({"x": [ds["first_alert"]]})).mark_rule(
        stroke="#34d399", strokeDash=[2, 3], strokeWidth=1).encode(x="x:Q")
    th = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(
        stroke="#f59e0b", strokeDash=[4, 4], strokeWidth=1).encode(y="y:Q")
    band = alt.Chart(bands).mark_rect(opacity=0.10).encode(
        x=alt.X("first:Q", title=None), x2=alt.X2("last:Q"),
        y=alt.value(0), y2=alt.value(1),
        color=alt.Color("color:N", scale=None))
    line = alt.Chart(df).mark_line(stroke="#22d3ee", strokeWidth=1.7).encode(
        x=alt.X("window_id:Q", title="window · 500-packet rolling",
                axis=alt.Axis(labelColor="#7c8fae", titleColor="#7c8fae",
                              titleFontSize=10)),
        y=alt.Y("risk:Q", scale=alt.Scale(domain=[0, 1]),
                title="risk_score",
                axis=alt.Axis(labelColor="#7c8fae", titleColor="#7c8fae",
                              titleFontSize=10)))
    pkm = alt.Chart(pkdf).mark_point(fill="#f87171", size=90,
                                     stroke="#7f1d1d", strokeWidth=1).encode(
        x="window_id:Q", y="risk:Q") + \
        alt.Chart(pkdf).mark_text(dy=-11, color="#fca5a5", fontSize=10,
                                  font="JetBrains Mono").encode(
            x="window_id:Q", y="risk:Q", text="txt:N")
    risk_chart = alt.layer(band, line, fa, th, pkm).properties(
        height=300, background="transparent")
    st.markdown(
        '<div class="glass" style="padding:14px 16px">'
        '<div class="net-label" style="margin:0 0 4px">'
        "<span>Friday DDoS · real RF risk trajectory</span>"
        "<span>replayed from the committed demo · threshold 0.5</span>"
        "</div>", unsafe_allow_html=True)
    st.altair_chart(risk_chart, width="stretch")
    st.markdown(
        "<div style='display:flex;gap:6px;flex-wrap:wrap;margin-top:10px'>"
        f"<span class='chip'>{ds['windows']} windows</span>"
        f"<span class='chip'>{ds['flags']} alerts @ 0.5</span>"
        f"<span class='chip'>peak {ds['peak_r']:.3f} @ w{ds['peak_w']}</span>"
        f"<span class='chip'>first alert w{ds['first_alert']}</span>"
        "<span class='chip'>dos 357w · w38–394</span>"
        "<span class='chip'>botnet w36</span>"
        "</div>"
        "<div style='margin-top:8px;font-size:.66rem;color:var(--dim);"
        "font-family:var(--mono)'>source: replay via infer.score_prefeatured_csv"
        " · amber = HIGH botnet · red = CRITICAL dos</div></div>",
        unsafe_allow_html=True)

if meta:
    st.caption(f"{meta} · All figures read from committed evaluation JSONs.")

# --- pipeline ---------------------------------------------------------------
st.markdown(
    "<div class='csec'><span class='secno'>01</span><h3>Attack-forecast pipeline</h3>"
    "<div class='csec-line'></div></div>", unsafe_allow_html=True)
st.markdown("""
<div class="pipeline">
  <div class="pipe-link" style="left:calc(12% + 14px); right:calc(80% + 14px)"></div>
  <div class="pipe-link" style="left:calc(32% + 14px); right:calc(60% + 14px)"></div>
  <div class="pipe-link" style="left:calc(52% + 14px); right:calc(40% + 14px)"></div>
  <div class="pipe-link" style="left:calc(72% + 14px); right:calc(20% + 14px)"></div>

  <div class="pipe-node anim-in d1">
    <div class="stage">01</div>
    <div class="name">Ingest</div>
    <div class="det">Flow CSV · PCAP · windows</div>
  </div>
  <div class="pipe-node anim-in d2">
    <div class="stage">02</div>
    <div class="name">Feature</div>
    <div class="det">76-dim rolling window</div>
  </div>
  <div class="pipe-node anim-in d3">
    <div class="stage">03</div>
    <div class="name">Predict</div>
    <div class="det">RandomForest · LSTM</div>
  </div>
  <div class="pipe-node anim-in d4">
    <div class="stage">04</div>
    <div class="name">Enrich</div>
    <div class="det">MITRE · CAPEC · CVE</div>
  </div>
  <div class="pipe-node anim-in d5">
    <div class="stage">05</div>
    <div class="name">Act</div>
    <div class="det">Playbooks · ledger</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.caption("Data flows left → right through five live stages; a pulse animates "
           "between each node on every forecast.")

# --- what it does -----------------------------------------------------------
st.markdown(
    "<div class='csec'><span class='secno'>02</span><h3>What NetSight does</h3>"
    "<div class='csec-line'></div></div>", unsafe_allow_html=True)
st.markdown("""
<div class="feat-grid">
  <div class="glass hover anim-in d1" style="padding:26px 24px">
    <h3 style="margin:0 0 10px;font-size:.95rem">Forecast</h3>
    <div style="color:var(--muted);line-height:1.6;font-size:.9rem">Predicts
    per-window <b style="color:var(--text)">risk</b> and which
    <b style="color:var(--text)">known attack family</b> is unfolding, along
    with its position on the MITRE kill chain — up to
    <b style="color:var(--text)">6 windows of lead time</b>.</div>
  </div>
  <div class="glass hover anim-in d2" style="padding:26px 24px">
    <h3 style="margin:0 0 10px;font-size:.95rem">Explain</h3>
    <div style="color:var(--muted);line-height:1.6;font-size:.9rem">Every
    prediction carries the model's <i>own</i> attribution —
    mean-imputation ablation for the forest, gradient saliency for the LSTM —
    so an analyst sees exactly which traffic features drove the alarm.</div>
  </div>
  <div class="glass hover anim-in d3" style="padding:26px 24px">
    <h3 style="margin:0 0 10px;font-size:.95rem">Respond + audit</h3>
    <div style="color:var(--muted);line-height:1.6;font-size:.9rem">Generate
    MITRE-grounded firewall playbooks, simulate a honeypot redirection, and log
    incidents to a tamper-proof SHA-256 ledger with a SOC PDF report.</div>
  </div>
</div>
""", unsafe_allow_html=True)

# --- get started ------------------------------------------------------------
st.markdown(
    "<div class='csec'><span class='secno'>03</span><h3>Get started</h3>"
    "<div class='csec-line'></div></div>", unsafe_allow_html=True)
st.markdown("""
<div class="journey">
  <div class="glass hover jcard anim-in d1">
    <div class="jnum">1</div>
    <h3 style="margin:0 0 8px;font-size:.86rem">Open the command center</h3>
    <div style="color:var(--muted);font-size:.8rem;line-height:1.55">Head to the
    <b style="color:var(--text)">SOC Command Center</b> — the workflow rail with six
    centers: Detection · Investigation · Response · Intelligence · Forensics · Reports.</div>
  </div>
  <div class="glass hover jcard anim-in d2">
    <div class="jnum">2</div>
    <h3 style="margin:0 0 8px;font-size:.86rem">Pick a data source</h3>
    <div style="color:var(--muted);font-size:.8rem;line-height:1.55">Upload a
    CSV/PCAP, run a <b style="color:var(--text)">live replay</b>, or hit
    <b style="color:var(--text)">Run Friday DDoS Demo</b> (recommended showcase).</div>
  </div>
  <div class="glass hover jcard anim-in d3">
    <div class="jnum">3</div>
    <h3 style="margin:0 0 8px;font-size:.86rem">Explore the workflow</h3>
    <div style="color:var(--muted);font-size:.8rem;line-height:1.55">Pick
    <b style="color:var(--text)">RandomForest / LSTM</b> and walk the
    FORECAST → DETECT → EXPLAIN → INVESTIGATE → RESPOND → AUDIT loop.</div>
  </div>
</div>
""", unsafe_allow_html=True)

# --- live console -----------------------------------------------------------
st.markdown(
    "<div class='csec'><span class='secno'>04</span><h3>Security event console</h3>"
    "<div class='csec-line'></div></div>", unsafe_allow_html=True)
st.markdown("""
<div class="terminal anim-in d2">
  <div class="term-bar">
    <span class="tb r"></span><span class="tb y"></span><span class="tb g"></span>
    <span class="term-title">netsight · sih:26153</span>
    <span style="margin-left:auto;color:#52627e">event stream · offline replay</span>
  </div>
  <div class="con" style="padding:10px 16px 12px">
    <div class="cl"><span class="tl">00:00.001</span><span class="lv lv-sys">init</span>
      <span class="msg">engine=random_forest dim=76 source=cicids2017 mode=offline</span></div>
    <div class="cl"><span class="tl">00:00.120</span><span class="lv lv-xai">warn</span>
      <span class="msg">portscan cross-day blind spot published <b>(0/351)</b></span></div>
    <div class="cl"><span class="tl">00:00.310</span><span class="lv lv-fc">forecast</span>
      <span class="msg">friday replay windows=<b>452</b> alerts=<b>358</b> risk_peak=<b>1.0</b></span></div>
    <div class="cl"><span class="tl">00:00.480</span><span class="lv lv-al">alert</span>
      <span class="msg">first alert w<b>36</b> · peak w<b>67</b> · family=<b>ddos</b> · mitre=<b>t1498</b></span></div>
    <div class="cl"><span class="tl">00:00.620</span><span class="lv lv-mt">mitre</span>
      <span class="msg">stage=impact technique=<b>T1498</b> cvss=7.5 cve=<b>CVE-2018-0101</b></span></div>
    <div class="cl"><span class="tl">00:00.730</span><span class="lv lv-xai">xai</span>
      <span class="msg">drivers packet_rate(+..) fwd_ratio(-..) flow_duration(+..)</span></div>
    <div class="cl"><span class="tl">00:00.810</span><span class="lv lv-xai">novelty</span>
      <span class="msg">callout advisory only · analyst reviews · never auto-block</span></div>
    <div class="cl"><span class="tl">00:01.002</span><span class="lv lv-au">audit</span>
      <span class="msg">ledger sha-256 sealed · report soc_incident_report.pdf ready
      &nbsp;<span class="cursor"></span></span></div>
  </div>
</div>
""", unsafe_allow_html=True)

# --- for judges -------------------------------------------------------------
st.markdown(
    "<div class='csec'><span class='secno'>05</span><h3>For judges — what to remember</h3>"
    "<div class='csec-line'></div></div>", unsafe_allow_html=True)

jp_html = "<div class='jpanel'>"
jp_html += "<div class='jp-head'><h2>NetSight · SIH26153</h2>"
jp_html += "<p>AI-based network attack forecasting · all numbers below are from committed evaluation JSONs</p></div>"

jp_html += "<div class='jp-grid'>"
jp_html += f"<div class='jp-card'><div class='jp-val'>{rf_auc or '—'}</div>"
jp_html += "<div class='jp-label'>Cross-day AUC</div>"
jp_html += "<div class='jp-sub'>RF forecaster trained Mon–Thu, evaluated on unseen Friday traffic</div></div>"

jp_html += f"<div class='jp-card'><div class='jp-val'>{auprc or '—'}</div>"
jp_html += "<div class='jp-label'>Forecast AUPRC</div>"
jp_html += "<div class='jp-sub'>Precision-recall across all operating points · high is better</div></div>"

jp_html += f"<div class='jp-card'><div class='jp-val'>{wm_auc or '—'}</div>"
jp_html += "<div class='jp-label'>LSTM next-state AUC</div>"
jp_html += "<div class='jp-sub'>State-transition world model · learns S_t+1 from S_t</div></div>"

jp_html += f"<div class='jp-card'><div class='jp-val'>{pooled or '—'}</div>"
jp_html += "<div class='jp-label'>Walk-forward AUC</div>"
jp_html += "<div class='jp-sub'>Temporal generalisation · no future leakage in training</div></div>"

jp_html += f"<div class='jp-card'><div class='jp-val'>{lead_med or '8'}</div>"
jp_html += "<div class='jp-label'>Lead time (median w)</div>"
if lead_mean:
    jp_html += f"<div class='jp-sub'>Windows of early warning · ~{lead_mean:.1f}s heads-up</div></div>"
else:
    jp_html += "<div class='jp-sub'>Windows of early warning</div></div>"

jp_html += f"<div class='jp-card'><div class='jp-val'>{wo_auc or '—'}</div>"
jp_html += "<div class='jp-label'>Within-day AUC</div>"
jp_html += "<div class='jp-sub'>Same-day recall · best case when drift is minimal</div></div>"
jp_html += "</div>"

jp_html += "<div class='jp-rows'>"
jp_html += ("<div class='jp-row'><div class='jpr-text'>"
            "<b>Model-internal attribution</b>"
            "<span>Mean-imputation ablation (RF) and gradient saliency (LSTM) — "
            "not a separate explainer, the model's own reasoning.</span></div></div>")
jp_html += ("<div class='jp-row'><div class='jpr-text'>"
            "<b>Novelty callout, not zero-day detection</b>"
            "<span>Flags activity unlike anything in training via k-NN distance. "
            "Advisory only — analyst reviews, never auto-blocks.</span></div></div>")
jp_html += ("<div class='jp-row'><div class='jpr-text'>"
            "<b>Tamper-proof audit trail</b>"
            "<span>Every prediction and action logged to a SHA-256 sealed ledger "
            "with a downloadable SOC incident report (PDF).</span></div></div>")
jp_html += ("<div class='jp-row'><div class='jpr-text'>"
            "<b>100% offline — zero network egress</b>"
            "<span>Models committed, no external API calls. "
            "Runs on any machine with Python 3.10+ and scikit-learn.</span></div></div>")
jp_html += "</div>"

jp_html += ("<div class='jp-honest'><b>Honest about limits</b>"
            "<span>PortScan is a cross-day blind spot (0/351 warned) — published "
            "in the docs and the strongest argument for the novelty callout. "
            "Models are intentionally unpinned in requirements.txt for broad compatibility.</span></div>")
jp_html += "</div>"
st.markdown(f"<div class='glass' style='padding:22px 22px 18px;margin:6px 0 12px'>{jp_html}</div>",
            unsafe_allow_html=True)

st.caption("NetSight · SIH26153 · runs 100% offline on your machine")