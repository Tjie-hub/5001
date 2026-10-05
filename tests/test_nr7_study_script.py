"""Thin wiring smoke test — proves the orchestration runs end-to-end on a tiny
slice. Does NOT assert statistics (that's the pure module's job)."""
import os
import sqlite3

import numpy as np
import pandas as pd
import research.studies.nr7_generalization_study as study


def test_results_path_resolves_under_repo_root():
    """RESULTS previously resolved one directory short (research/docs/... instead
    of docs/...) after this script moved into research/studies/ -- silently
    writing outside version control every run. Guards the fix."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(study.__file__))))
    assert os.path.exists(os.path.join(repo_root, '.git'))
    assert study.RESULTS == os.path.join(
        repo_root, 'docs', 'superpowers', 'results',
        '2026-07-07-nr7-generalization-study.md')


def _synth_df(ticker, start='2020-01-01', n=400, base=1000.0, volume=10_000_000):
    dates = pd.date_range(start, periods=n, freq='B')
    rng = np.random.default_rng(abs(hash(ticker)) % 2**32)
    close = base * (1 + 0.0003 * np.arange(n) + rng.normal(0, 0.01, n)).cumprod()
    return pd.DataFrame({'date': dates.astype(str), 'open': close,
                         'high': close * 1.01, 'low': close * 0.99,
                         'close': close, 'volume': volume})


def _conn_with_ohlcv(ticker, df):
    """In-memory conn so get_adv_value_30d's per-trade-date ADV gate (audit
    P4-1) has data to query -- collect_trades_for_ticker now needs one."""
    conn = sqlite3.connect(':memory:')
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL, volume REAL)")
    conn.executemany(
        "INSERT INTO ohlcv VALUES (?, ?, ?, ?)",
        [(ticker, row.date, row.close, row.volume) for row in df.itertuples()],
    )
    conn.commit()
    return conn


def test_collect_trades_for_ticker_returns_study_trades():
    df = _synth_df('SMOKE')
    conn = _conn_with_ohlcv('SMOKE', df)
    trades = study.collect_trades_for_ticker(conn, 'SMOKE', df)
    for t in trades:
        assert set(t) >= {'ticker', 'entry_date', 'raw_entry', 'raw_exit', 'regime'}
        assert t['regime'] in ('BULL', 'SIDEWAYS', 'BEAR')
        assert t['raw_entry'] > 0 and t['raw_exit'] > 0


def test_collect_trades_for_ticker_gates_on_adv_at_entry_date():
    """A ticker illiquid for its whole history yields zero trades -- proves the
    gate is real, not a no-op (audit P4-1)."""
    df = _synth_df('ILLIQUID', volume=1)
    conn = _conn_with_ohlcv('ILLIQUID', df)
    trades = study.collect_trades_for_ticker(conn, 'ILLIQUID', df)
    assert trades == []
