# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the ASTRA desktop application.
# Build:  pyinstaller --noconfirm --clean astra.spec   ->  dist/ASTRA/ASTRA.exe
from PyInstaller.utils.hooks import collect_submodules

# Only collect submodules for packages we actually use
hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("server")
    + ["ewsmart.config", "ewsmart.environment", "ewsmart.receiver",
       "ewsmart.schedulers", "ewsmart.periodic", "ewsmart.metrics",
       "ewsmart.runner", "ewsmart.live", "ewsmart.dataset",
       "ewsmart.persistence", "ewsmart.identification", "ewsmart.geo",
       "ewsmart.sigtests", "ewsmart.multireceiver", "ewsmart.db",
       "ewsmart.exceptions", "markdown"]
)

# Aggressive exclusion of heavy unused packages
EXCLUDES = [
    # GUI frameworks we don't use
    "tkinter", "webview", "webview.platforms",
    # ML/DL frameworks (not used at runtime)
    "torch", "torchvision", "torchaudio",
    "transformers", "tokenizers", "sentencepiece",
    "datasets", "huggingface_hub",
    # Scientific libs we don't need in the EXE
    "scipy", "sklearn", "scikit-learn",
    "pandas", "dask",
    # Image/video processing
    "PIL", "cv2", "opencv-python",
    # Visualization (not needed at runtime)
    "matplotlib", "seaborn",
    # Other unused
    "pyarrow", "tensorflow", "keras",
    "streamlit", "PyInstaller",
    "pytest", "coverage",
    "lxml", "bs4", "html5lib",
    "cryptography", "cffi",
    "notebook", "IPython", "ipykernel",
    "pygments", "docutils", "sphinx",
    "networkx", "sympy",
    "dateutil", "tzdata",
    # Redundant torch ecosystem
    "filelock", "fsspec", "jinja2",
    "mpmath", "networkx", "nvidia-cublas-cu12",
    "nvidia-cuda-cupti-cu12", "nvidia-cuda-nvrtc-cu12",
    "nvidia-cuda-runtime-cu12", "nvidia-cudnn-cu12",
    "nvidia-cufft-cu12", "nvidia-curand-cu12",
    "nvidia-cusolver-cu12", "nvidia-cusparse-cu12",
    "nvidia-nccl-cu12", "nvidia-nvjitlink-cu12",
    "nvidia-nvtx-cu12", "triton",
    "pythonnet", "tiktoken",
]

a = Analysis(
    ["desktop_qt.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("frontend/dist", "frontend/dist"),
        ("docs/ASTRA_Software_Documentation.md", "docs"),
        ("scenarios", "scenarios"),
        ("results/suite_results.json", "results"),
        ("figures", "figures"),
        ("models", "models"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ASTRA",
    icon="assets/astra.ico",
    version="tools/version_info.txt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ASTRA",
)
