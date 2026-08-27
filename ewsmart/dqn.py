"""Deep Q-Network agent implemented in pure NumPy.

A compact MLP Q-function with experience replay and a target network - the
canonical DQN ingredients - kept dependency-free so the whole project runs on
NumPy alone.  The state is a per-band feature summary; actions are band choices.
"""
from __future__ import annotations

import numpy as np


def _he(fan_in: int, fan_out: int, rng: np.random.Generator) -> np.ndarray:
    return rng.normal(0.0, np.sqrt(2.0 / fan_in), size=(fan_in, fan_out))


class MLP:
    """Two-hidden-layer ReLU network with a linear head."""

    def __init__(self, dims: tuple, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.W = [_he(dims[i], dims[i + 1], rng) for i in range(len(dims) - 1)]
        self.b = [np.zeros(d) for d in dims[1:]]

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass; returns activations of every layer."""
        acts = [x]
        for W, b in zip(self.W[:-1], self.b[:-1]):
            acts.append(np.maximum(acts[-1] @ W + b, 0.0))
        acts.append(acts[-1] @ self.W[-1] + self.b[-1])
        return acts

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


class DQNAgent:
    """DQN agent over discrete band-selection actions.

    Args:
        n_bands: number of actions / bands.
        state_dim: flattened per-step feature dimension.
        hidden: hidden layer widths.
        gamma: discount factor.
        lr: SGD learning rate.
        batch: replay minibatch size.
        target_sync: steps between hard target-network syncs.
        eps_start/min/decay: epsilon-greedy schedule (decayed per episode).
    """

    def __init__(self, n_bands: int, state_dim: int, hidden=(64, 64),
                 gamma: float = 0.9, lr: float = 5e-4, batch: int = 32,
                 target_sync: int = 400, eps_start: float = 0.30,
                 eps_min: float = 0.10, eps_decay: float = 0.97, seed: int = 0):
        self.n_bands = n_bands
        self.state_dim = state_dim
        self.gamma, self.lr, self.batch = gamma, lr, batch
        self.target_sync = target_sync
        self.eps, self.eps_min, self.eps_decay = eps_start, eps_min, eps_decay
        self.rng = np.random.default_rng(seed)
        self.q = MLP((state_dim, *hidden, n_bands), seed=seed)
        self.target = MLP((state_dim, *hidden, n_bands), seed=seed + 1)
        self.target.copy_from(self.q)
        self.buffer = ReplayBuffer(50000, state_dim)
        self.step_count = 0

    def act(self, state: np.ndarray, greedy: bool = False) -> int:
        """Epsilon-greedy action selection."""
        if not greedy and self.rng.random() < self.eps:
            return int(self.rng.integers(self.n_bands))
        q = self.q.forward(state[None, :])[-1][0]
        return int(np.argmax(q))

    def observe(self, s, a, r, s2, done: bool) -> None:
        """Store one transition and run one training step when warm."""
        self.buffer.add(s, a, r, s2, done)
        self.step_count += 1
        if len(self.buffer) >= 500:
            self._train_step()
        if self.step_count % self.target_sync == 0:
            self.target.copy_from(self.q)

    def end_episode(self) -> None:
        """Called at episode end: decay exploration and soft-sync target."""
        self.eps = max(self.eps_min, self.eps * self.eps_decay)
        self.target.soft_update(self.q, tau=0.05)

    def _train_step(self) -> None:
        s, a, r, s2, d = self.buffer.sample(self.batch, self.rng)
        q_next = self.target.forward(s2)[-1]
        max_next = q_next.max(axis=1)
        target = r + self.gamma * max_next * (1.0 - d)
        acts = self.q.forward(s)
        out = acts[-1]
        pred = out[np.arange(len(a)), a]
        err = pred - np.clip(target, -5.0, 10.0)
        delta = err / len(a)
        grad_out = np.zeros_like(out)
        grad_out[np.arange(len(a)), a] = delta
        grads = self._backprop(acts, grad_out)
        for i in range(len(self.q.W)):
            self.q.W[i] -= self.lr * grads["W"][i]
            self.q.b[i] -= self.lr * grads["b"][i]

    def _backprop(self, acts: list[np.ndarray], grad_out: np.ndarray) -> dict:
        gW, gb = [None] * len(self.q.W), [None] * len(self.q.b)
        g = grad_out
        for i in range(len(self.q.W) - 1, -1, -1):
            gW[i] = acts[i].T @ g
            gb[i] = g.sum(axis=0)
            if i > 0:
                g = (g @ self.q.W[i].T) * (acts[i] > 0)
        return {"W": gW, "b": gb}

    def get_weights(self) -> dict:
        """Return a serialisable snapshot of all learned parameters."""
        return {"W": [w.copy() for w in self.q.W], "b": [b.copy() for b in self.q.b],
                "eps": self.eps}

    def set_weights(self, w: dict) -> None:
        """Restore parameters from :meth:`get_weights` output."""
        self.q.W = [np.asarray(x) for x in w["W"]]
        self.q.b = [np.asarray(x) for x in w["b"]]
        self.target.copy_from(self.q)
        self.eps = w.get("eps", self.eps)
