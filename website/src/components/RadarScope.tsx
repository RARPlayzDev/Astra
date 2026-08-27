import { useEffect, useRef, useCallback } from "react";

interface Blip {
  x: number;
  y: number;
  type: "active" | "caution" | "hostile";
  phase: number;
  size: number;
}

const BLIPS: Blip[] = [
  { x: 0.35, y: -0.42, type: "active", phase: 0, size: 2.5 },
  { x: 0.58, y: -0.15, type: "caution", phase: 1.2, size: 3 },
  { x: -0.32, y: 0.48, type: "hostile", phase: 0.5, size: 3.2 },
  { x: 0.20, y: 0.30, type: "active", phase: 2.0, size: 2 },
  { x: -0.52, y: -0.22, type: "caution", phase: 0.8, size: 2.5 },
  { x: 0.44, y: 0.50, type: "hostile", phase: 1.5, size: 3.2 },
  { x: -0.18, y: -0.55, type: "active", phase: 0.3, size: 2 },
  { x: 0.60, y: 0.18, type: "active", phase: 1.8, size: 2.5 },
  { x: -0.48, y: 0.28, type: "caution", phase: 0.7, size: 2.5 },
  { x: 0.12, y: -0.62, type: "hostile", phase: 2.2, size: 3 },
  { x: -0.25, y: 0.15, type: "active", phase: 1.0, size: 2 },
  { x: 0.40, y: -0.35, type: "caution", phase: 0.4, size: 2.5 },
];

