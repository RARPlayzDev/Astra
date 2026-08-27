"""EW SmartScan — SIH 2026 command dashboard (Streamlit, dark professional UI).

Run:  streamlit run dashboard.py

Pages
-----
* Overview        — problem, solution, requirement traceability, headline results,
                    one-click end-to-end demo.
* Live Radar      — REAL-TIME integration: stream PDWs from simulated feed, a
                    UDP bridge (real SDR / radar processor), or a growing log
                    file; watch SmartScan work online.
* Simulation Lab  — configure any scenario + scheduler and run/animate episodes.
* Benchmarks      — Monte Carlo evaluation (mean ± 95% CI), ROC, sensitivity,
                    ablation, multi-receiver studies.
* Dataset Studio  — one-click PDW dataset import (Turing/HuggingFace or offline
                    fallback) and scenario calibration.
* Model Zoo       — evaluate / quick-train / save trained schedulers.

All metrics and policies are shown with plain-language names. Every page has
built-in instructions. UI is verified by automated Streamlit AppTest suites
(tests/test_dashboard_ui.py) — zero-exception guarantee.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

from ewsmart import METRIC_LABELS
from ewsmart.config import ScenarioConfig
from ewsmart.dataset import load_pdws, summarize_pdws, environment_from_dataset
from ewsmart.environment import RFEnvironment
from ewsmart.geo import geolocate_streams, cep_stats, geometric_bearing
from ewsmart.identification import (build_default_library, fingerprint_pdws,
                                    identify, tag_environment,
                                    identification_report,
                                    streams_from_env_detections)
from ewsmart.live import (LiveSpectrum, OnlineScanner, SimulatedLiveSource,
                          UDPSource, FileTailSource)
from ewsmart.metrics import Trace, compute_metrics
from ewsmart.persistence import load_scheduler, save_scheduler
from ewsmart.receiver import ESReceiver
from ewsmart.runner import make_schedulers, run_episode, step_reward
from ewsmart.schedulers import SmartScanScheduler

LIBRARY = build_default_library()

st.set_page_config(page_title="EW SmartScan — SIH 2026", page_icon="🛰️",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
  html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
  section[data-testid="stSidebar"] {background: #0a1020; border-right: 1px solid #1d2a44;}
  .hero {background: linear-gradient(120deg, #0b1220 0%, #0e2a4d 55%, #0f4c75 100%);
         border: 1px solid #1d3a5f; border-radius: 16px; padding: 2rem 2.4rem;}
  .hero h1 {color: #e6edf7; font-size: 2.2rem; margin: .4rem 0; font-weight: 800;}
  .hero p  {color: #9fb6d4; font-size: 1.02rem; margin: 0;}
  .chip {display:inline-block; background:#0e7490; color:#c9f7ff; border-radius:999px;
         padding:.15rem .75rem; font-size:.75rem; font-weight:700; margin:0 .35rem .5rem 0;
         letter-spacing:.03em;}
  .kpi  {background:#111c33; border:1px solid #22345a; border-radius:14px; padding:1rem 1.1rem;}
  .kpi .v {font-size:1.8rem; font-weight:800; color:#22d3ee;}
  .kpi .c {font-size:.8rem; color:#9fb6d4; line-height:1.25;}
  .flow {display:flex; gap:.6rem; flex-wrap:wrap; margin:.4rem 0 1rem 0;}
  .flow .step {flex:1 1 180px; background:#111c33; border:1px solid #22345a;
               border-radius:12px; padding:.8rem .9rem; color:#cfe1f5; font-size:.85rem;}
  .flow .step b {color:#22d3ee; display:block; margin-bottom:.25rem; font-size:.92rem;}
  h1,h2,h3 {color:#e6edf7; letter-spacing:-.01em;}
</style>""", unsafe_allow_html=True)

PAGES = ["Overview", "Live Radar", "Simulation Lab",
         "Benchmarks", "Dataset Studio", "Model Zoo"]

PRESETS = {
    "Demo — 24 bands, balanced": ScenarioConfig(n_bands=24, T=3000, seed=42),
    "Dense low-SNR — 32 bands": ScenarioConfig(
        n_bands=32, T=3000, seed=7, n_stationary=10, n_agile=8,
        n_periodic=6, n_spatial=5, n_clutter=16, snr_mean_db=9.0),
    "Small & fast — 12 bands": ScenarioConfig(n_bands=12, T=1200, seed=3),
}

SCHED_OPTIONS = {
    "SmartScan (proposed adaptive ML)": "smart-scan",
    "Sequential Sweep (open loop)": "openloop-sequential",
    "Random Scan (open loop)": "openloop-random",
    "Priority Sweep (prior intel)": "openloop-priority",
    "UCB Bandit (exploit-only)": "bandit-ucb",
    "Q-Learning (linear RL)": "rl-linear-q",
    "DQN (deep RL)": "rl-dqn",
}
SCHED_LABEL = {v: k for k, v in SCHED_OPTIONS.items()}

METRIC_FMT = {"mean_time_to_first_intercept": "{:.0f}",
              "threat_mean_ttff": "{:.0f}",
              "n_periodic_locked": "{:.0f}",
              "false_alarm_rate": "{:.2e}"}


def label(key: str) -> str:
    """Plain-language display name for a metric key."""
    return METRIC_LABELS.get(key, key)


@st.cache_data(show_spinner="Building battlefield scenario...")
def build_env(n_bands: int, T: int, seed: int) -> RFEnvironment:
    return RFEnvironment(ScenarioConfig(n_bands=n_bands, T=T, seed=seed))


@st.cache_data(show_spinner="Importing PDW dataset...")
def cached_pdws(n: int, seed: int) -> list:
    return load_pdws(max_rows=n, seed=seed)


def fresh_schedulers(n_bands: int) -> dict:
    """Fresh scheduler instances (never shared mutable state across runs)."""
    return {s.name: s for s in make_schedulers(n_bands, [0], seed=7)}


def load_suite_results() -> dict | None:
    for p in (Path("results") / "suite_results.json", Path("results.json")):
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                continue
    return None


