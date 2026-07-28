import sqlite3

from research.regime.storage import (ensure_profile_tables, persist_profile,
                                      load_latest_profile)


def _profile():
    return {
        "strategy_fn": "nr7_breakout",
        "config_hash": "abc123",
        "taxonomy_version": 1,
        "corpus_fingerprint": "fp1",
        "cells": [
            {"regime": "BULL", "verdict": "PRESENT", "n_trades": 300,
             "mean_net": 1.2, "ci_low": 0.32, "ci_high": 2.06,
             "vol_axis_declared": False, "liq_axis_declared": False,
             "evidence": {"note": "golden"}},
            {"regime": "BEAR", "verdict": "ABSENT", "n_trades": 150,
             "mean_net": -0.1, "ci_low": -0.8, "ci_high": 0.6,
             "vol_axis_declared": False, "liq_axis_declared": False,
             "evidence": {}},
        ],
    }


def test_round_trip_persist_and_load():
    conn = sqlite3.connect(":memory:")
    ensure_profile_tables(conn)
    pid = persist_profile(conn, _profile())
    loaded = load_latest_profile(conn, "nr7_breakout")
    assert loaded["profile_id"] == pid
    assert loaded["cells"]["BULL"]["verdict"] == "PRESENT"
    assert loaded["cells"]["BULL"]["ci_low"] == 0.32


def test_append_only_rerun_makes_a_new_profile_id():
    conn = sqlite3.connect(":memory:")
    ensure_profile_tables(conn)
    p1 = persist_profile(conn, _profile())
    p2 = persist_profile(conn, _profile())
    assert p1 != p2
    n = conn.execute("SELECT COUNT(*) FROM regime_profiles").fetchone()[0]
    assert n == 2
    # load_latest returns the most recent.
    assert load_latest_profile(conn, "nr7_breakout")["profile_id"] == p2


def test_load_latest_none_when_absent():
    conn = sqlite3.connect(":memory:")
    ensure_profile_tables(conn)
    assert load_latest_profile(conn, "no_such_strategy") is None
