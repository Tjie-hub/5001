"""Route → minimum-role policy (security hardening Phases 1-2).

Keyed by url_map rule string. Value is a level, or {method: level} when
GET/POST semantics differ. Unlisted rules require ADMIN (fail closed);
tests/security/test_route_policy.py makes an unclassified route a CI failure.

  public   — no credential (health probe, telegram webhook w/ own HMAC, login)
  viewer   — read-only data/UI
  operator — manual scans, backtests, paper-trade actions (state-changing ops)
  admin    — configuration, provider/agent controls, maintenance
The internal-scheduler role ranks with operator (see security.auth.ROLE_RANK).
"""
from security.auth import PUBLIC, VIEWER, OPERATOR, ADMIN

POLICY = {
    # --- core app ---
    "/health": PUBLIC,
    "/static/<path:filename>": PUBLIC,
    "/": VIEWER, "/backtest/multi": VIEWER, "/screener": VIEWER,
    "/signal-scanner": VIEWER, "/portfolio": VIEWER, "/dashboard": VIEWER,
    "/sector": VIEWER, "/dive/<ticker>": VIEWER, "/metrics": VIEWER,
    # --- frontend/ SPA stop-gap serving (ADR-005/U-8 still undecided) ---
    "/assets/<path:filename>": PUBLIC, "/favicon.svg": PUBLIC,
    "/<path:path>": VIEWER,
    # --- auth ---
    "/auth/login": PUBLIC, "/auth/logout": PUBLIC, "/auth/whoami": PUBLIC,
    # --- telegram ---
    "/telegram/updates": PUBLIC,          # protected by its own HMAC secret
    "/telegram/status": VIEWER,
    "/telegram/setup": ADMIN, "/telegram/start-polling": ADMIN,
    "/telegram/stop-polling": ADMIN, "/telegram/poll-updates": ADMIN,
    # --- backtest / signals / paper ---
    "/api/backtest/scan_all": OPERATOR, "/api/backtest/quick_scan": OPERATOR,
    "/api/backtest/precompute": OPERATOR, "/api/backtest/multi_quick_scan": OPERATOR,
    "/api/backtest/roll": OPERATOR, "/api/backtest/multi": OPERATOR,
    "/api/backtest/walkforward": OPERATOR, "/api/backtest/equity": OPERATOR,
    "/api/backtest/trades/<ticker>/<strategy_name>": VIEWER,
    "/api/signals/today": VIEWER, "/api/signals/scheduled": VIEWER,
    # 2026-08-19: moved to ADMIN -- confirmed external side effect (Telegram
    # send and/or external API call), see Audit/PRODUCTION_ENGINE_BACKLOG.md.
    "/api/signals/custom": ADMIN,
    "/api/agent/status": VIEWER, "/api/agent/audit": VIEWER,
    "/api/agent/config": ADMIN,
    "/api/scheduler/run": ADMIN,   # 2026-08-19: incident route, see backlog
    "/api/paper/config": {"GET": VIEWER, "POST": ADMIN},
    "/api/paper/open": ADMIN, "/api/paper/close": ADMIN,
    "/api/paper/clear_history": ADMIN, "/api/paper/summary": VIEWER,
    "/api/paper/report-telegram": ADMIN,
    "/api/paper/premover_mode": {"GET": VIEWER, "POST": ADMIN},
    "/api/optimizer/run": OPERATOR,
    "/api/optimizer/result/<ticker>/<strategy>": VIEWER,
    "/api/scanner/adaptive_strategy/<ticker>": VIEWER,
    # --- portfolio ---
    "/api/portfolio/sectors": VIEWER, "/api/portfolio/backtest": OPERATOR,
    # --- screener blueprint (/api/screener prefix) ---
    "/api/screener/run": ADMIN, "/api/screener/status": VIEWER,
    "/api/screener/results": VIEWER, "/api/screener/ticks": VIEWER,
    "/api/screener/cumdelta": VIEWER, "/api/screener/vpin": VIEWER,
    "/api/screener/vpin/multi": VIEWER, "/api/screener/vpin/scan": VIEWER,
    "/api/screener/lq45": VIEWER, "/api/screener/run_log": VIEWER,
    "/api/screener/columns": VIEWER, "/api/screener/presets": VIEWER,
    "/api/screener/fundamental": VIEWER,
    "/api/screener/stockbit/templates": VIEWER,
    "/api/screener/stockbit/run": ADMIN,   # GET, but it launches a scrape run
    "/api/screener/brpt_filter": VIEWER,
    # --- screener_main blueprint ---
    "/api/screener/swing_onset": ADMIN,
    "/api/sector/rotation": VIEWER, "/api/calendar/status": VIEWER,
    "/api/calendar/events": VIEWER, "/api/fastmover/summary": VIEWER,
    "/api/fastmover/run": OPERATOR,
    "/api/ticker/<ticker>/full": VIEWER, "/api/ticker/<ticker>/broker": VIEWER,
    "/api/strategy/list": VIEWER,
    "/api/strategy/markers/<path:strategy>/<ticker>": VIEWER,
    "/api/ticker/<ticker>/ohlcv": VIEWER,
    "/api/premover/run": ADMIN,
    # --- flow / market / dashboard ---
    "/api/flow/monitor": VIEWER, "/api/flow/check": ADMIN,
    "/api/broker-flow/<ticker>": VIEWER, "/api/broker-flow/dates/<ticker>": VIEWER,
    "/api/market/accdist": VIEWER, "/api/market/vpin": VIEWER,
    "/api/market/technicals": VIEWER, "/api/market/breadth": VIEWER,
    "/api/market/risk": VIEWER,
    "/api/dashboard/risk": VIEWER, "/api/dashboard/signals": VIEWER,
    "/api/dashboard/strategy_pnl": VIEWER, "/api/dashboard/watchlist": VIEWER,
    "/api/dashboard/unified-watchlist": VIEWER, "/api/dashboard/checklist": VIEWER,
    "/api/liquidity/impact": VIEWER, "/api/liquidity/ticker/<ticker>": VIEWER,
    "/api/ticker/<ticker>/ohlcv/<freq>": VIEWER,
    # --- chart ---
    "/api/chart/<ticker>/indicators": VIEWER, "/api/chart/<ticker>/delta": VIEWER,
    "/api/chart/tv/sync": OPERATOR, "/api/chart/tv/status": VIEWER,
    # --- API v1 (Production Engine Phase 2, Workstream A) ---
    "/api/v1/": VIEWER, "/api/v1/openapi.json": VIEWER,
    "/api/v1/status/jobs/running": VIEWER, "/api/v1/status/jobs/latest": VIEWER,
    "/api/v1/status/jobs/failed": VIEWER, "/api/v1/status/jobs/history": VIEWER,
    "/api/v1/status/summary": VIEWER,
    "/api/v1/scheduler": VIEWER, "/api/v1/scheduler/jobs": VIEWER,
    "/api/v1/scheduler/jobs/<job_id>": VIEWER,
    "/api/v1/metrics": VIEWER, "/api/v1/metrics/jobs": VIEWER,
    "/api/v1/metrics/engine": VIEWER,
    "/api/v1/config": VIEWER, "/api/v1/config/runtime": VIEWER,
    "/api/v1/health": VIEWER,
    "/api/v1/watchlists/current": VIEWER, "/api/v1/watchlists/history": VIEWER,
    "/api/v1/watchlists/diff": VIEWER, "/api/v1/watchlists/persistent": VIEWER,
    "/api/v1/watchlists/<date_str>": VIEWER,
    "/api/v1/snapshots": VIEWER, "/api/v1/snapshots/<date_str>": VIEWER,
    "/api/v1/reports": VIEWER, "/api/v1/reports/<date_str>": VIEWER,
    "/api/v1/candidates": VIEWER, "/api/v1/candidates/<date_str>": VIEWER,
    "/api/v1/candidates/screening": VIEWER,
    "/api/v1/candidates/reversal-watchlist": VIEWER,
    "/api/v1/candidates/premover-watchlist": VIEWER,
    "/api/v1/version": VIEWER, "/api/v1/capabilities": VIEWER,
    "/api/v1/resources": VIEWER,
    "/api/v1/registry/status": VIEWER,
    "/api/v1/market/summary": VIEWER,
    "/api/v1/search/instruments": VIEWER,
    "/api/v1/tickers/<symbol>": VIEWER,
    "/api/v1/tickers/<symbol>/trade-flow": VIEWER,
    "/api/v1/runtime": VIEWER,
    # --- investments (consolidation 2026-09-03: ex-5003 canonical ledger) ---
    "/api/v1/investments/summary": VIEWER,
    "/api/v1/investments/holdings": VIEWER,
    "/api/v1/investments/transactions": {"GET": VIEWER, "POST": OPERATOR},
    "/api/v1/investments/transactions/<int:txn_id>": {"DELETE": OPERATOR},
    "/api/v1/investments/dividends": {"GET": VIEWER, "POST": OPERATOR},
    "/api/v1/investments/dividends/<int:row_id>": {"DELETE": OPERATOR},
    "/api/v1/investments/funds": {"GET": VIEWER, "POST": OPERATOR},
    "/api/v1/investments/funds/<fund_id>/redeem": {"POST": OPERATOR},
    "/api/v1/investments/funds/<fund_id>/nav": {"POST": OPERATOR},
    "/api/v1/investments/funds/<fund_id>": {"DELETE": OPERATOR},
    "/api/v1/investments/closed-equity": {"GET": VIEWER, "POST": OPERATOR},
    "/api/v1/investments/closed-equity/<int:row_id>": {"DELETE": OPERATOR},
    "/api/v1/investments/prices": {"GET": VIEWER, "POST": OPERATOR},
    "/api/v1/investments/prices/refresh": {"POST": OPERATOR},
    "/api/v1/investments/export": VIEWER,
    "/api/v1/investments/import": {"POST": OPERATOR},
}


def required_level(rule, method) -> str:
    spec = POLICY.get(rule, ADMIN)   # unknown rule -> fail closed
    if isinstance(spec, dict):
        return spec.get(method, ADMIN)
    return spec
