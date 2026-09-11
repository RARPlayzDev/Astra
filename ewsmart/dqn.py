"""Deep Q-Network agent implemented in pure NumPy.

A compact MLP Q-function with experience replay and a target network - the
canonical DQN ingredients - kept dependency-free so the whole project runs on
NumPy alone.  The state is a per-band feature summary; actions are band choices.

Implements the modern DQN recipe, all of it ablatable via DQNAgent flags:

* Double DQN targets (van Hasselt et al., 2016);
* Dueling value/advantage architecture (Wang et al., 2016);
* Prioritised experience replay with importance-sampling weights
  (Schaul et al., 2016);
* Polyak-averaged soft target updates on every gradient step;
* Huber loss with per-sample IS weighting.
"""
from __future__ import annotations

import numpy as np


def _he(fan_in: int, fan_out: int, rng: np.random.Generator) -> np.ndarray:
    return rng.normal(0.0, np.sqrt(2.0 / fan_in),
                      size=(fan_in, fan_out)).astype(np.float32)


class MLP:
    """Dueling Q-network: ReLU trunk with value and advantage heads.

    Weights are kept in ``float32`` throughout: the state vector produced by
    ``build_state`` is already ``float32`` and the replay buffer stores
    ``float32``, so single precision avoids per-matmul upcasts and roughly
    halves the cost of the training step (the perf-critical path).

    Trunk weights and both heads share the single ``W`` / ``b`` lists (value
    head last), so weight snapshots and target-network updates remain uniform
    over the whole parameter set.
    """

    def __init__(self, dims: tuple, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.n_actions = int(dims[-1])
        self.n_trunk = len(dims) - 2  # layers before the dueling heads
        self.W = [_he(dims[i], dims[i + 1], rng) for i in range(self.n_trunk)]
        self.b = [np.zeros(d, dtype=np.float32)
                  for d in dims[1:self.n_trunk + 1]]
        feat = int(dims[self.n_trunk])  # last trunk width
        self.W.append(_he(feat, self.n_actions, rng))  # advantage head
        self.W.append(_he(feat, 1, rng))               # value head
        self.b.append(np.zeros(self.n_actions, dtype=np.float32))
        self.b.append(np.zeros(1, dtype=np.float32))

    def _features(self, x: np.ndarray, keep_acts: bool):
        acts, a = [x], x
        for i in range(self.n_trunk):
            a = np.maximum(a @ self.W[i] + self.b[i], 0.0)
            if keep_acts:
                acts.append(a)
        return (acts, a) if keep_acts else a

    def forward(self, x: np.ndarray) -> tuple[list, np.ndarray, np.ndarray]:
        """Forward pass; returns (trunk activations, advantages, state value)."""
        acts, feats = self._features(x, True)
        A = feats @ self.W[self.n_trunk] + self.b[self.n_trunk]
        V = feats @ self.W[self.n_trunk + 1] + self.b[self.n_trunk + 1]
        return acts, A, V

    def q_values(self, x: np.ndarray) -> np.ndarray:
        """Greedy Q-values for states (no activation bookkeeping).

        Q(s, a) = V(s) + A(s, a) - mean_a' A(s, a')  (dueling composition).
        Faster than :meth:`forward` for inference: avoids building the
        per-layer activation list on every decision tick.
        """
        feats = self._features(x, False)
        A = feats @ self.W[self.n_trunk] + self.b[self.n_trunk]
        V = feats @ self.W[self.n_trunk + 1] + self.b[self.n_trunk + 1]
        return V + A - A.mean(axis=-1, keepdims=True)

    def copy_from(self, other: "MLP") -> None:
        """Hard-update weights from another network."""
        self.W = [w.copy() for w in other.W]
        self.b = [b.copy() for b in other.b]

    def soft_update(self, other: "MLP", tau: float = 0.005) -> None:
        """Polyak-averaged update toward ``other``."""
        for i in range(len(self.W)):
            self.W[i] += tau * (other.W[i] - self.W[i])
            self.b[i] += tau * (other.b[i] - self.b[i])


class ReplayBuffer:
    """Fixed-size uniform experience replay buffer."""

    def __init__(self, capacity: int, state_dim: int):
        self.capacity = capacity
        self.s = np.zeros((capacity, state_dim), dtype=np.float32)
        self.a = np.zeros(capacity, dtype=np.int64)
        self.r = np.zeros(capacity, dtype=np.float32)
        self.s2 = np.zeros((capacity, state_dim), dtype=np.float32)
        self.d = np.zeros(capacity, dtype=np.float32)
        self.idx = 0
        self.full = False

    def add(self, s, a, r, s2, d) -> None:
        i = self.idx
        self.s[i], self.a[i], self.r[i], self.s2[i], self.d[i] = s, a, r, s2, d
        self.idx = (self.idx + 1) % self.capacity
        self.full = self.full or self.idx == 0

    def __len__(self) -> int:
        return self.capacity if self.full else self.idx

    def sample(self, batch: int, rng: np.random.Generator):
        n = len(self)
        idx = rng.integers(0, n, size=min(batch, n))
        return self.s[idx], self.a[idx], self.r[idx], self.s2[idx], self.d[idx]


class PrioritizedReplayBuffer(ReplayBuffer):
    """Proportional prioritised experience replay (PER, Schaul et al. 2016).

    Transitions with larger absolute TD error are sampled more often
    (priority ``p = |TD| + eps``, sampled proportionally with replacement);
    importance-sampling (IS) weights correct the resulting distribution
    shift, with the correction annealed from ``beta0`` toward 1 as training
    progresses.  New transitions start at the current maximum priority so
    recent experience is not systematically under-sampled.

    The ``prio ** alpha`` weights are maintained incrementally (vectorised
    over the minibatch indices on every priority update), so a sample costs
    one O(n) sum + cumsum over cached weights instead of re-powdering the
    whole priority array - which keeps the per-decision latency inside the
    real-time budget even when the buffer holds tens of thousands of
    transitions.
    """

    def __init__(self, capacity: int, state_dim: int, alpha: float = 0.6,
                 eps: float = 1e-4):
        super().__init__(capacity, state_dim)
        self.alpha, self.eps = alpha, eps
        self.prio = np.full(capacity, eps, dtype=np.float64)
        self._w = np.zeros(capacity, dtype=np.float64)   # prio ** alpha
        self._max_prio = 1.0

    def add(self, s, a, r, s2, d) -> None:
        self._w[self.idx] = self._max_prio ** self.alpha
        self.prio[self.idx] = self._max_prio
        super().add(s, a, r, s2, d)

    def sample(self, batch: int, rng, beta: float = 1.0):
        n = len(self)
        w_n = self._w[:n]
        total = float(w_n.sum())
        m = min(batch, n)
        idx = np.searchsorted(
            np.cumsum(w_n), rng.random(m) * total, side="right")
        idx = np.minimum(idx, n - 1).astype(np.int64)
        probs = w_n[idx] / total
        w = (n * probs) ** (-beta)
        w /= w.max()
        return (self.s[idx], self.a[idx], self.r[idx], self.s2[idx],
                self.d[idx], w.astype(np.float32), idx)

    def update_priorities(self, idx, td_err) -> None:
        idx = np.asarray(idx, dtype=np.int64)
        td = np.abs(td_err) + self.eps
        self._w[idx] = td ** self.alpha
        self.prio[idx] = td
        m = float(td.max())
        if m > self._max_prio:
            self._max_prio = m


class DQNAgent:
    """DQN agent over discrete band-selection actions (modern recipe).

    Args:
        n_bands: number of actions / bands.
        state_dim: flattened per-step feature dimension.
        hidden: hidden layer widths.
        gamma: discount factor.
        lr: SGD learning rate.
        batch: replay minibatch size.
        target_sync: retained for compatibility; when > 0 a hard target sync
            also fires every ``target_sync`` steps on top of the per-step
            soft update.
        train_every: run one gradient step every N observations (staggered
            training keeps per-step decision latency low; N > 1 amortises
            the replay update).
        eps_start/min/decay: epsilon-greedy schedule (decayed per episode).
        double: enable Double-DQN targets.
        per: enable prioritised experience replay.
        tau: Polyak soft-update rate for the target network.
        per_alpha / per_beta0: PER prioritisation exponent and initial IS
            exponent (annealed linearly to 1 over 20k steps).
    """

    def __init__(self, n_bands: int, state_dim: int, hidden=(64, 64),
                 gamma: float = 0.9, lr: float = 5e-4, batch: int = 32,
                 target_sync: int = 400, train_every: int = 3,
                 eps_start: float = 0.30,
                 eps_min: float = 0.10, eps_decay: float = 0.97, seed: int = 0,
                 double: bool = True, per: bool = True, tau: float = 0.005,
                 per_alpha: float = 0.6, per_beta0: float = 0.4):
        if not isinstance(train_every, (int, np.integer)) or train_every < 1:
            raise ValueError(f"train_every must be a positive integer, "
                             f"got {train_every!r}")
        self.n_bands = n_bands
        self.state_dim = state_dim
        self.gamma, self.lr, self.batch = gamma, lr, batch
        self.target_sync = target_sync
        self.train_every = int(train_every)
        self.eps, self.eps_min, self.eps_decay = eps_start, eps_min, eps_decay
        self.double, self.per, self.tau = bool(double), bool(per), float(tau)
        self.per_beta0 = float(per_beta0)
        self.rng = np.random.default_rng(seed)
        dims = (state_dim, *hidden, n_bands)
        self.q = MLP(dims, seed=seed)
        self.target = MLP(dims, seed=seed + 1)
        self.target.copy_from(self.q)
        self.buffer = (PrioritizedReplayBuffer(50000, state_dim,
                                               alpha=per_alpha)
                       if per else ReplayBuffer(50000, state_dim))
        self.step_count = 0
        self.visit_counts = np.ones(n_bands)
        self.band_rewards = np.zeros(n_bands)

    def act(self, state: np.ndarray, greedy: bool = False) -> int:
        """Epsilon-greedy with UCB warm-up before the replay buffer fills."""
        if not greedy and self.rng.random() < self.eps:
            return int(self.rng.integers(self.n_bands))
        # Before enough experience, bias toward under-explored bands
        if len(self.buffer) < self.batch:
            bonus = 0.6 * np.sqrt(np.log(self.step_count + 2) / self.visit_counts)
            ucb = self.band_rewards / self.visit_counts + bonus
            return int(np.argmax(ucb))
        q = self.q.q_values(state[None, :])[0]
        return int(np.argmax(q))

    def observe(self, s, a, r, s2, done: bool) -> None:
        """Store one transition and run one training step when warm.

        Gradient steps are staggered (every ``train_every`` observations) to
        keep the per-step decision latency under the real-time budget.
        """
        self.buffer.add(s, a, r, s2, done)
        self.step_count += 1
        self.visit_counts[a] += 1
        self.band_rewards[a] += r
        if len(self.buffer) >= self.batch \
                and self.step_count % self.train_every == 0:
            self._train_step()
        if self.target_sync and self.step_count % self.target_sync == 0:
            self.target.copy_from(self.q)

    def end_episode(self) -> None:
        """Called at episode end: decay exploration and soft-sync target."""
        self.eps = max(self.eps_min, self.eps * self.eps_decay)
        self.target.soft_update(self.q, tau=0.05)
        self.visit_counts = np.ones(self.n_bands)
        self.band_rewards = np.zeros(self.n_bands)

    def _train_step(self) -> None:
        if self.per:
            beta = min(1.0, self.per_beta0
                       + self.step_count / 20000.0 * (1.0 - self.per_beta0))
            s, a, r, s2, d, w, idx = self.buffer.sample(self.batch, self.rng,
                                                        beta)
        else:
            s, a, r, s2, d = self.buffer.sample(self.batch, self.rng)
            w = np.ones(len(a), dtype=np.float32)
            idx = None
        if self.double:
            # Double DQN: online net picks the next action, target net scores
            # it - removes the over-estimation bias of the vanilla max.
            a_next = np.argmax(self.q.q_values(s2), axis=1)
            max_next = self.target.q_values(s2)[np.arange(len(a)), a_next]
        else:
            max_next = self.target.q_values(s2).max(axis=1)
        target = np.clip(r + self.gamma * max_next * (1.0 - d), -5.0, 10.0)
        acts, A, V = self.q.forward(s)
        qsa = V + A - A.mean(axis=1, keepdims=True)
        pred = qsa[np.arange(len(a)), a]
        err = pred - target
        # Huber loss derivative with per-sample IS weights.
        g = (w * np.clip(err, -1.0, 1.0) / len(a)).astype(np.float32)
        self._backprop(acts, a, g)
        if idx is not None:
            self.buffer.update_priorities(idx, err)
        self.target.soft_update(self.q, tau=self.tau)

    def _backprop(self, acts: list[np.ndarray], a: np.ndarray,
                  g: np.ndarray) -> None:
        """Backprop the weighted Huber gradient through the dueling network.

        Q = V + A - mean(A) gives dQ/dA = g * (onehot - 1/N) (through the
        mean subtraction) and dQ/dV = g (the value head enters Q with unit
        weight for every action).
        """
        q = self.q
        n_act, n_trunk = q.n_actions, q.n_trunk
        rows = np.arange(len(a))
        gA = np.broadcast_to(g[:, None], (len(a), n_act)) \
            * (-np.float32(1.0 / n_act))
        gA = gA.astype(np.float32)
        gA[rows, a] += g
        gV = g[:, None].astype(np.float32)
        feats = acts[-1]
        g_feat = gA @ q.W[n_trunk].T + gV @ q.W[n_trunk + 1].T
        g_feat = g_feat * (feats > 0)  # through the last trunk ReLU
        gW = [None] * len(q.W)
        gb = [None] * len(q.b)
        gW[n_trunk], gb[n_trunk] = feats.T @ gA, gA.sum(axis=0)
        gW[n_trunk + 1], gb[n_trunk + 1] = feats.T @ gV, gV.sum(axis=0)
        for i in range(n_trunk - 1, -1, -1):
            gW[i], gb[i] = acts[i].T @ g_feat, g_feat.sum(axis=0)
            if i > 0:
                g_feat = (g_feat @ q.W[i].T) * (acts[i] > 0)
        for i in range(len(q.W)):
            q.W[i] -= self.lr * gW[i]
            q.b[i] -= self.lr * gb[i]

    def get_weights(self) -> dict:
        """Return a serialisable snapshot of all learned parameters."""
        return {"W": [w.copy() for w in self.q.W], "b": [b.copy() for b in self.q.b],
                "eps": self.eps}

    def set_weights(self, w: dict) -> None:
        """Restore parameters from :meth:`get_weights` output."""
        self.q.W = [np.asarray(x, dtype=np.float32) for x in w["W"]]
        self.q.b = [np.asarray(x, dtype=np.float32) for x in w["b"]]
        self.target.copy_from(self.q)
        self.eps = w.get("eps", self.eps)