export default function RadarScope({ size = 400 }: { size?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const angleRef = useRef(0);
  const frameRef = useRef(0);
  const trailRef = useRef<HTMLCanvasElement | null>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = size * dpr;
    const h = size * dpr;
    canvas.width = w;
    canvas.height = h;

    const cx = w / 2;
    const cy = h / 2;
    const R = w * 0.42;

    // Trail buffer
    if (!trailRef.current) trailRef.current = document.createElement("canvas");
    const trail = trailRef.current;
    if (trail.width !== w || trail.height !== h) { trail.width = w; trail.height = h; }
    const tc = trail.getContext("2d")!;

    // Decay trail
    tc.globalCompositeOperation = "destination-out";
    tc.fillStyle = "rgba(0,0,0,0.02)";
    tc.fillRect(0, 0, w, h);
    tc.globalCompositeOperation = "source-over";

    // Slower rotation — 0.003 rad/frame ≈ 11.4 seconds per revolution
    angleRef.current += 0.003;
    const angle = angleRef.current;
    frameRef.current++;

    // ── Draw sweep on trail ──
    tc.save();
    tc.translate(cx, cy);
    tc.rotate(angle);
    tc.beginPath();
    tc.moveTo(0, 0);
    tc.arc(0, 0, R, -0.06, 0.06);
    tc.closePath();
    const sweepGrad = tc.createRadialGradient(0, 0, 0, 0, 0, R);
    sweepGrad.addColorStop(0, "rgba(200, 200, 200, 0.35)");
    sweepGrad.addColorStop(0.3, "rgba(200, 200, 200, 0.15)");
    sweepGrad.addColorStop(0.7, "rgba(200, 200, 200, 0.04)");
    sweepGrad.addColorStop(1, "rgba(200, 200, 200, 0)");
    tc.fillStyle = sweepGrad;
    tc.fill();
    // Beam line
    tc.beginPath();
    tc.moveTo(0, 0);
    tc.lineTo(R, 0);
    tc.strokeStyle = "rgba(240, 240, 240, 0.7)";
    tc.lineWidth = 1.2 * dpr;
    tc.stroke();
    tc.restore();

    // ── Main canvas ──
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, w, h);

    // Subtle radial glow at center
    const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.6);
    glow.addColorStop(0, "rgba(200, 210, 220, 0.04)");
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, h);

    // Vignette
    const vig = ctx.createRadialGradient(cx, cy, R * 0.3, cx, cy, R * 1.1);
    vig.addColorStop(0, "rgba(0,0,0,0)");
    vig.addColorStop(1, "rgba(0,0,0,0.65)");
    ctx.fillStyle = vig;
    ctx.fillRect(0, 0, w, h);

    // Concentric rings — brighter
    [0.25, 0.5, 0.75, 1.0].forEach((f) => {
      ctx.beginPath();
      ctx.arc(cx, cy, R * f, 0, Math.PI * 2);
      ctx.strokeStyle = f === 1.0 ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.10)";
      ctx.lineWidth = (f === 1.0 ? 1.2 : 0.7) * dpr;
      ctx.stroke();
    });

    // Crosshair — brighter
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.lineWidth = 0.7 * dpr;
    ctx.beginPath();
    ctx.moveTo(cx - R, cy); ctx.lineTo(cx + R, cy);
    ctx.moveTo(cx, cy - R); ctx.lineTo(cx, cy + R);
    ctx.stroke();

    // Degree labels — brighter
    ctx.fillStyle = "rgba(255,255,255,0.28)";
    ctx.font = `${8 * dpr}px monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let d = 0; d < 360; d += 30) {
      const r = (d * Math.PI) / 180;
      ctx.fillText(`${d}`, cx + Math.cos(r) * (R + 16 * dpr), cy + Math.sin(r) * (R + 16 * dpr));
    }

    // Outer tick marks — brighter
    ctx.strokeStyle = "rgba(255,255,255,0.18)";
    ctx.lineWidth = 0.8 * dpr;
    for (let d = 0; d < 360; d += 5) {
      const r = (d * Math.PI) / 180;
      const major = d % 30 === 0;
      const len = (major ? 6 : 2.5) * dpr;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(r) * R, cy + Math.sin(r) * R);
      ctx.lineTo(cx + Math.cos(r) * (R + len), cy + Math.sin(r) * (R + len));
      ctx.stroke();
    }

    // Range labels — brighter
    ctx.font = `${8 * dpr}px monospace`;
    ctx.fillStyle = "rgba(255,255,255,0.30)";
    ctx.textAlign = "left";
    [25, 50, 75, 100].forEach((km, i) => {
      ctx.fillText(`${km}km`, cx + 5 * dpr, cy - R * [0.25, 0.5, 0.75, 1.0][i] + 12 * dpr);
    });

    // Composite trail
    ctx.globalAlpha = 0.92;
    ctx.drawImage(trail, 0, 0);
    ctx.globalAlpha = 1;

    // ── Blips — brighter ──
    const t = frameRef.current * 0.015;
    const BLIP_COLORS: Record<string, string> = {
      active: "#8ab0d8",
      caution: "#d8b860",
      hostile: "#d06060",
    };
    BLIPS.forEach((b) => {
      const bx = cx + b.x * R;
      const by = cy + b.y * R;
      const bAngle = Math.atan2(b.y, b.x);
      let diff = angle - bAngle;
      diff = ((diff % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
      const fade = diff < 4.5 ? Math.max(0, 1 - diff / 4.5) : 0;
      if (fade <= 0) return;

      const pulse = 0.6 + 0.4 * Math.sin(t + b.phase);
      const sz = b.size * dpr;
      const col = BLIP_COLORS[b.type];

      // Outer glow
      ctx.globalAlpha = fade * 0.25 * pulse;
      ctx.beginPath();
      ctx.arc(bx, by, sz * 3, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();

      // Core dot
      ctx.globalAlpha = fade * (0.7 + 0.3 * pulse);
      ctx.beginPath();
      ctx.arc(bx, by, sz * 0.6, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();
      ctx.globalAlpha = 1;
    });

    // Center dot — brighter
    ctx.beginPath();
    ctx.arc(cx, cy, 2 * dpr, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255,255,255,0.55)";
    ctx.fill();

    requestAnimationFrame(draw);
  }, [size]);

  useEffect(() => {
    const id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [draw]);

  return (
    <div className="radar-wrap">
      <canvas ref={canvasRef} style={{ width: size, height: size }} />
    </div>
  );
}
