import { useEffect } from "react";
import { DOWNLOAD_URL, Footer, GateAndMc, Nav, SITE_VERSION as SITE_VER, useResults } from "../shared";
import HeroScroll from "../components/HeroScroll";
import { CountUp, CursorFollower, Preloader, SectionDots } from "../components/Fx";
import SweepScope from "../components/SweepScope";

/** Chapter rail for the long-form home page. */
const CHAPTERS: [string, string][] = [
  ["instrument", "The receiver"],
  ["numbers", "By the numbers"],
  ["problem", "The problem"],
  ["walkthrough", "Mission walkthrough"],
  ["how", "How it works"],
  ["architecture", "Architecture"],
  ["results", "Results"],
  ["compare", "Head-to-head"],
  ["capabilities", "Capabilities"],
  ["desktop", "Desktop app"],
  ["reproduce", "Reproduce"],
  ["roadmap", "Roadmap"],
  ["faq", "FAQ"],
];

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

const STEPS: [string, string, string][] = [
  ["Survey", "A fast reconnaissance sweep bootstraps statistics across every band — no prior intelligence required.", "24 BANDS · 2–18 GHZ · ZERO PRIOR"],
  ["Learn", "Detection streams fingerprinted by SNR and angle-of-arrival. Periodicities estimated with Rayleigh significance testing.", "SNR · AOA · RAYLEIGH"],
  ["Predict", "Validated locks predict each emitter's next transmission window before it opens.", "96.9% NEXT-WINDOW"],
  ["Position", "The receiver arrives early and dwells through the predicted window — interception becomes schedule, not luck.", "1.8× FASTER FIRST FIX"],
  ["Rotate", "Remaining time allocated by discounted value with recency guarantees, so no band starves.", "NO STARVATION GUARANTEE"],
];

const FEATURES: [string, string, string][] = [
  ["◉", "Adaptive scan scheduler", "Five behaviours multiplexed by learned confidence — validated online, stale beliefs self-destruct."],
  ["◈", "Prediction engine", "Rayleigh period estimation converts periodic emitters from search problems into appointments."],
  ["●", "Emitter identification", "Streams fingerprinted against a JC Wise-class library with confidence scores and threat classification."],
  ["◆", "Multi-receiver geolocation", "Cooperative AOA triangulation; CEP improves from 3.2 km to 1.7 km with more receivers."],
  ["◐", "Live paired demonstration", "Two receivers fly identical battlefields side by side — strategy is the only variable."],
  ["◎", "Reproducible by construction", "Seed-defined scenarios, strict JSON outputs, 306 automated tests, one-command builds."],
  ["⬢", "Fixed-point policy kernel", "A C++ header kernel mirrors the Python policy in fixed point — the on-ramp from simulation to receiver firmware."],
  ["⇄", "UDP PDW ingest", "Pulse-descriptor-word stream interface, so the same engine can consume live receiver output instead of a simulation."],
];

/** Mission walkthrough — one cycle of the loop, told as phases. */
const PHASES: [string, string, string, string][] = [
  ["Phase 01 · Cold start", "No prior intelligence",
    "The receiver begins knowing nothing. A reconnaissance sweep samples all 24 bands (2–18 GHz) evenly — every dwell is counted, nothing is assumed, and there is no pre-mission pattern for an adversary to exploit.",
    "24 BANDS · 2–18 GHZ · ZERO PRIOR"],
  ["Phase 02 · Fingerprint", "Separating rhythm from noise",
    "Each detection stream is fingerprinted by SNR and angle-of-arrival. Periodicities are tested for Rayleigh significance, so a rhythm is only believed once the statistics justify it — and stale beliefs expire.",
    "RAYLEIGH SIGNIFICANCE TEST"],
  ["Phase 03 · Lock", "Search becomes appointment",
    "Validated locks convert periodic emitters from a search problem into a schedule. Once locked, more than 91% of that emitter's cycles are intercepted per mission.",
    ">91% OF CYCLES INTERCEPTED"],
  ["Phase 04 · Predict", "Arrive before the emitter does",
    "Locked rhythms forecast the next transmission window. On the held-out agile-hop probe the policy predicts 96.9% of next windows against 54.1% for a sequential sweep.",
    "96.9% NEXT-WINDOW (PROBE · SEED 4242)"],
  ["Phase 05 · Defend", "Coverage is structural, not luck",
    "A coverage guard keeps threat interception at or above the 90% KPP floor — 90–95.8% across seeds — while discounted-value rotation spends the remainder of the timeline on what the policy has actually learned.",
    "90–95.8% COVERAGE · GATE HELD"],
];