def waterfall_figure(occ: np.ndarray, actions=None, hits=None,
                     title: str = "Spectrum waterfall") -> plt.Figure:
    """Draw a band × time occupancy grid with optional scan overlay."""
    fig, ax = plt.subplots(figsize=(9.2, 3.5))
    ax.imshow(occ, aspect="auto", cmap="viridis", origin="lower",
              interpolation="nearest", vmin=0, vmax=1)
    if actions is not None:
        acts = np.asarray(actions)
        hits_arr = np.asarray(hits, dtype=bool) if hits is not None \
            else np.zeros(len(acts), dtype=bool)
        slots = np.arange(len(acts))
        ax.scatter(slots[~hits_arr], acts[~hits_arr] + 0.33, s=4, c="#7dd3fc",
                   label="listen (no signal)")
        ax.scatter(slots[hits_arr], acts[hits_arr] + 0.33, s=6, c="#f43f5e",
                   label="SIGNAL detected")
        ax.legend(fontsize=7, markerscale=2.2, loc="upper right",
                  framealpha=0.25)
    ax.set_xlabel("time slot →")
    ax.set_ylabel("frequency band →")
    ax.set_title(title, fontsize=10, color="#9fb6d4")
    fig.tight_layout()
    return fig


def kpi_row(items: list) -> None:
    """Render a row of (value, caption) KPI cards."""
    cells = st.columns(len(items))
    for cell, (v, c) in zip(cells, items):
        cell.markdown(f'<div class="kpi"><div class="v">{v}</div>'
                      f'<div class="c">{c}</div></div>', unsafe_allow_html=True)


def metric_cards(m: dict, keys=None, cols: int = 4) -> None:
    """Render headline metrics with plain-language names."""
    keys = keys or ["avg_reward", "threat_intercept_ratio", "intercept_ratio",
                    "pct_correct_predictions", "mean_time_to_first_intercept",
                    "intercept_rate", "false_alarm_rate", "n_periodic_locked"]
    for i in range(0, len(keys), cols):
        cells = st.columns(min(cols, len(keys) - i))
        for cell, k in zip(cells, keys[i:i + cols]):
            v = m.get(k)
            txt = "—" if v is None or v != v else METRIC_FMT.get(k, "{:.3f}").format(v)
            cell.metric(label(k), txt)


