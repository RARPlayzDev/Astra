# ASTRA — Full Production YouTube Script (Shoot-by-Shoot)

**Runtime:** ~8:30 · **Tone:** confident, technical, zero hype that isn't backed by a
number · **Speak at ~145 wpm** — every `SAY` block below is written word-for-word at
that pace, so read it exactly as written and the timing holds.

**How to read this document**

| Marker | Meaning |
|---|---|
| `SCREEN` | Exactly what must be visible (URL · section · tab). Never talk about a screen that isn't up. |
| `ACTION` | What your cursor does, in order. Record the screen doing *only* this. |
| `SAY` | Verbatim narration. Pause at `…`, emphasis in **bold**. |
| `ON-SCREEN` | Caption / lower-third / stat-chip the editor places on the video (see `VIDEO_EDITING.md`). |
| `EDIT` | Cut, zoom and sound cue for the edit pass. |

---

## 0 · Pre-flight checklist (do this once, before any take)

1. **Build everything fresh** so numbers on screen match this script:
   ```powershell
   cd website; npm run build          # site
   python -m pytest tests -q          # must end: 306 passed
   powershell -File tools\build_exe.ps1
   ```
2. **Browser:** new guest window, 100 % zoom (or 90 % on small screens), dark theme,
   bookmarks bar hidden, extensions off, window maximised, screen recorded at 1920×1080
   (or 1440p) — never record a window with visible personal tabs.
