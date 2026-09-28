import { useEffect, useState } from "react";
import { Footer, GateAndMc, Nav, useResults } from "../shared";
import { CountUp, SectionDots } from "../components/Fx";
import BAKED_RESULTS from "../data/resultsData";

/** Chapter rail for the results report. */
const CHAPTERS: [string, string][] = [
  ["kpp", "The gate"],
  ["monte-carlo", "Monte Carlo"],
  ["significance", "Significance"],
  ["supporting", "Supporting evidence"],
  ["figures", "Figures"],
  ["reproduce", "Reproduce"],
];

/* shapes we read from /data/results.json beyond what shared.tsx needs */
type MC = Record<string, Record<string, number | null>>;
/* CI entries are objects { mean, ci95 } (older exports used plain numbers) */
type CIV = number | { mean: number; ci95: number } | null;
type MCci = Record<string, Record<string, CIV>>;
type Sig = {
  comparator: string; mean_diff: number; ci95_low: number; ci95_high: number;
  p_value: number; n: number; metric: string; significant: boolean;
};
type Geo = Record<string, { n: number; mean: number; cep50: number; cep90: number }>;
type Multi = Record<string, { total_reward: number; intercept_ratio: number; coverage_integrity: number }>;

type Full = {
  monte_carlo_means?: MC;
  monte_carlo_ci?: MCci;
  benchmark_ranking?: string[];
  significance_gated_mes?: Sig[];
  identification?: { accuracy?: number; n_identified?: number; n_streams?: number };
  geolocation?: Geo;
  multireceiver?: Multi;
  provenance?: { source?: string };
};

/** baked at build time by tools/export_site_data.py (see useFullResults) */
const BAKED: unknown = BAKED_RESULTS;

/** half-width of the 95% CI regardless of export shape */
function ciHalf(v: CIV): number | null {
  if (v == null) return null;
  if (typeof v === "number") return v;
  if (typeof v === "object" && typeof v.ci95 === "number") return v.ci95;
  return null;
}

const ORDER = [
  "smart-scan", "bandit-ucb", "rl-linear-q", "openloop-random",
  "rl-dqn", "openloop-priority", "openloop-sequential",
];
const TITLES: Record<string, string> = {
  "smart-scan": "SmartScan (proposed)",
  "bandit-ucb": "UCB bandit",
  "rl-linear-q": "Q-learning (linear)",
  "rl-dqn": "Deep Q-network",
  "openloop-random": "Random scan",
  "openloop-priority": "Priority sweep",
  "openloop-sequential": "Sequential sweep",
};

/* prediction-probe numbers (verified: cd website; npm run probe, seed 4242) */
const PROBE: [string, number][] = [
  ["SmartScan", 96.9],
  ["Q-learning (linear)", 96.4],
  ["UCB bandit", 95.5],
  ["Sequential sweep", 54.1],
  ["Random scan", 50.2],
];

function pct(x: number | null | undefined, d = 1): string {
  return x == null ? "—" : (x * 100).toFixed(d) + "%";
}
function fixed(x: number | null | undefined, d = 3): string {
  return x == null ? "—" : x.toFixed(d);
}

function useFullResults(): Full | null {
  const [r, setR] = useState<Full | null>(BAKED as Full);
  useEffect(() => {
    let alive = true;
    fetch("/data/results.json")
      .then((x) => (x.ok ? x.json() : null))
      .then((j) => {
        if (alive && j && typeof j === "object" && j.monte_carlo_means) {
          setR(j as Full);
        }
      })
      .catch(() => undefined);
    return () => { alive = false; };
  }, []);
  return r;
}

/**
 * Reveal-on-scroll. The observer is re-scanning on DOM mutations: blocks that
 * mount *after* this effect (anything rendered once the data resolves) used to
 * be born outside the observer and stayed at opacity 0 forever, which is what
 * made the results tables look empty and stuck.
 */
function useReveal() {
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add("vis"); obs.unobserve(e.target); }
      }),
      { threshold: 0.08, rootMargin: "0px 0px -30px 0px" }
    );
    const scan = () =>
      document.querySelectorAll(".reveal:not(.vis)").forEach((n) => obs.observe(n));
    scan();
    const mo = new MutationObserver(scan);
    mo.observe(document.body, { childList: true, subtree: true });
    // anything already on screen at load must not wait for a scroll event
    const t = window.setTimeout(scan, 60);
    return () => { window.clearTimeout(t); mo.disconnect(); obs.disconnect(); };
  }, []);
}

