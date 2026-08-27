# File Formats

## Scenario JSON

See [Scenarios](/integration/scenarios) for the full field reference.

```json
{
  "n_bands": 24,
  "T": 3000,
  "seed": 42,
  "n_stationary": 6,
  "n_agile": 4,
  "n_periodic": 4
}
```

## PDW Datagram

See [Radar & SDR Integration](/integration/radar-sdr) for the schema.

Single object:
```json
{"toa_us": 1000.0, "freq_mhz": 9450.0, "pw_us": 1.5, "pa_db": 12.0, "aoa_deg": 90.0}
```

Array:
```json
[{"toa_us": 1000.0, "freq_mhz": 9450.0}, {"toa_us": 1001.0, "freq_mhz": 8200.0}]
```

## Model artifact (.npz)

Pickle-free NumPy archive. Loaded with `allow_pickle=False`.

Contents:
- `meta`: JSON string — `{format: "ewsmart-npz-v1", class, n_bands, ...}`
- Weight arrays specific to the scheduler class

```python
from ewsmart.persistence import load_scheduler
sched = load_scheduler("models/smart-scan.npz")
```

## suite_results.json

The output of the full experiment suite. Sections:

| Section | Content |
|---|---|
| `monte_carlo` | Per-scheduler mean ± CI for all FoMs |
| `significance` | Paired permutation test results |
| `significance_gated_mes` | Gated MES significance tests |
| `mission_effectiveness` | KPP gate + MES ranking |
| `learning` | Training curves + held-out evaluation |
| `identification` | Emitter ID accuracy |
| `roc` | Detection vs false-alarm trade-off |
| `sensitivity` | Robustness vs bands/SNR/agility/density |
| `ablation` | SmartScan component attribution |
| `multireceiver` | Cooperative team results |
| `geolocation` | AOA triangulation accuracy |
