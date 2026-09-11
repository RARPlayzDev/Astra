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
    "avg_net_reward": "Avg Net Reward per Dwell (after cost)",
    "switch_rate": "Band Switch Rate (/slot)",
    "cost_per_dwell": "Resource Cost per Dwell",
    "total_reward": "Total Episode Reward",
    "threat_intercept_ratio": "Threat Interception Ratio",
    "intercept_ratio": "All-Emitter Interception Ratio",
    "intercept_rate": "Intercept Rate (hits/slot)",
    "false_alarm_rate": "False Alarm Rate (/slot)",
    "mean_time_to_first_intercept": "Mean Time to First Intercept (slots)",
    "threat_mean_ttff": "Threat Time to First Intercept (slots)",
    "threat_ttff_censored": "Censored Threat Latency (slots)",
    "pct_correct_predictions": "Prediction Accuracy (steady state)",
    "pct_correct_predictions_full": "Prediction Accuracy (full episode)",
    "intercept_fraction_of_transmissions":
        "Pd - Fraction of Transmissions Intercepted",
    "threat_intercept_fraction_of_transmissions":
        "Pd - Threat Transmissions Intercepted",
    "avg_intercept_time_error": "Intercept-Time Prediction Error (slots)",
    "intercept_time_error_n": "Intercept-Time Error Samples",
    "intercept_time_error_coverage": "Intercept-Time Error Coverage",
    "n_periodic_locked": "Periodic Emitters Locked",
    "ambiguous_hit_rate": "Ambiguous Co-channel Hit Rate (/slot)",
    "agile_hop_follow_rate": "Agile Hop Follow Rate (window)",
    "agile_hop_follow_latency": "Mean Agile Hop Follow Latency (slots)",
    "ir_stationary": "Interception Ratio - Stationary",
    "ir_agile": "Interception Ratio - Frequency Agile",
    "ir_periodic": "Interception Ratio - Periodic",
    "ir_spatial": "Interception Ratio - Spatial Scan",
    "ir_evasive": "Interception Ratio - Evasive",
    "ttff_stationary": "TTFF - Stationary (slots)",
    "ttff_agile": "TTFF - Frequency Agile (slots)",
    "ttff_periodic": "TTFF - Periodic (slots)",
    "ttff_spatial": "TTFF - Spatial Scan (slots)",
    "ttff_evasive": "TTFF - Evasive (slots)",
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
    ambiguous: list[bool] = field(default_factory=list)  # co-channel dwells
    costs: list[float] = field(default_factory=list)  # explicit resource cost


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
    # Censored threat latency: a threat never intercepted is not dropped from
    # the average (that would flatter policies that miss hard threats); it is
    # credited the full episode horizon - a conservative lower bound on its
    # true time-to-intercept.  Operationally the correct T&E treatment.
    unfound_threats = len(threat_ids) - len(ttff_threats)
    threat_ttff_censored = ((sum(ttff_threats) + unfound_threats * T)
                            / max(1, len(threat_ids)))
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

    # Per-emitter-class FoMs (PS: "prediction of intercept time and
    # interception ratio ... against spatially scanning and frequency agile
    # emitters").  Interception ratio and censored mean time-to-first-intercept
    # are reported for every emitter class; classes absent from the scenario
    # yield NaN so they are excluded from Monte Carlo aggregates rather than
    # diluting the averages with phantom zeros.
    class_out: dict[str, float] = {}
    for kind in ("stationary", "agile", "periodic", "spatial", "evasive"):
        ids = {e.eid for e in env.emitters if e.kind == kind}
        if not ids:
            class_out[f"ir_{kind}"] = float("nan")
            class_out[f"ttff_{kind}"] = float("nan")
            continue
        got = [i for i in intercepted if i in ids]
        class_out[f"ir_{kind}"] = len(got) / len(ids)
        tt = [trace.first_intercept[i] for i in got]
        n_miss = len(ids) - len(got)
        class_out[f"ttff_{kind}"] = (sum(tt) + n_miss * T) / len(ids)

    # --- explicit cost model (PS FoM: "Avg Reward / cost function") -------
    # Resource costs (band-switch settle time + per-dwell operating budget)
    # are recorded per slot in ``trace.costs``; net reward is gross reward
    # minus those costs.  Legacy traces without a costs field are treated as
    # zero-cost so every consumer stays backward compatible.
    rewards_arr = np.asarray(trace.rewards, dtype=float)
    n_rew = len(rewards_arr)
    tc = getattr(trace, "costs", None)
    if tc is None or len(tc) != n_rew:
        costs_arr = np.zeros(n_rew, dtype=float)
    else:
        costs_arr = np.asarray(tc, dtype=float)
    net_rewards = rewards_arr - costs_arr
    n_switches = int(np.sum(actions[1:] != actions[:-1])) if T > 1 else 0

    # --- system-level probability of detection (PS FoM D3a) ----------------
    # Pd at the scheduler level is "what fraction of actual transmissions
    # did the scheduler-receiver system intercept": a true detection credited
    # while dwelling on the emitter's band during one of its ON slots.  This
    # is distinct from the receiver-level per-dwell curve
    # (ESReceiver.detection_prob) and from threat_intercept_ratio ("found at
    # least once in T slots", which any long-lived scan almost guarantees).
    seq = env.band_seq
    n_emit = seq.shape[0]
    n_slots = min(T, len(actions))
    if n_slots < 1:
        pdt, pdt_thr = 0.0, 0.0
    else:
        on = seq[:, :n_slots] >= 0
        hit_b = np.broadcast_to(
            np.asarray(hits[:n_slots], dtype=bool)[None, :], (n_emit, n_slots))
        intercepted_trans = (on & (seq[:, :n_slots] == actions[:n_slots][None, :])
                             & hit_b)
        n_trans = int(on.sum())
        pdt = float(intercepted_trans.sum()) / n_trans if n_trans else 0.0
        thr_vec = np.asarray([e.threat for e in env.emitters], dtype=bool)
        n_thr_trans = int(on[thr_vec].sum())
        pdt_thr = (float(intercepted_trans[thr_vec].sum()) / n_thr_trans
                   if n_thr_trans else 0.0)
    # Full-episode prediction accuracy (no warm-up exclusion) alongside the
    # steady-state figure: reporting both makes the calibration transient
    # visible instead of silently re-scoring it away.
    pct_correct_full = (float(np.mean(preds == truth_present))
                        if len(preds) else 0.0)

    return {
        "avg_reward": float(np.mean(trace.rewards)) if T else 0.0,
        "avg_net_reward": float(net_rewards.mean()) if n_rew else 0.0,
        "switch_rate": n_switches / max(1, T - 1),
        "cost_per_dwell": float(costs_arr.mean()) if n_rew else 0.0,
        "total_reward": float(np.sum(trace.rewards)),
        "intercept_ratio": len(intercepted) / max(1, len(env.emitters)),
        "threat_intercept_ratio": len(ttff_threats) / max(1, len(threat_ids)),
        "intercept_rate": float(hits.sum()) / T,
        "false_alarm_rate": float(fas.sum()) / T,
        "mean_time_to_first_intercept": float(np.mean(ttff)) if ttff else float(T),
        "threat_mean_ttff": float(np.mean(ttff_threats)) if ttff_threats else float(T),
        "threat_ttff_censored": float(threat_ttff_censored),
        "pct_correct_predictions": pct_correct,
        "pct_correct_predictions_full": pct_correct_full,
        "intercept_fraction_of_transmissions": pdt,
        "threat_intercept_fraction_of_transmissions": pdt_thr,
        "avg_intercept_time_error": float(np.mean(est_errs)) if est_errs else float("nan"),
        "intercept_time_error_n": len(est_errs),
        "intercept_time_error_coverage": (sum(1 for eid in periodic_ids
                                              if len(hit_times[eid]) >= 3)
                                          / max(1, len(periodic_ids))),
        "n_periodic_locked": sum(1 for eid in periodic_ids
                                 if len(hit_times[eid]) >= 3),
        "ambiguous_hit_rate": (float(np.mean(trace.ambiguous))
                               if len(trace.ambiguous) else 0.0),
        **class_out,
    }


