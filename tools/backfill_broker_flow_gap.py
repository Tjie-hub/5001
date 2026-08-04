#!/usr/bin/env python3
"""
Backfill broker_flow for missing/partial trading dates.

Investigation (docs/audit/BROKER_FLOW_BACKFILL_REPORT.md, 2026-08-04) proved
the marketdetectors endpoint serves genuine historical broker data when both
`from` and `to` are supplied — verified live back to at least 2020-01-02,
cross-validated exact against already-collected broker_flow rows.

As of the 2026-08-04 freeze, the full corrected-scope backfill has already
run to completion (see the report) — this script remains for future drift
recovery, not because further backfill is currently expected.

Idempotent: for each gap date, only the tickers not yet present in
broker_flow are fetched (never the whole ticker list), and only dates
tools.check_broker_flow_coverage classifies as PARTIAL or MISSING are ever
touched — a COMPLETE date is never re-fetched or overwritten. Interrupting
and re-running is always safe: the missing (date, ticker) set is recomputed
fresh from the DB every run.

Writes to broker_flow AND bandar_detector only (the two tables
fetch_broker_flow() populates) — mirrors backfill_stockbit_flow_gap.py's
precedent of reimplementing a narrow store step rather than reusing
stockbit_fetcher.run_flow(), which would also re-fetch/re-write
stockbit_flow and stockbit_flow_bars on every call.

Usage:
    venv/bin/python3 tools/backfill_broker_flow_gap.py [--dry-run] [--limit-dates N]

Logs to: backfill_broker_flow_gap.log
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from data.db import connect as db_connect  # noqa: E402
import stockbit_fetcher as sf  # noqa: E402
from tools.check_broker_flow_coverage import build_report, EXPECTED_COVERAGE_START  # noqa: E402

DB_PATH = HERE / "data" / "walkforward.db"
LOG_PATH = HERE / "backfill_broker_flow_gap.log"

MAX_RETRIES = 3
RETRY_BACKOFF_S = 5
RATE_LIMIT_DELAY = 1.5  # matches stockbit_fetcher.RATE_LIMIT_DELAY


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def gap_dates(conn) -> list[str]:
    """Trade dates classified PARTIAL or MISSING by the coverage audit —
    COMPLETE dates are excluded and therefore never touched."""
    return [r["trade_date"] for r in build_report(conn) if r["status"] != "COMPLETE"]


def summarize_gaps(conn) -> dict:
    """Pre-flight summary printed before any backfill runs (never skip this
    — task requirement: know the blast radius before touching the API)."""
    report = [r for r in build_report(conn) if r["status"] != "COMPLETE"]
    n_missing = sum(1 for r in report if r["status"] == "MISSING")
    n_partial = sum(1 for r in report if r["status"] == "PARTIAL")
    total_requests = sum(r["expected"] - r["actual"] for r in report)
    avg_expected = round(sum(r["expected"] for r in report) / len(report)) if report else 0
    return {
        "n_missing": n_missing,
        "n_partial": n_partial,
        "avg_expected_tickers": avg_expected,
        "total_requests": total_requests,
        "estimated_hours": total_requests * RATE_LIMIT_DELAY / 3600,
    }


def select_dates_to_process(all_gap_dates: list[str], only_dates=None, limit=None) -> list[str]:
    """Narrow the work list for a validation run (`only_dates`) or a bounded
    run (`limit`, oldest-first). Requesting a date that isn't a genuine gap
    (e.g. already COMPLETE, or before EXPECTED_COVERAGE_START) is a hard
    error, not a silent no-op — the validation phase must fail loudly."""
    if only_dates:
        gap_set = set(all_gap_dates)
        unknown = [d for d in only_dates if d not in gap_set]
        if unknown:
            raise ValueError(
                f"date(s) not in the current gap list (already complete, or "
                f"before {EXPECTED_COVERAGE_START}?): {', '.join(unknown)}"
            )
        return list(only_dates)
    if limit:
        return all_gap_dates[:limit]
    return all_gap_dates


def missing_tickers_for_date(conn, trade_date: str) -> list[str]:
    expected = {r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM ohlcv WHERE date=?", (trade_date,)
    )}
    have = {r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM broker_flow WHERE trade_date=?", (trade_date,)
    )}
    return sorted(expected - have)


def fetch_and_store_one(conn, token: str, ticker: str, trade_date: str) -> bool:
    """Fetch broker flow for one (ticker, date) and INSERT OR REPLACE into
    broker_flow + bandar_detector only."""
    bf_result = sf.fetch_broker_flow(token, ticker, trade_date)
    if not bf_result or not bf_result.get("broker_rows"):
        return False

    conn.executemany(
        """INSERT OR REPLACE INTO broker_flow
        (ticker,trade_date,broker_code,side,lot,lot_value,value,
         value_total,avg_price,freq,investor_type)
        VALUES (:ticker,:trade_date,:broker_code,:side,:lot,:lot_value,
                :value,:value_total,:avg_price,:freq,:investor_type)""",
        bf_result["broker_rows"],
    )
    b = bf_result["bandar"]
    conn.execute(
        """INSERT OR REPLACE INTO bandar_detector
        (ticker,trade_date,avg_price,total_buyer,total_seller,
         net_broker_count,broker_accdist,value,volume,
         top1_accdist,top3_accdist,top5_accdist,top10_accdist,
         avg_accdist,updated_at)
        VALUES (:ticker,:trade_date,:avg_price,:total_buyer,:total_seller,
                :net_broker_count,:broker_accdist,:value,:volume,
                :top1_accdist,:top3_accdist,:top5_accdist,:top10_accdist,
                :avg_accdist,:updated_at)""",
        b,
    )
    conn.commit()
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit-dates", type=int, default=None,
                     help="process at most N gap dates (oldest first) this run")
    ap.add_argument("--dates", default=None,
                     help="comma-separated specific date(s) to process (validation runs), "
                          "e.g. --dates 2026-08-03. Errors if a date isn't a genuine gap.")
    args = ap.parse_args()

    conn = db_connect(str(DB_PATH))
    sf.init_flow_db().close()  # idempotent CREATE TABLE IF NOT EXISTS

    all_gaps = gap_dates(conn)

    # Pre-flight summary — always printed before any request is made.
    summary = summarize_gaps(conn)
    log(f"=== Pre-flight summary (coverage expected from {EXPECTED_COVERAGE_START}) ===")
    log(f"  MISSING dates: {summary['n_missing']}")
    log(f"  PARTIAL dates: {summary['n_partial']}")
    log(f"  Avg expected tickers/date: {summary['avg_expected_tickers']}")
    log(f"  Estimated requests: {summary['total_requests']:,}")
    log(f"  Estimated runtime: {summary['estimated_hours']:.1f}h")

    only_dates = [d.strip() for d in args.dates.split(",")] if args.dates else None
    try:
        dates = select_dates_to_process(all_gaps, only_dates=only_dates, limit=args.limit_dates)
    except ValueError as e:
        log(f"ERROR: {e}")
        sys.exit(1)

    token = sf.ensure_valid_token(None)
    if not token:
        log("ERROR: could not obtain a valid token — aborting")
        sys.exit(1)

    log(f"=== Backfill start: {len(dates)} date(s) selected dry_run={args.dry_run} ===")

    t0 = time.time()
    total_inserted = 0
    total_failed = 0
    failed_pairs: list[tuple[str, str]] = []
    dates_skipped = 0

    for di, d in enumerate(dates, 1):
        need = missing_tickers_for_date(conn, d)
        if not need:
            dates_skipped += 1
            log(f"[{di}/{len(dates)}] {d}: already complete — skip")
            continue

        log(f"[{di}/{len(dates)}] {d}: {len(need)} missing tickers")
        if args.dry_run:
            continue

        for ticker in need:
            ok = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    ok = fetch_and_store_one(conn, token, ticker, d)
                    break
                except Exception as e:
                    log(f"  [WARN] {d} {ticker} attempt {attempt}/{MAX_RETRIES} error: {e}")
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_BACKOFF_S * attempt)
            if ok:
                total_inserted += 1
            else:
                total_failed += 1
                failed_pairs.append((d, ticker))
                log(f"  ✗ {d} {ticker}: failed after {MAX_RETRIES} attempts")
            time.sleep(RATE_LIMIT_DELAY)

    elapsed = time.time() - t0
    log(
        f"=== DONE: inserted={total_inserted} failed={total_failed} "
        f"dates_already_complete={dates_skipped} elapsed={elapsed/3600:.2f}h ==="
    )
    if failed_pairs:
        log(f"Failed (date, ticker) pairs ({len(failed_pairs)}):")
        for d, t in failed_pairs:
            log(f"  {d} {t}")


if __name__ == "__main__":
    main()
