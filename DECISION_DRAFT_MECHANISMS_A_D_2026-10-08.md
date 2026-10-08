# DECISION_LOG drafts: mechanism acceptance for tender offers (A) and dividend ex-dates (D) (2026-10-08)

**Status:** DRAFT. Not filed.
**Filing:** append to `docs/roadmap/DECISION_LOG.md` on `ops/hardening-2026-07-10`. Use the next free
numbers at filing, expected **D-073** (A) and **D-074** (D).
**Why these entries exist:** D-070 §1 admits a structural-event study only after its economic
mechanism is accepted in its own D-entry before G0. These two entries do that for the pair the owner
accepted from Task 2 (`research/structural-events-feasibility-2026-10` @ `1c20f56`), ranked again by
Task 3 (`research/mechanism-inventory-b-2026-10` @ `571dee3`).
**Sources:**
- ZCode's mechanism drafts in `FEASIBILITY_B_2026-10-07.md` §"Mechanism D-entry drafts".
- Planner additions, 2026-10-08, from **pre-event data only**: the tender spread at the close before
  the offer window, the dividend yield at the close before the cum date, window lengths and month
  counts. No post-event price was read.

**Owner choices before filing:** §"Owner choices" at the end.

---

### D-0xx (A) · Mechanism accepted: tender-offer price floor (arbitrage spread to a contractual price with a deadline)
**Status:** DRAFT · **Type:** Mechanism acceptance (D-070 §1) · no registration, no G0.

**Mechanism.** A tender offer is a public, contractual commitment to buy at a fixed price until a fixed
date (`tender_end`), with payment on `tender_paydate`. While the offer is open, it sets a floor under the
market price. A market price below the offer is therefore an arbitrage spread bounded by deal risk and
the time to payment. It is not a price prediction.

Mandatory offers under the takeover rule (POJK 9/POJK.04/2018) are rarely withdrawn. The spread pays for:
- time value
- the settlement and acceptance friction for retail holders
- proration risk on partial voluntary offers

**Prediction (direction declared).** For events where the offer price is above the market at entry, the
market price converges towards the offer price by `tender_end`. Mean net return is > 0.

**Pre-event facts (planner, 2026-10-08):**
- 165 events. 129 have 20 pre-event bars. All offer prices are stored.
- Most offers sit **below** the market: 67 of 129. Those have no spread and are ineligible.
- Spread ≥ 0.6% at the close before `tender_start`:

  | Liquidity floor (ADV20) | Eligible events | Median spread |
  |---|---:|---:|
  | Rp 10bn | **8** | 7.4% |
  | Rp 1bn | **26** | 3.6% |
  | none | 61 | 5.0% |

- Eligible events: 2021 → 2026 only. The median offer window is 22 sessions (range 4–25).
- **Power, under the feasibility convention** (pre-event σ 2.42%/day, n = 26, bar ≈ 3.29): MDE ≈ 7.5%,
  which is above the median spread.
  - This convention is pessimistic for an arbitrage trade: a price pinned under an offer moves far
    less than its pre-event volatility.
  - But the G0 can't use outcome dispersion. So a G1 would be decided by whether the realised
    dispersion is small, and by any deal-break tail.

**Decision.**
1. The mechanism is accepted as a rule-constraint forced-flow mechanism under D-070 §1.
2. **Design limits for any G0** (the G0 freezes the details):
   - **Population:** offers with a stored `tender_price`, `tender_start` and `tender_end`. ADV20 ≥
     Rp 1bn on the session before `tender_start`. Spread at that close ≥ the 0.60% round trip plus the
     D-059 modelled cost for the name's ADV.
   - **Entry:** that close. The terms are public by `tender_start`.
   - **Outcome: one tested arm.**
     - Market exit at the `tender_end` close, net of the modelled cost.
     - Test statistic: pooled mean with month-clustered t. It must also be > 0 in excess of the EW
       liquid book over the same window.
     - Report only: acceptance at the offer price, paid on `tender_paydate` with no proration. This is
       the upper bound and is not tested.
   - **Stop rule:** if the frozen population has fewer than **20** eligible events, there is no G1. A
     descriptive spread ledger is filed instead.
   - **Report:** a breakdown by mandatory vs voluntary offer and full vs partial offer (`tender_percentage`).
