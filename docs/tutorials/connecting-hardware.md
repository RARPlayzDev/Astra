# Connecting Hardware

How to wire real SDR or radar hardware into ASTRA.

## Overview

```
Your SDR/Radar → PDWs → Bridge → UDP → ASTRA → SmartScan
```

## Step 1: Produce PDWs

Your equipment must output pulse descriptor words in JSON format:

```json
{"toa_us": 1000.0, "freq_mhz": 9450.0, "pw_us": 1.5, "pa_db": 12.0, "aoa_deg": 90.0}
```

### Option A: rtl_power CSV sweep

```bash
rtl_power -f 2G:18G:100k -g 40 -i 1 -e 1h sweep.csv
```

### Option B: GNU Radio

Use a UDP sink block to emit JSON PDWs per detected peak.

### Option C: Direct emission

Write your own adapter mapping your format to the PDW schema.

## Step 2: Bridge to ASTRA

```bash
# Bridge a CSV sweep
python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555

# Relay an existing JSON UDP feed
python tools/sdr_bridge.py --mode udp --in-port 5000 --out-port 5555
```

## Step 3: Attach in ASTRA

1. Open **Data & Sources** perspective
2. Select **UDP feed** from the dropdown
3. Enter port `5555`
4. Click **Attach**
5. Verify: PDW count increases, rate shows a non-zero value

## Step 4: Start a mission

Return to **Operations** and start a mission. SmartScan will adapt
against your live data in real time.

## Verification checklist

- [ ] Bridge is running and sending PDWs
- [ ] ASTRA source shows non-zero PDW count and rate
- [ ] No errors in the source row
- [ ] Operations waterfall shows live data (not empty)

## Troubleshooting

| Problem | Solution |
|---|---|
| `WinError 10048` | Port already in use — choose another port |
| 0 PDWs received | Check bridge is running, port matches, firewall allows Python |
| Source shows "starting..." | Normal on first attach — wait 2 seconds |
| Empty waterfall | PDWs not reaching ASTRA — verify bridge output with `nc` |
