"""EOD finalisation pass verifies the Stockbit token before scraping (2026-09-23).

Incident: 2026-09-21/22 the token was revoked server-side mid-afternoon while its exp claim was
valid; run_intraday(final=True) read the file raw and got HTTP 401 on all 958 tickers. No real
network: token status, refresh, scrape and DB writes are all stubbed.
"""
from unittest.mock import MagicMock

import pytest

import screener.screener_jobs as sj

TICKERS = [f"T{i:02d}" for i in range(10)]
BAR = {'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000}


@pytest.fixture
def env(monkeypatch):
    """Stub everything run_intraday touches. `tokens` is the token file history (refresh appends)."""
    st = {'tokens': ['old'], 'status': {}, 'scrape': None}

    def load():                                       # the file holds the latest token written
        return st['tokens'][-1]

    def status(tok):
        seq = st['status'].get(tok, [200])
        return seq.pop(0) if len(seq) > 1 else seq[0]

    fetch_calls = []

    def fetch(tickers, token, trade_date=None, progress_cb=None, statuses=None, **kw):
        fetch_calls.append((list(tickers), token))
        return st['scrape'](tickers, token, statuses)

    refresh = MagicMock(side_effect=lambda: st['tokens'].append('new') or True)
    save = MagicMock(return_value=0)
    sent = MagicMock()
    monkeypatch.setattr(sj, "_load_stockbit_token", load)
    monkeypatch.setattr(sj, "_token_status", status)
    monkeypatch.setattr(sj, "_refresh_token", refresh)
    monkeypatch.setattr(sj, "VERIFY_BACKOFF_S", (0, 0, 0))
    monkeypatch.setattr(sj, "load_all_tickers", lambda: list(TICKERS))
    monkeypatch.setattr(sj.scraper, "fetch_all_stockbit", fetch)
    monkeypatch.setattr(sj.scraper, "save_ohlcv_to_db", save)
    monkeypatch.setattr(sj.scraper, "get_avg_vol_20d_from_db", lambda *a: None)
    monkeypatch.setattr(sj.db, "get_avg_vol_from_db", lambda *a: None)
    monkeypatch.setattr(sj.db, "insert_ticks", lambda *a: None)
    monkeypatch.setattr(sj.db, "upsert_daily_screen", lambda *a: None)
    monkeypatch.setattr(sj.db, "log_run", lambda *a: None)
    monkeypatch.setattr(sj.calc, "process_ticker", lambda t, *a: {
        'date': '2026-09-23', 'ticker': t, 'close': 1, 'volume': 1, 'avg_vol_20d': None,
        'vol_ratio': None, 'vwap': None, 'delta': 0, 'cum_delta': 0, 'signal': 'neutral',
        'consec_up': 0})
    st.update(fetch_calls=fetch_calls, refresh=refresh, save=save, sent=sent)
    return st


def _scrape_ok_for(good_token):
    def scrape(tickers, token, statuses):
        out = {}
        for t in tickers:
            code = 200 if token == good_token else 401
            if statuses is not None:
                statuses[t] = code
            out[t] = dict(BAR) if code == 200 else {'close': None}
        return out, {t: [] for t in tickers}
    return scrape


def test_revoked_token_is_refreshed_once_and_scrape_uses_new_token(env):
    env['status'] = {'old': [401], 'new': [200]}
    env['scrape'] = _scrape_ok_for('new')
    r = sj.run_intraday('2026-09-23', final=True, send_telegram=env['sent'])
    assert env['refresh'].call_count == 1
    assert [tok for _, tok in env['fetch_calls']] == ['new']
    assert r['filled'] == len(TICKERS) and r['token'].startswith('refreshed')
    assert env['save'].call_args[1]['is_final'] is True


def test_refresh_failure_saves_nothing_and_alerts(env):
    env['status'] = {'old': [401], 'new': [401]}
    env['scrape'] = _scrape_ok_for('new')
    r = sj.run_intraday('2026-09-23', final=True, send_telegram=env['sent'])
    assert r['error'] == 'token_invalid'
    assert env['refresh'].call_count == 1
    assert not env['fetch_calls'] and not env['save'].called
    msg = env['sent'].call_args[0][0]
    assert 'ABORTED' in msg and '2026-09-23' in msg


def test_5xx_on_verify_retries_without_login(env):
    env['status'] = {'old': [503, 503, 502, 200]}
    env['scrape'] = _scrape_ok_for('old')
    r = sj.run_intraday('2026-09-23', final=True, send_telegram=env['sent'])
    assert not env['refresh'].called
    assert r['token'] == 'verified' and r['filled'] == len(TICKERS)


def test_persistent_5xx_scrapes_with_current_token_and_never_logs_in(env):
    env['status'] = {'old': [503]}
    env['scrape'] = _scrape_ok_for('old')
    r = sj.run_intraday('2026-09-23', final=True, send_telegram=env['sent'])
    assert not env['refresh'].called
    assert r['token'].startswith('unverified')


def test_mid_run_401_retries_only_failed_tickers_once(env):
    env['status'] = {'old': [200], 'new': [200]}
    revoked_from = 3                                  # token dies after the 3rd ticker

    def scrape(tickers, token, statuses):
        out = {}
        for i, t in enumerate(tickers):
            code = 200 if token == 'new' or i < revoked_from else 401
            if statuses is not None:
                statuses[t] = code
            out[t] = dict(BAR) if code == 200 else {'close': None}
        return out, {t: [] for t in tickers}
    env['scrape'] = scrape
    r = sj.run_intraday('2026-09-23', final=True, send_telegram=env['sent'])
    assert env['refresh'].call_count == 1
    assert len(env['fetch_calls']) == 2               # full pass + exactly one retry
    assert env['fetch_calls'][1] == (TICKERS[revoked_from:], 'new')
    assert r['retried'] == len(TICKERS) - revoked_from
    assert r['filled'] == len(TICKERS)
    saved = env['save'].call_args[0][0]
    assert all(saved[t].get('close') for t in TICKERS)


def test_mid_run_retry_skipped_when_failures_are_not_auth(env):
    # empty-data day (2026-09-18 pattern): HTTP 200 with no bars -> no re-login
    env['status'] = {'old': [200]}

    def scrape(tickers, token, statuses):
        for t in tickers:
            statuses[t] = 200
        return {t: {'close': None} for t in tickers}, {t: [] for t in tickers}
    env['scrape'] = scrape
    r = sj.run_intraday('2026-09-23', final=True, send_telegram=env['sent'])
    assert not env['refresh'].called and len(env['fetch_calls']) == 1
    assert r['retried'] == 0


def test_provisional_runs_do_not_verify_or_refresh(env, monkeypatch):
    called = MagicMock(return_value=200)
    monkeypatch.setattr(sj, "_token_status", called)
    env['scrape'] = _scrape_ok_for('old')
    sj.run_intraday('2026-09-23', final=False)
    assert not called.called and not env['refresh'].called
    assert env['save'].call_args[1]['is_final'] is False


# ── 17:30 same-day EOD retry (run_eod_retry) ─────────────────────────────────

def _retry_env(env, monkeypatch, final, prov):
    state = {'final': set(final), 'prov': set(prov)}

    def fstate(date, tickers):
        return set(state['final']), set(state['prov'])

    def save(got, date, is_final=False):
        assert is_final is True
        state['final'] |= set(got)
        state['prov'] -= set(got)
        return len(got)
    monkeypatch.setattr(sj, "_final_state", fstate)
    monkeypatch.setattr(sj.scraper, "save_ohlcv_to_db", save)
    return state


def test_retry_on_degraded_day_targets_every_ticker_without_a_final_bar(env, monkeypatch):
    _retry_env(env, monkeypatch, final=TICKERS[:2], prov=TICKERS[2:5])
    env['scrape'] = _scrape_ok_for('old')
    r = sj.run_eod_retry('2026-09-23', env['sent'], today='2026-09-23')
    assert env['fetch_calls'][0][0] == TICKERS[2:]          # provisional AND missing
    assert r['action'] == 'retried' and r['final_after'] == len(TICKERS)
    assert '10/10' in env['sent'].call_args[0][0]


def test_retry_on_healthy_day_only_touches_provisional_leftovers(env, monkeypatch):
    _retry_env(env, monkeypatch, final=TICKERS[:8], prov=['T09'])
    env['scrape'] = _scrape_ok_for('old')
    r = sj.run_eod_retry('2026-09-23', env['sent'], today='2026-09-23')
    assert env['fetch_calls'][0][0] == ['T09']                # T08 (no bar = no trade) left alone
    assert r['retried'] == 1


def test_retry_does_nothing_when_all_final(env, monkeypatch):
    _retry_env(env, monkeypatch, final=TICKERS[:8], prov=[])
    env['scrape'] = _scrape_ok_for('old')
    r = sj.run_eod_retry('2026-09-23', env['sent'], today='2026-09-23')
    assert r['action'] == 'none' and not env['fetch_calls'] and not env['sent'].called


def test_retry_refuses_a_past_date(env, monkeypatch):
    _retry_env(env, monkeypatch, final=[], prov=[])
    r = sj.run_eod_retry('2026-09-22', env['sent'], today='2026-09-23')
    assert r['action'] == 'refused' and not env['fetch_calls']


def test_retry_with_dead_token_saves_nothing_and_alerts(env, monkeypatch):
    state = _retry_env(env, monkeypatch, final=[], prov=[])
    env['status'] = {'old': [401], 'new': [401]}
    env['scrape'] = _scrape_ok_for('new')
    r = sj.run_eod_retry('2026-09-23', env['sent'], today='2026-09-23')
    assert r['action'] == 'token_invalid' and not env['fetch_calls'] and not state['final']
    assert env['refresh'].call_count == 1
    assert 'ABORTED' in env['sent'].call_args[0][0]


def test_retry_job_is_deduped_per_day(tmp_path, monkeypatch):
    import scheduler.jobs as jobs
    calls = MagicMock(return_value={})
    monkeypatch.setattr(jobs, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    monkeypatch.setattr(sj, "run_eod_retry", calls)
    jobs.run_eod_retry_job()
    jobs.run_eod_retry_job()
    assert calls.call_count == 1


def test_retry_job_registered_at_1730():
    import inspect
    import scheduler as sched
    src = inspect.getsource(sched.start_scheduler)
    idx = src.index("run_eod_retry_job, CronTrigger")
    window = src[idx:idx + 200]
    assert "hour=17, minute=30" in window and 'day_of_week="mon-fri"' in window
    assert 'id="eod_retry_1730"' in window
