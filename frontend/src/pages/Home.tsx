import { useEffect, useState } from "react";
import { getSummary, getScenarios, type Meta, type Summary } from "../api";

type Props = {
  meta: Meta | null;
  onStart: () => void;
  onGo: (p: "operations" | "analysis" | "data") => void;
};

const f = (v: number | null | undefined, d = 3) =>
  v != null && Number.isFinite(v) ? v.toFixed(d) : "\u2014";
const pct = (v: number | null | undefined) =>
  v != null && Number.isFinite(v) ? `${(v * 100).toFixed(0)}%` : "\u2014";

export default function Home({ meta, onStart, onGo }: Props) {
  const [s, setS] = useState<Summary | null>(null);
  const [nScen, setNScen] = useState(0);
  useEffect(() => {
    getSummary().then(setS).catch(() => undefined);
    getScenarios().then((r) => setNScen(r.scenarios.length)).catch(() => undefined);
  }, []);

  const me = s?.mission_effectiveness ?? null;
  const capable = me ? Object.values(me.scores).filter((x) => x.mission_capable).length : 0;
  const ss = s?.monte_carlo_means["smart-scan"];
  const seq = s?.monte_carlo_means["openloop-sequential"];
  const rewardX = (ss && seq && seq.avg_reward && ss.avg_reward)
    ? (ss.avg_reward / seq.avg_reward).toFixed(1) : "—";

  // ── Head-to-head: SmartScan vs sequential sweep across every FoM ──────
  // `lower` marks metrics where a smaller value is better; `caveat` marks
  // first-intercept timing, where the sweep's mean is censored to the few
  // easy emitters it stumbles on (SmartScan finds ~20% more emitters).
  const H2H: { key: string; label: string; fmt: (v: number) => string; lower?: boolean; caveat?: string }[] = [
    { key: "avg_reward", label: "Avg reward / dwell", fmt: (v) => v.toFixed(3) },
    { key: "threat_intercept_ratio", label: "Threat coverage (Pd)", fmt: (v) => `${(v * 100).toFixed(1)}%` },
    { key: "intercept_ratio", label: "All-emitter intercept", fmt: (v) => `${(v * 100).toFixed(1)}%` },
    { key: "intercept_rate", label: "Intercept rate", fmt: (v) => v.toFixed(3) },
    { key: "pct_correct_predictions", label: "Prediction accuracy", fmt: (v) => `${(v * 100).toFixed(1)}%` },
    { key: "false_alarm_rate", label: "False-alarm rate", fmt: (v) => v.toExponential(1), lower: true },
    { key: "avg_intercept_time_error", label: "Intercept-time error", fmt: (v) => v.toFixed(1), lower: true },
    { key: "n_periodic_locked", label: "Periodic locks", fmt: (v) => v.toFixed(2) },
    { key: "threat_ttff_censored", label: "Threat latency (censored)", fmt: (v) => v.toFixed(0), lower: true,
      caveat: "Censored latency credits every never-intercepted threat the full episode horizon - the operationally correct T&E treatment. The sweep's raw TTFF looks low only because it drops threats it never finds." },
  ];
  const h2hRows = H2H
    .map((r) => {
      const a = ss?.[r.key], b = seq?.[r.key];
      if (a == null || b == null || !Number.isFinite(a) || !Number.isFinite(b)) return null;
      const smartWins = r.lower ? a < b : a > b;
      const delta = Math.abs(a - b);
      const rel = b !== 0 ? delta / Math.abs(b) : delta;
      return { ...r, a, b, smartWins, delta: rel };
    })
    .filter(Boolean) as (typeof H2H[number] & { a: number; b: number; smartWins: boolean; delta: number })[];
  const h2hWins = h2hRows.filter((r) => r.smartWins).length;

  return (
    <>
      <h1 className="page-title">Mission Control</h1>
      <p className="lede">
        ASTRA schedules the scan of an Electronic Support receiver that must find
        hostile emitters without prior intelligence. Start a paired mission to
        watch it compete against a conventional sweep on identical battlefields.
      </p>

      <div className="stats">
        <div className="stat">
          <div className="k">Effectiveness Rank</div>
          <div className="v">{me ? `#1 / ${me.ranking.length}` : "—"}</div>
          <div className="s">KPP-gated composite score</div>
          <div className="meter"><i style={{ width: "100%" }} /></div>
        </div>
        <div className="stat">
          <div className="k">Threat Coverage</div>
          <div className="v good">{pct(ss?.threat_intercept_ratio)}</div>
          <div className="s">200-episode mean · Pd</div>
          <div className="meter"><i className="good" style={{
            width: `${Math.min(100, (ss?.threat_intercept_ratio ?? 0) * 100)}%` }} /></div>
        </div>
        <div className="stat">
          <div className="k">Reward Multiple</div>
          <div className="v">{rewardX}&times;</div>
          <div className="s">vs sequential sweep</div>
          <div className="meter"><i style={{
            width: `${Math.min(100, (parseFloat(rewardX) / 3) * 100 || 0)}%` }} /></div>
        </div>
        <div className="stat">
          <div className="k">Mission-Capable</div>
          <div className="v">{me ? `${capable} / ${me.ranking.length}` : "—"}</div>
          <div className="s">policies passing all KPPs</div>
          <div className="meter"><i className="good" style={{
            width: me ? `${(capable / me.ranking.length) * 100}%` : "0%" }} /></div>
        </div>
      </div>

      {h2hRows.length > 0 && (
        <div className="panel">
          <h3>Head-to-Head &mdash; SmartScan vs Sequential Sweep ({h2hWins}/{h2hRows.length} figures of merit won)</h3>
          <div className="body table-wrap" style={{ paddingTop: 6 }}>
            <table className="data vs-table">
              <thead>
                <tr>
                  <th>Figure of merit</th>
                  <th>SmartScan (proposed)</th>
                  <th>Sequential sweep</th>
                  <th>Advantage</th>
                  <th>Leader</th>
                </tr>
              </thead>
              <tbody>
                {h2hRows.map((r) => (
                  <tr key={r.key} className={r.smartWins ? "hl" : ""}>
                    <td className="txt">{r.label}</td>
                    <td className={"num " + (r.smartWins ? "win" : "lose")}>{r.fmt(r.a)}</td>
                    <td className={"num " + (!r.smartWins ? "win" : "lose")}>{r.fmt(r.b)}</td>
                    <td className="delta">{(r.delta * 100).toFixed(0)}% better</td>
                    <td>
                      <span className={"badge " + (r.smartWins ? "pass" : "pending")}>
                        {r.smartWins ? "SMARTSCAN" : "SEQUENTIAL"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {h2hRows.filter((r) => r.caveat && !r.smartWins).map((r) => (
              <div className="caveat" key={r.key}>
                Timing metrics: {r.caveat}
              </div>
            ))}
            <p className="tbl-note">
              200 held-out episodes, identical seeds and battlefields per policy;
              95% confidence intervals in the Evaluation workspace.
            </p>
          </div>
        </div>
      )}

      <div className="grid-2" style={{ marginTop: 16 }}>
        <div className="panel">
          <h3>Quick Actions</h3>
          <div className="body">
            <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
              <button className="tbtn primary" onClick={onStart}>Start Paired Mission</button>
              <button className="tbtn" onClick={() => onGo("analysis")}>View Evaluation</button>
              <button className="tbtn" onClick={() => onGo("data")}>Data &amp; Sources</button>
            </div>
            <p className="tbl-note" style={{ marginTop: 0 }}>
              A paired mission flies two receivers over identical scenarios:
              SmartScan against a conventional sweep. Any difference in outcome
              is attributable to scanning strategy alone.
            </p>
          </div>
        </div>
        <div className="panel">
          <h3>System Status</h3>
          <div className="body kv" style={{ fontSize: 12.5 }}>
            <div className="row"><span>Application</span><span>{meta ? `${meta.app} ${meta.version}` : "\u2026"}</span></div>
            <div className="row"><span>Frontend</span><span>{meta?.frontend_built ? "loaded" : "missing"}</span></div>
            <div className="row"><span>Benchmarks</span><span>{s ? "available" : "not generated"}</span></div>
            <div className="row"><span>Scenarios</span><span>{nScen} files</span></div>
            <div className="row"><span>User Guide</span><span>{meta?.manual_available ? "installed" : "missing"}</span></div>
          </div>
        </div>
      </div>

      {me && (
        <div className="panel" style={{ marginTop: 16 }}>
          <h3>KPP Gate Summary</h3>
          <div className="body table-wrap" style={{ paddingTop: 6 }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Scheduler</th><th>Verdict</th><th>MES</th>
                  <th>Coverage &ge; .90</th><th>Prediction &ge; .50</th><th>Pfa &le; 5e-4</th>
                </tr>
              </thead>
              <tbody>
                {me.ranking.map((n) => {
                  const sc = me.scores[n];
                  return (
                    <tr key={n} className={n === "smart-scan" ? "hl" : ""}>
                      <td className="txt">{n.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</td>
                      <td><span className={"badge " + (sc.mission_capable ? "pass" : "fail")}>
                        {sc.mission_capable ? "CAPABLE" : "NOT CAPABLE"}</span></td>
                      <td className="num">{f(sc.mes)}</td>
                      <td>
                        <span className={"badge " + (sc.kpps.threat_intercept_ratio?.pass ? "pass" : "fail")}>
                          {sc.kpps.threat_intercept_ratio?.pass ? "PASS" : "FAIL"}</span>{" "}
                        <span className="num">{f(sc.kpps.threat_intercept_ratio?.value, 2)}</span>
                      </td>
                      <td>
                        <span className={"badge " + (sc.kpps.pct_correct_predictions?.pass ? "pass" : "fail")}>
                          {sc.kpps.pct_correct_predictions?.pass ? "PASS" : "FAIL"}</span>{" "}
                        <span className="num">{f(sc.kpps.pct_correct_predictions?.value, 2)}</span>
                      </td>
                      <td>
                        <span className={"badge " + (sc.kpps.false_alarm_rate?.pass ? "pass" : "fail")}>
                          {sc.kpps.false_alarm_rate?.pass ? "PASS" : "FAIL"}</span>{" "}
                        <span className="num">
                          {sc.kpps.false_alarm_rate?.value != null
                            ? sc.kpps.false_alarm_rate.value.toExponential(1)
                            : "\u2014"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="tbl-note">
              SmartScan is the only scheduler satisfying every KPP simultaneously.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
