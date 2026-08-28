"""Lightweight SQLite persistence for evaluation runs and metrics.

Replaces flat-JSON-only result dumps for extensive testing: every trial of a
Monte Carlo evaluation is streamed into the database as it completes, so long
runs are crash-resilient and results can be queried/aggregated with SQL.

Schema
------
``scenarios``  one row per distinct scenario configuration (JSON serialised).
``runs``       one row per invocation of an evaluation/training campaign.
``trials``     one row per (scheduler, episode) trial, with the metrics
               stored as a JSON blob.
``aggregates`` one row per (run, scheduler, metric) with mean, SEM and 95% CI,
               produced by :meth:`MetricsDB.finalize_run`.

The wrapper is intentionally dependency-free (stdlib ``sqlite3``) and
single-writer; wrap usage in a ``with`` block or call :meth:`close`.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .exceptions import DatabaseError
from .metrics import confidence_interval

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scenarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT,
    config_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id  INTEGER REFERENCES scenarios(id),
    kind         TEXT NOT NULL DEFAULT 'evaluation',
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    meta_json    TEXT
);
CREATE TABLE IF NOT EXISTS trials (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES runs(id),
    scheduler   TEXT NOT NULL,
    episode     INTEGER NOT NULL,
    n_bands     INTEGER,
    T           INTEGER,
    seed        INTEGER,
    metrics_json TEXT NOT NULL,
    UNIQUE (run_id, scheduler, episode)
);
CREATE TABLE IF NOT EXISTS aggregates (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    INTEGER NOT NULL REFERENCES runs(id),
    scheduler TEXT NOT NULL,
    metric    TEXT NOT NULL,
    mean      REAL,
    sem       REAL,
    ci_low    REAL,
    ci_high   REAL,
    n         INTEGER,
    UNIQUE (run_id, scheduler, metric)
);
CREATE INDEX IF NOT EXISTS idx_trials_run ON trials(run_id, scheduler);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MetricsDB:
    """SQLite-backed store for evaluation runs, trials and aggregate metrics.

    Args:
        path: database file path (created on connect).  Use ``":memory:"``
            for an in-memory database (handy in tests).

    Raises:
        DatabaseError: if the database file cannot be opened.
    """

    def __init__(self, path: str | Path = "ewsmart.db"):
        self.path = str(path)
        try:
            self.conn = sqlite3.connect(self.path)
            self.conn.executescript(_SCHEMA)
            self.conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(
                f"cannot open metrics database at {self.path!r}: {exc}") from exc

    def __enter__(self) -> "MetricsDB":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur
        except sqlite3.Error as exc:
            raise DatabaseError(f"metrics DB query failed: {exc}") from exc

    # -- writes ---------------------------------------------------------------
    def add_scenario(self, config: dict, name: str | None = None) -> int:
        """Insert a scenario configuration; returns its id."""
        cur = self._execute(
            "INSERT INTO scenarios (name, config_json, created_at) "
            "VALUES (?, ?, ?)",
            (name, json.dumps(config, sort_keys=True), _utcnow()))
        return int(cur.lastrowid)

    def start_run(self, scenario_id: int | None = None, kind: str = "evaluation",
                  meta: dict | None = None) -> int:
        """Open a new run row; returns the run id."""
        cur = self._execute(
            "INSERT INTO runs (scenario_id, kind, started_at, meta_json) "
            "VALUES (?, ?, ?, ?)",
            (scenario_id, kind, _utcnow(),
             json.dumps(meta or {}, sort_keys=True)))
        return int(cur.lastrowid)

    def finish_run(self, run_id: int) -> None:
        self._execute("UPDATE runs SET finished_at = ? WHERE id = ?",
                      (_utcnow(), run_id))

    def add_trial(self, run_id: int, scheduler: str, episode: int,
                  metrics: dict, n_bands: int | None = None,
                  T: int | None = None, seed: int | None = None) -> None:
        """Stream one (scheduler, episode) trial's metrics into the database.

        Raises:
            DatabaseError: if ``metrics`` is not strictly JSON-serialisable
                (NaN/inf values) or the insert fails.
        """
        try:
            payload = json.dumps(metrics, sort_keys=True, allow_nan=False)
        except (ValueError, TypeError) as exc:
            raise DatabaseError(
                f"trial metrics are not strictly JSON-serialisable: {exc}"
                ) from exc
        self._execute(
            "INSERT OR REPLACE INTO trials (run_id, scheduler, episode, "
            "n_bands, T, seed, metrics_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, scheduler, int(episode), n_bands, T, seed, payload))

    def finalize_run(self, run_id: int, scheduler_names: list[str] | None = None,
                     confidence: float = 0.95) -> dict:
        """Aggregate all trials of ``run_id`` into the ``aggregates`` table.

        Computes mean, SEM and a two-sided confidence interval per
        (scheduler, metric) pair from the stored trial rows, then marks the
        run finished.

        Returns:
            ``{scheduler: {metric: {mean, sem, ci95, ci_low, ci_high, n}}}``.
        """
        rows = self.conn.execute(
            "SELECT scheduler, episode, metrics_json FROM trials "
            "WHERE run_id = ? ORDER BY scheduler, episode", (run_id,)).fetchall()
        if scheduler_names is None:
            scheduler_names = sorted({r[0] for r in rows})
        per_sched: dict[str, list[dict]] = {name: [] for name in scheduler_names}
        for sched, _ep, mj in rows:
            if sched in per_sched:
                per_sched[sched].append(json.loads(mj))
        out: dict[str, dict] = {}
        for sched, eps in per_sched.items():
            if not eps:
                continue
            out[sched] = {}
            for k in eps[0]:
                ci = confidence_interval([e.get(k) for e in eps], confidence)
                out[sched][k] = ci
                self._execute(
                    "INSERT OR REPLACE INTO aggregates (run_id, scheduler, "
                    "metric, mean, sem, ci_low, ci_high, n) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (run_id, sched, k, ci["mean"], ci["sem"],
                     ci["ci_low"], ci["ci_high"], ci["n"]))
        self.finish_run(run_id)
        return out

    # -- reads ------------------------------------------------------------------
    def trials(self, run_id: int, scheduler: str | None = None) -> list[dict]:
        """Fetch trial rows (parsed) for a run, optionally one scheduler."""
        if scheduler is None:
            rows = self.conn.execute(
                "SELECT scheduler, episode, metrics_json FROM trials "
                "WHERE run_id = ? ORDER BY scheduler, episode",
                (run_id,)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT scheduler, episode, metrics_json FROM trials "
                "WHERE run_id = ? AND scheduler = ? ORDER BY episode",
                (run_id, scheduler)).fetchall()
        return [{"scheduler": s, "episode": e, "metrics": json.loads(mj)}
                for s, e, mj in rows]

    def aggregates(self, run_id: int) -> list[dict]:
        """Fetch the aggregate (mean/SEM/CI) rows for a run."""
        rows = self.conn.execute(
            "SELECT scheduler, metric, mean, sem, ci_low, ci_high, n "
            "FROM aggregates WHERE run_id = ? ORDER BY scheduler, metric",
            (run_id,)).fetchall()
        return [{"scheduler": s, "metric": m, "mean": mean, "sem": sem,
                 "ci_low": lo, "ci_high": hi, "n": n}
                for s, m, mean, sem, lo, hi, n in rows]

    def table_names(self) -> list[str]:
        """Names of all tables present in the database."""
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "ORDER BY name").fetchall()
        return [r[0] for r in rows]
