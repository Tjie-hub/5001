# ZCODE REPORT — Pre-open news-timing hypothesis, 2026-10-28

**Plain statement: the hypothesis is not testable on current data. The screen stopped at the G0 breadth
check — the pre-open news capture exists for only 8 of the last 119 trading days. Nothing was registered,
the census is unchanged at 615, and no event-day return was ever read.** D-117 filed; withdrawn before
registration and therefore uncounted (D-113/PEAD precedent).

## Owner request

"so the news hit before opening. test this new hypothesis" — after the 2026-10-28 tape check showed BBCA
+7.65% on its Q3 headline ("laba naik 4,2%"), which the 08:00 WIB pre-market Google News crawl had already
captured (news_mentions updated_at 08:22).

## What the staged protocol did

Mirroring this morning's C-003 flow (freeze → G0 breadth → register → pin → G1 once), the screen froze a
construction first and ran only formability counts:

- **Would-be event:** ticker-date with ≥ 1 same-day-published Google News headline already captured by the
  08:00 crawl (PIT-safe by construction — a 08:xx fetch proves the headline existed before the 09:00 open).
- **Would-be test:** daily equal-weight event portfolio, same-day open→close, net of one 0.60% round trip
  (D-082 basis); one-sided Newey–West t vs the exact deflation bar at census 616 = **3.300988** (formula
  verified: reproduces 3.300069 at N=614); kill if either half ≤ 0; sentiment/liquidity variants locked out
  as sensitivities (D-115 no-widening style).
- **Frozen stop rule:** ≥ 60 event-days (half the coverage window) required to proceed to a power check;
  no return read before that.

## G0 breadth result — STOP RULE FIRED

| Measure | Value |
|---|---|
| news_mentions coverage | 2026-04-26 → 2026-10-28 — 119 trading dates, 972 tickers |
| Dates with any 08:00–08:59 crawl rows | **8 of 119** (06-16, 07-08, 07-13, 07-23, 08-20, 10-15, 10-16, 10-28) |
| Event ticker-dates (count ≥ 1, pre-open) | 197 |
| Joinable to final ohlcv bars | **179 events over 7 dates** — vs the 60-date floor |

## Why the data looks like this (root cause)

1. **Coverage gap:** the pre-market job (`news_fetch_premarket`, 08:00 Mon–Fri) exists in code since
   `02c2034` (2026-06-10) but has written on only 8 trading days — the scheduler evidently is not up (or
   the job does not fire) before 08:00 on the other 111 days.
2. **Destructive overwrite:** `save_news_count` uses `INSERT OR REPLACE`, so on every normal day the
   17:00 crawl overwrites the row and erases the pre-open evidence. For all non-captured days, "was there
   news before the open?" is unrecoverable from this store. The 8 surviving dates are an endogenous subset
   (shaped by scheduler uptime), not a sample of pre-open-news days.

On today's date, 2026-10-28, the morning crawl happened to run — 38 tickers had pre-open news, BBCA among
them. That is the mechanism the owner saw. It is currently the exception, not a daily capability.

## Governance disposition

- **Withdrawn before registration** — never registered, so **not counted**: census stays **615**
  (bar 3.300069 at 614 / 3.300529 at 615 for any arm registered next). No HYPOTHESIS_REGISTRY row, no
  EXPERIMENT_LEDGER record, no G1, no return read.
- **Close-relative check:** PEAD (D-113) is the only relative — withdrawn at its own G0 on power, and it
  tested SUE-ranked post-earnings drift, not news timing. The 2026-09-29 broad search only inventoried
  news coverage (phase0_counts family F); no news-based return trial has ever been counted.
  `catalyst_flags` is empty — no alternative instrument exists.
- Freeze doc: `P-M/news_timing/G0_FREEZE_NEWS_TIMING_2026-10-28.md` (sha256 `f23914b6…`), with the exact
  count SQL in its appendix. Decision: **D-117**.

## Path to testability (owner decision — propose only, nothing changed)

1. **Append-only pre-market capture:** a `news_mentions_premarket` table written only by the 08:00 job
   (17:00 never touches it), or a `first_seen_at` column that the 17:00 REPLACE must preserve.
2. **Scheduler coverage fix:** root-cause why the 08:00 job fired on only 8/119 days and make it fire
   every trading day.
3. Accumulate event-days (the frequency is unknowable until capture is continuous), then re-freeze and
   re-run this breadth G0. A census trial is consumed only at the first return read — today nothing was
   consumed.

Artifacts: freeze + D-117 + this report. Commits local, **push HOLD** per standing rule.

---

**Correction note, 2026-10-29 (D-118).** Two statements above are superseded: (1) the census in force was
**614**, not 615 — C-003 was not registered on 10-28 — so the would-be bar was 3.300529 (615), not 3.300988;
(2) the 08:00 job did run: it completed on 33 of 37 trading days 2026-09-08 → 10-28, so the 17:00
`INSERT OR REPLACE` alone explains the missing pre-open rows (no scheduler fix needed). Also: the
`"<ticker> saham"` query matches word-tickers (PADA/LABA/BANK/DATA = 30% of the 10-29 pre-open headlines).
The verdict (withdrawn, uncounted, no return read) is unchanged.
