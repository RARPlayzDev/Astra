from __future__ import annotations

import numpy as np


def _z_at(h, p):
    ph = 2.0 * np.pi * (h % p) / p
    c = np.mean(np.exp(1j * ph))
    r = np.abs(c)
    return len(h) * r * r, r


def best_period(hit_times, min_p=10, max_p=450, n_candidates=64):
    h = np.asarray(sorted(hit_times), dtype=float)
    n = len(h)
    if n < 5:
        return None
    periods = np.unique(np.linspace(min_p, max_p, n_candidates).astype(int))
    zb, rb, pb = -1.0, 0.0, None
    for p in periods:
        z, r = _z_at(h, p)
        if z > zb:
            zb, rb, pb = z, r, int(p)
    for p in range(max(min_p, pb - n_candidates), min(max_p, pb + n_candidates) + 1):
        z, r = _z_at(h, p)
        if z > zb:
            zb, rb, pb = z, r, int(p)
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
    p = est["period"]
    on_center = est["phase"] * p
    k = np.ceil((t_now - on_center) / p)
    s = on_center + k * p
    while s <= t_now:
        s += p
    return int(round(s))


def predict_on(est, t, guard_frac=0.2, width_cap=None):
    p = est["period"]
    width = float(np.clip(p * est.get("spread", 0.1), 2.0, p * 0.35))
    if width_cap is not None:
        width = min(width, p * float(width_cap))
    width *= (1 + guard_frac)
    d = (t - est["phase"] * p) % p
    if d < 0:
        d += p
    return d <= width or d >= p - 2
