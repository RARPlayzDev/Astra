import { useEffect, useMemo, useRef, useState } from "react";
import { startMission, subscribeLive,
         type ArenaEvent, type IdRow, type LiveKpis, type MissionConfig,
         type SimFrame } from "../api";

const MAXCOLS = 300;

type Buf = { occ: number[][]; actions: number[]; hits: number[]; nBands: number };
const newBuf = (): Buf => ({ occ: [], actions: [], hits: [], nBands: 24 });

function pushFrame(b: Buf, f: SimFrame) {
  b.nBands = f.occupancy.length || b.nBands;
  const chunkCols = f.occupancy[0]?.length ?? 0;
  for (let c = 0; c < chunkCols; c++) {
    b.occ.push(f.occupancy.map((row) => row[c] ?? 0));
    b.actions.push(f.actions[c] ?? -1);
    b.hits.push(f.hits[c] ?? 0);
  }
  while (b.occ.length > MAXCOLS) {
    b.occ.shift(); b.actions.shift(); b.hits.shift();
  }
}

function draw(canvas: HTMLCanvasElement | null, b: Buf) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const W = canvas.width, H = canvas.height;
  ctx.fillStyle = "#10161d";
  ctx.fillRect(0, 0, W, H);
  const cols = Math.max(1, b.occ.length);
  const cw = W / cols;
  const ch = H / b.nBands;
  for (let i = 0; i < b.occ.length; i++) {
    const x = i * cw;
    const act = b.actions[i];
    if (act >= 0 && act < b.nBands) {
      ctx.fillStyle = "rgba(255,255,255,0.09)";
      ctx.fillRect(x, 0, Math.max(1, cw), H);
    }
    for (let bd = 0; bd < b.nBands; bd++) {
      if (b.occ[i][bd]) {
        ctx.fillStyle = "rgba(111,158,199,0.55)";
        ctx.fillRect(x + 0.5, bd * ch + 0.5, Math.max(1, cw - 1), Math.max(1, ch - 1));
      }
    }
    if (b.hits[i] && act >= 0 && act < b.nBands) {
      ctx.fillStyle = "#cfa453";
      ctx.fillRect(x, act * ch, Math.max(1.5, cw), Math.max(1.5, ch));
    }
  }
}

export const POLICIES: [string, string][] = [
  ["smart-scan", "SmartScan (adaptive)"],
  ["openloop-sequential", "Sequential sweep"],
  ["openloop-random", "Random scan"],
  ["bandit-ucb", "UCB bandit"],
  ["rl-linear-q", "Q-learning (linear)"],
  ["rl-dqn", "Deep Q-network"],
];
const policyTitle = (n: string) =>
  POLICIES.find(([id]) => id === n)?.[1] ?? n;

type Props = { resetKey: number; running: boolean;
               onStartMission: (cfg: MissionConfig) => void };

