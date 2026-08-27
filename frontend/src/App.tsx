import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  getMeta, getSummary, getScenarios, getDiagnostics, exportResults,
  startMission, stopMission, shutdownApp, manualUrl, liveStatus,
  type Meta, type MissionConfig, type Scenario,
} from "./api";
import Home from "./pages/Home";
import Operations from "./pages/Operations";
import Analysis from "./pages/Analysis";
import DataSources from "./pages/DataSources";
import Intelligence from "./pages/Intelligence";
import Geolocation from "./pages/Geolocation";

type Persp = "home" | "operations" | "analysis" | "data" | "intel" | "geo";
type DiagState =
  | { open: true; loading: boolean; data: Awaited<ReturnType<typeof getDiagnostics>> | null }
  | { open: false };

const SPEEDS: [string, number][] = [
  ["Slow (120/s)", 120], ["Normal (400/s)", 400], ["Fast (800/s)", 800],
  ["Maximum (1500/s)", 1500],
];

const NAV_ITEMS: { id: Persp; icon: string; label: string }[] = [
  { id: "home",       icon: "⬡", label: "Home" },
  { id: "operations", icon: "▶",  label: "Operations" },
  { id: "analysis",   icon: "📊", label: "Analysis" },
  { id: "intel",      icon: "🎯", label: "Intelligence" },
  { id: "geo",        icon: "🌐", label: "Geolocation" },
  { id: "data",       icon: "⚙",  label: "Data & Sources" },
];

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [persp, setPersp] = useState<Persp>("home");
  const [speed, setSpeed] = useState(400);
  const [running, setRunning] = useState(false);
  const [slot, setSlot] = useState(0);
  const [slotT, setSlotT] = useState(2400);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [diag, setDiag] = useState<DiagState>({ open: false });
  const [about, setAbout] = useState(false);
  const [scenModal, setScenModal] = useState<{ open: boolean; items: Scenario[] }>({ open: false, items: [] });
  const [resetKey, setResetKey] = useState(0);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => undefined);
    const t = setInterval(() => {
      liveStatus().then((s) => {
        setRunning(s.running); setSlot(s.slot); setSlotT(s.T);
      }).catch(() => undefined);
    }, 2000);
    return () => clearInterval(t);
  }, []);

  const shield = openMenu !== null || diag.open || about || scenModal.open;

  const doStart = async (opts: MissionConfig | string = {}) => {
    try {
      const cfg: MissionConfig = typeof opts === "string" ? { scenario: opts } : opts;
      await startMission({ ...cfg, speed });
      setResetKey((k) => k + 1);
      setPersp("operations");
      setRunning(true);
      setOpenMenu(null);
    } catch { /* surfaced via status bar */ }
  };
  const doStop = async () => { await stopMission().catch(() => undefined); setRunning(false); };
  const showDiag = async () => {
    setOpenMenu(null); setDiag({ open: true, loading: true, data: null });
    const data = await getDiagnostics().catch(() => null);
    setDiag({ open: true, loading: false, data });
  };
  const showScenarios = async () => {
    setOpenMenu(null);
    const r = await getScenarios().catch(() => ({ scenarios: [] }));
    setScenModal({ open: true, items: r.scenarios });
  };
  const doExit = async () => {
    type PyWeb = { pywebview?: { api?: { exit_app?: () => Promise<void>; open_manual?: () => void } } };
    const pw = (window as unknown as PyWeb).pywebview;
    if (pw?.api?.exit_app) {
      await pw.api.exit_app();
      return;
    }
    await shutdownApp().catch(() => undefined);
    window.close();
  };

  const openGuide = () => {
    type PyWeb = { pywebview?: { api?: { open_manual?: () => void } } };
    const pw = (window as unknown as PyWeb).pywebview;
    if (pw?.api?.open_manual) { pw.api.open_manual(); }
    else { window.open(manualUrl, "_blank"); }
  };

  type Entry = { label: string; hint?: string; action?: () => void; disabled?: boolean; sep?: boolean };
  const MENUS: Record<string, Entry[]> = {
    File: [
      { label: "New mission", hint: "Operations", action: () => { setResetKey((k) => k + 1); setPersp("operations"); setOpenMenu(null); } },
      { label: "Open scenario...", hint: "load battlefield", action: () => void showScenarios() },
      { sep: true, label: "" },
      { label: "Export results (JSON)", hint: "benchmarks", action: () => { void exportResults(); setOpenMenu(null); } },
      { label: "Exit", hint: "shut down", action: () => void doExit() },
    ],
    Run: [
      { label: "Start paired mission", action: () => void doStart() },
      { label: "Stop mission", action: () => void doStop() },
      { sep: true, label: "" },
      ...SPEEDS.map(([lbl, v]) => ({
        label: `Rate: ${lbl}`,
        hint: speed === v ? "\u2713" : undefined,
        action: () => { setSpeed(v); if (running) void doStart(); setOpenMenu(null); },
      })),
    ],
    Tools: [
      { label: "Diagnostics...", hint: "self-test", action: () => void showDiag() },
      { label: "Export results", hint: "JSON file", action: () => { void exportResults(); setOpenMenu(null); } },
    ],
    Help: [
      ...(meta?.manual_available
        ? [{ label: "User guide", hint: "F1", action: () => { openGuide(); setOpenMenu(null); } }]
        : []),
      { label: "About ASTRA", action: () => { setAbout(true); setOpenMenu(null); } },
    ],
  };

  const statusText = running ? `RUNNING — slot ${slot}/${slotT}` : "READY";

  return (
    <>
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="menubar" onMouseLeave={() => setOpenMenu(null)}>
        <span className="brand">
          <img src="/astra_logo.svg" alt="" />
          ASTRA
        </span>
        {Object.entries(MENUS).map(([name, entries]) => (
          <div key={name} className={"menu-item" + (openMenu === name ? " open" : "")}>
            <button onClick={() => setOpenMenu(openMenu === name ? null : name)}>{name}</button>
            {openMenu === name && (
              <div className="dropdown">
                {entries.map((e, i) => e.sep ? <hr key={i} /> : (
                  <button key={e.label} className={"entry" + (e.disabled ? " disabled" : "")}
                          onClick={e.disabled ? undefined : e.action}>
                    {e.label}{e.hint && <span className="hint">{e.hint}</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        <div className="header-right">
          <span className="version">{meta ? `${meta.app} ${meta.version}` : ""}</span>
        </div>
      </div>

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <nav className="sidebar">
        <div className="sidebar-section">
          <div className="sidebar-label">Navigation</div>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={"nav-item" + (persp === item.id ? " active" : "")}
              onClick={() => setPersp(item.id)}
            >
              <span className="icon">{item.icon}</span>
              <span className="label">{item.label}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-divider" />

        <div className="sidebar-section">
          <div className="sidebar-label">Mission Control</div>
          <button
            className="nav-item"
            onClick={() => void doStart()}
            disabled={running}
          >
            <span className="icon" style={{ color: running ? "var(--text-muted)" : "var(--green)" }}>▶</span>
            <span className="label">{running ? "Running..." : "Start Mission"}</span>
          </button>
          <button
            className="nav-item"
            onClick={() => void doStop()}
            disabled={!running}
          >
            <span className="icon" style={{ color: !running ? "var(--text-muted)" : "var(--red)" }}>⏹</span>
            <span className="label">Stop</span>
          </button>
        </div>

        <div className="sidebar-divider" />

        <div className="sidebar-section">
          <div className="sidebar-label">Simulation Rate</div>
          <div style={{ padding: "4px 14px" }}>
            <select
              value={speed}
              onChange={(e) => {
                const v = Number(e.target.value);
                setSpeed(v);
                if (running) {
                  stopMission().then(() => startMission({ speed: v }))
                    .then(() => setRunning(true)).catch(() => undefined);
                }
              }}
              style={{
                width: "100%",
                background: "var(--bg-surface)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: "6px",
                padding: "7px 10px",
                fontSize: "12.5px",
                fontFamily: "var(--font-sans)",
                cursor: "pointer",
                outline: "none",
              }}
            >
              {SPEEDS.map(([lbl, v]) => <option key={v} value={v}>{lbl}</option>)}
            </select>
          </div>
        </div>

        {/* Bottom actions */}
        <div className="sidebar-bottom">
          <button className="sidebar-btn" onClick={() => void showDiag()}>
            <span>🔧</span> Diagnostics
          </button>
          {meta?.manual_available && (
            <button className="sidebar-btn" onClick={() => openGuide()}>
              <span>📖</span> User Guide
            </button>
          )}
        </div>
      </nav>

      {/* ── Workspace ───────────────────────────────────────────── */}
      <main className="workspace">
        {persp === "home" && <Home meta={meta} onStart={() => void doStart()} onGo={(p) => setPersp(p)} />}
        {persp === "operations" && (
          <Operations resetKey={resetKey} running={running}
                      onStartMission={(cfg) => void doStart(cfg)} />
        )}
        {persp === "analysis" && <Analysis />}
        {persp === "data" && (
          <DataSources onScenarioLoad={(s) => void doStart(s)}
                       onFlyCustom={(nb, t) => void doStart({ n_bands: nb, T: t })} />
        )}
        {persp === "intel" && <Intelligence />}
        {persp === "geo" && <Geolocation />}
      </main>

      {/* ── Status Bar ──────────────────────────────────────────── */}
      <div className="statusbar">
        <span><span className={"dot" + (running ? " on" : "")} />{statusText}</span>
        <span>{meta ? meta.long : ""}</span>
        <div className="right">
          <span>{window.location.port ? `port ${window.location.port}` : "embedded service"}</span>
          {meta?.manual_available && (
            <button className="linklike" onClick={() => openGuide()}>docs</button>
          )}
        </div>
      </div>

      {/* ── Overlays ────────────────────────────────────────────── */}
      {shield && <div className="click-shield"
        onClick={() => { setOpenMenu(null); setAbout(false); setScenModal({ open: false, items: [] }); }}
        style={{ zIndex: 40 }} />}

      {diag.open && (
        <Modal title={`Diagnostics — ${diag.data ? `${diag.data.passed}/${diag.data.total} passed` : "running..."}`}
               onClose={() => setDiag({ open: false })}>
          {diag.loading && <div className="content">Running self-tests...</div>}
          {!diag.loading && diag.data && (
            <div className="content">
              {diag.data.checks.map((c) => (
                <div className="diag-row" key={c.name}>
                  <span className={"mark " + (c.ok ? "ok" : "no")}>{c.ok ? "\u2713" : "\u2717"}</span>
                  <div>
                    <div>{c.name}</div>
                    <div className="detail">{c.detail}</div>
                  </div>
                </div>
              ))}
              {!diag.data.all_ok && (
                <p style={{ color: "var(--amber)", marginBottom: 0 }}>
                  Some checks failed. The service may still run. See the user guide for troubleshooting.
                </p>
              )}
            </div>
          )}
          <footer><button className="tbtn" onClick={() => setDiag({ open: false })}>Close</button></footer>
        </Modal>
      )}

      {about && (
        <Modal title="About ASTRA" onClose={() => setAbout(false)}>
          <div className="content" style={{ textAlign: "center", padding: "32px 28px" }}>
            <img src="/astra_logo.svg" alt="ASTRA" style={{ width: 56, height: 56, marginBottom: 16 }} />
            <p style={{
              fontFamily: "var(--font-mono)", fontSize: 24, letterSpacing: 4,
              color: "var(--accent-bright)", margin: "0 0 8px", fontWeight: 700,
            }}>ASTRA</p>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, lineHeight: 1.6, marginBottom: 16 }}>
              {meta?.long ?? "Adaptive Spectrum Threat Recognition & Analysis"}
            </p>
            <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
              Version {meta?.version ?? "1.0.0"}
            </p>
            <p style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 16, lineHeight: 1.5 }}>
              Smart India Hackathon 2026 prototype.<br />
              Simulation-based research software; not operational equipment.
            </p>
          </div>
          <footer><button className="tbtn" onClick={() => setAbout(false)}>Close</button></footer>
        </Modal>
      )}

      {scenModal.open && (
        <Modal title="Open Scenario" onClose={() => setScenModal({ open: false, items: [] })}>
          <div className="content">
            <p style={{ marginTop: 0, color: "var(--text-secondary)" }}>
              Load a scenario to start a new paired mission with that battlefield definition.
            </p>
            {scenModal.items.length === 0 && <p>No scenario files found in /scenarios.</p>}
            {scenModal.items.map((s) => (
              <div className="list-item" key={s.name}>
                <div>
                  <b>{s.name}</b>
                  <div className="meta">
                    bands: {String((s.config as Record<string, number>).n_bands ?? "?")} ·
                    horizon: {String((s.config as Record<string, number>).T ?? "?")} slots
                  </div>
                </div>
                <button className="tbtn primary" onClick={() => {
                  setScenModal({ open: false, items: [] }); void doStart(s.name);
                }}>Load</button>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </>
  );
}

function Modal(p: { title: string; onClose: () => void;
                    children?: ReactNode; footer?: ReactNode }) {
  useEffect(() => {
    const h = (ev: KeyboardEvent) => { if (ev.key === "Escape") p.onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [p]);
  return (
    <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) p.onClose(); }}>
      <div className="modal">
        <header>
          <b>{p.title}</b>
          <button className="x" onClick={p.onClose}>&times;</button>
        </header>
        {p.children}
        {p.footer}
      </div>
    </div>
  );
}
