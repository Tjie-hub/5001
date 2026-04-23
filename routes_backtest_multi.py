"""
routes_backtest_multi.py — Flask Blueprint untuk Multi-Strategy Backtest
Tambahkan ke app.py idx-walkforward:

    from routes_backtest_multi import backtest_multi_bp
    app.register_blueprint(backtest_multi_bp)
"""

import json
import sqlite3
import pandas as pd
from flask import Blueprint, jsonify, request, render_template_string
from engine.walkforward_multi import run_all_strategies, run_walk_forward
from engine.strategies import (
    filter_vwma_above, filter_above_ma50,
    filter_low_atr, filter_vr_min, filter_uptrend
)

FILTER_MAP = {
    'vwma_above': filter_vwma_above,
    'ma50_above': filter_above_ma50,
    'low_atr':    filter_low_atr,
    'vr_min':     filter_vr_min,
    'uptrend':    filter_uptrend,
}

def resolve_filters(filter_names: list) -> list:
    return [FILTER_MAP[f] for f in (filter_names or []) if f in FILTER_MAP]

import os
backtest_multi_bp = Blueprint('backtest_multi', __name__)

DB_PATH = os.getenv('DB_PATH', '/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db')


def get_ohlcv(ticker: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql(
        "SELECT date, open, high, low, close, volume FROM ohlcv WHERE ticker = ? ORDER BY date ASC",
        conn, params=(ticker,)
    )
    conn.close()
    df['date']   = pd.to_datetime(df['date'])
    df['open']   = df['open'].astype(float)
    df['high']   = df['high'].astype(float)
    df['low']    = df['low'].astype(float)
    df['close']  = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df


# ─────────────────────────────────────────────
# API: Full Backtest (semua bar)
# ─────────────────────────────────────────────

@backtest_multi_bp.route('/api/backtest/multi', methods=['POST'])
def api_backtest_multi():
    """
    POST /api/backtest/multi
    Body: {"ticker": "BBCA", "capital": 50000000}
    """
    body    = request.get_json(force=True)
    ticker  = body.get('ticker', 'BBCA').upper()
    capital = float(body.get('capital', 50_000_000))
    filters = resolve_filters(body.get('filters', []))

    try:
        df = get_ohlcv(ticker)
        if len(df) < 60:
            return jsonify({'error': f'Data {ticker} kurang (hanya {len(df)} bar)'}), 400

        results = run_all_strategies(df, capital=capital, filters=filters)
        dates = [str(d)[:10] for d in df['date'].tolist()]

        # Strategy name → wf_scores key mapping
        STRAT_KEY = {
            'Vol-Weighted Entry':   'vol_weighted',
            'Momentum Following':   'momentum',
            'VWAP Reversion':       'vwap_reversion',
            'Conservative Confirm': 'conservative',
            'Volume Profile POC':   'Volume Profile POC',
            'Inside Bar Breakout':  'Inside Bar Breakout',
            'NR7 Breakout':         'NR7 Breakout',
            'ORB':                  'ORB',
        }

        # Load WF scores for this ticker
        wf_map = {}
        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute("""
                SELECT strategy, consistency_pct, weighted_score
                FROM wf_scores WHERE ticker=?
            """, (ticker,)).fetchall()
            conn.close()
            wf_map = {r[0]: {'consistency_pct': r[1], 'weighted_score': r[2]} for r in rows}
        except Exception:
            pass

        # Include equity inline (trimmed to dates length)
        for r in results:
            eq = r.get('equity', [])
            r['equity'] = eq[:len(dates)] if eq else []
            # Attach WF score using name mapping
            key = STRAT_KEY.get(r['strategy'], r['strategy'])
            wf = wf_map.get(key, {})
            r['wf_score'] = wf.get('weighted_score')
            r['wf_consistency'] = wf.get('consistency_pct')

        return jsonify({
            'ticker':  ticker,
            'bars':    len(df),
            'capital': capital,
            'dates':   dates,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# API: Walk-Forward
# ─────────────────────────────────────────────

@backtest_multi_bp.route('/api/backtest/walkforward', methods=['POST'])
def api_walkforward():
    """
    POST /api/backtest/walkforward
    Body: {"ticker": "BBCA", "capital": 50000000}
    """
    body    = request.get_json(force=True)
    ticker  = body.get('ticker', 'BBCA').upper()
    capital = float(body.get('capital', 50_000_000))
    filters = resolve_filters(body.get('filters', []))

    try:
        df  = get_ohlcv(ticker)
        wf  = run_walk_forward(df, capital=capital, filters=filters)

        if 'error' in wf:
            return jsonify(wf), 400

        # Bersihkan data per-window agar response tidak terlalu besar
        clean_summary = {}
        for name, s in wf['summary'].items():
            clean_summary[name] = {k: v for k, v in s.items() if k != 'windows'}

        return jsonify({
            'ticker':   ticker,
            'bars':     len(df),
            'windows':  wf['windows'],
            'best':     wf['best'],
            'summary':  clean_summary,
            'ranked':   [{k: v for k, v in r.items() if k != 'windows'} for r in wf['ranked']]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# API: Equity Curve Data (untuk chart)
# ─────────────────────────────────────────────

@backtest_multi_bp.route('/api/backtest/equity', methods=['POST'])
def api_equity_curves():
    """
    POST /api/backtest/equity
    Body: {"ticker": "BBCA", "capital": 50000000}
    Returns: equity curves untuk semua 4 strategi + dates
    """
    body    = request.get_json(force=True)
    ticker  = body.get('ticker', 'BBCA').upper()
    capital = float(body.get('capital', 50_000_000))

    try:
        df      = get_ohlcv(ticker)
        results = run_all_strategies(df, capital=capital)
        dates   = [str(d)[:10] for d in df['date'].tolist()]

        curves = {}
        for r in results:
            eq = r.get('equity', [])
            # equity bisa lebih panjang 1 dari df — trim
            curves[r['strategy']] = eq[:len(dates)]

        return jsonify({'dates': dates, 'curves': curves})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# API: Trade Log per Strategy
# ─────────────────────────────────────────────

@backtest_multi_bp.route('/api/backtest/trades/<ticker>/<strategy_name>', methods=['GET'])
def api_trade_log(ticker, strategy_name):
    """
    GET /api/backtest/trades/BBCA/Vol-Weighted%20Entry
    Returns detailed trade log untuk 1 strategi.
    """
    capital = float(request.args.get('capital', 50_000_000))
    try:
        df      = get_ohlcv(ticker.upper())
        results = run_all_strategies(df, capital=capital)
        for r in results:
            if r['strategy'].lower() == strategy_name.lower():
                return jsonify({
                    'ticker':   ticker,
                    'strategy': r['strategy'],
                    'metrics':  {k: v for k, v in r.items() if k not in ['trades_detail', 'equity']},
                    'trades':   r.get('trades_detail', [])
                })
        return jsonify({'error': 'Strategy tidak ditemukan'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
