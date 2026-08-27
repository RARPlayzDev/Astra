# Scheduling Policies

Seven policies ship with ASTRA. Six are honest reference baselines;
SmartScan is the proposed hybrid.

## Policy comparison

| Name | Type | Learns? | Coverage | Reward | Prediction |
|---|---|---|---|---|---|
| **Sequential sweep** | Open loop | No | High | Low | None |
| **Random scan** | Open loop | No | High | Low | None |
| **Priority sweep** | Open loop | No | Medium | Low | None |
| **UCB bandit** | Adaptive | Yes (exploit only) | **Low** | **High** | High |
| **Linear Q-learning** | RL | Yes | High | Medium | **Low** |
| **Deep Q-network** | Deep RL | Yes | Medium | Medium | Medium |
| **SmartScan** | Hybrid | Yes | **High** | **High** | **High** |

## Detailed descriptions

### Sequential sweep
Visits every band in a fixed cyclic order. The simplest approach — no
learning, no adaptation. Serves as the conventional baseline.

### Random scan
Selects bands uniformly at random. Covers the spectrum well (by chance)
but wastes time on empty bands with no intelligence.

### Priority sweep
Uses pre-programmed intelligence to visit high-priority bands first.
Requires prior knowledge that may not be available in practice.

### UCB bandit (Upper Confidence Bound)
Multi-armed bandit approach: exploits the highest-reward band while
occasionally exploring others. Converges on the richest band but
**misses 46% of threats** — the classic exploit trap.

### Linear Q-learning
Tabular reinforcement learning with hand-crafted features. Learns
value estimates over bands but predicts presence at near-chance level
on this sparse-reward task.

### Deep Q-network (DQN)
Neural network function approximation with experience replay and
target network. More capacity than linear Q-learning but suffers
from overfitting on the sparse, high-dimensional EW task. Declines
on held-out greedy evaluation.

### SmartScan (proposed)
Hybrid scheduler multiplexing five behaviours (recon, phase-lock
pursuit, predict-and-probe, burst characterisation, value-weighted
rotation) based on learned confidence. The only policy passing all
three KPP gates simultaneously.

## Why UCB fails despite high reward

The UCB bandit achieves the highest raw reward because it camps on
the single most productive band. But it **misses 46% of all threats** —
it never sweeps for new or rare emitters. In a defence context,
missing nearly half the threats is unacceptable regardless of reward.

## Why Q-learning fails despite coverage

Linear Q-learning covers most threats (89.6%) but its prediction
accuracy is only 19% — barely above chance. It learns to visit
threatening bands but cannot predict when they will transmit again.