3. **Console prep:** open `/console.html` **once**, click through the first-run cards and
   the guided tour (so the tour doesn't interrupt a take), then reload. For Scene 5 you
   will deliberately reset the first-run state with:
   ```javascript
   localStorage.removeItem("astra.console.v1");
   ```
4. **Audio:** record voice separately (phone/lav in a soft room) if possible — separate
   audio track = 10× easier edit. Keep -12 dB peaks, no EQ games yet.
5. **Mouse:** OS pointer size normal, cursor highlight effect ON in the recorder, no
   double-clicks (double-clicks desync click animations in the edit).
6. **Window for desktop app:** launch `dist\ASTRA\ASTRA.exe` once beforehand so
   first-run slowness never lands on camera.

## 1 · Verified fact sheet — the ONLY numbers you may say

Every figure below was re-verified in this repo. If a number isn't here, don't say it.

| # | Fact | Source |
|---|---|---|
| 1 | **306 automated tests, all passing** | `python -m pytest tests --collect-only -q` → 306; `pytest -q` |
| 2 | Prediction accuracy: **SmartScan 96.9 %** vs linear-Q 96.4 %, UCB 95.5 %, sequential **54.1 %**, random **50.2 %** (seed 4242) | `cd website; npm run probe` + Console → Model Lab → Verification numbers |
| 3 | Threat coverage **90.3–95.8 %** across seeds; sequential sweep ≈ **78 %** | `results/benchmark.json`, Home → Problem card |
| 4 | Threat time-to-first-fix **~1.8× faster** than sequential on the canonical KPP scene | `results/benchmark.json` |
| 5 | Periodic interception **> 91 % per cycle** (Rayleigh phase-lock) | benchmark |
| 6 | Agile-hop prediction **53 % top-1** vs **~4 %** chance | `results/benchmark.json` |
| 7 | Decision latency **~0.5–0.9 ms per dwell** (Python) | `results/performance.json` |
| 8 | PS coverage audit **13/13** live checks | `GET /api/ps-coverage` |
| 9 | Geolocation CEP improves **3.2 km → 1.7 km** with more receivers | Home → Capabilities |
| 10 | Battlefield: **24 bands, 2–18 GHz**; emitters transmit ~**2 %** of the time | `website/src/engine/core.ts`, README |
| 11 | 200-episode Monte Carlo, paired permutation tests, **Holm-corrected** | Home → Results |
| 12 | Deep Q-network was benchmarked and **lost** under sparse, non-stationary reward — kept as documented negative result | `results/` + README |
| 13 | Site: `astra-ew.vercel.app` · repo: `github.com/RARPlayzDev/Astra` · installer `ASTRA-Setup-2.0.0.exe` | nav/footer |

---

## 2 · Scene index (record in this order — easier than chronology)

| Scene | Time | On screen | Beat |
|---|---|---|---|
| 1 | 0:00–0:30 | `/console.html` → Live Mission, Flagship race mid-run | Hook — the invisible radar |
| 2 | 0:30–1:10 | `/` → #problem | The 2-D search you can't brute-force |
| 3 | 1:10–1:50 | `/` → #how | The loop: survey → learn → predict → position → rotate |
| 4 | 1:50–2:30 | `/` → #results | Judged the way defence judges systems (KPP gate) |
| 5 | 2:30–3:15 | `/console.html` first-run (fresh state) | Onboarding: 3+ intro cards → spotlight tour |
| 6 | 3:15–4:30 | Console → Live Mission | The live A/B race — watch it learn |
| 7 | 4:30–5:10 | Console → Learning Arena | Training across episodes (hits & misses) |
| 8 | 5:10–5:55 | Console → Model Lab | The numbers, including the honest one |
| 9 | 5:55–6:25 | `/documentation.html` + GitHub repo | What's under the hood / where the evidence lives |
| 10 | 6:25–7:10 | `ASTRA.exe` desktop app | Beyond the browser — desktop command centre |
| 11 | 7:10–7:40 | `build/rtl/astra_policy_kernel.hpp` + `tools/pdw_generator.py` | Hardware on-ramp (fixed-point kernel, UDP PDW) |
| 12 | 7:40–8:15 | Console → Live Mission, race running | Close — the one-line pitch |

---

## 3 · The shoot

### Scene 1 — [0:00–0:30] HOOK — the invisible radar

**SCREEN:** `https://astra-ew.vercel.app/console.html` → **Live Mission** tab, Flagship
race already running (set this up before rolling: click `1 - Flagship race`, let it run
~40 s so both waterfalls are alive).

**ACTION:**
1. Cursor rests on Receiver A's waterfall; a few **gold intercept cells** flash.
2. Slow cursor sweep left → right across the two receiver panels (one smooth pass, no click).

**SAY:**
> A radar that transmits two percent of the time is effectively invisible to a
> conventional scanner. You must be listening on the right frequency, at the right
> millisecond — and you have no idea which frequency that is. This is the core
> problem of Electronic Support. This is **ASTRA** — and in the next eight minutes
> I'll show you the engine, the learning, and the numbers behind it.

**ON-SCREEN:** (0:02) title chip — `ASTRA · Adaptive Spectrum Threat Recognition &
Analysis`; (0:10) corner caption — `Live simulation · seed 4242 · running in your browser`.

**EDIT:** Cold open — no music fade-in, hard cut from black. Punch-in 110 % on the gold
flashes at "right millisecond". Low tension drone bed starts at 0:00, -24 LUFS under VO.

---

### Scene 2 — [0:30–1:10] THE PROBLEM — a 2-D search you can't brute-force

**SCREEN:** `https://astra-ew.vercel.app/` → scroll to `#problem`
("Finding a needle that transmits for 2% of the time"; three cards: Conventional /
Naive Adaptivity / ASTRA's Answer).

**ACTION:**
1. Scroll from hero into `#problem` (smooth, one motion).
2. Cursor underlines "2% of the time" in the heading.
3. Hover the red **Conventional** card, then the red **Naive Adaptivity** card, then
   the green **ASTRA's Answer** card — one second each, in that order.

**SAY:**
> An ES receiver is sensitive but narrowband — it listens to one slice of spectrum
> while being responsible for a far wider range, so interception becomes a
> two-dimensional search: right frequency, right time. The old approach is open-loop:
> sweep the band, top to bottom, forever — it burns dwell on empty spectrum and it
> never learns. Even naive adaptivity fails: a pure bandit camps on the busiest band
> and misses half the threats. Hostile emitters are periodic, hopping, and evasive —
> designed to be found only by luck.

**ON-SCREEN:** stat chips fly in over the cards — `78 % coverage · open-loop sweep`
(red), `54 % threats found · bandit` (red), `High reward AND near-total coverage ·
SmartScan` (green).

**EDIT:** 200 ms zoom-step on each card as the cursor reaches it. No cuts inside the
paragraph — one continuous take reads as confidence.

---

### Scene 3 — [1:10–1:50] THE LOOP — from blind sweep to scheduled intercept

**SCREEN:** `/` → `#how` — the five-step pipeline: Survey · Learn · Predict · Position ·
Rotate.

**ACTION:**
1. Scroll into `#how`; cursor walks the five pipe-steps left → right, ~1.5 s each.
2. Pause the cursor on **Predict** while you say "arrives before it turns on".

**SAY:**
> ASTRA replaces the fixed pattern with a loop. **Survey** — a fast reconnaissance
> sweep bootstraps statistics across every band, no prior intelligence required.
> **Learn** — detections are fingerprinted by SNR and angle-of-arrival, and
> periodicities are estimated with Rayleigh significance testing. **Predict** — a
> validated lock knows each emitter's next transmission window before it opens.
> **Position** — the receiver arrives early and dwells through the predicted window,
> so interception becomes schedule, not luck. **Rotate** — the rest of the time is
> allocated by discounted value, so no band starves. Wrong hypotheses are validated
> continuously and die cheap.

**ON-SCREEN:** step labels pop as numbered lower-thirds `1 Survey … 5 Rotate`; chip —
`no prior intelligence required`.

**EDIT:** Keep the five steps as one shot; in the edit, add a 5 % push-in that resets
each time the cursor enters a new step (visible "step pulse").

---

### Scene 4 — [1:50–2:30] RESULTS FIRST — judged the way defence judges systems

**SCREEN:** `/` → `#results` — the KPP-gate table (Scheduler · Verdict · MES · Threat
coverage · Prediction accuracy) with the `KPP Gate Criteria` legend above it.

**ACTION:**
1. Scroll into `#results`; cursor traces the legend chips (Threat coverage ≥ 90 %,
   Prediction accuracy ≥ …, False alarm ≤ …).
2. Hover the SmartScan row — the `CAPABLE` pill — then sweep down the
   `DISQUALIFIED` rows.

**SAY:**
> Before the demo, the scoreboard. We judge this the way defence judges systems:
> Key Performance Parameters first — threat coverage above ninety percent,
> prediction better than chance, false alarms bounded — all must pass
> simultaneously. Two hundred Monte Carlo episodes, paired permutation tests,
> Holm-corrected. SmartScan is the only scheduler in the field that passes **every**
> KPP at once. Others score high on one metric and get disqualified on the gate.

**ON-SCREEN:** chip over the verdict column — `all-or-nothing gate`; corner caption —
`200-episode Monte Carlo · Holm-corrected · seed-exact reproducible`.

**EDIT:** Slow 105 % drift-zoom toward the `CAPABLE` pill; hit a soft "tick" SFX when
the pill fills frame at ~2:20.

### Scene 5 — [2:30–3:15] FIRST-RUN UX — onboarding that explains itself

**SCREEN:** `https://astra-ew.vercel.app/console.html` in a **fresh state**. Before the
take, run in DevTools console:
```javascript
localStorage.removeItem("astra.console.v1")
```
reload, so the console opens its first-run experience exactly as a new judge would see it.

**ACTION:**
1. Page loads → the **intro modal appears with the info cards** (what this console is /
   the three bays / how to read the waterfall / how to use). Cursor circles the card grid.
2. Click **Start guided tour**.
3. The **spotlight tour** begins: first box lands on the demo chips; click **Next** and
   let it walk 3–4 highlights (demos → Start/Pause → waterfall → KPIs).

**SAY:**
> This is the browser console — and watch what a first-time visitor gets. Before you
> touch anything, three-plus plain-language cards explain what the console is, what
> the three bays do, and how to read the waterfall — blue is ground truth, the grey
> column is where the receiver is listening, gold is an intercept. One click later a
> spotlight tour points at every important control and tells you exactly what it does
> and how to use it. No manual required — the interface teaches itself.

**ON-SCREEN:** chips — `first-run onboarding`, `spotlight tour · replayable from
Help`, `306 tests behind the engine` (bottom-left corner caption).

**EDIT:** Cut on each "Next" click so four highlights play in ~12 s (10–12 frames of
each tooltip minimum — readable). Add a subtle 8-frame white flash on the spotlight
ring as it lands.

---

### Scene 6 — [3:15–4:30] LIVE DEMO — watch it learn

**SCREEN:** Console → **Live Mission** tab. Demo panel visible at top; two receiver
waterfalls below; KPI tables; event log at the bottom.

**ACTION:**
1. Click `1 - Flagship race` (configures seed 4242 and starts immediately).
2. Let it run. Cursor points at **Receiver A (SmartScan)** waterfall, then **Receiver B
   (sequential sweep)** — one pass each.
3. When `phase-lock CONFIRMED` appears in the event log, stop the cursor on that line.
4. Move up to Receiver A's KPI table: hover **Threat coverage**, then **Threat TTFF**;
   then Receiver B's same rows for contrast.

**SAY:**
> Here's the live mission. Two receivers, byte-identical battlefields — same scene,
> same receiver physics, only the scheduling brain differs. Left: ASTRA. Right: the
> classic sequential sweep. Watch the gold flashes — that's an intercept. The sweep
> covers everything and finds almost nothing. ASTRA surveys, locks onto the rhythm —
> see "phase-lock CONFIRMED" in the event log — and then arrives at the emitter's
> next window **before it turns on**. Threat coverage in the nineties versus the
> high seventies for the sweep, and threat time-to-first-fix tells the same story —
> about 1.8 times faster on the canonical scene. Every dwell decision you're
> watching costs half a millisecond in Python.

**ON-SCREEN:** split captions under panels — `A · SmartScan (adaptive)` /
`B · Sequential sweep (open-loop)`; when the log line hits — pull-quote animation
`phase-lock CONFIRMED`; corner chip `same battlefield · same receiver · only the
strategy differs`.

**EDIT:** This is your hero sequence — longest uninterrupted take. Two things only:
(1) 115 % punch-in when the cursor reaches the CONFIRMED line, hold 3 s;
(2) side-by-side crop zoom if the two waterfalls don't read clearly at 1080p. Keep
music under; add a soft riser when the first gold streak lands.

### Scene 7 — [4:30–5:10] LEARNING ARENA — trained on hits and misses

**SCREEN:** Console → **Learning Arena** tab (the isolation banner is visible).

**ACTION:**
1. Click **Learning Arena** tab.
2. Click `Train 5 episodes` — wait for the table + rising bar chart.
3. Cursor walks the bars episode 1 → 5.

**SAY:**
> The problem statement requires the model to be trained on hits and misses, so
> there's a dedicated arena — deliberately isolated from the live mission, so
> experiments can't contaminate it. Five full episodes on five *fresh* battlefields,
> while the learner carries its consolidated band-value memory forward. Compare
> episode one — cold start — with what follows: each new battlefield is conquered
> faster. That rising bar chart is warm-starting made visible. One click wipes the
> memory if you want to start over.

**ON-SCREEN:** chip — `isolated sandbox · own learner`, arrow annotation on bar 1 —
`cold start` → on bars 4–5 — `warm start`.

**EDIT:** Speed-ramp the training wait to 2–3× (keep the bars' final state at 1×);
cut the moment the last bar settles.

---

### Scene 8 — [5:10–5:55] MODEL LAB — the numbers, including the honest one

**SCREEN:** Console → **Model Lab** tab → "Policy shootout" panel, then "Verification
numbers — engine probe" panel below it.

**ACTION:**
1. Click **Model Lab** tab; click `Run shootout`; table fills (SmartScan row is
   highlighted).
2. Scroll to **Verification numbers**; cursor underlines `96.9 %` then drops to
   `54.1 %` (sequential) and `50.2 %` (random).

**SAY:**
> In the Model Lab, every policy runs headlessly on the exact same seed and scene —
> same battlefield, same receiver, same reward. Prediction accuracy, scored honestly
> against ground truth: SmartScan 96.9 percent. Linear Q-learning, 96.4. UCB, 95.5.
> The sequential sweep? 54 — because with no model, your predictions are a coin flip.
> Now the honest part: we also built a full deep Q-network. It *lost*. Under sparse,
> non-stationary rewards it underperformed even the blind sweep — so we kept it in
> the repo as a documented negative result. In electronic support you ship what
> survives the benchmark, not what looks good in the title.

**ON-SCREEN:** table callouts (animated) — `96.9 % SmartScan` (gold), `54.1 %
sequential` (grey); caption — `reproduce: cd website && npm run probe`; over the
negative-result line — `documented negative result · deep Q-network`.

**EDIT:** When you say "It lost", hard cut to a 0.5 s black frame with white text
`IT LOST.` — then cut back. Strongest 12 frames in the video; don't overuse the trick
elsewhere.

### Scene 9 — [5:55–6:25] UNDER THE HOOD — where the evidence lives

**SCREEN:** `https://astra-ew.vercel.app/documentation.html` (sidebar with 21 sections
visible), then tab to the GitHub repo `github.com/RARPlayzDev/Astra` (file tree).

**ACTION:**
1. On the docs page, cursor sweeps the sidebar: *Interface tour*, *Scheduling policies*,
   *Evaluation methodology*, *Architecture reference*.
2. Cut to the repo root; cursor hovers `ewsmart/`, `tests/`, `results/`, `docs/`.

**SAY:**
> Everything I've shown is documented A to Z — the manual ships inside the desktop
> app and online: installation, interface tour, every scheduling policy, the
> evaluation methodology, the architecture reference. And the repo itself is the
> evidence: the engine in `ewsmart/`, three hundred six automated tests in `tests/`,
> every published figure regenerated from stored seeds in `results/`. Nothing here
> is a hand-typed number.

**ON-SCREEN:** captions — `21-section manual · in-app + online`, `306 tests · one
command: python -m pytest tests -q`, `seed-exact reproducibility`.

**EDIT:** Two shots max. On "hand-typed number", show a 1 s flash of a terminal
running `pytest -q` ending in green `306 passed` (record this separately — see
pre-flight).

---

### Scene 10 — [6:25–7:10] BEYOND THE BROWSER — the desktop command centre

**SCREEN:** Windows desktop → launch `dist\ASTRA\ASTRA.exe` (or installed Start Menu
shortcut). App opens to its **Operations** perspective with the paired live arena;
then click **Analysis**, then **Data & Sources**, then **Tools → Diagnostics**.

**ACTION:**
1. Double-click the ASTRA icon — window opens (record the launch; trim boot time in edit).
2. On Operations: point at the paired A/B panels.
3. Click **Analysis** (charts), **Data & Sources** (UDP/log/simulated source cards).
4. Open **Tools → Diagnostics** — all self-tests green.

**SAY:**
> The same engine ships as a native Windows command centre — no browser needed.
> Operations runs the paired live arena; Analysis holds the publication-grade
> statistics — Monte Carlo, KPP scoring, Holm-corrected comparisons; Data & Sources
> is where real hardware plugs in — a UDP stream of pulse descriptor words, a
> log-file tail, or the built-in simulated scene. Diagnostics re-runs the whole
> self-test suite on demand. One installer, offline, and the full manual is inside
> the app.

**ON-SCREEN:** captions per perspective — `Operations · live paired arena`,
`Analysis · statistics`, `Data & Sources · UDP PDW / log / simulated`;
chip — `ASTRA-Setup-2.0.0.exe · Windows 10/11 · offline`.

**EDIT:** Speed-ramp anything slower than 1× except the Diagnostics reveal. If the
launch has a window flash, cover it with a 6-frame brand wipe.

---

### Scene 11 — [7:10–7:40] THE HARDWARE ON-RAMP — from Python to FPGA

**SCREEN:** code view of `build/rtl/astra_policy_kernel.hpp` (fixed-point Q8.8 header)
— open in VS Code, dark theme — then one shot of a terminal running:
```powershell
python tools/pdw_generator.py --port 5555 --rate 400
```

**ACTION:**
1. Scroll slowly through the header's integer arithmetic (~8 lines).
2. Cut to terminal; run the generator; PDW counters tick.

**SAY:**
> And the decision kernel isn't locked in Python. The same arithmetic is exported as
> a header-only C++17 fixed-point kernel with a bounded-complexity contract — the
> on-ramp to FPGA and DSP, where dwell decisions happen in microseconds. On the
> input side, the UDP bridge already accepts real pulse descriptor words from an
> SDR or radar processor. Simulation to hardware is a port, not a rewrite.

**ON-SCREEN:** chips — `Q8.8 fixed point · O(bands) · contract-tested`,
`PDW schema: toa · freq · pw · pa · aoa`, `UDP ingest: tools/pdw_generator.py`.

**EDIT:** Static code shots die on camera — add 110 % slow drift-pan and a soft
keyboard texture under the VO only here.

---

### Scene 12 — [7:40–8:15] CLOSE — the one-line pitch

**SCREEN:** Back to `/console.html` → Live Mission, Flagship race mid-run (same state
as Scene 1 — record a fresh run so gold flashes are guaranteed).

**ACTION:**
1. No clicks — let both waterfalls run; cursor rests between the two panels.

**SAY:**
> Open-loop scanners *search*. ASTRA *anticipates*. Engine, tests, evidence, the
> desktop installer and the full documentation are in the repo — links in the
> description, and the console is live in your browser right now. If you're building
> Electronic Support systems, we'd love your feedback in the comments.

**ON-SCREEN:** end card over the footage — `ASTRA` wordmark · `github.com/RARPlayzDev/Astra`
· `astra-ew.vercel.app` · `306 tests · 13/13 PS checks · 96.9 % vs 54.1 %`.

**EDIT:** Music resolves on "anticipates" — let 2 s of waterfall run with no VO
before the end card. Fade to black over 12 frames.

---

## 4 · B-roll & stills to capture (10 extra minutes, saves hours in the edit)

| # | Shot | How |
|---|---|---|
| 1 | Waterfall close-up (gold intercepts) | Console, browser zoom 150 %, crop later |
| 2 | `phase-lock CONFIRMED` log line | Live Mission, Periodic hunter demo |
| 3 | Arena rising bars | Learning Arena → Train 5 |
| 4 | Shootout + probe tables | Model Lab → Run shootout |
| 5 | `ASTRA.exe` launch | double-click, record 10 s |
| 6 | Diagnostics all-green | Tools → Diagnostics |
| 7 | Terminal: `306 passed` | `python -m pytest tests -q` |
| 8 | Terminal: `npm run probe` printing the accuracy table | `website/` |
| 9 | Kernel header scroll | `build/rtl/astra_policy_kernel.hpp` |
| 10 | First-run cards + one spotlight highlight | fresh `localStorage` (Scene 5 alternate takes) |

**Still assets:** `assets/astra_mark_512.png` (logo), `figures/*.png` (publication
figures — usable as translucent backgrounds), the repo dark palette
(`#0d1420` bg · `#cfa453` gold · `#6f9ec7` steel-blue) — the editor should reuse
these exact hex values for all captions (see `VIDEO_EDITING.md`).

## 5 · YouTube metadata

**Titles (A/B test two):**
1. `ASTRA — an AI scan strategy that finds radars hiding 98% of the time (SIH 2026)`
2. `Open-loop sweeps search. This one anticipates. — ASTRA Electronic Support demo`

**Chapters (paste into description):**
```
0:00 The invisible radar (hook)
0:30 The problem: a 2-D search you can't brute-force
1:10 The loop: survey → learn → predict → position → rotate
1:50 Results first: the KPP gate
2:30 First-run onboarding in the console
3:15 Live A/B demo: ASTRA vs sequential sweep
4:30 Learning Arena: trained on hits and misses
5:10 Model Lab: 96.9% vs 54.1% (and the DQN that lost)
5:55 Documentation & evidence
6:25 Windows desktop command centre
7:10 Hardware on-ramp: fixed-point kernel + UDP PDW
7:40 Close
```

**Description skeleton:**
> ASTRA (Adaptive Spectrum Threat Recognition & Analysis) — an ML Electronic Support
> receiver scheduler that minimises intercept time without prior intelligence.
> Live console: https://astra-ew.vercel.app/console.html · Repo:
> https://github.com/RARPlayzDev/Astra · Windows installer:
> `ASTRA-Setup-2.0.0.exe` (Releases) · 306 automated tests · prediction accuracy
> 96.9% vs 54.1% sequential sweep (`npm run probe`) · results are seed-exact and
> reproducible. Simulation-based research prototype for Smart India Hackathon 2026 —
> not operational equipment.

**Tags:** `electronic warfare`, `electronic support`, `signal intelligence`, `radar
detection`, `spectrum awareness`, `Smart India Hackathon`, `SIH 2026`, `reinforcement
learning`, `smart scan`, `ASTRA`, `ES receiver`, `LPI radar`.

**Thumbnail:** split frame from Scene 6 — left waterfall sparse/grey labelled
`BLIND SWEEP · 54%`, right waterfall dense/gold labelled `ASTRA · 96.9%`; dark
`#0d1420` background, gold `#cfa453` for the ASTRA number only, one human element
(optional: your face bottom-right, surprised/proud, 15 % of frame). Max two text
elements — thumbnail text must be readable at 120 px wide.

## 6 · Optional: mapping to the 6-slide deck (offline pitch version)

If you must present with `ASTRA_SIH2026_Presentation.pptx` instead of the site, the
scenes map 1:1 — S1 hook = Scene 1+2 · S2 problem = Scene 2 · S3 architecture =
Scene 3+9 · S4 intelligence = Scene 7 (arena/phase-lock) · S5 results/demo = Scenes
6+8 · S6 roadmap = Scenes 10+11. Speaker notes for each slide already live in
`ppt.md` — use the same `SAY` text here for consistency between video and stage.

---

*Fact sheet re-verified: 306 tests collected (`pytest --collect-only`), probe numbers
from `website/scripts/pred_probe.ts`, benchmark numbers from `results/benchmark.json`
and `ppt.md`. Re-verify before re-recording after any engine change.*




