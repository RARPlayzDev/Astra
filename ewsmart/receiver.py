"""Narrowband ES receiver model with per-emitter detection, AOA and PDW output.

Each receiver instance draws its own noise-floor realisation so multiple
cooperating receivers experience independent noise, as physically required.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass
class DwellResult:
    """Outcome of one receiver dwell on a band.

    Attributes:
        band: tuned band index.
        t: time slot.
        hit: any detection (true signal or false alarm).
        false_alarm: detection occurred with no emitter present.
        snr_db: strongest detected SNR (``-inf`` when nothing detected).
        truth_present: ground-truth occupancy of the band at ``t``.
        detections: per-emitter resolved ``(snr_db, aoa_deg)`` pairs.
        aoa_deg: angle-of-arrival of the strongest emitter (degrees).
        pdws: pulse-descriptor words measured during the dwell.
    """

    band: int
    t: int
    hit: bool
    false_alarm: bool
    snr_db: float
    truth_present: bool
    detections: tuple = ()
    aoa_deg: float | None = None
    pdws: tuple = ()


class ESReceiver:
    """Single-channel surveillance receiver sensing one band per slot.

    Args:
        env: environment to sense.
        pd_mid_offset: detection-threshold offset above sensitivity (dB);
            sweeping it traces the system ROC.
        pd_k: logistic slope of the detection curve (dB).
        base_fa: nominal false-alarm rate before the band noise floor.
        seed: RNG seed for detection and noise draws.
        floor_jitter_db: log-normal jitter (dB std) applied to the band noise
            floor so each receiver of a team realises independent noise.
    """

    def __init__(self, env, pd_mid_offset: float = 6.0, pd_k: float = 3.0,
                 base_fa: float = 2e-4, seed: int = 0,
                 floor_jitter_db: float = 1.0):
        self.env = env
        self.pd_mid_offset = pd_mid_offset
        self.pd_k = pd_k
        self.base_fa = base_fa
        self.rng = np.random.default_rng(seed)
        jitter = self.rng.lognormal(0.0, floor_jitter_db / 8.6859, env.n_bands)
        self.fa_floor = env.noise_floor * jitter

    def detection_prob(self, snr_db: float) -> float:
        """Logistic single-dwell detection probability for a given SNR."""
        z = (snr_db - (self.env.sens_db + self.pd_mid_offset)) / self.pd_k
        return float(0.97 / (1.0 + np.exp(-z)))

    def dwell(self, band: int, t: int) -> DwellResult:
        """Tune to ``band`` at slot ``t`` and return the measurement result."""
        ems = self.env.emitters_at(band, t)
        det = []
        for e in ems:
            if self.rng.random() < self.detection_prob(e.snr_db):
                aoa = float((e.bearing_deg + self.rng.normal(0, 2.5)) % 360.0)
                det.append((float(e.snr_db), aoa, e))
        det.sort(key=lambda p: -p[0])
        detections = tuple((s, a) for s, a, _ in det)
        snr = detections[0][0] if detections else -np.inf
        aoa_lead = detections[0][1] if detections else None
        pdws = tuple({
            "toa_us": t * 1000.0,
            "freq_mhz": e.freq_mhz,
            "pw_us": e.pw_us,
            "pa_db": s,
            "aoa_deg": a,
        } for s, a, e in det)
        fa = False
        hit = bool(det)
        if not hit and not ems:
            if self.rng.random() < min(0.4, self.base_fa * self.fa_floor[band]):
                fa = True
                hit = True
        # Notify environment of intercepts for counter-ESM evasion logic
        if hit and not fa:
            for e in ems:
                self.env.report_intercept(e.eid, t)
        return DwellResult(band, t, hit, fa, snr, bool(ems), detections,
                           aoa_deg=aoa_lead, pdws=pdws)
