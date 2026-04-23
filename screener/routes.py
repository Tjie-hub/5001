"""
screener/routes.py — Flask Blueprint for intraday screener endpoints
"""
import threading
import logging
from datetime import date as dt_date
from flask import Blueprint, jsonify, request

import screener.db as db
import screener.idx_scraper as scraper
import screener.calculator as calc
import screener.vpin as vpin_mod
import screener.vpin_multi as vpin_multi
import screener.screener_jobs as jobs

logger = logging.getLogger(__name__)
screener_bp = Blueprint('screener', __name__)

_task_lock = threading.Lock()


@screener_bp.route('/run', methods=['POST'])
def api_run():
    with _task_lock:
        state = jobs.get_task_state()
        if state['running']:
            return jsonify({'error': 'Run already in progress'}), 409

        body = request.get_json(silent=True) or {}
        run_type = body.get('type', 'intraday')
        trade_date = body.get('date', dt_date.today().isoformat())

    def _run():
        try:
            if run_type == 'eod':
                jobs.run_eod(trade_date)
            else:
                jobs.run_intraday(trade_date)
        except Exception as e:
            logger.error(f"[screener/routes] Run error: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started', 'type': run_type, 'date': trade_date})


@screener_bp.route('/status')
def api_status():
    return jsonify(jobs.get_task_state())


@screener_bp.route('/results')
def api_results():
    trade_date = request.args.get('date', dt_date.today().isoformat())
    rows = db.get_screen_results(trade_date)
    return jsonify({'date': trade_date, 'count': len(rows), 'data': rows})


@screener_bp.route('/ticks')
def api_ticks():
    ticker = request.args.get('ticker', '').upper()
    trade_date = request.args.get('date', dt_date.today().isoformat())
    if not ticker:
        return jsonify({'error': 'ticker required'}), 400
    ticks = db.get_ticks(trade_date, ticker)
    bars_1h = calc.calc_vwap_1h(ticks)
    delta_d = calc.calc_delta(ticks)
    vwap = calc.calc_vwap(ticks)
    return jsonify({'date': trade_date, 'ticker': ticker, 'ticks': ticks,
                    'bars_1h': bars_1h, 'vwap': vwap, **delta_d})


@screener_bp.route('/cumdelta')
def api_cumdelta():
    ticker = request.args.get('ticker', '').upper()
    trade_date = request.args.get('date', dt_date.today().isoformat())
    if not ticker:
        return jsonify({'error': 'ticker required'}), 400
    ticks = db.get_ticks(trade_date, ticker)
    series = calc.calc_cum_delta_series(ticks)
    divergence = calc.calc_divergence(ticks)
    delta_d = calc.calc_delta(ticks)
    return jsonify({'date': trade_date, 'ticker': ticker,
                    'cum_delta': delta_d['cum_delta'], 'divergence': divergence, 'series': series})


@screener_bp.route('/vpin')
def api_vpin():
    ticker = request.args.get('ticker', '').upper()
    date = request.args.get('date', dt_date.today().isoformat())
    if not ticker:
        return jsonify({'error': 'ticker required'}), 400
    with db.get_conn() as conn:
        actual_date = vpin_mod.get_latest_vpin_date(conn, ticker, date) or date
        result = vpin_mod.calc_vpin(conn, ticker, actual_date)
        result.pop('buckets', None)
    return jsonify(result)


@screener_bp.route('/vpin/multi')
def api_vpin_multi():
    ticker = request.args.get('ticker', '').upper()
    date = request.args.get('date', dt_date.today().isoformat())
    if not ticker:
        return jsonify({'error': 'ticker required'}), 400
    with db.get_conn() as conn:
        actual_date = vpin_mod.get_latest_vpin_date(conn, ticker, date) or date
        result = vpin_multi.calc_vpin_multi(conn, ticker, actual_date)
    if result is None:
        return jsonify({'error': 'insufficient VPIN history', 'ticker': ticker})
    return jsonify(result)


@screener_bp.route('/vpin/scan')
def api_vpin_scan():
    date = request.args.get('date', dt_date.today().isoformat())
    with db.get_conn() as conn:
        results = vpin_multi.scan_vpin_signals(conn, scraper.LQ45, date)
    for r in results:
        r.pop('days_data', None)
    return jsonify({'date': date, 'signals': results, 'count': len(results)})


@screener_bp.route('/lq45')
def api_lq45():
    return jsonify({'tickers': scraper.LQ45, 'count': len(scraper.LQ45)})


@screener_bp.route('/run_log')
def api_run_log():
    limit = int(request.args.get('limit', 10))
    return jsonify({'run_log': db.get_run_log(limit)})
