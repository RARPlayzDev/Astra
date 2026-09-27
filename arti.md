# ASTRA — Architecture Diagrams

Canonical architecture views for the ASTRA Cognitive ES Smart Scan system.
Every box below maps to a real module in this repository (paths in brackets).
Rendered best in any Markdown viewer with Mermaid support (GitHub, VS Code).

---

## 0. Full technology stack (layer cake)

One diagram covering every technology in the system, bottom to top —
hardware/runtime up to the user. Versions match `requirements.txt`,
`pyproject.toml`, `frontend/package.json` and `website/package.json`.

```mermaid
flowchart TB
    subgraph L6["L6 · Delivery surfaces"]
        EXE["Desktop app\nASTRA.exe — PyInstaller (astra.spec)\ndesktop.py (pywebview/Edge) · desktop_qt.py (PySide6)"]
        WEBD["Website — Vite 5 static build\nvercel.json · Dockerfile\nnode:22-slim → python:3.11-slim"]
        INST["Installer — Inno Setup\ninstaller/astra_installer.iss"]
    end

    subgraph L5["L5 · UI frameworks"]
        REACT["Desktop console — React 18 + TypeScript 5.6\nfrontend/ (Operations · Analysis · Data)"]
        WTS["Website console — React + TS\nwebsite/src (Console · Home · Docs)\nengine/ = TS parity port"]
    end

    subgraph L4["L4 · API / realtime"]
        FA["FastAPI >= 0.110\nserver/api.py — REST + SSE"]
        UV["Uvicorn >= 0.29\nASGI server (threaded in desktop app)"]
        MK["markdown — /manual renderer"]
    end

    subgraph L3["L3 · Core engine (Python 3.10+)"]
        PY["Python 3.11 runtime"]
        NUMPY["NumPy >= 1.26\nvectorised engine core"]
        EWSMART["ewsmart/ package v3.0.0\nenvironment · receiver · schedulers\nmetrics · runner · experiments"]
        SIG["scipy-free statistics\nRayleigh Z-test · permutation tests\nbootstrap CIs (sigtests.py)"]
    end

    subgraph L2["L2 · Persistence & data"]
        LITEDB["SQLite metrics DB\newsmart/db.py · persistence.py"]
        JSOND["JSON artifacts — results/*.json\nNaN-safe · provenance-stamped"]
        DATASET["PDW datasets — JC Wise / Turing\nreplay (dataset.py) · optional datasets>=2.19"]
        SCEN["Scenario JSON — scenarios/*.json"]
    end

    subgraph L1["L1 · Ports & deployment targets"]
        UDPP["UDP / file PDW ingest\nserver/sources.py · sdr_bridge.py"]
        CPPK["C++17 header — Q8.8 fixed point\nbuild/rtl/astra_policy_kernel.hpp"]
        RTL["Future: Xilinx UltraScale+ / Zynq RTL"]
    end

    subgraph L0["L0 · Verification & toolchain"]
        PYT["pytest >= 8 + pytest-cov — 306 tests"]
        ESB["esbuild + node — engine probe\nnpm run probe"]
        ISCC["Inno Setup ISCC — installer build"]
    end

    REACT -->|REST + SSE| FA
    WTS -->|"self-contained TS engine"| WTS
    FA --> UV --> PY
    MK --> FA
    EWSMART --> NUMPY --> PY
    SIG --> EWSMART
    EWSMART --> LITEDB
    EWSMART --> JSOND
    DATASET --> EWSMART
    SCEN --> EWSMART
    UDPP --> FA
    EWSMART -->|decision kernel| CPPK --> RTL
    EXE --> REACT
    EXE --> UV
    WEBD --> WTS
    INST --> EXE
    PYT --> EWSMART
    ESB --> WTS
```

Stack summary table:

| Layer | Technology | Where |
|---|---|---|
| L6 delivery | PyInstaller exe · Vite static site · Inno installer · Docker | `astra.spec`, `vercel.json`, `Dockerfile`, `installer/` |
| L5 UI | React 18 · TypeScript 5.6 · Vite 5 | `frontend/`, `website/` |
| L4 API | FastAPI ≥0.110 · Uvicorn ≥0.29 · markdown · SSE | `server/api.py` |
| L3 engine | Python ≥3.10 · NumPy ≥1.26 | `ewsmart/` |
| L2 data | SQLite · strict JSON · PDW datasets · scenario JSON | `ewsmart/db.py`, `results/`, `scenarios/` |
| L1 ports | UDP/file PDW · C++17 fixed-point header (→ FPGA) | `server/sources.py`, `build/rtl/` |
| L0 verify | pytest ≥8 · esbuild probe · ISCC | `tests/`, `website/scripts/` |

---

## 1. High-level system architecture