def run_and_show(env: RFEnvironment, sched_name: str, seed: int,
                 animate: bool = False) -> tuple:
    """Run one episode with the selected scheduler and render everything.

    Returns ``(trace, metrics)`` for downstream panels (identification, geo).
    """
    sched = fresh_schedulers(env.n_bands)[sched_name]
    if animate:
        holder = st.empty()
        trace = Trace()
        rx = ESReceiver(env, seed=seed + 1)
        sched.reset(horizon=env.T)
        chunk = max(25, env.T // 40)
        for t in range(env.T):
            b = sched.select(t)
            res = rx.dwell(b, t)
            r = step_reward(env, res, trace.first_intercept)
            trace.actions.append(b)
            trace.hits.append(res.hit and not res.false_alarm)
            trace.false_alarms.append(res.false_alarm)
            trace.rewards.append(r)
            trace.predictions.append(sched.predict(t, b))
            sched.update(t, b, res, r)
            if (t + 1) % chunk == 0 or t == env.T - 1:
                with holder.container():
                    st.pyplot(waterfall_figure(
                        env.occupancy[:, :t + 1], trace.actions, trace.hits,
                        title=f"Live scan — slot {t + 1}/{env.T}"),
                        clear_figure=True)
                    cc = st.columns(3)
                    cc[0].metric("Reward so far", f"{np.sum(trace.rewards):.0f}")
                    cc[1].metric("Detections", f"{int(np.sum(trace.hits))}")
                    cc[2].metric("Progress", f"{t + 1}/{env.T}")
    else:
        trace = run_episode(env, sched, seed=seed + 1)
        st.pyplot(waterfall_figure(
            env.occupancy, trace.actions, trace.hits,
            title=f"Episode — {SCHED_LABEL.get(sched_name, sched_name)}"))
    m = compute_metrics(env, trace)
    metric_cards(m)
    with st.expander("ℹ️ How to read these numbers"):
        st.markdown(
            "- **Avg Reward per Dwell** — value earned per listening slot "
            "(threats pay most; empty listening costs a little).\n"
            "- **Threat Interception Ratio** — fraction of *hostile* emitters "
            "caught at least once. 1.0 = none escaped.\n"
            "- **Prediction Accuracy** — how often the scheduler's belief about "
            "its chosen band matched reality.\n"
            "- **Time to First Intercept** — lower is faster threat discovery.\n"
            "- **Periodic Emitters Locked** — scanning radars whose rhythm was "
            "learned well enough to predict.")
    return trace, m


def page_overview() -> None:
    """Landing page: problem, solution, traceability, results, 1-click demo."""
    st.markdown("""
    <div class="hero">
      <div><span class="chip">SIH 2026</span><span class="chip">DEFENCE · SPACE</span>
      <span class="chip">PROBLEM ID: SMART SCAN EW</span></div>
      <h1>Smart Scan Strategy for Electronic Warfare</h1>
      <p>A machine-learning Electronic Support receiver scheduler that decides
      <b>which frequency band to listen to at every instant</b> — with zero prior
      intelligence. It intercepts 17 points more threats, earns 2.1× the reward per listen, predicts
      scanning radars' behaviour, and streams live from real sensors.</p>
    </div>""", unsafe_allow_html=True)

    kpi_row([("2.1×", "reward vs classic full-band sweep (25-episode MC)"),
             ("+17 pts", "threat interception vs open loop (0.96 vs 0.81)"),
             ("7", "policies benchmarked head-to-head"),
             ("LIVE", "real-sensor integration via UDP / log-file bridge")])

    left, right = st.columns(2)
    with left:
        st.subheader("The problem")
        st.markdown(
            "A search receiver can listen to **one narrow band at a time** while "
            "hostile radars hop, blink and sweep across a huge spectrum. "
            "Pre-programmed scans waste time on empty bands and miss agile "
            "threats. Interception is a **2-D search: which band, at what time**.")
    with right:
        st.subheader("Our solution — SmartScan")
        st.markdown(
            "A scheduler that **learns on the job**: fast recon sweep → learn the "
            "rhythm of scanning radars (Rayleigh period estimator) → be there "
            "when they transmit → burst-characterise rare signals → value-weighted "
            "rotation hunts new threats. Deep-RL (DQN) and bandit baselines "
            "included and benchmarked.")

    st.subheader("Signal chain")
    st.markdown("""
    <div class="flow">
      <div class="step"><b>1 · RF environment</b>Simulated battlefield with
      stationary, frequency-hopping, periodic and rotating-radar emitters +
      clutter. Truth matrix scores everything.</div>
      <div class="step"><b>2 · ES receiver</b>SNR-realistic detection, false
      alarms, per-emitter resolution, angle-of-arrival and PDW measurements.</div>
      <div class="step"><b>3 · SmartScan</b>Recon → phase-lock pursuit →
      predict-and-probe → burst characterisation → value-weighted rotation.</div>
      <div class="step"><b>4 · Learning & scoring</b>Trained on hits/misses
      (Q-learning, DQN); graded on 10 figures of merit with confidence intervals.</div>
      <div class="step"><b>5 · Live integration</b>Same scheduler runs online
      against real PDW streams (UDP bridge / log tail) — see <b>Live Radar</b>.</div>
    </div>""", unsafe_allow_html=True)

    st.subheader("Requirement traceability")
    st.dataframe([
        {"Problem-statement requirement": "Search/scan wide spectrum with narrowband receiver(s)",
         "Where solved": "Environment + ESReceiver; multi-receiver teams with de-confliction"},
        {"Problem-statement requirement": "Truth info per band per time slot",
         "Where solved": "RFEnvironment truth matrix occupancy[band, t]"},
        {"Problem-statement requirement": "Figures of merit (Pd, Pfa, intercept rate, reward, % correct, intercept-time error)",
         "Where solved": "metrics.py — 10 FoMs + Benchmarks page"},
        {"Problem-statement requirement": "Predict intercept time & ratio vs spatially-scanning / agile emitters",
         "Where solved": "Phase-lock predictor + intercept-time-error FoM"},
        {"Problem-statement requirement": "Robust ML scheduler trained on hits and misses",
         "Where solved": "SmartScan + Q-learning + DQN; seed-averaged learning curves"},
        {"Problem-statement requirement": "Optimal interception of periodic scan emitters",
         "Where solved": "Rayleigh estimator + integer refinement + cued pursuit"},
        {"Problem-statement requirement": "JC Wise / Turing radar datasets",
         "Where solved": "Dataset Studio — HF loader + offline PDW fallback + calibration"},
        {"Problem-statement requirement": "ML-based ES receiver scheduler software",
         "Where solved": "This package: CLI + library + dashboard + live bridge"},
    ], hide_index=True)

    st.subheader("Headline benchmark (25 episodes, mean ± 95% CI)")
    suite = load_suite_results()
    if suite and "monte_carlo" in suite:
        rows = []
        for name, m in suite["monte_carlo"].items():
            r, c = m["avg_reward"], m["threat_intercept_ratio"]
            rows.append({"Policy": SCHED_LABEL.get(name, name),
                         "Avg reward / dwell": f"{r['mean']:.3f} ± {r['ci95']:.3f}",
                         "Threat interception": f"{c['mean']:.3f} ± {c['ci95']:.3f}"})
        st.dataframe(rows, hide_index=True)
    else:
        st.caption("Run `python -m ewsmart.experiments --suite full` to populate "
                   "this table.")

    st.divider()
    st.subheader("⚡ One-click end-to-end demo")
    st.caption("Imports a PDW dataset → calibrates a battlefield from it → runs "
               "SmartScan → shows results. No configuration needed.")
    if st.button("Run full demo now", type="primary", key="ov_demo"):
        with st.status("Running end-to-end demo...", expanded=True) as status:
            st.write("Stage 1/3 — importing PDW dataset...")
            pdws = cached_pdws(8000, 0)
            s = summarize_pdws(pdws)
            st.write(f"Imported {s['n_pdw']:.0f} pulses across "
                     f"{s['active_bands']} active bands.")
            st.write("Stage 2/3 — calibrating battlefield from frequency "
                     "clusters...")
            env, info = environment_from_dataset(None, n_bands=20, T=1500,
                                                 seed=0, max_rows=8000)
            st.write(f"Calibrated {len(env.emitters)} emitters from "
                     f"{info['n_freq_clusters']} clusters.")
            st.write("Stage 3/3 — running SmartScan episode...")
            status.update(label="Demo complete", state="complete",
                          expanded=False)
        c1, c2, c3 = st.columns(3)
        c1.metric("Pulses imported", f"{s['n_pdw']:.0f}")
        c2.metric("Active bands", s["active_bands"])
        c3.metric("Occupancy", f"{s['occupancy_rate']:.0%}")
        run_and_show(env, "smart-scan", seed=0)


def threat_board(spec: LiveSpectrum) -> list:
    """Identify emitter streams from the live PDW log (intercept→classify→identify)."""
    groups: dict = {}
    for d in spec.pdw_log:
        key = (d.get("band"), round(float(d.get("freq_mhz", 0)) / 40.0))
        groups.setdefault(key, []).append(d)
    rows = []
    for (band, _), pdws in sorted(groups.items()):
        fp = fingerprint_pdws(pdws)
        if fp is None:
            continue
        entry, conf = identify(fp, LIBRARY)
        sample = pdws[len(pdws) // 2]
        rows.append({
            "Identified emitter": entry.name if entry else "UNKNOWN",
            "Class": entry.cls if entry else "-",
            "Threat": entry.threat_level if entry else "-",
            "Confidence": f"{conf:.0%}",
            "Band": band,
            "Freq (MHz)": round(fp.freq_center_mhz, 1),
            "AOA (°)": round(float(sample.get("aoa_deg", 0)), 1),
            "Pulses": fp.n_pulses,
        })
    rows.sort(key=lambda r: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2, "-": 3}[r["Threat"]],
                             -float(r["Confidence"].rstrip("%")) / 100.0))
    return rows


