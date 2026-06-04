import logging
import sqlite3
import threading

import pandas as pd
from flask import Blueprint, jsonify, render_template, request

from config import DB_PATH
from flow_filter import get_flow_batch
from scheduler import send_telegram as _send_telegram

screener_main_bp = Blueprint("screener_main", __name__)


@screener_main_bp.route('/api/screener/swing_onset', methods=['POST'])
def api_swing_onset():
    """
    Swing-trend onset screener.
    Body: { "min_score": 60, "tickers": ["BBCA",...] (optional), "include_flow": true }
    Returns ranked list of candidates entering a new uptrend.
    """
    import sqlite3, pandas as pd
    from engine.swing_screener import score_swing_onset

    body = request.get_json(force=True) or {}
    min_score   = int(body.get('min_score', 60))
    include_flow = bool(body.get('include_flow', True))
    requested   = body.get('tickers') or []

    conn = sqlite3.connect(DB_PATH)
    if requested:
        tickers = [t.upper() for t in requested]
    else:
        tickers = [r[0] for r in conn.execute('SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker').fetchall()]
    conn.close()

    # Optional flow batch
    flow_map = {}
    if include_flow:
        try:
            flow_map = get_flow_batch(tickers, token=None, delay=0.8) or {}
        except Exception:
            flow_map = {}

    results = []
    for ticker in tickers:
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql('SELECT date, open, high, low, close, volume FROM ohlcv WHERE ticker=? ORDER BY date ASC',
                             conn, params=(ticker,))
            conn.close()
            if len(df) < 60:
                continue
            for c in ['open','high','low','close','volume']:
                df[c] = df[c].astype(float)

            flow_row = None
            if ticker in flow_map:
                flow_row = {'composite_score': flow_map[ticker].get('score')}

            s = score_swing_onset(df, flow_row=flow_row)
            if s['score'] < min_score and s['verdict'] != 'WATCH':
                continue
            results.append({
                'ticker': ticker,
                'score': s['score'],
                'verdict': s['verdict'],
                'components': s['components'],
                'close': s['close'],
                'initial_sl_hint': s['initial_sl_hint'],
                'tp_projection': s['tp_projection'],
                'atr14': s['atr14'],
                'flow': flow_map.get(ticker),
            })
        except Exception as e:
            logging.exception("signal scan error for %s", ticker)
            results.append({'ticker': ticker, 'error': 'scan error'})

    results.sort(key=lambda r: r.get('score', 0), reverse=True)
    onsets = [r for r in results if r.get('verdict') == 'SWING_ONSET']
    watches = [r for r in results if r.get('verdict') == 'WATCH']
    return jsonify({
        'min_score': min_score,
        'total_scanned': len(tickers),
        'n_onsets': len(onsets),
        'n_watch': len(watches),
        'onsets': onsets,
        'watch': watches,
    })


@screener_main_bp.route('/api/sector/rotation', methods=['GET'])
def api_sector_rotation():
    from engine.sector_rotation import score_sectors
    try:
        ranked = score_sectors()
        return jsonify({'success': True, 'sectors': ranked})
    except Exception as e:
        logging.exception("sector rotation error")
        return jsonify({'success': False, 'error': 'internal error'}), 500


@screener_main_bp.route('/api/calendar/status', methods=['GET'])
def api_calendar_status():
    from engine.calendar_filter import is_blackout_day, get_upcoming_events
    from datetime import date
    blackout, reason = is_blackout_day()
    return jsonify({
        'today':         date.today().isoformat(),
        'is_blackout':   blackout,
        'reason':        reason,
        'upcoming':      get_upcoming_events(14),
    })


@screener_main_bp.route('/api/calendar/events', methods=['GET'])
def api_calendar_events():
    from engine.calendar_filter import get_all_events, is_blackout_day
    from datetime import date
    blackout, reason = is_blackout_day()
    return jsonify({
        'today':       date.today().isoformat(),
        'is_blackout': blackout,
        'reason':      reason,
        'events':      get_all_events(),
    })


@screener_main_bp.route('/dive/<ticker>')
def dive(ticker):
    return render_template('dive.html', ticker=ticker.upper())


@screener_main_bp.route('/api/fastmover/summary', methods=['GET'])
def api_fastmover_summary():
    from engine.fastmover_study import get_summary
    return jsonify(get_summary(DB_PATH))


