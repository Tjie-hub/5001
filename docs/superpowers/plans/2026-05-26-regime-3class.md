# Regime 3-Class (BULL/BEAR/SIDEWAYS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the binary TRENDING/NOT_TRENDING regime engine with three directional states (BULL / BEAR / SIDEWAYS), route each to a different strategy, and add a bear dip-scout watchlist for the live scan.

**Architecture:** Multinomial LogisticRegression replaces binary classifier; signed MA-slope rule-based fallback distinguishes BULL from BEAR; `strategy_regime_adaptive` routes per regime; a new `engine/watchlist.py` module owns the bear dip-scout table and its logic independently of the scheduler; app.py, templates, and agent_firm updated to use the new label set.

**Tech Stack:** Python 3.12, scikit-learn (multinomial LogReg), SQLite, pytest, pandas, APScheduler (existing). Run tests with `venv/bin/pytest`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `engine/regime_filter.py` | Modify | Core: `detect_regime`, `label_regime_from_future`, `RegimeClassifier`, `apply_macro_overlay`, `strategy_regime_adaptive` |
| `engine/walkforward_multi.py` | Verify only | No hardcoded regime strings — confirm no-op |
| `engine/watchlist.py` | **Create** | Watchlist DDL + `add`, `promote`, `expire`, `priority_tickers` functions |
| `scheduler.py` | Modify | Bear lane: call watchlist functions per scan; expire stale on scan start |
| `app.py` | Modify | Replace all `"UNCERTAIN"` → `"SIDEWAYS"`, update emoji logic and regime gate |
| `engine/agent_firm/prompts/regime_v1.md` | Modify | Update output schema to `BULL`/`BEAR`/`SIDEWAYS` |
| `engine/agent_firm/analytics.py` | Modify | Line 110: `== "TRENDING"` → `== "BULL"` |
| `engine/agent_firm/smoke.py` | Modify | Canned `regime="TRENDING"` → `"BULL"` |
| `templates/dive.html` | Modify | CSS classes and emoji logic for new label set |
| `tests/test_regime_3class.py` | **Create** | All unit tests for `engine/regime_filter.py` changes |
| `tests/test_watchlist.py` | **Create** | Unit tests for `engine/watchlist.py` |

---

## Task 1: Relabel detection primitives — `label_regime_from_future` + `detect_regime`

**Files:**
- Modify: `engine/regime_filter.py`
- Create: `tests/test_regime_3class.py`

- [ ] **Step 1: Create test file with failing tests for `label_regime_from_future`**

```python
# tests/test_regime_3class.py
import pandas as pd
import pytest


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
```

- [ ] **Step 2: Run tests — confirm they FAIL**

```bash
venv/bin/pytest tests/test_regime_3class.py -v 2>&1 | head -40
```

Expected: 9 failures (functions still return old labels).

- [ ] **Step 3: Update `label_regime_from_future` in `engine/regime_filter.py`**

Replace the existing function body (currently uses `abs()` + int labels) with:

```python
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
```

- [ ] **Step 4: Update `detect_regime` in `engine/regime_filter.py`**

Replace the existing function body:

```python
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
```

- [ ] **Step 5: Run tests — confirm they PASS**

```bash
venv/bin/pytest tests/test_regime_3class.py -v 2>&1 | head -40
```

Expected: 9 PASS.

- [ ] **Step 6: Commit**

```bash
git add engine/regime_filter.py tests/test_regime_3class.py
git commit -m "feat(regime): 3-class signed labels — BULL/BEAR/SIDEWAYS primitives"
```

---

## Task 2: `RegimeClassifier` — multinomial LogReg

**Files:**
- Modify: `engine/regime_filter.py`
- Modify: `tests/test_regime_3class.py`

- [ ] **Step 1: Add failing tests for multinomial classifier**

Append to `tests/test_regime_3class.py`:

