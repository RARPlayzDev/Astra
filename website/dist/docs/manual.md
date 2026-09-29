# ASTRA — Software Documentation

**ASTRA — Adaptive Spectrum Threat Recognition & Analysis**
Adaptive scan scheduling for Electronic Support receivers.
Version 3.0.0 · SIH 2026 prototype · simulation-based research software, not operational equipment.

---

## Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Quick start](#3-quick-start)
4. [Interface tour](#4-interface-tour)
5. [Operations perspective](#5-operations-perspective)
6. [Analysis perspective](#6-analysis-perspective)
7. [Data & Sources perspective](#7-data--sources-perspective)
8. [Radar and sensor integration](#8-radar-and-sensor-integration)
9. [Scenarios](#9-scenarios)
10. [Datasets and calibration](#10-datasets-and-calibration)
11. [Scheduling policies](#11-scheduling-policies)
12. [Evaluation methodology](#12-evaluation-methodology)
13. [Diagnostics and troubleshooting](#13-diagnostics-and-troubleshooting)
14. [Testing without a radar](#14-testing-without-a-radar)
15. [Architecture reference](#15-architecture-reference)
16. [Local API reference](#16-local-api-reference)
17. [Command-line tools](#17-command-line-tools)
18. [File formats](#18-file-formats)
19. [Frequently asked questions](#19-frequently-asked-questions)
20. [Glossary](#20-glossary)
21. [Simulation fidelity reference](#21-simulation-fidelity-reference)
22. [Desktop application reference](#22-desktop-application-reference)
23. [Web console reference](#23-web-console-reference)
24. [Console metrics reference](#24-console-metrics-reference)
25. [Metric audit harness](#25-metric-audit-harness)
26. [Geolocation and cooperative AOA reference](#26-geolocation-and-cooperative-aoa-reference)
27. [Emitter identification reference](#27-emitter-identification-reference)
28. [Website verification gates](#28-website-verification-gates)
29. [Performance and latency reference](#29-performance-and-latency-reference)

---

## 1. Introduction

### 1.1 What ASTRA is

ASTRA is a desktop application that schedules the scan pattern of an
Electronic Support (ES) receiver. Such receivers are sensitive but narrowband:
they can listen to only one slice of spectrum at a time while remaining
responsible for a much wider range. Where a conventional receiver sweeps bands
in a fixed pre-mission order, ASTRA decides **where to listen next** based on
what has already been heard — surveying the spectrum, learning each emitter's
behaviour, predicting when periodic emitters will transmit again, and
positioning the receiver on those windows before they open.

### 1.2 What problem it addresses

Interception is a two-dimensional search: the receiver must be on the right
frequency at the right time. Fixed scans waste dwell time on empty or
unimportant bands and are slow to return to new or threatening emitters.
Naive adaptivity swings to the opposite failure — camping on one busy band and
missing most threats. ASTRA resolves this tension explicitly, achieving both
high reward and high coverage where reference systems achieve only one.

### 1.3 What it is not

ASTRA is a prototype for evaluation. It ships with a physically motivated
simulated RF environment so that it runs anywhere with no hardware; it does not
transmit, jam, or connect to any classified system.

---

## 2. Installation

### 2.1 Requirements

| Item | Requirement |
|---|---|
| Operating system | Windows 10/11 (Linux/macOS run from source) |
| For `ASTRA.exe` | None beyond the OS; WebView runtime (Edge) ships with Windows |
| From source | Python ≥ 3.10 with pip; Node.js ≥ 18 only if rebuilding the UI |

### 2.2 Installer (recommended)

1. Copy or install the `ASTRA` folder.
2. Double-click **`ASTRA.exe`**. A console window shows service startup, then
   the application window opens.
3. Closing the application window does not stop the service by itself; use
   **File → Exit** inside ASTRA, or close the console window.

### 2.3 From source

```powershell
git clone <repository> ; cd p1
python -m pip install -r requirements.txt fastapi uvicorn markdown
cd frontend ; npm install ; npm run build ; cd ..
python desktop.py
```

### 2.4 Browser-only mode

Any mode above also works from a normal browser at `http://127.0.0.1:<port>`
(the port is printed at startup). All features are identical; only the window
frame differs.

---

## 3. Quick start

1. Launch ASTRA (Section 2).
2. Press **Start Mission** on the toolbar (or File → Start paired mission).
3. Watch the Operations perspective: two receivers fly identical battlefields;
   blue-grey cells are true transmissions, amber marks intercepts.
4. Open **Tools → Diagnostics** at any time to verify the installation.
5. Press **User Guide** on the toolbar whenever you need this document.

---

## 4. Interface tour

The main window follows a classic desktop-application layout:

```
+--------------------------------------------------------------+
| ASTRA   File  View  Run  Tools  Help              ASTRA 1.0.0 |  <- menu bar
+--------------------------------------------------------------+
| [Start Mission] [Stop] | Rate [v] | Diagnostics | User Guide |  <- toolbar
|                                     Home Operations ...      |     + perspectives
+--------------------------------------------------------------+
|                                                              |
|                    workspace (perspective)                   |
|                                                              |
+--------------------------------------------------------------+
| * READY - slot 0/2400      Adaptive Spectrum ...  port 8000  |  <- status bar
+--------------------------------------------------------------+
```

### Menu bar

| Menu | Entries | Purpose |
|---|---|---|
| File | New mission window · Open scenario… · Export results (JSON) · Exit | Reset the arena, load a battlefield definition, save current benchmarks, shut down |
| View | Home · Operations · Analysis · Data & Sources · Full screen | Perspective switching |
| Run | Start / Stop paired mission · Rate presets | Mission control and simulation rate |
| Tools | Diagnostics… · Open data folder | Self-test of the installation |
| Help | User guide · About ASTRA | This document; version information |

### Toolbar

Run controls (start/stop), simulation-rate selector, quick access to
Diagnostics and this guide, and the perspective switcher on the right.

### Status bar

Live state: `READY` or `RUNNING - slot n/T`, the product name, the local port,
and a link to the user guide.

---

## 5. Operations perspective

Two panels fly simultaneously:

* **Receiver A — SmartScan (adaptive).** Surveys the spectrum, estimates emitter
  rhythms, predicts transmission windows and arrives before they open.
* **Receiver B — sequential sweep (conventional).** Visits every band in fixed
  order, ignoring content — standard practice without intelligence.

Both receivers experience **byte-identical battlefields** (same emitters, same
noise draws), so any difference in outcome is attributable to scanning strategy
alone.

Waterfall reading:

| Symbol | Meaning |
|---|---|
| Blue-grey cell | An emitter truly transmitted on that band in that slot (ground truth) |
| Bright vertical band | The band that receiver is currently tuned to |
| Amber marker | Confirmed intercept (receiver tuned to a transmitting band) |

Per-receiver counters beneath each waterfall update continuously: threat
coverage, threats intercepted (of total present), reward per dwell, hit rate,
false alarms. When an episode completes a result line summarises the A/B
outcome, and the next episode begins automatically on a fresh scenario.

Controls: toolbar **Rate** selects simulation speed (slots per second); rate
affects wall-clock pacing only, never outcomes. **File → Open scenario…**
starts a mission on a stored battlefield definition.

---

## 6. Analysis perspective

All values are generated by the bundled experiment suite from stored scenario
seeds; nothing is hand-entered.

**KPP gate table.** Each scheduler is first judged against hard Key Performance
Parameters (threat coverage ≥ 0.90, prediction accuracy ≥ 0.50, false-alarm
rate ≤ 5×10⁻⁴ per slot). Only systems passing every KPP are considered
mission-capable and ranked by the Mission Effectiveness Score (MES).

**Monte Carlo table.** Mean ± 95% confidence intervals across 50 held-out (canonical protocol: 24 bands × 3000 slots, base_seed 9000)
episodes for reward, threat coverage, prediction accuracy, intercept rate,
false-alarm rate, time-to-first-intercept and intercept-time prediction error.
Paired permutation tests on the gated score separate SmartScan from every
reference policy (p < 1e-4, Holm-Bonferroni corrected).

**Evidence gallery.** Generated figures: effectiveness under the gate,
scheduler comparison, training vs held-out greedy evaluation curves, ablation
study, ROC across sensitivity thresholds, geolocation accuracy versus receiver
count.

File → Export results (JSON) writes the full machine-readable payload behind
these tables to disk.

---

## 7. Data & Sources perspective

Three panels manage inputs and artefacts.

### Sensor sources

Attach live pulse-descriptor-word (PDW) feeds; each attached source reports its
cumulative PDW count and instantaneous rate, proving connectivity before real
hardware is wired in.

| Type | Parameters | Typical use |
|---|---|---|
| UDP feed | port (1024–65535), bind address | SDR sweeps, radar processors, `tools/pdw_generator.py`, `tools/sdr_bridge.py` |
| Log file tail | path to growing JSONL/CSV | Third-party equipment writing PDW logs |
| Internal simulated scene | band count, seed | Testing with no hardware at all |

Detach removes the source cleanly. Errors (for example a busy UDP port or a
missing file) are shown inline on the source row.

### Scenario library

Every JSON scenario in `/scenarios` with its band count and horizon. **Fly
paired** starts a new paired mission using that battlefield definition.

### Trained models

Model artifacts (`/models/*.npz`) with their policy class, band count and an
integrity verdict. Artifacts are pickle-free NumPy archives validated on load;
a corrupt file is flagged here rather than executed.

---

## 8. Radar and sensor integration

### 8.1 Integration contract

ASTRA consumes standard ESM measurements — **pulse descriptor words**:

```json
{"toa_us": 1000.0, "freq_mhz": 9450.0, "pw_us": 1.5, "pa_db": 12.0, "aoa_deg": 90.0}
```

| Field | Meaning | Required |
|---|---|---|
| `toa_us` | time of arrival, microseconds | yes |
| `freq_mhz` | centre frequency, MHz | yes |
| `pw_us` | pulse width, µs | optional (default 1.0) |
| `pa_db` | amplitude, dB | optional |
| `aoa_deg` | angle of arrival, degrees | optional |

Datagrams may carry **one JSON object or a JSON array** of objects. A single
datagram per pulse-group per slot is the intended cadence (default slot =
1 ms), but the pipeline tolerates bursty delivery and re-bins by `toa_us`.

### 8.2 Wiring any radar / SDR processor

Three supported paths, in increasing fidelity:

1. **Synthetic generator (no hardware).**
   `python tools/pdw_generator.py --port 5555 --rate 400`
   emits realistic multi-emitter traffic over UDP for integration testing.
2. **Bridge an existing sweep log.**
   `python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555`
   converts CSV sweeps (or relays an existing JSON feed with `--mode udp`) into
   the ASTRA datagram format.
3. **Direct emission.** Your processor writes the JSON schema above straight to
   ASTRA's UDP port (attach the source in **Data & Sources**, then select the
   same port).

### 8.3 Adapting exotic front-ends

If your equipment produces another format, write a ~30-line adapter that maps
it onto the five-field PDW schema and forwards datagrams — see
`tools/sdr_bridge.py` as the template. Channelised or FFT-based receivers can
emit one PDW per detected peak per dwell.

### 8.4 Notes and limits

* Frequency-to-band mapping uses the scenario's `[fmin, fmax]`; out-of-range
  frequencies clamp to the edge bands.
* The demo pipeline assumes a single receiver location; AOA is carried end to
  end for identification and geolocation studies.
* No data leaves the machine: all networking is local loopback unless you bind
  otherwise deliberately.

---

## 9. Scenarios

A scenario is a JSON file in `/scenarios`. Key fields (all optional):

| Field | Default | Meaning |
|---|---|---|
| `n_bands` | 24 | number of frequency bins |
| `T` | 3000 | episode length in slots |
| `seed` | 0 | reproducibility seed |
| `n_stationary` / `n_agile` / `n_periodic` / `n_spatial` / `n_clutter` | 6/4/4/3/8 | emitter mix |
| `snr_mean_db`, `snr_std_db` | 12 / 4 | signal strength distribution |
| `freq_min_mhz`, `freq_max_mhz` | 2000–18000 | tuning range |
| `period_range`, `on_len_range`, `dwell_range`, `hop_set_range` | class priors | behavioural ranges |

Scenario + seed ⇒ exactly reproducible battlefield.

---

## 10. Datasets and calibration

ASTRA honours the referenced datasets:

* **JC Wise, Radar Emitter Database (2024)** — basis of the identification
  library profiles used to tag intercepted streams.
* **Alan Turing Institute synthetic radar dataset (HuggingFace)** — imported by
  Dataset Studio (Streamlit dashboard) online when reachable, with a
  schema-identical offline fallback so everything works air-gapped.

Imported PDWs drive scenario calibration: observed frequency clusters become
emitters, and their temporal statistics set behavioural classes.

---

## 11. Scheduling policies

Seven policies ship with the system; six exist as honest references:

| Name | Class | Character |
|---|---|---|
| Sequential sweep | open loop | fixed cyclic visitation |
| Random scan | open loop | uniform random selection |
| Priority sweep | open loop | prior-intelligence ordering |
| UCB bandit | adaptive, exploit-only | converges on richest band (demonstrates the exploit trap) |
| Linear Q-learning | reinforcement learning | learned value over hand-crafted features |
| Deep Q-network | deep RL | MLP + replay + target network |
| **SmartScan** | proposed hybrid | five behaviours multiplexed by learned confidence |

SmartScan's behaviours: reconnaissance sweep; cued pursuit of validated phase
locks; predict-and-probe of candidate rhythms; characterisation bursts;
value-weighted rotation with recency guarantees and an exploitation ramp.
Locks require repeated mutually isolated detections on one SNR+AOA fingerprint
and are deleted automatically after repeated failed predictions.

---

## 12. Evaluation methodology

Following defence test & evaluation practice:

1. **KPPs (hard gates).** Threat coverage ≥ 0.90 · prediction accuracy ≥ 0.50 ·
   false alarms ≤ 5×10⁻⁴/slot. Failing any gate ⇒ *not mission-capable*.
2. **MES ranking.** Among capable systems, mean of six normalised
   problem-statement figures of merit (Pd, Pfa performance, intercept rate,
   reward, prediction accuracy, intercept-time error).
3. **Statistics.** Paired per-episode permutation tests on the gated score with
   Holm-Bonferroni correction; 50 held-out episodes; 95% confidence intervals.

Headline outcome: **SmartScan is the only mission-capable scheduler in the
field** and leads every comparator at p < 1e-4 on gated MES. Learning claims
are backed by held-out greedy evaluation; the deep-network reference's decline
on this sparse task is reported as measured.

Regenerate everything:

```powershell
python -m ewsmart.experiments --suite full
```

---

## 13. Diagnostics and troubleshooting

**Tools → Diagnostics** verifies the installation: module imports, environment
boot, benchmark presence, figure inventory, model-artifact integrity, frontend
bundle, manual availability and a UDP loopback test.

| Symptom | Likely cause | Remedy |
|---|---|---|
| Window opens blank | frontend bundle missing | rebuild: `cd frontend && npm run build` |
| "Benchmark data: not generated" on Home | suite never ran | run the experiment suite command above |
| Source row shows `WinError 10048` | UDP port already bound | choose another port; stop the other process |
| Source attaches but 0 PDWs | no sender / wrong port / firewall | start `tools/pdw_generator.py --port <same>`; allow python through the firewall |
| Analysis empty after export | results file absent | regenerate via experiment suite |
| Exit did nothing | popup blocked for `window.close()` | close the console window; service stops with it |

---

## 14. Testing without a radar

Full instructions in [`HOW_TO_TEST.md`](../HOW_TO_TEST.md). Summary ladder:

1. **Automated tests** — 50 backend + 7 interface tests, each runnable standalone.
2. **In-app diagnostics** — Tools → Diagnostics.
3. **Internal simulated scene source** — attach in Data & Sources; counts PDWs with zero hardware.
4. **UDP generator** — `tools/pdw_generator.py` streams realistic emitter traffic to a chosen port.
5. **CSV replay bridge** — `tools/sdr_bridge.py` replays recorded sweeps.
6. **Paired missions** — statistical A/B evidence at any simulation rate.

Recommended edge cases: malformed datagrams (ignored gracefully), burst floods,
empty feeds (source stays healthy, zero counts), port conflicts (inline error),
scenario extremes (few bands, short horizons), repeated start/stop cycling, two
browser windows sharing one service.

---

## 15. Architecture reference

```
desktop.py            app-window launcher: free port, uvicorn thread, Edge/Chrome --app window
server/api.py         FastAPI: results, figures, scenarios, models, sources, diagnostics,
                      SSE live arena, manual renderer, shutdown hook
server/livesim.py     paired A/B simulation thread emitting synchronised frames
server/sources.py     sensor source hub: udp / file / sim with health + rates
ewsmart/environment   RF scene: four emitter classes; occupancy truth matrix
ewsmart/receiver      narrowband detection physics; AOA; PDWs
ewsmart/schedulers    seven policies incl. SmartScan
ewsmart/periodic      Rayleigh period estimation + integer refinement
ewsmart/metrics       figures of merit; KPP gate; Mission Effectiveness Score
ewsmart/experiments   Monte Carlo, significance, ROC, sensitivity, ablation, geolocation
ewsmart/live          streaming ingestion core (simulated / UDP / file tail)
frontend/             React application (menu bar, toolbar, perspectives, status bar)
tools/                sdr_bridge.py, pdw_generator.py, build_exe.ps1
docs/                 this document
```

---

## 16. Local API reference

All endpoints are local-first (`127.0.0.1`). Interactive OpenAPI UI: `/api-docs`.

| Method & path | Purpose |
|---|---|
| GET `/api/meta` | name, version, availability flags |
| GET `/api/health` | liveness probe |
| GET `/api/summary` | full benchmark payload |
| GET `/api/figures` · `/api/figures/{name}.png` | figure inventory and images |
| GET `/api/scenarios` | scenario library |
| POST `/api/live/start?speed&scenario` | start paired mission (optionally from a named scenario) |
| POST `/api/live/stop` | stop mission |
| GET `/api/live/status` | running flag, slot, per-scheduler KPIs |
| GET `/api/live/stream` | SSE frame stream |
| GET/POST/DELETE `/api/sources` | sensor source management |
| GET `/api/models` | model artifacts + integrity |
| GET `/api/diagnostics` | self-test checklist |
| GET `/manual` | rendered user guide |
| POST `/api/shutdown` | graceful shutdown (used by File → Exit) |

---

## 17. Command-line tools

| Command | Purpose |
|---|---|
| `python desktop.py` | launch the desktop application |
| `python -m ewsmart.runner --scenario scenarios/demo.json --save-dir models --json-out results.json` | train + evaluate one scenario |
| `python -m ewsmart.experiments --suite full` | regenerate all published results |
| `python tools/pdw_generator.py --port 5555 --rate 400` | synthetic PDW feed over UDP |
| `python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555` | bridge CSV/JSON sweeps into ASTRA format |
| `powershell -File tools/build_exe.ps1` | build `dist/ASTRA/ASTRA.exe` |

---

## 18. File formats

**Scenario JSON** — fields per Section 9.

**PDW datagram** — Section 8.1.

**Model artifact (.npz)** — `meta` = JSON string `{format:"ewsmart-npz-v1",
class, n_bands, ...}` plus plain arrays; loaded with `allow_pickle=False`.

**results/suite_results.json** — sections: `monte_carlo`, `significance`,
`mission_effectiveness`, `significance_gated_mes`, `learning`,
`identification`, `roc`, `sensitivity`, `ablation`, `multireceiver`,
`geolocation`.

---

## 19. Frequently asked questions

**Does closing the app window stop the service?** Use File → Exit for a clean
shutdown; the console window also stops the service when closed.

**Can several windows share one service?** Yes — open additional browser tabs
to the printed URL; all views stay in sync because state lives server-side.

**Where do numbers come from?** Experiments over stored seeds; re-run the suite
to reproduce byte-for-byte.

**Is any data sent to the internet?** No. Networking is loopback except an
optional HuggingFace fetch inside Dataset Studio, which falls back offline.

**Why does Receiver B exist?** Controlled comparison. Identical battlefields
make the strategy the only variable.

---

## 20. Glossary

| Term | Meaning |
|---|---|
| ES / ESM | Electronic Support — passive search, intercept, analysis of emissions |
| PDW | Pulse Descriptor Word (TOA, frequency, width, amplitude, AOA) |
| Dwell | One listening interval on one band |
| Slot | Discrete time step of the simulation (default 1 ms) |
| Phase lock (ASTRA) | Validated estimate of a periodic emitter's period and window timing |
| KPP | Key Performance Parameter — hard pass/fail requirement |
| MES | Mission Effectiveness Score — composite FoM after gating |
| CEP | Circular Error Probable — median geolocation error radius |

---

## 21. Simulation fidelity reference

ASTRA's scheduler works on a discrete band/time grid because scheduling is what
it studies. This chapter documents the *physical* layers underneath that grid:
pulse-level signal processing, waveform classes, front-end impairments, the
angle-of-arrival measurement, and the two deployment artifacts (scenario
auto-calibration and the fixed-point kernel). Each module states what it does,
how it works, and which measured number demonstrates it.

### 21.1 Pulse-level deinterleaving (`ewsmart/deinterleave.py`)

**What it does.** A real ES receiver's wideband front-end receives an
interleaved stream of pulses from every emitter in view — at combat densities
10^5–10^6 pulses/second — and must separate that stream back into individual
emitters before anything can be tracked or identified. ASTRA performs that
separation instead of assuming it away.

**How it works.** Four classical stages:

1. `emit_pulse_train` synthesises one emitter's pulses in a dwell (TOA, RF,
   pulse width, amplitude, AOA) from its PRI model.
2. `interleave` builds the raw, time-ordered PDW stream a receiver would see.
3. `deinterleave` separates it: descriptor clustering on (RF, PW, AOA), then an
   all-pairs difference-of-time-of-arrival histogram to find the dominant PRI,
   then coarse-to-fine period sharpening by *phase-histogram entropy
   minimisation*, then a circular-phase test that discriminates
   fixed / staggered / jittered / aperiodic trains.
4. `deinterleave_accuracy` scores the result against ground truth.

Two details matter physically: amplitude is derived with the peak-to-average
term (`pri/pw`) that makes a low-duty pulsed radar detectable at a lower
average power, and a staggered train's reported PRI is the *mean interval*
(frame/k) — the quantity a real PRI estimator reports.

**Measured.** Four emitters (fixed 250 µs, staggered 3-level 97 µs, jittered
410 µs ±12%, LPI 600 µs) interleaved into one stream: fragmentation 1.0, pulse
purity 1.0, attributed fraction 1.0, mean PRI error 0.4%, PRI-model
classification 100%. The deinterleaver never reads the ground-truth label
(leakage asserted by test).

### 21.2 Waveform classes and the matched filter

**What it does.** Models Low Probability of Intercept radar: an emitter may
spread its energy over a large time-bandwidth product so that it sits *below*
the noise floor in any one channel.

**How it works.** `EmitterSpec.waveform` is `pulsed`, `lpi_fmcw` or
`lpi_barker` with a time-bandwidth product `tb_product`. An LPI emitter's
in-channel SNR is reduced by exactly `10 log10(BT)`; a receiver running the
matched-filter / de-chirp bank (`matched_filter: true`, on by default) earns
that gain back before the detection decision.

**Measured.** A −14 dB in-channel LPI emitter with BT = 256 (24.1 dB gain):
283 of 300 dwells detected with the matched filter, 5 of 300 without. The
switch is in the scenario config, so the comparison is reproducible.

### 21.3 RF front-end impairments (`ewsmart/frontend.py`)

**What it does.** Models the hardware between the antenna and the digitiser so
its costs are measurable rather than narrated.

| Effect | Model |
|---|---|
| Retune settling | `settling_time_us` of each retuned dwell is blanked (integration time, hence processing gain, is lost) |
| LNA blocking | above the 1 dB compression point the noise floor rises (compression + LO phase-noise reciprocal mixing) |
| Mixer non-linearity | third-order products 2f1−f2 / 2f2−f1 at level `3*P_tone − 2*IP3`; image and `m*f_RF ± n*f_LO` spur responses enumerated |
| ADC | 12-bit full-scale saturation with odd-harmonic fold-back bounded by the spurious-free dynamic range |

**How to use it.** `ESReceiver.attach_front_end(FrontEnd(FrontEndSpec(...)))`.
Below P1dB the model is *exactly* linear (zero noise rise), so attaching a
front-end never silently changes normal operation; the impairment appears only
where physics says it should.
### 21.4 Angle-of-arrival measurement (`ewsmart/aoa.py`)

**What it does.** Replaces the constant 2.5 degree Gaussian bearing error with a
dual-baseline phase interferometer whose error is coupled to SNR and frequency
through the Cramer-Rao bound.

**How it works.** The coarse (5 cm) baseline measures the angle unambiguously
across the field of view; the fine (20 cm) baseline is four times more precise
but wraps, so its ambiguity is resolved against the coarse estimate, with exact
hypothesis ties broken by angular proximity, as real systems do. A
front/back-ambiguous single array face is modelled honestly: the folded bearing
is restored using the observation hemisphere, standing in for the second array
face. `aoa_model: "monopulse"` or `"fixed"` select the alternative models.

**Measured.** At 20 dB SNR the error is 0.35-0.5 degrees and unbiased across all
eight compass bearings; at -10 dB it degrades to tens of degrees
(CRLB-consistent). That coupling is the point: weak or high-frequency emitters
fingerprint poorly, which the scheduler experiences as stream fragmentation.

### 21.5 Scenario auto-calibration (`ewsmart/calibration.py`)

**What it does.** Derives the scheduler's behaviour constants from the scenario
scale instead of hard-coding values tuned for 24 bands x 3000 slots.

**How it works.** `calibrate(n_bands, T, n_emitters)` returns `recon_factor`,
`burst_horizon`, `stale_revisit_factor`, `pursuit_budget`, `pursuit_window`,
`hop_min_obs`, `lock_hits` and `exploit_ramp`, each from a documented formula
over the band, time and density scales. On the canonical scenario it reproduces
the shipped constants exactly, so calibration is a no-op where the tuning is
known good and adapts elsewhere: an 8-band radio survey or a 128-band full
ELINT sweep both get appropriately sized behaviour.

### 21.6 Fixed-point real-time kernel (`ewsmart/realtime.py`)

**What it does.** Provides the per-slot decision in Q8.8 integer arithmetic as
the concrete port artifact for FPGA/DSP deployment.

**How it works.** Every statistic is quantised once on write with saturation;
the per-slot score is an integer multiply-accumulate over `n_bands` lanes
(O(n_bands), no dynamic allocation, no per-slot transcendental); the log/sqrt
terms are cached and recomputed only when the underlying statistics change.
`tools/export_cpp_kernel.py` emits the same arithmetic as a header-only C++
kernel (`build/rtl/astra_policy_kernel.hpp`) plus a `kernel_metadata.json`
complexity contract.

**Measured.** Over 200 randomised states the fixed-point argmax matches the
float reference, and the recorded decision cost remains under the 1 ms gate.

### 21.7 Learned behaviour arbitration (`ewsmart/meta.py`)

**What it does.** Adds a genuine learning component to the *decision core*: a
linear-upper-confidence-bound contextual bandit that learns which behaviour
(survey, pursue, probe, camp, rotate) pays in which situation, from hits and
misses alone.

**How it works.** The scheduler tags every decision with the behaviour that
produced it and, on the dwell result, folds `(context, behaviour, reward)` into
the arbiter. A safe action mask means the arbiter can only choose among
behaviours whose preconditions hold, so an immature model cannot destabilise a
proven policy; its learned preferences are inspectable via `arbiter.score()`.
Cross-episode persistence is available through `get_state` / `set_state`.

**Measured.** A full episode trains the arbiter from 500+ outcome triples, and
in a two-armed test it converges to preferring the rewarded behaviour.

### 21.8 Documentation pipeline

`tools/export_docs.py` makes this manual the single source of truth: it
converts the markdown to HTML for the website's Documentation page
(`website/src/content/docsHtml.ts`), copies it to
`website/public/docs/manual.md` for the "Download (.md)" button, and emits the
section index the site's table of contents is built from. The desktop
application serves the same file at `/manual`; nothing is maintained twice.

---

## 22. Desktop application reference

The installed application (`dist/ASTRA/ASTRA.exe`, built from
`desktop_qt.py` by `astra.spec` via `tools/build_exe.ps1`) is a native
PySide6 window wrapping the same console the website serves.

### 22.1 Window, service and offline guarantees

On launch the app picks a free loopback port, starts the FastAPI service in a
daemon thread, polls `GET /api/health` for up to 30 seconds, then opens a
`QWebEngineView` at `http://127.0.0.1:<port>`. Remote URL access from the
page is disabled (`LocalContentCanAccessRemoteUrls = False`), so a running
mission never reaches the network. Closing the window shuts the service down
cleanly (`server.shutdown()` plus `hub.stop_all()`), as does **File → Exit**.

### 22.2 Menus and keyboard shortcuts

Qt supplies the native menu bar; the React menu bar inside the page is hidden
in Qt mode (`window.__AstraQt`).

| Menu | Entry | Shortcut |
|---|---|---|
| File | New mission | Ctrl+N |
| File | Open scenario… | Ctrl+O |
| File | Export results (JSON) | Ctrl+E |
| File | Exit | Ctrl+Q |
| Run | Start mission | F5 |
| Run | Stop mission | Shift+F5 |
| Run | Rate: Slow (120/s) · Normal (400/s) · Fast (800/s) · Maximum (1500/s) | — |
| Tools | Diagnostics… | Ctrl+D |
| Help | User guide (opens `/manual`) | F1 |
| Help | About ASTRA | — |

The status bar polls `GET /api/live/status` every 2 seconds and shows
`READY` or `RUNNING — slot n/T`, with a permanent `ASTRA 3.0.0` label. The
Run-menu rate presets inject `window.__astra_set_speed(n)` into the page; the
default is Normal (400 slots/s).

### 22.3 System tray and page bridge

The system tray offers **Show** (or double-click) and **Exit**. After the page
loads, a small bridge defines `window.__AstraQt`, `__astra_start`,
`__astra_stop` and `__astra_diag`, which the native menus call; the Help menu
navigates the view to `/manual`, the rendered copy of this document.

---

## 23. Web console reference

`/console.html` is the browser build of the same engine
(`website/src/engine/`): battlefield generator, receiver physics and five
policies compiled to run entirely client-side. No server, no install, and
runs are seed-exact.

### 23.1 The three bays

| Bay | Purpose |
|---|---|
| Live Mission | Real-time A/B race: SmartScan against a conventional sweep on one battlefield |
| Learning Arena | Cross-episode training in an isolated sandbox with its own learner memory |
| Model Lab | Headless shootouts and the verification-numbers probe table |

### 23.2 First-run onboarding and guided tour

On first visit (state stored under `localStorage["astra.console.v1"]`) an
intro modal shows five cards — what the console is, the three bays, how to
read the waterfall, how to use it, and the offline desktop build — then
offers the guided tour. The tour has seven stops (demo chips, mission
configuration, the waterfall, live KPIs and threat board, event log, the
three bays, replay). Keyboard: **Esc** skips, **←** steps back, **→** or
**Enter** steps forward; the spotlight follows its target while the page
moves. *Quick Guide* and *Help / Tour* in the top bar replay either at any
time.

### 23.3 Presentation demo presets

One-click scenarios that fully determine seed, opponent and scene, then
start instantly:

| # | Preset | Seed | Battlefield |
|---|---|---|---|
| 1 | Flagship race | 4242 | standard scene, sequential opponent — the headline A/B |
| 2 | Periodic hunter | 777 | eight scanning radars (period 30–120) — watch phase-locks confirm |
| 3 | Exploit trap | 999 | UCB opponent on clutter-rich spectrum — high score, half the threats missed |
| 4 | Low-SNR stress | 31337 | weak signals (SNR 7 ± 3 dB), reduced sensitivity |
| 5 | Cooperative swarm | 2024 | three receivers per side, band de-confliction, dense 32-band scene |

### 23.4 Waterfall, event log and KPIs

The waterfall shows blue-grey cells for true transmissions (ground truth), a
light grey column for the band currently tuned, and gold for confirmed
intercepts. The scheduler event log classifies every line — **PROBE**
(rhythm hypothesis), **LOCK/CONFIRMED** (phase lock), **DROP** (stale belief
retired), **SHIFT** (environment change), **DONE**, **INFO** — with live
lock/drop/probe counters and a Clear button. Per-receiver KPI rows update
every slot: threat coverage, intercepts, reward per dwell, hit rate, false
alarms (count and per-1k rate), mean first-fix and censored threat TTFF,
prediction accuracy and phase locks held - each comparable row marks the
leading receiver in amber. Chapter 24 is the full metric contract, including
when and why a baseline can lead a row; `npm run audit:metrics` guards it.

### 23.5 Learning Arena and Model Lab

**Train 5 / Train 10 episodes** runs full missions back-to-back on fresh
seeds while the SmartScan learner keeps its consolidated band-value memory
between episodes; *Reset learner memory* wipes it. Results render as an
episode table plus coverage bars (rising bars = warm start paying off).
**Run shootout** races the five browser policies — SmartScan, sequential
sweep, random scan, UCB bandit, linear Q-learning — on the configured seed,
and the verification table reports next-window prediction accuracy:
SmartScan 96.9 %, linear Q 96.4 %, UCB 95.5 %, sequential sweep 54.1 %,
random scan 50.2 %.

---

## 24. Console metrics reference

The web console's Live Mission KPI cards update every slot. This chapter is
the contract for each row: what is measured, over what denominator, and which
direction is better. Both receivers run in one twin-battlefield mission: the
same emitters, the same slot clock, only the scan policy differs (Receiver A
is SmartScan, Receiver B is the selected baseline). Each side's receiver noise
realisation comes from its own derived seed (`seed*7+11` for A, `seed*13+29`
for B), so detection luck is independent but statistically identical.

### 24.1 Row definitions

| Row | Definition | Better |
|---|---|---|
| Threat coverage | distinct threat emitters ever intercepted / total threats | higher |
| Threats intercepted | the same quantity in absolute form (found of total) | higher |
| All-emitter intercept ratio | distinct emitters ever intercepted / all emitters (clutter included) | higher |
| Reward per dwell | sum of per-dwell rewards / (slots x receivers). Dwell rewards: threat hit +1.00, clutter hit +0.15, empty -0.05, false alarm -0.08 | higher |
| Hit rate | slots with at least one clean intercept / slots | higher |
| False alarms | count, plus rate per 1000 slots, of dwells that raised a false alarm | lower |
| Mean TTFF (first fix) | mean over emitters *found* of the slot of their first interception - parity with `ewsmart.metrics.mean_time_to_first_intercept` | lower |
| Threat TTFF (censored) | the same first-fix mean over *every* threat: a threat not yet fixed costs the full horizon T - parity with `ewsmart.metrics.threat_ttff_censored` | lower |
| Prediction accuracy | fraction of dwells where `predict(t, band)` equals the chosen band's ground truth; the context row shows how often that band was truly ON | higher |
| Phase locks held | validated periodic locks held by *this side's* scheduler | n/a (SmartScan only) |

Two defects used to distort this card and are now fixed and guarded by the
audit harness (chapter 25): the opponent's card displayed Receiver A's lock
count, and "Mean TTFF" averaged *every* clean-hit slot - a value that drifts
toward T/2 and made every baseline look faster in 16 of 16 audit runs.

### 24.2 When a baseline leads a row - and why it is honest

The audit (4 seeds x 4 baselines, full 3000-slot missions) found the
remaining opponent leads are small, rare and explainable:

| Row | Where the baseline leads | Why it is real |
|---|---|---|
| Reward / hit rate / prediction (UCB) | 3 of 16 runs (e.g. seed 4242: 0.949 vs 0.935 reward) | UCB is exploit-only: it camps on the richest band and never spends slots surveying. SmartScan's reconnaissance and probe dwells are deliberate one-slot costs. Where camping happens to be enough, UCB edges those rows - then its threat coverage collapses (0.527-0.857 on the seeds that matter; the "exploit trap" demo, preset 3) |
| Mean TTFF over found emitters | 3 of 16 runs, by 1-10 slots | Survivorship: the baseline only counts emitters it managed to find - misses drop out of the mean. Read it together with coverage; Threat TTFF (censored) charges misses the full horizon |
| All-emitter intercept ratio | 2 of 16 runs (seed 31337 vs sweep/random) | SmartScan deprioritises valueless clutter under the reward model while a blind sweep eventually visits every band. Threat coverage - the KPP that matters - stays at 100 % for A in those runs |
| Threat TTFF (censored), early mission | 3 of 16 runs, by 1-10 slots | A blind sweep's first revolution gives every band one visit within `n_bands` slots, while SmartScan pays a ~10-slot cold-start survey. The lead never survives to coverage, reward or prediction |

**Reading rule.** No single row decides the comparison - the KPP gate does
(coverage >= 0.90, prediction >= 0.50, false alarms <= 5e-4/slot). The
flagship A/B (seed 4242, sequential) shows the shape: SmartScan 100 %
coverage, 0.935 reward/dwell, 96.2 % hit rate, 97.9 % prediction accuracy,
versus the sweep's 85.7 %, 0.142, 45.1 % and 54.1 %. The two cards mark the
leader of each comparable row in amber; ties stay neutral.

---

## 25. Metric audit harness

`npm run audit:metrics` (from `website/`) is the regression check for
chapter 24's contract. It replays the console's exact KPI pipeline headless -
four seeds (4242, 777, 999, 31337) x four baselines (sequential, random, UCB,
linear Q), full 3000-slot missions, twin battlefields - and then:

1. asserts every displayed figure is in range (coverage, hit rate and
   prediction within [0,1]; first-fix TTFF inside the horizon);
2. asserts the side-specific lock rule: a baseline side can never report a
   non-zero phase-lock count;
3. prints a per-run A/B table - coverage, hit rate, reward, false alarms,
   prediction, both TTFF forms (old and fixed semantics), lock counts;
4. prints the "where the opponent beats SmartScan" tally quoted in 24.2.

The script exits non-zero on any invariant failure, so it can be chained
after `npm run check` in CI. Related probes:

| Command | What it measures |
|---|---|
| `npm run probe` | prediction accuracy exactly as the console scores it: SmartScan 96.9 %, linear Q 96.4 %, UCB 95.5 %, sequential 54.1 %, random 50.2 % (seed 4242) |
| `npm run audit:metrics` | KPI invariants + opponent-leads report (this chapter) |
| `npm run smoke` | render-time page assertions (chapter 28) |

---

## 26. Geolocation and cooperative AOA reference

**What it does.** Converts angle-of-arrival bearings from cooperating
receivers into emitter ground positions and reports error the way defence
T&E does - CEP percentiles, not anecdotes.

**How it works.** The solver (`website/src/engine/geo.ts`, a direct port of
`ewsmart/geo.py`) takes bearing lines from known node positions, computes a
least-squares fix refined by Gauss-Newton iterations (`triangulate`), then
reports mean, CEP50 and CEP90 error (`cepStats`). Bearings are degrees from
east, 0-360, in both implementations - a parity contract. Node geometry comes
from `receiverRing(3, 50)`: the primary receiver at the origin and two
cooperating nodes on a 50 km ring, the same geometry `GET /api/geolocation`
builds. Modelled cooperating bearings carry a CRLB-style sigma = 2.0 deg,
mirroring `ewsmart.geo.simulate_bearings(..., 2.0, rng)`.

**Console panel semantics.** The Live Mission geolocation panel localises
every stream Receiver A actually intercepted:

1. node 0 carries the receiver's *measured* AOA - the circular mean of the
   intercepted pulses' bearings, a real measurement;
2. nodes 1-2 carry the 2 deg bearing model at their baselines (a single
   receiver cannot observe the other nodes' AOAs - the panel says so);
3. ground truth is used only for scoring: per-row error plus the mean / CEP50
   / CEP90 readout. It is never an input to the solver.

**Measured.** Headless sanity at seed 4242, default scene: every intercepted
stream localised with no NaN - mean error 2.17 km, CEP50 2.06 km, CEP90
4.56 km. Bearing diversity is what tightens the fix: adding receivers moves
median CEP from 3.2 km (two nodes) to 1.7 km (three), the figure quoted on
the landing page.

**How to read the panel.** Hollow amber markers are ground truth, filled red
are triangulated estimates, the grey ring is the receiver network, and each
line from node 0 is a measured bearing. Rows sort by error; a large residual
on one stream means poor geometry for that bearing, not a solver fault.

---

## 27. Emitter identification reference

**What it does.** After three or more intercepts of one stream, match its
measured fingerprint against the emitter library and score the call with a
confidence the operator can audit.

**How it works** (console `website/src/engine/library.ts`, parity with
`ewsmart/identification.py`):

1. *Measurement.* Each stream's centre frequency and pulse width are observed
   through the receiver chain: a per-emitter systematic bias scaled by signal
   quality, so the fingerprint is what the receiver could measure - never the
   emitter's true parameters. The board's Measured column shows the observed
   MHz / us / SNR values directly.
2. *Gate.* Library entries whose frequency range excludes the measured centre
   frequency (5 % band tolerance) are eliminated outright.
3. *Grade.* The best remaining entry scores `(2 + pwFit + scanFit) / 4` -
   frequency is implicitly full weight after the gate, pulse width and scan
   rhythm contribute graded fits that decay linearly one range-width outside
   the library range. Confidence is therefore in [0.5, 1.0]; a perfect 1.00
   only appears when every measured feature sits inside the range.
4. *Rank.* The board sorts by threat rank, then confidence; ground truth is
   shown only to score the call (MATCH / MISS columns).

**Library.** Ten ELINT radar classes in the browser console: SNOW DRIFT,
FLAT FACE, POP GROUP, FLAP LID-A, SQUARE PAIR, BIG BACK, CROSS SLOT, HALF
PLATE, TIN SHIELD, LONG TRACK - each with frequency, pulse-width and (where
applicable) scan-period ranges plus a HIGH / MEDIUM / LOW threat level. The
Python library adds two COMINT profiles (RADIO SET-FH, TDM NET) that are
reached through the signal-class stage, never by generic fingerprint scoring.

**Measured.** Seed-4242 sanity run: confidences graded across 0.95-1.00 with
a MISS row present - the board is a measurement, not a rubber stamp.
Overlapping classes (TIN SHIELD vs SNOW DRIFT share S-band) can legitimately
swap on a weak stream; the ground-truth column exists precisely so the call
can be audited.

---

## 28. Website verification gates

The site ships self-checking; run everything from `website/`:

| Command | Asserts |
|---|---|
| `npm run check` | the full gate: docs:check + smoke + build + verify:dist |
| `npm run docs:check` | every manual section derives and renders (> 200 chars, anchors resolve), at least 20 sections, no mojibake |
| `npm run smoke` | server-renders all four pages; required headline strings present; unique ids; every `#anchor` resolves; one `<h1>` per page |
| `npm run build` | production build into `dist/` |
| `npm run verify:dist` | every hashed asset referenced by the four HTML entries resolves; shared CSS carries required markers |
| `npm run probe` | prediction-accuracy probe under console scoring rules |
| `npm run audit:metrics` | KPI invariants + opponent-leads report (chapter 25) |
| `npx tsc --noEmit` | type safety across engine, pages and scripts |

Python side: `python -m pytest tests -q` (306 tests). The full verification
ladder, including the engine parity bundle, is in `HOW_TO_TEST.md`.

---

## 29. Performance and latency reference

| Claim | Evidence |
|---|---|
| Per-decision latency under 1 ms for every scheduler | `tests/test_performance.py::test_scheduler_decision_under_1ms[...]` - parametrised once per policy: bandit-ucb, openloop-priority, openloop-random, openloop-sequential, rl-dqn, rl-linear-q, smart-scan |
| Measured decision cost 0.5-0.9 ms per dwell on the benchmark host | `results/performance.json` (platform stamped into the artifact) |
| Fixed-point kernel matches the float policy | `ewsmart.realtime.PolicyKernel` in Q8.8; `tests/test_realtime_kernel.py` asserts bit-for-bit agreement at the kernel's quantisation granularity; `tools/export_cpp_kernel` emits the same arithmetic as compilable C++ |
| Full-episode wall clock stays sane | `tests/test_performance.py::test_full_episode_wall_clock_sane` |
| Browser engine stays honest | the TypeScript port runs the same scenario engine; `npm run probe` and the page smoke gate keep behaviour aligned |

Simulation slots are discrete and seed-defined, so the console's speed knob
changes only how fast slots are *played*, never the result: the same seed
reproduces the same mission, frame for frame, on any machine.



