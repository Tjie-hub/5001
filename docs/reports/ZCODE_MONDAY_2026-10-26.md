# ZCODE Monday 2026-10-26 — status report (written 2026-10-26 ~12:30 WIB)

Brief: `ZCODE_BRIEF_MONDAY_2026-10-26.md`. The ZCode session was stopped mid-run at ~11:50 (memory pressure); the
rest was completed in a Claude Code session. Push is **HOLD** in both repos; nothing was pushed.

| Item | Status |
|---|---|
| H1 Auction monitor, first live day | **DONE with defects found and fixed; 18:30 backfill pending** |
| H2 PEAD G0 power run | **NOT RUN** — refuses during market hours; one-shot timer `zcode-pead-g0-20261026` armed for 17:45 |
| H3 {FQ} PIT prep | **DONE** (D4 list verified; day-30 question unanswerable from local data; D8 texts blocked) |
| H4 Index rebalance 2026-11-02 | **NOT RUN (not yet announced)** — stopped per brief |

## H1. Auction monitor

1. **Timers fired but all three crashed** (exit 1) at 08:57 (`iep`), 08:59 (`match`) and 09:02/09:05/09:15/09:30
   (`post`). One cause: `parse_snapshot` did `float(d["arb"])`, but the live book reply sends
   `arb`/`ara` as `{'value': '4,680', 'visible': true}`. **Fixed** (`_band()` helper) — jurnal26 `d99a7e1`, with the
   09:30 post slot now calling `report(day)`.
2. **No report for 2026-10-26 yet** (`data/auction_reports/` ends at 10-22). The 09:30 slots are lost.
3. **A second defect was found in the backfill path** by a `--check` dry run: the dated running-trade pages carry
   `action ''` on the live day's 08:58 match prints, and the side filter dropped the whole auction (every name
   `auction 0 lots`, 7 names missing). **Fixed** — jurnal26 `12cb3c8`, with a regression test. Re-check: 25 names,
   ARNA 2,786 / BMTR 2,527 / TOWR 5,580 auction lots; NAYZ 0 (also 0 on 10-22). 25 tests pass.
4. **Recovery:** transient timer `zcode-auction-backfill-20261026` fires **18:30** (verified armed); runs the fixed
   working tree and writes `data/auction_reports/2026-10-26.md`. Transient units do not survive a reboot or logout
   (linger not checked).
5. **Not done:** `GET /api/auction?date=2026-10-26` with the read token (needs the 18:30 report to exist).
6. **Telegram:** the only Telegram path in `auction_watch.py` is `alert_holdings` → `notify.now(kind="position")`,
   an allowlisted kind. Not sent today because the `match` run crashed before reaching it. Nothing else is sent.

## H2. PEAD G0 power run
Not run. Timer fires 17:45. Expected per the brief: power ~2–8% against the 20% minimum, stop rule probably fires. No
numbers and no proposed D-entry text yet. No post-event return may be read.

## H3. {FQ} PIT prep
See `docs/research_programs/P-M/data_acquisition/12_FQ_PIT_FOLLOWUPS_2026-10-26.md`. Summary: D4 list = 417 rows,
142 tickers, all [S]; 39 names appear in all six periods, 7 duplicate (ticker, period) rows. Day-30 count cannot be
built — `fin.db` has no filing date. D8: idx.co.id still 403, Wayback 404; owner-browser list written. No v3, no
freeze, no D-entry.

## H4. Index rebalance
Latest announcement found: Peng-00148/BEI.POP/07-2026 (27 Jul), effective 3 Aug – 30 Oct 2026. The announcement for
the period starting 2 Nov was not found in search; typically late October. Nothing prepared. Re-check ~27–30 Oct.

## Files and commits
- 5001: `12_FQ_PIT_FOLLOWUPS_2026-10-26.md`, this report, `12_FQ_LATE_FILERS_2026-10-26.csv` (committed with them).
  `forward_fade` / `forward_regime` `ledger.json` changes are the 09:30/09:35 cron appends and are left uncommitted.
- jurnal26: `d99a7e1`, `12cb3c8` (local, `main` 5 ahead of origin; `logs/` untracked).
