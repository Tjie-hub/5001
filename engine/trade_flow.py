"""engine/trade_flow.py — per-ticker cumulative trade-flow read model.

Backs GET /api/v1/tickers/<symbol>/trade-flow (Ticker workspace "Trade
Flow" section). Same conventions as engine/ticker_detail.py: pure
aggregation over existing production tables, read-only connection,
fail-soft sections, no new data source and no new classification rule.

Source table: stockbit_flow_bars (Stockbit order-trade/trade-book/chart,
time_interval=1m — the same vendor surface Stockbit's own trade-flow view
renders). Vendor semantics, verified 2026-09-04 against the broker-flow-v001
snapshot and stockbit_fetcher.py/_parse_bars:

  * buy_lot / sell_lot / buy_freq / sell_freq are CUMULATIVE session totals
    through bar_time (monotone within a session; reset at each session open;
    the first bar absorbs the opening auction). Cross-checks: bars' final
    cumulative buy+sell for TOWR 2026-09-01 ≈ the ticks table's final
    cumulative volume; summing the cumulative series does NOT equal the day
    total, so de-cumulation is required before any per-minute maths.
  * net_value is the PER-MINUTE net traded value (IDR) — its session sum
    equals the day's net value (TOWR 2026-09-01: −7.198 B IDR, consistent
    with the cumulative lot totals at the session's price level).
  * price is the minute's price (IDR).

Derived series (the only computation this module adds):
  delta_buy(t)  = buy_lot(t) − buy_lot(t−1)   (≥ 0; negative ⇒ vendor
                revision, clamped to 0 and counted in anomaly_minutes)
  buy_value(t)  = delta_buy(t) × lot_shares × price(t)
  sell_value(t) = delta_sell(t) × lot_shares × price(t)
  cum_buy(t)    = Σ buy_value over all selected sessions ≤ t (chained
                across sessions in chronological order)
  cum_sell(t)   = Σ sell_value, same chaining
  net_flow(t)   = cum_buy(t) − cum_sell(t)
  price(t)      = the vendor minute price, passed through

lot_shares = 100 (1 IDX regular-board lot = 100 shares) — the same
convention flow_filter.py already uses (avg_vol / 100 → lots). Buy/sell
classification is the vendor's aggressor split exactly as ingested; this
module does not re-classify anything and introduces no threshold.

Big Money: production has NO trade-size classification (no per-trade data —
the bars are 1-minute aggregates — and flow_filter's `smart_money` is a
session-shape verdict, not a size cut), so the big_money filter is reported
as unavailable rather than invented.

Investor / trade-type: the intraday bars carry neither an investor split
(broker_flow.investor_type is EOD per-broker-side only) nor a non-regular
board (ingestion queries the regular board only), so only "all" / "regular"
are advertised as supported.
"""
from __future__ import annotations

import logging
import sqlite3
from data.db import connect as db_connect
from datetime import datetime

logger = logging.getLogger(__name__)

# 1 IDX regular-board lot = 100 shares (flow_filter.py convention).
LOT_SHARES = 100

# Transport cap: at most this many points per series reach the browser.
# TOWR-sized single days are 335 bars; a multi-session range can exceed
# this, so series are step-downsampled (index-strided, terminal point kept).
MAX_POINTS = 1500

SUPPORTED_METRICS = ("value",)

_BIG_MONEY_REASON = (
    "No production trade-size classification exists: stockbit_flow_bars are "
    "1-minute aggregates (no per-trade sizes) and flow_filter smart_money is "
    "a session-shape verdict, not a size threshold. Left disabled rather "
    "than inventing a cutoff."
)


def _connect_ro(db_path: str) -> sqlite3.Connection:
    conn = db_connect(db_path, read_only=True)
    conn.row_factory = None
    return conn


def _norm_hhmm(bar_time: str) -> str:
    """bar_time is stored 'HH:MM'; tolerate 'HH:MM:SS' defensively."""
    parts = bar_time.split(":")
    return ":".join(parts[:2]) if len(parts) > 2 else bar_time


def get_trade_flow(
    db_path: str,
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    metric: str = "value",
) -> dict | None:
    """Cumulative buy/sell trade flow for `symbol` over an inclusive date range.

    Returns None when the ticker has no stockbit_flow_bars rows at all (the
    route turns that into a 404 envelope). A range with no matching sessions
    returns the available-coverage envelope with empty series instead — the
    requested window simply had no intraday flow, which is production truth
    the UI must show, not an error.
    """
    sym = symbol.strip().upper()
    if metric not in SUPPORTED_METRICS:
        raise ValueError(f"unsupported metric: {metric!r}")
    conn = _connect_ro(db_path)
    try:
        span = conn.execute(
            "SELECT MIN(trade_date), MAX(trade_date) FROM stockbit_flow_bars "
            "WHERE ticker = ?",
            (sym,),
        ).fetchone()
        if span is None or span[0] is None:
            return None
        first_available, last_available = span[0], span[1]

        # Default window: the latest available session (single day), the same
        # default the vendor app shows when you open the page.
        if not start_date and not end_date:
            start_date, end_date = last_available, last_available
        elif not start_date:
            start_date = end_date
        elif not end_date:
            end_date = start_date

        rows = conn.execute(
            "SELECT trade_date, bar_time, buy_lot, sell_lot, "
            "buy_freq, sell_freq, net_value, price "
            "FROM stockbit_flow_bars "
            "WHERE ticker = ? AND trade_date >= ? AND trade_date <= ? "
            "ORDER BY trade_date, bar_time",
            (sym, start_date, end_date),
        ).fetchall()

        calendar_dates = {
            r[0]
            for r in conn.execute(
                "SELECT date FROM trading_calendar WHERE date >= ? AND date <= ?",
                (start_date, end_date),
            ).fetchall()
        }
    finally:
        conn.close()

    payload = _build_flow(sym, start_date, end_date, metric, rows,
                          calendar_dates, first_available, last_available)
    return payload


