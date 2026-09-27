# ASTRA — Software Documentation

**ASTRA — Adaptive Spectrum Threat Recognition & Analysis**
Adaptive scan scheduling for Electronic Support receivers.
Version 2.0.0 · SIH 2026 prototype · simulation-based research software, not operational equipment.

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
