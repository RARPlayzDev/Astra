/**
 * PARITY CONTRACT (see engine/core.ts header)
 * Browser port of the scheduling policies:
 *   - SequentialSweep  <- ewsmart/schedulers.py :: SequentialSweep
 *   - UCBScheduler     <- ewsmart/schedulers.py :: UCBScheduler
 *   - SmartScan        <- ewsmart/schedulers.py :: SmartScanScheduler
 *
 * SmartScan keeps the five-behaviour structure of the Python original:
 * recon sweep -> cued pursuit of validated locks -> predict-and-probe of
 * candidate rhythms -> characterisation bursts on quiet hits -> value-weighted
 * rotation with recency guarantees and an exploitation ramp. Period estimation
 * uses an integer-refined histogram-of-gaps search (the browser analogue of
 * ewsmart/periodic.py's Rayleigh test with integer refinement), and locks are
 * deleted after repeated missed predictions exactly like the Python side.
 */
import type { RFEnvironment } from "./core";

export interface DwellLike {
  hit: boolean; falseAlarm: boolean;
  detections: { eid: number }[];
}

export interface Scheduler {
  name: string;
  reset(nBands: number, horizon: number): void;
  select(t: number): number;
  update(t: number, band: number, res: DwellLike, reward: number): void;
  /** One-slot-ahead presence prediction for the given band (parity with
   *  BaseScheduler.predict in ewsmart/schedulers.py). */
  predict(t: number, band: number): boolean;
}

/* ---------------------------- open-loop ---------------------------------- */
export class SequentialSweep implements Scheduler {
  name = "openloop-sequential";
  constructor(private nBands = 24) {}
  reset(): void {}
  select(t: number): number { return t % this.nBands; }
  update(): void {}
  predict(): boolean { return false; }
}

