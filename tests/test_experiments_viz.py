import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))
"""Smoke coverage for the experiment suite, viz extras and the runner CLI."""
import json
import sys

import numpy as np
import pytest

import matplotlib
matplotlib.use("Agg")

from ewsmart.config import ScenarioConfig
from ewsmart.environment import RFEnvironment
from ewsmart.runner import run_episode, train
from ewsmart.schedulers import LinearQLearning, SmartScanScheduler
from ewsmart.experiments import (monte_carlo_eval, significance_tests,
                                 mission_effectiveness_experiment,
                                 evaluate_meta_learning, learning_experiment,
                                 sensitivity_experiment, geolocation_experiment,
                                 multireceiver_experiment, greedy_eval,
                                 _set_exploration, _restore_exploration)


class DQNForTest:
    def __init__(self):
        from ewsmart.dqn import DQNAgent
        self.agent = DQNAgent(4, 32, hidden=(4, 4), seed=0)
        self.agent.eps = 0.5


def test_greedy_eval_restores_exploration():
    env = RFEnvironment(n_bands=6, T=200, seed=5)
    s = LinearQLearning(6, seed=6)
    run_episode(env, s, seed=7)
    w = s.get_weights()
    old_eps = s.eps
    r = greedy_eval(s, env, seed=8)
    assert np.isfinite(r)
    assert s.eps == old_eps
    assert np.array_equal(s.get_weights()["theta"], w["theta"])


def test_set_restore_exploration_paths():
    s = SmartScanScheduler(6, seed=1)
    initial = s.explore_eps
    old = _set_exploration(s, 0.0)
    assert s.explore_eps == 0.0
    _restore_exploration(s, old)
    assert s.explore_eps == initial
    d = DQNForTest()
    old2 = _set_exploration(d, 0.0)
    assert d.agent.eps == 0.0
    _restore_exploration(d, old2)
    assert d.agent.eps == 0.5


def test_experiments_small_suite():
    mc = monte_carlo_eval(n_bands=6, T=200, episodes=5)
    names = [k for k in mc if not k.startswith("_")]
    assert "smart-scan" in names and len(names) == 7
    rows = significance_tests(mc, baseline="smart-scan",
                              metric="avg_reward")
    assert len(rows) == 6
    for r in rows:
        assert "p_value" in r and "mean_diff" in r
        assert r["significant"] in (True, False)
    me, sig_rows = mission_effectiveness_experiment(mc)
    assert "scores" in me and "ranking" in me
    assert "smart-scan" in me["scores"]
    assert isinstance(sig_rows, list)


def test_meta_and_learning_experiments_small():
    meta = evaluate_meta_learning(n_bands=6, T=200, episodes=1, seed_base=31)
    assert "meta_reward_gain" in meta and "per_episode" in meta
    curves, summary = learning_experiment(episodes=2, n_bands=6, T=200,
                                          seeds=(0,))
    assert set(curves) == {"training", "eval"}
    for n, v in curves["training"].items():
        assert len(v) == 2
    assert summary["rl-linear-q"]["n_runs"] == 1


def test_sensitivity_and_geo_small():
    sens = sensitivity_experiment(T=120, episodes=1)
    for key in ("bands_reward", "snr_coverage", "agility_reward",
                "density_reward"):
        assert key in sens and "series" in sens[key]
    geo = geolocation_experiment(trials=8, sigma_deg=2.0)
    assert 2 in geo["by_receivers"] and geo["example"] is not None
    mr = multireceiver_experiment(team_sizes=(1, 2), n_bands=8, T=200,
                                  episodes=1)
    assert "smart-scan-x1" in mr and "openloop-sequential-x2" in mr


def test_train_returns_learning_curve():
    scheds = [LinearQLearning(6, seed=0), SmartScanScheduler(6, seed=1)]
    curve = train(scheds, episodes=2, n_bands=6, T=200, base_seed=100)
    assert set(curve) == {"rl-linear-q", "smart-scan"}
    assert all(len(v) == 2 for v in curve.values())


def _run_main(monkeypatch, argv):
    import ewsmart.runner as R
    monkeypatch.setattr(sys, "argv", argv)
    R.main()


