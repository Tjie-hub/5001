# Task 2B-2 — Operational Metrics API

**Status:** Approved 2026-08-06 (Production Engine Phase 2, Workstream 2B, Task 2 of 4).
Builds on the frozen v1 foundation and 2B-1's scheduler API; no framework changes.

## Sources audited

- `engine/job_status.get_status_summary()` — already the data behind `/api/v1/status/summary`;
  reused as-is for `/api/v1/metrics/jobs` (same call, second URL — deliberate exposure under
  a metrics-oriented path, not a reinvention).
- `scheduler.get_scheduler()` (2B-1) — availability + job count, reused for the rollup.
- App-level "engine" metrics (open trades, today's signals, agent decisions, OHLCV coverage,
  market risk score, avg VPIN, last scan) only existed as **inline SQL inside `app.py`'s
  Prometheus `/metrics` route** (`prometheus_metrics()`) — no service-layer function to call.
  Per this task's own instruction ("if a small reusable service helper is needed... place it
  in the service layer"), a new `engine/metrics.py::get_engine_metrics()` extracts that same
  query set as a plain function. `app.py`'s Prometheus route is **not touched** — refactoring
  a route other systems may already be scraping is out of this task's scope
  ("no unrelated file modifications"); the two now read the same tables via separate query
  code, which is an accepted minor duplication in exchange for not risking a live scrape
  target.
- **Defect found, not fixed here:** `app.py`'s Prometheus query for market risk
  (`SELECT risk_score FROM market_risk_log ORDER BY computed_at DESC LIMIT 1`) references
  columns that don't exist — the real schema (`engine/risk_alert.py`) is `score`/`created_at`,
  not `risk_score`/`computed_at` (confirmed correct usage elsewhere: `engine/trade_plan.py`
  queries `score`). The Prometheus route's own `_q()` helper swallows the error, so
  `idx_market_risk_score` has silently always reported `NaN`. `engine/metrics.py` uses the
  correct columns (`score`, `created_at`) since it's new code, not a literal reuse of the
  broken query — but the pre-existing bug in `app.py` itself is left as-is (not this task's
  file to touch) and flagged here for the record.
- Health subsystem, watchlist/snapshot statistics: left for **Task 2B-4 (Health Expansion)**,
  which explicitly owns that composition — not duplicated here.

## Endpoints

- `GET /api/v1/metrics/jobs` — `job_status.get_status_summary()` verbatim: `{total, success,
  failed, skipped, running}`.
- `GET /api/v1/metrics/engine` — `engine.metrics.get_engine_metrics()`: `{open_trades,
  signals_today_total, signals_today_buy, signals_today_sell, agent_decisions_today,
  ohlcv_tickers_today, market_risk_score, avg_vpin_today, last_scan_at}`. Per-query fail-soft
  (`None` on a single bad query, matching the Prometheus route's own `_q()` pattern) but no
  bespoke error handling beyond that — a total subsystem failure (e.g. `db_connect` itself
  raising) falls through to the existing generic 500 envelope handler from the frozen
  foundation, same as `/api/v1/status/*` and `/api/v1/scheduler/*` today.
- `GET /api/v1/metrics` — rollup: `{"jobs": ..., "engine": ..., "scheduler": {"available",
  "job_count"}}`, each key built from the same three calls above (the scheduler slice is a
  few inline lines reusing `scheduler.get_scheduler()`, not a new abstraction).
- All three: `VIEWER`.

## Explicitly out of scope

New metric computation of any kind (duration percentiles, watchlist/snapshot counts — no
existing aggregation function for either), and any change to `app.py`'s Prometheus endpoint.
