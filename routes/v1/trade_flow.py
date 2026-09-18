"""Trade Flow API (Ticker workspace — cumulative buy/sell flow + price).

Thin controller over engine.trade_flow.get_trade_flow(), the same
"engine computes, route wraps the envelope" pattern as ticker_detail.py.
Read-only over production stockbit_flow_bars; no classification or
threshold logic lives here (see engine/trade_flow.py's docstring for the
verified vendor semantics and the Big Money non-definition).
"""
import re
from datetime import date as _date

from flask import request

from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok

import config
from engine.trade_flow import SUPPORTED_METRICS, get_trade_flow

# Same symbol rule as ticker_detail.py — keep the two in sync.
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")


def _parse_date(value: str, field: str) -> str:
    try:
        parsed = _date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ApiError(
            "INVALID_DATE", 400,
            f"{field} must be an ISO date (YYYY-MM-DD), got {value!r}",
            details={field: value},
        )
    return parsed.isoformat()


@api_v1_bp.route("/tickers/<symbol>/trade-flow", methods=["GET"])
def ticker_trade_flow_route(symbol: str):
    """Cumulative buy/sell trade flow for one ticker over a date range.

    Query params:
      start  — YYYY-MM-DD inclusive (default: latest available session)
      end    — YYYY-MM-DD inclusive (default: start, or latest session)
      metric — 'value' (the only metric the data supports today)
    """
    sym = symbol.strip().upper()
    if not _SYMBOL_RE.fullmatch(sym):
        raise ApiError("INVALID_SYMBOL", 400,
                       f"'{symbol}' is not a valid IDX ticker symbol")

    metric = (request.args.get("metric") or "value").strip().lower()
    if metric not in SUPPORTED_METRICS:
        raise ApiError(
            "UNSUPPORTED_METRIC", 400,
            f"metric must be one of {', '.join(SUPPORTED_METRICS)}",
            details={"metric": metric, "supported": list(SUPPORTED_METRICS)},
        )

    start_raw = request.args.get("start")
    end_raw = request.args.get("end")
    start_date = _parse_date(start_raw, "start") if start_raw else None
    end_date = _parse_date(end_raw, "end") if end_raw else None
    if start_date and end_date and start_date > end_date:
        raise ApiError(
            "INVALID_DATE_RANGE", 400,
            f"start ({start_date}) is after end ({end_date})",
            details={"start": start_date, "end": end_date},
        )

    flow = get_trade_flow(config.DB_PATH, sym, start_date, end_date, metric)
    if flow is None:
        raise ApiError(
            "NO_TRADE_FLOW_DATA", 404,
            f"No intraday trade-flow data exists for {sym}",
            details={"symbol": sym},
        )
    return ok(flow)
