"""Investment portfolio API (consolidation 2026-09-03).

Versioned, enveloped read/write surface over the canonical investment store
(data/investments.py) that absorbed the Investment Dashboard (port 5003).
This is the one portfolio ledger for the Production OS — the Portfolio page
and the Investment Intelligence workspace both consume it; nothing re-stores
or duplicates it elsewhere.

Reads are VIEWER, state-changing writes OPERATOR (security/route_policy.py).
"""
import logging

from flask import request

from data import investments
from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok

# Self-healing schema: the staging entrypoint (`import app; app.app.run(...)`)
# never calls init_runtime(), so the idempotent init runs here too — every
# entrypoint (gunicorn hook, dev __main__, staging) gets the inv_* tables and
# the additive column migration. Cheap: one PRAGMA check per process.
try:
    investments.init_investment_tables()
except Exception:  # pragma: no cover - e.g. read-only FS during collection
    logging.getLogger("routes.v1.investments").warning(
        "investment table init deferred (db unavailable at import)", exc_info=True)


def _body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError("BAD_REQUEST", 400, "request body must be a JSON object")
    return body


def _require(body, *fields):
    missing = [f for f in fields if body.get(f) in (None, "")]
    if missing:
        raise ApiError("BAD_REQUEST", 400, f"missing required field(s): {', '.join(missing)}")
    return body


@api_v1_bp.route("/investments/summary", methods=["GET"])
def investments_summary():
    """Overview metrics: portfolio value, cost basis, unrealized/realized,
    dividends, total return, allocation (Portfolio tabs + Intelligence
    dashboard both read this)."""
    return ok(investments.summary())


@api_v1_bp.route("/investments/holdings", methods=["GET"])
def investments_holdings():
    return ok(investments.compute_holdings())


@api_v1_bp.route("/investments/transactions", methods=["GET", "POST"])
def investments_transactions():
    if request.method == "GET":
        return ok(investments.list_transactions())
    body = _require(_body(), "date", "ticker", "type", "price", "qty")
    try:
        txn_id = investments.add_transaction(
            body["date"], body["ticker"], body["type"], body["price"], body["qty"],
            body.get("notes", ""))
    except ValueError as e:
        raise ApiError("VALIDATION_ERROR", 400, str(e))
    return ok({"id": txn_id}, status=201)


@api_v1_bp.route("/investments/transactions/<int:txn_id>", methods=["DELETE"])
def investments_transaction_delete(txn_id):
    if not investments.delete_transaction(txn_id):
        raise ApiError("NOT_FOUND", 404, f"no transaction {txn_id}")
    return ok({"deleted": txn_id})


@api_v1_bp.route("/investments/dividends", methods=["GET", "POST"])
def investments_dividends():
    if request.method == "GET":
        return ok(investments.list_dividends())
    body = _require(_body(), "date", "ticker", "per_share", "qty")
    try:
        added = investments.add_dividend(
            body["date"], body["ticker"], body["per_share"], body["qty"],
            body.get("tax_pct", investments.DEFAULT_DIV_TAX_PCT), body.get("notes", ""))
    except ValueError as e:
        raise ApiError("VALIDATION_ERROR", 400, str(e))
    return ok({"added": added}, status=201)


@api_v1_bp.route("/investments/dividends/<int:row_id>", methods=["DELETE"])
def investments_dividend_delete(row_id):
    if not investments.delete_dividend(row_id):
        raise ApiError("NOT_FOUND", 404, f"no dividend {row_id}")
    return ok({"deleted": row_id})


@api_v1_bp.route("/investments/funds", methods=["GET", "POST"])
def investments_funds():
    if request.method == "GET":
        status = request.args.get("status", "ALL").upper()
        if status not in ("ALL", "OPEN", "CLOSED"):
            raise ApiError("BAD_REQUEST", 400, "status must be ALL, OPEN or CLOSED")
        return ok(investments.list_funds(status))
    body = _require(_body(), "id", "name", "entry_date", "entry_nav", "cost_basis")
    try:
        investments.add_fund(body["id"], body["name"], body["entry_date"],
                             body["entry_nav"], body["cost_basis"])
    except ValueError as e:
        raise ApiError("VALIDATION_ERROR", 400, str(e))
    return ok({"id": body["id"]}, status=201)


