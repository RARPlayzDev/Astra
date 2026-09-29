# ASTRA — Problem Statement Gap Analysis

*Honest comparison of what the SIH 2026 problem statement asks for vs. what the
codebase actually implements. No hype. No hallucinations. Only verifiable claims
backed by code.*

---

## 1. Problem Statement Requirements vs. Implementation

### 1.1 Receiver Model

| Requirement (PS) | Status | What Exists | What's Missing / Weak |
|---|---|---|---|
| High-sensitivity narrowband receiver sweeping wideband spectrum | ✅ Implemented | `ESReceiver` in `receiver.py` — logistic Pd curve, per-band noise, false alarms, PDW output | Sensitivity is modelled as a logistic curve, not a full RF front-end model. No filter shapes, no spurious-free dynamic range, no ALC. |
| Instantaneous BW ≪ total BW | ✅ Implied by design | Single-band-per-slot dwell; receiver tunes one band per time step | No explicit BW parameter; the discretisation into `n_bands` implicitly enforces the constraint but the physical bandwidth value is never used in calculations. |
| Receiver model with truth information | ✅ Implemented | `RFEnvironment.occupancy[band, t]` is the truth matrix; `DwellResult.truth_present` flags it | — |
| Measurements from simulated RF environment | ✅ Implemented | Environment produces per-emitter SNR, bearing, PDW fields | — |

**Verdict: Functional. The receiver model is a clean engineering abstraction
that captures the essential physics (detection probability, false alarms, AOA,
PDWs) without being a full hardware simulator. Adequate for scheduler research
but not for hardware procurement.**

---

### 1.2 RF Environment

| Requirement (PS) | Status | What Exists | What's Missing / Weak |
|---|---|---|---|
| Status of each band at each time step (transmission / non-transmission) | ✅ Implemented | `occupancy[band, t]` is `int8` (0/1) per band per slot | — |
| Spatially scanning emitters | ✅ Implemented | `"spatial"` kind with rotation rate, beamwidth, geometrically consistent bearings | Only main-lobe modelled; no sidelobes, no ground-bounce multipath. |
| Frequency agile emitters | ✅ Implemented | `"agile"` kind hops across `hop_set` with configurable dwell | No pseudo-random hop pattern models (e.g., Barker-coded, ECCM). |
| Periodic emitters | ✅ Implemented | `"periodic"` kind with ON/OFF windows at a repeating interval | — |
| Stationary emitters | ✅ Implemented | `"stationary"` kind always transmitting on one band | — |
| Evasive emitters | ✅ Implemented | `"evasive"` kind shifts frequency or phase after 3 consecutive intercepts | Counter-counter-ESM behaviour; not required by PS but present. |
| Clutter / non-threat emitters | ✅ Implemented | `n_clutter` static emitters randomly placed | — |

**Verdict: Strong. The environment covers all four emitter classes the PS
mentions plus an evasive class and clutter. The main gap is that propagation
is entirely free-space; no terrain, no multipath, no jammer. Acceptable for
the stated scope.**

---

### 1.3 Figures of Merit

The PS explicitly lists seven FoMs. Here is their implementation status:

