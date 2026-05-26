# tests/test_regime_3class.py
import pandas as pd


def _make_ohlcv(closes):
    n = len(closes)
    return pd.DataFrame({
        'open':   closes,
        'high':   [c * 1.01 for c in closes],
        'low':    [c * 0.99 for c in closes],
        'close':  closes,
        'volume': [1_000_000] * n,
    })


# ── label_regime_from_future ─────────────────────────────────────────────────

def test_label_bull():
    from engine.regime_filter import label_regime_from_future
    closes = [100 + i for i in range(15)]          # rises ~14% over 5 bars
    labels = label_regime_from_future(_make_ohlcv(closes), forward_days=5, trend_threshold=2.0)
    assert labels.iloc[0] == 'BULL'


def test_label_bear():
    from engine.regime_filter import label_regime_from_future
    closes = [115 - i for i in range(15)]          # drops ~13% over 5 bars
    labels = label_regime_from_future(_make_ohlcv(closes), forward_days=5, trend_threshold=2.0)
    assert labels.iloc[0] == 'BEAR'


def test_label_sideways():
    from engine.regime_filter import label_regime_from_future
    # oscillates ±0.3 — well within ±2%
    closes = [100.0 + 0.3 * (1 if i % 2 == 0 else -1) for i in range(15)]
    labels = label_regime_from_future(_make_ohlcv(closes), forward_days=5, trend_threshold=2.0)
    assert labels.iloc[0] == 'SIDEWAYS'


def test_label_last_rows_unlabeled():
    from engine.regime_filter import label_regime_from_future
    closes = list(range(100, 120))
    labels = label_regime_from_future(_make_ohlcv(closes), forward_days=5)
    # last 5 rows have no future data → NaN
    assert pd.isna(labels.iloc[-1])
    assert pd.isna(labels.iloc[-5])
    # the row just before the NaN boundary IS labeled
    assert not pd.isna(labels.iloc[-6])


def test_label_only_three_values():
    from engine.regime_filter import label_regime_from_future
    # mix of bull, bear, sideways sections
    up   = [100 + i     for i in range(30)]
    flat = [130.0] * 20
    down = [130 - i     for i in range(30)]
    closes = up + flat + down
    labels = label_regime_from_future(_make_ohlcv(closes), forward_days=5)
    valid = labels.dropna()
    assert set(valid.unique()).issubset({'BULL', 'BEAR', 'SIDEWAYS'})


# ── detect_regime ─────────────────────────────────────────────────────────────

def test_detect_sideways_short_df():
    from engine.regime_filter import detect_regime
    assert detect_regime(_make_ohlcv([100.0] * 20)) == 'SIDEWAYS'


def test_detect_sideways_flat():
    from engine.regime_filter import detect_regime
    closes = [100.0 + 0.1 * (i % 3 - 1) for i in range(60)]
    assert detect_regime(_make_ohlcv(closes)) == 'SIDEWAYS'


def test_detect_bull():
    from engine.regime_filter import detect_regime
    closes = [100 + i * 0.6 for i in range(80)]   # steady uptrend → ADX>25, slope>+1%
    assert detect_regime(_make_ohlcv(closes)) == 'BULL'


def test_detect_bear():
    from engine.regime_filter import detect_regime
    closes = [148 - i * 0.6 for i in range(80)]   # steady downtrend → ADX>25, slope<−1%
    assert detect_regime(_make_ohlcv(closes)) == 'BEAR'


# ── RegimeClassifier ──────────────────────────────────────────────────────────

def _rich_df(n=220):
    """Mixed-regime df long enough for multinomial training (all 3 classes)."""
    import pandas as pd
    up   = [100 + i * 0.5 for i in range(80)]
    flat = [140.0 + 0.2 * (i % 3 - 1) for i in range(60)]
    down = [140 - i * 0.5 for i in range(80)]
    closes = (up + flat + down)[:n]
    df = _make_ohlcv(closes)
    df['date'] = pd.date_range('2023-01-01', periods=n, freq='B').strftime('%Y-%m-%d')
    return df


