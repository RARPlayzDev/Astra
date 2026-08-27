# Multi-Receiver Cooperative Scanning

When multiple ES receivers work together, they can cover more spectrum
simultaneously — but must avoid listening to the same band redundantly.

## Cooperative team

ASTRA supports teams of 1-3 receivers using the `CooperativeTeam` scheduler.

```
Receiver A (SmartScan)  →  selects band 7
                               ↓
                        DND token: "Band 7 is locked"
                               ↓
Receiver B (SmartScan)  →  removes band 7 from pool
                        →  selects band 12 (next best)
```

## DND (Do Not Disturb) tokens

When a SmartScan member has a **confirmed phase-lock** on a target band,
it broadcasts a DND token for that band. Other team members completely
remove that band from their selection pools.

**Result:** Zero redundancy and perfectly partitioned spectrum coverage.

## Benefits

| Metric | Single receiver | Team of 3 |
|---|---|---|
| Total reward | 1.0× | ~2.7× (near-linear scaling) |
| Threat coverage | 95% | 99%+ |
| Coverage speed | Slow | 3× faster |

## Configuration

In Operations:
1. Set **Team size** to 2 or 3
2. Each receiver runs independently with DND de-confliction
3. The waterfall shows Receiver A's perspective; KPIs include team size

In the API:
```bash
POST /api/live/start?team_size=3&sched_a=smart-scan
```
