# Target 99 Hit Plan

**Current assessed alignment:** 83/100 (rev. 2, 2026-09-08 — see `docs/smart-scan-alignment-report.md`)  
**Target:** 99/100 alignment with the Smart Scan Strategy problem statement  
**Purpose:** execution plan for the developer and other AI agents

## Execution status addendum (updated by agent run)

The four P0 code gaps are now closed with regression tests (`tests/test_target99_gaps.py`, suite: 250 passed), and the alignment-gaps remediation (rev. 2) landed on top:

- **Phase 1 (attribution)** — `DwellResult.detected_eids`; reward/first-intercept credit only detected emitters (`runner.detected_eids`, `runner.step_reward`); ambiguous co-channel dwells tracked in `Trace.ambiguous` and reported as `ambiguous_hit_rate`; `metrics.attribution_conservation` verifies credits ≤ supported detections. Co-channel regression tests added.
- **Phase 2 (agile prediction)** — `ewsmart/prediction.py` (causal transition-count, persistence, uniform predictors + oracle) with top-1/top-k and missed-opportunity metrics; `ScenarioConfig.agile_mode` adds structured Markov hopping. Leakage test proves future truth cannot change predictions; random hopping is scored at chance. **Rev. 2:** the same causal transition model is now integrated into `SmartScanScheduler.select()` (urgency-gated `hop_weight` bonus, ablatable), and policy-level hop-follow rates are reported for every scheduler in `results/benchmark.json` (the standalone `results/hop_prediction.json` is superseded by the `hop_prediction` section of `benchmark.json`).
- **Phase 3 (learned control)** — `SmartScanScheduler(value_mode=...)` with `learned` / `heuristic` / `flat` ablations wired through `select()`; ablation experiment extended; test proves removing the learned value changes decisions materially.
- **Phase 4 (canonical benchmark)** — `experiments.benchmark_report()` generates `results/benchmark.json` + `results/benchmark.md` from the locked protocol (`CANONICAL_PROTOCOL`: 24 bands × 3000 slots × 50 episodes, base_seed 9000) for all 7 schedulers with 95% CIs, attribution-conservation checks, full FoM table, agile-hop follow rates, next-hop prediction benchmark, and a provenance stamp; no hand-entered numbers. Test counts reconciled to **250** everywhere.
- **Rev. 2 additions** — `results/performance.json` (p50/p95/p99/max latency + platform), `results/dataset_benchmark.json` (Turing-schema replay with provenance), `tools/export_site_data.py` (single command bakes artifacts into the website), multi-receiver `coverage_integrity` deconfliction evidence, and the re-scored alignment report (83/100).


## Important meaning of 99/100

The target is a **defensible alignment score**, not a claim that the system is operationally perfect. A 99 score requires every major sentence in the problem statement to be implemented, measured, tested, and documented with reproducible evidence. It must not be achieved by inflating metrics or relabeling a simulator as field-proven.

The score should be recalculated only after all acceptance gates below pass.

## Current gap summary

| Gap | Current condition | Target condition | Priority |
|---|---|---|---:|
| Emitter attribution | One detection can credit multiple co-channel emitters | Credit only the emitter(s) supported by detection evidence | P0 |
| Agile prediction | Random/configured hopping is searched but not predicted | Learn and evaluate next-hop/occupancy prediction | P0 |
| SmartScan learning | Main policy is a programmed hybrid | Learned value/policy must materially control decisions, while retaining interpretable safeguards | P0 |
| Metrics | Metrics exist but are not unified and some are coverage proxies | One canonical Pd/Pfa/sensitivity/rate/reward/prediction/time-error report | P0 |
| Evaluation | Evidence is mainly synthetic and counts are inconsistent | Reproducible benchmark protocol with seeds, confidence intervals, baselines, and artifact manifest | P0 |
| RF realism | Simplified bands, SNR, geometry, and spatial model | Add documented interference, noise, waveform, geometry, and calibration layers | P1 |
| Multi-receiver proof | Architecture exists, limited mission evidence | Demonstrate coordinated mission-level benefit and collision/deconfliction metrics | P1 |
| Hardware/data proof | Dataset and SDR transport scaffolding | Validate recorded data and complete an SDR-in-the-loop path | P1 |
| Performance | Software tests pass, but no deployment-level timing evidence | Measure deterministic latency and throughput on declared hardware | P1 |
| Documentation | Counts and evaluation descriptions disagree | One source of truth linked to generated results | P0 |

