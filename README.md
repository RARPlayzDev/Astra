<p align="center">
  <img src="assets/astra_mark_512.png" alt="ASTRA Logo" width="120" />
</p>

<h1 align="center">ASTRA</h1>
<h3 align="center">Adaptive Spectrum Threat Recognition & Analysis</h3>

<p align="center">
  <em>Smart Scan Strategy for Electronic Warfare — SIH 2026</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/tests-306_passing-10b981?style=for-the-badge&label=tests" alt="Tests" />
  <img src="https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/installer-164_MB-8b5cf6?style=for-the-badge" alt="Installer" />
  <img src="https://img.shields.io/badge/SIH_2026-submission-f59e0b?style=for-the-badge" alt="SIH 2026" />
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-the-problem">The Problem</a> •
  <a href="#-how-smartscan-works">SmartScan</a> •
  <a href="#-results">Results</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-file-formats">Docs</a>
</p>

---

## 🎯 What is ASTRA?

ASTRA is an **ML-based Electronic Support (ES) receiver scheduler** that minimises intercept time and maximises interception rate — **without prior reliable intelligence** about hostile emitters. It replaces rigid, pre-mission-programmed scan patterns with an adaptive strategy that learns the electromagnetic battlefield in real time.

Built as a complete, end-to-end system: simulation environment → receiver physics → seven competing schedulers → statistical evaluation → desktop application → live hardware integration → presentation website.

> **New to the project?** Read [`PROJECT_EXPLAINED.md`](PROJECT_EXPLAINED.md) for a plain-language walkthrough.
> **Judge self-assessment:** [`EVALUATION.md`](EVALUATION.md)

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.10 |
| Node.js | ≥ 18 (for frontend builds) |
| npm | ≥ 9 |

### Install & Run

```powershell
# Clone the repository
git clone https://github.com/RARPlayzDev/Astra.git
cd Astra

# Install core dependencies
pip install -e ".[api,dev]"

# Run a single episode with all schedulers
python -m ewsmart.runner --scenario scenarios/demo.json --save-dir models --json-out results.json

# Run the full Monte Carlo evaluation suite
python -m ewsmart.experiments --suite full

```

### React Command Centre

```powershell
cd frontend && npm install && npm run build && cd ..
python -m uvicorn server.api:app --port 8000
# → Open http://localhost:8000
```

### Desktop Application

```powershell
python desktop_qt.py
# Pre-built installer available at: installer/ASTRA-Setup-3.0.0.exe
```

### Docker (One Command)

```powershell
docker build -t astra .
docker run -p 8000:8000 astra
# → Open http://localhost:8000
```

---

## ❓ The Problem

An Electronic Support (ES) receiver must find hostile radar and communication signals across a wide spectrum, but its **instantaneous bandwidth covers only a small slice** — it must sweep across bands, listening to one at a time.

**Interception is a two-dimensional search problem:** the receiver must be on the *right frequency* at the *right time*.

Traditional receivers use fixed scan patterns programmed before the mission (*open loop*). This approach:

| ❌ Failure Mode | Impact |
|---|---|
| **Blind coverage** | Wastes dwell time on empty bands while threats go undetected |
| **No memory** | Never exploits periodic emitter rhythms; intercept is pure luck |
| **Exploit trap** | Naive adaptivity camps on the richest band; finds only 54% of threats |

ASTRA's **SmartScan** scheduler solves all three — it is the **only mission-capable policy** in our evaluation field.

---

## 🧠 How SmartScan Works

SmartScan is not a single algorithm — it is a **confidence-multiplexed control system** that activates six behaviours based on learned evidence:

```
┌─────────────────────────────────────────────────────────────┐
│                    SMARTSCAN SCHEDULER                       │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  RECON   │  │  CUED    │  │ PREDICT  │  │  BURST   │    │
│  │  SWEEP   │→ │ PURSUIT  │→ │ & PROBE  │→ │ CHARTING │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│        ↓              ↓             ↓             ↓         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          VALUE-WEIGHTED ROTATION (fallback)          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Governed by: learned confidence · SNR+AOA fingerprints     │
│               online lock validation · miss-based pruning   │
└─────────────────────────────────────────────────────────────┘
```

| # | Behaviour | When Active | What It Prevents |
|---|---|---|---|
| 1 | **Recon Sweep** | Episode start / low knowledge | Acting on no information |
| 2 | **Cued Pursuit** | Validated phase locks exist | Missing predictable targets |
| 3 | **Predict & Probe** | Unproven candidate rhythm | Never testing hypotheses |
| 4 | **Burst Characterisation** | Isolated hit on quiet fingerprint | Under-sampling rare emitters |
| 5 | **Agile-Hop Anticipation** | Frequent hops on a tracked stream | Losing agile emitters between hops |
| 6 | **Value-Weighted Rotation** | Always (fallback) | Band starvation; over-commitment |

