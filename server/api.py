"""ASTRA - Adaptive Spectrum Threat Recognition & Analysis: local API service.

Serves the desktop-style web application, benchmark results, figures, the
built-in user manual, sensor-source management (UDP / log-file / simulated
feeds) and a diagnostics self-test suite.

Run standalone:      python -m uvicorn server.api:app --port 8000
Desktop application: python desktop.py            (or ASTRA.exe once built)
"""
from __future__ import annotations

import json
import socket
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .livesim import LiveArena
from .sources import SourceHub

APP_NAME = "ASTRA"
APP_LONG = "Adaptive Spectrum Threat Recognition & Analysis"
APP_VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "suite_results.json"
FIGDIR = ROOT / "figures"
SCENARIOS = ROOT / "scenarios"
MODELS = ROOT / "models"
DOCS = ROOT / "docs" / "ASTRA_Software_Documentation.md"
DIST = ROOT / "frontend" / "dist"

app = FastAPI(title=f"{APP_NAME} - {APP_LONG}", version=APP_VERSION,
              docs_url="/api-docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

arena = LiveArena()
hub = SourceHub()
ARENA_SCHEDULERS = ("smart-scan", "openloop-sequential")


def _load_results() -> dict:
    if not RESULTS.exists():
        raise HTTPException(404, "results/suite_results.json not found - "
                                 "run `python -m ewsmart.experiments --suite full`")
    with open(RESULTS, "r", encoding="utf-8") as f:
        return json.load(f)


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (np.isnan(f) or np.isinf(f)) else f
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    return o


@app.get("/api/meta")
def meta() -> dict:
    dist_ok = (DIST / "index.html").exists()
    return {"app": APP_NAME, "long": APP_LONG, "version": APP_VERSION,
            "manual_available": DOCS.exists(), "frontend_built": dist_ok}


@app.get("/api/summary")
def summary() -> dict:
    data = _load_results()
    mc = data.get("monte_carlo", {})
    means = {n: {k: v.get("mean") for k, v in d.items()} for n, d in mc.items()}
    return {
        "monte_carlo_means": means,
        "monte_carlo": mc,
        "mission_effectiveness": data.get("mission_effectiveness"),
        "significance": data.get("significance", []),
        "significance_gated_mes": data.get("significance_gated_mes", []),
        "learning": data.get("learning", {}),
        "identification": data.get("identification", {}),
        "ablation": data.get("ablation", {}),
        "multireceiver": data.get("multireceiver", {}),
        "geolocation": data.get("geolocation", {}),
        "roc": data.get("roc", {}),
    }


@app.get("/api/figures")
def figures() -> dict:
    return {"figures": sorted(p.name for p in FIGDIR.glob("*.png"))}


@app.get("/api/figures/{name}")
def figure(name: str):
    path = FIGDIR / name
    if not path.exists() or path.suffix != ".png":
        raise HTTPException(404, f"figure '{name}' not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/scenarios")
def scenarios() -> dict:
    out = []
    for p in sorted(SCENARIOS.glob("*.json")):
        try:
            out.append({"name": p.stem,
                        "config": json.loads(p.read_text(encoding="utf-8"))})
        except json.JSONDecodeError:
            continue
    return {"scenarios": out}


@app.get("/api/models")
def models() -> dict:
    out = []
    for p in sorted(MODELS.glob("*.npz")):
        try:
            with np.load(p, allow_pickle=False) as z:
                meta = json.loads(str(z["meta"]))
            out.append({"file": p.name, "class": meta.get("class"),
                        "n_bands": meta.get("n_bands"),
                        "format": meta.get("format"), "ok": True})
        except Exception as exc:
            out.append({"file": p.name, "ok": False, "error": str(exc)})
    return {"models": out}


@app.post("/api/models/train")
def models_train(body: dict) -> dict:
    """Quick-train a persistable policy and save it to models/."""
    policy = str(body.get("policy", "")).lower()
    n_bands = int(body.get("n_bands", 12))
    T = int(body.get("T", 600))
    episodes = max(1, min(30, int(body.get("episodes", 5))))
    if policy not in ("smart-scan", "bandit-ucb", "rl-linear-q"):
        raise HTTPException(422, "policy must be smart-scan | bandit-ucb | rl-linear-q")
    from .livesim import make_live_scheduler
    from ewsmart.persistence import save_scheduler
    from ewsmart.environment import RFEnvironment
    from ewsmart.runner import run_episode
    s = make_live_scheduler(policy, n_bands, seed=0)
    s.reset(horizon=T)
    curve = []
    for ep in range(episodes):
        env = RFEnvironment(n_bands=n_bands, T=T, seed=100 + ep)
        tr = run_episode(env, s, seed=ep)
        curve.append(round(float(np.sum(tr.rewards)), 1))
        if hasattr(s, "end_episode"):
            s.end_episode()
    out = MODELS / f"{policy}.npz"
    try:
        save_scheduler(out, s)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"saved": str(out.name), "policy": policy,
            "episodes": episodes, "reward_curve": curve}


