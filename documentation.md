# ASTRA — Complete Project Documentation

**Adaptive Spectrum Threat Recognition & Analysis — Smart Scan Strategy for
Electronic Warfare**
Version 2.0.0 · SIH 2026 prototype · simulation-based research software, not
operational equipment.

This document is the single submission-ready reference for the project. It
documents **every feature**: what it does, how it works, where it lives, and
how it is verified. Where a number is quoted it is a *measured* value produced
by the repository's own test suite or benchmark artifacts, not an estimate.

Companion documents: `PROJECT_EXPLAINED.md` (narrative walkthrough),
`docs/ASTRA_Software_Documentation.md` (the user manual the desktop app serves
at `/manual` and the website renders), `docs/ps-coverage-v2.md`
(phrase-by-phrase problem-statement audit), `EVALUATION.md` (how to evaluate the
submission).

---

## 1. What the system is

ASTRA schedules the scan pattern of an Electronic Support (ES) receiver. Such a
receiver is sensitive but narrowband: it can listen to one slice of spectrum at
a time while remaining responsible for a far wider range. Interception is
therefore a two-dimensional search — the receiver must be on the right frequency
at the right time — and a fixed pre-mission sweep wastes dwell time on empty or
unimportant bands while missing new or threatening emitters.

ASTRA decides *where to listen next* from what has already been heard: it
surveys the spectrum, learns each emitter's behaviour, predicts when periodic
emitters will transmit again, positions the receiver on those windows before
they open, and performs the pulse-level signal processing (deinterleaving,
matched filtering) that real ESM hardware does before any of that reasoning can
start.

### 1.1 Problem-statement mapping

| Problem-statement requirement | Where it is implemented |
|---|---|
| Scan a wide spectrum covering relevant emitters | `ewsmart/environment.py` (ELINT + COMINT classes over a 24–128 band spectrum) |
| Sensors with ≥1 order lower instantaneous bandwidth, sweeping | `ewsmart/config.py` `bandwidth_model()` (ratio ≥ 10, default 24:1) |
| Open-loop baselines and their failure modes | `ewsmart/schedulers.py` (`SequentialSweep`, `RandomScan`, `PrioritySweep`) |
| Two-dimensional search (frequency × time) | `SmartScanScheduler.select(t)` |
| FoMs: Pd, Pfa, sensitivity, intercept rate, reward/cost, prediction accuracy, intercept-time error | `ewsmart/receiver.py`, `ewsmart/metrics.py`, `ewsmart/runner.py` |
| Receiver system model against a truth-instrumented environment | `ewsmart/receiver.py`, `RFEnvironment.occupancy` |
| Prediction of intercept time / ratio vs periodic and agile emitters | `ewsmart/periodic.py` (Rayleigh lock), `ewsmart/prediction.py`, `SmartScanScheduler._hop_pursuit` |
| ML-based scheduler minimising intercept time | `SmartScanScheduler` + `ewsmart/meta.py` (learned arbitration) |
| Trained on hits and misses | `runner.run_episode` → `scheduler.update(...)`; cross-episode consolidation in `end_episode()` |
| Optimal interception of a periodic scan | `ewsmart/periodic.py` (Rayleigh Z-test, phase lock) |

---

## 2. Architecture

