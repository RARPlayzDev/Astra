# Changelog

## Unreleased — evidence freeze (Phase 0)

### Added
- **Reproducibility manifest** (`docs/reproducibility.md`): single source of truth for the environment, canonical test/eval commands, Monte Carlo seeds, and the artifact-provenance rule.
- **Canonical result schema** (`results/result_schema.json`) + a dependency-free schema-validity test (`tests/test_result_schema.py`) that validates `results/suite_results.json`.

### Fixed
- **Reconciled contradictory counts** across `README.md`, `EVALUATION.md`, `problem.md`, `PROJECT_EXPLAINED.md` and this changelog: the canonical figures are **225 automated tests** and **200 held-out Monte Carlo episodes**.

### Technical
- 225 automated tests passing (`python -m pytest -q`); was 222 before the schema-validity test was added.

## v2.0.0 (2026-08-28)

### Added
- **SQLite metrics database**: `ewsmart-run --trials` now streams every trial into `ewsmart.db` (`runs`/`trials`/`aggregates` tables) with mean, SEM and 95% confidence intervals per scheduler/metric
- **`/api/summary` serves the live database**: Monte-Carlo dashboard data now comes from the SQLite aggregates (latest run), falling back to `results/suite_results.json` for the sections the DB does not hold (mission effectiveness, significance, learning, ROC, ...)

### Fixed
- **Desktop Help menu (F1)**: Qt app navigated to `/docs/manual.md` (404); now opens the manual at `/manual`
- **Confidence intervals across Monte Carlo runs** centralised in `metrics.confidence_interval`

### Technical
- Runtime input validation with branded `EwsmartError` exceptions throughout the scheduler/environment APIs
- Hard per-decision latency budget enforced (`< 1 ms`) by the performance test suite
- 221 automated tests passing at 92% coverage

## v1.0.0 (2026-08-27)

### Added
- **Counter-ESM evasion**: Evasive emitters that shift behaviour after 3+ consecutive interceptions
- **Swarm intelligence (DND tokens)**: Distributed cooperative deconfliction for multi-receiver teams
- **Meta-learning (MetaScheduler)**: State persistence across episodes for warm-start adaptation
- **Intelligence perspective**: Emitter identification board with threat classification
- **Geolocation perspective**: Multi-receiver AOA triangulation with CEP analysis
- **Native Qt desktop app**: PySide6-based window replacing pywebview (experimental)
- **DQN scheduler in live arena**: Deep Q-network now available as a paired mission policy

### Improved
- **SmartScan MES**: 0.558 → 0.628 (+12.5%) through exploitation/exploration tuning
- **Prediction accuracy**: 58.1% → 62.3% (+4.2pp)
- **Threat coverage**: 95.0% → 96.7% (+1.7pp)
- **Documentation**: Complete VitePress multi-page documentation site

### Technical
- `exploit_ramp`: 0.55 → 0.60 (steeper exploitation ramp)
- `explore_eps`: 0.08 → 0.048 (halved random exploration)
- Recency weight: 0.22 → 0.16 (less aggressive cold-band revisiting)
- All 222 automated tests passing

## v0.3.0 (2026-08-20)

### Added
- Emitter identification library (JC Wise-style profiles)
- Multi-receiver cooperative teams with band de-confliction
- Evasive emitter support in simulation environment
- `report_intercept()` for dynamic adversary tracking