@app.post("/api/dataset/calibrate")
def dataset_calibrate(body: dict) -> dict:
    """Calibrate a battlefield from the referenced PDW datasets (offline-safe)."""
    n_rows = max(200, min(5000, int(body.get("max_rows", 1500))))
    seed = int(body.get("seed", 0))
    from ewsmart.dataset import environment_from_dataset
    env, summary = environment_from_dataset(n_bands=int(body.get("n_bands", 20)),
                                            T=int(body.get("T", 1200)),
                                            seed=seed, max_rows=n_rows)
    return {"summary": _jsonable(summary),
            "suggested": {"n_bands": env.cfg.n_bands, "T": env.cfg.T}}


# ------------------------------------------------------------------ shutdown


@app.post("/api/live/start")
def live_start(n_bands: int = 24, T: int = 2400, speed: int = 400,
               scenario: str | None = None,
               sched_a: str = "smart-scan",
               sched_b: str = "openloop-sequential",
               team_size: int = 1, sens_offset: float = 6.0,
               use_saved: bool = False) -> dict:
    """Start (or restart) the paired live arena with full configuration."""
    global arena
    if scenario:
        cfg_path = SCENARIOS / f"{Path(scenario).stem}.json"
        if not cfg_path.exists():
            raise HTTPException(404, f"scenario '{scenario}' not found")
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            n_bands = int(cfg.get("n_bands", n_bands))
            T = int(cfg.get("T", T))
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(422, "scenario file is not valid JSON")
    try:
        arena.stop()
        arena = LiveArena(n_bands=n_bands, T=T, speed=speed,
                          sched_a=sched_a, sched_b=sched_b,
                          team_size=team_size, sens_offset=sens_offset,
                          use_saved=use_saved)
        arena.start()
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"started": True, "schedulers": [sched_a, sched_b],
            "n_bands": n_bands, "T": T, "team_size": arena.team_size,
            "sens_offset": sens_offset, "use_saved": use_saved}


@app.post("/api/live/stop")
def live_stop() -> dict:
    arena.stop()
    return {"stopped": True}


@app.get("/api/live/status")
def live_status() -> dict:
    return arena.snapshot()


@app.get("/api/live/stream")
def live_stream():
    def gen():
        seen_frames = seen_done = idle = 0
        while True:
            frames = list(arena.frames)
            dones = list(arena.episode_done)
            made_progress = False
            for fr in frames[seen_frames:]:
                yield f"data: {json.dumps(_jsonable(fr))}\n\n"
                made_progress = True
            seen_frames = len(frames)
            for dn in dones[seen_done:]:
                yield f"data: {json.dumps(_jsonable(dn))}\n\n"
                made_progress = True
            seen_done = len(dones)
            if not made_progress:
                idle += 1
                if idle > 600:
                    yield ": keepalive\n\n"
                    idle = 0
                time.sleep(0.1)
            else:
                idle = 0

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


# -------------------------------------------------------- geolocation
@app.get("/api/geolocation")
def geolocation(k_rx: int = 3, seed: int = 42) -> dict:
    """Run AOA triangulation on current arena emitters."""
    import numpy as np
    from ewsmart.geo import simulate_bearings, triangulate, cep_stats
    rng = np.random.default_rng(seed)
    runners = arena.runners
    if not runners:
        raise HTTPException(404, "No active mission — start one first")
    env = runners[0].env
    receivers = [(0.0, 0.0)]
    for i in range(1, k_rx):
        a = 2 * np.pi * i / k_rx
        receivers.append((50.0 * np.cos(a), 50.0 * np.sin(a)))
    true_pts = [(e.x_km, e.y_km) for e in env.emitters]
    est_pts = []
    for e in env.emitters:
        lines = simulate_bearings((e.x_km, e.y_km), receivers, 2.0, rng)
        x, y, res = triangulate(lines)
        est_pts.append({"x": x, "y": y, "residual_km": res})
    errors = [float(np.hypot(p["x"] - t[0], p["y"] - t[1]))
              for p, t in zip(est_pts, true_pts)]
    cs = cep_stats(errors)
    return {
        "receivers": receivers,
        "true_positions": true_pts,
        "estimated_positions": est_pts,
        "errors": errors,
        "cep": cs,
        "scene_km": max(50.0, env.scene_radius_km),
    }


# -------------------------------------------------------- identification
@app.get("/api/identification")
def identification() -> dict:
    """Run emitter identification on current streams."""
    runners = arena.runners
    if not runners:
        raise HTTPException(404, "No active mission — start one first")
    r = runners[0]
    rows = r.identification_rows()
    return {"rows": rows, "n_streams": len(r.streams)}


# ------------------------------------------------------------- sources hub
@app.get("/api/sources")
def sources_list() -> dict:
    return {"sources": hub.list_sources()}


