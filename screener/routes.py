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
import screener.brpt_filter as brpt_filter
from data.fetcher import load_all_tickers

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
    tickers = load_all_tickers()
    with db.get_conn() as conn:
        results = vpin_multi.scan_vpin_signals(conn, tickers, date)
    for r in results:
        r.pop('days_data', None)
    return jsonify({'date': date, 'signals': results, 'count': len(results)})


@screener_bp.route('/lq45')
def api_lq45():
    tickers = load_all_tickers()
    return jsonify({'tickers': tickers, 'count': len(tickers)})


@screener_bp.route('/run_log')
def api_run_log():
    limit = int(request.args.get('limit', 10))
    return jsonify({'run_log': db.get_run_log(limit)})


# ── Fundamental Screener ─────────────────────────────────────────────────────

@screener_bp.route('/columns')
def api_screener_columns():
    """List all available fundamental screener columns."""
    columns = {
        "ticker":        {"label": "Ticker", "type": "text"},
        "pe_ttm":        {"label": "PE (TTM)", "type": "float"},
        "pe_ann":        {"label": "PE (Annual)", "type": "float"},
        "pe_forward":    {"label": "PE (Forward)", "type": "float"},
        "pbv":           {"label": "PBV", "type": "float"},
        "ps_ttm":        {"label": "P/S (TTM)", "type": "float"},
        "eps_ttm":       {"label": "EPS (TTM)", "type": "float"},
        "bvps":          {"label": "BVPS", "type": "float"},
        "earnings_yield":{"label": "Earnings Yield", "type": "float"},
        "pcf_ttm":       {"label": "P/CF (TTM)", "type": "float"},
        "pfcf_ttm":      {"label": "P/FCF (TTM)", "type": "float"},
        "ev_ebit":       {"label": "EV/EBIT", "type": "float"},
        "ev_ebitda":     {"label": "EV/EBITDA", "type": "float"},
        "peg_ratio":     {"label": "PEG Ratio", "type": "float"},
        "fcf_per_share": {"label": "FCF/Share", "type": "float"},
        "cash_per_share":{"label": "Cash/Share", "type": "float"},
        "revenue_per_share":{"label": "Revenue/Share", "type": "float"},
        "current_ratio": {"label": "Current Ratio", "type": "float"},
        "quick_ratio":   {"label": "Quick Ratio", "type": "float"},
        "roe":           {"label": "ROE (%)", "type": "float"},
        "roa":           {"label": "ROA (%)", "type": "float"},
        "der":           {"label": "D/E Ratio", "type": "float"},
        "npm":           {"label": "Net Margin (%)", "type": "float"},
        "div_yield":     {"label": "Div Yield (%)", "type": "float"},
        "rev_growth":    {"label": "Rev Growth (%)", "type": "float"},
        "earn_growth":   {"label": "Earn Growth (%)", "type": "float"},
        "flow_score":    {"label": "Flow Score", "type": "int"},
        "flow_verdict":  {"label": "Flow Verdict", "type": "text"},
        "smart_money":   {"label": "Smart Money", "type": "text"},
        "net_lot":       {"label": "Net Lots", "type": "int"},
        "net_value":     {"label": "Net Value", "type": "int"},
        "last_price":    {"label": "Last Price", "type": "int"},
        "buy_lot":       {"label": "Buy Lots", "type": "int"},
        "sell_lot":      {"label": "Sell Lots", "type": "int"},
        "in_idx30":      {"label": "IDX30", "type": "int"},
        "in_lq45":       {"label": "LQ45", "type": "int"},
        "in_idx80":      {"label": "IDX80", "type": "int"},
    }
    return jsonify(columns)


