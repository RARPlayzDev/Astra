# Geolocation

Multi-receiver AOA triangulation tutorial.

## Overview

When multiple ES receivers cooperate, they can estimate the geographic
position of emitters by measuring the angle-of-arrival (AOA) from each
receiver and triangulating.

## How it works

1. Each receiver measures the AOA of intercepted pulses (±2° noise)
2. Bearing lines from each receiver intersect at the emitter's position
3. Least-squares triangulation minimizes the residual error
4. CEP (Circular Error Probable) quantifies accuracy

## Using the Geolocation page

1. Start a mission in **Operations** (any policy)
2. Switch to **Geolocation** perspective
3. Set the number of cooperating receivers (2-4)
4. Click **Recalculate**

### Reading the map

| Symbol | Meaning |
|---|---|
| Red stars | True emitter positions |
| Cyan circles | Estimated positions (with CEP rings) |
| Blue triangles | Receiver positions |
| Grey lines | Bearing lines from receivers |

### Reading the statistics

| Metric | What it means |
|---|---|
| **Mean error** | Average distance between true and estimated positions |
| **CEP50** | Radius containing 50% of estimates (median accuracy) |
| **CEP90** | Radius containing 90% of estimates (worst-case accuracy) |

## Adding receivers

More receivers dramatically improve accuracy:

| Receivers | Typical CEP50 | Improvement |
|---|---|---|
| 2 | ~15 km | baseline |
| 3 | ~5 km | 3× improvement |
| 4 | ~2 km | 7× improvement |

The improvement from 2→3 receivers is the most dramatic.

## Using from CLI

```python
from ewsmart.geo import simulate_bearings, triangulate, cep_stats
import numpy as np

rng = np.random.default_rng(42)
receivers = [(0, 0), (50, 0), (25, 43)]  # 3 receivers
true_pos = (30, 20)

# Simulate bearings with 2° noise
lines = simulate_bearings(true_pos, receivers, noise_deg=2.0, rng=rng)

# Triangulate
est_x, est_y, residual = triangulate(lines)
error = np.hypot(est_x - true_pos[0], est_y - true_pos[1])
print(f"Estimated: ({est_x:.1f}, {est_y:.1f}), Error: {error:.1f} km")
```
