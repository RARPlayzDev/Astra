import { useEffect, useState, type ReactNode } from "react";
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
  ["Max (1500/s)", 1500],
];

const TABS: [Persp, string][] = [
  ["home",       "Home"],
  ["operations", "Operations"],
  ["analysis",   "Analysis"],
  ["intel",      "Intelligence"],
  ["geo",        "Geolocation"],
  ["data",       "Data & Sources"],
];

/** Detect if running inside Qt desktop app */
const isQt = () => !!(window as unknown as Record<string, unknown>).__AstraQt;

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
    } catch { /* ignore */ }
  };
  const doStop = async () => {
    await stopMission().catch(() => undefined);
    setRunning(false);
  };
  const showDiag = async () => {
    setOpenMenu(null);
    setDiag({ open: true, loading: true, data: null });
    const data = await getDiagnostics().catch(() => null);
    setDiag({ open: true, loading: false, data });
  };
  const showScenarios = async () => {
    setOpenMenu(null);
    const r = await getScenarios().catch(() => ({ scenarios: [] }));
    setScenModal({ open: true, items: r.scenarios });
  };
  const doExit = async () => {
    type PW = { pywebview?: { api?: { exit_app?: () => Promise<void> } } };
    const pw = (window as unknown as PW).pywebview;
    if (pw?.api?.exit_app) { await pw.api.exit_app(); return; }
    await shutdownApp().catch(() => undefined);
    window.close();
  };
  const openGuide = () => {
    type PW = { pywebview?: { api?: { open_manual?: () => void } } };
    const pw = (window as unknown as PW).pywebview;
    if (pw?.api?.open_manual) pw.api.open_manual();
    else window.open(manualUrl, "_blank");
  };

  // ── Menu bar (browser mode only — Qt provides its own native menu) ──
  type Entry = { label: string; hint?: string; action?: () => void; disabled?: boolean; sep?: boolean };
  const MENUS: Record<string, Entry[]> = {
    File: [
      { label: "New mission", action: () => { setResetKey((k) => k + 1); setPersp("operations"); setOpenMenu(null); } },
      { label: "Open scenario\u2026", action: () => void showScenarios() },
      { sep: true, label: "" },
      { label: "Export results", action: () => { void exportResults(); setOpenMenu(null); } },
      { label: "Exit", action: () => void doExit() },
    ],
    Run: [
      { label: "Start paired mission", action: () => void doStart() },
      { label: "Stop mission", action: () => void doStop() },
      { sep: true, label: "" },
      ...SPEEDS.map(([lbl, v]) => ({
        label: `Rate: ${lbl}`,
        hint: speed === v ? "\u2713" : undefined,
        action: () => { setSpeed(v); setOpenMenu(null); },
      })),
    ],
    Tools: [
      { label: "Diagnostics\u2026", action: () => void showDiag() },
    ],
    Help: [
      ...(meta?.manual_available
        ? [{ label: "User guide", action: () => { openGuide(); setOpenMenu(null); } }]
        : []),
      { label: "About ASTRA", action: () => { setAbout(true); setOpenMenu(null); } },
    ],
  };

  const statusText = running ? `RUNNING \u2014 slot ${slot}/${slotT}` : "READY";

  return (
    <>
      {/* ── Menu bar (browser mode only) ───────────────────────── */}
      <div className={"menubar" + (isQt() ? " hidden" : "")}
           onMouseLeave={() => setOpenMenu(null)}>
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
      </div>

      {/* ── Control strip (tabs + action controls, always visible) ── */}
      <div className="control-strip">
        <div className="tabs">
          {TABS.map(([id, lbl]) => (
            <button key={id} className={persp === id ? "active" : ""}
                    onClick={() => setPersp(id)}>
              {lbl}
            </button>
          ))}
        </div>
        <div className="sep" />
        <div className="controls">
          <button className="tbtn primary" onClick={() => void doStart()} disabled={running}>
            Start
          </button>
          <button className="tbtn stop" onClick={() => void doStop()} disabled={!running}>
            Stop
          </button>
          <label>Rate</label>
          <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
            {SPEEDS.map(([, v]) => <option key={v} value={v}>{v}/s</option>)}
          </select>
          <button className="tbtn" onClick={() => void showDiag()}>Diagnostics</button>
          {meta?.manual_available && (
            <button className="tbtn" onClick={() => openGuide()}>Guide</button>
          )}
          <span className="port-tag">
            {window.location.port ? `:${window.location.port}` : ""}
          </span>
        </div>
      </div>

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

      {/* ── Status bar ──────────────────────────────────────────── */}
      <div className="statusbar">
        <span><span className={"dot" + (running ? " on" : "")} />{statusText}</span>
        <span>{meta ? meta.long : ""}</span>
        <div className="right">
          {meta?.manual_available && (
            <button className="linklike" onClick={() => openGuide()}>docs</button>
          )}
        </div>
      </div>

      {/* ── Overlays ────────────────────────────────────────────── */}
      {shield && <div className="click-shield"
        onClick={() => { setOpenMenu(null); setAbout(false); setScenModal({ open: false, items: [] }); }} />}

      {diag.open && (
        <Modal title={diag.data ? `Diagnostics \u2014 ${diag.data.passed}/${diag.data.total} passed` : "Diagnostics"}
               onClose={() => setDiag({ open: false })}>
          {diag.loading && <div className="content">Running self-tests\u2026</div>}
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
            </div>
          )}
          <footer><button className="tbtn" onClick={() => setDiag({ open: false })}>Close</button></footer>
        </Modal>
      )}

      {about && (
        <Modal title="About" onClose={() => setAbout(false)}>
          <div className="content">
            <p style={{ fontFamily: "var(--mono)", fontSize: 16, letterSpacing: 2, color: "var(--ink-hi)", margin: "2px 0" }}>ASTRA</p>
            <p>{meta?.long ?? "Adaptive Spectrum Threat Recognition & Analysis"}</p>
            <p style={{ color: "var(--muted)", fontSize: 11.5 }}>
              Version {meta?.version ?? "1.0.0"} &mdash; Smart India Hackathon 2026
            </p>
          </div>
          <footer><button className="tbtn" onClick={() => setAbout(false)}>Close</button></footer>
        </Modal>
      )}

      {scenModal.open && (
        <Modal title="Open scenario" onClose={() => setScenModal({ open: false, items: [] })}>
          <div className="content">
            {scenModal.items.length === 0 && <p>No scenario files found.</p>}
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

function Modal(p: { title: string; onClose: () => void; children?: ReactNode; footer?: ReactNode }) {
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
