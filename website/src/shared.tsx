import { useCallback, useEffect, useState } from "react";
import { PageWipe } from "./components/Fx";

type MeanCI = Record<string, number | null>;
type Results = {
  monte_carlo_means: Record<string, Record<string, number | null>>;
  monte_carlo_ci: Record<string, Record<string, number | null>>;
  mission_effectiveness: {
    scores: Record<string, {
      mes: number; mission_capable: boolean;
      kpps: Record<string, { pass: boolean; value: number }>;
    }>;
    ranking: string[];
    kpps: Record<string, { min?: number; max?: number; why?: string }>;
  } | null;
  identification: { accuracy?: number };
};

const TITLES: Record<string, string> = {
  "smart-scan": "SmartScan (proposed)",
  "bandit-ucb": "UCB bandit",
  "rl-linear-q": "Q-learning (linear)",
  "rl-dqn": "Deep Q-network",
  "openloop-random": "Random scan",
  "openloop-priority": "Priority sweep",
  "openloop-sequential": "Sequential sweep",
};

/** Single source of truth for every download button on the site. */
export const DOWNLOAD_URL =
  "https://github.com/RARPlayzDev/Astra/releases/download/v3.0.0/ASTRA-Setup-3.0.0.exe";
export const SITE_VERSION = "v3.0.0";
export const REPO_URL = "https://github.com/RARPlayzDev/Astra";

export function useResults(): Results | null {
  const [r, setR] = useState<Results | null>(null);
  useEffect(() => {
    fetch("/data/results.json").then((x) => x.json()).then(setR).catch(() => undefined);
  }, []);
  return r;
}

/* ── theme (dark default / light) ─────────────────────────────── */
type Theme = "dark" | "light";

export function currentTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  return (document.documentElement.dataset.theme === "light" ? "light" : "dark");
}

export function setTheme(t: Theme) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("astra.theme", t); } catch { /* private mode */ }
}

export function useTheme(): [Theme, () => void] {
  const [theme, setThemeState] = useState<Theme>(() => currentTheme());
  const toggle = useCallback(() => {
    const next: Theme = currentTheme() === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  }, []);
  return [theme, toggle];
}

export function ThemeToggle({ className = "" }: { className?: string }) {
  const [, toggle] = useTheme();
  return (
    <button
      className={"theme-toggle " + className}
      onClick={toggle}
      aria-label="Toggle light / dark theme"
      title="Toggle theme"
      type="button"
    >
      <svg className="ic-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
      <svg className="ic-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <circle cx="12" cy="12" r="4.2" />
        <path d="M12 2v2.5M12 19.5V22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M2 12h2.5M19.5 12H22M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" />
      </svg>
    </button>
  );
}

export function Logo({ size = 28 }: { size?: number }) {
  return <img src="/astra_logo.svg" alt="ASTRA logo" width={size} height={size} />;
}

export function Nav() {
  const [open, setOpen] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const h = document.documentElement;
      const max = h.scrollHeight - h.clientHeight;
      setProgress(max > 0 ? (h.scrollTop / max) * 100 : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      <nav className="nav">
        <div className="nav-inner">
        <a className="brand" href="/"><Logo /><span className="brand-name">ASTRA</span></a>
        <div className={"nav-links" + (open ? " open" : "")}>
          <a href="/#problem" onClick={() => setOpen(false)}>Problem</a>
          <a href="/#how" onClick={() => setOpen(false)}>How it works</a>
          <a href="/results.html">Results</a>
          <a href="/console.html">Console</a>
          <a href="/documentation.html">Docs</a>
          <a className="nav-download" href={DOWNLOAD_URL} download>Download</a>
        </div>
        <ThemeToggle />
        <button
          className={"nav-burger" + (open ? " open" : "")}
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
          type="button"
        ><span /></button>
      </div>
      <div className="nav-progress" style={{ width: progress + "%" }} />
      </nav>
      <PageWipe />
    </>
  );
}


