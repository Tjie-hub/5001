# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An Indonesian stock market (IDX) algorithmic trading suite running as a Flask app on port 5001. It scans IDX30/LQ45/IDX80 tickers with multiple quantitative strategies, manages paper trades with automatic SL/TP, fetches intraday flow data from Stockbit, and sends Telegram alerts. A multi-agent LLM pipeline (LangGraph + DeepSeek) optionally reviews signals before they trigger trades.

All times are in **WIB (Asia/Jakarta, UTC+7)**. IDX market hours: 09:00–15:30 WIB Mon–Fri.

---

## Commands

**Run the app:**
```bash
./start.sh          # production (sets SECTORS_APP_MODE=shadow)
python app.py       # direct
```

**Run all tests:**
```bash
pytest
```

**Run a single test:**
```bash
pytest tests/test_indicators.py::TestCalcAtr::test_returns_series
pytest tests/agent_firm/test_firm.py -k "test_evaluate"
```

**Manual data operations:**
```bash
python3 flow_filter.py                     # fetch flow for all tickers, save to DB
python3 flow_filter.py BBCA BRPT TLKM     # quick test for specific tickers (no DB write)
python3 stockbit_fetcher.py               # fetch keystats for IDX80
python3 stockbit_fetcher.py flow          # flow fetch for IDX80
python3 auto_token.py --check             # check if Stockbit JWT is still valid
python3 auto_token.py                     # headless token refresh via Playwright
python3 scheduler/__init__.py --once      # run daily_signal_scan once and exit
```

