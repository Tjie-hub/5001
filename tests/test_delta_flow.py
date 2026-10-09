import sqlite3
import pandas as pd
import pytest
from engine import delta_flow


@pytest.fixture
def flow_db(tmp_path):
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE stockbit_flow_bars (
        ticker TEXT, trade_date TEXT, bar_time TEXT,
        buy_lot INTEGER, sell_lot INTEGER, buy_freq INTEGER, sell_freq INTEGER,
        net_value INTEGER, price INTEGER, delta INTEGER,
        PRIMARY KEY (ticker, trade_date, bar_time))""")
    # Stored as the vendor sends them: lots/freq/delta are CUMULATIVE session
    # totals (per-minute buys 100,50,70 / sells 40,90,70); net_value is per-minute.
    rows = [
        ('BBCA', '2026-06-15', '09:00', 100, 40, 5, 3, 1000, 100, 60),
        ('BBCA', '2026-06-15', '09:01', 150, 130, 9, 9, -800, 101, 20),
        ('BBCA', '2026-06-15', '09:02', 220, 200, 13, 13, 0, 100, 20),
    ]
    conn.executemany("INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit(); conn.close()
    return str(db)


def test_load_bars_returns_session(flow_db):
    df = delta_flow.load_bars('BBCA', '2026-06-15', db_path=flow_db)
    assert len(df) == 3
    assert list(df['delta']) == [60, -40, 0]


def test_cvd_is_cumulative(flow_db):
    series = delta_flow.cvd('BBCA', '2026-06-15', db_path=flow_db)
    assert [p['cvd'] for p in series] == [60, 20, 20]
    assert series[0]['time'] == '09:00'


def test_delta_by_price_buckets(flow_db):
    prof = delta_flow.delta_by_price('BBCA', '2026-06-15', bins=2, db_path=flow_db)
    # prices 100,101,100 -> deltas 60,-40,0 ; volumes (buy+sell) 140,140,140
    assert all(set(r.keys()) == {'price', 'volume', 'delta'} for r in prof)
    assert sum(r['delta'] for r in prof) == 20      # net delta conserved
    assert sum(r['volume'] for r in prof) == 420    # total lots conserved


def test_session_delta_stats(flow_db):
    s = delta_flow.session_delta_stats('BBCA', '2026-06-15', db_path=flow_db)
    assert s['total_delta'] == 20
    assert s['buy_lot'] == 220 and s['sell_lot'] == 200
    assert s['net_value'] == 200


def test_out_of_window_returns_note(flow_db):
    s = delta_flow.session_delta_stats('BBCA', '2026-01-01', db_path=flow_db)
    assert s['total_delta'] == 0 and 'note' in s


def test_cvd_ema_length():
    series = [{'time': f'09:{i:02d}', 'cvd': i} for i in range(10)]
    ema = delta_flow.cvd_ema(series, length=3)
    assert len(ema) == len(series)
    assert ema[-1]['ema'] is not None


def test_load_bars_decumulates_counters(flow_db):
    df = delta_flow.load_bars('BBCA', '2026-06-15', db_path=flow_db)
    assert list(df['buy_lot']) == [100, 50, 70]
    assert list(df['sell_lot']) == [40, 90, 70]
    assert list(df['buy_freq']) == [5, 4, 4]
    assert list(df['net_value']) == [1000, -800, 0]   # already per-minute: untouched


def test_session_totals_equal_last_cumulative_value(flow_db):
    # The day's totals are the final running total, not a sum of running totals.
    s = delta_flow.session_delta_stats('BBCA', '2026-06-15', db_path=flow_db)
    assert (s['buy_lot'], s['sell_lot'], s['total_delta']) == (220, 200, 20)
    assert delta_flow.cvd('BBCA', '2026-06-15', db_path=flow_db)[-1]['cvd'] == 20


def test_negative_step_is_clamped(tmp_path):
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE stockbit_flow_bars (
        ticker TEXT, trade_date TEXT, bar_time TEXT,
        buy_lot INTEGER, sell_lot INTEGER, buy_freq INTEGER, sell_freq INTEGER,
        net_value INTEGER, price INTEGER, delta INTEGER)""")
    conn.executemany("INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)", [
        ('X', '2026-06-15', '09:00', 100, 10, 1, 1, 0, 50, 90),
        ('X', '2026-06-15', '09:01', 90, 30, 1, 2, 0, 50, 60),   # vendor revision down
    ])
    conn.commit(); conn.close()
    df = delta_flow.load_bars('X', '2026-06-15', db_path=str(db))
    assert list(df['buy_lot']) == [100, 0] and list(df['delta']) == [90, -20]
