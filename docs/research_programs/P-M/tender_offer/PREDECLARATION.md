# PREDECLARATION — tender-offer price floor T1 (HYP-PM-0018 draft), G0 freeze

**Status:** frozen before any outcome was read · **Date:** 2026-10-09 ·
**Authority:** **D-074** (mechanism accepted, owner 2026-10-08: "G1 + stop rule"; owner go-ahead
2026-10-09: "go for D-074"), brief `ZCODE_BRIEF_TENDER_OFFER_FLOOR_G0_2026-10-09.md` (f86d272).
Where brief and D-entry disagree, D-074 wins, EXCEPT the census line (brief N = 609, bar 3.2978)
which supersedes D-074's stale 602/3.2945 (owner 2026-10-09).
**Branch:** `research/tender-offer-floor-2026-10` from local hardening `f86d272` (origin was
behind; verified ancestor), own worktree.
**Family:** Structural-Event **{SE}**, slot 2 (opened by D-076; HYP-PM-0017 is slot 1, FAILED
D-077). One tested arm (T1). Registration HYP-PM-0018; expected D-number at filing **D-079**.
**Outcome at freeze: the STOP RULE FIRED** (12 eligible events < 20) — there is **NO G1**; the
deliverable is the descriptive spread ledger (`SPREAD_LEDGER.md`). The arm still counts in the
census from registration (D-074 X8). `g1_run.py` is frozen anyway and machine-refuses while the
census says stopped.
**The sha256 sidecar (`PREDECLARATION.sha256`) covers THIS file, `tender_floor.py`,
`g0_census.py`, `outcomes.py`, `g1_run.py`, `synthetic.py` and `test_pit_tender.py`.**

## 1. Question

A tender offer is a contractual promise to buy at a fixed price until `tender_end`, paid on
`tender_paydate` (POJK 9/2018). If the market trades below the offer, the gap is an arbitrage
spread bounded by deal risk and time — not a forecast. Honest prior (D-074): at n ≈ 26 expect a
small positive mean below the bar, or a stop. The forward recorder is the durable output.

## 2. Data and provenance (frozen)

- **Events:** 5001 `corporate_action_events` `action_type='tenderoffer'` (165 rows), fields from
  `raw_json` (`tender_price`, `tender_start`, `tender_end`, `tender_paydate`,
  `tender_percentage`, `tender_shares`, `tender_created`, `event_note`).
- **Prices:** 5001 `ohlcv` (`COALESCE(is_final,1)=1`) on the pinned snapshot — coverage
  2021-07-05 → 2026-10-07 (959 tickers). history_long is NOT used: offers from 2015 exist in
  the CA table but have no 5001 prices before 2021-07; those events die at the window check and
  are COUNTED (34), plus 1 malformed (KEJU start ≥ end).
- **Snapshot pinned:** REUSES the 2026-10-08 walkforward snapshot
  `a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47` (dataset fingerprint
  `9c26e0df2fdd4e4bec378ff9d38b4d4ccbbdeaa9a6176ca71b3fdb955f137c03`, max_date 2026-10-07,
  1,102,829 rows) — justified: the LIVE DB's tenderoffer rows are logically identical to the
  snapshot's (165 = 165, same `(ticker,event_id,event_date,raw_json)` sets; newest event_date
  2026-10-02; nothing newer than the snapshot). G1 (if it ever ran) re-verifies both.
- **BASIS RULE (settled at this G0, frozen):** `tender_price` is **AS-ANNOUNCED** (on the
  as-traded basis of the offer time), NOT pre-scaled to the stored basis — the OPPOSITE of
  `dividend_value`. Discriminating events (split-class factor f_cum ≥ 1.05 after entry): LPGI
  2023 r_stored 10.42 vs r_asannounced 1.042; PTRO 2022 10.19 vs 1.019; EDGE 2021 2.02 vs
  0.404 — stored-basis ratios of 6–10× are impossible spreads. **Frozen rescale:
  `adj_price = tender_price / f_cum(entry)`**, f_cum = product of split-class share factors
  (stocksplit new/old, bonus `stocksplit_factor`, stock_reverse new/old) with ex-date strictly
  after the entry session. This is an accounting identity (the same spread the trader saw),
  not future information. It changed no final eligibility (LPGI died at ADV, PTRO-2022 at the
  cost floor, PTRO-2024/EDGE below market) but is required for correct classification.
