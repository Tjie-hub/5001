# BRANCH A — NEW MECHANISM DESIGN AUDIT (post data-gap closure) — 2026-09-14

**Authority:** generated point-in-time record. **Mode:** hypothesis DESIGN / AUDIT ONLY.
**Owner decision document.** Not a registration.

> **ZERO empirical tests. ZERO backtests. ZERO predictive statistics** — no return, IC, t-stat, p-value,
> Sharpe, hit rate or profitability quantity was computed. **ZERO registry changes. ZERO Dataset B changes.
> ZERO production writes.** No family slot consumed, no `g1_config` touched, no terminal verdict created.
> Every database connection used `file:…?mode=ro`.

---

# A. INFORMATION-LOSS MAP — what C3/C7 actually discarded

This is the design constraint. A candidate qualifies only if it draws on a dimension in the right-hand
column.

| Registered test | Grain tested | What it kept | **What it discarded** |
|---|---|---|---|
| **C3** (HYP-PM-0005) breadth surprise | ticker-**day** | count of net-buying vs net-selling brokers → one binary state | broker **identity**; per-broker **magnitudes**; the whole distribution behind the count; **all intraday structure** |
| **C7** (HYP-PM-0006) intensity state | ticker-**day** | `gross/ADV20` → one binary flag at ≥ 2.0 | every distinction between brokers; the **magnitude distribution** either side of 2.0; each broker's **direction**; **all intraday structure** |
| **HYP-PM-0001** (and the HYP-PM-0002 draft) | ticker-**day** | `OFI_day = Σdelta / Σ(buy_lot+sell_lot)` → **one sign** | **335 minute bars per ticker-session** collapsed to one number, then one bit: intraday **timing**, **shape**, front/back-loading, within-day reversal, and the buy/sell split itself |

**Three structural facts follow, and they define the admissible space:**

1. **Every registered P-M test to date is daily-grain.** No registered hypothesis has ever consumed a
   within-session dimension. Intraday sequencing is therefore not merely under-used — it is **untouched**.
2. The instrument that carries it (`stockbit_flow_bars`, aggressor-side, `buy_lot`/`sell_lot` **separate**)
   is **structurally immune** to the accounting identity that voided HYP-PM-0003, BFI-001's primary and C2
   (`FOUR_TEST_IDENTITY_AND_REGISTRY_AUDIT_2026-09-11` Part D.2).
3. **Broker identity and intraday time are in different tables and cannot be crossed** — IDX does not
   disclose broker activity intraday. Any candidate needing "who moved first" is dead on arrival.

---

# B. CANDIDATE MECHANISM MATRIX

| | **A · broker persistence/concentration** | **B · broker coalition/co-activity** | **C · intraday flow sequencing** | **D · flow × price response** | **E · event-conditioned flow** |
|---|---|---|---|---|---|
| **1 Economic mechanism** | informed brokers repeat; concentrated flow moves price | coordinated broker groups act together | **informed execution is back-loaded within the session; late net buying carries more information than early net buying of the same daily size** | strong flow with no price response = absorption | flow conditioned on corporate events |
| **2 Raw information** | `v_d_broker_persistence`, `v_b_concentration` | `v_c_pair_structure` (17,266,207 rows) | **`v_e_minute_sequence` — 77,559,605 frozen minute bars** | `v_f_flow_price` | `v_g_event_flow` |
| **3 What C3/C7 discarded** | broker identity, magnitudes | pair co-activity | **intraday timing/shape** | intraday price-flow alignment | event conditioning |
| **4 Independent?** | **No** | **No** | **Yes** | **No** | **Partly** |
| **11 Capturable long-only?** | plausible | plausible | **YES** | plausible | plausible |
| **17 Already tested?** | **YES — BFI-001 `F4_conc` t=−2.65, `F4_binf` t=+0.086** | **YES — family map N, REJECTED** | **No** | **YES — C8 by definition** | **Partly — band leg = HYP-PM-0008** |
| **Verdict** | **REJECT** | **REJECT** | **ADVANCE** | **REJECT** | **REJECT** |

