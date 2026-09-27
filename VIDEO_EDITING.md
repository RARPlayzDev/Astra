# ASTRA Video — Professional Editing Guide

Companion to `YOUTUBE_SCRIPT.md`. Follow this **in order** after you finish recording.
Everything here is tuned for one specific problem: making a **dark UI screen-recording
plus voice-over** look like a polished defence-product launch, not a Zoom recording.

---

## 1 · Tooling (pick one — all three can hit broadcast quality)

| Editor | Cost | Best for |
|---|---|---|
| **DaVinci Resolve 19 (Free)** | $0 | Best all-round: cut, color, audio, captions in one. Recommended. |
| **Premiere Pro** | subscription | If you already know it; best auto-captions |
| **CapCut Pro** | cheap | Fastest captions/shorts; weaker for precise zoom work |

**Project settings:** 1920×1080, **60 fps**, square pixels, Rec.709, 48 kHz audio.
Record/keep everything at 60 fps — the waterfall animation looks choppy at 30.

## 2 · The workflow (never skip the order)

1. **Assembly cut** — drop scenes 1→12 in order on V1, butt-joined. No transitions.
2. **VO sync** — put the voice track on A1 first, then trim the screen recording to
   match the words (picture follows audio, never the reverse).
3. **Dead-air pass** — razor at every breath/pause > 0.4 s; delete; ripple delete.
   Target: zero silent gaps longer than half a second outside Scene 12.
4. **B-roll pass** — layer the 10 B-roll shots from the script over any moment where
   the screen is static for > 4 s.
5. **Zoom/pan pass** — every `EDIT` note in the script; plus your own on each click.
6. **Graphics pass** — chips, lower-thirds, pull-quotes (style kit in §4).
7. **Sound pass** — VO chain, music bed, SFX (§5).
8. **Captions** — (§6).
9. **Color** — (§7).
10. **Export → re-watch at 1.5×** — if it drags at 1.5×, it drags at 1×. Fix, re-export.

## 3 · Cut rhythm for screen recordings

- **One idea = one shot.** If the cursor moves to a new UI region, that's a cut
  opportunity — cut rather than watch a 4-second cursor journey.
- **Zoom on arrival, not during travel:** cut to a version of the frame already
  zoomed (110–125 %) the moment the cursor arrives at its target. Reset to 100 %
  when the action moves on. This is the single biggest quality difference between
  amateur and pro screen recordings.
- **Hold minimums:** any text the viewer must read (KPI row, table, tooltip) needs
  ≥ 2.5 s on screen, ≥ 4 s if it's a full table.
- **Never show:** boot times, page loads, typing, DevTools, notifications. Speed
  ramp 2–4× through waits instead of cutting (a ramp reads as "this is fast",
  a cut reads as "something happened here").
- **Jump-cut vs zoom-cut:** on talking-headless footage always zoom-cut (change
  scale 3–5 % between adjacent clips) so straight cuts don't strobe.
- **Music bar alignment:** cut on the beat wherever the script allows — it's
  subconscious but it's why pro edits "click".

## 4 · Graphics style kit (match the product exactly)

Palette — taken from the site so graphics feel native to ASTRA:

| Use | Hex |
|---|---|
| Background / caption plates | `#05070b` at 85 % opacity |
| Primary accent (numbers, rings) | `#cfa453` gold |
| Secondary (labels, B-side) | `#6f9ec7` steel-blue |
| Body text | `#dfe6ee` |
| Fail/negative callouts | `#e05c5c` |

Rules:
- **Font:** one sans family only (Inter, IBM Plex Sans or Roboto). Titles 700,
  captions 400. Numbers in mono (IBM Plex Mono / JetBrains Mono) — matches the
  site's monospace readouts.
- **Stat chip:** 2-line lockup — big number (48–64 px gold) + tiny uppercase caption
  (16 px, letter-spaced, steel). Animate: 8-frame fade + 12 px rise, hold ≥ 2 s.
- **Spotlight callout** (for buttons the script says to point at): gold 3 px rounded
  rectangle around the control + thin leader line to a text plate. Animate the ring
  drawing in over 10 frames.
- **Cursor:** enlarge the recorded pointer 1.5× in the edit and add a soft gold
  halo; give every click a 6-frame white ripple. (If your recorder already does
  this, skip.)
