"""Angle-of-arrival measurement models (interferometer and monopulse).

The scheduler treats AOA as an input; this module models *how* a real ES
receiver measures it, because the measurement error is neither constant nor
Gaussian-independent-of-signal:

* **Phase interferometry** (the primary model): the phase difference between
  two antennas separated by baseline ``d`` is
  ``phi = 2*pi*d*sin(theta)/lambda``, and its measurement error follows the
  Cramer-Rao bound ``sigma_phi = 1/sqrt(2*SNR)`` (radians, for a complex
  tone).  A long baseline is precise but ambiguous (``|phi| <= pi`` wraps);
  a short baseline is unambiguous but coarse - so the model measures the
  coarse angle on the short baseline and resolves the long baseline's
  ambiguity against it, exactly as real dual-baseline interferometers do.
* **Amplitude monopulse** (the fallback): two overlapping beams whose power
  ratio gives the angle; simpler, no ambiguity, but several degrees of error.

The measured AOA error therefore *depends on SNR and frequency* - a weak or
high-frequency emitter is poorly localised, which the scheduler-level
fingerprint clustering (AOA buckets of 15 degrees) experiences as stream
fragmentation at low SNR.  That coupling is the point.
"""
from __future__ import annotations

import math

import numpy as np

C_M_S = 299_792_458.0


def _wrap_pi(phi: float) -> float:
    """Wrap a phase to [-pi, pi]."""
    return (float(phi) + math.pi) % (2.0 * math.pi) - math.pi


def cramer_rao_sigma_deg(theta_deg: float, freq_mhz: float, snr_db: float,
                         baseline_m: float) -> float:
    """Cramer-Rao lower bound on the phase-interferometer AOA error (deg).

    ``sigma_theta >= lambda/(2*pi*d*cos(theta)) * 1/sqrt(2*SNR_lin)``.
    """
    lam = C_M_S / (max(freq_mhz, 1e-6) * 1e6)
    theta = math.radians(theta_deg)
    cos_t = max(abs(math.cos(theta)), 0.2)
    snr_lin = 10.0 ** (float(snr_db) / 10.0)
    sigma_phi = 1.0 / math.sqrt(max(2.0 * snr_lin, 1e-9))
    sigma_theta = (lam / (2.0 * math.pi * max(baseline_m, 1e-3) * cos_t)
                   * sigma_phi)
    return math.degrees(sigma_theta)