Rejection reasoning is in §I. Candidate C is specified in full below.

---

# CANDIDATE C — INTRADAY EXECUTION TIMING (the advancing candidate)

### 1 · Economic mechanism

**Informed and size-constrained participants execute progressively and back-load within the session.** A
participant with private information or a large parent order cannot lift the book at the open without
revealing itself and paying impact; it works the order, and its residual demand concentrates into the final
continuous hour, when the closing reference price is forming and liquidity is deepest. Uninformed flow shows
the opposite profile: it is front-loaded, reacting to overnight news at the open.

**Prediction:** conditional on a day being a **net-buying** day, a day whose net buying was **back-loaded**
is followed by higher subsequent return than a day whose net buying of the *same sign* was **front-loaded**.
The daily total is held fixed by construction; only *when* it happened varies.

**Mechanism class:** M2 · information / adverse selection. **Taxonomy entry: I7.**

### 2 · Exact raw information used

`v_e_minute_sequence` — `ticker, trade_date, bar_time, buy_lot, sell_lot, net_value, price, delta` at
1-minute grain, from the frozen store `data/frozen/stockbit-flow-bars-v002/stockbit-flow-bars-v002.db`
(sha256 `fa7f07b3415f4f644d083487db3613eb4c8c568e860f33b6ef43281764b61191`, FROZEN, validation PASSED,
double-verified via two independent hashing code paths).

Only `buy_lot` and `sell_lot` are used for the signal. **`freq` is never read** (forbidden as a
transaction-count denominator). **No broker table is used**, so the broker-DM and counterparty caveats do
not apply.

### 3 · What C3/C7 discarded that this uses

The **within-session distribution** of directional flow. Two ticker-days with identical `gross/ADV20`
(C7's entire input), identical broker counts (C3's entire input) and identical daily net (HYP-PM-0001/0002's
entire input) can sit at opposite extremes of this signal. It is the one dimension that survives all three
prior collapses.

### 4 · Why it is genuinely independent

| Prior test | Its variable | Why C is not it |
|---|---|---|
| C7 intensity | `gross/ADV20`, daily total | C fixes nothing about total size; a late-tilted and an early-tilted day can have identical gross |
| C3 breadth | broker counts | C reads no broker table at all |
| C8 absorption | C7 state ∧ small return | C conditions on flow **timing**, not on price response |
| HYP-PM-0003 | `SUM(lot)` broker net | different instrument; identity-immune; C never constructs an all-broker net |
| HYP-PM-0001 / 0002 | `sign(OFI_day)` | **C conditions on `daily_net > 0` and contrasts *within* that set**, so the daily-direction variable is held constant and cannot explain the contrast |
| HYP-PM-0008 (I1) | price-limit band contact | no band, no OHLCV rule construct |
| BFI-001 `F4_binf` | broker trailing IC | no broker identity |

**Critical-test compliance:** it does not replace C7's threshold, does not split C7 by concentration, does
not substitute a breadth metric, does not re-label C8, does not rescue HYP-PM-0003, does not recreate I1,
and is not a finer grid on any prior mechanism — it is a different **grain**.

### 5 · Observable signal definition (clock-time, grid-robust)

