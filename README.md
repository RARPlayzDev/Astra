# ASTRA - Adaptive Spectrum Threat Recognition & Analysis

*Delivered as the Smart Scan Strategy for Electronic Warfare submission - SIH 2026.*

ASTRA is a desktop application (Windows exe) and local service implementing an ML-based Electronic Support (ES) receiver scheduler that minimises
intercept time and maximises interception rate **without prior reliable
intelligence** about emitters - the adaptive alternative to open-loop
pre-mission-programmed scans. Built for SIH 2026.

**New to the project?** Read [`PROJECT_EXPLAINED.md`](PROJECT_EXPLAINED.md) -
a plain-language walkthrough of the entire system. Judge self-assessment:
[`EVALUATION.md`](EVALUATION.md).

## Quick start

```powershell
python -m pip install -r requirements.txt streamlit fastapi uvicorn   # or: pip install -e .[dash,api]
python -m ewsmart.runner --scenario scenarios/demo.json --save-dir models --json-out results.json
python -m ewsmart.experiments --suite full            # MC eval + ROC + sensitivity + MES -> results/ + figures/
python -X utf8 tests\test_smartscan.py                # plus test_modules / test_live / test_mission / test_api ...
streamlit run dashboard.py                            # the Streamlit app (6 pages)
```

### React command centre (the pitch UI)

```powershell
cd frontend; npm install; npm run build; cd ..       # one-time build (output in frontend/dist)
python -m uvicorn server.api:app --port 8000         # serves UI + API on http://localhost:8000
```

Four views: **Mission** (KPI cards, signal chain, KPP story), **Benchmarks**
(live-rendered MC table with KPP verdicts + evidence gallery), **Live Ops**
(paired A/B arena: SmartScan vs open-loop flying the *same battlefield* over
SSE, side-by-side waterfalls), **Traceability** (PS requirement -> module ->
evidence). Docker: `docker build -t ewsmart .` then `docker run -p 8000:8000 ewsmart`.

## The dashboard (6 pages, dark professional UI)

| Page | What it does |
|---|---|
| **Overview** | SIH landing: problem, solution, signal chain, **requirement-traceability table**, headline results, one-click end-to-end demo |
| **Live Radar** | **Real-time integration**: stream PDWs from a simulated feed, a **UDP bridge for real SDR/radar hardware**, or a growing log file; SmartScan adapts online with live waterfall, KPIs and PDW feed |
| **Simulation Lab** | Scenario presets + any scheduler, run or animate episodes with plain-language scoring |
| **Benchmarks** | Monte Carlo table (mean Â± 95% CI), head-to-head charts, figure gallery, ablation + multi-receiver studies |
| **Dataset Studio** | **One-click PDW dataset import** (Turing/HuggingFace online; schema-identical offline fallback), inspection, scenario calibration |
| **Model Zoo** | Evaluate saved trained schedulers, or quick-train & save new ones |

The UI is verified by **automated Streamlit AppTest interaction tests** (every
page, every primary button, zero exceptions - `tests/test_dashboard_ui.py`).

## Live radar integration (real hardware)

```powershell
# next to your SDR sweep / radar processor:
python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555
# or relay an existing JSON PDW feed:
python tools/sdr_bridge.py --mode udp --in-port 5000 --out-port 5555
```

Then select **UDP bridge (real hardware)** on the Live Radar page. PDW schema:
`toa_us, freq_mhz, pw_us, pa_db, aoa_deg` - the standard ESM measurement set.
A JSONL/CSV log written by third-party equipment can also be tailed directly.

## The SmartScan scheduler

Per episode, five behaviours multiplexed by learned confidence:

1. **Recon sweep** - fast full-band survey bootstraps all statistics.
2. **Cued pursuit** - *credible* phase-locks predict their emitter's next ON
   window; the receiver is already there (Rayleigh period estimator with
   integer refinement, continuous miss-based validation).
3. **Predict-and-probe** - unproven locks are probed once at the predicted
   window centre; cheap to be wrong.
4. **Burst characterisation** - after two *mutually isolated* detections on the
   same SNR+AOA fingerprint, camp through the emitter's cycle to harvest lock
   evidence; persistent streams are blacklisted.
5. **Value-weighted rotation with exploitation ramp** - discounted UCB +
   recency guarantees no starvation; a ramp shifts effort to high-value bands.

**Spatial awareness:** detections carry angle-of-arrival; streams are clustered
by (SNR, AOA) fingerprints so co-channel emitters stay separated, and two
locks sharing AOA *and* period are treated as one emitter family (no wasted
double-chasing).

## Headline results

Monte Carlo over 200 held-out episodes, 24 bands Ã— 3000 slots (mean Â± 95% CI):

```
scheduler              avg_reward          threat_coverage     pred_acc
openloop-sequential    0.196 +/- 0.003     0.779 +/- 0.013     0.458
openloop-random        0.197 +/- 0.003     0.977 +/- 0.006     0.458
openloop-priority      0.196 +/- 0.003     0.785 +/- 0.013     0.458
bandit-ucb             0.942 +/- 0.005     0.540 +/- 0.015     0.988
rl-linear-q            0.474 +/- 0.025     0.896 +/- 0.012     0.190
rl-dqn                 0.269 +/- 0.021     0.895 +/- 0.012     0.387
smart-scan             0.417 +/- 0.005     0.950 +/- 0.009     0.581
```

