import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))
"""Tests for identification, geolocation and significance tools."""
import numpy as np

from ewsmart.config import ScenarioConfig
from ewsmart.environment import RFEnvironment
from ewsmart.runner import run_episode
from ewsmart.schedulers import SequentialSweep
from ewsmart.identification import (build_default_library, fingerprint_pdws,
                                    identify, tag_environment,
                                    identification_report,
                                    streams_from_env_detections)
from ewsmart.geo import (geometric_bearing, triangulate, geolocate_streams,
                         cep_stats, simulate_bearings)
from ewsmart.sigtests import (paired_permutation_test, paired_bootstrap_ci,
                              holm_bonferroni)


def test_library_covers_sim_range():
    lib = build_default_library()
    assert len(lib) >= 8
    assert any(e.freq_range_mhz[0] <= 2400 for e in lib)
    assert any(e.freq_range_mhz[1] >= 12000 for e in lib)
    assert all(e.threat_level in ("HIGH", "MEDIUM", "LOW") for e in lib)


def test_fingerprint_and_match():
    pdws = [{"toa_us": 1000.0 * i, "freq_mhz": 9500.0, "pw_us": 3.0}
            for i in range(20)]
    fp = fingerprint_pdws(pdws)
    assert fp is not None and fp.n_pulses == len(pdws)
    entry, conf = identify(fp, build_default_library())
    assert entry is not None and entry.name == "FLAP LID-A"
    assert conf >= 0.75


def test_unknown_stream_not_forced():
    pdws = [{"toa_us": 1000.0 * i, "freq_mhz": 17500.0, "pw_us": 0.4}
            for i in range(10)]
    entry, conf = identify(fingerprint_pdws(pdws), build_default_library())
    assert entry is None and conf == 0.0


def test_environment_tagging_and_report():
    env = RFEnvironment(n_bands=12, T=600, seed=9)
    ids = tag_environment(env)
    assert len(ids) == len(env.emitters)
    tr = run_episode(env, SequentialSweep(12), seed=10)
    streams = streams_from_env_detections(env, tr)
    rep = identification_report(env, streams)
    assert rep["accuracy"] >= 0.0 and "rows" in rep and rep["n_streams"] == len(rep["rows"])
    assert all(r["threat"] in ("HIGH", "MEDIUM", "LOW", "-") for r in rep["rows"])
    assert all(("identified" in r) for r in rep["rows"])


def test_geometric_bearing_consistent():
    env = RFEnvironment(n_bands=8, T=200, seed=12)
    for e in env.emitters:
        expected = float(np.degrees(np.arctan2(e.y_km, e.x_km)) % 360.0)
        assert abs(expected - e.bearing_deg) < 1e-6


def test_triangulation_accuracy():
    rng = np.random.default_rng(0)
    true_xy = (12.0, 18.0)
    rxs = ((0.0, 0.0), (30.0, 2.0), (5.0, 35.0))
    lines = simulate_bearings(true_xy, rxs, sigma_deg=2.0, rng=rng)
    x, y, _ = triangulate(lines)
    err = float(np.hypot(x - true_xy[0], y - true_xy[1]))
    assert err < 1.5, f"triangulation error {err:.2f} km too large"


def test_geolocate_streams_filters_min():
    rng = np.random.default_rng(1)
    rxs = ((0.0, 0.0), (30.0, 0.0), (10.0, 30.0))
    sb = {"streamA": [(rxs[0], geometric_bearing(rxs[0], (5.0, 5.0)))],
          "streamB": simulate_bearings((10.0, 10.0), rxs, 1.0, rng)}
    out = geolocate_streams(sb, min_receivers=2)
    assert "streamA" not in out                     # single line filtered out
    est = out["streamB"]
    err = float(np.hypot(est["x"] - 10.0, est["y"] - 10.0))
    assert err < 1.5


def test_cep_stats():
    st = cep_stats([1.0, 2.0, 3.0, 4.0, 100.0])
    assert st["n"] == 5
    assert st["cep50"] == 3.0
    assert st["mean"] == 22.0


def test_permutation_test_separates():
    rng = np.random.default_rng(2)
    a = rng.normal(2.0, 1.0, 60)
    b = rng.normal(0.2, 1.0, 60)
    p_ab = paired_permutation_test(a, b, n_permutations=5000, seed=3,
                                   alternative="greater")
    p_aa = paired_permutation_test(a, a.copy(), n_permutations=5000, seed=3,
                                   alternative="greater")
    assert p_ab < 0.01
    assert p_aa > 0.25


def test_bootstrap_ci_and_holm():
    rng = np.random.default_rng(4)
    a = rng.normal(3.0, 1.0, 50)
    b = rng.normal(0.0, 1.0, 50)
    lo, hi = paired_bootstrap_ci(a, b, seed=5)
    assert lo > 0.05 and hi > lo
    decisions = holm_bonferroni([0.001, 0.002, 0.4], alpha=0.05)
    assert tuple(decisions) == (True, True, False)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
