"""Learned behaviour arbitration for the SmartScan scheduler.

The teardown's sharpest ML criticism is that SmartScan's *decision core* is
classical: five hand-written branches (lock pursuit, probe, burst camping,
recency rotation, hop pursuit) with only shallow online learning at the
edges.  :class:`BehaviourArbiter` adds a genuine learning component to the
core: a linear-upper-confidence-bound (LinUCB) contextual bandit that
learns, online and from hits/misses alone, *which behaviour to trust in
which situation*.

Design constraints (each one exists so the bandit cannot destabilise a
proven policy):

* **safe action mask** - the arbiter only chooses among behaviour branches
  whose preconditions currently hold; it can never invent a behaviour;
* **regret-bounded exploration** - LinUCB's alpha·sqrt(x' A^-1 x) term is
  exactly optimistic-under-uncertainty, not a hack;
* **cross-episode persistence** - ``get_state`` / ``set_state`` rehydrate
  the A/b statistics through the scheduler's existing memory mechanism;
* **shadow mode** - with ``control=False`` the arbiter only observes and
  learns (its learned preferences are inspectable), while the fixed policy
  keeps flying the mission; ``control=True`` hands it the decision, gated
  by a confidence margin over the incumbent heuristic.
"""
from __future__ import annotations

import math

import numpy as np

ACTIONS = ("pursue", "probe", "camp", "rotate", "survey")


class BehaviourArbiter:
    """LinUCB contextual bandit over the scheduler's behaviour modes."""

    def __init__(self, n_features: int, alpha: float = 0.35,
                 rng: np.random.Generator | None = None):
        if n_features < 1:
            raise ValueError("n_features must be >= 1")
        self.n_features = int(n_features)
        self.alpha = float(alpha)
        self.rng = rng
        self._a: dict[str, np.ndarray] = {
            m: np.eye(self.n_features) for m in ACTIONS}
        self._b: dict[str, np.ndarray] = {
            m: np.zeros(self.n_features) for m in ACTIONS}
        self.n_updates = 0

    # -- decision --------------------------------------------------------------
    def choose(self, features: np.ndarray,
               allowed: tuple[str, ...] = ACTIONS) -> str:
        """Pick a behaviour: LinUCB score = theta'x + alpha*sqrt(x' A^-1 x)."""
        x = np.asarray(features, dtype=float)
        best, best_score = allowed[0], None
        for mode in allowed:
            a_inv = np.linalg.inv(self._a[mode])
            theta = a_inv @ self._b[mode]
            score = float(theta @ x + self.alpha * math.sqrt(
                max(float(x @ a_inv @ x), 1e-12)))
            if best_score is None or score > best_score:
                best, best_score = mode, score
        return best

    def score(self, features: np.ndarray) -> dict:
        """All modes' UCB scores (inspectable, for the audit trail)."""
        x = np.asarray(features, dtype=float)
        out = {}
        for mode in ACTIONS:
            a_inv = np.linalg.inv(self._a[mode])
            theta = a_inv @ self._b[mode]
            out[mode] = round(float(theta @ x + self.alpha * math.sqrt(
                max(float(x @ a_inv @ x), 1e-12))), 4)
        return out

    # -- learning ----------------------------------------------------------------
    def update(self, features: np.ndarray, mode: str, reward: float) -> None:
        """Fold one observed (context, behaviour, reward) into the model."""
        if mode not in ACTIONS:
            raise ValueError(f"unknown behaviour mode {mode!r}")
        x = np.asarray(features, dtype=float)
        self._a[mode] += np.outer(x, x)
        self._b[mode] += float(reward) * x
        self.n_updates += 1

    # -- persistence ---------------------------------------------------------------
    def get_state(self) -> dict:
        return {"n_features": self.n_features, "alpha": self.alpha,
                "n_updates": self.n_updates,
                "a": [self._a[m].tolist() for m in ACTIONS],
                "b": [self._b[m].tolist() for m in ACTIONS]}

    def set_state(self, state: dict) -> None:
        n = int(state["n_features"])
        if n != self.n_features:
            raise ValueError("feature count mismatch")
        for i, m in enumerate(ACTIONS):
            self._a[m] = np.asarray(state["a"][i], dtype=float)
            self._b[m] = np.asarray(state["b"][i], dtype=float)
        self.n_updates = int(state.get("n_updates", 0))


def behaviour_features(*, t_frac: float, recon_done: float,
                       credible_locks: int, hop_predictability: float,
                       recent_hit_rate: float, unseen_bands: int) -> np.ndarray:
    """The context vector the arbiter conditions on (all O(1) statistics)."""
    return np.asarray([
        float(np.clip(t_frac, 0.0, 1.0)),
        float(np.clip(recon_done, 0.0, 1.0)),
        float(np.clip(credible_locks / 8.0, 0.0, 1.0)),
        float(np.clip(hop_predictability, 0.0, 1.0)),
        float(np.clip(recent_hit_rate, 0.0, 1.0)),
        float(np.clip(unseen_bands / 24.0, 0.0, 1.0)),
    ])