@api_v1_bp.route("/investments/funds/<fund_id>/redeem", methods=["POST"])
def investments_fund_redeem(fund_id):
    body = _require(_body(), "exit_date", "exit_nav")
    try:
        result = investments.redeem_fund(fund_id, body["exit_date"], body["exit_nav"])
    except ValueError as e:
        raise ApiError("VALIDATION_ERROR", 400, str(e))
    return ok(result)


@api_v1_bp.route("/investments/funds/<fund_id>/nav", methods=["POST"])
def investments_fund_nav(fund_id):
    """Manual NAV update for an OPEN fund position (5003 'Manual' flow)."""
    body = _require(_body(), "current_nav")
    try:
        investments.set_fund_nav(fund_id, body["current_nav"])
    except ValueError as e:
        raise ApiError("VALIDATION_ERROR", 400, str(e))
    return ok({"id": fund_id, "current_nav": body["current_nav"]})


@api_v1_bp.route("/investments/funds/<fund_id>", methods=["DELETE"])
def investments_fund_delete(fund_id):
    if not investments.delete_fund(fund_id):
        raise ApiError("NOT_FOUND", 404, f"no fund position {fund_id}")
    return ok({"deleted": fund_id})


@api_v1_bp.route("/investments/closed-equity", methods=["GET", "POST"])
def investments_closed_equity():
    if request.method == "GET":
        return ok(investments.list_closed_equity())
    body = _require(_body(), "entry_date", "exit_date", "ticker", "entry_price",
                    "exit_price", "qty", "net_pl", "pl_pct")
    added = investments.add_closed_equity(
        body["entry_date"], body["exit_date"], body["ticker"], body["entry_price"],
        body["exit_price"], body["qty"], body["net_pl"], body["pl_pct"])
    return ok({"added": added}, status=201)


@api_v1_bp.route("/investments/closed-equity/<int:row_id>", methods=["DELETE"])
def investments_closed_equity_delete(row_id):
    if not investments.delete_closed_equity(row_id):
        raise ApiError("NOT_FOUND", 404, f"no closed equity row {row_id}")
    return ok({"deleted": row_id})


@api_v1_bp.route("/investments/prices", methods=["GET", "POST"])
def investments_prices():
    if request.method == "GET":
        return ok(investments.get_prices())
    body = _require(_body(), "ticker", "price")
    investments.set_price(str(body["ticker"]).strip().upper(), body["price"], source="manual")
    return ok(investments.get_prices())


@api_v1_bp.route("/investments/prices/refresh", methods=["POST"])
def investments_prices_refresh():
    """Server-side Yahoo (.JK) refresh for open holdings (or an explicit
    ticker list). Per-ticker failures are reported inline; the call itself
    only fails on a malformed body."""
    body = request.get_json(silent=True) or {}
    tickers = body.get("tickers")
    if tickers is not None and not (isinstance(tickers, list) and all(
            isinstance(t, str) and t.strip() for t in tickers)):
        raise ApiError("BAD_REQUEST", 400, "tickers must be a list of ticker strings")
    return ok(investments.refresh_prices(tickers=tickers))


@api_v1_bp.route("/investments/export", methods=["GET"])
def investments_export():
    """Full-ledger JSON in the Investment Dashboard's export shape — the
    supported path out (and backup format) for the canonical store."""
    return ok(investments.export_snapshot())


@api_v1_bp.route("/investments/import", methods=["POST"])
def investments_import():
    """Import an Investment Dashboard snapshot ({txns, CEQ, mfOpen, CMF,
    divs, eqPrices}). Idempotent — safe to re-run; existing rows are kept."""
    body = _body()
    try:
        counts = investments.import_snapshot(body)
    except (TypeError, ValueError) as e:
        raise ApiError("VALIDATION_ERROR", 400, f"invalid snapshot: {e}")
    return ok({"imported": counts})