def _build_flow(
    symbol: str,
    start_date: str,
    end_date: str,
    metric: str,
    rows: list,
    calendar_dates: set[str],
    first_available: str,
    last_available: str,
) -> dict:
    times: list[str] = []
    session_marks: list[dict] = []
    cum_buy: list[int] = []
    cum_sell: list[int] = []
    net_flow: list[int] = []
    price: list[int] = []

    running_buy = 0
    running_sell = 0
    sessions: list[dict] = []
    anomaly_minutes = 0

    by_date: dict[str, list] = {}
    for r in rows:
        by_date.setdefault(r[0], []).append(r)

    for trade_date, day_rows in by_date.items():
        prev_buy_lot = 0
        prev_sell_lot = 0
        day_buy = 0
        day_sell = 0
        day_net_value = 0
        last_price = 0
        session_start_index = len(times)

        for i, (_, bar_time, buy_lot, sell_lot, _bf, _sf, net_value, px) in enumerate(day_rows):
            # De-cumulate. A decrease means the vendor revised the running
            # total downward after the fact; clamping to 0 keeps the
            # cumulative curves honest (no negative trading) and the
            # anomaly count surfaces it instead of hiding it.
            delta_buy = max(int(buy_lot or 0) - prev_buy_lot, 0)
            delta_sell = max(int(sell_lot or 0) - prev_sell_lot, 0)
            if int(buy_lot or 0) < prev_buy_lot or int(sell_lot or 0) < prev_sell_lot:
                anomaly_minutes += 1
            prev_buy_lot = int(buy_lot or 0)
            prev_sell_lot = int(sell_lot or 0)

            px = int(px or 0)
            if px == 0:
                # Minute without a printed price (vendor gap): carry the last
                # known price so lot deltas still value at the session's
                # level rather than collapsing to zero.
                px = last_price
                anomaly_minutes += 1
            last_price = px

            buy_value = delta_buy * LOT_SHARES * px
            sell_value = delta_sell * LOT_SHARES * px
            day_buy += buy_value
            day_sell += sell_value
            day_net_value += int(net_value or 0)

            running_buy += buy_value
            running_sell += sell_value
            times.append(f"{trade_date} {_norm_hhmm(bar_time)}")
            cum_buy.append(running_buy)
            cum_sell.append(running_sell)
            net_flow.append(running_buy - running_sell)
            price.append(px)

        sessions.append({
            "date": trade_date,
            "minutes": len(day_rows),
            "buy_value": day_buy,
            "sell_value": day_sell,
            "net_value": day_buy - day_sell,
            "net_value_exact": day_net_value,
            "last_price": last_price,
            "first_bar": _norm_hhmm(day_rows[0][1]),
            "last_bar": _norm_hhmm(day_rows[-1][1]),
        })
        session_marks.append({
            "date": trade_date,
            "index": session_start_index,
        })

    # Sessions the calendar says traded but the bars table never ingested —
    # reported, never fabricated.
    session_dates = {s["date"] for s in sessions}
    missing_sessions = sorted(calendar_dates - session_dates)

    total_points = len(times)
    if total_points > MAX_POINTS:
        stride = -(-total_points // MAX_POINTS)
        idx = list(range(0, total_points, stride))
        if idx[-1] != total_points - 1:
            idx.append(total_points - 1)
        times = [times[i] for i in idx]
        cum_buy = [cum_buy[i] for i in idx]
        cum_sell = [cum_sell[i] for i in idx]
        net_flow = [net_flow[i] for i in idx]
        price = [price[i] for i in idx]
        session_marks = [
            m for m in session_marks if m["index"] in set(idx)
        ]

    # Range totals = the sum over every selected session, so the UI's
    # "Buy (cum) / Net flow" figures equal the chained cumulative curves'
    # final point (series.cum_buy[-1] etc.) and aggregate the actual trades
    # across the whole selected range — not just its last session.
    total_buy_value = sum(s["buy_value"] for s in sessions)
    total_sell_value = sum(s["sell_value"] for s in sessions)
    total_net_exact = sum(s["net_value_exact"] for s in sessions)
    net_value = total_buy_value - total_sell_value
    if net_value > 0:
        net_side = "accumulation"
    elif net_value < 0:
        net_side = "distribution"
    else:
        net_side = "neutral"

    return {
        "symbol": symbol,
        "metric": metric,
        "requested": {"start": start_date, "end": end_date},
        "coverage": {
            "first_available_session": first_available,
            "last_available_session": last_available,
        },
        "sessions": sessions,
        "missing_sessions": missing_sessions,
        "session_marks": session_marks,
        "series": {
            "points": len(times),
            "time": times,
            "cum_buy": cum_buy,
            "cum_sell": cum_sell,
            "net_flow": net_flow,
            "price": price,
        },
        "totals": {
            "buy_value": total_buy_value,
            "sell_value": total_sell_value,
            "net_value": net_value,
            "net_value_exact": total_net_exact,
            "net_side": net_side,
            "last_price": sessions[-1]["last_price"] if sessions else 0,
        },
        "anomaly_minutes": anomaly_minutes,
        "big_money": {"available": False, "reason": _BIG_MONEY_REASON},
        "filters_supported": {
            "investor": ["all"],
            "trade_type": ["regular"],
            "metric": list(SUPPORTED_METRICS),
        },
        "as_of": datetime.now().astimezone().isoformat(),
    }
