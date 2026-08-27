# Training Models

How to train, save, and evaluate scheduling policies.

## Quick train (in-app)

1. Open **Data & Sources** → **Model studio**
2. Select a policy (SmartScan, UCB bandit, or Q-learning)
3. Set the number of training episodes (2-30)
4. Click **Train & save**

The trained model is saved to `/models/` as a `.npz` file.

## Using trained models

1. Start a mission in **Operations**
2. Check **Load saved weights** in the configuration
3. Start the mission — SmartScan loads its trained weights

## Training from CLI

```bash
python -m ewsmart.runner \
    --scenario scenarios/demo.json \
    --save-dir models \
    --json-out results.json
```

## What gets saved

The `.npz` artifact contains:
- **SmartScan**: Q-table weights, bandit arm statistics, locked phase estimates
- **Q-learning**: Value function weights
- **UCB**: Arm counts and mean rewards

All artifacts are pickle-free (loaded with `allow_pickle=False`) for security.

## Evaluation

After training, evaluate on fresh scenarios:

```python
from ewsmart.persistence import load_scheduler
from ewsmart.environment import RFEnvironment
from ewsmart.runner import run_episode
from ewsmart.metrics import compute_metrics

sched = load_scheduler("models/smart-scan.npz")
env = RFEnvironment(n_bands=24, T=3000, seed=99)
trace = run_episode(env, sched, seed=1)
metrics = compute_metrics(env, trace)
print(f"Threat coverage: {metrics['threat_intercept_ratio']:.1%}")
print(f"Prediction accuracy: {metrics['pct_correct_predictions']:.1%}")
```

## Meta-learning (warm start)

The MetaScheduler wraps any learnable scheduler and persists state
across episodes, giving a warm start in similar environments:

```python
from ewsmart.schedulers import SmartScanScheduler, MetaScheduler

inner = SmartScanScheduler(n_bands=24, seed=42)
meta = MetaScheduler(inner)

# Episode 1 — cold start
meta.reset(horizon=3000)
trace1 = run_episode(env, meta, seed=0)
meta.end_episode()

# Episode 2 — warm start (Q-table preserved)
meta.reset(horizon=3000)
trace2 = run_episode(env, meta, seed=1)
# TTFF should be significantly shorter on episode 2
```
