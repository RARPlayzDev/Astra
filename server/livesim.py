"""Live paired simulation arena for the ASTRA command centre.

Upgraded for full backend parity:
  * arbitrary scheduler pairing (both sides selectable),
  * cooperative multi-receiver teams with per-slot de-confliction,
  * receiver sensitivity control (detection-threshold offset),
  * optional use of trained model artifacts (.npz),
  * extended figures of merit (TTFF, prediction accuracy, periodic locks,
    all-emitter interception ratio),
  * emitter identification reports (JC Wise-style library) at episode end.

Both sides always fly byte-identical battlefields.
"""
from __future__ import annotations

import threading
import time
from collections import deque

import numpy as np

from ewsmart.environment import RFEnvironment
from ewsmart.receiver import ESReceiver
from ewsmart.runner import step_reward


def make_live_scheduler(name: str, n_bands: int, seed: int):
    """Instantiate a scheduler by public name for live operation."""
    from ewsmart.schedulers import (SequentialSweep, RandomScan, PrioritySweep,
                                    UCBScheduler, LinearQLearning, DQNScheduler,
                                    SmartScanScheduler)
    factories = {
        "smart-scan": lambda: SmartScanScheduler(n_bands, seed=seed),
        "openloop-sequential": lambda: SequentialSweep(n_bands, seed=seed),
        "openloop-random": lambda: RandomScan(n_bands, seed=seed),
        "bandit-ucb": lambda: UCBScheduler(n_bands, seed=seed),
        "rl-linear-q": lambda: LinearQLearning(n_bands, seed=seed),
        "rl-dqn": lambda: DQNScheduler(n_bands, seed=seed),
    }
    if name not in factories:
        raise ValueError(f"unknown scheduler '{name}'")
    return factories[name]()


PERSISTABLE = {"smart-scan", "bandit-ucb", "rl-linear-q", "rl-dqn"}
WINDOW = 320
CHUNK = 50  # steps per SSE frame (was 10; 5x faster wall-clock)


def _maybe_load_weights(name: str, instance):
    """Apply saved .npz weights to a persistable scheduler, if present."""
    if name not in PERSISTABLE:
        return instance, False
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "models" / f"{name}.npz"
    if not p.exists():
        return instance, False
    try:
        from ewsmart.persistence import load_scheduler
        loaded = load_scheduler(p)
        if hasattr(instance, "set_weights") and hasattr(loaded, "get_weights"):
            instance.set_weights(loaded.get_weights())
        if hasattr(instance, "load_state") and hasattr(loaded, "get_state"):
            instance.load_state(loaded.get_state())
        return instance, True
    except Exception:
        return instance, False