def test_runner_main_end_to_end(monkeypatch, tmp_path):
    jout = tmp_path / "out.json"
    savedir = tmp_path / "models"
    _run_main(monkeypatch, [
        "ewsmart-run", "--bands", "6", "--T", "200",
        "--train-episodes", "1", "--eval-episodes", "1",
        "--save-dir", str(savedir), "--json-out", str(jout),
        "--db-out", ""])
    data = json.loads(jout.read_text())
    assert {"results", "results_ci", "learning_curve"} <= set(data)
    assert any(savedir.glob("*.npz"))
    assert "openloop-sequential" in data["results"]


def test_runner_main_trials_streams_to_db(monkeypatch, tmp_path):
    from ewsmart.db import MetricsDB
    dbp = tmp_path / "cli.db"
    jout = tmp_path / "cli.json"
    _run_main(monkeypatch, [
        "ewsmart-run", "--bands", "6", "--T", "200",
        "--train-episodes", "1", "--trials", "2",
        "--db-out", str(dbp), "--json-out", str(jout)])
    with MetricsDB(dbp) as db:
        n = db.conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
        assert n == 14          # 7 schedulers x 2 trials
        assert len(db.aggregates(1)) > 0


def test_evasive_emitter_evasion_protocol():
    cfg = ScenarioConfig(n_bands=8, T=600, seed=3, n_stationary=1, n_agile=0,
                         n_periodic=0, n_spatial=0, n_evasive=2, n_clutter=1)
    env = RFEnvironment(cfg)
    ev = [e for e in env.emitters if e.kind == "evasive"]
    assert len(ev) == 2
    e0 = ev[0]
    for t in (10, 11, 12):
        env.report_intercept(e0.eid, t)     # 3rd consecutive intercept evades
    # occupancy matrix must stay consistent with the (rewritten) band_seq
    rows, cols = np.nonzero(env.band_seq >= 0)
    rebuilt = np.zeros_like(env.occupancy)
    rebuilt[env.band_seq[rows, cols], cols] = 1
    assert np.array_equal(rebuilt, env.occupancy)
    nxt = env.next_on_start(e0.eid, 50)
    assert nxt is None or nxt > 50


def test_viz_extra_plots():
    import matplotlib.pyplot as plt
    from ewsmart import viz
    from ewsmart.metrics import mission_scores
    flat = {"smart-scan": {"avg_reward": 0.5, "threat_intercept_ratio": 0.8,
                           "intercept_ratio": 0.9,
                           "pct_correct_predictions": 0.6,
                           "avg_intercept_time_error": 2.0,
                           "false_alarm_rate": 0.001},
            "openloop-sequential": {"avg_reward": 0.2,
                                    "threat_intercept_ratio": 0.4,
                                    "intercept_ratio": 0.7,
                                    "pct_correct_predictions": 0.4,
                                    "avg_intercept_time_error": 5.0,
                                    "false_alarm_rate": 0.002}}
    me = mission_scores(flat)
    assert me["ranking"]
    plt.close(viz.plot_mission_effectiveness(me))
    plt.close(viz.plot_learning_curves(
        {"training": {"a": [1, 2, 3, 4, 5, 6]},
         "eval": {"a": [2, 3, 4, 5, 6, 7]}}))
    plt.close(viz.plot_learning_curves({"a": [1, 2, 3]}))
    plt.close(viz.plot_geo_map([(5.0, 6.0)], [(0.0, 0.0), (45.0, 5.0)],
                               [{"x": 6.0, "y": 5.0, "residual_km": 1.2}]))
    plt.close(viz.plot_cep_curve({"1": {"mean": 2.0, "cep50": 1.5,
                                        "cep90": 3.0},
                                  "2": {"mean": 1.2, "cep50": 1.0,
                                        "cep90": 2.0}}))
    plt.close(viz.plot_sensitivity([1, 10, 100], {"s": [1, 2, 3]},
                                   "x", "y", "t", log_x=True))
    plt.close(viz.plot_scheduler_comparison(flat))


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
