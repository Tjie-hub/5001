# FWD-PM-TREND-002 — PROTOCOL (DRAFT — IN-SAMPLE EDGE CONCENTRATED IN 2025; NOT REGISTRABLE STANDALONE AS DRAFTED)

**Status:** DRAFT. **Not registered. No family slot consumed. Not open.**
Built as the successor to the withdrawn `FWD-PM-TREND-001` (big-cap top-80 Donchian,
premise falsified, six revisions, withdrawn 2026-09-20 — see `../forward_trend/PROTOCOL_DRAFT.md`).
This document is a **complete audit record**, not a registration request: §1's own evidence
argues against registering this candidate standalone in its current form. Read §6 before
anything else if you are deciding what to do next.

**Drafted:** 2026-09-20 · **Spec frozen:** 2026-09-20 v1 (section 2 + `scripts/donchian2_broad.py`, SHA256SUMS)
**In-sample reference run:** 2026-09-20, local settled DB (data through 2026-07-29), output in §1

## 0. What this is, and what it is not

This re-tests the Donchian 20/10 time-series trend rule from `FWD-PM-TREND-001` on the
**broad-liquid threshold universe** (`adv20 >= Rp 1e9`, the same threshold already used by the
registered `HYP-PM-0010` / `FWD-PM-REGIME-002`) instead of the withdrawn spec's top-80 monthly
ranking. `FWD-PM-TREND-001`'s own final conclusion pointed here: "the effect that survives
review lives in the broad-liquid band ... which is also the universe style of the registered
HYP-PM-0010."

**Structural design change, not just a universe swap.** `FWD-PM-TREND-001` went through six
revisions and was withdrawn because three of its six defects (v3 loss-hiding, v4 held-count
denominator, v5/v6 cross-ticker shift leak) were symptoms of one root cause: a continuous daily
portfolio book needs a daily aggregation denominator, and every version of that denominator hid
a bug. This spec has **no daily book**. It measures trade-level events — entry to actual channel
exit, whatever the duration — exactly the convention already registered for `HYP-PM-0010`
(excess vs IHSG over the identical window, aggregated as a mean with one-way
entry-date-clustered standard errors). There is no daily aggregation to get wrong, and no
membership table to go stale (the universe is a per-row threshold, not a monthly ranking — the
sticky-universe bug class is structurally impossible here). Position state is built via an
explicit per-ticker sequential scan, not a vectorised shift, specifically because that vectorised
shift was `FWD-PM-TREND-001` v5's defect.

**It is not a novel alpha claim.** Same rule family as `HYP-PM-0010` (time-series/channel trend),
independent replication logic, same universe style. What is new here is testing the *raw,
regime-unconditional* rule — `HYP-PM-0010` gates entries on an EMA-slope/efficiency-ratio/
participation regime classifier; this spec takes every Donchian-20 breakout in the liquid
universe with no regime filter at all.

## 1. Evidence being pre-registered (IN-SAMPLE, no confirmatory weight)

Full-sample the result looks like a real edge. It is not robust to a one-year exclusion, and
that failure has a coherent, boring explanation rather than a mysterious one — see below.

```
FWD-PM-TREND-002 frozen event study v1 (DRAFT, in-sample reference)
universe : adv20>=Rp1e9 threshold (not membership), 952 tickers loaded, 378,851 liquid ticker-days
trades   : 4,542 raw -> 34 contaminated (excluded) -> 4,508 used; 143 still open at data end (censored, excluded)
          726 distinct tickers, 1090 distinct entry dates
          top ticker UNTR = 21 trades (0.5% of total)
          median hold 31d, mean hold 43.8d
vs IHSG  : N=4,508  mean excess +3.55%  cluster-t 4.35
vs EWbook: N=4,508  mean excess +2.59%  cluster-t 3.32
ex-2025 vs IHSG: N=3,444  mean excess +0.83%  cluster-t 1.31
integrity: entry<exit for all trades OK; no hygiene-excluded ticker present OK
```

