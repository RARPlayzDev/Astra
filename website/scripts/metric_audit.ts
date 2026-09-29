/* Headless metric audit: replicates the Console's KPI pipeline exactly and
 * checks every displayed figure for errors / fairness problems.
 * Run: esbuild scripts/metric_audit.ts --bundle --platform=node --outfile=scripts/_metric_audit.cjs && node scripts/_metric_audit.cjs */
import { DEFAULT_SCENARIO, ESReceiver, RFEnvironment, type Scenario } from "../src/engine/core";
import {
  LinearQLearning, RandomScan, SequentialSweep, SmartScanScheduler,
  TeamScheduler, UCBScheduler, type Scheduler,
} from "../src/engine/schedulers";

type Opp = "openloop-sequential" | "openloop-random" | "bandit-ucb" | "rl-linear-q";
const makeLead = (p: Opp | "smart-scan", nBands: number, s: number): Scheduler =>
  p === "smart-scan" ? new SmartScanScheduler(nBands, s)
  : p === "openloop-random" ? new RandomScan(nBands, s)
  : p === "bandit-ucb" ? new UCBScheduler(nBands)
  : p === "rl-linear-q" ? new LinearQLearning(nBands, s)
  : new SequentialSweep(nBands);

interface Kpi {
  cov: number; allRatio: number; reward: number; hitRate: number; fa: number;
  ttffBuggy: number | null;   // current console: mean over ALL clean-hit slots
  ttffFixed: number | null;   // python parity: mean first-detection per emitter
  predAcc: number; predN: number;
  locksBuggy: number;         // current console: ALWAYS team A's locks
  locksFixed: number;
}

const seeds = [4242, 777, 999, 31337];
const opps: Opp[] = ["openloop-sequential", "openloop-random", "bandit-ucb", "rl-linear-q"];
const pct = (x: number | null) => (x == null ? "  -" : (x * 100).toFixed(1) + "%");
const slots = (x: number | null) => (x == null ? "  -" : x.toFixed(0).padStart(4));

let invariantFails = 0;
const fail = (msg: string) => { invariantFails++; console.error(`FAIL  ${msg}`); };

// Which metrics does the OPPONENT (B) beat SmartScan (A) on?  key=metric
const bWins: Record<string, string[]> = {};

