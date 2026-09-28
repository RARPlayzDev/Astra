/**
 * Browser analogue of ewsmart/identification.py - JC Wise-style library
 * matching over measured stream fingerprints. PARITY CONTRACT applies.
 */
import { mulberry32, type RFEnvironment } from "./core";

export interface LibraryEntry {
  name: string; cls: string;
  freqRange: [number, number]; pwRange: [number, number];
  scanRange: [number, number] | null; threat: "HIGH" | "MEDIUM" | "LOW";
}

export const LIBRARY: LibraryEntry[] = [
  { name: "SNOW DRIFT", cls: "S-band acquisition", freqRange: [2800, 3300], pwRange: [0.5, 4], scanRange: [40, 200], threat: "HIGH" },
  { name: "FLAT FACE", cls: "L-band search", freqRange: [1800, 2400], pwRange: [0.8, 6], scanRange: [60, 250], threat: "MEDIUM" },
  { name: "POP GROUP", cls: "E/F-band acquisition", freqRange: [4800, 6200], pwRange: [0.3, 3], scanRange: [30, 150], threat: "MEDIUM" },
  { name: "FLAP LID-A", cls: "X-band engagement", freqRange: [8600, 10200], pwRange: [0.8, 8], scanRange: [20, 120], threat: "HIGH" },
  { name: "SQUARE PAIR", cls: "X-band guidance", freqRange: [8800, 9600], pwRange: [0.2, 2], scanRange: null, threat: "HIGH" },
  { name: "BIG BACK", cls: "Ku-band surveillance", freqRange: [12000, 14500], pwRange: [1, 20], scanRange: [25, 160], threat: "MEDIUM" },
  { name: "CROSS SLOT", cls: "X-band navigation", freqRange: [8800, 9800], pwRange: [0.05, 1.2], scanRange: [40, 200], threat: "LOW" },
  { name: "HALF PLATE", cls: "Ku-band height finder", freqRange: [12500, 13500], pwRange: [2, 12], scanRange: [15, 90], threat: "HIGH" },
  { name: "TIN SHIELD", cls: "S-band long-range", freqRange: [2600, 3400], pwRange: [3, 25], scanRange: [100, 400], threat: "HIGH" },
  { name: "LONG TRACK", cls: "E-band search", freqRange: [2400, 2900], pwRange: [1, 10], scanRange: [80, 300], threat: "MEDIUM" },
];

const inRange = (v: number, r: [number, number] | null, slack = 0.15) => {
  if (r === null) return true;
  const pad = (r[1] - r[0]) * slack;
  return r[0] - pad <= v && v <= r[1] + pad;
};

/** 1 inside the range, decaying linearly to 0 one range-width outside it. */
const fit = (v: number, r: [number, number]) => {
  const width = Math.max(r[1] - r[0], 1e-6);
  if (v < r[0]) return Math.max(0, 1 - (r[0] - v) / width);
  if (v > r[1]) return Math.max(0, 1 - (v - r[1]) / width);
  return 1;
};

export interface Fingerprint {
  freqCenterMhz: number; pwMeanUs: number; scanPeriod: number | null;
}

/**
 * identify(): returns [entry|null, confidence]. Frequency is a hard gate (a
 * 5 % band tolerance, as in ewsmart/identification.py); pulse width and scan
 * rhythm contribute graded fit, so confidence reflects how well the *measured*
 * fingerprint sits inside the entry rather than a pass/fail count.
 */
export function identify(fp: Fingerprint,
                         library: LibraryEntry[] = LIBRARY):
    [LibraryEntry | null, number] {
  let best: LibraryEntry | null = null, bestScore = 0;
  for (const e of library) {
    if (!inRange(fp.freqCenterMhz, e.freqRange, 0.05)) continue;
    const pwFit = fit(fp.pwMeanUs, e.pwRange);
    const scanFit = e.scanRange === null || fp.scanPeriod === null
      ? 1 : fit(fp.scanPeriod, e.scanRange);
    const score = (2 * 1 + pwFit + scanFit) / 4;
    if (score > bestScore) { best = e; bestScore = score; }
  }
  return best !== null && bestScore >= 0.5 ? [best, bestScore] : [null, 0];
}

export interface IdRow {
  eid: number; identified: string; cls: string; threat: string;
  confidence: number; pulses: number; ground_truth: string; correct: boolean;
  /** Measured centre frequency (MHz) and pulse width (us). */
  freqMhz: number; pwUs: number; snrDb: number;
}

interface StreamInfo {
  freqSum: number; pwSum: number; n: number;
  hitTimes: number[];
  aoaSin: number; aoaCos: number; aoaN: number;
  snrMax: number;
}

/** Build measured fingerprints per emitter from dwell observations. */
export class StreamCollector {
  private streams = new Map<number, StreamInfo>();