**Year-by-year (excess vs IHSG, per trade, entry-date year):**

| year | N trades | mean excess | IHSG full-year return |
|---|---|---|---|
| 2021 | 422 | +3.35% | +9.6% |
| 2022 | 895 | +0.38% | +2.8% |
| 2023 | 831 | **−1.89%** | +6.2% |
| 2024 | 801 | +3.36% | −3.3% |
| **2025** | **1,064** | **+12.37%** | **+20.7%** |
| 2026 (YTD, through Jul) | 495 | −0.07% | **−30.3%** |

**This is the same "concentrates in and shrinks outside 2025" pattern flagged when
`FWD-PM-TREND-001` was withdrawn**, and it has an unusually clean explanation this time: **2025
was IHSG's strongest year in this whole window (+20.7%), and 2023 was among its weakest years
for a trend system to hold (choppy, +6.2% index but −1.89% mean excess)**. A regime-unconditional
Donchian breakout system mechanically thrives in a sustained trending year and struggles in a
choppy one — that is exactly what a trend-following rule is *supposed* to do, not a red flag on
its own. What it means for THIS document is narrower: the claim "positive excess in every year,
robust on average" does not hold (2023 is meaningfully negative; ex-2025 the pooled estimate is
statistically indistinguishable from zero, t=1.31). 2026 YTD is informative in the same direction
— IHSG fell 30.3% and the system's mean excess was flat (−0.07%), consistent with the
channel-exit rule doing its job (getting out, not shorting) rather than compounding the decline,
but it did not generate a positive edge in a falling market either.

Concentration by name is NOT the problem here (726 distinct tickers, top name 0.5% of trades) —
this is a genuine breadth effect, not a few outlier trades. The problem is concentration by
**calendar year**, which the program has learned to distrust by now (`FWD-PM-TREND-001`'s own
withdrawal text, and `FWD-PM-FADE-001` §5's falsification condition #4, both treat this pattern
as a standing concern).

## 2. Frozen specification

| | |
|---|---|
| universe | **per-row threshold gate**, evaluated independently each session, copied verbatim from the registered `FWD-PM-REGIME-002` protocol for direct comparability: `adv20 >= Rp 1e9` (20-session mean of close×volume, shifted 1, min_periods 15), `close >= Rp 50`, `>= 25` prior sessions, `volume > 0` on the row, `>= 18` of the trailing 20 sessions traded |
| hygiene exclusions | `TMAS, MLPT, RMKE, RAJA, INET, PYFA` — carried from `FWD-PM-TREND-001` §1.2, but that audit was **restricted to top-80 membership**; this broader universe has not had its own dedicated split-continuity audit (§8, limitation 1) |
| signal (entry) | Donchian-20 breakout: `close(t) > max(high, prior 20 calendar sessions)`, windows computed on the **full per-ticker calendar frame**, never dropped before computation; fill at that session's close (matches both `FWD-PM-TREND-001` and `FWD-PM-REGIME-002`'s convention) |
| signal (exit) | `close(t) < min(low, prior 10 calendar sessions)`; fill at that session's close; no time cap — channel exit is the rule, not gated by the liquidity flag (matches `FWD-PM-TREND-001` §2: exits are not membership/liquidity-gated) |
| position construction | **trade-level, not a daily book.** An explicit per-ticker sequential scan pairs each entry with its actual channel exit (or leaves the trade censored if data ends first — 143 such trades, excluded from the endpoint and counted separately). No pyramiding: while a ticker is in a trade, further entry signals on that ticker are ignored until exit. |
| costs | 0.60% round trip, the repo cost authority, applied once per trade |
| contamination guard | a trade is voided if any session in `(entry, exit]` has `|ret| > 35%` or a recorded split — 34 of 4,542 raw trades (0.7%) |
| benchmark, **dual** | (a) IHSG, entered/exited on the identical close-to-close window as the trade — primary, matches `FWD-PM-REGIME-002`'s own endpoint exactly; (b) equal-weight return of every liquidity-eligible name **at entry**, over the identical variable-duration window — secondary, declared because IHSG alone is known generous for liquid names |
| inference | one-way entry-date-clustered t-statistic (`cluster_t`, identical formula to `forward_regime/scripts/panel.py`, reused verbatim) |

