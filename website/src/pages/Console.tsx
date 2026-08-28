import { useEffect, useRef, useState } from "react";
import { Logo } from "../shared";
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
  predAcc: number; locks: number; team: number;
}
const emptyKpi = (): Kpi => ({ cov: 0, found: 0, threats: 0, allRatio: 0,
  reward: 0, hitRate: 0, fa: 0, ttff: null, threatTtff: null,
  predAcc: 0, locks: 0, team: 1 });

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
  pred: { a: [number, number]; b: [number, number] }; // [correct,total]
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
      pred: { a: [0, 0], b: [0, 0] },
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

        const runSide = (side: "a" | "b", team: TeamScheduler) => {
          const bands = team.selectJoint(t);
          const results = bands.map((b, i) => s.rx[side][i].dwell(b, t));
          let rTotal = 0, anyHit = false, anyFa = false, truth = false;
          const beforeThreats = s.seenThreats[side].size;
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
          const newly = s.seenAll[side].size -
            (beforeThreats - s.seenThreats[side].size) -
            [...s.seenAll[side]].filter((e) => !s.seenThreats[side].has(e)).length;
          void newly;
          if (anyHit && !anyFa) s.ttffAll[side].push(t);
          const pred = team.first.predict(t, bands[0]);
          s.pred[side][0] += Number(pred === truth);
          s.pred[side][1] += 1;
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

  const Kv = ({ k }: { k: Kpi }) => (
    <div className="kv">
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
      <div className="row"><span>Prediction accuracy</span>
        <span>{(k.predAcc * 100).toFixed(0)}%</span></div>
      {k.team > 1 && <div className="row"><span>Cooperative team</span>
        <span>{k.team} receivers</span></div>}
      <div className="row"><span>Phase locks held</span><span>{k.locks}</span></div>
    </div>
  );

  const [tourStep, setTourStep] = useState(0);
  const [showQuick, setShowQuick] = useState(false);

  const TOUR_STEPS = [
    { title: "Presentation Demos", text: "Click one of these presets to instantly configure and start a scenario. Try the 'Flagship race' to see ASTRA vs a standard sweeper." },
    { title: "Mission Configuration", text: "You can tweak the exact scenario variables manually: seed, sensitivity, opponent type, and even multi-receiver swarm sizes." },
    { title: "The Waterfall Display", text: "The blue blocks are true transmissions. The light grey column is where the receiver is currently listening. A gold flash means a successful intercept!" },
    { title: "Performance Metrics", text: "Live KPIs track the mission. Watch ASTRA's Threat Coverage stay high while its Reward per Dwell outpaces the baseline." },
    { title: "Emitter Identification", text: "As streams of intercepts come in, they are matched against a library of known threats. This is the final step: Intercept -> Classify -> Identify." }
  ];

  return (
    <>
      <div className="doc-topbar">
        <div className="wrap" style={{ display: "flex", alignItems: "center",
             gap: 20, padding: "12px 28px" }}>
          <a className="brand" href="/"><Logo size={30} /><b>ASTRA</b></a>
          <span style={{ color: "var(--muted)", fontSize: 14 }}>
            Prototype console - full-feature in-browser tester</span>
          <div className="doc-actions" style={{ marginLeft: "auto" }}>
            <button className="btn ghost" style={{ padding: "8px 16px", fontSize: 13.5 }} onClick={() => setShowQuick(true)}>Quick Guide</button>
            <button className="btn primary" style={{ padding: "8px 16px", fontSize: 13.5 }} onClick={() => setTourStep(1)}>Help / Tour</button>
            <a className="btn ghost" style={{ padding: "8px 16px", fontSize: 13.5 }}
               href="/">Back to site</a>
          </div>
        </div>
      </div>

      {showQuick && (
        <div className="modal-overlay" onClick={() => setShowQuick(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>ASTRA Quick Guide</h2>
            <p><b>1. Goal:</b> Find hostile emitters that transmit rarely (like 2% of the time).</p>
            <p><b>2. SmartScan:</b> ASTRA's engine learns when these emitters transmit, predicts their next window, and arrives early.</p>
            <p><b>3. Console:</b> Choose a demo (e.g. Flagship race) to see ASTRA (Receiver A) against a conventional sweep (Receiver B).</p>
            <p><b>4. Reading the UI:</b> Blue = ground truth, Grey = receiver listening, Gold = successful intercept.</p>
            <button className="btn primary" onClick={() => setShowQuick(false)}>Got it</button>
          </div>
        </div>
      )}

      {tourStep > 0 && (
        <div className="modal-overlay">
          <div className="modal-content tour-box">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, color: "var(--bright)" }}>{TOUR_STEPS[tourStep - 1].title}</h3>
              <span style={{ fontSize: 13, color: "var(--muted)" }}>Step {tourStep} of {TOUR_STEPS.length}</span>
            </div>
            <p style={{ margin: "0 0 20px 0", fontSize: 15.5, color: "var(--soft)" }}>
              {TOUR_STEPS[tourStep - 1].text}
            </p>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <button className="btn ghost" onClick={() => setTourStep(0)}>Close</button>
              <button className="btn primary" onClick={() => {
                if (tourStep < TOUR_STEPS.length) setTourStep(tourStep + 1);
                else setTourStep(0);
              }}>
                {tourStep < TOUR_STEPS.length ? "Next" : "Finish Tour"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="console-wrap">
        <p className="lede">
          The ASTRA engine compiled for the browser: every scheduling behaviour,
          cooperative teams, receiver sensitivity control and library-based
          emitter identification - running against identical battlefields.
        </p>

        <div className="panel">
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

        <div className="panel">
          <h3>Mission configuration</h3>
          <div className="body controls-row" style={{ marginBottom: 0 }}>
            <button className="tbtn primary" onClick={start}>Start mission</button>
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
                      width={640} height={190} />
              <Kv k={side === "a" ? kA : kB} />
            </div>
          ))}
        </div>
        <div className="legend">
          <span><i style={{ background: "rgba(111,158,199,.55)" }} />transmission (ground truth)</span>
          <span><i style={{ background: "rgba(255,255,255,.25)" }} />receiver tuned band</span>
          <span><i style={{ background: "#cfa453" }} />intercept</span>
        </div>

        <div className="panel" style={{ marginTop: 16 }}>
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

        <div className="panel">
          <h3>Scheduler event log</h3>
          <div className="body">
            {logLines.length === 0 && (
              <p className="tbl-note">Lock acquisitions, confirmations and deletions
              will appear here while the mission runs.</p>)}
            {logLines.map((l, i) => (
              <div key={i} style={{ fontFamily: "Consolas, monospace", fontSize: 13,
                                    color: "var(--soft)", padding: "2px 0" }}>{l}</div>
            ))}
          </div>
        </div>

        <p className="tbl-note">
          Browser port of the desktop engine core (parity contract in
          <code className="k"> website/src/engine/</code>). Publication-grade
          statistics remain the domain of the Windows application.
        </p>
      </div>
      <footer className="site"><div className="wrap">
        <p>ASTRA v2.0.0 - SIH 2026 prototype. In-browser tester; not operational equipment.</p>
      </div></footer>
    </>
  );
}
