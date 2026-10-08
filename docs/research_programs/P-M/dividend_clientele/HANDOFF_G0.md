# HANDOFF G0 — dividend clientele (HYP-PM-0017 draft, D-073) · 2026-10-08

**Branch:** `research/dividend-clientele-2026-10` (from hardening `8664856`, new worktree).
**Status:** G0 frozen — predeclaration, drivers, PIT tests and a counts-only census; **no return
after any event's entry/cum close was computed, printed or stored** (D-070 rule 1). Pushed and
STOPPED; G1 awaits owner approval (`DIVIDEND_G1_APPROVED=1`).

## The bar and its N

- **N = 603, bar = 3.2950** (exact `bar_v2.e_max_abs_z(603)` = 3.294959), frozen at G0.
- Ledger rows counted: **601** = D-071's ratified census 595 (its 9 components) + the **two
  exploratory arms run 2026-10-08** (the A/D "trap" check and the volume-profile swing check,
  both null) per the **D-075 census note** — plus **this G0's 2 arms** (D1, D2).
- **Conflict, resolved by the D-entry + owner correction (D-entry wins):** the brief's census line
  ("599 + 2 = 601", "primary t ≥ 3.2940") and its "next free number expected **D-075**" are stale —
  the D-075 census note post-dates the brief and puts the ledger at 601 (→ 603 here), and D-075 is
  now TAKEN (market-stress reversal), so the draft D-entry here is numbered **D-076**. Also noted:
  D-073 says "rups rows start in 2020" but the earliest `rups_date` is 2013-06-11 — no design
  impact (all liquid events are 2021+), recorded here.

## Snapshot (pinned; G1 verifies before any outcome)

- `/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db`
  sha256 `a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47`,
  dataset fingerprint `9c26e0df2fdd4e4bec378ff9d38b4d4ccbbdeaa9a6176ca71b3fdb955f137c03`
  (max date 2026-10-07, 1,102,829 final ohlcv rows). Shared with the stress-reversal G0
  (same day, same DB).

## The anchor rule as frozen

- Anchor = the **earlier of** (a) the latest `rups_date` 1–90 calendar days before cum, and
  (b) `dividend_created` when it is < cum and non-artefact. Entry = close of the later of
  cum−10 sessions and the first session after the anchor; window 3–10 sessions, shorter dropped.
- **The artefact test is reliable, so the two-clause rule applies (not the (a)-only fallback).**
  Findings (`CENSUS_G0.json: created`): of 4,762 parsed rows, 2,460 have `dividend_created` <
  `dividend_exdate` on dates shared by ≤ 50 rows (usable); the bulk loads are fully separated —
  2018-07-17 carries 1,061 rows and 2015-07-28 carries 134, **all** of which also fail the
  created ≥ exdate clause. 2,428 rows are usable AND before cum (gap to cum p25/p50/p75 =
  5 / 7 / 8 calendar days — the vendor record typically appears just BEFORE the AGM date).
  Semantics caveat, disclosed: `dividend_created` is the SOURCE-side record-creation date; we
  cannot prove the vendor's write policy, only that it is pre-cum and not bulk-stamped for the
  usable set — exactly what D-073's clause permits.
- **Decomposition of D1's n (owner's "about 445" expectation):** rups-anchored (a) = **437**
  (9 rups-only + 428 both-anchors) — matching the planner's 445 within data drift; the frozen
  earlier-of rule adds **125 created-only** anchors → **D1 n = 547**. 15 events dropped for
  windows < 3 sessions; no liquid event lacks an anchor.

## Pre-event counts (counts only; full funnel in CENSUS_G0.json)

- 4,762 dividend rows → 4,758 merged events → exclusions: 2,614 cum-not-session
  (**2,603 are pre-2021-07 — the walkforward corpus starts 2021-07-05**; the rest
  are market holidays), 1 ex-mismatch (excluded, not repaired), 14 corporate-action-in-window,
  1,567 not liquid (ADV20 < Rp 10bn), 0 missing bars, 0 FORU → **562 liquid events**
  (2021-07..2026-09; halves 237 / 325; AGM-season share 60.5%).
- **D1 n = 547** (halves 223 / 324), window distribution {3:13, 4:26, 5:474, 6:4, 7:3, 9:1, 10:26}
  — **median window 5 sessions**, NOT ~10: the `dividend_created` anchor (gap ~7 calendar days)
  is usually EARLIER than the rups date (gap 8/10/12 cal days, p25/p50/p75) and pulls entry in
  from the cum−10 cap. The brief's power expectation ("about 1.3% clustered") assumed the longer
  window; the frozen rule gives the numbers below.
- **D2 n = 324** (yield ≥ 2%; halves 128 / 196; tercile edges frozen at 3.48% / 6.23%).
- Planner cross-check (brief: "reproduce, don't trust"): 575 liquid → 562 (the 13 delta = the
  brief's own exclusion rules the planner did not apply: CA-in-window 14, ex-mismatch 1, session
  mapping); 333 yield ≥ 2% → 324; 445 rups-anchored → 437. All deltas explained; none changes a
  frozen rule.

## Power (pre-event σ only; t_bar = 3.2950)

- **D1:** median σ_d 2.63%/day, median window 5 sessions, n = 547, 56 months →
  **MDE 0.83% independent, 2.59% month-clustered.** (The brief expected ~1.3% clustered at a
  ~10-session window; the frozen anchor rule halves the window and the clustered MDE rises to
  ~2.6% — D1 is, as predeclared, likely null.)
- **D2:** median overnight σ 0.92%, n = 324 → **MDE 0.17%** (the brief's 0.43% used close-to-close
  σ; the frozen rule uses the pre-event overnight σ, which is much smaller). D2 is well powered
  for a clientele gap of the size the literature reports.

## Runtime estimate for G1

Census (same panel load + universe deciles): 2.0 min. G1 adds the Book build (per-session
membership + ADV20 over ~1,265 sessions × ~900 tickers) and 869 outcome evaluations — estimated
**15–30 minutes** single-threaded, well inside one session. RESULT schema already proven by
`g1_run.py --synthetic` on the fixture market (no real data touched).

## Conflicts raised (none open)

1. Brief census (601/3.2940) vs D-075 census note + owner correction (603/3.2950) → **frozen at
   603/3.2950** (D-entry + owner win), per the task's explicit correction.
2. Brief "next D-number expected D-075" → **D-076** (D-075 taken).
3. Brief's power expectations (~445 anchored, ~10-session windows, D2 MDE 0.43%) vs the frozen
   anchor rule's actuals (547 anchored, median window 5, D2 MDE 0.17%) → the FROZEN rule (owner's
   earlier-of anchor) governs; the expectations were planner estimates and are reported as such.
4. D-073 "rups rows start in 2020" → actually 2013-06-11 (no impact, recorded).

## Governance

Read-only DB (mode=ro) on the pinned snapshot; no network; HYPOTHESIS_REGISTRY / FAILURE_REGISTRY
/ DECISION_LOG untouched; `~/jurnal26`, production, the 5001 service and `ops/hardening` beyond the
branch point untouched; `logs/TELEGRAM_OFF` untouched; no secrets printed. Boundary + fence tests
pass. **Per the brief: push and STOP.**

*— ZCode, 2026-10-08*
