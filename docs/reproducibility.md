# Reproducibility & Evidence Baseline

This document is the **single source of truth** for how ASTRA's evidence is
regenerated. Every headline number in the README, the docs site and the
presentation website must trace back to a command listed here, run in the
environment recorded here, against a named artifact.

> **Rule (Phase 0 evidence freeze):** no headline metric may be hand-edited.
> Each reported number must carry a **seed**, a **scenario**, an **episode
> count**, and a **source artifact**. Numbers without provenance are treated as
> unverified.

## Verified environment

| Component | Version / value |
|---|---|
| Python | 3.14.2 |
| numpy | 2.5.3 |
| scipy | 1.18.1 |
| matplotlib | 3.11.1 |
| pytest | 9.1.1 |
| fastapi | 0.141.1 |
| OS | Windows 11 (10.0.26200) |
| Machine | AMD64 |

Regenerate this table from the working machine:

```powershell
python -c "import platform,sys;print(sys.version.split()[0], platform.platform(), platform.machine())"
python -c "import numpy,scipy,matplotlib,pytest;print(numpy.__version__,scipy.__version__,matplotlib.__version__,pytest.__version__)"
```

## Canonical test command

```powershell
python -m pytest -q
```

**Verified result: `306 passed`** (collected via `python -m pytest --collect-only -q`
&rightarrow; `306 tests collected`). This is the canonical test count used everywhere
in the documentation. It was `253` before the fidelity and problem-statement
regression bundles (`tests/test_fidelity_upgrades.py`, `tests/test_ps_gaps.py`,
`tests/test_target99_gaps.py`) were added.

Per-suite commands (mirror of `HOW_TO_TEST.md`, runnable standalone):

```powershell
python -X utf8 tests\test_smartscan.py       # scheduler + environment physics
python -X utf8 tests\test_modules.py         # config, dataset, DQN, persistence, viz
python -X utf8 tests\test_live.py            # streaming core incl. UDP round-trip
python -X utf8 tests\test_id_geo_stats.py    # identification, geolocation, statistics
python -X utf8 tests\test_mission.py         # KPP gate + MES scoring engine
python -X utf8 tests\test_software.py        # app layer: sources, diagnostics, manual
python -X utf8 tests\test_api.py             # API endpoints + live arena
python -X utf8 tests\test_result_schema.py   # canonical result-artifact schema (Phase 0)
```

## Canonical baseline evaluation command

```powershell
python -m ewsmart.experiments --suite full
```

This runs the complete evaluation programme and writes `results/suite_results.json`
plus the figures under `figures/`.

### Monte Carlo protocol (headline table)

Defined in `ewsmart/experiments.py :: monte_carlo_eval`:

| Parameter | Value |
|---|---|
| Held-out episodes per scheduler | **50** (`CANONICAL_PROTOCOL['episodes']`; calling `monte_carlo_eval` on its own defaults to 200) |
| Bands | 24 |
| Slots (horizon `T`) | 3000 |
| Schedulers | 7 (sequential, random, priority, UCB, Linear-Q, DQN, SmartScan) |
| Battlefield seed | `base_seed = 9000`, episode `ep` uses `seed = 9000 + ep` |
| Rollout seed | `seed = 9000 + 31 * ep` |
| Confidence interval | 95% (`1.96 * SEM`) |

**50 held-out episodes** (24 bands × 3000 slots, base_seed 9000) is the canonical episode count used everywhere in the
documentation.

### Recorded figures of merit

`ewsmart/metrics.py :: compute_metrics` produces, per episode:

- `threat_intercept_ratio` — Pd / threat coverage (KPP-gated in MES)
- `intercept_ratio` — all-emitter interception ratio
- `intercept_rate` — hits per slot
- `false_alarm_rate` — false alarms per slot (KPP-gated)
- `avg_reward`, `total_reward`
- `pct_correct_predictions` — prediction accuracy (KPP-gated)
- `mean_time_to_first_intercept`, `threat_mean_ttff`
- `avg_intercept_time_error` — intercept-time prediction error
- `n_periodic_locked`

## Result artifact contract

The machine-readable schema for `results/suite_results.json` lives at
[`results/result_schema.json`](../results/result_schema.json) and is enforced
by [`tests/test_result_schema.py`](../tests/test_result_schema.py). Any change
to the shape of the results file must update the schema in the same change-set,
so the human-readable tables and the machine artifact never diverge.

The schema is **tracked**: `.gitignore` ignores `results/*` and re-includes
`results/result_schema.json` (a re-include cannot work under a whole-directory
rule). `results/suite_results.json` is a generated artifact and is absent from a
fresh clone; `test_suite_results_matches_schema` skips in that case, but the two
self-consistency tests always need the schema file.