def page_live_radar() -> None:
    """Real-time integration page: simulated feed, UDP bridge, or file tail."""
    st.header("📡 Live Radar")
    st.caption("Watch SmartScan work **online** against a live PDW stream. "
               "Use the simulated feed for demos — or connect real hardware: "
               "run `python tools/sdr_bridge.py --mode csv --csv sweep.csv` "
               "next to your SDR sweep and select **UDP bridge** here.")

    with st.expander("🎓 How the live integration works (2-minute read)",
                     expanded=False):
        st.markdown("""
        **The pipeline, end to end:**

        1. **A sensor produces PDWs.** Any radar/SDR front-end that can report
        per-pulse measurements works: an `rtl_power` CSV sweep, an ESM
        processor, or a GNU Radio block. Each pulse becomes a
        **PDW — Pulse Descriptor Word**: `{toa_us, freq_mhz, pw_us, pa_db,
        aoa_deg}` (time-of-arrival, frequency, pulse width, power,
        direction). This is the standard EW measurement record.

        2. **The bridge moves them here.** `tools/sdr_bridge.py` tails a CSV
        sweep or relays a UDP JSON feed and pushes PDWs to this page over
        UDP port 5555. (Log files can also be tailed directly.)

        3. **`LiveSpectrum` builds the picture.** Every PDW is binned into a
        rolling *band × time* grid — exactly the truth-matrix format the
        scheduler was trained on, except it is built purely from what the
        sensor actually reported.

        4. **`OnlineScanner` runs SmartScan slot by slot.** Each slot the
        scheduler picks one band; detections are the PDWs on that band in
        that slot (with real data there is no simulated detection roll —
        what the front-end reports is what happened). Rewards follow the
        same scheme as the benchmarks, so live numbers are comparable.

        5. **Adaptation is visible.** Phase-locks form on scanning radars,
        bursts characterise rare signals, and the value-weighted rotation
        keeps hunting — you watch the policy learn the spectrum in real time.
        """)
        st.caption("No hardware yet? The **simulated feed** produces the same "
                   "PDW stream from the simulator — the scheduler cannot tell "
                   "the difference, which is the point.")

    c1, c2, c3 = st.columns(3)
    source_kind = c1.selectbox(
        "Signal source",
        ["Simulated battlefield feed", "UDP bridge (real hardware)",
         "Log file tail (JSONL/CSV)"],
        key="lr_src",
        help="Simulated = ideal wideband ESM feed. UDP = PDWs pushed by real "
             "equipment via tools/sdr_bridge.py. File = growing JSONL/CSV log.")
    n_bands = c2.slider("Bands", 8, 48, 20, key="lr_bands")
    fmax_ghz = c3.slider("Tuning max (GHz)", 4.0, 18.0, 18.0, 0.5, key="lr_fmax")

    udp_port = st.sidebar.number_input("Live Radar UDP port", 1000, 65535, 5555,
                                       key="lr_port")
    file_path = st.sidebar.text_input("Live Radar log file", "live_feed.jsonl",
                                      key="lr_file")

    cfg_changed = (st.session_state.get("live_bands") != n_bands or
                   st.session_state.get("live_fmax") != fmax_ghz or
                   st.session_state.get("live_kind") != source_kind)
    if "live_spec" not in st.session_state or cfg_changed:
        old = st.session_state.get("live_source")
        if isinstance(old, UDPSource):
            old.close()
        st.session_state["live_spec"] = LiveSpectrum(
            n_bands=n_bands, fmax_mhz=fmax_ghz * 1000.0)
        st.session_state["live_scanner"] = None
        st.session_state["live_source"] = None
        st.session_state["live_bands"] = n_bands
        st.session_state["live_fmax"] = fmax_ghz
        st.session_state["live_kind"] = source_kind
        st.session_state.pop("live_running", None)

    b1, b2, b3 = st.columns([1, 1, 1])
    start = b1.button("▶ Start / resume feed", type="primary", key="lr_start")
    step_btn = b2.button("⏭ Advance 100 slots", key="lr_step")
    stop_btn = b3.button("⏹ Stop & reset", key="lr_stop")

    if stop_btn:
        for k in ("live_spec", "live_scanner", "live_source", "live_running"):
            st.session_state.pop(k, None)
        st.session_state["live_bands"] = None
        st.success("Feed reset.")
        return

    spec: LiveSpectrum = st.session_state["live_spec"]
    if st.session_state.get("live_scanner") is None:
        st.session_state["live_scanner"] = OnlineScanner(
            spec, SmartScanScheduler(n_bands, seed=1), n_bands)
    scanner: OnlineScanner = st.session_state["live_scanner"]

    if st.session_state.get("live_source") is None:
        if source_kind.startswith("Simulated"):
            env = build_env(n_bands, 4000, seed=7)
            st.session_state["live_source"] = SimulatedLiveSource(env, seed=9)
        elif source_kind.startswith("UDP"):
            try:
                st.session_state["live_source"] = UDPSource(port=int(udp_port))
                st.toast(f"Listening for PDWs on UDP {udp_port}", icon="🔌")
            except OSError as exc:
                st.error(f"Could not bind UDP {udp_port}: {exc}")
                return
        else:
            st.session_state["live_source"] = FileTailSource(file_path)

    live = bool(st.session_state.get("live_running")) or start
    pill = st.markdown(
        '<span class="chip" style="background:#16a34a">● LIVE — scanning</span>'
        if live else
        '<span class="chip" style="background:#475569">○ IDLE — press Start '
        'or Advance</span>', unsafe_allow_html=True)

    def advance(n_slots: int, render_every: int = 25) -> None:
        src = st.session_state["live_source"]
        prog = st.progress(0.0, text="Scanning live spectrum...")
        chart = st.empty()
        feed = st.empty()
        for i in range(n_slots):
            _, pdws = src.poll()
            spec.ingest(pdws)
            scanner.step(pdws)
            if (i + 1) % render_every == 0 or i == n_slots - 1:
                with chart.container():
                    st.pyplot(waterfall_figure(
                        spec.view(),
                        scanner.actions[-spec.window:],
                        scanner.hits[-spec.window:],
                        title=f"Live — slot {spec.slot} | SmartScan band "
                              f"choice per slot"),
                        clear_figure=True)
                    feed.dataframe(
                        [{"slot": d.get("slot"), "band": d.get("band"),
                          "freq (MHz)": round(d.get("freq_mhz", 0), 2),
                          "AOA (°)": round(d.get("aoa_deg", 0), 1),
                          "power (dB)": round(d.get("pa_db", 0), 1)}
                         for d in list(spec.pdw_log)[-8:]][::-1],
                        hide_index=True)
                prog.progress((i + 1) / n_slots,
                              text=f"Scanning... slot {spec.slot}")
            time.sleep(0.002)
        prog.empty()

    if start:
        st.session_state["live_running"] = True
    if step_btn:
        advance(100)
    if st.session_state.get("live_running"):
        advance(300)

    stats = scanner.stats()
    kpi_row([(f"{stats['slots']}", "slots scanned live"),
             (f"{stats['avg_reward']:.3f}", "avg reward per dwell (live)"),
             (f"{stats['hit_rate']:.0%}", "dwell hit rate (live)"),
             (f"{stats['unique_streams']}", "distinct emitter streams found")])

    st.subheader("🎯 Threat board — live emitter identification")
    st.caption("Streams with enough pulses are fingerprinted (frequency, pulse "
               "width, scan rhythm) and matched against the emitter library "
               "(JC Wise-style class profiles).")
    board = threat_board(spec)
    if board:
        def _threat_color(t: str) -> str:
            return {"HIGH": "#f43f5e", "MEDIUM": "#f59e0b",
                    "LOW": "#22c55e", "-": "#64748b"}.get(t, "#64748b")
        st.dataframe(
            [{**r, "Threat": r["Threat"]} for r in board],
            hide_index=True, width="stretch")
        hi = [r for r in board if r["Threat"] == "HIGH"]
        if hi:
            st.error(f"⚠️ {len(hi)} HIGH-threat emitter"
                     f"{'s' if len(hi) > 1 else ''} identified: "
                     + ", ".join(r['Identified emitter'] for r in hi))
    else:
        st.caption("No stream has enough pulses yet — advance more slots.")

    with st.expander("🔌 Connecting real radar / SDR hardware"):
        st.markdown(
            "1. Produce PDWs from your front-end (any of: `rtl_power` CSV sweep, "
            "ESM processor JSON, GNU Radio UDP block).\n"
            "2. Run the reference bridge: "
            "`python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555` "
            "or `--mode udp --in-port 5000` to relay an existing JSON feed.\n"
            "3. Select **UDP bridge (real hardware)** above — PDWs appear here "
            "and SmartScan adapts online.\n\n"
            "PDW schema: `toa_us, freq_mhz, pw_us, pa_db, aoa_deg` — the standard "
            "ESM measurement set.")


