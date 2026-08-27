"""Reference bridge: push real SDR / radar-receiver PDWs into the dashboard.

This script is the integration point for **real hardware**. Run it next to
whatever produces per-pulse measurements, and it forwards standard JSON PDWs
to the dashboard's Live Radar page over UDP.

Supported input modes
---------------------
1. ``--mode udp``   - listen on ``--in-port`` for any upstream JSON PDWs and
                      re-forward them (pure relay; e.g. GNU Radio companion
                      block, radar processor, or another host).
2. ``--mode csv``   - tail a ``rtl_power``-style CSV sweep file (``--csv``) or
                      any CSV with columns ``toa_us,freq_mhz,pa_db,aoa_deg,pw_us``
                      and forward new rows as they appear.

PDW format forwarded (JSON, one per datagram)::

    {"toa_us": 123456.7, "freq_mhz": 9450.2, "pw_us": 1.3,
     "pa_db": 14.2, "aoa_deg": 87.0}

Hardware notes
--------------
* RTL-SDR / HackRF: run a sweep-to-CSV tool (e.g. ``rtl_power`` or
  ``soapy_power``), then use ``--mode csv``.  Convert the sweep's dB/Hz units
  with ``--freq-scale`` / ``--offset-us`` if needed.
* A radar warning receiver or ESM processor: emit the JSON above on UDP and
  use ``--mode udp`` (or point the dashboard straight at it).
* Anything that can write a growing JSONL file also works directly via the
  dashboard's FileTail source - no bridge needed.

Examples::

    python tools/sdr_bridge.py --mode udp --in-port 5000 --out-port 5555
    python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555
"""
from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path


def udp_relay(in_port: int, out_port: int, out_host: str) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", in_port))
    print(f"relaying UDP {in_port} -> {out_host}:{out_port} (Ctrl-C to stop)")
    while True:
        data, _ = sock.recvfrom(65535)
        sock.sendto(data, (out_host, out_port))


def csv_tail(csv_path: str, out_port: int, out_host: str,
             poll_s: float = 0.5) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    path = Path(csv_path)
    pos = 0
    header = None
    print(f"tailing {path} -> {out_host}:{out_port} (Ctrl-C to stop)")
    while True:
        if path.exists():
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(pos)
                for line in f:
                    parts = [x.strip() for x in line.strip().split(",")]
                    if not any(parts):
                        continue
                    if header is None:
                        header = parts
                        continue
                    row = dict(zip(header, parts))
                    try:
                        pdw = {"toa_us": float(row.get("toa_us",
                                                       time.time() * 1e6)),
                               "freq_mhz": float(row["freq_mhz"]) / 1e6,
                               "pw_us": float(row.get("pw_us", 1.0)),
                               "pa_db": float(row.get("pa_db", -100.0)),
                               "aoa_deg": float(row.get("aoa_deg", 0.0))}
                    except (KeyError, ValueError):
                        continue
                    sock.sendto(json.dumps(pdw).encode(), (out_host, out_port))
                pos = f.tell()
        time.sleep(poll_s)


def main() -> None:
    ap = argparse.ArgumentParser(description="EW SmartScan live PDW bridge")
    ap.add_argument("--mode", choices=["udp", "csv"], default="udp")
    ap.add_argument("--in-port", type=int, default=5000)
    ap.add_argument("--out-port", type=int, default=5555)
    ap.add_argument("--out-host", default="127.0.0.1")
    ap.add_argument("--csv", default="sweep.csv")
    args = ap.parse_args()
    if args.mode == "udp":
        udp_relay(args.in_port, args.out_port, args.out_host)
    else:
        csv_tail(args.csv, args.out_port, args.out_host)


if __name__ == "__main__":
    main()
