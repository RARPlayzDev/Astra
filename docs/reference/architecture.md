# Architecture

## System overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Desktop Application                          │
│  ┌─────────────┐  ┌──────────────────────────────────────────┐  │
│  │ desktop.py   │  │  frontend/ (React SPA)                    │  │
│  │ (pywebview   │  │  ┌──────┬──────┬────────┬─────┬──────┐  │  │
│  │  or Qt)      │  │  │ Home │ Ops  │Analysis│Intel│ Geo  │  │  │
│  └──────┬───────┘  │  └──────┴──────┴────────┴─────┴──────┘  │  │
│         │          └────────────────────┬─────────────────────┘  │
│         │          ┌────────────────────┴─────────────────────┐  │
│         │          │  server/ (FastAPI + uvicorn)              │  │
│         │          │  ┌─────────────────────────────────────┐  │  │
│         └──────────┤  │  api.py  ·  livesim.py  · sources.py│  │  │
│                    │  └──────────────────┬──────────────────┘  │  │
│                    └─────────────────────┼─────────────────────┘  │
│                    ┌─────────────────────┴─────────────────────┐  │
│                    │  ewsmart/ (core library)                   │  │
│                    │  ┌──────────┬───────────┬──────────────┐  │  │
│                    │  │scheduler │environment│  receiver     │  │  │
│                    │  │metrics   │experiments│  identification│ │  │
│                    │  │geo       │live       │  persistence  │  │  │
│                    │  │periodic  │multirecvr │  dataset      │  │  │
│                    │  └──────────┴───────────┴──────────────┘  │  │
│                    └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Module map

| Module | Purpose | Lines |
|---|---|---|
| `schedulers.py` | 8 scheduling policies (SmartScan, UCB, Q-Learning, DQN, Seq, Rand, Priority, MetaScheduler) | ~1200 |
| `environment.py` | RF scene: 6 emitter classes, occupancy truth matrix, Counter-ESM evasion | ~500 |
| `receiver.py` | Narrowband detection physics, AOA, PDW generation, `report_intercept` | ~300 |
| `metrics.py` | 11 figures of merit, KPP gate, MES, Trace | ~250 |
| `experiments.py` | Monte Carlo, significance, ROC, sensitivity, ablation, multi-receiver, meta-learning | ~600 |
| `multireceiver.py` | CooperativeTeam with DND token de-confliction | ~200 |
| `identification.py` | Emitter fingerprinting, library matching, JC Wise profiles | ~300 |
| `geo.py` | AOA geolocation, triangulation, CEP, bearing simulation | ~200 |
| `live.py` | LiveSpectrum, OnlineScanner, SimulatedLiveSource, UDPSource, FileTailSource | ~350 |
| `periodic.py` | Rayleigh period estimation, integer refinement | ~150 |
| `persistence.py` | Model save/load (pickle-free .npz) | ~100 |
| `dataset.py` | PDW import, HuggingFace + offline fallback | ~200 |
| `dqn.py` | DQN agent (MLP + replay + target network) | ~250 |
| `sigtests.py` | Paired permutation tests, Holm-Bonferroni correction | ~150 |
| `viz.py` | Matplotlib visualization helpers | ~200 |
| `config.py` | ScenarioConfig dataclass | ~80 |

## Data flow

```
1. RFEnvironment generates truth matrix (emitter × band × time)
   ↓
2. ESReceiver.dwell(band, t) → DwellResult (hit, SNR, AOA, PDW)
   ↓
3. Scheduler.select(t) → band choice
   ↓
4. Scheduler.update(t, band, result, reward) → learn from outcome
   ↓
5. compute_metrics(trace) → 11 figures of merit
   ↓
6. mission_scores(metrics) → KPP gate + MES ranking
```

## Threading model

- **Main thread**: PySide6/Qt event loop or pywebview
- **Server thread**: FastAPI + uvicorn (daemon thread)
- **Arena thread**: Live simulation loop (daemon thread)
- **Source threads**: One per attached sensor source (daemon)