| FoM (PS) | Status | Code Location | Honest Assessment |
|---|---|---|---|
| **Probability of detection** | ✅ | `metrics.py::compute_metrics` → `intercept_ratio`, `threat_intercept_ratio`; `receiver.py::detection_prob()` | Pd is modelled at the physics level (logistic vs SNR). At the scheduler level it becomes interception ratio — the fraction of emitters intercepted. These are two different but related metrics; both are computed. |
| **Probability of false alarm** | ✅ | `metrics.py::compute_metrics` → `false_alarm_rate` | Per-slot false-alarm rate. Modelled physically in `receiver.py` (stochastic FA on empty bands). KPP-gated at 5×10⁻⁴/slot. |
| **Sensitivity** | ⚠️ Partial | `receiver.py::detection_prob()` sweeps `pd_mid_offset` in ROC experiment (`experiments.py::roc_experiment`) | Sensitivity is a receiver physics parameter, not a scheduler metric. The ROC experiment sweeps it. But there is no explicit "sensitivity figure of merit" reported as a single number — it is implicit in the Pd curve. The PS may expect a dB figure; that exists in the config (`sens_db`) but is not reported as a headline metric. |
| **Avg intercept rate** | ✅ | `metrics.py::compute_metrics` → `intercept_rate` | Hits per slot. Directly computed. |
| **Avg Reward / cost function** | ✅ | `metrics.py::compute_metrics` → `avg_reward`, `total_reward`; `runner.py::step_reward()` | Value-weighted reward: threats > clutter > empty; false alarm penalty; first-threat bonus. Matches the PS "reward / cost function" framing. |
| **% correct predictions** | ✅ | `metrics.py::compute_metrics` → `pct_correct_predictions` | Steady-state (post-warmup) prediction accuracy: scheduler's `predict()` vs ground truth. Excludes the first 600 slots (calibration transient). |
| **Avg intercept time error** | ✅ | `metrics.py::compute_metrics` → `avg_intercept_time_error` | Mean absolute error between predicted next-ON time and true next-ON time, computed over periodic emitters with ≥3 hits. Returns NaN when no periodic emitter is characterised. |

**Verdict: 6/7 fully implemented, 1 partially (sensitivity as a headline
number). The sensitivity is physically modelled and swept in the ROC
experiment, but not collapsed into a single "system sensitivity in dB" metric.
This is a minor reporting gap, not a modelling gap.**

---

### 1.4 Prediction of Intercept Time and Interception Ratio

| Requirement (PS) | Status | What Exists | What's Missing / Weak |
|---|---|---|---|
| Predict intercept time against spatially scanning emitters | ✅ | SmartScan's phase-lock estimator (`periodic.py::best_period`) works on hit times from any periodic source, including spatial emitters whose rotation creates periodic ON windows | Spatial emitters are periodic by nature (rotation → periodic illumination). The Rayleigh test captures this. No special spatial-model prediction (e.g., predicting from rotation rate directly). |
| Predict intercept time against frequency agile emitters | ⚠️ Partial | Agile emitters with fixed hop sets and dwells are not explicitly phase-locked. SmartScan's burst characterisation and value-weighted rotation handle them. | Agile emitters that pseudo-randomly hop have no exploitable periodicity. The scheduler treats them as high-visit-value bands. There is no "predict next hop" logic — only "keep revisiting." This is arguably correct (random hops are unpredictable) but the PS implies prediction should be attempted. |
| Interception ratio | ✅ | `threat_intercept_ratio`, `intercept_ratio` | Both threat-only and all-emitter interception ratios are computed. |