@screener_main_bp.route('/api/fastmover/run', methods=['POST'])
def api_fastmover_run():
    import threading
    from engine.fastmover_study import run_study

    def _run():
        try:
            result = run_study(DB_PATH)
            print(f"[fastmover] Study complete: {result['total']} events, "
                  f"{result['inserted_this_run']} inserted")
        except Exception as e:
            print(f"[fastmover] Study error: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({'status': 'started', 'message': 'Fast-mover study running in background. Check /api/fastmover/summary for results.'})


@screener_main_bp.route('/api/ticker/<ticker>/full', methods=['GET'])
def api_ticker_full(ticker):
    import sqlite3, pandas as pd
    from engine.strategies import check_current_entry_signal
    from engine.regime_filter import detect_regime
    from engine.walkforward_multi import STRATEGY_FUNCS

    ticker = ticker.upper()
    conn = sqlite3.connect(DB_PATH)

    # ── OHLCV ──────────────────────────────────────────────────────────────
    df = pd.read_sql(
        'SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC', conn, params=(ticker,)
    )
    if df.empty:
        conn.close()
        return jsonify({'error': f'Ticker {ticker} not found'}), 404

    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)

    latest = df.iloc[-1]
    prev   = df.iloc[-2] if len(df) > 1 else latest
    chg    = latest['close'] - prev['close']
    chg_pct = chg / prev['close'] * 100 if prev['close'] else 0

    price = {
        'date':    str(latest['date'])[:10],
        'open':    latest['open'],
        'high':    latest['high'],
        'low':     latest['low'],
        'close':   latest['close'],
        'volume':  int(latest['volume']),
        'chg':     round(chg, 0),
        'chg_pct': round(chg_pct, 2),
    }

    # ── REGIME ─────────────────────────────────────────────────────────────
    try:
        regime = detect_regime(df)
    except Exception:
        regime = 'UNKNOWN'

    # ── WF SCORES + LIVE SIGNALS ───────────────────────────────────────────
    wf_rows = conn.execute("""
        SELECT strategy, consistency_pct, avg_return_pct, avg_sharpe, weighted_score
        FROM wf_scores WHERE ticker=? ORDER BY weighted_score DESC
    """, (ticker,)).fetchall()
    wf_map = {r[0]: {'consistency_pct': r[1], 'avg_return_pct': r[2],
                     'avg_sharpe': r[3], 'weighted_score': r[4]}
              for r in wf_rows}

    strategies = []
    for name in STRATEGY_FUNCS:
        sig = check_current_entry_signal(ticker, name, df=df)
        wf  = wf_map.get(name, {})
        strategies.append({
            'name':            name,
            'signal':          'BUY' if sig['has_signal'] else '—',
            'has_signal':      sig['has_signal'],
            'signal_reason':   sig.get('reason', ''),
            'consistency_pct': wf.get('consistency_pct', None),
            'avg_return_pct':  wf.get('avg_return_pct', None),
            'avg_sharpe':      wf.get('avg_sharpe', None),
            'weighted_score':  wf.get('weighted_score', None),
        })
    strategies.sort(key=lambda x: (x['has_signal'], x['weighted_score'] or 0), reverse=True)

    # ── FLOW (stockbit_flow last 20 days) ──────────────────────────────────
    flow_rows = conn.execute("""
        SELECT trade_date, net_lot, net_value, composite_score, verdict, smart_money, last_price
        FROM stockbit_flow WHERE ticker=? ORDER BY trade_date DESC LIMIT 20
    """, (ticker,)).fetchall()
    flow_history = [
        {'date': r[0], 'net_lot': r[1], 'net_value': r[2],
         'score': r[3], 'verdict': r[4], 'smart_money': r[5], 'price': r[6]}
        for r in flow_rows
    ]
    flow_latest  = flow_history[0] if flow_history else {}
    cum_delta_20d = [{'date': r['date'], 'net_value': r['net_value']} for r in reversed(flow_history)]

    # ── BROKER FLOW (top 5 buyers/sellers latest day) ──────────────────────
    broker_date = flow_latest.get('date') or ''
    brokers_raw = conn.execute("""
        SELECT broker_code, side, lot, value
        FROM broker_flow WHERE ticker=? AND trade_date=?
        ORDER BY side, ABS(lot) DESC
    """, (ticker, broker_date)).fetchall()
    broker_dates = [r[0] for r in conn.execute("""
        SELECT DISTINCT trade_date FROM broker_flow
        WHERE ticker=? ORDER BY trade_date DESC LIMIT 30
    """, (ticker,)).fetchall()]
    top_brokers = {
        'buyers':  [{'broker': r[0], 'lot': r[2], 'value': r[3]} for r in brokers_raw if r[1] == 'BUY'][:5],
        'sellers': [{'broker': r[0], 'lot': r[2], 'value': r[3]} for r in brokers_raw if r[1] == 'SELL'][:5],
        'date':    broker_date,
        'dates':   broker_dates,
    }

    # ── SUSPENSIONS ────────────────────────────────────────────────────────
    susp_rows = conn.execute("""
        SELECT last_normal_date, resume_date, missing_td, gap_pct
        FROM suspension_events
        WHERE ticker=? AND classification='suspension'
        ORDER BY resume_date DESC
    """, (ticker,)).fetchall()
    suspensions = [
        {
            'last_normal_date': r[0],
            'resume_date':      r[1],
            'missing_td':       r[2],
            'gap_pct':          round(r[3], 4),
        }
        for r in susp_rows
    ]

    conn.close()

    # ── PRE-MOVER SCORE (live, not cached) ────────────────────────────────
    from engine.premover_detector import score_ticker as _score_ticker
    from engine.premover_detector import score_ticker_reversal as _score_reversal
    import sqlite3 as _sq3
    _flow_conn = _sq3.connect(DB_PATH)
    try:
        _frow = _flow_conn.execute("""
            SELECT composite_score FROM stockbit_flow
            WHERE ticker=? ORDER BY trade_date DESC LIMIT 1
        """, (ticker,)).fetchone()
    except Exception:
        _frow = None
    finally:
        _flow_conn.close()
    _ihsg_conn = _sq3.connect(DB_PATH)
    try:
        _ihsg_df = pd.read_sql(
            'SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC',
            _ihsg_conn, params=('IHSG',)
        )
    except Exception:
        _ihsg_df = None
    finally:
        _ihsg_conn.close()
    _pm = _score_ticker(df, ihsg_df=_ihsg_df if (_ihsg_df is not None and not _ihsg_df.empty) else None,
                        flow_score=_frow[0] if _frow else None)
    _pm_rev = _score_reversal(df, flow_score=_frow[0] if _frow else None)

    # ── VPIN multi-day signal ──────────────────────────────────────────────
    from engine.vpin import calc_vpin_multi as _calc_vpin_multi_full
    _vpin_conn = _sq3.connect(DB_PATH)
    try:
        _vpin_raw = _calc_vpin_multi_full(_vpin_conn, ticker, str(latest['date'])[:10])
    except Exception:
        _vpin_raw = None
    finally:
        _vpin_conn.close()
    _vpin = None
    if _vpin_raw:
        _vpin = {
            'signal':        _vpin_raw['signal'],
            'signal_desc':   _vpin_raw['signal_desc'],
            'vpin_today':    _vpin_raw['vpin_today'],
            'vpin_label':    _vpin_raw['vpin_label'],
            'vpin_regime':   _vpin_raw['vpin_regime'],
            'vpin_z':        _vpin_raw['vpin_z'],
            'pressure':      _vpin_raw['pressure'],
            'delta_dir':     _vpin_raw['delta_dir'],
            'price_move':    _vpin_raw['price_move'],
            'lookback_days': _vpin_raw['lookback_days'],
        }

    _ohlcv = df[['date', 'open', 'high', 'low', 'close', 'volume']].tail(250).copy()
    _ohlcv['date'] = _ohlcv['date'].astype(str)

    return jsonify({
        'ticker':         ticker,
        'price':          price,
        'ohlcv':          _ohlcv.to_dict('records'),
        'regime':         regime,
        'strategies':     strategies,
        'flow':           {'latest': flow_latest, 'cum_delta_20d': cum_delta_20d},
        'broker':         top_brokers,
        'premover':       {
            'score':   _pm['score'],
            'reasons': _pm['reasons'],
            'adx':     _pm['adx'],
            'near_52w':  _pm['near_52w'],
            'atr_ratio': _pm['atr_ratio'],
            'vol_dryup': _pm['vol_dryup'],
            'rs':        _pm['rs'],
        },
        'premover_reversal': {
            'score':      _pm_rev['score'],
            'reasons':    _pm_rev.get('reasons', []),
            'vol_ratio':  _pm_rev.get('vol_ratio'),
            'near_low':   _pm_rev.get('near_low'),
            'above_3ma':  _pm_rev.get('above_3ma'),
            'green_day':  _pm_rev.get('green_day'),
            'atr_ratio':  _pm_rev.get('atr_ratio'),
        },
        'vpin': _vpin,
        'suspensions': suspensions,
    })


