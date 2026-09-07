"""Episode simulation, scheduler training and evaluation entry points."""
from __future__ import annotations

import argparse
import json

import numpy as np

from .environment import RFEnvironment
from .receiver import ESReceiver
from .metrics import (compute_metrics, Trace, json_safe,
                      aggregate_metrics_ci)
from .schedulers import (SequentialSweep, RandomScan, PrioritySweep,
                         UCBScheduler, LinearQLearning, DQNScheduler,
                         SmartScanScheduler)

REWARD_CFG = {"threat": 1.0, "clutter": 0.15, "empty": -0.05,
              "false_alarm": -0.08, "first_threat_bonus": 1.5}


def make_schedulers(n_bands: int, priority_bands: tuple | list,
                    seed: int = 0) -> list:
    """Instantiate every available scheduler for a scenario of ``n_bands``."""
    return [SequentialSweep(n_bands, seed),
            RandomScan(n_bands, seed),
            PrioritySweep(n_bands, tuple(priority_bands), seed),
            UCBScheduler(n_bands, seed),
            LinearQLearning(n_bands, seed),
            DQNScheduler(n_bands, seed),
            SmartScanScheduler(n_bands, seed)]


def detected_eids(env: RFEnvironment, res) -> tuple:
    """Emitters credited for a dwell under the attribution contract.

    Only emitters with an actual detection this dwell are credited; a
    band-level hit never credits co-channel emitters that were not resolved.
    Legacy result objects without ``detected_eids`` fall back to all emitters
    present (documented downgrade, used only by old test doubles).
    """
    eids = getattr(res, "detected_eids", None)
    if eids is not None:
        return tuple(eids)
    return tuple(e.eid for e in env.emitters_at(res.band, res.t))


def step_reward(env: RFEnvironment, res, first_intercept: dict) -> float:
    """Reward for one dwell: value-weighted hits with first-intercept bonus.

    Attribution contract: credit is given only to emitters actually detected
    in this dwell (``res.detected_eids``), never to silent co-channel
    emitters sharing the band.
    """
    if res.false_alarm:
        return REWARD_CFG["false_alarm"]
    if res.hit:
        eids = detected_eids(env, res)
        ems = {e.eid: e for e in env.emitters_at(res.band, res.t)}
        threat = any(ems[i].threat for i in eids if i in ems)
        r = REWARD_CFG["threat"] if threat else REWARD_CFG["clutter"]
        for eid in eids:
            if eid not in first_intercept:
                first_intercept[eid] = res.t
                if ems.get(eid) is not None and ems[eid].threat:
                    r += REWARD_CFG["first_threat_bonus"]
        return r
    return REWARD_CFG["empty"]


def run_episode(env: RFEnvironment, sched, seed: int = 1) -> Trace:
    """Simulate one episode of ``sched`` against ``env``; returns the trace.

    Trace lists are pre-allocated to the episode horizon and filled by
    index (no dynamic list growth in the hot simulation loop).
    """
    rx = ESReceiver(env, seed=seed)
    sched.reset(horizon=env.T)
    T = env.T
    trace = Trace(actions=[0] * T, hits=[False] * T,
                  false_alarms=[False] * T, rewards=[0.0] * T,
                  predictions=[False] * T, ambiguous=[False] * T)
    first_intercept = trace.first_intercept
    actions, hits, fas = trace.actions, trace.hits, trace.false_alarms
    rewards, predictions = trace.rewards, trace.predictions
    ambiguous = trace.ambiguous
    for t in range(T):
        b = sched.select(t)
        res = rx.dwell(b, t)
        pred = sched.predict(t, b)
        r = step_reward(env, res, first_intercept)
        actions[t] = b
        hits[t] = res.hit and not res.false_alarm
        fas[t] = res.false_alarm
        rewards[t] = r
        predictions[t] = pred
        ambiguous[t] = len(detected_eids(env, res)) > 1
        sched.update(t, b, res, r)
    return trace


def train(schedulers: list, episodes: int = 25, n_bands: int = 24,
          T: int = 3000, base_seed: int = 1000) -> dict:
    """Cross-episode training loop for learnable schedulers.

    Returns per-episode total-reward curves keyed by scheduler name.
    """
    curve: dict[str, list] = {}
    for s in schedulers:
        if not s.learnable:
            continue
        curve[s.name] = []
        for ep in range(episodes):
            env = RFEnvironment(n_bands=n_bands, T=T, seed=base_seed + ep)
            tr = run_episode(env, s, seed=base_seed + ep)
            curve[s.name].append(float(np.sum(tr.rewards)))
            s.end_episode()
    return curve


