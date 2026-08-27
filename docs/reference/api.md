# API Reference

All endpoints are local-first (`127.0.0.1`). Interactive OpenAPI UI at `/api-docs`.

## Health & metadata

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness probe |
| GET | `/api/meta` | App name, version, availability flags |
| GET | `/api/diagnostics` | Self-test checklist (8 checks) |

## Benchmark results

| Method | Path | Description |
|---|---|---|
| GET | `/api/summary` | Full benchmark payload (Monte Carlo, significance, MES, etc.) |
| GET | `/api/figures` | List of available figure filenames |
| GET | `/api/figures/{name}.png` | Fetch a specific figure image |

## Live arena

| Method | Path | Description |
|---|---|---|
| POST | `/api/live/start` | Start paired mission |
| POST | `/api/live/stop` | Stop mission |
| GET | `/api/live/status` | Running flag, slot, per-scheduler KPIs |
| GET | `/api/live/stream` | Server-Sent Events frame stream |

### Query parameters for `/api/live/start`

| Parameter | Default | Type | Description |
|---|---|---|---|
| `n_bands` | 24 | int | Frequency bands |
| `T` | 2400 | int | Episode length (slots) |
| `speed` | 400 | int | Slots per second |
| `scenario` | - | string | Load from `/scenarios/{name}.json` |
| `sched_a` | smart-scan | string | Receiver A policy |
| `sched_b` | openloop-sequential | string | Receiver B policy |
| `team_size` | 1 | int | Cooperative team size (1-3) |
| `sens_offset` | 6.0 | float | Detection threshold offset (dB) |
| `use_saved` | false | bool | Load trained weights from `/models/` |

### Available scheduler names

| Name | Class |
|---|---|
| `smart-scan` | SmartScan (proposed) |
| `openloop-sequential` | Sequential sweep |
| `openloop-random` | Random scan |
| `bandit-ucb` | UCB bandit |
| `rl-linear-q` | Linear Q-learning |
| `rl-dqn` | Deep Q-network |

## Intelligence & geolocation

| Method | Path | Description |
|---|---|---|
| GET | `/api/identification` | Emitter identification results |
| GET | `/api/geolocation` | AOA triangulation results |

### `/api/geolocation` query parameters

| Parameter | Default | Description |
|---|---|---|
| `k_rx` | 3 | Number of cooperating receivers (2-4) |
| `seed` | 42 | Random seed for bearing noise |

## Sensor sources

| Method | Path | Description |
|---|---|---|
| GET | `/api/sources` | List attached sources |
| POST | `/api/sources` | Attach a new source |
| DELETE | `/api/sources/{sid}` | Detach a source |

### Source types

| Type | Parameters |
|---|---|
| `udp` | `port` (int), `bind` (string, default "127.0.0.1") |
| `file` | `path` (string) |
| `sim` | `n_bands` (int), `T` (int), `seed` (int) |

## Models

| Method | Path | Description |
|---|---|---|
| GET | `/api/models` | List saved model artifacts |
| POST | `/api/models/train` | Train and save a policy |

### Training parameters

```json
{
  "policy": "smart-scan | bandit-ucb | rl-linear-q",
  "n_bands": 12,
  "T": 600,
  "episodes": 5
}
```

## Scenarios & datasets

| Method | Path | Description |
|---|---|---|
| GET | `/api/scenarios` | List scenario files |
| POST | `/api/dataset/calibrate` | Calibrate battlefield from PDW dataset |

## Shutdown

| Method | Path | Description |
|---|---|---|
| POST | `/api/shutdown` | Graceful shutdown (used by File → Exit) |
| GET | `/manual` | Rendered user guide (HTML) |
