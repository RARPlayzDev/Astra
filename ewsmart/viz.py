"""Matplotlib visualisations: learning curves, comparisons, waterfalls, ROC."""
from __future__ import annotations

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def plot_learning_curves(curve: dict, path: str | None = None):
    """Plot learning curves.

    ``curve`` may map name -> list (training only) or name -> {"training":
    [...], "eval": [...]} in which case both are drawn: dashed = training
    (with exploration), solid = greedy evaluation on held-out scenarios.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    if "training" in curve and isinstance(curve["training"], dict):
        pairs = ((n, curve["training"][n], curve.get("eval", {}).get(n))
                 for n in curve["training"])
    else:
        pairs = ((n, v, None) for n, v in curve.items())
    for name, tr_vals, ev_vals in pairs:
        tr = np.asarray(tr_vals, dtype=float)
        ax.plot(range(1, len(tr) + 1), tr, linestyle="--", alpha=0.45,
                label=f"{name} (training)")
        if ev_vals is not None:
            ev = np.asarray(ev_vals, dtype=float)
            ax.plot(range(1, len(ev) + 1), ev, marker="o", ms=3,
                    label=f"{name} (greedy eval)")
            if len(ev) >= 6:
                k = max(1, len(ev) // 5)
                ax.plot(range(k, len(ev) + 1),
                        np.convolve(ev, np.ones(k) / k, mode="valid"),
                        linewidth=2.2)
    ax.set_xlabel("episode")
    ax.set_ylabel("total reward")
    ax.set_title("Learning: dashed = training (with exploration), "
                 "solid = greedy evaluation")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig


def plot_scheduler_comparison(results: dict, metrics: tuple = (
        "avg_reward", "threat_intercept_ratio", "intercept_ratio",
        "pct_correct_predictions"), path: str | None = None):
    """Grouped bar chart comparing schedulers across key figures of merit."""
    names = [n for n, m in results.items()
             if all(np.isfinite(m.get(k, np.nan)) for k in metrics)]
    x = np.arange(len(metrics))
    width = 0.8 / max(1, len(names))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for i, n in enumerate(names):
        vals = [float(results[n][k]) for k in metrics]
        short = n.replace("openloop-", "OL-")[:18]
        ax.bar(x + i * width, vals, width * 0.92, label=short)
    ax.set_xticks(x + width * (len(names) - 1) / 2)
    ax.set_xticklabels([m.replace("_", "\n") for m in metrics], fontsize=8)
    ax.set_title("Scheduler comparison (higher is better)")
    ax.legend(fontsize=7, ncol=4)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig


def plot_mission_effectiveness(me: dict, path: str | None = None):
    """KPP-gated Mission Effectiveness Score per scheduler.

    Mission-capable schedulers are drawn in green; systems failing a KPP are
    grey with a red FAIL marker (a failed KPP is not mission-capable
    regardless of score).
    """
    scores = me["scores"]
    order = me.get("ranking", list(scores))
    names = [n for n in order]
    vals = [scores[n]["mes"] for n in names]
    capable = [scores[n]["mission_capable"] for n in names]
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    colors = ["#2e9e5b" if c else "#9aa0a6" for c in capable]
    bars = ax.bar(np.arange(len(names)), vals, 0.62, color=colors)
    for b, c, n in zip(bars, capable, names):
        if not c:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015,
                    "FAIL", ha="center", fontsize=8, color="#d64545",
                    fontweight="bold")
        else:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015,
                    "PASS", ha="center", fontsize=8, color="#2e9e5b",
                    fontweight="bold")
    ax.set_xticks(np.arange(len(names)))
    ax.set_xticklabels([n.replace("openloop-", "OL-") for n in names],
                       fontsize=8, rotation=12)
    ax.set_ylabel("Mission Effectiveness Score")
    ax.set_ylim(0, max(1.05, max(vals) * 1.15))
    ax.set_title("Mission Effectiveness (KPP-gated): green = mission-capable")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig


def plot_waterfall(env, trace=None, t_max: int | None = None,
                   path: str | None = None):
    """Band x time waterfall: ground-truth occupancy plus receiver decisions."""
    T = min(env.T, t_max or env.T)
    occ = env.occupancy[:, :T]
    fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True,
                             height_ratios=[3, 1])
    axes[0].imshow(occ, aspect="auto", interpolation="nearest",
                   cmap="Greys", origin="lower",
                   extent=[0, T, -0.5, env.n_bands - 0.5])
    axes[0].set_ylabel("band (truth)")
    axes[0].set_title("RF spectrum waterfall - grey = emitter transmitting")
    if trace is not None:
        acts = np.asarray(trace.actions[:T])
        hits = np.asarray(trace.hits[:T], dtype=bool)
        slots = np.arange(T)
        axes[1].scatter(slots[~hits], acts[~hits], s=4, c="#bbbbbb", label="dwell miss")
        axes[1].scatter(slots[hits], acts[hits], s=6, c="crimson", label="hit")
        axes[1].set_ylabel("band (scan)")
        axes[1].set_xlabel("time slot")
        axes[1].legend(fontsize=7, markerscale=2, loc="upper right")
    else:
        axes[1].axis("off")
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig


def plot_roc(roc_data: dict, path: str | None = None):
    """Plot system-level ROC curves (empirical Pd vs Pfa per scheduler)."""
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    for name, (pfa, pd_) in roc_data.items():
        order = np.argsort(pfa)
        ax.plot(np.asarray(pfa)[order], np.asarray(pd_)[order],
                marker="o", ms=3, label=name.replace("openloop-", "OL-"))
    ax.set_xlabel("false alarm rate (empirical)")
    ax.set_ylabel("probability of detection (empirical)")
    ax.set_title("System ROC - sensitivity threshold sweep")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig


def plot_sensitivity(x_values, series: dict, xlabel: str, ylabel: str,
                     title: str, path: str | None = None, log_x: bool = False):
    """Line plot of one metric against a swept scenario parameter."""
    fig, ax = plt.subplots(figsize=(6, 3.8))
    for name, ys in series.items():
        ax.plot(x_values, ys, marker="o", label=name)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if log_x:
        ax.set_xscale("log")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig


def plot_geo_map(true_positions, receivers, estimates, scene_km=50.0,
                 title="Multi-receiver geolocation", path: str | None = None):
    """Tactical map: true emitter positions, receivers, triangulated estimates."""
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    if true_positions:
        tx = [p[0] for p in true_positions]
        ty = [p[1] for p in true_positions]
        ax.scatter(tx, ty, marker="*", s=140, c="#f43f5e", zorder=3,
                   label="emitters (truth)")
    rx = [p[0] for p in receivers]
    ry = [p[1] for p in receivers]
    ax.scatter(rx, ry, marker="^", s=110, c="#38bdf8", zorder=3,
               label="receivers")
    for est in estimates:
        ax.scatter([est["x"]], [est["y"]], marker="o", s=90, facecolors="none",
                   edgecolors="#22d3ee", linewidths=2, zorder=4,
                   label="triangulated" if "triangulated" not in ax.get_legend_handles_labels()[1] else "")
        circ = plt.Circle((est["x"], est["y"]), max(est.get("residual_km", 1.0), 0.8),
                          fill=False, color="#22d3ee", alpha=0.45, linestyle="--")
        ax.add_patch(circ)
    ax.set_xlim(-scene_km, scene_km)
    ax.set_ylim(-scene_km, scene_km)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.set_title(title, fontsize=10, color="#9fb6d4")
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig


def plot_cep_curve(by_receivers: dict, path: str | None = None):
    """CEP (mean/50/90) vs number of cooperating receivers."""
    ks = sorted(by_receivers.keys(), key=int)
    fig, ax = plt.subplots(figsize=(6, 3.8))
    for key, lbl in (("mean", "mean error"), ("cep50", "CEP50 (median)"),
                     ("cep90", "CEP90")):
        ys = [by_receivers[k].get(key) for k in ks]
        ax.plot([int(k) for k in ks], ys, marker="o", label=lbl)
    ax.set_xlabel("cooperating receivers")
    ax.set_ylabel("localisation error (km)")
    ax.set_title("Geolocation accuracy vs receiver count", fontsize=10,
                 color="#9fb6d4")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig


def plot_heatmap(x_labels, y_labels, matrix: np.ndarray, xlabel: str,
                 ylabel: str, title: str, path: str | None = None):
    """Heatmap for two-parameter sensitivity surfaces."""
    fig, ax = plt.subplots(figsize=(6.5, 4))
    im = ax.imshow(matrix, aspect="auto", cmap="viridis", origin="lower")
    ax.set_xticks(range(len(x_labels)), [str(x) for x in x_labels])
    ax.set_yticks(range(len(y_labels)), [str(y) for y in y_labels])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig
