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
from data.fetcher import load_all_tickers
from engine.calendar_filter import is_blackout_day

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


def _load_stockbit_token() -> str | None:
    """Load Stockbit JWT from .stockbit_token file."""
    import os
    token_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.stockbit_token')
    try:
        with open(token_file) as f:
            t = f.read().strip()
        return t if t.startswith('eyJ') else None
    except Exception:
        return None


def run_intraday(trade_date: str = None, on_progress=None, send_telegram=None,
                 final: bool = False) -> dict:
    t0 = time.time()
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    logger.info(f"[screener] INTRADAY RUN {trade_date}")
    ok, err = 0, 0

    sb_token = _load_stockbit_token()
    if not sb_token:
        logger.error("[screener] Stockbit token not found — cannot run intraday")
        if send_telegram:
            try:
                send_telegram(
                    f"🔴 <b>Intraday GAGAL</b>\n\n"
                    f"Stockbit token tidak ditemukan ({trade_date}).\n"
                    f"Refresh token: <code>python3 auto_token.py</code>"
                )
            except Exception:
                pass
        return {'ok': 0, 'err': 0, 'duration_s': 0, 'type': 'intraday', 'error': 'no_token'}

    tickers = load_all_tickers()
    total = len(tickers)
    _task_state.update({'running': True, 'progress': 0, 'total': total, 'type': 'intraday', 'current': '', 'error': None})

    def _on_progress(ticker, i, t):
        _task_state['current'] = ticker
        _task_state['progress'] = i

    logger.info(f"[screener] Fetching Stockbit tradebook for {total} tickers...")
    ohlcv_all, all_trades = scraper.fetch_all_stockbit(
        tickers=tickers, token=sb_token, trade_date=trade_date,
        progress_cb=_on_progress,
    )

    filled = sum(1 for v in ohlcv_all.values() if v.get('close'))
    logger.info(f"[screener] OHLCV derived: {filled}/{total} tickers with data")
    if filled == 0 and send_telegram:
        try:
            send_telegram(
                f"🔴 <b>Stockbit Scraper GAGAL</b>\n\n"
                f"Tidak ada data dari Stockbit ({trade_date}).\n"
                f"Token mungkin expired — cek: <code>python3 auto_token.py --check</code>"
            )
        except Exception:
            pass

    scraper.save_ohlcv_to_db(ohlcv_all, trade_date, is_final=final)

    for i, ticker in enumerate(tickers):
        _task_state['current'] = ticker
        _task_state['progress'] = i + 1
        try:
            ticks = all_trades.get(ticker, [])
            ohlcv = ohlcv_all.get(ticker, {})
            avg_vol = db.get_avg_vol_from_db(ticker, trade_date)
            if avg_vol is None:
                avg_vol = scraper.get_avg_vol_20d_from_db(ticker, trade_date)
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


def _eod_calendar_cleanup(min_days: int = 1) -> int:
    """Phase 3A: self-clean the corpus daily — refresh the IHSG-derived trading
    calendar, then drop non-trading-day rows (yfinance holiday-fills). Previously
    only the yfinance incremental path purged, so fills accumulated (4,138 rows
    by 2026-07-04). Fail-soft: never let cleanup break the EOD run. Returns rows
    removed (0 on any error)."""
    try:
        from data.db import get_db
        from data.market_schema import build_trading_calendar
        from data.fetcher import purge_non_calendar_days
        _cal = get_db()
        build_trading_calendar(_cal)
        _cal.close()
        removed = purge_non_calendar_days(min_days=min_days)
        if removed:
            logger.info(f"[screener] EOD calendar purge removed {removed} non-trading-day rows")
        return removed
    except Exception as e:
        logger.warning(f"[screener] EOD calendar purge skipped: {e}")
        return 0


def _coverage_fallback_row(ticker: str, df, trade_date: str):
    """Compute a neutral daily_screen fallback row for `ticker` from its OHLCV
    history.

    Returns `(row_dict, None)` when there's enough history *and* the last
    available bar is actually dated `trade_date`. Otherwise returns
    `(None, skip_reason)` with reason `'insufficient_history'` or `'stale'` —
    a stale last bar must never be reported as trade_date's coverage
    (P0.E2.S1.T1, EOD coverage-fallback date guard).
    """
    if df is None or len(df) < 20:
        return None, 'insufficient_history'
    last = df.iloc[-1]
    if str(last['date']) != trade_date:
        return None, 'stale'
    avg_vol = df['volume'].tail(20).mean()
    vr = last['volume'] / avg_vol if avg_vol > 0 else None
    rng = last['high'] - last['low']
    delta_p = (last['close'] - last['open']) / rng * last['volume'] if rng > 0 else 0
    tp = (last['high'] + last['low'] + last['close']) / 3
    signal = 'neutral'
    if vr is not None and vr > 1.5:
        if delta_p > 0 and last['close'] > tp:
            signal = 'bullish'
        elif delta_p < 0 and last['close'] < tp:
            signal = 'bearish'
        else:
            signal = 'watch'
    row = {
        'close': int(last['close']), 'volume': int(last['volume']),
        'avg_vol_20d': int(avg_vol),
        'vol_ratio': round(float(vr), 2) if vr else None,
        'vwap': round(float(tp), 2), 'delta': int(delta_p), 'signal': signal,
    }
    return row, None


