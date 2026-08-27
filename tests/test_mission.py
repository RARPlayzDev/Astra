"""Mission Effectiveness scoring: KPP gating, ranking, gated episode arrays."""
import json
import pathlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ewsmart.metrics import gated_mes_episodes, mission_scores  # noqa: E402


def _flat(**over):
    base = {
        "avg_reward": 0.4,
        "threat_intercept_ratio": 0.95,
        "pct_correct_predictions": 0.6,
        "false_alarm_rate": 1e-4,
        "intercept_rate": 0.6,
        "avg_intercept_time_error": 40.0,
    }
    base.update(over)
    return base


def test_kpp_gate_disqualifies_low_coverage():
    out = mission_scores({
        "good": _flat(),
        "exploiter": _flat(threat_intercept_ratio=0.54, avg_reward=0.9),
    })
    assert out["ranking"][0] == "good"
    assert out["scores"]["good"]["mission_capable"]
    assert not out["scores"]["exploiter"]["mission_capable"]


def test_kpp_gate_disqualifies_poor_predictor():
    out = mission_scores({
        "good": _flat(),
        "blind": _flat(pct_correct_predictions=0.19, avg_reward=0.5),
    })
    assert out["scores"]["blind"]["mission_capable"] is False
    assert not out["scores"]["blind"]["kpps"]["pct_correct_predictions"]["pass"]


def test_ranking_prefers_capable_over_higher_mes():
    # exploiter has a higher raw MES but fails the coverage KPP
    out = mission_scores({
        "smart": _flat(),
        "ucb": _flat(threat_intercept_ratio=0.54, avg_reward=2.0),
    })
    assert out["ranking"] == ["smart", "ucb"]


def test_gated_episodes_zero_out_kpp_failures():
    per_ep = {
        "a": [dict(_flat(), threat_intercept_ratio=0.95) for _ in range(4)],
        "b": [dict(_flat(), threat_intercept_ratio=0.95) for _ in range(3)]
             + [dict(_flat(), threat_intercept_ratio=0.10)],
    }
    gated = gated_mes_episodes(per_ep)
    assert gated["b"][-1] == 0.0            # failed KPP -> zero credit
    assert gated["a"].min() > 0.0           # always capable -> positive
    assert len(gated["a"]) == len(gated["b"]) == 4


def test_nonfinite_inputs_are_tolerated():
    out = mission_scores({"x": dict(_flat(), avg_intercept_time_error=None)})
    assert np.isfinite(out["scores"]["x"]["mes"])


def test_real_suite_ranks_smartscan_first():
    path = Path("results") / "suite_results.json"
    if not path.exists():
        return  # suite not generated yet; unit tests above cover the logic
    mc_raw = json.loads(path.read_text(encoding="utf-8"))["monte_carlo"]
    flat = {n: {k: v["mean"] for k, v in d.items()} for n, d in mc_raw.items()}
    me = mission_scores(flat)
    assert me["ranking"][0] == "smart-scan"
    assert me["scores"]["smart-scan"]["mission_capable"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
