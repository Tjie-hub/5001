# Crypto Screener — Implementation Plan

**Date:** 2026-06-05
**Port:** 5002
**Research basis:** `PLAN/crypto-research.md`
**Parent system:** `idx-walkforward-5001` (port 5001)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Port 5002: Flask (crypto screener)                              │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ data/       │  │ engine/      │  │ agent_firm/             │ │
│  │ ├ fetcher   │──│ ├ indicators │──│ ├ 6 agents (parallel)   │ │
│  │ ├ coingecko │  │ ├ strategies │  │ │  ├ technical          │ │
│  │ ├ derivatives│ │ ├ patterns   │  │ │  ├ derivatives        │ │
│  │ └ db        │  │ ├ liq_zones  │  │ │  ├ regime             │ │
│  └─────────────┘  │ ├ trap_filter│  │ │  ├ news               │ │
│                   │ ├ regime     │  │ │  ├ bull               │ │
│  ┌─────────────┐  │ ├ market_ctx │  │ │  └ risk               │ │
│  │ scheduler/  │  │ └ walkforward│  │ └─────────────────────────┘ │
│  │ └ 24/7 jobs │  └──────────────┘                               │
│  └─────────────┘                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ screener/   │  │ templates/   │  │ static/                 │ │
│  │ ├ scanner   │  │ └ dashboard  │  │ └ css/js                │ │
│  │ └ routes    │  └──────────────┘  └─────────────────────────┘ │
│  └─────────────┘                                                 │
└──────────────────────────────────────────────────────────────────┘
```

### Strategy Suite (5 strategies)

| # | Strategy | Timeframe | Entry | Stop | Target | WR |
|---|----------|-----------|-------|------|--------|-----|
| 1 | Session ORB | 15m | Break of US/EU opening range | Range opposite side | 1.5-2x range | ~60% |
| 2 | Vol-Weighted Momentum | 1h | VR>1.8 + delta+ + >VWAP | ATR×1.0 | ATR×2.0 | ~60% |
| 3 | VWAP Reversion | 15m/1h | >1.5% below VWAP + vol spike | ATR×0.8 | VWAP | ~62% |
| 4 | Volume Profile POC | 1h | Price→POC from above | ATR×1.0 | Opposite VA edge | ~60% |
| 5 | Funding Rate Contrarian | 1h | Funding>0.05% at resistance (short) / <-0.05% at support (long) | ATR×1.2 | Opposite liq zone | ~65% |

---

## Phase 1: Foundation

### 1.1 Project skeleton
**New dir:** `/home/tjiesar/10 Projects/crypto-screener/`
**Files to create:**
- `app.py` — Flask app, port 5002, blueprints
- `config.py` — env-backed config (DB path, API keys, Telegram)
- `requirements_crypto.txt` — ccxt, pycoingecko, pandas, numpy, flask, APScheduler

### 1.2 Data layer
- `data/__init__.py`
- `data/db.py` — SQLite `crypto.db`, table init
- `data/fetcher.py` — CCXT Binance OHLCV (5m, 15m, 1h, 1d)
- `data/coingecko.py` — CoinGecko free API: top-200 coins, market cap, categories, 24h volume
- `data/derivatives.py` — Funding rate, OI, long/short ratio from Binance futures API

### 1.3 DB schema (crypto.db)

```sql
-- OHLCV (multi-timeframe)
CREATE TABLE ohlcv (
    ticker TEXT NOT NULL,
    timeframe TEXT NOT NULL,  -- '5m','15m','1h','1d'
    timestamp INTEGER NOT NULL,  -- unix ms
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    UNIQUE(ticker, timeframe, timestamp)
);

-- Coin metadata (from CoinGecko)
CREATE TABLE coin_meta (
    ticker TEXT PRIMARY KEY,
    name TEXT,
    market_cap REAL,
    volume_24h REAL,
    category TEXT,
    listed_since TEXT,
    coingecko_id TEXT,
    is_active INTEGER DEFAULT 1,
    updated_at TEXT
);

-- Derivatives data
CREATE TABLE derivatives (
    ticker TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    funding_rate REAL,
    open_interest REAL,
    oi_change_pct REAL,
    long_short_ratio REAL,
    long_liq_1h REAL,
    short_liq_1h REAL,
    UNIQUE(ticker, timestamp)
);

-- Walk-forward scores
CREATE TABLE wf_scores (
    ticker TEXT NOT NULL,
    strategy TEXT NOT NULL,
    consistency_pct REAL,
    avg_return_pct REAL,
    avg_sharpe REAL,
    weighted_score REAL,
    windows_tested INTEGER,
    updated_at TEXT,
    UNIQUE(ticker, strategy)
);

-- Scan signals
CREATE TABLE crypto_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    strategy TEXT NOT NULL,
    score REAL,
    scan_time TEXT NOT NULL,
    tf_primary TEXT,          -- '15m' or '1h'
    tf_alignment TEXT,        -- comma-sep: '1h,1d'
    session TEXT,             -- 'US','EU','ASIA'
    regime TEXT,
    trap_score INTEGER,       -- 0-8
    agent_decision TEXT,      -- 'approve','veto','degraded'
    agent_rationale TEXT,
    fired INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Paper trades
