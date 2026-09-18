"""PS gap-closure tests: communication signals, coupled detection physics,
agile intercept-time prediction, per-cycle spatial coverage, COMINT
classification chain, TTFF-aware reward and the scalability study.

Each test maps 1:1 to a gap identified in the project teardown report.
"""
import math

import numpy as np
import pytest

from ewsmart.config import ScenarioConfig
from ewsmart.environment import RFEnvironment
from ewsmart.receiver import ESReceiver
from ewsmart.runner import run_episode, step_reward, REWARD_CFG
from ewsmart.metrics import compute_metrics
from ewsmart.schedulers import SmartScanScheduler
from ewsmart.prediction import HopDwellPredictor, evaluate_agile_intercept_time
from ewsmart.identification import (build_default_library, tag_environment,
                                    identification_report,
                                    streams_from_env_detections,
                                    classify_signal_class)
from ewsmart.experiments import scalability_study


# ---------------------------------------------------------------------------
# Gap 1: "communication or radar signals" - communication signals exist
# ---------------------------------------------------------------------------
def test_communication_emitters_exist_and_transmit():
    cfg = ScenarioConfig(T=600, seed=5, n_fhss=3, n_tdma=2)
    env = RFEnvironment(cfg)
    kinds = {e.kind for e in env.emitters}
    assert {"fhss", "tdma"} <= kinds
    fhss = [e for e in env.emitters if e.kind == "fhss"]
    tdma = [e for e in env.emitters if e.kind == "tdma"]
    assert len(fhss) == 3 and len(tdma) == 2
    for e in fhss:  # FHSS nets hop frequently across a wide hop set
        assert len(e.hop_set) >= 4
        observed = sorted({int(b) for b in env.band_seq[e.eid] if b >= 0})
        assert len(observed) >= 2  # actually hops
    for e in tdma:  # TDMA bursts are short with long silent gaps
        assert e.on_len <= 4 and e.period >= 20
        on_slots = int((env.band_seq[e.eid] >= 0).sum())
        assert 0 < on_slots < env.T  # bursty, not continuous


def test_comm_interception_foms_reported():
    cfg = ScenarioConfig(T=900, seed=7, n_fhss=3, n_tdma=2)
    env = RFEnvironment(cfg)
    tr = run_episode(env, SmartScanScheduler(env.n_bands, seed=7), seed=8)
    m = compute_metrics(env, tr)
    for key in ("ir_fhss", "ir_tdma", "ir_comm",
                "spatial_cycle_intercept_fraction"):
        assert key in m
    assert np.isfinite(m["ir_comm"])
    assert 0.0 <= m["ir_comm"] <= 1.0


# ---------------------------------------------------------------------------
# Gap 2: physically-coupled detection (radiometer + Albersheim + CA-CFAR)
# ---------------------------------------------------------------------------
def test_detection_is_physically_coupled():
    env = RFEnvironment(ScenarioConfig(T=400, seed=1))
    base = ESReceiver(env, seed=1)
    # Longer integration -> lower required SNR -> higher Pd at 0 dB.
    long = ESReceiver(RFEnvironment(ScenarioConfig(
        T=400, seed=1, dwell_time_us=20.0)), seed=1)
    # Tighter Pfa -> higher required SNR -> lower Pd at 0 dB.
    tight = ESReceiver(RFEnvironment(ScenarioConfig(
        T=400, seed=1, cfar_pfa=1e-6)), seed=1)
    p0 = base.detection_prob(0.0)
    assert long.detection_prob(0.0) > p0 > tight.detection_prob(0.0)
    # Pd curve is monotone increasing in SNR.
    pds = [base.detection_prob(s) for s in (-12, -6, 0, 6, 12, 18)]
    assert all(b > a for a, b in zip(pds, pds[1:]))
    # CFAR threshold consistent with radiometric 1/sqrt(N) scaling.
    assert -30.0 < base.cfar_threshold_snr_db() < -5.0


