# HANDOFF G0 — tender-offer floor (HYP-PM-0018 draft, D-074) · 2026-10-09

**Branch:** `research/tender-offer-floor-2026-10` from LOCAL hardening `f86d272` (origin
behind; `git merge-base --is-ancestor` verified), own worktree.
**Status:** G0 BUILT and FROZEN — predeclaration, drivers, 8 PIT tests, counts-only census.
**No return or price after any entry close was computed, printed or stored** (D-070 rule 1).
**THE STOP RULE FIRED: 12 eligible events < 20 → NO G1.** `SPREAD_LEDGER.md` is the
deliverable; the arm still counts in the census from registration (X8). NOT SUBMITTED — the
planner files the registration (expected D-079).

## Provenance and snapshot

- Events: 165 `tenderoffer` rows from `corporate_action_events`; prices: `ohlcv`
  (`is_final=1`) 2021-07-05 → 2026-10-07, 959 tickers. history_long NOT used (no 5001 prices
  pre-2021-07; pre-coverage offers counted out at S1, not silently dropped).
- **Snapshot REUSED (the 2026-10-08 walkforward pin):** live-vs-snapshot tenderoffer rows are
  logically identical — 165 = 165, same `(ticker, event_id, event_date, raw_json)` sets,
  newest event_date 2026-10-02 — nothing newer. sha256
  `a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47`; fingerprint
  `9c26e0df2fdd4e4bec378ff9d38b4d4ccbbdeaa9a6176ca71b3fdb955f137c03` (max_date 2026-10-07,
  1,102,829 rows). Both recorded in `CENSUS_G0.json`; `g1_run.py` would re-verify (moot).
- **Basis check (required by the brief): tender_price is AS-ANNOUNCED** — rescale
  `adj = price / f_cum(entry)`. Evidence: LPGI 2023 r_stored 10.42 vs r_asannounced 1.042;
  PTRO 2022 10.19 vs 1.019; EDGE 2021 2.02 vs 0.404 (6–10× "spreads" are impossible; 1–4%
  are sane). Contrast: `dividend_value` IS pre-scaled (stress G0) — the vendor is
  inconsistent across fields, so each field needs its own basis test. The rescale changed no
  final eligibility (LPGI→S7, PTRO-2022→S8, PTRO-2024/EDGE→S6) but is required for correct
  classification; PTRO-2022's 0.02pp cost-floor miss only exists under the rescale.
- **tender_created audit:** 104/165 created ≤ tender_start; 61 after (18 on/after tender_end —
  ZBRA class); no created-date shared by > 50 rows. Used for nothing else; the PIT rule is
  "public at the close before tender_start" (POJK 9/2018).

## Census (counts only; full detail in `CENSUS_G0.json`)

165 rows → **S1** 35 out (34 pre-coverage windows + KEJU start≥end) → **S2** 4 open offers
(DOOH, MBSS, NAYZ, SUPR — unsettled, recorder cases) → **S3** 1 (UANG, no entry bar) →
**S4** 0 → **S5** 28 (zero-volume entry close) → **S6** 60 (offer ≤ market) → **S7** 16
(true-ADV20 < Rp 1bn) → **S8** 9 (spread < 0.60% + D-059 cost) → **S9** 0 →
**ELIGIBLE 12** (2022:3, 2023:2, 2024:1, 2025:2, 2026:4).

