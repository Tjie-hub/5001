#!/usr/bin/env python3
"""Production full-universe stockbit_flow_bars backfill (2026-08-21).

TRACKED production successor of gitignored scratchpad/backfill_flow_5liquid.py
(which is now a delegating shim). Behaviour (completion predicate, write path,
per-cell durable commits, resume-from-DB) is preserved from the validated
scratchpad runner; see docs/audit/STOCKBIT_FLOW_BARS_BACKFILL_CORRECTNESS_FIX_2026-08-21.md.

Completion semantics (tools/flow_bars_gap.py, regression-tested):
a (ticker, trade_date) cell is complete iff bars exist OR the summary row
records a genuinely empty session. stockbit_flow alone is NEVER evidence that
bars exist -- that defect silently skipped 9,341 cells (2026-08-20 soak).

5-hour invocation boundary (structural):
  * BUDGET_S (env/flag) is clamped to HARD_CAP_S = 5h.
  * budget is checked inside the ticker/cell loop, with CELL_MARGIN_S = 300s
    headroom covering the documented worst-case in-flight cell:
    429 ladder 20+40+60+80s plus up to 4x15s request timeouts = 260s.
    With any BUDGET_S > CELL_MARGIN_S the last started cell finishes by
    BUDGET_S - 300 + 260 < BUDGET_S <= 5h.
  * exit always emits PASS END + CHECKPOINT lines.

Exit codes (B2 -- cron_wrap.sh alerts on any nonzero rc):
  0  success (including a planned budget stop -- work remains, rerun resumes)
  2  authentication failure (no valid token / refresh failed)
  3  sustained fetch failure (SUSTAINED_FAIL_LIMIT consecutive errors)
  4  database/write failure
  5  frozen regression fixture would be consumed (see FROZEN_FIXTURE_DATES)

Frozen discrimination fixture: 2025-04-14 (79 IDX80 activity-summary-no-bars
cells, zero bars on the date) is reserved for the final Day-1 sign-off test
and must not be consumed by any run or backfill beforehand. Runs whose window
includes it must pass --release-fixture (deliberate, auditable release).

Usage (Day-1 launch contract -- through cron_wrap.sh, never bare nohup):
  scripts/cron_wrap.sh backfill_flow_bars_day1 timeout 18120 \
    venv/bin/python3 tools/backfill_flow_bars.py \
    --date-from 2025-01-02 --date-to 2026-04-28 --budget-s 17400

Environment overrides (backward compatible with the scratchpad runner):
  FLOW_TICKERS (default ALL), FLOW_DATE_FROM, FLOW_DATE_TO, BUDGET_S.

Logs to: backfill_flow_bars.log (stdout is captured by cron_wrap too).
"""
import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from data.db import connect as db_connect  # noqa: E402
import stockbit_fetcher as sf  # noqa: E402
from tools.flow_bars_gap import bars_cell_complete  # noqa: E402

DB_PATH = HERE / "data" / "walkforward.db"
LOG_PATH = HERE / "backfill_flow_bars.log"

RATE_DELAY = 1.6  # seconds between vendor requests (matches validated runner)

# --- 5-hour boundary (B3) ----------------------------------------------------
HARD_CAP_S = 5 * 3600
# Worst documented in-flight cell: 429 Retry-After ladder 20+40+60+80s
# (stockbit_fetcher.fetch_flow) + up to 4 x 15s request timeouts = 260s.
WORST_CASE_CELL_S = 20 + 40 + 60 + 80 + 4 * 15
CELL_MARGIN_S = 300  # > WORST_CASE_CELL_S with headroom

# --- failure signalling (B2) -------------------------------------------------
SUSTAINED_FAIL_LIMIT = 25  # consecutive fetch failures => vendor outage, abort

EXIT_OK = 0
EXIT_AUTH = 2
EXIT_SUSTAINED = 3
EXIT_DB = 4
EXIT_FROZEN_FIXTURE = 5

# Frozen for the final Day-1 discrimination test (see module docstring).
FROZEN_FIXTURE_DATES = ("2025-04-14",)

# Backward-compatible env defaults (scratchpad runner contract).
_DEF_TICKERS = os.getenv("FLOW_TICKERS", "ALL")
_DEF_FROM = os.getenv("FLOW_DATE_FROM", "2025-01-02")
_DEF_TO = os.getenv("FLOW_DATE_TO", "2026-04-28")  # exclusive; window ends 04-27
_DEF_BUDGET = os.getenv("BUDGET_S", "17400")  # 4h50m, inside the 5h hard cap


def effective_budget(raw: int) -> int:
    """Clamp any requested budget to the 5h hard cap."""
    return min(int(raw), HARD_CAP_S)


