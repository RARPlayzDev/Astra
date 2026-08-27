# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the ASTRA desktop application.
# Build:  pyinstaller --noconfirm --clean astra.spec   ->  dist/ASTRA/ASTRA.exe
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("server")
    + collect_submodules("webview")
    + ["ewsmart.config", "ewsmart.environment", "ewsmart.receiver",
       "ewsmart.schedulers", "ewsmart.periodic", "ewsmart.metrics",
       "ewsmart.runner", "ewsmart.live", "ewsmart.dataset",
       "ewsmart.persistence", "ewsmart.identification", "ewsmart.geo",
       "ewsmart.sigtests", "ewsmart.multireceiver", "markdown"]
)

webview_lib = []
import os, glob
for _p in glob.glob(os.path.join(os.path.dirname(__import__("webview").__file__), "lib", "*.dll")):
    webview_lib.append((_p, "webview/lib"))

a = Analysis(
    ["desktop.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("frontend/dist", "frontend/dist"),
        ("docs/ASTRA_Software_Documentation.md", "docs"),
        ("scenarios", "scenarios"),
        ("results/suite_results.json", "results"),
        ("figures", "figures"),
        ("models", "models"),
    ] + webview_lib,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "streamlit", "matplotlib", "pandas", "pytest",
              "PyInstaller"],
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