@screener_main_bp.route('/api/ticker/<ticker>/broker', methods=['GET'])
def api_ticker_broker(ticker):
    import sqlite3
    date = request.args.get('date', '')
    conn = sqlite3.connect(DB_PATH)
    try:
        if not date:
            row = conn.execute(
                "SELECT DISTINCT trade_date FROM broker_flow WHERE ticker=? ORDER BY trade_date DESC LIMIT 1",
                (ticker,)
            ).fetchone()
            date = row[0] if row else ''
        rows = conn.execute("""
            SELECT broker_code, side, lot, value
            FROM broker_flow WHERE ticker=? AND trade_date=?
            ORDER BY side, ABS(lot) DESC
        """, (ticker, date)).fetchall()
        return jsonify({
            'date':    date,
            'buyers':  [{'broker': r[0], 'lot': r[2], 'value': r[3]} for r in rows if r[1] == 'BUY'][:5],
            'sellers': [{'broker': r[0], 'lot': r[2], 'value': r[3]} for r in rows if r[1] == 'SELL'][:5],
        })
    finally:
        conn.close()


STRATEGY_MARKER_META = {
    'vol_weighted':             {'label': 'Vol-Weighted Entry',      'color': '#a78bfa', 'text': 'VW'},
    'momentum':                 {'label': 'Momentum Following',      'color': '#22c55e', 'text': 'M'},
    'vwap_reversion':           {'label': 'VWAP Reversion',          'color': '#eab308', 'text': 'V'},
    'conservative':             {'label': 'Conservative Confirm',    'color': '#06b6d4', 'text': 'C'},
    'Volume Profile POC':       {'label': 'Volume Profile POC',      'color': '#f97316', 'text': 'P'},
    'Inside Bar Breakout':      {'label': 'Inside Bar Breakout',     'color': '#ec4899', 'text': 'I'},
    'NR7 Breakout':             {'label': 'NR7 Breakout',            'color': '#14b8a6', 'text': 'N'},
    'ORB':                      {'label': 'Opening Range Breakout',  'color': '#8b5cf6', 'text': 'O'},
    'Swing Trend':              {'label': 'Swing Trend',             'color': '#3b82f6', 'text': 'S'},
    'Trend Following Breakout': {'label': 'Trend Following Breakout','color': '#ef4444', 'text': 'T'},
}


