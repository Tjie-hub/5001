import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from engine.strategies import check_current_entry_signal, get_ticker_data
from flow_filter import get_flow_confirmation, get_flow_batch
from scheduler import start_scheduler, scan_momentum_signals, daily_signal_scan, send_telegram
from routes_backtest_multi import backtest_multi_bp
from screener.routes import screener_bp
from screener.db import init_screener_tables
from stockbit_fetcher import init_flow_db
import requests
import hashlib
import hmac
import threading
import time

load_dotenv()
DB_PATH = os.getenv('DB_PATH', '/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db')
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8790169868:AAE6qno0LrxxIdFydSKSLKhD8EPUzevPIFo")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5919142813")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://192.168.31.120:5001")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/telegram/updates")

app = Flask(__name__)
app.register_blueprint(backtest_multi_bp)
app.register_blueprint(screener_bp, url_prefix='/api/screener')


def attach_flow_data(results, include_flow=True, flow_threshold=2):
    """
    Attach flow data to scan results.
    
    Args:
        results: List of dicts with ticker + signal data
        include_flow: Whether to fetch flow data
        flow_threshold: Minimum flow score to mark as confirmed (+2 default)
    
    Returns:
        results with added 'flow' key for each ticker
    """
    if not include_flow:
        return results
    
    # Extract unique tickers
    tickers = list(set(r['ticker'] for r in results if 'ticker' in r))
    if not tickers:
        return results
    
    # Batch fetch flow data
    try:
        flow_data = get_flow_batch(tickers, token=None, delay=0.8)
    except Exception as e:
        print(f"Flow fetch error: {e}")
        flow_data = {}
    
    # Attach to results
    for r in results:
        ticker = r.get('ticker')
        if not ticker:
            continue
            
        if ticker in flow_data:
            flow = flow_data[ticker]
            r['flow'] = {
                'available': True,
                'score': flow['score'],
                'verdict': flow['verdict'],
                'smart_money': flow['smart_money'],
                'cum_delta': flow['cum_delta'],
                'price_chg_pct': flow['price_chg_pct'],
                'confirmed': flow['score'] >= flow_threshold,  # +2 threshold
                'timestamp': flow['timestamp']
            }
        else:
            # No flow data available
            r['flow'] = {
                'available': False,
                'score': None,
                'verdict': 'UNAVAILABLE',
                'smart_money': None,
                'confirmed': None,
                'reason': 'Data not available or token expired'
            }
    
    return results


@app.route("/")
@app.route("/backtest/multi")
def backtest_multi_page():
    return render_template("backtest_multi.html")


@app.route('/api/backtest/scan_all', methods=['POST'])
def api_scan_all():
    import sqlite3, pandas as pd
    from engine.walkforward_multi import run_all_strategies
    from engine.regime_filter import detect_regime
    from routes_backtest_multi import resolve_filters
    body = request.get_json(force=True)
    capital             = float(body.get('capital', 50_000_000))
    filters             = resolve_filters(body.get('filters', []))
    strategy            = body.get('strategy', 'vol_weighted')
    filter_mode         = body.get('filter_mode', 'all')
    flow_confirmed_only = body.get('flow_confirmed_only', False)
    use_wf_filter       = body.get('use_wf_filter', False)
    wf_min_consistency  = float(body.get('wf_min_consistency', 50.0))
    conn = sqlite3.connect(DB_PATH)
    tickers = [r[0] for r in conn.execute('SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker').fetchall()]
    conn.close()

    results = []
    for ticker in tickers:
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql('SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC', conn, params=(ticker,))
            conn.close()
            if len(df) < 60:
                continue
            for c in ['open','high','low','close','volume']:
                df[c] = df[c].astype(float)
            strat_results = run_all_strategies(df, capital=capital, filters=filters)
            best = max(strat_results, key=lambda x: x['total_return_pct'])
            # Regime detection — rule-based only (fast)
            try:
                final_regime = detect_regime(df)
                regime_conf = 0
            except Exception:
                final_regime = "UNCERTAIN"
                regime_conf = 0
            # Check current entry signal
            signal_check = check_current_entry_signal(ticker, strategy, df)
            # Flow enrichment (per ticker, non-blocking)
            flow_score  = None
            flow_reason = "SKIP"
            flow_ok     = True
            if flow_confirmed_only:
                try:
                    from flow_filter import flow_confirms_signal
                    flow_ok, flow_reason, flow_data = flow_confirms_signal(ticker, "BUY")
                    flow_score = flow_data["score"] if flow_data else None
                except Exception as _fe:
                    flow_ok     = True   # jika error, jangan block
                    flow_reason = f"ERR:{_fe}"

            if flow_confirmed_only and not flow_ok:
                results.append({
                    'ticker': ticker, 'has_signal': False,
                    'fail_reason': f"FLOW: {flow_reason}",
                    'flow_score': flow_score, 'flow_reason': flow_reason,
                    'best_return': best['total_return_pct'],
                    'best_strategy': best['strategy'],
                    'profitable': False
                })
                continue

            results.append({
                'ticker': ticker,
                'best_strategy': best['strategy'],
                'best_return': best['total_return_pct'],
                'best_winrate': best['win_rate'],
                'best_sharpe': best['sharpe'],
                'best_trades': best['total_trades'],
                'profitable': bool(best['total_return_pct'] > 0),
                'regime': final_regime,
                'regime_conf': regime_conf,
                'has_signal': signal_check['has_signal'],
                'signal_reason': signal_check['reason'],
                'signal_details': signal_check['details'],
                'flow_score': flow_score,
                'flow_reason': flow_reason,
            })
        except Exception as e:
            results.append({'ticker': ticker, 'error': str(e), 'best_return': -999})
    
    # Load wf_scores untuk enrichment
    wf_map = {}
    try:
        conn_wf = sqlite3.connect(DB_PATH)
        # Ambil best WF score per ticker across ALL strategies
        rows = conn_wf.execute("""
            SELECT ticker,
                   MAX(consistency_pct) as best_consistency,
                   MAX(weighted_score)  as best_wf_score,
                   strategy
            FROM wf_scores
            GROUP BY ticker
        """).fetchall()
        conn_wf.close()
        wf_map = {r[0]: {
            'consistency_pct': r[1],
            'weighted_score':  r[2],
            'best_strategy_wf': r[3]
        } for r in rows}
    except Exception:
        pass

    for r in results:
        wf = wf_map.get(r['ticker'], {})
        r['consistency_pct'] = wf.get('consistency_pct', None)
        r['wf_score']        = wf.get('weighted_score', 0)

    # Min trades guard: mark low-trade results
    for r in results:
        if not r.get('error') and r.get('best_trades', 0) < 5:
            r['low_trades'] = True
            r['profitable'] = False  # exclude from profitable count

    # WF consistency filter
    if use_wf_filter:
        results = [r for r in results if (r.get('consistency_pct') or 0) >= wf_min_consistency]

    # Filter hanya yang ada signal (sudah di-early filter, tapi double-check)
    results = [r for r in results if r.get('has_signal', False)]
    
    # Sort by WF score dan return
    results.sort(key=lambda x: (x.get('wf_score', 0), x.get('best_return', -999)), reverse=True)
    
    # Limit max 15 cards dengan signal terbaik
    results = results[:15]
    profitable = [r for r in results if r.get('profitable')]
    tickers_with_signal = sum(1 for r in results if r.get('has_signal', False))
    
    return jsonify({
        'success': True,
        'total': len(results), 
        'profitable': len(profitable), 
        'results': results,
        'summary': {
            'total_tickers_scanned': len(tickers),
            'tickers_with_signal': tickers_with_signal,
            'tickers_displayed': len(results),
            'filter_mode': filter_mode,
            'strategy': strategy
        }
    })


