"""Smart Scan Strategy for Electronic Warfare - ML-based ES receiver scheduler.

Public API: build environments from configs or PDW datasets, schedule
single or multiple ES receivers with any of seven policies (three open-loop
baselines, a UCB bandit, two RL agents and the proposed SmartScan hybrid),
evaluate with rigorous figures of merit, persist trained models safely and
visualise everything.
"""
from .config import ScenarioConfig
from .environment import RFEnvironment, EmitterSpec
from .receiver import ESReceiver, DwellResult
from .metrics import compute_metrics, Trace, json_safe, METRIC_LABELS
from .schedulers import (BaseScheduler, SequentialSweep, RandomScan,
                         PrioritySweep, UCBScheduler, LinearQLearning,
                         DQNScheduler, SmartScanScheduler)
from .persistence import save_scheduler, load_scheduler

__version__ = "0.3.0"

__all__ = [
    "ScenarioConfig", "RFEnvironment", "EmitterSpec", "ESReceiver",
    "DwellResult", "compute_metrics", "Trace", "json_safe", "METRIC_LABELS",
    "BaseScheduler", "SequentialSweep", "RandomScan", "PrioritySweep",
    "UCBScheduler", "LinearQLearning", "DQNScheduler", "SmartScanScheduler",
    "save_scheduler", "load_scheduler", "__version__",
]
