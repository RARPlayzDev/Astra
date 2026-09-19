# Smart Scan Strategy for Electronic Warfare â€” Complete Project Explanation

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

---

## 1. The problem we were given

The SIH 2026 problem statement asks for a **Smart Scan Strategy for Electronic
Warfare**: a scheduler for an Electronic Support (ES) receiver that must find
hostile communication and radar signals **without prior reliable intelligence**
about the emitters.

The physical constraint that makes this hard: an ES receiver is highly
sensitive but its **instantaneous bandwidth** covers only a small slice of the
overall spectrum it must watch. It therefore has to *sweep* â€” retuning across
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
evaluation must catch it â€” which is why our scoring gates on mission
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

A battlefield is a grid: `occupancy[band, t]` records ground truth â€” which
bands transmit at which slot. Emitters come in four behavioural classes:

- **Stationary** â€” always transmitting on one band.
- **Frequency-agile** â€” hops among a small set of bands on short dwells.
- **Periodic** â€” transmits on one band with a repeating period (the hardest
  and most rewarding target class).
- **Spatially scanning** â€” rotating radar whose main beam only illuminates the
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

1. Sequential sweep â€” classic open loop.
2. Random scan â€” open loop without even determinism.
3. Priority sweep â€” open loop with pre-mission threat intelligence.
4. UCB bandit â€” adaptive but purely exploitative (demonstrates the exploit trap).
5. Linear Q-learning â€” reinforcement learning over hand-crafted band features.
6. Deep Q-network â€” MLP function approximation with replay buffer and target network.
7. **SmartScan** â€” the proposed hybrid (Section 5).

### The command centre (`server/`, `frontend/`, `website/`)

Three surfaces share one engine:

- **Desktop command centre** â€” a FastAPI service with a React console
  (Operations / Analysis / Data & Sources), packaged by PyInstaller into
  `dist/ASTRA/ASTRA.exe`. The live paired arena runs two receivers on
  byte-identical battlefields and streams synchronised frames over SSE.
- **Website console (`website/src/pages/Console.tsx`)** â€” the engine compiled
  to TypeScript for the browser, redesigned (rev 3) as a three-bay command
  centre:
  1. **Live Mission** â€” real-time A/B waterfall race (SmartScan vs a chosen
     baseline: sequential, random, UCB bandit or linear Q-learning), five
     one-click presentation demos, live KPI cards, library-identification
     board, AOA geolocation, event log with phase-lock confirmations and
     **environment-shift alerts** (baseline activity signature vs rolling
     window).
  2. **Learning Arena** â€” an *isolated sandbox* with its own battlefields and
     its own learner instance: full cross-episode training runs (train on hits
     and misses, memory carried between episodes), a per-episode coverage
     trend chart, and a memory reset. Nothing done here touches the Live
     Mission.
  3. **Model Lab** â€” headless policy shootouts on the identical battlefield
     (all five policies, same seed and reward) plus the engine-probe
     verification table: prediction accuracy SmartScan **96.9 %**, linear
     Q-learning 96.4 %, UCB 95.5 %, sequential 54.1 %, random 50.2 %
     (reproducible with `npm run probe` in `website/`).
  Prediction KPIs are shown with context (band-truly-ON share vs predicted-ON
  share) so an always-off baseline can never masquerade as "accurate".
- **Parity contract** â€” `website/src/engine/core.ts` and `schedulers.ts`
  mirror the Python engine's environment, receiver physics (Albersheim-style
  detection, LPI matched-filter gain, CRLB-coupled interferometer AOA) and
  scheduler behaviour; the probe script verifies the numbers headlessly.

## 4. How a mission unfolds, step by step

Consider one episode: 24 bands, 3000 time slots, roughly 25 emitters of mixed
types, no prior intelligence.

1. **Reconnaissance sweep (slots ~0â€“600).** SmartScan sweeps the entire
   spectrum quickly. Purpose: bootstrap statistics â€” which bands ever light
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
   probes at their predicted window centres â€” being wrong costs one slot.
