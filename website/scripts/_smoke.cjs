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
  let a2 = seed >>> 0;
  return function() {
    a2 |= 0;
    a2 = a2 + 1831565813 | 0;
    let t = Math.imul(a2 ^ a2 >>> 15, 1 | a2);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
var randn = (rng) => {
  const u = Math.max(1e-9, rng());
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng());
};
var bandFreq = (b2, s) => s.freqMinMhz + (s.freqMaxMhz - s.freqMinMhz) * (b2 + 0.5) / s.nBands;
var RFEnvironment = class {
  constructor(cfg2, seed) {
    this.emitters = [];
    this.cfg = cfg2;
    this.rng = mulberry32(seed);
    const r = this.rng;
    let eid = 0;
    const pos = () => ({ ang: r() * 2 * Math.PI, rad: 40 * Math.sqrt(r()) });
    const add = (kind, threat, home) => {
      const { ang, rad } = pos();
      const band = home ?? Math.floor(r() * cfg2.nBands);
      const p = kind === "stationary" || kind === "agile" ? 1 : Math.round(cfg2.periodRange[0] + r() * (cfg2.periodRange[1] - cfg2.periodRange[0]));
      this.emitters.push({
        eid: eid++,
        kind,
        threat,
        snrDb: Math.max(2, cfg2.snrMeanDb + randn(r) * cfg2.snrStdDb),
        freqMhz: +(bandFreq(band, cfg2) + randn(r) * 8).toFixed(1),
        bearingDeg: +((Math.atan2(rad * Math.sin(ang), rad * Math.cos(ang)) * 180 / Math.PI % 360 + 360) % 360).toFixed(1),
        homeBand: band,
        hopSet: kind === "agile" ? Array.from(
          { length: 3 + Math.floor(r() * 4) },
          () => Math.floor(r() * cfg2.nBands)
        ) : [],
        dwell: 3 + Math.floor(r() * 6),
        period: p,
        onLen: 2 + Math.floor(r() * 4),
        offset: Math.floor(r() * Math.max(1, p))
      });
    };
    const half = (n) => Math.max(1, Math.floor(n / 2));
    for (let i = 0; i < cfg2.nStationary; i++) add("stationary", i < half(cfg2.nStationary));
    for (let i = 0; i < cfg2.nAgile; i++) add("agile", i < half(cfg2.nAgile));
    for (let i = 0; i < cfg2.nPeriodic; i++) add("periodic", i < half(cfg2.nPeriodic));
    for (let i = 0; i < cfg2.nSpatial; i++) add("spatial", false);
    for (let i = 0; i < cfg2.nClutter; i++) add("stationary", false);
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
      const b2 = this.agileBand(e, t);
      if (b2 === band) out.push(e);
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
  constructor(env2, seed, pdMidOffset = 6, pdK = 3) {
    this.env = env2;
    this.pdMidOffset = pdMidOffset;
    this.pdK = pdK;
    this.rng = mulberry32(seed ^ 2654435769);
  }
  detectionProb(snrDb) {
    const z = (snrDb - (-10 + this.pdMidOffset)) / this.pdK;
    return 0.97 / (1 + Math.exp(-z));
  }
  dwell(band, t) {
    const ems = this.env.emittersAt(band, t);
    const dets = [];
    for (const e of ems) {
      if (this.rng() < this.detectionProb(e.snrDb)) {
        dets.push({
          snrDb: e.snrDb,
          aoaDeg: (e.bearingDeg + this.rng() * 5 - 2.5 + 360) % 360,
          eid: e.eid
        });
      }
    }
    dets.sort((a2, b2) => b2.snrDb - a2.snrDb);
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
  predict() {
    return false;
  }
};
var RECON_FACTOR = 26;
var LOCK_HITS = 5;
var MAX_MISS = 2;
var SmartScanScheduler = class {
  constructor(nBands = 24, seed = 7, log) {
    this.name = "smart-scan";
    this.horizon = 3e3;
    this.hitTimes = [];
    this._locks = /* @__PURE__ */ new Map();
    this.probeUntil = /* @__PURE__ */ new Map();
    // band -> dwell-until slot
    this.burstUntil = /* @__PURE__ */ new Map();
    this.log = () => {
    };
    this.nBands = nBands;
    this.rng = (() => {
      let a2 = seed >>> 0;
      return () => {
        a2 |= 0;
        a2 = a2 + 1831565813 | 0;
        let t = Math.imul(a2 ^ a2 >>> 15, 1 | a2);
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
    this._locks.clear();
    this.probeUntil.clear();
    this.burstUntil.clear();
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
  /** Parity with SmartScanScheduler.predict: inside a confirmed lock's window. */
  predict(t, band) {
    const l = this._locks.get(band);
    if (!l) return false;
    const d = (t - (l.nextOn - l.period)) % l.period;
    const width = Math.max(4, l.period * 0.2);
    return d >= 0 && d <= width;
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
      phases.sort((a2, b2) => a2 - b2);
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
    for (let b2 = 0; b2 < this.nBands; b2++) {
      const recency = 1 / (1 + Math.max(0, t - this.lastVisit[b2]));
      const exploreBonus = 0.9 * Math.sqrt(Math.log(t + 2) / this.visits[b2]) * (1 - 0.55 * ramp);
      const v = this.mu[b2] + exploreBonus + 0.05 * recency;
      const noisy = v + (this.rng() - 0.5) * 0.02 * (1 - ramp);
      if (noisy > bestV) {
        bestV = noisy;
        best = b2;
      }
    }
    return best;
  }
  update(t, band, res, r) {
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

// scripts/engine_smoke.ts
var cfg = { ...DEFAULT_SCENARIO, T: 2400 };
var env = new RFEnvironment(cfg, 4242);
var logs = [];
var a = new SmartScanScheduler(cfg.nBands, 4242, (m) => logs.push(m));
a.reset(cfg.nBands, cfg.T);
var b = new SequentialSweep(cfg.nBands);
b.reset(cfg.nBands, cfg.T);
function run(side, sched) {
  const rx = new ESReceiver(env, side === "a" ? 11 : 23);
  const seen = /* @__PURE__ */ new Map();
  let threatsFound = 0;
  let reward = 0, hits = 0;
  for (let t = 0; t < cfg.T; t++) {
    const band = sched.select(t);
    const res = rx.dwell(band, t);
    let r = res.falseAlarm ? -0.08 : !res.hit ? -0.05 : 0.15;
    if (res.hit && !res.falseAlarm) {
      hits++;
      const lead = env.emitters.find((e) => e.eid === res.detections[0]?.eid);
      r = lead?.threat ? 1 : 0.15;
      for (const d of res.detections) {
        if (!seen.has(d.eid)) {
          const e = env.emitters.find((x) => x.eid === d.eid);
          if (e?.threat) {
            threatsFound++;
            r += 1.5;
          }
          seen.set(d.eid, t);
        }
      }
    }
    reward += r;
    sched.update(t, band, res, r);
  }
  return { found: threatsFound, reward };
}
var A = run("a", a);
var B = run("b", b);
var threats = env.nThreats();
console.log(`threats=${threats} smart=${A.found} sequential=${B.found} (reward ${A.reward.toFixed(0)} vs ${B.reward.toFixed(0)})`);
console.log(`locks/events: ${logs.length}; sample: ${logs.slice(0, 3).join(" | ")}`);
if (!(A.found >= B.found)) {
  console.error("ENGINE SMOKE FAIL: SmartScan did not match/exceed sequential");
  process.exit(1);
}
console.log("ENGINE SMOKE OK");
