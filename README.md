<p align="center">
  <img src="assets/astra_mark_512.png" alt="ASTRA" width="120" />
</p>

<h1 align="center">ASTRA</h1>
<h3 align="center">Adaptive Spectrum Threat Recognition &amp; Analysis</h3>

<p align="center">
  Version 3.0.0 · Smart India Hackathon 2026 problem statement
  <em>“Development of a Smart Scan Strategy for Electronic Warfare”</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-%E2%89%A53.10-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License" />
  <img src="https://img.shields.io/badge/tests-306-10b981?style=flat-square" alt="Tests" />
</p>

---

## What this is

ASTRA schedules the dwells of an Electronic Support (ES) receiver. Such a
receiver can listen to one narrow band at a time, so at every time slot a policy
chooses a band, the receiver observes a hit, a miss or a false alarm, and the
policy updates. The task is to intercept as many emitters as possible, as early
as possible, without knowing their frequencies in advance.

What is in the repository:

| Path | Contents |
|---|---|
| `ewsmart/` | RF environment, receiver physics (detection, AOA, PDWs), seven schedulers, metrics, multi-receiver coordination, identification, geolocation, experiment harness |
| `server/` | FastAPI service: benchmarks, figures, manual, live A/B arena, source management |
| `frontend/` | React command centre (Home, Operations, Analysis, Intelligence, Data Sources, Geolocation) |
| `desktop_qt.py`, `desktop.py` | Desktop application (Qt WebEngine window, or a browser window fallback) |
| `website/` | Presentation site (Vite), pre-built bundle committed in `website/dist` for Vercel |
| `docs/` | Documentation site and the full software manual |
| `tests/` | 306 pytest tests |

> **Scope.** Simulation-based research software built for a hackathon
> submission. Emitters, propagation, detection and false alarms are modelled in
> software — there is no recorded RF data, no radar hardware, no classified
> material and nothing here is operational equipment.

---

## Requirements

| Dependency | Needed for |
|---|---|
| Python ≥ 3.10 | everything |
| Node.js ≥ 18 | building `frontend/` and `website/` |
| PyInstaller | rebuilding the desktop bundle `dist/ASTRA/` |
| Inno Setup 6 (`ISCC.exe`) | rebuilding `installer/*.exe` |

## Install

```powershell
git clone https://github.com/RARPlayzDev/Astra.git
cd Astra
python -m pip install -e ".[dev]"
```

The base install is `numpy`, `fastapi`, `uvicorn`, `markdown` and `matplotlib`
(`matplotlib` is imported by `ewsmart/viz.py` and `ewsmart/experiments.py`).
`[dev]` adds `pytest` and `pytest-cov`; the optional `[hf]` extra adds
`datasets` for the HuggingFace calibration path in `ewsmart/dataset.py`.

## Run

```powershell
# one episode with every scheduler → results.json and models/*.npz
python -m ewsmart.runner --scenario scenarios/demo.json --save-dir models --json-out results.json

# full Monte Carlo suite → results/*.json and figures/*.png
python -m ewsmart.experiments --suite full
python -m ewsmart.experiments --suite quick     # fast pass
```

The same entry points are installed as the console scripts `ewsmart-run` and
`ewsmart-experiments`. Two scenarios ship with the repository —
`scenarios/demo.json` and `scenarios/dense_low_snr.json`; further configurations
are produced by `ewsmart.config`.

### Web console and API

```powershell
cd frontend; npm install; npm run build; cd ..
python -m uvicorn server.api:app --port 8000
# http://localhost:8000 — OpenAPI schema at /api-docs
```

### Desktop application

```powershell
python desktop_qt.py     # Qt WebEngine window with a system-tray icon
python desktop.py        # serves the same app and opens the default browser
```

`START.bat` and `launch.ps1` are one-click launchers for the same thing.

### Windows installer

`installer/astra_installer.iss` (Inno Setup) packages the PyInstaller output
from `dist/ASTRA/`; build that first with `tools\build_exe.ps1`.

The installer itself is **not stored in the repository** — `*.exe` is ignored
and release binaries live on the GitHub releases page. The 3.0.0 build is
`ASTRA-Setup-3.0.0.exe`, 164,456,208 bytes, SHA-256
`139BFAE2271A1DBB5DC789FCF1698B54AB241F307C868A055B484EAE18DFA362`. It is **not
code-signed**, so Windows SmartScreen warns on first launch; sign it with your
own certificate before distributing.

### Docker (optional)

```powershell
docker build -t astra .
docker run -p 8000:8000 astra
```