```python
# ── RegimeClassifier ──────────────────────────────────────────────────────────

def _rich_df(n=220):
    """Mixed-regime df long enough for multinomial training (all 3 classes)."""
    up   = [100 + i * 0.5 for i in range(80)]
    flat = [140.0 + 0.2 * (i % 3 - 1) for i in range(60)]
    down = [140 - i * 0.5 for i in range(80)]
    closes = (up + flat + down)[:n]
    return _make_ohlcv(closes)


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
```

- [ ] **Step 2: Run new tests — confirm they FAIL**

```bash
venv/bin/pytest tests/test_regime_3class.py::test_classifier_trains_3class -v
```

Expected: FAIL — classifier still uses binary int labels.

- [ ] **Step 3: Update `RegimeClassifier.train()` in `engine/regime_filter.py`**

Replace the `train()` method body:

```python
def train(self, df: pd.DataFrame, forward_days: int = 5,
          trend_threshold: float = 2.0) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score

    features = build_regime_features(df)
    labels   = label_regime_from_future(df, forward_days, trend_threshold)

    # join on index, drop unlabeled (last forward_days rows) and NaN features
    aligned = features.join(labels.rename('label')).dropna()

    if len(aligned) < 60:
        return {'error': 'Not enough labeled data', 'n_samples': len(aligned)}

    X = aligned[self.feature_cols].values
    y = aligned['label'].values

    self.scaler  = StandardScaler()
    X_scaled     = self.scaler.fit_transform(X)

    self.model = LogisticRegression(
        C=1.0, max_iter=500, class_weight='balanced',
        random_state=42,                      # solver lbfgs auto-selects multinomial
    )
    self.model.fit(X_scaled, y)
    self.is_trained   = True
    y_pred            = self.model.predict(X_scaled)
    self.train_accuracy = accuracy_score(y, y_pred)

    unique, counts = np.unique(y, return_counts=True)
    self.majority_baseline = float(counts.max() / len(y))

    feature_importance = {
        cls: dict(zip(self.feature_cols, [round(float(c), 4) for c in coef]))
        for cls, coef in zip(self.model.classes_, self.model.coef_)
    }

    return {
        'accuracy':           round(self.train_accuracy, 4),
        'n_samples':          int(len(aligned)),
        'class_counts':       dict(zip(unique.tolist(), counts.tolist())),
        'feature_importance': feature_importance,
    }
```

- [ ] **Step 4: Update `RegimeClassifier.predict()` in `engine/regime_filter.py`**

Replace the `predict()` method body:

```python
def predict(self, df: pd.DataFrame) -> Tuple[str, float]:
    """
    Returns (regime_str, confidence).
    regime_str ∈ {'BULL', 'BEAR', 'SIDEWAYS'}.
    Falls back to rule-based if untrained or low confidence (<0.45).
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

    if conf < 0.45:                            # uncertain → rule-based fallback
        return detect_regime(df), conf
    return str(self.model.classes_[idx]), conf
```

- [ ] **Step 5: Run all classifier tests**

```bash
venv/bin/pytest tests/test_regime_3class.py -v
```

Expected: all PASS (14 tests).

- [ ] **Step 6: Commit**

```bash
git add engine/regime_filter.py tests/test_regime_3class.py
git commit -m "feat(regime): RegimeClassifier multinomial 3-class BULL/BEAR/SIDEWAYS"
```

---

## Task 3: `apply_macro_overlay` + `strategy_regime_adaptive`

**Files:**
- Modify: `engine/regime_filter.py`
- Modify: `tests/test_regime_3class.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_regime_3class.py`:

```python
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
```

- [ ] **Step 2: Run new tests — confirm they FAIL**

```bash
venv/bin/pytest tests/test_regime_3class.py -k "macro or adaptive" -v
```

Expected: 7 failures.

- [ ] **Step 3: Update `apply_macro_overlay` in `engine/regime_filter.py`**

Replace the existing function body:

```python
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
```

- [ ] **Step 4: Update `strategy_regime_adaptive` in `engine/regime_filter.py`**

Replace the existing function body:

