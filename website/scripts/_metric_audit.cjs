"use strict";

// src/engine/core.ts
var DEFAULT_SCENARIO = {
  nBands: 24,
  T: 3e3,
  nStationary: 6,
  nAgile: 4,
  nPeriodic: 4,
  nSpatial: 3,
  nClutter: 8,
  snrMeanDb: 12,
  snrStdDb: 4,
  periodRange: [40, 400],
  freqMinMhz: 2e3,
  freqMaxMhz: 18e3
};
function mulberry32(seed) {
  let a = seed >>> 0;
  return function() {
    a |= 0;
    a = a + 1831565813 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
var randn = (rng) => {
  const u = Math.max(1e-9, rng());
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng());
};
var bandFreq = (b, s) => s.freqMinMhz + (s.freqMaxMhz - s.freqMinMhz) * (b + 0.5) / s.nBands;
var RFEnvironment = class {
  constructor(cfg, seed) {
    this.emitters = [];
    this.cfg = cfg;
    this.rng = mulberry32(seed);
    const r = this.rng;
    let eid = 0;
    const pos = () => ({ ang: r() * 2 * Math.PI, rad: 40 * Math.sqrt(r()) });
    const add = (kind, threat, home) => {
      const { ang, rad } = pos();
      const band = home ?? Math.floor(r() * cfg.nBands);
      const p = kind === "stationary" || kind === "agile" ? 1 : Math.round(cfg.periodRange[0] + r() * (cfg.periodRange[1] - cfg.periodRange[0]));
      const lpi = kind !== "agile" && r() < (cfg.lpiFraction ?? 0);
      const tb = lpi ? 256 : 1;
      const rawSnr = cfg.snrMeanDb + randn(r) * cfg.snrStdDb;
      this.emitters.push({
        eid: eid++,
        kind,
        threat,
        snrDb: lpi ? rawSnr - 10 * Math.log10(tb) : Math.max(2, rawSnr),
        lpi,
        tbProduct: tb,
        freqMhz: +(bandFreq(band, cfg) + randn(r) * 8).toFixed(1),
        bearingDeg: +((Math.atan2(rad * Math.sin(ang), rad * Math.cos(ang)) * 180 / Math.PI % 360 + 360) % 360).toFixed(1),
        homeBand: band,
        hopSet: kind === "agile" ? Array.from(
          { length: 3 + Math.floor(r() * 4) },
          () => Math.floor(r() * cfg.nBands)
        ) : [],
        dwell: 3 + Math.floor(r() * 6),
        period: p,
        onLen: 2 + Math.floor(r() * 4),
        offset: Math.floor(r() * Math.max(1, p)),
        pwUs: +(0.5 + r() * 4).toFixed(1),
        xKm: +(rad * Math.cos(ang)).toFixed(2),
        yKm: +(rad * Math.sin(ang)).toFixed(2)
      });
    };
    const half = (n) => Math.max(1, Math.floor(n / 2));
    for (let i = 0; i < cfg.nStationary; i++) add("stationary", i < half(cfg.nStationary));
    for (let i = 0; i < cfg.nAgile; i++) add("agile", i < half(cfg.nAgile));
    for (let i = 0; i < cfg.nPeriodic; i++) add("periodic", i < half(cfg.nPeriodic));
    for (let i = 0; i < cfg.nSpatial; i++) add("spatial", false);
    for (let i = 0; i < cfg.nClutter; i++) add("stationary", false);
  }
  transmitting(e, t) {
    switch (e.kind) {
      case "stationary":
        return true;
      case "agile":
        return true;
      case "periodic":
      case "spatial": {
        if (e.period <= 1) return true;
        return (t - e.offset) % e.period < e.onLen;
      }
    }
  }
  agileBand(e, t) {
    if (e.kind !== "agile") return e.homeBand;
    const idx = Math.floor(t / e.dwell);
    return e.hopSet[idx % e.hopSet.length];
  }
  emittersAt(band, t) {
    const out = [];
    for (const e of this.emitters) {
      if (!this.transmitting(e, t)) continue;
      const b = this.agileBand(e, t);
      if (b === band) out.push(e);
    }
    return out;
  }
  nextOnStart(e, afterT) {
    if (e.kind !== "periodic" && e.kind !== "spatial") return null;
    const p = Math.max(1, e.period);
    let s = e.offset + Math.ceil(Math.max(0, afterT - e.offset) / p) * p;
    while (s <= afterT) s += p;
    return s;
  }
  nThreats() {
    return this.emitters.filter((e) => e.threat).length;
  }
};
var ESReceiver = class {
  constructor(env, seed, pdMidOffset = 6, pdK = 3) {
    this.env = env;
    this.pdMidOffset = pdMidOffset;
    this.pdK = pdK;
    this.rng = mulberry32(seed ^ 2654435769);
  }
  detectionProb(snrDb) {
    const z = (snrDb - (-10 + this.pdMidOffset)) / this.pdK;
    return 0.97 / (1 + Math.exp(-z));
  }
  /** Matched-filter / de-chirp coherent gain for an LPI waveform (dB). */
  mfGain(e) {
    if (!e.lpi || !this.env.cfg.matchedFilter) return 0;
    return 10 * Math.log10(Math.max(e.tbProduct ?? 1, 1));
  }
  /**
   * Dual-baseline phase-interferometer AOA error (deg), CRLB-coupled.
   * sigma_theta = lambda / (2*pi*d*cos(theta)) * 1/sqrt(2*SNR), fine baseline
   * d = 0.20 m.  The legacy constant 2.5 deg model stays selectable so the
   * two can be compared live.
   */
  aoaError(e) {
    if (this.env.cfg.aoaModel === "fixed") return 2.5;
    const lam = 299792458 / (e.freqMhz * 1e6);
    const snrLin = Math.pow(10, (e.snrDb + this.mfGain(e)) / 10);
    const sigmaPhi = 1 / Math.sqrt(2 * snrLin);
    const deg = lam / (2 * Math.PI * 0.2 * 0.7071) * sigmaPhi * 180 / Math.PI;
    return Math.min(45, deg);
  }
  dwell(band, t) {
    const ems = this.env.emittersAt(band, t);
    const dets = [];
    for (const e of ems) {
      const gain = this.mfGain(e);
      if (this.rng() < this.detectionProb(e.snrDb + gain)) {
        const sigma = this.aoaError(e);
        dets.push({
          snrDb: e.snrDb + gain,
          aoaDeg: (e.bearingDeg + randn(this.rng) * sigma + 360) % 360,
          eid: e.eid
        });
      }
    }
    dets.sort((a, b) => b.snrDb - a.snrDb);
    let falseAlarm = false;
    if (dets.length === 0 && ems.length === 0 && this.rng() < 4e-4) falseAlarm = true;
    return {
      hit: dets.length > 0 || falseAlarm,
      falseAlarm,
      truthPresent: ems.length > 0,
      strongestSnrDb: dets[0]?.snrDb ?? Number.NEGATIVE_INFINITY,
      detections: dets
    };
  }
};

// src/engine/schedulers.ts
var SequentialSweep = class {
  constructor(nBands = 24) {
    this.nBands = nBands;
    this.name = "openloop-sequential";
  }
  reset() {
  }
  select(t) {
    return t % this.nBands;
  }
  update() {
  }
  /** An open-loop sweep has no emitter model: its only "prediction" would be
   *  its own fixed schedule, so the honest baseline answer is OFF. */
  predict() {
    return false;
  }
};
var RandomScan = class {
  constructor(nBands = 24, seed = 3) {
    this.nBands = nBands;
    this.name = "openloop-random";
    let a = seed >>> 0;
    this.rng = () => {
      a |= 0;
      a = a + 1831565813 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  reset() {
  }
  select() {
    return Math.floor(this.rng() * this.nBands);
  }
  update() {
  }
  /** No emitter model: honest baseline answer is OFF (see SequentialSweep). */
  predict() {
    return false;
  }
};
var UCBScheduler = class {
  constructor(nBands = 24) {
    this.nBands = nBands;
    this.name = "bandit-ucb";
  }
  reset() {
    this.n = new Array(this.nBands).fill(1);
    this.mu = new Array(this.nBands).fill(1e-3);
  }
  select(t) {
    let best = 0, bestV = -Infinity;
    for (let b = 0; b < this.nBands; b++) {
      const v = this.mu[b] + 0.6 * Math.sqrt(Math.log(t + 2) / this.n[b]);
      if (v > bestV) {
        bestV = v;
        best = b;
      }
    }
    return best;
  }
  update(_t, band, _r0, r) {
    this.n[band] += 1;
    this.mu[band] += (r - this.mu[band]) / this.n[band];
  }
  predict(_t, band) {
    return this.mu[band] > 0.15;
  }
};
var LinearQLearning = class {
  constructor(nBands = 24, seed = 5) {
    this.nBands = nBands;
    this.name = "rl-linear-q";
    this.learnable = true;
    this.theta = [0, 0, 0, 0, 1];
    // [bias, prior, conf, recency, explore]
    this.alpha = 0.05;
    this.gamma = 0.9;
    this.eps = 0.3;
    this.epsMin = 0.05;
    this.epsDecay = 0.95;
    this.lastBand = 0;
    this.prevQ = 0;
    let a = seed >>> 0;
    this.rng = () => {
      a |= 0;
      a = a + 1831565813 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  feats(b, t) {
    const recency = 1 / (1 + Math.max(0, t - this.lastVisit[b]));
    const prior = this.discHit[b] / (this.discN[b] + 0.25);
    const conf = Math.sqrt(this.discN[b]) / (1 + Math.sqrt(this.discN[b]));
    return [
      1,
      prior,
      conf,
      recency,
      1 / (1 + Math.log(t + 2))
    ];
  }
  q(b, t) {
    const f = this.feats(b, t);
    return f.reduce((s, v, i) => s + v * this.theta[i], 0);
  }
  reset() {
    this.discHit = new Array(this.nBands).fill(0);
    this.discN = new Array(this.nBands).fill(0);
    this.lastVisit = new Array(this.nBands).fill(-1e9);
  }
  endEpisode() {
    this.eps = Math.max(this.epsMin, this.eps * this.epsDecay);
  }
  select(t) {
    if (this.rng() < this.eps) return Math.floor(this.rng() * this.nBands);
    let best = 0, bestQ = -Infinity;
    for (let b = 0; b < this.nBands; b++) {
      const qv = this.q(b, t);
      if (qv > bestQ) {
        bestQ = qv;
        best = b;
      }
    }
    this.lastBand = best;
    this.prevQ = bestQ;
    return best;
  }
  update(_t, band, res, r) {
    this.discHit[band] = this.discHit[band] * this.gamma + (res.hit ? 1 : 0);
    this.discN[band] = this.discN[band] * this.gamma + 1;
    const target = r + this.gamma * this.prevQ;
    const f = this.feats(band, _t);
    const pred = f.reduce((s, v, i) => s + v * this.theta[i], 0);
    const err = target - pred;
    for (let i = 0; i < this.theta.length; i++) this.theta[i] += this.alpha * err * f[i];
  }
  predict(_t, band) {
    const prior = this.discHit[band] / (this.discN[band] + 0.25);
    return prior > 0.35;
  }
};
var RECON_FACTOR = 18;
var LOCK_HITS = 5;
var MAX_MISS = 2;
var SmartScanScheduler = class {
  constructor(nBands = 24, seed = 7, log) {
    this.name = "smart-scan";
    this.horizon = 3e3;
    this.hitTimes = [];
    this._locks = /* @__PURE__ */ new Map();
    this.visitHits = [];
    // last visit outcomes per band
    this.probeUntil = /* @__PURE__ */ new Map();
    // band -> dwell-until slot
    this.burstUntil = /* @__PURE__ */ new Map();
    this.log = () => {
    };
    // Cross-episode memory (Learning Arena): consolidated value/visit priors
    // that survive reset(), so repeated episodes warm-start the learner.
    this.memory = null;
    this.episodesSeen = 0;
    this.nBands = nBands;
    this.rng = (() => {
      let a = seed >>> 0;
      return () => {
        a |= 0;
        a = a + 1831565813 | 0;
        let t = Math.imul(a ^ a >>> 15, 1 | a);
        t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
        return ((t ^ t >>> 14) >>> 0) / 4294967296;
      };
    })();
    if (log) this.log = log;
  }
  reset(nBands, horizon) {
    this.nBands = nBands;
    this.horizon = horizon;
    this.mu = new Array(nBands).fill(0.01);
    this.visits = new Array(nBands).fill(1);
    this.lastVisit = new Array(nBands).fill(-1e9);
    this.hitTimes = Array.from({ length: nBands }, () => []);
    this.visitHits = Array.from({ length: nBands }, () => []);
    this._locks.clear();
    this.probeUntil.clear();
    this.burstUntil.clear();
    if (this.memory && this.memory.mu.length === nBands) {
      this.mu = [...this.memory.mu];
      this.visits = [...this.memory.visits];
    }
  }
  /** Consolidate this episode's learning into cross-episode memory. */
  endEpisode() {
    this.episodesSeen += 1;
    this.memory = { mu: [...this.mu], visits: [...this.visits] };
  }
  get reconSteps() {
    return RECON_FACTOR * this.nBands / 12;
  }
  get locks() {
    return this.lockMap.size;
  }
  get lockMap() {
    return this._locks;
  }
  /** Parity with SmartScanScheduler.predict: phase-lock, confirmed
   *  persistent carrier, then yield fallback - in that order. */
  predict(t, band) {
    const l = this._locks.get(band);
    if (l && l.confirmed) {
      const d = (t - (l.nextOn - l.period)) % l.period;
      const width = Math.max(4, l.period * 0.2);
      if (d >= 0 && d <= width) return true;
    }
    const vh = this.visitHits[band] ?? [];
    if (vh.length === 10 && vh.reduce((s, v) => s + v, 0) >= 8) return true;
    if (vh.length >= 3 && vh.reduce((s, v) => s + v, 0) / vh.length >= 0.6)
      return true;
    return false;
  }
  estimatePeriod(times) {
    if (times.length < 4) return null;
    const diffs = [];
    for (let i = 1; i < times.length; i++) diffs.push(times[i] - times[i - 1]);
    const hist = /* @__PURE__ */ new Map();
    for (const d of diffs) {
      for (let p = Math.max(10, Math.round(d) - 8); p <= Math.min(450, Math.round(d) + 8); p++) {
        hist.set(p, (hist.get(p) ?? 0) + 1);
      }
    }
    let bestP = null, bestScore = 0;
    for (const [p, votes] of hist) {
      const phases = times.map((h) => (h % p + p) % p);
      phases.sort((a, b) => a - b);
      let maxGap = 0, gi = 0;
      for (let i = 0; i < phases.length; i++) {
        const nxt = i === phases.length - 1 ? phases[0] + p : phases[i + 1];
        const gap = nxt - phases[i];
        if (gap > maxGap) {
          maxGap = gap;
          gi = i;
        }
      }
      const span = p - maxGap;
      if (span <= p * 0.35) {
        const score = votes + phases.length * (span <= p * 0.2 ? 2 : 0);
        if (score > bestScore) {
          bestScore = score;
          bestP = p;
        }
      }
    }
    return bestP && bestScore >= times.length * 0.9 ? bestP : null;
  }
  select(t) {
    const reconEnd = this.reconSteps;
    if (t < reconEnd) return t % this.nBands;
    let bestLockBand = -1, bestEta = Infinity;
    for (const [band, lock] of this._locks) {
      if (!lock.confirmed) continue;
      const eta = lock.nextOn - t;
      if (eta <= 3 && eta >= -lock.period * 0.15 && eta < bestEta) {
        bestEta = eta;
        bestLockBand = band;
      }
    }
    if (bestLockBand >= 0) return bestLockBand;
    for (const [band, until] of this.probeUntil) {
      if (t < until) return band;
    }
    for (const [band, until] of this.burstUntil) {
      if (t < until) return band;
    }
    const ramp = Math.min(
      1,
      Math.max(0, (t - reconEnd) / Math.max(1, this.horizon - reconEnd))
    );
    let best = 0, bestV = -Infinity;
    for (let b = 0; b < this.nBands; b++) {
      const recency = 1 / (1 + Math.max(0, t - this.lastVisit[b]));
      const exploreBonus = 0.9 * Math.sqrt(Math.log(t + 2) / this.visits[b]) * (1 - 0.55 * ramp);
      const v = this.mu[b] + exploreBonus + 0.05 * recency;
      const noisy = v + (this.rng() - 0.5) * 0.02 * (1 - ramp);
      if (noisy > bestV) {
        bestV = noisy;
        best = b;
      }
    }
    return best;
  }
  update(t, band, res, r) {
    this.visits[band] += 1;
    this.lastVisit[band] = t;
    this.mu[band] += (r - this.mu[band]) / this.visits[band];
    const vh = this.visitHits[band] ?? (this.visitHits[band] = []);
    vh.push(res.hit && !res.falseAlarm ? 1 : 0);
    if (vh.length > 10) vh.shift();
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
            this.log(`slot ${t}: phase-lock CONFIRMED on band ${band} (period ~${lock.period} slots)`);
          }
          lock.nextOn = expected + lock.period;
          lock.misses = 0;
        }
      } else if (!this.probeUntil.has(band)) {
        this.burstUntil.set(band, t + Math.min(120, 3 * 30));
      }
    } else if (lock && t >= lock.nextOn - 2) {
      lock.misses += 1;
      if (lock.misses > MAX_MISS) {
        this._locks.delete(band);
        this.log(`slot ${t}: lock on band ${band} deleted after repeated misses`);
      }
    }
    if (!this._locks.has(band) && ht.length >= LOCK_HITS && !this.probeUntil.has(band)) {
      const est = this.estimatePeriod(ht);
      if (est !== null) {
        const phase = ht[ht.length - 1] % est;
        let nextOn = phase + Math.ceil((t - phase) / est) * est;
        while (nextOn <= t) nextOn += est;
        this._locks.set(band, {
          period: est,
          nextOn,
          misses: 0,
          confirmed: false,
          evidence: 0
        });
        this.probeUntil.delete(band);
        this.log(`slot ${t}: candidate rhythm found on band ${band} (period ~${est}) - probing`);
      }
    }
    if (ht.length >= 3 && !this._locks.has(band) && !this.probeUntil.has(band) && !this.burstUntil.has(band)) {
      this.probeUntil.set(band, t + 2);
    }
    this.burstUntil.delete(band);
  }
};
var TeamScheduler = class {
  // bands with active DND tokens
  constructor(members, nBands) {
    this.members = members;
    this.nBands = nBands;
    this.dndBands = /* @__PURE__ */ new Set();
  }
  reset(horizon) {
    for (const m of this.members) m.reset(this.nBands, horizon);
    this.dndBands.clear();
  }
  selectJoint(t) {
    this.dndBands.clear();
    for (const m of this.members) {
      const ss = m;
      if (ss._locks) {
        for (const [band, lock] of ss._locks) {
          if (lock.confirmed) this.dndBands.add(band);
        }
      }
    }
    const chosen = [];
    for (const m of this.members) {
      let b = m.select(t);
      if (this.dndBands.has(b) && !chosen.includes(b)) {
        const cands = Array.from(
          { length: this.nBands },
          (_, i) => i
        ).filter(
          (x) => !chosen.includes(x) && !this.dndBands.has(x)
        );
        if (cands.length > 0) {
          const anyUcb = m;
          b = anyUcb.mu ? cands.reduce(
            (best, c) => anyUcb.mu[c] > anyUcb.mu[best] ? c : best,
            cands[0]
          ) : cands[t % cands.length];
        }
      } else if (chosen.includes(b)) {
        const cands = Array.from(
          { length: this.nBands },
          (_, i) => i
        ).filter((x) => !chosen.includes(x));
        if (cands.length === 0) {
          chosen.push(b);
          continue;
        }
        const anyUcb = m;
        b = anyUcb.mu ? cands.reduce(
          (best, c) => anyUcb.mu[c] > anyUcb.mu[best] ? c : best,
          cands[0]
        ) : cands[t % cands.length];
      }
      chosen.push(b);
    }
    return chosen;
  }
  updateAll(t, bands, results, rAvg) {
    this.members.forEach((m, i) => m.update(t, bands[i], results[i], rAvg));
  }
  get first() {
    return this.members[0];
  }
};

// scripts/metric_audit.ts
var makeLead = (p, nBands, s) => p === "smart-scan" ? new SmartScanScheduler(nBands, s) : p === "openloop-random" ? new RandomScan(nBands, s) : p === "bandit-ucb" ? new UCBScheduler(nBands) : p === "rl-linear-q" ? new LinearQLearning(nBands, s) : new SequentialSweep(nBands);
var seeds = [4242, 777, 999, 31337];
var opps = ["openloop-sequential", "openloop-random", "bandit-ucb", "rl-linear-q"];
var pct = (x) => x == null ? "  -" : (x * 100).toFixed(1) + "%";
var slots = (x) => x == null ? "  -" : x.toFixed(0).padStart(4);
var invariantFails = 0;
var fail = (msg) => {
  invariantFails++;
  console.error(`FAIL  ${msg}`);
};
var bWins = {};
for (const seed of seeds) {
  for (const opp of opps) {
    const cfg = { ...DEFAULT_SCENARIO };
    const env = new RFEnvironment(cfg, seed);
    const nThreats = env.nThreats();
    const team = {
      a: new TeamScheduler([makeLead("smart-scan", cfg.nBands, seed)], cfg.nBands),
      b: new TeamScheduler([makeLead(opp, cfg.nBands, seed + 5)], cfg.nBands)
    };
    team.a.reset(cfg.T);
    team.b.reset(cfg.T);
    const rx = {
      a: new ESReceiver(env, seed * 7 + 11, 6),
      b: new ESReceiver(env, seed * 13 + 29, 6)
    };
    const st = {
      rewardSum: { a: 0, b: 0 },
      hits: { a: 0, b: 0 },
      fa: { a: 0, b: 0 },
      seenAll: { a: /* @__PURE__ */ new Set(), b: /* @__PURE__ */ new Set() },
      seenThreats: { a: /* @__PURE__ */ new Set(), b: /* @__PURE__ */ new Set() },
      ttffHitSlots: { a: [], b: [] },
      // buggy TTFF feed
      ttffFirst: { a: [], b: [] },
      // fixed TTFF feed
      threatFix: { a: [], b: [] },
      // threat first-fix times
      pred: { a: [0, 0], b: [0, 0] }
      // [correct, n]
    };
    for (let t = 0; t < cfg.T; t++) {
      for (const side of ["a", "b"]) {
        const bands = team[side].selectJoint(t);
        const res = rx[side].dwell(bands[0], t);
        let r = res.falseAlarm ? -0.08 : !res.hit ? -0.05 : 0.15;
        if (res.hit && !res.falseAlarm) {
          const lead = env.emitters.find((e) => e.eid === res.detections[0]?.eid);
          r = lead?.threat ? 1 : 0.15;
        }
        const clean = res.hit && !res.falseAlarm;
        if (clean) st.ttffHitSlots[side].push(t);
        if (clean) st.hits[side] += 1;
        if (res.falseAlarm) st.fa[side] += 1;
        for (const d of res.detections) {
          const isNew = !st.seenAll[side].has(d.eid);
          if (isNew) {
            st.seenAll[side].add(d.eid);
            st.ttffFirst[side].push(t);
          }
          const e = env.emitters.find((x) => x.eid === d.eid);
          if (e?.threat && !st.seenThreats[side].has(d.eid)) {
            st.seenThreats[side].add(d.eid);
            st.threatFix[side].push(t);
          }
        }
        const p = team[side].first.predict(t, bands[0]);
        st.pred[side][0] += Number(p === res.truthPresent);
        st.pred[side][1] += 1;
        st.rewardSum[side] += r;
        team[side].updateAll(t, bands, [res], r);
      }
    }
    const mk = (side) => ({
      cov: st.seenThreats[side].size / Math.max(1, nThreats),
      allRatio: st.seenAll[side].size / Math.max(1, env.emitters.length),
      reward: st.rewardSum[side] / Math.max(1, cfg.T),
      hitRate: st.hits[side] / Math.max(1, cfg.T),
      fa: st.fa[side],
      ttffBuggy: st.ttffHitSlots[side].length ? st.ttffHitSlots[side].reduce((x, y) => x + y, 0) / st.ttffHitSlots[side].length : null,
      ttffFixed: st.ttffFirst[side].length ? st.ttffFirst[side].reduce((x, y) => x + y, 0) / st.ttffFirst[side].length : null,
      predAcc: st.pred[side][1] ? st.pred[side][0] / st.pred[side][1] : 0,
      predN: st.pred[side][1],
      locksBuggy: team.a.first.locks ?? 0,
      // current console
      locksFixed: team[side].first.locks ?? 0
    });
    const A = mk("a"), B = mk("b");
    for (const [name, k] of [["A", A], ["B", B]]) {
      if (k.cov < 0 || k.cov > 1) fail(`${seed}/${opp} ${name} cov out of range ${k.cov}`);
      if (k.predAcc < 0 || k.predAcc > 1) fail(`${seed}/${opp} ${name} predAcc out of range`);
      if (k.hitRate < 0 || k.hitRate > 1) fail(`${seed}/${opp} ${name} hitRate out of range`);
      if (k.ttffFixed != null && (k.ttffFixed < 0 || k.ttffFixed > cfg.T))
        fail(`${seed}/${opp} ${name} ttffFixed out of range`);
    }
    if (B.locksFixed !== 0) fail(`${seed}/${opp} side-specific locks: opponent holds locks (${B.locksFixed} != 0)`);
    if (A.locksFixed < 0) fail(`${seed}/${opp} negative lock count`);
    if (seed === 4242 && opp === "openloop-sequential")
      console.log(`note  smart-scan predAcc=${pct(A.predAcc)} seq predAcc=${pct(B.predAcc)} (probe: 96.9 / 54.1)`);
    const better = (m, aV, bV, higherWins) => {
      const bBetter = higherWins ? bV > aV : bV < aV;
      if (bBetter && Math.abs(bV - aV) > 1e-9) (bWins[m] ??= []).push(`${seed}/${opp}`);
    };
    better("coverage", A.cov, B.cov, true);
    better("all-emitter ratio", A.allRatio, B.allRatio, true);
    better("reward/dwell", A.reward, B.reward, true);
    better("hit rate", A.hitRate, B.hitRate, true);
    better("false alarms (raw)", A.fa, B.fa, false);
    better("mean TTFF (buggy)", A.ttffBuggy ?? 1e9, B.ttffBuggy ?? 1e9, false);
    better("mean TTFF (fixed)", A.ttffFixed ?? 1e9, B.ttffFixed ?? 1e9, false);
    better("prediction acc", A.predAcc, B.predAcc, true);
    const censThreat = (side) => {
      const fx = st.threatFix[side];
      return (fx.reduce((x, y) => x + y, 0) + (nThreats - fx.length) * cfg.T) / Math.max(1, nThreats);
    };
    better("threat TTFF censored", censThreat("a"), censThreat("b"), false);
    console.log(
      `seed ${seed} vs ${opp.replace("openloop-", "").replace("bandit-", "").replace("rl-", "")}
  cov  A ${pct(A.cov)}  B ${pct(B.cov)}   hit  A ${pct(A.hitRate)}  B ${pct(B.hitRate)}   rew  A ${A.reward.toFixed(3)}  B ${B.reward.toFixed(3)}
  fa   A ${String(A.fa).padStart(3)}  B ${String(B.fa).padStart(3)}   pred A ${pct(A.predAcc)}  B ${pct(B.predAcc)}
  ttff buggy A ${slots(A.ttffBuggy)}  B ${slots(B.ttffBuggy)}  |  fixed A ${slots(A.ttffFixed)}  B ${slots(B.ttffFixed)}
  locks buggy A/B ${A.locksBuggy}/${B.locksBuggy}  fixed A/B ${A.locksFixed}/${B.locksFixed}`
    );
  }
}
console.log("\n=== metrics where the OPPONENT beats SmartScan (over all runs) ===");
for (const [m, runs] of Object.entries(bWins))
  console.log(`  ${m.padEnd(20)} ${runs.length}/${seeds.length * opps.length} runs: ${runs.join(", ")}`);
if (Object.keys(bWins).length === 0) console.log("  (none)");
console.log(invariantFails === 0 ? "\nAUDIT INVARIANTS PASSED" : `
AUDIT INVARIANTS FAILED (${invariantFails})`);
process.exit(invariantFails === 0 ? 0 : 1);
