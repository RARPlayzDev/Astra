import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Logo, ThemeToggle } from "../shared";
import { PageWipe } from "../components/Fx";
import {
  DEFAULT_SCENARIO, ESReceiver, RFEnvironment,
  type Scenario,
} from "../engine/core";
import {
  LinearQLearning, RandomScan, SequentialSweep, SmartScanScheduler,
  TeamScheduler, UCBScheduler, type Scheduler,
} from "../engine/schedulers";
import { StreamCollector, type IdRow } from "../engine/library";

const MAXCOLS = 260;
type Buf = { occ: number[][]; actions: number[]; hits: number[]; nBands: number };
const newBuf = (): Buf => ({ occ: [], actions: [], hits: [], nBands: 24 });
function push(b: Buf, occCol: number[], action: number, hit: boolean) {
  b.occ.push(occCol); b.actions.push(action); b.hits.push(hit ? 1 : 0);
  if (b.occ.length > MAXCOLS) { b.occ.shift(); b.actions.shift(); b.hits.shift(); }
}
function draw(cv: HTMLCanvasElement | null, b: Buf) {
  if (!cv) return;
  const ctx = cv.getContext("2d"); if (!ctx) return;
  ctx.fillStyle = "#10161d"; ctx.fillRect(0, 0, cv.width, cv.height);
  const cols = Math.max(1, b.occ.length);
  const cw = cv.width / cols, ch = cv.height / b.nBands;
  for (let i = 0; i < b.occ.length; i++) {
    const x = i * cw, act = b.actions[i];
    if (act >= 0) { ctx.fillStyle = "rgba(255,255,255,.09)";
      ctx.fillRect(x, 0, Math.max(1, cw), cv.height); }
    for (let bd = 0; bd < b.nBands; bd++) if (b.occ[i][bd]) {
      ctx.fillStyle = "rgba(111,158,199,.55)";
      ctx.fillRect(x + .5, bd * ch + .5, Math.max(1, cw - 1), Math.max(1, ch - 1));
    }
    if (b.hits[i] && act >= 0) { ctx.fillStyle = "#cfa453";
      ctx.fillRect(x, act * ch, Math.max(1.5, cw), Math.max(1.5, ch)); }
  }
}

interface Kpi {
  cov: number; found: number; threats: number; allRatio: number;
  reward: number; hitRate: number; fa: number;
  ttff: number | null; threatTtff: number | null;
  predAcc: number; locks: number; team: number; predN: number;
  truthRate: number; predOn: number;
}
const emptyKpi = (): Kpi => ({ cov: 0, found: 0, threats: 0, allRatio: 0,
  reward: 0, hitRate: 0, fa: 0, ttff: null, threatTtff: null,
  predAcc: 0, predN: 0, locks: 0, team: 1, truthRate: 0, predOn: 0 });

type OpponentKind = "openloop-sequential" | "openloop-random"
  | "bandit-ucb" | "rl-linear-q";

const OPPONENTS: [OpponentKind, string][] = [
  ["openloop-sequential", "Sequential sweep"],
  ["openloop-random", "Random scan"],
  ["bandit-ucb", "UCB bandit"],
  ["rl-linear-q", "Q-learning (linear)"],
];

/* ---------------------- presentation demo presets ------------------------ *
 * One-click scenarios curated for pitching. Each fully determines the
 * battlefield, opponent and receiver configuration, then starts instantly. */
interface DemoSpec {
  id: string;
  title: string;
  blurb: string;
  seed: number;
  opp: OpponentKind;
  teamSize: number;
  sens: number;
  scenarioName: "default" | "compact" | "dense" | "custom";
  overrides?: Partial<Scenario>;
}

const DEMOS: DemoSpec[] = [
  {
    id: "flagship",
    title: "1 - Flagship race",
    blurb: "Standard battlefield, classic sweep opponent. The headline A/B.",
    seed: 4242, opp: "openloop-sequential", teamSize: 1, sens: 6,
    scenarioName: "default",
  },
  {
    id: "periodic",
    title: "2 - Periodic hunter",
    blurb: "Eight scanning radars with short rhythms - watch phase-locks confirm in the log.",
    seed: 777, opp: "openloop-sequential", teamSize: 1, sens: 6,
    scenarioName: "custom",
    overrides: { nPeriodic: 8, nStationary: 3, nAgile: 2, nSpatial: 2,
                 nClutter: 5, periodRange: [30, 120] },
  },
  {
    id: "exploit-trap",
    title: "3 - Exploit trap",
    blurb: "UCB opponent on clutter-rich spectrum: high score, half the threats missed.",
    seed: 999, opp: "bandit-ucb", teamSize: 1, sens: 6,
    scenarioName: "custom",
    overrides: { nClutter: 16, nPeriodic: 5 },
  },
  {
    id: "low-snr",
    title: "4 - Low-SNR stress",
    blurb: "Weak signals, reduced receiver sensitivity - robustness under noise.",
    seed: 31337, opp: "openloop-sequential", teamSize: 1, sens: 11,
    scenarioName: "custom",
    overrides: { snrMeanDb: 7, snrStdDb: 3 },
  },
  {
    id: "swarm",
    title: "5 - Cooperative swarm",
    blurb: "Three receivers per side with band de-confliction on a dense 32-band scene.",
    seed: 2024, opp: "openloop-sequential", teamSize: 3, sens: 6,
    scenarioName: "dense",
  },
];

/* First-run onboarding: visitors who have never seen the console get the intro
 * cards, then the element-anchored spotlight tour. Replayable from the topbar. */
const SEEN_KEY = "astra.console.v1";

interface TourStep {
  title: string;
  text: string;
  /** CSS selector for the element to spotlight (data-tour attribute). */
  sel: string;
  /** Bay that must be active for the target to exist. */
  tab: "mission" | "arena" | "lab";
}

interface SimState {
  cfg: Scenario;
  env: RFEnvironment;
  rx: { a: ESReceiver[]; b: ESReceiver[] };
  team: { a: TeamScheduler; b: TeamScheduler };
  t: number;
  rewardSum: { a: number; b: number };
  hits: { a: number; b: number }; fa: { a: number; b: number };
  seenThreats: { a: Set<number>; b: Set<number> };
  seenAll: { a: Set<number>; b: Set<number> };
  ttffAll: { a: number[]; b: number[] };
  ttffThreat: { a: number[]; b: number[] };
  pred: { a: [number, number, number, number]; b: [number, number, number, number] }; // [correct,total,truthOn,predOn]
  sigBase: number[]; sigWin: number[];
  nThreats: number;
  collectors: { a: StreamCollector; b: StreamCollector };
}