**Planner cross-check (reproduce, don't trust):** planner 165 rows / 129 with 20 pre-bars /
67 of 129 below market / 26 eligible at ≥ Rp 1bn (median 3.6%). Mine: 165 / 129 / 60 (of the
129) / **12** (median 4.32%). The 26 → 12 delta decomposes into the frozen conventions the
planner did not apply: the zero-volume entry rule (28 events, mostly stale ARB names), the
D-059 cost INSIDE the spread floor (not just the 0.60%), settled-only windows, true-ADV
(split-corrected), and the basis rescale reclassifying several events at S6/S8. Same shape,
same era (2021→2026), same conclusion: n < 20.

## Power (pre-event facts only)

Pre-entry 60-session daily σ (bad-print masked, dividend add-back), scaled by
√window-sessions: median σ_d 1.96%, median window-scaled σ 9.14%, window median 21.5 sessions
(6–25). **MDE at n = 12 = 8.70%** vs bar 3.2978 — while the median spread is 4.32% (mean
9.63%, OASA's 58% outlier dominating). Even full convergence of every event would not clear
the bar at this n: the stop rule is power-correct, not merely count-correct.

## The bar and its N

**N = 609, bar 3.2978** (exact `bar_v2.e_max_abs_z(609)` = 3.29775843984798; recomputed at
this G0 from `docs/research_programs/deflation_audit/bar_v2.py`). Decomposition: 608 after
D-078 (605 after D-071/D-072 + 2 exploratory arms 2026-10-08 + 4 NR7 post-mortem comparisons
2026-10-08 + HYP-PM-0017's 2 arms + HYP-PM-0019's 1 arm) + THIS arm. **Conflict resolved
(owner 2026-10-09): the brief's census line (609/3.2978) supersedes D-074's stale 602/3.2945**
— the ledger moved three times after D-074 was written. No other brief-vs-D-074 conflicts
were found; the brief's rule-1 elaborations (≥ 2 window sessions; zero-volume entry;
settled-only) are refinements consistent with D-074's population, frozen here.

## D-059 cost source (frozen)

`docs/research_programs/P-M/cost_liquidity/cost_by_adv.py` @ **7e039ee** — verified
byte-identical on this branch (`git diff 7e039ee HEAD -- <path>` empty): 0.50% fees +
(½s_entry + ½s_exit) Abdi-Ranaldo over the 21 bars ending the bar before entry, floored at
one IDX tick + 2·σ_d·√(Q/ADV20), Q = Rp 100m.

## Mandatory/voluntary and full/partial

- **Mandatory vs voluntary: NO RULE — left unreported.** `event_note` is empty for ALL 165
  rows; no stored field classifies. Per the brief: don't guess.
- **Full vs partial: cut frozen at `tender_percentage` ≥ 99 = full. Degenerate — the maximum
  anywhere in the data is 90.0, so ALL events (eligible and not) are partial.** Reported as
  such.

## Withdrawn/proration (falsification clause 2; frozen definitions, never run)

withdrawn-suspect = close(tender_end) < 0.90 × min(close(entry), adj offer); proration-suspect
= `tender_percentage` < 99 (all events). Moot at the stop, but frozen for any future re-open.

## Forward recorder (D-074 §3; record only, NOT built — owner-gated)

Every new tender offer is logged at `tender_start` (price, adj basis, spread, true-ADV20,
volume) and again at `tender_end` (convergence ratio, any dividend add-back, paydate). First
case: **DOOH** — offer 148, window 2026-10-05 → 11-03 (excluded here as unsettled, with
MBSS/NAYZ/SUPR which close before it). Host: beside the D-064 ex-date monitor lineage —
a `scripts/check_tender_windows.py` in the style of `scripts/check_issuance_windows.py`
(cron 09:45 weekdays), ledger under `docs/research_programs/P-M/tender_offer/forward/`.
Approximate cadence from this census: ~3.4 eligible-shaped offers/year (12 in 4.7 years of
price coverage; 165 offers total since 2015).

## Runtime estimate for G1 (moot — stopped)

Census (panel build + hash + fingerprint + waterfall): **2.6 min**. A G1 run would add 12 ×
t1_event assemblies + one EW-book pass per event: **< 1 minute**. `g1_run.py` is frozen and
machine-refuses while `CENSUS_G0.json: stop_rule.n_eligible < 20`; re-arming requires a new,
disclosed, re-frozen G0 with a fresh census if the population ever grows past 20 settled
events (the recorder will eventually supply them).

## Governance

Read-only DB (mode=ro) on the pinned snapshot; no network; registries NOT edited (planner
files D-079); `~/jurnal26`, production, the 5001 service, `ops/hardening` beyond the branch
point untouched; `logs/TELEGRAM_OFF` untouched; no secrets printed. Boundary + fence tests
pass. All SQL inline-literal and parameterized.

*— ZCode, 2026-10-09*