```
ewsmart/
  config.py         scenario description, RF front-end bandwidth model
  environment.py    emitters, truth matrix, pulse descriptors, waveform classes
  deinterleave.py   pulse-level PDW synthesis + deinterleaving (DTOA/PRI)
  receiver.py       ES receiver: radiometer, Albersheim, CA-CFAR, matched filter,
                    interferometric AOA, optional front-end impairments
  aoa.py            phase-interferometer and monopulse AOA models (CRLB-coupled)
  frontend.py       synthesiser settling, LNA blocking, mixer spurs, ADC clipping
  periodic.py       Rayleigh circular-statistics period estimator + phase lock
  prediction.py     observation-only hop prediction + offline evaluation
  schedulers.py     SequentialSweep, RandomScan, PrioritySweep, UCBScheduler,
                    LinearQLearning, DQNScheduler, SmartScanScheduler, MetaScheduler
  meta.py           LinUCB behaviour arbiter (learned decision core)
  calibration.py    scenario-scale auto-calibration of behaviour constants
  realtime.py       Q8.8 fixed-point decision kernel (FPGA/DSP port artifact)
  runner.py         episode loop, reward, cost model, training
  metrics.py        all FoMs, Trace, per-class interception ratios
  dqn.py            deep Q-network reference implementation
  geo.py            AOA triangulation, CEP statistics
  multireceiver.py  cooperative multi-receiver allocation
  identification.py PDW fingerprinting, signal-class taxonomy, library matching
  dataset.py        dataset replay + calibration, dataset benchmarks
  sigtests.py       paired permutation tests, bootstrap confidence intervals
server/             FastAPI backend (mission control, live sim, PS audit, SDR ingest)
frontend/           React/TypeScript command-centre console (built into the exe)
website/            Public site: console, documentation, evidence gallery
tools/              dataset/site/doc exporters, C++ kernel export, SDR bridge, packaging
docs/               user manual, PS audits, changelog, reproducibility notes
tests/              306 automated tests
```

---

## 3. Feature reference

Each feature below follows the same structure: **what it does**, **how it
works**, **where**, **how it is verified**.

### 3.1 Spectrum model and emitter classes

- **What.** A multi-emitter RF scene over discrete bands and time slots with
  full ground truth.
- **How.** `RFEnvironment` builds a truth matrix `occupancy[n_bands, T]` plus a
  per-emitter band sequence. Seven emitter classes coexist: `stationary`,
  `agile` (frequency hopping), `periodic` (scanning radar), `spatial` (rotating
  main beam), `evasive`, `fhss` (frequency-hopping communications net) and
  `tdma` (burst communications station). Threat/clutter flags drive reward and
  coverage attribution.
- **Verified by.** `tests/test_target99_gaps.py`, `tests/test_ps_gaps.py`,
  `tests/test_fidelity_upgrades.py`.

### 3.2 Pulse structure and waveform classes

- **What.** Each emitter carries a physically plausible pulse descriptor set:
  PRI value, PRI model (fixed / staggered / jittered), pulse width, waveform
  class (`pulsed`, `lpi_fmcw`, `lpi_barker`) and a time-bandwidth product.
- **How.** `RFEnvironment._pulse_descriptors()` draws them per emitter;
  `EmitterSpec` validates them. A Low Probability of Intercept emitter has its
  in-channel SNR reduced by exactly `10 log10(BT)`, which is what makes it
  invisible to a plain radiometer and visible to a matched filter.
- **Verified by.** `test_lpi_emitters_are_negative_snr_in_the_scene`.

### 3.3 Pulse-level deinterleaving

- **What.** Separation of a raw interleaved pulse stream into individual
  emitters, with PRI estimation — the classical first task of an ESM chain.
- **How.** `emit_pulse_train` synthesises trains; `interleave` builds the raw
  PDW stream; `deinterleave` clusters on (RF, PW, AOA), builds an all-pairs
  difference-of-time-of-arrival histogram, sharpens the period by
  phase-histogram entropy minimisation (coarse-to-fine), and classifies the PRI
  model from the circular phase distribution. `deinterleave_accuracy` scores
  attribution purity, fragmentation, PRI error and model accuracy.
- **Verified by.** `test_deinterleave_recovers_all_pri_models` (4 emitters,
  purity 1.0, PRI error 0.4%, model accuracy 100%),
  `test_deinterleave_stagger_reports_mean_interval`,
  `test_deinterleave_never_reads_ground_truth` (no label leakage).

### 3.4 Receiver detection chain

- **What.** Per-dwell detection whose probability is *derived* from physics
  rather than declared.