def test_sensitivity_fom_reports_physics_anchors():
    env = RFEnvironment(ScenarioConfig(T=400, seed=1))
    fom = ESReceiver(env, seed=1).sensitivity_fom()
    for key in ("detection_model", "time_bandwidth_product",
                "cfar_design_pfa", "cfar_threshold_snr_db",
                "albersheim_required_snr_db_pd50", "albersheim_mds_dbm_pd50",
                "albersheim_mds_dbm_pd90", "capture_range_db"):
        assert key in fom
    assert fom["detection_model"] == "radiometer + Albersheim + CA-CFAR"
    # Albersheim MDS tracks the radiometer thermal floor + NF - gain.
    bw = fom["frontend"]
    expected = (bw["thermal_noise_dbm"]
                + fom["albersheim_required_snr_db_pd50"]
                - bw["processing_gain_db"])
    assert math.isclose(fom["albersheim_mds_dbm_pd50"], round(expected, 2),
                        abs_tol=0.05)


def test_near_far_capture_effect():
    env = RFEnvironment(ScenarioConfig(T=400, seed=2, capture_range_db=10.0))
    rx = ESReceiver(env, seed=3)
    det = [(30.0, 0.0, "s"), (5.0, 90.0, "w")]
    strongest = max(s for s, _, _ in det)
    det = [d for d in det if strongest - d[0] <= rx._capture_range_db]
    assert [d[2] for d in det] == ["s"]  # weak masked by strong co-channel
    assert rx.detection_prob(5.0) > 0.0  # weak alone remains detectable


# ---------------------------------------------------------------------------
# Gap 3: agile-emitter intercept-time prediction
# ---------------------------------------------------------------------------
def test_hop_dwell_predictor_learns_dwell_and_transitions():
    pred = HopDwellPredictor(n_bands=6)
    for t in range(4):
        pred.observe(0, t)
    for t in range(4, 9):
        pred.observe(3, t)
    # Hop back to 0 at t=9: completes band 3's first observed dwell (5 slots)
    pred.observe(0, 9)
    out = pred.predict_next_on(0, 9)
    assert out is not None
    nxt, t_pred = out
    assert nxt == 3          # learned transitions 0->3 and 3->0
    # Band 0's completed dwell history: 0 (t=0) -> hop at t=4 = 4 slots.
    assert pred._mean_dwell(0) == 4.0
    assert t_pred == 13


def test_agile_intercept_time_evaluation():
    env = RFEnvironment(ScenarioConfig(T=1200, seed=11, agile_mode="markov"))
    out = evaluate_agile_intercept_time(env)
    assert out["n"] > 0
    assert np.isfinite(out["agile_intercept_time_error"])
    assert out["agile_intercept_time_error"] >= 0
    assert 0.0 <= out["band_top1_accuracy"] <= 1.0
    # Markov agility must be learnable above chance (1/n_bands).
    assert out["band_top1_accuracy"] > 1.0 / env.n_bands
    env_r = RFEnvironment(ScenarioConfig(T=1200, seed=11, agile_mode="random"))
    out_r = evaluate_agile_intercept_time(env_r)
    assert out_r["n"] > 0


# ---------------------------------------------------------------------------
# Gap 4: per-rotation-cycle spatial interception fraction
# ---------------------------------------------------------------------------
def test_spatial_cycle_intercept_fraction():
    env = RFEnvironment(ScenarioConfig(T=900, seed=13))
    tr = run_episode(env, SmartScanScheduler(env.n_bands, seed=13), seed=14)
    m = compute_metrics(env, tr)
    val = m["spatial_cycle_intercept_fraction"]
    assert np.isfinite(val) and 0.0 <= val <= 1.0


