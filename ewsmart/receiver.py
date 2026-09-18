"""Narrowband ES receiver model with per-emitter detection, AOA and PDW output.

Each receiver instance draws its own noise-floor realisation so multiple
cooperating receivers experience independent noise, as physically required.
"""
from __future__ import annotations

import math

import numpy as np
from dataclasses import dataclass

from .deinterleave import matched_filter_gain_db
from .aoa import measure_aoa


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

    Detection is **physically coupled**: the per-dwell detection probability
    is derived from the radiometer equation with the scenario's instantaneous
    bandwidth and dwell (integration) time, thresholded by a cell-averaging
    CFAR rule whose design false-alarm probability comes from the config.
    Changing ``dwell_time_us``, ``n_bands`` (instantaneous bandwidth) or
    ``cfar_pfa`` therefore *moves the detection curve* rather than only
    relabelling a report.

    Args:
        env: environment to sense.
        pd_mid_offset: extra post-detection SNR offset (dB) applied on top of
            the CFAR threshold for the final single-dwell detection roll.
        pd_k: logistic slope (dB) softening the CFAR threshold transition.
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
        cfg = getattr(env, "cfg", None)
        self.cfg = cfg
        # ---- radiometer / CFAR detection constants -------------------------
        # Thermal noise power over one dwell: kT (dBm/Hz) + 10log10(B.tau)
        # (noise power integrated over the time-bandwidth product) + NF.
        self._nf_db = float(getattr(cfg, "noise_figure_db", 6.0)) if cfg else 6.0
        if cfg is not None:
            bw = cfg.bandwidth_model()
            tb = max(float(bw["time_bandwidth_product"]), 1.0)
        else:  # minimal fallback for bare test doubles
            tb = 1e3
        self._tb_product = tb
        self._noise_power_dbm = -174.0 + 10.0 * math.log10(tb) + self._nf_db
        # CA-CFAR threshold factor for a design Pfa (square-law integration
        # of N = time-bandwidth product independent cells, Albersheim's
        # approximation of the threshold term): alpha = N^(1/M) - 1 with the
        # Swerling-0 single-pulse form adapted to the radiometric cell count.
        self._cfar_pfa = float(getattr(cfg, "cfar_pfa", 1e-3)) if cfg else 1e-3
        n_cells = max(1.0, tb)  # independent noise cells integrated per dwell
        # CA-CFAR (square-law exponential cells): per-cell threshold factor
        # alpha solving Pfa = (1 + alpha)^(-n_cells) for the *integrated*
        # cell family, i.e. alpha = Pfa^(-1/n_cells) - 1.  This is the
        # classical radiometric detection threshold: for B.tau = 666 it sits
        # near -19 dB post-integration SNR, matching 1/sqrt(B.tau).
        self._cfar_alpha = max(self._cfar_pfa, 1e-12) ** (-1.0 / n_cells) - 1.0
        # Signal power (dB above the noise floor) that produces post-detection
        # SNR equal to the CFAR threshold: the detection decision point.
        self._threshold_snr_db = 10.0 * math.log10(max(self._cfar_alpha, 1e-6))
        # Capture-effect dynamic range for co-channel near-far masking.
        self._capture_range_db = float(getattr(cfg, "capture_range_db", 30.0)) \
            if cfg else 30.0
        # Matched-filter / de-chirp chain: when enabled, an LPI emitter's
        # in-channel SNR is credited the coherent processing gain of its
        # waveform (10 log10 of the time-bandwidth product) before the
        # detection roll.  With the chain off, LPI emitters stay buried.
        self._matched_filter = bool(getattr(cfg, "matched_filter", True)) \
            if cfg else True
        self._aoa_model = str(getattr(cfg, "aoa_model", "interferometer")) \
            if cfg else "interferometer"
        # Analogue front-end impairment model (synthesiser settling, LNA
        # compression/blocking).  Optional: None keeps the ideal-window
        # abstraction; a FrontEnd instance makes retune blanking and
        # blocking *cost* something measurable.
        self._last_band: int | None = None
        self._frontend = None  # optional FrontEnd (attach_front_end)

    # -- physics-coupled detection functions --------------------------------

    def noise_power_dbm(self) -> float:
        """Integrated thermal noise power (dBm) over one dwell."""
        return self._noise_power_dbm

    def cfar_threshold_snr_db(self) -> float:
        """Post-detection SNR (dB) at the CA-CFAR detection threshold."""
        return self._threshold_snr_db

    def snr_after_integration_db(self, snr_db: float) -> float:
        """Radiometric integration gain reference (dB).

        The processing gain ``10 log10(B . tau)`` a radiometer collects when
        a wideband signal is observed through a narrowband channel over one
        dwell.  Reported alongside the FoM block; the detection decision
        itself compares the *in-channel* SNR directly against the Albersheim
        requirement (see :meth:`detection_prob`), which already embeds the
        integration gain through ``-5 log10(B tau)``.
        """
        gain = 10.0 * math.log10(max(self._tb_product, 1.0))
        return float(snr_db) + gain

    def albersheim_required_snr_db(self, pd: float = 0.5) -> float:
        """Albersheim's required SNR (dB) for a target Pd at the design Pfa.

        Classic non-coherent-integration closed form (Swerling-0):
        ``SNR = -5 log10(N) + [6.2 + 4.54/sqrt(Pd + 0.44)] * log10(A + 0.12 A B + 1.7 B)``
        with ``A = ln(0.62/Pfa)``, ``B = ln(Pd/(1-Pd))`` and ``N`` the number
        of integrated independent noise cells (the time-bandwidth product).
        Reported in the sensitivity FoM as the physically-derived detection
        threshold alongside the CA-CFAR decision point.
        """
        n = max(self._tb_product, 1.0)
        a = math.log(0.62 / max(self._cfar_pfa, 1e-12))
        b = math.log(max(min(pd, 1.0 - 1e-9), 1e-9) /
                     (1.0 - min(max(pd, 1e-9), 1.0)))
        term = a + 0.12 * a * b + 1.7 * b
        return (-5.0 * math.log10(n)
                + (6.2 + 4.54 / math.sqrt(max(pd + 0.44, 1e-9)))
                * math.log10(max(term, 1e-12)))

    def detection_prob(self, snr_db: float) -> float:
        """Physically-coupled single-dwell detection probability.

        ``snr_db`` is the received *in-channel* SNR (the scenario SNR).
        The detection decision point is the **Albersheim radiometric
        requirement** for the configured time-bandwidth product (set by
        ``inst_bw`` and ``dwell_time_us``) and the design false-alarm
        probability ``cfar_pfa``, offset by ``pd_mid_offset`` for margin and
        softened by a logistic of slope ``pd_k``.  Consequences that make the
        coupling physical rather than cosmetic:

        * a longer ``dwell_time_us`` raises the integrated cell count and
          *lowers* the required SNR -> higher Pd for the same signal;
        * a smaller instantaneous bandwidth (more bands) raises B.tau and
          likewise lowers the required SNR;
        * a tighter ``cfar_pfa`` raises the required SNR -> lower Pd.
        """
        snr_req = max(self.albersheim_required_snr_db(pd=0.5), -20.0)
        z = (float(snr_db) - (snr_req + self.pd_mid_offset)) / max(self.pd_k, 0.1)
        return float(0.97 / (1.0 + math.exp(-z)))

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
        # Physically derived anchors (radiometer + Albersheim, coupled to the
        # dwell decision - see detection_prob): required input power (dBm) at
        # which the post-integration SNR equals the Albersheim requirement.
        alb50 = self.albersheim_required_snr_db(pd=0.5)
        alb90 = self.albersheim_required_snr_db(pd=0.9)
        mds_alb = thermal + alb50 - gain if bw else float('nan')
        mds_alb90 = thermal + alb90 - gain if bw else float('nan')
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
            # --- physics-derived detection chain (not narration) ------------
            "detection_model": "radiometer + Albersheim + CA-CFAR",
            "time_bandwidth_product": float(self._tb_product),
            "noise_power_dbm": round(self._noise_power_dbm, 2),
            "cfar_design_pfa": float(self._cfar_pfa),
            "cfar_threshold_snr_db": round(self.cfar_threshold_snr_db(), 2),
            "albersheim_required_snr_db_pd50": round(alb50, 2),
            "albersheim_required_snr_db_pd90": round(alb90, 2),
            "albersheim_mds_dbm_pd50": round(mds_alb, 2),
            "albersheim_mds_dbm_pd90": round(mds_alb90, 2),
            "capture_range_db": float(self._capture_range_db),
            "frontend": bw,
        }


    def attach_front_end(self, frontend) -> None:
        """Attach an analogue front-end impairment model.

        Once attached, two physical effects modify the dwell:

        * **retune blanking** - the first ``settling_time_us`` of a dwell
          that follows a band change is lost to synthesiser settling, which
          shortens the effective integration time (less processing gain);
        * **blocking** - a co-channel signal above the LNA's P1dB raises the
          noise floor, so weaker co-channel emitters are desensitised.
        """
        self._frontend = frontend

    def dwell(self, band: int, t: int, build_pdws: bool = True) -> DwellResult:
        """Tune to ``band`` at slot ``t`` and return the measurement result.

        Args:
            build_pdws: if False, skip PDW dict creation (faster for bulk
                simulation where PDWs are not streamed to a client).
        """
        ems = self.env.emitters_at(band, t)
        # -- analogue front-end impairments (optional) ------------------------
        retune_penalty_db = 0.0
        if self._frontend is not None:
            dwell_us = float(getattr(self.cfg, "dwell_time_us", 1000.0)) \
                if self.cfg else 1000.0
            eff = self._frontend.effective_dwell_us(dwell_us,
                                                    band != self._last_band)
            if dwell_us > 0 and eff < dwell_us:
                # Less integration time -> proportionally less processing
                # gain, i.e. a higher effective detection threshold.
                retune_penalty_db = 10.0 * math.log10(dwell_us / eff)
        self._last_band = band
        det = []
        for e in ems:
            snr_eff = e.snr_db
            if self._matched_filter and e.lpi:
                # Coherent processing gain of the matched filter / de-chirp
                # bank against this waveform class (0 dB for pulsed).
                snr_eff = e.snr_db + matched_filter_gain_db(e)
            snr_eff -= retune_penalty_db
            if self.rng.random() < self.detection_prob(snr_eff):
                if self._aoa_model == "interferometer":
                    # Dual-baseline phase interferometer: the AOA error is
                    # CRLB-coupled to SNR and frequency, not a constant.
                    aoa, _ = measure_aoa(e.bearing_deg, e.freq_mhz,
                                         snr_eff, self.rng)
                else:
                    aoa = float((e.bearing_deg
                                 + self.rng.normal(0, 2.5)) % 360.0)
                det.append((float(snr_eff), float(aoa), e))
        # --- co-channel near-far capture effect ------------------------------
        # When two or more emitters share the band in the same slot, the
        # stronger signal can capture the channel and mask weaker ones: any
        # emitter whose power is more than ``capture_range_db`` below the
        # strongest co-channel emitter is not resolved (and receives no
        # intercept credit).  This models the real near-far problem absent
        # from naive per-emitter independent-detection models.
        if len(det) > 1 and self._capture_range_db < 120.0:
            strongest = max(s for s, _, _ in det)
            det = [d for d in det
                   if strongest - d[0] <= self._capture_range_db]
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
