"""Snapshot one day's pre-open news_mentions rows before the 17:00 crawl overwrites them.

Stopgap for the D-117 root cause: `news_filter.save_news_count` is INSERT OR REPLACE, so the 17:00 crawl
replaces the 08:00 rows every day and the "headline existed before the 09:00 open" evidence is lost.
The 08:00 job itself fires daily (app.log: completed on 28 trading days 2026-09-09..10-28), so a same-day
copy is enough to keep the evidence until an append-only capture exists in production.

Read-only on the production DB. Writes `premarket_capture/<date>.jsonl` (every row of the date, zero
counts included -- "no pre-open news" is data too) and appends its sha256 to `premarket_capture/SHA256SUMS`.
Refuses when any row of the date was not written in [08:00, 09:00) WIB (already overwritten, or the
08:00 crawl did not run) and never overwrites an existing snapshot.

    venv/bin/python docs/research_programs/P-M/news_timing/snapshot_premarket.py            # today
    venv/bin/python docs/research_programs/P-M/news_timing/snapshot_premarket.py 2026-10-29
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))  # repo root, for data.db
from data.db import connect  # noqa: E402

OUT = HERE / "premarket_capture"


def preopen(updated_at, day):
    return updated_at[:10] == day and "08:00" <= updated_at[11:16] < "09:00"


def main(argv):
    day = argv[0] if argv else date.today().isoformat()
    date.fromisoformat(day)  # validate before touching anything
    out = OUT / f"{day}.jsonl"
    if out.exists():  # a retry after a good capture is not an error; the file is never rewritten
        print(f"{out.name} already captured; snapshots are append-only")
        return
    con = connect(read_only=True)
    try:
        rows = con.execute(
            "SELECT ticker, date, count, headlines_json, updated_at FROM news_mentions "
            "WHERE date = ? ORDER BY ticker", (day,)).fetchall()
    finally:
        con.close()
    if not rows:
        raise SystemExit(f"no news_mentions rows for {day}")
    late = [r for r in rows if not preopen(r[4] or "", day)]
    if late:
        raise SystemExit(f"{len(late)}/{len(rows)} rows not written 08:00-09:00 (e.g. {late[0][0]} "
                         f"{late[0][4]}): already overwritten or no pre-open crawl; refusing")
    OUT.mkdir(exist_ok=True)
    body = "".join(json.dumps({"ticker": t, "date": d, "count": c, "headlines": json.loads(h or "[]"),
                               "updated_at": u}, ensure_ascii=False) + "\n" for t, d, c, h, u in rows)
    out.write_text(body, encoding="utf-8")
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    with (OUT / "SHA256SUMS").open("a") as f:
        f.write(f"{sha}  {out.name}\n")
    with_news = [r for r in rows if r[2] > 0]
    print(f"{out.name}: {len(rows)} rows, {len(with_news)} tickers with pre-open news, "
          f"{sum(r[2] for r in rows)} headlines, written {rows[0][4]} | sha256 {sha[:16]}")


if __name__ == "__main__":
    main(sys.argv[1:])