Frozen implementation: `scripts/donchian2_broad.py` (sha256 in `scripts/SHA256SUMS.txt`).
Section 2 and this file's constants are closed. Any change requires a new dated superseding entry.

## 3. Endpoint and decision rule (documented for completeness — see §6 before using it)

If this candidate were opened as a standalone forward test on the strength of §1's full-sample
number alone, the endpoint would be: per-trade excess at exit, against both benchmarks, one-way
entry-date-clustered SE, with a **12-month PROMOTE-track bar of t < −2.5 → t > +2.5 on both**
(mirroring the cadence convention used across this program) and REJECT if cumulative excess
turns non-positive against either benchmark. **This section is not a recommendation to open
that test** — §6 explains why the in-sample evidence does not support it standalone.

### 3.1 Power / MDE, for context

At ~1,090 distinct entry dates over 5.1 years (~214/year), a forward window long enough to
accumulate a comparable cluster count to the in-sample ex-2025 read (N≈3,444 trades, ~900
dates) would take several years — and the ex-2025 in-sample estimate itself (t=1.31) is already
below the bar a forward test would need to clear at any checkpoint. Formal power derivation is
not repeated here because §6 recommends against opening this as its own test.

## 4. Expectations, stated in advance

If this were registered standalone: full-sample in-sample excess +3.55%/+2.59% (IHSG/EW-book),
t 4.35/3.32. **Declared in advance, not discovered after the fact:** any forward read should be
expected to land far closer to the ex-2025 number (+0.83%, t 1.31) than the full-sample number,
because the full-sample number is a single trending year away from being the whole result.

## 5. Falsification conditions (pre-declared, for the record)

1. Cumulative excess turns non-positive against either benchmark.
2. A single calendar year contributes more than 60% of total positive excess contribution (2025
   alone is close to this already in the in-sample read — quantify precisely if this is ever
   reopened).
3. Forward performance in a trending year (IHSG full-year return beyond +15%) fails to echo the
   2025 pattern — would argue the 2025 read was noise, not regime-dependence.
4. Forward performance in a choppy/declining year fails to echo 2023's negative or 2026's
   flat-to-negative read — same test in the other direction.

## 6. Why this is not recommended for standalone registration, and what it IS evidence for

**Not recommended standalone.** The program's own registration bar (§5.2, reused from every
other spec here) requires "positive daily excess ... positive cumulative excess at every
checkpoint." One of six years in this window (2023) is meaningfully negative, and the pooled
ex-2025 estimate is statistically indistinguishable from zero. A candidate whose entire in-sample
case rests on one unusually strong trending year does not meet that bar, however clean the
underlying construction is (and §2's construction is clean — every bug class from
`FWD-PM-TREND-001`'s audit trail was designed out from the start, not patched in after the fact).

**What it IS evidence for:** `HYP-PM-0010` already gates entries on an EMA-slope/efficiency-ratio/
participation regime classifier — i.e., it already tries to detect exactly the kind of trending
regime that made 2025 profitable for the raw, unconditional version tested here. This draft's
year-by-year pattern (strong in a trending year, weak-to-negative in a choppy one) is consistent
with — and mildly supportive of — the idea that `HYP-PM-0010`'s regime filter is doing real work,
not just adding noise-cancelling complexity. **This is corroborating context for the
already-registered hypothesis, not a second family member.**

**A natural follow-up, not built here:** re-run this same trade-level Donchian construction but
gated on `HYP-PM-0010`'s own regime flag (only take a Donchian breakout when the regime
classifier is already True) and see whether that removes 2023's negative year and 2026's flat
year while keeping 2025's contribution. That is a genuinely different, well-motivated question —
flagged as a candidate next step, not attempted in this document.

