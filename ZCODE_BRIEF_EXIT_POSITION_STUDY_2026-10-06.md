# ZCode brief — exits and position management on the owner's entry method (2026-10-06)

**Task 2 of 2 in the owner's queue.** Task 1 was HYP-PM-0015, the ML rank model, filed NULL in D-068.
**Category:** Research, practice study (decision support for the owner's own trading).
**Owner-requested 2026-10-06.**
**Branch:** create `research/exit-study-2026-10` from `origin/research/new-order-2026-09-30`. Push only
that branch. Do not touch `research/ml-rank-2026-10` or `research/broad-search-v2-zcode`.

## Why

The research program finds no tradeable entry edge. The owner still trades, so the question that
changes their results is **how a position is managed after entry**:

- where the stop goes
- whether to average down or add to winners
- when to take profit

The owner's actual method:

- buy at a **support zone in an uptrend** (the "sniper": two limit orders, half at the zone top and
  half at the zone bottom)
- stop below the zone
- target at the nearest resistance
- they have also averaged down in the past
- they use "swing lots": top up on a pullback and sell the top-up into a small rally

Nobody has measured which management rules help or hurt on that entry population.

**This is NOT a hypothesis registration.** It's a practice study: exploratory, consuming no family slot,
not filed in FAILURE_REGISTRY. It must still be predeclared and frozen before any outcome is read,
because choosing the best of many exit rules is itself a multiple-comparison problem.

## Mode: two gates

- **G0:**
  - write and freeze `PREDECLARATION.md`, the driver and the PIT (point-in-time) tests, which read no
    outcomes
  - run the entry-population census: counts only, no returns
  - push and **stop**
- **G1:** after planner/owner approval, one run, then RESULT, VERDICT and PRACTICE_NOTE. Stop.

No re-runs with changed settings after seeing results.

## Data and universe

**Data:** `research.rulecard.data.load_extended_ohlcv(issuance=True)`, daily OHLCV only. Record the
fingerprint and commit through `research/tracking.py`.

**Universe at the signal date:** liquid, ADV20 ≥ Rp 10 bn (the owner's screen). Also report the
top-150 ADV60 universe for parity with the earlier studies.

**Eras:** E1 signals 2001-01..2021-09 (discovery), E2 2021-10..2026-09 (confirmation). Both are read
in the one G1 run, but the recommendation rule (below) requires agreement.

## Entry populations (PIT; levels use only bars before the signal day)

**E-SN, the sniper rule.** Use exactly the jurnal26 watchlist logic, re-implemented on the research
side. Do not import from `~/jurnal26`; the rules are listed here.

- **Trend filter:** close > MA50 > MA200, MA200 rising over 20 sessions, close ≤ MA20 + 2·ATR14.
- **Pivots:** 5-bar pivots over the last 250 bars, strict versus the bars before (a plateau counts
  once).
- **Zones:** pivots merged within 4% of the zone's first pivot. The support zone is the nearest one
  below price.
- **Zone bounds:** zone low = min pivot; zone top = min(max(zone max, zone low + 0.5·ATR), close).
- **Stop:** zone low − 0.75·ATR.
- **Target:** the nearest resistance-zone low above (else the 52-week high).
- **When a setup is set:** a new setup is "set" on day s when the zone is valid and price is within
  10% above the zone top.
- **Fills:** the next 20 sessions are watched. A fill happens when the low ≤ the order price; on a gap
  down through the order, the fill is at the open.
- **Per stock:** one setup at a time.

**E-RND, the control.** The same stocks on random liquid days, same sizing, with stop and target
distances set to the same ATR multiples as the matched E-SN trade.

**E-BRK, a second, common entry (reported, not used for recommendations).** Close above the 20-day
high, entry at the next open.

## Arms (frozen; ≤ 12 per entry population)

**Exit arms** (with single full-size entry at the zone top, P0):

| Arm | Rule |
|---|---|
| X0 | Hold 20 sessions, no stop (baseline) |
| X1 | Structure stop (zone low − 0.75 ATR) + target at the nearest resistance (the owner's plan); max 60 sessions |
| X2 | Fixed stop 2·ATR + target 3·ATR; max 60 sessions |
| X3 | Structure stop + chandelier trail (highest close − 3·ATR); max 60 sessions |
| X4 | Structure stop + exit on the first close below MA20; max 60 sessions |
| X5 | Structure stop + time stop: exit at session 10 unless the close is ≥ entry + 1·ATR; then as X1 |
| X6 | No stop, target at resistance, max 60 sessions |

**Position arms** (with exit rule X1):

| Arm | Rule |
|---|---|
| P0 | Single entry, full size at the zone top |
| P1 | Split entry: half at the zone top, half at the zone low (the owner's two limit orders); unfilled halves cancel after 20 sessions |
| P2 | Average down: full at the zone top, then **+50% more** at entry − 1·ATR if hit before the stop; same stop |
| P3 | Pyramid: full at the zone top, then +50% at entry + 1·ATR on a close; stop for the whole position unchanged |
| P4 | Swing lot: core at the zone top; top-up of 50% at the first pullback to entry − 0.5·ATR after a close ≥ entry + 1·ATR; the top-up sells at its own entry + 1.5·ATR or with the core |

## Mechanics (frozen)

- **Daily bars only.** If stop and target are both inside one day's range, assume **the stop first**
  (conservative).
- **Stops trigger intraday** at the stop price; on a gap through, the fill is at the open.
- **Targets** fill at the limit; on a gap through, the fill is at the open.
- **Costs:** 0.15% per buy fill plus 0.25% per sell fill (the owner's broker; together the 0.40%
  base). Add a 0.20% slippage allowance per round trip, so 0.60% round trip in all.
- **Risk normalization:** report every trade as an R multiple (P/L ÷ initial risk to the structure
  stop) as well as in %.

## Metrics, per entry population × arm × era

- n, mean and median net %, expectancy in R, win rate, average win / average loss, holding sessions,
  and the max adverse excursion distribution.
- An **equal-risk portfolio:** 1% of equity risked per trade, at most 10 concurrent, the next signal
  skipped when full. Report CAGR, max drawdown, and the worst 12-month return.
- A **year-by-year table**, mandatory.
- E-SN versus E-RND (does the sniper entry itself add anything), for each arm.

## Recommendation rule (frozen at G0)

- An arm is **recommended over the baseline** (X0 for exits, P0 for positions) only if, in **both** E1
  and E2:
  - its expectancy in R is higher, with a paired difference t ≥ 2.0 on matched trades
  - its portfolio max drawdown is not worse by more than 20% relative
- An arm is **flagged harmful** if it is worse in both eras with t ≤ −2.0.
- Everything else is "no reliable difference".
- **Averaging down (P2) gets a specific question:** does it raise expectancy, or only the win rate,
  with a fatter loss tail? Report its effect on the worst 5% of trades.

## Deliverables

**G0:**
- `docs/research_programs/P-M/exit_study/` containing:
  - `PREDECLARATION.md` and its `.sha256` sidecar, **covering the predeclaration, the driver and the
    test file**
  - the driver and the PIT tests
  - `CENSUS_G0.json`: setup and fill counts per era and population, no returns
  - `HANDOFF_G0.md`

  Push and stop.

**G1:**
- `RESULT_<utc>.json`
- `VERDICT.md`: the tables and the recommendation per arm
- `PRACTICE_NOTE.md`: one page, plain language, for the owner. Cover:
  - which stop
  - average down or not
  - when to take profit
  - what to change in the jurnal26 sniper defaults, if anything
- `HANDOFF_G1.md`

Push and stop.

## Hard constraints

- No production changes. No service restarts. `logs/TELEGRAM_OFF` stays.
- Do not touch `~/jurnal26` or the registries / DECISION_LOG. The owner files a short D-entry at the
  end if anything is adopted.
- Read-only data. Never print secrets.
- Research-side code only (boundary tests).
