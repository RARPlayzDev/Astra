/**
 * PARITY CONTRACT — browser port of `ewsmart/geo.py`.
 *
 * Bearing-only geolocation: each receiver measures a bearing to an emitter
 * stream with noise; the emitter position is the least-squares intersection of
 * the bearing lines. Stage 1 solves the linear perpendicular-distance problem
 * for a robust initial guess, stage 2 refines it by Gauss-Newton on the
 * *angular* residuals with an Armijo-style halving fallback, exactly as the
 * Python engine does (the GN stage is what keeps CEP in the few-km band
 * instead of the tens of km a linear-only solve produces).
 *
 * Bearings use the project convention: degrees from east, 0-360.
 */

export type Pt = readonly [number, number];
export type BearingLine = readonly [Pt, number];

/** Bearing in degrees (0-360) from a receiver to an emitter. */
export function geometricBearing(rx: Pt, emitter: Pt): number {
  const dx = emitter[0] - rx[0];
  const dy = emitter[1] - rx[1];
  return ((Math.atan2(dy, dx) * 180) / Math.PI + 360) % 360;
}

/** Perpendicular distance (km) of the true position from a bearing line. */
export function bearingErrorKm(rx: Pt, trueXy: Pt, bearingDeg: number): number {
  const th = (bearingDeg * Math.PI) / 180;
  const u: Pt = [Math.cos(th), Math.sin(th)];
  const d: Pt = [trueXy[0] - rx[0], trueXy[1] - rx[1]];
  return Math.abs(u[0] * d[1] - u[1] * d[0]);
}

export interface Triangulation {
  x: number; y: number;
  /** RMS perpendicular distance of the solution from the input lines (km). */
  residualKm: number;
}

/**
 * Weighted least-squares bearing intersection with Gauss-Newton refinement.
 * Returns `null` when the geometry is degenerate (parallel bearings).
 */
export function triangulate(lines: BearingLine[]): Triangulation | null {
  if (lines.length < 2) return null;

  // ---- stage 1: linear perpendicular-distance least squares -------------
  let m00 = 0, m01 = 0, m11 = 0, v0 = 0, v1 = 0;
  for (const [[px, py], deg] of lines) {
    const th = (deg * Math.PI) / 180;
    const ux = Math.cos(th), uy = Math.sin(th);
    const p00 = 1 - ux * ux, p01 = -ux * uy, p11 = 1 - uy * uy;
    m00 += p00; m01 += p01; m11 += p11;
    v0 += p00 * px + p01 * py;
    v1 += p01 * px + p11 * py;
  }
  const det = m00 * m11 - m01 * m01;
  let x: number, y: number;
  if (Math.abs(det) < 1e-9) {
    const n = lines.length;
    x = lines.reduce((a, l) => a + l[0][0], 0) / n;
    y = lines.reduce((a, l) => a + l[0][1], 0) / n;
  } else {
    x = (m11 * v0 - m01 * v1) / det;
    y = (m00 * v1 - m01 * v0) / det;
  }
  // ---- stage 2: Gauss-Newton on angular residuals -----------------------
  const xs = lines.map((l) => l[0]);
  const us = lines.map((l): Pt => {
    const th = (l[1] * Math.PI) / 180;
    return [Math.cos(th), Math.sin(th)];
  });

  const residuals = (px: number, py: number): number[] =>
    xs.map((rx, i) => {
      const dx = px - rx[0], dy = py - rx[1];
      const dist = Math.max(Math.hypot(dx, dy), 1e-6);
      return (us[i][0] * dy - us[i][1] * dx) / dist;
    });
  const sumsq = (px: number, py: number) =>
    residuals(px, py).reduce((a, r) => a + r * r, 0);

  let s0 = sumsq(x, y);
  for (let iter = 0; iter < 15; iter++) {
    const res = residuals(x, y);
    let h00 = 0, h01 = 0, h11 = 0, g0 = 0, g1 = 0;
    for (let i = 0; i < xs.length; i++) {
      const dx = x - xs[i][0], dy = y - xs[i][1];
      const dist = Math.max(Math.hypot(dx, dy), 1e-6);
      const j0 = -us[i][1] / dist, j1 = us[i][0] / dist;
      h00 += j0 * j0; h01 += j0 * j1; h11 += j1 * j1;
      g0 += j0 * res[i]; g1 += j1 * res[i];
    }
    const hd = h00 * h11 - h01 * h01;
    if (Math.abs(hd) < 1e-12) break;
    let step0 = (h11 * g0 - h01 * g1) / hd;
    let step1 = (h00 * g1 - h01 * g0) / hd;
    if (!isFinite(step0) || !isFinite(step1)) break;
    step0 = Math.max(-60, Math.min(60, step0));
    step1 = Math.max(-60, Math.min(60, step1));

    let improved = false;
    for (let halve = 0; halve < 8; halve++) {
      const s1 = sumsq(x + step0, y + step1);
      if (s1 < s0) {
        const moved = Math.hypot(step0, step1);
        x += step0; y += step1;
        improved = true;
        const converged = moved < 1e-6 || s0 - s1 < 1e-9;
        s0 = s1;
        if (converged) halve = 8;
        break;
      }
      step0 *= 0.5; step1 *= 0.5;
    }
    if (!improved) break;
  }

  const final = residuals(x, y);
  const residualKm = Math.sqrt(
    final.reduce((a, r) => a + r * r, 0) / final.length);
  return { x, y, residualKm };
}

/** Bearings from every receiver to a true emitter position, with noise. */
export function simulateBearings(trueXy: Pt, rxPositions: Pt[],
                                 sigmaDeg: number,
                                 rng: () => number): BearingLine[] {
  return rxPositions.map((rx) => {
    const bearing = geometricBearing(rx, trueXy);
    const u = Math.max(1e-12, rng());
    const gauss = Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng());
    return [rx, ((bearing + gauss * sigmaDeg) % 360 + 360) % 360] as BearingLine;
  });
}

export interface CepStats {
  n: number; mean: number | null; cep50: number | null; cep90: number | null;
}

/** CEP50 = median miss distance, CEP90 = 90th percentile. */
export function cepStats(errorsKm: number[]): CepStats {
  if (errorsKm.length === 0) return { n: 0, mean: null, cep50: null, cep90: null };
  const e = [...errorsKm].sort((a, b) => a - b);
  const pct = (p: number) => {
    const idx = (e.length - 1) * p;
    const lo = Math.floor(idx), hi = Math.ceil(idx);
    return lo === hi ? e[lo] : e[lo] + (e[hi] - e[lo]) * (idx - lo);
  };
  return {
    n: e.length,
    mean: e.reduce((a, b) => a + b, 0) / e.length,
    cep50: pct(0.5),
    cep90: pct(0.9),
  };
}

/** Cooperative receiver ring used by the console (mirrors /api/geolocation). */
export function receiverRing(kRx = 3, radiusKm = 50): Pt[] {
  const out: Pt[] = [[0, 0]];
  for (let i = 1; i < kRx; i++) {
    const a = (2 * Math.PI * i) / kRx;
    out.push([+(radiusKm * Math.cos(a)).toFixed(2),
              +(radiusKm * Math.sin(a)).toFixed(2)]);
  }
  return out;
}
