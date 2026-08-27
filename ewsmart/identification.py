"""Emitter identification: match measured PDW fingerprints against a library.

Implements the classic Electronic Support chain *intercept -> classify ->
identify*.  The library ships with illustrative class profiles inspired by
public-domain references (JC Wise, Radar Emitter Database, 2024; NATO
reporting names).  Ranges are intentionally coarse class descriptions - this
is a demonstration matcher, not an operational ELINT database.

A *fingerprint* is the measurable set {centre frequency, frequency spread,
pulse width, scan period}.  :func:`identify` scores a fingerprint against
every library entry and returns the best match with a confidence.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import periodic


@dataclass(frozen=True)
class LibraryEntry:
    """One emitter class in the identification library.

    Attributes:
        name: display name (NATO-style reporting name).
        cls: role/class description.
        freq_range_mhz: (lo, hi) operating band in MHz.
        pw_range_us: (lo, hi) pulse width in microseconds.
        scan_period_range: (lo, hi) antenna rotation period in slots, or None
            for non-scanning classes.
        threat_level: "HIGH" | "MEDIUM" | "LOW".
    """

    name: str
    cls: str
    freq_range_mhz: tuple
    pw_range_us: tuple
    scan_period_range: tuple | None
    threat_level: str


def build_default_library() -> list[LibraryEntry]:
    """Illustrative public-domain class profiles covering 2-18 GHz."""
    return [
        LibraryEntry("SNOW DRIFT", "S-band acquisition radar",
                     (2800.0, 3300.0), (0.5, 4.0), (40, 200), "HIGH"),
        LibraryEntry("FLAT FACE", "L-band search radar",
                     (1800.0, 2400.0), (0.8, 6.0), (60, 250), "MEDIUM"),
        LibraryEntry("POP GROUP", "E/F-band acquisition + tracking",
                     (4800.0, 6200.0), (0.3, 3.0), (30, 150), "MEDIUM"),
        LibraryEntry("FLAP LID-A", "X-band engagement radar",
                     (8600.0, 10200.0), (0.8, 8.0), (20, 120), "HIGH"),
        LibraryEntry("SQUARE PAIR", "X-band missile guidance",
                     (8800.0, 9600.0), (0.2, 2.0), None, "HIGH"),
        LibraryEntry("BIG BACK", "Ku-band maritime surveillance",
                     (12000.0, 14500.0), (1.0, 20.0), (25, 160), "MEDIUM"),
        LibraryEntry("CROSS SLOT", "X-band navigation radar",
                     (8800.0, 9800.0), (0.05, 1.2), (40, 200), "LOW"),
        LibraryEntry("HALF PLATE", "Ku-band height finder",
                     (12500.0, 13500.0), (2.0, 12.0), (15, 90), "HIGH"),
        LibraryEntry("TIN SHIELD", "S-band long-range search",
                     (2600.0, 3400.0), (3.0, 25.0), (100, 400), "HIGH"),
        LibraryEntry("LONG TRACK", "E-band search radar",
                     (2400.0, 2900.0), (1.0, 10.0), (80, 300), "MEDIUM"),
    ]


@dataclass
class Fingerprint:
    """Measured fingerprint of one emitter stream."""

    freq_center_mhz: float
    freq_span_mhz: float
    pw_mean_us: float
    scan_period: float | None
    n_pulses: int


def fingerprint_pdws(pdws: list[dict]) -> Fingerprint | None:
    """Build a fingerprint from a stream of PDW dicts (>= 3 pulses)."""
    if len(pdws) < 3:
        return None
    freqs = np.array([float(p["freq_mhz"]) for p in pdws])
    pws = np.array([float(p.get("pw_us", 1.0)) for p in pdws])
    toas = np.array(sorted(float(p["toa_us"]) for p in pdws))
    scan = None
    est = periodic.best_period(toas)
    if est is not None:
        scan = float(est["period"])
    return Fingerprint(
        freq_center_mhz=float(freqs.mean()),
        freq_span_mhz=float(freqs.std() * 2.0),
        pw_mean_us=float(pws.mean()),
        scan_period=scan,
        n_pulses=len(pdws),
    )


def _score_range(value: float, rng: tuple | None, slack: float = 0.15) -> float:
    if rng is None:
        return 1.0
    lo, hi = rng
    span = hi - lo
    if span == 0:
        return 1.0 if value == lo else 0.0
        
    if lo <= value <= hi:
        # Center bonus to gracefully break ties
        center = (lo + hi) / 2.0
        dist_to_center = abs(value - center)
        max_dist = span / 2.0
        bonus = 0.05 * (1.0 - (dist_to_center / max_dist)) if max_dist > 0 else 0.05
        return 1.0 + bonus
        
    dist = lo - value if value < lo else value - hi
    max_dist = span * slack
    if max_dist > 0 and dist <= max_dist:
        return 1.0 - (dist / max_dist)
    return 0.0


def identify(fp: Fingerprint, library: list[LibraryEntry]) -> tuple:
    """Return ``(entry, confidence)`` for the best-matching library class.

    Confidence is the mean of per-feature membership indicators with
    frequency double-weighted.  Returns ``(None, 0.0)`` when nothing
    plausible matches.
    """
    best, best_score = None, 0.0
    for e in library:
        freq_score = _score_range(fp.freq_center_mhz, e.freq_range_mhz, slack=0.05)
        if freq_score == 0.0:
            continue
        pw_score = _score_range(fp.pw_mean_us, e.pw_range_us, slack=0.15)
        
        weight = 3.0
        scan_score = 0.0
        
        if fp.scan_period is not None:
            weight = 4.0
            if e.scan_period_range is not None:
                scan_score = _score_range(fp.scan_period, e.scan_period_range, slack=0.35)
            else:
                scan_score = 0.0
        else:
            if e.scan_period_range is not None:
                if fp.n_pulses < 5:
                    # Sparse intercept, might be scanning. Neutral weight.
                    weight = 3.0
                else:
                    # Many pulses, no period -> not scanning -> mismatch
                    weight = 4.0
                    scan_score = 0.0
            else:
                if fp.n_pulses < 5:
                    weight = 3.0
                else:
                    weight = 4.0
                    scan_score = 1.0
            
        score = (2.0 * freq_score + pw_score + scan_score) / weight
        
        # Tie breaker: narrower frequency range (more specific class) wins
        if e.freq_range_mhz is not None:
            span = e.freq_range_mhz[1] - e.freq_range_mhz[0]
            score += (1.0 / (span + 1.0)) * 0.001
            
        if score > best_score:
            best, best_score = e, score
            
    if best is None or best_score < 0.5:
        return None, 0.0
    return best, float(min(1.0, best_score))


def tag_environment(env, library: list[LibraryEntry] | None = None) -> dict:
    """Attach ground-truth library identities to environment emitters.

    Returns ``{eid: entry_or_None}``.  Emitters whose parameters fall outside
    every library profile are tagged ``None`` (genuinely unknown).
    """
    library = library or build_default_library()
    identities = {}
    for e in env.emitters:
        fp = Fingerprint(freq_center_mhz=e.freq_mhz, freq_span_mhz=0.0,
                         pw_mean_us=e.pw_us,
                         scan_period=(float(e.period)
                                      if e.kind in ("periodic", "spatial")
                                      else None),
                         n_pulses=100)
        entry, _ = identify(fp, library)
        identities[e.eid] = entry
    env.identities = identities
    return identities


def identification_report(env, detected_streams: dict, library=None) -> dict:
    """Identify detected streams and score against ground truth.

    Args:
        env: environment previously tagged with :func:`tag_environment`.
        detected_streams: ``{eid: [pdw, ...]}`` measured per emitter.
        library: optional custom library.

    Returns:
        Dict with per-stream rows and overall accuracy over taggable emitters.
    """
    library = library or build_default_library()
    rows, correct, taggable = [], 0, 0
    for eid, pdws in sorted(detected_streams.items()):
        fp = fingerprint_pdws(pdws)
        if fp is None:
            continue
        entry, conf = identify(fp, library)
        truth = getattr(env, "identities", {}).get(eid)
        truth_name = truth.name if truth else "UNKNOWN"
        got_name = entry.name if entry else "UNKNOWN"
        if truth is not None:
            taggable += 1
            correct += int(got_name == truth_name)
        rows.append({
            "eid": eid, "band": int(pdws[0].get("_band", -1)),
            "identified": got_name,
            "class": entry.cls if entry else "-",
            "threat": entry.threat_level if entry else "-",
            "confidence": round(conf, 2),
            "pulses": fp.n_pulses,
            "ground_truth": truth_name,
            "correct": got_name == truth_name,
        })
    return {"rows": rows,
            "accuracy": correct / max(1, taggable),
            "n_identified": sum(1 for r in rows if r["identified"] != "UNKNOWN"),
            "n_streams": len(rows)}


def streams_from_env_detections(env, trace) -> dict:
    """Group a trace's true detections into per-emitter PDW streams."""
    streams: dict[int, list[dict]] = {}
    for t, (b, hit, fa) in enumerate(zip(trace.actions, trace.hits,
                                         trace.false_alarms)):
        if not hit or fa:
            continue
        for e in env.emitters_at(b, t):
            streams.setdefault(e.eid, []).append({
                "toa_us": t * 1000.0,
                "freq_mhz": e.freq_mhz,
                "pw_us": e.pw_us,
                "pa_db": e.snr_db,
                "aoa_deg": e.bearing_deg,
                "_band": b,
            })
    return streams

