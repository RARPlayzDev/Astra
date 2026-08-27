"""Sensor source hub: manage live PDW feeds feeding ASTRA.

Three source types are supported, mirroring how real equipment integrates:

* ``udp``  - JSON pulse-descriptor words arriving as datagrams (the standard
  integration path for SDR sweeps and radar processors; see
  ``tools/sdr_bridge.py`` and ``tools/pdw_generator.py``).
* ``file`` - a growing JSONL/CSV log written by third-party equipment.
* ``sim``  - an internal synthetic emitter scene (no hardware required).

Each source runs its own polling thread and reports cumulative PDW count,
instantaneous rate and health.  The hub is intentionally independent from the
paired mission arena: sources represent *inputs*, the arena is a *demonstration*.
"""
from __future__ import annotations

import threading
import time
import uuid

from ewsmart.live import FileTailSource, LiveSpectrum, SimulatedLiveSource, UDPSource


class _Source:
    def __init__(self, sid: str, stype: str, params: dict):
        self.id = sid
        self.type = stype
        self.params = params
        self.pdw_total = 0
        self.rate = 0.0
        self.running = False
        self.error: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.impl = None
        self.spectrum: LiveSpectrum | None = None
        self.lock = threading.Lock()

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if isinstance(self.impl, UDPSource):
            try:
                self.impl.close()
            except OSError:
                pass

    # ------------------------------------------------------------------
    def _open(self):
        t = self.type
        if t == "udp":
            self.impl = UDPSource(port=int(self.params["port"]),
                                  bind=str(self.params.get("bind", "127.0.0.1")))
            self.running = True
            return None                      # UDPSource polls in its own thread;
        if t == "file":                      # our loop just drains counters
            path = str(self.params["path"])
            self.impl = FileTailSource(path)
            self.running = True
            return None
        if t == "sim":
            from ewsmart.environment import RFEnvironment
            env = RFEnvironment(n_bands=int(self.params.get("n_bands", 24)),
                                T=int(self.params.get("T", 3000)),
                                seed=int(self.params.get("seed", 7)))
            self.impl = SimulatedLiveSource(env, seed=3)
            self.spectrum = LiveSpectrum(n_bands=env.n_bands)
            self.running = True
            return None
        raise ValueError(f"unknown source type '{t}'")

    def _loop(self):
        try:
            self._open()
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.running = False
            return
        last_total, last_t = 0, time.monotonic()
        while not self._stop.is_set():
            try:
                _, pdws = self.impl.poll()
                with self.lock:
                    self.pdw_total += len(pdws)
                now = time.monotonic()
                dt = max(1e-3, now - last_t)
                inst = (self.pdw_total - last_total) / dt
                with self.lock:
                    self.rate = 0.6 * self.rate + 0.4 * inst
                    if self.pdw_total < last_total:   # counter reset safety
                        self.rate = inst
                last_total, last_t = self.pdw_total, now
                if self.type != "udp":
                    time.sleep(0.2)
                else:
                    time.sleep(0.1)
            except Exception as exc:
                self.error = f"{type(exc).__name__}: {exc}"
                self.running = False
                return

    def snapshot(self) -> dict:
        with self.lock:
            return {"id": self.id, "type": self.type, "params": self.params,
                    "pdw_total": self.pdw_total,
                    "rate_per_s": round(self.rate, 1),
                    "running": self.running, "error": self.error}


class SourceHub:
    def __init__(self):
        self._sources: dict[str, _Source] = {}
        self._lock = threading.Lock()

    def add(self, stype: str, params: dict) -> str:
        stype = stype.lower().strip()
        if stype == "udp":
            port = int(params.get("port", 0))
            if not (1024 <= port <= 65535):
                raise ValueError("port must be in [1024, 65535]")
            params = {"port": port, "bind": str(params.get("bind", "127.0.0.1"))}
        elif stype == "file":
            from pathlib import Path
            p = Path(str(params.get("path", "")))
            if not p.exists():
                raise ValueError(f"log file not found: {p}")
            params = {"path": str(p)}
        elif stype == "sim":
            params = {"n_bands": int(params.get("n_bands", 24)),
                      "T": int(params.get("T", 3000)),
                      "seed": int(params.get("seed", 7))}
        else:
            raise ValueError("type must be one of: udp, file, sim")
        sid = uuid.uuid4().hex[:10]
        src = _Source(sid, stype, params)
        src.start()
        with self._lock:
            self._sources[sid] = src
        return sid

    def remove(self, sid: str) -> bool:
        with self._lock:
            src = self._sources.pop(sid, None)
        if src is None:
            return False
        src.stop()
        return True

    def list_sources(self) -> list[dict]:
        with self._lock:
            items = list(self._sources.values())
        out = []
        for s in items:
            snap = s.snapshot()
            if not s.running and s.error is None and not s._stop.is_set():
                continue                       # still starting up; skip once
            out.append(snap)
        return out

    def stop_all(self):
        with self._lock:
            items = list(self._sources.values())
            self._sources.clear()
        for s in items:
            s.stop()
