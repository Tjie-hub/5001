import os
import logging
import sqlite3
import time
import uuid
from flask import Flask, render_template, jsonify, request, g
from scheduler import start_scheduler
from routes_backtest_multi import backtest_multi_bp
from screener.routes import screener_bp
from screener.db import init_screener_tables
from stockbit_fetcher import init_flow_db
from screener.stockbit_screener import init_db as init_stockbit_screener_table
from stockbit_broker_period import init_db as init_broker_period_summary_table
from stockbit_corporate_actions import init_db as init_corporate_action_events_table
from stockbit_ownership import init_db as init_ownership_composition_table
from data.db import init_agent_firm_tables
from paper_trade import init_paper_table
from data.db import connect as db_connect
from routes.telegram import telegram_bp, telegram_poller_loop
from routes.flow import flow_bp
from routes.screener import screener_main_bp
from routes.backtest import backtest_bp
from routes.portfolio import portfolio_bp
from routes.chart import chart_bp
from utils.logging_config import setup_logging
import threading

setup_logging()
from config import DB_PATH as _DEFAULT_DB_PATH  # single path authority (audit, Phase 5)
DB_PATH = os.getenv('DB_PATH', _DEFAULT_DB_PATH)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)
app.register_blueprint(backtest_multi_bp)
app.register_blueprint(screener_bp, url_prefix='/api/screener')
app.register_blueprint(telegram_bp)
app.register_blueprint(flow_bp)
app.register_blueprint(screener_main_bp)
app.register_blueprint(backtest_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(chart_bp)

# Security hardening: auth endpoints + authorization middleware. AUTH_MODE=off
# (the default) keeps behavior identical to the pre-hardening app.
from security.routes import auth_bp
from security.middleware import init_security
app.register_blueprint(auth_bp)
init_security(app)

@app.before_request
def _assign_correlation_id():
    g.correlation_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    g.request_start  = time.monotonic()


@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options']       = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection']      = '1; mode=block'
    response.headers['Referrer-Policy']        = 'strict-origin-when-cross-origin'
    response.headers['X-Request-ID']           = g.get('correlation_id', '')
    duration_ms = round((time.monotonic() - g.get('request_start', time.monotonic())) * 1000)
    logging.getLogger('request').info(
        '%s %s %d %dms', request.method, request.path,
        response.status_code, duration_ms,
        extra={'status': response.status_code, 'duration_ms': duration_ms},
    )
    return response


@app.errorhandler(500)
def _internal_error(e):
    """Generic 500: no traceback or exception detail crosses the HTTP
    boundary (security hardening Phase 3); full detail goes to the log with
    the request's correlation id."""
    logging.getLogger("app").exception("unhandled error (request_id=%s)",
                                       g.get("correlation_id", ""))
    return jsonify({"error": "internal server error",
                    "request_id": g.get("correlation_id", "")}), 500


@app.route("/health")
def health():
    import sqlite3
    from utils.release import release_info
    result = {"status": "ok", "db": "ok", "last_scan": None, "open_trades": 0,
              "version": release_info().get("version")}
    try:
        conn = db_connect(DB_PATH)
        result["last_scan"] = conn.execute(
            "SELECT MAX(scan_time) FROM scheduled_signals"
        ).fetchone()[0]
        result["open_trades"] = conn.execute(
            "SELECT COUNT(*) FROM paper_trades WHERE status='OPEN'"
        ).fetchone()[0]
        conn.close()
    except Exception as e:
        result["status"] = "error"
        result["db"] = str(e)
    try:
        from scheduler.scanner import _event_guard_active, _macro_panic_state
        _eg_on, _eg_mult = _event_guard_active()
        result["event_guard"] = {"active": _eg_on, "size_mult": _eg_mult}
        result["macro_panic_state"] = _macro_panic_state()
    except Exception as e:
        result["event_guard"] = {"active": False, "error": str(e)}
    return jsonify(result)


@app.route("/")
@app.route("/backtest/multi")
def backtest_multi_page():
    return render_template("workspace.html")

@app.route("/screener")
def screener_page():
    return render_template("screener.html")


@app.route("/signal-scanner")
def signal_scanner_page():
    return render_template("workspace.html")


@app.route("/portfolio")
def portfolio_page():
    return render_template("portfolio.html")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/sector")
def sector_page():
    return render_template("sector.html")


