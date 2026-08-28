import { useEffect, useRef } from "react";
import RadarScope from "../components/RadarScope";

export default function HeroScroll() {
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const radarRef = useRef<HTMLDivElement>(null);
  const indicatorRef = useRef<HTMLDivElement>(null);
  const stickyRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef(0);

  useEffect(() => {
    const container = containerRef.current;
    const textEl = textRef.current;
    const radarEl = radarRef.current;
    const indicatorEl = indicatorRef.current;
    const stickyEl = stickyRef.current;
    if (!container || !textEl || !radarEl || !indicatorEl || !stickyEl) return;

    let ticking = false;

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      rafRef.current = requestAnimationFrame(() => {
        const rect = container.getBoundingClientRect();
        const total = container.offsetHeight - window.innerHeight;
        const p = Math.max(0, Math.min(1, -rect.top / total));

        // Radar: scale 380→800, move toward center
        const radarSize = 380 + p * 420;
        radarEl.style.width = radarSize + "px";
        radarEl.style.height = radarSize + "px";
        radarEl.style.opacity = p < 0.85 ? "1" : String(1 - (p - 0.85) / 0.15);

        // Text: fade out
        textEl.style.opacity = p < 0.3 ? "1" : String(Math.max(0, 1 - (p - 0.3) / 0.3));
        textEl.style.transform = `translateY(${p * -40}px)`;

        // Entire hero fade
        stickyEl.style.opacity = p < 0.9 ? "1" : String(Math.max(0, 1 - (p - 0.9) / 0.1));

        // Scroll indicator
        indicatorEl.style.opacity = p < 0.05 ? "1" : "0";

        ticking = false;
      });
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div ref={containerRef} className="hero-scroll-container">
      <div ref={stickyRef} className="hero-scroll-sticky">
        <div className="hero-layout">
          <div ref={textRef} className="hero-text">
            <div className="hero-badge">SIH 2026 · ELECTRONIC WARFARE</div>
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
              <a className="btn-download" href="/ASTRA-Setup-2.0.0.exe" download>
                Download for Windows
              </a>
              <a className="btn-outline" href="/console.html">Console</a>
              <a className="btn-outline" href="/documentation.html">Docs</a>
            </div>
            <div className="hero-metrics">
              <div className="metric">
                <span className="metric-val">#1 / 7</span>
                <span className="metric-lbl">Rank</span>
              </div>
              <div className="metric-sep" />
              <div className="metric">
                <span className="metric-val">95%</span>
                <span className="metric-lbl">Coverage</span>
              </div>
              <div className="metric-sep" />
              <div className="metric">
                <span className="metric-val">2.1×</span>
                <span className="metric-lbl">Reward</span>
              </div>
            </div>
          </div>

          <div ref={radarRef} className="hero-radar">
            <RadarScope size={380} />
          </div>
        </div>

        <div ref={indicatorRef} className="scroll-indicator">
          <span>Scroll</span>
          <div className="scroll-line" />
        </div>
      </div>
    </div>
  );
}
