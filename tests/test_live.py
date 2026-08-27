import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))
"""Tests for the live radar integration module."""
import json
import time
from pathlib import Path

import numpy as np

from ewsmart.config import ScenarioConfig
from ewsmart.environment import RFEnvironment
from ewsmart.live import (FileTailSource, LiveSpectrum, OnlineScanner,
                          SimulatedLiveSource, UDPSource, _band_of)
from ewsmart.schedulers import SmartScanScheduler, SequentialSweep


def test_band_mapping():
    assert _band_of(2000.0, 8, 2000.0, 18000.0) == 0
    assert _band_of(18000.0, 8, 2000.0, 18000.0) == 7
    assert 2 <= _band_of(10000.0, 8, 2000.0, 18000.0) <= 5
    assert _band_of(100.0, 8, 2000.0, 18000.0) == 0      # below range clips
    assert _band_of(99999.0, 8, 2000.0, 18000.0) == 7    # above range clips


def test_simulated_source_streams():
    env = RFEnvironment(n_bands=8, T=300, seed=11)
    src = SimulatedLiveSource(env, seed=12)
    got = 0
    for _ in range(40):
        _, pdws = src.poll()
        got += len(pdws)
    assert got > 0, "simulated feed should emit PDWs on occupied bands"


def test_spectrum_ingest_and_view():
    spec = LiveSpectrum(n_bands=8, fmin_mhz=2000.0, fmax_mhz=18000.0, window=64)
    for i in range(20):
        pdws = [{"toa_us": float(i) * 1000.0, "freq_mhz": 2000.0 + 800.0,
                 "pa_db": 10.0, "aoa_deg": 45.0, "pw_us": 1.0}]
        spec.ingest(pdws)
    assert spec.view().shape == (8, 64)
    assert int(spec.view().sum()) >= 1
    assert len(spec.pdw_log) == 20


def test_online_scanner_learns_value():
    env = RFEnvironment(n_bands=8, T=300, seed=21)
    src = SimulatedLiveSource(env, seed=22)
    spec = LiveSpectrum(n_bands=8, fmin_mhz=2000.0, fmax_mhz=18000.0)
    scanner = OnlineScanner(spec, SmartScanScheduler(8, seed=23), 8)
    for _ in range(120):
        slot, pdws = src.poll()
        spec.ingest(pdws)
        scanner.step(pdws)
    st = scanner.stats()
    assert st["slots"] == len(scanner.actions) == len(scanner.hits)
    assert st["avg_reward"] > 0.0, "scanner should find value"
    assert st["unique_streams"] >= 1


def test_udp_source_roundtrip():
    rx = UDPSource(port=5571)
    time.sleep(0.1)
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pdw = {"toa_us": 1000.0, "freq_mhz": 9450.0, "pa_db": 12.0,
           "aoa_deg": 90.0, "pw_us": 1.5}
    sock.sendto(json.dumps(pdw).encode("utf-8"), ("127.0.0.1", 5571))
    time.sleep(0.05)
    _, items = rx.poll()
    got = []
    got.extend(items)
    rx.close()
    sock.close()
    assert len(got) == 1
    assert abs(float(got[0]["freq_mhz"]) - 9450.0) < 1e-6


def test_file_tail_jsonl_and_csv():
    tmp = Path(__import__("tempfile").mkdtemp())
    jl = tmp / "feed.jsonl"
    with open(jl, "w") as f:
        f.write(json.dumps({"toa_us": 1.0, "freq_mhz": 3000.0}) + "\n")
    src = FileTailSource(jl)
    items = src.poll()[1]
    assert len(items) == 1 and items[0]["freq_mhz"] == 3000.0
    with open(jl, "a") as f:
        f.write(json.dumps({"toa_us": 2.0, "freq_mhz": 4000.0}) + "\n")
    items = src.poll()[1]
    assert len(items) == 1 and items[0]["freq_mhz"] == 4000.0

    csvp = tmp / "sweep.csv"
    with open(csvp, "w") as f:
        f.write("toa_us,freq_mhz,pa_db,aoa_deg,pw_us\n")
        f.write("10.0,5000.0,-3.0,45.0,2.0\n")
    csv_src = FileTailSource(csvp)
    items = csv_src.poll()[1]
    assert len(items) == 1 and abs(items[0]["freq_mhz"] - 5000.0) < 1e-6


def test_scanner_with_sequential_baseline():
    env = RFEnvironment(n_bands=8, T=300, seed=31)
    src = SimulatedLiveSource(env, seed=32)
    spec = LiveSpectrum(n_bands=8, fmin_mhz=2000.0, fmax_mhz=18000.0)
    scanner = OnlineScanner(spec, SequentialSweep(8), 8)
    for _ in range(160):
        slot, pdws = src.poll()
        spec.ingest(pdws)
        scanner.step(pdws)
    st = scanner.stats()
    assert st["hit_rate"] > 0.3


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} live tests passed")
