# Evaluation Methodology

Following defence test & evaluation practice.

## The KPP Gate

Every scheduler is first judged against **hard Key Performance Parameters**.
Failing any gate means the system is **not mission-capable**, regardless of
how well it scores on other metrics.

| KPP | Threshold | Rationale |
|---|---|---|
| Threat coverage (Pd) | ≥ 0.90 | PS primary objective: high interception rate |
| Prediction accuracy | ≥ 0.50 | PS FoM: predictions better than chance |
| False alarm rate | ≤ 5×10⁻⁴ /slot | Operator loading limit |

::: warning
The gate is **all-or-nothing**. A scheduler with 99% prediction accuracy
but 89% threat coverage fails. A scheduler with 100% coverage but 49%
prediction accuracy fails.
:::

## Mission Effectiveness Score (MES)

Among KPP-passing systems, the MES ranks schedulers by a composite of
six normalised figures of merit:

1. **Pd (threat coverage)** — fraction of hostile emitters caught at least once
2. **1 - Pfa (relative false-alarm performance)** — fewer false alarms is better
3. **Average intercept rate** — fraction of dwells that produce detections
4. **Reward (relative)** — normalised to the field leader
5. **Prediction accuracy** — fraction of correct ON/OFF predictions
6. **Intercept-time error (relative)** — how accurately the scheduler predicts when emitters will transmit

MES = mean of all six normalised components.

## Headline result

**SmartScan is the only mission-capable scheduler in the field.**

| Scheduler | Coverage | Prediction | Verdict | MES |
|---|---|---|---|---|
| SmartScan | 95.0% ✅ | 62.3% ✅ | **CAPABLE** | **0.628** |
| UCB bandit | 54.0% ❌ | 98.8% ✅ | NOT CAPABLE | 0.680 |
| Random scan | 97.7% ✅ | 45.8% ❌ | NOT CAPABLE | 0.437 |
| Q-learning | 89.6% ❌ | 19.0% ❌ | NOT CAPABLE | 0.230 |

::: info
UCB bandit has a higher raw MES but fails the KPP gate because it
misses 46% of threats. The gate ensures operational viability before
ranking.
:::

## Statistical significance

Paired per-episode permutation tests on the gated MES score,
with Holm-Bonferroni correction at α=0.05:

- SmartScan vs UCB bandit: **p < 1e-4** ✓
- SmartScan vs Random scan: **p < 1e-4** ✓
- SmartScan vs Q-learning: **p < 1e-4** ✓

50 held-out episodes with 95% confidence intervals.

## Regenerating results

```bash
python -m ewsmart.experiments --suite full
```

This runs the complete evaluation suite (~10 minutes):
- Monte Carlo evaluation (50 episodes per scheduler)
- Statistical significance tests
- Mission Effectiveness Score with KPP gating
- Sensitivity analysis (bands, SNR, agility, density)
- Ablation study
- Multi-receiver cooperative evaluation
- ROC analysis
- Geolocation accuracy study
