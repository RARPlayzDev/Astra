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
  <img src="https://img.shields.io/badge/tests-222_passing-10b981?style=for-the-badge&label=tests" alt="Tests" />
  <img src="https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/installer-131_MB-8b5cf6?style=for-the-badge" alt="Installer" />
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
# Pre-built installer available at: installer/ASTRA-Setup-2.0.0.exe
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

SmartScan is not a single algorithm — it is a **confidence-multiplexed control system** that activates five behaviours based on learned evidence:

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
| 5 | **Value-Weighted Rotation** | Always (fallback) | Band starvation; over-commitment |

**Key innovations:**
- **Online lock validation** — predictions must keep coming true; stale locks self-destruct
- **SNR+AOA fingerprinting** — co-channel emitters stay separated; same-source locks merge
- **Cheap falsification** — wrong hypotheses die fast and cost only one slot

---

## 📊 Results

### Monte Carlo Evaluation

200 held-out episodes · 24 bands × 3000 slots · mean ± 95% CI:

| Scheduler | Avg Reward | Threat Coverage | Pred Accuracy | Mission Capable? |
|---|---|---|---|---|
| Sequential Sweep | 0.196 ± 0.003 | 0.779 ± 0.013 | 0.458 | ❌ |
| Random Scan | 0.197 ± 0.003 | 0.977 ± 0.006 | 0.458 | ❌ |
| Priority Sweep | 0.196 ± 0.003 | 0.785 ± 0.013 | 0.458 | ❌ |
| UCB Bandit | 0.942 ± 0.005 | 0.540 ± 0.015 | 0.988 | ❌ (coverage fail) |
| Linear Q-Learning | 0.474 ± 0.025 | 0.896 ± 0.012 | 0.190 | ❌ |
| Deep Q-Network | 0.269 ± 0.021 | 0.895 ± 0.012 | 0.387 | ❌ |
| **SmartScan** | **0.417 ± 0.005** | **0.950 ± 0.009** | **0.581** | **✅ YES** |

### Mission Effectiveness (KPP-Gated)

Following defence T&E practice — hard Key Performance Parameters gate first, then composite ranking:

| KPP Gate | Threshold | SmartScan |
|---|---|---|
| Threat Coverage | ≥ 0.90 | ✅ **0.950** |
| Prediction Accuracy | ≥ 0.50 | ✅ **0.581** |
| False Alarm Rate | ≤ 5×10⁻⁴/slot | ✅ **PASS** |
| **Mission Status** | | **✅ CAPABLE — #1 RANKED** |

> **SmartScan is the only mission-capable scheduler in the field.**
> UCB posts the top raw reward but misses 46% of threats — disqualified by coverage KPP.
> Statistical significance: SmartScan > every comparator at **p < 1e-4** (Holm-corrected).

### Supporting Evidence

- **2.1× sequential scan's reward** with **+17 points of threat coverage**
- **Multi-receiver scaling:** 601 → 1101 → 1898 total reward for 1 → 2 → 3 receivers
- **Geolocation:** CEP improves 3.2 km → 1.7 km with 2 → 4 receivers
- **Identification:** 100% accuracy on reference episode vs JC Wise-style library

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
├── tests/                    # 222 automated tests
├── tools/                    # Utilities
│   ├── sdr_bridge.py         # UDP/CSV bridge for real SDR hardware
│   ├── pdw_generator.py      # Synthetic PDW stream generator
│   ├── export_site_data.py   # Bake results into website
│   ├── build_exe.ps1         # PyInstaller build script
│   └── make_brand_assets.py  # Logo/icon generator
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

222 automated tests covering all layers of the system:

```powershell
# Run all tests
python -X utf8 tests/test_smartscan.py
python -X utf8 tests/test_modules.py
python -X utf8 tests/test_live.py
python -X utf8 tests/test_mission.py
python -X utf8 tests/test_api.py
python -X utf8 tests/test_software.py
python -X utf8 tests/test_id_geo_stats.py
python -X utf8 tests/test_software.py
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
cd website
npm install && npm run build           # Static output in website/dist
npx vercel deploy --prod               # Or import repo in Vercel dashboard
```

Set **Root Directory** = `website` in Vercel dashboard. `vercel.json` enables clean URLs.

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
