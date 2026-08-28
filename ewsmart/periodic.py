from __future__ import annotations

import math

import numpy as np


def _z_at(h, p):
    ph = 2.0 * np.pi * (h % p) / p
    c = np.mean(np.exp(1j * ph))
    r = np.abs(c)
    return len(h) * r * r, r


def _z_scan(h: np.ndarray, periods: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vectorised Rayleigh-style z-scores of ``h`` for many candidate periods.

    Equivalent to calling :func:`_z_at` for every period, but computed with a
    single broadcast complex exponential instead of a Python loop - the hot
    path of every phase-lock attempt.
    """
    ph = 2.0 * np.pi * np.mod.outer(h, periods) / periods
    c = np.exp(1j * ph).mean(axis=0)
    r = np.abs(c)
    return len(h) * r * r, r


def best_period(hit_times, min_p=10, max_p=450, n_candidates=64,
                max_hits=160):
    h = np.asarray(sorted(hit_times), dtype=float)
    if len(h) > max_hits:
        # Only the most recent hits matter for an ongoing rhythm; capping
        # bounds the cost of every scan.
        h = h[-max_hits:]
    n = len(h)
    if n < 5:
        return None
    periods = np.unique(
        np.linspace(min_p, max_p, n_candidates).astype(float))
    z_arr, r_arr = _z_scan(h, periods)
    i = int(np.argmax(z_arr))
    zb, rb, pb = float(z_arr[i]), float(r_arr[i]), int(periods[i])
    # Deep-miss early exit: the fine scan can lift z above the acceptance
    # threshold only marginally, so skip it when the coarse scan is far off
    # (most attempts fail here, and the scan is the expensive part).
    if zb < 2.5:
        return None
    fine = np.arange(max(min_p, pb - n_candidates),
                     min(max_p, pb + n_candidates) + 1, dtype=float)
    z_fine, r_fine = _z_scan(h, fine)
    j = int(np.argmax(z_fine))
    if z_fine[j] > zb:
        zb, rb, pb = float(z_fine[j]), float(r_fine[j]), int(fine[j])
    if zb < 3.9:
        return None
    ang = np.angle(np.mean(np.exp(2j * np.pi * (h % pb) / pb))) % (2 * np.pi)
    phase = ang / (2 * np.pi)
    spread = _phase_spread(h, pb)
    if not 1.0 / pb <= spread <= 0.35:
        return None
    return {"period": pb, "phase": phase, "R": float(rb),
            "z": float(zb), "spread": spread, "n": n}


def _phase_spread(hit_times, period):
    ph = (np.asarray(hit_times) % period) / period
    ph = np.sort(ph)
    d = np.diff(np.concatenate([ph, [ph[0] + 1.0]]))
    i = int(np.argmax(d))
    ordered = np.roll(ph, -(i + 1))
    span = ordered[-1] - ordered[0]
    if span > 0.5:
        span = 1.0 - (d.max())
    else:
        span = span + min(ordered[0], 1 - ordered[-1]) * 0
    return float(max(span, 1.0 / period))


def next_on_start(est, t_now):
    # Pure-Python arithmetic (no NumPy scalars): called in the per-tick hot
    # path of the schedulers, where NumPy call overhead dominates.
    p = float(est["period"])
    on_center = est["phase"] * p
    k = math.ceil((t_now - on_center) / p)
    s = on_center + k * p
    while s <= t_now:
        s += p
    return int(round(s))


def predict_on(est, t, guard_frac=0.2, width_cap=None):
    # Pure-Python arithmetic (no NumPy scalars): called once per locked band
    # per tick, so NumPy scalar-op overhead (~10x) is avoided.
    p = float(est["period"])
    width = p * float(est.get("spread", 0.1))
    if width < 2.0:
        width = 2.0
    hi = p * 0.35
    if width > hi:
        width = hi
    if width_cap is not None:
        cap = p * float(width_cap)
        if width > cap:
            width = cap
    width *= (1 + guard_frac)
    d = (t - est["phase"] * p) % p
    if d < 0:
        d += p
    return d <= width or d >= p - 2