**Key innovations:**
- **Online lock validation** — predictions must keep coming true; stale locks self-destruct
- **SNR+AOA fingerprinting** — co-channel emitters stay separated; same-source locks merge
- **Causal agile-hop prediction** — a per-stream transition model learned only from observed detections biases the rotation toward each agile emitter's likely next band; prediction accuracy is reported separately from hop coverage
- **Cheap falsification** — wrong hypotheses die fast and cost only one slot

---

## 📊 Results

> Every number below is quoted from a generated artifact — nothing hand-entered.
> Canonical protocol (locked in `ewsmart.experiments.CANONICAL_PROTOCOL`):
> **24 bands × 3000 slots × 50 episodes, `base_seed=9000`**, identical for all schedulers.

### Monte Carlo Evaluation — `results/benchmark.json`

Mean ± 95% CI across 50 episodes (`python -c "from ewsmart.experiments import benchmark_report; benchmark_report()"`):

| Scheduler | Avg Reward | Threat Coverage | Pred Accuracy | Mission Capable? |
|---|---|---|---|---|
| Sequential Sweep | 0.186 ± 0.004 | 0.775 ± 0.024 | 0.461 | ❌ |
| Random Scan | 0.188 ± 0.005 | 0.975 ± 0.012 | 0.460 | ❌ |
| Priority Sweep | 0.186 ± 0.004 | 0.765 ± 0.027 | 0.461 | ❌ |
| UCB Bandit | 0.900 ± 0.013 | 0.527 ± 0.026 | 0.995 | ❌ (coverage fail) |
| Linear Q-Learning | 0.449 ± 0.048 | 0.880 ± 0.029 | 0.184 | ❌ |
| Deep Q-Network | 0.200 ± 0.031 | 0.887 ± 0.024 | 0.426 | ❌ |
| **SmartScan** | **0.471 ± 0.014** | **0.920 ± 0.016** | **0.545** | **✅ YES** |

The same artifact reports the full FoM set (intercept rate, false-alarm rate,
time-to-first-intercept, intercept-time prediction error, ambiguous co-channel
hit rate), per-scheduler **agile-hop follow rates**, the observation-only
next-hop prediction benchmark, and attribution-conservation checks.

### Agile-Hop Prediction vs Coverage (reported separately)

- **Observation-only next-hop prediction** (Markov/structured agility):
  transition model **top-1 0.394 / top-3 0.740** (missed-opportunity 0.260) vs
  0.063 top-1 for a uniform guesser; random-mode agility numbers are in the
  artifact for comparison.
- **Policy-level hop coverage** is measured post hoc for *every* scheduler
  (fraction of agile hops whose destination band was dwelt within 8 slots) —
  see the "Agile-hop follow rate by scheduler" table in `results/benchmark.md`.

### Mission Effectiveness (KPP-Gated) — `results/suite_results.json`

Hard Key Performance Parameters gate first, then composite ranking (defence T&E practice):

| KPP Gate | Threshold | SmartScan |
|---|---|---|
| Threat Coverage | ≥ 0.90 | ✅ **0.903** |
| Prediction Accuracy | ≥ 0.50 | ✅ **0.548** |
| False Alarm Rate | ≤ 5×10⁻⁴/slot | ✅ **3.3×10⁻⁵** |
| **Mission Status** | | **✅ CAPABLE — #1 RANKED (MES 0.619)** |

> **SmartScan is the only mission-capable scheduler in the field.**
> UCB posts the top raw reward but misses 47% of threats — disqualified by the
> coverage KPP. On raw reward SmartScan does **not** beat the exploit-only UCB
> bandit (by design); on the gated Mission Effectiveness Score it beats every
> comparator at **p ≤ 1e-4** (paired permutation, Holm-corrected).

### Supporting Evidence

