import logging
import sqlite3

import pandas as pd
from flask import Blueprint, jsonify, request

from config import DB_PATH
from flow_filter import get_flow_batch, get_flow_confirmation
from scheduler import (
    scan_momentum_signals,
    send_telegram,
    check_fundamental,
    daily_signal_scan,
)
from engine.strategies import check_current_entry_signal, get_ticker_data

backtest_bp = Blueprint("backtest", __name__)


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


@backtest_bp.route('/api/backtest/scan_all', methods=['POST'])
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
                final_regime = "SIDEWAYS"
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
            logging.exception("scan_all error for %s", ticker)
            results.append({'ticker': ticker, 'error': 'scan error', 'best_return': -999})

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


@backtest_bp.route('/api/backtest/quick_scan', methods=['POST'])
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
                regime = cached.get('regime', 'SIDEWAYS')
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
                    regime = "SIDEWAYS"

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


@backtest_bp.route('/api/backtest/precompute', methods=['POST'])
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
                regime = "SIDEWAYS"

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


@backtest_bp.route('/api/paper/config', methods=['GET'])
def api_paper_config():
    from paper_trade import init_paper_table, get_config
    init_paper_table()
    cfg = get_config()
    return jsonify(cfg)


@backtest_bp.route('/api/paper/config', methods=['POST'])
def api_paper_config_set():
    from paper_trade import init_paper_table, get_db
    init_paper_table()
    body = request.get_json(force=True)
    allowed = {'capital', 'tp_pct', 'sl_pct', 'risk_pct', 'max_open',
               'filter_fundamental', 'filter_sector', 'filter_flow',
               'filter_rs', 'filter_regime', 'filter_vpin'}
    conn = get_db()
    for key, value in body.items():
        if key in allowed:
            conn.execute("INSERT OR REPLACE INTO paper_config (key, value) VALUES (?, ?)",
                         (key, str(value)))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@backtest_bp.route('/api/backtest/multi_quick_scan', methods=['POST'])
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
            regime = "SIDEWAYS"
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
            # Only run expensive backtest if at least one strategy has a signal
            has_any_signal = any(signals.get(s, {}).get('has_signal') for s in strategies)
            best = None
            regime = "SIDEWAYS"
            if has_any_signal:
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

        # Flatten results into single array (frontend expects array, not dict)
        flat_results = []
        for strategy_results in results_by_strategy.values():
            flat_results.extend(strategy_results)

        # Attach flow once on flat list (not per-strategy — avoids 9x redundant fetches)
        include_flow = body.get('include_flow', False)
        flow_threshold = body.get('flow_threshold', 2)
        flat_results = attach_flow_data(flat_results, include_flow, flow_threshold)

        return jsonify({
            'success': True,
            'results': flat_results,
            'summary': {
                'total_tickers_scanned': len(tickers),
                'total_signals': sum(len(r) for r in results_by_strategy.values()),
                'tickers_with_signal': len(set(r['ticker'] for r in flat_results if r.get('has_signal', False))),
                'filter_mode': filter_mode,
                'strategies': strategies,
                'intersection_mode': False,
                'by_strategy': {s: len(results_by_strategy[s]) for s in strategies}
            },
            'multi_strategy': True
        })


@backtest_bp.route("/api/signals/today", methods=["GET"])
def api_signals_today():
    signals = scan_momentum_signals()
    return jsonify({"count": len(signals), "signals": signals})


@backtest_bp.route("/api/signals/scheduled", methods=["GET"])
def api_signals_scheduled():
    """Pre-computed signals written by the scheduler's periodic scans."""
    import datetime, sqlite3
    since = request.args.get("since", datetime.date.today().isoformat())
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT scan_time, ticker, strategies, flow_score, flow_verdict, "
            "smart_money, signal_reasons "
            "FROM scheduled_signals WHERE date(scan_time) >= ? "
            "ORDER BY scan_time DESC, flow_score DESC",
            (since,),
        ).fetchall()
        conn.close()
    except Exception as e:
        return jsonify({"error": str(e), "count": 0, "signals": []})
    signals = [
        {
            "scan_time": r[0],
            "ticker": r[1],
            "strategies": [s.strip() for s in r[2].split(",")],
            "flow_score": r[3],
            "flow_verdict": r[4],
            "smart_money": r[5],
            "signal_reasons": r[6],
        }
        for r in rows
    ]
    return jsonify({"count": len(signals), "signals": signals})

