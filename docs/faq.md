# Frequently Asked Questions

## General

### What is ASTRA?

ASTRA (Adaptive Spectrum Threat Recognition & Analysis) is a desktop
application that schedules the scan pattern of an Electronic Support
receiver. It decides **which frequency band to listen to at every instant**
using machine learning, with zero prior intelligence on emitters.

### Is ASTRA operational equipment?

No. ASTRA is a **simulation-based research prototype** for Smart India
Hackathon 2026. It ships with a physically motivated simulated RF
environment so it runs anywhere with no hardware.

### Does ASTRA transmit or jam?

No. ASTRA is a **passive** system. It only listens. It never transmits,
jams, or connects to any classified system.

## Installation

### Does closing the app window stop the service?

Use **File → Exit** for a clean shutdown. The console window also stops
the service when closed.

### Can several windows share one service?

Yes — open additional browser tabs to the printed URL. All views stay in
sync because state lives server-side.

### Is any data sent to the internet?

No. Networking is loopback except an optional HuggingFace fetch inside
Dataset Studio, which falls back offline.

## Technical

### Where do the numbers come from?

Experiments over stored seeds. Re-run the suite to reproduce byte-for-byte:

```bash
python -m ewsmart.experiments --suite full
```

### Why does Receiver B exist?

Controlled comparison. Identical battlefields make the scanning strategy
the only variable. Any difference in outcome is attributable to strategy
alone.

### What KPPs does SmartScan satisfy?

1. **Threat coverage ≥ 90%** — finds 95%+ of hostile emitters
2. **Prediction accuracy ≥ 50%** — predicts at 62%+ accuracy
3. **False alarm rate ≤ 5×10⁻⁴/slot** — well within operator limits

### Why is UCB bandit not mission-capable despite high reward?

UCB bandit achieves the highest raw reward by camping on the single most
productive band. But it **misses 46% of all threats** — it never sweeps
for new or rare emitters. Missing nearly half the threats is unacceptable
regardless of reward.

### How does Counter-ESM evasion work?

Evasive emitters track consecutive interceptions. After 3+ consecutive
intercepts, they shift their rotation phase or swap to a new frequency
hop-set. The RF environment dynamically updates the truth matrix to
reflect the new behaviour.

### What is a DND token?

"Do Not Disturb" — when a receiver has a confirmed phase-lock on a
band, it broadcasts a DND token. Other team members remove that band
from their selection pools, ensuring zero redundancy.