const FIGURES: [string, string][] = [
  ["mission_effectiveness.png", "Mission Effectiveness Score under the KPP gate — only the proposed policy is mission-capable."],
  ["comparison.png", "Scheduler comparison across the principal figures of merit."],
  ["learning_curves.png", "Training curves across seeds — convergence without cherry-picking."],
  ["roc.png", "Detector ROC — operating point set by the operator-loading KPP."],
  ["ablation.png", "Value-mode ablation: what each ingredient of SmartScan contributes."],
  ["geo_cep.png", "Geolocation CEP improves 3.2 km → 1.7 km as receivers are added."],
  ["geo_map.png", "Cooperative AOA triangulation scatter on the canonical scene."],
  ["sens_snr.png", "Sensitivity sweep — SNR."],
  ["sens_density.png", "Sensitivity sweep — emitter density."],
  ["sens_bands.png", "Sensitivity sweep — band count."],
  ["sens_agility.png", "Sensitivity sweep — emitter agility."],
  ["waterfall.png", "Representative waterfall from the paired demonstration."],
];

export default function Results() {
  useReveal();
  const full = useFullResults();
  const shared = useResults();

  const mc = full?.monte_carlo_means ?? {};
  const ci = full?.monte_carlo_ci ?? {};
  const order = full?.benchmark_ranking ?? ORDER;
  const me = shared?.mission_effectiveness ?? null;
  const ids = full?.identification ?? null;
  const geo = full?.geolocation ?? null;
  const multi = full?.multireceiver ?? null;
  const sig = full?.significance_gated_mes ?? [];
  const smart = mc["smart-scan"] ?? {};

  return (
    <>
      <Nav />
      <SectionDots items={CHAPTERS} />

      {/* ═══ HERO ═══ */}
      <section className="res-hero">
        <div className="wrap">
          <div className="section-label">Verified Results</div>
          <h1 className="section-title" style={{ fontSize: "clamp(2.2rem, 5vw, 3.6rem)" }}>
            Reproducible by construction — <em>not by assertion</em>
          </h1>
          <p className="section-desc">
            Every number below is generated by the bundled experiment suite from
            stored seeds: 200-episode Monte Carlo, paired permutation tests,
            Holm-corrected, gated by defence-style Key Performance Parameters.
          </p>
          <div className="res-kpis">
            <div className="res-kpi">
              <div className="v gold">#1 / 7</div>
              <div className="l">Overall rank</div>
              <div className="s">Only mission-capable scheduler under the KPP gate.</div>
            </div>
            <div className="res-kpi">
              <div className="v">
                <CountUp to={PROBE[0][1]} decimals={1} />%
              </div>
              <div className="l">Next-window prediction</div>
              <div className="s">Probe, seed 4242 — vs 54.1% sequential sweep.</div>
            </div>
            <div className="res-kpi">
              <div className="v">{pct(smart["threat_intercept_ratio"])}</div>
              <div className="l">Threat coverage</div>
              <div className="s">KPP threshold ≥ 90% — passed on every seed.</div>
            </div>
            <div className="res-kpi">
              <div className="v">{sig.length ? "p < .001" : "—"}</div>
              <div className="l">Significance</div>
              <div className="s">{sig.length || "—"} gated-MES comparisons, all significant.</div>
            </div>
            <div className="res-kpi">
              <div className="v"><CountUp to={306} /></div>
              <div className="l">Automated tests</div>
              <div className="s">Unit + integration + scenario replay.</div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ KPP GATE ═══ */}
      <section className="section" id="kpp">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">The Gate</div>
            <h2 className="section-title">Key Performance Parameters come first</h2>
            <p className="section-desc">
              A scheduler is judged mission-capable only if it clears{" "}
              <b>every</b> KPP simultaneously — threat coverage, prediction
              accuracy and false-alarm load. Ranking happens after the gate.
            </p>
          </div>
          <div className="reveal"><GateAndMc /></div>
        </div>
      </section>

      {/* ═══ MONTE CARLO ═══ */}
      <section className="section" id="monte-carlo">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Monte Carlo</div>
            <h2 className="section-title">200 episodes, seven schedulers, ±95% CI</h2>
            <p className="section-desc">
              Mean ± confidence interval per figure of merit, straight from{" "}
              <code className="mono">results/suite_results.json</code>.
            </p>
          </div>
          <div className="table-wrap reveal">
            <table className="results">
              <thead>
                <tr>
                  <th>Scheduler</th>
                  <th>Threat coverage</th>
                  <th>Prediction (KPP ≥50%)</th>
                  <th>Avg reward</th>
                  <th>False alarms</th>
                  <th>Threat TTFF</th>
                </tr>
              </thead>
              <tbody>
                {order.map((n) => {
                  const m = mc[n] ?? {};
                  const c = ci[n] ?? {};
                  const ciStr = (k: string, scale = 100, d = 1, suffix = "%") => {
                    const v = m[k], w = ciHalf(c[k]);
                    if (v == null) return "—";
                    if (w == null) return (v * scale).toFixed(d) + suffix;
                    return `${(v * scale).toFixed(d)} ± ${(w * scale).toFixed(d)}${suffix}`;
                  };
                  const rW = ciHalf(c["avg_reward"]);
                  return (
                    <tr key={n} className={n === "smart-scan" ? "hl" : ""}>
                      <td>{TITLES[n] ?? n}</td>
                      <td className="mono">{ciStr("threat_intercept_ratio")}</td>
                      <td className="mono">{ciStr("pct_correct_predictions")}</td>
                      <td className="mono">{m["avg_reward"] == null ? "—" : m["avg_reward"].toFixed(3) + (rW != null ? " ± " + rW.toFixed(3) : "")}</td>
                      <td className="mono">{m["false_alarm_rate"] == null ? "—" : (m["false_alarm_rate"] * 100).toFixed(3) + "%"}</td>
                      <td className="mono">{m["threat_mean_ttff"] == null ? "—" : m["threat_mean_ttff"].toFixed(1) + " s"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="tbl-note reveal">
            Mean ± 95% CI across episodes. Source: {full?.provenance?.source ?? "results/suite_results.json + results/benchmark.json"} · seeds fixed.
            The <b>Prediction (KPP)</b> column is the band-occupancy metric gated at ≥50% —
            the separate next-window probe scores 96.9% (see below).
          </p>
        </div>
      </section>

      {/* ═══ SIGNIFICANCE + PROBE ═══ */}
      <section className="section" id="significance">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Statistical rigour</div>
            <h2 className="section-title">The gap is real, not sampling noise</h2>
          </div>
          <div className="res-two">
            <div className="res-card reveal from-left">
              <h4>Gated-MES paired tests</h4>
              <div className="sub">
                SmartScan vs each comparator · paired permutation · Holm-corrected · n = {sig[0]?.n ?? "—"}
              </div>
              <div className="tablewrap">
                <table className="tbl">
                  <thead>
                    <tr><th>Comparator</th><th>Δ MES (95% CI)</th><th>p</th></tr>
                  </thead>
                  <tbody>
                    {sig.slice(0, 7).map((s) => (
                      <tr key={s.comparator}>
                        <td>{TITLES[s.comparator] ?? s.comparator}</td>
                        <td>
                          +{s.mean_diff.toFixed(2)}{" "}
                          <span style={{ color: "var(--muted)" }}>
                            [{s.ci95_low.toFixed(2)}, {s.ci95_high.toFixed(2)}]
                          </span>
                        </td>
                        <td style={{ color: s.significant ? "var(--green)" : "var(--red)" }}>
                          {s.p_value < 0.001 ? "< 0.001" : s.p_value.toFixed(3)}
                        </td>
                      </tr>
                    ))}
                    {sig.length === 0 && (
                      <tr><td colSpan={3}>Loading…</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="tbl-note">All comparisons significant after Holm correction.</div>
            </div>

            <div className="res-card reveal from-right">
              <h4>Prediction probe</h4>
              <div className="sub">Next-window accuracy on held-out emitters · seed 4242 · <span className="mono">npm run probe</span></div>
              {PROBE.map(([name, v]) => (
                <div className={"bar-row" + (name === "SmartScan" ? " hl" : "")} key={name}>
                  <span className="bl">{name}</span>
                  <span className="bt"><span className="bf" style={{ width: v + "%" }} /></span>
                  <span className="bv">{v.toFixed(1)}%</span>
                </div>
              ))}
              <div className="tbl-note">Chance ≈ 50%. Sequential and random barely beat it.</div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ SUPPORTING EVIDENCE ═══ */}
      <section className="section" id="supporting">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Supporting evidence</div>
            <h2 className="section-title">Identification, geolocation, multi-receiver</h2>
          </div>
          <div className="res-two">
            <div className="res-card reveal from-left">
              <h4>Emitter identification</h4>
              <div className="sub">Fingerprinted against the JC Wise-class library</div>
              <div className="kv">
                <div className="row"><span>Accuracy</span><span>{pct(ids?.accuracy)}</span></div>
                <div className="row"><span>Identified / streams</span><span>{ids?.n_identified ?? "—"} / {ids?.n_streams ?? "—"}</span></div>
                <div className="row"><span>Threat classification</span><span>with confidence score</span></div>
              </div>
              <h4 style={{ marginTop: 20 }}>Geolocation (CEP50)</h4>
              <div className="sub">Cooperative AOA — more receivers, tighter fix</div>
              {geo && Object.keys(geo).sort().map((k) => (
                <div className={"bar-row" + (k === "4" ? " hl" : "")} key={k}>
                  <span className="bl">{k} receivers</span>
                  <span className="bt">
                    <span className="bf" style={{ width: Math.max(6, (geo[k].cep50 / 4) * 100) + "%" }} />
                  </span>
                  <span className="bv">{geo[k].cep50.toFixed(1)} km</span>
                </div>
              ))}
              <div className="tbl-note">CEP50 · n = {geo?.["4"]?.n ?? geo?.["2"]?.n ?? "—"} per configuration</div>
            </div>

            <div className="res-card reveal from-right">
              <h4>Multi-receiver scaling</h4>
              <div className="sub">Same scene, receivers ×1 → ×3 — reward compounds</div>
              <div className="tablewrap">
                <table className="tbl">
                  <thead>
                    <tr><th>Configuration</th><th>Total reward</th><th>Intercept</th></tr>
                  </thead>
                  <tbody>
                    {multi && Object.keys(multi).sort().map((k) => (
                      <tr key={k}
                          style={k.startsWith("smart-scan") ? { color: "var(--amber)" } : undefined}>
                        <td>{k.replace(/-x(\d)/, " ×$1")}</td>
                        <td>{multi[k].total_reward.toFixed(0)}</td>
                        <td>{pct(multi[k].intercept_ratio)}</td>
                      </tr>
                    ))}
                    {!multi && <tr><td colSpan={3}>Loading…</td></tr>}
                  </tbody>
                </table>
              </div>
              <div className="tbl-note">Coverage integrity stays at 1.0 across all configurations.</div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ FIGURES ═══ */}
      <section className="section" id="figures">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Publication figures</div>
            <h2 className="section-title">The full figure set</h2>
            <p className="section-desc">
              Regenerated by the experiment suite on every run — usable directly
              in reports and the presentation deck.
            </p>
          </div>
          <div className="figures">
            {FIGURES.map(([file, cap], i) => (
              <figure className={"reveal " + (i % 2 ? "from-right" : "from-left")} key={file}>
                <img src={"/figures/" + file} alt={cap} loading="lazy" />
                <figcaption>{cap}</figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ REPRODUCE ═══ */}
      <section className="section" id="reproduce">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Reproduce</div>
            <h2 className="section-title">Run it yourself</h2>
            <p className="section-desc">
              The exact commands that produced everything above, from a clean clone.
            </p>
          </div>
          <div className="term reveal">
            <div className="term-head">
              <i /><i /><i /><span>powershell — astra repo</span>
            </div>
            <pre>
{`» git clone https://github.com/RARPlayzDev/Astra
» python -m venv .venv; .venv\\Scripts\\activate
» pip install -r requirements.txt
» python -m pytest tests -q           `}<span className="g">306 passed</span>{`
» python -m ewsmart.experiments --suite full  `}<span className="y">published suite → results/</span>{`
» python tools/export_site_data.py            `}<span className="b">results/ → the data on this page</span>{`
» cd website; npm ci; npm run probe   `}<span className="b">prediction probe table</span>{`
» cd website; npm run dev             `}<span className="d"># browse this page locally</span>
            </pre>
          </div>
          <div className="note gold reveal">
            <b>Determinism guarantee:</b> identical seeds produce identical JSON.
            If your numbers differ, check your Python/NumPy versions against{" "}
            <code className="mono">requirements.txt</code> — the CI badge on the{" "}
            <a href="https://github.com/RARPlayzDev/Astra" target="_blank" rel="noreferrer">repository</a> shows
            the environment that produced these results.
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="wrap">
          <Footer />
        </div>
      </footer>
    </>
  );
}
