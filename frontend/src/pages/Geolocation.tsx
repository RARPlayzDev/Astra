import { useEffect, useRef, useState } from "react";
import { getGeolocation, type GeoResult } from "../api";

function GeoMap({ data }: { data: GeoResult }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const km = data.scene_km;
  const pad = 40;
  const size = 500;
  const scale = (size - 2 * pad) / (2 * km);
  const cx = size / 2;
  const cy = size / 2;
  const toSvg = (p: { x: number; y: number }) => ({
    x: cx + p.x * scale,
    y: cy - p.y * scale,
  });

  return (
    <svg
      ref={svgRef}
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      style={{ background: "#10161d", borderRadius: 4, border: "1px solid var(--line)" }}
    >
      {/* Grid */}
      {[-1, 0, 1].map((gx) =>
        [-1, 0, 1].map((gy) => (
          <line
            key={`${gx}-${gy}`}
            x1={cx + gx * km * scale}
            y1={cy + gy * km * scale}
            x2={cx + gx * km * scale}
            y2={cy}
            stroke="var(--line-soft)"
            strokeWidth={0.5}
          />
        ))
      )}
      {[-1, 0, 1].map((gx) =>
        [-1, 0, 1].map((gy) => (
          <line
            key={`h${gx}-${gy}`}
            x1={cx}
            y1={cy + gy * km * scale}
            x2={cx + gx * km * scale}
            y2={cy + gy * km * scale}
            stroke="var(--line-soft)"
            strokeWidth={0.5}
          />
        ))
      )}

      {/* Range circles */}
      {[0.25, 0.5, 0.75, 1.0].map((f) => (
        <circle
          key={f}
          cx={cx}
          cy={cy}
          r={f * km * scale}
          fill="none"
          stroke="var(--line)"
          strokeWidth={0.5}
          strokeDasharray={f < 1 ? "4,4" : undefined}
        />
      ))}

      {/* Bearing lines from receivers to estimated positions */}
      {data.estimated_positions.map((est, i) => {
        const trueP = data.true_positions[i];
        if (!trueP) return null;
        return (
          <line
            key={`bearing-${i}`}
            x1={cx}
            y1={cy}
            x2={cx + trueP.x * scale}
            y2={cy - trueP.y * scale}
            stroke="rgba(111,158,199,0.15)"
            strokeWidth={1}
          />
        );
      })}

      {/* Receiver positions */}
      {data.receivers.map((r, i) => {
        const p = toSvg(r);
        return (
          <g key={`rx-${i}`}>
            <polygon
              points={`${p.x},${p.y - 8} ${p.x - 6},${p.y + 5} ${p.x + 6},${p.y + 5}`}
              fill="#6f9ec7"
              stroke="#8bbad4"
              strokeWidth={1}
            />
            <text x={p.x} y={p.y + 18} textAnchor="middle" fill="var(--muted)" fontSize={10}>
              RX{i + 1}
            </text>
          </g>
        );
      })}

      {/* Estimated positions with CEP rings */}
      {data.estimated_positions.map((est, i) => {
        const p = toSvg(est);
        return (
          <g key={`est-${i}`}>
            <circle cx={p.x} cy={p.y} r={12} fill="none" stroke="rgba(45,212,191,0.25)" strokeWidth={1} />
            <circle cx={p.x} cy={p.y} r={4} fill="#2dd4bf" stroke="#5eead4" strokeWidth={1} />
          </g>
        );
      })}

      {/* True positions */}
      {data.true_positions.map((t, i) => {
        const p = toSvg(t);
        return (
          <g key={`true-${i}`}>
            <polygon
              points={`${p.x},${p.y - 8} ${p.x - 5},${p.y + 4} ${p.x + 5},${p.y + 4}`}
              fill="#c96a5b"
              stroke="#e08575"
              strokeWidth={1}
              transform={`rotate(180, ${p.x}, ${p.y})`}
            />
          </g>
        );
      })}

      {/* Scale bar */}
      <line x1={pad} y1={size - pad + 10} x2={pad + 25 * scale} y2={size - pad + 10} stroke="var(--muted)" strokeWidth={1} />
      <text x={pad + 12.5 * scale} y={size - pad + 22} textAnchor="middle" fill="var(--muted)" fontSize={9}>
        25 km
      </text>
    </svg>
  );
}

