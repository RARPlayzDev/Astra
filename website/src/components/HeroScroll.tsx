import { DOWNLOAD_URL } from "../shared";
import SpectrumStrip from "./SpectrumStrip";

const SPEC: [string, string][] = [
  ["STATUS", "OPERATIONAL"],
  ["BUILD", "v3.0.0"],
  ["RANK", "#1 OF 7"],
  ["THREAT COVERAGE", "90–95.8%"],
  ["PROBE PREDICT", "96.9%"],
  ["TESTS", "306 PASS"],
  ["RUNTIME", "OFFLINE"],
];

/** Editorial hero: big type + spec sheet + live spectrum strip (no radar). */
export default function HeroScroll() {
  return (
    <header className="hero">
      <div className="hero-grid-overlay" aria-hidden />

      <div className="wrap hero-inner">
        <div className="hero-kicker">
          <span className="k-dot" />
          SMART INDIA HACKATHON 2026 · DRDO PROBLEM STATEMENT · ELECTRONIC WARFARE
        </div>

        <div className="hero-main">
          <div className="hero-text">
            <h1 className="hero-title">ASTRA</h1>
            <p className="hero-subtitle">
              Adaptive Spectrum Threat Recognition &amp; Analysis
            </p>
            <p className="hero-desc">
              A scan scheduler that teaches an Electronic Support receiver to
              find hostile emitters without prior intelligence — learning their
              rhythms, predicting their transmissions, and arriving before
              they appear.
            </p>
            <div className="hero-buttons">
              <a className="btn-download" href={DOWNLOAD_URL} download>
                Download v3.0.0
              </a>
              <a className="btn-outline" href="/console.html">Live console</a>
              <a className="btn-outline" href="/results.html">Results</a>
            </div>
          </div>

          <dl className="hero-spec" aria-label="Key specifications">
            {SPEC.map(([k, v]) => (
              <div className="spec-row" key={k}>
                <dt>{k}</dt>
                <span className="spec-dots" aria-hidden />
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      <div className="hero-strip">
        <SpectrumStrip height={132} />
        <span className="strip-label l">24 BANDS · 2–18 GHZ</span>
        <span className="strip-label r">SPECTRUM · TRANSMIT ≈2% OF THE TIME</span>
      </div>
    </header>
  );
}