The Dockerfile builds the frontend in a Node stage, then serves the API and the
built SPA from a Python image. It is a convenience environment — the desktop
application and the installer are the primary deliverables.

`results/` and `figures/` are git-ignored build products, so the image starts
without them (the API reports an empty benchmark/figures payload). Mount a local
run of the experiment suite to serve the published numbers instead:

```powershell
docker run -p 8000:8000 -v "${PWD}/results:/app/results" -v "${PWD}/figures:/app/figures" astra
```

---

## Results

Every number below is written by `python -m ewsmart.experiments --suite full`
into `results/` (generated, not committed). The canonical protocol
(`ewsmart.experiments.CANONICAL_PROTOCOL`) is **24 bands × 3000 slots ×
50 episodes, `base_seed=9000`**, identical for every scheduler.

### Monte Carlo evaluation — `results/benchmark.json`

Mean ± 95% CI across 50 episodes
(`python -c "from ewsmart.experiments import benchmark_report; benchmark_report()"`):

| Scheduler | Avg Reward | Threat Coverage | Pred Accuracy | Mission Capable? |
|---|---|---|---|---|
| Sequential Sweep | 0.186 ± 0.004 | 0.775 ± 0.024 | 0.461 | ❌ |
| Random Scan | 0.188 ± 0.005 | 0.975 ± 0.012 | 0.460 | ❌ |
| Priority Sweep | 0.186 ± 0.004 | 0.765 ± 0.027 | 0.461 | ❌ |
| UCB Bandit | 0.900 ± 0.013 | 0.527 ± 0.026 | 0.995 | ❌ (coverage gate) |
| Linear Q-Learning | 0.449 ± 0.048 | 0.880 ± 0.029 | 0.184 | ❌ |
| Deep Q-Network | 0.200 ± 0.031 | 0.887 ± 0.024 | 0.426 | ❌ |
| **SmartScan** | **0.471 ± 0.014** | **0.920 ± 0.016** | **0.545** | **✅** |

The same artifact reports the full figure-of-merit set (intercept rate,
false-alarm rate, time-to-first-intercept, intercept-time prediction error,
ambiguous co-channel hit rate), per-scheduler agile-hop follow rates, the
observation-only next-hop prediction benchmark and attribution-conservation
checks.

### Agile-hop prediction vs coverage (reported separately)

- Observation-only next-hop prediction (Markov/structured agility): transition
  model **top-1 0.394 / top-3 0.740** (missed-opportunity 0.260) against 0.063
  top-1 for a uniform guesser. Random-mode agility figures are in the artifact.
- Policy-level hop coverage is measured post hoc for *every* scheduler as the
  fraction of agile hops whose destination band was dwelt within 8 slots (table
  in `results/benchmark.md`).

### Mission effectiveness (KPP-gated) — `results/suite_results.json`

Hard Key Performance Parameters gate first, composite ranking second:

| KPP gate | Threshold | SmartScan |
|---|---|---|
| Threat coverage | ≥ 0.90 | 0.903 |
| Prediction accuracy | ≥ 0.50 | 0.548 |
| False-alarm rate | ≤ 5×10⁻⁴ /slot | 3.3×10⁻⁵ |
| Mission status | | CAPABLE — rank 1 (MES 0.619) |

SmartScan is the only scheduler that clears all three gates in this field. UCB
posts the top raw reward (0.900) but covers only 0.527 of the threats, so the
coverage gate disqualifies it. On raw reward SmartScan does *not* beat UCB; on
the gated Mission Effectiveness Score it leads every comparator at
p ≤ 1e-4 (paired permutation, Holm-corrected).

### Supporting measurements

- 2.5× sequential scan's reward (0.471 vs 0.186) and +14 points of threat coverage.
- Multi-receiver scaling (1 → 2 → 3 SmartScan receivers): total reward 663 → 1192
  → 1808 (sequential 365 → 720 → 1067), coverage integrity 1.0 — no duplicate
  dwells in any episode.
- Geolocation: CEP50 improves from 3.2 km to 1.69 km going from 2 to 4 receivers.
- Identification: 86% (14/19 streams) on the reference episode's built-in
  library — library matching against synthetic signatures, not recorded-RF ID.
- Decision latency (`results/performance.json`, Windows 11 / AMD Ryzen): mean
  0.35 ms for SmartScan and 0.47 ms for the DQN against a 1 ms limit; p95 ≈ 1.2 ms
  for both, i.e. the tail is recorded rather than hidden.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Command centre (React + Vite)  ·  FastAPI service               │
