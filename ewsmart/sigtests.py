"""Statistical significance tools for scheduler comparisons.

Dependency-free paired tests used by the benchmark suite: a paired
permutation test (exact resampling of sign flips) on per-episode metric
differences, plus a paired bootstrap confidence interval on the mean
difference.  With paired designs the per-episode difference distribution is
what matters, and permutation needs no distributional assumptions.
"""
from __future__ import annotations

import numpy as np


def paired_permutation_test(a, b, n_permutations: int = 20000,
                            seed: int = 0, alternative: str = "greater") -> float:
    """P-value that mean(a) > mean(b) for paired samples.

    Randomly flips the sign of each paired difference; the p-value is the
    fraction of permutations whose mean difference is at least as extreme as
    the observed one.  ``alternative`` is ``"greater"``, ``"less"`` or
    ``"two-sided"``.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    assert len(a) == len(b) and len(a) >= 2
    diff = a - b
    observed = diff.mean()
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(n_permutations, len(diff)))
    perm_means = (signs * diff).mean(axis=1)
    if alternative == "greater":
        return float((perm_means >= observed - 1e-12).mean())
    if alternative == "less":
        return float((perm_means <= observed + 1e-12).mean())
    return float((np.abs(perm_means) >= abs(observed) - 1e-12).mean())


def paired_bootstrap_ci(a, b, n_boot: int = 10000, seed: int = 0,
                        confidence: float = 0.95) -> tuple:
    """Bootstrap confidence interval for mean(a) - mean(b) (paired)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    diff = a - b
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff), size=(n_boot, len(diff)))
    means = diff[idx].mean(axis=1)
    lo_q = (1.0 - confidence) / 2.0
    return (float(np.quantile(means, lo_q)),
            float(np.quantile(means, 1.0 - lo_q)))


def holm_bonferroni(pvalues: list, alpha: float = 0.05) -> list:
    """Holm-Bonferroni correction; returns per-test reject decisions."""
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    m = len(p)
    rejected = np.zeros(m, dtype=bool)
    running = 0.0
    for rank, idx in enumerate(order):
        thresh = alpha / (m - rank)
        ok = p[idx] <= thresh
        rejected[idx] = ok
        running = thresh
        if not ok:
            break
    return rejected.tolist()
