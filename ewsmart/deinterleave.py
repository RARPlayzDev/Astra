"""Pulse-level PDW generation and deinterleaving (ESM signal-processing chain).

The scheduler-level simulator deliberately works on a discrete band/time grid,
because *scheduling* is the object of study there.  That abstraction, however,
skips the hardest task in a real Electronic Support receiver: a wideband
front-end receives an interleaved stream of pulses from every emitter in view
(at combat densities 10^5-10^6 pulses/second) and must separate that stream
back into individual emitters before anything can be tracked or identified.

This module adds that layer explicitly:

* :func:`emit_pulse_train` synthesises physically-parameterised pulse trains
  (PRI model, pulse width, RF, amplitude, angle of arrival) for one emitter
  during one dwell;
* :func:`interleave` builds the raw, unsorted PDW stream a receiver would see;
* :func:`deinterleave` recovers the constituent emitters with the classical
  pipeline - descriptor clustering on (RF, PW, AOA), then a difference-of-
  time-of-arrival (DTOA) histogram to find the dominant PRI with harmonic
  suppression, then a staggered/jittered discrimination test;
* :func:`deinterleave_accuracy` scores the result against ground truth.

The deinterleaver is strictly observation-only: ``PDW.eid`` exists for scoring
and is never read by the algorithm itself (asserted by a leakage test).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

PRI_MODELS = ("fixed", "staggered", "jittered")
WAVEFORMS = ("pulsed", "lpi_fmcw", "lpi_barker")


def matched_filter_gain_db(spec) -> float:
    """Coherent matched-filter processing gain of an emitter's waveform (dB).

    A Low Probability of Intercept waveform spreads its energy over a large
    time-bandwidth product ``B*T``; a receiver that correlates against the
    (unknown in detail, but class-matched) modulation collects up to
    ``10 log10(B*T)`` dB of coherent gain.  That is precisely why LPI radars
    can be detected at negative in-channel SNR *if* the receiver implements
    matched filtering or de-chirping - and why they stay invisible to a plain
    radiometer.  Returns 0 dB for conventional pulsed waveforms.
    """
    wf = str(getattr(spec, "waveform", "pulsed"))
    if not wf.startswith("lpi"):
        return 0.0
    tb = float(getattr(spec, "tb_product", 1.0) or 1.0)
    return 10.0 * math.log10(max(tb, 1.0))


@dataclass(frozen=True)
class PDW:
    """One measured Pulse Descriptor Word.

    ``eid`` is ground truth for scoring only; :func:`deinterleave` consumes
    :class:`PDW` objects but never inspects ``eid``.
    """

    toa_us: float
    freq_mhz: float
    pw_us: float
    pa_dbm: float
    aoa_deg: float
    eid: int | None = None

    def observable(self) -> tuple:
        """The five measured quantities (no ground truth in the tuple)."""
        return (self.toa_us, self.freq_mhz, self.pw_us, self.pa_dbm,
                self.aoa_deg)


@dataclass
class PulseTrain:
    """One deinterleaved emitter track recovered from a raw PDW stream."""

    n_pulses: int
    pri_us: float
    pri_kind: str
    pri_levels: tuple
    freq_mhz: float
    pw_us: float
    aoa_deg: float
    confidence: float
    eid_truth: int | None = None
    pulses: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"n_pulses": int(self.n_pulses),
                "pri_us": round(float(self.pri_us), 3),
                "pri_kind": self.pri_kind,
                "pri_levels": [round(float(x), 3) for x in self.pri_levels],
                "freq_mhz": round(float(self.freq_mhz), 2),
                "pw_us": round(float(self.pw_us), 4),
                "aoa_deg": round(float(self.aoa_deg), 2),
                "confidence": round(float(self.confidence), 3),
                "eid_truth": self.eid_truth}


def _pri_sequence(pri_us: float, kind: str, n: int, levels: int,
                  jitter_frac: float, rng: np.random.Generator) -> np.ndarray:
    """Sequence of pulse-to-pulse intervals for one PRI model."""
    if kind == "staggered":
        levels = max(2, int(levels))
        k = np.arange(n) % levels
        offsets = np.linspace(-1.0, 1.0, levels)
        return pri_us * (1.0 + 0.18 * offsets)[k]
    if kind == "jittered":
        j = max(0.0, float(jitter_frac))
        return pri_us * (1.0 + j * rng.uniform(-1.0, 1.0, n))
    return np.full(n, float(pri_us))


def emit_pulse_train(spec, t_start: int, dwell_us: float, rng,
                     slot_us: float = 1000.0) -> list[PDW]:
    """Synthesise one emitter's pulses during one dwell window.

    Args:
        spec: an :class:`ewsmart.environment.EmitterSpec`.
        t_start: slot index of the dwell start.
        dwell_us: dwell length in microseconds.
        rng: NumPy generator (deterministic under a fixed seed).
        slot_us: microseconds per simulation slot (default 1 slot = 1 ms).

    Returns:
        PDWs sorted by time of arrival, each carrying the emitter's
        ground-truth ``eid`` (for scoring only).
    """
    pri = float(getattr(spec, "pri_us", 100.0)) or 100.0
    kind = str(getattr(spec, "pri_kind", "fixed"))
    if kind not in PRI_MODELS:                      # pragma: no cover - guard
        kind = "fixed"
    levels = int(getattr(spec, "stagger_levels", 2))
    jitter = float(getattr(spec, "jitter_frac", 0.0))
    pw = max(1e-3, float(getattr(spec, "pw_us", 1.0)))
    snr_db = float(getattr(spec, "snr_db", 0.0))
    # Amplitude in dBm: peak power of the pulse as seen in-channel.  A pulsed
    # emitter concentrates its average power into the duty cycle pri/pw, so the
    # peak-to-average term is added to the in-channel SNR - the reason a
    # low-duty pulsed radar is detectable at a lower *average* power.
    pa_dbm = -120.0 + snr_db
    if str(getattr(spec, "waveform", "pulsed")) == "pulsed":
        pa_dbm += 10.0 * math.log10(max(pri / pw, 1.0))
    aoa = float(getattr(spec, "bearing_deg", 0.0)) % 360.0
    freq = float(getattr(spec, "freq_mhz", 0.0))
    n = max(1, int(dwell_us // pri))
    t0 = float(t_start) * slot_us + float(rng.uniform(0.0, pri))
    counts = n + 2
    intervals = _pri_sequence(pri, kind, counts, levels, jitter, rng)
    toas = t0 + np.cumsum(np.concatenate(([0.0], intervals)))[:counts]
    base = t_start * slot_us
    return [PDW(toa_us=float(toa), freq_mhz=freq, pw_us=pw, pa_dbm=pa_dbm,
                aoa_deg=aoa, eid=int(spec.eid))
            for toa in toas if 0.0 <= toa - base < dwell_us]


def interleave(train_lists, max_pulses: int | None = None) -> list[PDW]:
    """Build the raw PDW stream a receiver sees (time-ordered, unsorted ids).

    Args:
        train_lists: iterable of per-emitter PDW lists.
        max_pulses: optional density cap emulating front-end throughput
            saturation (pulses beyond the cap are dropped at the receiver).
    """
    stream = [p for tr in train_lists for p in tr]
    stream.sort(key=lambda p: p.toa_us)
    if max_pulses is not None and len(stream) > max_pulses:
        stream = stream[:int(max_pulses)]
    return stream


def _cluster_pdws(pdws: list[PDW], rf_tol_mhz: float = 2.0,
                  pw_tol_frac: float = 0.25,
                  aoa_tol_deg: float = 8.0) -> list[list[PDW]]:
    """Separate a raw stream into emitter candidates by measured descriptors.

    Sequential agglomeration: the stream is sorted by RF, then split wherever
    RF, pulse width or AOA jumps beyond tolerance.  Descriptor separation is
    what makes deinterleaving tractable at all - emitters that agree on RF,
    PW *and* AOA are, by construction of the models above, the same track.
    """
    if not pdws:
        return []
    pts = sorted(pdws, key=lambda p: (p.freq_mhz, p.toa_us))
    groups: list[list[PDW]] = [[pts[0]]]
    ref_rf, ref_pw = pts[0].freq_mhz, max(pts[0].pw_us, 1e-3)
    ref_aoa = pts[0].aoa_deg
    for p in pts[1:]:
        pw_tol = pw_tol_frac * max(ref_pw, 1e-3)
        d_aoa = abs((p.aoa_deg - ref_aoa + 180.0) % 360.0 - 180.0)
        if (abs(p.freq_mhz - ref_rf) > rf_tol_mhz
                or abs(p.pw_us - ref_pw) > pw_tol
                or d_aoa > aoa_tol_deg):
            groups.append([p])
            ref_rf, ref_pw = p.freq_mhz, max(p.pw_us, 1e-3)
            ref_aoa = p.aoa_deg
        else:
            g = groups[-1]
            g.append(p)
            ref_rf = float(np.mean([q.freq_mhz for q in g]))
            ref_pw = float(np.mean([max(q.pw_us, 1e-3) for q in g]))
            ref_aoa = float(np.mean([q.aoa_deg for q in g]))
    return groups


def _dtoa_histogram(times: np.ndarray, bin_us: float,
                    max_dtoa_us: float) -> tuple:
    """All-pairs difference-of-time-of-arrival histogram.

    The classical first stage of PRI estimation: for a periodic emitter every
    DTOA equal to the PRI (or one of its multiples) accumulates counts, so the
    true PRI appears as a peak that reinjection noise cannot fake.
    """
    diffs = []
    for i in range(times.size):
        hi = int(np.searchsorted(times, times[i] + max_dtoa_us, side="right"))
        if hi > i + 1:
            diffs.append(times[i + 1:hi] - times[i])
    if not diffs:
        return np.zeros(0), np.zeros(0)
    d = np.concatenate(diffs)
    edges = np.arange(bin_us, max_dtoa_us + bin_us, bin_us)
    hist, edges = np.histogram(d, bins=edges)
    return hist.astype(float), edges


def _phase_entropy(times: np.ndarray, pri_us: float, nbins: int = 16) -> float:
    """Shannon entropy of the arrival-phase histogram folded at ``pri_us``.

    Low entropy means the arrivals concentrate into a few phase modes, i.e.
    the period is (close to) correct.  Used as the objective for period
    sharpening because it is agnostic to *how many* modes there are.
    """
    if pri_us <= 0:
        return float("inf")
    ph = (times / pri_us) % 1.0
    counts, _ = np.histogram(ph, bins=nbins, range=(0.0, 1.0))
    pr = counts.astype(float)
    pr /= max(pr.sum(), 1.0)
    pr = pr[pr > 0]
    return float(-(pr * np.log(pr)).sum())


def _refine_pri(times: np.ndarray, pri0: float, iters: int = 3) -> float:
    """Coarse-to-fine PRI refinement by repeated local DTOA zooming.

    The first histogram is necessarily coarse (one bin width across the whole
    observation span), which is far too wide to fold phases against.  Each
    iteration re-histograms only the +/-25% neighbourhood of the current
    estimate with a bin width two orders of magnitude finer, so the estimate
    converges onto the true interval to within a fraction of a microsecond.
    """
    p = float(pri0)
    for _ in range(iters):
        lo, hi = 0.75 * p, 1.25 * p
        if not np.isfinite(p) or p <= 0 or hi <= lo:
            return max(p, 0.0)
        bin_us = max((hi - lo) / 200.0, 0.02)
        hist, edges = _dtoa_histogram(times, bin_us, hi)
        if hist.size == 0:
            return p
        centres = edges[:-1] + 0.5 * np.diff(edges)
        mask = (centres >= lo) & (centres <= hi)
        if not mask.any() or float(hist[mask].max()) <= 0:
            return p
        idx = int(np.flatnonzero(mask)[int(np.argmax(hist[mask]))])
        p = float(centres[idx])
    # Period sharpening by phase-histogram entropy minimisation.  A correct
    # period folds the arrivals onto a few tight phase modes (low entropy);
    # a slightly wrong one smears them across all bins.  The scan is wide and
    # logarithmic first - the coarse DTOA peak can sit on any harmonic or
    # sub-multiple of the true period, so the search must be free to move by
    # whole factors, not percentages - then it narrows for precision.
    if p > 0 and times.size >= 6:
        # Physical lower bound: the mean interval can never be smaller than
        # the smallest observed gap between consecutive pulses, so the search
        # must not collapse onto degenerate sub-multiple periods.
        min_gap = float(np.min(np.diff(times))) if times.size > 1 else 0.0
        lo = max(p / 10.0, 0.98 * min_gap)
        hi = p * 3.0
        if hi > lo:
            grid = np.exp(np.linspace(np.log(lo), np.log(hi), 300))
            best_p, best_h = p, _phase_entropy(times, p)
            for cand in grid:
                h = _phase_entropy(times, cand)
                if h < best_h - 1e-12:
                    best_h, best_p = h, float(cand)
            p = best_p
        for span_frac, n_grid in ((0.03, 81), (1e-3, 81)):
            grid = np.linspace(p * (1.0 - span_frac), p * (1.0 + span_frac),
                               n_grid)
            best_p, best_h = p, _phase_entropy(times, p)
            for cand in grid:
                h = _phase_entropy(times, cand)
                if h < best_h - 1e-12:
                    best_h, best_p = h, float(cand)
            p = best_p
    return p


def _estimate_pri(times: np.ndarray, pri_hint_us: float | None = None
                  ) -> tuple | None:
    """Estimate ``(pri_us, kind, levels, confidence)`` from pulse times.

    Pipeline: DTOA histogram -> lowest significant peak with sub-multiple
    (harmonic) preference -> median refinement -> circular-concentration test
    that decides fixed / staggered / jittered.

    Returns ``None`` when the cluster is too small or shows no periodicity.
    """
    t = np.sort(np.asarray(times, dtype=float))
    if t.size < 4:
        return None
    span = float(t[-1] - t[0])
    if span <= 0:
        return None
    hint = float(pri_hint_us) if pri_hint_us and pri_hint_us > 0 else None
    max_dtoa = min(span, hint * 4.0 if hint else span)
    if max_dtoa <= 0:
        return None
    bin_us = max(max_dtoa / 600.0, 0.05)
    hist, edges = _dtoa_histogram(t, bin_us, max_dtoa)
    if hist.size == 0 or hist.max() <= 0:
        return None
    centres = edges[:-1] + 0.5 * np.diff(edges)
    thresh = 0.45 * float(hist.max())
    peaks = [i for i in range(1, hist.size - 1)
             if hist[i] >= thresh and hist[i] >= hist[i - 1]
             and hist[i] >= hist[i + 1]]
    if not peaks:
        return None
    strongest = max(peaks, key=lambda j: hist[j])
    # Candidate acceptance sweep, smallest first: a peak is accepted as the
    # fundamental when folding the arrivals at it yields either a single tight
    # phase (fixed PRI) or two-to-four balanced tight phases (staggered PRI,
    # in which case the peak is the *frame* period and the reported PRI is the
    # mean interval frame/k - the quantity a real PRI estimator reports).
    chosen: tuple | None = None
    for i in sorted(peaks, key=lambda j: centres[j]):
        p = _refine_pri(t, float(centres[i]))
        if p < 2.0 * bin_us:
            continue
        kind, levels, r_conc, k = _classify_pri_model(t, p)
        if kind == "staggered" and k >= 2 and p / k >= 2.0 * bin_us:
            chosen = (p / k, "staggered", levels, r_conc)
            break
        if kind == "fixed" and r_conc >= 0.90 and t.size >= 6:
            chosen = (p, "fixed", (), r_conc)
            break
    if chosen is None:
        p = _refine_pri(t, float(centres[strongest]))
        kind, levels, r_conc, _k = _classify_pri_model(t, p)
        chosen = (p, kind, levels, r_conc)
    accepted, kind_out, levels_out, r_out = chosen
    if accepted <= 0:
        return None
    # Polish: the median of the raw DTOAs just around the accepted interval.
    diffs = []
    for i in range(t.size):
        hi_ = int(np.searchsorted(t, t[i] + 1.2 * accepted, side="right"))
        if hi_ > i + 1:
            diffs.append(t[i + 1:hi_] - t[i])
    if diffs:
        d = np.concatenate(diffs)
        near = d[(d > 0.8 * accepted) & (d < 1.2 * accepted)]
        if near.size >= 3:
            accepted = float(np.median(near))
    conf = float(np.clip(r_out * min(1.0, t.size / 30.0), 0.0, 1.0))
    return accepted, kind_out, levels_out, conf


def _classify_pri_model(t: np.ndarray, pri_us: float) -> tuple:
    """Decide fixed / staggered / jittered from the circular phase of arrivals.

    A fixed PRI folds every pulse onto one phase (high circular
    concentration).  A staggered PRI folds onto two to four tight, well
    populated phase clusters (the fold period is then the stagger *frame*).
    A jittered PRI spreads but stays unimodal.

    Returns ``(kind, levels, r_conc, n_levels)``.
    """
    phase = (t / pri_us) % 1.0
    r_conc = float(np.abs(np.mean(np.exp(2j * np.pi * phase))))
    ph = np.sort(phase)
    kind, levels, n_levels = "fixed", (), 1
    if r_conc < 0.94 and t.size >= 8:
        # Rotate so the LARGEST circular gap becomes the wrap boundary: no
        # cluster then straddles the 0/1 edge and the wrap itself cannot
        # manufacture a spurious one-element "cluster".
        gaps_full = np.diff(np.concatenate((ph, [ph[0] + 1.0])))
        rot = int(np.argmax(gaps_full))
        ph = np.roll(ph, -(rot + 1))
        ph = ph - ph[0]
        gaps = np.diff(ph)
        cuts = np.flatnonzero(gaps > 0.12)
        if 1 <= len(cuts) <= 3:
            idx = np.concatenate((cuts, [ph.size]))
            clusters, start = [], 0
            for end in idx:
                seg = ph[start:end]
                if seg.size:
                    clusters.append(seg)
                start = end
            if len(clusters) >= 2:
                weights = [c.size / ph.size for c in clusters]
                spreads = [float(np.std(c)) for c in clusters]
                # Stagger clusters must be balanced and tight (a jittered
                # train folded at a near-mean interval also splits, but its
                # parts are broad and unequal).
                if min(weights) >= 0.15 and max(spreads) <= 0.06:
                    kind = "staggered"
                    n_levels = len(clusters)
                    levels = tuple(sorted(float(np.mean(c))
                                          for c in clusters))
    if kind == "fixed" and r_conc < 0.97 and t.size >= 8:
        if float(np.std(ph - 0.5)) > 0.02:
            kind = "jittered"
    return kind, levels, r_conc, n_levels


def deinterleave(stream: list[PDW], min_pulses: int = 6) -> dict:
    """Recover individual emitters from a raw interleaved PDW stream.

    Strictly observation-only: ``PDW.eid`` is never read here - it is only
    propagated onto the recovered track so callers can score the result
    (:func:`deinterleave_accuracy`).

    Returns:
        ``{"tracks": [PulseTrain], "n_pulses": int, "n_clusters": int}``.
        Clusters too small or too irregular to show periodicity are still
        reported as tracks with ``pri_kind = "aperiodic"`` so pulse
        attribution (which drives intercept credit) is not silently lost.
    """
    clusters = _cluster_pdws(stream)
    tracks: list[PulseTrain] = []
    for cl in clusters:
        if len(cl) < min_pulses:
            continue
        times = np.asarray([p.toa_us for p in cl], dtype=float)
        est = _estimate_pri(times)
        counts: dict = {}
        for p in cl:
            counts[p.eid] = counts.get(p.eid, 0) + 1
        majority = max(counts, key=counts.get) if counts else None
        if est is None:
            pri, kind, levels, conf = 0.0, "aperiodic", (), 0.0
        else:
            pri, kind, levels, conf = est
        tracks.append(PulseTrain(
            n_pulses=len(cl), pri_us=float(pri), pri_kind=kind,
            pri_levels=levels,
            freq_mhz=float(np.mean([p.freq_mhz for p in cl])),
            pw_us=float(np.mean([p.pw_us for p in cl])),
            aoa_deg=float(np.mean([p.aoa_deg for p in cl])),
            confidence=conf, eid_truth=majority, pulses=list(cl)))
    return {"tracks": tracks, "n_pulses": len(stream),
            "n_clusters": len(clusters)}


def deinterleave_accuracy(stream: list[PDW], specs) -> dict:
    """Score a deinterleaving result against ground-truth emitter specs.

    Reported figures of merit:

    * ``pulse_purity`` - mean fraction of a track's pulses that really belong
      to its majority emitter (1.0 = no pulses mis-assigned);
    * ``fragmentation`` - recovered tracks per truth emitter (1.0 = each
      emitter recovered exactly once);
    * ``pri_rel_error_mean`` - mean relative PRI error over periodic emitters;
    * ``pri_kind_accuracy`` - fraction of tracks whose PRI *model* (fixed /
      staggered / jittered) was classified correctly;
    * ``attributed_fraction`` - fraction of all pulses credited to the right
      emitter.
    """
    res = deinterleave(stream)
    tracks = res["tracks"]
    spec_by_eid = {int(getattr(s, "eid", -1)): s for s in specs}
    purity, pri_errs, kind_ok, kind_n = [], [], 0, 0
    attributed = total = 0
    for tr in tracks:
        counts: dict = {}
        for p in tr.pulses:
            counts[p.eid] = counts.get(p.eid, 0) + 1
            total += 1
        if counts:
            maj = max(counts, key=counts.get)
            purity.append(counts[maj] / len(tr.pulses))
            attributed += counts[maj]
        spec = spec_by_eid.get(tr.eid_truth)
        if spec is None:
            continue
        true_pri = float(getattr(spec, "pri_us", 0.0) or 0.0)
        true_kind = str(getattr(spec, "pri_kind", "fixed"))
        if true_pri > 0 and tr.pri_kind != "aperiodic":
            pri_errs.append(abs(tr.pri_us - true_pri) / true_pri)
        kind_n += 1
        kind_ok += int(tr.pri_kind == true_kind)
    n_truth = max(1, len(spec_by_eid))
    return {
        "n_truth_emitters": len(spec_by_eid),
        "n_tracks": len(tracks),
        "n_pulses": res["n_pulses"],
        "fragmentation": round(len(tracks) / n_truth, 3),
        "pulse_purity": round(float(np.mean(purity)), 4) if purity else None,
        "attributed_fraction": round(attributed / max(1, total), 4),
        "pri_rel_error_mean": (round(float(np.mean(pri_errs)), 4)
                               if pri_errs else None),
        "pri_kind_accuracy": (round(kind_ok / kind_n, 3) if kind_n else None),
        "tracks": [t.as_dict() for t in tracks],
    }