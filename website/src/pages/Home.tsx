import { useEffect } from "react";
import { DOWNLOAD_URL, Footer, GateAndMc, Nav, SITE_VERSION as SITE_VER, useResults } from "../shared";
import HeroScroll from "../components/HeroScroll";

const STATS: [string, string, string, string][] = [
  ["306", "", "Automated tests", "pytest suite, all passing in CI"],
  ["96.9", "%", "Prediction accuracy", "SmartScan vs 54.1% sequential sweep"],
  ["90–95.8", "%", "Threat coverage", "across seeds under the KPP gate"],
  ["1.8", "×", "Faster first fix", "time-to-intercept vs sequential"],
  ["200", "", "Monte Carlo episodes", "paired permutation, Holm-corrected"],
  ["13/13", "", "PS checks live", "problem-statement coverage audit"],
];

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
  { name: "306 automated tests", sub: "CI quality gate" },
  { name: "SQLite", sub: "Local storage" },
  { name: "CI/CD", sub: "Automated builds" },
  { name: "Canvas API", sub: "Radar visualization" },
];

const STEPS: [string, string][] = [
  ["Survey", "A fast reconnaissance sweep bootstraps statistics across every band — no prior intelligence required."],
  ["Learn", "Detection streams fingerprinted by SNR and angle-of-arrival. Periodicities estimated with Rayleigh significance testing."],
  ["Predict", "Validated locks predict each emitter's next transmission window before it opens."],
  ["Position", "The receiver arrives early and dwells through the predicted window — interception becomes schedule, not luck."],
  ["Rotate", "Remaining time allocated by discounted value with recency guarantees, so no band starves."],
];

