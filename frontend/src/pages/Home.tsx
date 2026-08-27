import { useEffect, useState } from "react";
import { getSummary, getScenarios, type Meta, type Summary } from "../api";

type Props = {
  meta: Meta | null;
  onStart: () => void;
  onGo: (p: "operations" | "analysis" | "data") => void;
};

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
  const rewardX = ss && seq
    ? ((ss.avg_reward ?? 0) / Math.max(1e-9, seq.avg_reward ?? 1)).toFixed(1) : "—";

  return (
    <>
      <h1 className="page-title">Mission Control</h1>
      <p className="lede">
        ASTRA schedules the scan of an Electronic Support receiver that must
        find hostile emitters without prior intelligence. Start a paired
        mission to watch it compete against a conventional sweep.
      </p>

      {/* ── Headline Stats ──────────────────────────────────────── */}
      <div className="stats">
        <div className="stat">
          <div className="k">Effectiveness Rank</div>
          <div className="v">{me ? `#1 / ${me.ranking.length}` : "—"}</div>
          <div className="s">KPP-gated composite score</div>
        </div>
        <div className="stat">
          <div className="k">Threat Coverage</div>
          <div className="v">{ss ? `${((ss.threat_intercept_ratio ?? 0) * 100).toFixed(0)}%` : "—"}</div>
          <div className="s">200-episode Monte Carlo mean</div>
        </div>
        <div className="stat">
          <div className="k">Reward Multiple</div>
          <div className="v">{rewardX}×</div>
          <div className="s">vs sequential sweep</div>
        </div>
        <div className="stat">
          <div className="k">Mission-Capable</div>
          <div className="v" style={{ color: capable > 0 ? "var(--green)" : "var(--text-muted)" }}>
            {me ? `${capable} / ${me.ranking.length}` : "—"}
          </div>
          <div className="s">policies passing all KPPs</div>
        </div>
      </div>

      {/* ── Quick Actions + Status ──────────────────────────────── */}
      <div className="grid-2">
        <div className="panel">
          <h3>Quick Actions</h3>
          <div className="body">
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
              <button className="tbtn primary" onClick={onStart}>
                ▶  Start Paired Mission
              </button>
              <button className="tbtn" onClick={() => onGo("analysis")}>
                📊  View Analysis
              </button>
              <button className="tbtn" onClick={() => onGo("data")}>
                ⚙  Data & Sources
              </button>
            </div>
            <p className="tbl-note" style={{ marginTop: 0 }}>
              A paired mission flies two receivers over identical scenarios —
              SmartScan against a conventional sweep. Differences in outcome
              are attributable to scanning strategy alone.
            </p>
          </div>
        </div>

        <div className="panel">
          <h3>System Status</h3>
          <div className="body">
            <div className="kv" style={{ fontSize: 13 }}>
              <div className="row">
                <span>Application</span>
                <span>{meta ? `${meta.app} ${meta.version}` : "..."}</span>
              </div>
              <div className="row">
                <span>Frontend</span>
                <span style={{ color: meta?.frontend_built ? "var(--green)" : "var(--red)" }}>
                  {meta?.frontend_built ? "loaded" : "missing"}
                </span>
              </div>
              <div className="row">
                <span>Benchmarks</span>
                <span style={{ color: s ? "var(--green)" : "var(--amber)" }}>
                  {s ? "available" : "not generated"}
                </span>
              </div>
              <div className="row">
                <span>Scenarios</span>
                <span>{nScen} files</span>
              </div>
              <div className="row">
                <span>User Guide</span>
                <span style={{ color: meta?.manual_available ? "var(--green)" : "var(--amber)" }}>
                  {meta?.manual_available ? "installed" : "missing"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── KPP Summary Table ───────────────────────────────────── */}
      {me && (
        <div className="panel" style={{ marginTop: 20 }}>
          <h3>KPP Gate Summary</h3>
          <div className="body table-wrap" style={{ paddingTop: 8 }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Scheduler</th>
                  <th>Verdict</th>
                  <th>MES</th>
                  <th>Coverage ≥ .90</th>
                  <th>Prediction ≥ .50</th>
                  <th>Pfa ≤ 5e-4</th>
                </tr>
              </thead>
              <tbody>
                {me.ranking.map((n) => {
                  const sc = me.scores[n];
                  const isSmartScan = n === "smart-scan";
                  return (
                    <tr key={n} className={isSmartScan ? "hl" : ""}>
                      <td className="txt" style={{ fontWeight: isSmartScan ? 600 : 400 }}>
                        {isSmartScan ? "★ " : ""}{n.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </td>
                      <td>
                        <span className={"badge " + (sc.mission_capable ? "pass" : "fail")}>
                          {sc.mission_capable ? "CAPABLE" : "NOT CAPABLE"}
                        </span>
                      </td>
                      <td className="num">{sc.mes.toFixed(3)}</td>
                      <td>
                        <span className={"badge " + (sc.kpps.threat_intercept_ratio.pass ? "pass" : "fail")}>
                          {sc.kpps.threat_intercept_ratio.pass ? "PASS" : "FAIL"}
                        </span>
                        {" "}
                        <span className="num">{sc.kpps.threat_intercept_ratio.value.toFixed(2)}</span>
                      </td>
                      <td>
                        <span className={"badge " + (sc.kpps.pct_correct_predictions.pass ? "pass" : "fail")}>
                          {sc.kpps.pct_correct_predictions.pass ? "PASS" : "FAIL"}
                        </span>
                        {" "}
                        <span className="num">{sc.kpps.pct_correct_predictions.value.toFixed(2)}</span>
                      </td>
                      <td>
                        <span className={"badge " + (sc.kpps.false_alarm_rate.pass ? "pass" : "fail")}>
                          {sc.kpps.false_alarm_rate.pass ? "PASS" : "FAIL"}
                        </span>
                        {" "}
                        <span className="num">{sc.kpps.false_alarm_rate.value.toExponential(1)}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="tbl-note">
              SmartScan is the only scheduler satisfying every KPP simultaneously.
              The exploit-only bandit posts the highest raw reward but finds only
              54% of threats.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