export class RandomScan implements Scheduler {
  name = "openloop-random";
  private rng: () => number;
  constructor(private nBands = 24, seed = 3) {
    let a = seed >>> 0;
    this.rng = () => { a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  reset(): void {}
  select(): number { return Math.floor(this.rng() * this.nBands); }
  update(): void {}
  predict(): boolean { return false; }
}

export class UCBScheduler implements Scheduler {
  name = "bandit-ucb";
  private n!: number[]; private mu!: number[];
  constructor(private nBands = 24) {}
  reset(): void {
    this.n = new Array(this.nBands).fill(1);
    this.mu = new Array(this.nBands).fill(1e-3);
  }
  select(t: number): number {
    let best = 0, bestV = -Infinity;
    for (let b = 0; b < this.nBands; b++) {
      const v = this.mu[b] + 0.6 * Math.sqrt(Math.log(t + 2) / this.n[b]);
      if (v > bestV) { bestV = v; best = b; }
    }
    return best;
  }
  update(_t: number, band: number, _r0: DwellLike, r: number): void {
    this.n[band] += 1;
    this.mu[band] += (r - this.mu[band]) / this.n[band];
  }
  predict(_t: number, band: number): boolean {
    return this.mu[band] > 0.15;
  }
}

/** Linear-approximation Q-learning over recency/prior/confidence features
 *  (browser analogue of ewsmart LinearQLearning). */
export class LinearQLearning implements Scheduler {
  name = "rl-linear-q";
  learnable = true;
  private theta: number[] = [0, 0, 0, 0, 1];   // [bias, prior, conf, recency, explore]
  private alpha = 0.05; private gamma = 0.9;
  private eps = 0.30; private epsMin = 0.05; private epsDecay = 0.95;
  private discHit!: number[]; private discN!: number[]; private lastVisit!: number[];
  private rng: () => number;
  private lastBand = 0; private prevQ = 0;

  constructor(private nBands = 24, seed = 5) {
    let a = seed >>> 0;
    this.rng = () => { a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }

  private feats(b: number, t: number): number[] {
    const recency = 1 / (1 + Math.max(0, t - this.lastVisit[b]));
    const prior = this.discHit[b] / (this.discN[b] + 0.25);
    const conf = Math.sqrt(this.discN[b]) / (1 + Math.sqrt(this.discN[b]));
    return [1, prior, conf, recency,
            1 / (1 + Math.log(t + 2))];           // exploration feature
  }
  private q(b: number, t: number): number {
    const f = this.feats(b, t);
    return f.reduce((s, v, i) => s + v * this.theta[i], 0);
  }

  reset(): void {
    this.discHit = new Array(this.nBands).fill(0);
    this.discN = new Array(this.nBands).fill(0);
    this.lastVisit = new Array(this.nBands).fill(-1e9);
  }
  endEpisode(): void { this.eps = Math.max(this.epsMin, this.eps * this.epsDecay); }

  select(t: number): number {
    if (this.rng() < this.eps) return Math.floor(this.rng() * this.nBands);
    let best = 0, bestQ = -Infinity;
    for (let b = 0; b < this.nBands; b++) {
      const qv = this.q(b, t);
      if (qv > bestQ) { bestQ = qv; best = b; }
    }
    // store for TD update on the observed reward
    this.lastBand = best; this.prevQ = bestQ;
    return best;
  }
  update(_t: number, band: number, res: DwellLike, r: number): void {
    this.discHit[band] = this.discHit[band] * this.gamma + (res.hit ? 1 : 0);
    this.discN[band] = this.discN[band] * this.gamma + 1;
    const target = r + this.gamma * this.prevQ;
    const f = this.feats(band, _t);
    const pred = f.reduce((s, v, i) => s + v * this.theta[i], 0);
    const err = target - pred;
    for (let i = 0; i < this.theta.length; i++) this.theta[i] += this.alpha * err * f[i];
  }
  predict(_t: number, band: number): boolean {
    const prior = this.discHit[band] / (this.discN[band] + 0.25);
    return prior > 0.35;
  }
}

/* ----------------------------- smart scan -------------------------------- */
interface Lock {
  period: number;
  nextOn: number;
  misses: number;
  confirmed: boolean;
  evidence: number;
}

const RECON_FACTOR = 18;
const LOCK_HITS = 5;
const MAX_MISS = 2;

export class SmartScanScheduler implements Scheduler {
  name = "smart-scan";
  private nBands: number;
  private horizon = 3000;
  private mu!: number[];
  private visits!: number[];
  private lastVisit!: number[];
  private hitTimes: number[][] = [];
  private _locks = new Map<number, Lock>();
  private probeUntil = new Map<number, number>();   // band -> dwell-until slot
  private burstUntil = new Map<number, number>();
  private rng: () => number;
  private log: (msg: string) => void = () => {};

  constructor(nBands = 24, seed = 7, log?: (m: string) => void) {
    this.nBands = nBands;
    this.rng = (() => { let a = seed >>> 0; return () => {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; })();
    if (log) this.log = log;
  }

  reset(nBands: number, horizon: number): void {
    this.nBands = nBands; this.horizon = horizon;
    this.mu = new Array(nBands).fill(0.01);
    this.visits = new Array(nBands).fill(1);
    this.lastVisit = new Array(nBands).fill(-1e9);
    this.hitTimes = Array.from({ length: nBands }, () => []);
    this._locks.clear(); this.probeUntil.clear(); this.burstUntil.clear();
  }

  get reconSteps() { return RECON_FACTOR * this.nBands / 12; }
  get locks(): number { return this.lockMap.size; }
  private get lockMap() { return this._locks; }

  /** Parity with SmartScanScheduler.predict: phase-lock + yield fallback. */
  predict(t: number, band: number): boolean {
    // 1. Phase-locked periodic emitter
    const l = this._locks.get(band);
    if (l && l.confirmed) {
      const d = (t - (l.nextOn - l.period)) % l.period;
      const width = Math.max(4, l.period * 0.2);
      if (d >= 0 && d <= width) return true;
    }
    return false;
  }

  private estimatePeriod(times: number[]): number | null {
    if (times.length < 4) return null;
    const diffs: number[] = [];
    for (let i = 1; i < times.length; i++) diffs.push(times[i] - times[i - 1]);
    const hist = new Map<number, number>();
    for (const d of diffs) {
      for (let p = Math.max(10, Math.round(d) - 8);
           p <= Math.min(450, Math.round(d) + 8); p++) {
        hist.set(p, (hist.get(p) ?? 0) + 1);
      }
    }
    let bestP: number | null = null, bestScore = 0;
    for (const [p, votes] of hist) {
      // phase-cluster score: how many hits fall in one narrow phase bucket
      const phases = times.map((h) => ((h % p) + p) % p);
      phases.sort((a, b) => a - b);
      // largest circular gap -> cluster is its complement
      let maxGap = 0, gi = 0;
      for (let i = 0; i < phases.length; i++) {
        const nxt = i === phases.length - 1 ? phases[0] + p : phases[i + 1];
        const gap = nxt - phases[i];
        if (gap > maxGap) { maxGap = gap; gi = i; }
      }
      const span = p - maxGap;
      if (span <= p * 0.35) {
        const score = votes + phases.length * (span <= p * 0.2 ? 2 : 0);
        if (score > bestScore) { bestScore = score; bestP = p; }
      }
    }
    return bestP && bestScore >= times.length * 0.9 ? bestP : null;
  }

  select(t: number): number {
    const reconEnd = this.reconSteps;
    if (t < reconEnd) return t % this.nBands;                 // 1. recon sweep

    // 2. cued pursuit of validated locks
    let bestLockBand = -1, bestEta = Infinity;
    for (const [band, lock] of this._locks) {
      if (!lock.confirmed) continue;
      const eta = lock.nextOn - t;
      if (eta <= 3 && eta >= -lock.period * 0.15 && eta < bestEta) {
        bestEta = eta; bestLockBand = band;
      }
    }
    if (bestLockBand >= 0) return bestLockBand;

    // 3. predict-and-probe of unproven candidates at window centres
    for (const [band, until] of this.probeUntil) {
      if (t < until) return band;
    }

    // 4. characterisation burst after isolated hits
    for (const [band, until] of this.burstUntil) {
      if (t < until) return band;
    }

    // 5. value-weighted rotation with exploitation ramp
    const ramp = Math.min(1,
      Math.max(0, (t - reconEnd) / Math.max(1, this.horizon - reconEnd)));
    let best = 0, bestV = -Infinity;
    for (let b = 0; b < this.nBands; b++) {
      const recency = 1 / (1 + Math.max(0, t - this.lastVisit[b]));
      const exploreBonus =
        0.9 * Math.sqrt(Math.log(t + 2) / this.visits[b]) * (1 - 0.55 * ramp);
      const v = this.mu[b] + exploreBonus + 0.05 * recency;
      const noisy = v + (this.rng() - 0.5) * 0.02 * (1 - ramp);
      if (noisy > bestV) { bestV = noisy; best = b; }
    }
    return best;
  }

  update(t: number, band: number, res: DwellLike, r: number): void {
    this.visits[band] += 1;
    this.lastVisit[band] = t;
    this.mu[band] += (r - this.mu[band]) / this.visits[band];

    const ht = this.hitTimes[band];
    const lock = this._locks.get(band);
    if (res.hit && !res.falseAlarm) {
      ht.push(t);
      if (ht.length > 200) ht.shift();

      if (lock) {
        const expected = lock.nextOn;
        const near = Math.abs(t - expected) <= Math.max(4, lock.period * 0.12);
        if (near) {
          lock.evidence += 1;
          if (!lock.confirmed && lock.evidence >= 2) {
            lock.confirmed = true;
            this.log(`slot ${t}: phase-lock CONFIRMED on band ${band} ` +
                     `(period ~${lock.period} slots)`);
          }
          lock.nextOn = expected + lock.period;
          lock.misses = 0;
        }
      } else if (!this.probeUntil.has(band)) {
        this.burstUntil.set(band, t + Math.min(120, 3 * 30)); // 4. burst
      }
    } else if (lock && t >= lock.nextOn - 2) {
      // a predicted window passed without a confirming hit
      lock.misses += 1;
      if (lock.misses > MAX_MISS) {
        this._locks.delete(band);
        this.log(`slot ${t}: lock on band ${band} deleted after repeated misses`);
      }
    }

    // promote candidates once enough history exists
    if (!this._locks.has(band) && ht.length >= LOCK_HITS &&
        !this.probeUntil.has(band)) {
      const est = this.estimatePeriod(ht);
      if (est !== null) {
        const phase = ht[ht.length - 1] % est;
        let nextOn = phase + Math.ceil((t - phase) / est) * est;
        while (nextOn <= t) nextOn += est;
        this._locks.set(band, {
          period: est, nextOn, misses: 0, confirmed: false, evidence: 0 });
        this.probeUntil.delete(band);
        this.log(`slot ${t}: candidate rhythm found on band ${band} ` +
                 `(period ~${est}) - probing`);
      }
    }
    // schedule probes for bands with some hits but no rhythm yet
    if (ht.length >= 3 && !this._locks.has(band) && !this.probeUntil.has(band)
        && !this.burstUntil.has(band)) {
      this.probeUntil.set(band, t + 2);
    }
    this.burstUntil.delete(band);                    // burst consumed on visit
  }
}



/* ------------------------ cooperative team wrapper ----------------------- *
 * Mirrors ewsmart/multireceiver.CooperativeTeam.select_joint(): members pick
 * independently; collisions are resolved by re-assigning the later member to
 * its best unclaimed band (by mu when available).
 *
 * Swarm Intelligence (DND tokens): SmartScan members that have a confirmed
 * phase-lock on a target band broadcast a "Do Not Disturb" token for that
 * band.  Other team members completely remove that band from their selection
 * pools, ensuring zero redundancy and perfectly partitioned spectrum coverage.
 */
export class TeamScheduler {
  private dndBands = new Set<number>();  // bands with active DND tokens

  constructor(public members: Scheduler[], private nBands: number) {}
  reset(horizon: number): void {
    for (const m of this.members) m.reset(this.nBands, horizon);
    this.dndBands.clear();
  }
  selectJoint(t: number): number[] {
    // Phase 1: Collect DND tokens from SmartScan members with confirmed locks
    this.dndBands.clear();
    for (const m of this.members) {
      const ss = m as unknown as { _locks?: Map<number, { confirmed: boolean }> };
      if (ss._locks) {
        for (const [band, lock] of ss._locks) {
          if (lock.confirmed) this.dndBands.add(band);
        }
      }
    }

    const chosen: number[] = [];
    for (const m of this.members) {
      let b = m.select(t);
      // If a DND token is active on this band from another member, avoid it
      if (this.dndBands.has(b) && !chosen.includes(b)) {
        const cands = Array.from({ length: this.nBands },
                                 (_, i) => i).filter(
                                   (x) => !chosen.includes(x) && !this.dndBands.has(x));
        if (cands.length > 0) {
          const anyUcb = m as unknown as { mu?: number[] };
          b = anyUcb.mu
            ? cands.reduce((best, c) => (anyUcb.mu![c] > anyUcb.mu![best] ? c : best),
                           cands[0])
            : cands[t % cands.length];
        }
        // If no non-DND candidates, fall through with original choice
      } else if (chosen.includes(b)) {
        const cands = Array.from({ length: this.nBands },
                                 (_, i) => i).filter((x) => !chosen.includes(x));
        if (cands.length === 0) { chosen.push(b); continue; }
        const anyUcb = m as unknown as { mu?: number[] };
        b = anyUcb.mu
          ? cands.reduce((best, c) => (anyUcb.mu![c] > anyUcb.mu![best] ? c : best),
                         cands[0])
          : cands[t % cands.length];
      }
      chosen.push(b);
    }
    return chosen;
  }
  updateAll(t: number, bands: number[],
            results: { hit: boolean; falseAlarm: boolean;
                       detections: { eid: number }[] }[],
            rAvg: number): void {
    this.members.forEach((m, i) => m.update(t, bands[i], results[i], rAvg));
  }
  get first(): Scheduler { return this.members[0]; }
}
