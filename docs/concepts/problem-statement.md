# The Problem

## Electronic Support receivers

An Electronic Support (ES) receiver is a **passive** sensor — it only listens.
It never transmits. Its job is to detect, intercept, and analyse radio frequency
emissions from hostile sources.

The critical constraint: **an ES receiver can listen to only one narrow frequency
band at a time** while remaining responsible for monitoring a much wider spectrum.

```
Hostile radar (EMITTER)     →  transmits RF pulses
                                   ↓
ASTRA's ES receiver (SENSOR) →  listens, intercepts, identifies
                                   ↓
ASTRA's scheduler (BRAIN)   →  decides WHICH band to listen to, WHEN
```

## The two-dimensional search

Interception is a **two-dimensional search problem**:
1. **Which frequency band** to listen to
2. **At what time** to be there

A hostile radar might transmit on band 7 at time slot 1000, then band 15 at
slot 1003, then band 3 at slot 1010. The receiver must be on the right band
at the right time to intercept it.

## Why conventional approaches fail

### Fixed sequential sweep
Visit every band in a fixed order (1, 2, 3, ..., 24, 1, 2, 3...).
- **Problem:** Wastes most dwell time on empty or unimportant bands.
  If a radar transmits 5% of the time, the sweep visits it only 5% as often
  as needed.

### Naive adaptivity (camp on busy band)
Listen to whichever band had the most recent detections.
- **Problem:** Misses most threats by ignoring the rest of the spectrum.
  Finds one emitter well but misses 46% of all threats (UCB bandit result).

### The tension
ASTRA resolves the fundamental tension: **high reward** (camp on productive
bands) vs **high coverage** (sweep for new threats). No reference system
achieves both simultaneously — SmartScan does.

## Why this matters for defence

In a real Electronic Warfare scenario:
- Hostile radars **hop frequencies** unpredictably
- Some radars **scan periodically** (rotation, pulse repetition)
- Some emitters are **agile** (frequency-hopping)
- Some are **stationary** (continuous transmission)
- New threats can appear at any time

An ES receiver that wastes time on empty bands will miss critical threats.
An ES receiver that camps on one band will miss everything else.
**ASTRA finds the optimal balance.**
