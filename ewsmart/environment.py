"""Simulated RF environment with ground-truth emitter activity.

The environment produces a truth matrix ``occupancy[band, t]`` describing which
bands are transmitting at every time slot, plus per-emitter band sequences used
for intercept credit assignment.  Emitters model four behaviours: stationary,
frequency-agile hopping, periodic scanning and spatially scanning radars whose
rotating main beam only illuminates the receiver periodically.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass

from .config import ScenarioConfig
from .exceptions import (ConfigurationError, SimulationBoundsError,
                         InvalidBandError)

KINDS = ("stationary", "agile", "periodic", "spatial", "evasive")

_INT_FIELDS = ("n_bands", "T", "seed", "n_stationary", "n_agile",
               "n_periodic", "n_spatial", "n_evasive", "n_clutter")
_RANGE_FIELDS = ("period_range", "on_len_range", "hop_set_range",
                 "dwell_range")


def _validate_config(cfg: ScenarioConfig) -> None:
    """Runtime validation of a scenario configuration.

    Raises:
        ConfigurationError: if any field falls outside its documented domain.
    """
    def _is_int(v) -> bool:
        return isinstance(v, (int, np.integer)) and not isinstance(v, bool)

    for f in _INT_FIELDS:
        v = getattr(cfg, f, None)
        if v is None:
            continue
        if not _is_int(v) or v < 0:
            raise ConfigurationError(
                f"ScenarioConfig.{f} must be a non-negative integer, got {v!r}")
    if cfg.n_bands < 1:
        raise ConfigurationError(
            f"ScenarioConfig.n_bands must be >= 1, got {cfg.n_bands}")
    if cfg.T < 1:
        raise ConfigurationError(f"ScenarioConfig.T must be >= 1, got {cfg.T}")
    for f in ("sens_db", "snr_mean_db", "freq_min_mhz", "freq_max_mhz"):
        v = float(getattr(cfg, f))
        if not np.isfinite(v):
            raise ConfigurationError(f"ScenarioConfig.{f} must be finite")
    for f in ("snr_std_db", "noise_floor_scale"):
        v = float(getattr(cfg, f))
        if not np.isfinite(v) or v < 0:
            raise ConfigurationError(
                f"ScenarioConfig.{f} must be a finite non-negative number, "
                f"got {v!r}")
    if cfg.freq_max_mhz <= cfg.freq_min_mhz:
        raise ConfigurationError(
            "ScenarioConfig.freq_max_mhz must exceed freq_min_mhz "
            f"(got {cfg.freq_min_mhz} .. {cfg.freq_max_mhz})")
    for f in _RANGE_FIELDS:
        r = getattr(cfg, f)
        if (not isinstance(r, (tuple, list)) or len(r) != 2
                or not _is_int(r[0]) or not _is_int(r[1])
                or r[0] < 1 or r[0] > r[1]):
            raise ConfigurationError(
                f"ScenarioConfig.{f} must be a (lo, hi) pair of integers "
                f"with 1 <= lo <= hi, got {r!r}")
    # Forward compatibility: any probability-like field must lie in [0, 1].
    for f in cfg.__dataclass_fields__:
        if f.endswith("_prob"):
            v = float(getattr(cfg, f))
            if not np.isfinite(v) or not 0.0 <= v <= 1.0:
                raise ConfigurationError(
                    f"ScenarioConfig.{f} is a probability and must lie in "
                    f"[0.0, 1.0], got {v!r}")
    if getattr(cfg, "agile_mode", "random") not in ("random", "markov"):
        raise ConfigurationError(
            f"ScenarioConfig.agile_mode must be 'random' or 'markov', "
            f"got {getattr(cfg, 'agile_mode', None)!r}")


@dataclass(frozen=True)
class EmitterSpec:
    """Static parameters of one emitter.

    Attributes:
        eid: unique emitter id within the episode.
        kind: one of ``KINDS``.
        home_band: band index used by non-agile kinds.
        snr_db: received signal-to-noise ratio at the ES receiver.
        threat: whether the emitter is a priority/threat target.
        freq_mhz: centre frequency (for PDW realism / dataset mapping).
        bearing_deg: bearing of the emitter relative to the receiver.
        rotation_rate_deg_s: main-beam rotation rate for scanning kinds.
        beamwidth_deg: main-beam 3 dB width for scanning kinds.
        hop_set: candidate bands for frequency-agile emitters.
        dwell: slots per hop for agile emitters.
        period: revisit interval in slots for periodic/spatial kinds.
        on_len: length of the visible ON window in slots.
        pri_us / pw_us: pulse repetition interval and width (PDW realism).
    """

    eid: int
    kind: str
    home_band: int
    snr_db: float
    threat: bool
    freq_mhz: float = 0.0
    bearing_deg: float = 0.0
    x_km: float = 0.0
    y_km: float = 0.0
    rotation_rate_deg_s: float = 0.0
    beamwidth_deg: float = 0.0
    hop_set: tuple = ()
    dwell: int = 1
    period: int = 1
    on_len: int = 1
    pri_us: float = 100.0
    pw_us: float = 1.0

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ConfigurationError(
                f"EmitterSpec.kind must be one of {KINDS}, got {self.kind!r}")
        if not isinstance(self.eid, int) or self.eid < 0:
            raise ConfigurationError(
                f"EmitterSpec.eid must be a non-negative integer, got {self.eid!r}")
        if not (isinstance(self.home_band, (int, np.integer))
                and self.home_band >= 0):
            raise ConfigurationError(
                f"EmitterSpec.home_band must be a non-negative integer, "
                f"got {self.home_band!r}")
        if not np.isfinite(self.snr_db):
            raise ConfigurationError(
                f"EmitterSpec(eid={self.eid}).snr_db must be finite, "
                f"got {self.snr_db!r}")
        if self.period < 1 or self.on_len < 1 or self.dwell < 1:
            raise ConfigurationError(
                f"EmitterSpec(eid={self.eid}) period/on_len/dwell must be >= 1 "
                f"(got period={self.period}, on_len={self.on_len}, "
                f"dwell={self.dwell})")
        for b in self.hop_set:
            if not isinstance(b, (int, np.integer)) or b < 0:
                raise ConfigurationError(
                    f"EmitterSpec(eid={self.eid}).hop_set contains an invalid "
                    f"band index {b!r}")


def _band_to_freq(band: int, n_bands: int, fmin: float, fmax: float) -> float:
    return fmin + (fmax - fmin) * (band + 0.5) / n_bands


class RFEnvironment:
    """Simulated multi-emitter RF spectrum over discrete bands and time slots."""

    def __init__(self, config: ScenarioConfig | None = None, **overrides):
        cfg = (config or ScenarioConfig()).scaled(**overrides) if overrides or config \
            else ScenarioConfig()
        _validate_config(cfg)
        self.cfg = cfg
        self.n_bands = cfg.n_bands
        self.T = cfg.T
        self.sens_db = cfg.sens_db
        self.rng = np.random.default_rng(cfg.seed)
        self.noise_floor = self.rng.lognormal(0.0, 0.5, cfg.n_bands) * cfg.noise_floor_scale
        self.rx_positions = [(0.0, 0.0)]
        self.scene_radius_km = 40.0
        specs, eid = [], 0

        def add(kind: str, threat_upto: int, count: int) -> None:
            nonlocal eid
            for _ in range(count):
                threat = eid < threat_upto
                specs.append(self._make_spec(eid, kind, threat))
                eid += 1

        base = cfg.n_stationary + cfg.n_agile + cfg.n_periodic
        n_evasive = getattr(cfg, "n_evasive", 0)
        add("stationary", max(1, cfg.n_stationary // 2), cfg.n_stationary)
        add("agile", cfg.n_stationary + max(1, cfg.n_agile // 2), cfg.n_agile)
        add("periodic", base + max(1, cfg.n_periodic // 2), cfg.n_periodic)
        add("spatial", base + cfg.n_periodic, cfg.n_spatial)
        if n_evasive:
            base2 = base + cfg.n_spatial
            add("evasive", base2 + max(1, n_evasive // 2), n_evasive)
        for _ in range(cfg.n_clutter):
            b = int(self.rng.integers(cfg.n_bands))
            rad = self.scene_radius_km * np.sqrt(self.rng.random())
            ang = self.rng.uniform(0, 2 * np.pi)
            x, y = float(rad * np.cos(ang)), float(rad * np.sin(ang))
            specs.append(EmitterSpec(
                eid, "stationary", b, float(self.rng.normal(cfg.snr_mean_db - 2.0, cfg.snr_std_db)),
                False, freq_mhz=_band_to_freq(b, cfg.n_bands, cfg.freq_min_mhz, cfg.freq_max_mhz),
                bearing_deg=float(np.degrees(np.arctan2(y, x)) % 360.0),
                x_km=x, y_km=y))
            eid += 1
        self.emitters = specs
        self._consec_intercepts: dict[int, int] = {}
        self.band_seq = self._generate()
        self.occupancy = np.zeros((cfg.n_bands, cfg.T), dtype=np.int8)
        rows, cols = np.nonzero(self.band_seq >= 0)
        self.occupancy[self.band_seq[rows, cols], cols] = 1

    def _make_spec(self, eid: int, kind: str, threat: bool) -> EmitterSpec:
        """Draw one random emitter of the requested kind from the scenario priors.

        Positions are sampled uniformly over a disc around the primary
        receiver; the reported bearing is the *geometric* bearing from that
        receiver, so angle-of-arrival measurements are physically consistent.
        """
        c = self.cfg
        band = int(self.rng.integers(c.n_bands))
        lo, hi = c.period_range
        olo, ohi = c.on_len_range
        hlo, hhi = c.hop_set_range
        dlo, dhi = c.dwell_range
        rad = self.scene_radius_km * np.sqrt(self.rng.random())
        ang = self.rng.uniform(0, 2 * np.pi)
        x = float(rad * np.cos(ang))
        y = float(rad * np.sin(ang))
        bearing = float(np.degrees(np.arctan2(y, x)) % 360.0)
        common = dict(
            snr_db=float(self.rng.normal(c.snr_mean_db, c.snr_std_db)),
            threat=threat,
            freq_mhz=_band_to_freq(band, c.n_bands, c.freq_min_mhz, c.freq_max_mhz),
            bearing_deg=bearing,
            x_km=x,
            y_km=y,
        )
        if kind == "stationary":
            return EmitterSpec(eid, kind, band, **common)
        if kind == "agile":
            if c.n_bands < 2:
                return EmitterSpec(eid, kind, band, hop_set=(band,), dwell=int(self.rng.integers(dlo, dhi + 1)), **common)
            hi_k = max(hlo + 1, min(hhi, c.n_bands) + 1)
            k = int(self.rng.integers(hlo, hi_k))
            k = max(2, min(k, c.n_bands))
            hops = tuple(sorted(int(x) for x in self.rng.choice(c.n_bands, size=k, replace=False)))
            return EmitterSpec(eid, kind, hops[0], hop_set=hops,
                               dwell=int(self.rng.integers(dlo, dhi + 1)), **common)
        if kind == "periodic":
            return EmitterSpec(eid, kind, band,
                               period=int(self.rng.integers(lo, min(hi, 160))),
                               on_len=int(self.rng.integers(olo, ohi + 1)), **common)
        if kind == "spatial":
            rate = float(self.rng.uniform(6, 30))
            bw = float(self.rng.uniform(2.5, 8.0))
            period = max(int(round(360.0 / rate)), lo)
            on_len = max(int(round(period * bw / 360.0)), olo)
            return EmitterSpec(eid, kind, band, rotation_rate_deg_s=rate,
                               beamwidth_deg=bw, period=period, on_len=on_len, **common)
        if kind == "evasive":
            # Evasive emitters behave like periodic but with a hop set they
            # can switch to when evading.
            if c.n_bands < 2:
                return EmitterSpec(eid, kind, band, hop_set=(band,),
                                   period=int(self.rng.integers(lo, min(hi, 100))),
                                   on_len=int(self.rng.integers(olo, ohi + 1)), dwell=1, **common)
            k = max(2, int(self.rng.integers(3, min(6, c.n_bands) + 1)))
            hops = tuple(sorted(int(x) for x in self.rng.choice(c.n_bands, size=k, replace=False)))
            period = int(self.rng.integers(lo, min(hi, 100)))
            on_len = int(self.rng.integers(olo, ohi + 1))
            return EmitterSpec(eid, kind, band, hop_set=hops,
                               period=period, on_len=on_len, dwell=1, **common)
        raise ValueError(kind)

    def _generate(self) -> np.ndarray:
        """Build the per-emitter band sequence array ``[E, T]`` (-1 = silent)."""
        E, T = len(self.emitters), self.T
        seq = np.full((E, T), -1, dtype=np.int16)
        markov_rows: dict[int, np.ndarray] = {}
        for i, e in enumerate(self.emitters):
            if e.kind == "stationary":
                seq[i, :] = e.home_band
            elif e.kind == "agile":
                t0 = 0
                markov = getattr(self.cfg, "agile_mode", "random") == "markov"
                if markov:
                    # Draw one sticky Markov transition matrix per emitter:
                    # high self-transition ("stickiness") plus a structured
                    # preference for one successor band, making hopping
                    # learnable from observations alone.
                    k = len(e.hop_set)
                    idx = {b: i for i, b in enumerate(e.hop_set)}
                    stick = float(self.rng.uniform(0.55, 0.85))
                    succ = idx.get(int(e.home_band) % int(self.n_bands), 0)
                    row = np.full(k, (1.0 - stick) / max(1, k - 1))
                    row[succ] = 0.0
                    row *= (1.0 - stick) / max(row.sum(), 1e-9)
                    row[succ] = stick
                    markov_rows[i] = row
                prev = -1
                while t0 < T:
                    d = min(e.dwell, T - t0)
                    if markov:
                        row = markov_rows[i]
                        j = (int(self.rng.choice(k, p=row)) if prev in idx
                             else int(self.rng.integers(k)))
                        b = e.hop_set[j]
                    else:
                        b = e.hop_set[self.rng.integers(len(e.hop_set))]
                    seq[i, t0:t0 + d] = b
                    prev = int(b)
                    t0 += d
            else:
                # periodic, spatial, and evasive all use phase-based windows
                phase = int(self.rng.integers(e.period))
                on = e.on_len + (1 if self.rng.random() < 0.3 else 0)
                s = -phase
                while s < T:
                    a, bnd = max(s, 0), min(s + on, T)
                    if bnd > a:
                        seq[i, a:bnd] = e.home_band
                    s += e.period
        return seq

    def report_intercept(self, eid: int, t: int) -> None:
        """Notify the environment that emitter ``eid`` was intercepted at slot ``t``.

        For evasive emitters, consecutive interceptions (>= 3) trigger an evasion
        protocol: the emitter shifts its rotation phase or swaps to a new
        frequency hop-set.  The band sequence is dynamically overwritten from
        ``t`` onward to reflect the new behaviour.

        Raises:
            SimulationBoundsError: if ``eid`` or ``t`` is out of range.
        """
        if not 0 <= eid < len(self.emitters):
            raise SimulationBoundsError(
                f"emitter id {eid!r} out of range [0, {len(self.emitters)})")
        if not 0 <= t < self.T:
            raise SimulationBoundsError(
                f"time slot {t!r} out of range [0, {self.T})")
        spec = self.emitters[eid]
        if spec.kind != "evasive":
            return
        # Track consecutive intercepts
        key = eid
        if not hasattr(self, "_consec_intercepts"):
            self._consec_intercepts: dict[int, int] = {}
        self._consec_intercepts[key] = self._consec_intercepts.get(key, 0) + 1
        if self._consec_intercepts[key] < 3:
            return
        # Evasion triggered - reset counter and reconfigure
        self._consec_intercepts[key] = 0
        row = self.band_seq[eid]
        old_band = int(row[t]) if row[t] >= 0 else spec.home_band
        if spec.kind == "evasive" and spec.hop_set and len(spec.hop_set) > 1:
            # Swap to a different band from the hop set
            candidates = [b for b in spec.hop_set if b != old_band]
            new_band = int(self.rng.choice(candidates)) if candidates else old_band
            # Overwrite band_seq from t onward with the new band pattern
            # using a shifted phase
            new_phase = int(self.rng.integers(max(1, spec.period)))
            s = t - new_phase
            while s < self.T:
                on = spec.on_len + (1 if self.rng.random() < 0.3 else 0)
                a, bnd = max(s, 0), min(s + on, self.T)
                if bnd > a:
                    row[a:bnd] = new_band
                s += spec.period
        else:
            # Shift rotation phase by a random offset
            shift = int(self.rng.integers(2, max(3, spec.period // 2)))
            for s in range(t, self.T):
                phase_slot = (s + shift) % spec.period
                if phase_slot < spec.on_len:
                    row[s] = spec.home_band
                else:
                    row[s] = -1
        # Rebuild occupancy from modified band_seq
        self.occupancy[:] = 0
        rows, cols = np.nonzero(self.band_seq >= 0)
        self.occupancy[self.band_seq[rows, cols], cols] = 1

    def emitters_at(self, band: int, t: int) -> list[EmitterSpec]:
        """Return emitters transmitting in ``band`` at slot ``t``.

        Raises:
            InvalidBandError: if ``band`` is outside ``[0, n_bands)``.
            SimulationBoundsError: if ``t`` is outside ``[0, T)``.
        """
        if not 0 <= band < self.n_bands:
            raise InvalidBandError(
                f"band {band!r} out of range [0, {self.n_bands})")
        if not 0 <= t < self.T:
            raise SimulationBoundsError(
                f"time slot {t!r} out of range [0, {self.T})")
        col = self.band_seq[:, t]
        # Fast path: use numpy for the lookup, then list-comp for emitter access
        matches = np.flatnonzero(col == band)
        if len(matches) == 0:
            return []
        ems = self.emitters
        return [ems[i] for i in matches]

    def present(self, band: int, t: int) -> bool:
        """Whether any emitter transmits in ``band`` at slot ``t``.

        Raises:
            InvalidBandError: if ``band`` is outside ``[0, n_bands)``.
            SimulationBoundsError: if ``t`` is outside ``[0, T)``.
        """
        if not 0 <= band < self.n_bands:
            raise InvalidBandError(
                f"band {band!r} out of range [0, {self.n_bands})")
        if not 0 <= t < self.T:
            raise SimulationBoundsError(
                f"time slot {t!r} out of range [0, {self.T})")
        return bool((self.band_seq[:, t] == band).any())

    def next_on_start(self, eid: int, after_t: int) -> int | None:
        """Next rising edge of emitter ``eid``'s transmission after ``after_t``.

        Raises:
            SimulationBoundsError: if ``eid`` or ``after_t`` is out of range.
        """
        if not 0 <= eid < len(self.emitters):
            raise SimulationBoundsError(
                f"emitter id {eid!r} out of range [0, {len(self.emitters)})")
        if not 0 <= after_t < self.T:
            raise SimulationBoundsError(
                f"time slot {after_t!r} out of range [0, {self.T})")
        row = self.band_seq[eid]
        band = self.emitters[eid].home_band
        prev = row[after_t] == band if after_t < self.T else False
        for s in range(after_t + 1, self.T):
            cur = row[s] == band
            if cur and not prev:
                return s
            prev = cur
        return None