- **2.5× sequential scan's reward** (0.471 vs 0.186) with **+14 points of threat coverage**
- **Multi-receiver scaling** (`suite_results.json`): total reward 663 → 1192 → 1808 for 1 → 2 → 3 SmartScan receivers (sequential: 365 → 720 → 1067), with **coverage integrity 1.0** — zero duplicate dwells in every episode (de-confliction working)
- **Geolocation:** CEP50 improves 3.2 km → 1.69 km with 2 → 4 receivers
- **Identification:** 86% (14/19 streams) on the synthetic reference episode's built-in JC Wise-style library — simulation-only evidence, not recorded-RF identification
- **Decision latency** (`results/performance.json`, Windows 11 / AMD Ryzen): SmartScan mean **0.35 ms**, DQN **0.47 ms** per decision (limit 1 ms); p95 ≈ 1.2 ms for both — tail spikes exist and are recorded rather than hidden

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  COMMAND CENTRE (React + Vite + FastAPI)                         │
│  Mission · Benchmarks · Live Ops (A/B Arena) · Traceability     │
├──────────────────────────────────────────────────────────────────┤
│  DESKTOP APP (Qt WebEngine)          │  WEBSITE (Vite + Vercel) │
│  System tray · Native window         │  Docs · Console          │
├──────────────────────────────────────────────────────────────────┤
│  LIVE INGESTION (simulated feed │ UDP bridge │ log tail)         │
├──────────────────────────────────────────────────────────────────┤
│  EXPLOITATION (ID library matching │ AOA triangulation)          │
├──────────────────────────────────────────────────────────────────┤
│  SCHEDULERS (SmartScan + 6 references)                           │
├──────────────────────────────────────────────────────────────────┤
│  RECEIVER MODEL (logistic Pd │ false alarms │ AOA │ PDWs)       │
├──────────────────────────────────────────────────────────────────┤
│  ENVIRONMENT (stationary │ agile │ periodic │ scanning emitters) │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
astra/
├── ewsmart/                  # Core library
│   ├── config.py             # JSON-serialisable scenario configuration
│   ├── environment.py        # Battlefield simulation + truth matrix
│   ├── receiver.py           # Detection physics, AOA, PDWs
│   ├── schedulers.py         # 7 policies including SmartScan
│   ├── dqn.py                # Deep Q-Network (NumPy MLP + replay)
│   ├── periodic.py           # Rayleigh period estimator
│   ├── metrics.py            # FoMs + KPP-gated MES scoring
│   ├── multireceiver.py      # Cooperative multi-platform teams
│   ├── identification.py     # Emitter ID library matching
│   ├── geo.py                # AOA triangulation / geolocation
│   ├── experiments.py        # Monte Carlo + ROC + sensitivity + ablation
│   ├── runner.py             # Episode simulation & CLI
│   ├── persistence.py        # Safe .npz save/load (no pickle)
│   ├── live.py               # Real-time ingestion pipeline
│   ├── viz.py                # Publication-quality chart generation
│   └── dataset.py            # Turing/HuggingFace dataset loaders
│
├── server/                   # FastAPI command centre backend
│   ├── api.py                # REST API + SSE live arena
│   ├── livesim.py            # Paired A/B simulation thread
│   └── sources.py            # Data source management
│
├── frontend/                 # React + Vite command centre UI
├── website/                  # Presentation website (Vite + Vercel)

├── desktop_qt.py             # Qt-based desktop application
│
├── scenarios/                # JSON battle configurations
├── models/                   # Trained scheduler weights (.npz)
├── results/                  # Generated evaluation data
├── figures/                  # Publication-quality charts
├── tests/                    # 306 automated tests
├── tools/                    # Utilities
│   ├── sdr_bridge.py         # UDP/CSV bridge for real SDR hardware
│   ├── export_site_data.py   # Bake results/figures/manual into website
│   ├── cleanup_dist.py       # Prune the PyInstaller build tree
│   ├── create_ppt.py         # Generate the pitch deck
│   ├── build_exe.ps1         # PyInstaller build script
│   └── sign_all.ps1          # Installer signing helpers
│
├── docs/                     # VitePress documentation site
├── assets/                   # Brand assets (logo, icons)
├── installer/                # Windows installer (NSIS)
├── Dockerfile                # Multi-stage Docker image
├── pyproject.toml            # Package metadata & dependencies
├── START.bat                 # One-click launcher
└── launch.ps1                # PowerShell launcher
```

---

## 📡 Live Hardware Integration

ASTRA can ingest real PDW streams from SDR or radar hardware over UDP:

```powershell
# Bridge a CSV sweep file from your SDR
python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555

