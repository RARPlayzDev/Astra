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
  const [nFhss, setNFhss] = useState(3);
  const [nTdma, setNTdma] = useState(2);
  const [cfarPfa, setCfarPfa] = useState(0.001);
  const [dwellUs, setDwellUs] = useState(1);
  // Fidelity controls (teardown rev. 5): LPI waveform share, the receiver's
  // matched-filter chain, and the AOA measurement model.
  const [lpiFraction, setLpiFraction] = useState(0);
  const [matchedFilter, setMatchedFilter] = useState(true);
  const [aoaModel, setAoaModel] = useState("interferometer");
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
    onStartMission({ schedA, schedB, teamSize, sensOffset: sens, useSaved,
                     nFhss, nTdma, cfarPfa, dwellTimeUs: dwellUs,
    lpiFraction, matchedFilter, aoaModel });
  };

  const names = Object.keys(kpis);
  const [n1, n2] = names;
  const a = names.length === 2 ? kpis[n1] : undefined;
  const b = names.length === 2 ? kpis[n2] : undefined;

  // Live head-to-head: per-metric leader with direction awareness.
  const ADV: { key: keyof LiveKpis; label: string; lower?: boolean; fmt?: (v: number) => string }[] = [
    { key: "threat_coverage", label: "Threat coverage", fmt: (v) => `${(v * 100).toFixed(0)}%` },
    { key: "avg_reward", label: "Reward / dwell", fmt: (v) => v.toFixed(3) },
    { key: "intercept_ratio", label: "Intercept ratio", fmt: (v) => `${(v * 100).toFixed(0)}%` },
    { key: "hit_rate", label: "Hit rate", fmt: (v) => `${(v * 100).toFixed(0)}%` },
    { key: "false_alarms", label: "False alarms", lower: true },
    { key: "locks", label: "Periodic locks" },
  ];
  const advRows = (a && b)
    ? ADV.map((r) => {
        const va = Number(a[r.key] ?? 0), vb = Number(b[r.key] ?? 0);
        const aWins = r.lower ? va < vb : va > vb;
        const tot = va + vb;
        return { ...r, va, vb, aWins, pct: tot > 0 ? va / tot : 0.5 };
      })
    : [];
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
    const smartAcc = k.pred_active_count && k.pred_active_count > 0
      ? `${((k.pred_active_accuracy ?? 0) * 100).toFixed(0)}% (${k.pred_active_count} predictions)`
      : "-";
    const rows: [string, string, boolean][] = [
      ["Threat coverage", `${((k.threat_coverage ?? 0) * 100).toFixed(0)}%`, true],
      ["Threats intercepted", `${k.threats_found} of ${k.n_threats}`, false],
      ["All-emitter intercept ratio", `${(((k.intercept_ratio ?? 0)) * 100).toFixed(0)}%`, false],
      ["Reward per dwell", (k.avg_reward ?? 0).toFixed(3), true],
      ["Hit rate", `${((k.hit_rate ?? 0) * 100).toFixed(0)}%`, true],
      ["False alarms", String(k.false_alarms), false],
      ["Threat TTFF", k.threat_mean_ttff != null ? `${k.threat_mean_ttff} slots` : "-", true],
      ["Smart prediction accuracy", smartAcc, true],
      ["Periodic locks", String(k.locks ?? 0), false],
    ];
    return (
      <div className="kv">
        {rows.map(([a, b, bold]) => (
          <div className="row" key={a}>
            <span style={bold ? { fontWeight: 600 } : undefined}>{a}</span>
            <span style={bold ? { fontWeight: 700, color: "var(--accent)" } : undefined}>{b}</span>
          </div>
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
          <label>FHSS comm nets
            <input type="number" min={0} max={12} value={nFhss}
                   onChange={(e) => setNFhss(Math.max(0, Number(e.target.value)))} />
          </label>
          <label>TDMA comm stations
            <input type="number" min={0} max={12} value={nTdma}
                   onChange={(e) => setNTdma(Math.max(0, Number(e.target.value)))} />
          </label>
          <label>CFAR P<sub>fa</sub>
            <select value={cfarPfa}
                    onChange={(e) => setCfarPfa(Number(e.target.value))}>
              <option value={0.001}>1e-3</option>
              <option value={0.0001}>1e-4</option>
              <option value={0.000001}>1e-6</option>
            </select>
          </label>
          <label>Dwell time
            <select value={dwellUs}
                    onChange={(e) => setDwellUs(Number(e.target.value))}>
              {[0.1, 1, 5, 20].map((v) => <option key={v} value={v}>{v} &micro;s</option>)}
            </select>
          </label>
          <label>LPI waveform share
            <select value={lpiFraction}
                    onChange={(e) => setLpiFraction(Number(e.target.value))}>
              {[0, 0.2, 0.5, 1].map((v) => (
                <option key={v} value={v}>{Math.round(v * 100)}%</option>))}
            </select>
          </label>
          <label>Matched filter
            <select value={matchedFilter ? "on" : "off"}
                    onChange={(e) => setMatchedFilter(e.target.value === "on")}>
              <option value="on">on (de-chirp bank)</option>
              <option value="off">off (plain radiometer)</option>
            </select>
          </label>
          <label>AOA model
            <select value={aoaModel}
                    onChange={(e) => setAoaModel(e.target.value)}>
              <option value="interferometer">interferometer (CRLB)</option>
              <option value="fixed">fixed 2.5&deg;</option>
            </select>
          </label>
        </div>
        <p className="tbl-note" style={{ margin: "6px 0 0" }}>
          Communication emitters exercise the COMINT half of the problem
          statement; CFAR P<sub>fa</sub> and dwell time drive the physically
          coupled radiometer + Albersheim + CA-CFAR detection chain.
        </p>
      </div>

      {advRows.length > 0 && a && b && (
        <div className="panel" style={{ marginBottom: 14 }}>
          <h3>Live advantage &mdash; {policyTitle(n1)} vs {policyTitle(n2)}</h3>
          <div className="body">
            <div className="adv-grid">
              {advRows.map((r) => (
                <div className="adv-cell" key={r.key as string}>
                  <div className="t">{r.label}</div>
                  <div className="nums">
                    <span className={r.aWins ? "leader" : "lag"}>{r.fmt ? r.fmt(r.va) : r.va}</span>
                    <span className={!r.aWins ? "leader" : "lag"}>{r.fmt ? r.fmt(r.vb) : r.vb}</span>
                  </div>
                  <div className="bar">
                    <i className="a" style={{ width: `${r.pct * 100}%` }} />
                    <i className="b" style={{ width: `${(1 - r.pct) * 100}%` }} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 5 }}>
                    <span className={"tag " + (r.aWins ? "ahead" : "behind")}>
                      {r.aWins ? "A LEADS" : "B LEADS"}
                    </span>
                    <span className={"tag " + (!r.aWins ? "ahead" : "behind")}>
                      {!r.aWins ? "B LEADS" : "A LEADS"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {verdict && <div className="result-note"><b>Result.</b> {verdict}</div>}

      <div className="receivers">
        {names.length === 0 && (
          <p style={{ color: "var(--muted)" }}>
            Configure and start a mission. Any two policies may be paired; teams
            above one receiver use cooperative band de-confliction.
          </p>
        )}
        {names.map((name) => (
          <div className={"rx-panel" + (finals && kpis[name] && Object.keys(kpis).length === 2 &&
            Number(kpis[name].avg_reward) >= Number(kpis[names[0] === name ? names[1] : names[0]]?.avg_reward ?? 0)
            ? " leader-panel" : "")} key={name}>
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
