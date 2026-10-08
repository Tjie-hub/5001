# PREDECLARATION — market-stress reversal S1 (HYP-PM-0019 draft), G0 freeze

**Status:** frozen before any outcome is read · **Date:** 2026-10-08 ·
**Authority:** **D-075** (mechanism accepted, owner 2026-10-08: "go with recommendations, file
it"; threshold −2.5σ fixed by the owner; arm "S1 only"), brief
`ZCODE_BRIEF_MARKET_STRESS_REVERSAL_G0_2026-10-08.md` (8664856). Where brief and D-entry
disagree, D-075 wins; conflicts are listed in HANDOFF_G0.md.
**Branch:** `research/market-stress-reversal-2026-10` from hardening `8664856`, new worktree.
**Order:** this G0 is BUILT now but SUBMITTED only after HYP-PM-0017's (D-073) G0 is approved
(D-075: "G0 after D-073's (owner)"); the census ledger then fixes the bar (§6).
**Family:** Price-Reversal widened **{R1, R2} → {R1, R2, R3}** by formal amendment at this
registration (D-028, PG-3/PG-6); R3 = market-stress liquidity provision; HYP-PM-0014 is the
closest relative. Two gates: **G0 = this freeze + a counts-only census + PIT tests**, then STOP;
**G1 = one run** after owner approval (machine-gated on `STRESS_G1_APPROVED=1`), then
RESULT/VERDICT/HANDOFF, STOP. Any fix after G1 is a new, disclosed, re-frozen run.
**The sha256 sidecar (`PREDECLARATION.sha256`) covers THIS file, `stress_reversal.py`,
`outcomes.py`, `g0_census.py`, `g1_run.py`, `synthetic.py` and `test_pit_stress_reversal.py`.**

## 1. Question

On a market-wide stress day, is the selling forced (margin calls, stop-outs, foreign outflows,
redemptions) rather than informative — so that liquidity supplied that day earns a premium,
visible as a partial reversal in the names that fell most? Price-only reversal on IDX is
exhausted and negative; the literature (Nagel 2012) places reversal profit in liquidity
provision, largest when liquidity is scarce. Honest prior (D-075): NULL is likely — ARB limits
drag forced selling out over days; a pass in E1 (2007–2020) only reads as decayed.

## 2. Panels and provenance (frozen; full findings in HANDOFF_G0.md)

- **E1** `data/history_long.db::ohlcv_long`, read-only, pinned snapshot
  `7d298068fbc5633277ef0c032ed0257f935c9ef902068b16daa75ac0ba5e5714`
  (events 2007-01-01..2021-06-30). Built by `atr_plan/build_long_db.py`: pre-2021-07-05 from a
  yfinance-derived pickle (split-adjusted, NOT dividend-adjusted; zero-volume stale bars already
  dropped by the builder), 2021-07-05+ appended from walkforward `ohlcv` (sampled overlap rows
  byte-identical). `adj_close` is a COPY of `close`.
- **E2** walkforward `data/walkforward.db::ohlcv` (`COALESCE(is_final,1)=1`), pinned snapshot
  `a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47` (events from 2021-07-01).
- **Returns are total return by add-back:** no panel carries dividend adjustment, so a name's
  day-t return is `(close_t + div_on_t)/close_{t−1} − 1`, div from `corporate_action_events`
  (IDR cash, deduped by `dividend_id`, summed per ex-date, EX date only). The vendor pre-scales
  `dividend_value` to the stored price basis (verified: AKRA 2021-08 = 60 = 300/5 for its
  2022-01 1:5 split; ASRM 2021-07 = 194/4.2 for its 4.2 bonus), so no further scaling applies.
  CA coverage starts 2009: events in 2007–2008 keep price-only legs and are COUNTED.
- **True-rupiah ADV20:** stored closes are split-adjusted to the fetch basis while volume is
  as-traded, so the liquid floor uses `mean(close × f_cum × volume)` over the 20 bars strictly
  before t, f_cum = the product of share-factors of split-class CA rows (stocksplit new/old,
  bonus `stocksplit_factor`, stock_reverse new/old) whose ex-date is AFTER t. Naive-ADV
  (`close × volume`) medians are reported alongside for the planner comparison.
- **Guards:** a name-day with |return| > 35% is a bad print and drops from every return
  aggregation that day; E2 additionally drops a name from the market and basket on a
  split/bonus/reverse/rights ex-date (raw vendor bars); FORU excluded from 2026-09-14 (D-063);
  a member whose window lacks a bar uses the LAST available close and is counted (never
  silently dropped).

## 3. Event (fixed by D-075)

- **Liquid set on day t:** true-ADV20 ≥ Rp 10bn; at least **30** liquid names required.
- **r_m(t)** = equal-weight mean of day-t returns across the liquid set (zero-volume ARB names
  stay in r_m; they are excluded from the BASKET only).
- **σ(t)** = SD of the last **250** DEFINED r_m values strictly before t (≥ **120** required).
- **Stress day:** r_m(t) ≤ **−2.5 × σ(t)** (fixed now, owner).
- **Episode:** a stress day starts a NEW episode iff no stress day occurred in the previous
  **5** panel sessions. **Only the first day of an episode is an event**; later stress days are
  report-only.
- **Overlap gate (pre-event):** both panels' flags are computed over 2021-07..2026-09; if the
  panels disagree on more than **20%** of flagged days, the census STOPS before anything else.

## 4. The arm (exactly one, S1) — G1 only

- **Basket:** liquid names in the **bottom quintile of day-t return** (k = max(1, n // 5);
  ties by (return, ticker)); zero-volume ARB names excluded (counted per event).
- **Entry:** the close of t. **Exit:** the close of t+5 panel sessions.
- **β per member:** OLS slope of the member's daily returns ON r_m over the last 250 DEFINED
  paired sessions strictly before t (≥ 120 required); basket β = the mean of member βs;
  members without enough history take the mean β of the other members (counted).
- **Cost per member (D-059, frozen):** `P-M/cost_liquidity/cost_by_adv.py` @ commit **7e039ee**
  — 0.50% fees + (½ s_entry + ½ s_exit) + 2·σ_d·√(Q/ADV20); s = Abdi-Ranaldo spread over the 21
  sessions ending t−1, floored at one IDX tick; σ_d = the member's daily-return SD over the 60
  sessions before t; Q = Rp 100m (D-059 primary size); ADV20 = the true-rupiah ADV. Basket cost
  = mean of member costs.
- **Outcome per event:** `R = basket − β × EW-liquid-market − cost`, all legs close t →
  close t+5, market leg = day-t membership, total return.
- **Test statistic:** the pooled mean of R over events, `t = mean/sd × √n`. Episodes are the
  independent unit; no clustering.
- **Report only (not tested):** S2 = the EW liquid market over t→t+5 minus its trailing-250
  mean 5-session return; later-in-episode stress days with the same construction; horizons
  1, 10, 20; a per-event table (date, r_m, σ multiple, basket size, β, R); the 5 worst events;
  the ARB-excluded count per event; a year table.

## 5. Pass bar and controls (frozen; all pass conditions must hold)

1. **Strength:** mean R > 0 **and** t ≥ the frozen bar = `bar_v2.e_max_abs_z(N)`:
   - **N = 604 is the expected freeze** (bar exact 3.295375 → **3.2954**): census ledger 601
     (D-075 census note) + HYP-PM-0017's 2 arms, registered at the owner's approval of that G0 —
     the submission gate for this study — + this G0's 1 arm (S1).
   - **N = 605** (bar exact 3.295896 → **3.2959**) applies only if HYP-PM-0018 (D-074, tender
     offers) registers before this one; its G0 is "NOT NOW" per the owner.
   - The final N is re-verified at submission and again at G1 against the ledger rows listed in
     `CENSUS_G0.json: census.ledger_rows_counted` (D-071 §2). Ledger counted: 595 (D-071's nine
     components) + 2 exploratory arms of 2026-10-08 + HYP-PM-0017's 2 arms + this arm.
2. **Both halves > 0:** E1 2007-01 → 2020-12 and E2 2021-07 →. Events from 2021-01..06 sit in
   the pooled test but in NEITHER half and are listed.
3. **Next-day entry > 0:** R with entry at the close of t+1 and exit at the close of t+6.
4. **Not volatility:** the basket's excess over a **Parkinson-60-decile-matched book** is > 0 —
   for each member, the EW of liquid names in its park-60 decile at t (deciles across the
   day's liquid cross-section), window t→t+5, member itself excluded, minus the basket cost.
   This guards the VOLEX {V} overlap (D-062).
- **Reported controls (a sign flip is named in VERDICT but does not fail the arm):** excluding
  the big-4 banks (BBCA, BBRI, BMRI, BBNI — HYP-PM-0014); excluding members with ANY ex-date
  (dividend included) in t−1..t+5.

## 6. Entry-timing pre-check (G0, pre-event, prices only)

From 5001 `stockbit_flow_bars` (2025+), each liquid name's last price at or before **15:49**
against its prior close recomputes r_m at 15:49; the 15:49 flag (`r_m_1549 ≤ −2.5σ(t)`, σ known
at t−1) is compared with the close flag on 2025+ stress days and near-misses (σ-multiple in
[−3.0, −2.0]). Prices only — the known minute-volume under-capture since 2026-07 is irrelevant
here. This answers whether a trader could KNOW at the pre-close; pass condition 3 covers the
case where they cannot.

## 7. Power (HANDOFF_G0; pre-event dispersion only)

Per event: each basket member's daily-return SD over the 60 sessions before t; the stress
multiplier = the day-t cross-sectional SD of the basket over the median member daily SD;
σ_5 = median member daily SD × √5 × median stress multiplier; **MDE = bar × σ_5 / √n** at
n = the pooled event count. Computed per half and pooled in `CENSUS_G0.json: power`.

## 8. PIT tests (frozen; all must pass at G0)

- **(a)** Liquid membership, ADV, σ and r_m at t are identical when every bar AFTER t is
  deleted — the day-t return is the only day-t input.
- **(b)** Episode rule: stress days 3 sessions apart → ONE event; exactly 5 apart → one; 6
  apart → TWO.
- **(c)** The basket quintile uses only liquid names with a valid day-t return; a zero-volume
  ARB name is excluded; an E2 split-day name is dropped.
- **(d)** The frozen assembly reproduces R = 2 − 1.5×1 − 0.6 = **−0.1%** exactly (to 10
  decimal places — the frozen float check; −0.1 has no exact binary representation), and β
  recovers its engineered value on the synthetic member.
- **(e)** The dividend add-back uses the EX date, never the prior session.
- **(f)** The G0 census path never computes a return after the close of t: AST proof that
  `g0_census.py` / `stress_reversal.py` import neither `outcomes` nor any outcome function,
  plus a forbidden-token grep (`pct_change`, `shift`).

## 9. G0 rule and G1 protocol

No return after any stress day's close is computed, printed or stored before G0 approval
(D-070 rule 1; a breach voids the study). Day-t returns are the trigger itself (D-075 allows
them); everything at t+1 or later lives in `outcomes.py`, physically outside the census path.
G1: one run, `STRESS_G1_APPROVED=1`, both snapshots re-hashed against `CENSUS_G0.json` BEFORE
any outcome (drift → STOP), the bar's N re-verified, then RESULT / VERDICT / HANDOFF, STOP.
`g1_run.py --synthetic` may run at any time (fixture market only).
**Forward test (record only, nothing built):** if S1 passes, the forward test is every new
first-day stress episode after the G1 date with the same frozen rules, recorded at t and t+5 —
expect ~3–6 episodes/year, so a verdict takes years; the natural host is a recorder beside the
D-074 tender-offer forward recorder (owner-gated).

**Falsification (D-075, unchanged):** S1 beta-adjusted net mean ≤ 0 or below the frozen bar; a
sign flip across the halves; positive only at close-t entry; explained by the Parkinson-matched
control.

**Governance (draft, do not file):** registration HYP-PM-0019 (HYP-PM-0017 = dividends,
HYP-PM-0018 = tender offers); family Price-Reversal widened to {R1, R2, R3} with the amendment
wording in `REGISTRATION_DRAFT.md`; next free D-number at filing (expected **D-077**).
HYPOTHESIS_REGISTRY.md, FAILURE_REGISTRY.md and DECISION_LOG.md are NOT edited by this branch.