@app.route('/api/backtest/quick_scan', methods=['POST'])
def api_quick_scan():
    """Quick scan - signal check + backtest metrics for each ticker"""
    import sqlite3, pandas as pd
    from engine.strategies import check_current_entry_signal
    from engine.walkforward_multi import run_all_strategies
    from engine.regime_filter import detect_regime

    body = request.get_json(force=True)
    strategy = body.get('strategy', 'vol_weighted')
    filter_mode = body.get('filter_mode', 'all')
    capital = float(body.get('capital', 50_000_000))

    conn = sqlite3.connect(DB_PATH)
    tickers = [r[0] for r in conn.execute('SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker').fetchall()]
    conn.close()

    # Load backtest cache for today
    from datetime import date as _date
    today = _date.today().isoformat()
    cache_map = {}
    try:
        _init_backtest_cache()
        conn_c = sqlite3.connect(DB_PATH)
        rows = conn_c.execute(
            "SELECT ticker, best_strategy, best_return, win_rate, sharpe, total_trades, profitable, regime FROM backtest_cache WHERE computed_date=?",
            (today,)
        ).fetchall()
        conn_c.close()
        cache_map = {r[0]: dict(zip(['best_strategy','best_return','win_rate','sharpe','total_trades','profitable','regime'], r[1:])) for r in rows}
    except Exception:
        pass

    results = []
    for ticker in tickers:
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql('SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC', conn, params=(ticker,))
            conn.close()

            if len(df) < 60:
                continue

            for c in ['open','high','low','close','volume']:
                df[c] = df[c].astype(float)

            # Get signal check (fast — always live)
            signal_check = check_current_entry_signal(ticker, strategy, df)

            # Only include tickers with signals
            if not signal_check['has_signal']:
                continue

            # Try cache first, fallback to live backtest
            cached = cache_map.get(ticker)
            if cached:
                best = cached
                regime = cached.get('regime', 'UNCERTAIN')
            else:
                # Fallback: run backtest live
                try:
                    strat_results = run_all_strategies(df, capital=capital)
                    best_r = max(strat_results, key=lambda x: x['total_return_pct'])
                    best = {
                        'best_strategy': best_r['strategy'],
                        'best_return': best_r['total_return_pct'],
                        'win_rate': best_r['win_rate'],
                        'sharpe': best_r.get('sharpe', 0),
                        'total_trades': best_r.get('total_trades', 0),
                        'profitable': int(best_r['total_return_pct'] > 0)
                    }
                except Exception:
                    best = None
                try:
                    regime = detect_regime(df)
                except Exception:
                    regime = "UNCERTAIN"

            # Build result with both signal and backtest data
            result = {
                'ticker': ticker,
                'has_signal': signal_check['has_signal'],
                'signal_reason': signal_check['reason'],
                'signal_details': signal_check['details'],
                'regime': regime,
            }

            # Add price and volume ratio from signal details
            if signal_check['details']:
                result['close'] = signal_check['details'].get('price')
                result['vol_ratio'] = signal_check['details'].get('vr')

            # Add backtest results (from cache or live)
            if best:
                result['best_strategy'] = best.get('best_strategy') or best.get('strategy')
                result['best_return'] = best.get('best_return') or best.get('total_return_pct') or 0
                result['win_rate'] = best.get('win_rate', 0)
                result['sharpe'] = best.get('sharpe', 0)
                result['best_trades'] = best.get('total_trades', 0)
                result['profitable'] = bool(best.get('profitable') or best.get('best_return', 0) > 0)

            results.append(result)
        except Exception as e:
            print(f"Error {ticker}: {e}")
            continue

    # Load WF scores for enrichment
    wf_map = {}
    try:
        conn_wf = sqlite3.connect(DB_PATH)
        rows = conn_wf.execute("""
            SELECT ticker, MAX(weighted_score) as best_wf_score
            FROM wf_scores
            GROUP BY ticker
        """).fetchall()
        conn_wf.close()
        wf_map = {r[0]: r[1] for r in rows}
    except Exception:
        pass

    # Add WF scores to results
    for r in results:
        if r['ticker'] in wf_map:
            r['wf_score'] = wf_map[r['ticker']]

    # Filter by profit status
    profitable = [r for r in results if r.get('profitable', False)]
    tickers_with_signal = sum(1 for r in results if r.get('has_signal', False))

    # Attach flow data (optional mode - display only, no filtering)
    include_flow = body.get('include_flow', True)
    flow_threshold = body.get('flow_threshold', 2)
    results = attach_flow_data(results, include_flow, flow_threshold)

    return jsonify({
        'success': True,
        'total': len(results),
        'profitable': len(profitable),
        'results': results,
        'summary': {
            'total_tickers_scanned': len(tickers),
            'tickers_with_signal': tickers_with_signal,
            'tickers_displayed': len(results),
            'filter_mode': filter_mode,
            'strategy': strategy,
            'flow_enabled': include_flow,
            'flow_threshold': flow_threshold
        }
    })