class _Runner:
    """One side of the arena: a (possibly cooperative) team of receivers."""

    def __init__(self, name: str, env: RFEnvironment, seed: int,
                 policy: str = "smart-scan", team: int = 1,
                 sens_offset: float = 6.0, use_saved: bool = False):
        self.name = name
        self.env = env
        self.policy = policy
        self.team = max(1, min(3, int(team)))
        self.rx = [ESReceiver(env, seed=seed + 1 + i, pd_mid_offset=sens_offset)
                   for i in range(self.team)]
        self.scheds = []
        self.loaded = False
        for i in range(self.team):
            s = make_live_scheduler(policy, env.n_bands, seed + i)
            s.reset(horizon=env.T)
            if use_saved and i == 0:
                s, self.loaded = _maybe_load_weights(policy, s)
            self.scheds.append(s)

        self.t = 0
        self.reward_sum = 0.0
        self.hits = 0
        self.false_alarms = 0
        self.n_threats = sum(1 for e in env.emitters if e.threat)
        # Pre-computed caches for hot-path performance
        self._threat_eids = frozenset(e.eid for e in env.emitters if e.threat)
        self._eid_lookup = {e.eid: e for e in env.emitters}
        self._has_evasive = any(e.kind == "evasive" for e in env.emitters)
        self._n_emitters = len(env.emitters)
        self.first_intercept: dict[int, int] = {}
        self.ttff_all: list[int] = []
        self.threat_ttff: list[int] = []
        self.pred_correct = 0
        self.pred_total = 0
        self.pred_true_pos = 0  # predicted True AND was True
        self.pred_true_total = 0  # predicted True (total)
        # Steady-state prediction accuracy: the initial calibration transient
        # (reconnaissance / first lock acquisition) is excluded for *every*
        # scheduler identically - parity with ewsmart.metrics.compute_metrics.
        self.warm = min(600, max(1, env.T // 5))
        self.streams: dict[int, list[dict]] = {}
        self.evasion_events: list[dict] = []
        self.dnd_bands: dict[int, int] = {}  # band -> receiver index that owns it
        # ring buffers for the client waterfall
        self.occ = np.zeros((env.n_bands, WINDOW), dtype=np.int8)
        self.actions = np.full(WINDOW, -1, dtype=np.int16)
        self.hitmask = np.zeros(WINDOW, dtype=np.int8)

    # ------------------------------------------------------------- helpers
    def _select_joint(self, t: int) -> list[int]:
        chosen: list[int] = []
        for s in self.scheds:
            b = int(s.select(t))
            if b in chosen:
                cands = [x for x in range(self.env.n_bands) if x not in chosen]
                if cands:
                    mu = getattr(s, "mu", None)
                    b = int(max(cands, key=lambda c: mu[c])) if mu is not None \
                        else cands[t % len(cands)]
            chosen.append(b)
        return chosen

    def _locks(self) -> int:
        return sum(len(getattr(s, "est", {}) or {}) for s in self.scheds)

    def _collect_dnd(self) -> dict[int, int]:
        """Collect DND (Do Not Disturb) tokens from all schedulers.
        Returns {band: receiver_index} for bands that are locked/owned."""
        dnd: dict[int, int] = {}
        for i, s in enumerate(self.scheds):
            est = getattr(s, "est", {})
            for band in est:
                if band not in dnd:
                    dnd[band] = i
        return dnd

    # ------------------------------------------------------------- stepping
    def step(self) -> dict:
        t = self.t
        bands = self._select_joint(t)
        results = [rx.dwell(b, t) for rx, b in zip(self.rx, bands)]
        r_total = 0.0
        any_hit = False
        any_fa = False
        truth_present = False
        before = len(self.first_intercept)
        toa_t = t * 1000.0  # precompute once
        for res in results:
            r_total += step_reward(self.env, res, self.first_intercept)
            any_hit |= bool(res.hit and not res.false_alarm)
            any_fa |= bool(res.false_alarm)
            truth_present |= bool(res.truth_present)
            # Use emitters from dwell result (avoids re-fetch)
            for e in res.emitters:
                buf = self.streams.setdefault(e.eid, [])
                if len(buf) < 64:
                    buf.append({"toa_us": toa_t, "freq_mhz": e.freq_mhz,
                                "pw_us": e.pw_us, "pa_db": e.snr_db,
                                "aoa_deg": e.bearing_deg})
        self.reward_sum += r_total
        self.hits += int(any_hit)
        self.false_alarms += int(any_fa)

        newly = len(self.first_intercept) - before
        if newly > 0:
            self.ttff_all.extend([t] * newly)
            for eid in list(self.first_intercept.keys())[before:]:
                e = self._eid_lookup.get(eid)
                if e is not None and e.eid in self._threat_eids:
                    self.threat_ttff.append(t)

        preds = [s.predict(t, b) for s, b in zip(self.scheds, bands)]
        if t >= self.warm:  # steady-state only: parity with compute_metrics
            self.pred_correct += int(preds[0] == truth_present)
            self.pred_total += 1
            # Track active predictions (when scheduler actually predicts True)
            if preds[0]:
                self.pred_true_total += 1
                if truth_present:
                    self.pred_true_pos += 1

        self.scheds[0].update(t, bands[0], results[0], r_total / max(1, len(results)))

        # Update DND tokens (only when locks change)
        if getattr(self.scheds[0], 'est', None):
            self.dnd_bands = self._collect_dnd()

        # Track evasion events (skip entirely if no evasive emitters)
        if self._has_evasive and hasattr(self.env, '_consec_intercepts'):
            for eid, count in self.env._consec_intercepts.items():
                if count >= 3 and not any(ev.get('eid') == eid and ev.get('slot') == t
                                          for ev in self.evasion_events):
                    emitter = self._eid_lookup.get(eid)
                    if emitter and emitter.kind == 'evasive':
                        self.evasion_events.append({
                            'eid': eid, 'slot': t,
                            'kind': 'band_shift',
                            'detail': f'Emitter {eid} evaded after 3 consecutive intercepts'
                        })

        col = t % WINDOW
        self.occ[:, col] = self.env.occupancy[:, t]
        self.actions[col] = bands[0]
        self.hitmask[col] = int(any_hit)
        self.t += 1
        return {"band": int(bands[0]), "hit": bool(any_hit),
                "false_alarm": bool(any_fa),
                "truth": bool(truth_present), "reward": float(r_total)}

    def kpis(self) -> dict:
        n = max(1, self.t)
        cov = len([e for e in self.first_intercept if e in self._threat_eids])
        all_ratio = len(self.first_intercept) / max(1, self._n_emitters)
        return {"slots": self.t,
                "avg_reward": round(self.reward_sum / n, 4),
                "threat_coverage": round(cov / max(1, self.n_threats), 4),
                "intercept_ratio": round(all_ratio, 4),
                "threats_found": cov,
                "n_threats": self.n_threats,
                "hit_rate": round(self.hits / n, 4),
                "false_alarms": self.false_alarms,
                "mean_ttff": round(float(np.mean(self.ttff_all)), 1)
                             if self.ttff_all else None,
                "threat_mean_ttff": round(float(np.mean(self.threat_ttff)), 1)
                                    if self.threat_ttff else None,
                # Denominator is the number of *scored* (post-warm-up) slots,
                # so the figure is a steady-state accuracy, not a slot ratio.
                "pred_accuracy": round(
                    self.pred_correct / max(1, self.pred_total), 4),
                "pred_active_accuracy": round(
                    self.pred_true_pos / max(1, self.pred_true_total), 4),
                "pred_active_count": self.pred_true_total,
                "locks": self._locks(),
                "team": self.team,
                "loaded_weights": self.loaded,
                "dnd_bands": self.dnd_bands,
                "evasion_count": len(self.evasion_events)}

    def frame(self, steps: list[dict]) -> dict:
        col0 = (self.t - len(steps)) % WINDOW
        idx = [(col0 + i) % WINDOW for i in range(len(steps))]
        occ_cols = self.occ[:, idx].astype(int).tolist()
        return {"name": self.name,
                "t0": self.t - len(steps), "t1": self.t,
                "occupancy": occ_cols,
                "actions": [int(self.actions[i]) for i in idx],
                "hits": [int(self.hitmask[i]) for i in idx],
                "steps": steps,
                "kpis": self.kpis(),
                "dnd_bands": self.dnd_bands,
                "evasion_events": self.evasion_events[-5:]}

    def identification_rows(self) -> list[dict]:
        try:
            from ewsmart.identification import (build_default_library,
                                                identification_report,
                                                tag_environment)
            tag_environment(self.env)
            rep = identification_report(self.env, self.streams)
            rows = [{"eid": r["eid"], "identified": r["identified"],
                                       "cls": r.get("class"), "threat": r["threat"],
                                       "confidence": r["confidence"], "pulses": r["pulses"],
                                       "ground_truth": r["ground_truth"],
                                       "correct": r["correct"]}
                    for r in rep.get("rows", [])]
            rows.sort(key=lambda r: (-r["confidence"], -r["pulses"]))
            return rows
        except Exception:
            return []


class LiveArena:
    """Paired A/B simulation thread emitting synchronised frames."""

    def __init__(self, n_bands: int = 24, T: int = 2400, speed: int = 400,
                 base_seed: int = 4242, sched_a: str = "smart-scan",
                 sched_b: str = "openloop-sequential", team_size: int = 1,
                 sens_offset: float = 6.0, use_saved: bool = False):
        self.n_bands, self.T, self.speed, self.base_seed = \
            n_bands, T, max(20, speed), base_seed
        self.side_policy = {"smart-scan": sched_a, "openloop-sequential": sched_b}
        self.team_size = team_size
        self.sens_offset = sens_offset
        self.use_saved = use_saved
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.frames: deque = deque(maxlen=1000)
        self.episode_done: deque = deque(maxlen=50)
        self.lock = threading.Lock()
        self.generation = 0
        self.runners: list[_Runner] = []
        self.slot = 0
        self.running_flag = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def snapshot(self) -> dict:
        with self.lock:
            return {"running": self.running_flag,
                    "slot": self.slot,
                    "T": self.T,
                    "generation": self.generation,
                    "policies": self.side_policy,
                    "kpis": {r.name: r.kpis() for r in self.runners}}

    def _fresh_episode(self):
        seed = self.base_seed + self.generation * 7919
        runners = []
        for i, side in enumerate(("smart-scan", "openloop-sequential")):
            env = RFEnvironment(n_bands=self.n_bands, T=self.T, seed=seed)
            runners.append(_Runner(
                side, env, seed + 100 * i,
                policy=self.side_policy[side], team=self.team_size,
                sens_offset=self.sens_offset, use_saved=self.use_saved))
        with self.lock:
            self.runners = runners
        return runners

    def _loop(self):
        self.running_flag = True
        try:
            while not self._stop.is_set():
                runners = self._fresh_episode()
                self.slot = 0
                delay = CHUNK / float(self.speed)
                while self.slot < self.T and not self._stop.is_set():
                    tick = {}
                    for r in runners:
                        steps = [r.step()
                                 for _ in range(min(CHUNK, self.T - self.slot))]
                        tick[r.name] = r.frame(steps)
                    self.slot = min(r.t for r in runners)
                    with self.lock:
                        self.frames.append({"type": "frame", "slot": self.slot,
                                            "sims": tick})
                    time.sleep(delay)
                finals = {r.name: r.kpis() for r in runners}
                id_rows = {r.name: r.identification_rows() for r in runners}
                with self.lock:
                    self.episode_done.append(
                        {"type": "episode_done", "generation": self.generation,
                         "finals": finals, "id_reports": id_rows})
                    self.generation += 1
        finally:
            self.running_flag = False