@app.route("/metrics")
def prometheus_metrics():
    """R14 — Prometheus-format metrics endpoint.

    Exposes operational counters/gauges queryable by Prometheus or any
    compatible scraper. No external library required.
    """
    lines: list[str] = []

    def _gauge(name: str, desc: str, value, labels: dict | None = None) -> None:
        label_str = ''
        if labels:
            parts = ','.join(f'{k}="{v}"' for k, v in labels.items())
            label_str = '{' + parts + '}'
        lines.append(f'# HELP {name} {desc}')
        lines.append(f'# TYPE {name} gauge')
        lines.append(f'{name}{label_str} {value if value is not None else "NaN"}')

    def _q(conn, sql, *params):
        try:
            row = conn.execute(sql, params).fetchone()
            return row[0] if row else None
        except Exception:
            return None

    try:
        conn = db_connect(DB_PATH)
        from datetime import date as _date
        import datetime as _dt
        today = str(_date.today())

        open_trades     = _q(conn, "SELECT COUNT(*) FROM paper_trades WHERE status='OPEN'") or 0
        signals_today   = _q(conn, "SELECT COUNT(*) FROM scheduled_signals WHERE date(scan_time)=?", today) or 0
        buy_signals     = _q(conn, "SELECT COUNT(*) FROM scheduled_signals WHERE date(scan_time)=? AND signal_direction='BUY'", today) or 0
        sell_signals    = _q(conn, "SELECT COUNT(*) FROM scheduled_signals WHERE date(scan_time)=? AND signal_direction='SELL'", today) or 0
        agent_decisions = _q(conn, "SELECT COUNT(*) FROM agent_decisions WHERE date(scan_time)=?", today) or 0
        ohlcv_tickers   = _q(conn, "SELECT COUNT(DISTINCT ticker) FROM ohlcv WHERE date=?", today) or 0
        risk_score      = _q(conn, "SELECT risk_score FROM market_risk_log ORDER BY computed_at DESC LIMIT 1")
        avg_vpin        = _q(conn, "SELECT AVG(vpin) FROM daily_screen WHERE date=? AND vpin IS NOT NULL", today)

        last_scan_str   = _q(conn, "SELECT MAX(scan_time) FROM scheduled_signals")
        last_scan_ts    = None
        if last_scan_str:
            try:
                last_scan_ts = int(_dt.datetime.fromisoformat(last_scan_str).timestamp())
            except ValueError:
                pass

        conn.close()
    except Exception as e:
        logging.warning('metrics db error: %s', e)
        return f'# metrics db error: {e}\n', 500, {'Content-Type': 'text/plain; charset=utf-8'}

    _gauge('idx_open_trades',          'Number of currently open paper trades', open_trades)
    _gauge('idx_signals_today_total',  'Total signals generated today', signals_today)
    _gauge('idx_signals_today_buy',    'BUY-direction signals today', buy_signals)
    _gauge('idx_signals_today_sell',   'SELL-direction signals today', sell_signals)
    _gauge('idx_agent_decisions_today','Agent decisions made today', agent_decisions)
    _gauge('idx_ohlcv_tickers_today',  'Tickers with OHLCV data for today', ohlcv_tickers)
    _gauge('idx_market_risk_score',    'Latest composite market risk score (0-100)', risk_score)
    _gauge('idx_avg_vpin_today',       'Average VPIN across all tickers today', avg_vpin)
    if last_scan_ts:
        _gauge('idx_last_scan_timestamp', 'Unix timestamp of last scheduled scan', int(last_scan_ts))

    body = '\n'.join(lines) + '\n'
    return body, 200, {'Content-Type': 'text/plain; charset=utf-8; version=0.0.4'}


def init_runtime():
    """One-time process initialization: idempotent table migrations, the
    APScheduler, and the Telegram poller thread. Called from __main__ (dev,
    Flask server) and from gunicorn's post_worker_init hook (production,
    see gunicorn.conf.py) — extracted so both runtimes share exactly the
    same startup path (audit P-5)."""
    from config import validate_config
    validate_config()
    init_screener_tables()
    init_flow_db()
    init_stockbit_screener_table()
    init_broker_period_summary_table()
    init_corporate_action_events_table()
    init_ownership_composition_table()
    init_agent_firm_tables()
    init_paper_table()
    scheduler = start_scheduler()
    poller_thread = threading.Thread(target=telegram_poller_loop, daemon=True)
    poller_thread.start()
    from utils.release import release_info
    _rel = release_info()
    logging.getLogger("app").info(
        "runtime initialized (scheduler + telegram poller) version=%s source=%s",
        _rel.get("version"), _rel.get("source"))
    return scheduler


if __name__ == "__main__":
    init_runtime()
    app.run(host="0.0.0.0", port=5001, debug=False)
