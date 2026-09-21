# FWD-PM-TREND-001 — PROTOCOL (DRAFT — PREMISE FALSIFIED, v6 FINAL: −6.1%, Sharpe −0.17; WITHDRAWN AS BIG-CAP SPEC)

**Status:** DRAFT, **premise falsified by its own frozen spec (§1, v3).** Do not register
in its present form. Retained as the audit record of the pre-registration process.
**Not registered. No family slot consumed. Not open.**
Second-member candidate for the P-M · **Price-Trend {T1}** family (1st member: HYP-PM-0010).
Registration into the family requires an Owner/CRO act (PG-3/OS-10); this document is the
completed pre-registration package for that act and freezes the spec NOW, before any forward
observation, so that forward evidence — if the draft is opened — carries no multiplicity penalty.

**Drafted:** 2026-09-20 · **Spec frozen:** 2026-09-20 v3 (section 2 + `scripts/donchian_backtest.py`, SHA256SUMS)
**In-sample reference run:** 2026-09-20 v3, local settled DB (data through 2026-07-29), output in §1
**Amendment record (all pre-registration era, draft not yet open):**
- **v2 (2026-09-20):** v1's `load()` dropped zero-volume rows upstream, making the traded-days guard a **provable no-op** (`traded20 == 20` for every row — the exact failure class that superseded FWD-PM-REGIME-001; caught in external review of the draft). Windows now span calendar sessions; `volume > 0` required only at the entry check. §1.1.
- **v2.1 (2026-09-20):** membership-restricted split audit added **INET, PYFA** to the hygiene exclusion list — both carried >35% single-session moves inside top-80 membership.
- **v3 (2026-09-20):** **universe membership bug** — v1/v2/v2.1 collapsed monthly top-80 membership into a flat ticker set (`isin`), so a name cracking top-80 in any month kept its **entire history**: 69.5% of v2.1 rows never ranked ≤80 in their own month (median ADV60 of wrongly-included rows Rp3.7bn vs Rp60bn for true members — the effective universe was ~3.8× broader than advertised and only ever grew). v3 restricts membership to the **(month, ticker) pair**. §1.3.
- **v4 (2026-09-20):** window-splice fix (§1.4) — membership gates **entries only**, all windows on the full calendar. BUT v4's aggregation **divided by the held-name count**, an unstated deviation from §2's "remainder cash" sizing, concentrating the book and overstating vol/drawdown (−61.1%, Sharpe −0.82 — artifact).
- **v5 (2026-09-20, SUPERSEDED):** denominator restored to §2 — daily return = sum of held-position returns ÷ **current top-80 member count** (the opportunity set; remainder cash earns zero). Reported −12.0%, CAGR −2.50%, maxDD −20.9%, Sharpe −0.34 — but the position-lag step still leaked across ticker boundaries (§1.5); the number was still an artifact.
- **v6 (2026-09-20, FINAL):** `held = pos.shift(1)` ran on the whole ticker-sorted panel un-grouped, bleeding one ticker's terminal position into the next ticker's first row at every boundary (§1.5) — 29 of 1,047,710 rows, reviewer-verified via 21 impossible held-positions on 2021-07-05, the DB's true start date. Fix: `pos.groupby(d.ticker).shift(1)`, the only line touched. **Final: −6.1%, CAGR −1.23%, maxDD −20.9%, Sharpe −0.17.**

## 0. What this is, and what it is not

This is an **independent replication spec** of the effect already registered as
**HYP-PM-0010** (time-series momentum; forward test FWD-PM-REGIME-002, OPEN).
It is **not** a novel alpha claim. Trend/time-series momentum is documented globally,
and tonight's work found the same effect with a materially different rule set
(Donchian channel vs EMA-slope/ER classifier) on an overlapping universe — the
corroborating pattern the program requires before trusting a family.

The session that produced this draft (2026-09-19/20, ZCode adversarial pass) also
**falsified** every chart-pattern level it tested (round numbers, EMA20/VWMA20
support, Fibonacci retracements, third-touch trend-line bounces, intraday
crossing entries) and every short-side inversion of a negative signal. What
survived, twice, in two independent implementations, was long-only trend on the
liquid universe. That asymmetry is the reason this document exists.

## 1. Evidence being pre-registered (IN-SAMPLE, no confirmatory weight)

Three reference runs of the same backtest, quoted in full because the delta IS
the governance story:

