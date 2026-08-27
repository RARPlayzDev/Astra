# SmartScan Algorithm

SmartScan is a hybrid scheduler that **learns on the job**. It multiplexes
five behaviours based on learned confidence.

## The five behaviours

### 1. Reconnaissance sweep
Initial sweep across all bands to gather baseline statistics.
Every band is visited at least `recon_factor × n_bands` times to build
initial hit-rate estimates and detect any transmission activity.

### 2. Cued pursuit (phase-lock)
When SmartScan detects a **periodic** emitter (one that transmits at regular
intervals), it estimates the period using a Rayleigh estimator with integer
refinement. Once validated (multiple consistent detections), it phase-locks
and arrives **before** each predicted transmission window.

### 3. Predict-and-probe
For phase-locked bands, SmartScan predicts the next ON window and positions
the receiver there before it opens. This is the core intelligence advantage —
being in the right place at the right time.

### 4. Burst characterisation
When a new or uncertain signal is detected, SmartScan allocates a short burst
of consecutive dwells to characterise it: measure its frequency, pulse width,
scan rhythm, and AOA. This builds the emitter fingerprint for identification.

### 5. Value-weighted rotation
After the recon phase, SmartScan allocates dwell time based on a value score:
- **High-value bands** (recently productive, periodic locks, high SNR) get more time
- **Cold bands** (not visited recently) get guaranteed minimum visits (recency)
- **Empty bands** get progressively less time as confidence grows

## Decision flow

```
                    ┌─────────────────────┐
                    │   Band selected?     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Phase-locked on this │──YES──→ Cued pursuit
                    │ band?                │         (predict window)
                    └──────────┬──────────┘
                               │ NO
                    ┌──────────▼──────────┐
                    │ Persistent stream    │──YES──→ Value-weighted
                    │ confirmed?           │         exploitation
                    └──────────┬──────────┘
                               │ NO
                    ┌──────────▼──────────┐
                    │ Recon phase still    │──YES──→ Sequential sweep
                    │ active?              │
                    └──────────┬──────────┘
                               │ NO
                    ┌──────────▼──────────┐
                    │ Exploration needed   │──YES──→ Epsilon-greedy
                    │ (explore_eps)?       │         exploration
                    └──────────┬──────────┘
                               │ NO
                    ┌──────────▼──────────┐
                    │ Value-weighted       │
                    │ band selection       │
                    └─────────────────────┘
```

## Key parameters

| Parameter | Default | Purpose |
|---|---|---|
| `recon_factor` | 26 | Recon slots per band = factor × n_bands |
| `explore_eps` | 0.048 | Post-recon random exploration rate |
| `exploit_ramp` | 0.60 | Steepness of exploitation ramp |
| `recency_weight` | 0.16 | Minimum revisit weight for cold bands |
| `phase_lock_threshold` | 3 | Consecutive validations needed for lock |
| `persistent_window` | 10 | Visits needed for persistent confirmation |
| `persistent_threshold` | 0.85 | Hit rate for persistent confirmation |

## Predictions

SmartScan makes binary predictions (ON/OFF) for the band it selects each slot:
- **ON**: If the band has a validated phase-lock or is confirmed persistent
- **OFF**: Otherwise

Prediction accuracy is evaluated over the steady-state phase (after initial
reconnaissance) across all slots.
