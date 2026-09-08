"""Receiver scheduling policies.

All schedulers share a common interface:

* ``reset(horizon=None)`` - prepare for a new episode.
* ``select(t) -> int`` - choose the band to dwell on at slot ``t``.
* ``update(t, band, res, r=0.0)`` - learn from the dwell result and reward.
* ``predict(t, band) -> bool`` - belief whether ``band`` is occupied at ``t``
  (used for the % correct predictions figure of merit).
* ``end_episode()`` / ``learnable`` - cross-episode training hooks.
"""
from __future__ import annotations

import math

import numpy as np
from collections import deque

from . import periodic
from .dqn import DQNAgent
from .exceptions import (ConfigurationError, InvalidBandError,
                         SimulationBoundsError, InvalidDwellResultError,
                         InvalidRewardError)



def ang_dist(a1: float, a2: float) -> float:
    """Circular distance between two angles in degrees (0..180)."""
    return abs((float(a1) - float(a2) + 180.0) % 360.0 - 180.0)


class BaseScheduler:
    """Common scheduler interface.

    All concrete schedulers validate their inputs against the branded
    exception hierarchy in :mod:`ewsmart.exceptions`:

    * ``n_bands <= 0`` / negative horizons -> :class:`ConfigurationError`
    * out-of-range band indices            -> :class:`InvalidBandError`
    * negative time slots                  -> :class:`SimulationBoundsError`
    * non-numeric / NaN rewards            -> :class:`InvalidRewardError`
    * result objects missing attributes    -> :class:`InvalidDwellResultError`
    """

    name = "base"
    learnable = False

    def __init__(self, n_bands: int, seed: int = 0):
        if not isinstance(n_bands, (int, np.integer)) or isinstance(n_bands, bool) \
                or n_bands < 1:
            raise ConfigurationError(
                f"{type(self).__name__}: n_bands must be a positive integer, "
                f"got {n_bands!r}")
        self.n_bands = int(n_bands)
        self.rng = np.random.default_rng(seed)

    @staticmethod
    def _check_horizon(horizon: int | None) -> None:
        if horizon is not None and (not isinstance(horizon, (int, np.integer))
                                    or horizon < 0):
            raise ConfigurationError(
                f"horizon must be a non-negative integer or None, got "
                f"{horizon!r}")

    def _check_t(self, t: int) -> None:
        if t < 0:
            raise SimulationBoundsError(
                f"{type(self).__name__}.select: time slot must be >= 0, "
                f"got {t!r}")

    def _check_band(self, band: int) -> None:
        if not 0 <= band < self.n_bands:
            raise InvalidBandError(
                f"{type(self).__name__}: band index {band!r} out of range "
                f"[0, {self.n_bands})")

    @staticmethod
    def _check_reward(r) -> float:
        try:
            v = float(r)
        except (TypeError, ValueError) as exc:
            raise InvalidRewardError(
                f"reward must be a real number, got {r!r}") from exc
        if not math.isfinite(v):
            raise InvalidRewardError(f"reward must be finite, got {r!r}")
        return v

    @staticmethod
    def _check_res(res) -> tuple[bool, tuple]:
        """Validate a dwell result object; return ``(hit, detections)``."""
        try:
            hit = bool(res.hit)
            fa = bool(res.false_alarm)
            dets = res.detections
        except AttributeError as exc:
            raise InvalidDwellResultError(
                f"dwell result {type(res).__name__} is missing required "
                f"attributes (band, t, hit, false_alarm, detections): {exc}"
                ) from exc
        return hit and not fa, dets

    def reset(self, horizon: int | None = None) -> None:
        """Prepare internal state for a new episode of ``horizon`` slots."""
        self._check_horizon(horizon)

    def select(self, t: int) -> int:
        """Return the band to observe at slot ``t``."""
        raise NotImplementedError

    def update(self, t: int, band: int, res, r: float = 0.0) -> None:
        """Update internal statistics from one dwell."""
        self._check_band(band)
        self._check_reward(r)
        self._check_res(res)

    def predict(self, t: int, band: int) -> bool:
        """Belief that ``band`` is occupied at slot ``t``."""
        return False

    def end_episode(self) -> None:
        """Finalise an episode (training hooks override this)."""


class SequentialSweep(BaseScheduler):
    """Classic open-loop cyclic sweep across every band in order."""

    name = "openloop-sequential"

    def select(self, t: int) -> int:
        self._check_t(t)
        return int(t % self.n_bands)


class RandomScan(BaseScheduler):
    """Open-loop uniform random band selection each dwell."""

    name = "openloop-random"

    def select(self, t: int) -> int:
        self._check_t(t)
        return int(self.rng.integers(self.n_bands))