```python
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
            'strategy':       'Regime Adaptive',
            'trades':         [],
            'equity':         [capital] * len(df),
            'final_capital':  capital,
            'initial_capital': capital,
        }

    result['strategy']          = 'Regime Adaptive'
    result.setdefault('initial_capital', capital)
    result['regime']            = regime
    result['regime_confidence'] = round(confidence, 4)
    return result
```

- [ ] **Step 5: Run all tests**

```bash
venv/bin/pytest tests/test_regime_3class.py -v
```

Expected: all PASS (21 tests).

- [ ] **Step 6: Commit**

```bash
git add engine/regime_filter.py tests/test_regime_3class.py
git commit -m "feat(regime): macro overlay BULL→SIDEWAYS; strategy_regime_adaptive 3-branch"
```

---

## Task 4: `engine/watchlist.py` — bear dip-scout module

**Files:**
- Create: `engine/watchlist.py`
- Create: `tests/test_watchlist.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_watchlist.py
import sqlite3
import pandas as pd
import pytest


@pytest.fixture
def tmp_db(tmp_path):
    """Temp SQLite DB with regime_watchlist + paper_trades tables."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE regime_watchlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL,
            added_date  TEXT NOT NULL,
            regime_at_add TEXT NOT NULL DEFAULT 'BEAR',
            rsi_at_add  REAL,
            close_vs_ma50_pct REAL,
            wf_score    REAL,
            status      TEXT NOT NULL DEFAULT 'active',
            promoted_date TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_rwl_ticker_status
            ON regime_watchlist(ticker, status);

        CREATE TABLE paper_trades (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker  TEXT,
            status  TEXT DEFAULT 'OPEN'
        );
    """)
    conn.commit()
    return conn


def test_add_new_entry(tmp_db):
    from engine.watchlist import add_to_watchlist
    added = add_to_watchlist(tmp_db, 'BBRI', rsi=28.0,
                              close_vs_ma50_pct=-5.2, wf_score=72.0,
                              scan_date='2026-05-26')
    assert added is True
    row = tmp_db.execute(
        "SELECT ticker, status, rsi_at_add FROM regime_watchlist WHERE ticker='BBRI'"
    ).fetchone()
    assert row[0] == 'BBRI'
    assert row[1] == 'active'
    assert row[2] == 28.0


def test_duplicate_not_added(tmp_db):
    from engine.watchlist import add_to_watchlist
    add_to_watchlist(tmp_db, 'BBRI', rsi=28.0, close_vs_ma50_pct=-5.2,
                     wf_score=72.0, scan_date='2026-05-26')
    added = add_to_watchlist(tmp_db, 'BBRI', rsi=27.0, close_vs_ma50_pct=-6.0,
                              wf_score=72.0, scan_date='2026-05-26')
    assert added is False
    count = tmp_db.execute(
        "SELECT COUNT(*) FROM regime_watchlist WHERE ticker='BBRI'"
    ).fetchone()[0]
    assert count == 1


def test_open_trade_not_added(tmp_db):
    from engine.watchlist import add_to_watchlist
    tmp_db.execute("INSERT INTO paper_trades (ticker, status) VALUES ('BMRI', 'OPEN')")
    tmp_db.commit()
    added = add_to_watchlist(tmp_db, 'BMRI', rsi=28.0, close_vs_ma50_pct=-5.0,
                              wf_score=72.0, scan_date='2026-05-26')
    assert added is False


def test_promote_on_bull_flip(tmp_db):
    from engine.watchlist import add_to_watchlist, promote_watchlist
    add_to_watchlist(tmp_db, 'BBCA', rsi=29.0, close_vs_ma50_pct=-6.0,
                     wf_score=65.0, scan_date='2026-05-20')
    promoted = promote_watchlist(tmp_db, ['BBCA', 'TLKM'], scan_date='2026-05-26')
    assert 'BBCA' in promoted
    row = tmp_db.execute(
        "SELECT status, promoted_date FROM regime_watchlist WHERE ticker='BBCA'"
    ).fetchone()
    assert row[0] == 'promoted'
    assert row[1] == '2026-05-26'


def test_promote_ignores_unknown_tickers(tmp_db):
    from engine.watchlist import promote_watchlist
    promoted = promote_watchlist(tmp_db, ['NONEXISTENT'], scan_date='2026-05-26')
    assert promoted == []


def test_expire_stale(tmp_db):
    from engine.watchlist import add_to_watchlist, expire_stale
    # entry added 25 trading days ago (stale)
    tmp_db.execute("""
        INSERT INTO regime_watchlist (ticker, added_date, wf_score, status)
        VALUES ('ASII', '2026-04-15', 70.0, 'active')
    """)
    tmp_db.commit()
    expired = expire_stale(tmp_db, scan_date='2026-05-26', max_calendar_days=30)
    assert 'ASII' in expired
    row = tmp_db.execute(
        "SELECT status FROM regime_watchlist WHERE ticker='ASII'"
    ).fetchone()
    assert row[0] == 'expired'


def test_priority_tickers_returns_promoted(tmp_db):
    from engine.watchlist import add_to_watchlist, promote_watchlist, priority_tickers
    add_to_watchlist(tmp_db, 'BBNI', rsi=30.0, close_vs_ma50_pct=-4.0,
                     wf_score=68.0, scan_date='2026-05-20')
    promote_watchlist(tmp_db, ['BBNI'], scan_date='2026-05-26')
    tickers = priority_tickers(tmp_db)
    assert 'BBNI' in tickers


def test_compute_rsi_uptrend_high():
    from engine.watchlist import compute_rsi
    # steady uptrend → RSI should be high (>60)
    closes = pd.Series([100 + i for i in range(30)])
    rsi = compute_rsi(closes)
    assert rsi > 60


def test_compute_rsi_downtrend_low():
    from engine.watchlist import compute_rsi
    # steady downtrend → RSI should be low (<40)
    closes = pd.Series([130 - i for i in range(30)])
    rsi = compute_rsi(closes)
    assert rsi < 40
```

