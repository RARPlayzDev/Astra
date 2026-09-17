import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))
"""Edge-case and validation tests: every scheduler and the environment must
reject malformed inputs with branded EwsmartError subclasses."""
import numpy as np
import pytest

import ewsmart
from ewsmart import exceptions as exc
from ewsmart.config import ScenarioConfig
from ewsmart.environment import RFEnvironment, _validate_config
from ewsmart.receiver import DwellResult
from ewsmart.schedulers import (BaseScheduler, SequentialSweep, RandomScan,
                                PrioritySweep, UCBScheduler, LinearQLearning,
                                DQNScheduler, SmartScanScheduler)


def _factories():
    """Factory per concrete scheduler (kept small for fast DQN construction)."""
    return [
        lambda nb: SequentialSweep(nb),
        lambda nb: RandomScan(nb),
        lambda nb: PrioritySweep(nb, (0,)),
        lambda nb: UCBScheduler(nb),
        lambda nb: LinearQLearning(nb),
        lambda nb: DQNScheduler(nb, hidden=(8, 8)),
        lambda nb: SmartScanScheduler(nb),
    ]


def _fact_names():
    return ["sequential", "random", "priority", "ucb", "linear-q", "dqn",
            "smart-scan"]


def _dwell_res(band=0, t=0, hit=False):
    return DwellResult(band=band, t=t, hit=hit, false_alarm=False,
                       snr_db=10.0 if hit else -np.inf, truth_present=hit,
                       detections=((10.0, 45.0),) if hit else ())


SCHED_IDS = _fact_names()


# ---------------------------------------------------------------------------
# n_bands construction validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n_bands", [0, -1, -100, 1.5, "8", None])
def test_scheduler_rejects_invalid_n_bands(n_bands):
    for factory in _factories():
        with pytest.raises(exc.ConfigurationError):
            factory(n_bands)


@pytest.mark.parametrize("n_bands", [0, -5])
def test_base_scheduler_rejects_invalid_n_bands(n_bands):
    with pytest.raises(exc.ConfigurationError):
        BaseScheduler(n_bands)


def test_scheduler_accepts_numpy_integer_n_bands():
    s = SequentialSweep(np.int64(8))
    assert s.n_bands == 8 and s.select(3) == 3


# ---------------------------------------------------------------------------
# horizon validation
# ---------------------------------------------------------------------------

def test_negative_horizon_rejected():
    with pytest.raises(exc.ConfigurationError):
        BaseScheduler(8).reset(horizon=-1)
    for factory in _factories():
        s = factory(8)
        with pytest.raises(exc.ConfigurationError):
            s.reset(horizon=-10)


def test_none_and_zero_horizon_accepted():
    for factory in _factories():
        s = factory(8)
        s.reset(horizon=None)
        s.reset(horizon=0)


# ---------------------------------------------------------------------------
# select() time-slot validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("t", [-1, -1000])
@pytest.mark.parametrize("factory", _factories(), ids=SCHED_IDS)
def test_select_negative_t_raises(factory, t):
    s = factory(8)
    s.reset(horizon=100)
    with pytest.raises(exc.SimulationBoundsError):
        s.select(t)


# ---------------------------------------------------------------------------
# update() band / reward / result validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("band", [-1, 8, 100])
@pytest.mark.parametrize("factory", _factories(), ids=SCHED_IDS)
def test_update_out_of_range_band_raises(factory, band):
    s = factory(8)
    s.reset(horizon=10)
    with pytest.raises(exc.InvalidBandError):
        s.update(0, band, _dwell_res(), 0.1)


@pytest.mark.parametrize("bad_r", [float("nan"), float("inf"), float("-inf"),
                                   "oops", None, [1.0]])
@pytest.mark.parametrize("factory", _factories(), ids=SCHED_IDS)
def test_update_invalid_reward_raises(factory, bad_r):
    s = factory(8)
    s.reset(horizon=10)
    with pytest.raises(exc.InvalidRewardError):
        s.update(0, 0, _dwell_res(), bad_r)


@pytest.mark.parametrize("factory", _factories(), ids=SCHED_IDS)
def test_update_result_missing_attributes_raises(factory):
    s = factory(8)
    s.reset(horizon=10)

    class Fake:
        pass

    with pytest.raises(exc.InvalidDwellResultError):
        s.update(0, 0, Fake(), 0.1)

    partial = Fake()
    partial.hit = True          # false_alarm / detections missing
    with pytest.raises(exc.InvalidDwellResultError):
        s.update(0, 0, partial, 0.1)


def test_update_base_scheduler_validates():
    base = BaseScheduler(4)
    with pytest.raises(exc.InvalidBandError):
        base.update(0, 9, _dwell_res(), 0.0)
    with pytest.raises(exc.InvalidRewardError):
        base.update(0, 0, _dwell_res(), float("nan"))
    with pytest.raises(exc.InvalidDwellResultError):
        base.update(0, 0, object(), 0.0)


