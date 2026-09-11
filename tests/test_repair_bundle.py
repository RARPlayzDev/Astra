"""Regression tests for the teardown-repair bundle.

Covers the fixes that address the CRITICAL/MAJOR findings of the external
review:

* CRITICAL #4 / #19 - SmartScan now trains across episodes
  (``end_episode`` consolidates memory; ``reset`` warm-starts from it); the
  memory survives ``get_state``/``load_state`` and npz persistence.
* CRITICAL #2 - the DQN is modernised: dueling heads, Double-DQN targets,
  prioritised replay (vectorised, real-time safe) and Polyak soft targets.
* MAJOR #13 - the PS "reward / cost function" FoM: per-slot switching and
  dwell costs are recorded and net reward is reported (schedulers keep
  learning gross mission reward: cost-aware learning below the coverage
  KPP on the canonical protocol).
* MAJOR #19 / D3 - honest Pd: the fraction of *actual transmissions*
  intercepted is reported (distinct from "found at least once"), and the
  full-episode prediction accuracy is reported alongside the steady-state
  figure instead of being silently excluded.
* CRITICAL #6 - receiver sensitivity reported in physical units: MDS in dBm
  from the radiometer chain (kT+B+NF floor, integration gain, required SNR).
"""
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from ewsmart.config import ScenarioConfig
from ewsmart.environment import RFEnvironment
from ewsmart.receiver import ESReceiver
from ewsmart.metrics import compute_metrics, Trace, json_safe
from ewsmart.runner import run_episode, REWARD_CFG
from ewsmart.schedulers import (SequentialSweep, SmartScanScheduler)
from ewsmart.dqn import DQNAgent, PrioritizedReplayBuffer
from ewsmart.persistence import save_scheduler, load_scheduler


# ---------------------------------------------------------------------------
# SmartScan cross-episode learning (CRITICAL #4)
# ---------------------------------------------------------------------------

def test_smartscan_end_episode_builds_memory():
    s = SmartScanScheduler(8, seed=1)
    assert s.memory is None
    env = RFEnvironment(n_bands=8, T=400, seed=2)
    run_episode(env, s, seed=3)
    s.end_episode()
    assert s.memory is not None, "end_episode must consolidate memory"
    assert s.episodes_seen == 1
    assert "mu" in s.memory and "hop_succ" in s.memory


def test_smartscan_reset_warmstarts_from_memory():
    s = SmartScanScheduler(8, seed=1)
    env = RFEnvironment(n_bands=8, T=500, seed=2)
    run_episode(env, s, seed=3)
    s.end_episode()
    learned_mu = s.memory["mu"].copy()
    s.reset(horizon=500)
    assert np.array_equal(s.mu, learned_mu), \
        "reset() must warm-start band values from cross-episode memory"
    assert np.all(s.n >= 1.0)
    assert np.max(s.n) > 1.0  # visit counts must survive warm-up too


def test_smartscan_memory_persists_via_state_roundtrip():
    s = SmartScanScheduler(8, seed=1)
    env = RFEnvironment(n_bands=8, T=400, seed=2)
    run_episode(env, s, seed=3)
    s.end_episode()
    st = s.get_state()
    assert "memory" in st and st["memory"] is not None
    s2 = SmartScanScheduler(8, seed=9)
    s2.load_state(st)
    assert s2.memory is not None
    assert np.allclose(s2.memory["mu"], s.memory["mu"])
    assert list(s2.memory["logit_n"]) == list(s.memory["logit_n"])


def test_smartscan_memory_persists_via_npz(tmp_path):
    s = SmartScanScheduler(6, seed=1)
    env = RFEnvironment(n_bands=6, T=400, seed=2)
    run_episode(env, s, seed=3)
    s.end_episode()
    p = tmp_path / "smart.npz"
    save_scheduler(p, s)
    loaded = load_scheduler(p)
    assert isinstance(loaded, SmartScanScheduler)
    assert loaded.memory is not None
    assert np.allclose(loaded.memory["mu"], s.memory["mu"])
    json_safe(s.get_state())  # meta JSON must be strictly serialisable


# ---------------------------------------------------------------------------
# DQN modernisation (CRITICAL #2)
# ---------------------------------------------------------------------------

def test_dqn_defaults_use_modern_recipe():
    ag = DQNAgent(n_bands=4, state_dim=8, hidden=(8,), seed=0)
    assert ag.double is True
    assert ag.per is True
    assert isinstance(ag.buffer, PrioritizedReplayBuffer)
    # Dueling structure: trunk layers + advantage + value heads.
    assert ag.q.n_trunk == 1
    assert len(ag.q.W) == 3
    assert ag.q.W[1].shape[1] == 4 and ag.q.W[2].shape[1] == 1


def test_dqn_per_priorities_update():
    buf = PrioritizedReplayBuffer(64, 4)
    rng = np.random.default_rng(0)
    s = np.zeros(4, dtype=np.float32)
    for _ in range(40):
        buf.add(s, 1, 0.5, s, False)
    idx = np.array([5, 9], dtype=np.int64)
    buf.update_priorities(idx, np.array([0.0, 9.0]))
    assert buf._w[9] > buf._w[5]
    samp = buf.sample(8, rng, beta=1.0)
    assert len(samp) == 7  # s,a,r,s2,d,w,idx


def test_dqn_weights_roundtrip_with_dueling_heads():
    ag = DQNAgent(n_bands=4, state_dim=8, hidden=(8,), seed=0)
    w = ag.get_weights()
    assert len(w["W"]) == 3  # dueling heads included
    ag.set_weights(w)
    assert np.allclose(ag.q.W[0], w["W"][0])
    q0 = ag.q.q_values(np.zeros((1, 8), dtype=np.float32))[0]
    assert q0.shape == (4,) and np.all(np.isfinite(q0))