- [ ] **Step 2: Run tests — confirm they FAIL**

```bash
venv/bin/pytest tests/test_watchlist.py -v 2>&1 | head -20
```

Expected: ImportError — `engine.watchlist` does not exist yet.

- [ ] **Step 3: Create `engine/watchlist.py`**

```python
"""Bear dip-scout watchlist — add, promote, expire, and query functions.

The watchlist captures oversold quality tickers detected in BEAR regime
so they can be prioritised when their regime flips back to BULL.
"""

import sqlite3
from typing import List


_DDL = """
CREATE TABLE IF NOT EXISTS regime_watchlist (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker            TEXT NOT NULL,
    added_date        TEXT NOT NULL,
    regime_at_add     TEXT NOT NULL DEFAULT 'BEAR',
    rsi_at_add        REAL,
    close_vs_ma50_pct REAL,
    wf_score          REAL,
    status            TEXT NOT NULL DEFAULT 'active',
    promoted_date     TEXT,
    created_at        TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rwl_ticker_status
    ON regime_watchlist(ticker, status);
"""

RSI_THRESHOLD  = 35.0     # oversold gate
WF_SCORE_MIN   = 60.0     # quality gate


def ensure_table(conn: sqlite3.Connection) -> None:
    """Create regime_watchlist table if it does not exist."""
    conn.executescript(_DDL)
    conn.commit()


def compute_rsi(close, period: int = 14) -> float:
    """RSI-14 for the last bar of a pandas Series of closing prices."""
    import pandas as pd
    close = pd.Series(close)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, float('nan'))
    rsi   = 100 - 100 / (1 + rs)
    val   = rsi.iloc[-1]
    return float(val) if not (val != val) else float('nan')  # NaN-safe


def add_to_watchlist(
    conn: sqlite3.Connection,
    ticker: str,
    rsi: float,
    close_vs_ma50_pct: float,
    wf_score: float,
    scan_date: str,
) -> bool:
    """
    Add ticker to watchlist if all criteria pass. Returns True if inserted.

    Criteria (all must hold):
    - Not already 'active' in watchlist
    - Not currently OPEN in paper_trades
    """
    # Guard: already active
    existing = conn.execute(
        "SELECT id FROM regime_watchlist WHERE ticker=? AND status='active'",
        (ticker,),
    ).fetchone()
    if existing:
        return False

    # Guard: open trade
    open_trade = conn.execute(
        "SELECT id FROM paper_trades WHERE ticker=? AND status='OPEN'",
        (ticker,),
    ).fetchone()
    if open_trade:
        return False

    conn.execute(
        """INSERT INTO regime_watchlist
           (ticker, added_date, rsi_at_add, close_vs_ma50_pct, wf_score, status)
           VALUES (?, ?, ?, ?, ?, 'active')""",
        (ticker, scan_date, rsi, close_vs_ma50_pct, wf_score),
    )
    conn.commit()
    return True


def promote_watchlist(
    conn: sqlite3.Connection,
    tickers_flipped_bull: List[str],
    scan_date: str,
) -> List[str]:
    """
    Mark active watchlist entries for bull-flipped tickers as 'promoted'.
    Returns list of tickers actually promoted.
    """
    promoted = []
    for ticker in tickers_flipped_bull:
        cur = conn.execute(
            """UPDATE regime_watchlist
               SET status='promoted', promoted_date=?
               WHERE ticker=? AND status='active'""",
            (scan_date, ticker),
        )
        if cur.rowcount > 0:
            promoted.append(ticker)
    conn.commit()
    return promoted


def expire_stale(
    conn: sqlite3.Connection,
    scan_date: str,
    max_calendar_days: int = 30,
) -> List[str]:
    """
    Expire active entries older than max_calendar_days.
    Returns list of expired tickers.
    """
    cur = conn.execute(
        """UPDATE regime_watchlist
           SET status='expired'
           WHERE status='active'
             AND julianday(?) - julianday(added_date) > ?
           RETURNING ticker""",
        (scan_date, max_calendar_days),
    )
    expired = [row[0] for row in cur.fetchall()]
    conn.commit()
    return expired


def priority_tickers(conn: sqlite3.Connection) -> List[str]:
    """Return tickers promoted from bear watchlist (priority for bull entry scan)."""
    rows = conn.execute(
        "SELECT ticker FROM regime_watchlist WHERE status='promoted' ORDER BY promoted_date DESC"
    ).fetchall()
    return [r[0] for r in rows]
```