## Execution rules for all agents

1. Read the relevant existing tests before editing implementation.
2. Preserve public APIs unless a compatibility change is necessary and documented.
3. Add a focused regression test with every behavioral change.
4. Use deterministic seeds in tests and report confidence intervals in experiments.
5. Do not silently change metric definitions to improve the score.
6. Keep synthetic, recorded-data, and hardware results visibly separated.
7. Run the narrow test after each work package, then run the complete suite before merging.
8. Do not commit changes; the project owner will review and commit them.

## Phase 0: Baseline and evidence freeze

**Goal:** create a trustworthy before/after comparison.

### Tasks

- Record the current test command, Python version, dependency versions, OS, CPU, and random seeds.
- Generate a baseline result artifact for all schedulers: open-loop/baseline, UCB, Linear Q, DQN, and SmartScan.
- Record Pd, Pfa, sensitivity, intercept rate, mean and percentile TTFF, reward, prediction accuracy, intercept-time error, coverage, and decision latency.
- Reconcile the test and episode counts in `README.md`, `EVALUATION.md`, and result files.
- Create one machine-readable result schema and one human-readable summary table.

### Likely files

`README.md`, `EVALUATION.md`, `ewsmart/experiments.py`, `ewsmart/metrics.py`, `results/`

### Acceptance criteria

- A clean baseline can be regenerated from one documented command.
- Every headline number has a seed, scenario, episode count, and source artifact.
- No documentation contains contradictory test counts or evaluation protocols.

### Agent prompt

> Audit the repository's current evaluation commands and result files. Create a reproducible baseline experiment manifest and canonical result schema without changing algorithm behavior. Reconcile conflicting test/episode counts in README.md and EVALUATION.md. Add tests for schema validity and report the exact command used.

## Phase 1: Correct emitter-level attribution

**Goal:** make all interception and reward metrics scientifically valid for co-channel emitters.

### Tasks

- Trace `receiver.py`, `runner.py`, `metrics.py`, and detection tuple/PDW structures.
- Define a detection attribution contract: a hit must identify the detected emitter or explicitly be marked ambiguous.
- Separate `band_hit`, `emitter_detected`, `ambiguous_cochannel_hit`, and `false_alarm`.
- Credit `first_intercept`, reward, threat ratio, and intercept-time metrics only according to the contract.
- Add deterministic tests with zero, one, and multiple emitters on the same band.
- Add a conservation check: emitter-level credits cannot exceed supported detections.

### Acceptance criteria

- A co-channel test proves that detecting one of two emitters does not automatically intercept both.
- Ambiguous detections are visible in metrics rather than silently counted as true emitter hits.
- Baseline results are regenerated after the fix.

### Agent prompt

> Fix emitter-level interception attribution in `ewsmart/receiver.py`, `ewsmart/runner.py`, and `ewsmart/metrics.py`. First inspect existing detection/PDW data structures and tests. Implement explicit emitter, ambiguous, band-hit, and false-alarm outcomes. Add regression tests for co-channel emitters and ensure reward and first-intercept metrics use the corrected attribution. Do not change unrelated scheduler behavior.

## Phase 2: Add explicit frequency-agile prediction

**Goal:** satisfy the strongest missing requirement: predicting agile emitter opportunities.

### Tasks