**Multiplicity.** This draft consumes no family slot (not registered) and is not proposed as a
`{T1}` member. If a future draft along the "regime-gated Donchian" line above is built, it would
most naturally be framed as a rule-robustness check *within* `HYP-PM-0010`'s own registered test
rather than a new family member — that framing decision belongs to whoever builds that draft.

## 7. Registration elements (program §5.2 checklist) — completed for the record, not endorsed

| element | value |
|---|---|
| mechanism | time-series/channel trend continuation; regime-unconditional (no filter), unlike the registered `HYP-PM-0010` |
| directional prediction | positive trade-level excess vs IHSG and EW-book |
| null | excess return = 0 |
| scope | IDX liquid universe (`adv20 >= Rp 1e9` threshold), long-only, Donchian 20/10, 2021-07-05 through 2026-07-29 |
| effect_size_floor | **not cleared**: ex-2025 pooled t=1.31, below any registration threshold used elsewhere in this program |
| multiplicity_family | none claimed (§6) |
| refutation condition | already triggered in-sample: one of six years negative, pooled ex-2025 estimate not significant — this is why §6 recommends against opening a forward test on this draft as-is |

## 8. Limitations, stated rather than buried

1. The split-hygiene list (`TMAS, MLPT, RMKE, RAJA, INET, PYFA`) was audited under top-80
   membership only (`FWD-PM-TREND-001` §1.2); this broader threshold universe has not had its
   own dedicated split-continuity audit. The ±35% contamination guard is the only defense
   pending that audit — voided 0.7% of raw trades, consistent with the guard doing real work
   rather than nothing.
2. Close-fill convention (both legs) assumes executable closing liquidity; no slippage modelled
   beyond the flat 0.60% round trip.
3. 143 trades (3.1% of raw) are still open at the data cutoff and were excluded from the
   endpoint as censored, not scored as wins or losses. This is standard event-study practice but
   worth naming: those positions' eventual outcome is unknown.
4. The EW-book benchmark is computed only from names liquid **at entry**; it does not track
   whether those same names stay liquid through a trade's holding window, unlike the trade
   itself (which is intentionally not liquidity-gated after entry, matching §2).
5. One 5.1-year window, one market. The year-by-year read in §1 is the central finding of this
   document, not a footnote — treat it as such before reusing any number from here elsewhere.
6. No sector-level concentration check was run (unlike `FWD-PM-FADE-001`'s year/sector
   falsification condition); ticker-level concentration is clean (§1) but sector concentration in
   the 2025 read specifically is unmeasured.

## 9. Provenance

- Data: local settled DB `data/walkforward.db`, `ohlcv.is_final=1`, data through 2026-07-29.
- Spec script: `scripts/donchian2_broad.py` · SHA256SUMS: `scripts/SHA256SUMS.txt`
- Predecessor: `../forward_trend/PROTOCOL_DRAFT.md` (`FWD-PM-TREND-001`, withdrawn 2026-09-20,
  v6 final) — every structural guarantee in §2 here traces directly to a defect found in that
  document's six-revision audit trail.
- Corroboration target: `../forward_regime/PROTOCOL.md` (`HYP-PM-0010` / `FWD-PM-REGIME-002`,
  REGISTERED, OPEN) — universe, cost basis, traded-days guard, and cluster_t formula copied
  verbatim from that protocol for direct comparability.
- Session record: reviewer-directed build, 2026-09-20 — built as the recommended next step
  after `FWD-PM-TREND-001`'s withdrawal, deliberately designed to be structurally immune to
  that document's bug classes; the design succeeded, but the resulting in-sample evidence does
  not clear the program's registration bar on its own merits (§6).
