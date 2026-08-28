# Testing ASTRA â€” without a radar

This project is built to be tested end-to-end with **zero hardware**. Work
through the ladder below; each level removes one more assumption.

---

## Level 1 â€” automated test battery (fast, no window)

Each file runs standalone from the project root:

```powershell
python -X utf8 tests\test_smartscan.py      # scheduler + environment physics
python -X utf8 tests\test_modules.py        # config, dataset, DQN, persistence, viz
python -X utf8 tests\test_live.py           # streaming core incl. UDP round-trip
python -X utf8 tests\test_id_geo_stats.py   # identification, geolocation, statistics
python -X utf8 tests\test_mission.py        # KPP gate + MES scoring engine
python -X utf8 tests\test_software.py       # ASTRA app layer: sources, diagnostics, manual
python -X utf8 tests\test_api.py            # API endpoints + live arena advance
```

All must print `... passed`. If any fails, that is a real regression â€” stop and
fix before continuing.

## Level 2 â€” in-app diagnostics

Launch the app â†’ **Tools â†’ Diagnostics**. Eight self-tests cover imports,
simulation boot, benchmark data, figures, model-artifact integrity, frontend
bundle, manual availability and a UDP loopback send/receive. Everything green =
installation is sound.

## Level 3 â€” simulated sensor source

**Data & Sources â†’ Sensor sources â†’ Internal simulated scene â†’ Attach.**
The row should show a growing PDW count at roughly 20â€“60 PDWs/s. Detach should
remove it cleanly. This exercises the whole ingestion path with zero setup.

## Level 4 â€” UDP feed over the real network stack

Terminal 1 â€” start ASTRA (`ASTRA.exe` or `python desktop.py`).
Terminal 2 â€” generate radar traffic:

```powershell
python tools\pdw_generator.py --port 5555 --rate 400
```

Attach a **UDP feed** source on port 5555 in Data & Sources. Expect ~400 PDWs/s.
This validates: datagram parsing, multi-emitter patterns (stationary / agile /
periodic), out-of-order tolerance and rate accounting.

Variants worth trying:

| Test | Command / action | Expected behaviour |
|---|---|---|
| Low rate | `--rate 40` | counts grow slowly; source stays healthy |
| Burst flood | `--rate 3000` for 30 s | no crash; rate spikes then settles |
| Stop mid-stream | Ctrl+C the generator | source stays attached, rate decays to 0 |
| Wrong port | attach 5556, generate on 5555 | 0 PDWs (proves isolation) |
| Malformed data | `Write-Text "junk" > udp` via netcat-style tool | datagrams ignored, no crash |
| Port conflict | attach same port twice | second attach shows inline error |

## Level 5 â€” CSV replay bridge

Record or write a sweep as CSV (`toa_us,freq_mhz,pw_us,pa_db,aoa_deg` header)
and bridge it:

```powershell
python tools\sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555
```

Attach UDP on 5555. This is exactly how a real SDR processor would integrate.

## Level 6 â€” paired missions under load

Run **Start Mission** while a generator streams on another port. Try every
rate preset; let episodes complete; use File â†’ Open scenarioâ€¦ with different
battlefields; cycle Start/Stop rapidly 10Ã—; open two browser windows on the
service simultaneously and confirm both stay in sync.

### Edge-case checklist (tick all)

- [ ] Start Mission twice quickly â€” arena restarts cleanly, status bar shows RUNNING
- [ ] Stop while running â€” status returns READY, counters freeze
- [ ] Open scenario with tiny battlefield (edit a scenario to `n_bands: 4, T: 200`) â€” renders without errors
- [ ] Export results JSON â€” file downloads and parses
- [ ] Diagnostics after stopping mission â€” still all green
- [ ] File â†’ Exit â€” service shuts down; console exits
- [ ] Relaunch â€” previous state not required; app comes up clean
- [ ] Analysis tab with results file temporarily renamed â€” shows friendly "No results found", no crash

---

## Building the installer

`powershell
powershell -File tools\build_exe.ps1        # -> dist\ASTRA\ASTRA.exe (folder bundle)
# compile installer\ASTRA-Setup-2.0.0.exe with Inno Setup 6 (winget install JRSoftware.InnoSetup)
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\astra_installer.iss
```

Smoke-test the installer: run it, tick the desktop-icon box, finish, launch from the Start menu,
run Diagnostics (expect 8/8), then uninstall from Add/Remove Programs to confirm clean removal.

```powershell
powershell -File tools\build_exe.ps1     # produces dist\ASTRA\ASTRA.exe
```

Smoke-test the exe: launch it â†’ Diagnostics all green â†’ run Level 4 against it.

For an installed look (Start-menu shortcut, uninstaller), install
[Inno Setup](https://jrsoftware.org/isinfo.php) and compile
`installer/astra_installer.iss`.


## Level 7 - web prototype console (zero install)

The website ships an in-browser tester built from the same engine logic
(`website/src/engine/` mirrors `ewsmart/` core): open `/console.html` after
deploying (or `npm run dev` locally), press **Start mission**, and watch
SmartScan race a sequential sweep on identical battlefields. Use the seed field
to reproduce any battle and the event log to see phase-locks confirm or
self-destruct.

Engine parity check (headless, CI-friendly):

```powershell
cd website ; node scripts\_bundle.cjs ; node scripts\_smoke.cjs   # expect ENGINE SMOKE OK
```

> Maintenance rule: any behavioural change to `ewsmart` environment/receiver/
> schedulers must be mirrored in `website/src/engine/` in the same change-set -
> the PARITY CONTRACT header in each file tracks this.
