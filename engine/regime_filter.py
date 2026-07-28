"""
Regime Filter — AI-powered market regime detection per ticker.
==============================================================
Deteksi regime: BULL / BEAR / SIDEWAYS
Lalu pilih strategi yang sesuai.

Usage:
    from engine.regime_filter import detect_regime, strategy_regime_adaptive

    # Detect regime saja
    regime = detect_regime(df)  # "BULL" / "BEAR" / "SIDEWAYS"

    # Full strategy — auto-select berdasarkan regime
    result = strategy_regime_adaptive(df, capital=50_000_000)
"""

import numpy as np
import pandas as pd
from typing import Tuple
try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False

from data.db import connect as db_connect
from engine.indicators import (
    calc_adx,
    calc_close_vs_ma,
    calc_ma_slope,
    calc_price_range_pct,
    calc_vr_mean,
)

# ── Macro config (update manual per rapat BI) ─────────────────────────
BI_RATE: float = 6.25  # % — update kalau ada perubahan BI rate
_IDR_WEAKEN_THRESHOLD: float = 1.0  # % 5-hari, positif = IDR melemah


# ── Macro regime overlay ─────────────────────────────────────────────

def get_macro_overlay(period: str = "30d") -> dict:
    """
    Fetch USD/IDR 5-hari change + BI Rate.
    Fallback ke 0.0 kalau yfinance gagal (tidak block sinyal).
    """
    result = {
        "idr_weakening": 0.0,
        "bi_rate": BI_RATE,
        "source": "fallback",
        "error": None
    }
    if not _YF_AVAILABLE:
        result["error"] = "yfinance not installed"
        return result
    try:
        data = yf.download("USDIDR=X", period=period, auto_adjust=True,
                           progress=False)
        if data is None or len(data) < 6:
            result["error"] = f"Data terlalu sedikit: {len(data) if data is not None else 0} bars"
            return result
        close = data["Close"].squeeze()
        last  = float(close.iloc[-1])
        prev5 = float(close.iloc[-6])
        result["idr_weakening"] = round((last - prev5) / prev5 * 100, 4)
        result["source"] = "yfinance"
    except Exception as e:
        result["error"] = str(e)
    return result


def apply_macro_overlay(regime: str, macro: dict) -> tuple:
    """
    Apply macro overlay to regime prediction.
    IDR weakening >threshold → BULL downgraded to SIDEWAYS.
    BEAR is never upgraded by macro alone.
    """
    idr_weak = macro.get("idr_weakening", 0.0)
    bi_rate  = macro.get("bi_rate", BI_RATE)
    reason_parts = []
    final_regime = regime

    if idr_weak > _IDR_WEAKEN_THRESHOLD:
        reason_parts.append(f"IDR melemah {idr_weak:+.2f}% (5d)")
        if regime == "BULL":
            final_regime = "SIDEWAYS"
            reason_parts.append("BULL→SIDEWAYS")

    if bi_rate > 6.5:
        reason_parts.append(f"BI Rate tinggi {bi_rate}%")

    reason = "; ".join(reason_parts) if reason_parts else "macro OK"
    return final_regime, reason


# ── Rule-based regime detection (no ML needed for cold start) ────────

def detect_regime(df: pd.DataFrame) -> str:
    """
    Detect market regime from signed MA-slope.
    Returns: 'BULL' / 'BEAR' / 'SIDEWAYS'

    Rules:
      BULL:     ADX > 25 AND MA-slope > +1.0%
      BEAR:     ADX > 25 AND MA-slope < -1.0%
      SIDEWAYS: everything else (folds old SIDEWAYS + UNCERTAIN)
    """
    if len(df) < 30:
        return 'SIDEWAYS'

    adx   = calc_adx(df, 14)
    slope = calc_ma_slope(df, 20, 5)          # signed, NOT abs()

    last_adx   = adx.iloc[-1]
    last_slope = slope.iloc[-1]

    if pd.isna(last_adx) or pd.isna(last_slope):
        return 'SIDEWAYS'

    if last_adx > 25 and last_slope > 1.0:
        return 'BULL'
    elif last_adx > 25 and last_slope < -1.0:
        return 'BEAR'
    else:
        return 'SIDEWAYS'


# ── Feature matrix builder (for ML training) ─────────────────────────

