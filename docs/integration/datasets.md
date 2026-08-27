# Datasets

ASTRA supports the referenced datasets from the problem statement.

## JC Wise Radar Emitter Database (2024)

Used as the basis for the **identification library** — emitter profiles
that intercepted signal streams are matched against during fingerprinting.

Each library entry contains:
- Emitter name and classification (search radar, tracking radar, etc.)
- Typical frequency range, pulse width, scan type
- Threat level (HIGH / MEDIUM / LOW)

## Alan Turing Institute Synthetic Radar Dataset

Available on HuggingFace. ASTRA can import it in two modes:

### Online (HuggingFace)
```python
from ewsmart.dataset import load_pdws
pdws = load_pdws(max_rows=8000, seed=0)
```

### Offline fallback
A schema-identical synthetic fallback is bundled so ASTRA works air-gapped.
The fallback generates PDWs matching the HuggingFace schema.

## Import workflow

1. **Import PDWs**: Data & Sources → "Import pre-loaded dataset"
2. **Inspect**: Scatter plot of frequency vs time-of-arrival
3. **Calibrate**: "Calibrate battlefield from this dataset" → creates scenario
4. **Run**: SmartScan runs against the calibrated battlefield

## Calibration

Frequency clustering groups observed PDWs into emitter streams.
Cluster statistics (frequency, temporal pattern, power) become the
scenario's emitter definitions.
