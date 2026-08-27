# First Mission

Step-by-step walkthrough of your first ASTRA mission.

## 1. Launch ASTRA

```bash
python desktop.py
```

The application opens with the **Home** perspective showing headline stats.

## 2. Navigate to Operations

Click **Operations** in the toolbar (or press the Operations button).
You'll see the mission configuration panel.

## 3. Configure the mission

- **Receiver A**: SmartScan (adaptive) — our proposed scheduler
- **Receiver B**: Sequential sweep — the conventional baseline
- **Team size**: 1 (single receiver per side)
- **Sensitivity**: 6.0 dB (default)

## 4. Start the mission

Click **▶ Start Mission** (or press `F5`).

Two waterfall displays appear side by side. Each shows:
- **Blue-grey cells**: True emitter transmissions (ground truth)
- **Bright column**: Where the receiver is currently tuned
- **Amber markers**: Confirmed intercepts

## 5. Watch and learn

Observe how SmartScan (left) behaves differently from the sequential sweep (right):

- SmartScan quickly identifies productive bands and returns to them
- The sequential sweep blindly cycles through all bands regardless of content
- After ~300 slots, SmartScan begins phase-locking on periodic emitters

## 6. Read the results

KPI counters below each waterfall update continuously:
- **Threat coverage**: % of hostile emitters found at least once
- **Reward per dwell**: Average value earned per listen
- **Hit rate**: % of dwells that produced detections
- **Prediction accuracy**: % of correct ON/OFF predictions

## 7. Episode completion

When the episode completes (slot 2400/2400), a result line shows the
A/B comparison. The next episode starts automatically on a fresh scenario.

## 8. Try different configurations

- Change Receiver B to **UCB bandit** to see the exploit trap
- Increase **Team size** to 2 or 3 for cooperative scanning
- Try **Open scenario** (File → Open scenario) for different battlefields
- Adjust **Rate** to speed up or slow down the simulation

## Next steps

- [Connecting Hardware](/tutorials/connecting-hardware) — wire in real SDR data
- [Training Models](/tutorials/training-models) — train and save schedulers
- [Geolocation](/tutorials/geolocation) — multi-receiver triangulation