@screener_main_bp.route('/api/strategy/list', methods=['GET'])
def api_strategy_list():
    from engine.walkforward_multi import STRATEGY_FUNCS
    items = []
    for key in STRATEGY_FUNCS:
        meta = STRATEGY_MARKER_META.get(key, {'label': key, 'color': '#94a3b8', 'text': '•'})
        items.append({'key': key, **meta})
    return jsonify({'strategies': items})


@screener_main_bp.route('/api/strategy/markers/<path:strategy>/<ticker>', methods=['GET'])
def api_strategy_markers(strategy, ticker):
    """Return historical entry markers for a strategy on a ticker.

    Runs the canonical engine/strategies.py function with effectively unlimited
    capital, then projects each Trade.entry_date into a Lightweight Charts marker.
    Daily timeframe only — engine strategies operate on daily bars.
    """
    import sqlite3
    import pandas as pd
    from engine.walkforward_multi import STRATEGY_FUNCS

    ticker = ticker.upper()
    if strategy not in STRATEGY_FUNCS:
        return jsonify({'error': f'Unknown strategy: {strategy}'}), 400

    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql(
            'SELECT date, open, high, low, close, volume FROM ohlcv '
            'WHERE ticker=? ORDER BY date ASC',
            conn, params=(ticker,)
        )
    finally:
        conn.close()

    if df.empty:
        return jsonify({'error': f'No data for {ticker}'}), 404

    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)

    func = STRATEGY_FUNCS[strategy]
    try:
        result = func(df, capital=1e13)
    except Exception as e:
        logging.error(f'[strategy_markers] {strategy}/{ticker}: {e}')
        return jsonify({'error': f'Strategy execution failed: {e}'}), 500

    meta = STRATEGY_MARKER_META.get(strategy, {'color': '#94a3b8', 'text': '•'})
    markers = [
        {
            'time':     str(t.entry_date)[:10],
            'position': 'belowBar',
            'color':    meta['color'],
            'shape':    'arrowUp',
            'text':     meta['text'],
            'size':     2,
        }
        for t in result.get('trades', [])
    ]

    return jsonify({
        'strategy': strategy,
        'ticker':   ticker,
        'count':    len(markers),
        'markers':  markers,
    })