Segments are defined by **clock time**, not bar index, so the Friday grid is handled without a special case
(verified: **all 58 Friday sessions carry 275 bars, all Mon–Thu sessions carry 335** — the difference is the
Friday prayer lunch break, and zero sessions deviate from their weekday's grid):

```
OPEN  segment := bars with 09:00 <= bar_time <= 09:59
LATE  segment := bars with 14:50 <= bar_time <= 15:49     (final continuous hour)

nbuy(seg)   := SUM(buy_lot) - SUM(sell_lot)  over the segment
daily_net   := nbuy over 09:00..15:49        (continuous session only)

POPULATION  := ticker-days with daily_net > 0              # net-buying days only
STATE       := LATE_TILTED  if  nbuy(LATE) / daily_net >= 0.50
               EARLY_TILTED otherwise
```

**The 16:00–16:14 bars are deliberately excluded from every quantity.** They sit after the pre-closing /
closing-auction gap (15:50–15:59) and are a different market mechanism; mixing them into a continuous-session
flow statistic would confound execution timing with auction mechanics.

**The 0.50 threshold is a structural midpoint, not a tuned parameter** — it is the point at which more than
half the day's net buying occurred in the final hour. It is frozen here and may not be varied at execution.

### 6 · PIT requirements

- Formation uses only session-*t* bars, all timestamped within session *t*. No T+1 artifact.
- **Entry reference is `close(t+1)`** — a full session after formation (§11).
- PIT universe declared from `ohlcv` by trailing-60-session median traded value with `shift(1)`; the
  101-ticker Dataset B roster is **not** used, because the intraday asset spans **958 tickers**.
- All timestamps WIB; `bar_time` is exchange local time.

### 7 · Historical coverage

| Fact | Value |
|---|---|
| Frozen minute bars | **77,559,605** |
| Window | 2025-01-02 → 2026-04-27 |
| Sessions | **309** · Tickers | **958** |
| Complete coverage | **99.7031%** (295,143 of 296,022 ticker-days either carry bars or are certified genuinely-empty) |
| Missing ticker-days | 879 — **all on the fixture date 2025-04-14** |
| Dates with zero coverage | **0** |

### 8 · Mandatory exclusions (all pre-declared, all counted)

| # | Exclusion | Size |
|---|---|---|
| X1 | **2025-04-14** — frozen Day-1 regression fixture, never fetched by design | 1 session / 768 ticker-days |
| X2 | **2025-08-04 → 2025-09-17** — minute contradiction zone (OHLCV says traded; both Stockbit endpoints say zero flow and zero bars) | **31 sessions / 20,981 cells** |
| X3 | Non-admitted sessions per `session_calendar.is_admitted = 0` | 3 |
| X4 | `coverage_state != 'BARS'`, or `n_bars` not equal to that weekday's structural grid (335 Mon–Thu / 275 Fri) | counted |
| X5 | Corporate action on *t*, *t+1* or *t+2*; ticker `RAJA`; `close(t) < Rp 100`; PIT liquidity floor unmet | counted |
| X6 | *t, t+1, t+2* not strictly consecutive admitted sessions | counted |

**Effective admitted sample: 309 − 31 − 1 ≈ 277 sessions.** The six production outage dates
(2026-05-18..21, 06-17..19) fall **after** the frozen window's end and do not bind.

### 9 · Primary estimand — ONE test

```
Step 1  For each admitted formation date d with >= 1 LATE_TILTED and >= 1 EARLY_TILTED cell:
            m(d) = mean fwd return of LATE_TILTED cells  -  mean fwd return of EARLY_TILTED cells
        Dates lacking either side are skipped and counted (never zero-filled).

Step 2  theta_primary = mean of the daily series m(d), Newey-West t, lag = 5, two-sided p.

PREDICTION: theta_primary > 0.
```

Daily-series-first aggregation is the program's registered convention (BFI-001 §G/§I; used by both C3 and
C7), and it prevents within-date cross-sectional correlation from inflating the statistic.

**Single cell. Holm at the primary is the identity.** Everything else is non-confirmatory.

### 10 · Horizon

`fwd_return = close(t+2)/close(t+1) - 1`. **Primary k = 1 session, entered at the close(t+1) reference.**
Secondary k ∈ {2,3} reported as robustness only and may never become primary.

### 11 · Capturability — verified mechanically, not assumed

