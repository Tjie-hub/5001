# DRAFT — D-0xx (number assigned on approval; D-098 went to the tape protocol) · Mechanism proposed: post-earnings announcement drift (consensus anchor → under-reaction)

> **SUPERSEDED 2026-10-23 by `G0_FREEZE_PEAD_2026-10-23.md`** (same directory). Kept unchanged below as the
> 10-15 record. What changed and why: the census moved (HYP-PM-0022 went to D-105, so this arm is HYP-PM-0023 at
> N = 614, bar 3.3001); the 2005–2020 holdout drew only on names liquid in 2025–26 (survivorship), now replaced
> by a KSEI point-in-time universe from 2009-04; the earnings file is re-fetched for that universe and pinned
> by sha256; the effect floor and minimum power are frozen; and data checks plus distinctness measures were added.

**Status of this file:** DRAFT for the owner. Nothing is appended to `DECISION_LOG.md`, nothing is registered,
no G0 has run, and **no post-event return has been read**. Census stays at 612.
**Origin:** owner 2026-10-15 "Go PEAD", after a screen of the SetupAlpha "60+ market edges" list against the
5001 record: PEAD was the only edge that applies to IDX, has strong prior evidence elsewhere, and has not been
tested here.

---

### D-0xx · Mechanism proposed: post-earnings announcement drift (consensus anchor → under-reaction)
**Status:** DRAFT · **Date:** 2026-10-15 · **Type:** Mechanism acceptance (D-070 §1) ·
**Approval authority:** Owner (pending). Mechanism only: no G0 has run, nothing is registered, census stays 612.

- **Mechanism: under-reaction to a quantified surprise against a salient anchor (M5.2, with I10 as rival).**
  - Quarterly earnings are compared with a public anchor, the analyst consensus. Participants revise their
    beliefs only partly toward the reported number, so the price adjusts partly on the announcement and the
    rest arrives as drift in the direction of the surprise (Ball and Brown 1968; Bernard and Thomas 1989;
    anchoring account: Hirshleifer, Lim and Teoh 2009; attention account: DellaVigna and Pollet 2009).
  - **Participant class (R9):** domestic retail and local mutual funds, which dominate IDX turnover outside the
    largest names and react to headlines more than to the number versus consensus. **Why unarbitraged:**
    IDX has no practical single-stock short selling, so the negative half cannot be traded; the long half
    competes with transaction costs (0.60% round trip, D-082) and with the thin analyst coverage of most names.
  - **Pre-declared sign: positive surprise → positive excess return after the announcement; negative → negative.**
    A flat or opposite result is not rescued.
  - **Two rival originations, declared now and separated by a pre-declared test, not by the drift itself.**
    M5.2 (anchoring) predicts drift scaled by the surprise against the consensus. I10 (limited attention)
    predicts drift concentrated in low-coverage names **and its own decay over the sample** (taxonomy I10: a
    stable effect over 2005–2026 refutes the attention origination even if it confirms the effect). The decay
    slope is therefore a **mandatory, pre-declared secondary**, reported with its sign.
  - **Known competing explanations:** risk compensation for post-event uncertainty; slow adjustment through
    friction (M3.1, illiquid names); gradual information arrival (M2.2). Controls below.
- **Instrument (measurable; defined before any outcome).**
  - Source: Yahoo Finance earnings calendar per ticker (announcement timestamp, reported EPS, consensus EPS),
    fetched 2026-10-15 for the 274 names with average traded value ≥ Rp 5bn since 2025
    (`~/scratch/pead_g0/fetch_earnings_dates.py`, `earnings_dates.json`). Prices: 5001 `ohlcv` from 2021-07,
    the research pre-2021 panel (`forward_volex/remeasure/work/hist_pre2021.pkl`, adjusted) before that.
  - **Surprise:** `SUE = (reported EPS − consensus EPS) / price` at the close two sessions before the
    announcement. Price-scaled, because Yahoo's surprise % divides by |consensus| and explodes near zero.
  - **Event day:** the timestamp converted to WIB; before 16:00 → that session, after → the next session.
  - **Date check (volume only, no returns read):** on 758 events since 2021-07, the median volume ratio is
    1.3–1.6× on the event session and 25–35% of events trade ≥ 2× their 20-day median, so the dates are real
    but appear to carry ±1 session of error (pre-open stamps peak on the session after). **Design response:**
    the drift window starts after event day +1, so a one-session date error cannot leak the announcement
    reaction into the drift.
- **Feasibility gate (counts only).**

  | era | events | tickers | distinct dates | distinct months |
  |---|---|---|---|---|
  | 2005–2020 (pre-2021, holdout) | 1,937 | 67 | 925 | 172 |
  | 2021-07 → 2026-10 (5001 era) | 778 | 58 | 358 | 57 |
  | all, 2005 → 2026-10 | 2,786 | 87 | — | — |

  The top 10 announcement months hold 13% of events. 75 of the 87 covered names are in the pre-2021 panel.
  Coverage is the **analyst-covered** large and mid caps only (87 of 274 liquid names); the low-coverage names
  where I10 predicts the strongest drift have no consensus and are **outside this instrument**, a stated limit.
- **Design constraints for the G0.**
  - **Primary outcome:** for the top SUE quintile (formed within each calendar quarter, so no future surprise
    sets the cut), the return from the **close of event day +1** to the **close of event day +60** sessions,
    **net of 0.60%**, minus the same-window equal-weight return of the liquid cross-section. **Long side only**:
    IDX cannot short single stocks, so only the long leg is tradeable. The bottom quintile and the top-minus-
    bottom spread are pre-declared secondaries reported with their signs.
  - **Horizon:** 60 sessions primary; 20 and 120 sessions are not run unless the primary passes.
  - **Inference:** clustered by announcement month (events bunch at the IDX filing deadlines).
  - **Holdout:** the quintile rule has no tuned threshold. The primary is judged on **2005–2020 and
    2021–2026 separately**, and must hold in both with the same sign (the D-070 era-flip test, available here).
  - **Decay test (I10):** the slope of the yearly effect over 2005–2026, reported with its sign.
  - **Distinctness, shown before any outcome:** against 52-week-high momentum (factor zoo; the only survivor),
    the volatility exclusion (VOLEX-001), price trend {T1} (HYP-PM-0010) and size (which was reversed on IDX).
    The claim is the surprise increment over these, not drift in general.
- **Power: likely to be the binding constraint, stated now.**
  - Rough pre-outcome arithmetic (assumption, to be measured at G0 from the pre-event distribution, not from
    event outcomes): ~550 top-quintile events, a 60-session excess-return sd of about 15–20%, and ~230 clusters
    give a standard error of roughly 1–1.3%, a minimum detectable effect of about 4–5% at the census bar.
    PEAD estimates for the long leg in developed markets are around 1–3% over 60 days.
  - The **D-086 stop rule applies** (effect floor and 20% minimum power frozen before power is computed). If
    it fires, the arm is WITHDRAWN before registration and uncounted, as in D-094 and D-097.
- **Family and census.** Proposed as a new family **Earnings-Information {EI}** (M5.2 / I10), opened only at
  first registration (D-028, PG-3). The census stays at **612**; it counts only at registration (next id
  HYP-PM-0022, N = 613, bar 3.2996).
- **Source caveats.** Yahoo's EPS and consensus are not guaranteed point-in-time (restatements, revised
  consensus). This biases toward cleaner surprises than were tradeable; it is a limit of any result, not
  correctable without a vendor PIT database (same limit as the factor-zoo fundamentals addendum).

**Amendment.** Only by a superseding D-entry.