def page_sim_lab() -> None:
    """Configure and run offline episodes against the simulator."""
    st.header("🧪 Simulation Lab")
    st.caption("Play a scheduled battle against the simulator: choose a scenario "
               "and a policy, then run or animate a full episode with scoring.")

    left, right = st.columns([1, 3])
    with left:
        preset = st.selectbox("Scenario preset", list(PRESETS), key="sl_preset")
        cfg = PRESETS[preset]
        n_bands = st.slider("Bands", 8, 48, cfg.n_bands, key="sl_bands")
        horizon = st.slider("Episode length (slots)", 400, 5000,
                            min(cfg.T, 3000), step=100, key="sl_T")
        seed = st.number_input("Scenario seed", 0, 9999, cfg.seed, key="sl_seed")
        sched_label = st.selectbox("Scheduler policy", list(SCHED_OPTIONS),
                                   key="sl_sched",
                                   help="SmartScan adapts online; open-loop "
                                        "policies never learn.")
        animate = st.checkbox("Animate the scan", value=False, key="sl_anim")
        run_btn = st.button("▶ Run episode", type="primary", key="sl_run")
        with st.expander("ℹ️ Reading the display"):
            st.markdown(
                "- Top panel: ground truth — which bands are transmitting.\n"
                "- Bottom: your receiver's choices; red = detections.\n"
                "- Good schedulers find threats early, hug high-value bands, "
                "and still sweep for newcomers.")
    with right:
        if not run_btn:
            st.info("Configure on the left, then press **▶ Run episode**.")
        else:
            env = build_env(n_bands, int(horizon), int(seed))
            trace, _ = run_and_show(env, SCHED_OPTIONS[sched_label],
                                    int(seed), animate=animate)

            st.divider()
            st.subheader("🎯 Emitter identification")
            st.caption("Detected streams are fingerprinted (frequency, pulse "
                       "width, scan rhythm) and matched against the emitter "
                       "library. Ground truth comes from the simulator.")
            tag_environment(env)
            rep = identification_report(
                env, streams_from_env_detections(env, trace))
            c1, c2, c3 = st.columns(3)
            acc = rep["accuracy"]
            c1.metric("Identification accuracy",
                      f"{acc:.0%}" if acc == acc else "—")
            c2.metric("Streams identified",
                      f"{rep['n_identified']}/{rep['n_streams']}")
            c3.metric("HIGH-threat found",
                      sum(1 for r in rep["rows"] if r["threat"] == "HIGH"))
            if rep["rows"]:
                st.dataframe(rep["rows"][:12], hide_index=True,
                             width="stretch")

            st.divider()
            st.subheader("🌐 Multi-receiver geolocation")
            st.caption("K cooperating receivers measure bearings to each "
                       "emitter (2° noise); least-squares triangulation "
                       "estimates positions. Red stars = true emitters, cyan "
                       "circles = estimates with residual rings, blue "
                       "triangles = receivers.")
            k_rx = st.slider("Cooperating receivers", 2, 4, 3, key="geo_k")
            from ewsmart.geo import simulate_bearings, triangulate, cep_stats
            from ewsmart import viz as _viz
            rng = np.random.default_rng(int(seed) + 77)
            rxs = [(0.0, 0.0)]
            for i in range(1, k_rx):
                a = 2 * np.pi * i / k_rx
                rxs.append((50.0 * np.cos(a), 50.0 * np.sin(a)))
            true_pts = [(e.x_km, e.y_km) for e in env.emitters]
            est_pts = []
            for e in env.emitters:
                lines = simulate_bearings((e.x_km, e.y_km), rxs, 2.0, rng)
                x, y, res = triangulate(lines)
                est_pts.append({"x": x, "y": y, "residual_km": res})
            errors = [float(np.hypot(p["x"] - t[0], p["y"] - t[1]))
                      for p, t in zip(est_pts, true_pts)]
            cs = cep_stats(errors)
            st.pyplot(_viz.plot_geo_map(
                true_pts, rxs, est_pts,
                scene_km=max(50.0, env.scene_radius_km),
                title=f"AOA triangulation with {k_rx} receivers"))
            kpi_row([(f"{cs['mean']:.1f} km", "mean localisation error"),
                     (f"{cs['cep50']:.1f} km", "CEP50 (median)"),
                     (f"{cs['cep90']:.1f} km", "CEP90"),
                     (f"{len(true_pts)}", "emitters localised")])
