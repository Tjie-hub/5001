# PREDECLARATION: retail ownership (KSEI) {OC}, A1 level + A2 flow. G0 freeze

**Status:** frozen before any outcome is read · **Date:** 2026-10-09
**Authority:** **D-083** (mechanism accepted; owner 2026-10-09: "Yes, run it"). The study is run by the
planner (Claude), not ZCode, at the owner's request.
**Branch:** `research/retail-ownership-2026-10` from hardening `a8d6a20`, in a new worktree.
**Gates:**
- **G0** = this freeze, a counts-only census and the PIT tests. Then STOP.
- **G1** = one run, only after owner approval. It is machine-gated on `OC_G1_APPROVED=1`.
- Any fix after G1 is a new, disclosed, re-frozen run.

**The sha256 sidecar (`PREDECLARATION.sha256`)** covers this file, `ownership.py`, `outcomes.py`,
`g0_census.py`, `g1_run.py`, `cost_realised.py`, `test_pit_ownership.py`, `ksei_manifest.json`,
`fetch_ksei.sh` and `parse_ksei.py`.

## 1. Question

Do IDX stocks held mostly by individual investors, or gaining individual holders, underperform
afterwards? The mechanism (D-083) is clientele demand: retail lottery-like demand overprices the stocks
it concentrates in (Kumar 2009; Han and Kumar 2013).

**Honest prior:** the median individual share doubled from 2016 to 2026. An era split is plausible, and
so is a NULL.

## 2. Data and provenance (frozen)

- **KSEI holdings:**
  - Source: the public month-end holding composition, `BalanceposEfekYYYYMMDD.zip`.
  - Coverage: 211 files, 2009-03-31 → 2026-09-30, with no gaps.
  - Hashes: the zip set's manifest sha256 is `ae06e4a2…` (`ksei_manifest.json`), and the parsed CSV's
    is `38c8a90b…`.
  - Fields: EQUITY rows only, giving listed shares, then local/foreign × {IS, CP, PF, IB, ID, MF, SC,
    FD, OT}.
  - Checks: the per-type sums equal the totals in every row.
- **Prices:** `history_long ohlcv_long`, snapshot `7d298068…`, the same panel as the stress G0.
  - Before 2021-07-05 it is yfinance-derived and split-adjusted. After that it is appended from
    walkforward `ohlcv` with `is_final = 1`.
- **Corporate actions and minute volume:** walkforward snapshot `a2d7e675…`.
- **Returns are total returns by add-back:** `(close + dividend on its ex-date) / previous close − 1`.
  The dividend is the IDR cash value, already scaled to the stored basis (verified in the stress G0).
- **True-rupiah ADV20:** the mean of `close × f_cum × volume` over the 20 bars ending at the formation
  session.
  - **Volume basis (D-081):** bars from 2026-07-06 use regular-market volume, `(max buy_lot + max
    sell_lot) × 100` from `stockbit_flow_bars`, for 40,698 bars.
  - Where no minute bars exist, the ohlcv volume is kept: **5,652 bars, disclosed**.
- **Guards:**
  - A daily |return| > 35% is a bad print, and the name drops from that month.
  - FORU is excluded from 2026-09-14 (D-063).

## 3. Formation calendar (PIT, frozen)

- **Rule:** file M (dated D_M) is used at the close of the **5th panel session strictly after D_M**
  (K_M).
- **Late stamps:** if the file's zip timestamp is on or after that session, K_M moves to the first
  session strictly after the stamp. This happened 4 of 210 times, so every formation now follows its
  stamp.
- **Holding period:** close K_M → close K_{M+1}, monthly and non-overlapping.
- **Testable months:** 209, from 2009-04-07 → 2026-08-07 (the last file has no next formation).

## 4. Universe at K_M (pre-outcome)

A name is included if all of these hold:
- it is a KSEI EQUITY row with a custodied total > 0
- it has a price bar at K_M
- **true ADV20 ≥ Rp 1bn**
- close ≥ Rp 50
- it has ≥ 252 bars of history

Census: median 150 names, min 61, max 503.

## 5. Signals (frozen)