class PrioritySweep(BaseScheduler):
    """Open-loop sweep prioritising pre-mission known threat bands.

    Models a receiver driven by prior (possibly stale) intelligence: priority
    bands are visited every cycle, remaining bands fill the gaps.

    Raises:
        InvalidBandError: if any priority band is outside ``[0, n_bands)``.
    """

    name = "openloop-priority"

    def __init__(self, n_bands: int, priority_bands: tuple | list, seed: int = 0):
        super().__init__(n_bands, seed)
        prio = list(priority_bands)
        for b in prio:
            if not 0 <= b < self.n_bands:
                raise InvalidBandError(
                    f"priority band {b!r} out of range [0, {self.n_bands})")
        self.route = prio + [b for b in range(n_bands) if b not in set(prio)]

    def select(self, t: int) -> int:
        self._check_t(t)
        return self.route[t % len(self.route)]


class UCBScheduler(BaseScheduler):
    """Discounted UCB1 bandit over band rewards.

    Serves as the pure-exploitation reference: it converges onto the single
    highest-yield band and progressively abandons sparse emitters, illustrating
    why naive adaptivity fails the coverage objective.
    """

    name = "bandit-ucb"

    def reset(self, horizon: int | None = None) -> None:
        self._check_horizon(horizon)
        self.n = np.ones(self.n_bands)
        self.mu = np.full(self.n_bands, 1e-3)

    def select(self, t: int) -> int:
        self._check_t(t)
        bonus = 0.6 * np.sqrt(np.log(t + 2) / self.n)
        return int(np.argmax(self.mu + bonus))

    def update(self, t: int, band: int, res, r: float = 0.0) -> None:
        self._check_band(band)
        r = self._check_reward(r)
        self._check_res(res)
        self.n[band] += 1
        self.mu[band] += (r - self.mu[band]) / self.n[band]

    def predict(self, t: int, band: int) -> bool:
        return bool(self.mu[band] > 0.15)


FEATURE_DIM = 5


class LinearQLearning(BaseScheduler):
    """Linear-approximation Q-learning over hand-crafted band features.

    Trained across episodes on observed rewards; kept as an interpretable
    ML baseline (the DQN below is the nonlinear counterpart).
    """

    name = "rl-linear-q"
    learnable = True

    def __init__(self, n_bands: int, seed: int = 0, alpha: float = 0.01,
                 gamma: float = 0.9, eps: float = 0.3,
                 eps_min: float = 0.05, eps_decay: float = 0.95):
        super().__init__(n_bands, seed)
        self.theta = np.zeros(FEATURE_DIM)
        self.alpha, self.gamma = alpha, gamma
        self.eps, self.eps_min, self.eps_decay = eps, eps_min, eps_decay
        self.reset()

    def reset(self, horizon: int | None = None) -> None:
        self._check_horizon(horizon)
        self.disc_hit = np.zeros(self.n_bands)
        self.disc_n = np.zeros(self.n_bands)
        self.last_visit = np.full(self.n_bands, -100.0)

    def end_episode(self) -> None:
        self.eps = max(self.eps_min, self.eps * self.eps_decay)

    def _features(self, band: int, t: int) -> np.ndarray:
        recency = 1.0 / (1.0 + max(0.0, t - self.last_visit[band]))
        prior = self.disc_hit[band] / (self.disc_n[band] + 0.25)
        conf = np.sqrt(self.disc_n[band]) / (1 + np.sqrt(self.disc_n[band]))
        return np.array([1.0, prior * conf, recency,
                         self.disc_hit[band] / 10.0, 0.0])

    def _feature_matrix(self, t: int) -> np.ndarray:
        """Vectorised ``(n_bands, FEATURE_DIM)`` feature matrix at slot ``t``."""
        recency = 1.0 / (1.0 + np.maximum(0.0, t - self.last_visit))
        prior = self.disc_hit / (self.disc_n + 0.25)
        sqrt_n = np.sqrt(self.disc_n)
        conf = sqrt_n / (1.0 + sqrt_n)
        X = np.empty((self.n_bands, FEATURE_DIM))
        X[:, 0] = 1.0
        X[:, 1] = prior * conf
        X[:, 2] = recency
        X[:, 3] = self.disc_hit / 10.0
        X[:, 4] = 0.0
        return X

    def _q_all(self, t: int) -> np.ndarray:
        return self._feature_matrix(t) @ self.theta

    def select(self, t: int) -> int:
        self._check_t(t)
        if self.rng.random() < self.eps:
            return int(self.rng.integers(self.n_bands))
        return int(np.argmax(self._q_all(t)))

    def update(self, t: int, band: int, res, r: float = 0.0) -> None:
        self._check_band(band)
        r = self._check_reward(r)
        hit, _ = self._check_res(res)
        x = self._features(band, t)
        q = float(self.theta @ x)
        decay = 0.98
        if hit:
            self.disc_hit[band] = decay * self.disc_hit[band] + 1.0
            self.disc_n[band] = decay * self.disc_n[band] + 1.0
        else:
            self.disc_hit[band] *= decay
            self.disc_n[band] = decay * self.disc_n[band]
        self.last_visit[band] = t
        td_err = float(np.clip(r - q, -5.0, 5.0))
        self.theta += self.alpha * td_err * x

    def get_weights(self) -> dict:
        return {"theta": self.theta.copy(), "eps": self.eps}

    def set_weights(self, w: dict) -> None:
        self.theta = np.asarray(w["theta"])
        self.eps = w.get("eps", self.eps)


