"""Tests for the teardown-v2 fidelity upgrades.

Covers the pulse-level ESM chain (deinterleaving, LPI matched filtering),
the analogue front-end impairment model, the interferometric AOA model,
scenario auto-calibration, the fixed-point real-time kernel (+ C++ export)
and the learned behaviour arbiter.  All deterministic (fixed seeds).
"""
import json
import sys
import pathlib

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ewsmart.config import ScenarioConfig
from ewsmart.environment import RFEnvironment, EmitterSpec
from ewsmart.receiver import ESReceiver
from ewsmart.deinterleave import (PDW, emit_pulse_train, interleave,
                                  deinterleave, deinterleave_accuracy,
                                  matched_filter_gain_db)
from ewsmart.frontend import FrontEnd, FrontEndSpec
from ewsmart.aoa import measure_aoa, cramer_rao_sigma_deg
from ewsmart.calibration import calibrate
from ewsmart.realtime import PolicyKernel, to_q, from_q
from ewsmart.meta import BehaviourArbiter
from ewsmart.runner import run_episode
from ewsmart.schedulers import SmartScanScheduler


def _specs():
    return [
        EmitterSpec(0, "stationary", 0, 12.0, True, freq_mhz=3500.0,
                    bearing_deg=30.0, pri_us=250.0, pw_us=2.0,
                    pri_kind="fixed"),
        EmitterSpec(1, "stationary", 0, 12.0, True, freq_mhz=6200.0,
                    bearing_deg=120.0, pri_us=97.0, pw_us=0.8,
                    pri_kind="staggered", stagger_levels=3),
        EmitterSpec(2, "stationary", 0, 12.0, False, freq_mhz=9100.0,
                    bearing_deg=250.0, pri_us=410.0, pw_us=5.0,
                    pri_kind="jittered", jitter_frac=0.12),
        EmitterSpec(3, "stationary", 0, 10.0, True, freq_mhz=14000.0,
                    bearing_deg=80.0, pri_us=600.0, pw_us=80.0,
                    pri_kind="fixed", waveform="lpi_fmcw", tb_product=400.0),
    ]


# ---------------------------------------------------------------------------
# Pulse-level deinterleaving
# ---------------------------------------------------------------------------
def test_deinterleave_recovers_all_pri_models():
    rng = np.random.default_rng(5)
    specs = _specs()
    stream = interleave([emit_pulse_train(s, 0, 20000.0, rng) for s in specs])
    acc = deinterleave_accuracy(stream, specs)
    assert acc["n_tracks"] == len(specs), "every emitter must be recovered"
    assert acc["fragmentation"] == pytest.approx(1.0)
    assert acc["pulse_purity"] == pytest.approx(1.0)
    assert acc["attributed_fraction"] == pytest.approx(1.0)
    # fixed PRIs must be recovered to <1%; the staggered mean interval to <5%
    assert acc["pri_rel_error_mean"] < 0.05
    assert acc["pri_kind_accuracy"] >= 0.75


def test_deinterleave_never_reads_ground_truth():
    """PRI estimation must be invariant to the scoring labels (no leakage)."""
    rng = np.random.default_rng(5)
    specs = _specs()
    stream = interleave([emit_pulse_train(s, 0, 20000.0, rng) for s in specs])
    base = [(t.pri_us, t.pri_kind) for t in deinterleave(stream)["tracks"]]
    # relabel every PDW's eid to the same value: the deinterleaver must
    # produce identical physics (only attribution changes).
    relabelled = [PDW(p.toa_us, p.freq_mhz, p.pw_us, p.pa_dbm, p.aoa_deg,
                      eid=7) for p in stream]
    same = [(t.pri_us, t.pri_kind) for t in deinterleave(relabelled)["tracks"]]
    assert base == same


def test_deinterleave_stagger_reports_mean_interval():
    """A staggered emitter's reported PRI is its mean interval (frame/k)."""
    rng = np.random.default_rng(5)
    spec = EmitterSpec(1, "stationary", 0, 12.0, True, freq_mhz=6200.0,
                       bearing_deg=120.0, pri_us=97.0, pw_us=0.8,
                       pri_kind="staggered", stagger_levels=3)
    tracks = deinterleave(interleave([emit_pulse_train(spec, 0, 20000.0,
                                                       rng)]))["tracks"]
    assert len(tracks) == 1
    assert tracks[0].pri_kind == "staggered"
    assert tracks[0].pri_us == pytest.approx(97.0, rel=0.02)