def build_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature matrix for regime classification.
    Each row = 1 bar, features computed from trailing window.
    """
    features = pd.DataFrame(index=df.index)
    features['adx'] = calc_adx(df, 14)
    features['ma_slope'] = calc_ma_slope(df, 20, 5)
    features['vr_mean'] = calc_vr_mean(df, 20, 10)
    features['range_pct'] = calc_price_range_pct(df, 20)
    features['close_vs_ma'] = calc_close_vs_ma(df, 20)

    # Trend consistency — berapa % bar di atas MA20 dalam 20 hari terakhir
    ma20 = df['close'].rolling(20).mean()
    above_ma = (df['close'] > ma20).astype(float)
    features['pct_above_ma'] = above_ma.rolling(20).mean() * 100

    return features.dropna()


def label_regime_from_future(df: pd.DataFrame, forward_days: int = 5,
                              trend_threshold: float = 2.0) -> pd.Series:
    """
    Auto-label regime from signed future return (for ML training).
    - forward return > +threshold%  → 'BULL'
    - forward return < -threshold%  → 'BEAR'
    - abs(return) <= threshold%     → 'SIDEWAYS'
    - last forward_days rows        → NaN (no future data)
    """
    future_ret = (df['close'].shift(-forward_days) - df['close']) / df['close'] * 100
    labels = pd.Series(index=df.index, dtype=object)          # all NaN by default
    labels[future_ret > trend_threshold]  = 'BULL'
    labels[future_ret < -trend_threshold] = 'BEAR'
    mask_sideways = (future_ret >= -trend_threshold) & (future_ret <= trend_threshold)
    labels[mask_sideways] = 'SIDEWAYS'
    return labels


# ── ML Regime Classifier ─────────────────────────────────────────────

class RegimeClassifier:
    """
    Logistic Regression regime classifier.
    Binary: TRENDING (1) vs NOT_TRENDING (0).

    Train on historical data, predict on latest bar.
    Auto-retrain setiap kali dipanggil dengan train=True.
    """

    def __init__(self):
        self.model = None
        self.feature_cols = ['adx', 'ma_slope', 'vr_mean', 'range_pct',
                             'close_vs_ma', 'pct_above_ma']
        self.is_trained = False
        self.train_accuracy = 0.0          # in-sample (optimistic; see holdout_accuracy)
        self.holdout_accuracy = None       # honest temporal-holdout accuracy (item 2.6)
        self.beats_baseline = None         # holdout_accuracy > holdout majority baseline?
        self.majority_baseline = 0.0

    def train(self, df: pd.DataFrame, forward_days: int = 5,
              trend_threshold: float = 2.0, holdout_frac: float = 0.3) -> dict:
        """
        Train on df. Returns training metrics.

        Honesty (audit item 2.6): the headline `accuracy` is a TEMPORAL-holdout
        number — fit on the early (1-holdout_frac) of the labeled data, evaluate
        on the later portion, with a `forward_days` embargo at the split so the
        forward-looking labels never leak across it. In-sample accuracy is still
        reported but clearly labeled `in_sample_accuracy`. `beats_baseline` says
        whether the holdout accuracy exceeds the holdout majority baseline — a
        classifier that doesn't is no better than "guess the common regime".
        The DEPLOYED model (self.model) is fit on ALL labeled data.
        """
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score

        features = build_regime_features(df)
        labels   = label_regime_from_future(df, forward_days, trend_threshold)

        # join on index, drop unlabeled (last forward_days rows) and NaN features.
        # keep chronological order for the temporal split.
        aligned = features.join(labels.rename('label')).dropna()
        aligned = aligned.sort_index()

        if len(aligned) < 60:
            return {'error': 'Not enough labeled data', 'n_samples': len(aligned)}

        X = aligned[self.feature_cols].values
        y = aligned['label'].values
        n = len(aligned)

        # ── Temporal holdout with embargo (the honest OOS estimate) ──────────
        split = int(n * (1.0 - holdout_frac))
        tr_end = max(0, split - forward_days)          # embargo the boundary
        holdout_accuracy = None
        holdout_baseline = None
        beats_baseline   = None
        if tr_end >= 40 and (n - split) >= 15 and len(set(y[:tr_end])) >= 2:
            _sc = StandardScaler()
            X_tr = _sc.fit_transform(X[:tr_end])
            _m = LogisticRegression(C=1.0, max_iter=500,
                                    class_weight='balanced', random_state=42)
            _m.fit(X_tr, y[:tr_end])
            X_ho = _sc.transform(X[split:])
            y_ho = y[split:]
            holdout_accuracy = float(accuracy_score(y_ho, _m.predict(X_ho)))
            _u, _c = np.unique(y_ho, return_counts=True)
            holdout_baseline = float(_c.max() / len(y_ho))
            beats_baseline = bool(holdout_accuracy > holdout_baseline)

        # ── Deployed model: fit on ALL labeled data ──────────────────────────
        self.scaler  = StandardScaler()
        X_scaled     = self.scaler.fit_transform(X)
        self.model = LogisticRegression(
            C=1.0, max_iter=500, class_weight='balanced',
            random_state=42,
        )
        self.model.fit(X_scaled, y)
        self.is_trained   = True
        in_sample = float(accuracy_score(y, self.model.predict(X_scaled)))
        self.train_accuracy = in_sample
        self.holdout_accuracy = holdout_accuracy
        self.beats_baseline = beats_baseline

        unique, counts = np.unique(y, return_counts=True)
        self.majority_baseline = float(counts.max() / len(y))

        feature_importance = {
            cls: dict(zip(self.feature_cols, [round(float(c), 4) for c in coef]))
            for cls, coef in zip(self.model.classes_, self.model.coef_)
        }

        return {
            # honest headline: the temporal-holdout accuracy (falls back to the
            # in-sample number only when the holdout was too small to estimate).
            'accuracy':           round(holdout_accuracy, 4) if holdout_accuracy is not None else round(in_sample, 4),
            'in_sample_accuracy': round(in_sample, 4),
            'holdout_accuracy':   round(holdout_accuracy, 4) if holdout_accuracy is not None else round(in_sample, 4),
            'holdout_baseline':   round(holdout_baseline, 4) if holdout_baseline is not None else round(self.majority_baseline, 4),
            'beats_baseline':     bool(beats_baseline) if beats_baseline is not None else False,
            'n_samples':          int(len(aligned)),
            'class_counts':       dict(zip(unique.tolist(), counts.tolist())),
            'feature_importance': feature_importance,
        }

    def predict(self, df: pd.DataFrame) -> Tuple[str, float]:
        """
        Predict regime for latest bar.
        Returns: (regime_str, confidence)
          regime_str: 'BULL' / 'BEAR' / 'SIDEWAYS'
          confidence: max predict_proba score
        Falls back to rule-based detect_regime if untrained or confidence < 0.45.
        """
        if not self.is_trained:
            return detect_regime(df), 0.0

        features = build_regime_features(df)
        if len(features) == 0:
            return 'SIDEWAYS', 0.0

        X        = features[self.feature_cols].iloc[[-1]].values
        X_scaled = self.scaler.transform(X)
        proba    = self.model.predict_proba(X_scaled)[0]
        idx      = int(proba.argmax())
        conf     = float(proba[idx])

        if conf < 0.45:                            # low confidence → rule-based fallback
            return detect_regime(df), conf
        return str(self.model.classes_[idx]), conf


# ── Strategi 6: Regime Adaptive Strategy ──────────────────────────────

def strategy_regime_adaptive(df: pd.DataFrame, capital: float = 50_000_000,
                              filters: list = None,
                              classifier: 'RegimeClassifier' = None) -> dict:
    """
    BULL     → Momentum Following
    SIDEWAYS → VWAP Reversion
    BEAR     → No trades (equity flat); dip-scouting is handled in live scan
    """
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from engine.strategies import strategy_momentum, strategy_vwap_reversion

    if classifier and classifier.is_trained:
        regime, confidence = classifier.predict(df)
    else:
        regime    = detect_regime(df)
        confidence = 0.0

    if regime == 'BULL':
        result = strategy_momentum(df, capital=capital, filters=filters)
    elif regime == 'SIDEWAYS':
        result = strategy_vwap_reversion(df, capital=capital, filters=filters)
    else:                                       # BEAR
        result = {
            'strategy':        'Regime Adaptive',
            'trades':          [],
            'equity':          [capital] * len(df),
            'final_capital':   capital,
            'initial_capital': capital,
        }

    result['strategy']          = 'Regime Adaptive'
    result.setdefault('initial_capital', capital)
    result['regime']            = regime
    result['regime_confidence'] = round(confidence, 4)
    return result


# ── Standalone test ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sqlite3
    import sys

    from config import DB_PATH
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BRPT"

    conn = db_connect(DB_PATH)
    df = pd.read_sql(
        f'SELECT * FROM ohlcv WHERE ticker="{ticker}" ORDER BY date ASC', conn)
    conn.close()

    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)

    print(f"\n{'='*50}")
    print(f"REGIME FILTER — {ticker}")
    print(f"{'='*50}")

    # 1. Rule-based
    regime = detect_regime(df)
    adx = calc_adx(df, 14).iloc[-1]
    slope = calc_ma_slope(df, 20, 5).iloc[-1]
    print(f"\n[Rule-based]")
    print(f"  ADX(14):    {adx:.2f}")
    print(f"  MA Slope:   {slope:.2f}%")
    print(f"  Regime:     {regime}")

    # 2. ML-based
    clf = RegimeClassifier()
    train_result = clf.train(df)
    print(f"\n[ML Training]")
    for k, v in train_result.items():
        print(f"  {k}: {v}")

    regime_ml, conf = clf.predict(df)
    print(f"\n[ML Prediction]")
    print(f"  Regime:     {regime_ml}")
    print(f"  Confidence: {conf:.4f}")

    # 3. Run strategy
    result = strategy_regime_adaptive(df, classifier=clf)
    n_trades = len(result['trades'])
    final = result['final_capital']
    ret = (final - 50_000_000) / 50_000_000 * 100
    print(f"\n[Strategy Result]")
    print(f"  Regime used:  {result['regime']}")
    print(f"  Trades:       {n_trades}")
    print(f"  Final capital: Rp {final:,.0f}")
    print(f"  Return:       {ret:+.2f}%")
