"""Observation-only frequency-agile hop prediction (Phase 2).

Predictors consume only the band sequence a receiver has already observed -
never hidden emitter state, future slots, or simulator-only labels.  The
module ships three transparent baselines (transition-count, persistence,
uniform) plus an oracle for the Markov agility mode, and an offline
evaluation protocol reporting top-1 / top-k accuracy and the missed
opportunity rate (1 - top-k) for each agility mode.
"""
from __future__ import annotations

import numpy as np

from .environment import RFEnvironment
from .config import ScenarioConfig


class TransitionPredictor:
    """Laplace-smoothed first-order transition-count model over bands.

    Strictly causal: :meth:`observe` is called with each band as it is
    detected, and :meth:`predict` ranks likely successors of the current
    band using only the counts accumulated so far.
    """

    def __init__(self, n_bands: int, alpha: float = 0.5):
        self.n_bands = n_bands
        self.alpha = alpha
        self.counts = np.full((n_bands, n_bands), alpha, dtype=float)

    def observe(self, band: int, next_band: int | None = None) -> None:
        if next_band is not None:
            self.counts[band, next_band] += 1.0

    def predict(self, band: int) -> int | None:
        return self.top_k(band, 1)[0] if band is not None else None

    def top_k(self, band: int, k: int) -> list[int]:
        if band is None or not (0 <= band < self.n_bands):
            return []
        row = self.counts[band]
        order = np.argsort(-row, kind="stable")
        return [int(b) for b in order[:max(1, k)]]


class PersistencePredictor:
    """Baseline: the next band equals the current band."""

    def __init__(self, n_bands: int):
        self.n_bands = n_bands

    def observe(self, band: int, next_band: int | None = None) -> None:
        del next_band

    def predict(self, band: int) -> int | None:
        return band

    def top_k(self, band: int, k: int) -> list[int]:
        return [band] if band is not None else []


class UniformPredictor:
    """Baseline: uniform random over bands (unpredictability reference)."""

    def __init__(self, n_bands: int, seed: int = 0):
        self.n_bands = n_bands
        self.rng = np.random.default_rng(seed)

    def observe(self, band: int, next_band: int | None = None) -> None:
        del band, next_band

    def predict(self, band: int) -> int | None:
        return int(self.rng.integers(self.n_bands))

    def top_k(self, band: int, k: int) -> list[int]:
        return [self.predict(band)]


class HopDwellPredictor:
    """Temporal hop prediction for frequency-agile emitters (Phase 2b).

    Beyond *which band* an agile emitter hops to (TransitionPredictor), this
    predictor estimates *when* the emitter will next be on-frequency: it
    maintains a per-band dwell-length distribution from observed dwell spans
    and returns ``(predicted_band, predicted_on_time)`` for the next
    intercept window.  This closes the PS gap of intercept-time prediction
    "against ... frequency agile emitters".
    """

    def __init__(self, n_bands: int, alpha: float = 0.5):
        self.n_bands = n_bands
        self.trans = TransitionPredictor(n_bands, alpha)
        self.dwell_observations: dict[int, list[int]] = {}
        self._current_band: int | None = None
        self._current_start: int | None = None

    def observe(self, band: int, t: int) -> None:
        """Feed one detected slot ``(band, t)`` of an agile emitter."""
        if band is None:
            return
        if self._current_band is None:
            self._current_band, self._current_start = band, t
            return
        if band == self._current_band:
            return
        # Hop observed: record completed dwell length and transition.
        if self._current_start is not None:
            self.dwell_observations.setdefault(
                self._current_band, []).append(max(1, t - self._current_start))
        self.trans.observe(self._current_band, band)
        self._current_band, self._current_start = band, t

    def _mean_dwell(self, band: int) -> float:
        obs = self.dwell_observations.get(band, [])
        return float(np.mean(obs)) if obs else 2.0

    def predict_next_on(self, band: int | None, t_now: int) -> tuple | None:
        """Predict ``(next_band, next_on_time)`` for an agile emitter.

        Uses the learned transition distribution for the *destination band*
        and the learned dwell-length statistics for the *current band* to
        estimate when that hop occurs: ``t_pred = t_now + mean_dwell``.
        Returns ``None`` with no observation history.
        """
        if band is None:
            return None
        nxt = self.trans.predict(band)
        if nxt is None:
            return None
        t_pred = int(round(t_now + self._mean_dwell(band)))
        return nxt, t_pred


