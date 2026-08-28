import { useEffect } from "react";
import { Footer, GateAndMc, Nav, useResults } from "../shared";
import HeroScroll from "../components/HeroScroll";

const TECH_STACK = [
  { name: "Python", sub: "Core engine" },
  { name: "TypeScript", sub: "Web frontend" },
  { name: "React", sub: "UI framework" },
  { name: "PyInstaller", sub: "Desktop packaging" },
  { name: "NumPy", sub: "Numerical computing" },
  { name: "Rayleigh estimation", sub: "Period detection" },
  { name: "UCB Bandits", sub: "Exploration" },
  { name: "Q-Learning", sub: "Value-based RL" },
  { name: "Monte Carlo", sub: "200-episode validation" },
  { name: "Webview", sub: "Desktop UI shell" },
  { name: "Vite", sub: "Frontend bundler" },
  { name: "Holm correction", sub: "Statistical rigor" },
  { name: "Cooperative AOA", sub: "Multi-receiver" },
  { name: "Seed reproducibility", sub: "Deterministic results" },
  { name: "57 automated tests", sub: "CI quality gate" },
  { name: "SQLite", sub: "Local storage" },
  { name: "CI/CD", sub: "Automated builds" },
  { name: "Canvas API", sub: "Radar visualization" },
];

const STEPS: [string, string][] = [
  ["Survey", "A fast reconnaissance sweep bootstraps statistics across every band — no prior intelligence required."],
  ["Learn", "Detection streams fingerprinted by SNR and angle-of-arrival; periodicities estimated with Rayleigh significance testing."],
  ["Predict", "Validated locks predict each emitter's next transmission window before it opens."],
  ["Position", "The receiver arrives early and dwells through the predicted window — interception becomes schedule, not luck."],
  ["Rotate", "Remaining time allocated by discounted value with recency guarantees, so no band starves."],
];

const FEATURES: [string, string, string][] = [
  ["◉", "Adaptive scan scheduler", "Five auditable behaviours multiplexed by learned confidence, validated online — stale beliefs self-destruct."],
  ["◈", "Prediction engine", "Rayleigh period estimation with integer refinement converts periodic emitters from search problems into appointments."],
  ["●", "Emitter identification", "Intercepted streams fingerprinted against a JC Wise-class library; 100% accuracy on the reference episode."],
  ["◆", "Multi-receiver geolocation", "Cooperative AOA triangulation; CEP50 improves from 3.2 km to 1.7 km with two to four receivers."],
  ["◐", "Live paired demonstration", "Two receivers fly identical battlefields side by side — strategy is the only variable."],
  ["◎", "Reproducible by construction", "Seed-defined scenarios, strict JSON outputs, 57 automated tests, one-command builds."],
];

function useReveal() {
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("vis");
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -30px 0px" }
    );
    document.querySelectorAll(".reveal").forEach((n) => obs.observe(n));
    return () => obs.disconnect();
  }, []);
}

