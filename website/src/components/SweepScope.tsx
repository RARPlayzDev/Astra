/**
 * SweepScope — the live instrument on the landing page.
 *
 * One ES receiver sweeping a 24-band spectrum: the beam rotates, emitters blip
 * as the beam crosses them, and lock marks persist where a periodic emitter
 * stayed phase-locked. Deliberately cheap: one rAF loop, paused whenever it
 * scrolls out of view, and a single static frame under prefers-reduced-motion.
 */
import { useEffect, useRef } from "react";

type Emitter = {
  a: number;      // angle, radians
  r: number;      // radius, 0..1
  period: number; // slots between transmissions
  next: number;   // next transmission slot
  agile: boolean; // hops frequency instead of keeping a rhythm
};

const N_BANDS = 24;

export default function SweepScope({ height = 380 }: { height?: number }) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const readout = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;

    const reduced =
      typeof matchMedia === "function" &&
      matchMedia("(prefers-reduced-motion: reduce)").matches;

    let w = 0;
    let h = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const r = cv.getBoundingClientRect();
      w = r.width; h = r.height;
      cv.width = Math.round(w * dpr);
      cv.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();

    /* deterministic so the instrument looks identical on every reload */
    const rnd = (seed: number) => {
      const x = Math.sin(seed * 12.9898) * 43758.5453;
      return x - Math.floor(x);
    };

    const emitters: Emitter[] = Array.from({ length: 9 }, (_, i) => ({
      a: rnd(i + 1) * Math.PI * 2,
      r: 0.3 + rnd(i + 11) * 0.62,
      period: 9 + Math.floor(rnd(i + 21) * 26),
      next: Math.floor(rnd(i + 31) * 20),
      agile: rnd(i + 41) > 0.68,
    }));

    const locks: { a: number; r: number; life: number }[] = [];
    const flashes: { a: number; r: number; life: number; agile: boolean }[] = [];
    let slot = 0;
    let beam = -Math.PI / 2;
    let raf = 0;
    let last = 0;
    let acc = 0;
    let live = true;

    const R = () => Math.min(w, h) * 0.46;

    /* ── polar grid, band ring, sweep beam, blips ── */
    const drawBase = () => {
      const cx = w / 2, cy = h / 2, r = R();
      ctx.clearRect(0, 0, w, h);

      ctx.lineWidth = 1;
      for (let i = 1; i <= 4; i++) {
        ctx.strokeStyle = "rgba(111, 158, 199, 0.15)";
        ctx.beginPath();
        ctx.arc(cx, cy, (r / 4) * i, 0, Math.PI * 2);
        ctx.stroke();
      }
      for (let i = 0; i < N_BANDS; i++) {
        const ang = (i / N_BANDS) * Math.PI * 2 - Math.PI / 2;
        ctx.strokeStyle = i % 6 === 0
          ? "rgba(207, 164, 83, 0.20)" : "rgba(111, 158, 199, 0.09)";
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(ang) * r, cy + Math.sin(ang) * r);
        ctx.stroke();
      }
      for (let i = 0; i < N_BANDS; i++) {
        const a = (i / N_BANDS) * Math.PI * 2 - Math.PI / 2;
        const busy = emitters.some((e) => {
          const d = Math.abs(((e.a - a + Math.PI * 3) % (Math.PI * 2)) - Math.PI);
          return d < 0.22;
        });
        ctx.fillStyle = busy
          ? "rgba(111, 158, 199, 0.55)" : "rgba(111, 158, 199, 0.15)";
        ctx.fillRect(
          cx + Math.cos(a) * (r + 13) - 2,
          cy + Math.sin(a) * (r + 13) - 4, 4, 8);
      }
    };

    const drawBeam = () => {
      const cx = w / 2, cy = h / 2, r = R();
      const anyCtx = ctx as CanvasRenderingContext2D & {
        createConicGradient?: (s: number, x: number, y: number) => CanvasGradient;
      };
      if (typeof anyCtx.createConicGradient === "function") {
        const g = anyCtx.createConicGradient(beam, cx, cy);
        g.addColorStop(0, "rgba(207, 164, 83, 0.26)");
        g.addColorStop(0.07, "rgba(207, 164, 83, 0.09)");
        g.addColorStop(0.2, "rgba(207, 164, 83, 0)");
        g.addColorStop(1, "rgba(207, 164, 83, 0)");
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.strokeStyle = "rgba(207, 164, 83, 0.8)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(beam) * r, cy + Math.sin(beam) * r);
      ctx.stroke();
    };

    const drawMarks = () => {
      const cx = w / 2, cy = h / 2, r = R();
      for (const l of locks) {
        const x = cx + Math.cos(l.a) * l.r * r;
        const y = cy + Math.sin(l.a) * l.r * r;
        ctx.strokeStyle = `rgba(207, 164, 83, ${0.14 + l.life * 0.5})`;
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(x, y, 7, 0, Math.PI * 2); ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x - 10, y); ctx.lineTo(x + 10, y);
        ctx.moveTo(x, y - 10); ctx.lineTo(x, y + 10);
        ctx.stroke();
      }
      for (const f of flashes) {
        const x = cx + Math.cos(f.a) * f.r * r;
        const y = cy + Math.sin(f.a) * f.r * r;
        ctx.fillStyle = f.agile
          ? `rgba(111, 158, 199, ${f.life})`
          : `rgba(207, 164, 83, ${f.life})`;
        ctx.beginPath();
        ctx.arc(x, y, f.agile ? 3.4 : 4.6, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    const paint = () => {
      drawBase();
      drawBeam();
      drawMarks();
      const cx = w / 2, cy = h / 2;
      ctx.fillStyle = "rgba(207, 164, 83, 0.9)";
      ctx.beginPath();
      ctx.arc(cx, cy, 2.5, 0, Math.PI * 2);
      ctx.fill();
    };

    /* ── the loop: advance the sweep, fire transmitters once per slot ── */
    const tick = (t: number) => {
      raf = requestAnimationFrame(tick);
      if (!live) { last = t; return; }
      const dt = last ? Math.min(50, t - last) : 16;
      last = t;

      beam += dt * 0.0012;
      acc += dt;
      while (acc >= 380) {
        acc -= 380;
        slot++;
        for (const e of emitters) {
          if (slot >= e.next) {
            e.next = slot + e.period;
            flashes.push({ a: e.a, r: e.r, life: 1, agile: e.agile });
            if (!e.agile && rnd(slot + e.r * 97) > 0.25) {
              locks.push({ a: e.a, r: e.r, life: 1 });
              if (locks.length > 26) locks.shift();
            }
            if (e.agile) e.a += (rnd(slot * 3.7 + e.r) - 0.5) * 1.4;
          }
        }
      }
      for (let i = flashes.length - 1; i >= 0; i--) {
        flashes[i].life -= dt * 0.0009;
        if (flashes[i].life <= 0) flashes.splice(i, 1);
      }
      for (const l of locks) l.life = Math.max(0.12, l.life - dt * 0.00006);

      if (readout.current) {
        const band = 1 + (Math.abs(Math.round((beam / (Math.PI * 2)) * N_BANDS)) % N_BANDS);
        const sweep = Math.round((((beam + Math.PI / 2) % (Math.PI * 2)) / (Math.PI * 2)) * 100);
        readout.current.textContent =
          `SLOT ${String(slot).padStart(4, "0")}  ·  BAND ${String(band).padStart(2, "0")}` +
          `  ·  SWEEP ${String(Math.max(0, sweep)).padStart(3, "0")}%` +
          `  ·  LOCKS ${String(locks.length).padStart(2, "0")}`;
      }
      paint();
    };



    paint();
    if (reduced) {
      const ro = new ResizeObserver(() => { resize(); paint(); });
      ro.observe(cv);
      return () => ro.disconnect();
    }
    raf = requestAnimationFrame(tick);
    const io = new IntersectionObserver(
      ([e]) => { live = e.isIntersecting; },
      { threshold: 0.02 }
    );
    io.observe(cv);
    const ro = new ResizeObserver(() => { resize(); paint(); });
    ro.observe(cv);
    return () => { cancelAnimationFrame(raf); io.disconnect(); ro.disconnect(); };
  }, []);

  return (
    <div className="sweep-instrument">
      <canvas ref={ref} style={{ height }} aria-hidden />
      <div className="sweep-readout mono" ref={readout}>
        SLOT 0000 · BAND 01 · SWEEP 000% · LOCKS 00
      </div>
    </div>
  );
}