def build_state(band_stats: dict, n_bands: int) -> np.ndarray:
    """Assemble the flattened DQN state from per-band statistics.

    Features per band (8): normalised mean reward, visit confidence, visit
    recency, time since last hit, locked flag, predicted-on flag, persistent
    flag, burst flag.
    """
    feats = np.zeros((n_bands, 8), dtype=np.float32)
    feats[:, 0] = np.clip(np.asarray(band_stats["mu"], dtype=np.float32), -1, 2) / 2.0
    feats[:, 1] = np.sqrt(np.asarray(band_stats["n"], dtype=np.float32))
    feats[:, 1] /= max(1.0, feats[:, 1].max())
    feats[:, 2] = np.asarray(band_stats["recency"], dtype=np.float32)
    feats[:, 3] = np.asarray(band_stats["since_hit"], dtype=np.float32)
    feats[:, 4] = np.asarray(band_stats["locked"], dtype=np.float32)
    feats[:, 5] = np.asarray(band_stats["pred_on"], dtype=np.float32)
    feats[:, 6] = np.asarray(band_stats["persistent"], dtype=np.float32)
    feats[:, 7] = np.asarray(band_stats["burst"], dtype=np.float32)
    return feats.reshape(-1)


class DQNScheduler(BaseScheduler):
    """Deep RL scheduler: DQN over per-band feature states.

    The state embeds live band statistics *and* learned periodicity features:
    a lightweight phase-lock estimator runs on the agent's own hit stream so
    the Q-function can condition on "this band is predicted ON now" - a hybrid
    of deep value learning and model-based signal processing.  Experience is
    replayed with a target network (see :mod:`ewsmart.dqn`).
    """

    name = "rl-dqn"
    learnable = True

    def __init__(self, n_bands: int, seed: int = 0, state_dim: int | None = None,
                 lock_hits: int = 5, **agent_kwargs):
        super().__init__(n_bands, seed)
        state_dim = state_dim or 8 * n_bands
        self.lock_hits = lock_hits
        self.agent = DQNAgent(n_bands, state_dim, seed=seed, **agent_kwargs)
        self.reset()

    def reset(self, horizon: int | None = None) -> None:
        self._check_horizon(horizon)
        self.mu = np.full(self.n_bands, 0.01)
        self.n = np.ones(self.n_bands)
        self.last_visit = np.zeros(self.n_bands)
        self.last_hit = np.full(self.n_bands, -10 ** 9)
        self.band_hits = [[] for _ in range(self.n_bands)]
        self.est: dict[int, dict] = {}
        self.new_hits = np.zeros(self.n_bands)
        self._lock_try: dict[int, int] = {}
        self._cached_state: np.ndarray | None = None
        self._cached_t: int = -10 ** 9
        self.prev_state: np.ndarray | None = None
        self.prev_action: int | None = None

    def end_episode(self) -> None:
        self.agent.end_episode()
        self.prev_state = None
        self.prev_action = None
        self._cached_state = None
        self._cached_t = -10 ** 9

    def _maybe_lock(self, band: int, t: int) -> None:
        """Lightweight phase-lock on the agent's own hit stream.

        A per-band cooldown between estimation attempts bounds the cost of
        repeatedly scanning non-periodic bands that keep producing hits.
        """
        if len(self.band_hits[band]) < self.lock_hits:
            return
        if band in self.est and self.new_hits[band] < 4:
            return
        if t - self._lock_try.get(band, -10 ** 9) < 60:
            return
        self._lock_try[band] = t
        est = periodic.best_period([t for t, _, _ in self.band_hits[band]])
        if est is not None:
            self.est[band] = est
            self.new_hits[band] = 0

    def _state(self, t: int) -> np.ndarray:
        # select(t+1) rebuilds the exact state update(t) produced; caching
        # removes that duplicate construction from the hot path.
        if self._cached_state is not None and self._cached_t == t:
            return self._cached_state
        recency = 1.0 / (1.0 + np.maximum(0.0, t - self.last_visit))
        since_hit = np.clip((t - self.last_hit) / 1000.0, 0.0, 3.0)
        locked = np.zeros(self.n_bands)
        pred_on = np.zeros(self.n_bands)
        for b, e in self.est.items():
            locked[b] = 1.0
            if periodic.predict_on(e, t):
                pred_on[b] = 1.0
        s = build_state({"mu": self.mu, "n": self.n, "recency": recency,
                         "since_hit": since_hit, "locked": locked,
                         "pred_on": pred_on,
                         "persistent": np.zeros(self.n_bands),
                         "burst": np.zeros(self.n_bands)}, self.n_bands)
        self._cached_state = s
        self._cached_t = t
        return s

    def select(self, t: int) -> int:
        self._check_t(t)
        s = self._state(t)
        self.prev_state = s
        self.prev_action = self.agent.act(s)
        return self.prev_action

    def update(self, t: int, band: int, res, r: float = 0.0) -> None:
        self._check_band(band)
        r = self._check_reward(r)
        hit, _ = self._check_res(res)
        s2 = self._state(t + 1)
        if self.prev_state is not None and self.prev_action is not None:
            self.agent.observe(self.prev_state, self.prev_action,
                               float(np.clip(r, -0.5, 3.0)), s2, False)
        self.n[band] += 1
        self.mu[band] += (r - self.mu[band]) / self.n[band]
        self.mu *= 0.999
        self.last_visit[band] = t
        if hit:
            self.last_hit[band] = t
            for snr, aoa in res.detections:
                self.band_hits[band].append((t, snr, aoa))
            # Bound the fingerprint history so phase-lock rescans stay O(1)
            # in the number of recent hits rather than growing unbounded.
            if len(self.band_hits[band]) > 400:
                del self.band_hits[band][:-200]
            self.new_hits[band] += len(res.detections) or 1
            self._maybe_lock(band, t)

    def get_weights(self) -> dict:
        w = self.agent.get_weights()
        return w

    def set_weights(self, w: dict) -> None:
        self.agent.set_weights(w)


