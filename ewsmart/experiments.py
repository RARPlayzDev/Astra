"""Experiment suite: Monte Carlo evaluation, ROC, sensitivity, ablation.

Runs the complete evaluation programme and writes JSON results plus PNG
figures into an output directory.  Two suites are provided:

* ``quick``  - smoke-scale (small T, few episodes) for CI and tests;
* ``full``   - presentation-scale for SIH deliverables.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import matplotlib.pyplot as plt

from .environment import RFEnvironment
from .metrics import compute_metrics, mission_scores, gated_mes_episodes
from .runner import run_episode, REWARD_CFG, train
from .schedulers import (LinearQLearning, DQNScheduler, SmartScanScheduler,
                         SequentialSweep, UCBScheduler)
from .multireceiver import CooperativeTeam, run_episode_multi
from .identification import (build_default_library, tag_environment,
                             identification_report, streams_from_env_detections)
from .geo import geolocate_streams, cep_stats, simulate_bearings, triangulate
from .sigtests import paired_permutation_test, paired_bootstrap_ci


def _threat_bands(n_bands: int, T: int) -> list[int]:
    probe = RFEnvironment(n_bands=n_bands, T=T, seed=1)
    return sorted({e.home_band for e in probe.emitters
                   if e.threat and e.kind == "stationary"}) or [0]


def monte_carlo_eval(n_bands=24, T=3000, episodes=200, base_seed=9000) -> dict:
    """Evaluate all schedulers over many episodes with 95% confidence intervals.

    Also stores per-episode arrays so paired significance tests can be run
    between schedulers (see :func:`significance_tests`).
    """
    from .runner import make_schedulers
    scheds = make_schedulers(n_bands, _threat_bands(n_bands, T), seed=11)
    out: dict = {}
    per_episode: dict = {}
    for s in scheds:
        per_ep = []
        for ep in range(episodes):
            env = RFEnvironment(n_bands=n_bands, T=T, seed=base_seed + ep)
            tr = run_episode(env, s, seed=base_seed + 31 * ep)
            per_ep.append(compute_metrics(env, tr))
        per_episode[s.name] = per_ep
        agg = {}
        for k in per_ep[0]:
            vals = np.array([m[k] for m in per_ep], dtype=float)
            vals = vals[np.isfinite(vals)]
            if len(vals) == 0:
                agg[k] = {"mean": None, "ci95": None}
                continue
            ci = 1.96 * vals.std(ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0.0
            agg[k] = {"mean": float(vals.mean()), "ci95": float(ci)}
        out[s.name] = agg
    out["_per_episode"] = per_episode
    return out


def significance_tests(mc: dict, baseline: str = "smart-scan",
                       metric: str = "avg_reward") -> list:
    """Paired permutation tests of ``baseline`` vs every other scheduler.

    Uses the per-episode metric arrays stored by :func:`monte_carlo_eval`.
    Returns rows with mean difference, bootstrap CI, p-value (one-sided,
    baseline greater) and Holm-Bonferroni decisions.
    """
    from .sigtests import holm_bonferroni
    per_ep = mc.get("_per_episode", {})
    if baseline not in per_ep:
        return []
    base = np.array([m[metric] for m in per_ep[baseline]
                     if np.isfinite(m[metric])], dtype=float)
    rows = []
    pvals, keys = [], []
    for name, eps in per_ep.items():
        if name == baseline or name.startswith("_"):
            continue
        other = np.array([m[metric] for m in eps if np.isfinite(m[metric])],
                         dtype=float)
        n = min(len(base), len(other))
        if n < 5:
            continue
        diff = float((base[:n] - other[:n]).mean())
        p = paired_permutation_test(base[:n], other[:n],
                                    n_permutations=20000, seed=7,
                                    alternative="greater")
        lo, hi = paired_bootstrap_ci(base[:n], other[:n], seed=7)
        rows.append({"comparator": name, "mean_diff": diff,
                     "ci95_low": lo, "ci95_high": hi, "p_value": p, "n": n})
        pvals.append(p)
        keys.append(len(rows) - 1)
    if pvals:
        decisions = holm_bonferroni(pvals, alpha=0.05)
        for i, rej in zip(keys, decisions):
            rows[i]["significant"] = bool(rej)
    return rows


def mission_effectiveness_experiment(mc: dict) -> tuple[dict, list]:
    """KPP-gated Mission Effectiveness Score + paired tests on gated MES.

    Returns ``(mission_scores(flat_means), significance_rows)`` where the
    significance rows compare smart-scan against every other scheduler on
    per-episode *gated* MES (KPP-violating episodes score zero - a mission
    failure), with Holm-Bonferroni correction.
    """
    per_ep = mc.get("_per_episode", {})
    flat = {n: {k: (v["mean"] if isinstance(v, dict) else v)
                for k, v in d.items()}
            for n, d in mc.items()
            if not n.startswith("_") and isinstance(d, dict)}
    me = mission_scores(flat)

    rows = []
    if "smart-scan" in per_ep and len(per_ep) > 1:
        from .sigtests import holm_bonferroni
        gated = gated_mes_episodes(per_ep)
        base = gated["smart-scan"]
        pvals, keys = [], []
        for name, vals in gated.items():
            if name == "smart-scan":
                continue
            n = min(len(base), len(vals))
            diff = float((base[:n] - vals[:n]).mean())
            p = paired_permutation_test(base[:n], vals[:n],
                                        n_permutations=20000, seed=7,
                                        alternative="greater")
            lo, hi = paired_bootstrap_ci(base[:n], vals[:n], seed=7)
            rows.append({"comparator": name, "mean_diff": diff,
                         "ci95_low": lo, "ci95_high": hi, "p_value": p,
                         "n": n, "metric": "gated_mes"})
            pvals.append(p)
            keys.append(len(rows) - 1)
        if pvals:
            decisions = holm_bonferroni(pvals, alpha=0.05)
            for i, rej in zip(keys, decisions):
                rows[i]["significant"] = bool(rej)
    return me, rows


def _set_exploration(sched, value):
    """Temporarily set a scheduler's exploration rate (handles all policies)."""
    old = {}
    for attr_path in (("eps",), ("agent", "eps"), ("explore_eps",)):
        obj = sched
        try:
            for attr in attr_path[:-1]:
                obj = getattr(obj, attr)
            old[attr_path] = getattr(obj, attr_path[-1])
            setattr(obj, attr_path[-1], value)
        except (AttributeError, KeyError):
            continue
    return old


