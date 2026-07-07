"""Wiring tests for the regime-conditional edge scan (Phase 4 second increment).
Statistics are the pure module's job (tests/test_nr7_study.py) — here we test the
generalized collector's shape contract and the scan matrix wiring only."""
import numpy as np
import pandas as pd

import research.studies.regime_edge_scan as scan
from engine.strategies import strategy_vwap_reversion, strategy_vwma_breakout_pullback


def _synth_df(ticker, start='2019-01-01', n=500, base=1000.0):
    dates = pd.date_range(start, periods=n, freq='B')
    rng = np.random.default_rng(abs(hash(ticker)) % 2**32)
    close = base * (1 + 0.0002 * np.arange(n) + rng.normal(0, 0.015, n)).cumprod()
    return pd.DataFrame({'date': dates.astype(str), 'open': close,
                         'high': close * 1.015, 'low': close * 0.985,
                         'close': close, 'volume': 1_000_000})


def test_collect_trades_for_strategy_shape_contract():
    df = _synth_df('SMOKE')
    trades = scan.collect_trades_for_strategy(
        strategy_vwap_reversion, 'vwap_reversion', 'SMOKE', df)
    for t in trades:
        assert set(t) >= {'strategy', 'ticker', 'entry_date',
                          'raw_entry', 'raw_exit', 'regime'}
        assert t['strategy'] == 'vwap_reversion'
        assert t['ticker'] == 'SMOKE'
        assert t['regime'] in ('BULL', 'SIDEWAYS', 'BEAR')
        assert t['raw_entry'] > 0 and t['raw_exit'] > 0


def test_collect_handles_vwma_no_filters_signature():
    df = _synth_df('VWMA')
    trades = scan.collect_trades_for_strategy(
        strategy_vwma_breakout_pullback, 'VWMA Breakout Pullback', 'VWMA', df)
    assert isinstance(trades, list)


# ── Task 2: classify_cell ───────────────────────────────────────────────────
def _mk(ticker, date, entry, exit_, regime):
    return {'strategy': 'X', 'ticker': ticker, 'entry_date': date,
            'raw_entry': entry, 'raw_exit': exit_, 'regime': regime}


def test_classify_cell_rejected_when_regime_bar_fails():
    cell = [_mk('A', '2024-01-0%d' % i, 100, 100, 'SIDEWAYS') for i in range(1, 9)]
    r = scan.classify_cell(cell, boundary='2024-06-01')
    assert r['state'] == 'REJECTED'


def test_classify_cell_promising_when_thin_late_sample():
    # >=100 trades in the cell (regime bar), but < 60 in the held-out late half.
    early = [_mk('A', '2023-%02d-%02d' % ((i // 28) + 1, (i % 28) + 1), 100, 112, 'SIDEWAYS')
             for i in range(90)]
    late = [_mk('A', '2024-07-%02d' % (i + 1), 100, 112, 'SIDEWAYS') for i in range(20)]
    r = scan.classify_cell(early + late, boundary='2024-01-01')
    assert r['regime_pass'] is True
    assert r['state'] == 'PROMISING'
    assert r['late_n'] == 20


def test_classify_cell_confirmed_when_persistent_and_enough_late():
    early = [_mk('A', '2023-%02d-01' % (m + 1), 100, 110, 'BULL') for m in range(12)] * 6
    late = [_mk('A', '2024-%02d-02' % ((i % 12) + 1), 100, 110, 'BULL') for i in range(70)]
    r = scan.classify_cell(early + late, boundary='2024-01-01')
    assert r['regime_pass'] is True
    assert r['late_n'] >= 60
    assert r['state'] == 'CONFIRMED'


# ── Task 3: build_matrix ────────────────────────────────────────────────────
def test_build_matrix_smoke_two_strategies():
    dfs = {'AAA': _synth_df('AAA'), 'BBB': _synth_df('BBB')}
    strategies = {'vwap_reversion': strategy_vwap_reversion}
    matrix = scan.build_matrix(strategies, dfs)
    assert 'vwap_reversion' in matrix
    for regime, cell in matrix['vwap_reversion'].items():
        assert regime in ('BULL', 'SIDEWAYS', 'BEAR')
        assert cell['state'] in ('CONFIRMED', 'PROMISING', 'REJECTED')