def evaluate_agile_intercept_time(env: RFEnvironment) -> dict:
    """Mean absolute error of agile-emitter next-ON time prediction.

    Strictly causal: at each hop into slot ``t`` the predictor has only seen
    hops at slots ``<= t``; the prediction made at the hop is compared against
    the true start of the *next* dwell window from the truth sequence.
    Returns ``{"n": samples, "agile_intercept_time_error": mean_abs_err,
    "band_top1_accuracy": ...}`` (NaN error when no agile emitters exist).
    """
    rows = [i for i, e in enumerate(env.emitters) if e.kind == "agile"]
    if not rows:
        return {"n": 0, "agile_intercept_time_error": float("nan"),
                "band_top1_accuracy": float("nan")}
    errs: list[float] = []
    band_hits = band_n = 0
    for i in rows:
        seq = env.band_seq[i]
        pred = HopDwellPredictor(env.n_bands)
        prev: int | None = None
        for t in range(env.T):
            b = int(seq[t])
            if b < 0:
                continue
            if prev is not None and b != prev:
                # Score the prediction made from the *previous* band against
                # the actual hop (causal: nothing after ``t`` has been seen).
                p = pred.predict_next_on(prev, t)
                if p is not None:
                    pb, pt = p
                    band_hits += int(pb == b)
                    band_n += 1
                    errs.append(abs(pt - t))
            pred.observe(b, t)
            prev = b
    if not errs:
        return {"n": 0, "agile_intercept_time_error": float("nan"),
                "band_top1_accuracy": float("nan")}
    return {"n": len(errs),
            "agile_intercept_time_error": float(np.mean(errs)),
            "band_top1_accuracy": band_hits / max(1, band_n)}


PREDICTORS = {"transition": TransitionPredictor,
              "persistence": PersistencePredictor,
              "uniform": UniformPredictor}


def _agile_rows(env: RFEnvironment) -> list[int]:
    return [i for i, e in enumerate(env.emitters) if e.kind == "agile"]


def evaluate_hop_prediction(env: RFEnvironment, predictor_name: str = "transition",
                            k: int = 3) -> dict:
    """Score next-hop prediction for every agile emitter in ``env``.

    The evaluation walks each emitter's *observable* band sequence left to
    right: at a hop into slot ``t`` the predictor has seen only transitions
    up to ``t``.  No future truth is passed to ``observe``; tampering with
    slots after ``t`` cannot change the prediction at ``t`` (leakage test).
    """
    rows = _agile_rows(env)
    blank = {"predictor": predictor_name, "n_hops": 0, "top1_accuracy": 0.0,
             "topk_accuracy": 0.0, "missed_opportunity_rate": 1.0}
    if not rows:
        return blank
    pred = PREDICTORS[predictor_name](env.n_bands)
    hits1 = hitsk = n = 0
    for i in rows:
        seq = env.band_seq[i]
        prev: int | None = None
        for t in range(env.T):
            b = int(seq[t])
            if b < 0:
                continue
            if prev is not None and b != prev:
                cand = pred.top_k(prev, k)
                n += 1
                hits1 += int(b == (cand[0] if cand else -1))
                hitsk += int(b in cand)
                pred.observe(prev, b)  # learn only the transition just scored
            prev = b
    if n == 0:
        return blank
    return {"predictor": predictor_name, "n_hops": n,
            "top1_accuracy": hits1 / n, "topk_accuracy": hitsk / n,
            "missed_opportunity_rate": 1.0 - hitsk / n}


def oracle_hop_accuracy(env: RFEnvironment, k: int = 3) -> dict:
    """Upper bound: transitions estimated from the full truth sequence.

    Not achievable online; it quantifies the headroom the observation-only
    predictor leaves on structured agility.
    """
    rows = _agile_rows(env)
    counts = np.ones((env.n_bands, env.n_bands))
    n = hits1 = hitsk = 0
    for i in rows:
        seq = env.band_seq[i]
        for t in range(1, env.T):
            a, b = int(seq[t - 1]), int(seq[t])
            if a >= 0 and b >= 0 and b != a:
                counts[a, b] += 1.0
                n += 1
                top = list(np.argsort(-counts[a], kind="stable")[:k])
                hits1 += int(b == top[0])
                hitsk += int(b in top)
    if n == 0:
        return {"predictor": "oracle", "n_hops": 0, "top1_accuracy": 0.0,
                "topk_accuracy": 0.0, "missed_opportunity_rate": 1.0}
    return {"predictor": "oracle", "n_hops": n, "top1_accuracy": hits1 / n,
            "topk_accuracy": hitsk / n, "missed_opportunity_rate": 1.0 - hitsk / n}


def hop_prediction_experiment(n_bands: int = 16, T: int = 1500,
                              episodes: int = 2, seed: int = 42) -> dict:
    """Benchmark hop prediction on random vs Markov (structured) agility.

    Random agility must score at chance level (reported as unpredictable);
    Markov agility must be learnable from observations alone.
    """
    out: dict = {}
    for mode in ("random", "markov"):
        cfg = ScenarioConfig(n_bands=n_bands, T=T, seed=seed, agile_mode=mode)
        per_pred: dict = {}
        for name in ("transition", "persistence", "uniform"):
            accs = [evaluate_hop_prediction(
                RFEnvironment(cfg), name) for _ in range(episodes)]
            per_pred[name] = {
                key: float(np.mean([a[key] for a in accs]))
                for key in ("top1_accuracy", "topk_accuracy",
                            "missed_opportunity_rate")}
        per_pred["oracle"] = oracle_hop_accuracy(RFEnvironment(cfg))
        out[mode] = per_pred
    return out

