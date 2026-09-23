"""basis_factor must refuse a rebase it cannot anchor on a reference AFTER the session.

Regression for 2026-09-23 (FORU, ~20:1 split ex 2026-09-22 inside a stranded 09-18..09-22 gap):
every settled reference preceded the gap, so the pre-split factor was applied to a post-split bar.
"""
import importlib.util
from pathlib import Path

from data.db import connect

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "repair_provisional_bars", ROOT / "scripts" / "repair_provisional_bars.py")
rpb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rpb)


def _db(tmp_path, rows):
    conn = connect(str(tmp_path / "t.db"))
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL, is_final INT)")
    conn.executemany("INSERT INTO ohlcv VALUES ('X', ?, ?, 1)", rows)
    return conn


def test_rebase_refused_when_all_references_precede_session(tmp_path):
    # raw store ~3,000 before the split; yfinance back-adjusted by 20 -> factor 20 on refs
    conn = _db(tmp_path, [("2026-09-15", 3000.0), ("2026-09-16", 3020.0), ("2026-09-17", 2980.0)])
    bars = {"2026-09-15": {"close": 150.0}, "2026-09-16": {"close": 151.0},
            "2026-09-17": {"close": 149.0}, "2026-09-22": {"close": 176.0}}
    f, info = rpb.basis_factor(conn, "X", "2026-09-22", bars)
    assert f is None and "no reference after" in info


def test_rebase_allowed_when_references_straddle_session(tmp_path):
    conn = _db(tmp_path, [("2026-09-15", 3000.0), ("2026-09-24", 3040.0)])
    bars = {"2026-09-15": {"close": 150.0}, "2026-09-24": {"close": 152.0},
            "2026-09-18": {"close": 151.0}}
    f, n = rpb.basis_factor(conn, "X", "2026-09-18", bars)
    assert abs(f - 20.0) < 0.01 and n == 2


def test_unit_factor_with_one_sided_references_still_repairs(tmp_path):
    conn = _db(tmp_path, [("2026-09-15", 150.0), ("2026-09-16", 151.0)])
    bars = {"2026-09-15": {"close": 150.0}, "2026-09-16": {"close": 151.0},
            "2026-09-18": {"close": 152.0}}
    f, n = rpb.basis_factor(conn, "X", "2026-09-18", bars)
    assert abs(f - 1.0) < 1e-9 and n == 2


def _db_multi(tmp_path, rows):
    conn = connect(str(tmp_path / "m.db"))
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL, is_final INT)")
    conn.executemany("INSERT INTO ohlcv VALUES (?, ?, ?, ?)", rows)
    return conn


def test_plausible_move_rejects_split_misdated_by_source(tmp_path):
    # FORU 2026-09-18: settled 3,540 on 09-17, yfinance says 154.3 -> -96% in one session
    conn = _db_multi(tmp_path, [("X", "2026-09-17", 3540.0, 1), ("X", "2026-09-18", 3010.0, 0)])
    assert not rpb.plausible_move(conn, "X", "2026-09-18", 154.3)
    assert rpb.plausible_move(conn, "X", "2026-09-18", 3010.0)


def test_plausible_move_scales_with_gap_length(tmp_path):
    # three sessions after the last settled bar: up to 1.35^3 ~= 2.46x is admissible
    rows = [("X", "2026-09-17", 100.0, 1)] + [
        ("Y", d, 1.0, 1) for d in ("2026-09-18", "2026-09-21", "2026-09-22")]
    conn = _db_multi(tmp_path, rows)
    assert rpb.plausible_move(conn, "X", "2026-09-22", 240.0)
    assert not rpb.plausible_move(conn, "X", "2026-09-22", 260.0)
