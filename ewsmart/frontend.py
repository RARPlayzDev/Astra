"""RF front-end impairment model (synthesiser, LNA, mixer, ADC).

The scheduler-level receiver treats a dwell as an ideal integration window.
Real hardware does not: the local oscillator needs time to settle after a
retune, a strong signal compresses the LNA and raises the noise floor
(blocking/desensitisation), mixer non-linearity folds intermodulation
products into the channel, and the ADC saturates.  This module models those
impairments explicitly so their cost is *measurable* rather than narrated:

* :meth:`FrontEnd.effective_dwell_us` - retune settling/blanking loss;
* :meth:`FrontEnd.noise_rise_db` - blocking/desensitisation above P1dB;
* :meth:`FrontEnd.intermod_spurs` - 2f1-f2 / 2f2-f1 third-order products;
* :meth:`FrontEnd.spur_responses` - image and mixer spur frequencies
  (m*f_rf +/- n*f_lo);
* :meth:`FrontEnd.adc_clip_dbm` / ``clipping_spur_dbm`` - ADC saturation.

All parameters have physically plausible defaults and are configurable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FrontEndSpec:
    """Hardware parameters of one receiver front-end."""

    settling_time_us: float = 5.0      # synthesiser retune-to-lock time
    phase_noise_dbc_hz: float = -95.0  # LO phase noise at 10 kHz offset
    p1db_dbm: float = -10.0            # LNA 1-dB compression (input-referred)
    ip3_dbm: float = 0.0               # third-order intercept (input-referred)
    sfdr_db: float = 70.0              # spurious-free dynamic range
    adc_bits: int = 12
    adc_fullscale_dbm: float = 5.0     # ADC full-scale input power
    lo_freq_mhz: float = 2150.0        # first LO for the mixer spur model

    def __post_init__(self) -> None:
        if self.settling_time_us < 0:
            raise ValueError("settling_time_us must be >= 0")
        if self.ip3_dbm <= self.p1db_dbm:
            raise ValueError("ip3_dbm must be above p1db_dbm")
        if not (1 <= self.adc_bits <= 32):
            raise ValueError("adc_bits must lie in [1, 32]")


class FrontEnd:
    """Behavioural model of the receiver's analogue front-end and ADC."""

    def __init__(self, spec: FrontEndSpec | None = None):
        self.spec = spec or FrontEndSpec()

    # -- synthesiser / retune -------------------------------------------------
    def blanked_time_us(self, dwell_us: float, retuned: bool) -> float:
        """Listening time lost to LO settling after a retune (us)."""
        if not retuned or self.spec.settling_time_us <= 0:
            return 0.0
        return min(float(dwell_us), float(self.spec.settling_time_us))

    def effective_dwell_us(self, dwell_us: float, retuned: bool) -> float:
        """Integration time actually collected in the dwell (us)."""
        return max(0.0, float(dwell_us) - self.blanked_time_us(dwell_us,
                                                               retuned))

    # -- LNA compression / blocking -------------------------------------------
    def noise_rise_db(self, strongest_dbm: float) -> float:
        """Noise-floor rise (dB) caused by a strong in-channel signal.

        Above the LNA's 1-dB compression point the front-end desensitises:
        gain compression plus LO phase-noise reciprocal mixing raise the
        effective noise floor, so a weak co-channel emitter becomes harder to
        detect (the classical blocking problem).  Returns exactly 0 dB in the
        linear region - the model must not perturb normal operation.
        """
        over = float(strongest_dbm) - self.spec.p1db_dbm
        if over <= 0:
            return 0.0
        return min(over, 40.0) + min(0.5 * over, 15.0)

        # -- mixer non-linearity ---------------------------------------------------
    def intermod_spurs(self, f1_mhz: float, f2_mhz: float) -> list[float]:
        """Third-order intermodulation products of two strong tones (MHz).

        A mixer/LNA with input third-order intercept ``ip3`` produces 2f1-f2
        and 2f2-f1 products; the product level follows the classical
        relationship ``P_im3 = 3*P_tone - 2*IP3`` (all dBm).
        """
        if f1_mhz <= 0 or f2_mhz <= 0 or abs(f1_mhz - f2_mhz) < 1e-9:
            return []
        return [2.0 * f1_mhz - f2_mhz, 2.0 * f2_mhz - f1_mhz]

    def intermod_level_dbm(self, tone_dbm: float) -> float:
        """IM3 product level (dBm) for equal tones at ``tone_dbm``."""
        return 3.0 * float(tone_dbm) - 2.0 * self.spec.ip3_dbm

    def spur_responses(self, f_rf_mhz: float) -> list[tuple[int, int, float]]:
        """Mixer spur responses ``(m, n, f_spur)`` for m*f_rf +/- n*f_LO.

        Real mixers respond not only at f_rf - f_LO but at many m/n
        combinations; each can fold an out-of-band signal into the IF and
        masquerade as an in-channel emitter.  The strongest spurs
        (m, n <= 3) are enumerated so downstream code can discount or mask
        them.
        """
        out = []
        for m in (1, 2, 3):
            for n in range(1, 4):
                for sign in (1.0, -1.0):
                    f = m * f_rf_mhz + sign * n * self.spec.lo_freq_mhz
                    if f > 0 and (abs(m - 1) + abs(n - 1)) > 0:
                        out.append((m, n, float(f)))
        out.sort(key=lambda s: (s[0] + s[1], s[2]))
        return out

    # -- ADC -------------------------------------------------------------------
    def adc_clip_dbm(self) -> float:
        """Input power at which the ADC saturates (dBm)."""
        return float(self.spec.adc_fullscale_dbm)

    def clipping_spur_dbm(self, strongest_dbm: float) -> float | None:
        """Odd-harmonic spur level (dBm) when the ADC clips, else ``None``.

        A saturating ADC hard-clips the waveform, folding odd harmonics of
        the strong signal back into band - a false emitter invisible to a
        linear receiver model.  The spur level is bounded by the
        spurious-free dynamic range.
        """
        if float(strongest_dbm) <= self.spec.adc_fullscale_dbm:
            return None
        over = float(strongest_dbm) - self.spec.adc_fullscale_dbm
        return (self.spec.adc_fullscale_dbm - self.spec.sfdr_db
                + min(over, 20.0))
