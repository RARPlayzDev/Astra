"""ASTRA desktop application — native PySide6 window with embedded browser.

Replaces the pywebview approach with a proper Qt application:
  * Native QMenuBar with File / View / Run / Tools / Help
  * QToolBar with Start / Stop / Speed / Diagnostics / User Guide
  * QWebEngineView as the central widget (React SPA)
  * QStatusBar showing READY / RUNNING state
  * QSystemTrayIcon for minimize-to-tray
  * F11 for fullscreen, F1 for user guide

The FastAPI backend runs in a daemon thread exactly as before.

Build:
    python tools/build_exe_qt.py   ->  dist/ASTRA/ASTRA.exe
"""
from __future__ import annotations

import http.client
import os
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "ASTRA"
APP_LONG = "Adaptive Spectrum Threat Recognition & Analysis"
APP_VERSION = "1.0.0"


def _bootstrap_paths():
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "."))
        os.chdir(base)
        if str(base) not in sys.path:
            sys.path.insert(0, str(base))
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
    """FastAPI backend running in a daemon thread."""

    def __init__(self, port: int):
        import uvicorn
        self.port = port
        self.config = uvicorn.Config(
            "server.api:app", host="127.0.0.1",
            port=port, log_level="warning", access_log=False,
        )
        self.server = uvicorn.Server(self.config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self):
        self.thread.start()

    def shutdown(self):
        self.server.should_exit = True


