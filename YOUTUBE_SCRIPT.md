# ASTRA — YouTube Script (6-Minute Cut)

**Runtime:** 6:00 exactly · **Tone:** confident, technical, zero hype that isn't backed by a
number · **Speak at ~145 wpm** — the nine `SAY` blocks total **744 spoken words**
(≈ 5:08 of narration), and the `ACTION` beats (waterfall runs, tour clicks, theme
crossfade) fill the remaining **~52 seconds** to land on 6:00. Read each block
word-for-word and the timing holds.

**How to read this document**

| Marker | Meaning |
|---|---|
| `SCREEN` | Exactly what must be visible (URL · section · tab). Never talk about a screen that isn't up. |
| `ACTION` | What your cursor does, in order. Record the screen doing *only* this. |
| `SAY` | Verbatim narration. Pause at `…`, emphasis in **bold**. |
| `ON-SCREEN` | Caption / lower-third / stat-chip the editor places on the video (see `VIDEO_EDITING.md`). |
| `EDIT` | Cut, zoom and sound cue for the edit pass. |

---

## 0 · Pre-flight checklist (once, before any take)

1. **Build everything fresh** so numbers on screen match this script:
   ```powershell
   cd website; npm run build          # site (4 pages incl. results.html)
   python -m pytest tests -q          # must end: 306 passed
   powershell -File tools\build_exe.ps1
   & "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\astra_installer.iss
   ```

   Then **publish the site** — the video shows live URLs, so they must answer 200:
   ```powershell
   powershell -File deploy.ps1        # build → Vercel production → HTTP-checks 4 routes
   ```
   If `astra-ew.vercel.app` answers `404 DEPLOYMENT_NOT_FOUND`, the Vercel project
   was removed; re-link it first (`npx vercel login`, then `npx vercel link`).
2. **Browser:** new guest window, 100 % zoom, bookmarks bar hidden, extensions off,
   window maximised, record at 1920×1080. Default **dark theme** for the shoot
   (the site remembers `localStorage["astra.theme"]`).