| run | spec state | total | CAGR | maxDD | Sharpe | note |
|---|---|---|---|---|---|---|
| exploratory (unguarded, coarse costs) | session draft, **sticky universe** | +63% | +10.1% | −16% | 1.65 | superset universe, no calendar-session guard |
| **v1 (2026-09-20, SUPERSEDED)** | guard present in code but **provably a no-op**; **sticky universe** | +55.1% | +9.05% | −16.2% | 1.55 | delta vs exploratory = costs + 4-ticker exclusion + ±35% mask; guard contributed nothing |
| **v2.1 (SUPERSEDED)** | real guard (428/11,106 blocked); **still sticky universe**; lapsed-member positions silently stopped accruing losses when their rows dropped out | +50.7% | +8.43% | −14.1% | 1.55 | guard real; universe still 69.5% contaminated |
| **v3 (SUPERSEDED)** | true (month, ticker) membership — but membership rows *dropped*: held positions stopped accruing at membership lapse (loss-hiding) and re-entry windows spliced stale rows (up to 554d) | −7.4% | −1.54% | −15.6% | −0.25 | understated: did not count positions through membership lapses |
| **v4 (SUPERSEDED)** | loss-hiding closed, splice closed (windows full-calendar, median 29d) — but aggregation **divided by held-name count** (deviation from §2 sizing) | −61.1% | −17.02% | −71.2% | −0.82 | denominator artifact; book artificially concentrated |
| **v5 (SUPERSEDED)** | v4 logic; denominator = **current top-80 member count** (§2 "remainder cash" honoured) — but `held = pos.shift(1)` was un-grouped, leaking across ticker boundaries (§1.5) | −12.0% | −2.50% | −20.9% | −0.34 | denominator fix correct; position-lag still leaking |
| **v6 (frozen, FINAL)** | v5 logic; position lag grouped by ticker (`pos.groupby(ticker).shift(1)`), closing the boundary leak (§1.5) | **−6.1%** | **−1.23%** | **−20.9%** | **−0.17** | **the honest, all-in result of this spec on true top-80** |

v6 full output:

```
window   : 2021-07-05 -> 2026-07-29  (5.1y, 1216 active days)
total    : -6.1%   CAGR -1.23%
maxDD    : -20.9%   Sharpe -0.17   avg deployment 32.6%
per-day  : mean -0.0043%
universe : 93,919 member-bars, mean 80 names/mo, 293 tickers ever member
guards   : entry signals 31,358 -> guard-blocked 2,788, member-blocked 24,952, taken 3,618
window-span check (entry hh20 windows): median 29d, >40d: 2.07%, max 41d
IHSG same window: ≈ flat, maxDD -41.5%
```

**The frozen v6 run falsifies the draft's premise.** The trend effect claimed
for big caps does not exist on the true rotating top-80: correctly
denominated and correctly lagged, the book is flat-to-negative (−6.1%, Sharpe −0.17) against a
flat index — not a tradeable edge, and nowhere near the +9%/yr the draft was
drafted around. The audit trail also **withdraws the "monotone direction"
claim** made mid-review (that every fix moved the number downward): the
v4 denominator bug moved it sharply down before v5 corrected it back — and
v5 itself was still wrong, in the same direction, for an unrelated reason
(§1.5), only caught because the review did not stop at "FINAL." What
is monotone is only the *level of scrutiny*, not the numbers, and not the
label "FINAL" either. The effect
that survives review lives in the broad-liquid band (ADV60 ≥ Rp1bn, clean
threshold universe, no membership logic: +7.9%/yr, Sharpe 1.08 exploratory),
which is also the universe style of the registered HYP-PM-0010 (adv20 ≥
Rp1e9) — that registration is unaffected by any bug in this chain. Any
successor draft must be scoped to the threshold universe, frozen from
scratch, and must carry v6's structural guarantees: calendar-session
windows, flag-gated membership, positions accrued to exit, an
opportunity-set denominator, and a per-ticker-grouped position lag.

Rule-neighbour robustness quoted in the exploratory session (Donchian 60/20
Sharpe 1.06, MA20>MA60 0.65) was measured on clean *threshold* universes and
therefore stands for the threshold-universe claim; it says nothing about
top-80 membership. Independent corroboration of the family: registered
HYP-PM-0010 backtest +1.26%/trade ex-2025 (t 3.90) on an adv20-threshold
universe.
universe.

### 1.1 The v1→v2 guard bug, recorded rather than buried

