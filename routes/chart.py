"""Chart overlays, order-flow delta, and TradingView sync endpoints.

Candle OHLCV itself is served by the existing /api/ticker/... routes; this
blueprint only adds computed overlays (engine.chart_indicators), delta
(engine.delta_flow), and the TV CDP bridge (engine.tv_bridge).
"""
import sqlite3
import pandas as pd
from flask import Blueprint, jsonify, request

from config import DB_PATH
from engine import chart_indicators as ci
from engine import delta_flow
from engine import tv_bridge
from engine.indicators import calc_vwap, calc_vwma
from engine.timeframe import aggregate_ohlcv

chart_bp = Blueprint('chart', __name__)


def _load_ohlcv(ticker: str, freq: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker=? ORDER BY date ASC", conn, params=(ticker.upper(),))
    finally:
        conn.close()
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    f = (freq or 'D').upper()
    if f in ('W', 'M', 'ME'):
        df = aggregate_ohlcv(df, f)
    return df


def _series_tail(s: pd.Series, n: int = 250) -> list:
    s = s.dropna().tail(n)
    return [{'date': d.strftime('%Y-%m-%d'), 'value': round(float(v), 2)}
            for d, v in s.items()]


@chart_bp.route('/api/chart/<ticker>/indicators', methods=['GET'])
def indicators(ticker):
    tf = request.args.get('tf', 'D')
    inds = set((request.args.get('inds', '') or '').split(','))
    df = _load_ohlcv(ticker, tf)
    if df.empty:
        return jsonify({'error': f'no data for {ticker}'}), 404
    out = {}
    if 'vp' in inds:
        out['vp'] = ci.volume_profile(df)
    if 'fvg' in inds:
        out['fvg'] = ci.fair_value_gaps(df)
    if 'sr' in inds:
        out['sr'] = ci.support_resistance(df)
    if 'patterns' in inds:
        out['patterns'] = ci.detect_patterns(df)
    if 'vwap' in inds:
        out['vwap'] = _series_tail(calc_vwap(df, window=min(60, len(df))))
    if 'vwma' in inds:
        out['vwma'] = _series_tail(calc_vwma(df, period=min(20, len(df))))
    return jsonify(out)


@chart_bp.route('/api/chart/<ticker>/delta', methods=['GET'])
def delta(ticker):
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'date required (YYYY-MM-DD)'}), 400
    parts = set((request.args.get('parts', 'cvd,bars,profile,stats') or '').split(','))
    out = {}
    if 'cvd' in parts:
        series = delta_flow.cvd(ticker, date)
        out['cvd'] = series
        out['cvd_ema'] = delta_flow.cvd_ema(series)
    if 'bars' in parts:
        out['bars'] = delta_flow.delta_bars(ticker, date)
    if 'profile' in parts:
        out['profile'] = delta_flow.delta_by_price(ticker, date)
    if 'stats' in parts:
        out['stats'] = delta_flow.session_delta_stats(ticker, date)
    if 'imbalance' in parts:
        out['imbalance'] = delta_flow.stacked_imbalances(ticker, date)
    return jsonify(out)


@chart_bp.route('/api/chart/tv/sync', methods=['POST'])
def tv_sync():
    body = request.get_json(silent=True) or {}
    symbol = body.get('symbol', '')
    return jsonify(tv_bridge.set_symbol(symbol))


@chart_bp.route('/api/chart/tv/status', methods=['GET'])
def tv_status():
    return jsonify({'available': tv_bridge.is_available()})