@screener_main_bp.route('/api/ticker/<ticker>/ohlcv', methods=['GET'])
def api_ohlcv_cache(ticker):
    import sqlite3, json, time
    import yfinance as yf

    ticker = ticker.upper()
    tf = request.args.get('tf', '1h').lower()
    if tf not in ('1h', '1d', '1w'):
        return jsonify({'error': 'tf must be 1h, 1d or 1w'}), 400

    ttl = 900 if tf == '1h' else (14400 if tf == '1d' else 86400)  # 15min / 4h / 24h
    now = time.time()

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            'SELECT fetched_at, data FROM ohlcv_cache WHERE ticker=? AND tf=?',
            (ticker, tf)
        ).fetchone()

        if row and (now - row[0]) < ttl:
            return jsonify(json.loads(row[1]))

        # cache miss or expired — fetch from yfinance
        try:
            if tf == '1h':
                df = yf.Ticker(ticker + '.JK').history(period='60d', interval='1h', timeout=10)
            elif tf == '1d':
                df = yf.Ticker(ticker + '.JK').history(period='2y', interval='1d', timeout=10)
            else:
                df = yf.Ticker(ticker + '.JK').history(period='2y', interval='1wk', timeout=10)
        except Exception as e:
            logging.error(f'[ohlcv_cache] yfinance error {ticker}/{tf}: {e}')
            return jsonify({'error': 'Failed to fetch market data'}), 502

        if df is None or df.empty:
            return jsonify({'error': f'No data for {ticker}'}), 404

        candles = []
        for ts, r in df.iterrows():
            t = (int(ts.timestamp()) + 25200) if tf == '1h' else ts.strftime('%Y-%m-%d')
            candles.append({
                'time':   t,
                'open':   round(float(r['Open']),  2),
                'high':   round(float(r['High']),  2),
                'low':    round(float(r['Low']),   2),
                'close':  round(float(r['Close']), 2),
                'volume': int(r['Volume']),
            })

        payload = {'tf': tf, 'ticker': ticker, 'candles': candles}
        data_str = json.dumps(payload)

        conn.execute(
            'INSERT OR REPLACE INTO ohlcv_cache (ticker, tf, fetched_at, data) VALUES (?,?,?,?)',
            (ticker, tf, now, data_str)
        )
        conn.commit()
        return jsonify(payload)
    finally:
        conn.close()


@screener_main_bp.route('/api/premover/watchlist', methods=['GET'])
def api_premover_watchlist():
    from engine.premover_detector import get_watchlist
    min_score    = int(request.args.get('min_score', 50))
    days         = int(request.args.get('days', 5))
    pattern_type = request.args.get('pattern_type', None)
    items = get_watchlist(DB_PATH, min_score=min_score, days=days,
                          pattern_type=pattern_type)
    return jsonify({'count': len(items), 'watchlist': items})


@screener_main_bp.route('/api/premover/run', methods=['POST'])
def api_premover_run():
    from engine.premover_detector import run_scan
    from scheduler import send_telegram as _tg

    def _bg():
        try:
            new = run_scan(DB_PATH, send_alert_fn=_tg)
            print(f"[premover] Manual scan done: {len(new)} new setups")
        except Exception as e:
            print(f"[premover] Manual scan error: {e}")

    threading.Thread(target=_bg, daemon=True).start()
    return jsonify({'status': 'started',
                    'message': 'Pre-mover scan running. Check /api/premover/watchlist for results.'})