def run_eod(trade_date: str = None, send_telegram=None) -> dict:
    t0 = time.time()
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    logger.info(f"[screener] EOD RUN {trade_date}")

    intraday_result = run_intraday(trade_date, final=True)   # 16:15: bars become FINAL

    # VPIN calculation
    logger.info("[screener] Calculating VPIN...")
    tickers = load_all_tickers()
    vpin_ok = 0
    with db.get_conn() as conn:
        for ticker in tickers:
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

        signals = vpin_multi.scan_vpin_signals(conn, tickers, trade_date)
        
        # Blackout check for VPIN signals (Telegram suppressed — alerts disabled per config)
        _blackout, _bl_reason = is_blackout_day()
        if _blackout:
            logger.warning(f"[screener] VPIN BLACKOUT aktif: {_bl_reason} — VPIN alerts dilewati.")
        else:
            for sig in signals:
                logger.info(f"[screener] VPIN signal (silent): {sig.get('ticker')} {sig.get('signal')}")
    logger.info(f"[screener] VPIN: {vpin_ok} done, {len(signals)} signals")

    # ── Coverage fallback: insert neutral entries for tickers without daily_screen data today
    try:
        existing = set(r[0] for r in conn.execute(
            "SELECT ticker FROM daily_screen WHERE date=?", (trade_date,)
        ).fetchall())
        missing = [t for t in tickers if t not in existing]
        if missing:
            import pandas as _pd
            import numpy as _np
            ohlcv_all = _pd.read_sql(
                'SELECT * FROM ohlcv ORDER BY ticker, date ASC', conn
            )
            for c in ['open', 'high', 'low', 'close', 'volume']:
                ohlcv_all[c] = ohlcv_all[c].astype(float)
            grouped = {t: grp.reset_index(drop=True) for t, grp in ohlcv_all.groupby('ticker')}
            fallback_ok = 0
            stale_skipped = 0
            for ticker in missing:
                try:
                    row, skip_reason = _coverage_fallback_row(ticker, grouped.get(ticker), trade_date)
                    if row is None:
                        if skip_reason == 'stale':
                            stale_skipped += 1
                        continue
                    conn.execute(
                        "INSERT OR IGNORE INTO daily_screen "
                        "(date, ticker, close, volume, avg_vol_20d, vol_ratio, vwap, delta, signal) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (trade_date, ticker, row['close'], row['volume'],
                         row['avg_vol_20d'], row['vol_ratio'], row['vwap'], row['delta'], row['signal'])
                    )
                    fallback_ok += 1
                except Exception:
                    pass
            conn.commit()
            if fallback_ok:
                logger.info(f"[screener] Coverage fallback: {fallback_ok}/{len(missing)} tickers inserted")
            if stale_skipped:
                logger.warning(
                    f"[screener] Coverage fallback: {stale_skipped}/{len(missing)} tickers skipped "
                    f"(last bar predates {trade_date}, not treated as valid coverage)"
                )
    except Exception as _fe:
        logger.error(f"[screener] Coverage fallback error: {_fe}")

    # ── Reversal watchlist pre-scan: flag next-day liquid bounce/fade setups ──
    try:
        from screener.reversal_filter import scan_reversals, persist_watchlist
        with db.get_conn() as rconn:
            rev = scan_reversals(rconn, trade_date)
            persist_watchlist(rconn, trade_date, rev)
        logger.info(f"[screener] Reversal watchlist: {len(rev)} setups for next session")
        if send_telegram and rev:
            try:
                top = rev[:8]
                lines = [f"📋 <b>Reversal Watchlist</b> ({trade_date} EOD)",
                         f"{len(rev)} liquid setups for besok:\n"]
                for r in top:
                    d = "▲" if r["direction"] == "long" else "▼"
                    lines.append(f"{d} <b>{r['ticker']}</b> conv {r['conviction']:.0f} @ {r['close']:,}")
                send_telegram("\n".join(lines))
            except Exception:
                pass
    except Exception as _re:
        logger.error(f"[screener] Reversal scan error: {_re}")

    _eod_calendar_cleanup()

    duration = round(time.time() - t0, 1)
    ok = intraday_result['ok']
    err = intraday_result['err']
    db.log_run('eod', ok, err, duration)
    _task_state.update({'running': False, 'result': {'ok': ok, 'err': err, 'duration_s': duration}})
    return {'ok': ok, 'err': err, 'duration_s': duration, 'type': 'eod'}