3. **Forward recorder** (no hypothesis, no census arm). Every new offer is logged at `tender_start` with
   its spread, and at `tender_end` with the realised convergence. The live sample starts with DOOH:
   offer 148, window 2026-10-05 → 11-03. This grows n for a later test.
4. **Honest prior:** a small positive mean that doesn't clear the bar at n ≈ 26, or a stop. The
   recorder is the durable output.

**Falsification:**
- Pooled net market-exit return ≤ 0, or below the frozen bar.
- Or the losses concentrate in withdrawn or prorated deals that the rule can't exclude in advance.

**Multiplicity:** family **{SE} Structural-event forced flow** (new; opened at the first registration
per D-028, PG-3). A takes 1 tested arm: census 599 + 1 = **600**, bar **3.2935** if A's G0 is first.
The exact value is computed at G0 (D-071 §2).

**Amendment.** Only by a superseding D-entry.

---

### D-0xx (D) · Mechanism accepted: dividend clientele flow (pre-cum demand, ex-day tax clientele)
**Status:** DRAFT · **Type:** Mechanism acceptance (D-070 §1) · no registration, no G0.

**Mechanism.** The cash dividend is a scheduled event, and the right to it is fixed at the cum date. Two
flows follow from who wants to hold through it.
- **(i) Pre-cum demand.** Yield-seeking and dividend-capture buyers concentrate their purchases before
  the cum date. That is price pressure from demand, not news. This is the "dividend month premium"
  mechanism (Hartzmark & Solomon 2013). It should be stronger in a retail-heavy market.
- **(ii) Ex-day tax clientele.** Dividends are taxed differently by holder:
  - non-residents: 20% withholding (or the treaty rate)
  - resident individuals: 10% final, or exempt if reinvested under the 2021 rules
  - resident corporate holders: different rules again
  - capital gains: a 0.1% tax on sale proceeds

  So the marginal holder values one rupiah of dividend at less than one rupiah of price. The price
  should fall on the ex-date by **less** than the dividend, and buying the cum close and selling the ex
  open should earn the gap.

**Predictions (directions declared).**
- **D1:** positive excess return vs the EW liquid book over the 10 sessions ending at the cum-date close.
- **D2:** positive capture return.
  - Formula: (P_ex open + 0.9 × dividend − P_cum close) / P_cum close − 0.60% round trip, minus the EW
    book's return from the cum close to the ex open.
  - Population: yield ≥ 2% at the close before the cum date.

**Pre-event facts (planner, 2026-10-08):**
- 576 liquid events (ADV20 ≥ Rp 10bn, IDR dividend > 0, 20 pre-bars). Task 2 counted 574.
- Yield at the close before the cum date:

  | p10 | p25 | p50 | p75 | p90 |
  |---:|---:|---:|---:|---:|
  | 0.45% | 1.17% | 2.52% | 5.02% | 8.5% |

  333 events have yield ≥ 2%.
- **Strong seasonal clustering:** 346 of 576 cum dates (60%) fall in May–July, the AGM season.
- **Era:** 560 of 574 liquid events are in 2021-10 or later.
- **Power** (pre-event σ 2.36%/day, bar ≈ 3.29):
  - D1, 10 sessions: MDE ≈ 0.95% treating events as independent, **1.63%** clustered by month.
    That is at or above the literature's effect (about 0.5–1%/month), so a null is likely unless the
    IDX effect is larger.
  - D2, one night, n = 333: MDE ≈ 0.43% independent, roughly 0.7% clustered. This is the
    better-powered arm. Close-to-close σ overstates the overnight gap, so these numbers are pessimistic.