const FEATURES: [string, string, string][] = [
  ["◉", "Adaptive scan scheduler", "Five behaviours multiplexed by learned confidence — validated online, stale beliefs self-destruct."],
  ["◈", "Prediction engine", "Rayleigh period estimation converts periodic emitters from search problems into appointments."],
  ["●", "Emitter identification", "Streams fingerprinted against a JC Wise-class library with confidence scores and threat classification."],
  ["◆", "Multi-receiver geolocation", "Cooperative AOA triangulation; CEP improves from 3.2 km to 1.7 km with more receivers."],
  ["◐", "Live paired demonstration", "Two receivers fly identical battlefields side by side — strategy is the only variable."],
  ["◎", "Reproducible by construction", "Seed-defined scenarios, strict JSON outputs, 306 automated tests, one-command builds."],
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

      {/* ═══ STATS BAND ═══ */}
      <section className="section" id="numbers" style={{ paddingTop: "clamp(56px, 8vw, 96px)", paddingBottom: "clamp(56px, 8vw, 96px)" }}>
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">By the numbers</div>
            <h2 className="section-title">Every claim on this page is reproducible</h2>
            <p className="section-desc">
              Nothing here is a mock-up. Each figure is produced by the bundled
              experiment suite from stored seeds — run the commands yourself and
              you will get the same numbers.
            </p>
          </div>
          <div className="stats-band reveal">
            {STATS.map(([v, unit, lbl, sub]) => (
              <div className="stat" key={lbl}>
                <div className="stat-val">{v}{unit && <span className="unit">{unit}</span>}</div>
                <div className="stat-lbl">{lbl}</div>
                <div className="stat-sub">{sub}</div>
              </div>
            ))}
          </div>
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
              frequency, right time.{" "}
              <span className="footer-drdo" style={{ verticalAlign: "middle" }}>
                Submitted against a <b>DRDO</b> problem statement · Electronic Warfare
              </span>
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
              <a href="/results.html" style={{ marginLeft: 10, fontWeight: 600 }}>
                Full results page →
              </a>
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
            <h3>Get ASTRA {SITE_VER}</h3>
            <div className="dl-grid">
              <ol className="dl-steps">
                <li>
                  Download <b>ASTRA-Setup-3.0.0.exe</b>{" "}
                  <a href={DOWNLOAD_URL} download style={{ color: "var(--accent)", textDecoration: "underline" }}>
                    from GitHub Releases (~164 MB)
                  </a>
                </li>
                <li>Run the installer — choose destination folder and optional desktop icon.</li>
                <li>Launch <b>ASTRA</b> from the Start Menu.</li>
                <li>
                  Press <i>Start Mission</i>, then open{" "}
                  <i>Tools → Diagnostics</i> to verify all self-tests pass.
                </li>
                <li>
                  First run of the web console shows the guided tour — take it,
                  it maps every control in 60 seconds.
                </li>
              </ol>
              <div className="dl-reqs">
                <h4>Requirements</h4>
                <ul>
                  <li>Windows 10 or 11 (64-bit)</li>
                  <li>~600 MB disk space</li>
                  <li>No internet required at runtime</li>
                  <li>WebView2 ships with Windows</li>
                  <li>SHA256 checksum published in release notes</li>
                </ul>
                <div style={{ marginTop: 18, display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <a className="btn primary" href={DOWNLOAD_URL} download>Download installer</a>
                  <a className="btn ghost" href="/console.html">Try in browser</a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ REPRODUCE ═══ */}
      <section className="section" id="reproduce">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Evidence</div>
            <h2 className="section-title">Reproduce every number in three commands</h2>
            <p className="section-desc">
              The full stack ships in the repo: tests, benchmark suite, prediction
              probe and the website itself. Same seeds, same outputs — on any machine.
            </p>
          </div>
          <div className="term reveal">
            <div className="term-head">
              <i /><i /><i /><span>powershell — astra repo</span>
            </div>
            <pre>
{`» python -m pytest tests -q           `}<span className="g">306 passed in 4m16s</span>{`
» cd website; npm run probe           `}<span className="y">SmartScan 96.9% · sequential 54.1%</span>{`
» python -m tools.export_docs         `}<span className="b">manual → website docs (single source)</span>{`
» npm run build && npm run dev        `}<span className="d"># edit the site locally</span>
            </pre>
          </div>
          <div className="res-method reveal">
            <div className="method-step">
              <div className="mi">01 · SEED</div>
              <h5>Deterministic by construction</h5>
              <p>Scenarios are defined by seed — rerunning a benchmark reproduces bit-identical JSON outputs.</p>
            </div>
            <div className="method-step">
              <div className="mi">02 · GATE</div>
              <h5>KPPs before score</h5>
              <p>Schedulers must pass every Key Performance Parameter simultaneously before any ranking counts.</p>
            </div>
            <div className="method-step">
              <div className="mi">03 · STATISTICS</div>
              <h5>Significance, not vibes</h5>
              <p>200-episode Monte Carlo, paired permutation tests, Holm correction across seven comparators.</p>
            </div>
            <div className="method-step">
              <div className="mi">04 · AUDIT</div>
              <h5>Negative results kept</h5>
              <p>The DQN that lost under sparse reward stays in the report — with the reason it lost.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ FAQ ═══ */}
      <section className="section" id="faq">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">FAQ</div>
            <h2 className="section-title">Questions judges actually ask</h2>
          </div>
          <div className="faq reveal">
            <details open>
              <summary>What exactly does ASTRA do?</summary>
              <div className="faq-a">
                It decides <b>when and where</b> an Electronic Support receiver tunes.
                It learns each emitter's rhythm online, predicts the next transmission
                window, and positions the receiver ahead of it — turning intercept from
                luck into schedule, without any prior intelligence.
              </div>
            </details>
            <details>
              <summary>How do we know it actually works?</summary>
              <div className="faq-a">
                Three layers: <b>306 automated tests</b>, a <b>200-episode Monte Carlo</b>
                benchmark with paired permutation tests and Holm correction, and a
                <b> KPP gate</b> borrowed from defence acceptance style — coverage ≥ 90%,
                prediction better than chance, false alarms bounded. All numbers come
                from those runs; see the <a href="/results.html">results page</a>.
              </div>
            </details>
            <details>
              <summary>What makes it different from a bandit or RL scheduler?</summary>
              <div className="faq-a">
                A pure bandit maximises reward and camps on one busy band — highest raw
                score while detecting only ~54% of threats. ASTRA protects coverage
                structurally and exploits learned periodicity, so it wins on reward{" "}
                <b>and</b> coverage. It is also the only scheduler that passes every KPP
                simultaneously. The deep Q-network we benchmarked lost under sparse,
                non-stationary reward — that negative result is documented, not hidden.
              </div>
            </details>
            <details>
              <summary>Does it need a radar or live signals?</summary>
              <div className="faq-a">
                No. Everything runs against a deterministic, high-fidelity simulation
                (24 bands, 2–18 GHz, emitters transmitting ~2% of the time). The
                hardware on-ramp exists — a fixed-point C++ policy kernel and a UDP PDW
                stream interface — but the prototype validates in software so results
                are exactly reproducible.
              </div>
            </details>
            <details>
              <summary>Is the desktop app the same as the web console?</summary>
              <div className="faq-a">
                Yes. The Windows installer wraps the same React console in a WebView2
                shell with the Python engine running locally — offline, no server, plus{" "}
                <i>Tools → Diagnostics</i> self-tests. The{" "}
                <a href="/console.html">browser console</a> is the zero-install way to
                demo it.
              </div>
            </details>
            <details>
              <summary>Is this operational equipment?</summary>
              <div className="faq-a">
                No — ASTRA is a <b>simulation-based research prototype</b> built for
                Smart India Hackathon 2026 against a DRDO problem statement. It is not
                certified for operational use.
              </div>
            </details>
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
