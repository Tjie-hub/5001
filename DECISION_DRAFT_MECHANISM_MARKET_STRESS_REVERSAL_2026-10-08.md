# DECISION_LOG draft: mechanism acceptance for market-stress reversal (liquidity provision) (2026-10-08)

**Status:** DRAFT. Not filed.
**Filing:** append to `docs/roadmap/DECISION_LOG.md` on `ops/hardening-2026-07-10` under the next free number
(expected **D-075**, unless the D-073 G0 registration takes it first).
**Why this entry exists:**
- D-070 §1 admits a new study only after its economic mechanism is accepted in its own D-entry, before G0.
- Price-only reversal on IDX is exhausted and negative. That covers the next-day reversal after a ≥10% fall
  (S1-PM-0006), the 2026-09-17 pattern scan (every mean-reversion arm negative, HYP-PM-0012), the
  exhaustion and "confirmed bottom" grids, the chart-bottom studies, the factor-zoo short-horizon reversal,
  HYP-PM-0001 and HYP-PA-0001.
- The literature locates reversal profit in **liquidity provision to forced sellers**, and finds it largest
  when liquidity is scarce (Nagel 2012, RFS). The one surviving IDX reversal, the big-4 bank 2-ATR climax low
  (HYP-PM-0014, R2), fits that reading.
- This entry tests the mechanism directly, on market-wide stress days.

**Sources:** owner request 2026-10-08. The planner's pre-event facts were computed from **pre-event data
only**: stress-day counts, clustering, cross-section size, pre-event volatility. No return after any stress
day's close was computed.

---

### D-0xx · Mechanism accepted: market-stress reversal (liquidity provision to forced sellers on market-wide stress days)
**Status:** DRAFT · **Type:** Mechanism acceptance (D-070 §1) · no registration, no G0.

**Mechanism.** On a market-wide stress day, selling is driven by balance sheets more than by news:
- margin calls and forced deleveraging
- stop-outs
- foreign outflows and fund redemptions

IDX's structure concentrates this. Retail margin is heavy. Auto-rejection limits (ARB) spread the selling
over sessions. Short selling is barely available, so no natural buyer steps in early.

The stocks that fell most on the stress day fell partly for reasons unrelated to their value. Whoever supplies
liquidity on that day is paid a premium, which shows up as a partial reversal over the following days.
Price-only reversal fails on IDX because most large falls are **not** forced; conditioning on market-wide
stress selects the days when they are.

**Prediction (direction declared).** On a stress day t, the liquid stocks with the largest falls on t
outperform the market over the next 5 sessions, beta-adjusted and net of cost.

**Pre-event facts (planner, 2026-10-08):**
- **Definition used for the counts:** the EW liquid market's return on day t is ≤ −2.5 × its trailing
  250-session standard deviation.
  - Membership: ADV20 ≥ Rp 10bn, known on t−1.
  - The standard deviation is known before t.
- **A fixed threshold is regime-biased.** On 5001's 2021-07+ panel, days ≤ −2.5% number 47, and 30 of them
  are in 2026. The volatility-scaled definition spreads evenly across years.
- **Long panel** (`data/history_long.db`, from 2005; at least 30 liquid names from 2005-01-31):
  - **105 stress days in 63 episodes** (episodes are more than 5 sessions apart), 2007 → 2026
  - Years: 2008: 8 · 2011: 8 · 2013: 10 · 2015: 12 · 2018: 10 · 2020: 13 · 2023: 6 · 2025: 7 · 2026: 11
    · others 1–4
  - At −3σ: 61 days, 41 episodes.
- **5001 panel** (2021-07+): 32 days / 21 episodes at −2.5σ.
- **Liquid names per day:** median 137 (5001 panel); median 70, p10 40 (long panel).
  - The bottom-quintile basket is about 14–27 names.
- **Pre-event σ of the EW liquid market:** 1.34%/day (5001), 1.53%/day (long panel).
- **Power** (planner approximation; the G0 recomputes it from pre-event dispersion only):
  - S1, the cross-sectional basket, 5 sessions, n = 63 episodes: MDE ≈ 0.8–1.3% at a bar of about 3.3.
  - S2, the market-level rebound: MDE ≈ 1.4–2.8%. Underpowered, so it is report-only (see Decision).