v1's `load()` executed `volume > 0` before any rolling computation, so
`traded20` was identically 20 and the `>= 18` threshold could never fire —
reviewer-verified against the live DB (`min=20, max=20, std=0` across 295,534
values). This is the same zero-volume-contamination class that killed
FWD-PM-REGIME-001. v2 keeps all priced sessions; the guard now blocks 428
entries (3.8%), and the guarded estimate drops +55.1% → +50.7% total — i.e.
the contamination was **inflating** the book, the expected direction
(FWD-PM-REGIME-002 found the same on decontamination). LIFE itself — the
registry's contamination case — has zero sessions in the top-80 universe
(excluded by size, not by the broken v1 guard), so v1's headline was
contaminated by lesser names' carried bars, not by LIFE.

### 1.2 Membership-restricted split audit (v2.1; superseded by §1.3 — but its lesson stands)

The v1 hygiene list (4 tickers) came from 3-ticker spot checks generalised to
an all-splits test. v2.1 re-ran the audit **restricted to actual monthly
top-80 membership**: of 19 whole-history-jump candidates, 6 ever sat in the
universe — **INET** (23 months, min rank 10; worst in-universe single-day move
83.3%) and **PYFA** (207.1%) are verified split-artifact class and were
excluded; **BNBR** (36.2%) was unresolved.

### 1.3 The sticky-universe bug (v3), recorded rather than buried

**Post-v3 resolution of §1.2:** the v2.1 audit and the v2.1 build were
answering the membership question differently (audit = month-restricted, build
= sticky ticker set) — which is why re-derivations disagreed (reviewer's
sticky-definition numbers: BNBR −98.1%, PACK −91.7%, COCO −68.3%, ISEA
−58.9%, INET −39.4%). Under v3 the build IS month-restricted, audit and build
agree by construction, and the ±35% position-day mask handles any residual
in-member jump. BNBR's −98.1% session confirms it is a suspension/relisting
artifact, not an ARA trade — item §5.7 stands.

v1/v2/v2.1's `build()` computed the correct per-ticker-month rank and then
collapsed it to a flat set of ticker names — `isin(big)` kept every day of any
ticker that had *ever* cracked top-80, in every month, including years before
qualification. Reviewer-verified against the live DB: 294 eligible tickers vs
an actual mean monthly top-80 of 77.4; 214,282 of 308,201 rows (69.5%) in the
v2.1 universe were ticker-days that did not rank ≤80 that month; their median
ADV60 was Rp3.7bn vs Rp60bn for true members (16× less liquid — precisely the
contamination profile the spec exists to exclude). The tell that was missed at
draft time: the v2.1 universe printed a median ADV60 of Rp11bn, impossible for
a genuine rotating top-80. **Consequence:** the trend effect claimed for
big caps does not exist on them (v3: −7.4%, Sharpe −0.25); it lives in the
broad-liquid band (ADV60 ≥ Rp1bn), consistent with the registered
HYP-PM-0010 universe and with the overlay literature that edges concentrate
away from the most liquid names. Any successor draft starts from the
threshold universe, frozen from scratch.

The v1 hygiene list (4 tickers) came from 3-ticker spot checks generalised to
an all-splits test. v2.1 re-ran the audit **restricted to actual monthly
top-80 membership**: of 19 whole-history-jump candidates, 6 ever sat in the
universe — **INET** (23 months, min rank 10; worst in-universe single-day move
83.3%) and **PYFA** (207.1%) are verified split-artifact class and were
excluded; **BNBR** (36.2%) was unresolved. **Post-v3 resolution:** the v2.1
audit and the v2.1 build were answering the membership question differently
(audit = month-restricted, build = sticky ticker set) — which is why
re-derivations disagreed (reviewer's sticky-definition numbers: BNBR −98.1%,
PACK −91.7%, COCO −68.3%, ISEA −58.9%). Under v3 the build IS month-restricted,
audit and build agree by construction, and the ±35% position-day mask handles
any residual in-member jump. BNBR's −98.1% session (reviewer, sticky
definition) confirms it is a suspension/relisting artifact, not an ARA trade —
item §5.7 stands.

Rule-neighbour robustness (exploratory session): Donchian 20/10 Sharpe 1.08-1.55,
Donchian 60/20 Sharpe 1.06, MA20>MA60 cross Sharpe 0.65 — the family is positive
across parameterisations, not one cell. Independent corroboration: the registered
HYP-PM-0010 backtest (different rule, same family) read +1.26%/trade ex-2025
(t 3.90).

### 1.5 The cross-ticker position-lag leak (v6), recorded rather than buried