def attribution_conservation(env, trace: Trace) -> dict:
    """Conservation check of the emitter-attribution contract.

    Verifies that every credited emitter was actually detected at its
    credited slot, so emitter-level credits can never exceed supported
    detections.  Returns ``{"ok": bool, "violations": int}``.
    """
    violations = 0
    for eid, t in trace.first_intercept.items():
        if not (0 <= eid < len(env.emitters) and 0 <= t < env.T):
            violations += 1
            continue
        row = env.band_seq[eid]
        if t >= len(trace.actions) or row[t] != trace.actions[t]:
            violations += 1
    return {"ok": violations == 0, "violations": violations}


def agile_hop_follow_metrics(env, trace: Trace, window: int = 8) -> dict:
    """Policy-level agile-hop coverage, measured post hoc from a full trace.

    For every hop of every frequency-agile emitter (a band change in its
    observable band sequence) this checks whether the scheduler dwelt on the
    *destination* band within ``window`` slots after the hop.  It uses only
    the trace the scheduler actually produced plus the environment's band
    sequences, and nothing is fed back into the policy, so the measurement is
    leakage-free when used as an offline evaluation.  This is the
    policy-level companion to :mod:`ewsmart.prediction`: next-hop *prediction*
    accuracy is reported separately from *coverage* of the hops.

    Returns ``{"n_hops", "agile_hop_follow_rate", "agile_hop_follow_latency",
    "window"}``.  Latency is the mean slot offset between the hop and the
    first following dwell on the destination band (NaN when no hop followed).
    """
    actions = np.asarray(trace.actions)
    T = min(int(env.T), len(actions))
    hops = covered = 0
    latencies: list[int] = []
    for e in env.emitters:
        if e.kind != "agile":
            continue
        seq = env.band_seq[e.eid]
        for t in range(1, T):
            b_prev, b_new = int(seq[t - 1]), int(seq[t])
            if b_new < 0 or b_new == b_prev:
                continue
            hops += 1
            hit_t = next((tt for tt in range(t, min(T, t + window))
                          if int(actions[tt]) == b_new), None)
            if hit_t is not None:
                covered += 1
                latencies.append(hit_t - t)
    return {"n_hops": hops,
            "agile_hop_follow_rate": covered / hops if hops else 0.0,
            "agile_hop_follow_latency":
                float(np.mean(latencies)) if latencies else float("nan"),
            "window": int(window)}


