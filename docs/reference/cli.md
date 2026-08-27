# CLI Tools

## Core commands

| Command | Purpose |
|---|---|
| `python desktop.py` | Launch the desktop application (pywebview) |
| `python desktop_qt.py` | Launch the native Qt desktop application |
| `python -m uvicorn server.api:app --port 8000` | Run the API server standalone |

## Experiment suite

```bash
# Full evaluation suite (~10 minutes)
python -m ewsmart.experiments --suite full

# Individual suites
python -m ewsmart.experiments --suite monte_carlo
python -m ewsmart.experiments --suite significance
python -m ewsmart.experiments --suite sensitivity
python -m ewsmart.experiments --suite ablation
python -m ewsmart.experiments --suite multireceiver
```

## Training & evaluation

```bash
# Train + evaluate one scenario
python -m ewsmart.runner \
    --scenario scenarios/demo.json \
    --save-dir models \
    --json-out results.json

# Meta-learning evaluation
python -c "from ewsmart.experiments import evaluate_meta_learning; evaluate_meta_learning()"
```

## Sensor integration tools

```bash
# Synthetic PDW generator
python tools/pdw_generator.py --port 5555 --rate 400

# Bridge CSV sweeps into ASTRA format
python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555

# Relay an existing JSON feed
python tools/sdr_bridge.py --mode udp --in-port 5000 --out-port 5555
```

## Build

```bash
# Build the EXE (pywebview version)
powershell -File tools/build_exe.ps1

# Build the frontend
cd frontend && npm install && npm run build

# Build documentation
cd docs && npm install && npm run build
```

## Testing

```bash
# All tests
python -m unittest discover -s tests -v

# Core module tests
python tests/test_modules.py

# SmartScan tests
python tests/test_smartscan.py
```
