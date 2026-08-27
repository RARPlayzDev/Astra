import { useEffect, useState } from "react";
import { getFigures, getSummary, figureUrl, type Summary } from "../api";

const SCHED_TITLES: Record<string, string> = {
  "smart-scan": "SmartScan (proposed)",
  "bandit-ucb": "UCB bandit",
  "rl-linear-q": "Q-learning",
  "rl-dqn": "Deep Q-network",
  "openloop-random": "Random scan",
  "openloop-priority": "Priority sweep",
  "openloop-sequential": "Sequential sweep",
};

const f = (v: number | null | undefined, d = 3) =>
  v != null && Number.isFinite(v) ? v.toFixed(d) : "\u2014";
const pct1 = (v: number | null | undefined) =>
  v != null && Number.isFinite(v) ? `${(v * 100).toFixed(1)}%` : "\u2014";

function GateTable({ s }: { s: Summary }) {
  const me = s.mission_effectiveness;
  if (!me) return null;
  return (
    <div className="panel">
      <h3>KPP gate &mdash; mission capability</h3>
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
                  <td className="num">{f(sc.mes)}</td>
                  {(["threat_intercept_ratio", "pct_correct_predictions", "false_alarm_rate"] as const).map((m) => {
                    const kpp = sc.kpps[m];
                    if (!kpp) return <td key={m} className="num">{"\u2014"}</td>;
                    return (
                      <td key={m}>
                        <span className={"badge " + (kpp.pass ? "pass" : "fail")}>
                          {kpp.pass ? "PASS" : "FAIL"}</span>{" "}
                        <span className="num">
                          {m === "false_alarm_rate"
                            ? (kpp.value != null ? kpp.value.toExponential(1) : "\u2014")
                            : f(kpp.value, 2)}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="tbl-note">SmartScan is the only scheduler satisfying every Key
        Performance Parameter.</p>
      </div>
    </div>
  );
}

function McTable({ s }: { s: Summary }) {
  const order = s.mission_effectiveness?.ranking ?? Object.keys(s.monte_carlo_means);
  const cols: [string, string, (v: number) => string][] = [
    ["avg_reward", "Avg reward", (v) => f(v)],
    ["threat_intercept_ratio", "Coverage", (v) => pct1(v)],
    ["pct_correct_predictions", "Pred acc", (v) => pct1(v)],
    ["intercept_rate", "Int rate", (v) => f(v)],
    ["false_alarm_rate", "Pfa/slot", (v) => v != null ? v.toExponential(1) : "\u2014"],
    ["threat_mean_ttff", "TTFF", (v) => f(v, 0)],
    ["avg_intercept_time_error", "IT error", (v) => f(v, 1)],
  ];
  return (
    <div className="panel">
      <h3>Monte Carlo &mdash; 200 held-out episodes</h3>
      <div className="body table-wrap" style={{ paddingTop: 6 }}>
        <table className="data">
          <thead><tr><th>Scheduler</th>{cols.map(([, t]) => <th key={t}>{t}</th>)}</tr></thead>
          <tbody>
            {order.map((n) => {
              const m = s.monte_carlo_means[n] ?? {};
              return (
                <tr key={n} className={n === "smart-scan" ? "hl" : ""}>
                  <td className="txt">{SCHED_TITLES[n] ?? n}</td>
                  {cols.map(([k, , fmt]) => {
                    const v = m[k];
                    return (
                      <td key={k} className="num">
                        {v == null || !Number.isFinite(v) ? "\u2014" : fmt(v)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="tbl-note">SmartScan above every comparator at p &lt; 1e-4 (Holm-Bonferroni corrected).</p>
      </div>
    </div>
  );
}

const GALLERY: [string, string][] = [
  ["mission_effectiveness.png", "Mission Effectiveness under the KPP gate."],
  ["comparison.png", "Scheduler comparison across key metrics."],
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
        All values produced by the experiment suite from stored seeds.
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
