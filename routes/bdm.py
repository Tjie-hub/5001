"""Broker-flow context screen (NeoBDM-style) -- page + read-only API. Descriptive only (D-094);
see engine/bdm.py for what each reading is and why none of it is a signal."""
import logging

from flask import Blueprint, jsonify, render_template

from engine import bdm

log = logging.getLogger(__name__)
bdm_bp = Blueprint("bdm", __name__)


@bdm_bp.route("/bdm")
def bdm_page():
    return render_template("bdm.html")


@bdm_bp.route("/api/bdm/screener", methods=["GET"])
def api_bdm_screener():
    try:
        return jsonify(bdm.screener())
    except Exception as e:  # fail-soft: a context screen must never take the app down
        log.exception("bdm screener failed")
        return jsonify({"error": str(e), "rows": []}), 500


@bdm_bp.route("/api/bdm/ticker/<ticker>", methods=["GET"])
def api_bdm_ticker(ticker):
    try:
        out = bdm.ticker_detail(ticker)
    except Exception as e:
        log.exception("bdm ticker failed")
        return jsonify({"error": str(e)}), 500
    if out is None:
        return jsonify({"error": f"no broker_flow data for {ticker.upper()}"}), 404
    return jsonify(out)