@app.post("/api/sources")
def sources_add(body: dict) -> dict:
    stype = str(body.get("type", "")).lower()
    try:
        sid = hub.add(stype, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except OSError as exc:
        raise HTTPException(409, str(exc))
    return {"id": sid}


@app.delete("/api/sources/{sid}")
def sources_remove(sid: str) -> dict:
    if not hub.remove(sid):
        raise HTTPException(404, f"source '{sid}' not found")
    return {"removed": True}


# -------------------------------------------------------------- diagnostics
def _diag_udp_loopback() -> tuple[bool, str]:
    try:
        s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s1.bind(("127.0.0.1", 0))
        port = s1.getsockname()[1]
        s1.settimeout(2.0)
        s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s2.sendto(json.dumps({"probe": True}).encode(), ("127.0.0.1", port))
        s1.recvfrom(1024)
        s1.close()
        s2.close()
        return True, f"loopback on :{port}"
    except Exception as exc:
        return False, str(exc)


@app.get("/api/diagnostics")
def diagnostics() -> dict:
    checks = []

    def add(name, fn):
        try:
            ok, detail = fn()
        except Exception as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    def c_imports():
        from ewsmart.environment import RFEnvironment  # noqa: F401
        from ewsmart.schedulers import SmartScanScheduler  # noqa: F401
        return True, "core modules import cleanly"

    def c_env():
        from ewsmart.environment import RFEnvironment
        env = RFEnvironment(n_bands=8, T=50, seed=1)
        rx = __import__("ewsmart.receiver", fromlist=["ESReceiver"]).ESReceiver(env, seed=2)
        res = rx.dwell(0, 0)
        return res.band == 0, f"environment+receiver boot ok ({env.n_bands} bands)"

    def c_results():
        d = _load_results()
        return "monte_carlo" in d, f"{len(d)} result sections"

    def c_figures():
        n = len(list(FIGDIR.glob("*.png")))
        return n > 0, f"{n} figures on disk"

    def c_models():
        items = [p for p in MODELS.glob("*.npz")]
        if not items:
            return False, "no trained model artifacts found"
        bad = []
        for p in items:
            try:
                with np.load(p, allow_pickle=False) as z:
                    json.loads(str(z["meta"]))
            except Exception as exc:
                bad.append(f"{p.name}: {exc}")
        return not bad, (f"{len(items)} artifacts valid" if not bad
                         else "; ".join(bad))

    def c_frontend():
        return (DIST / "index.html").exists(), "frontend bundle present"

    def c_manual():
        return DOCS.exists(), str(DOCS.name)

    add("Core modules import", c_imports)
    add("Simulation environment boots", c_env)
    add("Benchmark results present", c_results)
    add("Figures generated", c_figures)
    add("Model artifacts valid", c_models)
    add("Frontend bundle", c_frontend)
    add("User manual available", c_manual)
    add("UDP loopback", _diag_udp_loopback)
    failed = [c["name"] for c in checks if not c["ok"]]
    return {"checks": checks, "passed": len(checks) - len(failed),
            "total": len(checks), "all_ok": not failed}


# ------------------------------------------------------------------- manual
_MANUAL_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<title>ASTRA - Software Documentation</title>
<style>
 body {{ font-family: Georgia,'Times New Roman',serif; max-width: 900px;
        margin: 0 auto; padding: 48px 32px; color:#1c1c1c; line-height:1.65;
        background:#fdfdfb; }}
 h1,h2,h3 {{ font-family:'Segoe UI',sans-serif; color:#12354f; line-height:1.3; }}
 h1 {{ border-bottom:3px solid #12354f; padding-bottom:8px; }}
 h2 {{ border-bottom:1px solid #c9cdc9; padding-bottom:5px; margin-top:40px; }}
 code, pre {{ font-family:Consolas,monospace; font-size:.92em; background:#f0f1ee;
             border-radius:3px; }}
 pre {{ padding:12px 14px; overflow-x:auto; border:1px solid #dfe2dc; }}
 table {{ border-collapse:collapse; width:100%; margin:14px 0; font-size:.95em; }}
 th,td {{ border:1px solid #cfd4cd; padding:6px 10px; text-align:left; }}
 th {{ background:#eef1ec; }}
 blockquote {{ border-left:3px solid #12354f; margin:14px 0; padding:4px 18px;
               background:#f4f6f2; }}
 @media print {{ body {{ padding:0 }} }}
</style></head><body>{body}</body></html>"""


@app.get("/manual", response_class=HTMLResponse)
def manual():
    if not DOCS.exists():
        return HTMLResponse("<h1>Manual not found</h1>", status_code=404)
    text = DOCS.read_text(encoding="utf-8")
    try:
        import markdown
        html_body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    except ImportError:
        html_body = f"<pre>{text}</pre>"
    return HTMLResponse(_MANUAL_TEMPLATE.format(body=html_body))


@app.post("/api/shutdown")
def shutdown() -> dict:
    cb = getattr(app.state, "shutdown_cb", None)
    if cb is None:
        return {"shutdown": "noop"}
    cb()
    return {"shutdown": "requested"}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="spa")
else:  # pragma: no cover
    @app.get("/")
    def root() -> dict:
        return Response(content=f"{APP_NAME} API is running. Build the "
                                "frontend or open /api-docs.",
                        media_type="text/plain")