export default function Operations({ resetKey, running, onStartMission }: Props) {
  const [kpis, setKpis] = useState<Record<string, LiveKpis>>({});
  const [slot, setSlot] = useState(0);
  const [finals, setFinals] = useState<Record<string, LiveKpis> | null>(null);
  const [idRows, setIdRows] = useState<IdRow[]>([]);
  const [evasionEvents, setEvasionEvents] = useState<{ eid: number; slot: number; kind: string; detail: string }[]>([]);
  const [dndBands, setDndBands] = useState<Record<number, number>>({});
  const [schedA, setSchedA] = useState("smart-scan");
  const [schedB, setSchedB] = useState("openloop-sequential");
  const [teamSize, setTeamSize] = useState(1);
  const [sens, setSens] = useState(6);
  const [useSaved, setUseSaved] = useState(false);
  const bufs = useRef<Record<string, Buf>>({ smart: newBuf(), other: newBuf() });
  const canvases = useRef<Record<string, HTMLCanvasElement | null>>({
    "smart-scan": null, other: null,
  });
  const sideOf = (name: string): "smart" | "other" =>
    name === kpisSideName.current ? "smart" : "other";
  const kpisSideName = useRef<string>("smart-scan");

  useEffect(() => {
    bufs.current = { smart: newBuf(), other: newBuf() };
    setKpis({}); setFinals(null); setIdRows([]);
    setEvasionEvents([]); setDndBands({});
  }, [resetKey]);

  useEffect(() => {
    const off = subscribeLive((e: ArenaEvent) => {
      if (e.type === "frame") {
        let touched = false;
        for (const name of Object.keys(e.sims)) {
          const f = e.sims[name];
          if (!f) continue;
          if (!kpisSideName.current) kpisSideName.current = name;
          pushFrame(bufs.current[sideOf(name)], f);
          setKpis((prev) => ({ ...prev, [name]: f.kpis }));
          // Track DND bands from the primary receiver
          if (f.dnd_bands && Object.keys(f.dnd_bands).length > 0) {
            setDndBands(f.dnd_bands);
          }
          // Track evasion events
          if (f.evasion_events && f.evasion_events.length > 0) {
            setEvasionEvents((prev) => {
              const existing = new Set(prev.map((ev) => `${ev.eid}-${ev.slot}`));
              const newEvents = f.evasion_events!.filter((ev) => !existing.has(`${ev.eid}-${ev.slot}`));
              return newEvents.length > 0 ? [...prev, ...newEvents] : prev;
            });
          }
          touched = true;
        }
        if (touched) { setSlot(e.slot); setFinals(null); }
        for (const name of Object.keys(e.sims)) {
          draw(canvases.current[sideOf(name)], bufs.current[sideOf(name)]);
        }
      } else {
        setFinals(e.finals);
        if (e.id_reports) setIdRows(e.id_reports[kpisSideName.current] ?? []);
      }
    });
    return off;
  }, []);

  const launch = () => {
    kpisSideName.current = schedA;
    onStartMission({ schedA, schedB, teamSize, sensOffset: sens, useSaved });
  };

  const names = Object.keys(kpis);
  const verdict = useMemo(() => {
    if (!finals || names.length < 2) return null;
    const [n1, n2] = names;
    const a = finals[n1], b = finals[n2];
    return `Episode complete on identical scenarios: ${policyTitle(n1)} ` +
      `intercepted ${a.threats_found}/${a.n_threats} threats ` +
      `(${((a.threat_coverage ?? 0) * 100).toFixed(0)}%) against ` +
      `${b.threats_found}/${b.n_threats} (${((b.threat_coverage ?? 0) * 100).toFixed(0)}%).`;
  }, [finals, names]);

  const KpiTable = ({ k }: { k: LiveKpis }) => {
    const rows: [string, string][] = [
      ["Threat coverage", `${((k.threat_coverage ?? 0) * 100).toFixed(0)}%`],
      ["Threats intercepted", `${k.threats_found} of ${k.n_threats}`],
      ["All-emitter intercept ratio", `${(((k.intercept_ratio ?? 0)) * 100).toFixed(0)}%`],
      ["Reward per dwell", (k.avg_reward ?? 0).toFixed(3)],
      ["Hit rate", `${((k.hit_rate ?? 0) * 100).toFixed(0)}%`],
      ["False alarms", String(k.false_alarms)],
      ["Mean time to first intercept", k.mean_ttff != null ? `${k.mean_ttff} slots` : "-"],
      ["Threat TTFF", k.threat_mean_ttff != null ? `${k.threat_mean_ttff} slots` : "-"],
      ["Prediction accuracy", `${(((k.pred_accuracy ?? 0)) * 100).toFixed(0)}%`],
      ["Periodic locks", String(k.locks ?? 0)],
    ];
    return (
      <div className="kv">
        {rows.map(([a, b]) => (
          <div className="row" key={a}><span>{a}</span><span>{b}</span></div>
        ))}
        {k.team && k.team > 1 && (
          <div className="row"><span>Cooperative team</span><span>{k.team} receivers</span></div>
        )}
        {k.loaded_weights && <div className="row"><span>Saved weights</span><span>loaded</span></div>}
      </div>
    );
  };

  return (
    <>
      <h1 className="page-title">Operations</h1>
      <p className="lede">
        Blue-grey cells are true emitter transmissions, the bright column is where
        each receiver is tuned, amber marks an intercept. Both sides fly identical
        battlefields.
      </p>

      <div className="panel">
        <h3>Mission configuration</h3>
        <div className="body controls-row" style={{ marginBottom: 0 }}>
          <button className="tbtn primary" onClick={launch}>Start mission</button>
          <label>Receiver A
            <select value={schedA} onChange={(e) => setSchedA(e.target.value)}>
              {POLICIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label>Receiver B
            <select value={schedB} onChange={(e) => setSchedB(e.target.value)}>
              {POLICIES.filter(([v]) => v !== schedA)
                .map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label>Team size
            <select value={teamSize}
                    onChange={(e) => setTeamSize(Number(e.target.value))}>
              {[1, 2, 3].map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>
          <label>
            Sensitivity offset
            <input type="range" min={3} max={12} step={0.5} value={sens}
                   onChange={(e) => setSens(Number(e.target.value))} />
            <span className="readout">{sens.toFixed(1)} dB</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={useSaved}
                   onChange={(e) => setUseSaved(e.target.checked)} />
            Load saved weights
          </label>
        </div>
      </div>

      {verdict && <div className="result-note"><b>Result.</b> {verdict}</div>}

      <div className="receivers">
        {names.length === 0 && (
          <p style={{ color: "var(--muted)" }}>
            Configure and start a mission. Any two policies may be paired; teams
            above one receiver use cooperative band de-confliction.
          </p>
        )}
        {names.map((name) => (
          <div className="rx-panel" key={name}>
            <h3>{policyTitle(name)}</h3>
            <p className="role">
              {name === "smart-scan"
                ? "Surveys, estimates emitter rhythms, predicts windows, arrives early."
                : "Reference policy for comparison on the same battlefield."}
            </p>
            <canvas ref={(el) => { canvases.current[sideOf(name)] = el; }}
                    width={640} height={190} />
            {kpis[name] ? <KpiTable k={kpis[name]} /> : null}
          </div>
        ))}
      </div>

      <div className="legend">
        <span><i style={{ background: "rgba(111,158,199,.55)" }} />transmission (ground truth)</span>
        <span><i style={{ background: "rgba(255,255,255,.25)" }} />receiver tuned band</span>
        <span><i style={{ background: "#cfa453" }} />intercept</span>
      </div>
      <p className="tbl-note">Current slot: {slot}. Episodes restart automatically
      with a fresh scenario when complete.</p>

      {idRows.length > 0 && (
        <div className="panel" style={{ marginTop: 16 }}>
          <h3>Threat board - identified emitters (Receiver A)</h3>
          <div className="body table-wrap" style={{ paddingTop: 4 }}>
            <table className="data">
              <thead><tr>
                <th>EID</th><th>Identified</th><th>Class</th><th>Threat</th>
                <th>Confidence</th><th>Pulses</th><th>Ground truth</th><th>Match</th>
              </tr></thead>
              <tbody>
                {idRows.map((r) => (
                  <tr key={r.eid}>
                    <td className="num">{r.eid}</td>
                    <td className="txt">{r.identified}</td>
                    <td className="txt">{r.cls}</td>
                    <td><span className={"badge " +
                        (r.threat === "HIGH" ? "fail" : r.threat === "-" ? "pass" : "pass")}>
                      {r.threat}</span></td>
                    <td className="num">{r.confidence}</td>
                    <td className="num">{r.pulses}</td>
                    <td className="txt">{r.ground_truth}</td>
                    <td><span className={"badge " + (r.correct ? "pass" : "fail")}>
                      {r.correct ? "MATCH" : "MISS"}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* DND Token Visualization */}
      {Object.keys(dndBands).length > 0 && (
        <div className="panel" style={{ marginTop: 16 }}>
          <h3>Spectrum de-confliction (DND tokens)</h3>
          <div className="body">
            <p className="tbl-note" style={{ marginTop: 0 }}>
              Bands locked by a receiver via phase-lock prediction are
              marked "Do Not Disturb" — other team members avoid them,
              ensuring zero redundancy and partitioned spectrum coverage.
            </p>
            <div style={{ display: "flex", gap: 2, flexWrap: "wrap", marginTop: 8 }}>
              {Array.from({ length: 24 }, (_, b) => {
                const owner = dndBands[b];
                const bg = owner === 0 ? "var(--accent-dark)"
                         : owner === 1 ? "var(--warn)"
                         : "var(--panel2)";
                return (
                  <div key={b} title={`Band ${b}${owner != null ? ` → receiver ${owner + 1}` : " (free)"}`}
                       style={{ width: 28, height: 20, borderRadius: 2,
                                background: bg, border: "1px solid var(--line)",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontSize: 8, color: "var(--muted)", fontFamily: "var(--mono)" }}>
                    {b}
                  </div>
                );
              })}
            </div>
            <div className="legend" style={{ marginTop: 8 }}>
              <span><i style={{ background: "var(--accent-dark)" }} />Receiver A locked</span>
              <span><i style={{ background: "var(--warn)" }} />Receiver B locked</span>
              <span><i style={{ background: "var(--panel2)" }} />Free band</span>
            </div>
          </div>
        </div>
      )}

      {/* Counter-ESM Evasion Log */}
      {evasionEvents.length > 0 && (
        <div className="panel" style={{ marginTop: 16 }}>
          <h3>Counter-ESM evasion events</h3>
          <div className="body table-wrap" style={{ paddingTop: 4 }}>
            <p className="tbl-note" style={{ marginTop: 0 }}>
              Evasive emitters that are intercepted 3+ consecutive times
              automatically shift their rotation phase or frequency hop-set
              to avoid further interception.
            </p>
            <table className="data">
              <thead><tr>
                <th>Slot</th><th>Emitter</th><th>Type</th><th>Detail</th>
              </tr></thead>
              <tbody>
                {evasionEvents.map((ev, i) => (
                  <tr key={i}>
                    <td className="num">{ev.slot}</td>
                    <td className="num">{ev.eid}</td>
                    <td><span className="badge fail">EVADED</span></td>
                    <td className="txt">{ev.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