for (const seed of seeds) {
  for (const opp of opps) {
    const cfg: Scenario = { ...DEFAULT_SCENARIO };
    const env = new RFEnvironment(cfg, seed);
    const nThreats = env.nThreats();
    const team = {
      a: new TeamScheduler([makeLead("smart-scan", cfg.nBands, seed)], cfg.nBands),
      b: new TeamScheduler([makeLead(opp, cfg.nBands, seed + 5)], cfg.nBands),
    };
    team.a.reset(cfg.T); team.b.reset(cfg.T);
    const rx = {
      a: new ESReceiver(env, seed * 7 + 11, 6),
      b: new ESReceiver(env, seed * 13 + 29, 6),
    };
    const st = {
      rewardSum: { a: 0, b: 0 }, hits: { a: 0, b: 0 }, fa: { a: 0, b: 0 },
      seenAll: { a: new Set<number>(), b: new Set<number>() },
      seenThreats: { a: new Set<number>(), b: new Set<number>() },
      ttffHitSlots: { a: [] as number[], b: [] as number[] },   // buggy TTFF feed
      ttffFirst: { a: [] as number[], b: [] as number[] },      // fixed TTFF feed
      threatFix: { a: [] as number[], b: [] as number[] },      // threat first-fix times
      pred: { a: [0, 0], b: [0, 0] },                           // [correct, n]
    };

    for (let t = 0; t < cfg.T; t++) {
      for (const side of ["a", "b"] as const) {
        const bands = team[side].selectJoint(t);
        const res = rx[side].dwell(bands[0], t);
        let r = res.falseAlarm ? -0.08 : !res.hit ? -0.05 : 0.15;
        if (res.hit && !res.falseAlarm) {
          const lead = env.emitters.find((e) => e.eid === res.detections[0]?.eid);
          r = lead?.threat ? 1 : 0.15;
        }
        const clean = res.hit && !res.falseAlarm;
        if (clean) st.ttffHitSlots[side].push(t);              // buggy TTFF feed
        if (clean) st.hits[side] += 1;
        if (res.falseAlarm) st.fa[side] += 1;
        for (const d of res.detections) {
          const isNew = !st.seenAll[side].has(d.eid);
          if (isNew) { st.seenAll[side].add(d.eid); st.ttffFirst[side].push(t); }
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

    const mk = (side: "a" | "b"): Kpi => ({
      cov: st.seenThreats[side].size / Math.max(1, nThreats),
      allRatio: st.seenAll[side].size / Math.max(1, env.emitters.length),
      reward: st.rewardSum[side] / Math.max(1, cfg.T),
      hitRate: st.hits[side] / Math.max(1, cfg.T),
      fa: st.fa[side],
      ttffBuggy: st.ttffHitSlots[side].length
        ? st.ttffHitSlots[side].reduce((x, y) => x + y, 0) / st.ttffHitSlots[side].length : null,
      ttffFixed: st.ttffFirst[side].length
        ? st.ttffFirst[side].reduce((x, y) => x + y, 0) / st.ttffFirst[side].length : null,
      predAcc: st.pred[side][1] ? st.pred[side][0] / st.pred[side][1] : 0,
      predN: st.pred[side][1],
      locksBuggy: (team.a.first as SmartScanScheduler).locks ?? 0, // current console
      locksFixed: (team[side].first as { locks?: number }).locks ?? 0,
    });
    const A = mk("a"), B = mk("b");

    // ---- invariants -------------------------------------------------------
    for (const [name, k] of [["A", A], ["B", B]] as const) {
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

    // ---- who wins each metric -------------------------------------------
    const better = (m: string, aV: number, bV: number, higherWins: boolean) => {
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
    // Censored threat TTFF (console display rule): unfixed threats cost the
    // full horizon, so a side that silently misses threats can never look
    // faster (parity with ewsmart.metrics threat_ttff_censored).
    const censThreat = (side: "a" | "b"): number => {
      const fx = st.threatFix[side];
      return (fx.reduce((x, y) => x + y, 0) + (nThreats - fx.length) * cfg.T)
             / Math.max(1, nThreats);
    };
    better("threat TTFF censored", censThreat("a"), censThreat("b"), false);

    console.log(
      `seed ${seed} vs ${opp.replace("openloop-", "").replace("bandit-", "").replace("rl-", "")}\n` +
      `  cov  A ${pct(A.cov)}  B ${pct(B.cov)}   ` +
      `hit  A ${pct(A.hitRate)}  B ${pct(B.hitRate)}   ` +
      `rew  A ${A.reward.toFixed(3)}  B ${B.reward.toFixed(3)}\n` +
      `  fa   A ${String(A.fa).padStart(3)}  B ${String(B.fa).padStart(3)}   ` +
      `pred A ${pct(A.predAcc)}  B ${pct(B.predAcc)}\n` +
      `  ttff buggy A ${slots(A.ttffBuggy)}  B ${slots(B.ttffBuggy)}  |  ` +
      `fixed A ${slots(A.ttffFixed)}  B ${slots(B.ttffFixed)}\n` +
      `  locks buggy A/B ${A.locksBuggy}/${B.locksBuggy}  fixed A/B ${A.locksFixed}/${B.locksFixed}`
    );
  }
}

console.log("\n=== metrics where the OPPONENT beats SmartScan (over all runs) ===");
for (const [m, runs] of Object.entries(bWins))
  console.log(`  ${m.padEnd(20)} ${runs.length}/${seeds.length * opps.length} runs: ${runs.join(", ")}`);
if (Object.keys(bWins).length === 0) console.log("  (none)");

console.log(invariantFails === 0 ? "\nAUDIT INVARIANTS PASSED" : `\nAUDIT INVARIANTS FAILED (${invariantFails})`);
process.exit(invariantFails === 0 ? 0 : 1);