def periodic_best(hit_times):
    """Late-bound wrapper so metrics does not import schedulers (avoids cycles)."""
    from . import periodic
    return periodic.best_period(hit_times)


def periodic_next_on(est, t_now):
    from . import periodic
    return periodic.next_on_start(est, t_now)


# ---------------------------------------------------------------------------
# Cross-run statistics: standard error and confidence intervals
# ---------------------------------------------------------------------------

def confidence_interval(values, confidence: float = 0.95) -> dict:
    """Mean, standard error and CI for one metric across Monte Carlo runs.

    Non-finite values (``None`` / NaN / inf) are excluded, matching the
    NaN-tolerant aggregation used elsewhere.  The interval is a normal
    approximation, ``mean +/- z * SEM`` with ``z = Phi^-1((1+c)/2)``, which is
    the standard choice for the episode-level Monte Carlo aggregates here.

    Args:
        values: per-episode values of one metric.
        confidence: coverage probability in ``(0, 1)`` (default 95%).

    Returns:
        ``{"mean", "sem", "ci95", "ci_low", "ci_high", "n"}`` where every
        field is ``None`` when no finite values exist.
    """
    from statistics import NormalDist
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must lie in (0, 1), got {confidence!r}")
    vals = np.asarray([float(v) for v in values
                       if v is not None and np.isfinite(v)], dtype=float)
    n = int(vals.size)
    if n == 0:
        return {"mean": None, "sem": None, "ci95": None,
                "ci_low": None, "ci_high": None, "n": 0}
    mean = float(vals.mean())
    sem = float(vals.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    z = float(NormalDist().inv_cdf(0.5 * (1.0 + confidence)))
    half = z * sem
    return {"mean": mean, "sem": sem, "ci95": half,
            "ci_low": mean - half, "ci_high": mean + half, "n": n}


def aggregate_metrics_ci(per_ep: list[dict], confidence: float = 0.95) -> dict:
    """Aggregate per-episode metric dicts with means and confidence intervals.

    Args:
        per_ep: list of metric dicts as produced by :func:`compute_metrics`,
            one per Monte Carlo episode.
        confidence: coverage probability for the intervals.

    Returns:
        ``{metric: confidence_interval(values)}`` for every metric key present
        in the first episode dict.
    """
    if not per_ep:
        return {}
    out: dict[str, dict] = {}
    for k in per_ep[0]:
        out[k] = confidence_interval([m.get(k) for m in per_ep], confidence)
    return out


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
        "Pd (threat coverage)": float(m.get("threat_intercept_ratio", 0.0)),
        "1 - Pfa (rel.)": float(1.0 - m.get("false_alarm_rate", 0.0) / far_max),
        "Avg intercept rate": float(m.get("intercept_rate", 0.0)),
        "Reward (rel.)": float(max(0.0, m.get("avg_reward", 0.0)) / rew_max),
        "Prediction accuracy": float(m.get("pct_correct_predictions", 0.0)),
        "Intercept-time error (rel.)":
            float(max(0.0, 1.0 - m.get("avg_intercept_time_error", 0.0) / err_max)),
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