- **Pull-quote** (`phase-lock CONFIRMED`): word-by-word reveal, mono font, gold
  left border — then delete it after 3 s so it doesn't cover the log.
- **Consistency beats variety:** same position (chips bottom-left, quotes
  top-center), same animation, every scene. No more than **two** graphic elements
  on screen at once.

## 5 · Sound design

**Voice chain (A1):** high-pass at 80 Hz → gentle EQ (+2 dB presence at 3–5 kHz) →
compressor 3:1, ~3 dB gain reduction → normalize to **-14 LUFS** integrated
(YouTube's target), peaks ≤ -1 dBTP.

**Music bed (A2):** dark/technical electronic or cinematic-minimal (YouTube Audio
Library → "cinematic" / "documentary" tags is a safe royalty-free pool). Ride it:
- Scenes 1, 6, 12 (peaks of the story): -26 LUFS under VO
- Dense-information scenes (4, 8, 9): -30 LUFS or drop out entirely
- Duck automatically under speech; **music must never be louder than 50 % of VO**
- Resolve the track exactly on the word "anticipates" in Scene 12

**SFX (A3) — use sparingly, max ~8 in the whole video:** soft tick on KPP pill
reveal, low riser into Scene 6, one impact hit on `IT LOST.` (Scene 8), whoosh on
the end-card fade. If you can hear the SFX as an event rather than feel it, it's
too loud (-20 dB is plenty).

## 6 · Captions

1. Auto-generate (Resolve: auto-captions; Premiere: speech-to-text; CapCut: auto).
2. Fix every technical term the auto-captions will butcher: ES receiver, SmartScan,
   phase-lock, Rayleigh, CFAR, dwell, TTFF, Holm-corrected, PDW, KPP.
3. Style: bottom-center, max 2 lines, 42 chars/line, 90 % black plate.
4. **Burn in** the hook (0:00–0:30) for silent autoplay feeds; leave the rest as a
   sidecar `.srt` for YouTube (enables the transcript panel + accessibility).
5. Time captions to phrases, not sentences.

## 7 · Color pass (dark-UI specific)

- The screen recording is already dark — your job is to **not crush it**: lift the
  blacks slightly (+2 IRE), keep shadows above 5 % so panel borders stay visible.
- Slight saturation boost (+8) so the gold intercepts pop against the blue cells —
  that contrast IS the video's story.
- One subtle vignette (-10 at corners) to focus attention; no teal-and-orange.
- Match B-roll (terminal shots, desktop app) to the web-console grade so cuts don't
  flicker brightness. Terminal whites: pull them to ~85 % so they don't flash.

## 8 · Export & upload

| Setting | Value |
|---|---|
| Codec | H.264 (or H.265 if you can wait) |
| Resolution / fps | 1920×1080 / 60 |
| Bitrate | VBR 2-pass, **16–20 Mbps** |
| Keyframe | 2 s |
| Audio | AAC 320 kbps, 48 kHz |
| Container | MP4 |

Watch the exported file end-to-end once — check: captions readable on a phone
(test at 25 % window size), gold visible on laptop brightness, no audio pops at
cuts, chapter timestamps in the description match the final edit (re-time them if
your assembly drifted).

## 9 · Publish package

- **Thumbnail** per `YOUTUBE_SCRIPT.md` §5 — create it in the same project at
  1280×720, export PNG (< 2 MB). Verify readable at 120 px wide.
- **Chapters** — first chapter must start at 0:00; format `MM:SS title`.
- **Pinned comment:** "Numbers are reproducible — `cd website && npm run probe`
  and `python -m pytest tests -q`. What would you benchmark next?" (drives comments).
- **Shorts cut:** Scene 6 condensed to 45 s (9:16 crop centered on the gold
  waterfall, burned captions, hook in first 2 s) — same edit, second export.

## 10 · Final QA checklist (tick every line before upload)

- [ ] No silent gap > 0.5 s (except the deliberate 2 s at the end)
- [ ] Every number spoken matches the script's fact sheet
- [ ] Every graphic uses only the palette in §4
- [ ] No personal info on screen (browser tabs, taskbar clock, filenames)
- [ ] Captions proofed for technical terms
- [ ] Music ducks under VO everywhere; total loudness ≈ -14 LUFS
- [ ] Chapters re-timed to the final cut
- [ ] Thumbnail tested at small size
- [ ] End card shows repo + live console URLs for ≥ 5 s

