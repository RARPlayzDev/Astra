import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))
"""Hard execution-time benchmark: every scheduler must average < 1 ms per
decision (select + predict + update) over a 10,000-tick episode."""
import time

import numpy as np
import pytest

from ewsmart.environment import RFEnvironment
from ewsmart.receiver import ESReceiver
from ewsmart.runner import make_schedulers

N_TICKS = 10_000
N_BANDS = 24
LIMIT_MS = 1.0
WARMUP_TICKS = 300


def _benchmark(sched, seed: int = 3) -> float:
    """Average milliseconds per scheduler decision over one full episode.

    Only the scheduler's own work (``select`` + ``predict`` + ``update``) is
    timed; the receiver dwell in between is real but is not a scheduler cost.
    """
    env = RFEnvironment(n_bands=N_BANDS, T=N_TICKS, seed=seed)
    rx = ESReceiver(env, seed=seed + 1)
    sched.reset(horizon=N_TICKS)
    # Warm-up (allocator / numpy caches) on a short prefix, not benchmarked.
    for t in range(WARMUP_TICKS):
        b = sched.select(t)
        res = rx.dwell(b, t)
        sched.update(t, b, res, 0.2)
    total = 0.0
    pc = time.perf_counter
    for t in range(WARMUP_TICKS, N_TICKS):
        a = pc()
        b = sched.select(t)
        c = pc()
        res = rx.dwell(b, t)
        d = pc()
        pred = sched.predict(t, b)
        e = pc()
        r = 0.3 if (res.hit and not res.false_alarm) else -0.05
        sched.update(t, b, res, r)
        f = pc()
        total += (c - a) + (e - d) + (f - e)
        assert 0 <= b < N_BANDS and pred in (True, False)
    return total * 1000.0 / (N_TICKS - WARMUP_TICKS)


@pytest.mark.parametrize("sched", make_schedulers(N_BANDS, (0, 1), seed=7),
                         ids=lambda s: s.name)
def test_scheduler_decision_under_1ms(sched):
    ms = _benchmark(sched)
    print(f"\n[{sched.name}] {ms:.4f} ms/decision over "
          f"{N_TICKS - WARMUP_TICKS} ticks (limit {LIMIT_MS} ms)")
    assert ms < LIMIT_MS, (
        f"{sched.name} averaged {ms:.4f} ms per decision over "
        f"{N_TICKS} ticks, exceeding the {LIMIT_MS} ms hard limit")


def test_full_episode_wall_clock_sane():
    """The heaviest scheduler must finish a 10k-tick episode in < N_TICKS ms."""
    scheds = make_schedulers(N_BANDS, (0, 1), seed=7)
    for s in scheds:
        ms = _benchmark(s)
        assert ms * N_TICKS < N_TICKS * LIMIT_MS


if __name__ == "__main__":
    scheds = make_schedulers(N_BANDS, (0, 1), seed=7)
    print(f"Average decision latency over {N_TICKS} ticks "
          f"(hard limit {LIMIT_MS} ms):")
    worst = 0.0
    for s in scheds:
        ms = _benchmark(s)
        worst = max(worst, ms)
        flag = "OK " if ms < LIMIT_MS else "FAIL"
        print(f"  [{flag}] {s.name:<22} {ms:.4f} ms")
    assert worst < LIMIT_MS, "performance requirement violated"
    print(f"\nAll schedulers under {LIMIT_MS} ms per decision")