def _restore_exploration(sched, old):
    for attr_path, v in old.items():
        obj = sched
        for attr in attr_path[:-1]:
            obj = getattr(obj, attr)
        setattr(obj, attr_path[-1], v)


def greedy_eval(sched, env, seed):
    """Greedy rollout (exploration off); any training state is snapshotted and
    restored afterwards so evaluation never contaminates learning."""
    snap = sched.get_weights() if hasattr(sched, "get_weights") else None
    old = _set_exploration(sched, 0.0)
    try:
        tr = run_episode(env, sched, seed=seed)
        return float(np.sum(tr.rewards))
    finally:
        if snap is not None:
            sched.set_weights(snap)
        _restore_exploration(sched, old)


def evaluate_meta_learning(n_bands=24, T=2000, episodes=4, seed_base=5000) -> dict:
    """Evaluate MetaScheduler by running back-to-back episodes on the same battlefield.

    Demonstrates few-shot adaptation: the mean Time-To-First-Intercept (TTFF)
    should drop significantly on the second deployment because the meta-learned
    scheduler carries forward phase locks and band statistics from the first run.
    """
    from .schedulers import SmartScanScheduler, MetaScheduler
    from .metrics import compute_metrics

    results: list[dict] = []
    for ep in range(episodes):
        battlefield_seed = seed_base + ep
        # Both episodes use the same battlefield layout
        env1 = RFEnvironment(n_bands=n_bands, T=T, seed=battlefield_seed)
        env2 = RFEnvironment(n_bands=n_bands, T=T, seed=battlefield_seed)

        # --- Baseline (no meta-learning): two fresh SmartScanSchedulers ---
        base1 = SmartScanScheduler(n_bands, seed=42)
        tr1 = run_episode(env1, base1, seed=100 + ep)
        base2 = SmartScanScheduler(n_bands, seed=42)
        tr2 = run_episode(env2, base2, seed=200 + ep)

        m1_base = compute_metrics(env1, tr1)
        m2_base = compute_metrics(env2, tr2)
        ttff1_base = m1_base.get("mean_time_to_first_intercept", T)
        ttff2_base = m2_base.get("mean_time_to_first_intercept", T)

        # --- Meta-learning: persistent state across episodes ---
        meta = MetaScheduler(SmartScanScheduler(n_bands, seed=42))
        meta.reset(horizon=T)
        tr_m1 = run_episode(env1, meta, seed=100 + ep)
        meta.end_episode()

        env2m = RFEnvironment(n_bands=n_bands, T=T, seed=battlefield_seed)
        meta.reset(horizon=T)
        tr_m2 = run_episode(env2m, meta, seed=200 + ep)
        meta.end_episode()

        m1_meta = compute_metrics(env1, tr_m1)
        m2_meta = compute_metrics(env2m, tr_m2)
        ttff1_meta = m1_meta.get("mean_time_to_first_intercept", T)
        ttff2_meta = m2_meta.get("mean_time_to_first_intercept", T)

        results.append({
            "episode": ep,
            "baseline_ep1_ttff": float(ttff1_base),
            "baseline_ep2_ttff": float(ttff2_base),
            "meta_ep1_ttff": float(ttff1_meta),
            "meta_ep2_ttff": float(ttff2_meta),
            "baseline_ep1_reward": float(m1_base["avg_reward"]),
            "baseline_ep2_reward": float(m2_base["avg_reward"]),
            "meta_ep1_reward": float(m1_meta["avg_reward"]),
            "meta_ep2_reward": float(m2_meta["avg_reward"]),
        })

    # Aggregate: mean TTFF reduction on episode 2 vs episode 1
    baseline_ttff_reduction = np.mean([
        r["baseline_ep2_ttff"] - r["baseline_ep1_ttff"] for r in results])
    meta_ttff_reduction = np.mean([
        r["meta_ep2_ttff"] - r["meta_ep1_ttff"] for r in results])
    baseline_reward_gain = np.mean([
        r["baseline_ep2_reward"] - r["baseline_ep1_reward"] for r in results])
    meta_reward_gain = np.mean([
        r["meta_ep2_reward"] - r["meta_ep1_reward"] for r in results])

    return {
        "per_episode": results,
        "baseline_mean_ttff_ep1": float(np.mean([r["baseline_ep1_ttff"] for r in results])),
        "baseline_mean_ttff_ep2": float(np.mean([r["baseline_ep2_ttff"] for r in results])),
        "meta_mean_ttff_ep1": float(np.mean([r["meta_ep1_ttff"] for r in results])),
        "meta_mean_ttff_ep2": float(np.mean([r["meta_ep2_ttff"] for r in results])),
        "baseline_ttff_change": float(baseline_ttff_reduction),
        "meta_ttff_change": float(meta_ttff_reduction),
        "baseline_reward_gain": float(baseline_reward_gain),
        "meta_reward_gain": float(meta_reward_gain),
    }


