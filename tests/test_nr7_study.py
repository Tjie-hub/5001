import math
import pytest
import research.nr7_study as ns


def _t(ticker, date, entry, exit_, regime='BULL'):
    return {'ticker': ticker, 'entry_date': date, 'raw_entry': entry,
            'raw_exit': exit_, 'regime': regime}


# ── Task 1: round-trip cost ─────────────────────────────────────────────────
def test_round_trip_net_pct_applies_both_legs():
    exp = (110*(1-0.0025-0.001) - 100*(1+0.0015+0.001)) / (100*(1+0.0015+0.001)) * 100
    assert ns.round_trip_net_pct(100.0, 110.0) == pytest.approx(exp, abs=1e-9)


def test_round_trip_net_pct_loss_is_more_negative_than_gross():
    assert ns.round_trip_net_pct(100.0, 100.0) < 0
    assert ns.round_trip_net_pct(100.0, 100.0) == pytest.approx(-0.599, abs=0.01)


# ── Task 2: pool ────────────────────────────────────────────────────────────
def test_pool_trade_weighted_and_win_rate():
    trades = [_t('A', '2025-01-01', 100, 110),
              _t('A', '2025-01-02', 100, 90),
              _t('B', '2025-01-03', 100, 100)]
    r = ns.pool(trades)
    assert r['n'] == 3
    nets = [ns.round_trip_net_pct(100, 110), ns.round_trip_net_pct(100, 90),
            ns.round_trip_net_pct(100, 100)]
    assert r['exp_pct'] == pytest.approx(sum(nets) / 3, abs=1e-9)
    assert r['win_rate'] == pytest.approx(100 * 1 / 3, abs=1e-9)


def test_pool_empty_is_zero_n():
    assert ns.pool([]) == {'exp_pct': 0.0, 'n': 0, 'win_rate': 0.0}


# ── Task 3: CV split + selection ────────────────────────────────────────────
def test_cv_split_partitions_by_date():
    trades = [_t('A', '2024-01-01', 100, 110), _t('A', '2025-06-01', 100, 90)]
    early, late = ns.cv_split(trades, '2025-01-01')
    assert [t['entry_date'] for t in early] == ['2024-01-01']
    assert [t['entry_date'] for t in late] == ['2025-06-01']


def test_select_positive_tickers_needs_min_trades_and_positive():
    early = ([_t('A', '2024-01-0%d' % i, 100, 110) for i in range(1, 7)]
             + [_t('B', '2024-02-01', 100, 110), _t('B', '2024-02-02', 100, 110)])
    assert ns.select_positive_tickers(early, min_trades=5) == {'A'}


def test_select_excludes_negative_ticker():
    early = [_t('C', '2024-01-0%d' % i, 100, 90) for i in range(1, 7)]
    assert ns.select_positive_tickers(early, min_trades=5) == set()


# ── Task 4: regime stratification ───────────────────────────────────────────
def test_stratify_by_regime_buckets_and_pools():
    trades = [_t('A', '2025-01-01', 100, 110, 'BULL'),
              _t('A', '2025-01-02', 100, 90, 'SIDEWAYS'),
              _t('B', '2025-01-03', 100, 108, 'SIDEWAYS')]
    strata = ns.stratify_by_regime(trades)
    assert set(strata) == {'BULL', 'SIDEWAYS'}
    assert strata['BULL']['n'] == 1
    assert strata['SIDEWAYS']['n'] == 2
    assert strata['SIDEWAYS']['exp_pct'] == pytest.approx(
        (ns.round_trip_net_pct(100, 90) + ns.round_trip_net_pct(100, 108)) / 2, abs=1e-9)


# ── Task 5: evaluate + decision ─────────────────────────────────────────────
def test_evaluate_widen_universe_when_t1_and_t2_pass():
    t1 = {'exp_pct': 0.9, 'n': 400, 'win_rate': 55}
    t2 = {'late_exp': 0.8, 'late_n': 200, 'early_exp': 1.2, 'retention': 0.667}
    t3 = {'SIDEWAYS': {'exp_pct': 0.2, 'n': 120, 'win_rate': 45},
          'BULL': {'exp_pct': 1.5, 'n': 150, 'win_rate': 60}}
    r = ns.evaluate(t1, t2, t3, ns.THRESHOLDS)
    assert r['T1']['pass'] is True
    assert r['T2']['pass'] is True
    assert r['widen_universe'] is True
    assert r['T3']['SIDEWAYS']['pass'] is False
    assert r['widen_sideways'] is False
    assert 'WIDEN-UNIVERSE' in r['decision']


def test_evaluate_do_not_widen_when_t2_fails_retention():
    t1 = {'exp_pct': 0.9, 'n': 400, 'win_rate': 55}
    t2 = {'late_exp': 0.55, 'late_n': 200, 'early_exp': 1.5, 'retention': 0.367}
    t3 = {'SIDEWAYS': {'exp_pct': 0.6, 'n': 120, 'win_rate': 48}}
    r = ns.evaluate(t1, t2, t3, ns.THRESHOLDS)
    assert r['T2']['pass'] is False
    assert r['widen_universe'] is False
    assert r['widen_sideways'] is True
    assert r['decision'] == 'WIDEN-SIDEWAYS'


def test_evaluate_t1_boundary_exact_threshold_passes():
    t1 = {'exp_pct': 0.50, 'n': 300, 'win_rate': 50}
    t2 = {'late_exp': 0.0, 'late_n': 0, 'early_exp': 1.0, 'retention': 0.0}
    r = ns.evaluate(t1, t2, {}, ns.THRESHOLDS)
    assert r['T1']['pass'] is True
    assert r['widen_universe'] is False
    assert r['decision'] == 'DO-NOT-WIDEN'
