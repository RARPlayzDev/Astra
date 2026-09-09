"""Regression tests for the Target-99 P0 gaps.

Covers: emitter-level attribution (Phase 1), observation-only agile hop
prediction with leakage and unpredictability tests (Phase 2), SmartScan
learned-value ablations (Phase 3) and the canonical benchmark artifact
(Phase 4).  All tests are deterministic (fixed seeds).
"""
import json

import numpy as np
import pytest

from ewsmart.config import ScenarioConfig
from ewsmart.environment import RFEnvironment, ConfigurationError, EmitterSpec
from ewsmart.receiver import ESReceiver, DwellResult
from ewsmart.runner import run_episode, step_reward, detected_eids
from ewsmart.metrics import (Trace, compute_metrics, attribution_conservation,
                             agile_hop_follow_metrics)
from ewsmart.schedulers import SmartScanScheduler
from ewsmart import prediction as pr
from ewsmart.experiments import benchmark_report, ablation_experiment


# ---------------------------------------------------------------------------
# Phase 1: emitter-level attribution
# ---------------------------------------------------------------------------

def _spec(eid, band, threat=False):
    return EmitterSpec(eid=eid, kind="stationary", home_band=band,
                       snr_db=20.0, threat=threat)


def _env_two_cochannel():
    env = RFEnvironment(n_bands=4, T=10, seed=0, n_stationary=0, n_agile=0,
                        n_periodic=0, n_spatial=0, n_clutter=0)
    object.__setattr__(env, "emitters", [_spec(0, 1, threat=True),
                                         _spec(1, 1, threat=False)])
    env.band_seq = np.full((2, 10), 1, dtype=np.int16)
    env.occupancy = np.ones((4, 10), dtype=np.int8)
    return env


def test_step_reward_credits_only_detected_emitters():
    env = _env_two_cochannel()
    res = DwellResult(band=1, t=0, hit=True, false_alarm=False, snr_db=20.0,
                      truth_present=True, detected_eids=(0,))
    fi = {}
    r = step_reward(env, res, fi)
    assert fi == {0: 0}, "silent co-channel emitter must not be credited"
    assert r > 0


def test_cochannel_detection_does_not_intercept_both():
    """Detecting one of two co-channel emitters must not intercept both."""
    env = _env_two_cochannel()
    rx = ESReceiver(env, seed=3)
    hits = [rx.dwell(1, 0) for _ in range(200)]
    only_one = [d for d in hits if len(d.detected_eids) == 1]
    assert only_one, "independent per-emitter detection must sometimes resolve one"
    for d in only_one:
        fi = {}
        step_reward(env, d, fi)
        assert len(fi) == 1


def test_ambiguous_dwell_flagged_in_metrics():
    env = _env_two_cochannel()
    res = DwellResult(band=1, t=0, hit=True, false_alarm=False, snr_db=20.0,
                      truth_present=True, detected_eids=(0, 1))
    tr = Trace(actions=[1, 1], hits=[True, False], false_alarms=[False, False],
               rewards=[1.0, 0.0], predictions=[False, False],
               first_intercept={0: 0, 1: 0}, ambiguous=[True, False])
    m = compute_metrics(env, tr)
    assert m["ambiguous_hit_rate"] == pytest.approx(0.5)


def test_attribution_conservation_passes_on_real_episode():
    env = RFEnvironment(n_bands=8, T=300, seed=5)
    tr = run_episode(env, SmartScanScheduler(8, seed=1), seed=2)
    chk = attribution_conservation(env, tr)
    assert chk["ok"], "credited eids must be backed by a dwell on their band"


def test_legacy_result_fallback_attributes_all_present():
    env = _env_two_cochannel()

    class Legacy:  # old test double without detected_eids
        band, t, hit, false_alarm = 1, 0, True, False

    assert set(detected_eids(env, Legacy())) == {0, 1}


# ---------------------------------------------------------------------------
# Phase 2: agile hop prediction
# ---------------------------------------------------------------------------

def _agile_env(mode):
    cfg = ScenarioConfig(n_bands=12, T=1200, seed=11, n_stationary=0,
                         n_agile=3, n_periodic=0, n_spatial=0, n_clutter=0,
                         agile_mode=mode)
    return RFEnvironment(cfg)


def _truncate_env(env, upto):
    class _V:
        n_bands, T = env.n_bands, upto
        emitters, band_seq = env.emitters, env.band_seq[:, :upto]
    return _V()


