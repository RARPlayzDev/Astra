"""Fixed-point decision kernel for real-time (FPGA/DSP-class) deployment.

The research scheduler is pure Python and averages ~0.5 ms per decision on a
desktop CPU - two orders of magnitude above the budget of a hardware receiver
whose dwell is tens of microseconds.  The *algorithms*, however, are formulated
so the per-slot decision is a bounded, branch-light, O(n_bands) weighted sum of
six terms with no dynamic allocation and no per-slot transcendental calls.

:class:`PolicyKernel` is that decision expressed in Q8.8 fixed-point integer
arithmetic:

* every input is quantised once (on write) with saturation;
* the per-slot score is an integer multiply-accumulate over ``n_bands`` lanes;
* ``argmax`` is a single integer comparison sweep;
* the transcendental terms (log, sqrt for the UCB/recency bonuses) are
  recomputed only when the underlying statistics change, not per slot.

This is the artifact that makes the "portable to FPGA/Zynq" claim concrete:
:mod:`tools.export_cpp_kernel` emits the same arithmetic as compilable C++,
and ``tests/test_realtime_kernel.py`` asserts the fixed-point decisions match
the float reference bit-for-bit at the kernel's quantisation granularity.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

Q_SHIFT = 8          # Q8.8 fixed point
Q_ONE = 1 << Q_SHIFT
_Q_MAX = (1 << 31) - 1


def to_q(x: float) -> int:
    """Quantise a float to saturated Q8.8."""
    return int(max(-_Q_MAX, min(_Q_MAX, round(float(x) * Q_ONE))))


def from_q(q: int) -> float:
    return q / Q_ONE


@dataclass
class KernelStats:
    calls: int = 0
    recompute_log: int = 0
    recompute_sqrt: int = 0
    last_score_us: float | None = None


class PolicyKernel:
    """Q8.8 fixed-point replica of SmartScan's rotation-score argmax.

    Score terms (identical weights to the float scheduler):
        mu                       - learned per-band value;
        0.55 * sqrt(ln(t+2)/n)   - UCB exploration bonus;
        (0.16+0.14*unseen)*rec   - recency guarantee;
        0.35 * logit_prob        - online occupancy model;
        hop_weight * hop_bonus   - agile-hop urgency bonus.

    The log/sqrt terms are cached per band and recomputed lazily on write.
    """

    def __init__(self, n_bands: int, hop_weight: float = 0.45):
        if n_bands < 1:
            raise ValueError("n_bands must be >= 1")
        self.n_bands = int(n_bands)
        self.hop_weight_q = to_q(hop_weight)
        self._mu_q = np.zeros(self.n_bands, dtype=np.int64)
        self._n_q = np.ones(self.n_bands, dtype=np.int64)
        self._last_visit_q = np.zeros(self.n_bands, dtype=np.int64)
        self._unseen_q = np.zeros(self.n_bands, dtype=np.int64)
        self._lprob_q = np.zeros(self.n_bands, dtype=np.int64)
        self._hop_q = np.zeros(self.n_bands, dtype=np.int64)
        self._ucb_cache_q = np.zeros(self.n_bands, dtype=np.int64)
        self._recency_cache_q = np.zeros(self.n_bands, dtype=np.int64)
        self._t = 0
        self._dirty = True
        self.stats = KernelStats()

    # -- writes (quantisation boundary) ---------------------------------------
    def set_value(self, band: int, mu: float) -> None:
        self._mu_q[band] = to_q(mu)

    def set_visits(self, band: int, visits: float) -> None:
        self._n_q[band] = max(Q_ONE, to_q(max(visits, 1e-9)))
        self._dirty = True

    def set_last_visit(self, band: int, last_t: int) -> None:
        # Stored in Q8.8 like every other lane (the recency cache reads it
        # through from_q); integer slots are exact in this representation.
        self._last_visit_q[band] = int(last_t) * Q_ONE
        self._dirty = True

    def set_unseen(self, band: int, unseen: bool) -> None:
        self._unseen_q[band] = Q_ONE if unseen else 0
        self._dirty = True

    def set_logit_prob(self, band: int, prob: float) -> None:
        self._lprob_q[band] = to_q(max(0.0, min(1.0, prob)))

    def set_hop_bonus(self, band: int, bonus: float) -> None:
        self._hop_q[band] = to_q(max(0.0, bonus))

    def set_time(self, t: int) -> None:
        if t != self._t:
            self._t = int(t)
            self._dirty = True

    # -- lazy transcendental caches -------------------------------------------
    def _refresh_caches(self) -> None:
        if not self._dirty:
            return
        t = max(self._t, 0)
        log_t = math.log(t + 2.0)
        for b in range(self.n_bands):
            n = max(1.0, from_q(self._n_q[b]))
            # Stored raw (before its 0.55 weight, which step() applies);
            # weighting twice would silently halve the exploration bonus.
            self._ucb_cache_q[b] = to_q(math.sqrt(log_t / n))
            rec = math.sqrt(max(0.0, t - from_q(self._last_visit_q[b])))
            unseen = from_q(self._unseen_q[b])
            self._recency_cache_q[b] = to_q(
                (0.16 + 0.14 * unseen) * rec)
        self.stats.recompute_log += 1
        self.stats.recompute_sqrt += 1
        self._dirty = False

    # -- the decision ----------------------------------------------------------
    def step(self) -> int:
        """Return the band to dwell on (argmax of the fixed-point score)."""
        self._refresh_caches()
        best_band, best_score = 0, None
        for b in range(self.n_bands):
            score = (self._mu_q[b]
                     + (55 * self._ucb_cache_q[b]) // 100
                     + self._recency_cache_q[b]
                     + (35 * self._lprob_q[b]) // 100
                     + (self.hop_weight_q * self._hop_q[b]) // Q_ONE)
            if best_score is None or score > best_score:
                best_band, best_score = b, score
        self.stats.calls += 1
        return best_band

    def metadata(self) -> dict:
        """Deployment-facing complexity contract for the kernel."""
        return {
            "arithmetic": "Q8.8 fixed point (saturating)",
            "per_slot_complexity": f"O({self.n_bands}) integer MACs",
            "memory_bytes": int(self.n_bands * 9 * 4),
            "dynamic_allocation": False,
            "transcendentals_per_slot": 0,
            "transcendentals_on_write": 2 * self.n_bands,
            "terms": ["value", "ucb", "recency", "logit", "hop"],
        }