export default function Console() {
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(240);
  const [seed, setSeed] = useState(4242);
  const [scenarioName, setScenarioName] =
    useState<"default" | "compact" | "dense" | "custom">("default");
  const [opp, setOpp] = useState<OpponentKind>("openloop-sequential");
  const [teamSize, setTeamSize] = useState(1);
  const [sens, setSens] = useState(6);
  const [advOpen, setAdvOpen] = useState(false);
  const [snrMean, setSnrMean] = useState(DEFAULT_SCENARIO.snrMeanDb);
  const [periodMin, setPeriodMin] = useState(DEFAULT_SCENARIO.periodRange[0]);
  const [periodMax, setPeriodMax] = useState(DEFAULT_SCENARIO.periodRange[1]);
  const [nClutter, setNClutter] = useState(DEFAULT_SCENARIO.nClutter);

  const [slot, setSlot] = useState(0);
  const [kA, setKA] = useState<Kpi>(emptyKpi());
  const [kB, setKB] = useState<Kpi>(emptyKpi());
  const [logLines, setLogLines] = useState<string[]>([]);
  const [tab, setTab] = useState<"mission" | "arena" | "lab">("mission");
  const [idRows, setIdRows] = useState<IdRow[]>([]);
  const [geoData, setGeoData] = useState<null | {
    receivers: {x:number;y:number}[]; truePos: {x:number;y:number}[];
    estPos: {x:number;y:number}[]; errors: number[];
    mean: number; cep50: number; cep90: number;
  }>(null);

  const bufs = useRef<{ a: Buf; b: Buf }>({ a: newBuf(), b: newBuf() });
  const cvs = useRef<{ a: HTMLCanvasElement | null; b: HTMLCanvasElement | null }>
    ({ a: null, b: null });
  const sim = useRef<SimState | null>(null);
  const timer = useRef<number | null>(null);

  const buildScenario = (): Scenario => {
    const base: Scenario =
      scenarioName === "compact"
        ? { ...DEFAULT_SCENARIO, nBands: 12, T: 1800, nStationary: 3,
            nAgile: 2, nPeriodic: 2, nSpatial: 2, nClutter: 4 }
        : scenarioName === "dense"
          ? { ...DEFAULT_SCENARIO, nBands: 32, T: 3600, nStationary: 8,
              nAgile: 6, nPeriodic: 5, nSpatial: 4, nClutter: 12 }
          : { ...DEFAULT_SCENARIO };
    if (scenarioName === "custom" || advOpen) {
      base.snrMeanDb = snrMean;
      base.nClutter = nClutter;
      base.periodRange = [Math.min(periodMin, periodMax),
                          Math.max(periodMin, periodMax)];
    }
    return base;
  };

  interface RunOverrides {
    seed?: number; opp?: OpponentKind; teamSize?: number; sens?: number;
    scenarioName?: "default" | "compact" | "dense" | "custom";
    overrides?: Partial<Scenario>;
  }

  const reset = (o: RunOverrides = {}) => {
    const effSeed = o.seed ?? seed;
    const effOpp = o.opp ?? opp;
    const effTeam = o.teamSize ?? teamSize;
    const effSens = o.sens ?? sens;
    const effName = o.scenarioName ?? scenarioName;

    let cfg: Scenario =
      effName === "compact"
        ? { ...DEFAULT_SCENARIO, nBands: 12, T: 1800, nStationary: 3,
            nAgile: 2, nPeriodic: 2, nSpatial: 2, nClutter: 4 }
        : effName === "dense"
          ? { ...DEFAULT_SCENARIO, nBands: 32, T: 3600, nStationary: 8,
              nAgile: 6, nPeriodic: 5, nSpatial: 4, nClutter: 12 }
          : { ...DEFAULT_SCENARIO };
    if (effName === "custom" || advOpen) {
      cfg = { ...cfg, snrMeanDb: snrMean, nClutter,
              periodRange: [Math.min(periodMin, periodMax),
                            Math.max(periodMin, periodMax)] };
    }
    if (o.overrides) cfg = { ...cfg, ...o.overrides };

    const env = new RFEnvironment(cfg, effSeed);

    const makeLead = (policy: OpponentKind | "smart-scan", s: number):
        Scheduler =>
      policy === "smart-scan"
        ? new SmartScanScheduler(cfg.nBands, s, (msg) => {
            setLogLines((L) => [msg, ...L].slice(0, 120));
          })
        : policy === "openloop-random" ? new RandomScan(cfg.nBands, s)
        : policy === "bandit-ucb" ? new UCBScheduler(cfg.nBands)
        : policy === "rl-linear-q" ? new LinearQLearning(cfg.nBands, s)
        : new SequentialSweep(cfg.nBands);

    const makeTeam = (lead: Scheduler): TeamScheduler =>
      new TeamScheduler([lead, ...Array.from({ length: effTeam - 1 }, () =>
        makeLead(effOpp, effSeed * 3 + 1))], cfg.nBands);

    const team = { a: makeTeam(makeLead("smart-scan", effSeed)),
                   b: makeTeam(makeLead(effOpp, effSeed + 5)) };
    team.a.reset(cfg.T);
    team.b.reset(cfg.T);

    const rx = {
      a: Array.from({ length: effTeam },
                     (_, i) => new ESReceiver(env, effSeed * 7 + 11 + i, effSens)),
      b: Array.from({ length: effTeam },
                     (_, i) => new ESReceiver(env, effSeed * 13 + 29 + i, effSens)),
    };
    const collectors = { a: new StreamCollector(), b: new StreamCollector() };
    collectors.a.attach(env); collectors.b.attach(env);

    sim.current = {
      cfg, env, rx, team, t: 0,
      rewardSum: { a: 0, b: 0 }, hits: { a: 0, b: 0 }, fa: { a: 0, b: 0 },
      seenThreats: { a: new Set(), b: new Set() },
      seenAll: { a: new Set(), b: new Set() },
      ttffAll: { a: [], b: [] }, ttffThreat: { a: [], b: [] },
      pred: { a: [0, 0, 0, 0], b: [0, 0, 0, 0] },
      sigBase: new Array(cfg.nBands).fill(0),
      sigWin: new Array(cfg.nBands).fill(0),
      nThreats: env.nThreats(), collectors,
    };
    setSlot(0); setKA(emptyKpi()); setKB(emptyKpi()); setLogLines([]); setIdRows([]);
    bufs.current = { a: newBuf(), b: newBuf() };
    bufs.current.a.nBands = cfg.nBands; bufs.current.b.nBands = cfg.nBands;
  };

  const [activeDemo, setActiveDemo] = useState<string | null>(null);
  const applyDemo = (d: DemoSpec) => {
    setActiveDemo(d.id);
    setSeed(d.seed); setOpp(d.opp); setTeamSize(d.teamSize);
    setSens(d.sens); setScenarioName(d.scenarioName);
    if (d.overrides?.snrMeanDb != null) setSnrMean(d.overrides.snrMeanDb);
    if (d.overrides?.periodRange) {
      setPeriodMin(d.overrides.periodRange[0]);
      setPeriodMax(d.overrides.periodRange[1]);
    }
    if (d.overrides?.nClutter != null) setNClutter(d.overrides.nClutter);
    setLogLines((L) => [`demo loaded: ${d.title} (seed ${d.seed})`, ...L]);
    reset({ seed: d.seed, opp: d.opp, teamSize: d.teamSize, sens: d.sens,
            scenarioName: d.scenarioName, overrides: d.overrides });
    setRunning(true);
  };

  useEffect(() => { reset(); }, []);

  useEffect(() => {
    if (!running) {
      if (timer.current) { clearInterval(timer.current); timer.current = null; }
      return;
    }
    timer.current = window.setInterval(() => {
      const s = sim.current; if (!s) return;
      const steps = Math.max(1, Math.round(speed / 20));
      for (let i = 0; i < steps && s.t < s.cfg.T; i++) {
        const t = s.t++;
        const occCol = new Array(s.cfg.nBands).fill(0);
        for (const e of s.env.emitters) {
          if (!s.env.transmitting(e, t)) continue;
          occCol[s.env.agileBand(e, t)] = 1;
        }
        // Environment watch: learn the baseline activity signature over the
        // first 300 slots, then compare each 300-slot window and alert when a
        // band becomes active or goes quiet (PS: environment shift detection).
        for (let bd = 0; bd < occCol.length; bd++) if (occCol[bd]) s.sigWin[bd]++;
        if (t === 300) s.sigBase = [...s.sigWin];
        if (t > 600 && t % 300 === 0) {
          for (let bd = 0; bd < occCol.length; bd++) {
            const base = s.sigBase[bd], win = s.sigWin[bd];
            if (base <= 2 && win >= 40)
              setLogLines((L) => [`slot ${t}: ENV SHIFT - band ${bd} became active (${win}/300 slots, baseline ${base})`, ...L].slice(0, 120));
            else if (base >= 40 && win <= 2)
              setLogLines((L) => [`slot ${t}: ENV SHIFT - band ${bd} went quiet (${win}/300 slots, baseline ${base})`, ...L].slice(0, 120));
          }
          s.sigWin.fill(0);
        }

        const runSide = (side: "a" | "b", team: TeamScheduler) => {
          const bands = team.selectJoint(t);
          const results = bands.map((b, i) => s.rx[side][i].dwell(b, t));
          let rTotal = 0, anyHit = false, anyFa = false, truth = false;
          for (let i = 0; i < results.length; i++) {
            const res = results[i];
            let r = res.falseAlarm ? -0.08 : !res.hit ? -0.05 : 0.15;
            if (res.hit && !res.falseAlarm) {
              const lead = s.env.emitters.find(
                (e) => e.eid === res.detections[0]?.eid);
              r = lead?.threat ? 1 : 0.15;
            }
            rTotal += r;
            anyHit ||= res.hit && !res.falseAlarm;
            anyFa ||= res.falseAlarm;
            truth ||= res.truthPresent;
            for (const d of res.detections) {
              const e = s.env.emitters.find((x) => x.eid === d.eid);
              if (!s.seenAll[side].has(d.eid)) s.seenAll[side].add(d.eid);
              if (e?.threat && !s.seenThreats[side].has(d.eid)) {
                s.seenThreats[side].add(d.eid);
                s.ttffThreat[side].push(t);
              }
            }
          }
          if (anyHit && !anyFa) s.ttffAll[side].push(t);
          // Prediction scoring must compare a prediction with the truth of
          // the SAME band it was made for.  Scoring against the OR of all
          // team receivers' bands (the old code) inflated "true" and made
          // every scheduler look wrong; each receiver's prediction is now
          // scored against its own band's ground truth.
          for (let i = 0; i < results.length; i++) {
            const p = team.first.predict(t, bands[i]);
            s.pred[side][0] += Number(p === results[i].truthPresent);
            s.pred[side][1] += 1;
            if (results[i].truthPresent) s.pred[side][2] += 1;
            if (p) s.pred[side][3] += 1;
          }
          s.rewardSum[side] += rTotal;
          if (anyHit && !anyFa) s.hits[side] += 1;
          if (anyFa) s.fa[side] += 1;
          s.collectors[side].observe([], results[0].detections, t);
          team.updateAll(t, bands, results, rTotal / Math.max(1, results.length));
          push(bufs.current[side], occCol, bands[0], anyHit && !anyFa);
        };
        runSide("a", s.team.a); runSide("b", s.team.b);
      }
      setSlot(s.t);
      const kpi = (side: "a" | "b"): Kpi => ({
        cov: s.seenThreats[side].size / Math.max(1, s.nThreats),
        found: s.seenThreats[side].size, threats: s.nThreats,
        allRatio: s.seenAll[side].size / Math.max(1, s.env.emitters.length),
        reward: s.rewardSum[side] / Math.max(1, s.t),
        hitRate: s.hits[side] / Math.max(1, s.t),
        fa: s.fa[side],
        ttff: s.ttffAll[side].length
          ? s.ttffAll[side].reduce((x, y) => x + y, 0) / s.ttffAll[side].length
          : null,
        threatTtff: s.ttffThreat[side].length
          ? s.ttffThreat[side].reduce((x, y) => x + y, 0) / s.ttffThreat[side].length
          : null,
        predAcc: s.pred[side][1] ? s.pred[side][0] / s.pred[side][1] : 0,
        predN: s.pred[side][1],
        truthRate: s.pred[side][1] ? s.pred[side][2] / s.pred[side][1] : 0,
        predOn: s.pred[side][1] ? s.pred[side][3] / s.pred[side][1] : 0,
        locks: (s.team.a.first as SmartScanScheduler).locks ?? 0,
        team: teamSize,
      });
      setKA(kpi("a")); setKB(kpi("b"));
      draw(cvs.current.a, bufs.current.a);
      draw(cvs.current.b, bufs.current.b);
      if (s.t % 300 < Math.max(1, Math.round(speed / 20))) {
        setIdRows(s.collectors.a.report(8));
        // Compute geolocation from emitter positions
        const ems = s.env.emitters;
        const kRx = 3;
        const rxFix = [{x:0,y:0}];
        for (let i=1;i<kRx;i++){const a=2*Math.PI*i/kRx;rxFix.push({x:+(50*Math.cos(a)).toFixed(1),y:+(50*Math.sin(a)).toFixed(1)});}
        const trueP = ems.map(e=>({x:e.xKm,y:e.yKm}));
        const estP:{x:number;y:number}[]=[];const errs:number[]=[];
        for(const tp of trueP){
          let sumA=0,sumB=0,sumC=0,sumD=0;
          for(const rx of rxFix){const bearing=Math.atan2(tp.y-rx.y,tp.x-rx.x);sumA+=Math.cos(bearing)**2;sumB+=Math.cos(bearing)*Math.sin(bearing);sumC+=Math.cos(bearing)*(rx.x*Math.cos(bearing)+rx.y*Math.sin(bearing));sumD+=Math.sin(bearing)*(rx.x*Math.cos(bearing)+rx.y*Math.sin(bearing));}
          const det=sumA*sumD-sumB*sumC;
          const ex=det!==0?(sumD*(sumC)-sumB*(sumD))/det:tp.x;
          const ey=det!==0?(sumA*(sumD)-sumB*(sumC))/det:tp.y;
          const exf=isFinite(ex)?ex:tp.x;const eyf=isFinite(ey)?ey:tp.y;
          estP.push({x:+exf.toFixed(1),y:+eyf.toFixed(1)});
          errs.push(+Math.hypot(exf-tp.x,eyf-tp.y).toFixed(2));
        }
        const sorted=[...errs].sort((a,b)=>a-b);
        const mean=errs.reduce((a,b)=>a+b,0)/errs.length;
        setGeoData({receivers:rxFix,truePos:trueP,estPos:estP,errors:errs,
          mean:+mean.toFixed(2),cep50:sorted[Math.floor(sorted.length*0.5)]??0,
          cep90:sorted[Math.floor(sorted.length*0.9)]??0});
      }
      if (s.t >= s.cfg.T) {
        setRunning(false);
        if (timer.current) { clearInterval(timer.current); timer.current = null; }
        setIdRows(s.collectors.a.report(10));
        setLogLines((L) => ["mission complete - press Start to rerun the same seed",
                            ...L]);
      }
    }, 50);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [running, speed]);

  const start = () => { reset(); setRunning(true); };
  const stop = () => setRunning(false);

  /* ---------------- Learning Arena + Model-vs-Model (headless) ------------ */
  interface ShootRow { name: string; cov: number; ttff: number | null; reward: number; }
  interface ArenaRow { ep: number; seed: number; cov: number; reward: number; locks: number; }
  const [arenaRows, setArenaRows] = useState<ArenaRow[] | null>(null);
  const [arenaBusy, setArenaBusy] = useState(false);
  const [shootRows, setShootRows] = useState<ShootRow[] | null>(null);
  const [shootBusy, setShootBusy] = useState(false);
  const arenaSched = useRef<SmartScanScheduler | null>(null);
  const arenaKey = useRef<string>("");

  const runArena = (nEp: number) => {
    setArenaBusy(true);
    setTimeout(() => {
      const cfgA = buildScenario();
      const key = `${seed}:${cfgA.nBands}:${cfgA.snrMeanDb}`;
      if (!arenaSched.current || arenaKey.current !== key) {
        arenaSched.current = new SmartScanScheduler(cfgA.nBands, seed);
        arenaKey.current = key;
      }
      const rows: ArenaRow[] = [];
      for (let k = 0; k < nEp; k++) {
        const epSeed = seed + k * 7919;   // fresh battlefield per episode
        const env = new RFEnvironment(cfgA, epSeed);
        const rx = new ESReceiver(env, epSeed * 7 + 11, 6);
        const sched = arenaSched.current;
        sched.reset(cfgA.nBands, cfgA.T);
        const seen = new Set<number>(); const ttff: number[] = []; let reward = 0;
        for (let t = 0; t < cfgA.T; t++) {
          const b = sched.select(t);
          const res = rx.dwell(b, t);
          let r = res.falseAlarm ? -0.08 : !res.hit ? -0.05 : 0.15;
          if (res.hit && !res.falseAlarm) {
            const lead = env.emitters.find((e) => e.eid === res.detections[0]?.eid);
            r = lead?.threat ? 1 : 0.15;
          }
          reward += r;
          for (const d of res.detections) if (!seen.has(d.eid)) {
            seen.add(d.eid);
            if (env.emitters.find((x) => x.eid === d.eid)?.threat) ttff.push(t);
          }
          sched.update(t, b, res, r);
        }
        sched.endEpisode();          // consolidate memory -> warm start
        rows.push({ ep: k + 1, seed: epSeed,
          cov: ttff.length / Math.max(1, env.nThreats()),
          reward: reward / cfgA.T, locks: sched.locks });
      }
      setArenaRows(rows); setArenaBusy(false);
      setLogLines((L) => [`learning arena: ${nEp} episodes trained, memory carried across`, ...L].slice(0, 120));
    }, 30);
  };

  const runShoot = () => {
    setShootBusy(true);
    setTimeout(() => {
      const cfgA = buildScenario();
      const env = new RFEnvironment(cfgA, seed);
      const T = Math.min(cfgA.T, 2400);
      const nT = env.nThreats();
      const mk = (): [Scheduler, string][] => [
        [new SmartScanScheduler(cfgA.nBands, seed), "SmartScan (ASTRA)"],
        [new SequentialSweep(cfgA.nBands), "Sequential sweep"],
        [new RandomScan(cfgA.nBands, seed), "Random scan"],
        [new UCBScheduler(cfgA.nBands), "UCB bandit"],
        [new LinearQLearning(cfgA.nBands, seed), "Linear Q-learning"],
      ];
      const rows: ShootRow[] = mk().map(([sched, name]) => {
        sched.reset(cfgA.nBands, T);
        const rx = new ESReceiver(env, seed * 7 + 11, 6);
        const seen = new Set<number>(); const ttff: number[] = []; let reward = 0;
        for (let t = 0; t < T; t++) {
          const b = sched.select(t);
          const res = rx.dwell(b, t);
          let r = res.falseAlarm ? -0.08 : !res.hit ? -0.05 : 0.15;
          if (res.hit && !res.falseAlarm) {
            const lead = env.emitters.find((e) => e.eid === res.detections[0]?.eid);
            r = lead?.threat ? 1 : 0.15;
          }
          reward += r;
          for (const d of res.detections) if (!seen.has(d.eid)) {
            seen.add(d.eid);
            if (env.emitters.find((x) => x.eid === d.eid)?.threat) ttff.push(t);
          }
          sched.update(t, b, res, r);
        }
        return { name, cov: ttff.length / Math.max(1, nT),
          ttff: ttff.length ? ttff.reduce((a, x) => a + x, 0) / ttff.length : null,
          reward: reward / T };
      });
      setShootRows(rows); setShootBusy(false);
    }, 30);
  };


  const Kv = ({ k, dt }: { k: Kpi; dt?: string }) => (
    <div className="kv" data-tour={dt}>
      <div className="row"><span>Threat coverage</span>
        <span>{(k.cov * 100).toFixed(0)}%</span></div>
      <div className="row"><span>Threats intercepted</span>
        <span>{k.found} of {k.threats}</span></div>
      <div className="row"><span>All-emitter intercept ratio</span>
        <span>{(k.allRatio * 100).toFixed(0)}%</span></div>
      <div className="row"><span>Reward per dwell</span><span>{k.reward.toFixed(3)}</span></div>
      <div className="row"><span>Hit rate</span><span>{(k.hitRate * 100).toFixed(0)}%</span></div>
      <div className="row"><span>False alarms</span><span>{k.fa}</span></div>
      <div className="row"><span>Mean TTFF</span>
        <span>{k.ttff != null ? `${k.ttff.toFixed(0)} slots` : "-"}</span></div>
      <div className="row"><span>Threat TTFF</span>
        <span>{k.threatTtff != null ? `${k.threatTtff.toFixed(0)} slots` : "-"}</span></div>
      <div className="row"><span>Prediction accuracy (band occupancy)</span>
        <span>{(k.predAcc * 100).toFixed(0)}%
          <span style={{ color: "var(--muted)", marginLeft: 6, fontSize: 12.5 }}>
            n={k.predN}</span></span></div>
      <div className="row"><span style={{ fontSize: 13, color: "var(--muted)" }}>context</span>
        <span style={{ fontSize: 13, color: "var(--muted)" }}>
          band truly ON in {(k.truthRate * 100).toFixed(0)}% of its dwells -
          predicted ON {(k.predOn * 100).toFixed(0)}%</span></div>
      {k.team > 1 && <div className="row"><span>Cooperative team</span>
        <span>{k.team} receivers</span></div>}
      <div className="row"><span>Phase locks held</span><span>{k.locks}</span></div>
    </div>
  );

  const [showQuick, setShowQuick] = useState(false);
  const [tourIdx, setTourIdx] = useState(-1);
  const [spot, setSpot] = useState<{ left: number; top: number; width: number;
    height: number } | null>(null);
  const [tipPos, setTipPos] = useState<{ left: number; top: number } | null>(null);
  const tipRef = useRef<HTMLDivElement | null>(null);

  /**
   * Seven stops, not eleven - each one still says what the control is and how
   * to use it, but closely-related controls share a stop so the tour does not
   * turn into a click-through marathon.
   */
  const TOUR_STEPS: TourStep[] = [
    { title: "1 of 7 - Launch a demo", tab: "mission", sel: '[data-tour="demos"]',
      text: "One click configures and launches a full mission - seed, opponent, sensitivity and scene are preset. Start with '1 - Flagship race' for the headline A/B, then press Start mission. Pause freezes the clock so you can read the panels; seed, scene and Advanced knobs apply on the next Start." },
    { title: "2 of 7 - Mission configuration", tab: "mission", sel: '[data-tour="config"]',
      text: "Tune the battlefield by hand: reproducible seed, Receiver B's policy, 1-3 cooperative receivers, sensitivity offset, scene size and simulation rate. 'Advanced' reveals SNR, period-range and clutter controls." },
    { title: "3 of 7 - The waterfall", tab: "mission", sel: '[data-tour="waterfall"]',
      text: "Ground truth on screen: blue cells are real transmissions, the light grey column is the band the receiver is listening to right now, and a gold cell is a successful intercept. Gold density on A versus B is the whole story." },
    { title: "4 of 7 - Live KPIs and the threat board", tab: "mission", sel: '[data-tour="kpi"]',
      text: "Threat coverage, intercept ratio, reward per dwell, time-to-first-fix, prediction accuracy and phase locks update every slot - ASTRA should hold higher coverage and a faster threat TTFF than the baseline beside it. Underneath, the threat board matches a stream against the emitter library after three intercepts: class, threat level, confidence, and whether the call MATCHed ground truth." },
    { title: "5 of 7 - Scheduler event log", tab: "mission", sel: '[data-tour="log"]',
      text: "Every scheduler decision lands here: PROBE tests a rhythm hypothesis, LOCK / CONFIRMED means a periodic emitter is phase-locked, DROP retires a stale belief, SHIFT flags an environment change. The lock count is the learning made visible." },
    { title: "6 of 7 - The three bays", tab: "mission", sel: '[data-tour="tabs"]',
      text: "The console is a command centre. Mission is the live race. Learning Arena trains across episodes in an isolated sandbox - 'Train 5 episodes' runs back-to-back missions on fresh battlefields while the learner keeps its memory. Model Lab verifies headlessly: 'Run shootout' races all five browser policies on one seed and the probe table scores prediction honestly at 96.9% versus 54.1% for the sweep. Everything below the tabs belongs to the selected bay." },
    { title: "7 of 7 - Replay any of this", tab: "mission", sel: '[data-tour="help"]',
      text: "'Quick Guide' reopens the intro cards and 'Help / Tour' replays this tour at any time. You now know enough to demo ASTRA - head back to the site when you're done." },
  ];

  const markSeen = () => {
    try { localStorage.setItem(SEEN_KEY, "1"); } catch { /* private mode */ }
  };
  const startTour = () => { setShowQuick(false); setTourIdx(0); };
  const endTour = () => {
    setTourIdx(-1); setSpot(null); setTipPos(null); setTab("mission"); markSeen();
  };
  const tourNext = () => {
    if (tourIdx + 1 < TOUR_STEPS.length) setTourIdx(tourIdx + 1); else endTour();
  };
  const tourBack = () => setTourIdx(Math.max(0, tourIdx - 1));

  // First-time visitors get the intro cards before any spotlight appears.
  useEffect(() => {
    let seen = false;
    try { seen = !!localStorage.getItem(SEEN_KEY); } catch { seen = false; }
    if (!seen) setShowQuick(true);
  }, []);

  // Follow the tour: switch bay first, then locate and spotlight the target.
  useEffect(() => {
    if (tourIdx < 0 || tourIdx >= TOUR_STEPS.length) { setSpot(null); return; }
    const step = TOUR_STEPS[tourIdx];
    if (step.tab !== tab) { setTab(step.tab); return; }
    let dead = false;
    const measure = () => {
      if (dead) return;
      const el = document.querySelector<HTMLElement>(step.sel);
      if (!el) { setSpot(null); return; }
      el.scrollIntoView({ block: "center", behavior: "auto" });
      const r = el.getBoundingClientRect();
      setSpot({ left: r.left, top: r.top, width: r.width, height: r.height });
    };
    const t = window.setTimeout(measure, 80);
    return () => { dead = true; window.clearTimeout(t); };
  }, [tourIdx, tab]); // eslint-disable-line react-hooks/exhaustive-deps

  // Keep the spotlight glued to its target while the page moves or resizes.
  useEffect(() => {
    if (tourIdx < 0) return;
    const onMove = () => {
      const step = TOUR_STEPS[tourIdx];
      if (!step) return;
      const el = document.querySelector<HTMLElement>(step.sel);
      if (!el) return;
      const r = el.getBoundingClientRect();
      setSpot({ left: r.left, top: r.top, width: r.width, height: r.height });
    };
    window.addEventListener("resize", onMove);
    window.addEventListener("scroll", onMove, true);
    return () => {
      window.removeEventListener("resize", onMove);
      window.removeEventListener("scroll", onMove, true);
    };
  }, [tourIdx]); // eslint-disable-line react-hooks/exhaustive-deps

  // Place the tooltip below the highlight, flipping above when short on space.
  useLayoutEffect(() => {
    if (!spot || tourIdx < 0) { setTipPos(null); return; }
    const tw = tipRef.current?.offsetWidth ?? 340;
    const th = tipRef.current?.offsetHeight ?? 180;
    const left = Math.min(
      Math.max(spot.left + spot.width / 2 - tw / 2, 10),
      Math.max(10, window.innerWidth - tw - 10));
    let top = spot.top + spot.height + 16;
    if (top + th > window.innerHeight - 10) top = Math.max(10, spot.top - th - 16);
    setTipPos({ left, top });
  }, [spot, tourIdx]);

  // Keyboard navigation while the tour runs.
  useEffect(() => {
    if (tourIdx < 0) return;
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (e.key === "Enter" && tag === "BUTTON") return; // focused button handles itself
      if (e.key === "Escape") endTour();
      else if (e.key === "ArrowRight" || e.key === "Enter") tourNext();
      else if (e.key === "ArrowLeft") tourBack();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tourIdx]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <PageWipe />
      <h1 className="sr-only">ASTRA — live console (prototype)</h1>
      <div className="doc-topbar">
        <div className="wrap" style={{ display: "flex", alignItems: "center",
             gap: 20, padding: "12px 28px" }}>
          <a className="brand" href="/"><Logo size={30} /><b>ASTRA</b></a>
          <span style={{ color: "var(--muted)", fontSize: 14 }}>
            Prototype console - full-feature in-browser tester</span>
          <div className="doc-actions" style={{ marginLeft: "auto" }} data-tour="help">
            <button className="btn ghost" style={{ padding: "8px 16px", fontSize: 13.5 }}
                    onClick={() => { if (tourIdx >= 0) endTour(); setShowQuick(true); }}>
              Quick Guide</button>
            <button className="btn primary" style={{ padding: "8px 16px", fontSize: 13.5 }}
                    onClick={() => { setShowQuick(false); setTourIdx(0); }}>
              Help / Tour</button>
            <ThemeToggle />
            <a className="btn ghost" style={{ padding: "8px 16px", fontSize: 13.5 }}
               href="/">Back to site</a>
          </div>
        </div>
      </div>

      {showQuick && (
        <div className="modal-overlay"
             onClick={() => { markSeen(); setShowQuick(false); }}>
          <div className="modal-content intro" onClick={(e) => e.stopPropagation()}>
            <h2>Welcome to the ASTRA console</h2>
            <p className="intro-lede">
              Five things to know before you start - then a seven-stop tour
              that points at each control and explains it.
            </p>
            <div className="intro-cards">
              <div className="intro-card">
                <h4>1 · What this console is</h4>
                <p>The full ASTRA engine - battlefield generator, receiver
                  physics, five competing policies - compiled to run entirely
                  in your browser. No install, no server, results are seed-exact.</p>
              </div>
              <div className="intro-card">
                <h4>2 · Three bays</h4>
                <p><b>Live Mission</b> races ASTRA against a baseline in real
                  time. <b>Learning Arena</b> trains across episodes in an
                  isolated sandbox. <b>Model Lab</b> runs headless shootouts and
                  verification numbers.</p>
              </div>
              <div className="intro-card">
                <h4>3 · Reading the waterfall</h4>
                <p>
                  <span className="sw" style={{ background: "rgba(111,158,199,.55)" }} />
                  blue = a true transmission (ground truth){" "}
                  <span className="sw" style={{ background: "rgba(255,255,255,.25)" }} />
                  grey column = where the receiver is tuned right now{" "}
                  <span className="sw" style={{ background: "#cfa453" }} />
                  gold = successful intercept.
                </p>
              </div>
              <div className="intro-card">
                <h4>4 · How to use it</h4>
                <p>Pick a one-click demo - start with <b>1 - Flagship race</b> -
                  and watch both receivers race on the same battlefield. Fine-tune
                  seed, opponent, sensitivity and rate below, or train the learner
                  in the Arena.</p>
              </div>
              <div className="intro-card">
                <h4>5 · This runs offline too</h4>
                <p>The same engine ships as a Windows desktop application -
                  diagnostics, PDW/UDP ingest, SQLite logging and the full manual.
                  The <b>Docs</b> tab of the site and the app's Help menu serve the
                  identical manual, generated from one source.</p>
              </div>
            </div>
            <div className="intro-actions">
              <button className="btn ghost"
                      onClick={() => { markSeen(); setShowQuick(false); }}>
                Explore on my own</button>
              <button className="btn primary" onClick={startTour}>
                Take the guided tour</button>
            </div>
          </div>
        </div>
      )}

      {tourIdx >= 0 && TOUR_STEPS[tourIdx] && (<>
        {spot && (<>
          <div className="spot-pad" style={{ left: 0, top: 0, width: "100%",
                height: Math.max(0, spot.top) }} />
          <div className="spot-pad" style={{ left: 0, top: spot.top + spot.height,
                width: "100%", bottom: 0 }} />
          <div className="spot-pad" style={{ left: 0, top: spot.top,
                width: Math.max(0, spot.left), height: spot.height }} />
          <div className="spot-pad" style={{ left: spot.left + spot.width,
                top: spot.top, right: 0, height: spot.height }} />
          <div className="spot-hole" style={{
                left: spot.left - 6, top: spot.top - 6,
                width: spot.width + 12, height: spot.height + 12 }} />
        </>)}
        <div className="spot-tip" ref={tipRef}
             style={tipPos ? { left: tipPos.left, top: tipPos.top }
                           : { left: -9999, top: -9999 }}>
          <div className="spot-head">
            <b>{TOUR_STEPS[tourIdx].title}</b>
            <span>{tourIdx + 1} / {TOUR_STEPS.length}</span>
          </div>
          <p>{TOUR_STEPS[tourIdx].text}</p>
          <div className="spot-actions">
            <button className="btn ghost" onClick={endTour}>Skip</button>
            <span className="spot-hint">← → navigate · Esc exit</span>
            {tourIdx > 0 && (
              <button className="btn ghost" onClick={tourBack}>Back</button>)}
            <button className="btn primary" onClick={tourNext}>
              {tourIdx + 1 < TOUR_STEPS.length ? "Next" : "Finish"}
            </button>
          </div>
        </div>
      </>)}

      <div className="console-wrap">
        <p className="lede">
          The ASTRA engine compiled for the browser - reorganised as a
          three-bay command centre: <b>watch</b> the live race against a
          baseline, <b>train</b> the learner across episodes in an isolated
          arena, then put <b>every policy</b> on the same battlefield.
        </p>

        <div className="ctabs" data-tour="tabs">
          <button className={"ctab" + (tab === "mission" ? " on" : "")}
                  onClick={() => setTab("mission")}>
            <b>Live Mission</b>
            <span>Real-time A/B race - SmartScan vs a conventional sweep</span>
          </button>
          <button className={"ctab" + (tab === "arena" ? " on" : "")}
                  onClick={() => setTab("arena")}>
            <b>Learning Arena</b>
            <span>Train across episodes - isolated sandbox, own learner</span>
          </button>
          <button className={"ctab" + (tab === "lab" ? " on" : "")}
                  onClick={() => setTab("lab")}>
            <b>Model Lab</b>
            <span>Headless shootouts and verification numbers</span>
          </button>
        </div>

        {tab === "mission" && (<>
        <div className="panel" data-tour="demos">
          <h3>Presentation demos - one click, instant mission</h3>
          <div className="body">
            <div className="demo-chips">
              {DEMOS.map((d) => (
                <button key={d.id}
                        className={"demo-chip" + (activeDemo === d.id ? " active" : "")}
                        onClick={() => applyDemo(d)}>
                  <b>{d.title}</b>
                  <span>{d.blurb}</span>
                </button>
              ))}
            </div>
            <p className="tbl-note" style={{ marginBottom: 0 }}>
              Selecting a demo configures and starts a full mission immediately.
              Manual controls below remain available afterwards.
            </p>
          </div>
        </div>

        <div className="panel" data-tour="config">
          <h3>Mission configuration</h3>
          <div className="body controls-row" style={{ marginBottom: 0 }}>
            <button className="tbtn primary" data-tour="start" onClick={start}>Start mission</button>
            <button className="tbtn stop" onClick={stop} disabled={!running}>Pause</button>
            <label>Seed
              <input type="number" value={seed}
                     onChange={(e) => setSeed(Number(e.target.value))} />
            </label>
            <label>Opponent (Receiver B)
              <select value={opp}
                      onChange={(e) => setOpp(e.target.value as OpponentKind)}>
                {OPPONENTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <label>Receivers per side
              <select value={teamSize}
                      onChange={(e) => setTeamSize(Number(e.target.value))}>
                {[1, 2, 3].map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
            </label>
            <label>Sensitivity offset
              <input type="range" min={3} max={12} step={0.5} value={sens}
                     onChange={(e) => setSens(Number(e.target.value))} />
              <span className="readout">{sens.toFixed(1)} dB</span>
            </label>
            <label>Scene
              <select value={scenarioName}
                      onChange={(e) => setScenarioName(e.target.value as typeof scenarioName)}>
                <option value="default">Standard - 24 bands</option>
                <option value="compact">Compact - 12 bands</option>
                <option value="dense">Dense - 32 bands</option>
                <option value="custom">Custom (advanced)</option>
              </select>
            </label>
            <label>Rate
              <input type="range" min={40} max={900} step={20} value={speed}
                     onChange={(e) => setSpeed(Number(e.target.value))} />
              <span className="readout">{speed}/s</span>
            </label>
            <button className="tbtn" onClick={() => setAdvOpen(!advOpen)}>
              {advOpen ? "Hide advanced" : "Advanced"}
            </button>
            <span className="readout">slot {slot}</span>
          </div>
          {advOpen && (
            <div className="body controls-row" style={{ borderTop: "1px solid var(--line)", marginTop: 10, paddingTop: 12 }}>
              <label>SNR mean (dB)
                <input type="number" style={{ width: 70 }} value={snrMean}
                       onChange={(e) => setSnrMean(Number(e.target.value))} />
              </label>
              <label>Period min
                <input type="number" style={{ width: 70 }} value={periodMin}
                       onChange={(e) => setPeriodMin(Number(e.target.value))} />
              </label>
              <label>Period max
                <input type="number" style={{ width: 70 }} value={periodMax}
                       onChange={(e) => setPeriodMax(Number(e.target.value))} />
              </label>
              <label>Clutter emitters
                <input type="number" style={{ width: 70 }} value={nClutter}
                       onChange={(e) => setNClutter(Number(e.target.value))} />
              </label>
              <span className="readout">applied on next Start</span>
            </div>
          )}
        </div>

        <div className="receivers">
          {[["a", "Receiver A - SmartScan (adaptive)",
             "Surveys, estimates rhythms, predicts windows, arrives early."],
            [`b`, `Receiver B - ${OPPONENTS.find(([v]) => v === opp)?.[1]}`,
             "Reference policy on the same battlefield."]].map(([side, title, role]) => (
            <div className="rx-panel" key={side}>
              <h3>{title}</h3>
              <p className="role">{role}</p>
              <canvas ref={(el) => { cvs.current[side as "a" | "b"] = el; }}
                      width={640} height={190}
                      data-tour={side === "a" ? "waterfall" : undefined} />
              <Kv k={side === "a" ? kA : kB}
                  dt={side === "a" ? "kpi" : undefined} />
            </div>
          ))}
        </div>
        <div className="legend">
          <span><i style={{ background: "rgba(111,158,199,.55)" }} />transmission (ground truth)</span>
          <span><i style={{ background: "rgba(255,255,255,.25)" }} />receiver tuned band</span>
          <span><i style={{ background: "#cfa453" }} />intercept</span>
        </div>

        <div className="panel" data-tour="threats" style={{ marginTop: 16 }}>
          <h3>Threat board - library identification (Receiver A)</h3>
          <div className="body tablewrap">
            {idRows.length === 0 && (
              <p className="tbl-note">Streams appear here after three or more
              intercepts, matched against the JC Wise-class library.</p>)}
            {idRows.length > 0 && (
              <table className="res" style={{ minWidth: 520 }}>
                <thead><tr>
                  <th>EID</th><th>Identified</th><th>Class</th><th>Threat</th>
                  <th>Confidence</th><th>Pulses</th><th>Match</th>
                </tr></thead>
                <tbody>
                  {idRows.map((r) => (
                    <tr key={r.eid}>
                      <td className="num">{r.eid}</td>
                      <td>{r.identified}</td>
                      <td>{r.cls}</td>
                      <td><span className={"pill " +
                            (r.threat === "HIGH" ? "fail" : "pass")}>{r.threat}</span></td>
                      <td className="num">{r.confidence}</td>
                      <td className="num">{r.pulses}</td>
                      <td><span className={"pill " + (r.correct ? "pass" : "fail")}>
                        {r.correct ? "MATCH" : "MISS"}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        </>)}

        {tab === "arena" && (<>
        <div className="sandbox">
          <b>Isolated sandbox.</b> Training here runs its own battlefields and
          its own learner instance - nothing in this tab touches the Live
          Mission. The cross-episode memory belongs to this tab alone and can
          be wiped with "Reset learner memory".
        </div>
        <div className="panel" data-tour="arena" style={{ marginTop: 16 }}>
          <h3>Learning arena - cross-episode training</h3>
          <div className="body">
            <p className="tbl-note">
              Runs full missions back-to-back on <b>new battlefields</b> (fresh
              seeds) while the SmartScan learner keeps its consolidated band-value
              memory between episodes - the PS "train on hits and misses" loop,
              visible as warm-start improvement in the early episodes.
            </p>
            <div className="controls-row" style={{ marginBottom: 12 }}>
              <button className="tbtn primary" disabled={arenaBusy}
                      onClick={() => runArena(5)}>
                {arenaBusy ? "Training..." : "Train 5 episodes"}</button>
              <button className="tbtn" disabled={arenaBusy}
                      onClick={() => runArena(10)}>Train 10 episodes</button>
              <button className="tbtn" disabled={arenaBusy}
                      onClick={() => { arenaSched.current = null; arenaKey.current = ""; setArenaRows(null); }}>
                Reset learner memory</button>
            </div>
            {arenaRows && (
              <table className="res" style={{ minWidth: 460 }}>
                <thead><tr><th>Episode</th><th>Battlefield</th>
                  <th>Threat coverage</th><th>Reward / dwell</th><th>Phase locks</th></tr></thead>
                <tbody>
                  {arenaRows.map((r) => (
                    <tr key={r.ep}>
                      <td className="num">{r.ep}</td>
                      <td className="num">seed {r.seed}</td>
                      <td className="num">{(r.cov * 100).toFixed(0)}%</td>
                      <td className="num">{r.reward.toFixed(3)}</td>
                      <td className="num">{r.locks}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {!arenaRows && (
              <p className="tbl-note">No training run yet - the comparison to
              read is episode 1 (cold start) vs later episodes (warm start).</p>)}
            {arenaRows && (
              <div style={{ display: "flex", alignItems: "flex-end", gap: 8, marginTop: 14 }}>
                {arenaRows.map((r) => (
                  <div key={r.ep} style={{ textAlign: "center" }}>
                    <div className="abar-wrap" style={{ display: "flex", alignItems: "flex-end", width: 26, height: 58, margin: 0 }}>
                      <div className="abar" style={{ height: `${Math.max(5, r.cov * 100)}%` }} />
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 4 }}>{r.ep}</div>
                  </div>
                ))}
                <span className="tbl-note" style={{ marginLeft: 12 }}>
                  threat coverage per trained episode - rising bars = warm start
                  paying off on new battlefields</span>
              </div>
            )}
          </div>
        </div>

        </>)}

        {tab === "lab" && (<>
        <div className="panel" data-tour="lab" style={{ marginTop: 16 }}>
          <h3>Model-vs-model - identical battlefield shootout</h3>
          <div className="body">
            <p className="tbl-note">
              Runs every scheduling policy headlessly on the <b>exact same seed
              and scene</b> as configured above - learned policies (SmartScan,
              linear Q-learning) against classical baselines (sweep, random,
              bandit). Same battlefield, same receiver, same reward.
            </p>
            <button className="tbtn primary" disabled={shootBusy} onClick={runShoot}>
              {shootBusy ? "Running..." : "Run shootout"}</button>
            {shootRows && (
              <table className="res" style={{ minWidth: 460, marginTop: 12 }}>
                <thead><tr><th>Policy</th><th>Threat coverage</th>
                  <th>Mean threat first-fix</th><th>Reward / dwell</th></tr></thead>
                <tbody>
                  {shootRows.map((r) => (
                    <tr key={r.name} className={r.name.startsWith("SmartScan") ? "hl" : ""}>
                      <td>{r.name}</td>
                      <td className="num">{(r.cov * 100).toFixed(0)}%</td>
                      <td className="num">{r.ttff != null ? `${r.ttff.toFixed(0)} slots` : "-"}</td>
                      <td className="num">{r.reward.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="panel" style={{ marginTop: 16 }}>
          <h3>Verification numbers - engine probe</h3>
          <div className="body">
            <p className="tbl-note">
              Measured headlessly on the exact browser engine you are running
              (seed 4242, standard scene, reproducible with
              <code className="k"> npm run probe</code> in
              <code className="k"> website/</code>). Prediction accuracy = honest
              per-band occupancy calls, scored against ground truth.
            </p>
            <table className="res" style={{ minWidth: 420 }}>
              <thead><tr><th>Policy</th><th>Prediction accuracy</th>
                <th>Read</th></tr></thead>
              <tbody>
                <tr className="hl"><td>SmartScan (ASTRA)</td>
                  <td className="num">96.9%</td><td>learns occupancy, predicts ON windows</td></tr>
                <tr><td>UCB bandit</td><td className="num">95.5%</td><td>value-driven, no timing model</td></tr>
                <tr><td>Linear Q-learning</td><td className="num">96.4%</td><td>learned value features</td></tr>
                <tr><td>Sequential sweep</td><td className="num">54.1%</td><td>no model - blind raster</td></tr>
                <tr><td>Random scan</td><td className="num">50.2%</td><td>no model - coin flip</td></tr>
              </tbody>
            </table>
          </div>
        </div>
        </>)}

        {tab === "mission" && (<>
        {geoData && (
          <div className="panel" style={{ marginTop: 16 }}>
            <h3>Geolocation — AOA Triangulation</h3>
            <div className="body">
              <div className="kv" style={{ marginBottom: 12 }}>
                <div className="row"><span>Mean error</span><span>{geoData.mean} km</span></div>
                <div className="row"><span>CEP50 (median)</span><span>{geoData.cep50} km</span></div>
                <div className="row"><span>CEP90</span><span>{geoData.cep90} km</span></div>
                <div className="row"><span>Emitters localised</span><span>{geoData.truePos.length}</span></div>
                <div className="row"><span>Receivers</span><span>{geoData.receivers.length}</span></div>
              </div>
              <table className="res" style={{ minWidth: 400 }}>
                <thead><tr><th>#</th><th>True (km)</th><th>Est (km)</th><th>Error (km)</th></tr></thead>
                <tbody>
                  {geoData.truePos.slice(0,12).map((t,i)=>(
                    <tr key={i}>
                      <td className="num">{i+1}</td>
                      <td className="num">({t.x}, {t.y})</td>
                      <td className="num">({geoData.estPos[i]?.x}, {geoData.estPos[i]?.y})</td>
                      <td className="num">{geoData.errors[i]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {geoData.truePos.length>12 && <p className="tbl-note">Showing 12 of {geoData.truePos.length} emitters</p>}
            </div>
          </div>
        )}

        <div className="panel" data-tour="log">
          <h3>Scheduler event log</h3>
          <div className="body">
            <div className="c-log-bar">
              <span className="c-pill pass">{logLines.filter((l) => l.includes("CONFIRMED")).length} locks</span>
              <span className="c-pill fail">{logLines.filter((l) => l.includes("deleted")).length} drops</span>
              <span className="c-pill pending">{logLines.filter((l) => l.includes("rhythm")).length} probes</span>
              <span className="c-pill info">{logLines.length} events</span>
              <button className="c-clear" onClick={() => setLogLines([])}>Clear</button>
            </div>
            <div className="c-log">
              {logLines.length === 0 && (
                <p className="tbl-note">Lock acquisitions, confirmations and deletions
                will appear here while the mission runs.</p>)}
              {(() => {
                const lvl = (l: string): [string, string] => {
                  if (l.includes("CONFIRMED")) { return ["LOCK", "pass"]; }
                  if (l.includes("deleted")) { return ["DROP", "fail"]; }
                  if (l.includes("ENV SHIFT")) { return ["SHIFT", "pending"]; }
                  if (l.includes("rhythm") || l.includes("candidate")) { return ["PROBE", "pending"]; }
                  if (l.includes("mission complete")) { return ["DONE", "pass"]; }
                  if (l.includes("demo loaded")) { return ["INFO", "info"]; }
                  return ["EVENT", "info"];
                };
                return logLines.slice(0, 90).map((l, i) => {
                  const m = l.match(/^slot (\d+):\s*(.*)/);
                  const [tag, cls] = lvl(l);
                  const slot = m ? m[1] : "·";
                  const text = m ? m[2] : l;
                  return (
                    <div className="c-row" key={logLines.length - i}>
                      <span className="c-slot">{slot}</span>
                      <span className={"c-pill " + cls}>{tag}</span>
                      <span className="c-txt">{text}</span>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        </div>
        </>)}

        <p className="tbl-note">
          Browser port of the desktop engine core (parity contract in
          <code className="k"> website/src/engine/</code>). Publication-grade
          statistics remain the domain of the Windows application.
        </p>
      </div>
      <footer className="site"><div className="wrap">
        <p>ASTRA v3.0.0 - SIH 2026 prototype. In-browser tester; not operational equipment.</p>
      </div></footer>
    </>
  );
}