**Mission Effectiveness (the number that matters operationally).** Judged the
way defence T&E judges systems - Key Performance Parameters first, then a
composite Mission Effectiveness Score (MES = mean of the PS figures of merit,
each normalised across the field):

| scheduler | threat cov >= 0.90 | pred acc >= 0.50 | Pfa <= 5e-4 | mission capable? | MES |
|---|---|---|---|---|---|
| smart-scan | PASS (.950) | PASS (.581) | PASS | **YES** | **#1 ranked** |
| bandit-ucb | FAIL (.540) | pass | PASS | no | high MES, disqualified |
| rl-linear-q | FAIL (.896) | FAIL (.190) | PASS | no | - |
| all open-loop | FAIL | FAIL | PASS | no | - |

* **SmartScan is the only mission-capable scheduler in the field.** Exploit-only
  UCB posts the top raw reward but misses 46% of threats - disqualified by the
  coverage KPP; linear-Q cannot predict presence better than chance.
* Paired per-episode tests on *gated* MES (KPP-violating episodes score zero):
  **SmartScan > every baseline with p < 1e-4**, Holm-corrected
  (`significance_gated_mes` in `results/suite_results.json`,
  `figures/mission_effectiveness.png`).
* SmartScan: **2.1Ã— sequential's reward** *and* **+17 points of threat
  coverage** - it resolves the reward/coverage trade-off rather than trading.
* Ablations attribute each component's value; multi-receiver teams scale
  reward near-linearly (601 â†’ 1101 â†’ 1898 for 1â†’2â†’3 de-conflicted receivers).
* Learning claims are backed by **held-out greedy evaluation curves**
  (exploration off, weights snapshotted): Q-learning reaches 716â€“841 greedy eval reward. The DQN declines on this sparse-reward task (588 â†’ 352) â€”
  a measured, disclosed data-efficiency result
  (`figures/learning_curves.png`; dashed = training, solid = greedy eval).

## Repository map

```
ewsmart/
  config.py         ScenarioConfig: JSON-serialisable battle description
  environment.py    Fake battlefield + truth matrix (physical spatial model)
  receiver.py       Detection physics, per-emitter resolution, AOA + PDWs
  periodic.py       Rayleigh period estimator + integer refinement
  schedulers.py     7 policies incl. SmartScan (AOA-aware)
  dqn.py            Deep Q-network (NumPy MLP + replay + target net)
  multireceiver.py  Cooperative teams with per-slot de-confliction
  metrics.py        FoMs + KPP-gated Mission Effectiveness Score, strict JSON
  persistence.py    Safe .npz model save/load (no pickle - no code execution)
  runner.py         Episode sim, training, CLI (ewsmart-run)
  experiments.py    Monte Carlo + ROC + sensitivity + ablation + MES (ewsmart-experiments)
  viz.py            All chart drawing
server/
  api.py            FastAPI command centre: results, figures, SSE live arena
  livesim.py        Paired A/B simulation thread (SmartScan vs open-loop)
frontend/           React + Vite command centre (Mission / Benchmarks / Live Ops / Traceability)
dashboard.py        Streamlit app (landing + live sim + benchmarks + dataset + models)
scenarios/          Ready-made JSON battle configurations
models/ results/ figures/   Trained schedulers, evaluation output, charts
tests/              57 automated tests
PROJECT_EXPLAINED.md  Plain-language walkthrough of everything
```

## Engineering guarantees

* **Valid JSON everywhere** - `json_safe()` strips NaN/Inf; outputs parse with
  strict parsers (tested).
* **Safe model artifacts** - NPZ + JSON metadata, loaded with
  `allow_pickle=False`; corrupt/foreign artifacts are rejected (tested).
* **Independent receiver noise** - every platform realises its own noise floor
  (tested).
* **Reproducibility** - every scenario is a seed + JSON config; learning
  curves are seed-averaged; evaluation is greedy on held-out scenarios.
* **57 tests** cover the environment, receiver, dataset loaders (including a
  mocked HuggingFace path), estimators, all schedulers, persistence,
  multi-receiver, live radar streaming (UDP round-trip), the KPP/MES scoring
  engine, the FastAPI endpoints (incl. a live-arena advance test), all plots,
  the Streamlit UI (AppTest interactions), and end-to-end dominance.



## Repository deliverables

| Deliverable | Location | Notes |
|---|---|---|
| Desktop application (exe + installer) | `dist\ASTRA\`, `installer\ASTRA-Setup-1.0.0.exe` | Native window (WebView2), Start Menu entry, clean uninstaller, embedded logo |
| Presentation website | `website/` | Static, deployable to Vercel; rendered documentation page + in-browser prototype console (`/console.html`) |
| A-Z software manual | `docs/ASTRA_Software_Documentation.md` | Ships inside the exe AND renders on the website |

The two UIs are intentionally independent: the desktop app is an operations tool,
the website is the presentation layer. Both are driven by the same engine
(`ewsmart/`) and the same generated results.

## Deploying the website (Vercel)

```powershell
python tools\export_site_data.py     # bake results/figures/manual into website/
cd website
npm install ; npm run build          # static output in website/dist
npx vercel deploy --prod             # or import the repo in the Vercel dashboard
```

In the Vercel dashboard set Root Directory = `website` (framework auto-detects
Vite; output dir `dist`). `vercel.json` enables clean URLs (`/documentation`).