- Extend the environment with multiple documented agility modes:
  - random hopping,
  - Markov/transition hopping,
  - periodic hop sequence,
  - burst or dwell-time changes,
  - optional adversarial/evasive hopping.
- Add a predictor interface that consumes only observations available to the receiver.
- Implement a simple transition-count predictor as a transparent baseline.
- Implement a learned predictor if justified by the data volume; compare against persistence, uniform random, and oracle upper bound.
- Expose top-1 accuracy, top-k accuracy, calibration, missed-opportunity rate, and agile-emitter intercept-time error.
- Prevent truth leakage: the predictor must not read hidden emitter state, future band sequences, or simulator-only labels at decision time.

### Likely files

`ewsmart/environment.py`, `ewsmart/schedulers.py`, `ewsmart/metrics.py`, `ewsmart/experiments.py`, new focused tests

### Acceptance criteria

- Predictor performance beats the uniform-random baseline on structured agility.
- Random agility is correctly reported as unpredictable rather than falsely scored as predictable.
- A leakage test fails if future truth is passed to the predictor.
- Agile results are reported separately from periodic and stationary results.

### Agent prompt

> Implement an observation-only agile-hop prediction module. Add random, Markov, periodic-sequence, and evasive hop modes to the simulator with deterministic seeds. Provide a baseline transition predictor and metrics for top-1/top-k accuracy, calibration, missed opportunities, and agile TTFF. Add tests proving no future truth leakage and proving random hopping is not incorrectly represented as predictable.

## Phase 3: Make SmartScan measurably learned

**Goal:** strengthen the claim that the proposed scheduler is ML-based without losing interpretability.

### Tasks

- Define which decisions are learned and which are hard safety constraints.
- Add a learned value or policy component that ranks candidate bands using observation history, emitter class evidence, uncertainty, predicted occupancy, and opportunity cost.
- Ensure hits and misses update the learning component, including episode finalization and persistence behavior.
- Add ablations:
  - heuristic-only SmartScan,
  - learned-only policy,
  - hybrid policy,
  - no agile predictor,
  - no periodic lock.
- Compare against open-loop sweep, random, UCB, Linear Q, and DQN under identical seeds and scenario sets.
- Document exploration, exploitation, cold-start, reset, checkpoint, and replay behavior.

### Acceptance criteria

- Removing the learned component measurably changes behavior and performance.
- Training on hits/misses improves held-out episodes over the cold-start policy.
- `end_episode()` and state persistence have explicit tests.
- The paper/demo describes SmartScan accurately as hybrid learned control if it remains hybrid.

### Agent prompt

> Audit `SmartScanScheduler` and make its learned component explicit and testable. Preserve interpretable reconnaissance and safety constraints, but route candidate-band ranking through learned value estimates using only receiver observations. Implement episode finalization, reset, persistence, and checkpoint tests. Add ablation experiments proving the learned component affects decisions and held-out results.

## Phase 4: Build the canonical metric and benchmark suite

**Goal:** make every requested figure of merit precise, comparable, and reproducible.

### Tasks

- Define formal numerator/denominator rules for Pd, Pfa, sensitivity, intercept rate, average reward/cost, prediction accuracy, and intercept-time error.
- Distinguish event-level, emitter-level, band-level, and episode-level metrics.
- Report mean, median, p90/p95, standard deviation, and bootstrap confidence intervals where appropriate.
- Add per-emitter-class and per-SNR breakdowns.
- Add calibration and ROC/PR curves for detection and prediction.
- Publish a single benchmark table generated by code rather than manually edited numbers.

### Acceptance criteria

- Metric unit tests cover empty episodes, no emitters, all-false alarms, all-hits, co-channel ambiguity, and censored TTFF.
- All schedulers use the same scenarios, seeds, episode counts, and receiver configuration.
- The generated report includes every figure of merit named in the problem statement.

### Agent prompt