- **How.** Thermal noise floor `kT + B + NF` over the dwell's time-bandwidth
  product; Albersheim's non-coherent-integration closed form gives the required
  SNR for the design Pd; a cell-averaging CFAR threshold factor
  `alpha = Pfa^(-1/N) - 1` sets the decision point. Longer dwells, narrower
  instantaneous bandwidth and looser Pfa all move the curve. A matched-filter /
  de-chirp bank adds the coherent gain for LPI waveforms. Optional front-end
  impairments (retune blanking, LNA blocking) modify the effective integration
  time and noise floor.
- **Verified by.** `tests/test_repair_bundle.py`, `tests/test_ps_gaps.py`
  (sensitivity FoM, CFAR), `tests/test_fidelity_upgrades.py` (LPI on/off,
  blanking, blocking).

### 3.5 Angle-of-arrival measurement

- **What.** Bearing measurement whose error is coupled to SNR and frequency.
- **How.** A dual-baseline phase interferometer: the coarse baseline resolves
  the field of view, the fine baseline supplies precision, and the fine
  baseline's ambiguity is resolved against the coarse estimate with
  angular-proximity tie breaking. The Cramér–Rao bound gives the error.
  Monopulse and legacy fixed models are selectable.
- **Verified by.** `test_aoa_error_follows_crlb_scaling`,
  `test_aoa_unbiased_across_all_bearings`.

### 3.6 Schedulers

- **What.** Seven policies under one interface, from open-loop baselines to the
  hybrid flagship.
- **How.**
  - `SequentialSweep`, `RandomScan`, `PrioritySweep` — open-loop references.
  - `UCBScheduler` — bandit baseline (exposes the exploit trap).
  - `LinearQLearning`, `DQNScheduler` — reinforcement-learning references.
  - `SmartScanScheduler` — the flagship: reconnaissance sweep → cued pursuit of
    validated periodic locks → predict-and-probe → burst characterisation →
    agile-hop pursuit → value-weighted rotation with a recency guarantee. It
    learns online (per-band value EMAs, online logistic occupancy model,
    per-stream hop transition model), consolidates across episodes, and gates
    its aggressive behaviours on *measured* success.
  - `MetaScheduler` — warm-start wrapper persisting learned state.
- **Verified by.** `tests/test_smartscan.py`, `tests/test_target99_gaps.py`,
  `tests/test_schedulers_edge.py`.

### 3.7 Agile-hop prediction and pursuit

- **What.** Prediction of an agile emitter's next band and next-on time, used
  live in band selection.
- **How.** `HopDwellPredictor` learns per-band dwell-length statistics and
  Laplace-smoothed transitions from observed detections only. The scheduler
  maintains an incrementally indexed candidate set and dwells on the predicted
  destination just before the predicted window — but only when a majority
  successor exists, the predicted hop is imminent, the rotation is not already
  covering that band, the measured pursuit success rate clears its gate, and
  the survey phase is over. A pursuit that fails to intercept its stream blocks
  that stream until fresh evidence arrives.
- **Verified by.** `test_hop_dwell_predictor_is_wired_into_live_scheduling`,
  `test_hop_pursuit_dwells_on_predicted_successor`,
  `test_pursuit_acceptance_gate_adapts_to_measured_outcomes`,
  `test_pursuit_accountability_blocks_a_stream_after_a_miss`,
  `test_pursuit_phase_gate_holds_tracking_until_survey_completes`.
- **Measured effect.** Structured (Markov) hopping, 10 seeds x 24 threats:
  14 missed threats without pursuit vs **10 with**; canonical 6-seed threat
  coverage 0.9028 → **0.9167**. On effectively-random hopping the pursuit is
  neutral (1 vs 2 missed of 192) and the adaptive gate switches it off.

### 3.8 Periodic interception (Rayleigh phase lock)

- **What.** Optimal interception of a periodically scanning emitter.
- **How.** A vectorised Rayleigh Z-test on arrival times estimates the period;
  validated locks (Z >= 3.9, tight phase spread) let the receiver arrive
  *before* each illumination window instead of searching for it. Locks are
  re-validated every cycle and self-destruct after repeated misses.
- **Verified by.** `tests/test_smartscan.py` (period estimation),
  `tests/test_ps_gaps.py` (lock behaviour).

### 3.9 Learned behaviour arbitration