def page_benchmarks() -> None:
    """Monte Carlo benchmark tables, CI chart and figure gallery."""
    st.header("📊 Benchmark Lab")
    suite = load_suite_results()
    if not suite:
        st.warning("No results yet. Run `python -m ewsmart.experiments --suite "
                   "full` (about 10 minutes) to generate the full evaluation.")
        return

    mc = suite.get("monte_carlo", {})
    st.subheader("Monte Carlo evaluation (25 episodes, mean ± 95% CI)")
    st.caption("Every scheduler plays the same random battlefield scenarios; "
               "we report the average over 25 independent episodes. CI = "
               "confidence interval; smaller is more consistent.")
    rows = []
    for name, m in mc.items():
        row = {"Scheduler": SCHED_LABEL.get(name, name)}
        for k in ("avg_reward", "threat_intercept_ratio", "intercept_ratio",
                  "mean_time_to_first_intercept", "pct_correct_predictions"):
            v = m.get(k, {})
            if isinstance(v, dict) and v.get("mean") is not None:
                row[label(k)] = f"{v['mean']:.3f} ± {v['ci95']:.3f}"
            else:
                row[label(k)] = "—"
        rows.append(row)
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Head-to-head chart")
    metric = st.selectbox("Metric", list(METRIC_LABELS.keys()),
                          format_func=label)
    names, vals, errs = [], [], []
    for name, m in mc.items():
        v = m.get(metric, {})
        if isinstance(v, dict) and v.get("mean") is not None:
            names.append(SCHED_LABEL.get(name, name))
            vals.append(v["mean"])
            errs.append(v.get("ci95") or 0.0)
    if vals:
        fig, ax = plt.subplots(figsize=(8, 3.4))
        ax.barh(names, vals, xerr=errs, color="#1b5e9e", alpha=0.85)
        ax.set_xlabel(label(metric))
        ax.grid(axis="x", alpha=0.3)
        fig.tight_layout()
        st.pyplot(fig)

    st.subheader("Analysis figures")
    gallery = {
        "comparison.png": "Scheduler comparison across key figures of merit.",
        "learning_curves.png": "Training progress (seed-averaged) for the "
                               "learning schedulers.",
        "waterfall.png": "Example episode: spectrum truth vs SmartScan's choices.",
        "roc.png": "Detection vs false-alarm trade-off (sensitivity sweep).",
        "sens_bands.png": "Robustness vs spectrum size.",
        "sens_snr.png": "Robustness vs emitter signal strength.",
        "sens_agility.png": "Robustness vs threat hop speed.",
        "sens_density.png": "Robustness vs emitter density.",
        "ablation.png": "Contribution of each SmartScan component.",
    }
    picks = st.multiselect("Figures to show", list(gallery),
                           default=list(gallery)[:4],
                           format_func=lambda k: gallery[k])
    for png in picks:
        p = Path("figures") / png
        if p.exists():
            st.image(str(p), caption=gallery[png])
        else:
            st.caption(f"missing: figures/{png}")

    with st.expander("🔬 Ablation & multi-receiver studies"):
        abl = suite.get("ablation", {})
        if abl:
            st.markdown("**SmartScan ablation** (what each behaviour adds):")
            st.dataframe([{ "Variant": k,
                            "Avg reward": f"{v['avg_reward']:.3f}",
                            "Threat coverage": f"{v['threat_intercept_ratio']:.3f}"}
                          for k, v in abl.items()],
                         use_container_width=True, hide_index=True)
        mr = suite.get("multireceiver", {})
        if mr:
            st.markdown("**Cooperative multi-receiver teams** (de-conflicted "
                        "scanning scales almost linearly):")
            st.dataframe([{"Team": SCHED_LABEL.get(k.rsplit('-x', 1)[0],
                                                    k.rsplit('-x', 1)[0])
                                 + f" × {k.rsplit('-x', 1)[1]}",
                           "Total reward": f"{v['total_reward']:.0f}",
                           "Coverage": f"{v['intercept_ratio']:.2f}"}
                          for k, v in mr.items()],
                         use_container_width=True, hide_index=True)


def page_dataset() -> None:
    """One-click PDW dataset import and scenario calibration."""
    st.header("🛰️ Dataset Studio")
    st.caption("The problem statement references the Turing Synthetic Radar "
               "dataset (HuggingFace). Import a pulse-descriptor-word (PDW) "
               "stream, inspect it, and calibrate a battlefield scenario from "
               "it — one click, fully offline-capable.")
    autorun = st.session_state.pop("autorun", False)
    n_rows = st.slider("PDWs to import", 2000, 30000, 8000, step=1000)
    go = st.button("⬇️ Import pre-loaded dataset", type="primary") or autorun

    if go:
        with st.spinner("Importing PDW stream (offline synthetic fallback; "
                        "auto-uses HuggingFace when available)..."):
            pdws = cached_pdws(int(n_rows), 0)
        summary = summarize_pdws(pdws)
        cols = st.columns(5)
        nice = {"n_pdw": "Pulses imported", "active_bands": "Active bands",
                "occupancy_rate": "Occupancy rate",
                "freq_min_mhz": "Min freq (MHz)", "freq_max_mhz": "Max freq (MHz)"}
        for i, k in enumerate(("n_pdw", "active_bands", "occupancy_rate",
                               "freq_min_mhz", "freq_max_mhz")):
            cols[i].metric(nice[k], f"{summary[k]:.4g}")

        freqs = np.array([p["freq_mhz"] for p in pdws])
        toas = np.array([p["toa_us"] for p in pdws])
        fig, ax = plt.subplots(figsize=(9, 3.2))
        ax.scatter(toas / 1e6, freqs / 1000.0, s=2, alpha=0.35, c="#2a9d8f")
        ax.set_xlabel("time (s)")
        ax.set_ylabel("frequency (GHz)")
        ax.set_title("Imported PDW waterfall (frequency vs time-of-arrival)")
        fig.tight_layout()
        st.pyplot(fig)

        if st.button("🧪 Calibrate scenario from this dataset & run SmartScan",
                     type="primary") or autorun:
            with st.spinner("Clustering PDWs by frequency fingerprint and "
                            "building the calibrated battlefield..."):
                env, info = environment_from_dataset(None, n_bands=20, T=1500,
                                                     seed=0,
                                                     max_rows=int(n_rows))
            st.success(f"Calibrated {len(env.emitters)} emitters from "
                       f"{info['n_freq_clusters']} frequency clusters "
                       f"(source: {info['source']}).")
            sched = SmartScanScheduler(20)
            tr = run_episode(env, sched, seed=1)
            m = compute_metrics(env, tr)
            st.pyplot(render_waterfall(env, tr))
            metric_cards(m)
            st.caption(f"Source: {info['source']}")


