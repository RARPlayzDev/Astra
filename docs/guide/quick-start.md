# Quick Start

Three steps to your first ASTRA mission.

## Step 1: Launch

```bash
python desktop.py
# or double-click ASTRA.exe
```

A console window shows service startup, then the application window opens.

## Step 2: Start a mission

Press **▶ Start Mission** on the toolbar (or press `F5`).

Two receivers fly identical battlefields simultaneously:
- **Receiver A** — SmartScan (our adaptive scheduler)
- **Receiver B** — Sequential sweep (conventional baseline)

## Step 3: Read the results

Watch the Operations perspective:

| What you see | Meaning |
|---|---|
| Blue-grey cells | True emitter transmissions (ground truth) |
| Bright vertical band | Where the receiver is currently tuned |
| Amber markers | Confirmed intercepts |
| KPI counters | Threat coverage, reward, hit rate, prediction accuracy |

When the episode completes, a result line summarises the A/B outcome.
The next episode starts automatically on a fresh scenario.

---

**That's it.** You've just observed SmartScan outperforming a conventional sweep on identical battlefields. The difference in outcome is attributable to scanning strategy alone.

## Next steps

- [Interface Tour](/guide/interface-tour) — learn the full layout
- [Analysis](/concepts/evaluation-methodology) — understand the metrics
- [Connect Hardware](/tutorials/connecting-hardware) — wire in real SDR data