- [ ] **Step 4: Run tests**

```bash
venv/bin/pytest tests/test_watchlist.py -v
```

Expected: all PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add engine/watchlist.py tests/test_watchlist.py
git commit -m "feat(watchlist): bear dip-scout module — add/promote/expire/priority"
```

---

## Task 5: Wire watchlist into `scheduler.py` bear lane

**Files:**
- Modify: `scheduler.py`

- [ ] **Step 1: Add watchlist table migration to scheduler startup**

In `scheduler.py`, find `def start_scheduler():` and add the migration call before `scheduler.start()`:

```python
def start_scheduler():
    # Ensure regime_watchlist table exists (safe to run every start)
    try:
        import sqlite3 as _sql
        from engine.watchlist import ensure_table as _ensure_watchlist
        _wl_conn = _sql.connect(DB_PATH)
        _ensure_watchlist(_wl_conn)
        _wl_conn.close()
    except Exception as _e:
        print(f"[scheduler] watchlist table init error: {_e}")

    scheduler = BackgroundScheduler(timezone=WIB)
    # ... rest of existing code unchanged ...
```

- [ ] **Step 2: Add bear lane to `scheduled_multi_strategy_scan`**

In `scheduler.py`, locate the block that begins `# ── Agent Firm evaluation` (the hook restored in the prior session). Insert the **bear lane block** immediately AFTER the DB save try/except and BEFORE the agent firm block:

