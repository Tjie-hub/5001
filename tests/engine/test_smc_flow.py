import pandas as pd
import numpy as np
from engine.smc import detect_liquidity_sweep, calc_sweep_signal


def _df(rows):
    """rows: list of (date, open, high, low, close, volume)."""
    return pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])


def test_detect_bullish_pdl_sweep():
    # Bar 3's PDL is bar 2's low (105). Low 95 < 105, wick=(105-95)/(108-95)=0.77 >= 0.3,
    # close 106 > 105 -> bullish sweep signal=1.
    df = _df([
        ('2026-05-01', 105, 110, 100, 108, 1_000_000),
        ('2026-05-02', 106, 109, 105, 107, 1_000_000),
        ('2026-05-03', 106, 108,  95, 106, 1_500_000),
    ])
    sweeps = detect_liquidity_sweep(df, use_weekly=False)
    assert not sweeps.empty
    bull = sweeps[sweeps['signal'] == 1]
    assert len(bull) == 1
    assert bull.iloc[0]['sweep_type'] == 'pdl'
    assert bull.iloc[0]['direction'] == 'bullish'
    assert bull.iloc[0]['wick_pct'] >= 0.3


def test_no_sweep_when_wick_too_small():
    df = _df([
        ('2026-05-01', 105, 110, 100, 108, 1_000_000),
        ('2026-05-02', 106, 109, 104, 107, 1_000_000),  # PDL for bar3 = 104
        ('2026-05-03', 106, 120, 103, 119, 1_500_000),  # low 103 < 104 but wick tiny
    ])
    sweeps = detect_liquidity_sweep(df, use_weekly=False)
    assert sweeps[sweeps['signal'] == 1].empty


def test_calc_sweep_signal_marks_bullish_bar():
    df = _df([
        ('2026-05-01', 105, 110, 100, 108, 1_000_000),
        ('2026-05-02', 106, 109, 105, 107, 1_000_000),
        ('2026-05-03', 106, 108,  95, 106, 1_500_000),
    ])
    sig = calc_sweep_signal(df)
    assert sig.iloc[2] == True
    assert sig.iloc[0] == False


import sqlite3
from engine.smc_flow import confirm_sweep_flow


def _flow_db(tmp_path, rows):
    """rows: list of (ticker, trade_date, composite_score). Returns db path str."""
    db = str(tmp_path / 'flow.db')
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, composite_score INTEGER)")
    conn.execute("CREATE TABLE stockbit_flow_bars (ticker TEXT, trade_date TEXT, bar_time TEXT, "
                 "buy_lot INT, sell_lot INT, buy_freq INT, sell_freq INT, net_value INT, "
                 "price REAL, delta INT)")
    conn.executemany("INSERT INTO stockbit_flow VALUES (?,?,?)", rows)
    conn.commit(); conn.close()
    return db


def test_daily_positive_flow_confirms(tmp_path):
    db = _flow_db(tmp_path, [('BBCA', '2026-05-03', 5)])
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is True
    assert r['source'] == 'daily'
    assert r['score'] == 5.0


def test_daily_negative_flow_rejects(tmp_path):
    db = _flow_db(tmp_path, [('BBCA', '2026-05-03', -3)])
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is False
    assert r['source'] == 'daily'


def test_daily_zero_flow_rejects(tmp_path):
    db = _flow_db(tmp_path, [('BBCA', '2026-05-03', 0)])
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is False


def test_intraday_positive_delta_confirms(tmp_path):
    # No daily row -> falls through to intraday bars.
    db = _flow_db(tmp_path, [])  # empty stockbit_flow
    conn = sqlite3.connect(db)
    conn.executemany(
        "INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)",
        [('BBCA', '2026-05-03', '09:00', 500, 200, 5, 2, 100, 4000.0, 300),
         ('BBCA', '2026-05-03', '09:01', 400, 300, 4, 3, 90, 4010.0, 100)])
    conn.commit(); conn.close()
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is True
    assert r['source'] == 'intraday'
    assert r['score'] == 400.0  # 300 + 100


def test_intraday_negative_delta_rejects(tmp_path):
    db = _flow_db(tmp_path, [])
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)",
                 ('BBCA', '2026-05-03', '09:00', 100, 600, 1, 6, -50, 4000.0, -500))
    conn.commit(); conn.close()
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is False
    assert r['source'] == 'intraday'


def test_no_flow_data_passthrough(tmp_path):
    db = _flow_db(tmp_path, [])  # both tables empty
    r = confirm_sweep_flow('BBCA', '2026-01-01', db_path=db)
    assert r['confirmed'] is True
    assert r['source'] == 'none'
