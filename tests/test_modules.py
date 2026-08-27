import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))
"""End-to-end tests for config, dataset, DQN, persistence, multi-receiver, viz."""
import io
import json
import tempfile
from pathlib import Path

import numpy as np

from ewsmart.config import ScenarioConfig
from ewsmart.environment import RFEnvironment
from ewsmart.receiver import ESReceiver
from ewsmart.dataset import (synthetic_pdws, summarize_pdws,
                             environment_from_dataset)
from ewsmart.dqn import DQNAgent
from ewsmart.schedulers import (SmartScanScheduler, LinearQLearning,
                                DQNScheduler, SequentialSweep, UCBScheduler)
from ewsmart.persistence import save_scheduler, load_scheduler
from ewsmart.multireceiver import CooperativeTeam, run_episode_multi
from ewsmart.runner import run_episode, REWARD_CFG
from ewsmart.metrics import compute_metrics, json_safe
from ewsmart.experiments import roc_experiment, ablation_experiment


def test_config_roundtrip():
    cfg = ScenarioConfig(n_bands=12, T=500, seed=2)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "scenario.json"
        cfg.to_json(str(p))
        cfg2 = ScenarioConfig.from_json(str(p))
        assert cfg2.n_bands == 12 and cfg2.T == 500
    assert cfg.scaled(period_range=(10, 20)).period_range == (10, 20)


def test_env_from_config_spatial_physical():
    cfg = ScenarioConfig(n_bands=10, T=800, seed=3, n_spatial=3)
    env = RFEnvironment(cfg)
    spat = [e for e in env.emitters if e.kind == "spatial"]
    assert len(spat) >= 1
    for e in spat:
        assert e.rotation_rate_deg_s > 0.0
        assert e.beamwidth_deg > 0.0
        expect_on = max(1, int(round(e.period * e.beamwidth_deg / 360.0)))
        assert 1 <= e.on_len <= max(expect_on + 1, 2)


def test_receiver_reports_aoa_and_pdw():
    env = RFEnvironment(ScenarioConfig(n_bands=6, T=400, seed=4))
    rx = ESReceiver(env, seed=5)
    found = False
    for _ in range(120):
        b = int(env.rng.integers(env.n_bands))
        t = int(env.rng.integers(env.T))
        res = rx.dwell(b, t)
        if res.detections:
            snr, aoa = res.detections[0]
            assert 0.0 <= aoa < 360.0
            assert np.isfinite(res.snr_db)
            assert len(res.pdws) == len(res.detections)
            assert "freq_mhz" in res.pdws[0]
            found = True
    assert found


def test_receivers_independent_noise():
    env = RFEnvironment(ScenarioConfig(n_bands=6, T=2000, seed=6))
    r1, r2 = ESReceiver(env, seed=7), ESReceiver(env, seed=8)
    assert not np.allclose(r1.fa_floor, r2.fa_floor)
    assert not np.allclose(r1.fa_floor, env.noise_floor)


def test_json_output_strictly_valid():
    buf = io.StringIO()
    env = RFEnvironment(n_bands=8, T=300, seed=14)
    m = compute_metrics(env, run_episode(env, SmartScanScheduler(8, seed=15), seed=16))
    json.dump(json_safe(m), buf, allow_nan=False)   # must not raise
    buf.seek(0)
    parsed = json.load(buf)
    assert parsed["threat_intercept_ratio"] >= 0.0


def _install_fake_datasets(loader):
    mod = __import__("types").ModuleType("datasets")
    mod.load_dataset = loader
    prev = __import__("sys").modules.get("datasets")
    __import__("sys").modules["datasets"] = mod
    return prev


def _restore_fake_datasets(prev):
    import sys
    if prev is None:
        sys.modules.pop("datasets", None)
    else:
        sys.modules["datasets"] = prev


def test_huggingface_loader_mock():
    class FakeDS:
        column_names = ("toa", "rf", "pw", "pa", "aoa")

        def __iter__(self):
            for i in range(50):
                yield {"toa": float(i), "rf": 3000.0, "pw": 2.0,
                       "pa": 12.0, "aoa": 45.0}

    prev = _install_fake_datasets(lambda *a, **k: FakeDS())
    try:
        from ewsmart.dataset import load_pdws
        rows = load_pdws(max_rows=10)
        assert len(rows) == 10
        assert rows[0]["freq_mhz"] == 3000.0
    finally:
        _restore_fake_datasets(prev)


def test_huggingface_loader_falls_back_offline():

    def boom(*a, **k):
        raise ConnectionError("offline")

    prev = _install_fake_datasets(boom)
    try:
        from ewsmart.dataset import load_pdws
        rows = load_pdws(max_rows=100, seed=1)
        assert len(rows) == 100
        assert {"toa_us", "freq_mhz"} <= set(rows[0])
    finally:
        _restore_fake_datasets(prev)


def test_dataset_synthetic_schema_and_calibration():
    syn = synthetic_pdws(n=3000, seed=0)
    assert all({"toa_us", "freq_mhz", "pw_us", "pa_db", "aoa_deg"} <= set(p)
               for p in syn[:50])
    s = summarize_pdws(syn)
    assert s["n_pdw"] == 3000
    assert 17000 < s["freq_max_mhz"] <= 18100
    env, summ = environment_from_dataset(n_bands=20, T=600, seed=0,
                                         max_rows=2000)
    assert env.band_seq.shape[1] == 600
    assert len(env.emitters) > 0
    assert summ["n_freq_clusters"] >= 1