@backtest_bp.route("/api/agent/status", methods=["GET"])
def agent_status():
    from engine.agent_firm import config as _agent_config
    import sqlite3, datetime
    today = datetime.date.today().isoformat()
    stats = {"evaluated": 0, "approved": 0, "vetoed": 0, "cost_usd": 0.0}
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT COUNT(*), "
            "SUM(CASE WHEN decision='approve' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN decision='veto' THEN 1 ELSE 0 END), "
            "COALESCE(SUM(cost_usd), 0.0) "
            "FROM agent_decisions WHERE DATE(created_at) = ?",
            (today,),
        ).fetchone()
        conn.close()
        if row and row[0]:
            stats = {
                "evaluated": row[0] or 0,
                "approved": row[1] or 0,
                "vetoed": row[2] or 0,
                "cost_usd": round(row[3] or 0.0, 4),
            }
    except Exception:
        pass
    return jsonify({
        "enabled": _agent_config.FIRM_ENABLED,
        "enforce": _agent_config.get_enforce(),
        "active": _agent_config.is_active(),
        "model": _agent_config.MODEL_ID,
        "today_stats": stats,
    })

@backtest_bp.route("/api/agent/config", methods=["POST"])
def agent_config():
    from engine.agent_firm import config as _agent_config
    body = request.get_json(force=True) or {}
    mode = body.get("mode", "off")
    if mode == "enforce":
        _agent_config.set_mode(enabled=True, enforce=True)
    elif mode == "shadow":
        _agent_config.set_mode(enabled=True, enforce=False)
    else:
        _agent_config.set_mode(enabled=False, enforce=False)
    return jsonify({
        "enabled": _agent_config.is_active() or mode != "off",
        "enforce": _agent_config.get_enforce(),
        "active": _agent_config.is_active(),
        "mode": mode,
    })

@backtest_bp.route("/api/agent/audit", methods=["GET"])
def agent_audit():
    try:
        from engine.agent_firm.analytics import agent_agreement, cohort_summary, decision_log
        return jsonify({
            "cohorts":   cohort_summary(DB_PATH),
            "agreement": agent_agreement(DB_PATH),
            "log":       decision_log(DB_PATH, limit=100),
        })
    except Exception as e:
        logging.exception("agent audit error")
        return jsonify({
            "error":     "internal error",
            "cohorts":   {"approve": {"n":0,"win_rate":0.0,"avg_return_pct":0.0,"sharpe":0.0},
                          "veto":    {"n":0,"win_rate":0.0,"avg_return_pct":0.0,"sharpe":0.0},
                          "baseline":{"n":0,"win_rate":0.0,"avg_return_pct":0.0,"sharpe":0.0}},
            "agreement": [],
            "log":       [],
        })

@backtest_bp.route("/api/scheduler/run", methods=["POST"])
def api_run_scan():
    signals = daily_signal_scan()
    return jsonify({"count": len(signals), "signals": signals})


@backtest_bp.route('/api/paper/open', methods=['POST'])
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

@backtest_bp.route('/api/paper/close', methods=['POST'])
def api_paper_close():
    from paper_trade import close_trade
    from scheduler import send_telegram
    body = request.get_json(force=True)
    result = close_trade(int(body['trade_id']), float(body['exit_price']), body.get('reason','MANUAL'), notify=False)
    if 'pnl_rp' in result:
        emoji = "🟢" if result['pnl_rp'] >= 0 else "🔴"
        send_telegram(f"{emoji} Paper Trade Closed - {result['ticker']} | {result['exit_reason']} | P&L: Rp {result['pnl_rp']:,} ({result['pnl_pct']:+.2f}%)")
    return jsonify(result)


@backtest_bp.route('/api/paper/clear_history', methods=['POST'])
def api_paper_clear_history():
    from paper_trade import clear_history
    result = clear_history()
    return __import__('flask').jsonify({'status': 'ok', 'deleted': result['deleted']})

@backtest_bp.route('/api/paper/summary', methods=['GET'])
def api_paper_summary():
    from paper_trade import get_summary, init_paper_table
    init_paper_table()
    return jsonify(get_summary())


@backtest_bp.route('/api/paper/report-telegram', methods=['POST'])
def api_paper_report_telegram():
    """Manually trigger open trades report to Telegram."""
    try:
        from scheduler import open_trades_status_report
        open_trades_status_report()
        return jsonify({'success': True, 'message': 'Report sent to Telegram'}), 200
    except Exception as e:
        logging.exception("paper report telegram error")
        return jsonify({'success': False, 'error': 'internal error'}), 500


@backtest_bp.route('/api/signals/custom', methods=['POST'])
def api_signals_custom():
    import sqlite3, pandas as pd, logging
    from engine.indicators import calc_vol_ratio
    from engine.regime_filter import RegimeClassifier, get_macro_overlay, apply_macro_overlay
    import datetime as _dt

    body = request.get_json(force=True)
    tickers_input = [t.strip().upper() for t in body.get('tickers', '').split(',') if t.strip()][:100]
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

            if use_regime and regime_label not in ("BULL", "SIDEWAYS"):
                row["fail_reason"] = f"REGIME: {regime_label} ({round(regime_conf*100)}%)"
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
                regime_emoji = "📈" if r.get("regime") == "BULL" else "🐻" if r.get("regime") == "BEAR" else "➡️" if r.get("regime") == "SIDEWAYS" else "❓"
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