export function Footer() {
  return (
    <div className="footer-grid">
      <div className="footer-brand">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <Logo size={26} />
          <span className="brand-name" style={{ fontSize: 15, letterSpacing: 4 }}>ASTRA</span>
        </div>
        <p>Adaptive Spectrum Threat Recognition &amp; Analysis — an adaptive scan scheduler for Electronic Support receivers.</p>
        <p>A prototype developed for Smart India Hackathon 2026. Simulation-based research software, not operational equipment.</p>
        <span className="footer-drdo">
          Problem statement issued by <b>DRDO</b> · Electronic Warfare
        </span>
      </div>
      <div className="footer-col">
        <h4>Product</h4>
        <a href="/console.html">Console</a>
        <a href="/documentation.html">Documentation</a>
        <a href="/results.html">Results</a>
        <a href={DOWNLOAD_URL} download>Download {SITE_VERSION}</a>
      </div>
      <div className="footer-col">
        <h4>Research</h4>
        <a href="/#how">Methodology</a>
        <a href="/#capabilities">Capabilities</a>
        <a href="/results.html#figures">Figures</a>
        <a href="/results.html#reproduce">Reproduce</a>
      </div>
      <div className="footer-col">
        <h4>Source</h4>
        <a href={REPO_URL} target="_blank" rel="noreferrer">GitHub repository</a>
        <a href={REPO_URL + "/releases"} target="_blank" rel="noreferrer">Releases</a>
        <a href={REPO_URL + "/actions"} target="_blank" rel="noreferrer">CI / builds</a>
        <a href="/documentation.html#19-frequently-asked-questions">FAQ</a>
      </div>
      <div className="footer-bottom" style={{ gridColumn: "1 / -1" }}>
        <p>&copy; 2026 ASTRA Project Team. All benchmark figures are generated by the bundled experiment suite from stored seeds and are fully reproducible.</p>
        <p className="mono">{SITE_VERSION} · 306 automated tests · seed-exact results</p>
      </div>
    </div>
  );
}

export function GateAndMc() {
  const r = useResults();
  if (!r?.mission_effectiveness) return null;
  const me = r.mission_effectiveness;
  const kppDefs = me.kpps ?? {};

  return (
    <>
      {/* KPP thresholds legend */}
      <div className="kpp-legend">
        <span className="kpp-legend-title">KPP Gate Criteria (all must pass):</span>
        {Object.entries(kppDefs).map(([k, spec]) => {
          const label = k === "threat_intercept_ratio" ? "Threat coverage"
            : k === "pct_correct_predictions" ? "Prediction accuracy"
            : k === "false_alarm_rate" ? "False alarm rate" : k;
          const threshold = "min" in spec
            ? `≥ ${(spec.min! * 100).toFixed(0)}%`
            : `≤ ${(spec.max! * 100).toFixed(2)}%`;
          return <span key={k} className="kpp-tag">{label} {threshold}</span>;
        })}
      </div>

      <div className="table-wrap">
        <table className="results">
          <thead>
            <tr>
              <th>Scheduler</th>
              <th>Verdict</th>
              <th>MES</th>
              <th>Threat coverage</th>
              <th>Prediction accuracy</th>
            </tr>
          </thead>
          <tbody>
            {me.ranking.map((n) => {
              const sc = me.scores[n];
              const cov = sc.kpps["threat_intercept_ratio"]?.value ?? 0;
              const pred = sc.kpps["pct_correct_predictions"]?.value ?? 0;
              const covPass = sc.kpps["threat_intercept_ratio"]?.pass ?? false;
              const predPass = sc.kpps["pct_correct_predictions"]?.pass ?? false;
              return (
                <tr key={n} className={n === "smart-scan" ? "hl" : ""}>
                  <td>{TITLES[n] ?? n}</td>
                  <td>
                    <span className={"pill " + (sc.mission_capable ? "pass" : "fail")}>
                      {sc.mission_capable ? "CAPABLE" : "DISQUALIFIED"}
                    </span>
                  </td>
                  <td className="mono">{sc.mes.toFixed(3)}</td>
                  <td className={"mono " + (covPass ? "kpp-pass" : "kpp-fail")}>
                    {(cov * 100).toFixed(1)}%
                  </td>
                  <td className={"mono " + (predPass ? "kpp-pass" : "kpp-fail")}>
                    {(pred * 100).toFixed(1)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="kpp-note">
        SmartScan is the only scheduler that passes <b>every</b> KPP simultaneously —
        high threat coverage <b>and</b> accurate predictions. Others may score higher
        on individual metrics but fail the all-or-nothing gate.
      </p>
    </>
  );
}
