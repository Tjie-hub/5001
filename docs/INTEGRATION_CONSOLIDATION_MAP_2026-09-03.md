# Production OS Consolidation — 5001 / 5002 / 5003 → ONE app on 5002

Date: 2026-09-03
Status: Implemented (this document is the feature comparison + migration map that
drove the implementation; see the final migration report for outcomes).

## What the three applications actually are

| | Port | What it is | Codebase | Database |
|---|---|---|---|---|
| OLD Production OS | 5001 (gunicorn, 0.0.0.0, scheduler live) | "IDX Strategy Suite" — legacy template UI (Trades/Signals/Scanner/Backtest/Screener/Broker Flow/Portfolio-backtest) + React SPA (Decision Center/Watchlist/Ticker/Market/Search/Settings) | `/home/tjiesar/10 Projects/idx-walkforward-5001` @ `dev-9b6e380` | `data/walkforward.db` |
| CURRENT Production OS | 5002 (staging Flask, 127.0.0.1, scheduler off) | **The same codebase, same release, same DB** — identical index HTML and `/api/v1/health` release string | Same repo, same commit | Same SQLite file |
| Investment Dashboard | 5003 (nginx static + basic auth) | Single-file vanilla JS personal investment tracker (equities tranches, mutual funds, dividends, closed trades, overview analytics) + Google Sheets cloud sync + Yahoo prices via public CORS proxy | `/var/www/investment-dashboard` | localStorage + Google Sheets (Apps Script) |

**Key finding on 5001 vs 5002:** they are the same application at the same commit
(`dev-9b6e380`) sharing one database. 5001's only *operational* uniqueness is that
its gunicorn deployment runs the APScheduler + Telegram poller. There is **no
unique functionality and no unique data to recover from 5001**; nothing was migrated
from it. The "old vs current" distinction is purely which process you open in a browser.

**Key finding on 5003:** despite the "Investment Intelligence" label, 5003 contains
**portfolio tracking** (holdings/P&L/dividends), not signals/research/risk/decisions.
Those intelligence layers already exist in 5002 (watchlist candidates, market risk
engine, agent decisions, ticker research). So the honest mapping is:

- 5003's **portfolio ledger** → merges INTO the canonical 5002 Portfolio layer.
- 5003's **Overview dashboard** → becomes the Investment Dashboard tab of a new
  Investment Intelligence workspace, reading the canonical portfolio summary API.
- Signals / Opportunities / Research / Risk / Decisions → composed from existing
  5002 APIs (no new data models, no duplication).

## Feature comparison

| Feature | 5001 | 5002 | 5003 | Decision |
|---|---|---|---|---|
| Trades/Signals/Scanner/Backtest/Screener/Broker Flow UI | ✔ | ✔ (same) | ✘ | Keep 5002 |
| Decision Center, Watchlist, Ticker, Market, Search, Settings (SPA) | ✔ | ✔ (same) | ✘ | Keep 5002 |
| Sector portfolio **backtest** (`/portfolio`, `/api/portfolio/*`) | ✔ | ✔ | ✘ | Keep (untouched) |
| Paper trading positions/P&L (`paper_trades`) | ✔ | ✔ | ✘ | Keep (untouched; strategy sandbox ≠ real ledger) |
| Market risk score/breadth/flow/VPIN | ✔ | ✔ | ✘ | Keep; surface in Intelligence |
| Watchlist candidates / signals / agent decisions | ✔ | ✔ | ✘ | Keep; surface in Intelligence |
| Real equity transaction ledger w/ tranches + fees | ✘ | ✘ | ✔ | **Migrate into 5002 canonical tables** |
| Holdings math (avg cost, breakeven, net-if-sold, unrealized) | ✘ | ✘ | ✔ | **Reimplement server-side in 5002** |
| Mutual funds (NAV, redeem) open + closed | ✘ | ✘ | ✔ | **Migrate into 5002 canonical tables** |
| Dividend journal (gross/tax 10%/net) | ✘ | ✐ | ✔ | **Migrate into 5002 canonical tables** |
| Closed-trade journals (EQ + MF) | ✘ | ✐ (paper only) | ✔ | **Migrate into 5002 canonical tables** |
| Overview dashboard (value, cost, P&L, dividends, allocation) | ✘ | ✘ | ✔ | **Rebuild in 5002** (Portfolio tabs + Intelligence dashboard) |
| Live IDX prices | ✘ | ✘ (has OHLCV engine) | ✔ (Yahoo via CORS proxy) | **Server-side Yahoo fetch in 5002** (drops public CORS proxy) |
| Manual price overrides | ✘ | ✘ | ✔ | Migrate (`inv_prices`, source='manual') |
| Export/import JSON | ✘ | ✘ | ✔ | Migrate (`/api/v1/investments/export|import`) |
| Cloud sync | ✘ | ✘ | Google Sheets | **Not migrated** — 5002 SQLite is the canonical store; Sheets snapshot archived in `backups/` |
| Auth | token/role middleware | same | nginx basic auth only | **Unified on 5002 middleware**; basic auth retired with 5003 |

## Migration map (what was built)

1. **Canonical store** (`data/investments.py`, tables `inv_transactions`,
   `inv_closed_equity`, `inv_fund_positions`, `inv_dividends`, `inv_prices`) inside the
   single `data/walkforward.db` — one data model, no second DB.
2. **Versioned API** (`routes/v1/investments.py`, `/api/v1/investments/*`, standard
   `{ok,data,meta}` envelope) — holdings/summary computed server-side with 5003's
   exact fee model (buy 0.15%, sell 0.25%, div tax default 10%).
3. **Data migration** (`scripts/migrate_investment_dashboard_5003.py`) — imports the
   archived Google Sheets snapshot (live-fetch fallback) into the canonical tables,
   idempotently, with a normalizer that maps 5003's UTC ISO dates to WIB dates.
4. **Portfolio page** (`templates/portfolio.html`) — gains Overview / Holdings /
   Mutual Funds / Dividends / Closed tabs beside the existing Backtest panel.
   One portfolio page, one portfolio layer.
5. **Investment Intelligence workspace** (SPA `/intelligence`) — Dashboard, Signals,
   Opportunities, Risk, Decisions, Research tabs; composes existing
   `/api/v1/market/summary`, `/api/v1/watchlists/*`, `/api/v1/registry/status`,
   `/api/v1/scheduler` + the new investments summary. References the canonical
   portfolio; never re-stores it.
6. **Navigation** — SPA sidebar gains "Investment Intelligence"; legacy topbar gains
   the same link. One nav, two consistent shells.
7. **Auth** — every new route classified in `security/route_policy.py`
   (reads VIEWER, writes OPERATOR), so the existing token/role middleware covers the
   integrated features identically on 5002.
8. **Not migrated (intentionally):** 5003's localStorage persistence, Google Sheets
   sync (superseded by the canonical DB), the allorigins CORS proxy (replaced by a
   server-side fetcher), nginx basic auth (superseded by 5002 auth), 5001's process
   role (only the scheduler — a deployment concern, see retirement notes).

## Data safety

- Pre-change snapshot: `backups/migration_5003_20260903/walkforward_pre_integration_20260903.db`
  (consistent SQLite backup, taken live via the backup API).
- 5003 source data: `backups/migration_5003_20260903/investment_dashboard_sheets_snapshot_20260903.json`
  (fetched from the live Sheets backend before any change).
- All new tables are additive (`CREATE TABLE IF NOT EXISTS`); no existing table,
  row, or route was altered or dropped.
