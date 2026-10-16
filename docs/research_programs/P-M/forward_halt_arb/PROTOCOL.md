# FWD-PM-HALTARB-001 — forward record: names at ARB on IHSG trading-halt days

**Status:** FROZEN at D-100 (2026-10-16) · **Type:** forward recording only — no hypothesis, no census arm ·
**Owner approval:** 2026-10-16, "Forward recorder (Recommended)".

## 1. Why a recorder and not a backtest

On 2026-10-16 IHSG opened −8.01% and was halted 09:00–09:28 after MSCI's consultation on moving Indonesia to
Standalone; many names that touched ARB rebounded after the resume (TOWR 382 → 424 by 11:25). The owner asked
for a backtest. It cannot be done honestly:
- Only **4 halt-threshold days** exist in the data (IHSG from 2021-07, minute bars from 2025-01): 2025-03-18,
  2025-04-08, 2026-01-28, 2026-01-29. Names on one day move together, so the effective sample is 4 dates; no
  result could clear the census bar (t ≥ 3.30), and the D-074/D-080 floor is 20 events.
- 2026-10-16 is the case that suggested the idea; it is excluded from any test.
- Prior evidence runs the other way: D-079 (HYP-PM-0019, market-stress reversal) found continuation,
  mean −2.12%, t −6.18, gross ≈ −0.09%. That study entered at the close; the intraday bounce off ARB after a halt
  was not tested.

So the facts are recorded forward, from settled data, and **no outcome is read** until §5's gate.

## 2. Event day (frozen)

A trading session `D` whose settled IHSG bar (`ohlcv`, `ticker='IHSG'`, `is_final=1`) has
`low(D) / close(D-1) − 1 ≤ −8%` — the IDX trading-halt level (Kep-00002/BEI/04-2025, in force since 2025-04-08).
The recorder logs each event day with IHSG open/low/close changes. Event days are counted only from the ledger's
`opened_utc` (2026-10-16, after the close): **no back-fill**, and 2026-10-16 itself is refused.

## 3. Names (frozen)

All non-IHSG tickers with a settled bar on `D` and:
- **Liquid, ex-ante:** mean of `close × volume` over the 20 sessions before `D` ≥ Rp 1bn; `close(D-1)` ≥ Rp 50.
- **ARB touch:** `low(D) ≤ ARB(D)`, where `ARB(D)` = `close(D-1) × 0.85` rounded **up** to the IDX tick
  (tick: < 200 → 1; < 500 → 2; < 2,000 → 5; < 5,000 → 10; else 25). 15% is the ARB in force since 2025-04-08.
- The **comparison set** is every liquid name on `D` (touched or not).

## 4. What is written (per name, once its t+5 leg has closed)

| Field | Meaning |
|---|---|
| `entry_arb` | `ARB(D)`: a buy limit at the floor (fills when the floor trades) |
| `close_d` | close of `D` |
| `close_t1`, `close_t5` | close of the 1st and 5th session after `D` |
| `ret_arb_close` | `close_d / entry_arb − 1` (the intraday rebound) |
| `ret_arb_t1`, `ret_arb_t5` | from `entry_arb` |
| `ret_close_t1`, `ret_close_t5` | from `close_d` (the D-079-style close entry) |
| `bench_*` | same legs for IHSG and for the equal-weight mean of all liquid names on `D` |

Cost for any later test: 0.60% round trip (repo cost authority). A row with any session |return| > 35% inside
`D..t+5` (an unadjusted split shows up as one) is written with `void: true` and its reason, never dropped silently.

## 5. Gate (frozen)

- No outcome field is read, summarised or plotted before **20 event days** are in the ledger.
- Then a G0 under the D-086 stop rule: floor and minimum power (20%) frozen **before** power is computed;
  inference clustered by event date.
- Registration of a test needs its own D-entry. Note: the Price-Reversal family's slots are used (D-079 took
  slot 3); a test here needs either a family amendment (PG-3/PG-6/R7.5: widening only) or a new mechanism family.
  Settle that at the gate, not now.

## 6. Stated limits

- Daily settled bars only: the true intraday path (when, after the resume, the name left ARB) is not recorded
  here; jurnal26's halt watch (`macro_watch.py --halt`) logs a 20-big-cap snapshot at each halt and resume as
  context, not as evidence.
- ARB-touch does not mean a fill at the floor for any size: the queue at ARB is on the offer side, so a buy limit
  at the floor fills when the floor trades, but the recorded return assumes the floor price.
- Halt days are rare (4 in ~5 years of data at the then-current thresholds); reaching 20 may take years. This is
  stated so the wait is not mistaken for neglect.