class _BandLogit:
    """Online logistic regression over per-band dwell features (SGD).

    A second learned model inside SmartScan: while phase locks capture
    periodic rhythm, this calibrates a per-band occupancy probability from
    the receiver's own observation history (hit-rate EMA, dwell interval,
    time since last detection).  It powers occupancy predictions for bands
    without a validated lock and adds a learned bonus to the exploit score.
    """

    _NFEAT = 5

    def __init__(self, lr: float = 0.08):
        self.w = np.zeros(self._NFEAT)
        self.lr = lr
        self.n = 0
        self.ema_hit = 0.1
        self.ema_dt = 20.0
        self.last_hit_t = -100.0
        self.last_visit_t = 0.0

    def features(self, t: int) -> np.ndarray:
        dt = max(1.0, float(t - self.last_visit_t))
        return np.array([1.0, self.ema_hit,
                         min(2.0, dt / max(self.ema_dt, 1.0)),
                         min(2.0, (t - self.last_hit_t) / 120.0),
                         min(1.0, self.n / 40.0)])

    def observe(self, t: int, hit: bool) -> float:
        """Update on one dwell; returns the probability predicted *before* it."""
        x = self.features(t)
        p = float(1.0 / (1.0 + np.exp(-float(x @ self.w))))
        y = 1.0 if hit else 0.0
        self.w += self.lr * (y - p) * x
        self.n += 1
        self.ema_hit = 0.85 * self.ema_hit + 0.15 * (y if hit else 0.0)
        if self.n > 1:
            self.ema_dt = 0.8 * self.ema_dt + 0.2 * (t - self.last_visit_t)
        if hit:
            self.last_hit_t = t
        self.last_visit_t = t
        return p

    def prob(self, t: int) -> float:
        if self.n < 8:
            return 0.0
        x = self.features(t)
        return float(1.0 / (1.0 + np.exp(-float(x @ self.w))))