```python
    # ── Bear dip-scout watchlist ──────────────────────────────────────────────
    try:
        import sqlite3 as _sql
        import pandas as _pd
        from engine.regime_filter import detect_regime as _detect_regime
        from engine.watchlist import (
            add_to_watchlist as _wl_add,
            promote_watchlist as _wl_promote,
            expire_stale as _wl_expire,
            priority_tickers as _wl_priority,
            compute_rsi as _compute_rsi,
        )

        _wl_conn = _sql.connect(DB_PATH)

        # Expire stale entries at start of each scan
        _expired = _wl_expire(_wl_conn, scan_date=date_str, max_calendar_days=30)
        if _expired:
            print(f"[{time_str}] Watchlist expired: {_expired}")

        # Per-ticker: detect regime, add bears to watchlist
        _bear_added = []
        _bull_tickers = []

        for _r in intersection_results:
            _tk = _r['ticker']
            try:
                _df_wl = _pd.read_sql_query(
                    "SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT 70",
                    _wl_conn, params=(_tk,)
                )
                if len(_df_wl) < 50:
                    continue
                _df_wl = _df_wl[::-1].reset_index(drop=True)
                _regime_wl = _detect_regime(_df_wl.rename(columns={'close': 'close'}).assign(
                    open=_df_wl['close'], high=_df_wl['close'] * 1.001,
                    low=_df_wl['close'] * 0.999, volume=1_000_000,
                ))
                if _regime_wl == 'BEAR':
                    _rsi_wl = _compute_rsi(_df_wl['close'])
                    _wf_row = _wl_conn.execute(
                        "SELECT MAX(weighted_score) FROM wf_scores WHERE ticker=?", (_tk,)
                    ).fetchone()
                    _wf_sc = float(_wf_row[0]) if _wf_row and _wf_row[0] else 0.0
                    from engine.watchlist import RSI_THRESHOLD, WF_SCORE_MIN
                    if _rsi_wl < RSI_THRESHOLD and _wf_sc >= WF_SCORE_MIN:
                        _ma50 = _df_wl['close'].rolling(50).mean().iloc[-1]
                        _vs_ma = (_df_wl['close'].iloc[-1] - _ma50) / _ma50 * 100 if _ma50 else None
                        if _wl_add(_wl_conn, _tk, rsi=_rsi_wl,
                                   close_vs_ma50_pct=_vs_ma, wf_score=_wf_sc,
                                   scan_date=date_str):
                            _bear_added.append(_tk)
                elif _regime_wl == 'BULL':
                    _bull_tickers.append(_tk)
            except Exception:
                pass

        # Promote watchlist entries that have flipped to BULL
        _promoted = _wl_promote(_wl_conn, _bull_tickers, scan_date=date_str)

        # Prepend promoted tickers to flow_confirmed for priority entry
        _priority = _wl_priority(_wl_conn)
        if _priority:
            _priority_set = set(_priority)
            _priority_fc  = [r for r in flow_confirmed if r['ticker'] in _priority_set]
            _rest_fc      = [r for r in flow_confirmed if r['ticker'] not in _priority_set]
            flow_confirmed = _priority_fc + _rest_fc

        if _bear_added:
            print(f"[{time_str}] Watchlist added (BEAR): {_bear_added}")
        if _promoted:
            print(f"[{time_str}] Watchlist promoted (→BULL): {_promoted}")

        _wl_conn.close()
    except Exception as _wl_err:
        print(f"[{time_str}] Bear watchlist error (fail-open): {_wl_err}")
    # ── End bear watchlist ────────────────────────────────────────────────────
```

- [ ] **Step 3: Verify syntax**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/python -m py_compile scheduler.py && echo "OK"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add scheduler.py
git commit -m "feat(scheduler): bear dip-scout watchlist lane — add/promote/expire per scan"
```

---

## Task 6: Update `app.py` — replace old regime labels

**Files:**
- Modify: `app.py`

The goal: replace all 6 occurrences of `"UNCERTAIN"` → `"SIDEWAYS"`, update the TRENDING emoji logic, and update the regime gate check.

- [ ] **Step 1: Replace `"UNCERTAIN"` fallback strings**

Run this to find all occurrences and confirm count:
```bash
grep -n "UNCERTAIN" app.py
```
Expected: lines 140, 308, 327, 466, 593, 688 (and the gate at 1164–1165).

For **each** of these, replace `"UNCERTAIN"` with `"SIDEWAYS"`. Use the Edit tool or sed:

```bash
sed -i 's/"UNCERTAIN"/"SIDEWAYS"/g' app.py
```

- [ ] **Step 2: Update regime gate check (line ~1164)**

Find and replace:
```python
            if use_regime and regime_label == "UNCERTAIN":
                row["fail_reason"] = f"REGIME: UNCERTAIN ({round(regime_conf*100)}%)"
