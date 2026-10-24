# ZCODE BRIEF — IHSG settled-bar fallback in the provisional repair; order-book foreign fields are the previous session

**Issued:** 2026-10-23, by Claude (planner role). Owner: "write it".
**Repos:** `~/10 Projects/idx-walkforward-5001` (branch `ops/hardening-2026-07-10`) and `~/jurnal26` (`main`).
**Push: HOLD.** The owner pushed everything up to `3fb2a73` (jurnal26 `5054fb6`) on 10-23. That approval was for
that push only. Commit locally; push when the owner says "push" (fast-forward only, never force).

## 0. The incident (2026-10-23, verified by Claude)

- **09:00 alert:** `provisional_bars_check` rc=1 reported 2026-10-21 with 1 provisional bar. That bar was **IHSG**:
  - close 5,297.77 = +0.36% on 10-20, the ~11:05 intraday snapshot that the 11:05 risk scan logged;
  - volume 0.
- **Script skipped it.** `scripts/repair_provisional_bars.py` (dry run) said `no settled bar for the session`. yfinance
  `^JKSE` has **no 2026-10-21 row at all**: it jumps from 10-20 to 10-22. Every stock has a final 10-21 bar.
- **A second, unreported error on 10-22.** The IHSG 10-22 bar was also provisional, with close **5,219.4** against
  settled **5,387.9** (−3.13%). It wasn't flagged as stranded yet. The script repaired it with `--apply`.
- **10-21 fixed by hand, by the owner.** Source: Stockbit `GET
  https://exodus.stockbit.com/company-price-feed/historical/summary/IHSG?period=HS_PERIOD_DAILY&start_date=…&end_date=…&limit=…&page=1`.
  - 10-21: open 5,310.848, high 5,328.36, low 5,185.36, close **5,328.36**, volume 299,973,450.
  - Its 10-22 close (5,387.905) equals yfinance's (5,387.90).
  - The row is now `is_final=1`, and the check reports no stranded sessions.
- **Same endpoint, foreign fields.** It returns BBCA 10-21 `net_foreign` **Rp448.09bn**. That is the exact value the
  order book `company-price-feed/v2/orderbook/companies/BBCA` returned as `fnet` on **10-22 at 09:09**. **The
  order book's `fbuy/fsell/fnet` are the previous session's foreign flow**, not today's.

## Rules
- **Production DB:** writes only through `data.db.connect()` and the repair script's existing write path. Never call
  `sqlite3.connect()` directly in new code.
- **Repair runs:** run the script `--apply` only after a dry run shows exactly what it will change. The live DB should
  have nothing stranded now, so test on fixtures.
- **Stockbit:** read `.stockbit_token` only, never log in, stop on 401/403/429, and run nothing heavy 21:05–06:30.
- **Frozen files:** jurnal26 `bigplayer_watch.py`, `tape.py` and `limit_watch.py` stay untouched (D-098/D-108).
- **Tests:** `tests/test_repair_provisional_bars.py`, `tests/test_db_centralization.py`, `tests/test_cron_contract.py`
  and `tests/security/test_secret_hygiene.py` must pass, plus `pytest -q` in jurnal26.

---

## F1. `repair_provisional_bars.py`: fall back to Stockbit for IHSG when yfinance has no settled bar

1. **Fallback rule:** when yfinance returns no bar for a stranded `(IHSG, date)`, fetch Stockbit's historical
   summary for `IHSG` over a small window around the date and use that day's open/high/low/close/volume.
   - Limit the fallback to **IHSG** for now: one GET per stranded IHSG session.
   - Stocks keep the yfinance path, with its split-basis guard. Stockbit stock bars could be a later option, but
     write no stock prices from Stockbit here.
2. **Agreement check before writing:** Stockbit's close must equal yfinance's within 0.05% on the nearest session
   where both exist (10-22: 5,387.905 vs 5,387.90). If they disagree, or no common session exists, skip with a new
   reason, `stockbit fallback disagrees with yfinance`, and leave the bar provisional.