6. **Characterisation bursts.** A detection on a quiet stream triggers a short
   camping burst through the next cycle to gather lock evidence quickly;
   streams later proven persistent-but-valueless are blacklisted.
7. **Value-weighted rotation.** Time not committed to locks is spent by a
   discounted UCB policy with recency guarantees (no band starves) and an
   exploitation ramp that shifts effort toward high-value bands as confidence
   grows.
8. **Continuous validation.** Every lock predicts; predictions that miss
   repeatedly are deleted automatically. The scheduler can never anchor on a
   stale belief â€” this is what makes it robust when emitters move or go silent.
9. **End of episode.** Figures of merit are computed against the truth matrix;
   learned parameters persist to disk as pickle-free NumPy archives.

## 5. Inside SmartScan: the five behaviours

SmartScan is not one algorithm but a small control system that multiplexes five
behaviours according to a **learned confidence signal**:

| # | Behaviour | Activated when | Failure it prevents |
|---|---|---|---|
| 1 | Recon sweep | Episode start / low global knowledge | Acting on no information |
| 2 | Cued pursuit of proven phase locks | Lock validated by â‰¥ N isolated detections | Ignoring predictable targets |
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
   rhythm is known, intercepting it requires zero search â€” just presence at the
   predicted window. This attacks the two-dimensional (frequency Ã— time) search
   problem directly: the time dimension collapses for predictable emitters.
   Removing phase-lock pursuit in the ablation costs the largest reward drop of
   any component.
2. **Coverage is protected structurally, not hoped for.** The rotation
   fallback guarantees every band is revisited (recency term), so threats in
   quiet regions are found eventually. Pure exploitation has no such guarantee
   â€” and indeed misses 46% of threats in our evaluation.
3. **False beliefs are cheap and short-lived.** Miss-based validation deletes
   wrong locks; probes cost one slot. The system pays a small, bounded price
   for wrong hypotheses instead of a large unbounded one.
4. **Fingerprints prevent double-chasing.** SNR+AOA clustering keeps co-channel
   emitters distinct, and two locks sharing bearing and period are merged into
   one emitter family â€” the receiver does not waste dwell time chasing the same
   radar twice.

The net effect resolves the reward-versus-coverage trade-off rather than
picking a point on it: **2.1Ã— the sequential scan's reward at +17 points of
threat coverage** â€” and under KPP gating it is the only mission-capable policy
in the field (Section 7).

## 7. The evidence base

All numbers below are generated by `python -m ewsmart.experiments --suite
full` into `results/suite_results.json`; nothing is hand-entered.

**Monte Carlo evaluation.** 50 held-out episodes (canonical protocol: 24 bands Ã— 3000 slots, base_seed 9000),
mean Â± 95% CI on all figures of merit, seven schedulers.

**KPP gate and Mission Effectiveness Score.** Following defence test &
evaluation practice, a scheduler must pass hard Key Performance Parameters to
be considered mission-capable: threat coverage â‰¥ 0.90, prediction accuracy â‰¥
0.50, false-alarm rate â‰¤ 5Ã—10â»â´/slot. Capable systems are ranked by MES (mean
of six normalised problem-statement FoMs). Outcome: **SmartScan is the only
mission-capable scheduler**; the exploit-only bandit, despite the highest raw
reward, is disqualified by coverage.

**Statistical significance.** Paired per-episode permutation tests on gated
MES (violating episodes score zero): SmartScan exceeds every comparator at
p < 1e-4 with Holm-Bonferroni correction over the six comparisons.

**Supporting studies.** ROC sweep across sensitivity thresholds; sensitivity
surfaces over band count, SNR, agility and emitter density; five-way ablation
attributing SmartScan's performance to its behaviours; cooperative
multi-receiver scaling (663 â†’ 1192 â†’ 1808 total reward for 1 â†’ 2 â†’ 3
de-conflicted receivers); geolocation CEP improving 3.2 km â†’ 1.7 km as
receivers grow 2 â†’ 4; identification accuracy 86% (14/19 streams) on the synthetic reference episode
against the JC Wise-style library.