| Required leg | Status | Basis |
|---|---|---|
| Direction of predicted move | **LONG** | the contrast predicts *higher* return for LATE_TILTED; the capture is to buy |
| Short-selling required? | **NO** | the predicted leg is upward; no short exposure anywhere |
| Queue-position dependency | **NONE** | entry is during ordinary continuous trading, not into a one-sided band queue |
| Closing-auction fill required? | **NO** | `close(t+1)` is an *entry reference*, not a required fill; the order can be worked through the whole of session *t+1* |
| Board | ordinary continuous session | no auction-only mechanism involved |
| T+2 settlement | **compatible** | holding ≥ 1 session; no intraday round-trip |
| Formation-to-entry latency | **one full session** | signal completes at 15:49 on *t*; entry anywhere in *t+1* |

**Verdict: CAPTURABLE.** This is the decisive contrast with HYP-PM-0008, whose predicted continuation leg
required shorting (IDX-infeasible) or an ARA queue fill that structurally excludes late arrivals.

**One declared approximation:** realized fill will differ from `close(t+1)`. This is a **cost-model** matter,
reported as `theta_net = theta_primary − 0.006` sensitivity per program convention, **never** as a
statistical verdict.

### 12 · Expected sample structure

~277 admitted sessions × the PIT-eligible cross-section, restricted to `daily_net > 0` days and split into
two states. The estimand is a **daily series of ~277 observations** — the same order as C3's 329, which
produced a *determinate* (not underpowered) null. **No count was computed from the data for this audit.**

### 13 · MDE feasibility (conceptual only — nothing computed)

Feasible in the same class as C3 and C7: a daily-series estimator over ~277 observations against the
program's 0.60% friction bar. At registration the MDE must be declared **ex ante from a stated assumed σ**
(the pattern used in `HYP-PM-0008_SPEC` §11), and a **pre-execution feasibility gate** must specify a
minimum count of qualifying event-days per state, with shortfall terminating the hypothesis as
**RETIRED — UNPOWERED** (a non-failure). No MDE number is asserted here.

### 14 · Multiplicity / family implications — **and this is the candidate's biggest advantage**

The mechanism is **M2 / I7 adverse selection**, which is **already inside P-M's declared family
`{I5, I6, I7, I12}`** (D-028).

> **No new family is required. No multiplicity amendment is required. The D-1 impasse that blocks
> HYP-PM-0008 does not arise.**

Consequences to declare at registration:

- Consumes **P-M slot #3**, permanently (PG-3). The family currently holds two terminal failures
  (HYP-PM-0001 F2, HYP-PM-0003 INVALID-DATA), and registering re-weights both — the honest direction.
- **HYP-PM-0002 (DRAFT) also targets I7 on this instrument.** It remains DRAFT and consumes no slot, but
  the overlap must be recorded, and the `daily_net > 0` conditioning (§4) is what keeps this test
  orthogonal to HYP-PM-0002's variable rather than a re-cut of it.

### 15 · Leakage risks

| Risk | Treatment |
|---|---|
| Auction/post-close contamination | 16:00–16:14 bars excluded from every quantity (§5) |
| Friday grid | segments defined by clock time; grid verified 275 Fri / 335 Mon–Thu with zero deviation |
| Contradiction zone masquerading as low flow | X2 excludes all 31 sessions |
| Fixture date | X1 |
| Corporate actions / adjustment basis | X5; note 139/959 tickers carry an in-place adjustment with no CA row |
| Survivorship | PIT liquidity-floor universe with `shift(1)`; no roster look-ahead |
| **Vendor revision (the live one)** | The frozen store fixes *reproducibility* but the original capture had no raw-response archive or retrieval timestamps. Whether a bar could have been **revised by the vendor after session t** is **unresolved** — see §H |
| `freq` | never read |
| PPK / board | unidentifiable (B4 open); mitigated but **not solved** by the liquidity floor — must be declared as a limitation |

### 16 · Failure / kill rule (one sentence)