v5's position book was built as:

```python
held = pos.shift(1).fillna(0.0)
```

`pos` is a single Series concatenated across the whole panel, sorted
`(ticker, date)` (`load()`'s own sort order). A plain `.shift(1)` walks that
concatenated order, so at every ticker boundary row *n* of the shift is row
*n-1* of the RAW panel — the **last row of the previous ticker**, not
"yesterday" for the current one. Every ticker's first row therefore inherited
whatever position the previous ticker (in sort order) happened to be in on
its own last day of data, for exactly one spurious held-day.

Caught by: 717 of 952 tickers share an identical first date, 2021-07-05 (the
settled DB's true start of history, not a genuine listing date). If the leak
were live, the very first calendar day of the entire dataset would show
held positions — impossible, since `hh20` needs 20 prior bars and is `NaN`
for every ticker's first 19 rows, and `pos` is explicitly zeroed wherever
`hh20` is `NaN`. It wasn't impossible in the v5 output: `held.groupby(date).sum()`
on 2021-07-05 read **21**, not 0. Isolating those rows traced every one to a
ticker's first-ever row inheriting `pos==1` from the immediately-preceding
ticker (alphabetically) in the sort, on whatever date happened to be *that*
ticker's own last row.

Magnitude: 29 of 1,047,710 rows differ between the shipped (ungrouped) shift
and the correct `pos.groupby(d.ticker).shift(1)`. Small in row count, not
small in effect — re-running the full backtest with only that one line
changed moves the headline from v5's −12.0%/Sharpe −0.34 to v6's
**−6.1%/Sharpe −0.17**, roughly a 2× change on the number this document
uses to declare the premise falsified. The direction of the finding
(flat-to-negative on true top-80, no tradeable edge) does not change; the
magnitude quoted throughout §0/§1/the title does.

Fix (v6, the only line touched): `held = pos.groupby(d.ticker).shift(1).fillna(0.0)`.
Verified: `held.groupby(date).sum()` on 2021-07-05 now reads 0.0. This bug
class — a row-order-dependent pandas op (`shift`, `diff`, `pct_change`,
`rolling`) applied to a ticker-sorted panel without an explicit
`.groupby(ticker)` — is distinct from the window-splice and sticky-universe
classes already catalogued in §1.1–§1.3 (those concerned *which rows exist*;
this concerns *row order across entity boundaries*) and should be added to
the standing pre-registration checklist alongside them.

## 2. Frozen specification

| | |
|---|---|
| universe | per calendar month, the **top 80 tickers by trailing ADV60** (60-session mean of close×volume, min_periods 40), ranked once per ticker-month; membership enforced **per (month, ticker) pair** — v3 inner-merge, not a ticker-level set (§1.3); `close >= Rp 50`; `is_final=1` bars only; IHSG excluded |
| hygiene exclusions | tickers with verified unadjusted-split / jump histories excluded from the universe: **TMAS, MLPT, RMKE, RAJA, INET, PYFA** (v2.1, membership-restricted audit §1.2); **BNBR** unresolved (36.2% in-universe session) and covered by the contamination mask pending cause verification |
| **traded-days guard (v2 semantics)** | all priced sessions are retained in the frame — including carried-forward zero-volume bars — so every rolling window spans **calendar sessions**. Entry requires: entry bar `volume > 0`, **`close(t) > max(high, prior 20 calendar sessions)`**, and **≥ 18 of the trailing 20 sessions with `volume > 0`**. Blocking is observable (428 entries blocked in the frozen run) — this is a testable property, not a declaration. |
| signal (entry) | Donchian-20 breakout over calendar sessions, evaluated at the close; **fill at that session's close** (same convention as FWD-PM-REGIME-002) |
| exit | `close(t) < min(low, prior 10 calendar sessions)`; fill at that session's close; no time cap (channel exit is the rule) |
| position return | close-to-close while held, next-session delay applied (signal close t → held from t+1; no look-ahead) — the lag (`pos.shift`) is computed **per ticker** (v6, §1.5); an un-grouped shift bled one ticker's terminal position into the next ticker's first row at every panel boundary in v5 and earlier |
| sizing | **v5 denominator (precise, unchanged in v6):** daily portfolio return = Σ(close-to-close returns of currently held names) ÷ N_members(t), where N_members(t) = that day's top-80 member count. The opportunity set is the denominator; the uninvested remainder earns zero; positions whose membership lapses mid-trade are still counted (you still own them) until their channel exit. |
| costs | **0.30% charged per turn** (entry turn and exit turn) = **0.60% round trip**, the repo cost authority (`engine/exits/costs.py` operator basis). Conservative vs the exploratory session's convention. |
| contamination guard | position-days with a single-session move beyond ±35% are zeroed (suspension/resumption gaps; 4 such histories excluded at universe level) |
| benchmark | IHSG close-to-close; **primary endpoint is excess vs IHSG** |
| multi-leg shorting | **none.** Long-only. The 2026-09 short-selling regulation change was tested and rejected for this spec: short-side trend on the same universe read −1.24%/trade mean (median −3.36%, win 38%) and L/S halved the long Sharpe. |

Frozen implementation: `scripts/donchian_backtest.py` (sha256 in `scripts/SHA256SUMS.txt`).
Section 2 and this file's constants are closed. Any change requires a new dated
superseding entry.

## 3. Endpoint and decision rule

*(derived against the superseded v2.1 reference; after §1.3's v3 result the
premise is falsified and §3/§3.1/§4 are retained as the record of what a
corrected registration would have committed to.)*

**Primary endpoint:** daily portfolio return **minus IHSG same-day return**, aggregated as a
mean with **date-clustered (one-way) standard errors** — the same inference form as
FWD-PM-REGIME-002, at portfolio instead of per-trade grain.

- **24 months:** interim only, no decision.
- **36 months:** PROMOTE requires accumulated excess t > 2.5 **and** positive cumulative excess.
- **60 months:** final. PROMOTE requires t > 3.0.
- **REJECT** at any checkpoint if cumulative excess is below zero, or if the book records
  fewer than 30 completed round trips (dead-signal guard — mirrors the 001 zero-trade failure).

### 3.1 Power / MDE (derived for THIS spec, not inherited)

From the v2.1 frozen run: per-day mean +0.0361%, daily Sharpe **Ŝ = 1.55**.
With date-clustered inference, accumulated t at horizon T years ≈ Ŝ·√T if the
in-sample effect holds exactly:

| checkpoint | t if Ŝ holds | PROMOTE bar | P(confirm) at Ŝ=1.55 | true Sharpe needed for 80% power |
|---|---|---|---|---|
| 24 months | 2.15 | (interim, no decision) | — | — |
| 36 months | 2.63 | t > 2.5 | **≈ 55%** | **1.93** |
| 60 months | 3.40 | t > 3.0 | ≈ 65% | **1.72** |

Stated plainly, per the R2 requirement that the test be capable of failing:
the 36-month confirm bar sits **above** the in-sample point estimate — a true
Sharpe of 1.55 confirms at 36 months barely more often than not, and 80%-power
confirmation requires a true Sharpe ≥ 1.93. The likely failure mode is a
not-confirmed at 36 months with continuation to 60 months; the binding risk
control is therefore the §3 REJECT rule (cumulative excess < 0), not the t
threshold. If the true effect is the overlay-scale Sharpe (~0.9), this test
correctly fails to confirm at both checkpoints.

## 4. Expectations, stated in advance

In-sample: +9.05%/yr CAGR, Sharpe 1.55, maxDD −16.2%, at 32% average deployment
(≈ +28%/yr at full deployment, linearly scaled, with drawdown scaled accordingly).
Excess over IHSG ≈ the portfolio return itself (IHSG ≈ flat over the window).

**Decay haircut, pre-declared:** in-sample discovery, three rules tried (mild selection),
single 5-year regime window. If forward annualised excess runs below **+4%/yr by month 36**,
the in-sample estimate was optimistic or the effect decayed — treat as failure to confirm
even if t does not formally reject.

## 5. Falsification conditions (pre-declared)

1. Cumulative excess < 0 at any checkpoint (§3).
2. Forward Sharpe below ~0.8 at month 36 (underpowered continuation; stop, do not roll).
3. Result concentrated in one calendar year (no year contributing > 60% of total excess).
4. Excess disappears once the zero-volume guard is tightened further in audit.
5. Universe re-derivation against the real IDX80 membership history materially changes
   composition (the ADV60 top-80 is a proxy; if opened, re-verify before first entry).
6. BNBR's 36.2% in-universe session is confirmed to be an unadjusted split rather than a
   real trade — then it joins the exclusion list and the frozen run is re-issued.

## 6. Multiplicity accounting — stated honestly

- The discovery session (2026-09-19/20) ran approximately **20+ exploratory
  specifications** across gap fades, close-at-high filters, overnight ladders,
  S/R break-fail tables, Fibonacci bands, EMA/VWMA touch tests, trend-line touch
  counts, short-side inversions, and exit grids. **All of that counts as
  in-sample search.** This draft is the pre-declared survivor, registered as a
  hypothesis *after* seeing data — it therefore enters with the family's
  multiplicity debt attached, and confirmatory weight comes only from the
  forward test of §3.
- The session also produced one governance-relevant self-catch, recorded in
  §1.1: the v1 traded-days guard was a no-op (upstream `volume > 0` filter),
  found only on external re-verification of the draft. §1's three-run table is
  the audit trail.
- A second governance-relevant self-catch, recorded in §1.5: the v5 run,
  already tagged FINAL, still carried a row-order defect (an un-grouped
  `pos.shift`) that overstated the loss by roughly 2×. Found only because
  external re-verification continued past a "FINAL" label. Both self-catches
  argue for re-verification as a standing step before any draft is treated as
  closed, not only before registration.
- Family placement: Price-Trend {T1} currently has one member (HYP-PM-0010).
  Registering this draft as the second member consumes a family slot and
  requires the Owner act per PG-3/OS-10. Until then this draft is free-era:
  refine or discard at no family cost, but it earns nothing.
- **Open family-scope question for the Owner act:** {T1}'s declared mechanism
  list enumerates "MA slope, Kaufman ER, participation above a MA, ATR-based
  exits." A channel breakout/channel-exit rule is *not* in the enumeration; the
  general clause ("directional trend features derived from OHLCV") plausibly
  covers it, but this draft does not assume the answer — the Owner call at
  registration must state explicitly whether Donchian channel rules are {T1}
  or require a new family.
- Relationship to FWD-PM-REGIME-002: this draft is **replication evidence for
  the already-open test**, and §1 should be cited there as corroboration
  (independent rule set, overlapping universe, same sign, comparable Sharpe).
  It does not amend 002's frozen spec.

## 7. Registration elements (program §5.2 checklist)

| element | value |
|---|---|
| mechanism | time-series momentum / trend continuation in liquid names (Price-Trend); globally documented effect, no IDX-specific anomaly claimed |
| directional prediction | positive daily excess vs IHSG while positioned; positive cumulative excess at every checkpoint |
| null | excess return = 0 |
| scope | IDX big-cap liquid universe (monthly top-80 by ADV60), long-only, settled daily data, long-side only (short leg tested and rejected §2) |
| effect_size_floor | forward annualised excess ≥ +4%/yr at month 36 (§4 haircut); per-day mean > 0 with date-clustered t > 2.5. Power for THIS spec derived in §3.1: 80%-power detection needs true Sharpe ≥ 1.93 at 36 months — the test is capable of failing |
| multiplicity_family | P-M · Price-Trend {T1} — second member **pending Owner act** (this draft consumes no slot) |
| refutation condition, one sentence | if the frozen Donchian 20/10 book on the top-80 universe fails to beat IHSG cumulatively by month 36 or prints Sharpe < 0.8, the trend effect does not replicate out-of-family and this draft dies |

## 8. Limitations, stated rather than buried

1. In-sample discovery with rule selection (3 variants tried); §3 thresholds are the only
   pre-committed inference.
2. Close-fill convention assumes executable closing liquidity; big-cap closes are liquid but
   the model has no slippage beyond the 0.60% round trip.
3. The universe is an ADV60-ranking proxy, not real IDX80 membership history (file exists on
   the production DB: `idx80_membership_history`, 640 rows — §5.5 requires re-derivation
   before first live entry).
4. One 5-year window, one market, one rate regime; the ±35% contamination guard zeroes rather
   than repairs suspension gaps, which understates tail outcomes in both directions.
5. Costs are the repo authority, not broker-quoted; a retail account should re-check before sizing.

## 9. Provenance

- Data: local settled DB `data/walkforward.db`, `ohlcv.is_final=1`, data through 2026-07-29
  (frozen copy; production DB on the Dell carries later backfills — re-run the frozen script
  there before opening).
- Spec script: `scripts/donchian_backtest.py` · SHA256SUMS: `scripts/SHA256SUMS.txt`
- Corroboration target: [[HYP-PM-0010_REGISTERED]] · `../forward_regime/PROTOCOL.md`
  (FWD-PM-REGIME-002, OPEN)
- Session record: ZCode adversarial session 2026-09-20 (replication + falsification sweeps
  summarised in §0/§6)