```mermaid
flowchart TB
    subgraph USER["User surfaces"]
        DESK["Desktop app\nASTRA.exe (PyInstaller)\ndesktop.py + desktop_qt.py"]
        CONSOLE["Desktop console\n(frontend/ · React + Vite)\nOperations · Analysis · Data & Sources"]
        WEB["Website console\n(website/ · React + TS)\nHome · Console · Documentation"]
    end

    subgraph SERVICE["Service layer"]
        API["FastAPI server\nserver/api.py\nmissions · live · ps-coverage\ngeo · identification · figures"]
        LIVE["Paired A/B arena thread\nserver/livesim.py\nSmartScan vs baseline, SSE frames"]
        SOURCES["Sensor source hub\nserver/sources.py\nudp / log-file / sim"]
        DB["Metrics DB\newsmart/db.py + persistence.py"]
    end

    subgraph ENGINE["Engine (ewsmart/ package)"]
        ENV["environment.py\ntruth matrix + emitters\nPRI / waveform models"]
        RX["receiver.py\nCFAR + Albersheim detection\nmatched filter · PDWs"]
        SCHED["schedulers.py\n8 policies (SmartScan flagship)"]
        MET["metrics.py\n11 FoMs · KPP gate · MES"]
        RUN["runner.py\nepisode loop · reward · costs"]
    end

    subgraph FIDELITY["Fidelity modules (teardown rev. 5)"]
        DINT["deinterleave.py\nPDW → cluster → DTOA/PRI"]
        FE["frontend.py\nsettling · P1dB/IP3 · spurs · ADC"]
        AOA["aoa.py\ninterferometer (CRLB) · monopulse"]
        META["meta.py\nLinUCB behaviour arbiter"]
        CAL["calibration.py\nscale-derived constants"]
        RT["realtime.py\nQ8.8 fixed-point kernel"]
    end

    subgraph TOOLS["Toolchain (tools/)"]
        EXP["export_docs.py\nmanual → website docs"]
        CPP["export_cpp_kernel.py\nFPGA/DSP C++ header"]
        SDRI["sdr_bridge.py\nPDW/UDP ingest"]
        BEXE["build_exe.ps1\nPyInstaller + astra.spec"]
    end

    DESK --> API
    CONSOLE -->|REST + SSE| API
    WEB -->|static build| DESK
    API --> LIVE --> ENV
    SOURCES --> API
    API --> DB
    ENV --> RX --> SCHED
    SCHED --> RUN --> MET
    FE --> RX
    AOA --> RX
    META --> SCHED
    CAL --> SCHED
    RT -.FPGA/DSP port.-> CPP
    DINT --> RX
    EXP --> WEB
```

---

## 2. Live mission data flow (desktop paired A/B arena)

```mermaid
sequenceDiagram
    participant U as Console (Operations page)
    participant A as FastAPI /api/live
    participant T as Arena thread (livesim.py)
    participant E as RFEnvironment (seeded)
    participant R as ESReceiver + Scheduler pair

    U->>A: POST /api/live/start (n_bands, T, n_fhss, cfar_pfa,<br/>dwell_time_us, lpi_fraction, matched_filter, aoa_model)
    A->>T: LiveArena(...).start()
    loop every tick (speed slots/s)
        T->>E: fresh seeded scene per generation
        T->>R: schedA.select(t) / schedB.select(t)
        R->>R: rx.dwell(band, t) → DwellResult
        R-->>T: hits, false alarms, first_intercept, PDWs
        T->>T: reward (threat/clutter/empty/FA) + cost model
        T-->>U: SSE frame (occ columns, KPIs, evasion, DND tokens)
    end
    U->>A: GET /api/live/status → KPIs (coverage, TTFF, pred acc)
    U->>A: POST /api/live/stop
```

**Two receivers, byte-identical battlefields** — the seed is identical, so any
performance difference is attributable to the scheduling policy alone.

---

## 3. SmartScan decision pipeline (per slot)

```mermaid
flowchart TB
    START(("slot t")) --> RECON{"t < recon?"}
    RECON -->|yes| SWEEP["Survey sweep\nband = t % n_bands"]
    RECON -->|no| LOCK{"credible phase-lock\ndue now? (periodic.py\nRayleigh Z >= 3.9)"}
    LOCK -->|yes| CUE["Cued pursuit:\ndwell the locked band"]
    LOCK -->|no| PROBE{"probe window open?\n(unproven rhythm)"}
    PROBE -->|yes| PRB["Predict-and-probe"]
    PROBE -->|no| BURST{"isolated-hit burst\narmed on a band?"}
    BURST -->|yes| CAMP["Characterisation camp"]
    BURST -->|no| PURS{"hop pursuit gate open?\nmajority successor + imminent\n+ adaptive outcome gate"}
    PURS -->|yes| HOP["Dwell predicted destination\n(HopDwellPredictor)"]
    PURS -->|no| ROT["Value-weighted rotation\nmu + UCB + recency + logit\n+ hop urgency"]
    SWEEP --> UPD["update(t, band, res, r)"]
    CUE --> UPD
    PRB --> UPD
    CAMP --> UPD
    HOP --> UPD
    ROT --> UPD
    UPD --> LEARN["learn: value EMA · logistic\noccupancy · hop transitions\n→ end_episode consolidation"]
    UPD --> FO["FoMs: coverage · TTFF\nFA rate · prediction %\nintercept-time error"]
```