CREATE TABLE crypto_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    strategy TEXT NOT NULL,
    direction TEXT NOT NULL,  -- 'LONG','SHORT'
    entry_price REAL,
    entry_time TEXT,
    exit_price REAL,
    exit_time TEXT,
    size_usdt REAL,
    pnl_usdt REAL,
    pnl_pct REAL,
    status TEXT DEFAULT 'OPEN',  -- 'OPEN','CLOSED','CANCELLED'
    exit_reason TEXT,
    signal_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Liquidity zones (pre-computed)
CREATE TABLE liquidity_zones (
    ticker TEXT NOT NULL,
    zone_type TEXT NOT NULL,  -- 'equal_high','equal_low','prev_day_high','prev_day_low','poc','vah','val'
    price_level REAL NOT NULL,
    strength INTEGER,        -- 1-5
    detected_at TEXT NOT NULL,
    timeframe TEXT,           -- '1h','1d'
    UNIQUE(ticker, zone_type, price_level, timeframe)
);
```

---

## Phase 2: Engine

### 2.1 Indicators (`engine/indicators.py`)
Clone from idx-walkforward-5001. Same functions: ATR, VWAP, VR, delta, VWMA, SMA, ADX, RSI, weekly trend. Add:
- `calc_cvd(df)` — cumulative volume delta
- `calc_choppiness(df)` — choppiness index
- `calc_atr_percentile(df, period=90)` — ATR as percentile

### 2.2 Strategies (`engine/strategies.py`)
Adapt 5 strategies from idx engine:
1. `strategy_orb_session()` — session-anchored ORB
2. `strategy_vol_weighted()` — cloned from idx strategy_vol_weighted
3. `strategy_vwap_reversion()` — cloned from idx, adapted for crypto VWAP
4. `strategy_volume_profile_poc()` — cloned from idx strategy_volume_profile_poc
5. `strategy_funding_contrarian()` — new, crypto-specific

### 2.3 Pattern Detector (`engine/pattern_detector.py`) — NEW
Detect chart patterns specified in research:
- Flag / pennant detection
- Double top / bottom (equal highs/lows)
- Wedge detection
- Wick reversal pattern (pin bar)
- Wick fill pattern
- Double wick rejection
- Liquidity grab pattern

### 2.4 Liquidity Zones (`engine/liquidity_zones.py`) — NEW
Pre-compute and update liquidity zones:
- Equal highs/lows (last 20 bars)
- Previous day H/L, previous week H/L
- Volume profile POC/VAH/VAL (1d and 1w)
- Level strength scoring (1-5)

### 2.5 Trap Filter (`engine/trap_filter.py`) — NEW
8-point checklist from research:
1. Volume confirmation check
2. Follow-through candle check
3. CVD alignment check
4. RSI context check
5. Funding rate check
6. Session quality check
7. Higher TF alignment check
8. Liquidity zone proximity check
Returns score 0-8 + list of failing checks.

### 2.6 Market Context (`engine/market_context.py`) — NEW
Pre-trade context:
- fetch BTC.D, TOTAL, USDT.D
- determine risk-on/risk-off
- session detection
- position size multiplier (0.5x / 1.0x)
- active narrative detection

### 2.7 Regime Filter (`engine/regime_filter.py`)
Adapt from idx: 3-class (BULL/BEAR/SIDEWAYS) on 1h instead of daily.
Same ADX + MA slope logic, retrained thresholds.

### 2.8 Walk-Forward (`engine/walkforward.py`)
Clone from idx `walkforward_multi.py`. Same 12/3-month split logic, adapted for crypto perpetual data.

---

## Phase 3: Agent Firm

### 3.1 Architecture
6-agent LangGraph DAG (drop flow, add derivatives):

```
SignalCandidate (with tf_primary, tf_alignment, session)
       │
       ▼
Stage 1 (parallel): technical ─┬─ derivatives ─┬─ regime ─┬─ news
                               │               │          │
Stage 2 (sequential): bull ───► bear ───► risk
                               │
                         approve / veto / degraded
