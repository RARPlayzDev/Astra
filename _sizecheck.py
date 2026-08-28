import os
from pathlib import Path

root = Path(r"d:\Kaarthi\Dev Space\SIH2026\p1")
internal = root / "dist" / "ASTRA" / "_internal"


def dir_size(p):
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


dirs = []
for d in internal.iterdir():
    if d.is_dir():
        dirs.append((d.name, dir_size(d) / 1e6))
dirs.sort(key=lambda x: -x[1])
print("Top dist/_internal directories by size (MB):")
for name, mb in dirs[:10]:
    print(f"  {name:<28} {mb:>8.1f}")

print(f"\n_internal total: {dir_size(internal)/1e6:.0f} MB")

print("\nSource imports of heavy packages (ewsmart/server):")
for f in sorted(list((root / "ewsmart").glob("*.py")) +
                list((root / "server").glob("*.py"))):
    txt = f.read_text(encoding="utf-8", errors="ignore")
    for line in txt.splitlines():
        if any(k in line for k in ("import scipy", "from scipy", "import sklearn",
                                   "from sklearn", "import PIL", "from PIL",
                                   "import matplotlib", "import dask",
                                   "import pandas")):
            print(f"  {f.name}: {line.strip()}")