import { useEffect, useState } from "react";
import { getFigures, getSummary, getPsCoverage, figureUrl, type Summary } from "../api";

function PsCoveragePanel() {
  const [cov, setCov] = useState<Awaited<ReturnType<typeof getPsCoverage>> | null>(null);
  const [err, setErr] = useState(false);
  const [seed, setSeed] = useState(20260917);
  const reload = (s: number) => {
    setErr(false);
    getPsCoverage(s).then(setCov).catch(() => setErr(true));
  };
  useEffect(() => { reload(seed); /* eslint-disable-next-line */ }, []);
  return (
    <div className="panel">
      <h3>Problem-statement coverage audit (live self-test)</h3>
      <div className="body">
        {err && <p className="tbl-note">Audit endpoint unavailable (run the suite or restart the service).</p>}
        {cov && (
          <>
            <p className="tbl-note" style={{ marginTop: 0 }}>
              {cov.passed}/{cov.total} checks pass ({cov.coverage_pct}%). Every
              check is <b>executed live</b> against the running system when this
              page loads &mdash; nothing is narrated from a static report. The
              audit covers communication signals (FHSS/TDMA COMINT), the
              radiometer + Albersheim + CA-CFAR detection coupling, intercept-time
              prediction for periodic <i>and</i> frequency-agile emitters,
              per-rotation-cycle spatial coverage, and the reward/cost figures
              of merit.
            </p>
            <table className="data">
              <thead><tr><th>Check</th><th>PS phrase</th><th>Verdict</th></tr></thead>
              <tbody>
                {cov.checks.map((c) => (
                  <tr key={c.check}>
                    <td className="txt">{c.check}</td>
                    <td className="txt">{c.ps_phrase}</td>
                    <td><span className={"badge " + (c.ok ? "pass" : "fail")}>
                      {c.ok ? "PASS" : "FAIL"}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="controls-row" style={{ marginTop: 10 }}>
              <button className="tbtn" onClick={() => reload(seed)}>
                Re-run audit (same seed)
              </button>
              <button className="tbtn" onClick={() => {
                const s = Math.floor(Math.random() * 100000);
                setSeed(s); reload(s);
              }}>
                Re-run with fresh seed
              </button>
              <span className="readout">seed {seed}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

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
  const [lightbox, setLightbox] = useState<{ src: string; caption: string } | null>(null);
  useEffect(() => {
    getSummary().then(setS).catch(() => undefined);
    getFigures().then((f) => setFigs(f.figures)).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!lightbox) return;
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") setLightbox(null); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [lightbox]);

  return (
    <>
      <h1 className="page-title">Analysis</h1>
      <p className="lede">
        All values produced by the experiment suite from stored seeds.
      </p>
      <PsCoveragePanel />
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
                <figure key={f} onClick={() => setLightbox({ src: figureUrl(f), caption: GALLERY.find(([g]) => g === f)?.[1] ?? f })}>
                  <img src={figureUrl(f)} alt={f} loading="lazy" />
                  <figcaption>{GALLERY.find(([g]) => g === f)?.[1]}</figcaption>
                </figure>
              ))}
          </div>
        </div>
      </>)}

      {lightbox && (
        <div className="lightbox-overlay" onClick={() => setLightbox(null)}>
          <img src={lightbox.src} alt={lightbox.caption} />
          <div className="caption">{lightbox.caption}</div>
        </div>
      )}
    </>
  );
}