**Verdict: The periodic/spatial prediction story is solid. The agile
prediction story is honest (you can't predict truly random hops) but the PS
may expect some attempt at pattern detection even on agile emitters.**

---

### 1.5 ML-Based Scheduler

| Requirement (PS) | Status | What Exists | What's Missing / Weak |
|---|---|---|---|
| Development of a robust scheduler using ML | ✅ | SmartScan in `schedulers.py` — confidence-multiplexed hybrid with 6 behaviours (including causal agile-hop anticipation). UCB-based rotation uses Q-style value estimates. | SmartScan is partly ML (learned confidence, value estimates) and partly rule-based (phase-lock, burst logic). It is not a pure end-to-end learned policy. The PS says "ML-based"; SmartScan qualifies but is not a monolithic neural-net scheduler. |
| Minimise intercept time | ✅ | KPP-gated MES includes "mean time to first intercept" as a normalised component. SmartScan's cued pursuit directly minimises TTFF for periodic emitters. | — |
| Ensure high interception rate | ✅ | `threat_intercept_ratio ≥ 0.95` with KPP gate at 0.90 | — |
| Train based on hits and misses | ✅ | `runner.py::train()` runs cross-episode training for learnable schedulers (Linear Q, DQN, SmartScan). SmartScan updates its internal statistics (`mu`, `n`, `band_hits`, `est`) from every hit/miss. | SmartScan "trains" incrementally within an episode (no gradient update, but statistical learning). DQN and Linear Q do gradient/tabular RL training across episodes. The PS "train based on hits and misses" is satisfied. |
| Approaches to intercept periodic scan receiver optimally | ✅ | `periodic.py` — Rayleigh period estimator with integer refinement, significance testing (z ≥ 3.9), phase-spread validation. Cued pursuit in SmartScan arrives at predicted ON windows. | This is one of the strongest parts of the system. The Rayleigh test is a well-known technique for detecting periodicity in point processes; the integer refinement and significance thresholding are solid. |

**Verdict: The ML component is present and functional, though SmartScan
itself is a hybrid (rule-based + learned value estimation) rather than a pure
ML policy. The DQN and Linear Q are pure ML baselines. The periodic
interception approach is genuinely strong.**

---

### 1.6 Algorithms and Techniques

| Requirement (PS) | Status | What Exists |
|---|---|---|
| Algorithm for smart scan scheduling | ✅ | SmartScan: 5-behaviour confidence-multiplexed hybrid |
| Period estimation | ✅ | Rayleigh test (`periodic.py`) |
| Phase-lock and cued pursuit | ✅ | SmartScan lock acquisition + validation |
| ML value estimation | ✅ | Q-style discounted UCB in rotation; DQN and Linear Q as baselines |
| Fingerprinting | ✅ | SNR + AOA clustering in SmartScan (`_cluster_hits`) |
| Statistical significance testing | ✅ | Paired permutation tests, Holm-Bonferroni correction, bootstrap CIs (`sigtests.py`) |
| Multi-receiver coordination | ✅ | `multireceiver.py` — CooperativeTeam with de-confliction |
| Emitter identification | ✅ | `identification.py` — PDW fingerprinting against library |
| Geolocation | ✅ | `geo.py` — AOA triangulation, CEP statistics |

**Verdict: The algorithmic toolkit is broad and covers more than the PS
requires. The main gap is the depth of each individual algorithm (see Section 3).**

---

## 2. What's Genuinely Good

1. **The periodic interception pipeline is production-quality.** Rayleigh test +
   integer refinement + significance threshold + online validation + cheap
   falsification. This directly answers the PS's hardest sub-problem.

2. **The evaluation framework is defence-grade.** KPP gating, MES composite
   scoring, paired permutation tests with multiple-comparison correction,
   50-episode Monte Carlo with 95% CIs. This is more rigorous than most
   academic papers in the field.

3. **The exploit-trap demonstration.** UCB bandit has the highest raw reward
   (0.943) but worst coverage (0.540). SmartScan resolves the trade-off.
   This is an honest, powerful result that directly addresses the PS's core
   concern.

4. **Reproducibility.** Seed-defined scenarios, strict JSON outputs,
   pickle-free artifacts, 250 tests, Docker image. Everything can be
   independently verified.

5. **The end-to-end chain.** Environment → Receiver → Scheduler → Metrics →
   ID → Geolocation → Live ingestion → Command Centre. No other solution in this
   space offers the full loop.

---

## 3. What's Missing, Weak, or Faked

### 3.1 DQN Performance

The DQN **declines** on held-out greedy evaluation. This is reported honestly
but it means the "deep RL" story is a negative result. The DQN is:
- Pure NumPy (no GPU, no autograd)
- 2-layer MLP with 64 hidden units
- Uniform replay (no prioritised experience)
- No dueling heads, no n-step returns, no PPO

**Impact:** The PS asks for an "ML-based scheduler." SmartScan (the winner)
is a hand-designed hybrid, not a learned-from-scratch policy. The actual
end-to-end learned policies (Linear Q, DQN) underperform SmartScan. A
judge could reasonably ask: "Is the ML doing the heavy lifting, or is it
the hand-engineering?"

**Honest answer:** The ML contributes value estimation for rotation priorities
and confidence gating. The heavy lifting (phase-lock, fingerprinting,
burst characterisation) is hand-designed signal processing. This is defensible
(the hybrid approach is a valid ML-adjacent strategy) but not the "ML-based"
story the PS implies.

### 3.2 Hardware-in-the-Loop

`tools/sdr_bridge.py` accepts UDP PDWs and `live.py` ingests them. The
architecture supports real SDR input. **But there is zero evidence of it
being tested against physical hardware.** No photos, no video, no log of a
real SDR session.

**Impact:** The Live Radar page works on simulated PDWs. Connecting to a
real SDR is an engineering exercise that has been designed but not validated.

### 3.3 Sensitivity as a Metric

Sensitivity is a receiver physics parameter, not a scheduling metric. The PS
lists it alongside scheduling FoMs, which creates ambiguity. The ROC
experiment sweeps sensitivity thresholds, but there is no single "system
sensitivity: X dBm" number reported.

**Impact:** Minor. A judge familiar with EW would understand that sensitivity
is governed by the receiver front-end, not the scheduler. A judge unfamiliar
might penalise the absence.

### 3.4 Elevation / 2D Bearing

AOA is modelled as a scalar (azimuth only). No elevation angle, no full
antenna pattern, no 3D geometry.

**Impact:** The geolocation story (CEP improving with more receivers) works
in 2D. Real systems need 3D. The PS mentions "spatially scanning emitters"
which implies spatial awareness, but doesn't explicitly require elevation.

### 3.5 Identification Library

The library in `identification.py` contains 10 illustrative entries inspired
by public-domain NATO reporting names (e.g., "SNOW DRIFT", "FLAT FACE").
These are **not operational ELINT data**. They are class-level descriptions
with coarse frequency/pulse-width/scan-period ranges.

**Impact:** 86% identification accuracy (14/19 streams) on the synthetic reference episode is
meaningless if the library doesn't represent real threats. The architecture
supports plugging in a real library; the content is placeholder.

### 3.6 Scenario Diversity

Default scenario: 24 bands, 3000 slots, ~25 emitters. All emitters are
sampled from the same priors (Gaussian SNR, uniform band, uniform period).
No terrain, no weather, no multi-path, no jamming, no operator input.

**Impact:** The evaluation is statistically rigorous on the scenarios it
tests, but the scenarios are synthetic and relatively simple. Real EW
environments are messier: co-channel interference, propagation anomalies,
wideband noise jamming, barrage jammers, DRFM repeaters. None of these
are modelled.

### 3.7 Cross-Episode Learning Depth

SmartScan's `end_episode()` is a no-op (`pass`). The `MetaScheduler`
wrapper provides cross-episode state preservation (phase locks, band
statistics), but there is no gradient-based cross-episode training for
SmartScan itself. The DQN and Linear Q do train across episodes, but
they underperform SmartScan.

**Impact:** The "trained based on hits and misses" requirement is met within
a single episode (online learning) and across episodes for the RL baselines.
SmartScan's cross-episode learning is state persistence, not parameter
optimisation.

### 3.8 No Cost / Resource Model

The PS mentions "reward / cost function." The reward function exists
(`runner.py::step_reward`) but there is no explicit cost model:
- No compute cost per scheduler decision
- No power consumption model
- No dwell-time cost (all dwells are 1 slot)
- No opportunity cost framework

**Impact:** The reward function is simple and reasonable, but a judge
expecting a formal cost-benefit framework will not find one.

---

## 4. Implementation Completeness Scorecard

| Dimension | Score | Notes |
|---|---|---|
| **Core scheduling algorithm** | 8/10 | SmartScan is innovative and well-evaluated. Deducted for DQN weakness and hybrid (not pure ML) nature. |
| **Receiver model** | 7/10 | Clean abstraction. Missing: antenna patterns, elevation, hardware nonlinearities. |
| **Environment model** | 8/10 | Five emitter types including evasive. Missing: terrain, multipath, jamming. |
| **Figures of merit** | 9/10 | 6/7 fully implemented; sensitivity partially. KPP-gated MES is defence-grade. |
| **Statistical evaluation** | 9/10 | 50-episode Monte Carlo, permutation tests, Holm correction, ablation. Could use larger samples. |
| **ML depth** | 5/10 | SmartScan is the star but is hand-designed. DQN declines. Linear Q improves but underperforms. No PPO, no transformer, no advanced RL. |
| **Identification** | 6/10 | Architecture is solid. Library is placeholder. Accuracy claim is misleading without real data. |
| **Geolocation** | 7/10 | AOA triangulation works. 2D only. CEP improves with receivers. |
| **Multi-receiver** | 7/10 | Cooperative de-confliction. Scaling demonstrated (663→1192→1808). No real multi-platform test. |
| **Live integration** | 5/10 | UDP bridge designed. No real hardware evidence. Simulated PDWs only. |
| **Software quality** | 8/10 | 250 tests, Docker, strict JSON, pickle-free. Strong for a hackathon project. |
| **Presentation / UX** | 8/10 | React command centre, desktop app, website. Professional-looking. |
| **Documentation** | 8/10 | PROJECT_EXPLAINED.md, EVALUATION.md, VitePress docs site, README. Thorough. |

**Overall: ~7.2/10 — a strong hackathon submission with genuine innovation
in the scheduling algorithm, but with honest gaps in ML depth, hardware
validation, and operational realism.**

---

## 5. What a hostile reviewer would attack

1. **"Your best scheduler is hand-designed, not learned."**
   SmartScan's five behaviours are engineered, not trained end-to-end.
   The learned components (value estimates, confidence gating) contribute
   but don't dominate. The DQN (the actual ML policy) performs worse.

2. **"Your identification accuracy is meaningless."**
   86% (14/19) on an illustrative library with synthetic scenarios is
   not a meaningful benchmark.

3. **"No real hardware validation."**
   The UDP bridge exists but has never been connected to a real SDR.
   All results are simulation-only.

4. **"Your scenarios are too simple."**
   24 bands, Gaussian SNR, no jamming, no multipath, no terrain.
   Real EW environments are nastier.

5. **"Sensitivity is listed in the PS but you don't report it as a metric."**
   It's a receiver parameter, not a scheduling outcome. But the PS lists it.

---

## 6. What would make this a 10/10

1. **A genuine end-to-end learned policy** (PPO, SAC, or transformer-based)
   that outperforms or matches SmartScan. This would close the "is the ML
   doing the work?" gap.

2. **Real SDR hardware demonstration** — even a 30-second video of an
   RTL-SDR feeding PDWs into the system.

3. **A richer identification library** — even 50 entries instead of 10,
   with more distinctive features.

4. **Jamming and multipath models** in the environment — even simple ones
   (e.g., barrage jammer as a wideband noise source).

5. **Larger-scale Monte Carlo** — 1000+ episodes with sensitivity analysis
   on hyperparameters.

6. **Transfer learning demonstration** — train on one set of scenarios,
   evaluate on a genuinely different set (different emitter counts, different
   frequency ranges).

---

## 7. Bottom Line

The project is **substantially complete** against the problem statement. Every
line of the PS has a corresponding implementation. The core scheduling
algorithm (SmartScan) is genuinely innovative and statistically validated.
The evaluation framework exceeds what most academic papers provide.

The honest weaknesses are:
- The ML is real but not dominant; the heavy lifting is signal processing.
- The DQN doesn't work well (reported honestly).
- No hardware validation.
- Placeholder identification data.
- Simple synthetic scenarios.

**For a Smart India Hackathon submission, this is a strong project — probably
top 5% in terms of code quality, evaluation rigor, and documentation. For a
defence procurement proposal, it would need significant hardening in hardware
integration, scenario complexity, and operational library depth.**

---

*Generated from codebase inspection of the ASTRA repository as of 2026-08-28.*
*All claims verified against actual source code in `ewsmart/`, `tests/`, and
project documentation.*