> **If `theta_primary` is not positive with two-sided p < 0.05 under the §9 specification, the hypothesis
> that within-session back-loading of net buying carries information beyond the daily total is refuted, and
> the hypothesis terminates as FAILED (mode F2 · prediction failure).**

### 17 · Has this been tested under another name? **No.**

Checked against all 21 objects in the master inventory: HYP-PM-0001/0002/0003, C1a/C1b/C2/C3/C7/C8,
BFI-001 and its 14 cells, LIT-001/002, H1/H6, HLIQ, NR7/P0, HYP-PA-0001, S2-PM-0004, and the legacy
falsified strategies. **No object uses a within-session dimension.** The nearest neighbours —
HYP-PM-0001 and the HYP-PM-0002 draft — consume the same table but reduce it to a daily scalar, which is
precisely the information this candidate recovers.

---

# C. INDEPENDENCE ASSESSMENT (summary)

| Axis | Candidate C |
|---|---|
| Instrument | vendor aggressor-side intraday — **identity-immune**, disjoint from the broker tables |
| Grain | **within-session** — no registered test has ever used it |
| Variable | timing distribution **conditional on** daily direction ⇒ orthogonal by construction to `sign(OFI_day)` |
| Family | I7, already declared — no new denominator |
| Evidence overlap | none: no prior result, null or otherwise, has been produced on this dimension |

---

# D. DATA / PIT / CAPTURE ASSESSMENT

| Dimension | Status |
|---|---|
| Content completeness | **STRONG** — 99.70% coverage, 0 zero-coverage dates, defect set fully enumerated |
| Structural integrity | **STRONG** — weekday grid exact (335/275), zero deviations |
| Reproducibility | **STRONG** — frozen store, sha256 double-verified, MANIFEST with integrity check |
| **Original-capture PIT** | **WEAK — the one material caveat.** The production source used `INSERT OR REPLACE` with no raw payload and no retrieval timestamp; vendor post-hoc revision cannot be excluded from held evidence |
| Exclusions | **ENUMERATED AND BOUNDED** — 32 sessions total, every one named |
| Prospective capture | **BUILT, NOT ACTIVATED** |

---

# E. CAPTURABILITY ASSESSMENT

Candidate C is the **only** candidate in this audit whose predicted leg is both directionally long and
mechanically reachable without a queue-position assumption. It requires: no shorting, no band-queue fill, no
closing-auction execution, no order-book visibility, and no intraday round-trip. Every one of those is a leg
that HYP-PM-0008 or a price-limit design cannot satisfy.

**The residual execution assumption is a slippage approximation, not a structural impossibility** — which is
the categorical difference between "costly" and "not capturable."

---

# F. RECOMMENDED CANDIDATE

## **Candidate C — Intraday Execution Timing (I7, P-M family)**

It is the only candidate that simultaneously (i) draws on a dimension all prior registered tests provably
discarded, (ii) uses an identity-immune instrument, (iii) has a long-only capturable leg, (iv) needs **no new
family and no multiplicity amendment**, and (v) has never been tested under any name.

---

# G. EXACT REGISTRATION REQUIREMENTS (if the Owner proceeds)

1. **A dated registration document** freezing: mechanism, population, PIT universe, segment clock-time
   definitions, the 0.50 threshold, `daily_net > 0` conditioning, exclusions X1–X6, the single primary
   estimand, horizon k=1, entry reference `close(t+1)`, inference (NW lag 5), multiplicity (single cell),
   cost convention, missing-data rule, kill rule, interpretation rule, no-rescue rule.
2. **An ex-ante MDE with a declared assumed σ**, plus a **pre-execution feasibility gate** (minimum
   qualifying event-days per state) whose shortfall yields **RETIRED — UNPOWERED**, not FAILED.
3. **A declared PIT limitation** on vendor revision (§H item 1), recorded in the registration itself rather
   than discovered afterwards.
4. **A declared B4 limitation** — PPK/board membership remains unidentifiable; the liquidity floor is a
   mitigation, not a solution.
