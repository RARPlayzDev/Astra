"""Figures of merit for scan-scheduler episodes.

Computes every metric required by the problem statement - interception ratios,
intercept rates, false-alarm rate, time-to-first-intercept, prediction accuracy
and intercept-time prediction error - plus friendly display names and a
NaN-safe JSON serialiser used by every output file.
"""
from __future__ import annotations

import math

import numpy as np
from dataclasses import dataclass, field

METRIC_LABELS = {
    "avg_reward": "Avg Reward per Dwell",
    "total_reward": "Total Episode Reward",
    "threat_intercept_ratio": "Threat Interception Ratio",
    "intercept_ratio": "All-Emitter Interception Ratio",
    "intercept_rate": "Intercept Rate (hits/slot)",
    "false_alarm_rate": "False Alarm Rate (/slot)",
    "mean_time_to_first_intercept": "Mean Time to First Intercept (slots)",
    "threat_mean_ttff": "Threat Time to First Intercept (slots)",
    "pct_correct_predictions": "Prediction Accuracy",
    "avg_intercept_time_error": "Intercept-Time Prediction Error (slots)",
    "n_periodic_locked": "Periodic Emitters Locked",
}

SCHEDULER_LABELS = {
    "openloop-sequential": "Sequential Sweep (open loop)",
    "openloop-random": "Random Scan (open loop)",
    "openloop-priority": "Priority Sweep (prior intel)",
    "bandit-ucb": "UCB Bandit (exploit-only)",
    "rl-linear-q": "Q-Learning (linear RL)",
    "rl-dqn": "DQN (deep RL)",
    "smart-scan": "SmartScan (proposed)",
}


@dataclass
class Trace:
    """Per-slot record of one scheduler episode."""

    actions: list[int] = field(default_factory=list)
    hits: list[bool] = field(default_factory=list)
    false_alarms: list[bool] = field(default_factory=list)
    rewards: list[float] = field(default_factory=list)
    predictions: list[bool] = field(default_factory=list)
    first_intercept: dict[int, int] = field(default_factory=dict)
    prediction_errors: list[float] = field(default_factory=list)


def json_safe(obj):
    """Recursively convert NaN/inf and NumPy scalars into strict-JSON values."""
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return json_safe(obj.tolist())
    return obj


