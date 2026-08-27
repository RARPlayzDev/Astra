/* Headless smoke-test for the browser engine port (run via tools/check_web_engine.ps1) */
import { DEFAULT_SCENARIO, ESReceiver, RFEnvironment } from "../src/engine/core";
import { SequentialSweep, SmartScanScheduler, type Scheduler } from "../src/engine/schedulers";

const cfg = { ...DEFAULT_SCENARIO, T: 2400 };
const env = new RFEnvironment(cfg, 4242);
const logs: string[] = [];
const a = new SmartScanScheduler(cfg.nBands, 4242, (m) => logs.push(m));
a.reset(cfg.nBands, cfg.T);
const b = new SequentialSweep(cfg.nBands);
b.reset(cfg.nBands, cfg.T);

function run(side: "a" | "b", sched: Scheduler): { found: number; reward: number } {
  const rx = new ESReceiver(env, side === "a" ? 11 : 23);
  const seen = new Map<number, number>();          // every emitter (reward bookkeeping)
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
          if (e?.threat) { threatsFound++; r += 1.5; }
          seen.set(d.eid, t);
        }
      }
    }
    reward += r;
    sched.update(t, band, res, r);
  }
  void hits;
  return { found: threatsFound, reward };
}

const A = run("a", a);
const B = run("b", b);
const threats = env.nThreats();
console.log(`threats=${threats} smart=${A.found} sequential=${B.found} ` +
            `(reward ${A.reward.toFixed(0)} vs ${B.reward.toFixed(0)})`);
console.log(`locks/events: ${logs.length}; sample: ${logs.slice(0, 3).join(" | ")}`);
if (!(A.found >= B.found)) {
  console.error("ENGINE SMOKE FAIL: SmartScan did not match/exceed sequential");
  process.exit(1);
}
console.log("ENGINE SMOKE OK");