```

Replace with:
```python
            if use_regime and regime_label not in ("BULL", "SIDEWAYS"):
                row["fail_reason"] = f"REGIME: {regime_label} ({round(regime_conf*100)}%)"
```

(SIDEWAYS tickers are still tradeable via VWAP reversion — only BEAR blocks entry in the live gate.)

- [ ] **Step 3: Update emoji logic (line ~1199)**

Find:
```python
                regime_emoji = "📈" if r.get("regime") == "TRENDING" else "📉" if r.get("regime") == "SIDEWAYS" else "❓"
```

Replace with:
```python
                regime_emoji = "📈" if r.get("regime") == "BULL" else "🐻" if r.get("regime") == "BEAR" else "➡️" if r.get("regime") == "SIDEWAYS" else "❓"
```

- [ ] **Step 4: Verify syntax**

```bash
venv/bin/python -m py_compile app.py && echo "OK"
```

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "fix(app): replace UNCERTAIN→SIDEWAYS, TRENDING→BULL in regime display"
```

---

## Task 7: Update `templates/dive.html` — CSS classes for new regime set

**Files:**
- Modify: `templates/dive.html`

- [ ] **Step 1: Find and replace CSS regime classes**

Find (lines 104–106):
```css
    .regime-badge.TRENDING { background: rgba(34,197,94,.12);  color: var(--green); }
    .regime-badge.BREAKOUT { background: rgba(99,102,241,.12); color: var(--accent); }
    .regime-badge.RANGING  { background: rgba(234,179,8,.12);  color: var(--yellow); }
```

Replace with:
```css
    .regime-badge.BULL     { background: rgba(34,197,94,.12);  color: var(--green); }
    .regime-badge.BEAR     { background: rgba(239,68,68,.12);  color: #ef4444; }
    .regime-badge.SIDEWAYS { background: rgba(234,179,8,.12);  color: var(--yellow); }
```

- [ ] **Step 2: Commit**

```bash
git add templates/dive.html
git commit -m "fix(templates): regime badge classes BULL/BEAR/SIDEWAYS"
```

---

## Task 8: Agent firm blast radius — prompt, analytics, smoke

**Files:**
- Modify: `engine/agent_firm/prompts/regime_v1.md`
- Modify: `engine/agent_firm/analytics.py`
- Modify: `engine/agent_firm/smoke.py`

- [ ] **Step 1: Update `regime_v1.md` — output schema to new labels**

Find the JSON output block and guidance section in `regime_v1.md`. Replace:

```markdown
{
  "regime_call": "TRENDING" | "SIDEWAYS" | "VOLATILE" | "UNKNOWN",
  ...
}

Guidance:
- TRENDING: quant pipeline says TRENDING AND walk-forward consistency >= 55% for at least one strategy
- VOLATILE: vpin_label is "EXTREME" in recent bars OR avg vol_ratio > 3.0
- SIDEWAYS: signal neutral across most bars with no clear direction
- UNKNOWN: wf_scores empty or all data missing
```

With:

```markdown
{
  "regime_call": "BULL" | "BEAR" | "SIDEWAYS" | "VOLATILE" | "UNKNOWN",
  ...
}

Guidance:
- BULL: quant pipeline says BULL AND walk-forward consistency >= 55% for at least one strategy
- BEAR: quant pipeline says BEAR OR strong downward price structure confirmed
- VOLATILE: vpin_label is "EXTREME" in recent bars OR avg vol_ratio > 3.0
- SIDEWAYS: signal neutral across most bars with no clear directional bias
- UNKNOWN: wf_scores empty or all data missing
```

