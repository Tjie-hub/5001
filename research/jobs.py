"""Research batch jobs (spec §10-M3) — moved verbatim from scheduler/jobs.py.

These produce research artifacts (wf_scores, wf_edge, backtest_cache) and run
via research/cli.py (cron or manual) — NEVER from the production scheduler.
Bodies unchanged from the pre-move versions; only module plumbing differs.
"""
import os
import sqlite3
import logging
from datetime import datetime

import pytz

from data.db import connect as db_connect
from data.loaders import _load_ohlcv_bulk
from utils.telegram import send_telegram

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "walkforward.db"))


_WF_LOCK_JOB = "refresh_wf_scores"


def _pid_alive(pid) -> bool:
    """True if `pid` is a running process. Signal 0 = liveness probe, no-op."""
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _wf_lock_acquire(db_path: str, job: str = _WF_LOCK_JOB) -> bool:
    """Take a pid-aware advisory lock so two heavy refreshes can't run at once.
    A lock held by a dead pid is treated as stale and overwritten (self-healing)."""
    with db_connect(db_path) as g:
        g.execute("CREATE TABLE IF NOT EXISTS _job_lock "
                  "(job TEXT PRIMARY KEY, pid INTEGER, started_at TEXT)")
        row = g.execute("SELECT pid FROM _job_lock WHERE job=?", (job,)).fetchone()
        if row and _pid_alive(row[0]):
            return False
        g.execute("INSERT OR REPLACE INTO _job_lock VALUES (?,?,?)",
                  (job, os.getpid(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    return True


def _wf_lock_release(db_path: str, job: str = _WF_LOCK_JOB) -> None:
    try:
        with db_connect(db_path) as g:
            g.execute("DELETE FROM _job_lock WHERE job=? AND pid=?", (job, os.getpid()))
    except Exception as e:
        print(f"[WF] lock release error: {e}")


def refresh_wf_scores():
    """Run walk-forward semua ticker & simpan ke wf_scores table.

    Lock-safe (DB-lock incident 2026-06-25): the long walk-forward compute runs
    with NO db transaction open; all results are written in one short transaction
    at the end (lock held ~seconds, not the ~35 min that used to block EOD scans).
    A pid-aware _job_lock guard prevents concurrent refreshes from stacking.
    """
    from research.walkforward_multi import run_walk_forward
    from research.tracking import track_run, ensure_column
    from engine.wf_edge import aggregate_wf_windows, save_wf_edge, ensure_wf_edge_table
    from datetime import datetime as dt

    if not _wf_lock_acquire(DB_PATH):
        print("[WF] refresh_wf_scores: another run is in progress — skipped")
        return
    try:
      with track_run("wf-refresh", params={"final_only": True, "adjusted": True}) as run:
        # Survivorship (item 2.4): score EVERY ticker in the corpus, not just
        # currently-active idx_tickers — a name that later delists must keep
        # its real (often losing) history in wf_scores. _refresh_backtest_cache
        # already iterates the corpus; this aligns the WF refresh.
        ohlcv_map = _load_ohlcv_bulk(final_only=True)  # research: no partial bars (plan 2A)
        tickers = sorted(ohlcv_map.keys())
        now_str = dt.now().strftime("%Y-%m-%d %H:%M")

        # ---- COMPUTE PHASE: no DB write lock held (this is the ~35-min CPU work) ----
        score_rows = []        # tuples ready for wf_scores
        edge_payloads = []     # (ticker, aggregated_rows) for wf_edge
        updated = 0
        for ticker in tickers:
            try:
                df = ohlcv_map.get(ticker)
                if df is None or len(df) < 60:
                    continue
                result = run_walk_forward(df)
                if "error" in result:
                    continue
                ranked = result.get("ranked", [])
                for metrics in ranked:
                    strategy = metrics.get("strategy", "")
                    if not strategy:
                        continue
                    score_rows.append(
                        (ticker, strategy,
                         metrics.get("consistency_pct", 0),
                         float(metrics.get("avg_return_pct", 0)),
                         float(metrics.get("avg_sharpe", 0)),
                         float(metrics.get("score", 0)),
                         metrics.get("windows_tested", 0),
                         now_str))
                edge_payloads.append((ticker, aggregate_wf_windows(ranked)))
                updated += 1
            except Exception as e:
                print(f"[WF] {ticker} error: {e}")

        # ---- WRITE PHASE: one short transaction (lock held ~seconds) ----
        conn = db_connect(DB_PATH)
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS wf_scores ("
                "ticker TEXT NOT NULL, strategy TEXT NOT NULL, consistency_pct REAL, "
                "avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL, "
                "windows_tested INTEGER, updated_at TEXT, run_id TEXT, "
                "PRIMARY KEY(ticker,strategy))")
            ensure_wf_edge_table(conn)
            # run_id provenance (audit R-4): nullable columns, added
            # idempotently so pre-existing tables keep working.
            ensure_column(conn, "wf_scores", "run_id")
            ensure_column(conn, "wf_edge", "run_id")
            conn.executemany(
                "INSERT OR REPLACE INTO wf_scores "
                "(ticker,strategy,consistency_pct,avg_return_pct,avg_sharpe,weighted_score,windows_tested,updated_at,run_id) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                [row + (run.run_id,) for row in score_rows])
            for ticker, agg in edge_payloads:
                save_wf_edge(conn, ticker, agg, now_str)
            conn.execute("UPDATE wf_edge SET run_id=? WHERE last_computed=?",
                         (run.run_id, now_str))
            conn.commit()
            edge_count = conn.execute(
                "SELECT COUNT(*) FROM wf_edge WHERE last_computed=?", (now_str,)
            ).fetchone()[0]
            run.metrics.update({"tickers_total": len(tickers),
                                "score_rows": len(score_rows),
                                "wf_edge_rows": edge_count,
                                "updated_at_stamp": now_str})
            print(f"[WF] wf_edge updated: {edge_count} rows")

            # Strategy health re-validation: alert when a live-selectable strategy's
            # cross-ticker average walk-forward return is negative. This is how the
            # Jan-2026 regime break should have been caught in days, not months.
            try:
                # Inline paper_config read (M3): research must not import the
                # scanner. Data-level read of production config is the allowed
                # direction; prod always has the key (set by Phase 2C).
                try:
                    _raw = conn.execute(
                        "SELECT value FROM paper_config WHERE key='disabled_strategies'"
                    ).fetchone()
                    disabled = {s.strip() for s in str(_raw[0]).split(',')
                                if s.strip()} if _raw else set()
                except Exception:
                    disabled = set()
                rows = conn.execute(
                    "SELECT strategy, ROUND(AVG(avg_return_pct),2), COUNT(*) "
                    "FROM wf_scores GROUP BY strategy"
                ).fetchall()
                losing = [(s, r) for s, r, n in rows
                          if s not in disabled and r is not None and r < 0 and n >= 50]
                if losing:
                    msg = "⚠️ <b>WF Re-validation: strategi live dengan avg return negatif</b>\n\n"
                    for s, r in sorted(losing, key=lambda x: x[1]):
                        msg += f"  {s}: {r:+.2f}%/window\n"
                    msg += "\nPertimbangkan menambahkan ke disabled_strategies (paper_config)."
                    send_telegram(msg)
                    print(f"[WF] Re-validation alert: {len(losing)} losing live strategies")
            except Exception as _rv_err:
                print(f"[WF] Re-validation check error: {_rv_err}")
        finally:
            conn.close()
        run.metrics["tickers_updated"] = updated
        print(f"[WF] refresh_wf_scores selesai: {updated}/{len(tickers)} ticker diupdate")
    finally:
        _wf_lock_release(DB_PATH)


def _refresh_backtest_cache():
    try:
        from research.walkforward_multi import run_all_strategies
        from research.tracking import track_run, ensure_column
        from engine.regime_filter import detect_regime
        from datetime import date
        today = date.today().isoformat()
        with track_run("backtest-cache", params={"final_only": True, "adjusted": True}) as run:
            conn = db_connect(DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_cache (
                    ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
                    best_strategy TEXT, best_return REAL, win_rate REAL,
                    sharpe REAL, total_trades INTEGER, profitable INTEGER,
                    regime TEXT, updated_at TEXT, run_id TEXT,
                    PRIMARY KEY (ticker, computed_date)
                )""")
            ensure_column(conn, "backtest_cache", "run_id")   # audit R-4 provenance
            ohlcv_map = _load_ohlcv_bulk(final_only=True)  # research: no partial bars (plan 2A)
            computed = 0
            rows_to_insert = []
            for ticker, df in ohlcv_map.items():
                try:
                    if len(df) < 60:
                        continue
                    strat_results = run_all_strategies(df, capital=50_000_000)
                    best = max(strat_results, key=lambda x: x['total_return_pct'])
                    try:
                        regime = detect_regime(df)
                    except Exception:
                        regime = "UNCERTAIN"
                    rows_to_insert.append((
                        ticker, today, best['strategy'], best['total_return_pct'],
                        best['win_rate'], best.get('sharpe', 0), best.get('total_trades', 0),
                        int(best['total_return_pct'] > 0), regime, run.run_id,
                    ))
                    computed += 1
                except Exception:
                    pass
            conn.executemany("""
                INSERT OR REPLACE INTO backtest_cache
                (ticker, computed_date, best_strategy, best_return, win_rate, sharpe,
                 total_trades, profitable, regime, run_id, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))
            """, rows_to_insert)
            conn.commit()
            conn.close()
            run.metrics["tickers_computed"] = computed
            print(f"[scheduler] Backtest cache refreshed: {computed} tickers")
    except Exception as e:
        print(f"[scheduler] Cache refresh error: {e}")


def run_backtest_roller():
    """Monthly backtest window roller — appends new windows, exports JSON."""
    from research.backtest_roller import roll_all, export_meta_dataset
    from research.tracking import track_run
    now_str = datetime.now(WIB).strftime('%H:%M')
    print(f"[{now_str}] Backtest roller dimulai...")
    try:
        with track_run("roller", params={"include_partial": True}) as run:
            summary = roll_all(include_partial=True)
            n_exported = export_meta_dataset()
            run.metrics.update({"new_complete": summary["new_complete"],
                                "new_partial": summary["new_partial"],
                                "tickers_updated": summary["tickers_updated"],
                                "exported": n_exported,
                                "errors": len(summary["errors"])})
        msg = (
            f"🔄 <b>Backtest Roller Selesai</b>\n\n"
            f"New complete windows: <b>{summary['new_complete']}</b>\n"
            f"New partial windows: <b>{summary['new_partial']}</b>\n"
            f"Tickers updated: <b>{summary['tickers_updated']}/{summary['total_tickers']}</b>\n"
            f"JSON exported: <b>{n_exported} records</b>"
        )
        if summary['errors']:
            msg += f"\n⚠️ Errors: {len(summary['errors'])}"
        logging.info(msg)
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Backtest roller selesai. "
              f"{summary['new_complete']} complete, {summary['new_partial']} partial")
    except Exception as e:
        logging.error(f"[backtest_roller] {e}")
        print(f"[{now_str}] Backtest roller error: {e}")


_WF_PARITY_LOCK_JOB = "refresh_wf_edge_rule"

# Bounded-write tuning for the long parity study (audit P-1).
_PARITY_WRITE_ATTEMPTS = 6      # ~1+2+4+8+16 = 31 s of backoff on top of busy_timeout
_PARITY_WRITE_BACKOFF_S = 1.0


def _is_lock_error(exc) -> bool:
    return isinstance(exc, sqlite3.OperationalError) and (
        "locked" in str(exc).lower() or "busy" in str(exc).lower())


def _commit_with_retry(conn, write_fn, *, what: str,
                       attempts: int = _PARITY_WRITE_ATTEMPTS):
    """Run `write_fn(conn)` and commit as ONE transaction, retrying on lock.

    Atomicity is per call: on any failure the transaction is rolled back, so a
    ticker is either fully persisted (rows + checkpoint) or not at all. It is
    never half-written, and never marked complete without its rows.

    Raises the last error if every attempt is exhausted -- the caller decides
    whether to abandon the ticker or the run.
    """
    import time as _time
    delay = _PARITY_WRITE_BACKOFF_S
    last = None
    for attempt in range(1, attempts + 1):
        try:
            write_fn(conn)
            conn.commit()
            return True
        except Exception as e:            # noqa: BLE001 - re-raised below
            last = e
            try:
                conn.rollback()
            except Exception:
                pass
            if not _is_lock_error(e) or attempt == attempts:
                raise
            print(f"[WF-PARITY] {what}: database locked "
                  f"(attempt {attempt}/{attempts}), retrying in {delay:.0f}s",
                  flush=True)
            _time.sleep(delay)
            delay *= 2
    raise last


def refresh_wf_edge_rule(tickers=None, progress_every=25,
                         only_strategies=None, lock_job=None,
                         restart=False, checkpoint_every=1):
    """Walk-forward under the rule PRODUCTION ACTUALLY EXECUTES (finding L-1).

    `refresh_wf_scores` runs STRATEGY_FUNCS bare. The live scanner runs the same
    functions and then applies a weekly multi-timeframe trend gate to every
    strategy outside `_WEEKLY_GATE_BYPASS`. So wf_edge is evidence about a rule
    the engine does not execute, and engine/admission.py refuses to admit any
    strategy on it.

    This job closes that by MEASURING the production variant rather than by
    removing the gate: it re-runs the identical walk-forward with
    engine.filters_mtf.WEEKLY_MTF_FILTER applied at every candidate entry bar
    (bar-for-bar equivalent to the live gate — proven in
    tests/test_filters_mtf.py) and writes the result to `wf_edge_rule`, keyed by
    the rule_id the evidence belongs to.

    Deliberately NOT touched: `wf_scores` and `wf_edge`. They are the frozen
    record of the bare-rule study and remain the valid evidence for the three
    bypass strategies, whose live rule already equals the researched one.

    Warm-up is raised to engine.filters_mtf.WARMUP_BARS (160) because the weekly
    gate soft-passes until it has ~25 weeks of weekly history; a 60-bar tail
    would silently measure "gate mostly off". The extra tail is prior data only —
    trades are still filtered to entry_date >= test_start, so the OOS boundary is
    identical to the bare run.
    """
    from research.walkforward_multi import run_walk_forward
    from research.tracking import track_run
    from engine.wf_edge import (aggregate_wf_windows, save_wf_edge_rule,
                                ensure_wf_edge_rule_table, save_wf_rule_study,
                                ensure_wf_parity_checkpoint_table,
                                completed_parity_tickers, save_parity_checkpoint)
    from data.db import LONG_WRITE_BUSY_TIMEOUT_MS
    import hashlib as _hashlib
    import json as _json
    from engine.strategies import STRATEGY_FUNCS, _WEEKLY_GATE_BYPASS
    from engine.filters_mtf import WEEKLY_MTF_FILTER, WARMUP_BARS, clear_mask_cache
    from engine.rule_identity import live_rule_id, live_gates
    from datetime import datetime as dt

    # Only the gated strategies need re-measuring; the bypass three already have
    # rule-valid evidence in wf_edge.
    roster = {k: v for k, v in STRATEGY_FUNCS.items() if k not in _WEEKLY_GATE_BYPASS}
    if only_strategies:
        want = set(only_strategies)
        roster = {k: v for k, v in roster.items() if k in want}
        missing = want - set(roster)
        if missing:
            raise ValueError(f"not gated strategies (or unknown): {sorted(missing)}")
    rule_ids = {k: live_rule_id(k) for k in roster}
    gates = sorted({g for k in roster for g in live_gates(k)})

    job = lock_job or _WF_PARITY_LOCK_JOB
    if not _wf_lock_acquire(DB_PATH, job):
        print(f"[WF-PARITY] another run is in progress ({job}) — skipped")
        return
    try:
      with track_run("wf-parity", params={"final_only": True, "adjusted": True,
                                          "gates": gates,
                                          "warmup_bars": WARMUP_BARS,
                                          "strategies": sorted(roster)}) as run:
        ohlcv_map = _load_ohlcv_bulk(final_only=True)
        all_tickers = sorted(ohlcv_map.keys())
        if tickers:
            wanted = {t.strip().upper() for t in tickers}
            all_tickers = [t for t in all_tickers if t in wanted]
        now_str = dt.now().strftime("%Y-%m-%d %H:%M")

        # Identity of THIS study configuration. Resuming is only safe against an
        # identical configuration; a different roster, rule set or warm-up must
        # recompute rather than silently mix two studies' results.
        config_hash = _hashlib.sha256(_json.dumps(
            {"rule_ids": dict(sorted(rule_ids.items())),
             "gates": gates, "warmup_bars": WARMUP_BARS},
            sort_keys=True).encode()).hexdigest()[:16]

        # One long-lived connection for the whole run, with a much larger
        # busy_timeout than the interactive default (audit P-1).
        conn = db_connect(DB_PATH, busy_timeout_ms=LONG_WRITE_BUSY_TIMEOUT_MS)
        try:
            ensure_wf_edge_rule_table(conn)
            ensure_wf_parity_checkpoint_table(conn)
            conn.commit()
            done = set() if restart else completed_parity_tickers(conn, config_hash)
            pending = [t for t in all_tickers if t not in done]

            print(f"[WF-PARITY] {len(all_tickers)} tickers x {len(roster)} "
                  f"strategies, gates={gates}, warmup={WARMUP_BARS}, "
                  f"config={config_hash}")
            if done:
                print(f"[WF-PARITY] resuming: {len(done)} ticker(s) already "
                      f"persisted under this configuration, {len(pending)} to go",
                      flush=True)

            state = {"updated": 0, "errors": 0, "written": 0, "abandoned": []}
            batch = []                      # (ticker, aggregated_rows)

            def _flush(rows_batch):
                # Persist a batch: its wf_edge_rule rows AND its checkpoints in
                # ONE transaction, so a crash can never mark a ticker done whose
                # rows were not written.
                if not rows_batch:
                    return

                def _write(c):
                    n_written = 0
                    for tk, agg_rows in rows_batch:
                        n_written += save_wf_edge_rule(c, tk, rule_ids, agg_rows,
                                                       now_str, run.run_id)
                        save_parity_checkpoint(c, config_hash, tk,
                                               rows_written=len(agg_rows),
                                               completed_at=now_str,
                                               run_id=run.run_id)
                    _write.n = n_written

                _commit_with_retry(conn, _write,
                                   what=f"batch of {len(rows_batch)}")
                state["written"] += getattr(_write, "n", 0)

            for n, ticker in enumerate(pending, 1):
                try:
                    df = ohlcv_map.get(ticker)
                    if df is None or len(df) < 60:
                        # Nothing to score, but record the decision so a resume
                        # does not reconsider it every time.
                        batch.append((ticker, []))
                    else:
                        clear_mask_cache()
                        result = run_walk_forward(df, filters=[WEEKLY_MTF_FILTER],
                                                  warmup_bars=WARMUP_BARS,
                                                  strategies=roster)
                        if "error" in result:
                            batch.append((ticker, []))
                        else:
                            batch.append((ticker, aggregate_wf_windows(
                                result.get("ranked", []))))
                            state["updated"] += 1
                except Exception as e:
                    state["errors"] += 1
                    print(f"[WF-PARITY] {ticker} error: {e}")

                if len(batch) >= max(1, int(checkpoint_every)):
                    try:
                        _flush(batch)
                    except Exception as we:
                        # This batch is lost, but every PREVIOUS batch is durably
                        # committed and the run continues. Losing 229 minutes of
                        # work to one lock is the failure mode being removed.
                        state["abandoned"].extend(t for t, _ in batch)
                        print(f"[WF-PARITY] batch write abandoned after retries: "
                              f"{we}", flush=True)
                    batch = []

                if progress_every and n % progress_every == 0:
                    print(f"[WF-PARITY] {n}/{len(pending)} pending "
                          f"({state['updated']} scored, {state['errors']} errors, "
                          f"{state['written']} rows)", flush=True)

            try:
                _flush(batch)
            except Exception as we:
                state["abandoned"].extend(t for t, _ in batch)
                print(f"[WF-PARITY] final batch abandoned: {we}", flush=True)

            # Study manifests reflect the FULL study under this configuration --
            # counted from the persisted rows, so a resumed run reports totals
            # across all of its parts rather than only this process's share.
            scored_total = conn.execute(
                "SELECT COUNT(*) FROM wf_parity_checkpoint WHERE config_hash=?",
                (config_hash,)).fetchone()[0]

            def _write_manifests(c):
                for name, rid in rule_ids.items():
                    n_rows = c.execute(
                        "SELECT COUNT(*) FROM wf_edge_rule WHERE strategy=? "
                        "AND rule_id=?", (name, rid)).fetchone()[0]
                    save_wf_rule_study(c, name, rid, run_id=run.run_id,
                                       tickers_scored=scored_total,
                                       rows_written=n_rows,
                                       warmup_bars=WARMUP_BARS, gates=gates,
                                       last_computed=now_str)

            _commit_with_retry(conn, _write_manifests, what="study manifests")

            run.metrics.update({"tickers_total": len(all_tickers),
                                "tickers_resumed": len(done),
                                "tickers_scored": state["updated"],
                                "tickers_persisted": scored_total,
                                "rows_written": state["written"],
                                "errors": state["errors"],
                                "abandoned": state["abandoned"],
                                "config_hash": config_hash,
                                "rule_ids": rule_ids,
                                "updated_at_stamp": now_str})
            print(f"[WF-PARITY] wf_edge_rule updated: {state['written']} rows "
                  f"this run ({state['updated']} scored, "
                  f"{scored_total}/{len(all_tickers)} persisted overall, "
                  f"{state['errors']} errors, "
                  f"{len(state['abandoned'])} abandoned)")
        finally:
            conn.close()
    finally:
        _wf_lock_release(DB_PATH, job)