/** Architecture — ingest → perceive → decide → act & audit. */
const LAYERS: [string, string, string[]][] = [
  ["Layer 01", "Ingest", [
    "Simulated battlefield — 24 bands, 2–18 GHz, emitters transmitting ~2% of the time.",
    "UDP PDW stream — pulse-descriptor-word interface for live receiver input.",
    "Seed-defined scenarios, so every rerun is bit-identical.",
  ]],
  ["Layer 02", "Perceive", [
    "Pulse fingerprinting by SNR and angle-of-arrival.",
    "Rayleigh period estimation with significance testing.",
    "Library matching for emitter identification and threat classification.",
  ]],
  ["Layer 03", "Decide", [
    "Five behaviours multiplexed by learned confidence.",
    "Discounted-value scheduling with recency guarantees.",
    "Coverage guard: no band starves, no threat is silently dropped.",
  ]],
  ["Layer 04", "Act & audit", [
    "Dwell plan issued to the tuner every cycle.",
    "Fixed-point C++ policy kernel for deployment targets.",
    "KPP gate · mission-effectiveness score · 200-episode Monte Carlo audit.",
  ]],
];

/** Head-to-head — verbatim from results/benchmark.json (50-episode means). */
const CMP: [string, string, string, string, "ok" | "no"][] = [
  ["Sequential sweep", "0.186", "77.5%", "46.1%", "no"],
  ["Random scan", "0.188", "97.5%", "46.0%", "no"],
  ["Priority sweep", "0.186", "76.5%", "46.1%", "no"],
  ["UCB bandit", "0.900", "52.7%", "99.5%", "no"],
  ["Linear Q-learning", "0.449", "88.0%", "18.4%", "no"],
  ["Deep Q-network", "0.200", "88.7%", "42.6%", "no"],
  ["ASTRA SmartScan", "0.471", "92.0%", "54.5%", "ok"],
];

