# HANDOFF — mechanism inventory B (Task 3, classes G–O), 2026-10-07

**Branch:** `research/mechanism-inventory-b-2026-10` (from `origin/ops/hardening-2026-07-10`
@ `a28ec7e`, worktree `idx-walkforward-mechb`). **Authority:**
`ZCODE_BRIEF_MECHANISM_INVENTORY_B_2026-10-07.md` (e1aee99) + amendment 1 (2cec4db) +
amendment 2 (ed4b65e) + the owner's census ruling
(`DECISION_DRAFT_CENSUS_RATIFICATION_2026-10-07.md` @ `2937488`: N=595, +4 = 599 primary).
**Status: PUSHED AND STOPPED — no registration, no D-entry filing, no G0.**

## The rule, stated explicitly

**No post-event price was read.** `census_feasibility_b.py` (the one census script) touches
databases strictly read-only (`sqlite3` URI `mode=ro`, and `data.db.connect(read_only=True)`)
and every price/return statistic is computed from a slice **strictly before** the event's
decision date (or before a calendar window's start, or before class O's decision minute
09:15). No return, price change or excess return after any decision date was computed, printed
or stored, for any horizon or aggregate; no full-sample return series is materialized
(book volatilities are per-event trailing-60-session slices). Liquidity (ADV20) and pre-event
volatility are the only panel statistics. Class M reports only formation-date counts,
cross-section size and pre-formation volatility (stopped per brief). Class O reads lots and
prices from minutes 09:00–09:14 only; the cumulative-lots verification reads lot columns only.

## Files

| file | role |
|---|---|
| `census_feasibility_b.py` | **the one census script** — classes G/H/I/K/M/N/O → `CENSUS_FEASIBILITY_B.json`. Authored by the parallel Task-3 session (G/H/I/K core, 14:25), amended in this session: bars 599/280 per the ratification ruling, class I outcome-taint split + price-free breadth populations, class M allowed-stats, class N, class O. |
| `CENSUS_FEASIBILITY_B.json` | produced by that script alone (re-run end-to-end after the last edit). |
| `probe_class_n.py` + `PROBE_LOG_N.json` + `probe_n_data/` | the brief's ONE permitted network fetch (class N signal series only: GPR xls incl GPRC_IDN, 1900-01→2026-09, ~1-month publication lag; yfinance GC=F/CL=F/NG=F/HG=F 2000-08+, NICK.L 2008-01+, BTU 2017-04+; coal API2/CPO not attempted — no free source per v2 W2 §2). No-auth, logged, sha256 per file. The .csv variant 404'd and is recorded in the log. |
| `FEASIBILITY_B_2026-10-07.md` | the per-class report + mechanism D-entry drafts (draft only, nothing filed). |
| `COMBINED_RANKING.md` | A–O ranking; top 1–2 = A + D (owner-accepted), N next. |

## Provenance

- Panel: `research.rulecard.data.load_extended_ohlcv(issuance=True)` (D-053 backfill pickle
  `hist_pre2021.pkl` + production DB raw corpus, gap-verified splits, D-064 issuance
  correction), 2000-03-30 → 2026-10-06, 958 tickers. Run command (from the worktree):
  `DB_PATH=<production walkforward.db> python3 census_feasibility_b.py --hist <main-tree
  hist_pre2021.pkl> --db <production walkforward.db>` — the worktree carries no data; both
  paths point into the production tree READ-ONLY.
- The frozen minute store `data/frozen/stockbit-flow-bars-v002/` is read via `mode=ro` from
  the production tree (store sha `fa7f07b3…` per its MANIFEST); nothing in the production tree
  was written, checked out or modified.
- Bars: exact two-sided E[max|Z|], method identical to `deflation_audit/bar_v2.py`;
  reproduced in-script: 3.0558@266 (check), 3.067@276, 3.0713@280 (secondary), 3.2912@595
  (ratified census), **3.2931@599 (primary, 595 + HYP-PM-0016's 4)**.
- Deterministic: no sampling anywhere except the declared cumulative-lots check (12 evenly
  spaced dates × first 5 tickers each, fixed rule) — no RNG, no seed needed.

## Disclosures

- Class I: the recorded `classification` label is outcome-derived (resume-gap rule) and is
  used only as a disclosed population filter; a price-free breadth split (dataset_b rule,
  presence-only) is reported beside it; 1,618 episodes have no observable missing session
  (market/infra signature) and are excluded from resumption populations by construction.
- Class H: listing = first panel bar (S2 proxy); 181 onboarding artifacts excluded; the
  statutory 8-month clock (POJK 25/POJK.04/2017, verified) runs from the registration
  statement's effective date — the proxy is early by days-to-weeks; pre-2017 listings sit
  under an unverified older rule; survivorship bias disclosed.
- Class K: exactly 2 windows predeclared; no window scan; Lebaran/THR not computed (no holiday
  archive in-corpus).
- Class N: mapping ambiguity (Farm Products includes non-CPO agri; gold only 6 names) and the
  BTU-only coal proxy from 2017-04 are stated in the report.
- Class O: 2025-01→2026-04-28 is SEEN (planner's descriptive read, disclosed in amendment 2);
  its confirmation sample must come from the live window (2026-04-28→). The planner's
  descriptive statistics themselves were not re-derived here (they are the planner's, quoted).
- Task 2's outputs were read from `research/structural-events-feasibility-2026-10` @ `1c20f56`
  (pushed) for the combined ranking; no Task 2 file was modified.
- The sniper worktree (`idx-walkforward-sniperfilter`) was NOT touched by this session (its
  Revision 1/2 + G1 NULL landed via the parallel session: b3dd0bc, d261260, b9e5e5b).

## Boundary compliance

No registry or DECISION_LOG edits; no production checkout/commit/push; `logs/TELEGRAM_OFF`
untouched; no secrets printed; no force-push. Network: exactly one logged no-auth probe
(class N signal series). Pushed: this branch only, then STOP.