def evaluate_ci(schedulers: list, episodes: int = 15, n_bands: int = 24,
                T: int = 3000, base_seed: int = 5000,
                confidence: float = 0.95) -> tuple[dict, dict]:
    """Evaluate every scheduler on held-out episodes with confidence intervals.

    Returns:
        ``(results, ci)`` where ``results`` maps scheduler -> flat mean
        metrics (backward compatible with :func:`evaluate`) and ``ci`` maps
        scheduler -> :func:`ewsmart.metrics.aggregate_metrics_ci` output
        (mean / SEM / confidence interval per metric across the episodes).
    """
    results: dict[str, dict] = {}
    ci_out: dict[str, dict] = {}
    for s in schedulers:
        per_ep = []
        for ep in range(episodes):
            env = RFEnvironment(n_bands=n_bands, T=T, seed=base_seed + ep)
            tr = run_episode(env, s, seed=base_seed + 777 + ep)
            per_ep.append(compute_metrics(env, tr))
        agg = aggregate_metrics_ci(per_ep, confidence)
        ci_out[s.name] = agg
        results[s.name] = {k: (a["mean"] if a["mean"] is not None
                               else float("nan"))
                           for k, a in agg.items()}
    return results, ci_out


def evaluate(schedulers: list, episodes: int = 15, n_bands: int = 24,
             T: int = 3000, base_seed: int = 5000) -> dict:
    """Evaluate every scheduler on held-out episodes; returns averaged metrics."""
    results, _ = evaluate_ci(schedulers, episodes=episodes, n_bands=n_bands,
                             T=T, base_seed=base_seed)
    return results


def monte_carlo(schedulers: list, trials: int = 50, n_bands: int = 24,
                T: int = 3000, base_seed: int = 5000, confidence: float = 0.95,
                db_path: str | None = "ewsmart.db",
                config: dict | None = None) -> tuple[dict, dict]:
    """Monte Carlo evaluation streaming every trial into SQLite.

    Each trial's metrics are written to the database immediately after the
    episode completes (no giant in-memory accumulation), then the run is
    finalised with per-metric means, SEMs and confidence intervals.

    Args:
        schedulers: schedulers under test.
        trials: Monte Carlo episodes per scheduler.
        n_bands / T / base_seed: episode geometry and seeding.
        confidence: CI coverage for the aggregate rows.
        db_path: SQLite file to create/update, or ``None`` to skip storage.
        config: optional scenario configuration snapshot to store.

    Returns:
        ``(results, ci)`` as produced by :func:`evaluate_ci`.
    """
    db: MetricsDB | None = None
    run_id: int | None = None
    if db_path:
        from .db import MetricsDB
        db = MetricsDB(db_path)
        try:
            scen_id = db.add_scenario(config or {"n_bands": n_bands, "T": T},
                                      name=f"mc-{n_bands}b-{T}t")
            run_id = db.start_run(
                scen_id, kind="monte-carlo",
                meta={"trials": trials, "confidence": confidence,
                      "base_seed": base_seed})
        except Exception:
            db.close()
            raise
    results: dict[str, dict] = {}
    ci_out: dict[str, dict] = {}
    try:
        for s in schedulers:
            per_ep = []
            for ep in range(trials):
                env = RFEnvironment(n_bands=n_bands, T=T, seed=base_seed + ep)
                tr = run_episode(env, s, seed=base_seed + 777 + ep)
                m = compute_metrics(env, tr)
                per_ep.append(m)
                if db is not None and run_id is not None:
                    db.add_trial(run_id, s.name, ep, json_safe(m),
                                 n_bands=n_bands, T=T,
                                 seed=base_seed + 777 + ep)
            agg = aggregate_metrics_ci(per_ep, confidence)
            ci_out[s.name] = agg
            results[s.name] = {k: (a["mean"] if a["mean"] is not None
                                   else float("nan"))
                               for k, a in agg.items()}
        if db is not None and run_id is not None:
            db.finalize_run(run_id, [s.name for s in schedulers],
                            confidence=confidence)
            print(f"Metrics DB: {db.path} (run #{run_id}, "
                  f"{trials} trials x {len(schedulers)} schedulers)")
    finally:
        if db is not None:
            db.close()
    return results, ci_out


