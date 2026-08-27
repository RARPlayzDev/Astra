# Scenarios

A scenario is a JSON file in `/scenarios` that defines a battlefield.

## Format

```json
{
  "n_bands": 24,
  "T": 3000,
  "seed": 42,
  "n_stationary": 6,
  "n_agile": 4,
  "n_periodic": 4,
  "n_spatial": 3,
  "n_clutter": 8,
  "snr_mean_db": 12.0,
  "snr_std_db": 4.0,
  "freq_min_mhz": 2000,
  "freq_max_mhz": 18000
}
```

## Fields

| Field | Default | Meaning |
|---|---|---|
| `n_bands` | 24 | Number of frequency bins |
| `T` | 3000 | Episode length in slots |
| `seed` | 0 | Reproducibility seed |
| `n_stationary` | 6 | Continuous transmitters |
| `n_agile` | 4 | Frequency-hopping emitters |
| `n_periodic` | 4 | Scanning radars (rotation-based) |
| `n_spatial` | 3 | Rotating beam emitters |
| `n_clutter` | 8 | Background noise sources |
| `n_evasive` | 0 | Counter-ESM evasive emitters |
| `snr_mean_db` | 12 | Signal strength mean |
| `snr_std_db` | 4 | Signal strength std dev |
| `freq_min_mhz` | 2000 | Tuning range lower bound |
| `freq_max_mhz` | 18000 | Tuning range upper bound |

## Emitter types

| Type | Behaviour | Scheduler challenge |
|---|---|---|
| **Stationary** | Transmits 100% of the time on one band | Easy to detect, wastes dwell time if visited repeatedly |
| **Agile** | Hops between a set of frequencies | Hard to predict; must visit multiple bands |
| **Periodic** | Transmits at regular intervals (scan rotation) | Learnable with phase-lock; high reward when predicted |
| **Spatial** | Rotating beam, ON/OFF pattern | Periodic-like but with spatial component |
| **Clutter** | Background noise, low threat | Should be deprioritised |
| **Evasive** | Shifts phase/frequency after 3+ consecutive intercepts | Counter-ESM: must re-acquire after evasion |

## Reproducibility

Scenario + seed → exactly reproducible battlefield.
The same seed always produces the same emitter placement, frequencies,
and temporal patterns.

## Built-in presets

| Name | Bands | Horizon | Seed | Description |
|---|---|---|---|---|
| Demo | 24 | 3000 | 42 | Balanced scenario |
| Dense low-SNR | 32 | 3000 | 7 | 10 stationary + 8 agile |
| Small & fast | 12 | 1200 | 3 | Quick iteration |