export default function Home() {
  useReveal();

  // Duplicate for seamless loop
  const techLoop = [...TECH_STACK, ...TECH_STACK];

  return (
    <>
      <Nav />
      <HeroScroll />

      {/* ═══ TECH STACK MARQUEE ═══ */}
      <section className="tech-marquee-section">
        <div className="tech-marquee-label">Technology Stack</div>
        <div className="tech-marquee-track">
          {techLoop.map((t, i) => (
            <div className="tech-item" key={i}>
              <span className="tech-item-dot" />
              <span className="tech-item-text">{t.name}</span>
              <span className="tech-item-sub">{t.sub}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ PROBLEM ═══ */}
      <section className="section" id="problem">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">The Problem</div>
            <h2 className="section-title">
              Finding a needle that transmits for 2% of the time
            </h2>
            <p className="section-desc">
              An ES receiver is sensitive but narrowband: it listens to one
              slice of spectrum at a time while being responsible for a far
              wider range. Interception is a two-dimensional search — right
              frequency, right time.
            </p>
          </div>
          <div className="cards-grid">
            <div className="card border-red reveal from-left">
              <div className="card-tag red">Conventional</div>
              <h4>Open-loop sweeps</h4>
              <p>
                Fixed pre-mission patterns visit every band blindly. Dwell time
                wasted on clutter, new threats found late, periodic rhythms
                never exploited. 78% threat coverage, lowest reward.
              </p>
            </div>
            <div className="card border-red reveal from-right">
              <div className="card-tag red">Naive Adaptivity</div>
              <h4>The exploitation trap</h4>
              <p>
                A pure bandit camps on the busiest band — highest raw score,
                while detecting only 54% of threats. Reward and coverage pull
                in opposite directions.
              </p>
            </div>
            <div className="card border-green card-full reveal scale-in">
              <div className="card-tag green">ASTRA's Answer</div>
              <h4>Resolve the trade-off</h4>
              <p>
                SmartScan learns each emitter's behaviour online, predicts
                transmission windows, positions the receiver ahead, and
                protects coverage structurally. High reward <b>and</b> near-total
                threat coverage — the only mission-capable scheduler in its field.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ HOW IT WORKS ═══ */}
      <section className="section" id="how">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">How It Works</div>
            <h2 className="section-title">From blind sweep to scheduled intercept</h2>
            <p className="section-desc">
              Every mission runs the same loop — survey, learn, predict,
              position, rotate — with continuous validation so wrong hypotheses
              die cheap.
            </p>
          </div>
          <div className="pipeline">
            {STEPS.map(([t, d], i) => (
              <div className="pipe-step reveal" key={t} style={{ transitionDelay: `${i * 0.08}s` }}>
                <div className="pipe-num">{i + 1}</div>
                <h4>{t}</h4>
                <p>{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ RESULTS ═══ */}
      <section className="section" id="results">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Results</div>
            <h2 className="section-title">Judged the way defence judges systems</h2>
            <p className="section-desc">
              Hard Key Performance Parameters first — threat coverage ≥ 90%,
              prediction better than chance, false alarms bounded. 200-episode
              Monte Carlo, paired permutation tests, Holm-corrected.
            </p>
          </div>
          <div className="reveal">
            <GateAndMc />
          </div>
          <div className="figures">
            <figure className="reveal from-left">
              <img src="/figures/mission_effectiveness.png" alt="Mission effectiveness" loading="lazy" />
              <figcaption>Mission Effectiveness Score under the KPP gate — only the proposed policy is mission-capable.</figcaption>
            </figure>
            <figure className="reveal from-right">
              <img src="/figures/comparison.png" alt="Scheduler comparison" loading="lazy" />
              <figcaption>Scheduler comparison across the principal figures of merit.</figcaption>
            </figure>
          </div>
        </div>
      </section>

      {/* ═══ CAPABILITIES ═══ */}
      <section className="section" id="capabilities">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Capabilities</div>
            <h2 className="section-title">A complete Electronic Support pipeline</h2>
          </div>
          <div className="features-grid">
            {FEATURES.map(([ic, t, d], i) => (
              <div className="feat reveal" key={t} style={{ transitionDelay: `${i * 0.06}s` }}>
                <div className="feat-icon">{ic}</div>
                <h4>{t}</h4>
                <p>{d}</p>
              </div>
            ))}
          </div>
          <div id="download" className="download-section reveal">
            <h3>Get ASTRA</h3>
            <div className="dl-grid">
              <ol className="dl-steps">
                <li>
                  Download <b>ASTRA-Setup-2.0.0.exe</b>{" "}
                  <a
                    href="/ASTRA-Setup-2.0.0.exe"
                    download
                    style={{ color: "var(--accent)", textDecoration: "underline" }}
                  >
                    (35 MB)
                  </a>
                </li>
                <li>Run the installer — choose destination folder and optional desktop icon.</li>
                <li>Launch <b>ASTRA</b> from the Start Menu.</li>
                <li>
                  Press <i>Start Mission</i>, then open{" "}
                  <i>Tools → Diagnostics</i> to verify all self-tests pass.
                </li>
              </ol>
              <div className="dl-reqs">
                <h4>Requirements</h4>
                <ul>
                  <li>Windows 10 or 11 (64-bit)</li>
                  <li>~150 MB disk space</li>
                  <li>No internet required at runtime</li>
                  <li>WebView2 ships with Windows</li>
                </ul>
              </div>
            </div>
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
