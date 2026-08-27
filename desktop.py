"""ASTRA desktop application entry point.

Owns its native window via pywebview (Edge WebView2 runtime, preinstalled on
Windows 10/11): no address bar, no tabs, no separate browser processes.
Closing the window shuts the local service down cleanly - exactly like an
installed desktop application.

Fallbacks, in order, if the native window cannot be created:
  1. Edge/Chrome "--app" mode window
  2. System default browser

Build the distributable:
    powershell -File tools/build_exe.ps1     ->  dist/ASTRA/ASTRA.exe
"""
from __future__ import annotations

import http.client
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

APP_NAME = "ASTRA"
APP_LONG = "Adaptive Spectrum Threat Recognition & Analysis"


def _bootstrap_paths():
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "."))
        os.chdir(base)
        if str(base) not in sys.path:
            sys.path.insert(0, str(base))
        # Windowed builds have no stdout/stderr; logging would crash on None.
        if sys.stdout is None or sys.stderr is None:
            log_path = Path(os.environ.get("TEMP", ".")) / "astra_service.log"
            try:
                sys.stdout = sys.stdout or open(log_path, "a", buffering=1)
                sys.stderr = sys.stderr or open(log_path, "a", buffering=1)
            except OSError:
                import io
                sys.stdout = sys.stdout or io.StringIO()
                sys.stderr = sys.stderr or io.StringIO()
    else:
        os.chdir(ROOT)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_healthy(port: int, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.5)
            conn.request("GET", "/api/health")
            ok = conn.getresponse().status == 200
            conn.close()
            if ok:
                return True
        except OSError:
            time.sleep(0.25)
    return False


class _Server:
    def __init__(self, port: int):
        import uvicorn
        self.port = port
        self.config = uvicorn.Config("server.api:app", host="127.0.0.1",
                                     port=port, log_level="warning",
                                     access_log=False)
        self.server = uvicorn.Server(self.config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self):
        self.thread.start()

    def shutdown(self):
        self.server.should_exit = True


class _JsBridge:
    """Functions callable from the UI as window.pywebview.api.<name>()."""

    def __init__(self, server: "_Server"):
        self._server = server
        self.base_url = f"http://127.0.0.1:{server.port}"

    def exit_app(self):
        """File -> Exit: stop service, close window, process exits."""
        def _close():
            self._server.shutdown()
            try:
                from server.api import hub
                hub.stop_all()
            except Exception:
                pass
            for w in list(webview.windows):
                try:
                    w.destroy()
                except Exception:
                    pass
            os._exit(0)
        threading.Timer(0.15, _close).start()

    def open_manual(self):
        try:
            webview.create_window("ASTRA - User Guide", f"{self.base_url}/manual",
                                  width=980, height=820)
        except Exception:
            webbrowser.open(f"{self.base_url}/manual")


def _find_browser() -> list[str] | None:
    pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pfx86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    lad = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        rf"{pfx86}\Microsoft\Edge\Application\msedge.exe",
        rf"{pf}\Microsoft\Edge\Application\msedge.exe",
        rf"{lad}\Google\Chrome\Application\chrome.exe",
        rf"{pf}\Google\Chrome\Application\chrome.exe",
        rf"{pfx86}\Google\Chrome\Application\chrome.exe",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return [c]
    return None


def _fallback_window(server: _Server):
    url = f"http://127.0.0.1:{server.port}"
    browser = _find_browser()
    if browser:
        profile = Path(os.environ.get("TEMP", ".")) / "astra_app_profile"
        subprocess.Popen([*browser, f"--app={url}",
                          f"--user-data-dir={profile}",
                          "--window-size=1360,860", "--no-first-run"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(url)
    try:
        while server.server.should_exit is False:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=f"{APP_NAME} desktop application")
    ap.add_argument("--port", type=int, default=0,
                    help="fixed service port (default: auto-select free port)")
    args = ap.parse_args()

    _bootstrap_paths()
    port = args.port or _free_port()

    server = _Server(port)
    from server.api import app as fastapi_app
    fastapi_app.state.shutdown_cb = server.shutdown
    server.start()

    print(f"[{APP_NAME}] service starting on 127.0.0.1:{port} ...")
    if not _wait_healthy(port):
        print(f"[{APP_NAME}] service failed to become healthy; exiting.")
        return 1
    print(f"[{APP_NAME}] {APP_LONG} ready.")

    url = f"http://127.0.0.1:{port}"
    try:
        import webview
        bridge = _JsBridge(server)
        webview.create_window(
            f"{APP_NAME} - {APP_LONG}", url,
            js_api=bridge, width=1380, height=880, min_size=(1080, 680),
            background_color="#14171b",
        )
        # Blocks until the user closes the window; then we shut down cleanly.
        webview.start()
        print(f"[{APP_NAME}] window closed - shutting down.")
    except Exception as exc:
        print(f"[{APP_NAME}] native window unavailable ({exc}); "
              "falling back to application-mode browser.")
        _fallback_window(server)

    server.shutdown()
    try:
        from server.api import hub
        hub.stop_all()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