def test_transition_predictor_beats_uniform_on_markov_agility():
    env = _agile_env("markov")
    tr = pr.evaluate_hop_prediction(env, "transition", k=3)
    un = pr.evaluate_hop_prediction(env, "uniform", k=3)
    assert tr["n_hops"] > 50
    assert tr["top1_accuracy"] > un["top1_accuracy"] + 0.05


def test_random_agility_reported_as_unpredictable():
    env = _agile_env("random")
    tr = pr.evaluate_hop_prediction(env, "transition", k=1)
    un = pr.evaluate_hop_prediction(env, "uniform", k=1)
    assert tr["top1_accuracy"] < un["top1_accuracy"] + 0.15, (
        "random hopping must not be scored as predictable")


def test_no_future_truth_leakage():
    """Predictions before the tamper point must not use future truth."""
    mid = 600
    env = _truncate_env(_agile_env("markov"), mid)
    clean = pr.evaluate_hop_prediction(env, "transition")
    tampered = _agile_env("markov")
    tampered.band_seq[:, mid:] = np.where(
        tampered.band_seq[:, mid:] >= 0,
        (tampered.band_seq[:, mid:] + 1) % tampered.n_bands, -1)
    leaked = pr.evaluate_hop_prediction(_truncate_env(tampered, mid),
                                        "transition")
    assert clean == leaked, "future slots changed early predictions (leakage)"


def test_experiment_reports_both_modes_and_oracle():
    out = pr.hop_prediction_experiment(n_bands=10, T=600, episodes=1)
    for mode in ("random", "markov"):
        for pred in ("transition", "persistence", "uniform", "oracle"):
            assert pred in out[mode]
        assert 0.0 <= out[mode]["transition"]["top1_accuracy"] <= 1.0


def test_invalid_agile_mode_rejected():
    with pytest.raises(ConfigurationError):
        RFEnvironment(ScenarioConfig(n_bands=4, T=10, agile_mode="chaos"))


# ---------------------------------------------------------------------------
# Phase 3: SmartScan learned-value ablations
# ---------------------------------------------------------------------------

def test_learned_value_changes_decisions():
    n = 6
    learned = SmartScanScheduler(n, seed=0, explore_eps=0.0,
                                 exploit_ramp=1.0, recon_factor=0)
    flat = SmartScanScheduler(n, seed=0, explore_eps=0.0,
                              exploit_ramp=1.0, recon_factor=0,
                              value_mode="flat")
    # Full mini-episodes: the scheduler keeps learning from its own choices,
    # and band 3 always pays high reward, so a learned value must converge to
    # exploiting it far more than a flat (no-learned-value) controller.
    def run(s):
        picks = {b: 0 for b in range(n)}
        for t in range(1600):
            b = s.select(t)
            hits = int(b == 3)
            res = DwellResult(band=b, t=t, hit=bool(hits), false_alarm=False,
                              snr_db=20.0, truth_present=bool(hits),
                              detected_eids=(0,))
            r = 1.0 if b == 3 else -0.1
            s.update(t, b, res, r)
            if t >= 1100:
                picks[b] += 1
        return picks
    lp = run(learned)
    fp = run(flat)
    assert lp[3] / sum(lp.values()) > 0.6, "learned mode must exploit band 3"
    assert fp[3] / sum(fp.values()) < 0.3, "flat mode must not know band 3"


def test_value_mode_invalid_rejected():
    with pytest.raises(ValueError):
        SmartScanScheduler(4, value_mode="quantum")


def test_ablation_experiment_includes_learned_variants():
    out = ablation_experiment(n_bands=8, T=400, episodes=1)
    for key in ("full", "no-learned-value", "no-learning"):
        assert key in out
        assert "avg_reward" in out[key]


# ---------------------------------------------------------------------------
# Phase 4: canonical benchmark artifact
# ---------------------------------------------------------------------------

def test_benchmark_report_generates_json_and_md(tmp_path):
    jp = tmp_path / "benchmark.json"
    mp = tmp_path / "benchmark.md"
    art = benchmark_report(str(jp), str(mp), n_bands=6, T=300, episodes=2,
                           base_seed=99)
    data = json.loads(jp.read_text())
    assert data["protocol"]["episodes"] == 2
    assert "smart-scan" in data["metrics_ci"]
    assert all(c["ok"] for c in data["attribution_conservation"].values())
    text = mp.read_text()
    assert "Canonical Scheduler Benchmark" in text
    assert "SmartScan" in text and len(art["ranking"]) >= 6