def phase_interferometer_aoa(true_deg: float, freq_mhz: float, snr_db: float,
                             rng: np.random.Generator,
                             coarse_baseline_m: float = 0.05,
                             fine_baseline_m: float = 0.20,
                             fov_deg: float = 60.0) -> tuple[float, float]:
    """Measure one AOA with a dual-baseline phase interferometer.

    Returns ``(measured_deg, sigma_deg)``.  The coarse (short) baseline is
    unambiguous across the field of view; the fine (long) baseline is
    ``fine/coarse`` times more precise but wraps, so its ambiguity is
    resolved by choosing the fine phase solution closest to the coarse
    measurement.
    """
    theta = ((float(true_deg) % 360.0 + 90.0) % 360.0) - 90.0
    theta = float(np.clip(theta, -fov_deg, fov_deg))
    offset = (float(true_deg) % 360.0) - theta
    lam = C_M_S / (max(freq_mhz, 1e-6) * 1e6)
    out = []
    for baseline in (coarse_baseline_m, fine_baseline_m):
        phi_true = 2.0 * math.pi * baseline * math.sin(
            math.radians(theta)) / lam
        sigma_phi = 1.0 / math.sqrt(max(2.0 * 10.0 ** (snr_db / 10.0), 1e-9))
        phi_meas = _wrap_pi(phi_true + float(rng.normal(0.0, sigma_phi)))
        out.append((phi_meas, baseline, sigma_phi))
    (phi_c, b_c, sig_c), (phi_f, b_f, sig_f) = out
    # Resolve the fine baseline's ambiguity: its phase wraps with period
    # lambda/fine_baseline in sin(theta); every k whose scaled phase matches
    # the coarse estimate (mod 2*pi) is a valid hypothesis - exact ties are
    # broken by angular proximity to the coarse angle, which is what real
    # dual-baseline interferometers do.
    k_best, err_best = 0, float("inf")
    hypotheses: list[tuple[float, int]] = []
    for k in range(-int(math.ceil(b_f / max(b_c, 1e-6))) - 1,
                   int(math.ceil(b_f / max(b_c, 1e-6))) + 2):
        scaled = (phi_f + 2.0 * math.pi * k) * (b_c / b_f)
        err = abs(_wrap_pi(scaled - phi_c))
        hypotheses.append((err, k))
        if err < err_best - 1e-9:
            err_best, k_best = err, k
    tied = [k for err, k in hypotheses if err <= err_best + 1e-6]
    if len(tied) > 1:
        theta_c = math.degrees(math.asin(
            max(-1.0, min(1.0, phi_c * lam / (2.0 * math.pi * b_c)))))
        def _angle_dist(k: int) -> float:
            tf = math.degrees(math.asin(max(-1.0, min(
                1.0, (phi_f + 2.0 * math.pi * k) * lam
                / (2.0 * math.pi * b_f)))))
            return abs(tf - theta_c)
        k_best = min(tied, key=_angle_dist)
    phi_f_res = phi_f + 2.0 * math.pi * k_best
    # Combine: precision is set by the fine baseline, the coarse baseline
    # pins the ambiguity.  Convert both phase estimates to angles.
    theta_c = math.degrees(math.asin(
        max(-1.0, min(1.0, phi_c * lam / (2.0 * math.pi * b_c)))))
    theta_f = math.degrees(math.asin(
        max(-1.0, min(1.0, phi_f_res * lam / (2.0 * math.pi * b_f)))))
    theta_hat = 0.15 * theta_c + 0.85 * theta_f
    sigma_deg = cramer_rao_sigma_deg(theta_hat, freq_mhz, snr_db,
                                     fine_baseline_m)
    # A single array face covers the forward hemisphere; the folded bearing
    # offset (0 or 180 degrees) is restored here, standing in for the
    # second array face a real system would use to resolve front/back.
    return float((theta_hat + offset) % 360.0), float(sigma_deg)


def amplitude_monopulse_aoa(true_deg: float, snr_db: float,
                            rng: np.random.Generator,
                            beamwidth_deg: float = 60.0) -> tuple[float, float]:
    """Measure one AOA with a two-beam amplitude-monopulse cluster.

    Simpler and unambiguous, but the slope of the power ratio is shallow, so
    the error is several degrees and degrades with falling SNR.
    """
    theta = math.radians(true_deg)
    slope = 1.2 / math.radians(beamwidth_deg)   # dB per radian, boresight
    ratio_db = slope * theta * 2.0
    sigma_ratio = math.sqrt(2.0) / math.sqrt(max(10.0 ** (snr_db / 10.0),
                                                 1e-9))
    ratio_meas = ratio_db + float(rng.normal(0.0, sigma_ratio))
    theta_hat = math.degrees(ratio_meas / (2.0 * slope))
    theta = ((float(true_deg) % 360.0 + 90.0) % 360.0) - 90.0
    return float((theta + theta_hat) % 360.0), float(
        math.degrees(1.0 / (2.0 * slope) * sigma_ratio))


def measure_aoa(true_deg: float, freq_mhz: float, snr_db: float,
                rng: np.random.Generator, model: str = "interferometer",
                **kwargs) -> tuple[float, float]:
    """Front door: measure one AOA with the configured model."""
    if model == "monopulse":
        return amplitude_monopulse_aoa(true_deg, snr_db, rng, **kwargs)
    return phase_interferometer_aoa(true_deg, freq_mhz, snr_db, rng, **kwargs)
