export type MeanCI = { mean: number | null; ci95: number | null };
export type McRow = Record<string, MeanCI>;
export type KppSpec = { min?: number; max?: number; why?: string };

export type MissionScore = {
  mes: number;
  components: Record<string, number>;
  kpps: Record<string, { pass: boolean; value: number }>;
  mission_capable: boolean;
};

export type Summary = {
  monte_carlo_means: Record<string, Record<string, number | null>>;
  monte_carlo: Record<string, McRow>;
  mission_effectiveness: {
    scores: Record<string, MissionScore>;
    ranking: string[];
    kpps: Record<string, KppSpec>;
  } | null;
  significance_gated_mes: SigRow[];
  identification: { accuracy?: number; n_identified?: number; n_streams?: number };
};

export type SigRow = {
  comparator: string;
  mean_diff: number;
  p_value: number;
  significant: boolean;
};

export type Meta = {
  app: string;
  long: string;
  version: string;
  manual_available: boolean;
  frontend_built: boolean;
};

export type Diagnostic = { name: string; ok: boolean; detail: string };
export type Diagnostics = {
  checks: Diagnostic[];
  passed: number;
  total: number;
  all_ok: boolean;
};

export type Scenario = { name: string; config: Record<string, unknown> };
export type ModelInfo = {
  file: string;
  ok: boolean;
  class?: string;
  n_bands?: number;
  format?: string;
  error?: string;
};
export type SourceInfo = {
  id: string;
  type: string;
  params: Record<string, string | number>;
  pdw_total: number;
  rate_per_s: number;
  running: boolean;
  error: string | null;
};

const j = async (r: Response) => {
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
};

export const getMeta = (): Promise<Meta> => fetch("/api/meta").then(j);
export const getSummary = (): Promise<Summary> => fetch("/api/summary").then(j);
export const getScenarios = (): Promise<{ scenarios: Scenario[] }> =>
  fetch("/api/scenarios").then(j);
export const getFigures = (): Promise<{ figures: string[] }> =>
  fetch("/api/figures").then(j);
export const getModels = (): Promise<{ models: ModelInfo[] }> =>
  fetch("/api/models").then(j);
export const getDiagnostics = (): Promise<Diagnostics> =>
  fetch("/api/diagnostics").then(j);

/* ---------------------------- PS coverage audit ------------------------- */
export type PSCheck = {
  check: string; ps_phrase: string; ok: boolean;
  evidence: Record<string, unknown>;
};
export type PSCoverage = {
  passed: number; total: number; coverage_pct: number; checks: PSCheck[];
  note?: string;
};
export const getPsCoverage = (seed?: number): Promise<PSCoverage> =>
  fetch(`/api/ps-coverage${seed != null ? `?seed=${seed}` : ""}`).then(j);
export const figureUrl = (name: string) => `/api/figures/${name}`;
export const manualUrl = "/manual";

/* ------------------------------ live arena ------------------------------ */
export type FrameStep = { band: number; hit: boolean; false_alarm: boolean; truth: boolean; reward: number };
export type SimFrame = {
  name: string; t0: number; t1: number;
  occupancy: number[][]; actions: number[]; hits: number[];
  steps: FrameStep[]; kpis: LiveKpis;
  dnd_bands?: Record<number, number>;
  evasion_events?: { eid: number; slot: number; kind: string; detail: string }[];
};
export type LiveKpis = {
  slots: number; avg_reward: number; threat_coverage: number;
  threats_found: number; n_threats: number; hit_rate: number; false_alarms: number;
  intercept_ratio?: number; mean_ttff?: number | null; threat_mean_ttff?: number | null;
  pred_accuracy?: number; pred_active_accuracy?: number; pred_active_count?: number;
  locks?: number; team?: number; loaded_weights?: boolean;
  dnd_bands?: Record<number, number>; evasion_count?: number;
};
export type IdRow = {
  eid: number; identified: string; cls?: string; threat: string;
  confidence: number; pulses: number; ground_truth: string; correct: boolean;
};
export type ArenaEvent =
  | { type: "frame"; slot: number; sims: Record<string, SimFrame> }
  | { type: "episode_done"; generation: number;
      finals: Record<string, LiveKpis>;
      id_reports?: Record<string, IdRow[]> };

export function subscribeLive(onEvent: (e: ArenaEvent) => void): () => void {
  const es = new EventSource("/api/live/stream");
  es.onmessage = (m) => {
    try { onEvent(JSON.parse(m.data)); } catch { /* ignore malformed */ }
  };
  es.onerror = () => { /* browser retries automatically */ };
  return () => es.close();
}