- **True-rupiah ADV20** as in the stress G0: mean(close × f_cum(bar) × volume) over the 20
  bars strictly before the entry bar.
- **Guards:** daily |return| > 35% is a bad print (NaN for return aggregation); FORU excluded
  from 2026-09-14 (D-063; the 2024-05 FORU tender predates the cutoff and is unaffected);
  dividends IDR-only, deduped by `dividend_id`, summed per (ticker, ex-date), add-back on EX
  dates only.

## 3. When is the offer known? (settled at G0)

The offer is treated as **public at the close of the session before `tender_start`** (the offer
statement precedes the window; POJK 9/2018). `tender_created` is a vendor stamp used for
NOTHING except the audit: 104/165 rows created ≤ `tender_start`, 61 after (18 on/after
`tender_end`, e.g. ZBRA created 2021-09-23 for window 2021-04-30→05-29); no created-date is
shared by > 50 rows (no bulk-stamp artefact). PIT test (a): the spread, ADV20 and eligibility
use only bars at or before the entry close.

## 4. Population (D-074, frozen waterfall; each stage counted)

0. 165 tenderoffer rows.
1. **Rule 1:** price/start/end stored & parseable, price > 0, start < end, ≥ 2 5001-sessions
   inside [start, end] → 35 fail (34 windows entirely pre-coverage + KEJU).
2. **Settled:** `tender_end` ≤ the panel's last session — open offers belong to the forward
   recorder → 4 fail (DOOH, MBSS, NAYZ, SUPR).
3. **Entry:** the last session strictly before `tender_start` exists and the ticker has a bar
   on it with close > 0 → 1 fail (UANG).
4. **20 pre-bars** (ADV20 defined) → 0 fail.
5. **Entry volume > 0** (a zero-volume entry close is not tradeable) → 28 fail.
6. **Priced above the market:** spread = adj_price/close(entry) − 1 > 0 → 60 fail.
7. **True-ADV20 ≥ Rp 1bn** on the entry session → 16 fail.
8. **Spread ≥ 0.60% + the D-059 modelled round-trip cost** at the name's ADV20 → 9 fail.
9. **Guards:** no split/bonus/reverse/rights ex-date inside (entry, exit]; FORU-post-cutoff →
   0 fail.
**Eligible: 12 events** (2022:3, 2023:2, 2024:1, 2025:2, 2026:4). Planner's pre-counts (26 at
≥1bn) were NOT trusted — reproduced instead; the delta is the frozen conventions above
(zero-volume entry rule, settled-only, the D-059 cost INSIDE the spread floor, true-ADV, and
the basis rescale reclassifying several events at S6/S8).

## 5. The arm (T1 — frozen, but NOT RUN: the stop rule fired)

- **Entry:** the close of the session before `tender_start`. **Exit:** the close of the last
  session on or before `tender_end`.
- **R = (close(exit) + dividends ex inside (entry, exit]) / close(entry) − 1 − D-059 cost**
  (market exit at the tender_end close).
- **Cost:** `P-M/cost_liquidity/cost_by_adv.py` @ **7e039ee** (verified byte-identical on this
  branch): 0.50% fees + (½s_entry + ½s_exit via Abdi-Ranaldo over the 21 bars ending the bar
  before entry, floored at one IDX tick) + 2·σ_d·√(Q/ADV20), Q = Rp 100m, σ_d = pre-entry
  60-session daily-return SD.
- **Test:** pooled mean of R, **month-clustered t** on the entry calendar month:
  V = G/(G−1) · Σ_g (Σ_{i∈g}(R_i − mean))² / n², t = mean/√V.
- **Required:** mean excess over the EW liquid book (true-ADV20 ≥ Rp 10bn at entry, total
  return, same window, last-bar rule) > 0; excess = R − book.