5. **Family declaration**: P-M `{I5,I6,I7,I12}`, slot #3, with the HYP-PM-0002 overlap recorded.
6. Semantic-register gate (D-049) compliance statement — trivial: no all-broker net is constructed.

---

# H. REMAINING OWNER DECISIONS

1. **PIT acceptance (the live one).** The frozen store guarantees reproducibility, not original-capture
   provenance. Choose: **(a)** accept a declared vendor-revision limitation on the historical leg;
   **(b)** activate prospective capture and register a forward-only test, paying a long accrual wait;
   or **(c)** hold the candidate until (b) matures. *This audit takes no position.*
2. **Spend P-M slot #3?** The family holds two terminal failures; registration is permanent and re-weights
   both.
3. **Accept the B4 limitation** (PPK/board unidentifiable) for an intraday-flow population.
4. **Sequencing against HYP-PM-0008**, which remains DRAFT with D-1 and D-3 unresolved. *No recommendation
   is offered here on either.*

---

# I. WHY THE REJECTED CANDIDATES FAIL

**A · broker persistence / concentration — REJECT.** Its two channels are already consumed: BFI-001's
`F4_conc` (CONC, t = −2.65, Holm 0.097 — a *suggestive* secondary, so selecting on it is a textbook post-hoc
rescue) and `F4_binf` (broker trailing informed-IC, t = +0.086 — a clean null; the informed-broker channel
was tested and is flat). The brief additionally bans splitting C7 by broker concentration.

**B · broker coalition / co-activity — REJECT, and this is the most important rejection.**
`v_c_pair_structure`'s 17,266,207 rows are not observed pairs. The view's own catalog note states it is a
**"POTENTIAL-counterparty space: daily data cannot identify which buy broker actually traded with which sell
broker."** The rows are a **cartesian product** of each day's buy-side and sell-side broker lists. A
"coalition" statistic computed on them measures the combinatorics of the product, not coordination.
Independently, family map N already looked for coordination and did not find it (avg pairwise daily tilt
correlation **−0.065**; dominant-broker identity churn **80%/day**). Registering here would risk spending a
permanent slot on an artifact.

**D · flow × price response — REJECT.** "Strong flow, weak price response" **is** C8 absorption by
definition; the brief bans re-labelling it. An intraday version is the same mechanism at finer resolution —
also banned. And C8 is semantically nested inside C7's state space, which is itself a terminal null.

**E · event-conditioned flow — REJECT.** `v_g_event_flow`'s band columns (`band_contact`, `band_regime`,
`band_exceeds`) are HYP-PM-0008/I1 territory — using them recreates a DRAFT hypothesis. The remaining
corporate-action leg is heterogeneous across eight event types (dividend / RUPS / rights / tender /
split / warrant / bonus / reverse), would need its own per-type power argument and its own semantic
validation, and overlaps P-A's declared event-dislocation family. Not refused on merit — refused as
**not yet specifiable as one clean primary test**.

---

# FINAL STATUS

## **ONE REGISTERABLE CANDIDATE**

Candidate C — Intraday Execution Timing — passes the critical test, the capturability test, and the
independence test, and requires no family or multiplicity amendment. **It is not registered, and this audit
does not recommend registering it before the Owner resolves §H item 1 (PIT acceptance).**

# CONFIRMATIONS

- **Empirical tests = 0** · **Backtests = 0** · **Predictive statistics = 0** (no return, IC, t-stat,
  p-value, Sharpe, hit rate or profitability quantity computed)
- **Registry changes = 0** — `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `EXPERIMENT_LEDGER.jsonl`,
  `DECISION_LOG.md` untouched · **no family slot consumed**
- **Dataset B changes = 0** · **Production writes = 0** · **`g1_config` untouched** · **no terminal verdict**
- No threshold tuned against outcomes; the 0.50 split is a structural midpoint and the segment bounds are
  clock-time definitions
- **Files created by this task: 1** — this report
