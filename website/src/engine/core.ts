/**
 * PARITY CONTRACT
 * ===============
 * This module is the browser-side port of the ASTRA engine core.
 * It mirrors `ewsmart/environment.py`, `ewsmart/receiver.py` and the reward
 * scheme in `ewsmart/runner.py`. When behaviour changes in the Python engine,
 * update this file in the same change-set so the web Prototype Console stays a
 * faithful tester of the software. Differences that are inherent to the port
 * (RNG family, float ordering) are noted inline.
 *
 * Deliberate simplifications vs Python (documented, not behavioural drift):
 *  - mulberry32 PRNG instead of numpy PCG64 (scenario seeds are self-consistent
 *    inside the console; cross-platform slot-exact equality is not claimed).
 *  - Spatially scanning emitters use their illumination schedule directly
 *    (period/on-len), identical to how environment.py exposes them to the
 *    receiver - bearing is carried for fingerprints only.
 */

export type EmitterKind = "stationary" | "agile" | "periodic" | "spatial";

export interface Emitter {
  eid: number;
  kind: EmitterKind;
  threat: boolean;
  snrDb: number;
  freqMhz: number;
  bearingDeg: number;
  homeBand: number;
  hopSet: number[];
  dwell: number;
  period: number;
  onLen: number;
  offset: number;
  pwUs: number;
  xKm: number;
  yKm: number;
}

export interface Scenario {
  nBands: number;
  T: number;
  nStationary: number;
  nAgile: number;
  nPeriodic: number;
  nSpatial: number;
  nClutter: number;
  snrMeanDb: number;
  snrStdDb: number;
  periodRange: [number, number];
  freqMinMhz: number;
  freqMaxMhz: number;
}

export const DEFAULT_SCENARIO: Scenario = {
  nBands: 24, T: 3000,
  nStationary: 6, nAgile: 4, nPeriodic: 4, nSpatial: 3, nClutter: 8,
  snrMeanDb: 12, snrStdDb: 4,
  periodRange: [40, 400],
  freqMinMhz: 2000, freqMaxMhz: 18000,
};

/* ------------------------------ RNG -------------------------------------- */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const randn = (rng: () => number) => {
  const u = Math.max(1e-9, rng());
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng());
};
const bandFreq = (b: number, s: Scenario) =>
  s.freqMinMhz + (s.freqMaxMhz - s.freqMinMhz) * (b + 0.5) / s.nBands;

/* --------------------------- environment --------------------------------- */
export class RFEnvironment {
  readonly cfg: Scenario;
  readonly emitters: Emitter[] = [];
  private readonly rng: () => number;

  constructor(cfg: Scenario, seed: number) {
    this.cfg = cfg;
    this.rng = mulberry32(seed);
    const r = this.rng;
    let eid = 0;
    const pos = () => ({ ang: r() * 2 * Math.PI, rad: 40 * Math.sqrt(r()) });

    const add = (kind: EmitterKind, threat: boolean, home?: number) => {
      const { ang, rad } = pos();
      const band = home ?? Math.floor(r() * cfg.nBands);
      const p = kind === "stationary" || kind === "agile"
        ? 1 : Math.round(cfg.periodRange[0] + r() *
            (cfg.periodRange[1] - cfg.periodRange[0]));
      this.emitters.push({
        eid: eid++,
        kind, threat,
        snrDb: Math.max(2, cfg.snrMeanDb + randn(r) * cfg.snrStdDb),
        freqMhz: +(bandFreq(band, cfg) + randn(r) * 8).toFixed(1),
        bearingDeg: +((Math.atan2(rad * Math.sin(ang), rad * Math.cos(ang))
          * 180 / Math.PI % 360 + 360) % 360).toFixed(1),
        homeBand: band,
        hopSet: kind === "agile"
          ? Array.from({ length: 3 + Math.floor(r() * 4) },
              () => Math.floor(r() * cfg.nBands))
          : [],
        dwell: 3 + Math.floor(r() * 6),
        period: p,
        onLen: 2 + Math.floor(r() * 4),
        offset: Math.floor(r() * Math.max(1, p)),
        pwUs: +(0.5 + r() * 4).toFixed(1),
        xKm: +(rad * Math.cos(ang)).toFixed(2),
        yKm: +(rad * Math.sin(ang)).toFixed(2),
      });
    };

    const half = (n: number) => Math.max(1, Math.floor(n / 2));
    for (let i = 0; i < cfg.nStationary; i++) add("stationary", i < half(cfg.nStationary));
    for (let i = 0; i < cfg.nAgile; i++) add("agile", i < half(cfg.nAgile));
    for (let i = 0; i < cfg.nPeriodic; i++) add("periodic", i < half(cfg.nPeriodic));
    for (let i = 0; i < cfg.nSpatial; i++) add("spatial", false);
    for (let i = 0; i < cfg.nClutter; i++) add("stationary", false);
  }

