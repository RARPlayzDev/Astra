# Radar & SDR Integration

ASTRA consumes standard ESM measurements — **pulse descriptor words (PDWs)**.

## PDW Schema

```json
{
  "toa_us": 1000.0,
  "freq_mhz": 9450.0,
  "pw_us": 1.5,
  "pa_db": 12.0,
  "aoa_deg": 90.0
}
```

| Field | Meaning | Required |
|---|---|---|
| `toa_us` | Time of arrival (microseconds) | yes |
| `freq_mhz` | Centre frequency (MHz) | yes |
| `pw_us` | Pulse width (µs) | optional (default 1.0) |
| `pa_db` | Amplitude (dB) | optional |
| `aoa_deg` | Angle of arrival (degrees) | optional |

Datagrams may carry **one JSON object or a JSON array** of objects.

## Integration paths

### 1. Synthetic generator (no hardware)

```bash
python tools/pdw_generator.py --port 5555 --rate 400
```

Emits realistic multi-emitter traffic over UDP for integration testing.

### 2. Bridge an existing sweep log

```bash
python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555
```

Converts CSV sweeps (or relays an existing JSON feed with `--mode udp`)
into the ASTRA datagram format.

### 3. Direct emission

Your processor writes the PDW schema straight to ASTRA's UDP port.
Attach the source in **Data & Sources**, then select the same port.

## Wiring steps

1. **Produce PDWs** from your front-end (rtl_power CSV, ESM processor JSON, GNU Radio UDP block).
2. **Run the bridge** (if needed): `python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555`
3. **In ASTRA**: Open Data & Sources → Select "UDP feed" → Enter port → Click "Attach"
4. **Start a mission**: SmartScan adapts online against your live data.

## Adapting exotic front-ends

Write a ~30-line adapter mapping your format onto the five-field PDW schema.
See `tools/sdr_bridge.py` as the template. Channelised or FFT-based receivers
can emit one PDW per detected peak per dwell.

## Notes

- Frequency-to-band mapping uses the scenario's `[fmin, fmax]`
- All networking is local loopback by default
- The demo pipeline assumes a single receiver location; AOA is carried end-to-end
