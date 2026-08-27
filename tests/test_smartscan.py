import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))
import numpy as np

from ewsmart.environment import RFEnvironment
from ewsmart.receiver import ESReceiver
from ewsmart import periodic
from ewsmart.metrics import compute_metrics, Trace
from ewsmart.runner import run_episode, REWARD_CFG, make_schedulers, evaluate
from ewsmart.schedulers import (SequentialSweep, SmartScanScheduler,
                                LinearQLearning)


def test_truth_matrix_consistent():
    env = RFEnvironment(n_bands=16, T=500, seed=1)
    for _ in range(200):
        t = int(env.rng.integers(env.T))
        b = int(env.rng.integers(env.n_bands))
        assert env.present(b, t) == bool((env.band_seq[:, t] == b).any())
        for e in env.emitters_at(b, t):
            assert env.band_seq[e.eid, t] == b


def test_periodic_emitter_rising_edges():
    env = RFEnvironment(n_bands=8, T=1000, seed=2)
    per = [e for e in env.emitters if e.kind == "periodic"][0]
    row = env.band_seq[per.eid]
    on = (row >= 0).astype(int)
    starts = [t for t in range(1, env.T) if on[t] == 1 and on[t - 1] == 0]
    gaps = np.diff(starts)
    assert np.all(gaps == per.period) or np.std(gaps.astype(float)) <= 1.5


def test_period_estimator_recovers_period():
    rng = np.random.default_rng(3)
    for _ in range(5):
        p_true = int(rng.integers(20, 200))
        hits = sorted(int(t) for t in
                      np.arange(10, 10 + 8 * p_true, p_true) +
                      rng.normal(0, 0.4, 8))
        est = periodic.best_period(hits)
        assert est is not None
        assert abs(est["period"] - p_true) <= max(2, p_true * 0.05)


def test_receiver_detection_and_fa_bounds():
    env = RFEnvironment(n_bands=8, T=400, seed=4)
    rx = ESReceiver(env, seed=7)
    total_hits = sum(rx.dwell(int(env.rng.integers(8)),
                              int(env.rng.integers(400))).hit
                     for _ in range(50))
    assert total_hits > 0
    assert total_hits <= 50


def test_metrics_no_nan_core():
    env = RFEnvironment(n_bands=12, T=800, seed=5)
    m = compute_metrics(env, run_episode(env, SequentialSweep(12), seed=6))
    for k in ("avg_reward", "intercept_ratio", "pct_correct_predictions"):
        assert not np.isnan(m[k])


def test_smartscan_beats_sequential():
    sm, sq = [], []
    smc, sqc = [], []
    for ep in range(4):
        env = RFEnvironment(n_bands=12, T=2500, seed=90 + ep)
        ms = compute_metrics(env, run_episode(env, SmartScanScheduler(12, seed=ep), seed=ep))
        env2 = RFEnvironment(n_bands=12, T=2500, seed=90 + ep)
        mo = compute_metrics(env2, run_episode(env2, SequentialSweep(12), seed=ep))
        sm.append(ms["total_reward"]); sq.append(mo["total_reward"])
        smc.append(ms["threat_intercept_ratio"]); sqc.append(mo["threat_intercept_ratio"])
    assert np.mean(sm) > np.mean(sq)
    assert np.mean(smc) > np.mean(sqc) + 0.05


def test_qlearning_improves_with_training():
    first_all, last_all = [], []
    for seed0 in (1, 7, 11):
        s = LinearQLearning(10, seed=seed0, eps=0.35)
        first, last = [], []
        for ep in range(10):
            env = RFEnvironment(n_bands=10, T=900, seed=200)
            r = float(np.sum(run_episode(env, s, seed=ep).rewards))
            (first if ep < 5 else last).append(r)
            s.end_episode()
        first_all.append(np.mean(first))
        last_all.append(np.mean(last))
    # averaged over seeds, training must improve mean episode reward
    assert np.mean(last_all) > np.mean(first_all)


def test_evaluation_pipeline_runs():
    scheds = make_schedulers(10, [1, 2], seed=3)[:4] + [SmartScanScheduler(10, seed=3)]
    res = evaluate(scheds, episodes=2, n_bands=10, T=600, base_seed=42)
    assert set(res.keys()) == {s.name for s in scheds}
    assert all(np.isfinite(m["avg_reward"]) for m in res.values())


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
