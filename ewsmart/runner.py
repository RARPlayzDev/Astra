"""Episode simulation, scheduler training and evaluation entry points."""
from __future__ import annotations

import argparse
import json

import numpy as np

from .environment import RFEnvironment
from .receiver import ESReceiver
from .metrics import compute_metrics, Trace
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


def step_reward(env: RFEnvironment, res, first_intercept: dict) -> float:
    """Reward for one dwell: value-weighted hits with first-intercept bonus."""
    if res.false_alarm:
        return REWARD_CFG["false_alarm"]
    if res.hit:
        ems = env.emitters_at(res.band, res.t)
        threat = any(e.threat for e in ems)
        r = REWARD_CFG["threat"] if threat else REWARD_CFG["clutter"]
        for e in ems:
            if e.eid not in first_intercept:
                first_intercept[e.eid] = res.t
                if e.threat:
                    r += REWARD_CFG["first_threat_bonus"]
        return r
    return REWARD_CFG["empty"]


def run_episode(env: RFEnvironment, sched, seed: int = 1) -> Trace:
    """Simulate one episode of ``sched`` against ``env``; returns the trace."""
    rx = ESReceiver(env, seed=seed)
    sched.reset(horizon=env.T)
    trace = Trace()
    for t in range(env.T):
        b = sched.select(t)
        res = rx.dwell(b, t)
        pred = sched.predict(t, b)
        r = step_reward(env, res, trace.first_intercept)
        trace.actions.append(b)
        trace.hits.append(res.hit and not res.false_alarm)
        trace.false_alarms.append(res.false_alarm)
        trace.rewards.append(r)
        trace.predictions.append(pred)
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


def evaluate(schedulers: list, episodes: int = 15, n_bands: int = 24,
             T: int = 3000, base_seed: int = 5000) -> dict:
    """Evaluate every scheduler on held-out episodes; returns averaged metrics."""
    results: dict[str, dict] = {}
    for s in schedulers:
        per_ep = []
        for ep in range(episodes):
            env = RFEnvironment(n_bands=n_bands, T=T, seed=base_seed + ep)
            tr = run_episode(env, s, seed=base_seed + 777 + ep)
            per_ep.append(compute_metrics(env, tr))
        agg = {}
        for k in per_ep[0]:
            vals = [m[k] for m in per_ep]
            agg[k] = float(np.nanmean(vals)) if any(np.isfinite(v) for v in vals) \
                else float("nan")
        results[s.name] = agg
    return results


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
    results = evaluate(scheds, episodes=args.eval_episodes,
                       n_bands=cfg.n_bands, T=cfg.T)
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
            json.dump(json_safe({"results": results, "learning_curve": curve}),
                      f, indent=2, allow_nan=False)
        print(f"\nSaved -> {args.json_out}")


if __name__ == "__main__":
    main()