@app.route("/signal-scanner")
def signal_scanner_page():
    return render_template("backtest_multi.html")


def _init_backtest_cache():
    """Create backtest_cache table if not exists."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_cache (
            ticker TEXT NOT NULL,
            computed_date TEXT NOT NULL,
            best_strategy TEXT,
            best_return REAL,
            win_rate REAL,
            sharpe REAL,
            total_trades INTEGER,
            profitable INTEGER,
            regime TEXT,
            updated_at TEXT,
            PRIMARY KEY (ticker, computed_date)
        )
    """)
    conn.commit()
    conn.close()


@app.route('/api/backtest/precompute', methods=['POST'])
def api_precompute():
    """
    Pre-compute and cache backtest results for all tickers.
    Run this once daily (or manually) to speed up quick_scan.
    """
    import sqlite3, pandas as pd
    from engine.walkforward_multi import run_all_strategies
    from engine.regime_filter import detect_regime
    from datetime import date

    _init_backtest_cache()
    capital = float(request.get_json(force=True).get('capital', 50_000_000))
    today = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    tickers = [r[0] for r in conn.execute('SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker').fetchall()]
    conn.close()

    computed = 0
    errors = 0
    for ticker in tickers:
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql('SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC', conn, params=(ticker,))
            conn.close()
            if len(df) < 60:
                continue
            for c in ['open','high','low','close','volume']:
                df[c] = df[c].astype(float)

            strat_results = run_all_strategies(df, capital=capital)
            best = max(strat_results, key=lambda x: x['total_return_pct'])
            try:
                regime = detect_regime(df)
            except Exception:
                regime = "UNCERTAIN"

            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT OR REPLACE INTO backtest_cache
                (ticker, computed_date, best_strategy, best_return, win_rate, sharpe, total_trades, profitable, regime, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?, datetime('now'))
            """, (ticker, today, best['strategy'], best['total_return_pct'],
                  best['win_rate'], best.get('sharpe', 0), best.get('total_trades', 0),
                  int(best['total_return_pct'] > 0), regime))
            conn.commit()
            conn.close()
            computed += 1
        except Exception as e:
            errors += 1
            print(f"[precompute] Error {ticker}: {e}")

    return jsonify({'computed': computed, 'errors': errors, 'date': today})


@app.route('/api/paper/config', methods=['GET'])
def api_paper_config():
    from paper_trade import init_paper_table, get_config
    init_paper_table()
    cfg = get_config()
    return jsonify(cfg)


@app.route('/api/backtest/multi_quick_scan', methods=['POST'])
def api_multi_quick_scan():
    """Quick scan - support multiple strategies with intersection mode"""
    import sqlite3, pandas as pd
    from engine.strategies import check_current_entry_signal
    
    body = request.get_json(force=True)
    strategies = body.get('strategies', ['vol_weighted'])
    if isinstance(strategies, str):
        strategies = [strategies]
    filter_mode = body.get('filter_mode', 'all')
    intersection_mode = body.get('intersection_mode', True)  # NEW: default True
    
    conn = sqlite3.connect(DB_PATH)
    tickers = [r[0] for r in conn.execute('SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker').fetchall()]
    conn.close()
    
    # Collect signals per ticker per strategy
    ticker_signals = {}  # {ticker: {strategy: signal_data}}
    
    for ticker in tickers:
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql('SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC', conn, params=(ticker,))
            conn.close()

            if len(df) < 20:
                continue

            for c in ['open','high','low','close','volume']:
                df[c] = df[c].astype(float)

            ticker_signals[ticker] = {}

            for strategy in strategies:
                signal_check = check_current_entry_signal(ticker, strategy, df)
                ticker_signals[ticker][strategy] = {
                    'has_signal': signal_check['has_signal'],
                    'reason': signal_check['reason'],
                    'details': signal_check['details']
                }
        except Exception as e:
            print(f"Error {ticker}: {e}")
            continue
    
    # Filter based on mode
    results = []
    
    if intersection_mode:
        # INTERSECTION: hanya ticker yang pass SEMUA strategy
        from engine.walkforward_multi import run_all_strategies
        from engine.regime_filter import detect_regime
        capital = float(body.get('capital', 50_000_000))

        for ticker, signals in ticker_signals.items():
            # Skip jika tidak punya signal untuk semua strategy
            if len(signals) < len(strategies):
                continue

            # Check jika semua strategy punya signal
            all_pass = all(signals[s]['has_signal'] for s in strategies)

            # Filter berdasarkan mode
            if filter_mode == 'signals_only' and not all_pass:
                continue

            # Only run backtest for tickers with all signals (optimization)
            if not all_pass:
                continue

            # Combine info dari semua strategy
            combined_reasons = []
            combined_details = {}

            for strategy in strategies:
                sig = signals[strategy]
                combined_reasons.append(f"{strategy}: {sig['reason']}")
                combined_details[strategy] = sig['details']

            # Run backtest untuk get metrics
            best = None
            regime = "UNCERTAIN"
            try:
                conn = sqlite3.connect(DB_PATH)
                df = pd.read_sql('SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC', conn, params=(ticker,))
                conn.close()
                if len(df) >= 60:
                    for c in ['open','high','low','close','volume']:
                        df[c] = df[c].astype(float)
                    strat_results = run_all_strategies(df, capital=capital)
                    best = max(strat_results, key=lambda x: x['total_return_pct'])
                    regime = detect_regime(df)
            except Exception:
                pass

            result = {
                'ticker': ticker,
                'strategies': strategies,
                'has_signal': all_pass,
                'signal_reasons': combined_reasons,
                'signal_details': combined_details,
                'regime': regime,
            }

            # Add price and volume ratio from first strategy's details
            first_strategy = strategies[0]
            if combined_details.get(first_strategy):
                result['close'] = combined_details[first_strategy].get('price')
                result['vol_ratio'] = combined_details[first_strategy].get('vr')

            # Add backtest results
            if best:
                result['best_strategy'] = best['strategy']
                result['best_return'] = best['total_return_pct']
                result['win_rate'] = best['win_rate']
                result['sharpe'] = best.get('sharpe', 0)
                result['best_trades'] = best.get('total_trades', 0)
                result['profitable'] = bool(best['total_return_pct'] > 0)

            results.append(result)

        # Load WF scores
        wf_map = {}
        try:
            conn_wf = sqlite3.connect(DB_PATH)
            rows = conn_wf.execute("""
                SELECT ticker, MAX(weighted_score) as best_wf_score
                FROM wf_scores
                GROUP BY ticker
            """).fetchall()
            conn_wf.close()
            wf_map = {r[0]: r[1] for r in rows}
        except Exception:
            pass

        # Add WF scores
        for r in results:
            if r['ticker'] in wf_map:
                r['wf_score'] = wf_map[r['ticker']]

        # Attach flow for intersection results
        include_flow = body.get('include_flow', True)
        flow_threshold = body.get('flow_threshold', 2)
        results = attach_flow_data(results, include_flow, flow_threshold)

        # Return early for intersection mode
        profitable = [r for r in results if r.get('profitable', False)]
        tickers_with_signal = len([r for r in results if r.get('has_signal', False)])

        return jsonify({
            'success': True,
            'total': len(results),
            'profitable': len(profitable),
            'results': results,
            'summary': {
                'total_tickers_scanned': len(tickers),
                'tickers_with_signal': tickers_with_signal,
                'tickers_displayed': len(results),
                'filter_mode': filter_mode,
                'strategies': strategies,
                'intersection_mode': True
            },
            'multi_strategy': len(strategies) > 1,
            'intersection_mode': True
        })
    else:
        # UNION: group by strategy - include backtest metrics
        from engine.walkforward_multi import run_all_strategies
        from engine.regime_filter import detect_regime
        capital = float(body.get('capital', 50_000_000))
        results_by_strategy = {s: [] for s in strategies}

        for ticker, signals in ticker_signals.items():
            # Fetch data once per ticker
            try:
                conn = sqlite3.connect(DB_PATH)
                df = pd.read_sql('SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC', conn, params=(ticker,))
                conn.close()
                if len(df) < 60:
                    continue
                for c in ['open','high','low','close','volume']:
                    df[c] = df[c].astype(float)
                strat_results = run_all_strategies(df, capital=capital)
                best = max(strat_results, key=lambda x: x['total_return_pct'])
                regime = detect_regime(df)
            except Exception:
                best = None
                regime = "UNCERTAIN"

            for strategy in strategies:
                if strategy in signals:
                    sig = signals[strategy]
                    if filter_mode == 'signals_only' and not sig['has_signal']:
                        continue

                    result = {
                        'ticker': ticker,
                        'strategy': strategy,
                        'has_signal': sig['has_signal'],
                        'signal_reason': sig['reason'],
                        'signal_details': sig['details'],
                        'regime': regime,
                    }

                    # Add price and volume ratio
                    if sig['details']:
                        result['close'] = sig['details'].get('price')
                        result['vol_ratio'] = sig['details'].get('vr')

                    # Add backtest results
                    if best:
                        result['best_strategy'] = best['strategy']
                        result['best_return'] = best['total_return_pct']
                        result['win_rate'] = best['win_rate']
                        result['sharpe'] = best.get('sharpe', 0)
                        result['best_trades'] = best.get('total_trades', 0)
                        result['profitable'] = bool(best['total_return_pct'] > 0)

                    results_by_strategy[strategy].append(result)

        # Load WF scores
        wf_map = {}
        try:
            conn_wf = sqlite3.connect(DB_PATH)
            rows = conn_wf.execute("""
                SELECT ticker, MAX(weighted_score) as best_wf_score
                FROM wf_scores
                GROUP BY ticker
            """).fetchall()
            conn_wf.close()
            wf_map = {r[0]: r[1] for r in rows}
        except Exception:
            pass

        # Add WF scores to all results
        for strategy_results in results_by_strategy.values():
            for r in strategy_results:
                if r['ticker'] in wf_map:
                    r['wf_score'] = wf_map[r['ticker']]

        # Attach flow for union results
        include_flow = body.get('include_flow', True)
        flow_threshold = body.get('flow_threshold', 2)
        for strategy in results_by_strategy:
            results_by_strategy[strategy] = attach_flow_data(
                results_by_strategy[strategy],
                include_flow,
                flow_threshold
            )

        return jsonify({
            'success': True,
            'results': results_by_strategy,
            'summary': {
                'total_tickers_scanned': len(tickers),
                'total_signals': sum(len(r) for r in results_by_strategy.values()),
                'filter_mode': filter_mode,
                'strategies': strategies,
                'intersection_mode': False,
                'by_strategy': {s: len(results_by_strategy[s]) for s in strategies}
            },
            'multi_strategy': True
        })


@app.route("/api/signals/today", methods=["GET"])
def api_signals_today():
    signals = scan_momentum_signals()
    return jsonify({"count": len(signals), "signals": signals})

@app.route("/api/scheduler/run", methods=["POST"])
def api_run_scan():
    signals = daily_signal_scan()
    return jsonify({"count": len(signals), "signals": signals})


@app.route('/api/screener/swing_onset', methods=['POST'])
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
            results.append({'ticker': ticker, 'error': str(e)})

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


@app.route('/api/paper/open', methods=['POST'])
def api_paper_open():
    from paper_trade import open_trade, init_paper_table
    init_paper_table()
    body = request.get_json(force=True)
    kwargs = {}
    if body.get('sl_price'):
        kwargs['sl_price'] = float(body['sl_price'])
    if body.get('tp_price'):
        kwargs['tp_price'] = float(body['tp_price'])
    if body.get('strategy'):
        kwargs['strategy'] = body['strategy']
    return jsonify(open_trade(body['ticker'], float(body['entry_price']), **kwargs))

@app.route('/api/paper/close', methods=['POST'])
def api_paper_close():
    from paper_trade import close_trade
    from scheduler import send_telegram
    body = request.get_json(force=True)
    result = close_trade(int(body['trade_id']), float(body['exit_price']), body.get('reason','MANUAL'), notify=False)
    if 'pnl_rp' in result:
        emoji = "🟢" if result['pnl_rp'] >= 0 else "🔴"
        send_telegram(f"{emoji} Paper Trade Closed - {result['ticker']} | {result['exit_reason']} | P&L: Rp {result['pnl_rp']:,} ({result['pnl_pct']:+.2f}%)")
    return jsonify(result)


@app.route('/api/paper/clear_history', methods=['POST'])
def api_paper_clear_history():
    from paper_trade import clear_history
    result = clear_history()
    return __import__('flask').jsonify({'status': 'ok', 'deleted': result['deleted']})

@app.route('/api/paper/summary', methods=['GET'])
def api_paper_summary():
    from paper_trade import get_summary, init_paper_table
    init_paper_table()
    return jsonify(get_summary())


@app.route('/api/flow/monitor', methods=['GET'])
def api_flow_monitor():
    import sqlite3
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


@app.route('/api/signals/custom', methods=['POST'])
def api_signals_custom():
    import sqlite3, pandas as pd, logging
    from engine.strategies import calc_vol_ratio
    from engine.regime_filter import RegimeClassifier, get_macro_overlay, apply_macro_overlay
    import datetime as _dt

    body = request.get_json(force=True)
    tickers_input = [t.strip().upper() for t in body.get('tickers', '').split(',') if t.strip()]
    use_fundamental = body.get('use_fundamental', True)
    use_flow        = body.get('use_flow', True)
    use_consist     = body.get('use_consist', True)
    use_regime      = body.get('use_regime', True)
    use_streak      = body.get('use_streak', True)
    vr_min          = float(body.get('vr_min', 1.3))

    conn = sqlite3.connect(DB_PATH)
    all_tickers = [r[0] for r in conn.execute('SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker').fetchall()]
    conn.close()
    tickers = tickers_input if tickers_input else all_tickers

    conn = sqlite3.connect(DB_PATH)
    wf_rows = conn.execute("SELECT ticker, consistency_pct, weighted_score FROM wf_scores WHERE strategy='Momentum Following'").fetchall()
    conn.close()
    wf_map = {r[0]: {"consistency_pct": r[1], "weighted_score": r[2]} for r in wf_rows}

    try:
        macro_data = get_macro_overlay()
    except Exception:
        macro_data = {"idr_weakening": 0.0, "bi_rate": 6.25}

    results = []
    for ticker in tickers:
        row = {"ticker": ticker, "passed": False, "fail_reason": None}

        if use_fundamental:
            from scheduler import check_fundamental
            fund_ok, fund_reason = check_fundamental(ticker)
            if not fund_ok:
                row["fail_reason"] = f"FUND: {fund_reason}"
                results.append(row)
                continue
        row["fundamental"] = "OK" if use_fundamental else "SKIP"

        if use_flow:
            from flow_filter import flow_confirms_signal
            flow_ok, flow_reason, flow_data = flow_confirms_signal(ticker, "BUY")
            row["flow"] = flow_reason
            if not flow_ok:
                row["fail_reason"] = f"FLOW: {flow_reason}"
                results.append(row)
                continue
        else:
            row["flow"] = "SKIP"

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql('SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC', conn, params=(ticker,))
            conn.close()
            if len(df) < 25:
                row["fail_reason"] = "DATA: bars < 25"
                results.append(row)
                continue
            for c in ["open","high","low","close","volume"]:
                df[c] = df[c].astype(float)

            vr = calc_vol_ratio(df)
            vr_val = round(float(vr.iloc[-1]), 2)
            streak = (df["close"] > df["close"].shift(1)) & (df["close"].shift(1) > df["close"].shift(2))
            streak_val = bool(streak.iloc[-1])
            last = df.iloc[-1]
            row["close"] = round(float(last["close"]))
            row["vr"] = vr_val
            row["streak"] = streak_val

            if use_streak and not streak_val:
                row["fail_reason"] = f"STREAK: False (VR={vr_val})"
                results.append(row)
                continue
            if vr_val < vr_min:
                row["fail_reason"] = f"VR: {vr_val} < {vr_min}"
                results.append(row)
                continue

            wf = wf_map.get(ticker)
            row["consistency"] = wf["consistency_pct"] if wf else None
            row["wf_score"] = wf["weighted_score"] if wf else 0
            if use_consist and wf and wf["consistency_pct"] < 50.0:
                row["fail_reason"] = f"CONSIST: {wf['consistency_pct']}% < 50%"
                results.append(row)
                continue

            regime_label = "N/A"
            regime_conf  = 0
            try:
                clf = RegimeClassifier()
                clf.train(df)
                regime_info = clf.predict(df)
                adj_regime, _ = apply_macro_overlay(regime_info[0], macro_data)
                regime_label = adj_regime
                regime_conf  = regime_info[1]
            except Exception:
                pass
            row["regime"] = regime_label
            row["regime_conf"] = round(regime_conf, 2)

            if use_regime and regime_label == "UNCERTAIN":
                row["fail_reason"] = f"REGIME: UNCERTAIN ({round(regime_conf*100)}%)"
                results.append(row)
                continue

            row["passed"] = True
        except Exception as e:
            row["fail_reason"] = f"ERROR: {str(e)[:50]}"
        results.append(row)

    passed = [r for r in results if r["passed"]]
    failed = [r for r in results if not r["passed"]]

    # Telegram notif
    try:
        from scheduler import send_telegram
        from datetime import datetime
        import pytz
        WIB = pytz.timezone("Asia/Jakarta")
        now_str = datetime.now(WIB).strftime("%d/%m/%Y %H:%M")
        active_filters = []
        if use_fundamental: active_filters.append("Fundamental")
        if use_flow:        active_filters.append("Flow")
        if use_consist:     active_filters.append("WF Consist")
        if use_regime:      active_filters.append("Regime")
        if use_streak:      active_filters.append("Streak")
        filter_str = " · ".join(active_filters) if active_filters else "No filters"
        ticker_label = ", ".join(tickers_input) if tickers_input else "ALL"

        if passed:
            msg = f"🔍 <b>Custom Scan — {now_str}</b>\n"
            msg += f"🎯 Ticker: {ticker_label}\n"
            msg += f"⚙️ Filter aktif: <i>{filter_str}</i> | VR≥{vr_min}x\n"
            msg += f"✅ {len(passed)} lolos / {len(results)} ticker\n\n"
            for r in passed:
                regime_emoji = "📈" if r.get("regime") == "TRENDING" else "📉" if r.get("regime") == "SIDEWAYS" else "❓"
                msg += f"🟢 <b>{r['ticker']}</b> Rp {r.get('close',0):,}\n"
                msg += f"   VR: {r.get('vr','?')}x | {regime_emoji} {r.get('regime','N/A')} ({round(r.get('regime_conf',0)*100)}%)\n"
                if r.get('flow') and r['flow'] != 'SKIP':
                    msg += f"   Flow: {r['flow']}\n"
                if r.get('consistency') is not None:
                    msg += f"   Consist: {r['consistency']}% | WF: {r.get('wf_score',0):.3f}\n"
                msg += "\n"
            msg += f"⚠️ <i>Custom scan — bukan sinyal resmi</i>"
        else:
            msg = f"🔍 <b>Custom Scan — {now_str}</b>\n"
            msg += f"🎯 Ticker: {ticker_label}\n"
            msg += f"⚙️ Filter aktif: <i>{filter_str}</i> | VR≥{vr_min}x\n\n"
            msg += f"❌ Tidak ada ticker lolos dari {len(results)} yang discan."
        send_telegram(msg)
    except Exception as _te:
        print(f"Telegram error: {_te}")

    return jsonify({"total": len(results), "passed": len(passed), "failed": len(failed), "results": results})


@app.route('/api/flow/check', methods=['POST'])
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/broker-flow/<ticker>', methods=['GET'])
def api_broker_flow(ticker):
    import sqlite3
    from datetime import date
    ticker = ticker.upper()
    trade_date = request.args.get('date', None)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Latest date if not specified
    if not trade_date:
        row = conn.execute(
            "SELECT MAX(trade_date) FROM broker_flow WHERE ticker=?", (ticker,)
        ).fetchone()
        trade_date = row[0] if row and row[0] else str(date.today())

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

    # Available dates for this ticker
    dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM broker_flow WHERE ticker=? ORDER BY trade_date DESC LIMIT 30",
        (ticker,)
    ).fetchall()]
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


@app.route('/api/broker-flow/dates/<ticker>', methods=['GET'])
def api_broker_flow_dates(ticker):
    import sqlite3
    ticker = ticker.upper()
    conn = sqlite3.connect(DB_PATH)
    dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM broker_flow WHERE ticker=? ORDER BY trade_date DESC LIMIT 30",
        (ticker.upper(),)
    ).fetchall()]
    conn.close()
    return jsonify({'ticker': ticker, 'dates': dates})


# ==================== TELEGRAM WEBHOOK ====================

def handle_telegram_message(message):
    """Process Telegram messages and commands."""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '').lower().strip()
    
    if not chat_id:
        return
    
    # Extract command (text starting with /)
    if text.startswith('/'):
        command = text.split()[0][1:]  # Remove '/'
        
        if command == 'start':
            send_telegram_reply(chat_id, "🤖 *IDX Walkforward Bot Activated*\n\nAvailable commands:\n/status - Current trading status\n/help - Show help")
        elif command == 'status':
            handle_status_command(chat_id)
        elif command == 'help':
            send_telegram_reply(chat_id, 
                "📋 *Available Commands:*\n\n"
                "/status - Get trading status\n"
                "/signals - Recent signals\n"
                "/flow - Flow confirmation status\n"
                "/help - Show this help message")
        elif command == 'signals':
            handle_signals_command(chat_id)
        elif command == 'flow':
            handle_flow_command(chat_id)
        else:
            send_telegram_reply(chat_id, f"❌ Unknown command: /{command}")
    else:
        # Echo non-command messages
        if text:
            send_telegram_reply(chat_id, f"📝 You said: {text}")

def send_telegram_reply(chat_id, text):
    """Send a reply via Telegram."""
    if "ISI_" in TELEGRAM_TOKEN:
        print(f"[Telegram skip] ChatID:{chat_id} - {text}")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id, 
            "text": text, 
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        print(f"Telegram reply error: {e}")

def handle_status_command(chat_id):
    """Get current trading status."""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        
        # Get recent trades
        recent = conn.execute(
            "SELECT COUNT(*) FROM ohlcv"
        ).fetchone()[0]
        
        # Get total tickers
        tickers_count = conn.execute(
            "SELECT COUNT(DISTINCT ticker) FROM ohlcv"
        ).fetchone()[0]
        
        conn.close()
        
        status_msg = f"📊 *Trading Status*\n\nTickers: {tickers_count}\nData points: {recent}\n✅ System Active"
        send_telegram_reply(chat_id, status_msg)
    except Exception as e:
        send_telegram_reply(chat_id, f"❌ Error getting status: {str(e)}")

def handle_signals_command(chat_id):
    """Get recent signals."""
    try:
        import sqlite3, pandas as pd
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect(DB_PATH)
        
        # Get tickers with recent data
        tickers = [r[0] for r in conn.execute(
            "SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker LIMIT 10"
        ).fetchall()]
        
        conn.close()
        
        signals_msg = f"📈 *Recent Signals*\n\nScanned: {len(tickers)} tickers\n✅ Scanning active..."
        send_telegram_reply(chat_id, signals_msg)
    except Exception as e:
        send_telegram_reply(chat_id, f"❌ Error getting signals: {str(e)}")

def handle_flow_command(chat_id):
    """Get flow confirmation status."""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        
        # Get any flow data available
        flow_count = conn.execute(
            "SELECT COUNT(*) FROM broker_flow"
        ).fetchone()[0]
        
        conn.close()
        
        flow_msg = f"💰 *Flow Status*\n\nBroker flow records: {flow_count}\n✅ Flow tracking active"
        send_telegram_reply(chat_id, flow_msg)
    except Exception as e:
        send_telegram_reply(chat_id, f"❌ Error getting flow: {str(e)}")

@app.route('/telegram/updates', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook updates."""
    try:
        data = request.get_json()
        
        if data and 'message' in data:
            message = data['message']
            handle_telegram_message(message)
        elif data and 'callback_query' in data:
            # Handle button clicks
            callback = data['callback_query']
            chat_id = callback['from']['id']
            send_telegram_reply(chat_id, "Button clicked! Coming soon...")
        
        return jsonify({'ok': True}), 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/telegram/setup', methods=['GET'])
