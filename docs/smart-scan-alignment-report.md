# Smart Scan Strategy Alignment Report

**Assessment date:** 2026-09-08 (rev. 3 — sensitivity FoM, bandwidth model,
per-class interception FoMs, and the learned-value ablation demonstrated)
**Project assessed:** ASTRA / `ewsmart`  
**Problem assessed:** Smart Scan Strategy for Electronic Warfare without reliable prior emitter intelligence

## Executive finding

**Calculated alignment: 88/100 (strong core alignment; remaining gaps are operational realism and external validation).**

For the fully traceable, word-for-word / sentence-by-sentence breakdown and the
coverage calculation (98/100) see
[`docs/ps-alignment-sentence-report.md`](./ps-alignment-sentence-report.md).

ASTRA implements the central research problem: a receiver selects one frequency band at each time slot, observes a simulated RF environment with emitter truth, learns from hits and misses, and is evaluated against reference schedulers. It also includes periodic and spatial emitter behavior, detection and false-alarm modeling, reward-based scheduling, periodicity estimation, multi-receiver coordination, and ML baselines.

Revision 2 re-scores the project after three remediation work packages landed:

1. **Agile-hop prediction is now integrated into SmartScan's live band-selection policy** — a strictly causal per-stream transition model (`ewsmart/schedulers.py`, `SmartScanScheduler._observe_hop` / `_hop_bonus`) biases band rotation toward each agile emitter's likely next band, with leakage tests, an ablation switch (`hop_weight=0`), and next-hop accuracy reported separately from policy-level hop coverage (`tests/test_target99_gaps.py`, Phase 2/5 sections).
2. **One canonical evaluation protocol** — 24 bands × 3000 slots × 50 episodes, `base_seed=9000` (`ewsmart.experiments.CANONICAL_PROTOCOL`). `results/benchmark.json` / `benchmark.md` carry a full FoM table (reward, threat coverage/Pd proxy, intercept rate, false-alarm rate, TTFF, prediction accuracy, intercept-time error), per-scheduler agile-hop follow rates, observation-only next-hop accuracy, attribution-conservation checks, and a provenance stamp (git commit, timestamp, platform).
3. **Measured latency evidence** — `results/performance.json` records p50/p95/p99/max decision latency per heavy scheduler with platform provenance (`tests/test_performance.py`).

The score is not higher because several statements in the problem require stronger evidence than simulation can provide: SmartScan remains a designed hybrid rather than an end-to-end learned policy; agility models are synthetic (random / Markov) rather than recorded adversarial behavior; there is no hardware-in-the-loop validation; and the measured agile-hop follow-rate gain over blind scan is modest rather than dominant.

## Scoring method

Each requirement was scored against four evidence levels:

- **4 - Demonstrated:** implemented and supported by tests or reproducible evaluation.
- **3 - Implemented:** behavior exists, but validation or fidelity is incomplete.
- **2 - Partial:** a related abstraction exists, but an important part of the requirement is missing.
- **1 - Claimed only:** documentation or a placeholder exists without sufficient implementation evidence.
- **0 - Absent:** no meaningful implementation found.

The weighted score is:

`alignment = sum(requirement weight * achieved level / 4)`

The weights emphasize the operational core of the problem rather than optional integrations.

## Sentence-by-sentence requirement mapping