export default function Geolocation() {
  const [data, setData] = useState<GeoResult | null>(null);
  const [kRx, setKRx] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = () => {
    setLoading(true);
    setError(null);
    getGeolocation(kRx)
      .then(setData)
      .catch((e) => setError(String(e instanceof Error ? e.message : e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetch();
  }, []);

  return (
    <>
      <h1 className="page-title">Geolocation</h1>
      <p className="lede">
        Multi-receiver AOA triangulation: K cooperating receivers measure
        bearings to each emitter (2° noise); least-squares triangulation
        estimates positions. Red stars = true emitters, cyan circles =
        estimates, blue triangles = receivers.
      </p>

      <div className="panel">
        <h3>Configuration</h3>
        <div className="body controls-row" style={{ marginBottom: 0 }}>
          <button className="tbtn primary" onClick={fetch} disabled={loading}>
            {loading ? "Computing..." : "Recalculate"}
          </button>
          <label>
            Receivers
            <select value={kRx} onChange={(e) => setKRx(Number(e.target.value))}>
              {[2, 3, 4].map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </label>
          <span className="readout">
            {data ? `${data.true_positions.length} emitters in scene` : ""}
          </span>
        </div>
      </div>

      {error && (
        <div className="err-text" style={{ marginBottom: 16 }}>
          {error} — start a mission first, then come back to geolocation.
        </div>
      )}

      {data && (
        <>
          <div className="grid-2">
            <div className="panel">
              <h3>Triangulation map</h3>
              <div className="body" style={{ textAlign: "center" }}>
                <GeoMap data={data} />
                <div className="legend" style={{ justifyContent: "center", marginTop: 12 }}>
                  <span><i style={{ background: "#c96a5b", transform: "rotate(180deg)", display: "inline-block" }} /> true emitter</span>
                  <span><i style={{ background: "#2dd4bf" }} /> estimate</span>
                  <span><i style={{ background: "#6f9ec7", clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }} /> receiver</span>
                </div>
              </div>
            </div>

            <div className="panel">
              <h3>Statistics</h3>
              <div className="body">
                <div className="stats" style={{ gridTemplateColumns: "1fr" }}>
                  <div className="stat">
                    <div className="k">Mean error</div>
                    <div className="v">{data.cep.mean.toFixed(1)} km</div>
                    <div className="s">average localization error</div>
                  </div>
                  <div className="stat">
                    <div className="k">CEP50 (median)</div>
                    <div className="v">{data.cep.cep50.toFixed(1)} km</div>
                    <div className="s">50th percentile error</div>
                  </div>
                  <div className="stat">
                    <div className="k">CEP90</div>
                    <div className="v">{data.cep.cep90.toFixed(1)} km</div>
                    <div className="s">90th percentile error</div>
                  </div>
                  <div className="stat">
                    <div className="k">Emitters localised</div>
                    <div className="v">{data.true_positions.length}</div>
                    <div className="s">from {kRx} cooperating receivers</div>
                  </div>
                </div>

                <table className="data" style={{ marginTop: 16 }}>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>True (km)</th>
                      <th>Est (km)</th>
                      <th>Error (km)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.true_positions.map((t, i) => (
                      <tr key={i}>
                        <td className="num">{i + 1}</td>
                        <td className="num">
                          ({t.x.toFixed(1)}, {t.y.toFixed(1)})
                        </td>
                        <td className="num">
                          ({data.estimated_positions[i]?.x.toFixed(1)},{" "}
                          {data.estimated_positions[i]?.y.toFixed(1)})
                        </td>
                        <td className="num">{data.errors[i]?.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="panel" style={{ marginTop: 16 }}>
            <h3>How geolocation works</h3>
            <div className="body">
              <p className="tbl-note" style={{ marginTop: 0 }}>
                Each cooperating receiver measures the angle-of-arrival (AOA)
                of intercepted pulses. With 2+ receivers, bearing lines
                intersect at the emitter's true position. Least-squares
                triangulation minimizes the residual error across all bearing
                pairs. The Circular Error Probable (CEP) quantifies accuracy:
                CEP50 is the radius containing 50% of estimates, CEP90
                contains 90%. Adding receivers dramatically reduces CEP — the
                improvement from 2→3 receivers is typically 3-5×.
              </p>
            </div>
          </div>
        </>
      )}
    </>
  );
}
