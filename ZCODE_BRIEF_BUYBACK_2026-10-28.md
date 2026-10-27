# ZCODE BRIEF — Buyback (share repurchase) as a new IDX hypothesis candidate (propose-only)

**Issued:** 2026-10-27, by Claude (planner role). Owner: "tambahkan juga buyback ke riset baru".
**Repos:** `~/10 Projects/idx-walkforward-5001` (`ops/hardening-2026-07-10`). **Push: HOLD.** Commit locally.
**Scheduling:** systemd one-shot timers only. Run after the C-003 brief; independent of it.

## Why this is open
Verified 2026-10-27 before issuing: `corporate_action_events` has types bonus, dividend, rightissue, rups, stock_reverse,
stocksplit, tenderoffer, warrant. **There is no buyback type**, and no `buyback`/`repurchase`/`buy back` string in any
`raw_json`. The hypothesis search (`search/00_EXCLUSION_INDEX`, `cand/C-001..C-008`) never considered buybacks. Tender
offers (D-080, dormant) are a different mechanism and are not buybacks.

## Rules (same as the search brief)
- **No return, spread, t-stat, IR or P/L of any buyback sort or event may be computed or read.** Event counts,
  coverage, date-quality checks and prior-only power only. If a step seems to need an outcome, stop and ask.
- Nothing registered, no D-entry, no registry or `DECISION_LOG.md` edit, no freeze pinned. Census stays 613.
- Frozen: {FQ} G0 freeze and its sums file, PEAD freeze, C-003 freeze draft, jurnal26 watchers.
- Production DB read-only via `data.db.connect()`. Stockbit: token file only, no login, stop on 401/403/429.
- Web sources allowed for announcements and regulation; tag every source [P]/[S]; nothing behind a login or against
  site terms. idx.co.id returned 403 before, so expect secondary sources and say so.

## B1. Data availability (the gating question)
1. Search the data already held first: `corporate_action_events` (esp. `rups` agendas), news tables, insider/filing
   tables, `fin.db` (treasury-stock / "Treasury Shares" / "Shares Repurchased" lines in equity and cashflow, including
   the vendor `Payment Of Dividend`-style taxonomy used for C-003), KSEI share counts. Record what each can and cannot
   identify (announcement date, executed amount, shares bought, period).
2. Then external: keterbukaan informasi / OJK / IDX announcements of buyback programmes (announcement date, value,
   share cap, execution window, with or without RUPS), and secondary coverage. Report reachability honestly.
3. Output `P-M/buyback/00_DATA_AVAILABILITY_2026-10-28.md`: per source — fields, date range, point-in-time quality,
   event count, cost to acquire. Mark the whole candidate INFEASIBLE if no source gives a dated announcement series.

## B2. Overlap and prior (before any build)
`P-M/buyback/01_OVERLAP_2026-10-28.md`: cite the nearest exclusion-index rows and say exactly how a buyback hypothesis
differs. At minimum address:
- **C-003 dividend-yield level** and **{FQ}**: net-payout (dividends + buybacks − issuance) overlaps both. Is a pure
  buyback arm distinct, or does it collapse into payout-commitment / value? State the FM-separator needed.
- **Issuance (C2, `RULE_FIRST_PROTOCOL`)**: McLean-Pontiff-Watanabe report the issuance effect is driven by low returns
  after share creation, not by positive returns after repurchases. Say what that prior implies for a long-only book.
- **Market-stress (D-079, F2)** and the tape/flow studies: buybacks are often announced in drawdowns or crisis rule
  relaxations, so a buyback signal may re-measure stress. State how to separate it.
- **Insider buys (null)**, **tender offers (D-080)**, **dividends (D-077)**.
If it is a re-skin of a closed arm, say so and stop.

## B3. Candidate file and power (only if B1 finds data and B2 finds it distinct)
Write `P-M/search/cand/C-009_buyback.md` in the C-001..C-008 format: mechanism (who is constrained or signalling, why it
persists after cost), falsifiable prediction (sign, horizon, universe, benchmark; kill condition), data and look-ahead
risks (announcement vs execution date, programmes announced but never executed, survivorship), event count and
**prior-only power** at the repo's bar (census 613 → ~3.3, no outcome used), minimum detectable effect, cost and
capacity (ADV, ARA/ARB execution), and distinctness from the live book. Tag **UNDERPOWERED** if the event count cannot
reach the bar (as for tenders and PEAD). Add a draft skeleton `SKEL-C-009_buyback.md` only if it is not UNDERPOWERED
and not INFEASIBLE.

## Deliverable
`docs/reports/ZCODE_BUYBACK_2026-10-28.md`: B1 table and verdict, B2 verdict, C-009 status (INFEASIBLE / OVERLAP /
UNDERPOWERED / CANDIDATE), open owner questions, files written and commit hashes. Append a row for C-009 to the
shortlist file `02_RANKED_SHORTLIST_2026-10-28.md` and a line to the `TODO.md` status block.
Commit small: `docs(research): buyback -- <step>`.
