import logging
import sqlite3
from datetime import date

from flask import Blueprint, jsonify, request

from config import DB_PATH
from flow_filter import get_flow_batch, get_market_accdist_summary
from engine.vpin import get_market_vpin_summary
from engine.breadth import get_market_breadth
from engine.technicals import detect_ihsg_technicals
from engine.risk_score import compute_market_risk_score

flow_bp = Blueprint("flow", __name__)


@flow_bp.route('/api/flow/monitor', methods=['GET'])
def api_flow_monitor():
    from datetime import date
    today_str = str(date.today())
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT ticker, composite_score, verdict, smart_money,
               buy_lot, sell_lot, net_lot, updated_at
        FROM stockbit_flow
        WHERE trade_date=?
        ORDER BY composite_score DESC
    """, (today_str,)).fetchall()
    conn.close()
    results = []
    for r in rows:
        verdict_clean = r[2].replace("🟢 ","").replace("🔴 ","").replace("🟡 ","")
        results.append({
            "ticker": r[0], "score": r[1], "verdict": verdict_clean,
            "smart_money": r[3], "buy_lot": r[4], "sell_lot": r[5],
            "net_lot": r[6], "updated_at": r[7]
        })
    bullish  = [x for x in results if x["score"] >= 3]
    neutral  = [x for x in results if -3 < x["score"] < 3]
    bearish  = [x for x in results if x["score"] <= -3]
    return jsonify({
        "date": today_str,
        "total": len(results),
        "bullish": len(bullish),
        "neutral": len(neutral),
        "bearish": len(bearish),
        "results": results
    })


@flow_bp.route('/api/flow/check', methods=['POST'])
def check_flow():
    """
    Standalone flow check endpoint.

    POST body:
        {
            "tickers": ["BRPT", "BBCA"],
            "threshold": 2
        }

    Returns flow data for requested tickers.
    """
    data = request.get_json()
    tickers = data.get('tickers', [])
    threshold = data.get('threshold', 2)

    if not tickers:
        return jsonify({'success': False, 'error': 'No tickers provided'}), 400

    try:
        flow_data = get_flow_batch(tickers, token=None, delay=0.8)

        results = []
        for ticker in tickers:
            if ticker in flow_data:
                flow = flow_data[ticker]
                results.append({
                    'ticker': ticker,
                    'score': flow['score'],
                    'verdict': flow['verdict'],
                    'smart_money': flow['smart_money'],
                    'confirmed': flow['score'] >= threshold,
                    'details': flow
                })
            else:
                results.append({
                    'ticker': ticker,
                    'score': None,
                    'verdict': 'UNAVAILABLE',
                    'confirmed': None
                })

        return jsonify({
            'success': True,
            'threshold': threshold,
            'results': results,
            'total': len(results)
        })

    except Exception as e:
        logging.exception("api error")
        return jsonify({
            'success': False,
            'error': 'internal error'
        }), 500


@flow_bp.route('/api/broker-flow/<ticker>', methods=['GET'])
def api_broker_flow(ticker):
    ticker = ticker.upper()
    trade_date = request.args.get('date', None)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Latest date if not specified — prefer broker_flow, fall back to stockbit_flow
    if not trade_date:
        row = conn.execute(
            "SELECT MAX(trade_date) FROM broker_flow WHERE ticker=?", (ticker,)
        ).fetchone()
        if row and row[0]:
            trade_date = row[0]
        else:
            row2 = conn.execute(
                "SELECT MAX(trade_date) FROM stockbit_flow WHERE ticker=?", (ticker,)
            ).fetchone()
            trade_date = row2[0] if row2 and row2[0] else str(date.today())

    brokers = conn.execute("""
        SELECT broker_code, side, lot, lot_value, value, value_total,
               avg_price, freq, investor_type
        FROM broker_flow
        WHERE ticker=? AND trade_date=?
        ORDER BY side, ABS(lot) DESC
    """, (ticker, trade_date)).fetchall()

    bandar = conn.execute("""
        SELECT avg_price, total_buyer, total_seller, net_broker_count,
               broker_accdist, value, volume,
               top1_accdist, top3_accdist, top5_accdist, top10_accdist, avg_accdist
        FROM bandar_detector
        WHERE ticker=? AND trade_date=?
    """, (ticker, trade_date)).fetchone()

    # Available dates: union broker_flow + stockbit_flow for this ticker
    dates_bf = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM broker_flow WHERE ticker=? ORDER BY trade_date DESC LIMIT 30",
        (ticker,)
    ).fetchall()]
    dates_sf = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM stockbit_flow WHERE ticker=? ORDER BY trade_date DESC LIMIT 30",
        (ticker,)
    ).fetchall()]
    dates = sorted(set(dates_bf + dates_sf), reverse=True)[:30]
    conn.close()

    buy_rows = [dict(r) for r in brokers if r['side'] == 'BUY']
    sell_rows = [dict(r) for r in brokers if r['side'] == 'SELL']

    return jsonify({
        'ticker': ticker,
        'trade_date': trade_date,
        'available_dates': dates,
        'bandar': dict(bandar) if bandar else None,
        'buyers': buy_rows,
        'sellers': sell_rows,
    })


@flow_bp.route('/api/broker-flow/dates/<ticker>', methods=['GET'])
def api_broker_flow_dates(ticker):
    ticker = ticker.upper()
    conn = sqlite3.connect(DB_PATH)
    dates_bf = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM broker_flow WHERE ticker=? ORDER BY trade_date DESC LIMIT 30",
        (ticker,)
    ).fetchall()]
    dates_sf = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM stockbit_flow WHERE ticker=? ORDER BY trade_date DESC LIMIT 30",
        (ticker,)
    ).fetchall()]
    dates = sorted(set(dates_bf + dates_sf), reverse=True)[:30]
    conn.close()
    return jsonify({'ticker': ticker, 'dates': dates})


@flow_bp.route('/api/market/accdist', methods=['GET'])
def api_market_accdist():
    """Market-wide accumulation/distribution summary from bandar_detector.

    Query param: date (YYYY-MM-DD, default today).
    Also returns a 30-day time series when ?series=1 is passed.
    """
    query_date = request.args.get('date', str(date.today()))
    summary = get_market_accdist_summary(query_date)

    series = []
    if request.args.get('series'):
        conn = sqlite3.connect(DB_PATH)
        dates = [r[0] for r in conn.execute(
            "SELECT DISTINCT trade_date FROM bandar_detector "
            "ORDER BY trade_date DESC LIMIT 30"
        ).fetchall()]
        conn.close()
        for d in sorted(dates):
            series.append(get_market_accdist_summary(d))

    return jsonify({'summary': summary, 'series': series})


@flow_bp.route('/api/market/vpin', methods=['GET'])
def api_market_vpin():
    """Market-wide VPIN toxicity summary aggregated from daily_screen.

    Query params:
      date   — YYYY-MM-DD (default today)
      series — if set, also returns 30-day time series
    """
    query_date = request.args.get('date', str(date.today()))
    conn = sqlite3.connect(DB_PATH)
    summary = get_market_vpin_summary(conn, query_date)

    series = []
    if request.args.get('series'):
        dates = [r[0] for r in conn.execute(
            "SELECT DISTINCT date FROM daily_screen "
            "WHERE vpin IS NOT NULL ORDER BY date DESC LIMIT 30"
        ).fetchall()]
        for d in sorted(dates):
            series.append(get_market_vpin_summary(conn, d))

    conn.close()
    return jsonify({'summary': summary, 'series': series})


@flow_bp.route('/api/market/technicals', methods=['GET'])
def api_market_technicals():
    """IHSG technical signals: death cross, lower high, support breaks.

    Query params:
      date — YYYY-MM-DD (default today)
    """
    query_date = request.args.get('date', str(date.today()))
    conn = sqlite3.connect(DB_PATH)
    result = detect_ihsg_technicals(conn, query_date)
    conn.close()
    return jsonify(result)


@flow_bp.route('/api/market/breadth', methods=['GET'])
def api_market_breadth():
    """Market breadth (advancers/decliners + % above MA20) from ohlcv.

    Query params:
      date   — YYYY-MM-DD (default today)
      series — if set, returns last 30 trading dates as time series
    """
    query_date = request.args.get('date', str(date.today()))
    conn = sqlite3.connect(DB_PATH)
    summary = get_market_breadth(conn, query_date)

    series = []
    if request.args.get('series'):
        dates = [r[0] for r in conn.execute(
            "SELECT DISTINCT date FROM ohlcv ORDER BY date DESC LIMIT 30"
        ).fetchall()]
        for d in sorted(dates):
            series.append(get_market_breadth(conn, d))

    conn.close()
    return jsonify({'summary': summary, 'series': series})


@flow_bp.route('/api/market/risk', methods=['GET'])
def api_market_risk():
    """Composite market risk score (0-100) combining all sensors.

    Query params:
      date — YYYY-MM-DD (default today)
    """
    query_date = request.args.get('date', str(date.today()))
    conn = sqlite3.connect(DB_PATH)

    vpin_s = get_market_vpin_summary(conn, query_date)
    accdist_s = get_market_accdist_summary(query_date)
    breadth_s = get_market_breadth(conn, query_date)
    tech_s = detect_ihsg_technicals(conn, query_date)

    try:
        foreign_buy = conn.execute(
            "SELECT SUM(lot_value) FROM broker_flow WHERE investor_type='Asing' AND side='BUY' AND trade_date<=? AND trade_date>=date(?,'-7 days')",
            (query_date, query_date),
        ).fetchone()[0] or 0
        foreign_sell = conn.execute(
            "SELECT SUM(lot_value) FROM broker_flow WHERE investor_type='Asing' AND side='SELL' AND trade_date<=? AND trade_date>=date(?,'-7 days')",
            (query_date, query_date),
        ).fetchone()[0] or 0
        foreign_net = foreign_buy - foreign_sell
    except Exception:
        foreign_net = None

    conn.close()

    risk = compute_market_risk_score(vpin_s, accdist_s, breadth_s, tech_s, foreign_net)
    risk['date'] = query_date
    risk['sensors'] = {
        'vpin': vpin_s, 'accdist': accdist_s,
        'breadth': breadth_s, 'technicals': tech_s,
        'foreign_net_5d': foreign_net,
    }
    return jsonify(risk)


@flow_bp.route('/api/dashboard/risk', methods=['GET'])
def api_dashboard_risk():
    """Unified market risk dashboard — all sensors in one response.

    Query params:
      date — YYYY-MM-DD (default today)

    Returns: date, risk_score, tier, components, ihsg, breadth,
             foreign_flow (today/5d/20d/trend), vpin, accdist.
    """
    from engine.dashboard import get_risk_dashboard
    query_date = request.args.get('date', str(date.today()))
    try:
        return jsonify(get_risk_dashboard(DB_PATH, query_date))
    except Exception as e:
        return jsonify({'error': str(e), 'date': query_date,
                        'risk_score': 0.0, 'tier': 'GREEN'}), 500


@flow_bp.route('/api/dashboard/watchlist', methods=['GET'])
def api_dashboard_watchlist():
    """Watchlist dashboard — BUY WATCH / AVOID / WAIT ticker lists.

    Query params:
      date — YYYY-MM-DD (default today)

    Returns: date, buy_watch, avoid, wait — each a list of ticker dicts
             with close, chg_pct, bounce_pct, foreign_net_today,
             foreign_net_3d, volume, ytd_pct.
    """
    from engine.dashboard import get_watchlist
    query_date = request.args.get('date', str(date.today()))
    try:
        return jsonify(get_watchlist(DB_PATH, query_date))
    except Exception as e:
        return jsonify({'error': str(e), 'date': query_date,
                        'buy_watch': [], 'avoid': [], 'wait': []}), 500