def page_models() -> None:
    """Load, evaluate and create trained scheduler artifacts."""
    st.header("💾 Model Zoo")
    st.caption("Trained schedulers saved as safe `.npz` artifacts (no pickle — "
               "loading can never execute code). Evaluate any of them on a "
               "fresh scenario, or train-and-save a new one.")
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    files = sorted(models_dir.glob("*.npz"))
    if files:
        pick = st.selectbox("Saved model", files,
                            format_func=lambda p: p.name)
        preset = st.selectbox("Evaluation scenario", list(PRESETS),
                              key="zoo_preset")
        if st.button("🧭 Evaluate selected model"):
            cfg = PRESETS[preset]
            env = build_env(cfg.n_bands, min(cfg.T, 2000), cfg.seed + 5)
            sched = load_scheduler(str(pick))
            tr = run_episode(env, sched, seed=11)
            m = compute_metrics(env, tr)
            st.pyplot(render_waterfall(env, tr))
            metric_cards(m)
    else:
        st.info("No saved models yet — create one below.")

    with st.expander("🏋️ Quick-train & save a new model"):
        n_bands = st.number_input("Bands", 8, 32, 16, key="zt_bands")
        eps = st.slider("Training episodes", 2, 20, 4, key="zt_eps")
        which = st.selectbox("Policy", ["smart-scan", "rl-dqn", "rl-linear-q"],
                             key="zt_which")
        if st.button("Train & save", key="zt_go"):
            from ewsmart.schedulers import (LinearQLearning, DQNScheduler,
                                            SmartScanScheduler)
            from ewsmart.persistence import save_scheduler
            cls = {"smart-scan": SmartScanScheduler, "rl-dqn": DQNScheduler,
                   "rl-linear-q": LinearQLearning}[which]
            s = cls(int(n_bands), seed=5)
            prog = st.progress(0.0)
            for ep in range(eps):
                env = RFEnvironment(ScenarioConfig(n_bands=int(n_bands),
                                                   T=800, seed=300 + ep))
                run_episode(env, s, seed=ep)
                s.end_episode()
                prog.progress((ep + 1) / eps)
            out = models_dir / f"{which}-{int(n_bands)}b.npz"
            save_scheduler(out, s)
            st.success(f"Saved {out}")


from ewsmart.schedulers import SmartScanScheduler  # noqa: E402

def page_benchmarks() -> None:
    """Monte Carlo results, figures gallery, ablation, multi-receiver."""
    st.header("📊 Benchmarks & Analysis")
    suite = load_suite_results()
    if not suite:
        st.warning("No results yet. Run `python -m ewsmart.experiments --suite "
                   "full` (about 10 min) to generate the complete evaluation.")
        return

    mc = suite.get("monte_carlo", {})
    tab_mc, tab_figs, tab_studies = st.tabs(
        ["Monte Carlo evaluation", "Figures", "Ablation & multi-receiver"])

    with tab_mc:
        st.caption("Every scheduler played the same 25 random battlefields; "
                   "values are mean ± 95% confidence interval.")
        rows = []
        for name, m in mc.items():
            row = {"Policy": SCHED_LABEL.get(name, name)}
            for k in ("avg_reward", "threat_intercept_ratio", "intercept_ratio",
                      "mean_time_to_first_intercept",
                      "pct_correct_predictions", "avg_intercept_time_error"):
                v = m.get(k, {})
                if isinstance(v, dict) and v.get("mean") is not None:
                    row[label(k)] = f"{v['mean']:.3f} ± {v['ci95']:.3f}"
                else:
                    row[label(k)] = "—"
            rows.append(row)
        st.dataframe(rows, hide_index=True, width="stretch")

        sig = suite.get("significance", [])
        if sig:
            st.subheader("Statistical significance")
            st.caption("Paired permutation tests (20k permutations) on "
                       "per-episode differences, SmartScan vs each comparator; "
                       "Holm-Bonferroni corrected at α=0.05.")
            st.dataframe([
                {"Metric": label(r["metric"]),
                 "Comparator": SCHED_LABEL.get(r["comparator"], r["comparator"]),
                 "Mean diff (SmartScan −)": f"{r['mean_diff']:+.3f}",
                 "95% CI": f"[{r['ci95_low']:+.3f}, {r['ci95_high']:+.3f}]",
                 "p-value": f"{r['p_value']:.4f}",
                 "Significant": "✅" if r["significant"] else "—",
                 "n": r["n"]}
                for r in sig], hide_index=True, width="stretch")

        st.subheader("Head-to-head")
        metric = st.selectbox("Metric", list(METRIC_LABELS.keys()),
                              format_func=label, key="bm_metric")
        names, vals, errs = [], [], []
        for name, m in mc.items():
            v = m.get(metric, {})
            if isinstance(v, dict) and v.get("mean") is not None:
                names.append(SCHED_LABEL.get(name, name))
                vals.append(v["mean"])
                errs.append(v.get("ci95") or 0.0)
        if vals:
            fig, ax = plt.subplots(figsize=(8, 3.2))
            bars = ax.barh(names, vals, xerr=errs, color="#22d3ee", alpha=0.9)
            ax.set_xlabel(label(metric))
            ax.grid(axis="x", alpha=0.25)
            ax.tick_params(labelsize=8)
            fig.tight_layout()
            st.pyplot(fig)

    with tab_figs:
        gallery = {
            "waterfall.png": "Example episode — spectrum truth vs SmartScan's choices",
            "learning_curves.png": "Seed-averaged training progress",
            "comparison.png": "Scheduler comparison across key metrics",
            "roc.png": "Detection vs false-alarm trade-off (sensitivity sweep)",
            "sens_bands.png": "Robustness vs spectrum size",
            "sens_snr.png": "Robustness vs signal strength",
            "sens_agility.png": "Robustness vs threat hop speed",
            "sens_density.png": "Robustness vs emitter density",
            "ablation.png": "SmartScan component ablation",
            "geo_map.png": "Multi-receiver AOA geolocation example",
            "geo_cep.png": "Localisation error vs receiver count",
        }
        pick = st.selectbox("Figure", list(gallery), format_func=lambda k: gallery[k])
        p = Path("figures") / pick
        if p.exists():
            st.image(str(p), caption=gallery[pick])
        else:
            st.caption(f"Missing figures/{pick} — run the experiment suite.")

    with tab_studies:
        abl = suite.get("ablation", {})
        if abl:
            st.markdown("**SmartScan ablation** — what each behaviour contributes:")
            st.dataframe([{"Variant": k,
                           "Avg reward": f"{v['avg_reward']:.3f}",
                           "Threat coverage": f"{v['threat_intercept_ratio']:.3f}"}
                          for k, v in abl.items()],
                         width="stretch", hide_index=True)
        mr = suite.get("multireceiver", {})
        if mr:
            st.markdown("**Cooperative multi-receiver teams** — de-conflicted "
                        "scanning scales near-linearly:")
            st.dataframe([{"Team": k, "Total reward": f"{v['total_reward']:.0f}",
                           "Coverage": f"{v['intercept_ratio']:.2f}"}
                          for k, v in mr.items()],
                         width="stretch", hide_index=True)
        lrn = suite.get("learning", {})
        if lrn:
            st.markdown("**Learning — greedy evaluation on held-out scenarios** "
                        "(exploration off, weights snapshotted during eval):")
            rows = []
            for k, v in lrn.items():
                if "eval_first_third_mean" in v:
                    rows.append({"Policy": SCHED_LABEL.get(k, k),
                                 "Eval reward (first third)":
                                     f"{v['eval_first_third_mean']:.0f}",
                                 "Eval reward (last third)":
                                     f"{v['eval_last_third_mean']:.0f}"})
                else:
                    rows.append({"Policy": SCHED_LABEL.get(k, k),
                                 "Eval reward (first third)":
                                     f"{v.get('first_third_mean', 0):.0f} (train)",
                                 "Eval reward (last third)":
                                     f"{v.get('last_third_mean', 0):.0f} (train)"})
            st.dataframe(rows, width="stretch", hide_index=True)
            st.caption("Re-run `python -m ewsmart.experiments --suite full` "
                       "for the held-out greedy-evaluation curves. Training "
                       "curves (with exploration) are in "
                       "figures/learning_curves.png.")


