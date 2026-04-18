"""
Regime Filter — AI-powered market regime detection per ticker.
==============================================================
Deteksi regime: TRENDING / SIDEWAYS / UNCERTAIN
Lalu pilih strategi yang sesuai.

Usage:
    from engine.regime_filter import detect_regime, strategy_regime_adaptive

    # Detect regime saja
    regime = detect_regime(df)  # "TRENDING" / "SIDEWAYS" / "UNCERTAIN"

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

# ── Macro config (update manual per rapat BI) ─────────────────────────
BI_RATE: float = 6.25  # % — update kalau ada perubahan BI rate
_IDR_WEAKEN_THRESHOLD: float = 1.0  # % 5-hari, positif = IDR melemah


# ── Regime feature calculations ──────────────────────────────────────

def calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index — ukuran kekuatan trend."""
    high, low, close = df['high'], df['low'], df['close']

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/period, min_periods=period).mean()
    return adx


def calc_ma_slope(df: pd.DataFrame, ma_period: int = 20, slope_window: int = 5) -> pd.Series:
    """Slope of MA20 over last N bars — normalized as percentage."""
    ma = df['close'].rolling(ma_period).mean()
    slope = (ma - ma.shift(slope_window)) / ma.shift(slope_window) * 100
    return slope


def calc_vr_mean(df: pd.DataFrame, vr_period: int = 20, mean_window: int = 10) -> pd.Series:
    """Rolling mean of Volume Ratio over last N bars."""
    avg_vol = df['volume'].rolling(vr_period).mean()
    vr = df['volume'] / avg_vol.replace(0, np.nan)
    return vr.rolling(mean_window).mean()


