"""Narrowband ES receiver model with per-emitter detection, AOA and PDW output.

Each receiver instance draws its own noise-floor realisation so multiple
cooperating receivers experience independent noise, as physically required.
"""
from __future__ import annotations

import math

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
        detected_eids: emitter ids actually detected this dwell (the
            attribution contract: only these may receive intercept credit).
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
    detected_eids: tuple = ()
    aoa_deg: float | None = None
    pdws: tuple = ()
    emitters: tuple = ()  # emitters present at dwell (avoids re-fetch)


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

    def sensitivity_fom(self) -> dict:
        """Receiver sensitivity figure-of-merit block (PS FoM: sensitivity).

        ``pd50_snr_db`` is the single-dwell SNR at which Pd = 0.485 (the
        logistic mid-point, i.e. the classical sensitivity threshold); the
        ``pd_vs_snr`` curve is the empirical single-dwell detection
        probability over a reference SNR grid.  The RF front-end bandwidth
        context from the scenario config is included so sensitivity is always
        reported against an explicit instantaneous bandwidth.

        Sensitivity is additionally anchored in **physical units** through
        the radiometer equation: with kT+B+NF thermal floor ``N``, coherent
        integration gain ``G = 10 log10(B tau)`` and required post-detection
        SNR ``S``, the minimum detectable signal is ``MDS_dBm = N + S - G``.
        ``pd50_mds_dbm`` and ``mds_dbm_at_pd90`` are the input powers (dBm)
        needed for Pd = 0.5 and Pd = 0.9 respectively, and
        ``pd_vs_input_power_dbm`` transposes the Pd curve onto that physical
        input-power axis.
        """
        bw = None
        cfg = getattr(self.env, "cfg", None)
        if cfg is not None and hasattr(cfg, "bandwidth_model"):
            bw = cfg.bandwidth_model()
        grid = [-6.0, -3.0, 0.0, 3.0, 6.0, 9.0, 12.0, 15.0, 18.0]
        curve = {f"{snr:+g}": round(self.detection_prob(snr), 4)
                 for snr in grid}
        # Physical anchor: input power (dBm) that produces post-detection
        # SNR ``snr`` = thermal floor + SNR - integration gain.
        thermal = float(bw["thermal_noise_dbm"]) if bw else float('nan')
        gain = float(bw.get("processing_gain_db", 0.0)) if bw else 0.0
        def _input_dbm(snr_db: float) -> float:
            return thermal + snr_db - gain
        pd50 = float(self.env.sens_db + self.pd_mid_offset)
        z90 = -math.log((0.97 / 0.90) - 1.0)  # SNR z where Pd = 0.9
        pd90 = pd50 + self.pd_k * z90
        return {
            "sens_db": float(self.env.sens_db),
            "pd_mid_offset_db": float(self.pd_mid_offset),
            "pd50_snr_db": pd50,
            "pd_k_db": float(self.pd_k),
            "base_false_alarm_rate": float(self.base_fa),
            "pd_vs_snr": curve,
            "pd50_mds_dbm": round(_input_dbm(pd50), 2),
            "mds_dbm_at_pd90": round(_input_dbm(pd90), 2),
            "pd_vs_input_power_dbm": {
                f"{snr:+g}": round(_input_dbm(snr), 2) for snr in grid},
            "frontend": bw,
        }


    def dwell(self, band: int, t: int, build_pdws: bool = True) -> DwellResult:
        """Tune to ``band`` at slot ``t`` and return the measurement result.

        Args:
            build_pdws: if False, skip PDW dict creation (faster for bulk
                simulation where PDWs are not streamed to a client).
        """
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
        pdws = ()
        if build_pdws and det:
            toa_t = t * 1000.0
            thermal = None
            gain = 0.0
            cfg = getattr(self.env, "cfg", None)
            if cfg is not None and hasattr(cfg, "bandwidth_model"):
                fe = cfg.bandwidth_model()
                thermal = float(fe["thermal_noise_dbm"])
                gain = float(fe.get("processing_gain_db", 0.0))
            pdws = tuple({
                "toa_us": toa_t, "freq_mhz": e.freq_mhz,
                "pw_us": e.pw_us, "pa_db": s, "aoa_deg": a,
                # Absolute received power (dBm): the same radiometer anchor
                # as the sensitivity FoM, so PDWs carry physical units.
                "pa_dbm": round(thermal + s - gain, 2)
                if thermal is not None else None,
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
                           detected_eids=tuple(e.eid for _, _, e in det),
                           aoa_deg=aoa_lead, pdws=pdws, emitters=tuple(ems))
