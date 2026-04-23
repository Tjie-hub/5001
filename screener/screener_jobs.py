"""
screener/screener_jobs.py — Screener run functions (intraday + EOD)
Adapted from idx_screener/scheduler.py to use shared walkforward.db.
"""
import logging
import time
from datetime import date as dt_date

import screener.db as db
import screener.idx_scraper as scraper
import screener.calculator as calc
import screener.vpin as vpin_mod
import screener.vpin_multi as vpin_multi

logger = logging.getLogger(__name__)

# Background task state shared with routes
_task_state = {
    'running': False,
    'progress': 0,
    'total': 0,
    'current': '',
    'type': '',
    'result': None,
    'error': None,
}


def get_task_state() -> dict:
    return dict(_task_state)


def run_intraday(trade_date: str = None, on_progress=None) -> dict:
    t0 = time.time()
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    logger.info(f"[screener] INTRADAY RUN {trade_date}")
    ok, err = 0, 0

    ohlcv_all = scraper.fetch_lq45_ohlcv()
    all_trades = scraper.fetch_all_running_trades(trade_date=trade_date)

    total = len(scraper.LQ45)
    _task_state.update({'running': True, 'progress': 0, 'total': total, 'type': 'intraday', 'current': '', 'error': None})

    for i, ticker in enumerate(scraper.LQ45):
        _task_state['current'] = ticker
        _task_state['progress'] = i + 1
        try:
            ticks = all_trades.get(ticker, [])
            ohlcv = ohlcv_all.get(ticker, {})
            avg_vol = db.get_avg_vol_from_db(ticker, trade_date)
            if avg_vol is None:
                avg_vol = calc.get_avg_vol_20d_yfinance(ticker, trade_date)
            result = calc.process_ticker(ticker, ticks, ohlcv, avg_vol, trade_date)
            if ticks:
                db.insert_ticks(ticks)
            db.upsert_daily_screen({
                'date': result['date'], 'ticker': result['ticker'],
                'close': result['close'], 'volume': result['volume'],
                'avg_vol_20d': result['avg_vol_20d'], 'vol_ratio': result['vol_ratio'],
                'vwap': result['vwap'], 'delta': result['delta'],
                'cum_delta': result['cum_delta'], 'signal': result['signal'],
                'consec_up': result['consec_up'],
            })
            ok += 1
        except Exception as e:
            logger.error(f"[screener] Error {ticker}: {e}")
            err += 1

    duration = round(time.time() - t0, 1)
    db.log_run('intraday', ok, err, duration)
    _task_state.update({'running': False, 'result': {'ok': ok, 'err': err, 'duration_s': duration}})
    logger.info(f"[screener] Intraday done: {ok} ok, {err} err, {duration}s")
    return {'ok': ok, 'err': err, 'duration_s': duration, 'type': 'intraday'}


def run_eod(trade_date: str = None, send_telegram=None) -> dict:
    t0 = time.time()
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    logger.info(f"[screener] EOD RUN {trade_date}")

    intraday_result = run_intraday(trade_date)

    ok_br, err_br = 0, 0
    all_broker = scraper.fetch_all_broker_summaries(trade_date=trade_date)
    for ticker, rows in all_broker.items():
        try:
            if rows:
                db.insert_broker_summary(rows)
            ok_br += 1
        except Exception as e:
            logger.error(f"[screener] Broker error {ticker}: {e}")
            err_br += 1

    # VPIN calculation
    logger.info("[screener] Calculating VPIN...")
    vpin_ok = 0
    with db.get_conn() as conn:
        for ticker in scraper.LQ45:
            try:
                r = vpin_mod.calc_vpin(conn, ticker, trade_date)
                if r['vpin'] is not None:
                    conn.execute(
                        "UPDATE daily_screen SET vpin=?, vpin_label=? WHERE date=? AND ticker=?",
                        (r['vpin'], r.get('label', ''), trade_date, ticker)
                    )
                    vpin_ok += 1
            except Exception as e:
                logger.error(f"[screener] VPIN error {ticker}: {e}")
        conn.commit()

        signals = vpin_multi.scan_vpin_signals(conn, scraper.LQ45, trade_date)
        for sig in signals:
            if send_telegram:
                try:
                    msg = vpin_multi.format_vpin_alert(sig)
                    send_telegram(msg)
                except Exception:
                    pass
    logger.info(f"[screener] VPIN: {vpin_ok} done, {len(signals)} signals")

    duration = round(time.time() - t0, 1)
    ok = intraday_result['ok'] + ok_br
    err = intraday_result['err'] + err_br
    db.log_run('eod', ok, err, duration)
    _task_state.update({'running': False, 'result': {'ok': ok, 'err': err, 'duration_s': duration}})
    return {'ok': ok, 'err': err, 'duration_s': duration, 'type': 'eod'}
