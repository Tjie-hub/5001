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


# ── EOD token verification (2026-09-23) ──────────────────────────────────────
# 2026-09-21/22: the token was revoked server-side mid-afternoon while its exp claim was still
# valid; run_intraday() read the file raw and the 16:15 finalisation got HTTP 401 on all 958
# tickers. The FINAL pass now verifies the token live before scraping. Only 401/403 justifies a
# re-login: an unnecessary login may itself be what revokes the account's other sessions, so a
# 5xx/timeout is retried with backoff instead.
_AUTH_FAIL = (401, 403)
VERIFY_BACKOFF_S = (5, 15, 45)


def _token_status(token: str):
    from stockbit_fetcher import token_status
    return token_status(token)


def _refresh_token() -> bool:
    from stockbit_fetcher import refresh_token_subprocess
    return refresh_token_subprocess()


def _verify_with_backoff(token: str, sleep=time.sleep):
    """Live status of `token`; transient failures (5xx/429/network) are retried with backoff."""
    status = _token_status(token)
    for wait in VERIFY_BACKOFF_S:
        if status == 200 or status in _AUTH_FAIL:
            break
        logger.warning(f"[screener] token verify inconclusive ({status}) — retry in {wait}s")
        sleep(wait)
        status = _token_status(token)
    return status


def _refresh_and_reverify(reason: str) -> str | None:
    """Re-login once (auto_token subprocess), re-read the token file, verify. Token or None."""
    logger.warning(f"[screener] {reason} — refreshing Stockbit token")
    _refresh_token()
    token = _load_stockbit_token()
    if token and _verify_with_backoff(token) == 200:
        logger.info("[screener] token refreshed and verified")
        return token
    return None


def _eod_verified_token() -> tuple[str | None, str]:
    """Token for the FINAL pass, plus a note. None means no usable token (do not scrape)."""
    token = _load_stockbit_token()
    status = _verify_with_backoff(token) if token else 401
    if status == 200:
        return token, 'verified'
    if status not in _AUTH_FAIL:
        # still inconclusive after backoff: says nothing about the token, so no login; the
        # scrape itself (and the mid-run 401 retry) is the next check
        logger.warning(f"[screener] token verify inconclusive ({status}) — scraping without re-login")
        return token, f'unverified ({status})'
    what = 'missing' if not token else f'HTTP {status}'
    new = _refresh_and_reverify(f"EOD token {what}")
    return (new, f'refreshed after {what}') if new else (None, f'dead ({what}, refresh failed)')


def _send(send_telegram, msg: str) -> None:
    if send_telegram:
        try:
            send_telegram(msg)
        except Exception as e:
            logger.warning(f"[screener] telegram send failed: {e}")