# ---------------------------------------------------------------------------
# LPI waveforms + matched filtering
# ---------------------------------------------------------------------------
def test_lpi_undetectable_without_matched_filter():
    cfg = ScenarioConfig(n_bands=8, T=2000, seed=9, n_stationary=0,
                         n_agile=0, n_periodic=0, n_spatial=0, n_clutter=0,
                         n_fhss=0, n_tdma=0, lpi_fraction=0.0)
    env = RFEnvironment(cfg)
    env.emitters = [EmitterSpec(0, "stationary", 3, -14.0, True,
                                freq_mhz=3000.0, bearing_deg=45.0,
                                pri_us=600.0, pw_us=80.0, waveform="lpi_fmcw",
                                tb_product=256.0)]
    env.band_seq = np.full((1, cfg.T), 3, dtype=np.int8)
    env.occupancy = np.ones((cfg.n_bands, cfg.T), dtype=np.int8)
    on = ESReceiver(env, seed=2)
    off = ESReceiver(env, seed=2)
    off._matched_filter = False
    assert matched_filter_gain_db(env.emitters[0]) == pytest.approx(
        24.08, abs=0.1)
    hits_on = sum(on.dwell(3, t).hit for t in range(300))
    hits_off = sum(off.dwell(3, t).hit for t in range(300))
    assert hits_on > 200, "matched filter must recover the LPI emitter"
    assert hits_off < 30, "without it the emitter stays buried below noise"


def test_lpi_emitters_are_negative_snr_in_the_scene():
    env = RFEnvironment(ScenarioConfig(n_bands=16, T=400, seed=3,
                                       lpi_fraction=1.0,
                                       lpi_tb_range=(256.0, 256.0)))
    lpi = [e for e in env.emitters if e.lpi]
    assert lpi, "the LPI fraction must produce LPI emitters"
    assert np.mean([e.snr_db for e in lpi]) < 0.0


# ---------------------------------------------------------------------------
# Analogue front-end impairments
# ---------------------------------------------------------------------------
def test_front_end_blanking_costs_integration_time():
    fe = FrontEnd(FrontEndSpec(settling_time_us=5.0))
    assert fe.blanked_time_us(1000.0, retuned=False) == 0.0
    assert fe.blanked_time_us(1000.0, retuned=True) == 5.0
    assert fe.effective_dwell_us(1000.0, retuned=True) == 995.0
    assert fe.effective_dwell_us(2.0, retuned=True) == 0.0


def test_front_end_linear_below_p1db_and_blocking_above():
    fe = FrontEnd(FrontEndSpec(p1db_dbm=-10.0))
    assert fe.noise_rise_db(-30.0) == 0.0, "linear region must be unperturbed"
    assert fe.noise_rise_db(-10.0) == 0.0
    assert fe.noise_rise_db(0.0) > 0.0
    assert fe.noise_rise_db(20.0) > fe.noise_rise_db(0.0)


def test_front_end_intermod_and_spurs():
    fe = FrontEnd(FrontEndSpec(ip3_dbm=0.0, lo_freq_mhz=2150.0))
    spurs = fe.intermod_spurs(3000.0, 3100.0)
    assert spurs == pytest.approx([2900.0, 3200.0])   # 2f1-f2 and 2f2-f1
    assert fe.intermod_level_dbm(-20.0) == pytest.approx(-60.0)
    resp = fe.spur_responses(3000.0)
    kinds = {(m, n) for m, n, _ in resp}
    assert (1, 2) in kinds and (2, 1) in kinds, "image + mixer spurs present"
    assert all(f > 0 for _, _, f in resp)


def test_front_end_adc_clipping():
    fe = FrontEnd(FrontEndSpec(adc_fullscale_dbm=5.0, sfdr_db=70.0))
    assert fe.clipping_spur_dbm(0.0) is None, "no clip below full scale"
    spur = fe.clipping_spur_dbm(15.0)
    assert spur is not None and spur < fe.adc_clip_dbm()


# ---------------------------------------------------------------------------
# Interferometric AOA
# ---------------------------------------------------------------------------
def test_aoa_error_follows_crlb_scaling():
    """Error must grow ~sqrt for 10 dB less SNR and stay small at high SNR."""
    e20 = np.mean([abs(((measure_aoa(45.0, 3000.0, 20.0,
                                        np.random.default_rng(11))[0]
                         - 45.0 + 180) % 360) - 180)
                   for _ in range(200)])
    e_m10 = np.mean([abs(((measure_aoa(45.0, 3000.0, -10.0,
                                         np.random.default_rng(11))[0]
                          - 45.0 + 180) % 360) - 180)
                     for _ in range(200)])
    assert e20 < 2.0, "high-SNR interferometry must be sub-degree accurate"
    assert e_m10 > e20, "weaker signals must be measured less precisely"
    assert (cramer_rao_sigma_deg(45.0, 3000.0, 0.0, 0.20)
            > cramer_rao_sigma_deg(45.0, 3000.0, 20.0, 0.20))


def test_aoa_unbiased_across_all_bearings():
    rng = np.random.default_rng(11)
    for brg in (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0):
        errs = [abs(((measure_aoa(brg, 3000.0, 20.0, rng)[0] - brg + 180)
                     % 360) - 180) for _ in range(150)]
        assert np.mean(errs) < 3.0, f"bearing {brg} must not be biased"


