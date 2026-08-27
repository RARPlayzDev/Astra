/**
 * Browser analogue of ewsmart/identification.py - JC Wise-style library
 * matching over measured stream fingerprints. PARITY CONTRACT applies.
 */
import type { RFEnvironment } from "./core";

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

export interface Fingerprint {
  freqCenterMhz: number; pwMeanUs: number; scanPeriod: number | null;
}

/** identify(): returns [entry|null, confidence]. */
export function identify(fp: Fingerprint,
                         library: LibraryEntry[] = LIBRARY):
    [LibraryEntry | null, number] {
  let best: LibraryEntry | null = null, bestScore = 0;
  for (const e of library) {
    const freqOk = inRange(fp.freqCenterMhz, e.freqRange, 0.05);
    if (!freqOk) continue;
    const pwOk = inRange(fp.pwMeanUs, e.pwRange);
    const scanOk = e.scanRange === null || fp.scanPeriod === null ||
      inRange(fp.scanPeriod, e.scanRange, 0.35);
    const score = (2 * Number(freqOk) + Number(pwOk) + Number(scanOk)) / 4;
    if (score > bestScore) { best = e; bestScore = score; }
  }
  return best !== null && bestScore >= 0.5 ? [best, bestScore] : [null, 0];
}

export interface IdRow {
  eid: number; identified: string; cls: string; threat: string;
  confidence: number; pulses: number; ground_truth: string; correct: boolean;
}

interface StreamInfo {
  freqSum: number; pwSum: number; n: number;
  hitTimes: number[];
}

/** Build measured fingerprints per emitter from dwell observations. */
export class StreamCollector {
  private streams = new Map<number, StreamInfo>();

  observe(eidsOnBand: number[],
          detections: { eid: number }[], t: number): void {
    for (const d of detections) {
      const s = this.streams.get(d.eid) ??
        { freqSum: 0, pwSum: 0, n: 0, hitTimes: [] };
      const e = this.emitters.get(d.eid);
      if (e) {
        s.freqSum += e.freqMhz; s.pwSum += e.pwUs; s.n += 1;
        s.hitTimes.push(t);
        this.streams.set(d.eid, s);
      }
    }
    void eidsOnBand;
  }

  attach(env: RFEnvironment): void {
    for (const e of env.emitters) {
      this.emitters.set(e.eid, {
        freqMhz: e.freqMhz, pwUs: e.pwUs, kind: e.kind,
        period: e.period, onLen: e.onLen, offset: e.offset,
      });
    }
  }
  private emitters = new Map<number, {
    freqMhz: number; pwUs: number; kind: string;
    period: number; onLen: number; offset: number }>();

  /** Rows for emitters with enough evidence, sorted by confidence. */
  report(limit = 10): IdRow[] {
    const rows: IdRow[] = [];
    for (const [eid, s] of this.streams) {
      if (s.n < 3) continue;
      const meta = this.emitters.get(eid)!;
      // measured fingerprint
      let scanPeriod: number | null = null;
      if (meta.kind === "periodic" || meta.kind === "spatial") {
        // estimate from intercept gaps when we have them
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
        freqCenterMhz: meta.freqMhz,
        pwMeanUs: meta.pwUs,
        scanPeriod,
      });
      const truthEntry = identify({
        freqCenterMhz: meta.freqMhz,
        pwMeanUs: meta.pwUs,
        scanPeriod: meta.kind === "periodic" || meta.kind === "spatial"
          ? meta.period : null,
      })[0];
      rows.push({
        eid,
        identified: entry?.name ?? "UNKNOWN",
        cls: entry?.cls ?? "-",
        threat: (entry?.threat ?? "-") as string,
        confidence: +conf.toFixed(2),
        pulses: s.n,
        ground_truth: truthEntry?.name ?? "UNKNOWN",
        correct: entry !== null &&
                 (entry?.name ?? "") === (truthEntry?.name ?? ""),
      });
    }
    rows.sort((a, b) => b.confidence - a.confidence || b.pulses - a.pulses);
    return rows.slice(0, limit);
  }
}