# Relay an existing JSON PDW feed
python tools/sdr_bridge.py --mode udp --in-port 5000 --out-port 5555
```

Then select **UDP bridge (real hardware)** on the Live Radar page.

**PDW Schema:** `toa_us, freq_mhz, pw_us, pa_db, aoa_deg` — the standard ESM measurement set.

---

## 🖥️ Deliverables

| Deliverable | Location | Description |
|---|---|---|
| **Desktop Application** | `dist/ASTRA/`, `installer/` | Native Windows app (~131 MB), signed by Team MCS |
| **React Command Centre** | `frontend/` | Mission · Benchmarks · Live A/B Arena · Traceability |
| **Presentation Website** | `website/` | Static site deployable to Vercel with documentation & console |
| **Software Manual** | `docs/` | Complete A-Z documentation, viewable in-app |

---

## 🧪 Testing

306 automated tests covering all layers of the system:

```powershell
# Run all tests
python -m pytest tests -q
```

| Test Suite | Scope |
|---|---|
| `test_smartscan.py` | SmartScan scheduler end-to-end dominance |
| `test_modules.py` | Environment, receiver, estimators, all schedulers, persistence |
| `test_live.py` | Live radar streaming, UDP round-trip |
| `test_mission.py` | KPP/MES scoring engine |
| `test_api.py` | FastAPI endpoints + live arena |
| `test_id_geo_stats.py` | Identification, geolocation, statistical tests |
| `test_software.py` | JSON safety, model artifacts, engineering guarantees |
| `test_target99_gaps.py` | Emitter attribution, agile-hop prediction (leakage-free), SmartScan learned-value ablations, canonical benchmark artifact |

---

## 🔒 Engineering Guarantees

- ✅ **Valid JSON everywhere** — `json_safe()` strips NaN/Inf; outputs parse with strict parsers
- ✅ **Safe model artifacts** — NPZ + JSON metadata, loaded with `allow_pickle=False`
- ✅ **Independent receiver noise** — every platform realises its own noise floor
- ✅ **Seed-exact reproducibility** — every scenario is a seed + JSON config
- ✅ **No exotic dependencies** — NumPy + Matplotlib core; FastAPI + React for UI only
- ✅ **Docker image** — multi-stage build, one-command reproducible environment

---

## 🌐 Website Deployment (Vercel)

```powershell
python tools/export_site_data.py       # Bake results/figures/manual into website/
cd website; npm run build              # Static output in website/dist
cd ..; npx vercel deploy --prod        # Or just: powershell -File deploy.ps1
```

The repository-root `vercel.json` publishes the pre-built `website/dist` with no
build step on Vercel, which is why the bundle is committed:

- **Root Directory** must stay at the repository root so the root `vercel.json`
  is read (`outputDirectory: website/dist`). Do not point it at `website`.
- `website/vercel.json` only adds clean URLs for a standalone/root-domain deploy.
- `deploy.ps1` (repo root) rebuilds, deploys to production and then HTTP-checks
  the live routes.

**Verify before you deploy** — one command runs the whole site gate:

```powershell
cd website; npm run check
```

| Step | What it proves |
|---|---|
| `npm run docs:check` | every manual section slices out of the generated HTML, no mojibake |
| `npm run smoke` | server-renders Home, Documentation, Console and Results; asserts headline copy is present and audits markup (unique ids, resolvable in-page links, one `<h1>`) |
| `npm run build` | the production bundle builds clean |
| `npm run verify:dist` | the built bundles still contain each page's class hooks, every asset the HTML references exists, and the no-flash theme bootstrap survived |

The engine parity check is separate and lives in
[`HOW_TO_TEST.md`](HOW_TO_TEST.md) (Level 7): `node scripts\_bundle.cjs ; node scripts\_smoke.cjs`
→ `ENGINE SMOKE OK`.

**Troubleshooting:** if `https://astra-ew.vercel.app/` answers
`404 DEPLOYMENT_NOT_FOUND`, the Vercel project or its deployment was removed —
nothing is wrong with the code. Run `npx vercel login`, `npx vercel link`
(project `astra-ew`), then `powershell -File deploy.ps1` to republish.

---

## 📖 Documentation

| Document | Description |
|---|---|
| [`PROJECT_EXPLAINED.md`](PROJECT_EXPLAINED.md) | Plain-language walkthrough of the entire system |
| [`EVALUATION.md`](EVALUATION.md) | Judge self-assessment scorecard with honest gaps |
| [`HOW_TO_TEST.md`](HOW_TO_TEST.md) | Step-by-step testing guide |
| [`docs/`](docs/) | Complete VitePress documentation site |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [`LICENSE`](LICENSE) file for details.

> **Note:** This is a prototype developed for the Smart India Hackathon 2026 problem statement "Development of a Smart Scan Strategy for Electronic Warfare". It is simulation-based research software and is not operational equipment.

---

<p align="center">
  <sub>Built with ❤️ for <strong>Smart India Hackathon 2026</strong></sub>
</p>
