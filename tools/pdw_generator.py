"""Synthetic PDW radar feed for testing ASTRA without hardware.

Streams pulse-descriptor words as JSON datagrams over UDP, emulating a small
heterogeneous emitter population (stationary, frequency-agile and periodic
scanning radars). Use it to verify end-to-end integration:

    python tools/pdw_generator.py --port 5555 --rate 400
    # then attach a UDP source on the same port in ASTRA -> Data & Sources
"""
from __future__ import annotations

import argparse
import json
import socket
import time

import numpy as np


def build_scene(seed: int):
    rng = np.random.default_rng(seed)
    emitters = []

    def add(kind, freq, **kw):
        e = {"kind": kind, "freq": float(freq), "pri_us": 200.0,
             "dwell_left": 0, "phase": float(rng.uniform(0, 360)), **kw}
        emitters.append(e)

    add("stationary", rng.uniform(2400, 4000), pa=14.0)
    add("stationary", rng.uniform(9000, 10000), pa=11.0)
    add("agile", rng.uniform(5000, 7000), hop=[float(f) for f in
        rng.uniform(5000, 16000, 4)], dwell_left=int(rng.integers(10, 60)))
    add("periodic", rng.uniform(2800, 3300), period_s=1.2, on_ms=40.0)   # SNOW DRIFT-ish
    add("periodic", rng.uniform(8800, 9800), period_s=2.0, on_ms=25.0)   # X-band scan
    return rng, emitters


def main() -> None:
    ap = argparse.ArgumentParser(description="Synthetic PDW feed over UDP")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5555)
    ap.add_argument("--rate", type=int, default=400, help="PDWs per second")
    ap.add_argument("--duration", type=float, default=0.0, help="seconds (0 = forever)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng, emitters = build_scene(args.seed)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    t0 = time.monotonic()
    sent, next_report = 0, t0 + 2.0
    print(f"streaming ~{args.rate} PDW/s to {args.host}:{args.port} "
          f"(Ctrl+C to stop)")

    try:
        while True:
            now = time.monotonic() - t0
            batch = []
            for _ in range(max(1, args.rate // 20)):
                e = emitters[int(rng.integers(len(emitters)))]
                if e["kind"] == "agile":
                    if e["dwell_left"] <= 0:
                        e["freq"] = float(rng.choice(e["hop"]))
                        e["dwell_left"] = int(rng.integers(10, 60))
                    e["dwell_left"] -= 1
                elif e["kind"] == "periodic":
                    cyc = (now * 1000.0) % (e["period_s"] * 1000.0)
                    if cyc > e["on_ms"]:
                        continue                       # beam pointed away
                phase_hit = (now * 1e6) % e["pri_us"] < (args.rate and 50)
                if not phase_hit and rng.random() > 0.35:
                    continue
                batch.append({
                    "toa_us": round((t0 + now) * 1e6 % 1e12, 1),
                    "freq_mhz": round(e["freq"] + float(rng.normal(0, 1.5)), 2),
                    "pw_us": round(float(rng.uniform(0.5, 8.0)), 2),
                    "pa_db": round(e.get("pa", 12.0) + float(rng.normal(0, 1.0)), 1),
                    "aoa_deg": round((e["phase"] + now * 12.0) % 360.0, 1),
                })
            if batch:
                sock.sendto(json.dumps(batch).encode("utf-8"),
                            (args.host, args.port))
                sent += len(batch)
            if time.monotonic() > next_report:
                print(f"  sent {sent} PDWs ({sent / (time.monotonic() - t0):.0f}/s)")
                next_report = time.monotonic() + 2.0
            if args.duration and (time.monotonic() - t0) >= args.duration:
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"done - {sent} PDWs sent")


if __name__ == "__main__":
    main()
