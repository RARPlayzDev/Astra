"""Command-centre API endpoints (auto-skipped when fastapi is unavailable)."""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

try:
    from fastapi.testclient import TestClient
    from server.api import app
    client = TestClient(app)
    _HAS_API = True
except ImportError:
    client = None
    _HAS_API = False


def _skip():
    print("SKIP (fastapi/httpx not installed)")


def _needs_results() -> bool:
    return (pathlib.Path("results") / "suite_results.json").exists()


def test_summary_shape():
    if not _HAS_API:
        return _skip()
    r = client.get("/api/summary")
    assert r.status_code == 200
    data = r.json()
    assert "monte_carlo" in data and "mission_effectiveness" in data
    if _needs_results():
        me = data["mission_effectiveness"]
        assert me["ranking"][0] == "smart-scan"
        assert me["scores"]["smart-scan"]["mission_capable"] is True


def test_figures_endpoint():
    if not _HAS_API:
        return _skip()
    figs = client.get("/api/figures").json()["figures"]
    assert isinstance(figs, list)
    if figs:
        r = client.get(f"/api/figures/{figs[0]}")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
    assert client.get("/api/figures/nope.png").status_code == 404


def test_live_status_and_start_stop():
    if not _HAS_API:
        return _skip()
    st = client.get("/api/live/status").json()
    for key in ("running", "slot", "T", "generation", "kpis"):
        assert key in st
    r = client.post("/api/live/start?n_bands=16&T=200&speed=2000")
    assert r.status_code == 200 and r.json()["started"] is True
    try:
        deadline = time.time() + 20
        slot, kpis = 0, {}
        while time.time() < deadline:
            st = client.get("/api/live/status").json()
            slot = st["slot"]
            kpis = st["kpis"]
            if slot >= 30 or not st["running"]:
                break
            time.sleep(0.2)
        assert slot >= 20, "arena did not advance slots"
        if kpis:
            assert kpis["smart-scan"]["slots"] == kpis["openloop-sequential"]["slots"]
    finally:
        client.post("/api/live/stop")


def test_spa_root_served_when_built():
    if not _HAS_API:
        return _skip()
    if (pathlib.Path("frontend") / "dist" / "index.html").exists():
        r = client.get("/")
        assert r.status_code == 200
        assert b"root" in r.content


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