# ---------------------------------------------------------------------------
# Cost model (MAJOR #13) - PS "reward / cost function"
# ---------------------------------------------------------------------------

def test_cost_model_recorded_and_reported():
    env = RFEnvironment(n_bands=12, T=900, seed=5)
    tr = run_episode(env, SequentialSweep(12), seed=6)
    assert len(tr.costs) == len(tr.actions)
    m = compute_metrics(env, tr)
    gross = m["avg_reward"]
    net = m["avg_net_reward"]
    assert net <= gross + 1e-9, "net reward must not exceed gross reward"
    assert 0.0 <= m["switch_rate"] <= 1.0
    assert m["cost_per_dwell"] >= REWARD_CFG["dwell_cost"] - 1e-12
    assert m["switch_rate"] >= 0.9  # sequential sweeps switch almost always
    assert net == pytest.approx(gross - m["cost_per_dwell"], abs=1e-9)


def test_schedulers_keep_learning_gross_and_metrics_finite():
    env = RFEnvironment(n_bands=12, T=600, seed=7)
    s = SmartScanScheduler(12, seed=1)
    tr = run_episode(env, s, seed=8)
    m = compute_metrics(env, tr)
    assert np.isfinite(m["avg_reward"])
    assert np.isfinite(m["avg_net_reward"])
    assert np.mean(tr.costs) >= REWARD_CFG["dwell_cost"] - 1e-12


# ---------------------------------------------------------------------------
# Honest Pd + full-episode prediction accuracy (MAJOR #19 / PS D3)
# ---------------------------------------------------------------------------

def test_transmission_intercept_fraction_bounds():
    env = RFEnvironment(n_bands=12, T=900, seed=5)
    tr = run_episode(env, SequentialSweep(12), seed=6)
    m = compute_metrics(env, tr)
    for k in ("intercept_fraction_of_transmissions",
              "threat_intercept_fraction_of_transmissions"):
        assert 0.0 <= m[k] <= 1.0
    assert m["intercept_fraction_of_transmissions"] < 1.0


def test_transmission_intercept_fraction_handbuilt_perfect():
    # Single-emitter scenario: a receiver that dwells on the only emitter's
    # band for the whole episode and detects every transmission must achieve
    # a transmission-intercept fraction of exactly 1.0.
    env = RFEnvironment(n_bands=8, T=120, seed=3, n_stationary=1,
                        n_agile=0, n_periodic=0, n_spatial=0,
                        n_evasive=0, n_clutter=0)
    sta = [e for e in env.emitters if e.kind == "stationary"][0]
    band, eid = sta.home_band, sta.eid
    assert np.all(env.band_seq[eid] == band), "stationary emitter always on"
    tr = Trace(actions=[band] * env.T, hits=[True] * env.T,
               false_alarms=[False] * env.T, rewards=[1.0] * env.T,
               predictions=[False] * env.T,
               first_intercept={eid: 0}, ambiguous=[False] * env.T)
    m = compute_metrics(env, tr)
    assert m["intercept_fraction_of_transmissions"] == pytest.approx(1.0)


def test_full_prediction_accuracy_reported_alongside_steady_state():
    env = RFEnvironment(n_bands=12, T=900, seed=5)
    tr = run_episode(env, SmartScanScheduler(12, seed=1), seed=6)
    m = compute_metrics(env, tr)
    assert "pct_correct_predictions_full" in m
    assert 0.0 <= m["pct_correct_predictions_full"] <= 1.0
    assert np.isfinite(m["pct_correct_predictions"])


# ---------------------------------------------------------------------------
# Physical receiver sensitivity (CRITICAL #6)
# ---------------------------------------------------------------------------

def test_sensitivity_fom_reports_mds_in_dbm():
    env = RFEnvironment(n_bands=12, T=300, seed=7)
    fom = ESReceiver(env, seed=7).sensitivity_fom()
    fe = fom["frontend"]
    assert fe["processing_gain_db"] > 0.0
    thermal = fe["thermal_noise_dbm"]
    gain = fe["processing_gain_db"]
    # MDS = thermal floor + required post-detection SNR - integration gain.
    assert fom["pd50_mds_dbm"] == pytest.approx(
        thermal + fom["pd50_snr_db"] - gain, abs=0.01)
    assert fom["mds_dbm_at_pd90"] > fom["pd50_mds_dbm"]
    assert np.isfinite(fom["mds_dbm_at_pd90"])
    assert len(fom["pd_vs_input_power_dbm"]) == len(fom["pd_vs_snr"])


def test_bandwidth_model_processing_gain_is_time_bandwidth():
    import math
    cfg = ScenarioConfig(n_bands=12)
    fe = cfg.bandwidth_model()
    tb = (cfg.inst_bw_mhz * 1e6) * (cfg.dwell_time_us * 1e-6)
    assert fe["time_bandwidth_product"] == pytest.approx(tb)
    assert fe["processing_gain_db"] == pytest.approx(10 * math.log10(tb))


def test_pdws_carry_physical_pa_dbm():
    env = RFEnvironment(n_bands=8, T=100, seed=4)
    rx = ESReceiver(env, seed=5)
    found = None
    for b in range(env.n_bands):
        res = rx.dwell(b, 10)
        if res.pdws:
            found = res.pdws[0]
            break
    assert found is not None
    assert "pa_dbm" in found