def test_classifier_trains_3class():
    from engine.regime_filter import RegimeClassifier
    clf = RegimeClassifier()
    metrics = clf.train(_rich_df())
    assert 'error' not in metrics, metrics.get('error')
    assert clf.is_trained
    assert set(clf.model.classes_).issubset({'BULL', 'BEAR', 'SIDEWAYS'})


def test_classifier_predict_valid_label():
    from engine.regime_filter import RegimeClassifier
    clf = RegimeClassifier()
    clf.train(_rich_df())
    regime, conf = clf.predict(_rich_df())
    assert regime in ('BULL', 'BEAR', 'SIDEWAYS')
    assert 0.0 <= conf <= 1.0


def test_classifier_feature_importance_per_class():
    from engine.regime_filter import RegimeClassifier
    clf = RegimeClassifier()
    metrics = clf.train(_rich_df())
    fi = metrics['feature_importance']
    assert isinstance(fi, dict)
    for cls in clf.model.classes_:
        assert cls in fi
        assert isinstance(fi[cls], dict)
        assert len(fi[cls]) == len(clf.feature_cols)


def test_classifier_untrained_falls_back_to_rule():
    from engine.regime_filter import RegimeClassifier
    clf = RegimeClassifier()
    regime, conf = clf.predict(_rich_df())
    assert regime in ('BULL', 'BEAR', 'SIDEWAYS')
    assert conf == 0.0


def test_classifier_class_counts_in_metrics():
    from engine.regime_filter import RegimeClassifier
    clf = RegimeClassifier()
    metrics = clf.train(_rich_df())
    cc = metrics['class_counts']
    assert set(cc.keys()).issubset({'BULL', 'BEAR', 'SIDEWAYS'})
    assert sum(cc.values()) == metrics['n_samples']


# ── apply_macro_overlay ───────────────────────────────────────────────────────

def test_macro_bull_downgrades_on_idr_weakness():
    from engine.regime_filter import apply_macro_overlay
    regime, reason = apply_macro_overlay('BULL', {'idr_weakening': 2.0, 'bi_rate': 5.5})
    assert regime == 'SIDEWAYS'
    assert 'BULL→SIDEWAYS' in reason


def test_macro_bear_unchanged_on_idr_weakness():
    from engine.regime_filter import apply_macro_overlay
    regime, _ = apply_macro_overlay('BEAR', {'idr_weakening': 2.0, 'bi_rate': 5.5})
    assert regime == 'BEAR'


def test_macro_sideways_unchanged():
    from engine.regime_filter import apply_macro_overlay
    regime, _ = apply_macro_overlay('SIDEWAYS', {'idr_weakening': 2.0, 'bi_rate': 5.5})
    assert regime == 'SIDEWAYS'


def test_macro_clean_bull_unchanged():
    from engine.regime_filter import apply_macro_overlay
    regime, reason = apply_macro_overlay('BULL', {'idr_weakening': 0.3, 'bi_rate': 5.5})
    assert regime == 'BULL'
    assert reason == 'macro OK'


# ── strategy_regime_adaptive ──────────────────────────────────────────────────

def test_adaptive_bear_flat_equity():
    from engine.regime_filter import strategy_regime_adaptive
    # Steady downtrend → rule-based returns BEAR → flat equity
    closes = [148 - i * 0.6 for i in range(80)]
    df = _make_ohlcv(closes)
    result = strategy_regime_adaptive(df, capital=10_000_000, classifier=None)
    assert result['regime'] == 'BEAR'
    assert result['trades'] == []
    assert result['final_capital'] == result['initial_capital']


def test_adaptive_has_regime_and_confidence():
    from engine.regime_filter import strategy_regime_adaptive
    result = strategy_regime_adaptive(_rich_df(120), capital=10_000_000, classifier=None)
    assert 'regime' in result
    assert result['regime'] in ('BULL', 'BEAR', 'SIDEWAYS')
    assert 'regime_confidence' in result
    assert result['strategy'] == 'Regime Adaptive'
