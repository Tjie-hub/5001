# G0 FREEZE — Pre-open news timing (proposed construction; STOPPED at breadth, never registered)

**Date:** 2026-10-28 · **Status:** STOPPED — breadth stop rule fired · **Census impact:** none (withdrawn
before registration, D-113 precedent: PEAD uncounted). **No return of any event ticker-date was read.**

## 1. Motivation (disclosed)

Owner observation, 2026-10-28 in-session: BBCA's Q3 headline ("laba naik 4,2%") was crawled by the 08:00 WIB
pre-market Google News job (news_mentions.updated_at 08:22, count ≥ 1) and the stock closed +7.65%. The owner
ordered: "test this new hypothesis." This motivating observation is known to owner and analyst **before** the
freeze; the freeze and the stop concern data formability only, and no systematic return read was performed.

## 2. Proposed construction (would-be registration — NOT registered)

- **Hypothesis (H1, sign positive):** ticker-dates whose same-day-published Google News headlines are already
  captured by the 08:00 WIB pre-market crawl (event = `news_mentions.count >= 1` with `updated_at`
  time-of-day in [08:00, 09:00) WIB) have positive same-day open→close returns.
- **PIT basis:** the 08:00 crawl stores only headlines with RSS `published_parsed == today`, fetched at
  ~08:00. A captured row therefore proves existence before the 09:00 open (`updated_at` is fetch time ≥
  publication time — conservative direction). (`news_filter.py::fetch_news_for_ticker`, scheduler job
  `news_fetch_premarket`, hour=8 Mon–Fri WIB.)
- **Instrument:** daily equal-weight mean of event ticker O2C returns (`ohlcv`, `is_final=1`, `open>0`);
  primary **net** of one 0.60% round trip per event-day (D-082 `cost_realised` basis), gross reported beside.
- **Statistic:** one-sided Newey–West t of the mean daily net portfolio return, 5 lags, vs the D-064 §C
  exact bar `E[max|Z|] = ∫₀^∞ 1−(2Φ(z)−1)^N dz` at the census in force at registration (616 if registered
  next → **3.300988**; formula reproduces 3.300069 at N=614 exactly). Kill: either calendar half ≤ 0.
- **No-widening clause (D-115 style):** sentiment-lexicon filtering of headlines and a liquid-only
  (ADV-filtered) variant are G1 sensitivities only, never later arms.

## 3. Pre-declared stop rules (breadth/power; frozen before any return read)

1. **Breadth floor:** ≥ 60 event-days (half the 119-day coverage window) with joinable final bars.
2. **Power floor:** ≥ 20% power at 0.20%/day net (PEAD D-113 minimum) via date-shift placebo σ.

These floors were set at the conventional levels used by D-112/D-113 before interpreting the counts below;
the decisive counts are far below any plausible floor, so no residual degree of freedom is outcome-relevant.

## 4. G0 breadth result (counts only — no return read)

| Measure | Value |
|---|---|
| news_mentions coverage | 2026-04-26 → 2026-10-28, 119 trading dates, 972 tickers, 113,610 rows |
| Rows with 08:00–08:59 `updated_at` | 6,535 — **on only 8 distinct dates** |
| Event rows (count ≥ 1, pre-open) | **197** ticker-dates |
| Event dates | 2026-06-16 (13), 07-08 (30), 07-13 (21), 07-23 (3), 08-20 (31), 10-15 (36), 10-16 (25), 10-28 (38) |
| Joinable to final ohlcv bars (open>0, close>0) | **179 events over 7 dates** |

**Stop rule 1: FIRED — 7–8 event-days << 60.** Rule 2 never reached (moot at this breadth).

### Root cause (data infrastructure, not the hypothesis)

- The 08:00 pre-market job exists in code since `02c2034` (2026-06-10) but has written on only 8 of 119
  trading days — the scheduler evidently is not up (or the job does not fire) before 08:00 on all other days.
- Worse, the store is destructive: `save_news_count` uses `INSERT OR REPLACE`, so on every normal day the
  17:00 crawl overwrites the row and **destroys the pre-open evidence**. "News existed pre-open" is
  therefore unrecoverable from `news_mentions` for all non-captured days. The 8 surviving dates are an
  incidental, non-random subset (endogenous to scheduler uptime), not a sample of pre-open-news days.

## 5. Verdict and disposition

**STOP — WITHDRAWN before registration.** Never registered, so not counted in the deflation census (census
stays 615); no HYPOTHESIS_REGISTRY row; no EXPERIMENT_LEDGER record; no return read. Precedent: D-113 (PEAD,
G0 stop, uncounted). Close-relative check: the 2026-09-29 broad search only inventoried news_mentions counts
(`phase0_counts.py`, family F); no news-based return trial has ever been counted. `catalyst_flags` is empty
(no alternative instrument).

## 6. Path to testability (owner decision — propose only, no code changed)

1. Make pre-open capture append-only and continuous: e.g. a `news_mentions_premarket` table written only by
   the 08:00 job (17:00 never touches it), or a `first_seen_at` column the 17:00 REPLACE must preserve.
2. Fix scheduler coverage so the 08:00 job actually fires every trading day (root-cause the 8/119 uptime).
3. Accumulate event-days (frequency unknowable until capture is continuous), then re-freeze this G0 and
   re-run the breadth check; only a return read at that point consumes a census trial.

## Appendix — exact G0 count SQL (read-only)

```sql
WITH ev AS (SELECT ticker, date FROM news_mentions
            WHERE count >= 1
              AND substr(replace(updated_at,'T',' '),12,5) >= '08:00'
              AND substr(replace(updated_at,'T',' '),12,5) < '09:00')
SELECT COUNT(*) joined, COUNT(DISTINCT date) days FROM ev e
JOIN ohlcv o ON o.ticker=e.ticker AND o.date=e.date
WHERE o.open > 0 AND o.close > 0 AND o.is_final=1;
```