- [ ] **Step 2: Update `analytics.py` line 110**

Find:
```python
        if role == "regime":
            return (output.get("regime_call") == "TRENDING") == is_approve
```

Replace with:
```python
        if role == "regime":
            return (output.get("regime_call") == "BULL") == is_approve
```

Note: historical `agent_traces` rows that stored `"TRENDING"` are unaffected — they predate this change and the analytics window is recent data only.

- [ ] **Step 3: Update `smoke.py` canned regime value**

Find:
```python
    regime="TRENDING",
```

Replace with:
```python
    regime="BULL",
```

- [ ] **Step 4: Run agent firm tests**

```bash
venv/bin/pytest tests/agent_firm/ -v --timeout=10 -x -q 2>&1 | tail -20
```

Expected: all PASS (smoke tests skip if firm disabled, which is fine).

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/prompts/regime_v1.md engine/agent_firm/analytics.py engine/agent_firm/smoke.py
git commit -m "fix(agent-firm): regime labels BULL/BEAR/SIDEWAYS — prompt, analytics, smoke"
```

---

## Task 9: Integration smoke test + walkforward regression

**Files:**
- No new files — verification only

- [ ] **Step 1: Run full test suite**

```bash
venv/bin/pytest tests/ -v -q --timeout=30 2>&1 | tail -30
```

Expected: all PASS.

- [ ] **Step 2: Run regime smoke test (live DB)**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
set -a; source .env; set +a
venv/bin/python -c "
import sqlite3, pandas as pd
from engine.regime_filter import detect_regime, RegimeClassifier

DB = '/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db'
conn = sqlite3.connect(DB)
for ticker in ['BBRI', 'BBCA', 'TLKM']:
    df = pd.read_sql(f'SELECT * FROM ohlcv WHERE ticker=\"{ticker}\" ORDER BY date ASC', conn)
    for c in ['open','high','low','close','volume']:
        df[c] = df[c].astype(float)
    rule = detect_regime(df)
    clf = RegimeClassifier()
    clf.train(df)
    ml, conf = clf.predict(df)
    print(f'{ticker}: rule={rule}  ml={ml} conf={conf:.2f}')
conn.close()
"
```

Expected: each ticker prints one of `BULL / BEAR / SIDEWAYS` for both rule and ML (no crashes, no `TRENDING`/`UNCERTAIN`).

- [ ] **Step 3: Run agent firm smoke test**

```bash
set -a; source .env; set +a
venv/bin/python -m engine.agent_firm.smoke
```

Expected: `decision=… OK` (or `SKIP` if firm disabled in env).

- [ ] **Step 4: Final commit**

```bash
git add -u
git commit -m "test(regime): integration smoke — 3-class labels verified on live DB"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] §1 Rule-based `detect_regime` signed slope → Task 1
- [x] §1 ML multinomial `label_regime_from_future` + `RegimeClassifier` → Tasks 1–2
- [x] §1 `apply_macro_overlay` BULL→SIDEWAYS → Task 3
- [x] §2 `strategy_regime_adaptive` 3-branch routing → Task 3
- [x] §3 Watchlist DDL + add/promote/expire/priority → Tasks 4–5
- [x] §3 Bear lane in scheduler → Task 5
- [x] §4 `app.py` UNCERTAIN→SIDEWAYS, TRENDING→BULL → Task 6
- [x] §4 `templates/dive.html` CSS classes → Task 7
- [x] §4 Agent firm smoke, analytics, prompt → Task 8
- [x] §4 `walkforward_multi.py` — confirmed no hardcoded strings (no task needed)
- [x] §5 Integration regression → Task 9
- [x] §6 All unit tests → Tasks 1–4

**Placeholder scan:** None found.

**Type consistency:** `detect_regime` returns `str` ∈ {BULL, BEAR, SIDEWAYS} throughout; `add_to_watchlist` accepts `sqlite3.Connection` (not path string); `compute_rsi` returns `float`; all consistent across tasks.