def calc_price_range_pct(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """(Highest - Lowest) / Lowest over window — ukuran range/volatility."""
    highest = df['high'].rolling(window).max()
    lowest = df['low'].rolling(window).min()
    return (highest - lowest) / lowest.replace(0, np.nan) * 100


def calc_close_vs_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Distance of close from MA as percentage."""
    ma = df['close'].rolling(period).mean()
    return (df['close'] - ma) / ma * 100


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
    Terapkan macro overlay ke hasil regime prediction.
    IDR melemah >1% dalam 5 hari → TRENDING di-downgrade ke UNCERTAIN.
    """
    idr_weak = macro.get("idr_weakening", 0.0)
    bi_rate  = macro.get("bi_rate", BI_RATE)
    reason_parts = []
    final_regime = regime

    if idr_weak > _IDR_WEAKEN_THRESHOLD:
        reason_parts.append(f"IDR melemah {idr_weak:+.2f}% (5d)")
        if regime == "TRENDING":
            final_regime = "UNCERTAIN"
            reason_parts.append("TRENDING→UNCERTAIN")

    if bi_rate > 6.5:
        reason_parts.append(f"BI Rate tinggi {bi_rate}%")

    reason = "; ".join(reason_parts) if reason_parts else "macro OK"
    return final_regime, reason


# ── Rule-based regime detection (no ML needed for cold start) ────────

def detect_regime(df: pd.DataFrame) -> str:
    """
    Detect market regime for the latest bar using rule-based approach.
    Returns: "TRENDING" / "SIDEWAYS" / "UNCERTAIN"

    Rules:
      TRENDING:  ADX > 25 AND |MA slope| > 1%
      SIDEWAYS:  ADX < 20 AND |MA slope| < 0.5%
      UNCERTAIN: everything else
    """
    if len(df) < 30:
        return "UNCERTAIN"

    adx = calc_adx(df, 14)
    slope = calc_ma_slope(df, 20, 5)

    last_adx = adx.iloc[-1]
    last_slope = abs(slope.iloc[-1])

    if pd.isna(last_adx) or pd.isna(last_slope):
        return "UNCERTAIN"

    if last_adx > 25 and last_slope > 1.0:
        return "TRENDING"
    elif last_adx < 20 and last_slope < 0.5:
        return "SIDEWAYS"
    else:
        return "UNCERTAIN"


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
    Auto-label regime berdasarkan future return (untuk training).
    - forward return > +threshold% → TRENDING (0 = trending up works)
    - forward return < -threshold% → TRENDING (1 = trending down)
    - abs(return) < threshold/2   → SIDEWAYS (2)
    - else                        → UNCERTAIN (3)

    Simplified to binary for Logistic Regression:
    - TRENDING (1): abs(forward return) > threshold → momentum strategies work
    - NOT_TRENDING (0): abs(forward return) <= threshold → reversion/skip
    """
    future_ret = (df['close'].shift(-forward_days) - df['close']) / df['close'] * 100
    labels = pd.Series(index=df.index, dtype='int32')
    labels[:] = -1  # unlabeled

    labels[future_ret.abs() > trend_threshold] = 1   # TRENDING
    labels[future_ret.abs() <= trend_threshold] = 0   # NOT_TRENDING

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
        self.train_accuracy = 0.0
        self.majority_baseline = 0.0

    def train(self, df: pd.DataFrame, forward_days: int = 5,
              trend_threshold: float = 2.0) -> dict:
        """
        Train on full df. Returns training metrics.
        """
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, classification_report

        features = build_regime_features(df)
        labels = label_regime_from_future(df, forward_days, trend_threshold)

        # Align features and labels, drop unlabeled
        aligned = features.join(labels.rename('label')).dropna()
        aligned = aligned[aligned['label'] >= 0]

        if len(aligned) < 50:
            return {'error': 'Not enough labeled data', 'n_samples': len(aligned)}

        X = aligned[self.feature_cols].values
        y = aligned['label'].values

        # Standardize
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train — simple logistic regression, L2 regularization
        self.model = LogisticRegression(
            C=1.0, max_iter=500, class_weight='balanced', random_state=42
        )
        self.model.fit(X_scaled, y)
        self.is_trained = True
        self.train_accuracy = accuracy_score(y, self.model.predict(X_scaled))
        # Baseline: majority class ratio
        self.majority_baseline = max(np.bincount(y.astype(int)) / len(y))

        # Training metrics
        y_pred = self.model.predict(X_scaled)
        acc = accuracy_score(y, y_pred)

        return {
            'accuracy': round(acc, 4),
            'n_samples': len(aligned),
            'n_trending': int(y.sum()),
            'n_not_trending': int((y == 0).sum()),
            'feature_importance': dict(zip(
                self.feature_cols,
                [round(c, 4) for c in self.model.coef_[0]]
            ))
        }

    def predict(self, df: pd.DataFrame) -> Tuple[str, float]:
        """
        Predict regime for latest bar.
        Returns: (regime_str, confidence)
          regime_str: "TRENDING" / "SIDEWAYS" / "UNCERTAIN"
          confidence: 0.0 - 1.0
        """
        if not self.is_trained:
            # Fallback to rule-based
            return detect_regime(df), 0.0

        features = build_regime_features(df)
        if len(features) == 0:
            return "UNCERTAIN", 0.0

        X = features[self.feature_cols].iloc[[-1]].values
        X_scaled = self.scaler.transform(X)

        proba = self.model.predict_proba(X_scaled)[0]
        pred_class = self.model.predict(X_scaled)[0]

        confidence = max(proba)

        # Kalau model lebih buruk dari naive baseline → pakai rule-based
        if self.train_accuracy < (self.majority_baseline - 0.05) or confidence < 0.52:
            return "UNCERTAIN", confidence
        elif pred_class == 1:
            return "TRENDING", confidence
        else:
            return "SIDEWAYS", confidence


# ── Strategi 6: Regime Adaptive Strategy ──────────────────────────────

def strategy_regime_adaptive(df: pd.DataFrame, capital: float = 50_000_000,
                              filters: list = None,
                              classifier: RegimeClassifier = None) -> dict:
    """
    Meta-strategy: detect regime lalu jalankan strategi yang sesuai.

    TRENDING  → Momentum Following (strategy_momentum)
    SIDEWAYS  → VWAP Reversion (strategy_vwap_reversion)
    UNCERTAIN → Skip (no trades)

    Jika classifier trained → pakai ML prediction
    Jika tidak → pakai rule-based detection
    """
    import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); from engine.strategies import strategy_momentum, strategy_vwap_reversion

    if classifier and classifier.is_trained:
        regime, confidence = classifier.predict(df)
        # Fallback ke rule-based jika ML tidak yakin
        if regime == "UNCERTAIN":
            regime = detect_regime(df)
            confidence = 0.0
    else:
        regime = detect_regime(df)
        confidence = 0.0

    if regime == "TRENDING":
        result = strategy_momentum(df, capital=capital, filters=filters)
    elif regime == "SIDEWAYS":
        result = strategy_vwap_reversion(df, capital=capital, filters=filters)
    else:
        # UNCERTAIN — return empty result
        result = {
            'strategy': 'Regime Adaptive',
            'trades': [],
            'equity': [capital] * len(df),
            'final_capital': capital,
            'initial_capital': capital,
        }

    # Tag with regime info
    result['strategy'] = 'Regime Adaptive'
    if 'initial_capital' not in result:
        result['initial_capital'] = capital
    result['regime'] = regime
    result['regime_confidence'] = round(confidence, 4)

    return result


# ── Standalone test ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sqlite3
    import sys

    DB_PATH = "/home/tjiesar/idx-walkforward/data/walkforward.db"
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BRPT"

    conn = sqlite3.connect(DB_PATH)
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
