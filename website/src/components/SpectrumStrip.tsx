import { useEffect, useRef } from "react";

/**
 * SpectrumStrip — full-width spectrum analyser band.
 * Thin FFT-style bins; most energy sits low in steel-blue, occasional
 * transmissions spike in gold (the "emitters fire 2% of the time" story).
 * Replaces the old radar scope in the hero: on-brand for an ES receiver
 * and deliberately NOT a radar PPI display.
 */
export default function SpectrumStrip({ height = 132 }: { height?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef(0);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0;
    let h = 0;

    const resize = () => {
      w = canvas.clientWidth;
      h = height;
      canvas.width = Math.max(1, Math.floor(w * dpr));
      canvas.height = Math.max(1, Math.floor(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    // per-bin phase + character
    let bins: { f: number; a: number; p: number; x: number }[] = [];
    const buildBins = () => {
      const bw = 3;                       // bin width px
      const gap = 2;
      const n = Math.max(24, Math.floor(w / (bw + gap)));
      bins = Array.from({ length: n }, (_, i) => ({
        f: 0.35 + Math.random() * 1.6,
        a: 0.12 + Math.random() * 0.3,
        p: Math.random() * Math.PI * 2,
        x: Math.random(),                 // 0..1 "activity" → occasional spikes
      }));
    };
    buildBins();
    window.addEventListener("resize", buildBins);

    // transmissions: rare gold spikes that travel
    let tx = -1;                 // active spike bin index, -1 = none
    let txT = 0;
    let nextTx = 1.2;            // seconds until first

    let t = 0;
    let last = performance.now();

    const draw = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (!reduced) t += dt;

      ctx.clearRect(0, 0, w, h);

      // baseline
      ctx.strokeStyle = getComputedStyle(document.documentElement)
        .getPropertyValue("--border").trim() || "#1a2433";
      ctx.globalAlpha = 1;
      ctx.beginPath();
      ctx.moveTo(0, h - 0.5);
      ctx.lineTo(w, h - 0.5);
      ctx.stroke();

      const bw = 3;
      const gap = 2;
      const mid = h * 0.55;

      // occasional transmission
      if (!reduced) {
        nextTx -= dt;
        if (nextTx <= 0 && tx < 0) {
          tx = Math.floor(Math.random() * bins.length);
          txT = 0;
          nextTx = 2.5 + Math.random() * 3.5;   // sparse: ~2% duty feel
        }
        if (tx >= 0) {
          txT += dt;
          if (txT > 1.6) { tx = -1; }
        }
      }

      bins.forEach((b, i) => {
        const x = i * (bw + gap);
        // envelope: mostly low, drifting
        let amp = (b.a + 0.16 * Math.sin(t * b.f + b.p)) * mid;
        amp = Math.max(4, amp);

        // gold spike?
        const dist = tx >= 0 ? Math.abs(i - tx) : 9999;
        const spike = tx >= 0 && dist < 5 ? (1 - dist / 5) : 0;
        const pulse = spike * (0.55 + 0.45 * Math.sin(txT * 9));

        const bh = amp + pulse * (h * 0.38);
        const y = h - bh;

        if (pulse > 0.05) {
          ctx.fillStyle = `rgba(207, 164, 83, ${0.35 + 0.6 * pulse})`;
        } else {
          // steel-blue bars, slightly brighter toward centre activity
          const alpha = 0.16 + 0.3 * (b.a / 0.42) * (0.75 + 0.25 * Math.sin(t * 0.7 + b.p));
          ctx.fillStyle = `rgba(111, 158, 199, ${Math.min(0.5, Math.max(0.08, alpha))})`;
        }
        ctx.fillRect(x, y, bw, bh);
      });

      // scanline sweep across the strip
      if (!reduced) {
        const sx = ((t * 60) % (w + 120)) - 60;
        const g = ctx.createLinearGradient(sx - 50, 0, sx + 10, 0);
        g.addColorStop(0, "rgba(111,158,199,0)");
        g.addColorStop(1, "rgba(111,158,199,0.14)");
        ctx.fillStyle = g;
        ctx.fillRect(sx - 50, 0, 60, h);
      }

      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", resize);
      window.removeEventListener("resize", buildBins);
    };
  }, [height]);

  return (
    <canvas
      ref={ref}
      className="spectrum-strip"
      style={{ height, width: "100%", display: "block" }}
      aria-hidden
    />
  );
}
