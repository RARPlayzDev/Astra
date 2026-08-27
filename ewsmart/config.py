"""Scenario configuration: JSON-serialisable description of an RF environment."""
from __future__ import annotations

import json
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