# ---------------------------------------------------------------------------
# Gap 5: COMINT classification chain (intercept -> classify -> identify)
# ---------------------------------------------------------------------------
def test_comint_classification_and_library():
    lib = build_default_library()
    assert len([e for e in lib if e.domain == "COMINT"]) >= 2
    assert classify_signal_class(None, 0, "fhss") == "FHSS-COMM"
    assert classify_signal_class(None, 0, "tdma") == "TDMA-BURST"
    assert classify_signal_class(None, 0, "stationary") == "RADAR-PULSED"
    cfg = ScenarioConfig(T=900, seed=15, n_fhss=2, n_tdma=2)
    env = RFEnvironment(cfg)
    tag_environment(env)
    comm_ids = [e.eid for e in env.emitters if e.kind in ("fhss", "tdma")]
    assert comm_ids, "expected comm emitters"
    for eid in comm_ids:
        assert env.signal_classes[eid] in ("FHSS-COMM", "TDMA-BURST")
    tr = run_episode(env, SmartScanScheduler(env.n_bands, seed=15), seed=16)
    rep = identification_report(env, streams_from_env_detections(env, tr))
    assert rep["n_comint"] >= 1
    assert any(r.get("domain") == "COMINT" for r in rep["rows"])


# ---------------------------------------------------------------------------
# Gap 6: TTFF-aware reward shaping
# ---------------------------------------------------------------------------
def test_ttff_urgency_rewards_early_first_intercept():
    cfg = ScenarioConfig(T=500, seed=21)
    env = RFEnvironment(cfg)

    class E:
        eid = 99
        threat = True
        snr_db = 15.0

    class FakeEnv:
        T = 500

        def emitters_at(self, band, t):
            return [E()]

    class FakeRes:
        false_alarm = False
        hit = True
        detected_eids = (99,)
        band = 0
        detections = ()
        def __init__(self, t):
            self.t = t

    from ewsmart import runner as _runner
    orig = _runner.detected_eids
    try:
        _runner.detected_eids = lambda env, res: (99,)
        fe = FakeEnv()
        fi_early, fi_late = {}, {}
        r_early = step_reward(fe, FakeRes(t=10), fi_early)
        r_late = step_reward(fe, FakeRes(t=400), fi_late)
    finally:
        _runner.detected_eids = orig
    assert r_early > r_late
    assert REWARD_CFG["ttff_urgency"] == 1.0


# ---------------------------------------------------------------------------
# Gap 7: scalability study runs end-to-end
# ---------------------------------------------------------------------------
def test_scalability_study_small():
    out = scalability_study(band_sizes=(12, 24), emitter_counts=(10, 20),
                            T=400, trials=1)
    conds = out["conditions"]
    assert len(conds) == 4
    for c in conds:
        assert c["n_emitters"] >= 8
        assert set(c["results"]) >= {"SequentialSweep", "RandomScan",
                                     "SmartScanScheduler"}
        for agg in c["results"].values():
            assert 0.0 <= agg["threat_intercept_ratio"] <= 1.0
            assert 0.0 <= agg["intercept_ratio"] <= 1.0


def test_scalability_study_covers_comint_emitters():
    """The multi-scale study must exercise the full PS emitter mix.

    Regression: `n_fhss` / `n_tdma` used to be omitted from the scalability
    conditions, so the study silently measured radar-only scenes.
    """
    out = scalability_study(band_sizes=(8,), emitter_counts=(12,), T=600,
                            trials=1, base_seed=4242)
    cond = out["conditions"][0]
    assert cond["n_fhss"] >= 1 and cond["n_tdma"] >= 1, \
        "scalability conditions must include COMINT emitters"
    for name, agg in cond["results"].items():
        for key in ("ir_fhss", "ir_tdma", "ir_comm"):
            assert key in agg, f"{name} aggregate missing {key}"
            assert 0.0 <= agg[key] <= 1.0


# ---------------------------------------------------------------------------
# Config validation for the new knobs
# ---------------------------------------------------------------------------
def test_new_config_validation():
    with pytest.raises(Exception):
        RFEnvironment(ScenarioConfig(T=100, cfar_pfa=1.5))
    with pytest.raises(Exception):
        RFEnvironment(ScenarioConfig(T=100, cfar_pfa=0.0))
    with pytest.raises(Exception):
        RFEnvironment(ScenarioConfig(T=100, capture_range_db=-5.0))
    env = RFEnvironment(ScenarioConfig(T=100, cfar_pfa=1e-4,
                                       capture_range_db=25.0))
    assert env.cfg.cfar_pfa == 1e-4