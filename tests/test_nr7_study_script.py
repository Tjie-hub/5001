"""Thin wiring smoke test — proves the orchestration runs end-to-end on a tiny
slice. Does NOT assert statistics (that's the pure module's job)."""
import numpy as np
import pandas as pd
import scripts.nr7_generalization_study as study


def _synth_df(ticker, start='2020-01-01', n=400, base=1000.0):
    dates = pd.date_range(start, periods=n, freq='B')
    rng = np.random.default_rng(abs(hash(ticker)) % 2**32)
    close = base * (1 + 0.0003 * np.arange(n) + rng.normal(0, 0.01, n)).cumprod()
    return pd.DataFrame({'date': dates.astype(str), 'open': close,
                         'high': close * 1.01, 'low': close * 0.99,
                         'close': close, 'volume': 1_000_000})


def test_collect_trades_for_ticker_returns_study_trades():
    df = _synth_df('SMOKE')
    trades = study.collect_trades_for_ticker('SMOKE', df)
    for t in trades:
        assert set(t) >= {'ticker', 'entry_date', 'raw_entry', 'raw_exit', 'regime'}
        assert t['regime'] in ('BULL', 'SIDEWAYS', 'BEAR')
        assert t['raw_entry'] > 0 and t['raw_exit'] > 0
