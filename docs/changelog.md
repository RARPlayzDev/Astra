# Changelog

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
- All 57 automated tests passing

## v0.3.0 (2026-08-20)

### Added
- Emitter identification library (JC Wise-style profiles)
- Multi-receiver cooperative teams with band de-confliction
- Evasive emitter support in simulation environment
- `report_intercept()` for dynamic adversary tracking
