# DECISION_LOG draft — close the daily price-pattern search (2026-10-07)

**Status:** DRAFT. The owner approved the direction on 2026-10-07 ("yes, do both").
**Filing:** append to `docs/roadmap/DECISION_LOG.md` on `ops/hardening-2026-07-10` **after the
consolidation merge lands** (so the log isn't edited while ZCode is merging it). Use the next free
number at filing time, expected **D-070**. D-069 is the D-066 collision record. The sniper-filter
registration takes the number after this one.

---

### D-0xx · Daily price-pattern search closed; research redirected to forced-flow, liquidity and risk-premium mechanisms (2026-10-07)

**Context.**

The census now stands at 276 trials, with a deflation bar of about 3.06. Almost every candidate
derived its signal from daily OHLCV shape. All of these came back null, an anti-edge, or an artefact:

- chart and swing patterns: double top, lower highs, staircase bottom, exhaustion, BOS / CHoCH,
  trendline breaks
- breakout and continuation families
- the sniper support-zone entry since 2021
- price-only learning: HYP-PM-0015, FAILED (D-068)
- the exit / position-management practice study: no arm recommended (2026-10-07)

Two patterns recur:
- an **era flip**, where results positive in 2001–2021 fail or reverse in 2021-10..2026
- **low power**: single-pattern event studies with a few hundred events

The only survivors so far are a risk premium (volatility exclusion, FWD-PM-VOLEX-001) and liquidity
provision (bank 2-ATR climax low, HYP-PM-0014, FWD-PM-BANK-001). Both are still in forward test, and
neither predicts a price pattern.

**Decision.**

1. **No new registration, and no new exploratory edge study, whose signal is derived from daily
   OHLCV shape.** This covers chart and swing patterns, breakouts, trendlines, candlesticks,
   indicator thresholds and price-only learning.

   The exception is a study that names a **new economic mechanism**, one that isn't price
   prediction: forced flow, liquidity provision, a risk premium, an institutional or rule
   constraint. That mechanism must be accepted in its own D-entry before G0.

   Price and volume may still be used as **controls, filters or risk measures** inside a
   mechanism-led study.
2. **HYP-PM-0016 (the sniper setup filter, briefed 2026-10-07 before this decision) is the last
   admitted price-feature study.** It is allowed because it filters an existing owner entry rule
   and its pre-registered baseline is a risk measure (low volatility). It counts in {L1} as briefed.
3. **Running forward tests continue unchanged:** VOLEX-001, BANK-001, FADE-001 and REGIME-002. No
   rule changes mid-test (Research Master Plan §3.2e).
4. **Next research direction:** structural events with a forced-flow or rule mechanism. In order:
   - tender offers
   - index reconstitution (IDX80, LQ45 / IDX30 if the history can be sourced)
   - rights issues, if not already covered by {CF} (D-064)
   - dividend ex-dates
   - splits, bonus and reverse splits

   Each starts with a **feasibility gate** (counts, point-in-time dates, power from pre-event
   volatility only, no event outcomes read) before any registration.
5. **Preference for pooled cross-sectional designs** where the mechanism allows them, over
   single-pattern event studies (power).
6. **Owner chart questions** (e.g. "analyze MAPI") may still be answered descriptively. They are not
   edge research and are not tested as such unless a mechanism under (1) is named.

**Multiplicity.**
- Nothing is removed from the census, and no family is narrowed (D-028).
- Price-pattern families stay counted forever (X8).
- This closes the search; it doesn't erase it.

**Amendment.** Only by a superseding D-entry.