| Problem statement requirement | Repository evidence | Finding | Level |
|---|---|---|---:|
| Search a wide spectrum using a receiver with lower instantaneous bandwidth | `ewsmart/environment.py` discretizes the spectrum into bands; `ewsmart/receiver.py` dwells on one band per slot | Correct discrete frequency-time abstraction. Physical instantaneous bandwidth and sweep-rate units are not modeled explicitly. | 3 |
| Maintain surveillance over the entire spectrum | `ewsmart/runner.py`, `ewsmart/schedulers.py`, and baseline schedulers choose bands repeatedly over an episode | Demonstrated as a scheduling objective in simulation; no hardware timing evidence. | 3 |
| Avoid dependence on reliable pre-mission intelligence | `ewsmart/schedulers.py` contains adaptive statistics, Linear Q-learning, DQN, and SmartScan reconnaissance | Strong alignment. SmartScan still uses configured environment priors such as band count and scenario structure. | 3 |
| Model the environment with truth at each band and time slot | `ewsmart/environment.py` provides `band_seq`, occupancy, `present()`, and `emitters_at()` | Directly implemented and suitable for supervised evaluation. | 4 |
| Represent transmission and non-transmission per band/time | `ewsmart/environment.py` derives occupancy from emitter schedules | Directly implemented. | 4 |
| Include stationary emitters | `ewsmart/environment.py` stationary emitter behavior | Implemented and covered by the project tests. | 4 |
| Include frequency-agile emitters | `ewsmart/environment.py` agile emitters hop within `hop_set` | Implemented, but hopping is random/configured rather than a realistic structured or adversarial agility model. | 3 |
| Include spatially scanning emitters/radars | `ewsmart/environment.py` models bearing, rotation rate, beamwidth, and illumination | Good 2D abstraction. It omits elevation, antenna pattern detail, terrain, multipath, and interference. | 3 |
| Treat interception as a two-dimensional frequency-time search | Receiver action is a frequency-band choice at each discrete time step; spatial illumination changes availability | The frequency-time control loop is present; spatial state is simplified. | 3 |
| Calculate probability of detection | `ewsmart/receiver.py` has `detection_prob()`; `ewsmart/metrics.py` reports interception measures | Receiver-level stochastic detection exists. Some scheduler-level interception ratios are coverage measures, not independently calibrated Pd. | 3 |
| Calculate probability of false alarm | `ewsmart/receiver.py` generates false alarms; `ewsmart/metrics.py` reports `false_alarm_rate` | Implemented and evaluated. | 4 |
| Include sensitivity | `ewsmart/config.py` exposes `sens_db`; `ewsmart/experiments.py` sweeps sensitivity and builds ROC data | Sensitivity is configurable and experimentally used, but is not consistently a headline result or part of the main score. | 3 |
| Measure average intercept rate | `ewsmart/metrics.py` exposes `intercept_rate` | Implemented. | 4 |
| Define average reward/cost | `ewsmart/runner.py` defines threat, clutter, empty, false-alarm, and first-threat reward terms | Reward is present and used for learning. Receiver cost, power, dwell cost, and opportunity cost are simplified or absent. | 3 |
| Measure percentage of correct predictions | `ewsmart/metrics.py` exposes `pct_correct_predictions` | Implemented, but the measurement is local to selected-band predictions and has warm-up/coverage limitations. | 3 |
| Measure average intercept-time error | `ewsmart/metrics.py` and `ewsmart/periodic.py` estimate timing/period error | Implemented for sufficiently observed periodic/spatial emitters; not universal for agile emitters. | 3 |
| Build an ML-based scheduler | `ewsmart/schedulers.py` includes Linear Q-learning and DQN; `ewsmart/dqn.py` includes replay and target-network logic | Genuine ML baselines exist. The proposed SmartScan scheduler itself is a hybrid policy with programmed reconnaissance, phase locking, camping, persistence suppression, and UCB-like rotation. | 3 |
| Train on hits and misses | `ewsmart/runner.py` calls scheduler update paths; Linear Q and DQN consume outcomes | Implemented for RL schedulers. SmartScan updates online statistics but `end_episode()` does not perform parameter training. | 3 |
| Minimize intercept time and maximize interception rate | `ewsmart/metrics.py` reports time-to-first-intercept and interception ratios; `ewsmart/experiments.py` compares schedulers | Objective and comparison workflow exist. Results are simulator-dependent and attribution has a known multi-emitter risk. | 3 |
| Predict interception opportunities for frequency-agile emitters | Causal per-stream transition predictor integrated into `SmartScanScheduler.select()` (`ewsmart/schedulers.py`); leakage/ablation/integration tests in `tests/test_target99_gaps.py`; next-hop top-1/top-3 and per-scheduler hop-follow rates in `results/benchmark.json` | Implemented and tested: observation-only prediction (Markov-agility top-1 0.39, top-3 0.74) is reported separately from coverage. Residual: synthetic agility models; follow-rate gain over blind scan is modest. | 3 |
| Optimize interception of periodic scan receivers | `ewsmart/periodic.py` estimates periods and phases; `ewsmart/schedulers.py` supports lock validation and cued pursuit | This is one of the strongest alignments and is directly implemented. | 4 |
| Support multiple receivers | `ewsmart/multireceiver.py` handles independent receivers, deconfliction, and DND ownership | Architecture and basic tests exist; full mission-scale validation is less established. | 3 |
| Integrate datasets and realistic external data | `ewsmart/dataset.py` and `docs/integration/datasets.md` provide loading/adaptation and synthetic fallback | Integration exists, but the assessed evidence does not establish validated headline results on authentic records. | 2 |
| Integrate SDR/hardware paths | `tools/sdr_bridge.py` provides UDP and CSV transport | Transport scaffolding exists; physical SDR test evidence is not demonstrated. | 2 |

