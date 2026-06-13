import sqlite3
import pytest
from engine.vpin import (
    classify_vpin,
    calc_vpin,
    calc_vpin_multi,
    VPIN_THRESHOLDS,
    SIGNAL_MAP,
)


def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE ticks (
            id INTEGER PRIMARY KEY, date TEXT, ticker TEXT,
            time TEXT, price REAL, volume INTEGER, tick_type TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE daily_screen (
            ticker TEXT, date TEXT, vpin REAL, delta INTEGER,
            cum_delta INTEGER, close REAL, volume INTEGER,
            vol_ratio REAL, vwap REAL, signal TEXT
        )
    """)
    return conn


def test_classify_vpin_bands():
    assert classify_vpin(None) == "N/A"
    assert classify_vpin(0.10) == "LOW"
    assert classify_vpin(0.30) == "MODERATE"
    assert classify_vpin(0.50) == "HIGH"
    assert classify_vpin(0.70) == "TOXIC"


def test_vpin_thresholds_present():
    assert "low" in VPIN_THRESHOLDS
    assert "moderate" in VPIN_THRESHOLDS
    assert "high" in VPIN_THRESHOLDS


def test_calc_vpin_no_ticks_returns_error():
    conn = _make_conn()
    result = calc_vpin(conn, "BBCA", "2026-05-30")
    assert result["vpin"] is None
    assert result["error"] is not None
    conn.close()


def test_calc_vpin_multi_no_rows_returns_none():
    conn = _make_conn()
    result = calc_vpin_multi(conn, "BBCA", "2026-05-30")
    assert result is None
    conn.close()


def test_calc_vpin_multi_insufficient_rows_returns_none():
    conn = _make_conn()
    for i in range(4):
        conn.execute(
            "INSERT INTO daily_screen VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("BBCA", f"2026-05-{i+1:02d}", 0.3 + i * 0.01, 100, 100,
             5000.0, 1000000, 1.2, 4900.0, "BUY"),
        )
    result = calc_vpin_multi(conn, "BBCA", "2026-05-04")
    assert result is None
    conn.close()


def test_calc_vpin_multi_returns_dict_with_5_rows():
    conn = _make_conn()
    for i in range(7):
        conn.execute(
            "INSERT INTO daily_screen VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("BBCA", f"2026-05-{i+1:02d}", 0.25 + i * 0.02, 100, 100,
             5000.0, 1000000, 1.3, 4900.0, "BUY"),
        )
    result = calc_vpin_multi(conn, "BBCA", "2026-05-07")
    assert result is not None
    assert "signal" in result
    assert "vpin_today" in result
    assert "vpin_regime" in result
    assert "vpin_z" in result
    assert "pressure" in result
    assert "delta_dir" in result
    assert "price_move" in result
    conn.close()


def test_calc_vpin_multi_saturated_window_neutralizes_zscore():
    """A VPIN window saturated near 1.0 has near-zero variance, so a tiny dip
    must NOT manufacture an extreme z-score that contradicts the absolute
    TOXIC label. Reviewer saw vpin 0.985 / z -3.0σ / regime NORMAL together —
    internally inconsistent. With a degenerate-variance floor, z collapses to 0.
    """
    conn = _make_conn()
    # 9 days pinned at 0.99, today dips to 0.97 -> std ~0.006, raw z ~ -3.0
    vpins = [0.99] * 9 + [0.97]
    for i, v in enumerate(vpins):
        conn.execute(
            "INSERT INTO daily_screen VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("BRPT", f"2026-06-{i+1:02d}", v, 100, 100,
             5000.0, 1000000, 1.3, 4900.0, "BUY"),
        )
    result = calc_vpin_multi(conn, "BRPT", "2026-06-10")
    assert result is not None
    # Absolute label is still TOXIC (>0.60) — that's correct and unchanged.
    assert result["vpin_label"] == "TOXIC"
    # But the relative z must be neutralized, not an extreme -3.0.
    assert result["vpin_z"] == 0.0, (
        f"saturated window should neutralize z, got {result['vpin_z']}"
    )
    conn.close()


def test_signal_map_keys_are_tuples():
    for key in SIGNAL_MAP:
        assert isinstance(key, tuple)
        assert len(key) == 3