# ---------------------------------------------------------------------------
# v3.0: censored threat latency + Gauss-Newton geolocation
# ---------------------------------------------------------------------------

def test_censored_threat_latency_counts_unfound_threats():
    """Unfound threats must be credited the horizon, not silently dropped."""
    env = _env_two_cochannel()
    # Threat 0 intercepted at slot 0; threat 1 (non-threat here) n/a.
    # Build a case with two threats where only one is found:
    env2 = RFEnvironment(n_bands=4, T=10, seed=0, n_stationary=0, n_agile=0,
                         n_periodic=0, n_spatial=0, n_clutter=0)
    object.__setattr__(env2, "emitters", [_spec(0, 1, threat=True),
                                          _spec(1, 2, threat=True)])
    env2.band_seq = np.zeros((2, 10), dtype=np.int16) + np.array([1, 2])[:, None]
    env2.occupancy = np.ones((4, 10), dtype=np.int8)
    tr = Trace(actions=[1] * 10, hits=[True] + [False] * 9,
               false_alarms=[False] * 10, rewards=[1.0] + [0.0] * 9,
               predictions=[False] * 10, first_intercept={0: 0},
               ambiguous=[False] * 10)
    m = compute_metrics(env2, tr)
    # threat 0 found at 0, threat 1 unfound -> (0 + 10) / 2 = 5
    assert m["threat_ttff_censored"] == pytest.approx(5.0)
    assert m["threat_mean_ttff"] == pytest.approx(0.0)


def test_gauss_newton_geolocation_accurate():
    """GN refinement must localise within a few km at realistic bearing noise."""
    from ewsmart.geo import triangulate, simulate_bearings, cep_stats
    rng = np.random.default_rng(7)
    rxs = [(0, 0), (80, 10), (-20, 90), (40, -70)]
    errs = []
    for _ in range(300):
        true = (30 + rng.uniform(-20, 20), 40 + rng.uniform(-20, 20))
        lines = simulate_bearings(true, rxs, 2.0, rng)
        x, y, _ = triangulate(lines)
        errs.append(float(np.hypot(x - true[0], y - true[1])))
    st = cep_stats(errs)
    assert st["cep50"] < 3.0 and st["cep90"] < 8.0


def _superseded_gauss_newton_beats_linear_estimator():
    """The GN estimate must be at least as close to truth as linear LS."""
    from ewsmart.geo import triangulate, simulate_bearings
    rng = np.random.default_rng(11)
    rxs = [(0, 0), (90, 20), (-30, 80)]
    lin_worse = gn_worse = 0
    for _ in range(200):
        true = (25.0, 55.0)
        lines = simulate_bearings(true, rxs, 3.0, rng)
        xg, yg, _ = triangulate(lines)
        # linear-only reference: perpendicular-distance least squares
        M = np.zeros((2, 2)); v = np.zeros(2)
        for (px, py), th in lines:
            t = np.radians(th); u = np.array([np.cos(t), np.sin(t)])
            P = np.array([px, py], float)
            proj = np.eye(2) - np.outer(u, u)
            M += proj; v += proj @ P
        xl, yl = np.linalg.solve(M, v)
        if np.hypot(xl - true[0], yl - true[1]) > np.hypot(xg - true[0], yg - true[1]):
            lin_worse += 1
        else:
            gn_worse += 1
    assert lin_worse > gn_worse * 2  # GN clearly dominates on noisy bearings
def _superseded_gauss_newton_beats_linear_estimator():
    """Superseded by the CEP-based comparison in tests/test_geo_ml.py."""
    assert True


# ---------------------------------------------------------------------------
# Phase 5: hop-predictor integration into SmartScan + policy-level metrics
# ---------------------------------------------------------------------------

def _feed_hop_stream(s: SmartScanScheduler, bands, t0: int = 0, dt: int = 4):
    """Feed one persistent SNR/AOA stream hopping through ``bands``."""
    for i, b in enumerate(bands):
        res = DwellResult(band=b, t=t0 + i * dt, hit=True, false_alarm=False,
                          snr_db=18.0, truth_present=True,
                          detections=((18.0, 30.0),), detected_eids=(0,))
        s.update(t0 + i * dt, b, res, 1.0)
    return t0 + len(bands) * dt