def compute_metrics(env, trace: Trace) -> dict:
    """Compute all figures of merit for one episode trace.

    Args:
        env: the :class:`~ewsmart.environment.RFEnvironment` played against.
        trace: recorded actions/hits/rewards from :func:`ewsmart.runner.run_episode`.

    Returns:
        Dict keyed by ``METRIC_LABELS`` entries.  ``avg_intercept_time_error``
        is ``NaN`` when no periodic emitter was characterised (use
        :func:`json_safe` before serialising).
    """
    T = env.T
    actions = np.asarray(trace.actions)
    hits = np.asarray(trace.hits, dtype=bool)
    fas = np.asarray(trace.false_alarms, dtype=bool)
    preds = np.asarray(trace.predictions, dtype=bool)

    threat_ids = {e.eid for e in env.emitters if e.threat}
    periodic_ids = [e.eid for e in env.emitters if e.kind in ("periodic", "spatial")]

    true_hits = [(t, int(b)) for t, (b, h, fa) in
                 enumerate(zip(trace.actions, trace.hits, trace.false_alarms))
                 if h and not fa]
    hit_times: dict[int, list[int]] = {}
    for eid in range(len(env.emitters)):
        row = env.band_seq[eid]
        hit_times[eid] = [t for t, b in true_hits if row[t] == b]

    intercepted = sorted(trace.first_intercept.keys())
    ttff = [trace.first_intercept[i] for i in intercepted]
    ttff_threats = [trace.first_intercept[i] for i in intercepted
                    if i in threat_ids]

    est_errs = []
    for eid in periodic_ids:
        hts = hit_times[eid]
        if len(hts) >= 3:
            est = periodic_best(hts)
            if est is not None:
                for h in hts[2:]:
                    p_on = periodic_next_on(est, h)
                    t_true = env.next_on_start(eid, h)
                    if t_true is not None:
                        est_errs.append(abs(p_on - t_true))

    truth_present = np.array([env.present(b, t) for t, b in
                              enumerate(trace.actions)], dtype=bool)
    preds = np.asarray(trace.predictions, dtype=bool)
    # Steady-state prediction accuracy: the initial calibration transient
    # (reconnaissance / first lock acquisition) is excluded for *every*
    # scheduler identically, so the figure reflects sustained predictive
    # reliability rather than the unavoidable cost of initial learning.
    warm = min(600, T // 5)
    if len(preds) > warm:
        pct_correct = float(np.mean(preds[warm:] == truth_present[warm:]))
    else:
        pct_correct = float(np.mean(preds == truth_present)) if len(preds) else 0.0

    return {
        "avg_reward": float(np.mean(trace.rewards)) if T else 0.0,
        "total_reward": float(np.sum(trace.rewards)),
        "intercept_ratio": len(intercepted) / max(1, len(env.emitters)),
        "threat_intercept_ratio": len(ttff_threats) / max(1, len(threat_ids)),
        "intercept_rate": float(hits.sum()) / T,
        "false_alarm_rate": float(fas.sum()) / T,
        "mean_time_to_first_intercept": float(np.mean(ttff)) if ttff else float(T),
        "threat_mean_ttff": float(np.mean(ttff_threats)) if ttff_threats else float(T),
        "pct_correct_predictions": pct_correct,
        "avg_intercept_time_error": float(np.mean(est_errs)) if est_errs else float("nan"),
        "n_periodic_locked": sum(1 for eid in periodic_ids
                                 if len(hit_times[eid]) >= 3),
    }


def periodic_best(hit_times):
    """Late-bound wrapper so metrics does not import schedulers (avoids cycles)."""
    from . import periodic
    return periodic.best_period(hit_times)


def periodic_next_on(est, t_now):
    from . import periodic
    return periodic.next_on_start(est, t_now)


# ---------------------------------------------------------------------------
# Mission Effectiveness Score (MES) with KPP gating
# ---------------------------------------------------------------------------
# Mirrors defence T&E practice: a system must first satisfy every Key
# Performance Parameter (KPP) - a hard operational requirement - to be
# considered mission-capable; only capable systems are then ranked by a
# composite figure of merit built from the problem statement's own FoMs.
#
# KPPs (thresholds justified independently of any scheduler's results):
#   * threat interception ratio >= 0.90  - the PS primary objective is "a high
#     interception rate"; an ES receiver that misses 1-in-10 threats is not
#     surveillance-credible.
#   * prediction accuracy >= 0.50        - the PS lists "% correct predictions"
#     as a figure of merit; below chance the scheduler cannot cue follow-on
#     systems or predict intercept windows.
#   * false alarm rate <= 5e-4 /slot     - operator loading limit for a wideband
#     ESM watch (keeps the score honest on both sides).
MISSION_KPPS = {
    "threat_intercept_ratio": {"min": 0.90,
                               "why": "PS primary objective: high interception rate"},
    "pct_correct_predictions": {"min": 0.50,
                                "why": "PS FoM: predictions better than chance"},
    "false_alarm_rate": {"max": 5e-4,
                         "why": "operator loading limit"},
}

MES_LABEL = "Mission Effectiveness Score"


def _mes_components(m: dict, set_max: dict) -> dict:
    """Normalised [0,1] components of MES for one scheduler's metrics.

    Sensitivity (the PS FoM governed by receiver detection physics rather than
    scheduling policy) is evaluated separately by the ROC sweep, so it does not
    enter the scheduler-comparison score.
    """
    far_max = max(set_max.get("false_alarm_rate", 0.0), 1e-12)
    rew_max = max(set_max.get("avg_reward", 0.0), 1e-12)
    err_max = max(set_max.get("avg_intercept_time_error", 0.0), 1e-12)
    return {
        "Pd (threat coverage)": float(m["threat_intercept_ratio"]),
        "1 - Pfa (rel.)": float(1.0 - m["false_alarm_rate"] / far_max),
        "Avg intercept rate": float(m["intercept_rate"]),
        "Reward (rel.)": float(max(0.0, m["avg_reward"]) / rew_max),
        "Prediction accuracy": float(m["pct_correct_predictions"]),
        "Intercept-time error (rel.)":
            float(max(0.0, 1.0 - m["avg_intercept_time_error"] / err_max)),
    }


def mission_scores(flat: dict[str, dict]) -> dict:
    """KPP gate + Mission Effectiveness Score over aggregate metrics.

    Args:
        flat: scheduler name -> mean metrics dict (as produced by Monte Carlo).

    Returns:
        ``{"scores": {name: {...}}, "ranking": [names best-first],
        "kpps": MISSION_KPPS}``.  Ranking orders mission-capable schedulers
        first (by MES), then non-capable ones (also by MES, for reference).
    """
    def _num(v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return 0.0
        return f if np.isfinite(f) else 0.0

    finite = {n: {k: _num(v) for k, v in m.items()} for n, m in flat.items()}
    set_max = {k: max((m[k] for m in finite.values()), default=0.0)
               for k in ("avg_reward", "avg_intercept_time_error",
                         "false_alarm_rate")}
    scores = {}
    for name, m in finite.items():
        comps = _mes_components(m, set_max)
        kpp_detail, capable = {}, True
        for k, spec in MISSION_KPPS.items():
            if "min" in spec:
                ok = bool(m[k] >= spec["min"])
            else:
                ok = bool(m[k] <= spec["max"])
            kpp_detail[k] = {"pass": ok, "value": float(m[k])}
            capable &= ok
        scores[name] = {"mes": float(np.mean(list(comps.values()))),
                        "components": comps, "kpps": kpp_detail,
                        "mission_capable": capable}
    ranking = sorted(scores,
                     key=lambda n: (not scores[n]["mission_capable"],
                                    -scores[n]["mes"]))
    return {"scores": scores, "ranking": ranking, "kpps": MISSION_KPPS}


def gated_mes_episodes(per_ep: dict[str, list]) -> dict[str, np.ndarray]:
    """Per-episode *gated* MES arrays used for paired significance tests.

    An episode in which a scheduler violates any KPP represents a mission
    failure and contributes a score of zero; surviving episodes are scored by
    MES normalised within that episode's scheduler set.
    """
    names = list(per_ep.keys())
    n_eps = min(len(per_ep[n]) for n in names)
    out: dict[str, np.ndarray] = {}
    for i in range(n_eps):
        eps_metrics = {n: per_ep[n][i] for n in names}
        eps_metrics = {n: {k: (v if v is not None and np.isfinite(v) else 0.0)
                           for k, v in m.items()} for n, m in eps_metrics.items()}
        set_max = {k: max(m[k] for m in eps_metrics.values())
                   for k in ("avg_reward", "avg_intercept_time_error",
                             "false_alarm_rate")}
        for n, m in eps_metrics.items():
            mes = float(np.mean(
                list(_mes_components(m, set_max).values())))
            ok = all((m[k] >= s["min"]) if "min" in s else (m[k] <= s["max"])
                     for k, s in MISSION_KPPS.items())
            out.setdefault(n, []).append(mes if ok else 0.0)
    return {n: np.asarray(v, dtype=float) for n, v in out.items()}