│  Mission · Benchmarks · Live A/B arena · Traceability            │
├──────────────────────────────────────────────────────────────────┤
│  Desktop app (Qt WebEngine)        │  Website (Vite → Vercel)    │
├──────────────────────────────────────────────────────────────────┤
│  Live ingestion (simulated feed · UDP bridge · log tail)         │
├──────────────────────────────────────────────────────────────────┤
│  Exploitation (ID library matching · AOA triangulation)          │
├──────────────────────────────────────────────────────────────────┤
│  Schedulers (SmartScan + 6 reference policies)                   │
├──────────────────────────────────────────────────────────────────┤
│  Receiver model (logistic Pd · false alarms · AOA · PDWs)        │
├──────────────────────────────────────────────────────────────────┤
│  Environment (stationary · agile · periodic · scanning emitters) │
└──────────────────────────────────────────────────────────────────┘
```

### How SmartScan decides

Six behaviours are activated from learned evidence:

| # | Behaviour | Active when | Mitigates |
|---|---|---|---|
| 1 | Recon sweep | episode start / little evidence | acting on no information |
| 2 | Cued pursuit | validated phase locks exist | missing predictable targets |
| 3 | Predict & probe | candidate rhythm, unproven | never testing a hypothesis |
| 4 | Burst characterisation | isolated hit on a quiet fingerprint | under-sampling rare emitters |
| 5 | Agile-hop anticipation | frequent hops on a tracked stream | losing agile emitters between hops |
| 6 | Value-weighted rotation | always (fallback) | band starvation |

Mechanisms: online lock validation (predictions must keep coming true, stale
locks are dropped), SNR+AOA fingerprinting so co-channel emitters stay apart, a
per-stream transition model for agile hops learned only from observed
detections, and one-slot falsification of wrong hypotheses.

---

## Repository layout

```
Astra/
├─ ewsmart/                    # core library
│  ├─ config.py                # scenario configuration (JSON round-trip)
│  ├─ environment.py           # RF environment + emitter truth
│  ├─ receiver.py              # detection physics, false alarms, AOA, PDWs
│  ├─ aoa.py                   # AOA measurement maths
│  ├─ deinterleave.py          # PDW deinterleaving, matched-filter gain
│  ├─ schedulers.py            # SmartScan + 6 reference policies
│  ├─ prediction.py            # agile-hop transition model
│  ├─ periodic.py              # period estimation
│  ├─ dqn.py                   # DQN agent (NumPy)
│  ├─ metrics.py               # figures of merit + KPP-gated MES
│  ├─ multireceiver.py         # cooperative teams, de-confliction
│  ├─ identification.py        # emitter ID library matching
│  ├─ geo.py                   # AOA triangulation, CEP statistics
│  ├─ experiments.py           # canonical suite, ROC, sensitivity, ablation
│  ├─ runner.py                # episode runner + CLI
│  ├─ persistence.py           # npz + JSON artifacts (allow_pickle=False)
│  ├─ live.py, realtime.py     # ingestion pipelines
│  ├─ dataset.py, calibration.py
│  ├─ db.py                    # SQLite trace store
│  ├─ viz.py                   # matplotlib figure generation
│  └─ meta.py, sigtests.py, frontend.py, exceptions.py
├─ server/                     # api.py, livesim.py, sources.py
├─ frontend/                   # React command centre
├─ website/                    # presentation site (dist/ committed for Vercel)
├─ desktop_qt.py, desktop.py   # desktop application entry points
├─ scenarios/                  # demo.json, dense_low_snr.json
├─ models/                     # trained weights (*.npz, git-ignored)
├─ results/, figures/          # generated artifacts
├─ tests/                      # 306 tests
├─ tools/                      # build and export utilities
├─ docs/                       # documentation site + software manual
├─ installer/                  # astra_installer.iss (Inno Setup)
├─ assets/                     # brand assets
├─ Dockerfile, vercel.json, deploy.ps1, START.bat, launch.ps1
└─ pyproject.toml, requirements.txt, LICENSE
```

---

## Live PDW ingestion

`tools/sdr_bridge.py` bridges a sensor or a file feed into the live pipeline:

```powershell
python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555
python tools/sdr_bridge.py --mode udp --in-port 5000  --out-port 5555
```

Then select the UDP bridge as the data source in the app. PDW schema:
`toa_us, freq_mhz, pw_us, pa_db, aoa_deg`. The bridge transports whatever the
sensor emits; the calibration and detection models shipped here are simulated.

---

## Testing

```powershell
python -m pytest tests -q        # 306 tests
```

`tests/test_performance.py` is the only wall-clock suite: it asserts a mean of
under 1 ms per scheduler decision (best of three identical passes, plus one
documented retry). It therefore measures the host as much as the code — run it on
an otherwise idle machine, and read `results/performance.json`, which stamps the
platform the numbers came from.

| File | Scope |
|---|---|
| `test_smartscan.py` | SmartScan scheduler end to end |
| `test_schedulers_edge.py` | boundary behaviour of all seven policies |
| `test_modules.py` | environment, receiver, estimators, persistence, plots |
| `test_mission.py` | KPP / MES scoring engine |
| `test_api.py` | FastAPI endpoints and the live arena |
| `test_id_geo_stats.py` | identification, geolocation, statistical tests |
| `test_software.py` | JSON safety, model artifacts, engineering guarantees |
| `test_target99_gaps.py` | attribution, agile-hop prediction, canonical artifact |
| `test_experiments_viz.py` | experiment harness and figure generation |
| `test_fidelity_upgrades.py` | simulation-fidelity changes |
| `test_geo_ml.py` | geolocation and ML components |
| `test_live.py` | live streaming, UDP round trip |
| `test_performance.py` | decision-latency budget |
| `test_ps_gaps.py` | problem-statement coverage gaps |
| `test_repair_bundle.py` | regression bundle |
| `test_result_schema.py` | result-artifact schema |

---

## Engineering notes

- **JSON everywhere** — `json_safe()` strips NaN/Inf, so artifacts parse with strict parsers.
- **Safe model artifacts** — npz + JSON metadata, loaded with `allow_pickle=False`.
- **Independent receiver noise** — every platform realises its own noise floor.
- **Seed-exact reproducibility** — a scenario is a seed plus a JSON config; see [`docs/reproducibility.md`](docs/reproducibility.md).
- **Runtime dependencies** — `numpy`, `fastapi`, `uvicorn`, `markdown` and `matplotlib` (the last only for figure generation).

---

## Website

```powershell
python tools/export_site_data.py      # bake results/figures/manual into website/
cd website; npm run check             # docs:check · smoke · build · verify:dist
npm run build                         # static output in website/dist
cd ..; powershell -File deploy.ps1    # build + vercel --prod + route check
```

The root [`vercel.json`](vercel.json) publishes the committed `website/dist`
with no build step (`outputDirectory: website/dist`), which is why the bundle is
tracked:

- **Root Directory** must stay at the repository root so the root `vercel.json`
  is read. Do not point it at `website`.
- `website/vercel.json` only adds clean URLs for a standalone/root-domain deploy.
- `deploy.ps1` rebuilds, deploys to production, then HTTP-checks the live routes.

Run `npm run check` before deploying: it runs the manual-section check, the
server-render smoke test, the production build and the dist-bundle verification
in sequence.

If `https://astra-ew.vercel.app/` answers `404 DEPLOYMENT_NOT_FOUND`, the Vercel
project or its deployment was removed — the code is unaffected. Run
`npx vercel login`, `npx vercel link` (project `astra-ew`) and
`powershell -File deploy.ps1` to republish.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/ASTRA_Software_Documentation.md`](docs/ASTRA_Software_Documentation.md) | the software manual — served by the app at `/manual` and rendered by the website |
| [`docs/`](docs/) | documentation site: concepts, guides, integration, reference, tutorials |
| [`HOW_TO_TEST.md`](HOW_TO_TEST.md) | step-by-step verification ladder |
| [`docs/reproducibility.md`](docs/reproducibility.md) | how the published numbers are reproduced |
| [`docs/changelog.md`](docs/changelog.md) | change log |

---

## Known limitations

- **Simulation only.** No recorded RF and no hardware-in-the-loop measurements.
  Agility is synthetic (random or Markov), and the agile-hop follow-rate gain
  over a blind sweep is modest.
- **Identification** is library matching against synthetic signatures, not
  identification of recorded emitters.
- **Latency** was measured on one Windows 11 / AMD Ryzen machine; the p95 tail
  is roughly 3× the mean.
- **The installer is unsigned**, and the desktop bundle in `dist/ASTRA/` is a
  local build product rather than a repository artifact.
- **Docker** is provided as a convenience environment and was not rebuilt during
  the last verification pass.

---

## Contributing

1. Fork the repository and create a branch (`git checkout -b feature/name`).
2. Keep `python -m pytest tests -q` green, and run `cd website; npm run check`
   if you touched the site.
3. Open a pull request describing the change and the evidence behind it.

---

## License

MIT — see [`LICENSE`](LICENSE).

Prototype developed for the Smart India Hackathon 2026 problem statement
*“Development of a Smart Scan Strategy for Electronic Warfare”*. It is
simulation-based research software, not operational equipment.