@screener_bp.route('/presets')
def api_screener_presets():
    """List preset screener configurations."""
    return jsonify({
        "graham_value": {
            "columns": "ticker,pe_ttm,pbv,roe,der,div_yield,current_ratio",
            "filters": "pe_ttm<15;pbv<1.5;der<1;current_ratio>2",
            "sort": "pe_ttm", "sort_dir": "ASC",
            "label": "Graham Deep Value"
        },
        "garp": {
            "columns": "ticker,pe_ttm,peg_ratio,roe,rev_growth,earn_growth,flow_score",
            "filters": "peg_ratio<1;roe>15;rev_growth>10",
            "sort": "peg_ratio", "sort_dir": "ASC",
            "label": "GARP — Growth at Reasonable"
        },
        "dividend": {
            "columns": "ticker,div_yield,pe_ttm,pbv,roe,der,current_ratio",
            "filters": "div_yield>4;roe>8;der<2",
            "sort": "div_yield", "sort_dir": "DESC",
            "label": "High Dividend Yield"
        },
        "flow_momentum": {
            "columns": "ticker,flow_score,flow_verdict,smart_money,net_lot,last_price",
            "filters": "flow_score>=3",
            "sort": "flow_score", "sort_dir": "DESC",
            "label": "Strong Flow Momentum"
        },
        "quality": {
            "columns": "ticker,roe,roa,npm,der,earn_growth,pe_ttm,pbv",
            "filters": "roe>20;npm>10;der<1.5",
            "sort": "roe", "sort_dir": "DESC",
            "label": "Quality Compounders"
        },
        "value": {
            "columns": "ticker,pe_ttm,pbv,div_yield,roe,der,current_ratio",
            "filters": "pe_ttm<10;pbv<1.5;div_yield>3",
            "sort": "pe_ttm", "sort_dir": "ASC",
            "label": "Deep Value"
        },
    })


@screener_bp.route('/fundamental')
def api_fundamental():
    """Run a fundamental screener query."""
    from screener.fundamental import run_query as f_query

    columns_str = request.args.get('columns', 'ticker,pe_ttm,pbv,roe')
    columns = [c.strip() for c in columns_str.split(',') if c.strip()]

    # Optional Stockbit template pre-filter
    ticker_filter = None
    sb_template = request.args.get('stockbit_template', type=int)
    if sb_template:
        try:
            from screener.stockbit_screener import fetch_template_tickers
            ticker_filter = fetch_template_tickers(sb_template)
        except Exception as e:
            logger.warning(f"[stockbit_template] Failed to fetch tickers: {e}")

    result = f_query(
        columns=columns,
        universe=request.args.get('universe', 'ALL'),
        filters=request.args.get('filters', ''),
        sort=request.args.get('sort', 'ticker'),
        sort_dir=request.args.get('sort_dir', 'ASC'),
        page=request.args.get('page', 1, type=int),
        perpage=request.args.get('perpage', 20, type=int),
        ticker_filter=ticker_filter,
    )
    if ticker_filter is not None:
        result['stockbit_template'] = sb_template
        result['stockbit_ticker_count'] = len(ticker_filter)
    return jsonify(result)


# ── Stockbit screener integration ─────────────────────────────────────────────

@screener_bp.route('/stockbit/templates')
def api_stockbit_templates():
    """List user's saved Stockbit screener templates."""
    try:
        from screener.stockbit_screener import fetch_favorites, GURU_TEMPLATES
        favs = fetch_favorites()
        return jsonify({
            'saved': favs,
            'builtin': [
                {'id': tid, 'type': ttype, 'name': name}
                for name, (tid, ttype) in GURU_TEMPLATES.items()
            ],
        })
    except Exception as e:
        logger.error(f"[stockbit/templates] {e}")
        return jsonify({'error': str(e)}), 500


@screener_bp.route('/stockbit/run')
def api_stockbit_run():
    """Run a Stockbit screener template and merge with local keystats."""
    template_id = request.args.get('template_id', 63, type=int)
    template_type = request.args.get('template_type', 'TEMPLATE_TYPE_GURU')
    try:
        from screener.stockbit_screener import run_screener
        result = run_screener(template_id, template_type)
        return jsonify(result)
    except Exception as e:
        logger.error(f"[stockbit/run] {e}")
        return jsonify({'error': str(e)}), 500


# ── BRPT Comparable Filter ────────────────────────────────────────────────────

@screener_bp.route('/brpt_filter')
def api_brpt_filter():
    """
    GET /screener/brpt_filter?top=20&date=2026-05-26
    
    Returns stocks comparable to BRPT (Barito Pacific) based on:
    - Big liquidity (high avg_vol_20d)
    - Tradeability (good fundamentals, index membership)
    - Profile similarity to BRPT (PE, PBV, ROE, price range)
    """
    top_n = request.args.get('top', 20, type=int)
    trade_date = request.args.get('date', None)
    
    try:
        results = brpt_filter.run_filter(screen_date=trade_date, top_n=top_n)
        return jsonify({
            'generated': dt_date.today().isoformat(),
            'reference_ticker': 'BRPT',
            'reference_profile': brpt_filter.BRPT_PROFILE,
            'count': len(results),
            'results': results,
        })
    except Exception as e:
        logger.error(f"[brpt_filter] Error: {e}")
        return jsonify({'error': str(e)}), 500