@backtest_bp.route('/api/optimizer/run', methods=['POST'])
def api_optimizer_run():
    """
    POST /api/optimizer/run
    Body: {"ticker": "BRPT", "strategy": "vol_weighted", "capital": 50000000}
    Returns: best_params, oos_metrics, per-window detail.
    """
    body     = request.get_json(force=True)
    ticker   = (body.get('ticker') or '').strip().upper()
    strategy = (body.get('strategy') or '').strip()
    capital  = float(body.get('capital', 50_000_000))

    if not ticker or not strategy:
        return jsonify({'error': 'ticker and strategy required'}), 400

    from engine.optimizer import STRATEGY_RUNNERS, optimize_strategy, save_optimizer_result
    if strategy not in STRATEGY_RUNNERS:
        return jsonify({
            'error': f"Unknown strategy: {strategy!r}. Valid: {list(STRATEGY_RUNNERS)}"
        }), 422

    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(
            "SELECT date, open, high, low, close, volume FROM ohlcv WHERE ticker=? ORDER BY date",
            conn, params=(ticker,),
        )
        conn.close()
        if len(df) < 60:
            return jsonify({'error': f'Insufficient data for {ticker}: {len(df)} bars'}), 400
        for col in ('open', 'high', 'low', 'close', 'volume'):
            df[col] = df[col].astype(float)

        result = optimize_strategy(df, strategy, capital)
        save_optimizer_result(ticker, strategy, result, DB_PATH)
        result['ticker'] = ticker
        for w in result.get('windows', []):
            w['oos_metrics'].pop('exit_reasons', None)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/api/optimizer/result/<ticker>/<strategy>', methods=['GET'])
def api_optimizer_result(ticker, strategy):
    """GET cached optimizer result for (ticker, strategy)."""
    from engine.optimizer import get_optimizer_result
    result = get_optimizer_result(ticker.upper(), strategy, DB_PATH)
    if not result:
        return jsonify({'error': f'No optimizer result for {ticker}/{strategy}'}), 404
    return jsonify(result)


@backtest_bp.route('/api/backtest/roll', methods=['POST'])
def api_backtest_roll():
    """Trigger backtest roller on demand.
    Body: {"tickers": ["BRPT", ...], "include_partial": true}
    tickers is optional — omit to roll all tickers.
    """
    from engine.backtest_roller import roll_all, export_meta_dataset
    body = request.get_json(force=True) or {}
    tickers = body.get('tickers')
    include_partial = bool(body.get('include_partial', True))
    try:
        summary = roll_all(tickers=tickers, include_partial=include_partial)
        n_exported = export_meta_dataset()
        summary['exported'] = n_exported
        return jsonify({'status': 'ok', 'summary': summary})
    except Exception as e:
        logging.exception("api_backtest_roll error")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@backtest_bp.route('/api/paper/premover_mode', methods=['GET'])
def api_premover_mode_get():
    """GET current auto_trade_from_premover mode."""
    from paper_trade import get_premover_mode, init_paper_table
    init_paper_table()
    return jsonify({'mode': get_premover_mode()})


@backtest_bp.route('/api/paper/premover_mode', methods=['POST'])
def api_premover_mode_set():
    """POST {'mode': 'off|shadow|enforce'} to update auto_trade_from_premover."""
    from paper_trade import set_premover_mode, get_premover_mode, init_paper_table
    init_paper_table()
    body = request.get_json(force=True) or {}
    mode = body.get('mode', 'off')
    try:
        set_premover_mode(mode)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'mode': get_premover_mode()})


@backtest_bp.route('/api/scanner/adaptive_strategy/<ticker>', methods=['GET'])
def api_adaptive_strategy(ticker):
    """Return what adaptive_strategy_selector would pick for ticker right now."""
    import pandas as pd
    from scheduler.scanner import (adaptive_strategy_selector,
                                   _REGIME_STRATEGY_MAP, _BULL_STRONG_ADX)
    from engine.regime_filter import detect_regime
    from engine.indicators import calc_adx

    ticker = ticker.upper()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(
            "SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC", conn,
            params=(ticker,)
        )
        conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    if df.empty or len(df) < 20:
        return jsonify({'error': f'Insufficient OHLCV data for {ticker}'}), 404

    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)

    try:
        regime = detect_regime(df)
    except Exception:
        regime = 'SIDEWAYS'

    adx_val = None
    sub_band = regime
    if regime == 'BULL':
        try:
            adx_val = round(float(calc_adx(df, 14).iloc[-1]), 1)
        except Exception:
            adx_val = None
        sub_band = 'BULL_STRONG' if (adx_val or 0) >= _BULL_STRONG_ADX else 'BULL_MODERATE'

    candidates = _REGIME_STRATEGY_MAP.get(sub_band, [])
    selected = adaptive_strategy_selector(ticker, df)
    fallback_used = bool(selected) and not any(s in candidates for s in selected)

    return jsonify({
        'ticker':        ticker,
        'regime':        regime,
        'adx':           adx_val,
        'sub_band':      sub_band,
        'candidates':    candidates,
        'selected':      selected,
        'fallback_used': fallback_used,
    })