---

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Purpose |
|---|---|
| `DB_PATH` | SQLite DB path (default: `data/walkforward.db`) |
| `TELEGRAM_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Chat ID for alerts |
| `AGENT_FIRM_ENABLED` | Enable LLM agent review (default: `false`) |
| `AGENT_FIRM_ENFORCE` | If true, veto blocks trade (default: `false` = observe only) |
| `DEEPSEEK_API_KEY` | DeepSeek API key for agent firm |
| `STOCKBIT_USER` / `STOCKBIT_PASS` | Stockbit credentials for `auto_token.py` |
| `SECTORS_APP_MODE` | `shadow` (log only) or `enforce` |

The Stockbit JWT token is stored in `.stockbit_token` (gitignored). The agent firm kill switch is `/tmp/agent_firm.disable` — creating this file disables the firm instantly without a restart.

---

## Architecture

### Entry Point & Blueprints (`app.py`)

Flask app registers these blueprints:
- `backtest_multi_bp` (`routes_backtest_multi.py`) — `/api/backtest/multi`
- `screener_bp` (`screener/routes.py`) — `/api/screener/*`
- `telegram_bp` (`routes/telegram.py`) — webhook + polling loop
- `flow_bp` (`routes/flow.py`) — flow confirmation endpoints
- `screener_main_bp` (`routes/screener.py`) — screener UI routes
- `backtest_bp` (`routes/backtest.py`) — single-ticker backtest
- `portfolio_bp` (`routes/portfolio.py`) — portfolio/trade management

On startup, `app.py` also calls `start_scheduler()` (APScheduler cron jobs) and spawns a Telegram polling thread.

### Config (`config.py`)

Central env config. **All modules should `from config import DB_PATH, TELEGRAM_TOKEN, ...`** instead of calling `os.getenv()` directly. Exception: `app.py` and `scheduler/` retain their own `os.getenv()` calls for `importlib.reload()` compatibility in tests.

### Database (`data/db.py`)

Single SQLite file: `data/walkforward.db`. Key tables:

| Table | Purpose |
|---|---|
| `ohlcv` | Daily OHLCV price data, indexed by ticker |
| `idx_tickers` | Active ticker registry with fetch status |
| `paper_trades` | Open/closed paper trades |
| `scheduled_signals` | Signals from multi-strategy scan |
| `agent_decisions` | LLM agent firm decisions |
| `agent_traces` | Per-agent LLM call details |
| `stockbit_flow` | Daily flow data from Stockbit |
| `stockbit_flow_bars` | 1-minute intraday tradebook bars |
| `broker_flow` | Broker-level flow data |
| `wf_scores` | Walk-forward strategy scores per ticker |
| `daily_screen` | Intraday screener results with VPIN labels |
| `news_mentions` | RSS news mentions per ticker |

Schema is managed inline via `init_db()` and `init_agent_firm_tables()` — no migration framework; `data/db.py` is the source of truth. One-off schema patches are in `migrations/applied/`.

### Ticker Universe (`data/fetcher.py`)

Three static lists: `IDX30`, `LQ45`, `IDX80` (cumulative subsets). `load_all_tickers()` reads the live `idx_tickers` DB table, falling back to `idx_master.csv`, then `IDX80`. OHLCV is fetched from yfinance using `.JK` suffix (e.g., `BBCA.JK`).

### Strategy Engine (`engine/`)

- **`engine/strategies.py`** — 10+ named strategies: `strategy_momentum`, `strategy_vwap_reversion`, `strategy_conservative`, `strategy_volume_profile_poc`, `strategy_inside_bar_breakout`, `strategy_nr7_breakout`, `strategy_orb`, `strategy_swing_trend`, `strategy_trend_following_breakout`, `strategy_vol_weighted`. Each returns a list of `Trade` dataclass instances.
- **`engine/walkforward_multi.py`** — Runs all strategies across rolling time windows, scores them, produces `wf_scores` ranking.
- **`engine/regime_filter.py`** — `RegimeClassifier` detects BULL/BEAR/SIDEWAYS per ticker from ADX, MA slope, and vol metrics. `strategy_regime_adaptive` auto-selects strategies based on regime.
- **`engine/indicators.py`** — Pure pandas functions: `calc_atr`, `calc_vwap`, `calc_adx`, `calc_sma`, `calc_vol_ratio`, `calc_delta`, `calc_weekly_trend`, etc.

Trade constants: commission buy 0.15%, sell 0.25%, slippage 0.10%. Position sizing: 2% risk per trade, max 30% capital, max 5 open positions. See `rule.md` for SL/TP logic.

### Scheduler (`scheduler/`)

APScheduler `BackgroundScheduler` in WIB timezone. Key jobs:

| Time (WIB) | Job |
|---|---|
| 09:05, 10:05, 11:05, 13:35, 14:35 | Multi-strategy signal scan + intraday screener |
| 09:30–15:15 hourly | Flow fetch from Stockbit |
| 09:00–15:00 :05 | Open trade monitor |
| 16:00 | Daily signal scan + Telegram report |
| 16:30 | Pre-mover EOD scan |
| 17:00 | News fetch (Google News RSS) |
| 17:15 | Flow + broker report |
| 17:30 | Daily fetch report |
| 20:15 | Broker flow fetch |
| Fri 16:00 | WF score refresh |

`scheduler/__init__.py` re-exports everything from `scanner.py`, `jobs.py`, `reports.py`, and `utils.py` — import from the package, not the submodules.

### Flow Data (`flow_filter.py`, `stockbit_fetcher.py`)

`flow_filter.py` is both a CLI tool and a library. It fetches 1-minute tradebook from Stockbit's internal API using the JWT in `.stockbit_token`, analyzes smart money flow (buy/sell pressure, composite score, verdict), and writes to `stockbit_flow` and `stockbit_flow_bars`. `auto_token.py` refreshes the JWT via Playwright headless browser.

### Paper Trading (`paper_trade.py`, `monitor.py`)

`paper_trade.py` manages open positions: entry sizing (ATR-based), SL/TP calculation, trailing stop logic, and auto-close. `monitor.py` is the intraday monitor that checks open trades every ~30 min against SL/TP, VPIN spikes, momentum reversal, and flow reversal, sending Telegram alerts.

SL priority: (1) explicit SL from screener, (2) 2×ATR14, (3) config default 2.5%. TP: swing high detection or ATR-based, min 2:1 R/R enforced. Swing Trend trades have 7 additional exit rules (R1–R7, see `rule.md`).

### Agent Firm (`engine/agent_firm/`)

A LangGraph DAG that reviews quant signal candidates before trade execution. **Off by default** (`AGENT_FIRM_ENABLED=false`).

**Pipeline (linear DAG):**
1. `build_context` — fetches 60d OHLCV, broker flow, stockbit flow, wf_scores, news, open trades from DB
2. `run_analysts` — 4 parallel async calls: `technical`, `flow`, `regime`, `news` agents
3. `run_bull` → `run_bear` — debate phase (sequential)
4. `run_risk` — Risk Manager makes final `approve`/`veto` decision
5. `persist` — writes `agent_decisions` + `agent_traces` to DB

**Decision states:** `approve` | `veto` | `bypassed` (firm disabled) | `degraded` (LLM failure, fail-open)

**LLM:** DeepSeek via OpenAI SDK (`engine/agent_firm/client.py`). Each agent loads its system prompt from `engine/agent_firm/prompts/<role>_v1.md`. Each `AgentResult` tracks token counts and cost.

**Config env vars:** `AGENT_FIRM_ENABLED`, `AGENT_FIRM_ENFORCE`, `DEEPSEEK_API_KEY`, `AGENT_FIRM_MODEL`, `AGENT_FIRM_DAILY_CAP`, `TAVILY_API_KEY` (for web search tool).

Public API: `firm.evaluate(candidates)` (sync, scheduler-facing) and `firm.evaluate_async(candidates, client)` (async, for tests).

### Tests (`tests/`)

`pytest.ini` sets `asyncio_mode = auto` and `testpaths = tests`. Agent firm tests use the `tmp_db` fixture (`tests/agent_firm/conftest.py`) which creates a temp SQLite DB, monkeypatches `DB_PATH`, and reloads `data.db`. External API calls (DeepSeek, Stockbit) are mocked via `respx` or `unittest.mock.AsyncMock`.

---

## Key Conventions

- **`config.py` is the single env source** — do not call `os.getenv()` directly in new modules; add new settings to `config.py` and import from there.
- **DB connection pattern:** `data.db.get_db()` returns a connection with `row_factory = sqlite3.Row`; always close manually or use `get_db_context()`.
- **Schema changes:** Add idempotent `ALTER TABLE` or `CREATE TABLE IF NOT EXISTS` in `data/db.py` (for core tables) or a new `migrations/applied/patch_*.py`. Never use a migration framework.
- **Agent prompts are versioned:** System prompts live in `engine/agent_firm/prompts/<role>_<version>.md`. Increment the version filename and update `PROMPT_VERSION` in the agent module when changing prompts.
- **Strategies are pure functions:** Each strategy in `engine/strategies.py` takes a DataFrame + capital params and returns `list[Trade]`. No side effects.
- **`_archive/`** contains superseded scripts — do not import from it.