  /**
   * Fold one dwell's detections into the stream fingerprints. Each sample is a
   * *measurement*: the emitter's true centre frequency and pulse width carry a
   * per-emitter systematic bias scaled by how well the signal is heard (weak
   * or LPI streams fingerprint poorly, exactly as section 21.4 of the manual
   * describes), and the AOA samples are the receiver's measured bearings.
   */
  observe(detections: { eid: number; aoaDeg?: number; snrDb?: number }[],
          t: number): void {
    for (const d of detections) {
      const meta = this.emitters.get(d.eid);
      if (!meta) continue;
      const s = this.streams.get(d.eid) ?? {
        freqSum: 0, pwSum: 0, n: 0, hitTimes: [],
        aoaSin: 0, aoaCos: 0, aoaN: 0, snrMax: Number.NEGATIVE_INFINITY,
      };
      s.freqSum += meta.freqMhz * meta.freqBias;
      s.pwSum += meta.pwUs * meta.pwBias;
      s.n += 1;
      s.hitTimes.push(t);
      if (d.aoaDeg != null) {
        const r = (d.aoaDeg * Math.PI) / 180;
        s.aoaSin += Math.sin(r); s.aoaCos += Math.cos(r); s.aoaN += 1;
      }
      if (d.snrDb != null) s.snrMax = Math.max(s.snrMax, d.snrDb);
      this.streams.set(d.eid, s);
    }
  }

  attach(env: RFEnvironment): void {
    for (const e of env.emitters) {
      // deterministic per-emitter measurement bias (reproducible per seed)
      const rng = mulberry32(
        (0x9e3779b9 ^ Math.imul(e.eid + 1, 2246822519)) >>> 0);
      const quality = Math.max(0, Math.min(1, (e.snrDb + 5) / 20));
      const freqSpread = 0.02 * (1.2 - quality);
      const pwSpread = 0.26 * (1.2 - quality);
      this.emitters.set(e.eid, {
        freqMhz: e.freqMhz, pwUs: e.pwUs, kind: e.kind,
        period: e.period, onLen: e.onLen, offset: e.offset,
        freqBias: 1 + (rng() - 0.5) * freqSpread,
        pwBias: 1 + (rng() - 0.5) * pwSpread,
      });
    }
  }
  private emitters = new Map<number, {
    freqMhz: number; pwUs: number; kind: string;
    period: number; onLen: number; offset: number;
    freqBias: number; pwBias: number }>();

  /** Circular-mean measured bearing (deg) per stream, for triangulation. */
  measuredAoa(): Map<number, number> {
    const out = new Map<number, number>();
    for (const [eid, s] of this.streams) {
      if (s.aoaN < 2) continue;
      const deg = (Math.atan2(s.aoaSin, s.aoaCos) * 180) / Math.PI;
      out.set(eid, (deg + 360) % 360);
    }
    return out;
  }

  /** Peak SNR (dB) heard for a stream, used for AOA error weighting. */
  snrOf(eid: number): number {
    const s = this.streams.get(eid);
    return s && isFinite(s.snrMax) ? s.snrMax : 12;
  }

  /** Streams with enough evidence to identify (>= 3 intercepted pulses). */
  streamCount(minHits = 3): number {
    let n = 0;
    for (const s of this.streams.values()) if (s.n >= minHits) n += 1;
    return n;
  }

  /** Rows for emitters with enough evidence: HIGH threat first, then confidence. */
  report(limit = 10): IdRow[] {
    const rows: IdRow[] = [];
    for (const [eid, s] of this.streams) {
      if (s.n < 3) continue;
      const meta = this.emitters.get(eid)!;
      // measured fingerprint (not the emitter's true specification)
      const measuredFreq = s.freqSum / s.n;
      const measuredPw = s.pwSum / s.n;
      // observed rhythm from intercept gaps, when the emitter is a scanner
      let scanPeriod: number | null = null;
      if (meta.kind === "periodic" || meta.kind === "spatial") {
        const ts = s.hitTimes;
        if (ts.length >= 3) {
          const diffs: number[] = [];
          for (let i = 1; i < Math.min(ts.length, 24); i++)
            diffs.push(ts[i] - ts[i - 1]);
          diffs.sort((x, y) => x - y);
          scanPeriod = diffs[Math.floor(diffs.length / 2)];
        }
      }
      const [entry, conf] = identify({
        freqCenterMhz: measuredFreq,
        pwMeanUs: measuredPw,
        scanPeriod,
      });
      const truthEntry = identify({
        freqCenterMhz: meta.freqMhz,
        pwMeanUs: meta.pwUs,
        scanPeriod: meta.kind === "periodic" || meta.kind === "spatial"
          ? meta.period : null,
      })[0];
      const identified = entry?.name ?? null;
      const truth = truthEntry?.name ?? null;
      rows.push({
        eid,
        identified: identified ?? "UNKNOWN",
        cls: entry?.cls ?? "-",
        threat: (entry?.threat ?? "-") as string,
        confidence: +conf.toFixed(2),
        pulses: s.n,
        ground_truth: truth ?? "UNKNOWN",
        correct: identified === truth,
        freqMhz: +measuredFreq.toFixed(1),
        pwUs: +measuredPw.toFixed(2),
        snrDb: +this.snrOf(eid).toFixed(1),
      });
    }
    const rank: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };
    rows.sort((a, b) =>
      (rank[a.threat] ?? 3) - (rank[b.threat] ?? 3) ||
      b.confidence - a.confidence || b.pulses - a.pulses);
    return rows.slice(0, limit);
  }
}