# ---------------------------------------------------------------------------
# priority-band validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [-1, 8, 999])
def test_priority_sweep_out_of_range_priority_band(bad):
    with pytest.raises(exc.InvalidBandError):
        PrioritySweep(8, (1, bad), seed=0)


# ---------------------------------------------------------------------------
# environment bounds validation
# ---------------------------------------------------------------------------

def test_env_present_and_emitters_at_bounds():
    env = RFEnvironment(n_bands=6, T=50, seed=1)
    with pytest.raises(exc.InvalidBandError):
        env.present(-1, 0)
    with pytest.raises(exc.InvalidBandError):
        env.present(6, 0)
    with pytest.raises(exc.SimulationBoundsError):
        env.present(0, 50)
    with pytest.raises(exc.InvalidBandError):
        env.emitters_at(-2, 0)
    with pytest.raises(exc.SimulationBoundsError):
        env.emitters_at(0, -1)
    with pytest.raises(exc.SimulationBoundsError):
        env.report_intercept(999, 0)
    with pytest.raises(exc.SimulationBoundsError):
        env.next_on_start(0, -5)


# ---------------------------------------------------------------------------
# configuration validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("overrides", [
    {"n_bands": 0}, {"n_bands": -3}, {"T": 0}, {"T": -10},
    {"snr_std_db": -1.0}, {"noise_floor_scale": -0.5},
    {"freq_max_mhz": 100.0},          # <= freq_min_mhz
    {"period_range": (0, 10)},        # lo must be >= 1
    {"on_len_range": (5, 2)},         # lo > hi
    {"dwell_range": (3, 3, 3)},       # malformed range
    {"snr_mean_db": float("nan")},
])
def test_env_rejects_invalid_config(overrides):
    with pytest.raises(exc.ConfigurationError):
        RFEnvironment(**overrides)


def test_env_prob_like_fields_validated():
    import dataclasses

    @dataclasses.dataclass
    class _Cfg(ScenarioConfig):
        threat_prob: float = 0.5

    _validate_config(_Cfg())                      # in range: fine
    with pytest.raises(exc.ConfigurationError):
        _validate_config(_Cfg(threat_prob=1.5))   # > 1.0
    with pytest.raises(exc.ConfigurationError):
        _validate_config(_Cfg(threat_prob=-0.1))  # < 0.0


def test_emitter_spec_validated():
    from ewsmart.environment import EmitterSpec
    with pytest.raises(exc.ConfigurationError):
        EmitterSpec(eid=0, kind="bogus", home_band=0, snr_db=10.0, threat=False)
    with pytest.raises(exc.ConfigurationError):
        EmitterSpec(eid=0, kind="stationary", home_band=-2, snr_db=10.0,
                    threat=False)
    with pytest.raises(exc.ConfigurationError):
        EmitterSpec(eid=0, kind="stationary", home_band=0, snr_db=float("nan"),
                    threat=False)
    with pytest.raises(exc.ConfigurationError):
        EmitterSpec(eid=0, kind="periodic", home_band=0, snr_db=10.0,
                    threat=False, period=0)


def test_all_exceptions_derive_from_branded_base():
    for name in ("ConfigurationError", "InvalidBandError",
                 "SimulationBoundsError", "InvalidDwellResultError",
                 "InvalidRewardError", "SchedulerStateError",
                 "DatabaseError"):
        assert issubclass(getattr(exc, name), exc.EwsmartError)
        assert issubclass(getattr(exc, name), ewsmart.EwsmartError)


# ---------------------------------------------------------------------------
# environment extreme-but-valid dimensions
# ---------------------------------------------------------------------------

def test_env_extreme_many_bands():
    env = RFEnvironment(n_bands=10000, T=20, seed=0, n_stationary=1,
                        n_agile=0, n_periodic=0, n_spatial=0, n_clutter=0)
    assert env.n_bands == 10000
    assert env.present(9999, 0) in (True, False)


def test_env_zero_emitters_metrics_safe():
    cfg = ScenarioConfig(n_bands=6, T=120, seed=1, n_stationary=0, n_agile=0,
                         n_periodic=0, n_spatial=0, n_clutter=0,
                         n_fhss=0, n_tdma=0)
    env = RFEnvironment(cfg)
    assert env.emitters == []
    from ewsmart.runner import run_episode
    from ewsmart.metrics import compute_metrics
    from ewsmart.schedulers import SmartScanScheduler
    m = compute_metrics(env, run_episode(env, SmartScanScheduler(6, seed=2),
                                         seed=3))
    assert m["intercept_ratio"] == 0.0
    assert m["threat_intercept_ratio"] == 0.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