- **A1 level:** `s = (L_ID + F_ID) / (L_total + F_total)`, the individual share of **custodied**
  shares.
  - The denominator choice was made at G0, before any outcome.
  - Custodied shares are the dematerialised, tradable float. The listed total includes scrip and
    controller stakes outside KSEI accounts: the median custody ratio is 0.84, and p10 is 0.21.
  - The listed-shares variant correlates at Spearman 0.856 and is **report-only**.
- **A2 flow:** `ds = s_M − s_{M−1}`, which requires the name in both files.
- **Quintiles:** Q1 = lowest, Q5 = highest. k = n // 5, with ties broken by (value, ticker).

## 6. Outcome and test (G1 only)

- **Net spread per month:** `S = EW(Q1) − EW(Q5) − c(Q1) − c(Q5)`.
  - Leg cost c = turnover × the mean member round trip.
  - The round trip is `cost_realised.d059_cost_realised(ADV20, σ60, "normal", q = Rp 100m)` (D-082,
    sha256 `65051253…`).
  - Turnover = 1 − |overlap with the previous month's leg| / |leg|, and 1 at an arm's first formation.
- **Prediction:** S > 0 for both arms (high retail share and retail inflow underperform).
- **Pass, per arm (all must hold):**
  1. **Strength:** mean S > 0 **and** Newey-West t (3 lags) ≥ **bar 3.2987**.
     - The bar is `bar_v2.e_max_abs_z(611)`, exact 3.298685.
     - N = the census ledger of 609 (after D-080) + these 2 arms. Re-verify at G1.
  2. **Both halves > 0:** formations ≤ 2017-12-31 (105 months) and after (104).
  3. **Incremental over VOLEX:** a monthly Fama-MacBeth regression of the name's holding return on
     z(signal), z(log size), z(Parkinson-60), z(12-1 momentum) and a VOLEX flag (top decile of
     Parkinson-60 in the universe).
     - The signal coefficient must have mean < 0 **and** NW t ≤ −2.0.
     - Size = listed shares × close × f_cum.
- **Report only (cannot rescue a failed arm):**
  - the gross spread
  - the avoidance book: EW universe without Q5, minus the EW universe
  - the listed-denominator A1
  - per-year means
  - counts of bad and stale names and of cost σ fallbacks (σ60 missing → 3%)

## 7. Power (pre-sample only)

- **σ of a random-quintile long-short monthly spread:** 5.876%. This is from 64 pseudo-months,
  2002-01 → 2009-04-06, before the first formation, using the same universe filters and no KSEI signal.
- **MDE at 80% power and the bar:** (3.2987 + 0.8416) × 5.876% / √209 = **1.68% a month**. This is
  optimistic, because it ignores the Newey-West inflation.
  - Retail-clientele effects in the literature are about 0.5–1% a month, so a real but
    literature-sized effect could fail the bar. That risk is stated now.

## 8. PIT tests (at G0; all pass)

`test_pit_ownership.py`, 7 tests, hermetic:
- (a) `ownership.py` and `g0_census.py` never import `outcomes` (AST)
- (b) the known session is the 5th session after the file date
- (c) the cross-section is identical when the panel is truncated at K_M
- (d) a synthetic name return compounds exactly
- (e) the dividend is added back on the ex-date only, never when the window starts at the ex-date close
- (f) a synthetic `run_arm` reproduces the gross and net spread with the cost formula
- (g) the turnover cost scales with overlap
- (h) N = 611 and the bar is 3.2987

The census reads no return after any formation. Its only returns are the pre-sample power sorts, and
those hard-assert they end before the first formation.

## 9. Conflicts and disclosures

- The brief (`ZCODE_BRIEF_RETAIL_OWNERSHIP_KSEI_G0_2026-10-09.md`) proposed this design. D-083 and this
  file supersede it where they differ:
  - the formation stamp rule (§3) is new
  - 5,652 post-break bars keep consolidated volume where no minute bars exist
- 45,621 KSEI rows have no price bar at K_M: unlisted, suspended or outside `history_long`. They are
  counted and dropped.