export type MissionConfig = {
  speed?: number; scenario?: string; n_bands?: number; T?: number;
  schedA?: string; schedB?: string;
  teamSize?: number; sensOffset?: number; useSaved?: boolean;
  nFhss?: number; nTdma?: number; cfarPfa?: number; dwellTimeUs?: number;
  lpiFraction?: number; matchedFilter?: boolean; aoaModel?: string;
};
export const startMission = (opts: MissionConfig = {}) => {
  const q = new URLSearchParams();
  if (opts.speed) q.set("speed", String(opts.speed));
  if (opts.scenario) q.set("scenario", opts.scenario);
  if (opts.n_bands) q.set("n_bands", String(opts.n_bands));
  if (opts.T) q.set("T", String(opts.T));
  if (opts.schedA) q.set("sched_a", opts.schedA);
  if (opts.schedB) q.set("sched_b", opts.schedB);
  if (opts.teamSize && opts.teamSize > 1) q.set("team_size", String(opts.teamSize));
  if (opts.sensOffset != null) q.set("sens_offset", String(opts.sensOffset));
  if (opts.useSaved) q.set("use_saved", "true");
  if (opts.nFhss != null) q.set("n_fhss", String(opts.nFhss));
  if (opts.nTdma != null) q.set("n_tdma", String(opts.nTdma));
  if (opts.cfarPfa != null) q.set("cfar_pfa", String(opts.cfarPfa));
  if (opts.dwellTimeUs != null) q.set("dwell_time_us", String(opts.dwellTimeUs));
  if (opts.lpiFraction != null) q.set("lpi_fraction", String(opts.lpiFraction));
  if (opts.matchedFilter != null)
    q.set("matched_filter", opts.matchedFilter ? "true" : "false");
  if (opts.aoaModel) q.set("aoa_model", opts.aoaModel);
  return fetch(`/api/live/start?${q}`, { method: "POST" }).then(j);
};
export const stopMission = () =>
  fetch("/api/live/stop", { method: "POST" }).then(j);
export const liveStatus = (): Promise<{ running: boolean; slot: number; T: number }> =>
  fetch("/api/live/status").then(j);

/* ------------------------------- sources -------------------------------- */
export const listSources = (): Promise<{ sources: SourceInfo[] }> =>
  fetch("/api/sources").then(j);
export const addSource = (body: Record<string, unknown>): Promise<{ id: string }> =>
  fetch("/api/sources", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async (r) => {
    if (!r.ok) throw new Error((await r.json()).detail ?? `${r.status}`);
    return r.json();
  });
export const removeSource = (id: string) =>
  fetch(`/api/sources/${id}`, { method: "DELETE" }).then(j);

/* ------------------------------- shutdown ------------------------------- */
export const shutdownApp = () =>
  fetch("/api/shutdown", { method: "POST" }).then(j);

export const trainModel = (body: { policy: string; n_bands?: number;
                                   T?: number; episodes?: number }) =>
  fetch("/api/models/train", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async (r) => {
    if (!r.ok) throw new Error((await r.json()).detail ?? `${r.status}`);
    return r.json() as Promise<{ saved: string; reward_curve: number[] }>;
  });

export const calibrateDataset = (body: { max_rows?: number; seed?: number;
                                         n_bands?: number; T?: number } = {}) =>
  fetch("/api/dataset/calibrate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async (r) => {
    if (!r.ok) throw new Error((await r.json()).detail ?? `${r.status}`);
    return r.json() as Promise<{ summary: Record<string, unknown>;
                                 suggested: { n_bands: number; T: number } }>;
  });

export async function exportResults() {
  const data = await (await fetch("/api/summary")).json();
  const blob = new Blob([JSON.stringify(data, null, 2)],
                        { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "astra_results_export.json";
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ------------------------------- geolocation --------------------------- */
export type GeoPoint = { x: number; y: number };
export type GeoResult = {
  receivers: GeoPoint[];
  true_positions: GeoPoint[];
  estimated_positions: (GeoPoint & { residual_km: number })[];
  errors: number[];
  cep: { mean: number; median: number; cep50: number; cep90: number };
  scene_km: number;
};
export const getGeolocation = (kRx: number = 3, seed: number = 42): Promise<GeoResult> =>
  fetch(`/api/geolocation?k_rx=${kRx}&seed=${seed}`).then(j);

/* ------------------------------- identification ------------------------ */
export type IdentificationRow = {
  eid: number; identified: string; cls?: string; threat: string;
  confidence: number; pulses: number; ground_truth: string; correct: boolean;
};
export const getIdentification = (): Promise<{ rows: IdentificationRow[]; n_streams: number }> =>
  fetch("/api/identification").then(j);


