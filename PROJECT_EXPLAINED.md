# Smart Scan Strategy for Electronic Warfare — Complete Project Explanation

*This document explains the project end to end: what problem it solves, why
that problem matters, exactly how the system works, why the approach succeeds,
how it compares with what is available commercially and academically, and what
makes it novel. It is written so that a reviewer with no prior exposure to the
codebase can understand every claim.*

---

## Table of contents

1. [The problem we were given](#1-the-problem-we-were-given)
2. [Why conventional scanning fails](#2-why-conventional-scanning-fails)
3. [What we built](#3-what-we-built)
4. [How a mission unfolds, step by step](#4-how-a-mission-unfolds-step-by-step)
5. [Inside SmartScan: the five behaviours](#5-inside-smartscan-the-five-behaviours)
6. [Why it works](#6-why-it-works)
7. [The evidence base](#7-the-evidence-base)
8. [What is included in the repository](#8-what-is-included-in-the-repository)
9. [How to run everything](#9-how-to-run-everything)
10. [Market landscape: what competes with this](#10-market-landscape-what-competes-with-this)
11. [Our unique factor](#11-our-unique-factor)
12. [Simulation fidelity: signal level and hardware](#12-simulation-fidelity-signal-level-and-hardware)
13. [Honest limitations](#13-honest-limitations)
14. [Glossary](#14-glossary)
15. [Presentation fact sheet](#15-presentation-fact-sheet)

---

## 1. The problem we were given

The SIH 2026 problem statement asks for a **Smart Scan Strategy for Electronic
Warfare**: a scheduler for an Electronic Support (ES) receiver that must find
hostile communication and radar signals **without prior reliable intelligence**
about the emitters.

The physical constraint that makes this hard: an ES receiver is highly
sensitive but its **instantaneous bandwidth** covers only a small slice of the
overall spectrum it must watch. It therefore has to *sweep* — retuning across
many frequency bands, listening to one band at a time. Interception is thus a
**two-dimensional search problem**: the receiver must be on the right
frequency at the right time. An emitter that transmits for 5 slots out of every
200 is invisible unless the receiver happens to be tuned to it during one of
those windows.

Traditional receivers are programmed before the mission with a fixed scan
pattern (*open loop*). The problem statement explicitly identifies the failure
mode of this practice: open-loop strategies "may lose time to non-threatening
emitters by not giving time to new or threatening ones." The required solution
is an ML-based scheduler that minimises intercept time while keeping the
interception rate high, evaluated on seven named figures of merit, trained from
hits and misses, capable of predicting intercept opportunities against
periodically scanning and frequency-agile emitters, and demonstrated on the
referenced datasets (JC Wise radar emitter database; Turing synthetic radar
dataset).

## 2. Why conventional scanning fails

Three structural failures, each of which our evaluation reproduces with a
reference implementation:

| Failure | What happens | Measured consequence |
|---|---|---|
| Blind coverage | Every band is visited in fixed order regardless of content | Dwell time wasted on clutter; threats found slowly |
| No memory | The scan learns nothing within or between missions | A periodic emitter's rhythm is never exploited; intercept chance is luck |
| Exploit trap | Naive adaptivity (pure banditry) camps on the richest band | Highest raw reward of any policy, but only 54% of threats ever found |

The third row deserves emphasis because it is the central tension of the whole
problem: **reward and coverage pull in opposite directions**, and the exploit
trap is precisely the pathology the problem statement warns about. A serious
evaluation must catch it — which is why our scoring gates on mission
requirements before ranking by composite score (Section 7).

## 3. What we built

A complete, tested, reproducible software system with six layers:

```
+----------------------------------------------------------------+
|  COMMAND CENTRE (React web app + FastAPI service)              |
|  overview / evaluation / live paired demonstration / docs      |
+----------------------------------------------------------------+
|  LIVE INGESTION   simulated feed | UDP bridge (real SDR) | log |
+----------------------------------------------------------------+
|  EXPLOITATION     identification vs emitter library            |
|                   multi-receiver geolocation (AOA triangulation)|
+----------------------------------------------------------------+
|  SCHEDULERS       SmartScan + 6 references (open-loop, UCB,    |
|                   linear Q, deep Q-network)                    |
+----------------------------------------------------------------+
|  RECEIVER MODEL   logistic detection law, false alarms, AOA,   |
|                   PDW output, independent noise floors         |
+----------------------------------------------------------------+
|  ENVIRONMENT      stationary / agile / periodic / spatially    |
|                   scanning emitters; truth matrix per band/slot|
+----------------------------------------------------------------+
```

Every layer is a plain Python module with no exotic dependencies (NumPy +
Matplotlib for the core; FastAPI + React only for the command centre), runs
offline, and is covered by 306 automated tests (unit, integration, API and
interface).

### The environment (`ewsmart/environment.py`)

A battlefield is a grid: `occupancy[band, t]` records ground truth — which
bands transmit at which slot. Emitters come in four behavioural classes:

- **Stationary** — always transmitting on one band.
- **Frequency-agile** — hops among a small set of bands on short dwells.
- **Periodic** — transmits on one band with a repeating period (the hardest
  and most rewarding target class).
- **Spatially scanning** — rotating radar whose main beam only illuminates the
  receiver periodically; physically modelled via rotation rate and beamwidth,
  with geometrically consistent bearings and positions.

Scenarios are fully seed-defined: a scenario JSON plus one integer reproduces a
mission exactly.

### The receiver (`ewsmart/receiver.py`)

Models a single-channel superheterodyne front-end: logistic detection
probability versus signal-to-noise ratio, per-band noise floors with
independent realisations per receiver (so cooperating platforms do not share
noise luck), false alarms when listening to empty spectrum, and measured
pulse-descriptor words (TOA, frequency, pulse width, amplitude, AOA) matching
the schema of the referenced Turing dataset.

### The schedulers (`ewsmart/schedulers.py`)

Seven policies, four of them as references that make the evaluation honest:

1. Sequential sweep — classic open loop.
2. Random scan — open loop without even determinism.
3. Priority sweep — open loop with pre-mission threat intelligence.
4. UCB bandit — adaptive but purely exploitative (demonstrates the exploit trap).
5. Linear Q-learning — reinforcement learning over hand-crafted band features.
6. Deep Q-network — MLP function approximation with replay buffer and target network.
7. **SmartScan** — the proposed hybrid (Section 5).

### The command centre (`server/`, `frontend/`, `website/`)

Three surfaces share one engine:

- **Desktop command centre** — a FastAPI service with a React console
  (Operations / Analysis / Data & Sources), packaged by PyInstaller into
  `dist/ASTRA/ASTRA.exe`. The live paired arena runs two receivers on
  byte-identical battlefields and streams synchronised frames over SSE.
- **Website console (`website/src/pages/Console.tsx`)** — the engine compiled
  to TypeScript for the browser, redesigned (rev 3) as a three-bay command
  centre:
  1. **Live Mission** — real-time A/B waterfall race (SmartScan vs a chosen
     baseline: sequential, random, UCB bandit or linear Q-learning), five
     one-click presentation demos, live KPI cards, library-identification
     board, AOA geolocation, event log with phase-lock confirmations and
     **environment-shift alerts** (baseline activity signature vs rolling
     window).
  2. **Learning Arena** — an *isolated sandbox* with its own battlefields and
     its own learner instance: full cross-episode training runs (train on hits
     and misses, memory carried between episodes), a per-episode coverage
     trend chart, and a memory reset. Nothing done here touches the Live
     Mission.
  3. **Model Lab** — headless policy shootouts on the identical battlefield
     (all five policies, same seed and reward) plus the engine-probe
     verification table: prediction accuracy SmartScan **96.9 %**, linear
     Q-learning 96.4 %, UCB 95.5 %, sequential 54.1 %, random 50.2 %
     (reproducible with `npm run probe` in `website/`).
  Prediction KPIs are shown with context (band-truly-ON share vs predicted-ON
  share) so an always-off baseline can never masquerade as "accurate".
- **Parity contract** — `website/src/engine/core.ts` and `schedulers.ts`
  mirror the Python engine's environment, receiver physics (Albersheim-style
  detection, LPI matched-filter gain, CRLB-coupled interferometer AOA) and
  scheduler behaviour; the probe script verifies the numbers headlessly.

## 4. How a mission unfolds, step by step

Consider one episode: 24 bands, 3000 time slots, roughly 25 emitters of mixed
types, no prior intelligence.

1. **Reconnaissance sweep (slots ~0–600).** SmartScan sweeps the entire
   spectrum quickly. Purpose: bootstrap statistics — which bands ever light
   up, how often, with what signal strength and bearing.
2. **Fingerprinting.** Each detection stream is tagged by an SNR + AOA
   fingerprint, so two emitters sharing a frequency remain distinct objects.
3. **Lock acquisition.** When a stream shows repeated, mutually isolated
   detections, the Rayleigh period estimator tests for a significant repeating
   rhythm (with integer refinement around the best candidate). A significant
   fit becomes a *lock*: a prediction of when that emitter will next transmit.
4. **Cued pursuit.** For proven locks, the receiver stops searching blindly:
   it arrives at the emitter's band shortly before the predicted window opens
   and dwells through it. Interception changes from luck to schedule.
5. **Predict-and-probe.** Candidate (not yet proven) rhythms get single cheap
   probes at their predicted window centres — being wrong costs one slot.
6. **Characterisation bursts.** A detection on a quiet stream triggers a short
   camping burst through the next cycle to gather lock evidence quickly;
   streams later proven persistent-but-valueless are blacklisted.
7. **Value-weighted rotation.** Time not committed to locks is spent by a
   discounted UCB policy with recency guarantees (no band starves) and an
   exploitation ramp that shifts effort toward high-value bands as confidence
   grows.
8. **Continuous validation.** Every lock predicts; predictions that miss
   repeatedly are deleted automatically. The scheduler can never anchor on a
   stale belief — this is what makes it robust when emitters move or go silent.
9. **End of episode.** Figures of merit are computed against the truth matrix;
   learned parameters persist to disk as pickle-free NumPy archives.

## 5. Inside SmartScan: the five behaviours

SmartScan is not one algorithm but a small control system that multiplexes five
behaviours according to a **learned confidence signal**:

| # | Behaviour | Activated when | Failure it prevents |
|---|---|---|---|
| 1 | Recon sweep | Episode start / low global knowledge | Acting on no information |
| 2 | Cued pursuit of proven phase locks | Lock validated by ≥ N isolated detections | Ignoring predictable targets |
| 3 | Predict-and-probe | Unproven candidate rhythm exists | Never testing hypotheses |
| 4 | Characterisation burst | Isolated hit on a quiet fingerprint | Under-sampling rare emitters |
| 5 | Value-weighted rotation | Otherwise (always available as fallback) | Starvation; over-commitment to one band |

Two design rules make the combination robust:

- **Cheap falsification.** Hypotheses are tested with the cheapest possible
  probe; wrong hypotheses die fast and cost little.
- **Asymmetric commitment.** Commitment scales with evidence: a lock needs
  repeated mutually-isolated detections plus passing a significance threshold,
  and it stays alive only while its predictions keep coming true.

Machine learning enters in three places: the Q-style value estimates that
drive rotation priorities, the confidence gating that decides behaviour
proportions, and (in the reference implementations) full RL agents trained on
hit/miss rewards for comparison.

## 6. Why it works

Four mechanisms, each tied to measurable evidence in the ablation study:

1. **Prediction converts search into scheduling.** Once a periodic emitter's
   rhythm is known, intercepting it requires zero search — just presence at the
   predicted window. This attacks the two-dimensional (frequency × time) search
   problem directly: the time dimension collapses for predictable emitters.
   Removing phase-lock pursuit in the ablation costs the largest reward drop of
   any component.
2. **Coverage is protected structurally, not hoped for.** The rotation
   fallback guarantees every band is revisited (recency term), so threats in
   quiet regions are found eventually. Pure exploitation has no such guarantee
   — and indeed misses 46% of threats in our evaluation.
3. **False beliefs are cheap and short-lived.** Miss-based validation deletes
   wrong locks; probes cost one slot. The system pays a small, bounded price
   for wrong hypotheses instead of a large unbounded one.
4. **Fingerprints prevent double-chasing.** SNR+AOA clustering keeps co-channel
   emitters distinct, and two locks sharing bearing and period are merged into
   one emitter family — the receiver does not waste dwell time chasing the same
   radar twice.

The net effect resolves the reward-versus-coverage trade-off rather than
picking a point on it: **2.1× the sequential scan's reward at +17 points of
threat coverage** — and under KPP gating it is the only mission-capable policy
in the field (Section 7).

## 7. The evidence base

All numbers below are generated by `python -m ewsmart.experiments --suite
full` into `results/suite_results.json`; nothing is hand-entered.

**Monte Carlo evaluation.** 50 held-out episodes (canonical protocol: 24 bands × 3000 slots, base_seed 9000),
mean ± 95% CI on all figures of merit, seven schedulers.

**KPP gate and Mission Effectiveness Score.** Following defence test &
evaluation practice, a scheduler must pass hard Key Performance Parameters to
be considered mission-capable: threat coverage ≥ 0.90, prediction accuracy ≥
0.50, false-alarm rate ≤ 5×10⁻⁴/slot. Capable systems are ranked by MES (mean
of six normalised problem-statement FoMs). Outcome: **SmartScan is the only
mission-capable scheduler**; the exploit-only bandit, despite the highest raw
reward, is disqualified by coverage.

**Statistical significance.** Paired per-episode permutation tests on gated
MES (violating episodes score zero): SmartScan exceeds every comparator at
p < 1e-4 with Holm-Bonferroni correction over the six comparisons.

**Supporting studies.** ROC sweep across sensitivity thresholds; sensitivity
surfaces over band count, SNR, agility and emitter density; five-way ablation
attributing SmartScan's performance to its behaviours; cooperative
multi-receiver scaling (663 → 1192 → 1808 total reward for 1 → 2 → 3
de-conflicted receivers); geolocation CEP improving 3.2 km → 1.7 km as
receivers grow 2 → 4; identification accuracy 86% (14/19 streams) on the synthetic reference episode
against the JC Wise-style library.

**Console metric audit.** The web console's headline KPIs are themselves
audited: `npm run audit:metrics` (in `website/`) replays the full KPI pipeline
across 4 seeds × 4 baselines and diffs every card against ground truth. The
first audit run caught two real defects — phase-lock cards displaying the
*opponent's* locks, and time-to-first-fix averaged over all hit slots (≈ half
the episode) — both fixed and now contractually specified in manual §24.
Residual differences the audit cannot close (UCB's exploit trap, survivorship
in paired rewards, sweep cold-start) are documented as honest, measured
properties in §24.2.

**Console honesty harness.** The threat board grades identification confidence
on *measured* fingerprints (SNR-biased frequency and pulse width,
circular-mean AOA) — never ground truth — and MISS rows are shown rather than
hidden. The geolocation panel ports the Python triangulation to TypeScript
(least squares plus Gauss–Newton refinement), draws the receiver ring and
bearing lines, and reports mean/CEP50/CEP90 against truth used only for
scoring (CEP50 ≈ 2 km on the default scene).

**Learning honesty.** Training claims are backed by held-out greedy evaluation
curves (exploration disabled, weights snapshotted). Linear Q-learning provably
improves; the DQN declines on this sparse-reward task and we report that as
measured — an intentionally disclosed negative result.

## 8. What is included in the repository

| Path | Contents |
|---|---|
| `ewsmart/` | Core library: environment, receiver, 7 schedulers, metrics/KPP-MES, experiments, identification, geolocation, persistence, live ingestion |
| `server/`, `frontend/` | Desktop command centre: FastAPI service + React console (Operations / Analysis / Data & Sources) |
| `website/` | SIH presentation site (`astra-ew.vercel.app`): landing page, browser console (five policies, seed-exact), 29-section manual, verified results — gated by `npm run check` (docs + smoke + build + dist verify), `npm run probe`, `npm run audit:metrics` |
| `docs/` | Single source of the 29-section software manual — `python -m tools.export_docs` regenerates the website copy, the desktop-app copy and `website/public/docs/manual.md` — plus the VitePress documentation site |
| `desktop_qt.py`, `astra.spec`, `installer/` | Desktop application and its build chain: `tools/build_exe.ps1` (PyInstaller → `dist/ASTRA/ASTRA.exe`) and Inno Setup → `ASTRA-Setup-3.0.0.exe` (~164 MB) |
| `tools/sdr_bridge.py` | UDP/CSV bridges for feeding real SDR or processor output into the live pipeline |
| `scenarios/` | Ready-made JSON battle configurations |
| `models/, results/, figures/` | Trained schedulers, generated results, publication-quality charts |
| `tests/` | 306 automated tests |
| `launch.ps1` / `START.bat` | One-click launcher (builds frontend if needed, boots API, opens browser) |

Engineering guarantees: strict-JSON outputs (NaN-safe), pickle-free safe model
artifacts loaded with `allow_pickle=False`, independent receiver noise
(tested), seed-exact reproducibility, Docker image.

## 9. How to run everything

```powershell
# one-click (builds frontend if needed, starts service, opens browser)
START.bat

# manual equivalent
cd frontend; npm install; npm run build; cd ..
python -m uvicorn server.api:app --port 8000

# regenerate every published number
python -m ewsmart.experiments --suite full

# single episode with all schedulers
python -m ewsmart.runner --scenario scenarios/demo.json --save-dir models --json-out results.json

# run the test battery
python -X utf8 tests/test_smartscan.py   # (each file in tests/ runs standalone)

# container
docker build -t ewsmart . ; docker run -p 8000:8000 ewsmart

# presentation website (website/): full verification gate — manual sync,
# render smoke test, production build, dist-link verification
cd website; npm install; npm run check

# engine parity probe + console KPI metric audit
npm run probe          # prediction-accuracy table (96.9% vs 54.1%)
npm run audit:metrics  # KPI pipeline across 4 seeds × 4 baselines

# regenerate the manual in every published location
cd ..; python -m tools.export_docs

# rebuild the desktop app and its installer
powershell -File tools\build_exe.ps1        # -> dist\ASTRA\ASTRA.exe
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\astra_installer.iss
```

## 10. Market landscape: what competes with this

There is no shrink-wrapped product that does exactly this; competition comes
from four directions. The honest comparison:

| Category | Examples | What they give | Where they fall short of this work |
|---|---|---|---|
| Full-spectrum ESM/ELINT suites on defence platforms | Thales, Leonardo, Saab, Elbit, L3Harris programme lines | Certified hardware, wideband channelised receivers, operator consoles | Scheduling logic is proprietary and largely pre-mission programmed; nothing reproducible or inspectable; hardware cost is prohibitive for algorithm research |
| EW simulation & training environments | Commercial EW wargaming/trainer frameworks | Scenario authoring, operator training | Built for training humans, not for discovering scheduling policies; rarely expose clean FoM APIs or statistical harnesses |
| SDR toolkits | GNU Radio and friends | Real-time DSP building blocks | Provide signal processing, not cognitive scan strategy; no emitter-behaviour modelling, no mission-level evaluation |
| Academic cognitive-EW / RL sensor-scheduling literature | Numerous papers on RL/bandit radar and sensor scheduling | Algorithmic ideas close to ours | Typically single-technique studies, small ad-hoc evaluations, no end-to-end pipeline (environment → receiver → identification → geolocation → live demo), almost never reproducible artefacts |

Positioning in one sentence: **existing products sell hardware with embedded,
fixed scan doctrine; academic work proposes fragments of smarter doctrine; we
deliver a complete, inspectable, statistically evaluated doctrine engine that
swaps onto either world** — it consumes standard PDWs from a real front-end
over UDP today, and it is small enough to embed tomorrow.

## 11. Our unique factor

Six elements, in decreasing order of defensibility:

1. **Confidence-multiplexed behavioural hybrid.** Not another monolithic RL
   agent: five auditable behaviours (survey, pursuit, probe, burst, rotation)
   governed by learned confidence, each cheap to disable — and the ablation
   quantifies exactly what each contributes. This gives the interpretability
   procurement requires with the adaptivity learning provides.
2. **Online lock validation.** Predictions must keep coming true; stale locks
   self-destruct. This is the mechanism that lets the system operate with *no
   prior intelligence* and survive non-stationary emitters — the precise
   requirement of the problem statement, and the thing naive adaptive scans
   lack.
3. **KPP-gated Mission Effectiveness Score as the headline metric.** We adopt
   the military T&E convention (hard gates first, composite score second). It
   exposes the exploit trap that raw-reward comparisons hide, and it is why we
   can state plainly: *under mission requirements, SmartScan is the only
   viable scheduler in its field.*
4. **Paired identical-battlefield demonstration.** The live page flies two
   receivers over byte-identical scenarios side by side. Attribution is
   airtight: differences are the strategy, nothing else. No competitor demo we
   are aware of offers controlled A/B proof in front of a reviewer.
5. **Dataset-calibrated realism chain.** PDWs from the referenced Turing/JC
   Wise ecosystem flow through fingerprinting → scenario calibration →
   scheduling → identification, closing the loop the problem statement asked
   for, offline-first.
6. **Total reproducibility discipline.** Seeds, JSON scenarios, strict JSON
   outputs, pickle-free artifacts, 306 tests, one-command Docker. The
   presentation website ships behind the same gates: `npm run check` (manual
   sync + render smoke + build + dist verification) and `npm run audit:metrics`
   must both pass. Everything a government evaluator would ask to verify a
   claim already exists in the box.

**Trademark sentence for the pitch:** *SmartScan turns the receiver from a
torch swept in the dark into an investigator that learns the room — same
hardware, same spectrum, radically more found.*

## 12. Simulation fidelity: signal level and hardware

A fair criticism of any scheduler study is that it can hide behind its
abstraction. ASTRA now implements the signal-processing and hardware layers
that sit underneath the scheduling decision, so the abstraction is a documented
choice rather than a gap.

**Pulse-level deinterleaving.** A real ES receiver's wideband front-end sees an
interleaved stream of pulses from every emitter in view — at combat densities
105–106 pulses per second — and must separate it back into individual emitters
before anything can be tracked. `ewsmart/deinterleave.py` does exactly that:
descriptor clustering on (RF, pulse width, AOA), an all-pairs
difference-of-time-of-arrival histogram for the dominant PRI, coarse-to-fine
period sharpening by phase-histogram entropy minimisation, and a circular-phase
test that discriminates fixed, staggered and jittered pulse trains. On a
four-emitter test scene (fixed 250 µs, staggered three-level 97 µs, jittered
410 µs ±12%, LPI 600 µs) it recovers every emitter: pulse purity 1.0,
fragmentation 1.0, mean PRI error 0.4%, PRI-model classification 100%.

**Waveform classes and the matched filter.** Emitters carry a waveform class
(`pulsed`, `lpi_fmcw`, `lpi_barker`) and a time-bandwidth product. A Low
Probability of Intercept emitter's in-channel SNR is reduced by exactly
`10 log10(BT)`, so it is invisible to a plain radiometer — and a receiver
running the matched-filter / de-chirp bank earns that gain back. Measured on a
−14 dB emitter with BT = 256: **283 of 300 dwells detected with matched
filtering, 5 of 300 without.**

**Front-end hardware.** `ewsmart/frontend.py` models what the hardware does to
a dwell: synthesiser settling time blanks part of every retuned dwell (lost
integration time, hence lost processing gain), a strong signal above the 1 dB
compression point raises the noise floor and desensitises weaker co-channel
emitters, mixer non-linearity folds third-order intermodulation products and
image/mixer spurs into the band, and a saturating ADC folds odd harmonics back.
Below P1dB the model is exactly linear, so attaching a front-end never changes
normal operation.

**Angle of arrival.** Instead of a constant 2.5° Gaussian bearing error, the
receiver runs a dual-baseline phase interferometer whose error follows the
Cramér–Rao bound — so it depends on SNR and frequency, and weak or
high-frequency emitters fingerprint poorly. At 20 dB SNR the measured error is
0.35–0.5° and unbiased across all bearings; at −10 dB it degrades to tens of
degrees, exactly as the bound predicts.

**Portability.** The per-slot decision is also implemented in Q8.8 saturating
fixed point (`ewsmart/realtime.py`): an O(n_bands) integer multiply-accumulate
with no dynamic allocation and no per-slot transcendental. Over 200 randomised
states it matches the float reference argmax, and `tools/export_cpp_kernel.py`
emits the same arithmetic as compilable C++ for an FPGA/DSP port.

**Learning in the decision core.** `ewsmart/meta.py` adds a LinUCB contextual
bandit over the scheduler's five behaviours. Every dwell outcome trains it on
which behaviour paid in which situation; a safe action mask means it can never
select a behaviour whose preconditions do not hold. A full episode trains it
from 500+ outcome triples, and its learned preferences are directly
inspectable.

**Scale-invariant tuning.** `ewsmart/calibration.py` derives the behaviour
constants from the scenario scale (bands, horizon, emitter density) instead of
hard-coding values tuned for one spectrum size — and reproduces the canonical
constants exactly, so it is a no-op where the tuning is known good.

## 13. Honest limitations

Stated up front, because credibility is part of the product:

- There is no digitised-I/Q simulation: the receiver works on PDWs and dwell
  statistics, with modulation represented by waveform class and processing
  gain.
- Deinterleaving is the classical textbook pipeline (clustering + DTOA/PRI
  estimation), not a learned deinterleaver.
- Propagation is geometric — path loss, multipath and terrain are not modelled.
- The learned behaviour arbiter currently trains in shadow mode; letting it fly
  the mission directly is the next step.
- The DQN reference declines on this sparse-reward task; the flagship is a
  designed hybrid with online learning, and deep-RL improvement remains future
  work.
- Decision latency is Python-bound (measured 0.42 ms mean / 0.16 ms p50 per
  decision, p95 ≈ 1.8 ms on an AMD Ryzen — `results/performance.json`,
  regenerated 2026-09-27); the fixed-point kernel and generated C++ header are
  the porting path to hardware budgets.
- Identification library profiles are illustrative public-domain classes, not
  operational ELINT data.

## 14. Glossary

| Term | Meaning |
|---|---|
| ESM / ES | Electronic Support Measures / Support — passive search, intercept and analysis of emissions |
| Open loop | Scan pattern fixed before the mission; does not react to what is heard |
| PDW | Pulse Descriptor Word — TOA, frequency, pulse width, amplitude, AOA measurement of one pulse group |
| Dwell | One listening interval on one band |
| Intercept | Receiver present on the right band during an emitter's transmission |
| Phase lock (ours) | Validated estimate of a periodic emitter's repeat period and ON-window timing |
| KPP | Key Performance Parameter — a hard pass/fail operational requirement |
| MES | Mission Effectiveness Score — composite of normalised FoMs after KPP gating |
| CEP | Circular Error Probable — median radius containing half of geolocation errors |

## 15. Presentation fact sheet

A compact table of verified headline facts for slides and narration. Every
value is reproducible from the repository; the right-hand column is its exact
source of truth. Use this alongside `ppt.md` (the slide-spec prompt for the
6-slide deck) and `YOUTUBE_SCRIPT.md` (the 6:00 narration script).

| Fact | Value | Source |
|---|---|---|
| Problem | Smart Scan Strategy for Electronic Warfare (SIH 2026 statement): find emitters without prior intelligence | problem statement |
| Live site | `https://astra-ew.vercel.app` — landing page, browser console, 29-section manual, verified results | deployed site |
| Repository | `https://github.com/RARPlayzDev/Astra` | — |
| Scheduling policies | 7 in Python; 5 in the browser console (SmartScan, sequential sweep, random scan, UCB bandit, linear Q) | `ewsmart/schedulers.py`, manual §23 |
| Canonical protocol | 50 held-out episodes × 7 schedulers × 24 bands × 3000 slots, base seed 9000, mean ± 95% CI | `CANONICAL_PROTOCOL`, `results/benchmark.json`, `website/public/data/results.json` |
| KPP outcome | SmartScan is the only mission-capable scheduler; the highest-raw-reward UCB bandit is disqualified at 52.7% threat coverage | `results/suite_results.json` gate table |
| Threat coverage (SmartScan) | 90.3% | `results.json` (Results page) |
| Next-window prediction | SmartScan 96.9% vs sequential 54.1%, random 50.2%, UCB 95.5%, linear Q 96.4% (seed 4242) | `npm run probe` |
| Statistical significance | Paired permutation tests on gated MES, Holm-corrected, p < 1e-4 against every comparator | `suite_results.json`, manual §12 |
| Automated tests | 306 collected, all passing | `python -m pytest --collect-only -q` |
| Decision latency | SmartScan 0.42 ms mean / 0.16 ms p50 per decision (Python) | `results/performance.json` |
| Deep-RL benchmark | Deep Q-network declines under sparse non-stationary reward — shipped as a documented negative result | `suite_results.json` → `learning` |
| Identification | 86% stream identification (14/19) on the synthetic reference episode | `suite_results.json` → `identification` |
| Geolocation scaling | CEP 3.2 km → 1.7 km as receivers grow 2 → 4 | `suite_results.json` → `geolocation` |
| Multi-receiver scaling | Total reward 663 → 1192 → 1808 for 1 → 2 → 3 de-conflicted receivers | `suite_results.json` → `multireceiver` |
| Console metric audit | `npm run audit:metrics`: 4 seeds × 4 baselines; two display bugs found and fixed; residual caveats documented in manual §24.2 | `website/scripts/metric_audit.ts` |
| Documentation | 29-section manual, synced into website and desktop app by one command | `python -m tools.export_docs`, `npm run docs:check` |
| Desktop installer | `ASTRA-Setup-3.0.0.exe`, 164,502,630 bytes (~164 MB), built 2026-09-30 with the current manual | `installer/`, GitHub Releases |
| Demo path | Website first — one-click flagship race, ~35 s fast path — then the desktop app | `YOUTUBE_SCRIPT.md` §1b, Scene 8 |
| Video reference | Narration timed to exactly 6:00 (744 spoken words at 145 wpm + ~52 s action beats) | `YOUTUBE_SCRIPT.md` |

*Episode-count note: `results/*.json` records the protocol as **50** held-out
episodes, and that is the number in the manual, this document and the Results
page data file. Some marketing prose elsewhere (site headings, video script)
still rounds it to "200-episode"; verify against the artifacts before quoting,
or regenerate the suite at 200 episodes so every surface agrees.*