def run_intraday(trade_date: str = None, on_progress=None, send_telegram=None,
                 final: bool = False) -> dict:
    t0 = time.time()
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    logger.info(f"[screener] INTRADAY RUN {trade_date}")
    ok, err = 0, 0

    token_note = None
    if final:
        sb_token, token_note = _eod_verified_token()
        if not sb_token:
            logger.error(f"[screener] EOD finalisation aborted: Stockbit token {token_note}")
            _send(send_telegram,
                  f"🔴 <b>EOD finalisation ABORTED</b> ({trade_date})\n\n"
                  f"Stockbit token {token_note}. Nothing was saved; bars for {trade_date} "
                  f"stay provisional.\n"
                  f"Fix: <code>python3 auto_token.py --login</code> — the 17:30 EOD retry "
                  f"will then finalise the session.")
            return {'ok': 0, 'err': 0, 'duration_s': round(time.time() - t0, 1),
                    'type': 'intraday', 'error': 'token_invalid', 'filled': 0, 'total': 0}
    else:
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
        return {'ok': 0, 'err': 0, 'duration_s': 0, 'type': 'intraday', 'error': 'no_token',
                'filled': 0, 'total': 0}

    tickers = load_all_tickers()
    total = len(tickers)
    _task_state.update({'running': True, 'progress': 0, 'total': total, 'type': 'intraday', 'current': '', 'error': None})

    def _on_progress(ticker, i, t):
        _task_state['current'] = ticker
        _task_state['progress'] = i

    logger.info(f"[screener] Fetching Stockbit tradebook for {total} tickers...")
    statuses = {}
    ohlcv_all, all_trades = scraper.fetch_all_stockbit(
        tickers=tickers, token=sb_token, trade_date=trade_date,
        progress_cb=_on_progress, statuses=statuses,
    )

    filled = sum(1 for v in ohlcv_all.values() if v.get('close'))
    logger.info(f"[screener] OHLCV derived: {filled}/{total} tickers with data")

    # Mid-run revocation (FINAL pass only): a degraded scrape whose failures are mostly
    # 401/403 gets exactly one refresh and a re-fetch of the auth-failed tickers only.
    retried = 0
    if final and total and filled / total < EOD_MIN_FILL_FRAC:
        auth_failed = [t for t in tickers if statuses.get(t) in _AUTH_FAIL]
        if auth_failed and 2 * len(auth_failed) >= total - filled:
            new_token = _refresh_and_reverify(
                f"EOD scrape degraded ({filled}/{total}), {len(auth_failed)} tickers got 401/403")
            if new_token:
                o2, t2 = scraper.fetch_all_stockbit(
                    tickers=auth_failed, token=new_token, trade_date=trade_date)
                for t in auth_failed:
                    if o2.get(t, {}).get('close'):
                        ohlcv_all[t] = o2[t]
                        all_trades[t] = t2.get(t, [])
                retried = len(auth_failed)
                filled = sum(1 for v in ohlcv_all.values() if v.get('close'))
                token_note = 'refreshed mid-run'
                logger.info(f"[screener] EOD retry of {retried} tickers: now {filled}/{total}")
            else:
                logger.error("[screener] EOD mid-run token refresh failed — no retry")

    if filled == 0 and send_telegram and not final:   # FINAL pass: run_eod's degraded alert
        try:
            send_telegram(
                f"🔴 <b>Stockbit Scraper GAGAL</b>\n\n"
                f"Tidak ada data dari Stockbit ({trade_date}).\n"
                f"Token mungkin expired — cek: <code>python3 auto_token.py --check</code>"
            )
        except Exception:
            pass

    # Refuse to finalise a partial run (2026-09-28): a FINAL pass under the fill gate saves every
    # bar PROVISIONAL, so research never reads a mostly-empty session as settled history. The
    # degraded alert (run_eod) and the 17:30 retry (run_eod_retry) own the session from there.
    saved_final = bool(final and total and filled / total >= EOD_MIN_FILL_FRAC)
    if final and not saved_final:
        logger.error(f"[screener] EOD finalisation REFUSED: {filled}/{total} tickers with data — "
                     f"bars stay provisional (gate {EOD_MIN_FILL_FRAC:.0%})")
    scraper.save_ohlcv_to_db(ohlcv_all, trade_date, is_final=saved_final)

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
    return {'ok': ok, 'err': err, 'duration_s': duration, 'type': 'intraday',
            'filled': filled, 'total': total, 'retried': retried, 'token': token_note,
            'saved_final': saved_final}


# A healthy 16:15 run gets bars for ~775 of 958 tickers (~81%; the rest did not trade).
# Every stranded session on record sat at 0-3% (2026-09-07 0/958, 09-18 14/958, 09-21 and
# 09-22 HTTP 401 on all 958), so half the universe separates the two with a wide margin.
EOD_MIN_FILL_FRAC = 0.5


def _alert_if_eod_degraded(intraday_result: dict, trade_date: str, send_telegram=None) -> bool:
    """Telegram-alert when the EOD finalisation pass got data for too few tickers.

    Why (2026-09-23): run_eod() called run_intraday() without a sender, so a 16:15 run that
    finalised nothing was silent; the first warning was the 09:00 provisional-bars check the
    next morning. Returns True when degraded. Fail-soft: never raises into run_eod()."""
    filled = int(intraday_result.get('filled') or 0)
    total = int(intraday_result.get('total') or 0)
    if total and filled / total >= EOD_MIN_FILL_FRAC:
        return False
    logger.error(f"[screener] EOD finalisation DEGRADED: {filled}/{total} tickers with data ({trade_date})")
    if send_telegram:
        try:
            send_telegram(
                f"🔴 <b>EOD finalisation DEGRADED</b> ({trade_date})\n\n"
                f"Stockbit returned data for only <b>{filled}/{total}</b> tickers "
                f"(normal ~775). The finalisation was REFUSED: bars for {trade_date} stay "
                f"provisional and research reads will not see them. The 17:30 EOD retry "
                f"re-attempts automatically.\n"
                f"Likely: token revoked (HTTP 401) or empty upstream responses — see app.log.\n"
                f"Fix the token (<code>python3 auto_token.py --login</code>), then "
                f"<code>python3 scripts/repair_provisional_bars.py --apply</code>"
            )
        except Exception as e:
            logger.warning(f"[screener] EOD degraded alert send failed: {e}")
    return True


def _final_state(trade_date: str, tickers: list) -> tuple[set, set]:
    """(tickers with a FINAL bar, tickers with only a PROVISIONAL bar) on trade_date."""
    conn = db.get_conn()
    try:
        rows = conn.execute("SELECT ticker, is_final FROM ohlcv WHERE date=?",
                            (trade_date,)).fetchall()
    finally:
        conn.close()
    universe = set(tickers)
    final = {r[0] for r in rows if r[1] == 1 and r[0] in universe}
    prov = {r[0] for r in rows if r[1] != 1 and r[0] in universe} - final
    return final, prov