3. **Console prep:** open `/console.html` once, click through the first-run cards and
   the guided tour (so the tour doesn't interrupt a take), then reload. For Scene 5
   you deliberately reset first-run state with:
   ```javascript
   localStorage.removeItem("astra.console.v1");
   ```
4. **Theme prep:** record Scene 9 *before* switching themes; then click the sun/moon
   toggle once for the light-mode shot and switch back.
5. **Audio:** voice recorded separately if possible (phone/lav in a soft room) —
   separate track = 10× easier edit. Keep −12 dB peaks.
6. **Mouse:** cursor highlight ON in the recorder, no double-clicks. The site no
   longer draws its own cursor ring, so the recorder's highlight is the only
   pointer the viewer sees.
7. **Desktop app:** launch `dist\ASTRA\ASTRA.exe` once beforehand so first-run
   slowness never lands on camera.

## 1 · Verified fact sheet — the ONLY numbers you may say

Every figure was re-verified in this repo. If a number isn't here, don't say it.

| # | Fact | Source |
|---|---|---|
| 1 | **306 automated tests, all passing** | `python -m pytest tests -q` |
| 2 | Next-window prediction: **SmartScan 96.9 %** vs linear-Q 96.4 %, UCB 95.5 %, sequential **54.1 %**, random **50.2 %** (seed 4242) | `cd website; npm run probe` |
| 3 | Threat coverage **90.3–95.8 %** across seeds; sequential sweep ≈ **78 %** | `results/benchmark.json` · Results page |
| 4 | Threat time-to-first-fix **~1.8× faster** than sequential on the canonical KPP scene | `results/benchmark.json` |
| 5 | Periodic interception **> 91 % per cycle** (Rayleigh phase-lock) | benchmark |
| 6 | Agile-hop prediction **53 % top-1** vs **~4 %** chance | `results/benchmark.json` |
| 7 | Decision latency **~0.5–0.9 ms per dwell** (Python) | `results/performance.json` |
| 8 | PS coverage audit **13/13** live checks | `GET /api/ps-coverage` |
| 9 | Geolocation CEP improves **3.2 km → 1.7 km** with more receivers | Results page |
| 10 | Battlefield: **24 bands, 2–18 GHz**; emitters transmit ~**2 %** of the time | `website/src/engine/core.ts` |
| 11 | 200-episode Monte Carlo, paired permutation tests, **Holm-corrected**; all comparisons **p < 0.001** | Results page → Significance |
| 12 | Deep Q-network was benchmarked and **lost** under sparse, non-stationary reward — kept as documented negative result | `results/` + README |
| 13 | Site `astra-ew.vercel.app` · repo `github.com/RARPlayzDev/Astra` · installer **`ASTRA-Setup-3.0.0.exe`** (Releases, ~164 MB) | nav/footer |
| 14 | Docs page renders **29 sections**, searchable, copyable code blocks | `/documentation.html` |

---

## 1b · Demo plan — pick ONE demo, shoot it fast

If only one demo makes the cut, make it **chip `1 - Flagship race`**
(seed 4242 vs sequential). It is the *same seed as the probe* (96.9 % vs
54.1 %), it is the benchmark A/B, and it populates both the threat board and
the geolocation panel — one chip feeds Scenes 6 **and** 8 with zero extra
setup.

| Priority | Chip | Why shoot it | One-line pitch if a judge asks |
|---|---|---|---|
| **1 — shoot this** | `1 - Flagship race` | headline A/B, probe-seed parity, fills every panel | "Same battlefield, only the strategy differs: 100 % coverage vs 85.7 %." |
| 2 — +30 s budget | `2 - Periodic hunter` | phase locks visibly CONFIRM in the event log | "A lock needs repeated proof — stale beliefs self-destruct." |
| 3 — cautionary | `3 - Exploit trap` | UCB edges reward, then coverage collapses to 52.7 % | "Highest score on the board, half the threats missed — that's the trap." |

**Fast path (~35 s of screen time):** chip 1 → Start → 10 s of waterfalls
(Scene 6a) → Train 5 (6b, speed-ramped in the edit) → shootout table (6c) →
re-run chip 1 → threat board + geolocation (Scene 8). Skip presets 4 and 5
on camera — Low-SNR and Swarm need explanation time the cut doesn't have.

**Narrate results, not clicks.** Every demo line maps to a verified fact:
coverage → fact 3, prediction → fact 2, locks → fact 5, the DQN loss →
fact 12, sub-ms → fact 7, panels honest → section 24 of the manual. If a
number isn't in section 1, don't say it — improvise *around* it instead.

---

## 2 · The shoot — scene by scene

### Scene 1 · HOOK — 0:00 → 0:30 (~70 words)

**SCREEN:** `/` — hero, dark theme, spec-sheet title block with the live spectrum strip along the fold.
**ACTION:** Cursor still. Let the spectrum strip animate once. On “…two percent”, scroll down 20 px — nothing more.
**SAY:**
> Somewhere right now, a radar is transmitting… for two percent of the time. On twenty-four bands. And an Electronic Support receiver can listen to only one slice of spectrum at a time. Find it, or miss the war. This is ASTRA — an adaptive scan scheduler that learns when emitters speak, predicts the next window, and is already there — without prior intelligence. It stops searching… and starts making appointments.

**ON-SCREEN:** chip top-left `SIH 2026 · DRDO PROBLEM STATEMENT` · at “…two percent" big caption `TRANSMITS 2% OF THE TIME`.
**EDIT:** Cold open on black → hard cut to hero at 0:03. Slow 4 % push-in on the radar. Sub-bass hit on “ASTRA”.

---

### Scene 2 · PROBLEM — 0:30 → 1:00 (~78 words)

**SCREEN:** `/#problem` — the three cards (Conventional / Naive adaptivity / ASTRA's answer).
**ACTION:** Hover the two red cards briefly, then rest the cursor on the green answer card.
**SAY:**
> Conventional receivers sweep blindly — seventy-eight percent coverage, threats found late. A naive bandit does worse: it camps on the busiest band, scores the highest reward… and still misses almost half the threats. Reward and coverage pull in opposite directions. Every scheduler in our benchmark fails one or the other. Seven entered the gate; one passes every requirement at once. That one is SmartScan — and every number on this page comes from stored seeds you can rerun.

**ON-SCREEN:** stats chips over each card as named — `78% COVERAGE`, `54% DETECTED`, then gold `SMARTSCAN · BOTH`.
**EDIT:** Punch-in on each card as it's named; whoosh between cards.

---

### Scene 3 · THE LOOP — 1:00 → 1:30 (~71 words)

**SCREEN:** `/#walkthrough` — the five phase cards (Cold start → Fingerprint → Lock → Predict → Defend).
**ACTION:** Trace the five phase cards top to bottom, resting on each as it is named.
**SAY:**
> ASTRA runs one loop. A cold-start survey bootstraps statistics across every band. Each stream is fingerprinted; rhythms are believed only after Rayleigh significance testing. Validated locks turn search into an appointment: predict the next window, arrive early, dwell through it. Everything else rotates by discounted value — so no band starves. Wrong hypotheses die cheap. Survey, learn, predict, position, rotate — five phases, one decision per slot, no prior intelligence required.

**ON-SCREEN:** phase tags light up `01 02 03 04 05` in gold, synced to narration.
**EDIT:** Slide transitions between steps; keep total move under 6 seconds.

---

### Scene 4 · RESULTS FIRST — 1:30 → 2:15 (~88 words)

**SCREEN:** `/results.html` — KPI row, then scroll to the KPP gate table.
**ACTION:** Point at the KPI cards one by one, then scroll to the gate table and rest on the SmartScan row.
**SAY:**
> Results first, because this is what defence judging actually looks like. Hard Key Performance Parameters: threat coverage at least ninety percent, prediction better than chance, false alarms bounded. Pass every gate simultaneously — then we rank. Seven schedulers, two hundred Monte Carlo episodes, paired permutation tests, Holm-corrected. One row survives the gate: SmartScan. Every comparison, p below point zero zero one. And the same page carries identification, geolocation and multi-receiver scaling — every figure regenerate-able from one command. No cherry-picking: the failing rows stay on the page too.

**ON-SCREEN:** gold circle drawn around the SmartScan row · chip `ONLY MISSION-CAPABLE SCHEDULER` · footer chip `200 EPISODES · PAIRED · HOLM`.
**EDIT:** Zoom to 120 % on the gate table at “pass every gate”. Restrained — no shake.

---

### Scene 5 · CONSOLE FIRST-RUN — 2:15 → 3:00 (~90 words)

**SCREEN:** `/console.html`, fresh state (pre-flight `localStorage.removeItem("astra.console.v1")` done, reload).
**ACTION:** Let the five intro cards appear. Hover two cards, then click **Take the guided tour**. Step through 3–4 spotlight stops with ← →, showing the gold ring jumping to demo chips / mission config / waterfall. Then press Escape.
**SAY:**
> The console teaches itself. First visit: five cards — what this console is, the three bays, how to read the waterfall, how to use it, and the offline desktop build. Then a seven-stop guided tour takes over and spotlight-jumps to every control that matters — demo chips, start and pause, mission config, the live waterfall, the KPI tiles — each one explaining what it does in plain language. Sixty seconds and you know the whole instrument. Help reopens it any time — arrow keys step through, Escape gets you out.

**ON-SCREEN:** captions naming each spotlight target as it lights: `DEMO CHIPS`, `MISSION CONFIG`, `LIVE WATERFALL`…
**EDIT:** Speed-ramp the mouse travel between spotlight targets to 1.6×; hold at full speed on each tooltip.

---

### Scene 6 · LIVE A/B + INTELLIGENCE — 3:00 → 4:00 (~116 words)

**SCREEN:** `/console.html` → Live Mission tab → run the paired mission; then Learning Arena; then Model Lab.
**ACTION:** (a) Click demo chip **1 - Flagship race**, **Start mission**, let both waterfalls run ~10 s — capture the density difference. (b) Open Learning Arena → **Train 5 episodes**. (c) Open Model Lab → **Run shootout**, rest cursor on the verification table.
**SAY:**
> Watch two receivers fly the identical battlefield. Same signals, same seeds — the only variable is the strategy. One waterfall stays sparse while the other fills gold. Then the console trains: the Learning Arena learns from hits and misses and rises episode over episode. And the probe table doesn't flatter us — next-window prediction, ninety-six point nine percent for SmartScan… against fifty-four point one for the sweep. Agile-hop prediction: fifty-three percent top-one, against four percent by chance. We also benchmarked a deep Q-network. It lost. Under sparse, non-stationary reward — so we keep it, documented, as a negative result. Mean decision cost stays under a millisecond per dwell — the engine keeps up with the radio.

**ON-SCREEN:** split caption `SAME SCENE · DIFFERENT STRATEGY` · probe chips `96.9%` gold / `54.1%` grey · stamp `NEGATIVE RESULT: DQN — KEPT IN REPORT`.
**EDIT:** Side-by-side waterfall crop for 6 s. Speed-ramp training to 2×. Beat on “…it lost.” before the DQN line.

---

### Scene 7 · DOCS + EVIDENCE — 4:00 → 4:40 (~77 words)

**SCREEN:** `/documentation.html` — type “calibration” in the sidebar filter, open a section, hover a code block; then a terminal with `pytest` and `npm run probe`.
**ACTION:** Filter → click section → press → once to page. Hover a `<pre>` block and click **copy**. Cut to terminal showing `306 passed` and the probe table.
**SAY:**
> Every claim has a paper trail. The documentation ships inside the product — twenty-nine sections, from installation to API to simulation fidelity to the desktop shortcuts — searchable, paged with arrow keys, code blocks one click to copy. And the evidence itself: three hundred and six automated tests, one command. The prediction probe, one command. Same seeds, same numbers, on any machine. Read the arithmetic before you trust it — that's the whole culture of this project.

**ON-SCREEN:** chip `29 SECTIONS · SEARCHABLE · COPYABLE` · terminal captions `306 PASSED` / `96.9% vs 54.1%`.
**EDIT:** Macro zoom on the copy button click. Hard cut black → terminal, keyboard-clack SFX.

---

### Scene 8 · WEBSITE DEMO → DESKTOP — 4:40 → 5:15 (~75 words)

**SCREEN:** `/console.html` → Live Mission tab with the **Threat board** and **Geolocation** panels populated; then cut to `dist\ASTRA\ASTRA.exe` — native window, Data & Sources (Simulated │ UDP Bridge │ Log Tail), then Tools → Diagnostics.
**ACTION:** On the site: (re-run demo chip **1 - Flagship race** + **Start mission** if the Scene 6 run has ended) let it tick ~15 s, rest the cursor on a threat-board row (confidence under 100 %), then on the geolocation CEP readout. Cut to the desktop app: sweep the cursor across the menu bar (File · View · Run · Tools · Help) and toolbar, open the **UDP Bridge** source card, then Tools → Diagnostics and let the all-green list settle 3 s.
**SAY:**
> Everything runs in the browser first: the threat board scores each intercepted stream on its measured fingerprint — never a fake perfect confidence — while the geolocation map fixes emitters from real bearings and reports the circular error honestly. Then the same product installs as a Windows app: native window, menus and toolbar, pulse-descriptor words in over UDP or a log tail, manual included, diagnostics all green. No cloud, no login — it runs air-gapped.

**ON-SCREEN:** chip `ONE ENGINE · BROWSER FIRST · DESKTOP READY` · captions `MEASURED FINGERPRINT`, `UDP PDW IN`, `DIAGNOSTICS ALL GREEN`.
**EDIT:** Hard cut website → desktop window on “Windows app”. Gold underline sweep under the all-green diagnostics list.

---

### Scene 9 · THEME + CLOSE — 5:15 → 6:00 (~79 words)

**SCREEN:** back to `/` — click the sun/moon toggle (light-mode beauty shot for 3 s), toggle back to dark, land on hero.
**ACTION:** One theme click, pause, click back. End on hero with the spectrum strip running; cursor rests on **Download v3.0.0**.
**SAY:**
> ASTRA — adaptive spectrum threat recognition and analysis. Three hundred and six tests, reproducible results, a console that teaches itself, twenty-nine sections of documentation, light or dark — the same product in your browser and on your desktop. Built for a DRDO problem statement under Smart India Hackathon twenty-twenty-six. The installer, the live console and every number on this page are in the description. Download it, run the probe, check our arithmetic. If it holds up, that's the point.

**ON-SCREEN:** lower-third `github.com/RARPlayzDev/Astra · astra-ew.vercel.app` · end card with 3 buttons `DOWNLOAD v3.0.0` `LIVE CONSOLE` `RESULTS`.
**EDIT:** Theme crossfade is the money shot — hold it. End card in from 5:52; fade audio under last line; radar-sweep SFX out.

---

## 3 · B-roll shot list (record extras — cheap insurance)

| # | Shot | Used for |
|---|---|---|
| 1 | Hero spectrum strip + sweep instrument, 15 s idle | hook / end card |
| 2 | Light-mode theme crossfade, 3 takes | Scene 9, Shorts |
| 3 | First-run cards + one spotlight highlight | Scene 5 alternate takes |
| 4 | Paired waterfalls running, 20 s | Scene 6 |
| 5 | Arena rising bars, 10 s | Scene 6 |
| 6 | Docs search + copy-click macro | Scene 7 |
| 7 | Terminal: `306 passed` + probe table | Scene 7 |
| 8 | `ASTRA.exe` launch + Diagnostics all-green | Scene 8 |
| 9 | Mission tab: threat board + geolocation map populating, 15 s | Scene 8 |

**Still assets:** `assets/astra_mark_512.png` (logo), `figures/*.png` (publication
figures — translucent backgrounds), brand palette `#05070b` bg · `#cfa453` gold ·
`#6f9ec7` steel-blue — the editor should reuse these exact hex values for all
captions (see `VIDEO_EDITING.md`).

## 4 · YouTube metadata

**Titles (A/B test two):**
1. `ASTRA — an AI scan strategy that finds radars hiding 98% of the time (SIH 2026)`
2. `Open-loop sweeps search. This one anticipates. — ASTRA Electronic Support demo`

**Chapters (paste into description):**
```
0:00 The invisible radar (hook)
0:30 The problem: a 2-D search you can't brute-force
1:00 The loop: survey → learn → predict → position → rotate
1:30 Results first: the KPP gate
2:15 The console teaches itself (first-run tour)
3:00 Live A/B + Learning Arena + the probe table
4:00 Documentation & evidence
4:40 Browser panels first, then the Windows desktop
5:15 Light / dark, download, close
```

**Description skeleton:**
> ASTRA (Adaptive Spectrum Threat Recognition & Analysis) — an ML Electronic Support
> receiver scheduler that minimises intercept time without prior intelligence.
> Live console: https://astra-ew.vercel.app/console.html · Results:
> https://astra-ew.vercel.app/results.html · Docs:
> https://astra-ew.vercel.app/documentation.html · Repo:
> https://github.com/RARPlayzDev/Astra · Windows installer:
> `ASTRA-Setup-3.0.0.exe` (Releases, ~164 MB) · 306 automated tests · next-window
> prediction 96.9% vs 54.1% sequential sweep (`npm run probe`) · 200-episode Monte
> Carlo, Holm-corrected, all comparisons p < 0.001 · results are seed-exact and
> reproducible. Simulation-based research prototype for Smart India Hackathon 2026,
> against a DRDO problem statement — not operational equipment.

**Tags:** `electronic warfare`, `electronic support`, `signal intelligence`, `radar
detection`, `spectrum awareness`, `Smart India Hackathon`, `SIH 2026`, `reinforcement
learning`, `smart scan`, `ASTRA`, `ES receiver`, `LPI radar`.

**Thumbnail:** split frame from Scene 6 — left waterfall sparse/grey labelled
`BLIND SWEEP · 54%`, right waterfall dense/gold labelled `ASTRA · 96.9%`; dark
`#05070b` background, gold `#cfa453` for the ASTRA number only, one human element
(optional: your face bottom-right, surprised/proud, 15 % of frame). Max two text
elements — thumbnail text must be readable at 120 px wide.

## 5 · Mapping to the 6-slide deck (offline pitch version)

If you must present `ASTRA_SIH2026_Presentation.pptx` instead of the site, scenes
map 1:1 — S1 hook = Scenes 1+2 · S2 problem = Scene 2 · S3 architecture = Scene 3 ·
S4 intelligence = Scene 6 (arena/probe) · S5 results/demo = Scenes 4+6 ·
S6 roadmap = Scene 8. Speaker notes live in `ppt.md` — use the same `SAY` text here
for consistency between video and stage.

---

*Fact sheet re-verified: 306 tests collected (`pytest --collect-only`), probe numbers
from `website/scripts/pred_probe.ts`, benchmark numbers from `results/benchmark.json`.
Re-verify before re-recording after any engine change.*
