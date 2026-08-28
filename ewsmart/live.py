"""Live radar integration: stream real or simulated PDWs into the scheduler.

This module is the bridge between the simulated world and **real hardware**.
Any system that can emit pulse-descriptor words (PDWs) - an SDR sweep, a radar
warning receiver, a log file, or a UDP feed from a signal processor - can be
plugged in.  Three source adapters are provided:

* :class:`SimulatedLiveSource` - streams PDWs from a simulated environment
  (demo mode, also used for the command centre's live view).
* :class:`UDPSource` - receives JSON PDWs on a UDP port (the recommended path
  for real radar/SDR front-ends; see ``tools/sdr_bridge.py``).
* :class:`FileTailSource` - follows a growing JSONL/CSV log written by
  third-party equipment.

:class:`LiveSpectrum` maintains a rolling band x slot occupancy picture built
purely from received PDWs, and :class:`OnlineScanner` runs any scheduler
against the live picture one slot at a time, producing the same figures of
merit as the offline pipeline.
"""
from __future__ import annotations

import json
import socket
import threading
import time
from collections import deque
from pathlib import Path

import numpy as np

from .config import ScenarioConfig
from .environment import RFEnvironment


def _band_of(freq_mhz: float, n_bands: int, fmin: float, fmax: float) -> int:
    """Map a frequency to its band index (clipped to the tuning range)."""
    frac = (float(freq_mhz) - fmin) / max(1e-9, (fmax - fmin))
    return int(np.clip(frac * n_bands, 0, n_bands - 1))


def _slot_of(toa_us: float, t0_us: float, slot_us: float) -> int:
    return int((float(toa_us) - t0_us) / max(1e-9, slot_us))


class SimulatedLiveSource:
    """Streams PDWs from a simulated environment indefinitely.

    Emits pulses for every transmitting emitter each tick, honouring each
    emitter's detection probability so the feed behaves like a real sensor.
    The environment loops (``t % T``) so a demo never runs dry.
    """

    def __init__(self, env: RFEnvironment, seed: int = 0, slot_us: float = 1000.0):
        from .receiver import ESReceiver
        self.env = env
        self.rx = ESReceiver(env, seed=seed)
        self.slot_us = slot_us
        self.t = 0

    def poll(self) -> tuple[int, list[dict]]:
        """Advance one slot; returns ``(slot_index, pdws)``."""
        t_mod = self.t % self.env.T
        pdws: list[dict] = []
        for b in range(self.env.n_bands):
            res = self.rx.dwell(b, t_mod)
            for p in res.pdws:
                p = dict(p)
                p["_band"] = b
                pdws.append(p)
        self.t += 1
        return self.t - 1, pdws


class UDPSource:
    """Receive JSON PDWs on a UDP port from real equipment.

    Each datagram is one JSON object or a JSON array of PDWs with at least
    ``toa_us`` and ``freq_mhz`` (``pw_us``/``pa_db``/``aoa_deg`` optional).
    Datagrams are buffered by a daemon thread; :meth:`poll` drains the buffer.
    """

    def __init__(self, port: int = 5555, bind: str = "127.0.0.1",
                 buffer: int = 10000):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((bind, port))
        self.sock.settimeout(0.05)
        self.buf: deque = deque(maxlen=buffer)
        self._stop = threading.Event()
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                data, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                obj = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            items = obj if isinstance(obj, list) else [obj]
            with self.lock:
                for it in items:
                    if isinstance(it, dict) and "freq_mhz" in it:
                        self.buf.append(it)

    def poll(self) -> tuple[int, list[dict]]:
        """Drain buffered PDWs; slot index is wall-clock based."""
        with self.lock:
            items = list(self.buf)
            self.buf.clear()
        return int(time.time() * 1e3), items

    def close(self) -> None:
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass


