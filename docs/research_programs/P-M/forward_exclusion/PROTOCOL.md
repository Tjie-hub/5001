# FWD-PM-VOLEX-001 — forward test of the volatility-exclusion rule

**Status:** OPEN · **Opened:** 2026-09-16 · **First formation:** 2026-09-14
**Spec frozen at opening.** Any change requires a new, dated, superseding protocol entry and a
new spec id — the ledger is append-only and is never rewritten.

## 1. What is being tested

Whether excluding the highest-volatility decile from a broad liquid IDX book produces a positive
incremental return prospectively, as it did in backtest.

This is **replication of a discovered effect**, not a novel alpha claim. The effect is the
low-volatility anomaly, documented globally. The backtest is in-sample discovery on the same data
the rule was found in, so it carries no confirmatory weight.

## 2. Frozen specification

| | |
|---|---|
| universe | liquid set (trailing-60 median traded value ≥ Rp 1e9, shift 1; close ≥ Rp 50; traded on the formation day; not within ±20 sessions of a suspension window), then the **top 200 by that trailing-60 median traded value** |
| signal | Parkinson-60 range volatility: `sqrt( mean_60( ln(high/low)^2 ) / (4 ln2) )` |
| rule | exclude the top 10% by signal; hold the remainder, equal weight |
| entry / horizon | enter `close(t+1)`, hold 21 sessions |
| benchmark | equal weight of the **same** universe, same entry and horizon |
| primary endpoint | `incremental = mean(held) − mean(universe)`, gross, per formation |
| cadence | one formation per calendar month, on the last **complete** session available |
| session guard | a session is complete only if priced-ticker count ≥ 95% of the trailing-20 median. This rejected 2026-09-15 (824 vs ~915 — morning fetch wrote `is_final=1` rows before the WIB open) and would reject 2026-09-07 (137). |

Costs are reported but do not gate the endpoint: turnover is ≈10.6%/month on **both** books, so the
cost terms very nearly cancel in the difference.

## 3. Pre-declared decision rule

Backtest reference (median across all 21 rebalance phases, 45 periods, 2022-07→2026-08):
**+0.394%/month, t = 3.74, P(>0) = 74%**, tracking error 2.34%/yr.

Monthly standard deviation of the incremental series ≈ **0.676%**. Therefore:

| n | SE | detectable effect (80% power, one-sided α=0.05) | status |
|---|---|---|---|
| 12 | 0.195% | +0.49% | **underpowered** for the backtest effect — interim read only, **no decision** |
| 24 | 0.138% | +0.34% | powered to detect +0.394% — **decision point** |

- **At n = 12:** report only. No decision, no spec change, no stopping.
- **At n = 24 (≈ 2026-09 + 24 months → 2028-09):**
  - **PASS** — mean incremental > 0, one-sided t > 1.71, **and** P(>0) ≥ 60%.
  - **FAIL** — mean incremental ≤ 0, or mean < +0.15%/month (under half the backtest estimate).
  - **INCONCLUSIVE** — anything else. Not a pass; the candidate stays parked.
- Early stopping is permitted in one direction only: if after n ≥ 12 the mean is below −0.20%/month,
  the rule is abandoned (it is doing active harm).

## 4. Forbidden once formations are visible

Changing the universe size, exclusion fraction, estimator, horizon, entry convention, liquidity
floor or cadence; adding or removing candidates; re-running the primary under any variation;
back-filling formations; selective sub-period reporting; silent edits to `ledger.json`.

## 5. Why the ledger starts empty

No historical formation has been or may be inserted. The backtest already exists and is recorded
in the session analysis; replaying it into this ledger would convert in-sample discovery into an
apparent forward record. Every entry carries `generated_utc` and a content fingerprint.

## 6. Known limitations, carried

1. **The benchmark lost money.** Over the backtest window the equal-weight top-200 book returned
   −2.61%/yr with a −36% max drawdown. A positive incremental does not make this a standalone
   investment proposition.
2. **Breadth.** The rule holds ~180 names. At 5–10 positions the edge is unharvestable
   (annualised IR ≈ 0.3). Whether the mandate can hold ~180 names is an open owner decision.
3. **Survivorship.** The price panel is a current-roster backfill with no dropouts. Dead names skew
   high-volatility, so their absence understates the effect — the bias is conservative here.
4. **Not novel.** Replication of a known anomaly; prior literature is a prior, not evidence.
5. **Decay.** In backtest the effect weakened from +0.73%/month (2022) to +0.42%/month (2026).

## 7. Operation

```
python3 docs/research_programs/P-M/forward_exclusion/run_forward.py     # form + score
python3 docs/research_programs/P-M/forward_exclusion/run_forward.py --json   # publish payload
```
Scheduled weekly in `deploy/crontab`; the calendar-month guard means at most one formation per
month, while the scorer runs each week so outcomes mature promptly.