def run_eod_retry(trade_date: str = None, send_telegram=None, today: str = None) -> dict:
    """17:30 WIB: re-run the FINAL scrape for today's tickers the 16:15 pass did not finalise.

    Why (2026-09-23): a failed 16:15 pass (token revoked 09-21/22, empty upstream 09-18) left
    each session provisional until a manual repair the next day. This retries the same day,
    from the same source (Stockbit tradebook).
      degraded (final < EOD_MIN_FILL_FRAC of the universe) -> every ticker without a final bar
      otherwise                                            -> only leftover provisional bars
    Tickers that did not trade stay absent: no bar is ever fabricated. Idempotent (a final bar
    is replaced by the same final bar); the scheduler wrapper dedups it per day.
    The tradebook endpoint has no date parameter — it always serves the current session — so
    this refuses any date but today."""
    today = today or dt_date.today().isoformat()
    trade_date = trade_date or today
    if trade_date != today:
        logger.error(f"[screener] EOD retry refused: {trade_date} is not today ({today}); "
                     f"the tradebook only serves the current session")
        return {'action': 'refused', 'reason': 'not_today', 'retried': 0, 'finalised': 0}

    tickers = load_all_tickers()
    total = len(tickers)
    final, prov = _final_state(trade_date, tickers)
    degraded = bool(total) and len(final) / total < EOD_MIN_FILL_FRAC
    targets = [t for t in tickers if t not in final] if degraded else sorted(prov)
    base = {'final_before': len(final), 'provisional_before': len(prov), 'total': total,
            'degraded': degraded}
    if not targets:
        logger.info(f"[screener] EOD retry: nothing to do ({len(final)}/{total} final)")
        return {**base, 'action': 'none', 'retried': 0, 'finalised': 0}

    sb_token, note = _eod_verified_token()
    if not sb_token:
        logger.error(f"[screener] EOD retry aborted: Stockbit token {note}")
        _send(send_telegram,
              f"🔴 <b>EOD retry ABORTED</b> ({trade_date})\n\n"
              f"{len(final)}/{total} final, {len(targets)} to retry, but the Stockbit token is "
              f"{note}. Nothing saved.\nFix: <code>python3 auto_token.py --login</code>")
        return {**base, 'action': 'token_invalid', 'retried': 0, 'finalised': 0}

    logger.info(f"[screener] EOD retry: {len(targets)} tickers ({'degraded' if degraded else 'provisional'})")
    ohlcv, _ = scraper.fetch_all_stockbit(tickers=targets, token=sb_token, trade_date=trade_date)
    got = {t: v for t, v in ohlcv.items() if v.get('close')}
    saved = scraper.save_ohlcv_to_db(got, trade_date, is_final=True) if got else 0
    final_after, prov_after = _final_state(trade_date, tickers)
    logger.info(f"[screener] EOD retry done: {saved} finalised; now {len(final_after)}/{total} final")
    _send(send_telegram,
          f"{'🟢' if len(final_after) / max(total, 1) >= EOD_MIN_FILL_FRAC else '🔴'} "
          f"<b>EOD retry</b> ({trade_date})\n\n"
          f"Retried {len(targets)} tickers ({'degraded day' if degraded else 'provisional leftovers'}), "
          f"token {note}.\nFinal bars: {len(final)} → <b>{len(final_after)}/{total}</b>; "
          f"provisional left: {len(prov_after)}.")
    return {**base, 'action': 'retried', 'retried': len(targets), 'finalised': saved,
            'final_after': len(final_after), 'provisional_after': len(prov_after), 'token': note}


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


def run_eod(trade_date: str = None, send_telegram=None) -> dict:
    t0 = time.time()
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    logger.info(f"[screener] EOD RUN {trade_date}")

    intraday_result = run_intraday(trade_date, final=True,   # 16:15: bars become FINAL
                                   send_telegram=send_telegram)
    if intraday_result.get('error') != 'token_invalid':      # that path already alerted
        _alert_if_eod_degraded(intraday_result, trade_date, send_telegram)

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
            for ticker in missing:
                try:
                    df = grouped.get(ticker)
                    if df is None or len(df) < 20:
                        continue
                    last = df.iloc[-1]
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
                    conn.execute(
                        "INSERT OR IGNORE INTO daily_screen "
                        "(date, ticker, close, volume, avg_vol_20d, vol_ratio, vwap, delta, signal) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (trade_date, ticker, int(last['close']), int(last['volume']),
                         int(avg_vol), round(float(vr), 2) if vr else None,
                         round(float(tp), 2), int(delta_p), signal)
                    )
                    fallback_ok += 1
                except Exception:
                    pass
            conn.commit()
            if fallback_ok:
                logger.info(f"[screener] Coverage fallback: {fallback_ok}/{len(missing)} tickers inserted")
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
                send_telegram("\n".join(lines), category="reversal_watchlist")
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