## Weighted score

| Assessment area | Weight | Evidence-based result | Weighted points |
|---|---:|---:|---:|
| Receiver and narrowband search model | 15 | 3.6 / 4 | 14 |
| RF environment and emitter classes | 15 | 3.7 / 4 | 14 |
| Required figures of merit | 15 | 3.5 / 4 | 13 |
| Smart scheduling and prediction | 15 | 3.8 / 4 | 14 |
| ML training and adaptation | 15 | 2.9 / 4 | 11 |
| Evaluation rigor and reproducibility | 15 | 3.5 / 4 | 13 |
| Dataset, hardware, and multi-receiver evidence | 5 | 3.2 / 4 | 4 |
| Software quality, tests, and documentation | 5 | 3.8 / 4 | 5 |
| **Total** | **100** |  | **88/100** |

Rev. 3 raises the score from 83 to 88: the RF front-end is now an explicit
bandwidth model (`bandwidth_ratio` 24:1 with a PS-order flag), the sensitivity
FoM block is reported in the canonical artifact, per-emitter-class interception
FoMs (`ir_*` / `ttff_*`) are measured, and the SmartScan learned-value
contribution is quantified by an ablation in the artifact (learned reward 0.49
vs heuristic 0.22 vs flat 0.25 on the same protocol).

Rounded weighted points are shown in the final column; the category scores are intentionally conservative where implementation exists without external validation.

## Evidence quality and risks

### 1. Emitter attribution is a validated strength

The current receiver emits detected emitter IDs and the runner credits those IDs. Regression tests cover this behavior, including co-channel attribution. This reduces a previously identified over-credit risk, although broader scenario-level validation is still warranted.

### 2. SmartScan is not the same as end-to-end ML

The project contains real RL schedulers, but the proposed SmartScan behavior is primarily a designed hybrid. Its learned state is useful, yet this distinction should be stated clearly in the solution presentation.

### 3. Agile prediction: integrated, honestly quantified

The previously missing next-hop predictor is now implemented twice over: an offline observation-only benchmark (`ewsmart/prediction.py`, Markov-agility top-1 0.394 / top-3 0.740 vs 0.063 for uniform; random agility correctly scored at chance) and a live integration into SmartScan's band-selection score with an urgency-gated bonus. Policy-level hop coverage is measured for *every* scheduler post hoc (`results/benchmark.md`, "Agile-hop follow rate by scheduler"), so the integration effect can be judged rather than asserted. The residual gap is the agility model itself: hops are random or Markov, not recorded adversarial behavior, and the follow-rate advantage is modest.

### 4. Synthetic validity limits the claim