def test_dqn_learns_toy_bandit():
    agent = DQNAgent(n_bands=4, state_dim=4, hidden=(16,), gamma=0.9,
                     lr=0.005, batch=32, eps_start=0.4, eps_min=0.02,
                     eps_decay=1.0, seed=0)
    rng = np.random.default_rng(0)
    eye = np.eye(4, dtype=np.float32)
    for _ in range(1500):
        a = agent.act(eye[0], greedy=False)
        r = 1.0 if a == 0 else 0.0
        agent.observe(eye[0], a, r, eye[int(rng.integers(4))], False)
    assert agent.act(eye[0].astype(np.float32), greedy=True) == 0


def test_dqn_scheduler_episode_runs():
    s = DQNScheduler(8, seed=17, hidden=(16,))
    env = RFEnvironment(n_bands=8, T=300, seed=18)
    tr = run_episode(env, s, seed=19)
    assert len(tr.actions) == 300
    w = s.get_weights()
    s.set_weights(w)
    assert np.allclose(s.agent.q.W[0], w["W"][0])


def test_persistence_roundtrip_safe_npz():
    with tempfile.TemporaryDirectory() as td:
        for cls in (LinearQLearning, SmartScanScheduler, DQNScheduler,
                    UCBScheduler):
            s = cls(6, seed=0)
            env = RFEnvironment(n_bands=6, T=250, seed=20)
            run_episode(env, s, seed=21)          # populate learned state
            p = Path(td) / f"{cls.__name__}.npz"
            save_scheduler(p, s)
            with np.load(p, allow_pickle=False) as z:
                meta = json.loads(str(z["meta"]))
                assert str(meta["format"]).startswith("ewsmart-npz")
            loaded = load_scheduler(p)
            assert type(loaded) is cls
            assert loaded.n_bands == 6
            if isinstance(s, LinearQLearning):
                assert np.allclose(loaded.get_weights()["theta"],
                                   s.get_weights()["theta"])
            if isinstance(s, SmartScanScheduler):
                assert set(loaded.get_state().keys()) == set(s.get_state().keys())


def test_persistence_rejects_corrupt():
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.npz"
        np.savez(str(bad), junk=np.array([1.0]))
        raised = False
        try:
            load_scheduler(bad)
        except (ValueError, KeyError):
            raised = True
        assert raised, "should have raised"


def _run_team(k, kind, n_bands=8, T=400, seed=30):
    if kind == "smart":
        factories = [lambda nb, i=i: SmartScanScheduler(nb, seed=17 + i)
                     for i in range(k)]
    else:
        factories = [lambda nb: SequentialSweep(nb) for _ in range(k)]
    env = RFEnvironment(n_bands=n_bands, T=T, seed=seed)
    team = CooperativeTeam(factories)
    team.reset(n_bands, horizon=T)
    tr = run_episode_multi(env, team, seed=seed)
    return team, tr, env


def test_multireceiver_deconflicts_independent_and_covers():
    team, tr, env = _run_team(2, "smart")

    # per-slot de-confliction: no two receivers on the same band
    for bands in tr.per_receiver_actions:
        assert len(set(bands)) == len(bands)
    # team found threats across distinct bands (coverage multiplier ~ 1)
    uniq = sum(1 for a in tr.actions if len(set(a)) == len(a))
    assert uniq / max(1, len(tr.actions)) > 0.95
    assert len(tr.first_intercept) >= 1

    _, tr_seq, _ = _run_team(2, "seq")
    assert len(tr_seq.per_receiver_actions) == len(tr_seq.actions)


def test_roc_and_ablation_small():
    roc = roc_experiment(scheduler_names=("openloop-sequential",
                                          "smart-scan"),
                         n_bands=6, T=400, episodes=1)
    for d in roc.values():
        assert len(d["pfa"]) == len(d["pd"]) > 0
        assert all(np.isfinite(x) for x in d["pfa"] + d["pd"])
    abl = ablation_experiment(n_bands=6, T=400, episodes=1)
    for key in ("full", "recon-only"):
        assert key in abl
        assert np.isfinite(abl[key]["avg_reward"])


def test_viz_all_plots():
    import matplotlib
    matplotlib.use("Agg")
    from ewsmart import viz
    td = tempfile.mkdtemp()
    viz.plot_learning_curves({"a": [1, 2, 3], "b": [3, 2, 1]},
                             path=str(Path(td) / "lc.png"))
    flat = {}
    for n in ("smart-scan", "openloop-sequential"):
        env = RFEnvironment(n_bands=8, T=200, seed=40)
        m = compute_metrics(env, run_episode(
            env, SmartScanScheduler(8) if n == "smart-scan" else SequentialSweep(8)))
        flat[n] = {k: (v if isinstance(v, (int, float)) else 0.0)
                   for k, v in m.items()}
    viz.plot_scheduler_comparison(flat, path=str(Path(td) / "cmp.png"))
    env = RFEnvironment(n_bands=8, T=200, seed=41)
    viz.plot_waterfall(env, run_episode(env, SequentialSweep(8)),
                       path=str(Path(td) / "wf.png"))
    viz.plot_roc({"s": (np.array([0.001, 0.01, 0.05]),
                        np.array([0.5, 0.8, 0.95]))},
                 path=str(Path(td) / "roc.png"))
    viz.plot_sensitivity([8, 16, 24],
                         {"smart-scan": [1.0, 2.0, 3.0],
                          "openloop-sequential": [1.0, 1.2, 2.0]},
                         "x", "y", "t", path=str(Path(td) / "sen.png"))
    viz.plot_heatmap(["8", "16"], ["lo", "hi"],
                     np.array([[1.0, 2.0], [3.0, 4.0]]),
                     "x", "y", "hm", path=str(Path(td) / "hm.png"))
    pngs = [p for p in Path(td).iterdir() if p.suffix == ".png"]
    assert len(pngs) == 6 and all(p.stat().st_size > 0 for p in pngs)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
