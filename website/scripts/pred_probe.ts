/* Headless probe: measure band-occupancy density and prediction accuracy
 * exactly as the Console scores it (predict(t,band) vs truthPresent). */
import { DEFAULT_SCENARIO, ESReceiver, RFEnvironment, type Scenario } from "../src/engine/core";
import { RandomScan, SequentialSweep, SmartScanScheduler, UCBScheduler, LinearQLearning } from "../src/engine/schedulers";

const cfg: Scenario = { ...DEFAULT_SCENARIO };
const env = new RFEnvironment(cfg, 4242);

// occupancy statistics over the horizon
let occ = 0, slots = 0;
for (let t = 0; t < 600; t++) {
  const bands = new Set<number>();
  for (const e of env.emitters) if (env.transmitting(e, t)) bands.add(env.agileBand(e, t));
  occ += bands.size / cfg.nBands; slots++;
}
console.log(`emitters=${env.emitters.length} threats=${env.nThreats()} mean occupancy=${(occ / slots * 100).toFixed(1)}%`);

const runSched = (name: string, sched: any, seed: number) => {
  sched.reset(cfg.nBands, cfg.T);
  const rx = new ESReceiver(env, seed, 6);
  let ok = 0, n = 0, trueRate = 0, predTrue = 0;
  for (let t = 0; t < cfg.T; t++) {
    const b = sched.select(t);
    const res = rx.dwell(b, t);
    const p = sched.predict(t, b);
    ok += Number(p === res.truthPresent); n++;
    trueRate += Number(res.truthPresent); predTrue += Number(p);
    sched.update(t, b, res, res.truthPresent ? 0.3 : -0.05);
  }
  console.log(`${name.padEnd(18)} predAcc=${(ok / n * 100).toFixed(1)}%  (truth-on ${(trueRate / n * 100).toFixed(1)}% of dwells, scheduler predicted ON ${(predTrue / n * 100).toFixed(1)}%)`);
};

runSched("smart-scan", new SmartScanScheduler(cfg.nBands, 4242), 4242 * 7 + 11);
runSched("sequential", new SequentialSweep(cfg.nBands), 4242 * 13 + 29);
runSched("random", new RandomScan(cfg.nBands, 4242), 4242 * 13 + 30);
runSched("ucb", new UCBScheduler(cfg.nBands), 4242 * 13 + 31);
runSched("linear-q", new LinearQLearning(cfg.nBands, 4242), 4242 * 13 + 32);