METRIC_COLS = ["avg_reward", "threat_intercept_ratio", "intercept_ratio",
               "mean_time_to_first_intercept", "threat_mean_ttff",
               "intercept_rate", "false_alarm_rate",
               "pct_correct_predictions", "avg_intercept_time_error"]


def print_table(results: dict) -> None:
    """Pretty-print an aggregated metrics comparison table."""
    hdr = f"{'scheduler':<22}" + "".join(f"{c[:14]:>16}" for c in METRIC_COLS)
    print(hdr)
    print("-" * len(hdr))
    for name, m in results.items():
        row = f"{name:<22}"
        for c in METRIC_COLS:
            v = m[c]
            row += f"{v:>16.4f}" if v == v else f"{'--':>16}"
        print(row)


def main() -> None:
    ap = argparse.ArgumentParser(description="Train and evaluate ES scan schedulers")
    ap.add_argument("--bands", type=int, default=None,
                    help="override scenario n_bands")
    ap.add_argument("--T", type=int, default=None,
                    help="override scenario horizon")
    ap.add_argument("--train-episodes", type=int, default=15)
    ap.add_argument("--eval-episodes", type=int, default=10)
    ap.add_argument("--trials", type=int, default=None,
                    help="Monte Carlo trials per scheduler; streams every "
                         "trial into the SQLite metrics DB (--db-out)")
    ap.add_argument("--db-out", default="ewsmart.db",
                    help="path of the SQLite metrics database "
                         "(used with --trials; pass an empty string to disable)")
    ap.add_argument("--confidence", type=float, default=0.95,
                    help="confidence-interval coverage for aggregated metrics")
    ap.add_argument("--scenario", default=None,
                    help="path to a scenario JSON produced by ewsmart.config")
    ap.add_argument("--save-dir", default=None,
                    help="directory to persist trained schedulers")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    from .config import ScenarioConfig
    cfg = ScenarioConfig.from_json(args.scenario) if args.scenario else \
        ScenarioConfig()
    overrides = {}
    if args.bands is not None:
        overrides["n_bands"] = args.bands
    if args.T is not None:
        overrides["T"] = args.T
    if overrides:
        cfg = cfg.scaled(**overrides)
    probe = RFEnvironment(cfg)
    threats = sorted({e.home_band for e in probe.emitters
                      if e.threat and e.kind == "stationary"})
    scheds = make_schedulers(cfg.n_bands, threats or [0], seed=7)

    print("Training learnable schedulers...")
    curve = train(scheds, episodes=args.train_episodes,
                  n_bands=cfg.n_bands, T=cfg.T)
    for name, vals in curve.items():
        half = max(1, len(vals) // 3)
        a, b = np.mean(vals[:half]), np.mean(vals[-half:])
        print(f"  {name}: total_reward {a:.0f} -> {b:.0f}")

    print("\nEvaluation on held-out episodes:")
    if args.trials:
        results, ci = monte_carlo(
            scheds, trials=args.trials, n_bands=cfg.n_bands, T=cfg.T,
            confidence=args.confidence,
            db_path=args.db_out or None,
            config={"n_bands": cfg.n_bands, "T": cfg.T})
    else:
        results, ci = evaluate_ci(scheds, episodes=args.eval_episodes,
                                  n_bands=cfg.n_bands, T=cfg.T,
                                  confidence=args.confidence)
    print_table(results)

    if args.save_dir:
        from pathlib import Path
        from .persistence import save_scheduler
        out = Path(args.save_dir)
        out.mkdir(parents=True, exist_ok=True)
        for s in scheds:
            p = out / f"{s.name}.npz"
            try:
                save_scheduler(p, s)
                print(f"saved {s.name} -> {p}")
            except ValueError as exc:
                print(f"skip {s.name}: {exc}")

    if args.json_out:
        from .metrics import json_safe
        with open(args.json_out, "w") as f:
            json.dump(json_safe({"results": results, "results_ci": ci,
                                 "learning_curve": curve}),
                      f, indent=2, allow_nan=False)
        print(f"\nSaved -> {args.json_out}")


if __name__ == "__main__":
    main()