**Decision.**
1. Mechanism accepted as liquidity provision under forced selling (D-070 §1: "liquidity" mechanisms).
2. **Design limits for any G0** (the G0 freezes the details):
   - **Event:** the first stress day of each episode, by the −2.5σ rule above.
     - A new episode needs more than 5 sessions without a stress day.
     - Later stress days in an episode are reported, not tested.
   - **One tested arm, S1:**
     - Basket: an equal-weight portfolio of the liquid names in the **bottom quintile of day-t return**.
       Exclude names at ARB with zero volume on t, which can't be bought.
     - Entry: the close of t. Exit: the close of t+5.
     - Outcome: basket return − β × EW liquid market return over the same window, net of the D-059
       modelled cost per name.
       - β is the basket's trailing-250 beta, known before t.
       - Beta adjustment is **required**. Stress-day losers are high-beta, so a market rebound alone would
         flatter a raw excess.
   - **Report only (not tested):**
     - S2: the EW liquid market from the close of t to the close of t+5, minus its trailing-250 mean
       5-session return
     - later-in-episode stress days
     - horizons 1, 10 and 20
   - **Entry-timing check (required):**
     - The stress condition uses day t's close. The G0 must show, from 2025+ minute bars, how often the
       condition already held at the 15:49 pre-close price. This is a pre-event fact.
     - S1 must also be > 0 with entry at the close of **t+1**. An edge that exists only at an unobservable
       close is not tradeable.
   - **Inference:**
     - one observation per episode, so episodes are the independent unit
     - halves: E1 2007 → 2020 (long panel) and E2 2021-07 → (5001 panel); both must be > 0
   - **Controls (required):**
     - (i) Parkinson-60-decile-matched excess, against VOLEX {V}, D-062
     - (ii) excluding the big-4 banks, against HYP-PM-0014 R2
     - (iii) excluding names with an ex-date (dividend, rights, split) inside the window
   - **Data the G0 must state:**
     - `history_long` provenance: source, adjustment, and survivorship (delisted names present or not)
     - the ADV floor in nominal rupiah across 2007–2026
     - the overlap with the VOLEX pre-2021 out-of-sample use of the same panel. That use was a different
       question; disclose it.
3. **Honest prior.**
   - The mechanism is strong in the literature.
   - But IDX's continuation bias is also strong: falls after a ≥10% drop continue, and confirmed bottoms
     were worse.
   - A NULL is likely if IDX stress selling keeps going for days, which ARB makes plausible.
   - A pass that holds in E1 only would be read as decayed.

**Falsification.** Any one of these:
- the S1 beta-adjusted net mean is ≤ 0 or below the frozen bar
- a sign flip across the halves
- positive only at close-t entry and not at close-(t+1) entry
- explained by the Parkinson-matched control (the excess vanishes against the matched book)

**Multiplicity:** see owner choice (a). 1 tested arm.
- The census ledger now stands at **601**: D-071/D-072's 599 plus 2 exploratory arms on 2026-10-08 (the A/D
  "trap" check and the volume-profile swing check).
- So D-073's G0 must freeze at **603** (bar 3.2950), not 601, and D-074's at 604 (3.2954).
- This arm at 605 gives a bar of about **3.2959** if its G0 comes third. Recomputed exactly at G0 (D-071 §2).

**Amendment.** Only by a superseding D-entry.

---

## Owner choices before filing (not part of the entry text)

- **(a) Family.**
  - **Recommendation: widen Price-Reversal {R1, R2} → {R1, R2, R3}** by formal amendment (D-028, as D-066 did
    for R2). The signal is still a price reversal, and HYP-PM-0014 is its closest relative. A new family
    {LP} would look like family-shopping to escape the reversal family's count.
  - Alternative: open **{LP} Liquidity provision** as a new family. Defensible only if the mechanism
    framing, rather than the feature space, is the deciding criterion.
- **(b) Arms.**
  - **Recommendation: S1 only**, with S2 report-only. S2 is underpowered (MDE about 1.4–2.8%), and every
    extra arm raises every later gate's bar.
  - Alternative: test both (2 arms).
- **(c) Stress threshold.**
  - **Recommendation: −2.5σ** (63 episodes).
  - −3σ gives 41 episodes with presumably purer forced selling, but less power. This must be fixed now:
    changing it later is a grid.
- **(d) Order.**
  - Recommendation: its G0 after D-073's (dividends), independent of D-074 (tender offers).

## Planner notes (not part of the entry text)

- **Census correction for the D-073 brief.** `ZCODE_BRIEF_DIVIDEND_CLIENTELE_G0_2026-10-08.md` names 601 /
  3.2940. The brief already says the bar is "recomputed exactly at G0". With the two exploratory arms run
  after it was written, the correct figure is **603 / 3.2950**. Tell ZCode at G0 review.
- **Why the 5-session horizon:** the literature's reversal lives within a week (Nagel 2012), and a single
  horizon avoids a grid. 1/10/20 are report-only.
- **Why beta adjustment is primary:**
  - Stress-day losers are disproportionately high-beta.
  - A raw basket-minus-market excess would mostly measure the market's own rebound times the beta gap.
    That is a market-timing bet, not liquidity provision.
- **Why the first day of each episode:** it gives independent events, and literature effects concentrate there.
  "Buy the second wave" is a different hypothesis.
- The screener audit of 2026-10-08 (production screens vs market) is not counted as an arm. It evaluated
  existing outputs and selected nothing. Owner to confirm.
