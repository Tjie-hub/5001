import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify
from scheduler import start_scheduler
from routes_backtest_multi import backtest_multi_bp
from screener.routes import screener_bp
from screener.db import init_screener_tables
from stockbit_fetcher import init_flow_db
from routes.telegram import telegram_bp, telegram_poller_loop
from routes.flow import flow_bp
from routes.screener import screener_main_bp
from routes.backtest import backtest_bp
import threading

load_dotenv()
DB_PATH = os.getenv('DB_PATH', '/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db')

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)
app.register_blueprint(backtest_multi_bp)
app.register_blueprint(screener_bp, url_prefix='/api/screener')
app.register_blueprint(telegram_bp)
app.register_blueprint(flow_bp)
app.register_blueprint(screener_main_bp)
app.register_blueprint(backtest_bp)

@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.route("/health")
def health():
    import sqlite3
    result = {"status": "ok", "db": "ok", "last_scan": None, "open_trades": 0}
    try:
        conn = sqlite3.connect(DB_PATH)
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
    return jsonify(result)


@app.route("/")
@app.route("/backtest/multi")
def backtest_multi_page():
    return render_template("backtest_multi.html")

@app.route("/screener")
def screener_page():
    return render_template("screener.html")


@app.route("/signal-scanner")
def signal_scanner_page():
    return render_template("backtest_multi.html")


if __name__ == "__main__":
    init_screener_tables()
    init_flow_db()
    start_scheduler()
    poller_thread = threading.Thread(target=telegram_poller_loop, daemon=True)
    poller_thread.start()
    app.run(host="0.0.0.0", port=5001, debug=False)
