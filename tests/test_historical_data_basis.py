"""Phase 9 tests — raw vs adjusted data separation (Phase 9 §5).

Signal geometry must come from the RAW basis (as-stored, no adjustment at
load); adjusted data is for PnL accounting only. Every signal/trade records
its data basis.
"""
import pytest

from data.db import connect as db_connect
from engine.historical.data import (ADJUSTED_BASIS, RAW_BASIS,
                                    load_pnl_closes, load_signal_bars,
                                    raw_to_pnl_factor)


@pytest.fixture
def split_db(tmp_path):
    """Two bars before and two after a 2:1 split (2026-01-05, ratio 2.0)."""
    path = str(tmp_path / "basis.db")
    conn = db_connect(path)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                 "low REAL, close REAL, volume REAL, is_final INTEGER)")
    conn.execute("CREATE TABLE corporate_actions (ticker TEXT, date TEXT, "
                 "action TEXT, value REAL)")
    rows = [
        ("X", "2026-01-01", 99.0, 101.0, 98.0, 100.0, 1000.0, 1),
        ("X", "2026-01-02", 100.0, 102.0, 99.0, 101.0, 1000.0, 1),
        ("X", "2026-01-05", 49.0, 51.0, 48.0, 50.0, 2000.0, 1),   # post-split
        ("X", "2026-01-06", 50.0, 52.0, 49.0, 51.0, 2000.0, 1),
    ]
    conn.executemany("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.execute("INSERT INTO corporate_actions VALUES "
                 "('X', '2026-01-05', 'split', 2.0)")
    conn.commit()
    yield conn
    conn.close()


def test_signal_bars_are_raw_unadjusted(split_db):
    bars, basis = load_signal_bars(split_db, "X")
    assert basis.basis == RAW_BASIS.basis == "stored_raw"
    # Pre-split bars keep their stored (raw) scale:
    assert bars[0].open == 99.0 and bars[1].close == 101.0
    assert bars[0].high - bars[0].low == 3.0            # H−L range from raw bars


def test_pnl_closes_are_split_adjusted(split_db):
    dates, closes, basis = load_pnl_closes(split_db, "X")
    assert basis.basis == ADJUSTED_BASIS.basis == "adjusted_gap_verified"
    # Gap-verified adjustment divides pre-ex-date bars by the ratio:
    assert closes[0] == pytest.approx(50.0)
    assert closes[1] == pytest.approx(50.5)
    assert closes[2] == pytest.approx(50.0)             # post-split unchanged


def test_raw_to_pnl_factor_conversion(split_db):
    bars, _ = load_signal_bars(split_db, "X")
    dates, closes, _ = load_pnl_closes(split_db, "X")
    raw_dates = [b.date for b in bars]
    raw_closes = [b.close for b in bars]
    factors = raw_to_pnl_factor(dates, closes, raw_dates, raw_closes)
    assert factors["2026-01-01"] == pytest.approx(0.5)   # adjusted / raw
    assert factors["2026-01-05"] == pytest.approx(1.0)   # same basis post-split


def test_raw_loader_helper_skips_adjustment(split_db):
    from data.loaders import load_ohlcv_raw
    df = load_ohlcv_raw(split_db, "X")
    assert float(df.loc[0, "open"]) == 99.0              # unadjusted pre-split bar
    adjusted = load_pnl_closes(split_db, "X")[1][0]
    assert adjusted == pytest.approx(50.0)               # adjusted path differs


def test_trades_record_their_signal_basis():
    """Every HistoricalTrade stamps the data basis that produced its geometry."""
    from engine.historical.base import (BreakevenPolicy, ExitConvention,
                                        ExitKind, ProtectiveStopMode,
                                        SessionDefinition)
    from engine.historical.crabel_open_stretch import CrabelOpenStretchConfig
    from engine.historical.crabel_open_stretch import run as run_a2
    from engine.historical.kernel import AmbiguityPolicy, Bar, GapPolicy
    from engine.historical.nr7 import TiePolicy

    bars = [Bar(date=f"2026-01-{i+1:02d}", open=100, high=102, low=92, close=101)
            for i in range(9)]
    bars.append(Bar(date="2026-01-10", open=100, high=102, low=97, close=101))
    bars.append(Bar(date="2026-01-11", open=100, high=110, low=96, close=105))
    cfg = CrabelOpenStretchConfig(
        nr7_tie_policy=TiePolicy.STRICT_LESS,
        session=SessionDefinition("09:00:00"),
        gap_policy=GapPolicy.FILL_AT_OPEN,
        ambiguity_policy=AmbiguityPolicy.PREFER_LONG,
        exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 0),
        breakeven_move=BreakevenPolicy.NONE,
        protective_stop_mode=ProtectiveStopMode.ENABLED)
    res = run_a2(bars, cfg)
    assert res.n_trades == 1
    assert res.trades[0].signal_basis == "stored_raw"
    assert res.trades[0].pnl_basis == "stored_raw"
    assert res.signal_basis == "stored_raw"
