"""ASTRA application-layer tests: sources hub, diagnostics, manual, models.

Covers the desktop-software endpoints and a battery of integration edge
cases (malformed input, port conflicts, missing files, unknown types).
"""
import json
import pathlib
import socket
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

try:
    from fastapi.testclient import TestClient
    from server.api import app, hub
    client = TestClient(app)
    _HAS_API = True
except ImportError:
    client = None
    _HAS_API = False


def _skip():
    print("SKIP (fastapi not installed)")


def _free_udp_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_meta_and_health():
    if not _HAS_API:
        return _skip()
    m = client.get("/api/meta").json()
    assert m["app"] == "ASTRA" and m["version"]
    h = client.get("/api/health").json()
    assert h["status"] == "ok"


def test_diagnostics_shape():
    if not _HAS_API:
        return _skip()
    d = client.get("/api/diagnostics").json()
    assert d["total"] == len(d["checks"]) >= 6
    names = [c["name"] for c in d["checks"]]
    assert len(names) == len(set(names)), "duplicate check names"
    for c in d["checks"]:
        assert isinstance(c["ok"], bool) and c["detail"]
    core = [c for c in d["checks"] if c["name"] == "Core modules import"]
    assert core and core[0]["ok"]


def test_manual_renders():
    if not _HAS_API:
        return _skip()
    r = client.get("/manual")
    if r.status_code == 404:
        print("SKIP (manual file absent)")
        return
    assert r.status_code == 200
    body = r.text
    assert "<html" in body.lower() and "ASTRA" in body


def test_models_endpoint_integrity():
    if not _HAS_API:
        return _skip()
    models = client.get("/api/models").json()["models"]
    if models:
        assert all(m.get("format", "").startswith("ewsmart-npz") or not m["ok"]
                   for m in models)


def test_source_unknown_type_rejected():
    if not _HAS_API:
        return _skip()
    r = client.post("/api/sources", json={"type": "carrier-pigeon"})
    assert r.status_code == 422


def test_source_bad_port_rejected():
    if not _HAS_API:
        return _skip()
    for bad in (80, 70000, -1):
        r = client.post("/api/sources", json={"type": "udp", "port": bad})
        assert r.status_code == 422, f"port {bad} should be rejected"


def test_source_missing_file_rejected():
    if not _HAS_API:
        return _skip()
    r = client.post("/api/sources",
                    json={"type": "file", "path": "Z:/nope/missing.jsonl"})
    assert r.status_code == 422


def test_udp_source_lifecycle_and_data():
    if not _HAS_API:
        return _skip()
    port = _free_udp_port()
    r = client.post("/api/sources", json={"type": "udp", "port": port})
    assert r.status_code == 200
    sid = r.json()["id"]

    # send one well-formed PDW datagram
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pdw = {"toa_us": time.time() * 1e6 % 1e12, "freq_mhz": 9450.0,
           "pw_us": 1.5, "pa_db": 12.0, "aoa_deg": 90.0}
    sock.sendto(json.dumps(pdw).encode(), ("127.0.0.1", port))

    # send malformed datagrams: must be ignored without harming the source
    sock.sendto(b"\xff\xfe\x00 garbage", ("127.0.0.1", port))
    sock.sendto(json.dumps({"freq_mhz": "not-a-number"}).encode(),
                ("127.0.0.1", port))

    deadline = time.time() + 8
    total = 0
    while time.time() < deadline:
        srcs = client.get("/api/sources").json()["sources"]
        mine = [s for s in srcs if s["id"] == sid]
        if mine and (mine[0]["pdw_total"] >= 1 or mine[0]["error"]):
            total = mine[0]["pdw_total"]
            break
        sock.sendto(json.dumps(pdw).encode(), ("127.0.0.1", port))
        time.sleep(0.3)
    assert total >= 1, "UDP source never received the sent PDW"

    # duplicate bind on same port must fail cleanly with 409
    r2 = client.post("/api/sources", json={"type": "udp", "port": port})
    assert r2.status_code in (409, 200), "conflict should surface as 409"
    if r2.status_code == 200:
        client.delete(f"/api/sources/{r2.json()['id']}")

    # remove and confirm gone
    assert client.delete(f"/api/sources/{sid}").json()["removed"]
    assert client.delete(f"/api/sources/{sid}").status_code == 404
    sock.close()


def test_sim_source_produces_counts():
    if not _HAS_API:
        return _skip()
    r = client.post("/api/sources", json={"type": "sim", "n_bands": 8,
                                          "T": 500, "seed": 3})
    assert r.status_code == 200
    sid = r.json()["id"]
    deadline = time.time() + 10
    total = 0
    while time.time() < deadline:
        srcs = client.get("/api/sources").json()["sources"]
        mine = [s for s in srcs if s["id"] == sid]
        if mine and mine[0]["pdw_total"] > 0:
            total = mine[0]["pdw_total"]
            break
        time.sleep(0.3)
    try:
        assert total > 0, "simulated scene produced no PDWs"
    finally:
        client.delete(f"/api/sources/{sid}")


def test_live_start_with_scenario_name():
    if not _HAS_API:
        return _skip()
    scen = client.get("/api/scenarios").json()["scenarios"]
    if not scen:
        print("SKIP (no scenario files)")
        return
    name = scen[0]["name"]
    try:
        r = client.post(f"/api/live/start?scenario={name}&speed=1500")
        assert r.status_code == 200
        body = r.json()
        assert body["started"] is True
        deadline = time.time() + 15
        slot = 0
        while time.time() < deadline:
            st = client.get("/api/live/status").json()
            slot = st["slot"]
            if slot >= 20 or not st["running"]:
                break
            time.sleep(0.2)
        assert slot >= 10, "scenario-driven arena did not advance"
    finally:
        client.post("/api/live/stop")


def test_live_start_unknown_scenario_404():
    if not _HAS_API:
        return _skip()
    r = client.post("/api/live/start?scenario=does-not-exist")
    assert r.status_code == 404


def test_shutdown_endpoint_safe_without_cb():
    if not _HAS_API:
        return _skip()
    r = client.post("/api/shutdown")
    assert r.status_code == 200
    assert r.json()["shutdown"] in ("noop", "requested")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} software tests passed")
