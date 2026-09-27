# Installation

## Requirements

| Item | Requirement |
|---|---|
| Operating system | Windows 10/11 (Linux/macOS from source) |
| Python | ≥ 3.10 with pip |
| Node.js | ≥ 18 (only if rebuilding the UI) |
| RAM | ≥ 4 GB recommended |

## Installer (recommended)

1. Download `ASTRA-Setup-3.0.0.exe` from the releases page.
2. Run the installer. ASTRA installs to `C:\Program Files\ASTRA\`.
3. Double-click **ASTRA.exe** to launch.

::: tip
The installer bundles the Edge WebView2 runtime. If it is missing on your system, the installer will download and install it automatically.
:::

## From source

```bash
# Clone the repository
git clone <repository-url>
cd p1

# Install Python dependencies
python -m pip install -r requirements.txt fastapi uvicorn markdown pywebview

# Build the frontend (optional — pre-built bundles are included)
cd frontend
npm install
npm run build
cd ..

# Launch
python desktop.py
```

## Using the Qt desktop app (experimental)

For a native window without pywebview:

```bash
pip install PySide6
python desktop_qt.py
```

## Verify installation

1. Launch ASTRA (any method above).
2. Open **Tools → Diagnostics** (or press `Ctrl+D`).
3. All checks should show ✓ (green).

| Check | What it verifies |
|---|---|
| Core modules import | `ewsmart` package loads without errors |
| Simulation environment boots | Creates an RF environment and runs one dwell |
| Benchmark results present | `results/suite_results.json` exists |
| Figures generated | At least one PNG in `/figures` |
| Model artifacts valid | `.npz` files load correctly |
| Frontend bundle | `index.html` exists in the dist |
| User manual available | Documentation file exists |
| UDP loopback | Local UDP socket send/receive works |

## Browser-only mode

Any mode above also works from a normal browser at `http://127.0.0.1:<port>`.
The port is printed at startup. All features are identical — only the window frame differs.
