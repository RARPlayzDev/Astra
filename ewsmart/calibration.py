"""Scenario-scale auto-calibration of scheduler behaviour constants.

SmartScan's behaviour constants (reconnaissance depth, burst horizon,
pursuit budget, revisit bounds) were tuned for the canonical 24-band,
3000-slot, ~25-emitter scenario.  Hard-coding them means an operator who
changes the spectrum plan - 8 bands for a radio survey, 128 for a full
ELINT sweep - silently inherits constants sized for a different problem.

:func:`calibrate` derives every constant from the scenario scale using the
same engineering reasoning the hand-tuned values embody, expressed as
formulas over three scale factors:

* ``band_scale  = n_bands / 24``   (how much wider the spectrum is);
* ``time_scale  = T / 3000``       (how much longer the episode is);
* ``density     = n_emitters / n_bands`` relative to the canonical 25/24
  (how crowded each band is).

The canonical scenario reproduces the shipped constants exactly, so
calibration is a no-op where the tuning is known good and adapts elsewhere.
"""
from __future__ import annotations

import math

CANONICAL = {"n_bands": 24, "T": 3000, "n_emitters": 25}

# Every derived constant, with the formula that produces it.
_FIELDS = ("recon_factor", "burst_horizon", "stale_revisit_factor",
           "pursuit_budget", "pursuit_window", "hop_min_obs",
           "lock_hits", "exploit_ramp")


def calibrate(n_bands: int, T: int = 3000, n_emitters: int = 25) -> dict:
    """Derive scheduler behaviour constants for a scenario scale.

    Formulas (canonical values in parentheses):

    * ``recon_factor`` - slots of full-band survey per band.  Survey cost
      grows with the square root of the band count (a wider spectrum needs
      more confidence per band before exploitation pays): ``12 * sqrt(
      n_bands/24)``, bounded to [6, 40] (12).
    * ``burst_horizon`` - how long a burst-camping window may run, in
      slots.  Scales with the geometric mean of the time and band scales:
      ``480 * sqrt(time_scale) * sqrt(band_scale)`` bounded to [240, 4800]
      (480).
    * ``stale_revisit_factor`` - maximum revisit latency of any band,
      expressed in multiples of ``n_bands`` (a full sweep).  Constant at 6:
      the guarantee "no band goes unvisited for 6 sweeps" is scale-free.
    * ``pursuit_budget`` - hop-pursuit dwells per 100-slot window.  Scales
      with the band count (more bands, more tracked streams), bounded to
      [3, 12] (6).
    * ``pursuit_window`` - the budget window itself, constant 100 slots.
    * ``hop_min_obs`` - transitions before a hop model is trusted.  Grows
      slowly with emitter density (a crowded band produces more spurious
      co-channel transitions): ``3 * sqrt(density_ratio)`` bounded [2, 8].
    * ``lock_hits`` - detections before a periodic lock attempt: ``5 *
      sqrt(density_ratio)`` bounded [3, 10].
    * ``exploit_ramp`` - final exploitation probability; 0.60 is scale-free
      (it balances reward against the 6-sweep coverage guarantee, not
      against any particular spectrum size).
    """
    if n_bands < 1:
        raise ValueError("n_bands must be >= 1")
    if T < 1:
        raise ValueError("T must be >= 1")
    if n_emitters < 0:
        raise ValueError("n_emitters must be >= 0")
    band_scale = float(n_bands) / CANONICAL["n_bands"]
    time_scale = float(T) / CANONICAL["T"]
    density = (float(n_emitters) / max(n_bands, 1)) / (25.0 / 24.0)
    density = max(density, 1e-6)

    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    return {
        "recon_factor": int(clamp(round(12.0 * math.sqrt(band_scale)),
                                  6, 40)),
        "burst_horizon": int(clamp(round(
            480.0 * math.sqrt(time_scale) * math.sqrt(band_scale)),
            240, 4800)),
        "stale_revisit_factor": 6.0,
        "pursuit_budget": int(clamp(round(6.0 * band_scale), 3, 12)),
        "pursuit_window": 100,
        "hop_min_obs": int(clamp(round(3.0 * math.sqrt(density)), 2, 8)),
        "lock_hits": int(clamp(round(5.0 * math.sqrt(density)), 3, 10)),
        "exploit_ramp": 0.60,
    }


def calibrate_for_env(env) -> dict:
    """Convenience wrapper: calibrate from a live environment object."""
    return calibrate(int(env.n_bands), int(env.T), len(env.emitters))