- **What.** A learned component in the decision core: which behaviour to trust,
  in which situation.
- **How.** `BehaviourArbiter` is a LinUCB contextual bandit over the scheduler's
  five behaviours. Every decision is tagged with the behaviour that produced it
  and the dwell outcome folds `(context, behaviour, reward)` into the model. A
  safe action mask restricts it to behaviours whose preconditions hold, and its
  learned preferences are inspectable via `arbiter.score()`.
- **Verified by.** `test_arbiter_learns_the_paying_behaviour`,
  `test_arbiter_state_roundtrip_and_validation`,
  `test_scheduler_trains_the_arbiter_from_live_dwells`.

### 3.10 Scenario auto-calibration

- **What.** Behaviour constants derived from the scenario scale rather than
  hard-coded for one spectrum size.
- **How.** `calibrate(n_bands, T, n_emitters)` computes reconnaissance depth,
  burst horizon, revisit guarantee, pursuit budget/window and lock thresholds
  from documented formulas; the canonical scenario reproduces the shipped
  constants exactly.
- **Verified by.** `test_calibration_reproduces_canonical_constants`,
  `test_calibration_scales_with_spectrum_size`.

### 3.11 Real-time deployment artifact

- **What.** The per-slot decision in fixed-point integer arithmetic, plus
  generated C++ for an FPGA/DSP port.
- **How.** `PolicyKernel` quantises every statistic once (Q8.8, saturating),
  performs an O(n_bands) integer multiply-accumulate per decision with no
  allocation and no per-slot transcendental, and caches the log/sqrt terms.
  `tools/export_cpp_kernel.py` emits the same arithmetic as a header-only C++
  kernel with a complexity contract.
- **Verified by.** `test_kernel_matches_float_reference_argmax`,
  `test_kernel_metadata_is_a_real_contract`, `test_cpp_kernel_export`.

### 3.12 Figures of merit and evaluation

- **What.** All seven problem-statement FoMs plus mission-level scoring.
- **How.** `metrics.compute_metrics` produces Pd proxies (`intercept_ratio`,
  `threat_intercept_ratio`, per-class `ir_*`), false-alarm rate, sensitivity
  (MDS in dBm from the radiometer chain), intercept rate, reward and net reward
  (gross minus explicit switching/dwell costs), prediction accuracy,
  intercept-time error (periodic and agile), time-to-first-intercept (censored),
  per-rotation-cycle spatial coverage and attribution-conservation checks.
  `MISSION_KPPS` defines hard gates; the Mission Effectiveness Score composites
  the normalised FoMs *after* gating.
- **Verified by.** `tests/test_target99_gaps.py`, `tests/test_result_schema.py`,
  `tests/test_ps_gaps.py`.

### 3.13 Interfaces: API, console, CLI, data

- **What.** Everything a reviewer needs to run, watch and verify the system.
- **How.**
  - FastAPI backend: mission control, live paired simulation, PS-coverage audit,
    geolocation, identification, metrics, SDR/log-file ingest.
  - React/TypeScript console: Operations (live paired A/B), Analysis (benchmark
    tables, PS audit panel, evidence gallery), Data & Sources.
  - CLI: `python -m ewsmart.experiments --suite quick|full`,
    `python -m ewsmart.runner`, `python -m server.api`.
  - Dataset tooling: PDW replay and calibration from the referenced dataset
    ecosystem (JC Wise / Turing synthetic), offline-first.
- **Verified by.** `tests/test_api.py`, `tests/test_live.py`,
  `tests/test_mission.py`, `tests/test_software.py`.

### 3.14 Deployment, packaging and the documentation pipeline

- **What.** Desktop application, installer, container, and single-source docs.
- **How.** PyInstaller build (`tools/build_exe.ps1`, `astra.spec`) bundles the
  backend and the built frontend into `dist/ASTRA/ASTRA.exe`; an Inno Setup
  installer (`installer/astra_installer.iss`) produces the distributable; a
  `Dockerfile` provides server deployment. The desktop Help menu opens
  `/manual`, which serves `docs/ASTRA_Software_Documentation.md`.
  `tools/export_docs.py` converts that manual into the website's documentation
  bundle, the downloadable markdown and the section index, so the desktop app
  and the website can never disagree.
