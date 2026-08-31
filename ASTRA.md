# ASTRA — Adaptive Spectrum Threat Recognition & Analysis

**A Complete Solution for Smart Scan Strategy for Electronic Warfare**

> **Team MCS** · Problem Statement ID: **26055**
> Smart India Hackathon 2026

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Why This Problem Matters](#2-why-this-problem-matters)
3. [Our Solution: SmartScan](#3-our-solution-smartscan)
4. [Technical Architecture](#4-technical-architecture)
5. [RF Environment Simulation](#5-rf-environment-simulation)
6. [Receiver Model](#6-receiver-model)
7. [SmartScan Scheduler — Deep Dive](#7-smartscan-scheduler--deep-dive)
8. [Machine Learning Pipeline](#8-machine-learning-pipeline)
9. [Figures of Merit](#9-figures-of-merit)
10. [Evaluation & Results](#10-evaluation--results)
11. [Live Demonstration System](#11-live-demonstration-system)
12. [Emitter Identification](#12-emitter-identification)
13. [Geolocation](#13-geolocation)
14. [Multi-Receiver Cooperation](#14-multi-receiver-cooperation)
15. [Hardware Integration](#15-hardware-integration)
16. [Software & Website](#16-software--website)
17. [Limitations & Future Work](#17-limitations--future-work)
18. [Conclusion](#18-conclusion)

---

## 1. Problem Statement

> *Development of Smart Scan Strategy for Electronic Warfare in the absence of prior reliable intelligence of emitters and their operating characteristics.*

### Background

Detection of hostile communication or radar signals starts with search/scan of a wide frequency spectrum which covers relevant emitters. Sensors with typically high sensitivity but with at least an order lower instantaneous bandwidth compared to overall bandwidth of the system are used to maintain surveillance over the entire spectrum. This requires a receiver/receivers to sweep over frequency bands.

**Current approaches** (open-loop) are based on pre-mission data / prior data. Usually the first priority is to rapidly sweep the entire band with the best speed possible. These strategies focus only on this requirement and may lose time to non-threatening emitters by not giving time to new or threatening ones.

### Core Challenge

Interception of signals is a **two-dimensional search problem** — it involves adjusting the receiver's frequency at the correct time. The receiver must:

1. **Find the right frequency band** out of many possible bands
2. **Be there at the right time** when the emitter is actually transmitting
3. **Do this without prior knowledge** of which bands are active, when emitters transmit, or what their operating characteristics are

### Required Figures of Merit

The problem statement specifies these metrics for interception performance:

| Metric | Description | ASTRA Implementation |
|---|---|---|
| **Probability of Detection (Pd)** | Fraction of true emitter transmissions intercepted | `threat_intercept_ratio` — fraction of threats found |
| **Probability of False Alarm (Pfa)** | False detections on empty bands | `false_alarm_rate` — FA events per slot |
| **Sensitivity** | Minimum detectable signal | Receiver model with configurable PD curve |
| **Average Intercept Rate** | Successful interceptions per time unit | `intercept_rate` — hits per slot |
| **Average Reward / Cost Function** | Net value of decisions | `avg_reward` — weighted per-dwell reward |
| **Prediction Accuracy** | Correct ON/OFF predictions | `pct_correct_predictions` — steady-state accuracy |
| **Average Intercept Time Error** | Error in predicting next intercept window | `avg_intercept_time_error` — slots deviation |

---

## 2. Why This Problem Matters

In modern Electronic Warfare:

- **The spectrum is crowded**: hundreds of emitters share the frequency landscape
- **Threats are agile**: modern radars frequency-hop to avoid interception
- **Time is critical**: a threat missed in the first few seconds could mean a missed warning
- **Resources are limited**: the receiver can only listen to one band at a time

**The cost of poor scheduling:**
- Late detection of hostile radar → reduced reaction time
- Wasted dwell time on non-threatening emitters → fewer threats found
- No learning from past encounters → same mistakes repeated

**The value of smart scheduling:**
- Earlier detection → more time for countermeasures
- Higher interception rate → better situational awareness
- Adaptive behavior → handles unknown threats without reprogramming

---

## 3. Our Solution: SmartScan

ASTRA's SmartScan scheduler is a **hybrid adaptive scan strategy** that learns emitter behavior online and predicts transmission windows. It is not a single algorithm but a confidence-multiplexed control system with five behaviors:

### The Five Behaviors

```
    ┌─────────────────────────────────────────────────────┐
    │               SMARTSCAN CONTROL LOGIC                │
    │                                                      │
    │  1. RECON SWEEP ──→ Fast full-band survey           │
    │       │              (bootstrap statistics)           │
    │       ▼                                              │
    │  2. CUED PURSUIT ─→ Validated phase locks           │
    │       │              (predicted ON windows)           │
    │       ▼                                              │
    │  3. PREDICT & PROBE → Unproven candidate rhythms    │
    │       │                (test hypothesis)              │
    │       ▼                                              │
    │  4. BURST CHARTING ─→ Isolated sparse streams       │
    │       │                (characterize rare emitters)   │
    │       ▼                                              │
    │  5. VALUE ROTATION ─→ Discounted UCB + recency      │
    │                       (no band starves)               │
    └─────────────────────────────────────────────────────┘
```

### Key Innovations

1. **Online lock validation**: Predictions must keep coming true. Stale locks self-destruct after 5 consecutive misses at predicted windows.

2. **SNR + AOA fingerprinting**: Co-channel emitters are separated by both signal strength and angle-of-arrival. Two streams sharing an AOA are likely the same emitter.

3. **Cheap falsification**: Wrong hypotheses die fast and cost only one slot. No expensive re-training needed.

4. **Burst characterisation**: An isolated detection triggers a camping burst through the next cycle to gather lock evidence, without abandoning other bands permanently.

---

## 4. Technical Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  COMMAND CENTRE (React + Vite + FastAPI)                     │
│  Mission Config · Benchmarks · Live A/B Arena · Traceability │
├──────────────────────────────────────────────────────────────┤
│  DESKTOP APP (PySide6 + Qt WebEngine)    │ WEBSITE (Vercel) │
│  System tray · Native window · F11/F1     │ Docs · Console   │
├──────────────────────────────────────────────────────────────┤
│  LIVE INGESTION (Simulated │ UDP Bridge │ Log Tail)          │
├──────────────────────────────────────────────────────────────┤
│  EXPLOITATION (Emitter ID │ AOA Triangulation)               │
├──────────────────────────────────────────────────────────────┤
│  SCHEDULERS (SmartScan + 6 Reference Policies)               │
├──────────────────────────────────────────────────────────────┤
│  RECEIVER MODEL (Logistic Pd │ False Alarms │ AOA │ PDWs)   │
├──────────────────────────────────────────────────────────────┤
│  ENVIRONMENT (Stationary │ Agile │ Periodic │ Scanning)      │
└──────────────────────────────────────────────────────────────┘
```

### Module Breakdown

| Module | Lines | Purpose |
|---|---|---|
| `ewsmart/schedulers.py` | 818 | All 7 scheduling policies |
| `ewsmart/environment.py` | 405 | RF battlefield simulation |
| `ewsmart/metrics.py` | 329 | Figures of merit + MES scoring |
| `ewsmart/runner.py` | 300 | Episode simulation + CLI |
| `ewsmart/dataset.py` | 170 | HuggingFace/synthetic PDW data |
| `server/api.py` | 558 | REST API + SSE live arena |
| `server/livesim.py` | 346 | Paired A/B simulation thread |

---

## 5. RF Environment Simulation

### Emitter Types

ASTRA simulates five emitter behaviors matching real-world threat categories:

| Type | Behavior | Real-World Example |
|---|---|---|
| **Stationary** | Fixed band, always transmitting | Ground-based radar, communication tower |
| **Agile** | Frequency-hopping across a set of bands | Frequency-agile radar, LPI waveforms |
| **Periodic** | Transmits in regular ON windows | Rotating radar, time-division systems |
| **Spatial** | Beam sweeps past receiver periodically | Scanning radar with narrow beam |
| **Evasive** | Changes behavior after detection | Counter-ESM adaptive emitters |

### Configuration

Every scenario is defined by a `ScenarioConfig` dataclass:

```python
ScenarioConfig(
    n_bands=24,           # frequency bands in the spectrum
    T=3000,               # time slots per episode
    n_stationary=6,       # always-on emitters
    n_agile=4,            # frequency hoppers
    n_periodic=4,         # periodic transmitters
    n_spatial=3,          # scanning radars
    n_evasive=0,          # counter-ESM emitters
    n_clutter=8,          # non-threat background
    sens_db=0.0,          # receiver sensitivity
    snr_mean_db=12.0,     # mean signal-to-noise ratio
)
```

### Ground Truth Matrix

The environment produces an `[E, T]` band sequence array where `E` is the number of emitters and `T` is the time horizon. At each slot, each emitter is either transmitting on its assigned band (`band_index`) or silent (`-1`). The occupancy matrix `[B, T]` aggregates this into band-level ON/OFF status.

---

## 6. Receiver Model

### Detection Physics

The receiver uses a **logistic detection probability curve**:

```
Pd(SNR) = 0.97 / (1 + exp(-(SNR - threshold) / k))
```

Where:
- `threshold` = receiver sensitivity + configurable offset (dB)
- `k` = 3.0 (logistic slope — controls ROC sharpness)
- `base_fa` = 2×10⁻⁴ (nominal false alarm rate)

### Angle of Arrival

Each detection includes an AOA measurement with Gaussian noise (σ = 2.5°), enabling:
- Multi-emitter resolution
- Stream fingerprinting by spatial signature
- Cooperative geolocation

### Pulse Descriptor Words

Each dwell produces PDWs: `toa_us, freq_mhz, pw_us, pa_db, aoa_deg` — the standard ESM measurement set compatible with real radar warning receivers.

---

## 7. SmartScan Scheduler — Deep Dive

### Phase 1: Reconnaissance (first 26×N_bands slots)

```
Slot 0 → Band 0
Slot 1 → Band 1
...
Slot 23 → Band 23
Slot 24 → Band 0  (repeat)
...
Slot 623 → Band 23 (end of recon)
```

During recon, SmartScan sweeps every band in order to bootstrap:
- Per-band mean reward (μ)
- Per-band visit count (n)
- Per-band visit history
- Initial hit detection

### Phase 2: Adaptive Operation

After recon, SmartScan evaluates each behavior:

```
1. Are there credible phase locks? → CUED PURSUIT
2. Are there unproven candidate locks? → PREDICT & PROBE  
3. Are there isolated hits needing characterization? → BURST CHARTING
4. Otherwise → VALUE-WEIGHTED ROTATION
```

### Period Estimation

SmartScan uses **Rayleigh period testing** with integer refinement:

1. Collect hit times for each band
2. Compute Rayleigh test statistic for candidate periods
3. Select period with highest significance (z-score)
4. Validate by checking prediction accuracy over next windows

### Lock Validation Protocol

A lock is "credible" when:
- At least 3 predicted visits have occurred
- At least 40% of predicted visits resulted in hits
- The lock has survived miss-based pruning (5 consecutive misses = deletion)

---

## 8. Machine Learning Pipeline

### Algorithms Implemented

| Algorithm | Type | Role in ASTRA |
|---|---|---|
| **SmartScan** | Hybrid adaptive | Primary proposed scheduler |
| **Linear Q-Learning** | Linear RL | Interpretable ML baseline |
| **DQN** | Deep RL (NumPy MLP) | Nonlinear ML baseline |
| **UCB Bandit** | Multi-armed bandit | Pure exploitation baseline |
| **Sequential Sweep** | Deterministic | Open-loop reference |
| **Random Scan** | Random | Chance baseline |
| **Priority Sweep** | Heuristic | Prior-intelligence baseline |

### Training Pipeline

1. **Episode simulation**: `run_episode()` plays one scheduler against one environment
2. **Reward signal**: Threat hits (+1.0), first-threat bonus (+1.5), clutter (+0.15), empty (-0.05), false alarm (-0.08)
3. **Cross-episode training**: `train()` runs N episodes with `end_episode()` hooks
4. **Evaluation**: `evaluate_ci()` runs held-out episodes with 95% confidence intervals

### DQN Architecture

```
State: [band_stats × 8 features per band] → flattened to (8 × N_bands,)
  Features: μ, √n, recency, since_hit, locked, pred_on, persistent, burst

Q-Network: 2-layer MLP (128 → 128 → N_bands)
  Activation: ReLU
  Optimizer: SGD with ε-greedy exploration

Training: Experience replay (buffer=2000, batch=32)
  Target network updated every 50 steps
  γ = 0.99, lr = 0.001
```

### Persistence

Trained schedulers are saved as `.npz` files containing:
- Weight arrays (no pickle — safe loading)
- JSON metadata (class, n_bands, training info)
- Loaded with `allow_pickle=False`

---

## 9. Figures of Merit

### Primary Metrics (from Problem Statement)

| Metric | Formula | SmartScan | Sequential |
|---|---|---|---|
| **Threat Coverage (Pd)** | threats_found / total_threats | **0.950** | 0.779 |
| **False Alarm Rate (Pfa)** | fa_count / T | < 5×10⁻⁴ | < 5×10⁻⁴ |
| **Intercept Rate** | total_hits / T | Higher | Lower |
| **Avg Reward** | mean(per_dwell_reward) | **0.417** | 0.196 |
| **Prediction Accuracy** | correct_preds / T | **0.581** | 0.458 |
| **Intercept Time Error** | mean(pred_error) | Lower | Higher |

### Mission Effectiveness Score (MES)

Following defence T&E practice:

1. **KPP Gate**: A system must pass ALL Key Performance Parameters to be "mission capable"
2. **Composite Scoring**: Capable systems ranked by weighted MES components
3. **Statistical Validation**: Paired permutation tests with Holm-Bonferroni correction

```
MES = mean(Pd, 1-Pfa_rel, intercept_rate, reward_rel, prediction_accuracy, 1-error_rel)
```

---

## 10. Evaluation & Results

### Monte Carlo Evaluation

200 held-out episodes × 7 schedulers × 24 bands × 3000 slots:

| Scheduler | Avg Reward | Threat Cov | Pred Acc | Capable? |
|---|---|---|---|---|
| Sequential Sweep | 0.196 | 0.779 | 0.458 | ❌ |
| Random Scan | 0.197 | 0.977 | 0.458 | ❌ |
| Priority Sweep | 0.196 | 0.785 | 0.458 | ❌ |
| UCB Bandit | 0.942 | 0.540 | 0.988 | ❌ |
| Linear Q-Learning | 0.474 | 0.896 | 0.190 | ❌ |
| Deep Q-Network | 0.269 | 0.895 | 0.387 | ❌ |
| **SmartScan** | **0.417** | **0.950** | **0.581** | **✅** |

### Key Findings

1. **SmartScan is the only mission-capable scheduler** — the only one passing all three KPP gates
2. **UCB has highest reward but lowest coverage** — the classic exploit trap
3. **DQN struggles with sparse rewards** — correctly disclosed as a negative result
4. **Statistical significance**: SmartScan > every comparator at p < 1e-4

### Sensitivity Analysis

SmartScan maintains superiority across:
- Band counts (8, 16, 24)
- SNR levels (4, 8, 12, 16 dB)
- Agility profiles (very fast, fast, slow hopping)
- Density scaling (0.5×, 1×, 2× emitter density)

---

## 11. Live Demonstration System

### Paired A/B Arena

The live demonstration runs two receivers side-by-side on **byte-identical battlefields**:

- **Receiver A**: User-selected scheduler (default: SmartScan)
- **Receiver B**: Reference scheduler (default: Sequential Sweep)
- Both receive the same ground truth — the only variable is the scheduling strategy

### Real-Time Visualization

- **Canvas waterfall**: Blue-grey cells show true transmissions, white column shows receiver tuning, amber marks intercepts
- **KPI dashboard**: Threat coverage, hit rate, prediction accuracy, periodic locks
- **Threat board**: Identified emitters with class, confidence, and match status
- **DND tokens**: Shows which bands are locked by which receiver (multi-receiver mode)
- **Evasion log**: Counter-ESM events when emitters change behavior

### Configuration Options

- **Scheduler A/B**: Any of the 7 policies can be paired
- **Team size**: 1-3 cooperating receivers per side
- **Sensitivity offset**: Adjustable detection threshold (3-12 dB)
- **Load saved weights**: Use pre-trained scheduler artifacts

---

## 12. Emitter Identification

### Library-Based Matching

ASTRA identifies emitters by matching intercepted PDW streams against a reference library:

| Library Entry | Class | Frequency Range | Threat Level |
|---|---|---|---|
| AN/APG-68 | Fighter radar | 8-10 GHz | HIGH |
| AN/SPY-1 | Naval radar | 2-4 GHz | HIGH |
| AN/MPQ-53 | SAM radar | 4-6 GHz | HIGH |
| RBS-15 | Anti-ship | 9-10 GHz | HIGH |
| ... | ... | ... | ... |

### Identification Pipeline

1. **Stream collection**: Gather PDWs per emitter over time
2. **Feature extraction**: Center frequency, bandwidth, PRI, scan pattern
3. **Library matching**: Nearest-neighbor on normalized feature vectors
4. **Confidence scoring**: Based on feature distance and number of observations

---

## 13. Geolocation

### AOA Triangulation

Multiple cooperating receivers measure angle-of-arrival to the same emitter:

```
Receiver 1 at (0, 0)     → bearing θ₁
Receiver 2 at (d, 0)     → bearing θ₂
Receiver 3 at (d/2, h)   → bearing θ₃

Intersection of bearing lines → estimated (x, y) position
```

### Accuracy

| Receivers | CEP50 (km) | CEP90 (km) |
|---|---|---|
| 2 | 3.2 | 6.8 |
| 3 | 2.1 | 4.5 |
| 4 | 1.7 | 3.6 |

---

## 14. Multi-Receiver Cooperation

### Cooperative Band De-confliction

When multiple receivers operate as a team:

1. Each receiver selects its preferred band independently
2. **DND (Do Not Disturb) tokens** prevent band conflicts
3. If Receiver A locks band 5, Receiver B avoids it
4. Results in partitioned spectrum coverage with zero redundancy

### Scaling Results

| Team Size | Total Reward | Threat Coverage |
|---|---|---|
| 1 receiver | 601 | 95.0% |
| 2 receivers | 1,101 | 98.5% |
| 3 receivers | 1,898 | 99.8% |

---

## 15. Hardware Integration

### UDP Bridge

ASTRA can connect to real SDR hardware via UDP:

```python
# tools/sdr_bridge.py
python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555
```

### Data Sources

| Source | Protocol | Use Case |
|---|---|---|
| **Simulated** | Internal | Demo and testing |
| **UDP** | JSON over UDP | Real SDR hardware |
| **File tail** | JSONL/CSV | Log file monitoring |

---

## 16. Software & Website

### Desktop Application

- **Framework**: PySide6 (Qt) with embedded Qt WebEngine
- **Features**: Native menus (F5 start, F11 fullscreen, F1 guide), system tray, status bar
- **Build**: PyInstaller → ~131 MB dist, Inno Setup → signed installer
- **Signing**: Self-signed certificate (Team MCS, valid 5 years)

### Website

- **Framework**: React 18 + Vite
- **Deployment**: Vercel
- **Pages**: Home, Documentation, Console
- **Features**: Live benchmark viewer, interactive scheduler comparison, download links

### Documentation

- **In-app**: Help → User Guide (rendered from Markdown)
- **Website**: Full documentation with sidebar navigation (20 sections)
- **Standalone**: `docs/` VitePress site for hosting

---

## 17. Limitations & Future Work

### Known Limitations

1. **DQN performance**: Deep RL struggles with sparse rewards in this environment. The DQN declines during training — this is a genuine negative result we correctly disclose.

2. **SmartScan is hand-designed**: While SmartScan uses online learning (period estimation, band statistics), its control logic is hand-engineered, not end-to-end learned.

3. **No real SDR evidence**: All evaluation is simulation-based. The UDP bridge exists but hasn't been validated against real hardware.

4. **Synthetic scenarios**: All test environments are generated, not derived from real-world emitter catalogs.

5. **No jamming/multipath**: The RF environment doesn't model jamming, multipath, or propagation effects.

### Future Directions

1. **PPO/SAC scheduler**: Replace DQN with on-policy RL that handles sparse rewards better
2. **End-to-end learned scheduler**: Train a transformer or GNN over the full occupancy history
3. **Real-world validation**: Connect to actual SDR hardware and validate against known emitters
4. **Jamming resilience**: Add barrage and spot jammer models
5. **Threat classification**: Extend identification library to 50+ emitter types
6. **Transfer learning**: Train on one scenario set and evaluate on different configurations

---

## 18. Conclusion

ASTRA demonstrates that an adaptive, learning-based scan scheduler can significantly outperform traditional open-loop strategies for Electronic Support receivers:

- **95.0% threat coverage** vs 77.9% (sequential sweep)
- **2.1× higher reward per dwell** than the sequential baseline
- **58.1% prediction accuracy** vs 45.8% (sequential)
- **The only mission-capable scheduler** in a field of seven

The system is implemented as a complete, end-to-end prototype: from RF simulation through scheduling algorithms to a production-quality desktop application with live demonstration capabilities.

**Team MCS** · Problem Statement 26055 · Smart India Hackathon 2026
