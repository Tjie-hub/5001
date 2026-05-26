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