3. **Labelling:** label the repaired row in the script's output (`source: stockbit`). If `ohlcv` has no source column,
   don't add one; log it.
4. **Also look at the 10-22 case.** Why was a provisional IHSG bar with a close 3% wrong never caught before the next
   session?
   - Find the IHSG writer: `data/fetcher.py`'s "Always refresh IHSG incrementally" block and its "finalised N
     provisional past session(s)" step, logged 10-21 09:31.
   - Say in the report why 10-22's bar was still provisional on 10-23 09:00, and whether that finalisation step skips
     IHSG when yfinance lacks the day.
   - **Fix it only if it is a small, clear bug**, with a test; otherwise report it.
5. **Tests**, with a fixture DB and mocked yfinance and Stockbit:
   - yfinance gap plus Stockbit agreeing: repaired, `is_final=1`;
   - Stockbit disagreeing: skipped with the new reason;
   - Stockbit 401: stops cleanly;
   - stocks never take the Stockbit path.

## F2. Order-book foreign fields: document them as previous-session values (jurnal26)

1. **Fix the explanations.**
   - **`auction_watch.py` comment (line ~23):** it already doesn't use `fbuy/fsell/fnet`, which is right, but the
     reason given is wrong. Replace it with the finding above: previous session's foreign buy/sell/net, matching the
     historical summary's `net_foreign` for the prior date (BBCA 10-21 Rp448.09bn, read on 10-22).
   - **C1 table:** correct `docs/ZCODE_AUCTION_WATCH_2026-10-22.md` C1 the same way.
2. **Optional, only if cheap.** The daily auction report may show it as context, labelled **"prior-session foreign
   net"**. Prefer the historical summary's `net_foreign` for the previous date over the book field, since it is
   explicitly dated. **Never present it as today's flow.**
3. **Same check elsewhere.** Grep both repos for other readers of the book's `fnet/fbuy/fsell` (5001 routes,
   screener, 5004 cards). List each one, and say whether it treats the value as today's. Fix display labels only;
   change no logic that feeds a frozen recorder or an alert threshold without saying so in the report.

## F3. Small follow-ups (added 2026-10-23 afternoon)

1. **The PNBS bank-layout caveat (your A1 finding).** Make the Sunday coverage step split bank and non-bank
   layouts on whether Interest Income is present, as you proposed. Write the rule into the A3 runbook in
   `docs/reports/ZCODE_FQ_FULL_PULL_2026-10-21.md` now, so Sunday's turn doesn't have to rediscover it.
   - **Parser check:** check `parse` on the pilot's PNBS and BBCA raw files. Does the parser store bank rows under
     the generic template because the HTML really uses it, or because the parser maps them wrongly?
   - **If the parser is wrong:** fix it with a test on the pilot fixtures. No live fetch is needed: the raw files are
     on disk.
2. **The auction monitor's first live day.** On **Monday 2026-10-26, after ~09:35**, check the run:
   - `jurnal26-auction-iep/match/post` fired;
   - `data/auction_events.jsonl` has lines for every phase;
   - `data/auction_reports/2026-10-26.md` rendered;
   - no request errors.

   Also check the new read endpoint `GET /api/auction?date=2026-10-26` on jurnal26. It is live since the
   13:33 restart on 10-23 and needs the owner or read token; use the read token in
   `~/.config/autoclaw-idx-monitor/read_token`, never the owner token. Report it in the same deliverable.
   - **Not this brief:** the C5 backfill at 19:00 tonight is yours from the consolidated brief; just confirm it ran.

## Deliverable

`docs/reports/ZCODE_IHSG_FALLBACK_FOREIGN_FIELDS_2026-10-23.md` (5001), covering:
- F1: the diff summary, the 10-22 root cause, and the test lines;
- F2: the list of readers and what changed;
- each item as DONE, BLOCKED (why) or NOT RUN (why);
- the commit and push hashes for both repos.
