import { useEffect, useRef, useState } from "react";
import {
  addSource, calibrateDataset, getModels, getScenarios, listSources,
  removeSource, trainModel, type ModelInfo, type Scenario, type SourceInfo,
} from "../api";

type Props = {
  onScenarioLoad: (name: string) => void;
  onFlyCustom: (nBands: number, tHorizon: number) => void;
};

export default function DataSources({ onScenarioLoad, onFlyCustom }: Props) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [srcType, setSrcType] = useState<"udp" | "file" | "sim">("udp");
  const [udpPort, setUdpPort] = useState(5555);
  const [filePath, setFilePath] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [trainPolicy, setTrainPolicy] = useState("rl-linear-q");
  const [trainEpisodes, setTrainEpisodes] = useState(5);
  const [training, setTraining] = useState(false);
  const [trainMsg, setTrainMsg] = useState<string | null>(null);
  const [trainOk, setTrainOk] = useState(false);
  const [calibrating, setCalibrating] = useState(false);
  const [calibSummary, setCalibSummary] = useState<Record<string, unknown> | null>(null);
  const [calibMsg, setCalibMsg] = useState<string | null>(null);
  const [calibOk, setCalibOk] = useState(false);

  const doTrain = async () => {
    setTraining(true); setTrainMsg(null);
    try {
      const r = await trainModel({ policy: trainPolicy,
                                   n_bands: 12, T: 600, episodes: trainEpisodes });
      setTrainOk(true);
      setTrainMsg(`Saved ${r.saved}. Reward curve: ${r.reward_curve.join(" -> ")}`);
      getModels().then((m) => setModels(m.models)).catch(() => undefined);
    } catch (e) {
      setTrainOk(false);
      setTrainMsg(String(e instanceof Error ? e.message : e));
    } finally { setTraining(false); }
  };

  const doCalibrate = async () => {
    setCalibrating(true); setCalibMsg(null);
    try {
      const r = await calibrateDataset({ max_rows: 1500, seed: 1 });
      setCalibSummary(r.summary); setCalibOk(true);
      setCalibMsg(`Calibrated battlefield ready (${r.suggested.n_bands} bands, ` +
                  `${r.suggested.T} slots). Loading paired mission...`);
      setTimeout(() => onScenarioLoadRef.current?.(r.suggested.n_bands,
                                                   r.suggested.T), 600);
    } catch (e) {
      setCalibOk(false);
      setCalibMsg(String(e instanceof Error ? e.message : e));
    } finally { setCalibrating(false); }
  };

  const onScenarioLoadRef = useRef(onFlyCustom);
  useEffect(() => { onScenarioLoadRef.current = onFlyCustom; }, [onFlyCustom]);

  const refreshSources = () => listSources().then((r) => setSources(r.sources)).catch(() => undefined);

  useEffect(() => {
    getScenarios().then((r) => setScenarios(r.scenarios)).catch(() => undefined);
    getModels().then((r) => setModels(r.models)).catch(() => undefined);
    refreshSources();
    const t = setInterval(refreshSources, 1500);
    return () => clearInterval(t);
  }, []);

  const doAdd = async () => {
    setErr(null);
    try {
      if (srcType === "udp") await addSource({ type: "udp", port: udpPort });
      else if (srcType === "file") await addSource({ type: "file", path: filePath });
      else await addSource({ type: "sim", n_bands: 24 });
      refreshSources();
    } catch (e) { setErr(String(e instanceof Error ? e.message : e)); }
  };

  return (
    <>
      <h1 className="page-title">Data &amp; Sources</h1>
      <p className="lede">
        Sensor feeds, battlefield scenarios and trained scheduling models. Any
        radar or SDR processor that can emit pulse-descriptor words over UDP (or
        write them to a log file) integrates through this page - see the user
        guide, section "Radar and sensor integration".
      </p>

      <div className="grid-2">
      <div className="grid-2">
        <div className="panel">
          <h3>Model studio - train &amp; save</h3>
          <div className="body">
            <p className="tbl-note" style={{ marginTop: 0 }}>
              Quick-train a persistable policy on simulated episodes and store it
              as an artifact. Saved weights can be loaded into a mission from the
              Operations configuration (Load saved weights).
            </p>
            <div className="form-row">
              <select value={trainPolicy}
                      onChange={(e) => setTrainPolicy(e.target.value)}>
                <option value="smart-scan">SmartScan (state)</option>
                <option value="bandit-ucb">UCB bandit</option>
                <option value="rl-linear-q">Q-learning (linear)</option>
              </select>
              <input type="number" min={1} max={30} value={trainEpisodes}
                     title="episodes"
                     onChange={(e) => setTrainEpisodes(Number(e.target.value))} />
              <span className="readout">episodes</span>
              <button className="tbtn primary" disabled={training}
                      onClick={() => void doTrain()}>
                {training ? "Training..." : "Train & save"}
              </button>
            </div>
            {trainMsg && (
              <div className={trainOk ? "ok-text" : "err-text"}>{trainMsg}</div>
            )}
          </div>
        </div>

        <div className="panel">
          <h3>Dataset calibration</h3>
          <div className="body">
            <p className="tbl-note" style={{ marginTop: 0 }}>
              Calibrate a battlefield from the referenced PDW datasets
              (JC Wise-class library; HuggingFace when online, deterministic
              offline fallback otherwise).
            </p>
            <div className="form-row">
              <button className="tbtn primary" disabled={calibrating}
                      onClick={() => void doCalibrate()}>
                {calibrating ? "Calibrating..." : "Calibrate from dataset"}
              </button>
              {calibSummary && (
                <span className="readout">
                  clusters: {String(calibSummary.n_freq_clusters ?? "?")} &middot;
                  PDWs: {String(calibSummary.n_pdw ?? "?")}
                </span>
              )}
            </div>
            {calibMsg && (
              <div className={calibOk ? "ok-text" : "err-text"}>{calibMsg}</div>
            )}
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <h3>Sensor sources</h3>
          <div className="body">
            <div className="form-row">
              <select value={srcType} onChange={(e) => setSrcType(e.target.value as typeof srcType)}>
                <option value="udp">UDP feed (PDW datagrams)</option>
                <option value="file">Log file tail (JSONL/CSV)</option>
                <option value="sim">Internal simulated scene</option>
              </select>
              {srcType === "udp" && (
                <input type="number" value={udpPort} min={1024} max={65535}
                       onChange={(e) => setUdpPort(Number(e.target.value))} title="UDP port" />
              )}
              {srcType === "file" && (
                <input type="text" value={filePath} placeholder="C:\\feeds\\sweep.jsonl"
                       style={{ width: 260 }}
                       onChange={(e) => setFilePath(e.target.value)} />
              )}
              <button className="tbtn primary" onClick={() => void doAdd()}>Attach</button>
            </div>
            {err && <div className="err-text">{err}</div>}
            {sources.length === 0 && (
              <p className="tbl-note">No sources attached. A source counts
              incoming PDWs and verifies connectivity - attach one before wiring
              real hardware.</p>
            )}
            {sources.map((s) => (
              <div className="list-item" key={s.id}>
                <div>
                  <b>{s.type.toUpperCase()}</b>{" "}
                  <span className="meta">
                    {Object.entries(s.params).map(([k, v]) => `${k}=${v}`).join("  ")}
                  </span>
                  {s.error && <div className="err-text">{s.error}</div>}
                  {!s.running && !s.error && <div className="err-text">starting...</div>}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <span className="meta">{s.pdw_total} PDWs &middot; {s.rate_per_s}/s</span>
                  <button className="iconbtn" onClick={() => {
                    void removeSource(s.id).then(refreshSources).catch(() => undefined);
                  }}>detach</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <h3>Scenario library</h3>
          <div className="body">
            {scenarios.length === 0 && <p className="tbl-note">No scenario files found in /scenarios.</p>}
            {scenarios.map((sc) => {
              const cfg = sc.config as Record<string, number>;
              return (
                <div className="list-item" key={sc.name}>
                  <div>
                    <b>{sc.name}</b>
                    <div className="meta">
                      bands {cfg.n_bands ?? "?"} &middot; horizon {cfg.T ?? "?"} slots
                    </div>
                  </div>
                  <button className="tbtn" onClick={() => onScenarioLoad(sc.name)}>Fly paired</button>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="panel">
        <h3>Trained scheduling models</h3>
        <div className="body table-wrap" style={{ paddingTop: 4 }}>
          <table className="data">
            <thead><tr><th>Artifact</th><th>Policy class</th><th>Bands</th><th>Integrity</th></tr></thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.file}>
                  <td className="num">{m.file}</td>
                  <td>{m.class ?? "-"}</td>
                  <td className="num">{m.n_bands ?? "-"}</td>
                  <td>{m.ok
                    ? <span className="badge pass">VALID</span>
                    : <span className="badge fail">CORRUPT</span>}</td>
                </tr>
              ))}
              {models.length === 0 && (
                <tr><td colSpan={4} className="txt">No model artifacts in /models.</td></tr>
              )}
            </tbody>
          </table>
          <p className="tbl-note">Artifacts are pickle-free NumPy archives validated
          on load; a corrupt file is reported here instead of being executed.</p>
        </div>
      </div>
    </>
  );
}