def learning_experiment(episodes=12, n_bands=24, T=2000, seeds=(0, 1)):
    """Train learnable schedulers; report training AND greedy-eval curves.

    The training curve includes exploration noise (what the agent experiences
    while learning).  The evaluation curve is a separate greedy rollout on
    held-out scenarios, with weights snapshotted and restored, so it measures
    what the policy has actually learned.  Curves are averaged over ``seeds``.
    """
    from .schedulers import LinearQLearning, DQNScheduler, SmartScanScheduler

    def fresh_learners(seed):
        return [LinearQLearning(n_bands, seed=seed),
                DQNScheduler(n_bands, seed=seed),
                SmartScanScheduler(n_bands, seed=seed)]

    names = ("rl-linear-q", "rl-dqn", "smart-scan")
    train_runs, eval_runs = [], []
    for sd in seeds:
        learners = fresh_learners(sd)
        tr_curve = {n: [] for n in names}
        ev_curve = {n: [] for n in names}
        for ep in range(episodes):
            for s, n in zip(learners, names):
                env = RFEnvironment(n_bands=n_bands, T=T,
                                    seed=1000 + 977 * sd + ep)
                tr = run_episode(env, s, seed=sd * 31 + ep)
                tr_curve[n].append(float(np.sum(tr.rewards)))
                s.end_episode()
                eval_env = RFEnvironment(n_bands=n_bands, T=T,
                                         seed=50000 + 977 * sd + ep)
                ev_curve[n].append(greedy_eval(s, eval_env, seed=sd * 17 + ep))
        train_runs.append(tr_curve)
        eval_runs.append(ev_curve)

    mean_train = {n: list(np.mean([r[n] for r in train_runs], axis=0))
                  for n in names}
    mean_eval = {n: list(np.mean([r[n] for r in eval_runs], axis=0))
                 for n in names}
    summary = {}
    for n in names:
        v = np.asarray(mean_eval[n])
        third = max(1, len(v) // 3)
        summary[n] = {"eval_first_third_mean": float(v[:third].mean()),
                      "eval_last_third_mean": float(v[-third:].mean()),
                      "train_first_third_mean": float(np.mean(mean_train[n][:third])),
                      "train_last_third_mean": float(np.mean(mean_train[n][-third:])),
                      "n_runs": len(train_runs), "episodes_per_run": episodes}
    return {"training": mean_train, "eval": mean_eval}, summary


def roc_experiment(scheduler_names=("openloop-sequential", "bandit-ucb",
                                    "smart-scan"),
                   n_bands=16, T=1000, episodes=2) -> dict:
    """Sweep receiver sensitivity threshold; build empirical system ROC curves."""
    offsets = (0.0, 3.0, 6.0, 9.0, 12.0)
    from .receiver import ESReceiver
    factory = {"openloop-sequential": lambda b: SequentialSweep(b),
               "bandit-ucb": lambda b: UCBScheduler(b),
               "smart-scan": lambda b: SmartScanScheduler(b)}
    roc = {n: ([], []) for n in scheduler_names}
    for off in offsets:
        for name in scheduler_names:
            pfa_num = pd_num = pfa_den = pd_den = 0.0
            for ep in range(episodes):
                env = RFEnvironment(n_bands=n_bands, T=T, seed=400 + ep)
                rx = ESReceiver(env, pd_mid_offset=off, seed=500 + ep)
                s = factory[name](n_bands)
                s.reset(horizon=T)
                for t in range(T):
                    b = s.select(t)
                    res = rx.dwell(b, t)
                    s.update(t, b, res, 0.0)
                    if res.truth_present:
                        pd_num += res.hit and not res.false_alarm
                        pd_den += 1
                    else:
                        pfa_num += res.false_alarm
                        pfa_den += 1
            roc[name][0].append(pfa_num / max(1, pfa_den))
            roc[name][1].append(pd_num / max(1, pd_den))
    return {n: {"pfa": v[0], "pd": v[1]} for n, v in roc.items()}


def _pair_score(cfg_kwargs, metric="total_reward", episodes=2):
    """Mean metric of smart-scan vs sequential on identical scenario draws."""
    names = ("smart-scan", "openloop-sequential")
    vals = {n: [] for n in names}
    nb = cfg_kwargs.get("n_bands", 20)
    scheds = {"smart-scan": SmartScanScheduler(nb, seed=3),
              "openloop-sequential": SequentialSweep(nb)}
    for ep in range(episodes):
        env_s = RFEnvironment(seed=700 + ep, **cfg_kwargs)
        env_o = RFEnvironment(seed=700 + ep, **cfg_kwargs)
        ms = compute_metrics(env_s, run_episode(env_s, scheds["smart-scan"], seed=ep))
        mo = compute_metrics(env_o, run_episode(env_o, scheds["openloop-sequential"], seed=ep))
        vals["smart-scan"].append(ms[metric])
        vals["openloop-sequential"].append(mo[metric])
    return float(np.mean(vals["smart-scan"])), float(np.mean(vals["openloop-sequential"]))


def sensitivity_experiment(T=1200, episodes=2) -> dict:
    """Sweep bands / SNR / agility / density; SmartScan vs sequential surfaces."""
    out: dict = {}
    band_axis = [8, 16, 24]
    sm, so = [], []
    for b in band_axis:
        a, bb = _pair_score({"n_bands": b, "T": T}, episodes=episodes)
        sm.append(a)
        so.append(bb)
    out["bands_reward"] = {"x": band_axis,
                           "series": {"smart-scan": sm, "openloop-sequential": so}}

    snr_axis = [4.0, 8.0, 12.0, 16.0]
    sm_c, sq_c = [], []
    for snr in snr_axis:
        kw = {"n_bands": 20, "T": T, "snr_mean_db": snr}
        env = RFEnvironment(seed=701, **kw)
        m = compute_metrics(env, run_episode(env, SmartScanScheduler(20, seed=5), seed=5))
        env2 = RFEnvironment(seed=701, **kw)
        m2 = compute_metrics(env2, run_episode(env2, SequentialSweep(20), seed=5))
        sm_c.append(m["threat_intercept_ratio"])
        sq_c.append(m2["threat_intercept_ratio"])
    out["snr_coverage"] = {"x": snr_axis,
                           "series": {"smart-scan": sm_c, "openloop-sequential": sq_c}}

    agility = [("very fast", (1, 3)), ("fast", (3, 9)), ("slow", (10, 18))]
    sm_a, sq_a = [], []
    for _, rng_ in agility:
        a, bb = _pair_score({"n_bands": 20, "T": T, "dwell_range": rng_},
                            episodes=episodes)
        sm_a.append(a)
        sq_a.append(bb)
    out["agility_reward"] = {"x": [n for n, _ in agility],
                             "series": {"smart-scan": sm_a, "openloop-sequential": sq_a}}

    dens_axis = [0.5, 1.0, 2.0]
    sm_d, sq_d = [], []
    for f in dens_axis:
        kw = {"n_bands": 20, "T": T, "n_stationary": int(6 * f),
              "n_agile": int(4 * f), "n_periodic": int(4 * f),
              "n_spatial": int(3 * f), "n_clutter": int(8 * f)}
        a, bb = _pair_score(kw, episodes=episodes)
        sm_d.append(a)
        sq_d.append(bb)
    out["density_reward"] = {"x": dens_axis,
                             "series": {"smart-scan": sm_d, "openloop-sequential": sq_d}}
    return out


def geolocation_experiment(trials=40, sigma_deg=2.0, scene_km=40.0,
                           seed=0) -> dict:
    """CEP of AOA-triangulation vs the number of cooperating receivers."""
    rng = np.random.default_rng(seed)
    out = {"by_receivers": {}, "example": None}
    for k in (2, 3, 4):
        errors = []
        for _ in range(trials):
            ang = rng.uniform(0, 2 * np.pi)
            rad = scene_km * np.sqrt(rng.random())
            true_xy = (float(rad * np.cos(ang)), float(rad * np.sin(ang)))
            rxs = []
            for i in range(k):
                a = 2 * np.pi * i / k + rng.uniform(-0.4, 0.4)
                rxs.append((scene_km * 1.2 * np.cos(a) + rng.normal(0, 3),
                            scene_km * 1.2 * np.sin(a) + rng.normal(0, 3)))
            lines = simulate_bearings(true_xy, rxs, sigma_deg, rng)
            x, y, _ = triangulate(lines)
            errors.append(float(np.hypot(x - true_xy[0], y - true_xy[1])))
        out["by_receivers"][k] = cep_stats(errors)
    ang = rng.uniform(0, 2 * np.pi)
    rad = scene_km * 0.7
    ex_true = [(float(rad * np.cos(ang)), float(rad * np.sin(ang)))]
    ex_rxs = [(0.0, 0.0), (45.0, 5.0), (10.0, 48.0)]
    ex_est = []
    for t in ex_true:
        lines = simulate_bearings(t, ex_rxs, sigma_deg, rng)
        x, y, res = triangulate(lines)
        ex_est.append({"x": x, "y": y, "residual_km": res})
    out["example"] = {"true": ex_true, "receivers": ex_rxs,
                      "estimates": ex_est, "sigma_deg": sigma_deg}
    return out


def ablation_experiment(n_bands=20, T=1500, episodes=3) -> dict:
    """Ablate SmartScan components to quantify each behaviour's contribution."""
    variants = {
        "full": {},
        "no-phase-lock": {"lock_hits": 10 ** 9},
        "no-burst": {"burst_horizon": 0},
        "no-exploit-ramp": {"exploit_ramp": 0.0},
        "recon-only": {"lock_hits": 10 ** 9, "burst_horizon": 0,
                       "exploit_ramp": 0.0, "explore_eps": 0.0},
    }
    out = {}
    for name, kwargs in variants.items():
        rs, cs = [], []
        for ep in range(episodes):
            env = RFEnvironment(n_bands=n_bands, T=T, seed=800 + ep)
            s = SmartScanScheduler(n_bands, seed=9, **kwargs)
            m = compute_metrics(env, run_episode(env, s, seed=ep))
            rs.append(m["avg_reward"])
            cs.append(m["threat_intercept_ratio"])
        out[name] = {"avg_reward": float(np.mean(rs)),
                     "threat_intercept_ratio": float(np.mean(cs))}
    return out


def multireceiver_experiment(team_sizes=(1, 2, 3), n_bands=20, T=1500,
                             episodes=2) -> dict:
    """Compare cooperative teams of receivers against single-receiver baselines."""
    def team_factories(k, kind):
        if kind == "smart-scan":
            return [lambda nb: SmartScanScheduler(nb, seed=17 + i) for i in range(k)]
        return [lambda nb: SequentialSweep(nb) for _ in range(k)]

    out = {}
    for k in team_sizes:
        for kind in ("smart-scan", "openloop-sequential"):
            key = f"{kind}-x{k}"
            rs, covs = [], []
            for ep in range(episodes):
                env = RFEnvironment(n_bands=n_bands, T=T, seed=850 + ep)
                team = CooperativeTeam(team_factories(k, kind))
                team.reset(n_bands, horizon=T)
                tr = run_episode_multi(env, team, seed=ep)
                rs.append(float(np.sum(tr.rewards)))
                covs.append(len(tr.first_intercept) / max(1, len(env.emitters)))
            out[key] = {"total_reward": float(np.mean(rs)),
                        "intercept_ratio": float(np.mean(covs))}
    return out

def run_suite(outdir: str = "results", figdir: str = "figures",
              suite: str = "quick") -> dict:
    """Run the full experiment programme and persist results + figures."""
    from pathlib import Path
    from . import viz
    out, figs = Path(outdir), Path(figdir)
    out.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    quick = suite == "quick"
    summary: dict = {}

    print("[1/8] Monte Carlo evaluation...")
    mc = monte_carlo_eval(n_bands=24 if not quick else 16,
                          T=3000 if not quick else 800,
                          episodes=200 if not quick else 6)
    summary["monte_carlo"] = mc

    print("[2/8] Significance tests (paired permutation, Holm-corrected)...")
    sig_rows = []
    for metric in ("avg_reward", "threat_intercept_ratio"):
        rows = significance_tests(mc, baseline="smart-scan", metric=metric)
        for r in rows:
            r["metric"] = metric
        sig_rows.extend(rows)
    mc_public = {k: v for k, v in mc.items() if k != "_per_episode"}
    summary["monte_carlo"] = mc_public
    summary["significance"] = sig_rows
    for r in sig_rows:
        if r["metric"] == "avg_reward":
            print(f"    smart-scan vs {r['comparator']}: "
                  f"diff {r['mean_diff']:+.3f}, p={r['p_value']:.4f}, "
                  f"significant={r['significant']}")

    print("[2b/8] Mission Effectiveness (KPP gate + gated-MES tests)...")
    me, me_sig = mission_effectiveness_experiment(mc)
    summary["mission_effectiveness"] = me
    summary["significance_gated_mes"] = me_sig
    for name in me["ranking"]:
        s = me["scores"][name]
        print(f"    {'PASS' if s['mission_capable'] else 'FAIL'} KPPs  "
              f"MES {s['mes']:.3f}  {name}")
    for r in me_sig:
        print(f"    gated-MES smart-scan vs {r['comparator']}: "
              f"diff {r['mean_diff']:+.3f}, p={r['p_value']:.4f}, "
              f"significant={r['significant']}")
    viz.plot_mission_effectiveness(
        me, path=str(figs / "mission_effectiveness.png"))

    print("[3/8] Learning curves (training + greedy eval, seed-averaged)...")
    curve, lsum = learning_experiment(episodes=30 if not quick else 4,
                                      n_bands=20, T=1500 if not quick else 500,
                                      seeds=(0, 1) if not quick else (0,))
    summary["learning"] = lsum
    viz.plot_learning_curves(curve, path=str(figs / "learning_curves.png"))

    env0 = RFEnvironment(n_bands=20, T=1200 if not quick else 500, seed=123)
    s0 = SmartScanScheduler(20, seed=123)
    tr0 = run_episode(env0, s0)
    m0 = compute_metrics(env0, tr0)
    tag_environment(env0)
    id_rep = identification_report(env0, streams_from_env_detections(env0, tr0))
    summary["identification"] = {"accuracy": id_rep["accuracy"],
                                 "n_identified": id_rep["n_identified"],
                                 "n_streams": id_rep["n_streams"]}
    print(f"    identification accuracy: {id_rep['accuracy']:.0%} "
          f"({id_rep['n_identified']}/{id_rep['n_streams']} streams)")
    summary["example_episode_metrics"] = {
        k: (v if isinstance(v, str) else float(v)) for k, v in m0.items()}
    viz.plot_waterfall(env0, tr0, path=str(figs / "waterfall.png"))

    flat = {n: {k: v["mean"] for k, v in d.items()} for n, d in mc_public.items()}
    viz.plot_scheduler_comparison(flat, path=str(figs / "comparison.png"))

    print("[4/8] ROC sweep...")
    roc = roc_experiment(T=600 if quick else 1000,
                         episodes=1 if quick else 2)
    summary["roc"] = roc
    viz.plot_roc({n: (np.array(d["pfa"]), np.array(d["pd"]))
                  for n, d in roc.items()},
                 path=str(figs / "roc.png"))

    print("[5/8] Sensitivity sweeps...")
    sens = sensitivity_experiment(episodes=1 if quick else 2)
    summary["sensitivity"] = sens
    viz.plot_sensitivity(sens["bands_reward"]["x"],
                         sens["bands_reward"]["series"], "n_bands",
                         "total reward", "Sensitivity: spectrum size",
                         path=str(figs / "sens_bands.png"))
    viz.plot_sensitivity(sens["snr_coverage"]["x"],
                         {k.replace("_cov", ""): v
                          for k, v in sens["snr_coverage"]["series"].items()},
                         "mean SNR (dB)", "threat intercept ratio",
                         "Sensitivity: SNR", path=str(figs / "sens_snr.png"))
    xi = np.arange(len(sens["agility_reward"]["x"]))
    viz.plot_sensitivity(xi, sens["agility_reward"]["series"], "agile dwell speed",
                         "total reward", "Sensitivity: agility")
    plt.gca().set_xticks(xi, sens["agility_reward"]["x"])
    plt.savefig(figs / "sens_agility.png", dpi=130)
    plt.close()
    viz.plot_sensitivity(sens["density_reward"]["x"],
                         sens["density_reward"]["series"], "emitter density x",
                         "total reward", "Sensitivity: emitter density",
                         path=str(figs / "sens_density.png"))

    print("[6/8] Ablation...")
    abl = ablation_experiment(episodes=2 if quick else 3,
                              T=1000 if quick else 2000)
    summary["ablation"] = abl
    names = list(abl.keys())
    xr = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(xr - 0.2, [abl[n]["avg_reward"] for n in names], 0.4,
           label="avg reward")
    ax2 = ax.twinx()
    ax2.bar(xr + 0.2, [abl[n]["threat_intercept_ratio"] for n in names], 0.4,
            color="tab:red", label="threat coverage")
    ax.set_xticks(xr, names, fontsize=8, rotation=15)
    ax.set_ylabel("avg reward")
    ax2.set_ylabel("threat coverage")
    ax.set_title("SmartScan ablation study")
    fig.tight_layout()
    fig.savefig(figs / "ablation.png", dpi=130)
    plt.close(fig)

    print("[6.5/8] Meta-learning (few-shot adaptation)...")
    meta_res = evaluate_meta_learning(
        n_bands=20, T=1200 if not quick else 400,
        episodes=4 if not quick else 2)
    summary["meta_learning"] = meta_res
    print(f"    baseline TTFF ep1={meta_res['baseline_mean_ttff_ep1']:.0f} "
          f"ep2={meta_res['baseline_mean_ttff_ep2']:.0f}")
    print(f"    meta     TTFF ep1={meta_res['meta_mean_ttff_ep1']:.0f} "
          f"ep2={meta_res['meta_mean_ttff_ep2']:.0f}")
    print(f"    meta reward gain: {meta_res['meta_reward_gain']:+.2f} "
          f"vs baseline {meta_res['baseline_reward_gain']:+.2f}")

    print("[7/8] Multi-receiver coordination...")
    mr = multireceiver_experiment(team_sizes=(1, 2) if quick else (1, 2, 3),
                                  T=800 if quick else 1500,
                                  episodes=2 if quick else 3)
    summary["multireceiver"] = mr

    print("[8/8] Geolocation study...")
    geo = geolocation_experiment(trials=25 if quick else 60,
                                 sigma_deg=2.0)
    summary["geolocation"] = geo
    viz.plot_geo_map(geo["example"]["true"], geo["example"]["receivers"],
                     geo["example"]["estimates"],
                     path=str(figs / "geo_map.png"))
    viz.plot_cep_curve(geo["by_receivers"], path=str(figs / "geo_cep.png"))

    from .metrics import json_safe
    with open(out / "suite_results.json", "w") as f:
        json.dump(json_safe(summary), f, indent=2, allow_nan=False)
    print(f"\nResults -> {out.resolve()}\nFigures -> {figs.resolve()}")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="EW SmartScan experiment suite")
    ap.add_argument("--suite", choices=["quick", "full"], default="quick")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--figdir", default="figures")
    args = ap.parse_args()
    run_suite(outdir=args.outdir, figdir=args.figdir, suite=args.suite)


if __name__ == "__main__":
    main()