  transmitting(e: Emitter, t: number): boolean {
    switch (e.kind) {
      case "stationary": return true;
      case "agile": return true;                 // always audible somewhere; band moves
      case "periodic":
      case "spatial": {
        if (e.period <= 1) return true;
        return ((t - e.offset) % e.period) < e.onLen;
      }
    }
  }

  agileBand(e: Emitter, t: number): number {
    if (e.kind !== "agile") return e.homeBand;
    const idx = Math.floor(t / e.dwell);
    return e.hopSet[idx % e.hopSet.length];
  }

  emittersAt(band: number, t: number): Emitter[] {
    const out: Emitter[] = [];
    for (const e of this.emitters) {
      if (!this.transmitting(e, t)) continue;
      const b = this.agileBand(e, t);
      if (b === band) out.push(e);
    }
    return out;
  }

  nextOnStart(e: Emitter, afterT: number): number | null {
    if (e.kind !== "periodic" && e.kind !== "spatial") return null;
    const p = Math.max(1, e.period);
    let s = e.offset + Math.ceil(Math.max(0, afterT - e.offset) / p) * p;
    while (s <= afterT) s += p;
    return s;
  }

  nThreats(): number {
    return this.emitters.filter((e) => e.threat).length;
  }
}

/* ------------------------------ receiver --------------------------------- */
export interface DwellResult {
  hit: boolean;
  falseAlarm: boolean;
  truthPresent: boolean;
  strongestSnrDb: number;
  detections: { snrDb: number; aoaDeg: number; eid: number }[];
}

export class ESReceiver {
  private rng: () => number;
  constructor(private env: RFEnvironment, seed: number,
              public pdMidOffset = 6, private pdK = 3) {
    this.rng = mulberry32(seed ^ 0x9e3779b9);
  }
  private detectionProb(snrDb: number) {
    const z = (snrDb - (-10 + this.pdMidOffset)) / this.pdK;
    return 0.97 / (1 + Math.exp(-z));
  }
  dwell(band: number, t: number): DwellResult {
    const ems = this.env.emittersAt(band, t);
    const dets: DwellResult["detections"] = [];
    for (const e of ems) {
      if (this.rng() < this.detectionProb(e.snrDb)) {
        dets.push({
          snrDb: e.snrDb,
          aoaDeg: (e.bearingDeg + this.rng() * 5 - 2.5 + 360) % 360,
          eid: e.eid,
        });
      }
    }
    dets.sort((a, b) => b.snrDb - a.snrDb);
    let falseAlarm = false;
    if (dets.length === 0 && ems.length === 0 && this.rng() < 0.0004) falseAlarm = true;
    return {
      hit: dets.length > 0 || falseAlarm,
      falseAlarm,
      truthPresent: ems.length > 0,
      strongestSnrDb: dets[0]?.snrDb ?? Number.NEGATIVE_INFINITY,
      detections: dets,
    };
  }
}

/* ------------------------------- rewards --------------------------------- */
export const REWARD = {
  threat: 1.0, clutter: 0.15, empty: -0.05, falseAlarm: -0.08,
  firstThreatBonus: 1.5,
} as const;

export function stepReward(
  env: RFEnvironment, res: DwellResult, firstIntercept: Map<number, number>,
): number {
  if (res.falseAlarm) return REWARD.falseAlarm;
  if (!res.hit) return REWARD.empty;
  // credit assignment mirrors runner.step_reward(): value of the strongest
  // detection plus a one-time bonus per newly intercepted emitter.
  const lead = env.emitters.find(
    (e) => e.eid === res.detections[0]?.eid) ?? null;
  let r = lead?.threat ? REWARD.threat : REWARD.clutter;
  for (const d of res.detections) {
    if (!firstIntercept.has(d.eid)) {
      firstIntercept.set(d.eid, -1);            // slot filled by caller
      const e = env.emitters.find((x) => x.eid === d.eid);
      if (e?.threat) r += REWARD.firstThreatBonus;
    }
  }
  return r;
}
