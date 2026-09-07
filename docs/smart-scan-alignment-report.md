# Smart Scan Strategy Alignment Report

**Assessment date:** 2026-09-06  
**Project assessed:** ASTRA / `ewsmart`  
**Problem assessed:** Smart Scan Strategy for Electronic Warfare without reliable prior emitter intelligence

## Executive finding

**Calculated alignment: 74/100 (strong core alignment, with material evidence and modeling gaps).**

ASTRA implements the central research problem: a receiver selects one frequency band at each time slot, observes a simulated RF environment with emitter truth, learns from hits and misses, and is evaluated against reference schedulers. It also includes periodic and spatial emitter behavior, detection and false-alarm modeling, reward-based scheduling, periodicity estimation, multi-receiver scaffolding, and ML baselines.

The score is not higher because several statements in the problem require stronger evidence than the current implementation provides. In particular, frequency-agile prediction is random-hop revisit behavior rather than explicit next-hop prediction; the proposed SmartScan policy is a hybrid of programmed heuristics and learned statistics rather than an end-to-end learned policy; the evaluation is primarily synthetic; emitter-level credit can be overstated when multiple emitters share a band; and the current performance limits are not fully met.

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
| Predict interception opportunities for frequency-agile emitters | Agile behavior exists in `environment.py`; scheduler revisits valuable bands | No explicit learned or analytical next-hop predictor was found for random/structured agile behavior. | 2 |
| Optimize interception of periodic scan receivers | `ewsmart/periodic.py` estimates periods and phases; `ewsmart/schedulers.py` supports lock validation and cued pursuit | This is one of the strongest alignments and is directly implemented. | 4 |
| Support multiple receivers | `ewsmart/multireceiver.py` handles independent receivers, deconfliction, and DND ownership | Architecture and basic tests exist; full mission-scale validation is less established. | 3 |
| Integrate datasets and realistic external data | `ewsmart/dataset.py` and `docs/integration/datasets.md` provide loading/adaptation and synthetic fallback | Integration exists, but the assessed evidence does not establish validated headline results on authentic records. | 2 |
| Integrate SDR/hardware paths | `tools/sdr_bridge.py` provides UDP and CSV transport | Transport scaffolding exists; physical SDR test evidence is not demonstrated. | 2 |

## Weighted score

| Assessment area | Weight | Evidence-based result | Weighted points |
|---|---:|---:|---:|
| Receiver and narrowband search model | 15 | 3.2 / 4 | 12 |
| RF environment and emitter classes | 15 | 3.7 / 4 | 14 |
| Required figures of merit | 15 | 2.7 / 4 | 10 |
| Smart scheduling and prediction | 15 | 3.2 / 4 | 12 |
| ML training and adaptation | 15 | 2.4 / 4 | 9 |
| Evaluation rigor and reproducibility | 15 | 2.7 / 4 | 10 |
| Dataset, hardware, and multi-receiver evidence | 5 | 2.4 / 4 | 3 |
| Software quality, tests, and documentation | 5 | 3.2 / 4 | 4 |
| **Total** | **100** |  | **74/100** |

Rounded weighted points are shown in the final column; the category scores are intentionally conservative where implementation exists without external validation.

## Evidence quality and risks

### 1. Emitter interception can be over-credited

The runner and receiver paths can credit every emitter present on a selected band when one true detection occurs. With co-channel emitters, this can inflate interception ratio, threat interception ratio, first-intercept time, and reward attribution. Detection tuples/PDW data exist in the project and should be used for emitter-specific credit.

### 2. SmartScan is not the same as end-to-end ML

The project contains real RL schedulers, but the proposed SmartScan behavior is primarily a designed hybrid. Its learned state is useful, yet this distinction should be stated clearly in the solution presentation.

### 3. Agile prediction is the largest direct requirement gap

Random hopping is modeled and can be searched adaptively, but there is no demonstrated next-hop model, transition learner, or structured agility predictor. The project satisfies agile-emitter simulation more strongly than agile-emitter prediction.

### 4. Synthetic validity limits the claim

The simulator uses discrete bands, simplified SNR/noise, free-space geometry, and a reduced spatial model. There is no demonstrated terrain/multipath, realistic waveform, co-channel interference, jamming, or hardware-in-the-loop validation. Results should therefore be presented as simulation evidence, not operational performance.

### 5. Real-time performance remains a qualification item

The repository’s performance test defines a 1 ms decision target. The focused current check, `pytest -q tests/test_smartscan.py tests/test_performance.py`, passed all 21 tests. This supports the software-level performance claim, but it is not hardware-in-the-loop evidence and does not by itself establish deterministic real-time behavior under deployment conditions.

### 6. Documentation and experiment counts need reconciliation

The repository contains inconsistent test and evaluation counts across `README.md`, `EVALUATION.md`, and generated result material. A final submission should name one exact command, dataset/scenario configuration, seed policy, episode count, and result artifact.

## Overall interpretation

ASTRA is a credible and substantial implementation of the **simulation, scheduling, learning, periodic-interception, and evaluation** portions of the problem statement. It is not yet a complete evidence-backed implementation of the entire operational claim. The most accurate presentation is:

> A simulation-first smart electronic-support receiver scheduler with adaptive RL baselines and a hybrid SmartScan policy, including periodic and spatial emitter modeling, but with incomplete agile prediction and limited real-world validation.

## Highest-value actions to raise the score

1. Correct emitter-specific detection credit for co-channel emitters, regenerate all metrics, and rerun the complete suite.
2. Add an explicit agile-hop predictor or transition model, then report next-hop accuracy and intercept-time error separately from random-hop coverage.
3. Optimize DQN and SmartScan decision latency below the stated 1 ms threshold, or revise the target with measured hardware assumptions.
4. Promote sensitivity, Pd, Pfa, intercept rate, reward, prediction accuracy, and intercept-time error into one reproducible evaluation table.
5. Validate at least one result set against recorded RF/SDR data and document the exact provenance and calibration procedure.
6. Reconcile test/evaluation counts and publish the command, seeds, scenarios, episode count, and generated result file used for the final score.

## Final score

**74/100 - strong alignment with the core Smart Scan research problem; partial alignment with operational realism, agile prediction, and validation requirements.**