"""Post-build cleanup: surgically remove safe packages from PyInstaller dist.

Run after pyinstaller to reduce the dist folder:
    python tools/cleanup_dist.py

Only removes packages we are CERTAIN are not needed at runtime.
"""
import shutil
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "dist" / "ASTRA" / "_internal"

# Only remove packages that are 100% not imported by ewsmart/server/desktop_qt
SAFE_DIRS = [
    # PySide6 bloat we don't use (but keep Qt6 DLLs!)
    "PySide6/resources",
    "PySide6/translations",
    "PySide6/qml",
    "PySide6/Designer",
    "PySide6/lupdate",
    "PySide6/lrelease",
    "PySide6/rcc",
    "PySide6/uic",
    # HuggingFace leftovers (not imported at runtime)
    "huggingface_hub-*.dist-info",
]

removed_size = 0

if not DIST.exists():
    print(f"Dist directory not found: {DIST}")
    raise SystemExit(1)

print(f"Cleaning {DIST} ...")

for pattern in SAFE_DIRS:
    for p in DIST.glob(pattern):
        if p.is_dir():
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            shutil.rmtree(p)
            removed_size += size
            print(f"  removed dir: {p.name}")
        elif p.is_file():
            size = p.stat().st_size
            p.unlink()
            removed_size += size
            print(f"  removed file: {p.name}")

# Remove specific dist-info directories for packages we don't need
for d in DIST.iterdir():
    if not d.is_dir() or not d.name.endswith(".dist-info"):
        continue
    name_lower = d.name.lower()
    # Only remove dist-info for packages we know we don't need
    safe_remove_prefixes = [
        "huggingface", "datasets", "transformers", "torch",
        "scipy", "scikit", "pandas", "pillow", "opencv",
        "tensorflow", "keras", "seaborn", "matplotlib",
        "lxml", "beautifulsoup", "cryptography", "pyarrow",
        "tiktoken", "pythonnet", "webview",
    ]
    if any(name_lower.startswith(x) for x in safe_remove_prefixes):
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        shutil.rmtree(d)
        removed_size += size
        print(f"  removed dist-info: {d.name}")

print(f"\nSaved {removed_size / 1024 / 1024:.1f} MB")
print("Done.")