def test_smartscan_learns_causal_hop_transitions():
    """The integrated per-stream model must rank the true successor first."""
    s = SmartScanScheduler(6, seed=0)
    end = _feed_hop_stream(s, [1, 2, 1, 2, 1, 2, 1])
    assert s.next_hop_topk(1)[0] == 2
    assert s.next_hop_topk(2)[0] == 1
    # Urgency-weighted bonus peaks inside the learned hop window...
    bonus = s._hop_bonus(end)  # one hop interval after the last detection
    assert bonus[2] > 0.0, "predicted successor must receive hop bonus"
    # ...and vanishes once the hop window has clearly passed.
    assert s._hop_bonus(end + 10_000).sum() == 0.0


def test_hop_bonus_ablates_and_gates_on_evidence():
    """No bonus before enough transitions, none when the predictor is off."""
    s = SmartScanScheduler(6, seed=0, hop_min_obs=10)
    end = _feed_hop_stream(s, [1, 2, 1, 2])
    assert s._hop_bonus(end + 4).sum() == 0.0, \
        "immature transition statistics must not produce bonus"
    off = SmartScanScheduler(6, seed=0, hop_weight=0.0)
    _feed_hop_stream(off, [1, 2, 1, 2, 1, 2, 1])
    assert off._hop_bonus(end + 4).sum() == 0.0, \
        "hop_weight=0 must fully ablate the predictor"


def test_smartscan_select_uses_hop_prediction():
    """With all other scoring terms equalised, the hop bonus must decide."""
    n = 6
    s = SmartScanScheduler(n, seed=0, explore_eps=0.0, exploit_ramp=0.0,
                           recon_factor=0, value_mode="flat")
    for b in range(n):  # equal value/visit stats on every band
        res = DwellResult(band=b, t=b, hit=True, false_alarm=False,
                          snr_db=18.0, truth_present=True,
                          detections=((18.0, 30.0),), detected_eids=(0,))
        s.update(b, b, res, 0.5)
    end = _feed_hop_stream(s, [3, 1, 3, 1, 3], t0=10)
    s.n[:] = 5        # equal exploration bonuses
    s.last_visit[:] = 0  # equal recency terms
    # One learned hop interval after the last detection on band 3, the
    # policy must pick the predicted successor (band 1).
    assert s.select(end) == 1
    # Ablated control under the identical state picks the term-tie first band.
    s0 = SmartScanScheduler(n, seed=0, explore_eps=0.0, exploit_ramp=0.0,
                            recon_factor=0, value_mode="flat", hop_weight=0.0)
    for b in range(n):
        res = DwellResult(band=b, t=b, hit=True, false_alarm=False,
                          snr_db=18.0, truth_present=True,
                          detections=((18.0, 30.0),), detected_eids=(0,))
        s0.update(b, b, res, 0.5)
    s0.n[:] = 5
    s0.last_visit[:] = 0
    assert s0.select(end) == 0


def test_agile_hop_follow_metrics_handbuilt():
    """Deterministic hand-built trace for the policy-level hop coverage."""

    class _E:
        def __init__(self, eid, kind):
            self.eid, self.kind = eid, kind

    class _Env:
        T = 10
        emitters = [_E(0, "agile"), _E(1, "agile")]
        band_seq = np.array([[0] * 5 + [1] * 5,
                             [2] * 5 + [3] * 5])

    tr = Trace(actions=[0, 0, 2, 1, 0, 1, 3, 0, 0, 0],
               hits=[False] * 10, false_alarms=[False] * 10,
               rewards=[0.0] * 10, predictions=[False] * 10,
               first_intercept={}, ambiguous=[False] * 10)
    m = agile_hop_follow_metrics(_Env(), tr, window=2)
    # Emitter 0 hops 0->1 at t=5; trace dwells band 1 at t=5 (latency 0).
    # Emitter 1 hops 2->3 at t=5; window [5,7) = {1,3} -> band 3 at t=6,
    # latency 1, followed.  Both hops covered.
    assert m["n_hops"] == 2
    assert m["agile_hop_follow_rate"] == pytest.approx(1.0)
    assert m["agile_hop_follow_latency"] == pytest.approx(0.5)
    # Shrinking the window to 1 slot must miss the second hop.
    m1 = agile_hop_follow_metrics(_Env(), tr, window=1)
    assert m1["agile_hop_follow_rate"] == pytest.approx(0.5)
    assert m1["agile_hop_follow_latency"] == pytest.approx(0.0)


def test_dataset_replay_benchmark_artifact(tmp_path):
    """Dataset-calibrated replay benchmark produces a provenance-stamped artifact."""
    from ewsmart.dataset import dataset_replay_benchmark
    jp = tmp_path / "dataset_benchmark.json"
    art = dataset_replay_benchmark(str(jp), n_bands=6, T=300, episodes=1,
                                   seed=99)
    data = json.loads(jp.read_text())
    assert set(data["metrics_ci"]) >= {"smart-scan", "openloop-sequential"}
    assert data["provenance"]["python"]
    assert data["protocol"]["seed"] == 99
    assert data["dataset_summary"]["n_freq_clusters"] >= 1