```

### 3.2 Files to create/clone

| File | Source | Action |
|------|--------|--------|
| `agent_firm/__init__.py` | Clone | Same |
| `agent_firm/firm.py` | Clone + rewrite | New DAG, new context builder |
| `agent_firm/schemas.py` | Clone + modify | SignalCandidate gets tf_primary, tf_alignment, session |
| `agent_firm/config.py` | Clone | Same pattern, crypto env vars |
| `agent_firm/client.py` | Clone | Same DeepSeek client |
| `agent_firm/analytics.py` | Clone | Same |
| `agent_firm/smoke.py` | Clone | Adapted to crypto |
| `agent_firm/agents/technical.py` | Rewrite | Multi-TF OHLCV, wick analysis |
| `agent_firm/agents/derivatives.py` | NEW | CVD, funding, OI, liquidations |
| `agent_firm/agents/regime.py` | Rewrite | 1h regime, session-aware |
| `agent_firm/agents/news.py` | Rewrite | CryptoPanic API |
| `agent_firm/agents/bull.py` | Rewrite | Reads 5 analysts |
| `agent_firm/agents/bear.py` | Rewrite | Reads 5 analysts |
| `agent_firm/agents/risk.py` | Rewrite | 8-point trap check, session cooldown |
| `agent_firm/prompts/*.md` | Rewrite | All 7 prompts |

### 3.3 Prompts to write
- `technical_v1.md` — multi-TF OHLCV analysis, wick patterns, volume profile
- `derivatives_v1.md` — CVD, funding rate, OI, L/S ratio, liquidation analysis
- `regime_v1.md` — 1h ADX+MA, session context, market-wide regime
- `news_v1.md` — CryptoPanic headlines, sentiment, narrative alignment
- `bull_v1.md` — Advocate long, synthesize 5 analyst reports
- `bear_v1.md` — Advocate short, challenge bull thesis
- `risk_v1.md` — 8-point trap checklist, session cooldown, position sizing

---

## Phase 4: Screener + Scanner

### 4.1 Multi-TF Scanner (`screener/scanner.py`)
Core loop:
1. Fetch 1d candles → determine regime for each coin
2. Fetch 1h candles → run pattern detection + signal check
3. Fetch 15m candles → confirm signals
4. Run trap filter on confirmed signals
5. Pass surviving signals to agent firm
6. Log results to crypto_signals table

### 4.2 API Routes (`screener/routes.py`)
Flask blueprint `crypto_bp`, url_prefix `/api/crypto`:
- `GET /api/crypto/scan` — trigger scan, return signals
- `GET /api/crypto/signals` — recent signals
- `GET /api/crypto/coins` — active coin list with metadata
- `GET /api/crypto/coin/{ticker}` — detailed coin data
- `GET /api/crypto/liquidity-zones/{ticker}` — computed zones
- `GET /api/crypto/market-context` — BTC.D, TOTAL, session, risk level
- `GET /api/crypto/agent/status` — agent firm status (off/shadow/enforce)
- `POST /api/crypto/agent/config` — toggle agent mode

---

## Phase 5: Scheduler + Dashboard

### 5.1 Scheduler (`scheduler/jobs.py`)
24/7 APScheduler jobs:
- Every 15 min: multi-TF scan (US+EU sessions only)
- Every 1 hour: full scan (all sessions) + funding rate check
- Every 6 hours: OHLCV refresh (CCXT Binance)
- Every 12 hours: CoinGecko metadata refresh
- Daily 00:00 UTC: Walk-forward score refresh
- Every 4 hours: derivatives data refresh

### 5.2 Dashboard (`templates/crypto_dashboard.html`)
- Signal table (ticker, strategy, score, regime, session, trap score, agent decision)
- Market context panel (BTC.D, TOTAL, USDT.D, session, risk level)
- Coin detail view (chart, liquidity zones, patterns, signals)
- Agent firm status bar
- Paper trade tracking

---

## Phase 6: Integration

### 6.1 Smoke test
- Start app on port 5002
- Fetch BTC/USDT OHLCV from Binance
- Run strategy scan, verify signals fire
- Verify trap filter scores
- Verify agent firm evaluates (in shadow mode)
- Verify scheduler jobs run
- Verify dashboard renders

### 6.2 Telegram integration
- New bot for crypto alerts
- Signal format: ticker, strategy, score, session, trap score, agent decision

---

## File Manifest (complete)

```
crypto-screener/
├── app.py
├── config.py
├── requirements_crypto.txt
├── start.sh
├── data/
│   ├── __init__.py
│   ├── db.py
│   ├── fetcher.py
│   ├── coingecko.py
│   └── derivatives.py
├── engine/
│   ├── __init__.py
│   ├── indicators.py
│   ├── strategies.py
│   ├── pattern_detector.py
│   ├── liquidity_zones.py
│   ├── trap_filter.py
│   ├── regime_filter.py
│   ├── market_context.py
│   ├── walkforward.py
│   └── agent_firm/
│       ├── __init__.py
│       ├── firm.py
│       ├── schemas.py
│       ├── config.py
│       ├── client.py
│       ├── analytics.py
│       ├── smoke.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── technical.py
│       │   ├── derivatives.py
│       │   ├── regime.py
│       │   ├── news.py
│       │   ├── bull.py
│       │   ├── bear.py
│       │   └── risk.py
│       └── prompts/
│           ├── technical_v1.md
│           ├── derivatives_v1.md
│           ├── regime_v1.md
│           ├── news_v1.md
│           ├── bull_v1.md
│           ├── bear_v1.md
│           └── risk_v1.md
├── scheduler/
│   ├── __init__.py
│   └── jobs.py
├── screener/
│   ├── __init__.py
│   ├── scanner.py
│   └── routes.py
├── templates/
│   └── crypto_dashboard.html
└── static/
    └── (empty for now)
```

**Total: ~40 files. Estimated build time: 6-8 hours.**

---

*Ready to build. Execute Phase 1 first.*