> Refactor the evaluation path into one canonical benchmark protocol. Define and test exact formulas for Pd, Pfa, sensitivity, intercept rate, reward/cost, prediction accuracy, and intercept-time error. Add confidence intervals and class/SNR breakdowns. Generate Markdown and JSON outputs from the same run, with no hand-entered headline values.

## Phase 5: Improve RF and spatial realism without breaking the simulator

**Goal:** close the gap between a useful abstract simulator and an evidence-backed receiver model.

### Tasks

- Make instantaneous bandwidth, center frequency, dwell time, sweep rate, and frequency resolution explicit configuration values.
- Add documented noise-floor, sensitivity, SNR, bandwidth, and detection-threshold relationships.
- Add co-channel interference and adjacent-channel leakage scenarios.
- Improve spatial scanning with antenna beam pattern, scan geometry, receiver bearing, optional elevation, and configurable propagation loss.
- Add waveform/pulse metadata sufficient for detection and identification experiments while keeping the simulator dependency-light.
- Add calibration tests showing that changing sensitivity and SNR changes Pd/Pfa in the expected direction.

### Acceptance criteria

- Configuration units are explicit and validated.
- Pd/Pfa behavior is monotonic where the model requires it.
- Spatial and frequency effects are independently testable.
- Existing tests remain green and old scenario files remain loadable.

### Agent prompt

> Extend the RF simulator conservatively. Add explicit receiver bandwidth, dwell, sweep, sensitivity, noise, interference, and spatial beam parameters while preserving existing scenario compatibility. Add calibration tests for monotonic Pd/Pfa, adjacent-channel behavior, and spatial illumination. Update docs with units and assumptions.

## Phase 6: Prove multi-receiver coordination

**Goal:** turn the existing architecture into measurable mission-level evidence.

### Tasks

- Define receiver roles, shared knowledge, communication delay, ownership, and deconfliction rules.
- Measure aggregate interception ratio, duplicate dwell rate, coverage, fairness, latency, and collision rate.
- Compare independent receivers against coordinated receivers under the same receiver budget.
- Test failures: receiver dropout, stale locks, delayed messages, conflicting claims, and overloaded bands.

### Acceptance criteria

- Coordination improves at least one declared mission metric without hiding degradation in another.
- Failure behavior is deterministic and documented.
- Multi-receiver results are included in the benchmark artifact.

### Agent prompt

> Extend `ewsmart/multireceiver.py` into a measured coordination experiment. Define shared-state and message-delay assumptions, add aggregate and fairness metrics, compare independent versus coordinated receivers, and add tests for stale locks, dropouts, and collisions.

## Phase 7: Validate recorded data and SDR-in-the-loop behavior

**Goal:** provide evidence beyond synthetic truth labels.

### Tasks

- Select one recorded dataset with documented provenance and licensing.
- Map recorded observations into the project schema without exposing future labels to the scheduler.
- Calibrate noise floor, sensitivity, timestamps, frequency bins, and missing data handling.
- Run the scheduler against replayed observations and compare synthetic versus recorded-data behavior.
- Exercise `tools/sdr_bridge.py` with a local deterministic producer/consumer integration test.
- Clearly label what is replay, simulated, and live hardware.

### Acceptance criteria

- Dataset provenance and preprocessing are documented.
- Replay results are reproducible from a checked-in manifest, excluding large external data when necessary.
- SDR bridge has an automated protocol test and a manual hardware test record if hardware is available.

### Agent prompt

> Audit `ewsmart/dataset.py`, `docs/integration/datasets.md`, and `tools/sdr_bridge.py`. Add a leakage-safe recorded-data replay path, calibration metadata, schema validation, and deterministic bridge integration tests. Document exactly which results are synthetic, replayed, or hardware-derived.

## Phase 8: Performance and deployment qualification

**Goal:** establish honest real-time behavior on declared hardware.

### Tasks

