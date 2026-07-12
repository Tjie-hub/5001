"""Append-only storage for regime profiles (spec §8). Never UPDATE/DELETE — a
re-run inserts a new profile_id, preserving full lineage (like gate_decisions)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

PROFILES_DDL = """
CREATE TABLE IF NOT EXISTS regime_profiles (
    profile_id        TEXT PRIMARY KEY,
    strategy_fn       TEXT NOT NULL,
    config_hash       TEXT,
    taxonomy_version  INTEGER,
    corpus_fingerprint TEXT,
    created_at        TEXT NOT NULL
)
"""

CELLS_DDL = """
CREATE TABLE IF NOT EXISTS regime_profile_cells (
    cell_id           TEXT PRIMARY KEY,
    profile_id        TEXT NOT NULL,
    regime            TEXT NOT NULL,
    verdict           TEXT NOT NULL,
    n_trades          INTEGER,
    mean_net          REAL,
    ci_low            REAL,
    ci_high           REAL,
    vol_axis_declared INTEGER,
    liq_axis_declared INTEGER,
    evidence_json     TEXT
)
"""


def ensure_profile_tables(conn) -> None:
    conn.execute(PROFILES_DDL)
    conn.execute(CELLS_DDL)
    conn.commit()


def persist_profile(conn, profile: dict) -> str:
    """Insert one regime_profiles row + one regime_profile_cells row per cell.
    Returns the freshly minted profile_id (new every call — append-only)."""
    profile_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO regime_profiles (profile_id, strategy_fn, config_hash, "
        "taxonomy_version, corpus_fingerprint, created_at) VALUES (?,?,?,?,?,?)",
        (profile_id, profile["strategy_fn"], profile.get("config_hash"),
         profile.get("taxonomy_version"), profile.get("corpus_fingerprint"),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
    for c in profile["cells"]:
        conn.execute(
            "INSERT INTO regime_profile_cells (cell_id, profile_id, regime, verdict, "
            "n_trades, mean_net, ci_low, ci_high, vol_axis_declared, liq_axis_declared, "
            "evidence_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (uuid.uuid4().hex, profile_id, c["regime"], c["verdict"], c["n_trades"],
             c["mean_net"], c["ci_low"], c["ci_high"],
             int(c["vol_axis_declared"]), int(c["liq_axis_declared"]),
             json.dumps(c.get("evidence", {}), default=float)))
    conn.commit()
    return profile_id


def load_latest_profile(conn, strategy_fn: str) -> dict | None:
    row = conn.execute(
        "SELECT profile_id, config_hash, taxonomy_version, corpus_fingerprint, "
        "created_at FROM regime_profiles WHERE strategy_fn=? "
        "ORDER BY created_at DESC LIMIT 1", (strategy_fn,)).fetchone()
    if row is None:
        return None
    profile_id = row[0]
    cells = {}
    for c in conn.execute(
            "SELECT regime, verdict, n_trades, mean_net, ci_low, ci_high, "
            "vol_axis_declared, liq_axis_declared, evidence_json "
            "FROM regime_profile_cells WHERE profile_id=?", (profile_id,)):
        cells[c[0]] = {"verdict": c[1], "n_trades": c[2], "mean_net": c[3],
                       "ci_low": c[4], "ci_high": c[5],
                       "vol_axis_declared": bool(c[6]), "liq_axis_declared": bool(c[7]),
                       "evidence": json.loads(c[8]) if c[8] else {}}
    return {"profile_id": profile_id, "strategy_fn": strategy_fn,
            "config_hash": row[1], "taxonomy_version": row[2],
            "corpus_fingerprint": row[3], "created_at": row[4], "cells": cells}