const ROAD: [string, string, string, string[]][] = [
  ["done", "Shipped", "Built, tested and reproducible today.", [
    "Simulation engine with a 306-test suite",
    "Adaptive web console with guided onboarding",
    "Windows desktop app — v3.0.0 installer",
    "Fixed-point C++ policy kernel",
    "UDP PDW stream interface",
    "Auto-generated docs and figure pipeline",
  ]],
  ["next", "Next", "The immediate engineering queue.", [
    "Hardware-in-the-loop trials over the UDP PDW stream",
    "Receiver-specific dwell constraints and tuner profiles",
    "Wider emitter library for threat classification",
  ]],
  ["vision", "Vision", "Where the architecture is designed to go.", [
    "Integration with DRDO Electronic Support suites",
    "Cooperative multi-node geolocation at operational scale",
    "On-device policy inference on embedded receivers",
  ]],
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
      <Preloader />
      <CursorFollower />
      <SectionDots items={CHAPTERS} />
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

      {/* ═══ LIVE SWEEP INSTRUMENT ═══ */}
      <section className="section" id="instrument" style={{ paddingTop: "clamp(56px, 8vw, 96px)", paddingBottom: "clamp(56px, 8vw, 96px)" }}>
        <div className="wrap">
          <div className="sweep-grid">
            <SweepScope height={400} />
            <div className="reveal">
              <div className="section-label">The receiver, live</div>
              <h2 className="section-title">One look tells you where to point the antenna</h2>
              <p className="section-desc">
                This is what a single ES receiver does all day: sweep 24 bands,
                wait for transmitters to speak, and remember who speaks on a
                rhythm. Gold blips are periodic emitters the learner can lock;
                blue ones are agile and keep changing frequency — those are the
                harder prey. Every lock mark is a candidate the follow-up scan
                will look at more closely.
              </p>
              <p className="section-desc">
                The same logic runs in the web console and in the desktop app;
                the picture above is decorative, but the schedule it imitates is
                the real one: dwell budgets, revisit intervals and lock
                bookkeeping straight out of <code>engine/models.py</code>.
              </p>
              <div className="sweep-legend">
                <span><i style={{ background: "#cfa453" }} /> Periodic — lockable</span>
                <span><i style={{ background: "#6f9ec7" }} /> Frequency agile</span>
                <span><i style={{ background: "rgba(207,164,83,.5)" }} /> Phase-locked mark</span>
              </div>
              <div className="sweep-stats">
                <div className="sweep-stat"><b>24</b><span>Bands swept</span></div>
                <div className="sweep-stat"><b>0.475</b><span>Sharpness cutoff</span></div>
                <div className="sweep-stat"><b>96.9%</b><span>SmartScan accuracy</span></div>
                <div className="sweep-stat"><b>1.8×</b><span>Faster first fix</span></div>
              </div>
            </div>
          </div>
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
                <div className="stat-val">
                  {/^\d+(\.\d+)?$/.test(v)
                    ? <CountUp to={parseFloat(v)} decimals={v.includes(".") ? 1 : 0} />
                    : v}
                  {unit && <span className="unit">{unit}</span>}
                </div>
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
              <div className="card-stat">
                MEASURED — <b>0.775</b> coverage · <b>0.186</b> reward · fails the KPP gate
              </div>
            </div>
            <div className="card border-red reveal from-right">
              <div className="card-tag red">Naive Adaptivity</div>
              <h4>The exploitation trap</h4>
              <p>
                A pure bandit camps on the busiest band — highest raw score,
                while detecting only 52.7% of threats. Reward and coverage pull
                in opposite directions.
              </p>
              <div className="card-stat">
                MEASURED — <b>0.900</b> reward, highest of seven schedulers · <b>0.527</b> coverage
              </div>
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
              <div className="card-stat">
                MEASURED — <b>0.920</b> mean coverage · <b>0.471</b> reward · the only scheduler to pass every KPP
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ HOW IT WORKS ═══ */}
      {/* ═══ MISSION WALKTHROUGH ═══ */}
      <section className="section" id="walkthrough">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Mission Walkthrough</div>
            <h2 className="section-title">One cycle of the loop, told as phases</h2>
            <p className="section-desc">
              This is the mission narrative behind the numbers: what the receiver
              actually does from the first blind sweep to a maintained lock, and
              which measurement stands behind each phase.
            </p>
          </div>
          <div className="tl reveal">
            <div className="tl-rail" />
            {PHASES.map(([tag, title, body, metric], i) => (
              <div className="tl-item reveal" key={tag} style={{ transitionDelay: `${i * 0.08}s` }}>
                <div className="tl-tag">{tag}</div>
                <h4>{title}</h4>
                <p>{body}</p>
                <span className="tl-metric">{metric}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

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
            {STEPS.map(([t, d, chip], i) => (
              <div className="pipe-step reveal" key={t} style={{ transitionDelay: `${i * 0.08}s` }}>
                <div className="pipe-num">{i + 1}</div>
                <h4>{t}</h4>
                <p>{d}</p>
                <span className="pipe-chip">{chip}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ RESULTS ═══ */}
      {/* ═══ ARCHITECTURE ═══ */}
      <section className="section" id="architecture">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Architecture</div>
            <h2 className="section-title">Four layers, one decision per cycle</h2>
            <p className="section-desc">
              The same pipeline runs in simulation, in the browser console and in
              the desktop app — with a fixed-point kernel path for real receiver
              hardware.
            </p>
          </div>
          <div className="arch reveal">
            {LAYERS.map(([n, title, items]) => (
              <div className="arch-col" key={n}>
                <div className="arch-n">{n}</div>
                <h4>{title}</h4>
                <ul>
                  {items.map((it) => <li key={it}>{it}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

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
      {/* ═══ HEAD-TO-HEAD ═══ */}
      <section className="section" id="compare">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Head-to-head</div>
            <h2 className="section-title">Seven schedulers, one acceptance gate</h2>
            <p className="section-desc">
              The full benchmark table, verbatim from the artifact. Reward alone
              is a trap — the top-scoring scheduler is the one that misses nearly
              half the threats.
            </p>
          </div>
          <div className="cmp-wrap reveal">
            <table className="cmp">
              <thead>
                <tr>
                  <th>Scheduler</th>
                  <th>Avg reward</th>
                  <th>Threat coverage</th>
                  <th>Next-hop prediction</th>
                  <th>Mission capable</th>
                </tr>
              </thead>
              <tbody>
                {CMP.map(([name, rew, cov, pred, verdict]) => {
                  const us = verdict === "ok";
                  return (
                    <tr key={name} className={us ? "win" : ""}>
                      <td className={us ? "us" : ""}>{name}</td>
                      <td className={us ? "us" : ""}>{rew}</td>
                      <td className={us ? "us" : ""}>{cov}</td>
                      <td className={us ? "us" : ""}>{pred}</td>
                      <td className={us ? "us" : ""}>
                        <span className={`verdict ${verdict}`}>{us ? "✓ PASS" : "✗ FAIL"}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="cmp-note reveal d2">
            <b>Read the prediction column carefully.</b> It is the next-hop
            prediction benchmark from the Monte Carlo artifact (KPP floor 0.5).
            The UCB bandit leads on reward and prediction because it camps on one
            busy band — and its threat coverage collapses to 0.527, so it fails
            the gate. Coverage and reward are reported separately from the
            agile-hop probe, where SmartScan predicts <b>96.9%</b> of windows
            against 54.1% for a sequential sweep.
          </p>
        </div>
      </section>

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

      {/* ═══ DESKTOP APPLICATION ═══ */}
      <section className="section" id="desktop" style={{ paddingTop: "clamp(48px, 7vw, 84px)" }}>
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Desktop application</div>
            <h2 className="section-title">The whole system as an offline Windows app</h2>
            <p className="section-desc">
              Everything on this site — simulation, prediction, Arena, results —
              also ships as a single installer. The desktop app is the field
              build: it starts a local server, opens the same console UI in a
              WebView2 window, and adds the hardware side the browser cannot do.
              Nothing phones home; the app runs air-gapped by design.
            </p>
          </div>
          <div className="features-grid">
            {[
              ["⊞", "Mission control", "Start Mission spins up the local server and the console loads inside the desktop window — identical tabs, identical tour, identical one-click demos."],
              ["⚕", "Diagnostics & self-test", "Tools → Diagnostics verifies survey data, builder mode, embedded scenario library, prediction report generator and full survey reports in one pass."],
              ["⇩", "PDW and UDP ingest", "Real pulse descriptor words arrive over UDP for offline analysis — the hardware pipeline that a browser tab can never own."],
              ["☰", "SQLite event log", "Runs, locks and alerts are written to a local SQLite file, so a mission stays auditable after the laptop shuts down."],
              ["⚙", "Config you can ship", "astra_config.json and scenario YAMLs live next to the exe — change dwell budgets or band plans without touching the code."],
              ["☂", "One manual, three places", "The PDF you generate from Report → Create astra documentation (F6) is the same source that feeds the Docs tab on this site and Help → Manual in the app."],
            ].map(([ic, t, d], i) => (
              <div className="feat reveal" key={t} style={{ transitionDelay: `${i * 0.06}s` }}>
                <div className="feat-icon">{ic}</div>
                <h4>{t}</h4>
                <p>{d}</p>
              </div>
            ))}
          </div>
          <div className="reveal" style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 26 }}>
            <a className="btn primary" href={DOWNLOAD_URL} download>Download ASTRA-Setup-3.0.0.exe</a>
            <a className="btn ghost" href="/documentation.html">Read the manual</a>
            <a className="btn ghost" href="/console.html">Or try it in the browser</a>
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
      {/* ═══ ROADMAP ═══ */}
      <section className="section" id="roadmap">
        <div className="wrap">
          <div className="reveal">
            <div className="section-label">Roadmap</div>
            <h2 className="section-title">Honest about what is built, and what is next</h2>
            <p className="section-desc">
              No roadmap theatre. Everything in the first column runs today, the
              second is the live engineering queue, the third is where this
              architecture is designed to go.
            </p>
          </div>
          <div className="road reveal">
            {ROAD.map(([cls, title, sub, items]) => (
              <div className={"road-col " + cls} key={cls}>
                <h4>{title}</h4>
                <p className="road-sub">{sub}</p>
                <ul>
                  {items.map((it) => <li key={it}>{it}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

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
                score while detecting only 52.7% of threats. ASTRA protects coverage
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

      {/* ═══ CTA BAND ═══ */}
      <section className="c-band">
        <div className="wrap">
          <div className="reveal">
            <div className="c-band-kicker">
              ASTRA {SITE_VER} · Windows installer · browser console · full source
            </div>
            <h2>Run the loop yourself — it takes one command.</h2>
            <p>
              Install the desktop build for the offline engine, or open the
              console in a browser tab and watch the policy adapt band by band.
              Every figure on this page is one command away from being reproduced
              on your machine.
            </p>
          </div>
          <div className="c-band-actions reveal d2">
            <a className="btn solid lg" href={DOWNLOAD_URL} download>Download ASTRA {SITE_VER}</a>
            <a className="btn lg" href="/console.html">Open the console</a>
            <a className="btn lg" href="/documentation.html">Read the manual</a>
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