# ---------------------------------------------------------------------------
# Scenario auto-calibration
# ---------------------------------------------------------------------------
def test_calibration_reproduces_canonical_constants():
    c = calibrate(24, 3000, 25)
    assert c["recon_factor"] == 12
    assert c["burst_horizon"] == 480
    assert c["stale_revisit_factor"] == 6.0
    assert c["pursuit_budget"] == 6
    assert c["pursuit_window"] == 100
    assert c["hop_min_obs"] == 3
    assert c["lock_hits"] == 5
    assert c["exploit_ramp"] == pytest.approx(0.60)


def test_calibration_scales_with_spectrum_size():
    small = calibrate(8, 3000, 10)
    big = calibrate(128, 3000, 120)
    assert small["recon_factor"] < 12 < big["recon_factor"]
    assert big["pursuit_budget"] > small["pursuit_budget"]
    for key in ("recon_factor", "burst_horizon", "pursuit_budget",
                "hop_min_obs", "lock_hits"):
        assert 1 <= small[key] <= 5000
        assert 1 <= big[key] <= 5000


# ---------------------------------------------------------------------------
# Fixed-point real-time kernel
# ---------------------------------------------------------------------------
def test_kernel_matches_float_reference_argmax():
    """The Q8.8 kernel must pick the same band as the float score."""
    rng = np.random.default_rng(13)
    n = 12
    k = PolicyKernel(n)
    mismatches = 0
    for trial in range(200):
        t = int(rng.integers(50, 3000))
        mu = rng.normal(0.3, 0.2, n)
        visits = rng.uniform(1.0, 60.0, n)
        last = t - rng.integers(0, 400, n)
        unseen = visits < 1.5
        lprob = rng.uniform(0, 1, n)
        hop = np.maximum(0.0, rng.normal(0.2, 0.2, n))
        k.set_time(t)
        for b in range(n):
            k.set_value(b, mu[b])
            k.set_visits(b, visits[b])
            k.set_last_visit(b, int(last[b]))
            k.set_unseen(b, bool(unseen[b]))
            k.set_logit_prob(b, lprob[b])
            k.set_hop_bonus(b, hop[b])
        kernel_pick = k.step()
        recency = np.sqrt(np.maximum(0.0, t - last))
        score = (mu + 0.55 * np.sqrt(np.log(t + 2.0) / visits)
                 + (0.16 + 0.14 * unseen.astype(float)) * recency
                 + 0.35 * lprob + 0.45 * hop)
        if int(np.argmax(score)) != kernel_pick:
            mismatches += 1
    assert mismatches <= 4, (
        f"fixed-point kernel diverged from the float reference on "
        f"{mismatches}/200 random states (quantisation ties allowed)")


def test_kernel_metadata_is_a_real_contract():
    meta = PolicyKernel(24).metadata()
    assert meta["per_slot_complexity"] == "O(24) integer MACs"
    assert meta["dynamic_allocation"] is False
    assert meta["transcendentals_per_slot"] == 0


def test_cpp_kernel_export(tmp_path):
    from tools.export_cpp_kernel import export_kernel
    res = export_kernel(out_dir=tmp_path / "rtl", n_bands=24)
    text = res.header_path.read_text(encoding="utf-8")
    assert "class PolicyKernel" in text
    assert "int step()" in text
    assert "namespace astra" in text
    meta = json.loads(res.metadata_path.read_text(encoding="utf-8"))
    assert meta["dynamic_allocation"] is False
    assert meta["n_bands"] == 24


# ---------------------------------------------------------------------------
# Learned behaviour arbitration
# ---------------------------------------------------------------------------
def test_arbiter_learns_the_paying_behaviour():
    """Two-armed context: the arbiter must prefer the rewarded action."""
    rng = np.random.default_rng(3)
    ab = BehaviourArbiter(2, alpha=0.1, rng=rng)
    for _ in range(60):
        x = np.array([1.0, 0.5])
        pick = ab.choose(x, allowed=("pursue", "rotate"))
        reward = 1.0 if pick == "pursue" else -0.5
        ab.update(x, pick, reward)
    scores = ab.score(x)
    assert scores["pursue"] > scores["rotate"]
    assert ab.n_updates == 60


def test_arbiter_state_roundtrip_and_validation():
    ab = BehaviourArbiter(3)
    x = np.ones(3)
    ab.update(x, "survey", 1.0)
    state = ab.get_state()
    ab2 = BehaviourArbiter(3)
    ab2.set_state(state)
    assert ab2.n_updates == 1
    assert ab2.score(x) == ab.score(x)
    with pytest.raises(ValueError):
        ab.update(x, "teleport", 1.0)


def test_scheduler_trains_the_arbiter_from_live_dwells():
    env = RFEnvironment(ScenarioConfig(n_bands=12, T=1500, seed=90))
    s = SmartScanScheduler(12, seed=0)
    run_episode(env, s, seed=1)
    assert s.arbiter.n_updates > 150, (
        "shadow-mode arbitration must learn from behaviour outcomes "
        "(training is throttled to every 4th dwell for latency)")
    assert set(s.arbiter.score(np.ones(6))) <= {
        "pursue", "probe", "camp", "rotate", "survey"}
