import { useEffect, useState } from "react";
import {
  getIdentification,
  subscribeLive,
  type ArenaEvent,
  type IdentificationRow,
} from "../api";

const POLICY_TITLES: Record<string, string> = {
  "smart-scan": "SmartScan (adaptive)",
  "openloop-sequential": "Sequential sweep",
  "openloop-random": "Random scan",
  "bandit-ucb": "UCB bandit",
  "rl-linear-q": "Q-learning",
  "rl-dqn": "Deep Q-network",
};

function threatColor(t: string): string {
  if (t === "HIGH") return "var(--bad)";
  if (t === "MEDIUM") return "var(--warn)";
  if (t === "LOW") return "var(--good)";
  return "var(--muted)";
}

function threatBadge(t: string): string {
  if (t === "HIGH") return "fail";
  if (t === "MEDIUM") return "warn";
  if (t === "UNKNOWN") return "pending";
  return "pass";
}

export default function Intelligence() {
  const [rows, setRows] = useState<IdentificationRow[]>([]);
  const [nStreams, setNStreams] = useState(0);
  const [lastUpdate, setLastUpdate] = useState(0);
  const [highThreats, setHighThreats] = useState<IdentificationRow[]>([]);
  const [selected, setSelected] = useState<IdentificationRow | null>(null);

  // Subscribe to live episode_done events for real-time identification
  useEffect(() => {
    const off = subscribeLive((e: ArenaEvent) => {
      if (e.type === "episode_done" && e.id_reports) {
        // Take identification from the first sim
        const reportKey = Object.keys(e.id_reports)[0];
        if (reportKey) {
          const newRows = e.id_reports[reportKey] ?? [];
          setRows(newRows);
          setHighThreats(newRows.filter((r) => r.threat === "HIGH"));
          setLastUpdate(e.generation);
        }
      }
    });
    return off;
  }, []);

  // Also poll periodically for identification data
  useEffect(() => {
    const t = setInterval(() => {
      getIdentification()
        .then((r) => {
          if (r.rows.length > 0) {
            setRows(r.rows);
            setNStreams(r.n_streams);
            setHighThreats(r.rows.filter((row) => row.threat === "HIGH"));
          }
        })
        .catch(() => undefined);
    }, 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      <h1 className="page-title">Intelligence</h1>
      <p className="lede">
        Emitter identification: intercepted signal streams are fingerprinted
        (frequency, pulse width, scan rhythm) and matched against the
        JC Wise-style emitter library. HIGH-threat emitters trigger alerts.
      </p>

      {highThreats.length > 0 && (
        <div
          style={{
            border: "1px solid #5c3a33",
            background: "rgba(201,106,91,.10)",
            color: "var(--bad)",
            padding: "10px 16px",
            borderRadius: 4,
            marginBottom: 16,
            fontSize: 13,
          }}
        >
          <b>ALERT:</b> {highThreats.length} HIGH-threat emitter
          {highThreats.length > 1 ? "s" : ""} identified:{" "}
          {highThreats.map((r) => r.identified).join(", ")}
        </div>
      )}

      <div className="stats" style={{ marginBottom: 16 }}>
        <div className="stat">
          <div className="k">Streams detected</div>
          <div className="v">{nStreams}</div>
          <div className="s">unique emitter signals</div>
        </div>
        <div className="stat">
          <div className="k">Identified</div>
          <div className="v">{rows.filter((r) => r.correct).length}/{rows.length}</div>
          <div className="s">matched against library</div>
        </div>
        <div className="stat">
          <div className="k">Unidentified</div>
          <div className="v">{rows.filter((r) => r.threat === "UNKNOWN").length}</div>
          <div className="s">streams pending analysis</div>
        </div>
        <div className="stat">
          <div className="k">HIGH threats</div>
          <div className="v" style={{ color: highThreats.length > 0 ? "var(--bad)" : "var(--good)" }}>
            {highThreats.length}
          </div>
          <div className="s">requires immediate attention</div>
        </div>
        <div className="stat">
          <div className="k">Last update</div>
          <div className="v" style={{ fontSize: 18 }}>
            {lastUpdate > 0 ? `gen ${lastUpdate}` : "waiting"}
          </div>
          <div className="s">episode generation</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel" style={{ gridColumn: "1 / -1" }}>
          <h3>Threat board — identified emitters</h3>
          <div className="body table-wrap" style={{ paddingTop: 6 }}>
            {rows.length === 0 ? (
              <p className="tbl-note">
                No identification data yet. Start a mission and wait for emitter
                streams to accumulate enough pulses for fingerprinting.
              </p>
            ) : (
              <table className="data">
                <thead>
                  <tr>
                    <th>EID</th>
                    <th>Identified</th>
                    <th>Class</th>
                    <th>Threat</th>
                    <th>Confidence</th>
                    <th>Pulses</th>
                    <th>Ground Truth</th>
                    <th>Match</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr
                      key={r.eid}
                      className={selected?.eid === r.eid ? "hl" : ""}
                      onClick={() => setSelected(r)}
                      style={{ cursor: "pointer" }}
                    >
                      <td className="num">{r.eid}</td>
                      <td className="txt">{r.identified}</td>
                      <td className="txt">{r.cls}</td>
                      <td>
                        <span className={`badge ${threatBadge(r.threat)}`}>
                          {r.threat}
                        </span>
                      </td>
                      <td className="num">
                        {r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : "\u2014"}
                      </td>
                      <td className="num">{r.pulses}</td>
                      <td className="txt">{r.ground_truth}</td>
                      <td>
                        <span className={`badge ${r.correct ? "pass" : "fail"}`}>
                          {r.correct ? "MATCH" : "MISS"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {selected && (
        <div className="panel" style={{ marginTop: 16 }}>
          <h3>Emitter detail — EID {selected.eid}</h3>
          <div className="body">
            <div className="grid-3">
              <div>
                <div className="k" style={{ marginBottom: 4, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: "var(--muted)" }}>
                  Identified name
                </div>
                <div style={{ fontSize: 16, fontWeight: 600 }}>{selected.identified}</div>
              </div>
              <div>
                <div className="k" style={{ marginBottom: 4, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: "var(--muted)" }}>
                  Classification
                </div>
                <div style={{ fontSize: 16 }}>{selected.cls ?? "—"}</div>
              </div>
              <div>
                <div className="k" style={{ marginBottom: 4, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: "var(--muted)" }}>
                  Threat level
                </div>
                <div style={{ fontSize: 16, color: threatColor(selected.threat), fontWeight: 700 }}>
                  {selected.threat}
                </div>
              </div>
              <div>
                <div className="k" style={{ marginBottom: 4, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: "var(--muted)" }}>
                  Confidence
                </div>
                <div className="meter" style={{ minWidth: 200 }}>
                  <i style={{ width: `${selected.confidence * 100}%`, background: selected.confidence > 0.8 ? "var(--good)" : "var(--warn)" }} />
                </div>
                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
                  {selected.confidence != null ? `${(selected.confidence * 100).toFixed(1)}%` : "\u2014"}
                </div>
              </div>
              <div>
                <div className="k" style={{ marginBottom: 4, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: "var(--muted)" }}>
                  Pulses intercepted
                </div>
                <div style={{ fontSize: 16 }}>{selected.pulses}</div>
              </div>
              <div>
                <div className="k" style={{ marginBottom: 4, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: "var(--muted)" }}>
                  Ground truth
                </div>
                <div style={{ fontSize: 16 }}>{selected.ground_truth}</div>
              </div>
            </div>
            <p className="tbl-note" style={{ marginTop: 12 }}>
              {selected.correct
                ? "Correctly matched against the emitter library. Classification is verified."
                : "Mismatch — identification did not match the ground truth. May indicate a new or unclassified emitter type."}
            </p>
          </div>
        </div>
      )}

      <div className="panel" style={{ marginTop: 16 }}>
        <h3>How identification works</h3>
        <div className="body">
          <p className="tbl-note" style={{ marginTop: 0 }}>
            Each intercepted signal stream is characterised by a{" "}
            <b>fingerprint</b> (centre frequency, pulse width distribution,
            scan rhythm). The fingerprint is matched against the built-in
            emitter library using nearest-neighbour distance in normalised
            feature space. Confidence is the inverse distance to the closest
            library entry. The threat level comes from the library's threat
            classification (HIGH = surveillance/tracking radar, MEDIUM = search
            radar, LOW = communication/navigation).
          </p>
        </div>
      </div>
    </>
  );
}
