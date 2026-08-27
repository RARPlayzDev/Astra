"""Safe model persistence: NPZ-based save/load (no pickle, no code execution).

Trained scheduler parameters are stored as plain arrays inside an ``.npz``
archive plus a JSON metadata record.  Loading uses ``allow_pickle=False`` so a
malicious artifact can never execute code - addressing the arbitrary-code-
execution risk of pickle-based persistence.

Supported schedulers must implement ``get_weights``/``set_weights`` (parameter
snapshots) and optionally ``get_state``/``load_state`` (SmartScan lock tables).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .schedulers import (BaseScheduler, UCBScheduler, LinearQLearning,
                         DQNScheduler, SmartScanScheduler)

FORMAT = "ewsmart-npz-v1"
_REGISTRY = {c.__name__: c for c in (UCBScheduler, LinearQLearning,
                                     DQNScheduler, SmartScanScheduler)}


def _encode_weights(sched: BaseScheduler, arrays: dict) -> dict:
    """Flatten a scheduler's weight snapshot into named arrays + JSON meta."""
    meta: dict = {}
    if isinstance(sched, LinearQLearning):
        w = sched.get_weights()
        arrays["theta"] = np.asarray(w["theta"], dtype=np.float64)
        meta["eps"] = float(w["eps"])
    elif isinstance(sched, DQNScheduler):
        w = sched.get_weights()
        for i, (Wm, bv) in enumerate(zip(w["W"], w["b"])):
            arrays[f"W{i}"] = np.asarray(Wm, dtype=np.float64)
            arrays[f"b{i}"] = np.asarray(bv, dtype=np.float64)
        meta["eps"] = float(w["eps"])
    elif isinstance(sched, UCBScheduler):
        arrays["mu"] = np.asarray(sched.mu, dtype=np.float64)
        arrays["n"] = np.asarray(sched.n, dtype=np.float64)
    elif isinstance(sched, SmartScanScheduler):
        meta["state_json"] = json.dumps(sched.get_state())
    return meta


def _decode_weights(sched: BaseScheduler, meta: dict, arrays: dict) -> None:
    """Restore weights from named arrays + JSON meta into a fresh scheduler."""
    if isinstance(sched, LinearQLearning):
        sched.set_weights({"theta": arrays["theta"], "eps": meta["eps"]})
    elif isinstance(sched, DQNScheduler):
        w = {"W": [], "b": [], "eps": meta["eps"]}
        i = 0
        while f"W{i}" in arrays:
            w["W"].append(arrays[f"W{i}"])
            w["b"].append(arrays[f"b{i}"])
            i += 1
        sched.set_weights(w)
    elif isinstance(sched, UCBScheduler):
        sched.mu = arrays["mu"].copy()
        sched.n = arrays["n"].copy()
    elif isinstance(sched, SmartScanScheduler):
        sched.load_state(json.loads(meta["state_json"]))


def save_scheduler(path: str | Path, sched: BaseScheduler) -> None:
    """Persist a trained scheduler to an ``.npz`` archive at ``path``."""
    cls = type(sched).__name__
    if cls not in _REGISTRY:
        raise ValueError(f"non-persistable scheduler class: {cls}")
    arrays: dict[str, np.ndarray] = {}
    meta = {"format": FORMAT, "class": cls, "n_bands": int(sched.n_bands)}
    meta.update(_encode_weights(sched, arrays))
    np.savez(str(path), meta=np.array(json.dumps(meta)), **arrays)


def load_scheduler(path: str | Path) -> BaseScheduler:
    """Restore a scheduler previously written by :func:`save_scheduler`."""
    with np.load(str(path), allow_pickle=False) as z:
        meta = json.loads(str(z["meta"]))
        if meta.get("format") != FORMAT:
            raise ValueError(f"unsupported artifact format: {meta.get('format')!r}")
        cls = _REGISTRY.get(meta["class"])
        if cls is None:
            raise ValueError(f"unknown scheduler class: {meta['class']}")
        arrays = {k: z[k] for k in z.files if k != "meta"}
    sched = cls(meta["n_bands"])
    _decode_weights(sched, meta, arrays)
    return sched