def effective_margin(budget_s: int) -> int:
    """Cell-loop headroom. Full worst-case margin whenever it does not
    dominate a deliberately small (test) budget; a small budget just permits
    a bounded overshoot of at most WORST_CASE_CELL_S, which can never reach
    the 5h operating constraint."""
    return CELL_MARGIN_S if budget_s > CELL_MARGIN_S else max(5, budget_s // 6)


def budget_expired(t0: float, budget_s: int, now: float = None) -> bool:
    """True when a NEW cell must not be started (checked inside the cell loop)."""
    if now is None:
        now = time.time()
    return (now - t0) + effective_margin(budget_s) > budget_s


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def _resolve_tickers(cat: str) -> list:
    """Category name, or an explicit comma-separated ticker list (legacy
    FLOW_TICKERS=BBCA,TPIA,... contract from the scratchpad runner)."""
    if "," in cat:
        return [t.strip().upper() for t in cat.split(",") if t.strip()]
    return sf.get_tickers(cat)


def gap_dates(date_from: str, date_to: str) -> list:
    """Distinct ohlcv dates in [date_from, date_to), oldest first."""
    conn = db_connect(str(DB_PATH))  # the one SQLite entry point (B1)
    try:
        rows = conn.execute(
            "SELECT DISTINCT date FROM ohlcv WHERE date >= ? AND date < ? ORDER BY date",
            (date_from, date_to),
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


def _write(conn, flow) -> None:
    """Persist one fetch_flow result into stockbit_flow + stockbit_flow_bars
    with a durable per-cell commit (mirrors run_flow's write path)."""
    now = datetime.now().isoformat()
    comp_score = verdict = smart_money = None
    bars = []
    if flow.get("_raw_data"):
        try:
            bars = sf._parse_bars(flow["_raw_data"])
            a = sf._analyze(flow["ticker"], bars) or {}
            comp_score, verdict, smart_money = a.get("score"), a.get("verdict"), a.get("smart_money")
        except Exception as e:
            log(f"  [WARN] score compute: {e}")
    if bars:
        conn.executemany(
            """INSERT OR REPLACE INTO stockbit_flow_bars
            (ticker,trade_date,bar_time,buy_lot,sell_lot,buy_freq,sell_freq,
             net_value,price,delta) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [(flow["ticker"], flow["trade_date"], b["time"], b["buy_lot"],
              b["sell_lot"], b["buy_freq"], b["sell_freq"], b["net_value"],
              b["price"], b["delta"]) for b in bars if b.get("time")],
        )
    conn.execute(
        """INSERT OR REPLACE INTO stockbit_flow
        (ticker,trade_date,buy_lot,sell_lot,net_lot,buy_freq,sell_freq,
         net_value,last_price,composite_score,verdict,smart_money,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (flow["ticker"], flow["trade_date"], flow["buy_lot"], flow["sell_lot"],
         flow["net_lot"], flow["buy_freq"], flow["sell_freq"], flow["net_value"],
         flow["last_price"], comp_score, verdict, smart_money, now),
    )
    conn.commit()


def _checkpoint(done: int, skipped: int, fail: int, elapsed_s: float,
                budget_s: int, budget_hit: bool, stop_at: str) -> None:
    log(f"PASS END — wrote {done}, skipped {skipped}, no-data {fail} "
        f"in {elapsed_s/60:.1f} min (budget {elapsed_s:.0f}/{budget_s}s"
        f"{', BUDGET HIT — work remains' if budget_hit else ''}; stopped at {stop_at})")
    log("CHECKPOINT: gaps are recomputed from DB bars state on next run — "
        "resume needs no ordering, no cursor, no stockbit_flow evidence")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cat", default=_DEF_TICKERS,
                    help="ticker category: ALL (full universe, default) or LQ45/IDX80")
    ap.add_argument("--date-from", default=_DEF_FROM)
    ap.add_argument("--date-to", default=_DEF_TO, help="exclusive upper bound")
    ap.add_argument("--budget-s", type=int, default=int(_DEF_BUDGET),
                    help=f"wall-clock budget in seconds, clamped to {HARD_CAP_S}")
    ap.add_argument("--probe", action="store_true",
                    help="bounded endpoint test: BBCA on first+last date of range")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan only: log the work, make no vendor calls, write nothing")
    ap.add_argument("--release-fixture", action="store_true",
                    help="explicitly release the frozen regression fixture date(s)")
    args = ap.parse_args(argv)

    budget_s = effective_budget(args.budget_s)

    dates = gap_dates(args.date_from, args.date_to)
    if args.probe:
        dates = [dates[0], dates[-1]]
    tickers = _resolve_tickers(args.cat)

    frozen_in_window = [d for d in FROZEN_FIXTURE_DATES if args.date_from <= d < args.date_to]
    targeted_frozen = [d for d in frozen_in_window
                       if not args.release_fixture and dates == [d]]
    if targeted_frozen:
        # A run whose ENTIRE work list is the frozen fixture is explicitly
        # targeting it -- refuse loudly unless deliberately released.
        log(f"REFUSED: run targets frozen Day-1 discrimination fixture "
            f"{targeted_frozen}. Pass --release-fixture only for the sign-off "
            f"test. No cells touched.")
        return EXIT_FROZEN_FIXTURE
    if frozen_in_window and not args.release_fixture:
        log(f"NOTE: window includes frozen fixture {frozen_in_window} — this run "
            f"will STOP at the barrier instead of consuming it.")

    log(f"=== Backfill start: {len(dates)} date(s) x {len(tickers)} tickers "
        f"[{args.date_from},{args.date_to}) budget={budget_s}s "
        f"probe={args.probe} dry_run={args.dry_run} ===")

    if args.dry_run:
        conn = db_connect(str(DB_PATH))
        try:
            for d in dates:
                if d in FROZEN_FIXTURE_DATES and not args.release_fixture:
                    log(f"  [plan] {d}: FROZEN FIXTURE barrier — not planned")
                    break
                need = sum(1 for t in tickers if not bars_cell_complete(conn, t, d))
                log(f"  [plan] {d}: {need} incomplete cells")
        finally:
            conn.close()
        log("=== DRY RUN — no vendor calls, no writes ===")
        return EXIT_OK

    conn = sf.init_flow_db()

    token = sf.ensure_valid_token()
    if not token:
        log("ABORT: no valid token (authentication failure)")
        conn.close()
        return EXIT_AUTH

    done = skipped = fail = 0
    consec_fail = 0
    budget_hit = False
    stop_at = "-"
    t0 = time.time()

    for di, date in enumerate(dates, 1):
        if date in FROZEN_FIXTURE_DATES and not args.release_fixture:
            # Barrier semantics: earlier dates may be processed, but the
            # frozen fixture itself is never consumed without an explicit,
            # auditable release. A planned stop, like the budget boundary.
            stop_at = f"{date} (FROZEN FIXTURE barrier)"
            log(f"FROZEN FIXTURE barrier at {date} — stopping before consuming it; "
                f"pass --release-fixture for the Day-1 sign-off test")
            break
        if budget_expired(t0, budget_s):
            budget_hit = True
            stop_at = date
            log(f"BUDGET hit before {date} — safe stop; rerun to resume")
            break
        if not sf.verify_token(token):
            token = sf.ensure_valid_token()
            if not token:
                log(f"ABORT: token refresh failed at {date} (authentication failure)")
                _checkpoint(done, skipped, fail, time.time() - t0, budget_s,
                            budget_hit, date)
                conn.close()
                return EXIT_AUTH
        d_done = d_skip = d_fail = 0
        for t in tickers:
            # Completion is decided on stockbit_flow_bars (plus zero-activity
            # summary rows for genuinely empty sessions), NOT on stockbit_flow
            # alone. See tools/flow_bars_gap.py.
            if bars_cell_complete(conn, t, date):
                skipped += 1; d_skip += 1
                continue
            # Per-CELL budget check: a date-only check could overshoot the
            # deadline by most of a full-universe date (~50 min).
            if budget_expired(t0, budget_s):
                budget_hit = True
                stop_at = f"{date} (mid-date)"
                break
            try:
                flow = sf.fetch_flow(token, t, date)
            except sqlite3.Error as e:
                log(f"  [DB-ERR] {t} {date}: {e}")
                _checkpoint(done, skipped, fail, time.time() - t0, budget_s,
                            budget_hit, f"{date} {t}")
                conn.close()
                return EXIT_DB
            except Exception as e:
                log(f"  [ERR] {t} {date}: {e}")
                flow = None
            if flow:
                try:
                    _write(conn, flow)
                except sqlite3.Error as e:
                    log(f"  [DB-ERR] write {t} {date}: {e}")
                    _checkpoint(done, skipped, fail, time.time() - t0, budget_s,
                                budget_hit, f"{date} {t}")
                    conn.close()
                    return EXIT_DB
                done += 1; d_done += 1
                consec_fail = 0
            else:
                fail += 1; d_fail += 1
                consec_fail += 1
                if consec_fail >= SUSTAINED_FAIL_LIMIT:
                    log(f"ABORT: {consec_fail} consecutive fetch failures at "
                        f"{date} {t} — sustained vendor error/429 condition")
                    _checkpoint(done, skipped, fail, time.time() - t0, budget_s,
                                budget_hit, f"{date} {t}")
                    conn.close()
                    return EXIT_SUSTAINED
            time.sleep(RATE_DELAY)
        if budget_hit:
            log(f"BUDGET hit mid-date at {date} after wrote={d_done} skip={d_skip} "
                f"this date — safe stop (last cell committed); rerun to resume")
            break
        if args.probe or di % 10 == 0 or d_fail:
            log(f"[{di}/{len(dates)} {date}] wrote={d_done} skip={d_skip} nodata={d_fail} "
                f"| cum={done} | {(time.time()-t0)/60:.1f}min")

    _checkpoint(done, skipped, fail, time.time() - t0, budget_s, budget_hit, stop_at)
    conn.close()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