class FileTailSource:
    """Follow a growing JSONL (one JSON PDW per line) or CSV log file."""

    def __init__(self, path: str | Path, freq_col: str = "freq_mhz",
                 toa_col: str = "toa_us"):
        self.path = Path(path)
        self.freq_col, self.toa_col = freq_col, toa_col
        self._pos = 0
        self.pending: deque = deque()
        self._csv_header: list | None = None

    def poll(self) -> tuple[int, list[dict]]:
        if not self.path.exists():
            return 0, []
        out: list[dict] = []
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(self._pos)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{"):
                    try:
                        it = json.loads(line)
                        if "freq_mhz" in it:
                            out.append(it)
                    except json.JSONDecodeError:
                        pass
                else:
                    parts = [x.strip() for x in line.split(",")]
                    if self._csv_header is None:
                        self._csv_header = parts
                    else:
                        row = dict(zip(self._csv_header, parts))
                        try:
                            out.append({self.toa_col: float(row[self.toa_col]),
                                        self.freq_col: float(row[self.freq_col]),
                                        "pa_db": float(row.get("pa_db", -100)),
                                        "aoa_deg": float(row.get("aoa_deg", 0)),
                                        "pw_us": float(row.get("pw_us", 1))})
                        except (KeyError, ValueError):
                            pass
            self._pos = f.tell()
        return int(time.time() * 1e3), out


class LiveSpectrum:
    """Rolling band x slot occupancy picture built from received PDWs."""

    def __init__(self, n_bands: int = 24, fmin_mhz: float = 2000.0,
                 fmax_mhz: float = 18000.0, window: int = 600,
                 slot_us: float = 1000.0):
        self.n_bands = n_bands
        self.fmin, self.fmax = fmin_mhz, fmax_mhz
        self.window = window
        self.slot_us = slot_us
        self.t0 = None
        self.occupancy = np.zeros((n_bands, window), dtype=np.int8)
        self.pdw_log: deque = deque(maxlen=5000)
        self.slot = 0

    def ingest(self, pdws: list[dict]) -> int:
        """Bin PDWs into the occupancy grid; returns newest slot index."""
        if not pdws:
            self.slot += 1
            return self.slot
        toas = [float(p.get("toa_us", 0.0)) for p in pdws]
        if self.t0 is None:
            self.t0 = min(toas)
        for p in pdws:
            b = _band_of(float(p["freq_mhz"]), self.n_bands, self.fmin, self.fmax)
            s = _slot_of(float(p.get("toa_us", 0.0)), self.t0, self.slot_us)
            col = s % self.window
            self.occupancy[b, col] = 1
            self.pdw_log.append({"slot": s, "band": b, **{
                k: p.get(k) for k in ("toa_us", "freq_mhz", "pa_db",
                                      "aoa_deg", "pw_us")}})
        self.slot = max(self.slot, _slot_of(max(toas), self.t0, self.slot_us))
        return self.slot

    def view(self) -> np.ndarray:
        """Occupancy in chronological order (oldest → newest columns)."""
        return np.roll(self.occupancy, self.window - 1 - (self.slot % self.window),
                       axis=1)


class OnlineScanner:
    """Run any scheduler against a :class:`LiveSpectrum`, one slot at a time.

    The scheduler chooses a band; detections are the PDWs present on that band
    in the current slot (real data needs no detection-probability roll - what
    the front-end reports is what happened).  Rewards follow the standard
    scheme so live numbers are comparable with the benchmarks.
    """

    def __init__(self, spectrum: LiveSpectrum, scheduler, n_bands: int):
        self.spec = spectrum
        self.sched = scheduler
        self.n_bands = n_bands
        self.actions: list[int] = []
        self.hits: list[bool] = []
        self.rewards: list[float] = []
        self.detections: list[dict] = []
        self.first_intercept: dict[int, int] = {}

    def step(self, slot_pdws: list[dict]) -> dict:
        """Advance one slot: choose band, score against this slot's PDWs."""
        t = self.spec.slot
        by_band: dict[int, list[dict]] = {}
        for p in slot_pdws:
            b = _band_of(float(p["freq_mhz"]), self.n_bands,
                         self.spec.fmin, self.spec.fmax)
            by_band.setdefault(b, []).append(p)
        band = self.sched.select(t)
        present_pdws = by_band.get(band, [])
        hit = len(present_pdws) > 0
        r = -0.05
        if hit:
            r = 0.15
            for p in present_pdws:
                key = (round(float(p.get("freq_mhz", 0)), 1),
                       round(float(p.get("aoa_deg", 0)) / 15.0))
                if key not in self.first_intercept:
                    self.first_intercept[key] = t
                    r = 1.0
        self.actions.append(band)
        self.hits.append(hit)
        self.rewards.append(r)
        self.sched.update(t, band, _LiveResult(band, t, hit, present_pdws), r)
        self.detections.extend(present_pdws[:8])
        return {"slot": t, "band": band, "hit": hit, "reward": r,
                "n_pdws": len(present_pdws)}

    def stats(self) -> dict:
        n = max(1, len(self.actions))
        return {"slots": len(self.actions),
                "avg_reward": float(np.mean(self.rewards)) if self.rewards else 0.0,
                "hit_rate": float(np.mean(self.hits)) if self.hits else 0.0,
                "unique_streams": len(self.first_intercept),
                "detections": int(np.sum(self.hits))}


class _LiveResult:
    """Minimal dwell-result shim satisfying the scheduler update interface."""

    def __init__(self, band: int, t: int, hit: bool, pdws: list[dict]):
        self.band = band
        self.t = t
        self.hit = hit
        self.false_alarm = False
        self.truth_present = hit
        self.detections = tuple(
            (float(p.get("pa_db", 10.0)), float(p.get("aoa_deg", 0.0)))
            for p in pdws)
        self.snr_db = self.detections[0][0] if self.detections else -np.inf
        self.pdws = tuple(pdws)