**Learning honesty.** Training claims are backed by held-out greedy evaluation
curves (exploration disabled, weights snapshotted). Linear Q-learning provably
improves; the DQN declines on this sparse-reward task and we report that as
measured â€” an intentionally disclosed negative result.

## 8. What is included in the repository

| Path | Contents |
|---|---|
| `ewsmart/` | Core library: environment, receiver, 7 schedulers, metrics/KPP-MES, experiments, identification, geolocation, persistence, live ingestion |
| `server/`, `frontend/` | Command centre: FastAPI service + React application (this website) |
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
```

## 10. Market landscape: what competes with this

There is no shrink-wrapped product that does exactly this; competition comes
from four directions. The honest comparison:

| Category | Examples | What they give | Where they fall short of this work |
|---|---|---|---|
| Full-spectrum ESM/ELINT suites on defence platforms | Thales, Leonardo, Saab, Elbit, L3Harris programme lines | Certified hardware, wideband channelised receivers, operator consoles | Scheduling logic is proprietary and largely pre-mission programmed; nothing reproducible or inspectable; hardware cost is prohibitive for algorithm research |
| EW simulation & training environments | Commercial EW wargaming/trainer frameworks | Scenario authoring, operator training | Built for training humans, not for discovering scheduling policies; rarely expose clean FoM APIs or statistical harnesses |
| SDR toolkits | GNU Radio and friends | Real-time DSP building blocks | Provide signal processing, not cognitive scan strategy; no emitter-behaviour modelling, no mission-level evaluation |
| Academic cognitive-EW / RL sensor-scheduling literature | Numerous papers on RL/bandit radar and sensor scheduling | Algorithmic ideas close to ours | Typically single-technique studies, small ad-hoc evaluations, no end-to-end pipeline (environment â†’ receiver â†’ identification â†’ geolocation â†’ live demo), almost never reproducible artefacts |

Positioning in one sentence: **existing products sell hardware with embedded,
fixed scan doctrine; academic work proposes fragments of smarter doctrine; we
deliver a complete, inspectable, statistically evaluated doctrine engine that
swaps onto either world** â€” it consumes standard PDWs from a real front-end
over UDP today, and it is small enough to embed tomorrow.

## 11. Our unique factor

Six elements, in decreasing order of defensibility:

1. **Confidence-multiplexed behavioural hybrid.** Not another monolithic RL
   agent: five auditable behaviours (survey, pursuit, probe, burst, rotation)
   governed by learned confidence, each cheap to disable â€” and the ablation
   quantifies exactly what each contributes. This gives the interpretability
   procurement requires with the adaptivity learning provides.
2. **Online lock validation.** Predictions must keep coming true; stale locks
   self-destruct. This is the mechanism that lets the system operate with *no
   prior intelligence* and survive non-stationary emitters â€” the precise
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
   Wise ecosystem flow through fingerprinting â†’ scenario calibration â†’
   scheduling â†’ identification, closing the loop the problem statement asked
   for, offline-first.
6. **Total reproducibility discipline.** Seeds, JSON scenarios, strict JSON
   outputs, pickle-free artifacts, 306 tests, one-command Docker. Everything a
   government evaluator would ask to verify a claim already exists in the box.

**Trademark sentence for the pitch:** *SmartScan turns the receiver from a
torch swept in the dark into an investigator that learns the room â€” same
hardware, same spectrum, radically more found.*

## 12. Simulation fidelity: signal level and hardware

A fair criticism of any scheduler study is that it can hide behind its
abstraction. ASTRA now implements the signal-processing and hardware layers
that sit underneath the scheduling decision, so the abstraction is a documented
choice rather than a gap.

**Pulse-level deinterleaving.** A real ES receiver's wideband front-end sees an
interleaved stream of pulses from every emitter in view â€” at combat densities
105â€“106 pulses per second â€” and must separate it back into individual emitters
before anything can be tracked. `ewsmart/deinterleave.py` does exactly that:
descriptor clustering on (RF, pulse width, AOA), an all-pairs
difference-of-time-of-arrival histogram for the dominant PRI, coarse-to-fine
period sharpening by phase-histogram entropy minimisation, and a circular-phase
test that discriminates fixed, staggered and jittered pulse trains. On a
four-emitter test scene (fixed 250 Âµs, staggered three-level 97 Âµs, jittered
410 Âµs Â±12%, LPI 600 Âµs) it recovers every emitter: pulse purity 1.0,
fragmentation 1.0, mean PRI error 0.4%, PRI-model classification 100%.

**Waveform classes and the matched filter.** Emitters carry a waveform class
(`pulsed`, `lpi_fmcw`, `lpi_barker`) and a time-bandwidth product. A Low
Probability of Intercept emitter's in-channel SNR is reduced by exactly
`10 log10(BT)`, so it is invisible to a plain radiometer â€” and a receiver
running the matched-filter / de-chirp bank earns that gain back. Measured on a
âˆ’14 dB emitter with BT = 256: **283 of 300 dwells detected with matched
filtering, 5 of 300 without.**

**Front-end hardware.** `ewsmart/frontend.py` models what the hardware does to
a dwell: synthesiser settling time blanks part of every retuned dwell (lost
integration time, hence lost processing gain), a strong signal above the 1 dB
compression point raises the noise floor and desensitises weaker co-channel
emitters, mixer non-linearity folds third-order intermodulation products and
image/mixer spurs into the band, and a saturating ADC folds odd harmonics back.
Below P1dB the model is exactly linear, so attaching a front-end never changes
normal operation.

**Angle of arrival.** Instead of a constant 2.5Â° Gaussian bearing error, the
receiver runs a dual-baseline phase interferometer whose error follows the
CramÃ©râ€“Rao bound â€” so it depends on SNR and frequency, and weak or
high-frequency emitters fingerprint poorly. At 20 dB SNR the measured error is
0.35â€“0.5Â° and unbiased across all bearings; at âˆ’10 dB it degrades to tens of
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
hard-coding values tuned for one spectrum size â€” and reproduces the canonical
constants exactly, so it is a no-op where the tuning is known good.

## 13. Honest limitations

Stated up front, because credibility is part of the product:

- There is no digitised-I/Q simulation: the receiver works on PDWs and dwell
  statistics, with modulation represented by waveform class and processing
  gain.
- Deinterleaving is the classical textbook pipeline (clustering + DTOA/PRI
  estimation), not a learned deinterleaver.
- Propagation is geometric â€” path loss, multipath and terrain are not modelled.
- The learned behaviour arbiter currently trains in shadow mode; letting it fly
  the mission directly is the next step.
- The DQN reference declines on this sparse-reward task; the flagship is a
  designed hybrid with online learning, and deep-RL improvement remains future
  work.
- Decision latency is Python-bound (~0.5â€“0.8 ms); the fixed-point kernel and
  generated C++ header are the porting path to hardware budgets.
- Identification library profiles are illustrative public-domain classes, not
  operational ELINT data.

## 14. Glossary

| Term | Meaning |
|---|---|
| ESM / ES | Electronic Support Measures / Support â€” passive search, intercept and analysis of emissions |
| Open loop | Scan pattern fixed before the mission; does not react to what is heard |
| PDW | Pulse Descriptor Word â€” TOA, frequency, pulse width, amplitude, AOA measurement of one pulse group |
| Dwell | One listening interval on one band |
| Intercept | Receiver present on the right band during an emitter's transmission |
| Phase lock (ours) | Validated estimate of a periodic emitter's repeat period and ON-window timing |
| KPP | Key Performance Parameter â€” a hard pass/fail operational requirement |
| MES | Mission Effectiveness Score â€” composite of normalised FoMs after KPP gating |
| CEP | Circular Error Probable â€” median radius containing half of geolocation errors |