Safety gates on the pursuit path (all measured, all ablatable): majority
successor ≥ 50 %, dwell statistics mature, predicted window imminent (±2
slots), target band not already covered, adaptive success-rate gate, survey
phase gate, rolling budget, and per-stream miss blocking.

---

## 4. Receiver detection chain

```mermaid
flowchart LR
    E["Emitter\n(kind · PRI model · waveform)"] --> ENVX["environment.py\nband_seq truth matrix"]
    ENVX -->|"emsAt(band,t)"| RECV
    subgraph RECV["ESReceiver"]
        MF["LPI matched filter\n+10log10(BT)"]
        CFAR["CA-CFAR + Albersheim\nthreshold = f(B·tau, Pfa)"]
        AOA1["AOA model\ninterferometer (CRLB) | fixed"]
    end
    FE2["front-end (optional)\nretune blanking · P1dB blocking"] --> CFAR
    CFAR -->|"detections (snr, aoa, eid)"| PDW["PDW stream\n(TOA, RF, PW, PA, AOA)"]
    PDW --> DINT["deinterleave.py\ncluster → DTOA → PRI"]
    PDW --> IDENT["identification.py\nfingerprint → library"]
    CFAR --> MET["metrics.py\nPd · Pfa · sensitivity (MDS)\nintercept % · prediction %"]
```

---

## 5. Website console — three-bay command centre (rev 3)

```mermaid
flowchart TB
    subgraph TABS["Console.tsx — tab switcher"]
        T1["Live Mission"]
        T2["Learning Arena\n(isolated sandbox)"]
        T3["Model Lab"]
    end

    subgraph TS["TS engine (parity port)"]
        C["core.ts\nRFEnvironment · ESReceiver\nLPI/MF · interferometer AOA"]
        S["schedulers.ts\nSmartScan · Seq · Rand · UCB · LinearQ\nTeamScheduler (DND de-confliction)"]
        L["library.ts\nStreamCollector + ID matching"]
    end

    T1 --> C
    T1 --> S
    T1 --> L
    T2 -->|"own envs + own learner\nmemory persists per episode"| S
    T3 -->|"headless shootouts\nall policies, same seed"| S
    C -->|"occupancy waterfall\n640x190 canvas per side"| T1
```

Tab isolation contract: the Learning Arena owns its `SmartScanScheduler`
instance, its own `RFEnvironment` per episode, and its cross-episode memory.
The Live Mission tab is untouched by arena runs; wiping arena memory never
affects a running mission.

---

## 6. Verification & evidence flow

```mermaid
flowchart LR
    TESTS["tests/ (306)\nunit · integration · API · packaging"] --> PYT["pytest -q\n306/306"]
    PROBE["website npm run probe\nheadless TS engine"] -->|predAcc 96.9 vs 54.1 pct| WEBB["website/dist build"]
    AUDIT["GET /api/ps-coverage\n13 live checks"] --> JSON["results/ps_coverage_live.json"]
    BENCH["experiments.py\nMonte-Carlo benchmark"] --> ART["results/benchmark.json|.md\nperformance.json · suite_results.json"]
    EXPD["tools/export_docs.py"] -->|"single source"| W1["docsHtml.ts · manual.md"]
    CPPX["tools/export_cpp_kernel.py"] --> HPP["build/rtl/astra_policy_kernel.hpp\n+ kernel_metadata.json"]
```

---

## 7. Deployment & packaging

```mermaid
flowchart TB
    SRC["source tree"] --> FEB["frontend npm run build"]
    FEB --> SPEC["astra.spec (PyInstaller)"]
    DOCS["docs/ASTRA_Software_Documentation.md"] --> SPEC
    SPEC --> EXE["dist/ASTRA/ASTRA.exe (+ runtime folder)"]
    EXE --> INSTALL["installer/astra_installer.iss\nInno Setup — rebuild where ISCC exists"]
    SRC --> WEBB2["website npm run build\nvercel.json"]
    SRC --> DOCKER["Dockerfile\ncontainer deployment"]
```

---

### Reading order for reviewers
0. Diagram 0 (stack cake) — every technology on one page; the "cover both in one" view.
1. Diagram 1 (system) — what exists.
2. Diagram 2 (live flow) — how it runs in front of a jury.
3. Diagram 3 (SmartScan pipeline) — where the intelligence is.
4. Diagram 4 (receiver chain) — why the FoMs are physically coupled.
5. Diagrams 5–7 — the browser port, verification, packaging.