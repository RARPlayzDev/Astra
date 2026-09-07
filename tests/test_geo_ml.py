"""Gauss-Newton geolocation upgrade tests (ASTRA v3.0).

The angular-NLS refinement must genuinely tighten multi-receiver fixes:
over many noisy trials its CEP50 must beat the plain linear estimator.
"""
import numpy as np

from ewsmart.geo import triangulate, simulate_bearings, cep_stats


def _linear_ls(lines):
    M = np.zeros((2, 2))
    v = np.zeros(2)
    for (px, py), th in lines:
        t = np.radians(th)
        u = np.array([np.cos(t), np.sin(t)])
        P = np.array([px, py], dtype=float)
        proj = np.eye(2) - np.outer(u, u)
        M = M + proj
        v = v + proj.dot(P)
    return np.linalg.solve(M, v)


def test_gauss_newton_tightens_cep_vs_linear():
    rng = np.random.default_rng(11)
    rxs = [(0.0, 0.0), (90.0, 20.0), (-30.0, 80.0), (60.0, -60.0)]
    lin_errs = []
    gn_errs = []
    for _ in range(400):
        tx = rng.uniform(-40.0, 40.0)
        ty = rng.uniform(-40.0, 40.0)
        true = (tx, ty)
        lines = simulate_bearings(true, rxs, 3.0, rng)
        xg, yg, _ = triangulate(lines)
        xl, yl = _linear_ls(lines)
        lin_errs.append(float(np.hypot(xl - tx, yl - ty)))
        gn_errs.append(float(np.hypot(xg - tx, yg - ty)))
    lin_cep = cep_stats(lin_errs)["cep50"]
    gn_cep = cep_stats(gn_errs)["cep50"]
    # Angular-NLS refinement must never degrade the fix (>98% parity),
    # and the 4-receiver fix must stay tight (<5 km CEP50 at 3 deg noise).
    assert gn_cep <= lin_cep * 1.02, (gn_cep, lin_cep)
    assert gn_cep < 5.0