- **Verified by.** `tests/test_software.py`; the website production build
  (`npm run build`) compiles the generated documentation bundle.

---

## 4. How to run everything

```bash
pip install -r requirements.txt
python -m ewsmart.experiments --suite quick     # benchmark + figures + artifacts
python -m pytest tests -q                       # 306 tests
python -m server.api                            # backend + /manual + /api-docs
cd frontend && npm install && npm run build     # console bundle
python desktop.py                               # desktop app (native window)
python -m tools.export_docs                     # regenerate website docs
python -m tools.export_cpp_kernel               # emit the FPGA/DSP kernel artifact
```

---

## 5. Evidence and reproducibility

- **306 automated tests** covering the physics chain, schedulers, metrics,
  interfaces, packaging and every fidelity module.
- **Machine-checkable PS audit**: `GET /api/ps-coverage` executes 13 checks
  against the running system. The ML and training checks assert *measured*
  learning (weight/EMA deltas, memory consolidation), not the existence of a
  method.
- **Benchmark artifacts**: `results/benchmark.json` / `.md` (canonical protocol
  with provenance), `results/performance.json` (latency percentiles with
  platform provenance), `results/suite_results.json`,
  `results/ps_coverage_live.json`.
- **Strict determinism**: seeded scenarios, JSON scenario files, NaN-safe JSON
  output, pickle-free artifacts.
- **Statistical hygiene**: paired permutation tests and bootstrap confidence
  intervals (`ewsmart/sigtests.py`) for every headline comparison.

---

## 6. Honest limitations

Stated plainly, because credibility is part of the deliverable:

- **No RF sample-level simulation.** The receiver operates on measured pulse
  descriptor words and dwell statistics, not digitised I/Q; modulation is
  modelled through waveform class and processing gain rather than a bit-level
  waveform.
- **Deinterleaving is classical, not deep.** Descriptor clustering plus
  DTOA/PRI estimation — a real implementation of the textbook pipeline, not a
  learned deinterleaver.
- **Propagation is geometric.** Bearing and range set the geometry, but path
  loss, multipath fading and terrain diffraction are not modelled.
- **Deep RL remains a documented negative result.** On this sparse-reward,
  non-stationary task the DQN reference underperforms the hybrid; the flagship
  scheduler is a designed hybrid with online learning, and the learned arbiter
  is the component that learns *which* behaviour pays.
- **The arbiter currently learns in shadow mode.** It trains from every dwell
  outcome and its preferences are inspectable; letting it drive the policy
  directly is the next step, gated on the safe-action-mask design.
- **Latency is Python-bound.** The research scheduler averages roughly
  0.5–0.8 ms per decision; the fixed-point kernel and generated C++ header are
  the porting path to hardware budgets.
- **Identification library profiles are illustrative public-domain classes**,
  not operational ELINT data.

---

## 7. Glossary

| Term | Meaning |
|---|---|
| ES / ESM | Electronic Support (Measures) — passive search, intercept and analysis of emissions |
| PDW | Pulse Descriptor Word: TOA, frequency, pulse width, amplitude, AOA |
| DTOA | Difference of time of arrival; the basis of PRI estimation |
| PRI | Pulse repetition interval; may be fixed, staggered or jittered |
| LPI | Low probability of intercept waveform (chirp / phase-coded, large time-bandwidth) |
| Dwell | One listening interval on one band |
| Phase lock (ASTRA) | Validated estimate of a periodic emitter's period and window timing |
| TTFF | Time to first fix — slots until a threat is first intercepted |
| KPP | Key Performance Parameter — hard pass/fail operational requirement |
| MES | Mission Effectiveness Score — composite of normalised FoMs after KPP gating |
| CEP | Circular error probable — median geolocation error radius |
| CRLB | Cramér–Rao lower bound — the best achievable estimator variance |
| LinUCB | Linear upper-confidence-bound contextual bandit |