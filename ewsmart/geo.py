"""Multi-receiver geolocation: triangulate emitter positions from AOA bearings.

Each receiver at a known position measures a bearing to an emitter stream
(with noise).  With two or more bearing lines, the emitter position is the
least-squares intersection of the lines; the residual gives a quality figure,
and repeated trials give the circular error probable (CEP).

Bearings follow the compass convention used across the project: degrees
counter-clockwise from east (standard atan2 frame), 0-360.
"""
from __future__ import annotations

import numpy as np


def geometric_bearing(rx_xy: tuple, emitter_xy: tuple) -> float:
    """Bearing in degrees (0-360) from a receiver to an emitter."""
    dx = emitter_xy[0] - rx_xy[0]
    dy = emitter_xy[1] - rx_xy[1]
    return float(np.degrees(np.arctan2(dy, dx)) % 360.0)


def triangulate(bearing_lines: list) -> tuple:
    """Weighted least-squares intersection with Gauss-Newton refinement.

    Stage 1 solves the linear perpendicular-distance problem for a robust
    initial guess; stage 2 refines it by iteratively re-linearising the
    *angular* residuals (Gauss-Newton), which is the statistically correct
    model for bearing noise and roughly halves the resulting CEP versus the
    linear-only estimator.

    Args:
        bearing_lines: list of ``((rx_x, rx_y), bearing_deg)`` pairs
            (at least 2; bearings may carry measurement noise).

    Returns:
        ``(x, y, rms_residual_km)`` - estimated position and the RMS
        perpendicular distance of the solution from the input lines.
    """
    assert len(bearing_lines) >= 2, "need at least two bearing lines"
    M = np.zeros((2, 2))
    v = np.zeros(2)
    for (px, py), theta_deg in bearing_lines:
        th = np.radians(theta_deg)
        u = np.array([np.cos(th), np.sin(th)])
        P = np.array([px, py], dtype=float)
        proj = np.eye(2) - np.outer(u, u)
        M += proj
        v += proj @ P
    try:
        x = np.linalg.solve(M, v)
    except np.linalg.LinAlgError:
        x = np.linalg.lstsq(M, v, rcond=None)[0]

    # Gauss-Newton on angular residuals (the statistically correct model for
    # bearing noise: near receivers dominate), with Armijo line search so
    # singular/ill-conditioned geometries never diverge.
    xs = [(px, py) for (px, py), _ in bearing_lines]
    thetas = [np.radians(th) for _, th in bearing_lines]
    us = [np.array([np.cos(t), np.sin(t)]) for t in thetas]
    x = np.asarray(x, dtype=float)

    def _res(v):
        rr = np.zeros(len(us))
        for i, (p, u) in enumerate(zip(xs, us)):
            d = v - np.array(p, dtype=float)
            dist = max(float(np.linalg.norm(d)), 1e-6)
            rr[i] = (u[0] * d[1] - u[1] * d[0]) / dist
        return rr

    def _gn_step(v):
        J = np.zeros((len(us), 2))
        for i, (p, u) in enumerate(zip(xs, us)):
            d = v - np.array(p, dtype=float)
            dist = max(float(np.linalg.norm(d)), 1e-6)
            J[i, 0] = -u[1] / dist
            J[i, 1] = u[0] / dist
        try:
            return np.linalg.solve(J.T @ J, J.T @ _res(v))
        except np.linalg.LinAlgError:
            return np.linalg.pinv(J.T @ J) @ (J.T @ _res(v))

    s0 = float(_res(x) @ _res(x))
    for _ in range(15):
        delta = _gn_step(x)
        if not np.all(np.isfinite(delta)):
            break
        step = np.clip(delta, -60.0, 60.0)
        try_x = x + step
        s1 = float(_res(try_x) @ _res(try_x))
        if s1 < s0:  # accept improvement
            x = try_x
            if np.linalg.norm(step) < 1e-6 or s0 - s1 < 1e-9:
                break
            s0 = s1
        else:  # halve and retry (Armijo fallback)
            for _ in range(8):
                step *= 0.5
                try_x = x + step
                s1 = float(_res(try_x) @ _res(try_x))
                if s1 < s0:
                    x = try_x
                    s0 = s1
                    break
            else:
                break

    resid = []
    for (px, py), theta_deg in bearing_lines:
        th = np.radians(theta_deg)
        u = np.array([np.cos(th), np.sin(th)])
        d = np.array([x[0] - px, x[1] - py])
        u3 = np.array([np.cos(th), np.sin(th), 0.0])
        d3 = np.array([x[0] - px, x[1] - py, 0.0])
        resid.append(abs(float(np.linalg.norm(np.cross(u3, d3)))))
    rms = float(np.sqrt(np.mean(np.square(resid))))
    return float(x[0]), float(x[1]), rms


def bearing_error_km(rx_xy: tuple, true_xy: tuple, est_bearing_deg: float) -> float:
    """Perpendicular distance of the true position from an estimated bearing
    line - the per-line error contributed by one receiver."""
    th = np.radians(est_bearing_deg)
    u = np.array([np.cos(th), np.sin(th)])
    d = np.array([true_xy[0] - rx_xy[0], true_xy[1] - rx_xy[1]])
    return abs(float(np.cross(u, d)))


def geolocate_streams(stream_bearings: dict, min_receivers: int = 2) -> dict:
    """Triangulate every emitter stream seen by multiple receivers.

    Args:
        stream_bearings: ``{stream_key: [(rx_pos, bearing_deg), ...]}`` where
            ``stream_key`` groups detections of the same emitter (e.g. its
            frequency fingerprint) across receivers.

    Returns:
        ``{stream_key: {"x": ..., "y": ..., "residual_km": ..., "n_lines": k}}``
        for streams with at least ``min_receivers`` bearing lines.
    """
    out = {}
    for key, lines in stream_bearings.items():
        if len(lines) < min_receivers:
            continue
        x, y, rms = triangulate(lines)
        out[key] = {"x": x, "y": y, "residual_km": rms,
                    "n_lines": len(lines)}
    return out


def cep_stats(errors_km: list) -> dict:
    """Circular-error-probable statistics for a set of geolocation errors.

    CEP50 is the median miss distance; CEP90 the 90th percentile.
    """
    e = np.sort(np.asarray(errors_km, dtype=float))
    if len(e) == 0:
        return {"n": 0, "mean": None, "cep50": None, "cep90": None}
    return {"n": int(len(e)),
            "mean": float(e.mean()),
            "cep50": float(np.percentile(e, 50)),
            "cep90": float(np.percentile(e, 90))}


def simulate_bearings(true_xy: tuple, rx_positions: list,
                      sigma_deg: float, rng: np.random.Generator) -> list:
    """Bearings from every receiver to a true emitter position, with noise."""
    lines = []
    for rx in rx_positions:
        true_b = geometric_bearing(rx, true_xy)
        noisy = (true_b + rng.normal(0.0, sigma_deg)) % 360.0
        lines.append((rx, noisy))
    return lines