- Benchmark scheduler decision latency separately from environment and logging overhead.
- Measure p50, p95, p99, maximum latency, allocations, and throughput for each scheduler.
- Profile DQN and SmartScan before optimizing.
- Add a no-logging/no-plot production path.
- Test cold start, warm start, long episode, many bands, many emitters, and multiple receivers.
- Declare hardware, Python version, BLAS/backend, and process settings.

### Acceptance criteria

- The 1 ms target is either met at the declared percentile or explicitly revised with engineering justification.
- No benchmark mixes setup time with per-decision time.
- Performance results are stored with environment metadata.

### Agent prompt

> Profile and benchmark DQN and SmartScan using the existing performance tests as a starting point. Separate decision computation from simulator/logging overhead, report p50/p95/p99/max latency, and optimize only after profiling. Add regression thresholds and document the exact hardware/software environment.

## Phase 9: Documentation, score recalculation, and release gate

**Goal:** convert implementation work into a reviewable submission.

### Tasks

- Update the alignment report with links to tests, benchmark artifacts, and limitations.
- Replace unsupported claims such as “100% identification” with scope-qualified claims.
- Add an architecture diagram, data-flow diagram, and metric definitions.
- Add a reproducibility section with one command and expected artifact names.
- Recalculate the weighted score using the same rubric and record evidence for every category.
- Run the complete test suite and save the result.

### Final release gate

Do not claim 99/100 unless all of these are true:

- [ ] Attribution tests pass for co-channel emitters.
- [ ] Agile prediction has a leakage test and structured/random benchmark.
- [ ] SmartScan ablations prove a learned component materially affects decisions.
- [ ] All named figures of merit are generated from one canonical protocol.
- [ ] Results include confidence intervals, seeds, scenarios, and artifact provenance.
- [ ] RF, spatial, and receiver configuration units are documented.
- [ ] Multi-receiver coordination has mission-level evidence.
- [ ] Recorded-data replay is complete, or the limitation is explicitly scored rather than hidden.
- [ ] SDR bridge has an integration test and hardware status is documented.
- [ ] Performance is measured on declared hardware with percentile latency.
- [ ] Full test suite passes.
- [ ] The score is recalculated from evidence, not from planned work.

## Recommended agent assignment order

1. **Agent A:** Phase 0 baseline and documentation reconciliation.
2. **Agent B:** Phase 1 emitter attribution and regression tests.
3. **Agent C:** Phase 2 agile prediction.
4. **Agent D:** Phase 3 SmartScan learned-control and ablations.
5. **Agent E:** Phase 4 canonical metrics and benchmark output.
6. **Agent F:** Phase 5 RF/spatial realism.
7. **Agent G:** Phase 6 multi-receiver validation.
8. **Agent H:** Phase 7 recorded-data and SDR replay.
9. **Agent I:** Phase 8 profiling and deployment qualification.
10. **Project owner:** Phase 9 integration, full tests, score recalculation, and final review.

Agents should work in separate branches or isolated worktrees when editing overlapping files. Merge Phase 1 before trusting any regenerated headline metrics; otherwise later agents may optimize against invalid measurements.

## Expected score trajectory

| Milestone | Expected defensible score | Condition |
|---|---:|---|
| Current baseline | 74 | Existing implementation and current evidence |
| After attribution, metric, and documentation correction | 82-86 | Core numbers become trustworthy and reproducible |
| After agile prediction and learned SmartScan ablations | 89-93 | Major direct requirement gaps are closed |
| After realism, multi-receiver, and performance evidence | 94-97 | Operational evidence is materially stronger |
| After recorded-data/SDR validation and final audit | 98-99 | Every major claim has implementation and evidence |

These are planning estimates, not guaranteed scores. The final score must be recomputed from the evidence rubric.

## Final operating principle

The fastest route to 99 is not adding more algorithm names. It is making every claim traceable:

**requirement -> implementation -> test -> benchmark -> artifact -> documented limitation**.

That chain is the standard every agent contribution must satisfy.