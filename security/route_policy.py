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
    "/api/signals/custom": OPERATOR,
    "/api/agent/status": VIEWER, "/api/agent/audit": VIEWER,
    "/api/agent/config": ADMIN,
    "/api/scheduler/run": OPERATOR,
    "/api/paper/config": {"GET": VIEWER, "POST": ADMIN},
    "/api/paper/open": OPERATOR, "/api/paper/close": OPERATOR,
    "/api/paper/clear_history": ADMIN, "/api/paper/summary": VIEWER,
    "/api/paper/report-telegram": OPERATOR,
    "/api/paper/premover_mode": {"GET": VIEWER, "POST": ADMIN},
    "/api/optimizer/run": OPERATOR,
    "/api/optimizer/result/<ticker>/<strategy>": VIEWER,
    "/api/scanner/adaptive_strategy/<ticker>": VIEWER,
    # --- portfolio ---
    "/api/portfolio/sectors": VIEWER, "/api/portfolio/backtest": OPERATOR,
    # --- screener blueprint (/api/screener prefix) ---
    "/api/screener/run": OPERATOR, "/api/screener/status": VIEWER,
    "/api/screener/results": VIEWER, "/api/screener/ticks": VIEWER,
    "/api/screener/cumdelta": VIEWER, "/api/screener/vpin": VIEWER,
    "/api/screener/vpin/multi": VIEWER, "/api/screener/vpin/scan": VIEWER,
    "/api/screener/lq45": VIEWER, "/api/screener/run_log": VIEWER,
    "/api/screener/columns": VIEWER, "/api/screener/presets": VIEWER,
    "/api/screener/fundamental": VIEWER,
    "/api/screener/stockbit/templates": VIEWER,
    "/api/screener/stockbit/run": OPERATOR,   # GET, but it launches a scrape run
    "/api/screener/brpt_filter": VIEWER,
    # --- screener_main blueprint ---
    "/api/screener/swing_onset": OPERATOR,
    "/api/sector/rotation": VIEWER, "/api/calendar/status": VIEWER,
    "/api/calendar/events": VIEWER, "/api/fastmover/summary": VIEWER,
    "/api/fastmover/run": OPERATOR,
    "/api/ticker/<ticker>/full": VIEWER, "/api/ticker/<ticker>/broker": VIEWER,
    "/api/strategy/list": VIEWER,
    "/api/strategy/markers/<path:strategy>/<ticker>": VIEWER,
    "/api/ticker/<ticker>/ohlcv": VIEWER,
    "/api/premover/watchlist": VIEWER, "/api/premover/run": OPERATOR,
    "/api/screener/reversal": VIEWER,
    # --- flow / market / dashboard ---
    "/api/flow/monitor": VIEWER, "/api/flow/check": OPERATOR,
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
}


def required_level(rule, method) -> str:
    spec = POLICY.get(rule, ADMIN)   # unknown rule -> fail closed
    if isinstance(spec, dict):
        return spec.get(method, ADMIN)
    return spec