class SmartScanScheduler(BaseScheduler):
    """The proposed hybrid adaptive scan strategy.

    Behaviours multiplexed by learned confidence:

    1. recon sweep - fast full-band survey to bootstrap all statistics;
    2. cued pursuit - credible phase locks are dwelt at predicted ON windows;
    3. predict-and-probe - unproven candidate locks are probed at predicted
       window centres, bounded by miss counters;
    4. burst characterisation - an isolated detection on a quiet stream triggers
       a camping burst through its next cycle to gather lock evidence; streams
       are separated by SNR fingerprints so co-channel emitters stay distinct,
       and proven-persistent streams are blacklisted;
    5. value-weighted rotation - discounted UCB + recency with an exploitation
       ramp that progressively shifts effort toward the highest-value bands;
    6. agile-hop anticipation - a strictly causal, per-stream band-transition
       model (learned only from detected SNR/AOA fingerprints) biases the
       rotation toward the bands an agile emitter is most likely to hop to
       next, with urgency decaying since the stream's last detection.

    Locks failing validation (repeated misses at predicted ON windows) are
    deleted automatically, keeping false locks cheap.
    """

    name = "smart-scan"
    learnable = True

    def __init__(self, n_bands: int, seed: int = 0, explore_eps: float = 0.08,
                 lock_hits: int = 5, recon_factor: int = 12,
                 burst_horizon: int = 480, exploit_ramp: float = 0.60,
                 value_mode: str = "learned", hop_weight: float = 0.45,
                 hop_min_obs: int = 3):
        super().__init__(n_bands, seed)
        if value_mode not in ("learned", "heuristic", "flat"):
            raise ValueError(
                f"value_mode must be 'learned', 'heuristic' or 'flat', "
                f"got {value_mode!r}")
        self.value_mode = value_mode
        self.hop_weight = float(hop_weight)
        self.hop_min_obs = int(hop_min_obs)
        self.explore_eps = explore_eps * 0.6  # slightly less random waste
        self.lock_hits = lock_hits
        self.recon_steps = recon_factor * n_bands
        self.burst_horizon = burst_horizon
        self.exploit_ramp = exploit_ramp
        self.horizon: int | None = None
        self.reset()

    def reset(self, horizon: int | None = None) -> None:
        self._check_horizon(horizon)
        self.horizon = horizon
        self.mu = np.full(self.n_bands, 0.01)
        self.n = np.ones(self.n_bands)
        self.last_visit = np.zeros(self.n_bands)
        self.visit_times = [[] for _ in range(self.n_bands)]
        self.hit_times = [[] for _ in range(self.n_bands)]
        self.band_hits = [[] for _ in range(self.n_bands)]
        self.est: dict[int, dict] = {}
        self.miss = np.zeros(self.n_bands)
        self.pred_visits: dict[int, int] = {}
        self.pred_hits: dict[int, int] = {}
        self.new_hits = np.zeros(self.n_bands)
        self.burst: dict[int, int] = {}
        self.burst_start: dict[int, int] = {}
        self.persistent: set[int] = set()
        self.dense_count = np.zeros(self.n_bands)
        self.iso_streams: dict = {}
        self._lock_try: dict[int, int] = {}
        # --- knowledge-state predictor (hard-confirmation policy) ---
        self.visit_hits: list[deque] = [
            deque(maxlen=10) for _ in range(self.n_bands)]
        # --- online logistic occupancy model (second learned component) ---
        self.logit = [_BandLogit() for _ in range(self.n_bands)]
        # --- causal agile-hop model (third learned component) ---
        # Per-stream (SNR/AOA fingerprint) band-transition counts learned only
        # from detections observed so far; never from hidden emitter state.
        self.hop_last_band: dict[tuple, int] = {}
        self.hop_last_t: dict[tuple, int] = {}
        self.hop_dt: dict[tuple, float] = {}
        self.hop_succ: dict[tuple, dict[int, dict[int, int]]] = {}

    def end_episode(self) -> None:
        pass

    @staticmethod
    def _cluster_hits(points: list[tuple], tol_db: float = 1.5,
                      tol_aoa: float = 12.0) -> list[list[tuple]]:
        """Group detections into emitter streams by SNR *and* AOA fingerprints.

        Each point is ``(t, snr_db, aoa_deg)``.  Co-channel emitters are
        separated when either fingerprint differs, giving the scheduler
        spatial awareness: two streams sharing an AOA are likely the same
        physical emitter (or a family), regardless of band.

        Vectorised with NumPy: the input is sorted once, then cluster
        boundaries are found with a single vectorised comparison of the
        SNR differences and circular AOA distances (no Python loop over
        points).
        """
        if not points:
            return []
        pts = sorted(points, key=lambda p: p[1])
        arr = np.asarray(pts, dtype=float)
        if arr.ndim == 1:
            arr = arr[None, :]
        n = len(pts)
        if n == 1:
            return [list(pts)]
        snr = arr[:, 1]
        new_cluster = np.empty(n, dtype=bool)
        new_cluster[0] = True
        d_snr = np.abs(np.diff(snr))
        if arr.shape[1] >= 3:
            d_aoa = np.abs((np.diff(arr[:, 2]) + 180.0) % 360.0 - 180.0)
            new_cluster[1:] = (d_snr > tol_db) | (d_aoa > tol_aoa)
        else:
            new_cluster[1:] = d_snr > tol_db
        bounds = np.flatnonzero(new_cluster)
        return [pts[a:b] for a, b in zip(bounds, list(bounds[1:]) + [n])]

    def _maybe_lock(self, band: int, t: int) -> None:
        """Attempt (or refine) a periodic phase-lock from clustered hits.

        A per-band cooldown between estimation attempts bounds the cost of
        repeatedly scanning non-periodic bands that keep producing hits.
        """
        if len(self.band_hits[band]) < self.lock_hits:
            return
        if band in self.est and self.new_hits[band] < 4:
            return
        if t - self._lock_try.get(band, -10 ** 9) < 60:
            return
        self._lock_try[band] = t
        total_visits = max(1, len(self.visit_times[band]))
        best = None
        for cl in self._cluster_hits(self.band_hits[band]):
            if len(cl) < self.lock_hits:
                continue
            if len(cl) > 0.55 * total_visits:
                continue
            est = periodic.best_period([t for t, _, _ in cl])
            if est is None:
                continue
            if est["period"] < 15:
                continue
            est["aoa"] = float(np.mean([a for _, _, a in cl]))
            if best is None or est["z"] > best["z"]:
                best = est
        if best is not None:
            self.est[band] = best
            self.miss[band] = 0
            self.pred_visits[band] = 0
            self.pred_hits[band] = 0
            self.new_hits[band] = 0

    def _credible(self, band: int) -> bool:
        """Whether a lock has demonstrated predictive value."""
        v = self.pred_visits.get(band, 0)
        h = self.pred_hits.get(band, 0)
        return v >= 3 and h >= 0.4 * v

    def _validate_locks(self, t: int, band: int, hit: bool) -> None:
        if band not in self.est:
            return
        if not periodic.predict_on(self.est[band], t):
            return
        self.pred_visits[band] = self.pred_visits.get(band, 0) + 1
        if hit:
            self.pred_hits[band] = self.pred_hits.get(band, 0) + 1
            self.miss[band] = 0
        else:
            self.miss[band] += 1
            if self.miss[band] >= 5:
                del self.est[band]
                self.hit_times[band] = self.hit_times[band][-3:]
                self.band_hits[band] = self.band_hits[band][-6:]
                self.miss[band] = 0
                self.pred_visits.pop(band, None)
                self.pred_hits.pop(band, None)

    def _update_burst(self, t: int, band: int, snr: float, aoa: float) -> None:
        """Burst-camp logic: characterise repeated isolated sparse streams.

        A burst (dwell camping through the next emitter cycle) is only armed
        after two mutually-isolated detections on the same SNR+AOA fingerprint,
        so single stray hits never divert the scan.  Streams that show dense
        multi-window activity are blacklisted as persistent.
        """
        if band in self.est or band in self.persistent:
            self.burst.pop(band, None)
            return
        times = sorted(tt for tt, s, a in self.band_hits[band][:-1]
                       if abs(snr - s) <= 1.5 and ang_dist(aoa, a) <= 12.0)
        groups: list[list[int]] = []
        for tt in times:
            if groups and tt - groups[-1][-1] <= 5:
                groups[-1].append(tt)
            else:
                groups.append([tt])
        if len(groups) >= 2 and groups[-1][0] - groups[-2][-1] <= 25:
            self.dense_count[band] += 1
            if self.dense_count[band] >= 2:
                self.persistent.add(band)
                self.burst.pop(band, None)
            return
        isolated = not times or t - times[-1] > 30
        stream_key = (band, round(snr * 2.0), int(aoa // 15.0))
        if not isolated:
            self.iso_streams.pop(stream_key, None)
            return
        self.iso_streams[stream_key] = t
        same_stream_iso = sum(1 for (b2, s2, a2), tt in self.iso_streams.items()
                              if b2 == band and abs(s2 - round(snr * 2.0)) <= 1
                              and abs(a2 - int(aoa // 15.0)) <= 1)
        if same_stream_iso >= 2:
            self.burst[band] = t + self.burst_horizon
            self.burst_start.setdefault(band, t)
            if len(self.burst) > 3:
                oldest = min(self.burst, key=self.burst_start.get)
                self.burst.pop(oldest)
                self.burst_start.pop(oldest, None)

    def _next_on_start(self, est: dict, t: int) -> float:
        p = est["period"]
        c = est["phase"] * p
        k = np.ceil((t - c) / p)
        return c + max(k, 0.0) * p

    def _exploit_prob(self, t: int) -> float:
        """Ramping greedy-exploitation probability after recon."""
        if self.horizon is None or self.exploit_ramp <= 0:
            return 0.0
        progress = min(1.0, max(0.0, (t - self.recon_steps)) /
                       max(1.0, 0.5 * (self.horizon - self.recon_steps)))
        return self.exploit_ramp * progress

    def _value_estimates(self) -> np.ndarray:
        """Learned per-band value estimates, ablated by ``value_mode``.

        * ``learned``  - full hybrid: reward means learned from hits/misses;
        * ``heuristic``- value estimates zeroed (pure UCB + recency ranking);
        * ``flat``     - no learned signal at all (uniform rotation exploit).
        """
        if self.value_mode == "learned":
            return self.mu
        return np.zeros(self.n_bands)

    # -------------------------------------------------- agile-hop prediction
    def _observe_hop(self, t: int, band: int, snr: float, aoa: float) -> None:
        """Feed one resolved detection into the causal per-stream hop model.

        Streams are keyed by the same SNR/AOA fingerprint used for burst
        characterisation, so a frequency-agile emitter keeps its identity as
        it hops.  A transition is counted only when a detection lands on a
        *different* band than the stream's previous detection, and the time
        between detections is tracked as an exponential-moving average of the
        hop interval (used as an urgency clock in :meth:`_hop_bonus`).
        Strictly causal: only detections seen so far are ever used.
        """
        key = (round(snr * 2.0), int(aoa // 15.0))
        prev = self.hop_last_band.get(key)
        last_t = self.hop_last_t.get(key)
        if prev is not None and last_t is not None and prev != band:
            succ = self.hop_succ.setdefault(key, {}).setdefault(prev, {})
            succ[band] = succ.get(band, 0) + 1
            dt = t - last_t
            if dt > 0:
                m = self.hop_dt.get(key)
                self.hop_dt[key] = float(dt) if m is None \
                    else 0.8 * m + 0.2 * float(dt)
        self.hop_last_band[key] = band
        self.hop_last_t[key] = t
        # Bound memory: keep only the most recently active streams.
        if len(self.hop_last_band) > 48:
            oldest = min(self.hop_last_band, key=self.hop_last_t.get)
            for d in (self.hop_last_band, self.hop_last_t,
                      self.hop_succ, self.hop_dt):
                d.pop(oldest, None)

    def _hop_bonus(self, t: int) -> np.ndarray:
        """Urgency-weighted successor distribution for imminent agile hops.

        For every recently-active stream with mature statistics (>=
        ``hop_min_obs`` observed hops) whose last detection was within about
        one learned hop interval, adds the model's successor probability mass
        to the candidate bands.  Returns zeros when the predictor is ablated
        (``hop_weight <= 0``) - used by the ablation study and tests.
        """
        bonus = np.zeros(self.n_bands)
        if self.hop_weight <= 0 or not self.hop_last_band:
            return bonus
        for key, last_b in self.hop_last_band.items():
            mean_dt = self.hop_dt.get(key)
            if mean_dt is None:
                continue
            dt = t - self.hop_last_t[key]
            if dt < 0 or dt > 2.0 * mean_dt:
                continue  # hop window passed; nothing imminent
            succ = self.hop_succ.get(key, {}).get(last_b)
            if not succ:
                continue
            total = sum(succ.values())
            if total < self.hop_min_obs:
                continue  # not enough evidence yet
            urg = max(0.0, 1.0 - dt / (2.0 * mean_dt))
            mass = urg / total
            for b, c in succ.items():
                if 0 <= b < self.n_bands:
                    bonus[b] += mass * c
        return bonus

    def next_hop_topk(self, band: int, k: int = 3) -> list[int]:
        """Model's most likely successor bands of ``band`` across streams.

        Aggregates the causal transition counts of every tracked stream and
        returns the top-``k`` successor band indices (best first).  Empty
        until at least one hop has been observed from ``band``.
        """
        counts: dict[int, int] = {}
        for succ in self.hop_succ.values():
            row = succ.get(band)
            if row:
                for b, c in row.items():
                    counts[b] = counts.get(b, 0) + c
        return sorted(counts, key=lambda b: -counts[b])[:max(1, k)]

    def select(self, t: int) -> int:
        self._check_t(t)
        if t < self.recon_steps:
            return int(t % self.n_bands)
        mu_eff = self._value_estimates()
        for b, dl in list(self.burst.items()):
            if t >= dl or b in self.est:
                self.burst.pop(b, None)
                self.burst_start.pop(b, None)
        best_probe, best_probe_d, best_lock = None, 10 ** 9, None
        credible = [(b, e) for b, e in self.est.items()
                    if periodic.predict_on(e, t, guard_frac=0.25)
                    and self._credible(b)]
        credible.sort(key=lambda be: -mu_eff[be[0]])
        suppressed: list[tuple[float, int]] = []
        for b, e in credible:
            aoa = e.get("aoa")
            if aoa is not None and any(
                    ang_dist(aoa, a) <= 15.0
                    and abs(e["period"] - p) <= 0.1 * max(p, 1)
                    for a, p in suppressed):
                continue
            if best_lock is None:
                best_lock = b
                if aoa is not None:
                    suppressed.append((aoa, int(e["period"])))
        for b, e in self.est.items():
            if b == best_lock or not periodic.predict_on(e, t, guard_frac=0.25):
                continue
            if self._credible(b):
                continue
            d = abs(t - self._next_on_start(e, t))
            if self.miss[b] < 2 and d <= 2 and d < best_probe_d:
                best_probe, best_probe_d = b, d
        if best_lock is not None:
            return best_lock
        if best_probe is not None:
            return best_probe
        for b, dl in self.burst.items():
            if t < dl and b not in self.est:
                return b
        if self.rng.random() < self.explore_eps:
            return int(self.rng.integers(self.n_bands))
        # Reconnaissance floor: bound the maximum revisit latency of any band
        # so emerging emitters cannot hide behind exploitation of known ones.
        stale = int(np.argmax(t - self.last_visit))
        if t - self.last_visit[stale] > 6 * self.n_bands:
            return stale
        if self.rng.random() < self._exploit_prob(t):
            if self.value_mode == "flat":
                return int(self.rng.integers(self.n_bands))
            return int(np.argmax(mu_eff))
        recency = np.sqrt(np.maximum(0.0, t - self.last_visit))
        unseen = (self.n <= 1).astype(float)
        lprob = (np.array([lg.prob(t) for lg in self.logit])
                 if self.value_mode == "learned"
                 else np.zeros(self.n_bands))
        score = mu_eff + 0.55 * np.sqrt(np.log(t + 2) / self.n) \
            + (0.16 + 0.14 * unseen) * recency + 0.35 * lprob \
            + self.hop_weight * self._hop_bonus(t)
        return int(np.argmax(score))

    def _persistent_confirmed(self, band: int) -> bool:
        """Hard confirmation of an always-on carrier.

        Requires a full window of 10 dwells with >=85% hit rate, or membership
        in the proven-persistent stream set.  Periodic emitters fail this test
        naturally (their duty cycle caps the hit rate), so they are only ever
        predicted through their validated phase-lock windows.
        """
        if band in self.persistent:
            return True
        h = self.visit_hits[band]
        return len(h) == h.maxlen and sum(h) / len(h) >= 0.85

    def predict(self, t: int, band: int) -> bool:
        """Knowledge-state prediction with yield fallback.

        States per band:
          * validated periodic phase-lock -> ON inside a tightly capped window
            derived from the measured spread;
          * confirmed persistent carrier  -> always ON (≥6 dwells, ≥75% hit
            rate, or proven-persistent stream);
          * yield-confirmed              -> ON if ≥3 visits with ≥60% hit
            rate (catches stationary emitters that weren't explicitly locked);
          * otherwise                     -> abstain (predict OFF).
        """
        # 1. Phase-locked periodic emitter
        if band in self.est:
            return periodic.predict_on(self.est[band], t, width_cap=0.18)
        # 2. Confirmed persistent carrier
        if self._persistent_confirmed(band):
            return True
        # 3. Online logistic model (learned occupancy probability)
        if self.value_mode != "learned":
            return False
        return self.logit[band].prob(t) >= 0.65

    def update(self, t: int, band: int, res, r: float = 0.0) -> None:
        self._check_band(band)
        r = self._check_reward(r)
        hit, _ = self._check_res(res)
        self.logit[band].observe(t, hit)
        self.visit_times[band].append(t)
        self.last_visit[band] = t
        # knowledge-state bookkeeping (hard confirmation / demotion)
        self.visit_hits[band].append(1 if hit else 0)
        for snr, aoa in (res.detections if not res.false_alarm else ()):
            self.band_hits[band].append((t, snr, aoa))
            # Bound the fingerprint history (see DQNScheduler.update).
            if len(self.band_hits[band]) > 400:
                del self.band_hits[band][:-200]
            self._update_burst(t, band, snr, aoa)
            self._observe_hop(t, band, snr, aoa)
        if hit:
            self.hit_times[band].append(t)
            self.new_hits[band] += len(res.detections) or 1
            self._maybe_lock(band, t)
        self._validate_locks(t, band, hit)
        self.mu[band] += (r - self.mu[band]) / self.n[band]
        self.mu *= 0.999
        self.n[band] += 1

    def get_state(self) -> dict:
        """Strictly JSON-serialisable snapshot of learned locks and knowledge."""
        est_out = {}
        for b, e in self.est.items():
            est_out[int(b)] = {"period": int(e["period"]),
                               "phase": float(e["phase"]),
                               "spread": float(e["spread"]),
                               "z": float(e["z"]),
                               "R": float(e["R"]),
                               "n": int(e["n"]),
                               "aoa": float(e.get("aoa", -1.0))}
        return {"est": est_out, "persistent": sorted(int(b) for b in self.persistent)}

    def load_state(self, state: dict) -> None:
        """Restore a snapshot produced by :meth:`get_state`."""
        self.est = {int(b): dict(e) for b, e in state["est"].items()}
        self.persistent = set(state.get("persistent", []))


class MetaScheduler(BaseScheduler):
    """Cross-episode meta-learning wrapper for any learnable scheduler.

    Instead of fully clearing the learned state on ``reset()`` (which discards
    all accumulated knowledge), ``MetaScheduler`` saves and restores the
    wrapped scheduler's state via ``get_state()`` / ``load_state()`` so that
    Q-tables, bandit weights, and locked rhythms carry over across episodes.
    This gives the receiver a *warm start* in similar environments, enabling
    rapid few-shot adaptation.
    """

    name = "meta-scan"
    learnable = True

    def __init__(self, inner: BaseScheduler):
        super().__init__(inner.n_bands, 0)
        self.inner = inner
        self._saved_state: dict | None = None

    def reset(self, horizon: int | None = None) -> None:
        # Restore previously persisted state (warm start) if available
        if self._saved_state is not None and hasattr(self.inner, "load_state"):
            self.inner.reset(horizon)
            self.inner.load_state(self._saved_state)
        else:
            self.inner.reset(horizon)

    def select(self, t: int) -> int:
        return self.inner.select(t)

    def update(self, t: int, band: int, res, r: float = 0.0) -> None:
        self.inner.update(t, band, res, r)

    def predict(self, t: int, band: int) -> bool:
        return self.inner.predict(t, band)

    def end_episode(self) -> None:
        # Persist learned state before episode boundary
        if hasattr(self.inner, "get_state"):
            self._saved_state = self.inner.get_state()
        self.inner.end_episode()

    def get_weights(self) -> dict:
        if hasattr(self.inner, "get_weights"):
            return {"inner": self.inner.get_weights(),
                    "saved_state": self._saved_state}
        return {"saved_state": self._saved_state}

    def set_weights(self, w: dict) -> None:
        self._saved_state = w.get("saved_state")
        if "inner" in w and hasattr(self.inner, "set_weights"):
            self.inner.set_weights(w["inner"])