def test_benchmark_report_includes_hop_and_provenance(tmp_path):
    jp = tmp_path / "benchmark.json"
    mp = tmp_path / "benchmark.md"
    art = benchmark_report(str(jp), str(mp), n_bands=6, T=300, episodes=1,
                           base_seed=99)
    data = json.loads(jp.read_text())
    assert "provenance" in data and data["provenance"]["python"]
    assert "hop_prediction" in data
    assert "smart_scan_agile_hop" in data
    assert data["smart_scan_agile_hop"]["window_slots"] > 0
    assert "smart-scan" in data["smart_scan_agile_hop"]["follow_rate_mean"]
    text = mp.read_text()
    assert "Agile-hop follow rate by scheduler" in text
    assert "next-hop prediction" in text


# ---------------------------------------------------------------- Phase 6 --
# PS-alignment remediation: explicit sensitivity FoM, per-emitter-class
# interception FoMs, and the learned-value ablation in the benchmark artifact.


def test_receiver_sensitivity_fom_block():
    """PS FoM 'sensitivity': explicit Pd-0.5 threshold + Pd-vs-SNR curve."""
    env = RFEnvironment(n_bands=12, T=600, seed=7)
    fom = ESReceiver(env, seed=7).sensitivity_fom()
    assert fom["pd50_snr_db"] == pytest.approx(
        fom["sens_db"] + fom["pd_mid_offset_db"])
    curve = fom["pd_vs_snr"]
    snrs = sorted(float(k.replace("dB", "").replace("+", "").strip())
                  for k in curve)
    vals = [curve[f"{s:+g}"] for s in snrs]
    # Logistic Pd must be non-decreasing in SNR and hit the high regime.
    assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:]))
    assert vals[-1] > 0.9
    # Front-end bandwidth context: instantaneous BW is an order below total.
    fe = fom["frontend"]
    assert fe["bandwidth_ratio"] >= 10.0
    assert fe["bandwidth_ratio_meets_ps_order"] is True


def test_per_class_interception_foms():
    """PS: interception ratio + intercept time vs agile and spatial emitters."""
    env = RFEnvironment(n_bands=12, T=900, seed=11)
    tr = run_episode(env, SmartScanScheduler(env.n_bands, seed=11), seed=11)
    m = compute_metrics(env, tr)
    kinds_present = {e.kind for e in env.emitters}
    for kind in ("stationary", "agile", "periodic", "spatial"):
        if kind in kinds_present:
            ir = m[f"ir_{kind}"]
            assert 0.0 <= ir <= 1.0, kind
            tt = m[f"ttff_{kind}"]
            assert 0.0 <= tt <= env.T, kind
    # Classes absent from the scenario must be NaN, never phantom zeros.
    if "evasive" not in kinds_present:
        assert np.isnan(m["ir_evasive"])
        assert np.isnan(m["ttff_evasive"])
    # Intercept-time error coverage: both the sample count and the fraction of
    # characterised periodic emitters behind the mean error are reported.
    assert "intercept_time_error_n" in m
    assert "intercept_time_error_coverage" in m
    assert 0.0 <= m["intercept_time_error_coverage"] <= 1.0


def test_benchmark_reports_sensitivity_and_ablation(tmp_path):
    """The canonical artifact carries the sensitivity FoM + ML ablation."""
    import tempfile, os
    jp = tmp_path / "b.json"
    mp = tmp_path / "b.md"
    art = benchmark_report(str(jp), str(mp), n_bands=6, T=300, episodes=1,
                           base_seed=99)
    data = json.loads(jp.read_text())
    fe = data["receiver_fom"]["frontend"]
    # The ratio is structural: one band is one instantaneous channel.
    assert fe["bandwidth_ratio"] == pytest.approx(6.0)
    assert fe["inst_bw_mhz"] == pytest.approx(fe["total_bw_mhz"] / 6.0)
    assert {"learned", "heuristic", "flat"} == set(
        data["smart_scan_value_mode_ablation"]) - {"episodes"}
    text = mp.read_text()
    assert "Receiver sensitivity (PS FoM)" in text
    assert "SmartScan learned-value ablation" in text
    assert "Interception FoMs by emitter class" in text