- **Pass bar:** mean R > 0 **and** t ≥ **3.2978** (exact `bar_v2.e_max_abs_z(609)` =
  3.29775843984798) at **N = 609** = 608 after D-078 (605 + HYP-PM-0017's 2 arms +
  HYP-PM-0019's 1 arm) + THIS arm. Re-verified at G0; D-074's stale 602/3.2945 is superseded.
- **Report only (defined, frozen; never run):** acceptance upper bound (adj offer paid on
  paydate, no proration, net of cost); convergence ratio (close(end) − close(entry)) /
  (adj offer − close(entry)); per-event table; 5 worst; splits by `tender_percentage`
  (**cut frozen at ≥ 99% = full — degenerate: the data's max is 90.0, ALL events partial**)
  and by ADV tier (1–10bn vs ≥ 10bn).
- **Mandatory vs voluntary:** **no rule exists** — `event_note` is empty for all 165 rows and
  no stored field classifies; left UNREPORTED per the brief ("don't guess").
- **Falsification clause 2 diagnostics (frozen definitions):** withdrawn-suspect =
  close(tender_end) < 0.90 × min(close(entry), adj offer); proration-suspect =
  `tender_percentage` < 99 (all events, per the data).

## 6. Stop rule (owner, D-074) — FIRED

Fewer than 20 eligible events → **no G1**; this G0 files a descriptive **spread ledger**
instead (pre-entry facts only: `SPREAD_LEDGER.md`). The arm still counts in the census from
registration (X8). Power confirms the stop is right, not just procedural: at n = 12, MDE =
bar × median window-scaled σ / √n = **8.70%**, while the median spread itself is **4.32%** —
even perfect convergence of the median event is undetectable at this n.

## 7. Power conventions (HANDOFF_G0; pre-event only)

Pre-entry daily σ over the 60 sessions before entry (≥ 30 defined returns, bad-print masked,
dividend add-back), scaled by √window-sessions per event. Volatility inside any tender window
is an outcome and is NEVER touched. Optimistic bound = the spread distribution itself (the max
a fully-converging event can earn): median 4.32%, mean 9.63%.

## 8. PIT tests (frozen; all pass at G0 — 8/8)

(a) truncation: pre-event facts identical when every bar after the entry is deleted;
(b) entry = last session strictly before `tender_start` (start tested on a Saturday); exit =
last session on or before `tender_end` (end tested on a Saturday);
(c) a synthetic 1:2 bonus after `tender_start` rescales the raw offer exactly (202 → 101 at
entry close 100);
(d) exactness: entry 100, end close 103, engineered cost 0.6% → R = +2.4000000000% and EW-book
excess = +1.4000000000% (10 dp);
(e) the dividend add-back uses the ex-date inside (entry, exit] only — never the cum date, the
entry date, or an ex after exit;
(f) `g0_census.py` imports no outcome module (AST) and neither census-path file contains
`pct_change` / `shift(`.

## 9. G0 rule and G1 protocol (moot — stopped)

No return/price after any entry close was computed, printed or stored before this freeze
(D-070 rule 1). Window "lengths" are session COUNTS (calendar facts). G1 would be one run,
`TENDER_G1_APPROVED=1`, snapshot + fingerprint + eligibility re-verified against
`CENSUS_G0.json` BEFORE any outcome (drift → STOP); `g1_run.py` refuses while
`stop_rule.n_eligible < 20`. Any fix after a G1 run is a new, disclosed, re-frozen run.

## 10. Forward recorder (D-074 §3; record only, NOT built)

Every new tender offer is logged at `tender_start` (price, spread, ADV) and at `tender_end`
(convergence). First case: **DOOH**, offer 148, window 2026-10-05 → 11-03 (excluded from the
historical population as unsettled, with MBSS/NAYZ/SUPR). Spec in HANDOFF_G0; it would live
beside the D-064 ex-date monitor lineage (`scripts/check_issuance_windows.py`, cron 09:45).
Owner-gated.

## Governance (draft, do not file)

Registration HYP-PM-0018 in {SE} slot 2; the D-entry (expected D-079) records the STOP, not a
G1. HYPOTHESIS_REGISTRY.md, FAILURE_REGISTRY.md and DECISION_LOG.md are NOT edited by this
branch.