**Decision.**
1. The mechanism is accepted, a forced-flow / clientele mechanism under D-070 §1.
2. **Design limits for any G0** (the G0 freezes the details):
   - **Two tested arms, D1 and D2, and no others.** No horizon or yield grid.
   - **Population:** IDR cash dividends with `dividend_value` > 0 and stored cum and ex dates. Several
     dividends on one cum date are summed. ADV20 ≥ Rp 10bn on the session before the cum date.
     Excluded: events with a split, bonus, reverse split or rights ex-date inside the window.
   - **PIT anchor for D1 (required).** Entry at cum−10 is valid only if the dividend was public by then.
     - Entry = the later of cum−10 and the first session after a PIT announcement anchor.
     - The anchor is the approving AGM (`rups` event) for final dividends. It is `dividend_created` only
       when that date is before the cum date and isn't a backfill artefact. The G0 must show this.
     - Events with no anchor are dropped from D1. They stay in D2, because by the cum-date close the
       dividend is certainly public.
   - **Benchmark:** a **total-return** EW liquid book, with dividends added back on each ex-date.
     5001's bars are raw, so a price-only book would carry every other stock's ex-day drop as a
     negative return.
   - **Inference:**
     - Clustering by event month and repeat ticker (530 multi-event tickers), using
       cluster-robust or month-aggregated t.
     - Halves 2009 → 2023-12 / 2024-01 → must both be > 0.
     - Required control: excess vs a Parkinson-60-decile-matched book. Dividend payers are low-vol, so
       this guards against overlap with VOLEX {V} (D-062).
   - **Report:**
     - by month (AGM season vs the rest)
     - by yield tercile
     - by foreign-ownership proxy, if a PIT one exists. If not, say so.
3. The D-064 ex-date monitor (detection only) continues unchanged.
4. **Honest prior:**
   - D1: likely null (underpowered for a literature-sized effect).
   - D2: the real test of the clientele claim. A positive capture return is plausible, but it may sit
     inside the 0.60% round-trip cost on mid-yield names. Neither result is a trading rule until the
     forward test.

**Falsification:**
- D1 or D2 pooled mean ≤ 0, below the frozen bar, or with a sign flip across the halves.
- **Or D2 positive only gross of the 10% tax, or only in the top yield tercile.** That shows the drop is
  tax-shaped, but the effect isn't economically usable.

**Multiplicity:** family {SE}. D takes 2 tested arms. Census: 600 + 2 = **602** (bar **3.2945**) if A's
G0 goes first; 599 + 2 = **601** (bar **3.2940**) if D's goes first. Computed exactly at G0.

**Amendment.** Only by a superseding D-entry.

---

## Owner choices before filing (not part of the entry text)

- **(a) Which G0 first.**
  - **Recommendation: D first.** It has the power, especially D2, and a clear yes/no.
  - A's G1 is cheap, but its result will be dominated by about 26 events. Its main value is the forward
    recorder, which can start now, alongside D.
- **(b) A: G1 at n ≈ 26, or recorder only.**
  - Recommendation: keep the G1 with the stop rule (< 20 means no G1). It costs one census arm.
  - The alternative: file A as mechanism-accepted with a recorder only, register no hypothesis, and add
    no census arm until n ≥ 50.
- **(c) D2 yield floor: 2%** (n ≈ 333). A 3% floor gives n ≈ 255 with a larger expected gap. This must
  be fixed now, before G0, because changing it later would be a grid.

## Planner notes (not part of the entry text)

- **ZCode's D draft said "direction pre-declared from the tax-clientele split" but never declared one.**
  The entry above declares D1 and D2. The run-up arm also needed the PIT announcement anchor: a cum−10
  entry before the dividend is public would be look-ahead.
- **ZCode's A draft assumed every offer is a floor.** In fact 67 of 129 offers were priced below the
  market (mandatory offers are priced off a 90-day average under the takeover rule, to verify at G0, and often trail the takeover move). Hence
  the spread eligibility rule and the stop rule.
- Both entries are mechanism acceptance only. Registration (HYP-PM-0017/0018, family {SE} opened) is
  done at each G0 approval, as with D-067/D-072.
