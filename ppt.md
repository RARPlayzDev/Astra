# ASTRA — PPT Modification Prompt (paste into Claude)

> **How to use:** Attach your existing deck (`ASTRA_SIH2026_Presentation.pptx`, 6 slides)
> to Claude along with this file, then paste everything below the line as the prompt.
> All numbers below are real measured values from this repo — do not invent others.

---

Below is my 6-slide SIH 2026 deck for **ASTRA — Cognitive Electronic Support (ES) Smart
Scan Strategy**. Restyle and rewrite it to SIH jury standards: minimum text, maximum
visual structure, every claim backed by a number. Keep exactly 6 slides.

## Global design rules (apply to every slide)

- Dark tactical theme: background #0d1420, accent gold #cfa453, secondary steel-blue
  #6f9ec7, body text #dfe6ee. One accent color per emphasis, no rainbows.
- Every slide: 1 diagram + ≤5 bullet fragments (≤12 words each). No paragraphs.
- Use consistent stat-chip style: big number + tiny caption (e.g. "96.9 % / prediction
  accuracy vs 54.1 % baseline").
- Footer on each slide: "ASTRA · SIH 2026 · PS <ID>".
- All numbers must match this table exactly:

| Metric | Value | Source |
|---|---|---|
| Threat coverage (SmartScan) | 90.3–95.8 % across seeds | `results/benchmark.json` |
| Threat TTFF (SmartScan vs sequential) | ~1.8× faster on the canonical KPP scene | benchmark run |
| Prediction accuracy (website probe, seed 4242) | SmartScan 96.9 % vs sequential 54.1 %, random 50.2 %, UCB 95.5 %, linear-Q 96.4 % | `website npm run probe` |
| Periodic interception ratio | > 91 % per cycle (Rayleigh phase-lock) | benchmark |
| Agile hop prediction (Markov hops) | 53 % top-1 (chance ≈ 4 %) | `results/benchmark.json` |
| Decision latency | ~0.5–0.9 ms per dwell, Python | `results/performance.json` |
| Test suite | 306 automated tests, all passing | `pytest` |
| PS audit | 13/13 live checks at `/api/ps-coverage` | FastAPI endpoint |

## Slide-by-slide specification

### Slide 1 — Title + problem hook
- Title: **ASTRA — Cognitive ES Smart Scan Strategy**; subtitle: "Finding the right
  band at the right time, without prior intelligence."
- Diagram: full-width background graphic — a dark spectrum waterfall (time × 24 bands,
  blue cells = true transmissions, gold flash = intercept). Reproduce the console
  waterfall look.
- One stat chip: "24 bands · 2–18 GHz · zero prior knowledge".

### Slide 2 — Problem & constraints
- Diagram (flow, left→right): Wide spectrum (2–18 GHz) → Receiver with narrow
  instantaneous bandwidth (B_inst ≪ B_total, ≥10:1) → 2-D search grid (frequency ×
  time). Draw the grid: x = time, y = frequency; emitters as sparse dots; a blind
  raster sweep line vs ASTRA's aimed dwell line.
- Bullets: hostile emitters transmit rarely; open-loop sweeps waste dwell on empty
  bands; interception is a 2-D search problem (frequency at the correct time).

### Slide 3 — System architecture
- Diagram (layered block diagram):
  `RF environment (truth matrix [bands × time])` → `ES receiver (CFAR + Albersheim
  detection, interferometer AOA)` → `SmartScan scheduler (recon sweep → Rayleigh
  phase-lock → cued pursuit → value-weighted rotation)` → `FoMs / mission score`.
- Side chip-stack: "7 FoMs tracked: Pd, Pfa, sensitivity, intercept rate, net reward,
  prediction %, intercept-time error".
- Mention honestly: hybrid policy — statistical learning + online value learning;
  deep RL benchmarked as a documented negative result under partial observability.

### Slide 4 — How the intelligence works (the differentiator)
- Diagram: 3-stage pipeline with icons:
  1. **Discover** — fast recon sweep, unsupervised SNR+AOA clustering.
  2. **Learn** — Rayleigh Z-test estimates each periodic emitter's period & phase;
     transition matrix predicts agile hops; value EMA ranks bands.
  3. **Exploit** — dwell at the predicted ON window (phase-locked pursuit),
     confirmed locks logged live.
- Stat chips: ">91 % per-cycle periodic capture", "53 % agile top-1 vs 4 % chance",
  "13/13 live PS-coverage checks".

### Slide 5 — Results / live demo
- Diagram: the A/B race — two waterfall panels side by side (SmartScan vs sequential),
  gold intercept flashes dense on the left.
- Table (4 rows max): SmartScan 96.9 % prediction accuracy vs 54.1 % sequential;
  threat coverage 90 %+; decision cost <1 ms; 306 tests green.
- Footer note: "Same battlefield, same receiver — only the scheduling brain differs."

### Slide 6 — Roadmap & ask
- Diagram: horizontal timeline: done (engine, console, desktop app, docs, tests) →
  next (SDR hardware-in-the-loop via PDW/UDP bridge, FPGA/C++ kernel port — fixed-point
  kernel already exported, CRLB AOA array) → vision (integration with DRDO ES suite).
- Close with the one-line pitch: "Open-loop sweeps search; ASTRA anticipates."

## Speaker notes (2–3 lines per slide, add verbatim)

- S1: hook — "a radar that transmits 2 % of the time is invisible to a dumb sweep."
- S2: the 10:1 bandwidth rule makes full-time monitoring physically impossible.
- S3: every number in the engine has a ground-truth matrix behind it — no black boxes.
- S4: emphasize phase-locking = arriving early, not searching longer.
- S5: if asked why not deep learning: we built it, benchmarked it, and it lost to the
  hybrid under partial observability — we ship what wins, and we show the data.
- S6: the C++ fixed-point kernel and UDP PDW bridge are the hardware on-ramp.

## Do NOT

- Do not add slides, do not remove slides.
- Do not use any number not in the table above.
- Do not use stock clip-art; all visuals must be the diagrams described.
- Keep fonts ≥20 pt body, ≥40 pt titles.
