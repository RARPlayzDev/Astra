# Changelog

## Unreleased — alignment remediation rev. 3 (2026-09-09)

### Added
- **Explicit RF front-end bandwidth model** (`ewsmart/config.py`): `total_bw_mhz` / `inst_bw_mhz` / `bandwidth_ratio` (24:1 on the canonical protocol) with a `bandwidth_ratio_meets_ps_order` flag and a kT+B thermal-noise floor — the PS "order-of-magnitude lower instantaneous bandwidth" is now a measured, tested property.
- **Receiver sensitivity FoM block** (`ESReceiver.sensitivity_fom()`): Pd = 0.5 threshold, Pd-vs-SNR logistic curve, false-alarm rate and bandwidth context, rendered as a `Receiver sensitivity (PS FoM)` section of `results/benchmark.md`.
- **Per-emitter-class interception FoMs** (`metrics.compute_metrics`): `ir_*` and censored `ttff_*` for stationary / agile / periodic / spatial / evasive classes, with an `Interception FoMs by emitter class` table in `results/benchmark.md`; absent classes are NaN, never phantom zeros.
- **Intercept-time-error evidence quantification**: `intercept_time_error_n` (sample count) and `intercept_time_error_coverage` (fraction of characterised periodic emitters) reported per scheduler.
- **Learned-value ablation in the canonical artifact**: `smart_scan_value_mode_ablation` (learned / heuristic / flat on the same protocol; learned reward 0.49 vs heuristic 0.22 vs flat 0.25) — the ML contribution is quantified, not asserted.
- **Site exporter** now bakes `receiver_fom` and the ablation into the website data.

### Changed
- Sentence-by-sentence PS coverage re-scored: **98/100**; evidence-weighted alignment **88/100** (`docs/ps-alignment-sentence-report.md` rev. 3, `docs/smart-scan-alignment-report.md` rev. 3).
- Test count is **253** everywhere (badge, README, EVALUATION, docs, reproducibility).

## Unreleased — alignment remediation rev. 2 (2026-09-08)

### Added
- **Agile-hop prediction integrated into SmartScan**: strictly causal per-stream (SNR/AOA fingerprint) transition model with urgency-gated bonus in `select()`; `next_hop_topk()` accessor; ablatable via `hop_weight` / `hop_min_obs`. Leakage, ablation and integration regression tests added.
- **Policy-level agile-hop follow-rate metric** (`metrics.agile_hop_follow_metrics`), reported for *every* scheduler in the canonical benchmark.
- **Canonical protocol locked**: `experiments.CANONICAL_PROTOCOL` = 24 bands × 3000 slots × 50 episodes, `base_seed=9000`; `benchmark_report()` defaults to it and stamps provenance (git commit, timestamp, Python/platform) into every artifact; `run_suite(full)` uses it too.
- **Latency evidence artifact**: `results/performance.json` with p50/p95/p99/max per heavy scheduler + platform provenance (`tests/test_performance.py`).
- **Dataset replay benchmark**: `ewsmart.dataset.dataset_replay_benchmark()` → `results/dataset_benchmark.json` (deterministic offline Turing-schema PDW calibration + provenance).
- **Site exporter**: `tools/export_site_data.py` bakes `results/` artifacts, figures and the manual into `website/public/` (now a real tool, previously a phantom README reference).
- **Sentence-by-sentence alignment ledger**: `docs/ps-alignment-sentence-report.md` scores all 25 PS clauses (98/100 coverage) and reconciles the 88/100 evidence-weighted result.
- **Multi-receiver de-confliction evidence**: `coverage_integrity` (fraction of slots with all-distinct dwells) in `multireceiver_experiment`.

### Changed
- Canonical episode count is **50** (24 bands × 3000 slots, `base_seed=9000`); all docs reconciled.
- Test count is **250** everywhere (badge, README, EVALUATION, problem.md, docs, reproducibility).
- `docs/smart-scan-alignment-report.md` re-scored from implemented evidence: **83/100** (rev. 2), with links to tests and artifacts.

### Fixed
- `server/livesim.py` live-arena prediction accuracy now excludes the warm-up calibration transient and divides by scored slots (regression test added).
- Removed scratch file `tests/_patch_livesim.py`; README repo map no longer lists phantom tools (`pdw_generator.py`, `make_brand_assets.py`).
- Stale headline numbers in `README.md`, `EVALUATION.md`, `problem.md`, `ASTRA.md`, `PROJECT_EXPLAINED.md`, `docs/*` now match the regenerated canonical artifacts.

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
