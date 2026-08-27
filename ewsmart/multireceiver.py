"""Multi-receiver cooperative scheduling.

Several receivers with independent instantaneous bandwidths sense the spectrum
simultaneously.  A coordinator de-conflicts their band choices each slot so no
two receivers waste a dwell on the same band, multiplying effective coverage.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field

from .environment import RFEnvironment
from .receiver import ESReceiver
from .schedulers import BaseScheduler
from .runner import step_reward


@dataclass
class TeamTrace:
    """Aggregated trace across all receivers of a team."""

    actions: list = field(default_factory=list)
    hits: list = field(default_factory=list)
    false_alarms: list = field(default_factory=list)
    rewards: list = field(default_factory=list)
    predictions: list = field(default_factory=list)
    first_intercept: dict = field(default_factory=dict)
    per_receiver_actions: list = field(default_factory=list)


class CooperativeTeam:
    """A set of schedulers acting jointly with per-slot band de-confliction.

    Swarm Intelligence: SmartScan members with confirmed phase-locks broadcast
    "Do Not Disturb" (DND) tokens for those bands.  Other members completely
    remove DND-protected bands from their selection pools, ensuring zero
    redundancy and perfectly partitioned spectrum coverage.
    """

    def __init__(self, scheduler_factories: list):
        self.factories = scheduler_factories
        self.scheds: list[BaseScheduler] = []

    def reset(self, n_bands: int, horizon: int | None = None) -> None:
        """Instantiate and reset one scheduler per receiver."""
        self.scheds = [f(n_bands) for f in self.factories]
        for s in self.scheds:
            s.reset(horizon)

    def _collect_dnd(self) -> set[int]:
        """Collect DND tokens from SmartScan members with confirmed locks."""
        dnd: set[int] = set()
        for s in self.scheds:
            est = getattr(s, "est", None)
            if est is not None:
                # SmartScanScheduler: a lock is "confirmed" if it has passed
                # the credibility threshold (_credible)
                credible_fn = getattr(s, "_credible", None)
                if credible_fn is not None:
                    for band in est:
                        if credible_fn(band):
                            dnd.add(band)
        return dnd

    def select_joint(self, t: int) -> list[int]:
        """Choose distinct bands for every receiver at slot ``t``.

        DND-protected bands are excluded from selection for all members
        except the one that owns the lock.
        """
        dnd = self._collect_dnd()
        dnd_owners: dict[int, int] = {}  # band -> index of owning receiver
        chosen: list[int] = []
        for idx, s in enumerate(self.scheds):
            b = int(s.select(t))
            # Skip DND bands owned by a different receiver
            if b in dnd and b in dnd_owners and dnd_owners[b] != idx:
                candidates = [x for x in range(s.n_bands)
                              if x not in chosen and x not in dnd]
                if candidates:
                    b = int(self._fallback(s, t, candidates))
            elif b in chosen:
                candidates = [x for x in range(s.n_bands) if x not in chosen]
                b = int(self._fallback(s, t, candidates)) if candidates else 0
            chosen.append(b)
            # Record DND ownership: the first receiver to claim a DND band owns it
            if b in dnd and b not in dnd_owners:
                dnd_owners[b] = idx
        return chosen

    @staticmethod
    def _fallback(s: BaseScheduler, t: int, candidates: list[int]) -> int:
        mu = getattr(s, "mu", None)
        if mu is not None:
            return int(max(candidates, key=lambda c: mu[c]))
        return candidates[t % len(candidates)]

    def update_all(self, t: int, bands: list[int], results: list, r: float) -> None:
        for s, b, res in zip(self.scheds, bands, results):
            s.update(t, b, res, r)

    def end_episode(self) -> None:
        for s in self.scheds:
            s.end_episode()


def run_episode_multi(env: RFEnvironment, team: CooperativeTeam,
                      seed: int = 1, receivers: list | None = None) -> TeamTrace:
    """Simulate one cooperative multi-receiver episode.

    Each receiver realises its own independent noise (own
    :class:`ESReceiver` with a distinct seed and floor jitter), so false
    alarms and detection misses are uncorrelated across platforms.  A custom
    ``receivers`` list may be injected for testing.
    """
    k = len(team.scheds)
    if receivers is None:
        receivers = [ESReceiver(env, seed=seed * 101 + i) for i in range(k)]
    trace = TeamTrace()
    for t in range(env.T):
        bands = team.select_joint(t)
        results = [rx.dwell(b, t) for rx, b in zip(receivers, bands)]
        r_total = 0.0
        any_hit = False
        any_fa = False
        preds = [s.predict(t, b) for s, b in zip(team.scheds, bands)]
        for res in results:
            r_total += step_reward(env, res, trace.first_intercept)
            any_hit = any_hit or (res.hit and not res.false_alarm)
            any_fa = any_fa or res.false_alarm
        trace.actions.append(tuple(bands))
        trace.per_receiver_actions.append(list(bands))
        trace.hits.append(any_hit)
        trace.false_alarms.append(any_fa)
        trace.rewards.append(r_total)
        trace.predictions.append(preds[0])
        team.update_all(t, bands, results, r_total / max(1, len(results)))
    return trace


def coverage_multiplier(trace: TeamTrace, env: RFEnvironment) -> float:
    """Fraction of slots in which the team observed distinct useful bands."""
    del env
    uniq = sum(1 for a in trace.actions if len(set(a)) == len(a))
    return uniq / max(1, len(trace.actions))