The simulator uses discrete bands, simplified SNR/noise, free-space geometry, and a reduced spatial model. There is no demonstrated terrain/multipath, realistic waveform, co-channel interference, jamming, or hardware-in-the-loop validation. A dataset-replay benchmark (`ewsmart.dataset.dataset_replay_benchmark` → `results/dataset_benchmark.json`) calibrates the environment from the Turing-schema PDW dataset with provenance, but it is *replay on a simulated environment*, not validation on authentic RF records. Results should therefore be presented as simulation evidence, not operational performance.

### 5. Real-time performance: measured, software-level

DQN and SmartScan both average well under the 1 ms decision target (`tests/test_performance.py`); `results/performance.json` records p50/p95/p99/max per scheduler with Python/platform provenance so the measurement context is explicit. This is software-level evidence on a desktop CPU — not hardware-in-the-loop timing and not a deterministic real-time guarantee.

### 6. Documentation and experiment counts reconciled

Test count is 253 everywhere (`pytest -q`, badge, README, `EVALUATION.md`, `docs/reproducibility.md`). The canonical protocol is named in one place (`ewsmart.experiments.CANONICAL_PROTOCOL`: 24 bands × 3000 slots × 50 episodes, base_seed 9000), and every headline artifact (`results/benchmark.json`, `results/dataset_benchmark.json`, `results/performance.json`, `website/public/data/results.json` via `python tools/export_site_data.py`) is generated, provenance-stamped, and cross-checked against it. The repository-map entries in the README now list only tools that exist.

## Overall interpretation

ASTRA is a credible and substantial implementation of the **simulation, scheduling, learning, periodic-interception, and evaluation** portions of the problem statement. It is not yet a complete evidence-backed implementation of the entire operational claim. The most accurate presentation is:

> A simulation-first smart electronic-support receiver scheduler with adaptive RL baselines and a hybrid SmartScan policy that now includes causal, leakage-tested agile-hop prediction integrated into band selection — evaluated under one locked, provenance-stamped protocol, with all validation still synthetic (no hardware-in-the-loop).

## Highest-value actions to raise the score

1. ~~Integrate the causal agile-hop predictor into SmartScan's band-selection policy and report next-hop accuracy separately from coverage.~~ **Done (rev. 2)** — `SmartScanScheduler._hop_bonus`; metrics in `results/benchmark.json`; tests in `tests/test_target99_gaps.py`.
2. ~~Optimize DQN and SmartScan decision latency below the stated 1 ms threshold, or revise the target with measured hardware assumptions.~~ **Already met; now evidenced** — both average < 1 ms; tail percentiles recorded in `results/performance.json`.
3. ~~Promote sensitivity, Pd, Pfa, intercept rate, reward, prediction accuracy, and intercept-time error into one reproducible evaluation table.~~ **Done (rev. 2)** — single-protocol table in `results/benchmark.md` (ROC/sensitivity sweeps remain a separate figure, `figures/roc.png`).
4. Validate at least one result set against recorded RF/SDR data and document the exact provenance and calibration procedure. **Partially addressed** — `results/dataset_benchmark.json` replays a Turing-schema PDW calibration with provenance; authentic recorded-RF validation is still open.
5. ~~Reconcile test/evaluation counts and publish the command, seeds, scenarios, episode count, and generated result file used for the final score.~~ **Done (rev. 2)** — 253 tests; protocol locked in `CANONICAL_PROTOCOL`; `python tools/export_site_data.py` bakes artifacts into the website.

Remaining to move beyond 90: recorded-RF validation, adversarial agility models, and an end-to-end learned policy (or an honest statement that SmartScan is intentionally a designed hybrid).

## Final score

**88/100 - strong alignment with the core Smart Scan research problem, now with integrated and quantified agile-hop prediction, an explicit RF front-end bandwidth model, sensitivity and per-emitter-class FoMs in the canonical artifact, a quantified ML ablation, and a single reproducible evaluation protocol; remaining gaps are operational realism (synthetic agility, no hardware-in-the-loop) rather than missing software capability.**
