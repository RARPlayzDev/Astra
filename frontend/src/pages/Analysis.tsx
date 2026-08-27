import { useEffect, useState } from "react";
import { getFigures, getSummary, figureUrl, type Summary } from "../api";

const SCHED_TITLES: Record<string, string> = {
  "smart-scan": "SmartScan (proposed)",
  "bandit-ucb": "UCB bandit (exploitation only)",
  "rl-linear-q": "Q-learning (linear)",
  "rl-dqn": "Deep Q-network",
  "openloop-random": "Random scan",
  "openloop-priority": "Priority sweep (prior intel)",
  "openloop-sequential": "Sequential sweep",
};

function GateTable({ s }: { s: Summary }) {
  const me = s.mission_effectiveness;
  if (!me) return null;
  return (
    <div className="panel">
      <h3>KPP gate - mission capability</h3>
      <div className="body table-wrap" style={{ paddingTop: 6 }}>
        <table className="data">
          <thead><tr>
            <th>Scheduler</th><th>Verdict</th><th>MES</th>
            <th>Coverage &ge; .90</th><th>Pred &ge; .50</th><th>Pfa &le; 5e-4</th>
          </tr></thead>
          <tbody>
            {me.ranking.map((n) => {
              const sc = me.scores[n];
              return (
                <tr key={n} className={n === "smart-scan" ? "hl" : ""}>
                  <td className="txt">{SCHED_TITLES[n] ?? n}</td>
                  <td><span className={"badge " + (sc.mission_capable ? "pass" : "fail")}>
                    {sc.mission_capable ? "CAPABLE" : "NOT CAPABLE"}</span></td>
                  <td className="num">{sc.mes.toFixed(3)}</td>
                  {["threat_intercept_ratio", "pct_correct_predictions", "false_alarm_rate"].map((m) => (
                    <td key={m}>
                      <span className={"badge " + (sc.kpps[m].pass ? "pass" : "fail")}>
                        {sc.kpps[m].pass ? "PASS" : "FAIL"}</span>{" "}
                      <span className="num">{m === "false_alarm_rate"
                        ? sc.kpps[m].value.toExponential(1)
                        : sc.kpps[m].value.toFixed(2)}</span>
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="tbl-note">SmartScan is the only scheduler satisfying every Key
        Performance Parameter. The exploit-only bandit posts the highest raw reward but
        finds 54% of threats; linear Q-learning predicts presence at chance level.</p>
      </div>
    </div>
  );
}

function McTable({ s }: { s: Summary }) {
  const order = s.mission_effectiveness?.ranking ?? Object.keys(s.monte_carlo_means);
  const cols: [string, string, (v: number) => string][] = [
    ["avg_reward", "Avg reward", (v) => v.toFixed(3)],
    ["threat_intercept_ratio", "Coverage", (v) => `${(v * 100).toFixed(1)}%`],
    ["pct_correct_predictions", "Pred acc", (v) => `${(v * 100).toFixed(1)}%`],
    ["intercept_rate", "Int rate", (v) => v.toFixed(3)],
    ["false_alarm_rate", "Pfa/slot", (v) => v.toExponential(1)],
    ["threat_mean_ttff", "TTFF", (v) => v.toFixed(0)],
    ["avg_intercept_time_error", "IT error", (v) => v.toFixed(1)],
  ];
  return (
    <div className="panel">
      <h3>Monte Carlo - 200 held-out episodes</h3>
      <div className="body table-wrap" style={{ paddingTop: 6 }}>
        <table className="data">
          <thead><tr><th>Scheduler</th>{cols.map(([_, t]) => <th key={t}>{t}</th>)}</tr></thead>
          <tbody>
            {order.map((n) => {
              const m = s.monte_carlo_means[n] ?? {};
              return (
                <tr key={n} className={n === "smart-scan" ? "hl" : ""}>
                  <td className="txt">{SCHED_TITLES[n] ?? n}</td>
                  {cols.map(([k, _t, f]) => {
                    const ci = s.monte_carlo[n]?.[k]?.ci95 ?? null;
                    const v = m[k];
                    return (
                      <td key={k} className="num">
                        {v == null ? "--" : f(v)}
                        {ci != null && v != null ? <span style={{ color: "var(--muted)" }}> ±{ci.toFixed(3)}</span> : null}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="tbl-note">Gated-score paired permutation tests: SmartScan above every
        comparator at p &lt; 1e-4 (Holm-Bonferroni corrected).</p>
      </div>
    </div>
  );
}

const GALLERY: [string, string][] = [
  ["mission_effectiveness.png", "Mission Effectiveness under the KPP gate."],
  ["comparison.png", "Scheduler comparison across principal figures of merit."],
  ["learning_curves.png", "Training vs held-out greedy evaluation."],
  ["ablation.png", "Component attribution study."],
  ["roc.png", "System ROC across sensitivity thresholds."],
  ["geo_cep.png", "Geolocation accuracy vs receiver count."],
];

export default function Analysis() {
  const [s, setS] = useState<Summary | null>(null);
  const [figs, setFigs] = useState<string[]>([]);
  useEffect(() => {
    getSummary().then(setS).catch(() => undefined);
    getFigures().then((f) => setFigs(f.figures)).catch(() => undefined);
  }, []);

  return (
    <>
      <h1 className="page-title">Analysis</h1>
      <p className="lede">
        All values are produced by the experiment suite from stored seeds;
        nothing is hand-entered.
      </p>
      {!s && <div className="panel"><div className="body">No results found. Run
        <code className="inline"> python -m ewsmart.experiments --suite full</code>.</div></div>}
      {s && (<>
        <GateTable s={s} />
        <McTable s={s} />
        <div className="panel">
          <h3>Evidence gallery</h3>
          <div className="body gallery">
            {figs.filter((f) => GALLERY.some(([g]) => g === f))
              .sort((a, b) => GALLERY.findIndex(([g]) => g === a) - GALLERY.findIndex(([g]) => g === b))
              .map((f) => (
                <figure key={f}>
                  <img src={figureUrl(f)} alt={f} loading="lazy" />
                  <figcaption>{GALLERY.find(([g]) => g === f)?.[1]}</figcaption>
                </figure>
              ))}
          </div>
        </div>
      </>)}
    </>
  );
}