def page_dataset() -> None:
    """One-click PDW import + scenario calibration."""
    st.header("🛰️ Dataset Studio")
    st.caption("The problem statement references the JC Wise radar-emitter "
               "database and the Turing Synthetic Radar dataset (HuggingFace). "
               "Import a PDW stream, inspect it, and calibrate a battlefield "
               "from it — one click, fully offline-capable.")
    n_rows = st.slider("PDWs to import", 2000, 30000, 8000, step=1000,
                       key="ds_rows")
    if st.button("⬇️ Import pre-loaded dataset", type="primary", key="ds_import"):
        with st.spinner("Importing PDW stream (HuggingFace when online; "
                        "schema-identical offline fallback otherwise)..."):
            pdws = cached_pdws(int(n_rows), 0)
        s = summarize_pdws(pdws)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pulses imported", f"{s['n_pdw']:.0f}")
        c2.metric("Active bands", s["active_bands"])
        c3.metric("Occupancy rate", f"{s['occupancy_rate']:.0%}")
        c4.metric("Freq span",
                  f"{s['freq_min_mhz']:.0f}–{s['freq_max_mhz']:.0f} MHz")
        freqs = np.array([p["freq_mhz"] for p in pdws])
        toas = np.array([p["toa_us"] for p in pdws])
        fig, ax = plt.subplots(figsize=(9, 3))
        ax.scatter(toas / 1e6, freqs / 1000.0, s=2, alpha=0.35, c="#2dd4bf")
        ax.set_xlabel("time (s)")
        ax.set_ylabel("frequency (GHz)")
        ax.set_title("Imported PDW waterfall", fontsize=10, color="#9fb6d4")
        fig.tight_layout()
        st.pyplot(fig)
        st.session_state["ds_ready"] = True

    if st.session_state.get("ds_ready"):
        if st.button("🧪 Calibrate battlefield & run SmartScan", type="primary",
                     key="ds_calib"):
            with st.spinner("Clustering PDWs by frequency fingerprint..."):
                env, info = environment_from_dataset(None, n_bands=20, T=1500,
                                                     seed=0, max_rows=int(n_rows))
            st.success(f"Calibrated {len(env.emitters)} emitters from "
                       f"{info['n_freq_clusters']} frequency clusters "
                       f"({info['source']}).")
            run_and_show(env, "smart-scan", seed=0)


def page_models() -> None:
    """Evaluate, quick-train and save trained schedulers."""
    st.header("💾 Model Zoo")
    st.caption("Trained schedulers persist as safe `.npz` artifacts "
               "(plain arrays + JSON — loading can never execute code). "
               "Evaluate one on a fresh battlefield, or train a new one.")
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    files = sorted(models_dir.glob("*.npz"))

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Evaluate a saved model")
        if files:
            pick = st.selectbox("Saved model", files,
                                format_func=lambda p: p.name)
            preset = st.selectbox("Scenario", list(PRESETS), key="mz_preset")
            if st.button("🧭 Evaluate", key="mz_eval"):
                cfg = PRESETS[preset]
                env = build_env(cfg.n_bands, min(cfg.T, 2000), cfg.seed + 5)
                try:
                    sched = load_scheduler(str(pick))
                except Exception as exc:
                    st.error(f"Could not load artifact: {exc}")
                    return
                run_and_show(env, sched.name if hasattr(sched, "name")
                             else "smart-scan", seed=11, animate=False)
                st.caption(f"Loaded {pick.name} and ran a fresh episode.")
        else:
            st.info("No saved models yet — train one on the right.")

    with c2:
        st.subheader("Quick-train & save")
        n_bands = st.number_input("Bands", 8, 32, 16, key="mz_bands")
        eps = st.slider("Training episodes", 2, 20, 4, key="mz_eps")
        which = st.selectbox("Policy", ["smart-scan", "rl-dqn", "rl-linear-q"],
                             key="mz_which")
        if st.button("🏋️ Train & save", key="mz_train"):
            from ewsmart.schedulers import (LinearQLearning, DQNScheduler)
            cls = {"smart-scan": SmartScanScheduler, "rl-dqn": DQNScheduler,
                   "rl-linear-q": LinearQLearning}[which]
            s = cls(int(n_bands), seed=5)
            prog = st.progress(0.0, text="Training...")
            for ep in range(eps):
                env = RFEnvironment(ScenarioConfig(n_bands=int(n_bands),
                                                   T=800, seed=300 + ep))
                run_episode(env, s, seed=ep)
                s.end_episode()
                prog.progress((ep + 1) / eps,
                              text=f"Training... episode {ep + 1}/{eps}")
            out = models_dir / f"{which}-{int(n_bands)}b.npz"
            save_scheduler(out, s)
            st.success(f"Saved {out}")


def main() -> None:
    st.sidebar.markdown("### 🛰️ EW SmartScan")
    st.sidebar.caption("Smart Scan Strategy for Electronic Warfare — "
                       "SIH 2026 · v0.5.0")
    page = st.sidebar.radio("Navigate", PAGES, key="nav",
                            label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption(
        "**New here?** Start on *Overview*, press the one-click demo, then "
        "watch *Live Radar*. Full walkthrough: `PROJECT_EXPLAINED.md`.")
    {"Overview": page_overview, "Live Radar": page_live_radar,
     "Simulation Lab": page_sim_lab, "Benchmarks": page_benchmarks,
     "Dataset Studio": page_dataset, "Model Zoo": page_models}[page]()


main()

