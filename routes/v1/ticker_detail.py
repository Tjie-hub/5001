"""Ticker detail API (Production Decision OS — Ticker workspace, D4 slice 1).

Thin controller over engine.ticker_detail.get_ticker_detail() — the same
"engine computes, route wraps the envelope" pattern as every other v1 read
model (search.py -> engine/instrument_search.py, market.py ->
engine/dashboard.py). The payload is assembled exclusively from production
tables (ohlcv, stockbit_flow, broker_flow, scheduled_signals,
watchlist_snapshot, agent_decisions, paper_trades, idx_tickers) and the
production admission chain (engine.admission + scanner's regime map), so the
Ticker workspace renders the same reality the scanner trades on.
"""
import re

from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok

import config
from engine.ticker_detail import get_ticker_detail

# IDX symbols: letters/digits with optional .- separators, at most 10 chars.
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")


@api_v1_bp.route("/tickers/<symbol>", methods=["GET"])
def ticker_detail_route(symbol: str):
    """Production detail for one ticker (all sections production-derived)."""
    sym = symbol.strip().upper()
    if not _SYMBOL_RE.fullmatch(sym):
        raise ApiError("INVALID_SYMBOL", 400,
                       f"'{symbol}' is not a valid IDX ticker symbol")

    detail = get_ticker_detail(config.DB_PATH, sym)
    if detail is None:
        raise ApiError("TICKER_NOT_FOUND", 404,
                       f"Ticker {sym} is not in the production universe",
                       details={"symbol": sym})
    return ok(detail)
