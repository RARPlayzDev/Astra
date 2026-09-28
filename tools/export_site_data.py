"""Bake evaluation results into the website (single source of truth).

Reads ``results/suite_results.json`` (and ``results/benchmark.json`` when
present) and projects them into ``website/public/data/results.json`` in the
exact shape the website expects, plus copies the regenerated figures and the
user manual into ``website/public``.  No headline number is ever hand-edited:
everything the site shows comes from a generated artifact.

Usage (from the repository root):
    python tools/export_site_data.py [--suite results/suite_results.json]
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_site_data(suite: dict, bench: dict | None) -> dict:
    """Project suite/benchmark artifacts into the website data shape."""
    mc = suite["monte_carlo"]
    out = {
        "monte_carlo_means": {
            n: {k: v["mean"] for k, v in d.items()} for n, d in mc.items()},
        "monte_carlo_ci": mc,
        "mission_effectiveness": suite["mission_effectiveness"],
        "significance_gated_mes": suite["significance_gated_mes"],
        "identification": suite["identification"],
        "geolocation": suite["geolocation"]["by_receivers"],
        "multireceiver": suite["multireceiver"],
        "hop_prediction": suite.get("hop_prediction"),
        "provenance": {
            "source": "results/suite_results.json + results/benchmark.json",
            "suite_protocol": suite.get("protocol",
                                        {"note": "see benchmark_protocol"}),
        },
    }
    if bench is not None:
        out["benchmark_protocol"] = bench["protocol"]
        out["benchmark_provenance"] = bench.get("provenance")
        out["smart_scan_agile_hop"] = bench.get("smart_scan_agile_hop")
        out["benchmark_ranking"] = bench.get("ranking")
        out["receiver_fom"] = bench.get("receiver_fom")
        out["smart_scan_value_mode_ablation"] = bench.get(
            "smart_scan_value_mode_ablation")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", default="results/suite_results.json")
    ap.add_argument("--benchmark", default="results/benchmark.json")
    args = ap.parse_args()

    suite = _load(ROOT / args.suite)
    if suite is None:
        raise SystemExit(f"missing {args.suite} - run the experiment suite "
                         f"first (python -m ewsmart.experiments --suite full)")
    bench = _load(ROOT / args.benchmark)
    data = build_site_data(suite, bench)

    out_dir = ROOT / "website" / "public"
    (out_dir / "data").mkdir(parents=True, exist_ok=True)
    with open(out_dir / "data" / "results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, allow_nan=False, default=str)

    # Also bake the same payload into a TypeScript module. The pages import it
    # statically, so the metrics are present on first paint even when the site
    # is opened from file:// or served from a sub-path where /data/... is not
    # reachable (a fetch that never lands used to leave the tables on
    # "Loading..." forever). Mirrors tools/export_docs.py -> docsHtml.ts.
    ts_out = ROOT / "website" / "src" / "data"
    ts_out.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, allow_nan=False, default=str)
    (ts_out / "resultsData.ts").write_text(
        "// AUTO-GENERATED from results/suite_results.json + "
        "results/benchmark.json by\n"
        "// tools/export_site_data.py -- do not edit by hand.\n"
        "// Baked statically so the results render without a network round-trip.\n"
        f"const DATA: unknown = {payload};\n"
        "export default DATA;\n",
        encoding="utf-8")

    figs = ROOT / "figures"
    if figs.exists():
        (out_dir / "figures").mkdir(parents=True, exist_ok=True)
        for png in figs.glob("*.png"):
            shutil.copy2(png, out_dir / "figures" / png.name)

    manual = ROOT / "docs" / "manual.md"
    if manual.exists():
        (out_dir / "docs").mkdir(parents=True, exist_ok=True)
        shutil.copy2(manual, out_dir / "docs" / "manual.md")

    print(f"wrote {out_dir / 'data' / 'results.json'} "
          f"(protocol: {data.get('benchmark_protocol', 'suite only')})")


if __name__ == "__main__":
    main()