"""Scenario configuration: JSON-serialisable description of an RF environment."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict, field


@dataclass
class ScenarioConfig:
    """Full parametrisation of a simulated RF environment.

    Attributes mirror :class:`ewsmart.environment.RFEnvironment` constructor
    arguments so any scenario can be persisted and replayed exactly.
    """

    n_bands: int = 24
    T: int = 3000
    seed: int = 0
    n_stationary: int = 6
    n_agile: int = 4
    n_periodic: int = 4
    n_spatial: int = 3
    n_evasive: int = 0
    n_clutter: int = 8
    sens_db: float = 0.0
    snr_mean_db: float = 12.0
    snr_std_db: float = 4.0
    freq_min_mhz: float = 2000.0
    freq_max_mhz: float = 18000.0
    noise_floor_scale: float = 1.0
    period_range: tuple = (40, 400)
    on_len_range: tuple = (2, 5)
    hop_set_range: tuple = (3, 7)
    dwell_range: tuple = (3, 9)
    agile_mode: str = "random"  # "random" | "markov" (structured hopping)
    noise_figure_db: float = 6.0  # receiver front-end noise figure
    dwell_time_us: float = 1.0  # coherent integration time per dwell
    # --- communication-signal emitters (PS: "communication *or* radar") ----
    n_fhss: int = 3   # FHSS communication nets (fast frequency hopping)
    n_tdma: int = 2   # TDMA burst communication stations
    # --- detection-processing model ----------------------------------------
    cfar_pfa: float = 1e-3      # CA-CFAR design false-alarm probability
    capture_range_db: float = 30.0  # co-channel near-far masking dynamic range

    @classmethod
    def from_json(cls, path: str) -> "ScenarioConfig":
        """Load a scenario from a JSON file."""
        with open(path) as f:
            raw = json.load(f)
        known = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
        for key in ("period_range", "on_len_range", "hop_set_range", "dwell_range"):
            if key in known:
                known[key] = tuple(known[key])
        return cls(**known)

    def to_json(self, path: str) -> None:
        """Persist the scenario to JSON."""
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def scaled(self, **overrides) -> "ScenarioConfig":
        """Return a copy with fields replaced (for sweeps)."""
        d = asdict(self)
        d.update(overrides)
        return ScenarioConfig(**d)

    # -- RF front-end bandwidth model --------------------------------------
    # The PS requires a receiver whose *instantaneous* bandwidth is at least
    # an order of magnitude below the surveilled spectrum.  The discretisation
    # into n_bands is that model; these properties make the bandwidth
    # semantics explicit and machine-checkable instead of merely implied.

    @property
    def total_bw_mhz(self) -> float:
        """Total surveilled spectrum width in MHz."""
        return float(self.freq_max_mhz - self.freq_min_mhz)

    @property
    def inst_bw_mhz(self) -> float:
        """Instantaneous bandwidth of one receiver dwell (one band) in MHz."""
        return self.total_bw_mhz / float(self.n_bands)

    @property
    def bandwidth_ratio(self) -> float:
        """Spectrum-to-instantaneous bandwidth ratio (PS: should be >= 10)."""
        return self.total_bw_mhz / self.inst_bw_mhz

    def bandwidth_model(self) -> dict:
        """Machine-readable RF front-end summary stamped into result artifacts.

        ``thermal_noise_dbm`` is the kT+B floor over one band's instantaneous
        bandwidth plus the receiver noise figure; ``sens_db`` is interpreted
        relative to the *received* signal, so ``required_input_sens_dbm`` is
        the input-referred floor a real front-end would need for 0 dB SNR.
        ``processing_gain_db`` is the time-bandwidth integration gain a
        receiver collects from coherently integrating one dwell: 10 log10
        (B . tau) with tau = ``dwell_time_us`` - the link that lets the
        sensitivity figure-of-merit be reported as a *minimum detectable
        signal in dBm* (the classical radiometer equation) rather than as a
        dimensionless offset.
        """
        inst_bw_hz = self.inst_bw_mhz * 1e6
        thermal = -174.0 + 10.0 * math.log10(inst_bw_hz)
        tau_s = max(self.dwell_time_us, 1e-3) * 1e-6
        tb_product = inst_bw_hz * tau_s
        gain = 10.0 * math.log10(max(tb_product, 1.0))
        return {
            "freq_min_mhz": float(self.freq_min_mhz),
            "freq_max_mhz": float(self.freq_max_mhz),
            "total_bw_mhz": self.total_bw_mhz,
            "n_bands": int(self.n_bands),
            "inst_bw_mhz": self.inst_bw_mhz,
            "bandwidth_ratio": self.bandwidth_ratio,
            "bandwidth_ratio_meets_ps_order": bool(self.bandwidth_ratio >= 10.0),
            "noise_figure_db": float(self.noise_figure_db),
            "dwell_time_us": float(self.dwell_time_us),
            "time_bandwidth_product": tb_product,
            "processing_gain_db": gain,
            "thermal_noise_dbm": thermal + float(self.noise_figure_db),
            "required_input_sens_dbm": thermal + float(self.noise_figure_db),
            "sens_db": float(self.sens_db),
        }