def setup_telegram_webhook():
    """Setup Telegram in polling mode (local development friendly)."""
    try:
        # Switch to polling mode (doesn't require HTTPS)
        remove_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook"
        response = requests.post(remove_url, json={"drop_pending_updates": True}, timeout=10)
        
        result = response.json()
        
        if result.get('ok'):
            global telegram_polling_active
            telegram_polling_active = True
            msg = f"✅ Telegram polling mode activated!\n\nPolling updates at /telegram/start-polling"
            send_telegram(msg)
            return jsonify({
                'success': True,
                'message': 'Telegram polling mode activated',
                'mode': 'polling',
                'instructions': 'Polling is now active and running in background',
                'webhook_url': None
            }), 200
        else:
            error = result.get('description', 'Unknown error')
            return jsonify({
                'success': False,
                'error': error
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Global polling flag
telegram_polling_active = False
telegram_last_update_id = 0


def poll_telegram_updates_once():
    """Fetch and process new Telegram updates once."""
    global telegram_last_update_id
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {
        'offset': telegram_last_update_id + 1,
        'timeout': 2,
        'allowed_updates': ['message', 'callback_query']
    }
    response = requests.get(url, params=params, timeout=10)
    result = response.json()
    
    updates = []
    if result.get('ok'):
        updates = result.get('result', [])
        for update in updates:
            update_id = update.get('update_id')
            if update_id > telegram_last_update_id:
                telegram_last_update_id = update_id
            
            if 'message' in update:
                handle_telegram_message(update['message'])
            elif 'callback_query' in update:
                callback = update['callback_query']
                chat_id = callback['from']['id']
                send_telegram_reply(chat_id, "Button clicked! Coming soon...")
    
    return updates


def telegram_poller_loop():
    """Continuously poll Telegram for new updates when polling is active."""
    while True:
        if telegram_polling_active:
            try:
                updates = poll_telegram_updates_once()
                if updates:
                    print(f"[Telegram poll] {len(updates)} new updates processed")
            except Exception as e:
                print(f"[Telegram poll error] {e}")
        time.sleep(3)


@app.route('/telegram/start-polling', methods=['GET'])
def start_telegram_polling():
    """Start polling for Telegram updates."""
    global telegram_polling_active
    
    telegram_polling_active = True
    
    return jsonify({
        'success': True,
        'message': 'Telegram polling started',
        'status': 'polling',
        'note': 'Polling will run in the background and process updates automatically'
    }), 200

@app.route('/telegram/stop-polling', methods=['GET'])
def stop_telegram_polling():
    """Stop polling for Telegram updates."""
    global telegram_polling_active
    
    telegram_polling_active = False
    
    return jsonify({
        'success': True,
        'message': 'Telegram polling stopped'
    }), 200

@app.route('/telegram/poll-updates', methods=['GET'])
def telegram_poll_updates():
    """Poll for new Telegram updates."""
    global telegram_last_update_id
    
    try:
        if not telegram_polling_active:
            return jsonify({
                'success': True,
                'updates': [],
                'note': 'Polling not active. Call /telegram/start-polling first'
            }), 200
        
        # Get updates
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        params = {
            'offset': telegram_last_update_id + 1,
            'timeout': 2,
            'allowed_updates': ['message', 'callback_query']
        }
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        updates = []
        if result.get('ok'):
            updates = result.get('result', [])
            
            # Process each update
            for update in updates:
                update_id = update.get('update_id')
                if update_id > telegram_last_update_id:
                    telegram_last_update_id = update_id
                
                # Handle message
                if 'message' in update:
                    message = update['message']
                    handle_telegram_message(message)
                
                # Handle callback query
                elif 'callback_query' in update:
                    callback = update['callback_query']
                    chat_id = callback['from']['id']
                    send_telegram_reply(chat_id, "Button clicked! Coming soon...")
        
        return jsonify({
            'success': True,
            'updates_received': len(updates),
            'last_update_id': telegram_last_update_id,
            'updates': updates
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/telegram/status', methods=['GET'])
def telegram_webhook_status():
    """Check Telegram polling status."""
    try:
        get_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getWebhookInfo"
        response = requests.post(get_url, timeout=10)
        info = response.json()
        
        if info.get('ok'):
            webhook_info = info.get('result', {})
            return jsonify({
                'success': True,
                'mode': 'polling',
                'polling_active': telegram_polling_active,
                'last_update_id': telegram_last_update_id,
                'webhook_url': webhook_info.get('url', 'Not set (using polling)'),
                'webhook_active': webhook_info.get('url') != '',
                'pending_update_count': webhook_info.get('pending_update_count', 0),
                'endpoints': {
                    'setup': 'GET /telegram/setup',
                    'start_polling': 'GET /telegram/start-polling',
                    'stop_polling': 'GET /telegram/stop-polling',
                    'poll': 'GET /telegram/poll-updates',
                    'status': 'GET /telegram/status'
                }
            }), 200
        else:
            return jsonify({'success': False, 'error': info.get('description')}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == "__main__":
    init_screener_tables()
    init_flow_db()
    start_scheduler()
    poller_thread = threading.Thread(target=telegram_poller_loop, daemon=True)
    poller_thread.start()
    app.run(host="0.0.0.0", port=5001, debug=False)
