# ASTRA — 7-Minute YouTube Video Script

**Runtime:** ~7:00 · **Tone:** confident, technical, zero hype that isn't backed by a
number · **All numbers in this script are measured** (repo evidence — see sources note
at the end). Speak at ~140 wpm; each block below is timed.

---

## [0:00 – 0:35] HOOK — the invisible radar
*(Screen: website console, Live Mission tab, waterfall running — blue cells flashing,
gold intercept flashes on the left panel only.)*

> A radar that transmits two percent of the time is effectively invisible to a
> conventional scanner — you have to be listening on the right frequency, at the right
> millisecond, and you have no idea which frequency that is. This is the core problem of
> Electronic Support. This is **ASTRA** — and in the next seven minutes I'll show you the
> engine, the learning, and the numbers behind it.

## [0:35 – 1:30] THE PROBLEM — a 2-D search you can't brute-force
*(Screen: Slide 2 diagram — spectrum 2–18 GHz → narrowband receiver → frequency×time grid.)*

> ES receivers can't monitor the whole spectrum at once — instantaneous bandwidth is at
> least an order of magnitude below the surveillance band. So interception becomes a
> two-dimensional search: adjust the receiver's frequency at the correct time. The old
> approach is open-loop: sweep the band, top to bottom, forever. It wastes dwell time on
> empty spectrum and it never *learns*. Hostile emitters are periodic, hopping, and
> evasive — they're designed to be found only by luck.

## [1:30 – 2:45] THE ENGINE — what's under the hood
*(Screen: Model Lab tab → scroll the architecture table; cut to repo tree briefly.)*

> ASTRA is a complete simulation-to-decision pipeline. A battlefield generator with a
> full ground-truth matrix — every emitter, every band, every slot. A receiver with real
> detection physics: CFAR false-alarm control, Albersheim's detection equation,
> time-bandwidth coupled sensitivity, LPI matched filtering, and a phase-interferometer
> angle-of-arrival model bounded by the Cramér–Rao limit. And on top: a scheduler with
> five behaviours — reconnaissance, Rayleigh phase-locking of periodic emitters, cued
> pursuit, predict-and-probe, and value-weighted rotation, with an online learned
> arbiter. Everything is trained on hits and misses, exactly as the problem statement
> demands.

## [2:45 – 4:00] LIVE DEMO — watch it learn
*(Screen: Live Mission tab. Start the "Flagship race" demo. Point at the two waterfalls.)*

> Here's the live mission. Two receivers, byte-identical battlefields. Left: ASTRA.
> Right: the classic sequential sweep. Watch the gold flashes — that's an intercept.
> The sweep covers everything and finds almost nothing. ASTRA surveys, locks onto the
> rhythm — see "phase-lock CONFIRMED" in the event log — and then arrives at the
> emitter's next window *before it turns on*. Threat coverage in the nineties versus
> half that for the sweep, and the threat time-to-first-fix tells the same story.

## [4:00 – 5:00] LEARNING ARENA — training across episodes
*(Screen: click Learning Arena tab. Hit "Train 5 episodes". Watch the trend bars.)*

> And because the problem statement says the model must be trained on hits and misses,
> there's a dedicated arena — deliberately isolated from the live mission, so
> experiments can't contaminate it. Five full episodes on five *fresh* battlefields,
> while the learner carries its consolidated memory forward. That rising bar chart is
> warm-starting: each new battlefield is conquered faster than the cold-start episode.
> Wipe the memory with one click if you want to start over.

## [5:00 – 5:50] THE NUMBERS — including the honest one
*(Screen: Model Lab tab — shootout table, then the probe verification table.)*

> In the Model Lab, every policy runs headlessly on the same battlefield. Prediction
> accuracy, scored honestly against ground truth: SmartScan 96.9 percent. Linear
> Q-learning 96.4. UCB 95.5. The sequential sweep? 54 — because when you have no model,
> your predictions are a coin flip. Now the honest part: we also built a full deep
> Q-network. It *lost* — under sparse, non-stationary rewards it underperformed even
> the blind sweep. We kept it in the repo as a documented negative result, because in
> electronic support you ship what survives the benchmark, not what looks good in the
> title.

## [5:50 – 6:30] BEYOND THE BROWSER — desktop app and hardware path
*(Screen: desktop app briefly — Operations page, paired arena; then the fixed-point
kernel header.)*

> The same engine ships as a Windows desktop command centre — FastAPI backend, paired
> live arena, analysis pages, a 306-test automated suite, and a 13-point self-audit
> endpoint that re-verifies problem-statement coverage live. The decision kernel is also
> exported as a fixed-point C++ header with a bounded-complexity contract — the on-ramp
> to FPGA hardware, where dwell decisions happen in microseconds.

## [6:30 – 7:00] CLOSE — the one-line pitch
*(Screen: Live Mission, waterfall racing, gold flashes.)*

> Open-loop scanners *search*. ASTRA *anticipates*. Engine, tests, evidence, and the
> full documentation are in the repo — links below. If you're building Electronic
> Support systems, we'd love your feedback in the comments.

---

### Production notes
- **Sources on screen** (tiny corner captions): "96.9 % vs 54.1 % — `npm run probe`",
  "306 tests — `pytest`", "13/13 — `/api/ps-coverage`".
- **B-roll list:** waterfall close-up; phase-lock log line; arena trend bars; shootout
  table; `dist/ASTRA/ASTRA.exe` launching; `kernel_export.hpp`.
- **Thumbnail idea:** split waterfall — empty grey sweep (left, "BLIND") vs gold-streaked
  SmartScan (right, "ANTICIPATING"), 96.9 % vs 54 % chips.
- **Chapters for the description:** 0:00 Hook · 0:35 The problem · 1:30 Engine ·
  2:45 Live demo · 4:00 Learning Arena · 5:00 The numbers · 5:50 Desktop & hardware ·
  6:30 Close.