def _run_app():
    """Main Qt application entry point."""
    from PySide6.QtCore import Qt, QTimer, QUrl, Signal
    from PySide6.QtGui import QAction, QFont, QIcon, QKeySequence
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QMenu, QMenuBar,
        QMessageBox, QSystemTrayIcon, QToolBar, QWidget,
        QVBoxLayout,
    )
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

    # ── Bootstrap server ──────────────────────────────────────────────
    port = _free_port()
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

    # ── Create application ────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("ASTRA")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # ── Main window ───────────────────────────────────────────────────
    win = QMainWindow()
    win.setWindowTitle(f"{APP_NAME} — {APP_LONG}")
    win.setMinimumSize(1080, 680)
    win.resize(1380, 880)

    # ── Central widget: embedded browser ──────────────────────────────
    web = QWebEngineView()
    page = web.page()
    page.settings().setAttribute(
        page.settings().WebAttribute.LocalContentCanAccessRemoteUrls, False
    )
    page.settings().setAttribute(
        page.settings().WebAttribute.LocalContentCanAccessFileUrls, True
    )
    win.setCentralWidget(web)

    # ── Menu bar ──────────────────────────────────────────────────────
    menu_bar = win.menuBar()

    # File menu
    file_menu = menu_bar.addMenu("&File")

    new_mission = QAction("New mission window", win)
    new_mission.setShortcut(QKeySequence("Ctrl+N"))
    file_menu.addAction(new_mission)

    open_scenario = QAction("Open scenario...", win)
    open_scenario.setShortcut(QKeySequence("Ctrl+O"))
    file_menu.addAction(open_scenario)

    file_menu.addSeparator()

    export_action = QAction("Export results (JSON)", win)
    export_action.setShortcut(QKeySequence("Ctrl+E"))
    file_menu.addAction(export_action)

    file_menu.addSeparator()

    exit_action = QAction("Exit", win)
    exit_action.setShortcut(QKeySequence("Ctrl+Q"))
    file_menu.addAction(exit_action)

    # View menu
    view_menu = menu_bar.addMenu("&View")

    for name, label in [
        ("home", "Home"), ("operations", "Operations"),
        ("analysis", "Analysis"), ("intel", "Intelligence"),
        ("geo", "Geolocation"), ("data", "Data & Sources"),
    ]:
        act = QAction(label, win)
        act.triggered.connect(lambda _, n=name: web.page().runJavaScript(
            f"window.__astra_nav && window.__astra_nav('{n}')"
        ))
        view_menu.addAction(act)

    view_menu.addSeparator()

    fullscreen_action = QAction("Full screen", win)
    fullscreen_action.setShortcut(QKeySequence("F11"))
    view_menu.addAction(fullscreen_action)

    # Run menu
    run_menu = menu_bar.addMenu("&Run")

    start_action = QAction("Start paired mission", win)
    start_action.setShortcut(QKeySequence("F5"))
    run_menu.addAction(start_action)

    stop_action = QAction("Stop mission", win)
    stop_action.setShortcut(QKeySequence("Shift+F5"))
    run_menu.addAction(stop_action)

    run_menu.addSeparator()

    speed_group = []
    for label_text, speed_val in [
        ("Slow (120/s)", 120), ("Normal (400/s)", 400),
        ("Fast (800/s)", 800), ("Maximum (1500/s)", 1500),
    ]:
        act = QAction(label_text, win)
        act.setCheckable(True)
        act.triggered.connect(lambda _, v=speed_val: web.page().runJavaScript(
            f"window.__astra_set_speed && window.__astra_set_speed({v})"
        ))
        speed_group.append(act)
        run_menu.addAction(act)
    speed_group[1].setChecked(True)

    # Tools menu
    tools_menu = menu_bar.addMenu("&Tools")

    diag_action = QAction("Diagnostics...", win)
    diag_action.setShortcut(QKeySequence("Ctrl+D"))
    tools_menu.addAction(diag_action)

    # Help menu
    help_menu = menu_bar.addMenu("&Help")

    guide_action = QAction("User guide", win)
    guide_action.setShortcut(QKeySequence("F1"))
    help_menu.addAction(guide_action)

    help_menu.addSeparator()

    about_action = QAction("About ASTRA", win)
    help_menu.addAction(about_action)

    # ── Toolbar ───────────────────────────────────────────────────────
    toolbar = QToolBar("Main")
    toolbar.setMovable(False)
    toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
    win.addToolBar(toolbar)

    tb_start = toolbar.addAction("▶ Start Mission")
    tb_stop = toolbar.addAction("⏹ Stop")
    toolbar.addSeparator()
    tb_rate = toolbar.addAction("Rate: Normal (400/s)")
    tb_rate.setCheckable(False)
    toolbar.addSeparator()
    tb_diag = toolbar.addAction("Diagnostics")
    tb_guide = toolbar.addAction("User Guide")
    toolbar.addSeparator()

    # ── Status bar ────────────────────────────────────────────────────
    status_bar = win.statusBar()
    status_label = status_bar.addWidget(QWidget())
    status_bar.showMessage("READY")

    version_label = status_bar.addPermanentWidget(QWidget())
    status_bar.addPermanentWidget(
        __import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel(
            f"{APP_NAME} {APP_VERSION}"
        )
    )

    # ── System tray ───────────────────────────────────────────────────
    tray = QSystemTrayIcon(QIcon(), win)
    tray_menu = QMenu()
    tray_menu.addAction("Show", win.show)
    tray_menu.addAction("Exit", lambda: app.quit())
    tray.setContextMenu(tray_menu)
    tray.activated.connect(
        lambda reason: win.show() if reason == QSystemTrayIcon.DoubleClick else None
    )
    tray.show()

    # ── Signal handlers ───────────────────────────────────────────────
    def do_exit():
        server.shutdown()
        try:
            from server.api import hub
            hub.stop_all()
        except Exception:
            pass
        app.quit()

    def do_start():
        web.page().runJavaScript(
            "window.__astra_start && window.__astra_start()"
        )

    def do_stop():
        web.page().runJavaScript(
            "window.__astra_stop && window.__astra_stop()"
        )

    def do_diag():
        web.page().runJavaScript(
            "window.__astra_diag && window.__astra_diag()"
        )

    def do_guide():
        import webbrowser
        webbrowser.open(f"{url}/manual")

    def do_fullscreen():
        if win.isFullScreen():
            win.showNormal()
        else:
            win.showFullScreen()

    def do_about():
        QMessageBox.about(
            win, f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2>"
            f"<p>{APP_LONG}</p>"
            f"<p>Version {APP_VERSION}</p>"
            f"<p>Smart India Hackathon 2026 prototype.<br>"
            f"Simulation-based research software; not operational equipment.</p>"
        )

    # Wire up actions
    exit_action.triggered.connect(do_exit)
    start_action.triggered.connect(do_start)
    stop_action.triggered.connect(do_stop)
    diag_action.triggered.connect(do_diag)
    guide_action.triggered.connect(do_guide)
    fullscreen_action.triggered.connect(do_fullscreen)
    about_action.triggered.connect(do_about)
    tb_start.triggered.connect(do_start)
    tb_stop.triggered.connect(do_stop)
    tb_diag.triggered.connect(do_diag)
    tb_guide.triggered.connect(do_guide)

    # ── Status polling ────────────────────────────────────────────────
    def poll_status():
        try:
            import urllib.request
            with urllib.request.urlopen(f"{url}/api/live/status", timeout=2) as r:
                import json
                data = json.loads(r.read())
                running = data.get("running", False)
                slot = data.get("slot", 0)
                T = data.get("T", 2400)
                if running:
                    status_bar.showMessage(f"RUNNING — slot {slot}/{T}")
                else:
                    status_bar.showMessage("READY")
        except Exception:
            status_bar.showMessage("READY")

    timer = QTimer()
    timer.timeout.connect(poll_status)
    timer.start(2000)

    # ── Bridge: inject navigation functions into the page ─────────────
    bridge_js = f"""
    window.__astra_nav = function(persp) {{
        // Dispatch custom event for React to pick up
        window.dispatchEvent(new CustomEvent('astra-nav', {{ detail: persp }}));
    }};
    window.__astra_start = function() {{
        // Click the start button if visible
        const btn = document.querySelector('.tbtn.primary');
        if (btn) btn.click();
    }};
    window.__astra_stop = function() {{
        const btns = document.querySelectorAll('.tbtn.stop');
        if (btns.length) btns[0].click();
    }};
    window.__astra_diag = function() {{
        // Navigate to tools > diagnostics
        window.dispatchEvent(new CustomEvent('astra-diag'));
    }};
    """

    def inject_bridge(ok):
        if ok:
            web.page().runJavaScript(bridge_js)

    web.loadFinished.connect(inject_bridge)

    # ── Clean shutdown ────────────────────────────────────────────────
    def on_close():
        server.shutdown()
        try:
            from server.api import hub
            hub.stop_all()
        except Exception:
            pass

    win.closeEvent = lambda event: (on_close(), event.accept())

    # ── Show and run ──────────────────────────────────────────────────
    web.setUrl(QUrl(url))
    win.show()
    return app.exec()


def main() -> int:
    _bootstrap_paths()
    return _run_app()


if __name__ == "__main__":
    raise SystemExit(main())
