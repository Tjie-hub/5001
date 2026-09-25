# Event-time Rule Card engine + RC-0002 (failed breakdown, pre-2021 replication) — design

**Date:** 2026-09-25 · **Status:** approved in session ("GO"), pending spec review · **Authority for the
test itself:** D-055 (Rule Card gate); freeze needs a separate Owner approval.

## 1. Purpose

Path 2 of the edge search: put the surviving in-house anti-edge through a genuinely out-of-sample test.

- The failed-breakdown anti-edge (HYP-PM-0012) was discovered by the 2026-09 pattern scan on 2021–26 data. It
  survived the 2026-09-24 validity audit against the EW liquid book: h20 gross −0.89%, robust t −3.6 to −4.4.
- The pre-2021 backfill (`hist_pre2021.pkl`, repaired under D-056) has never been used for this pattern.
- Testing the frozen rule there is a replication on unseen data, not a re-cut.

The Rule Card framework (`research/rulecard/`) supports only month-end sorts
(`card.py`: "event-time rules need a v2 engine"). This design adds an event mode and the first card that
uses it.

**Out of scope:**
- C2 (rights-issue avoidance). Recorded as likely underpowered on paper: about 25 names in the bucket,
  σ ≈ 4.6%/mo, needing about 1.0%/mo true. It can reuse the engine later.
- Combining signals (R8), and any change to FWD-PM-FADE-001.

## 2. The card: `P-M/rulecards/RC-0002-FB-PRE2021/`

| field | value |
|---|---|
| rule | FADE-001 frozen definition. On an eligible row, `low < lo20` and `close > lo20`, where `lo20` = min(low) over the prior 20 sessions (excluding today). Entry at the next session's open. Hold 20 sessions. Exit at the close of session t+20 |
| data | pre-2021 backfill only, loaded by `research.rulecard.data` with the D-056 repairs. **Every row dated ≥ 2021-07-05 is excluded** (the discovery corpus) |
| universe | `liquid_idx_v1` (ADV20 ≥ Rp 1bn nominal, close ≥ Rp 50, ≥ 25 prior sessions, ≥ 18/20 traded, no >36% move in the prior 21 sessions) |
| primary estimand | **calendar-time, day-weighted.** Each session d: EW mean daily return of all open positions − EW mean daily return of the liquid book (names eligible at d−1). Daily excess is summed within each calendar month into a monthly series. Newey-West t, lag 3 |
| predicted sign | negative (avoid) |
| halves | `windows.split = 2011-01-01`. Discovery and confirmation halves must each have the predicted sign (≥ 12 months each) |
| tier / hurdle | **N**: t ≤ −3.0 **and** DSR ≥ 0.95 |
| trials | `n_trials = 18` (the pattern scan's ~12 arms + 6 wedge variants, conservative). Owner may overrule to 1 |
| fingerprint | `adv_tercile`, predicted negative: the anti-edge is stronger in the lowest-ADV tercile (limits to arbitrage) |
| costs | 0.60% round trip, used only in the derived book uplift. The primary is gross |
| survivorship | corpus = names listed in 2026-09, so delisted pre-2021 losers are missing. For an avoid rule this biases **against** the effect (conservative) |
| family_mapping | proposed: out-of-sample replication of HYP-PM-0012 inside `{R1}`, no new slot. **Owner call before freeze** |
| power | planning effect = in-house monthly calendar-time effect × 0.5. σ = max(in-house σ, measured noise floor). `n_months` from `power` |

**Deliberate deviation from FADE-001.** FADE-001 drops events with a > 35% session move inside the holding
window. That is look-ahead (audit R-3; measured effect ≤ 0.01 pp for FADE). The framework never drops on
holding-window content; bad data makes the run INVALID via SPL-1 instead. Stated on the card.

## 3. Engine changes (`research/rulecard/`)

### 3.1 `events.py` (new)

- `run_event_months(pan, flags, card, start, end, with_returns) -> list[dict]`
  - `flags`: Series on the panel index. 1 = event at that row's close, computed from rows ≤ that date.
  - Only eligible rows count as events.
  - Entry at the next session's open. The name must have an entry bar with volume > 0; if not, the event is
    not tradeable, it is counted, and it is dropped.
  - Hold `hold_sessions` of the name's own sessions; exit at the close. A name with no exit bar exits at its
    last traded close and is flagged `stale` (same F-8 rule as the month engine).
  - Daily position return: open→close on the entry day, then close→close.
  - Book return: EW close→close of names eligible at d−1 (open→close is not used for the book).
  - Daily excess = signal-leg EW mean − book mean, on days with ≥ 1 open position.
  - **Monthly records**, one per calendar month with ≥ 1 position-day, with the same keys `evaluate.py` reads:
    `month, formation (first session), entry (first entry), exit (last exit), valid, primary, deployment
    (= primary), univ_mean, book_mean, uplift_net, turn_book, turn_univ, fp_adv_low/high,
    fp_price_low/high, state`, plus `events, position_days, stale_exits, big_moves_in_hold,
    max_abs_move_in_hold, zero_returns, univ`.
  - The fingerprints use the same daily construction restricted to events whose name sits in the lowest or
    highest tercile (ADV or price) of the eligible universe on the signal date. Each is measured against the
    same full book.
  - `uplift_net` = derived book effect of excluding flagged names: −(w·excess) − cost·turnover, with w = the
    share of the book flagged. Informational only (R4b).
  - A month with fewer than `MIN_EVENT_DAYS` position-days (5) is marked invalid with a reason.
- `placebo_flags(pan, flags, seed)`: shuffle flags across eligible names within each date, so the per-date
  event count is kept.
- `random_flags(pan, flags_rate_by_date, seed)`: used by `power`, with the same per-date count and random
  names. `signal()` is never called.
- `event_order_check(events)`: FILL-1/EX-1 per event (signal < entry < exit), returned in the checks format.

### 3.2 `card.py`

- `signal.formation` may be `month_end` or `event`.
- `event` requires `signal.hold_sessions` (int ≥ 1), `portfolio.bucketing: flag`,
  `estimand.primary_kind: bucket_minus_rest`, and `estimand.aggregation: calendar_time`.
- Unknown formations are refused as before.

### 3.3 `runner.py`

- `_compute` branches on formation. For `event`, the check formations are a seeded sample of event dates.
- `prefix_invariance` and `traded_days_guard` are reused unchanged.
- `predictor_nondegenerate` for flags means event coverage > 0 and not every eligible row flagged.
- `power()` in event mode uses `random_flags` over 10 seeds and reports `sigma_noise_floor` and `months_valid`.
- `dry` reports events per year, median universe and months valid, with no returns.

### 3.4 Unchanged

`evaluate.py` (flag bucketing already skips MR; halves, ex-2025, DSR, fingerprints, deployment), `checks.py`
(split_band, placebo, forward_returns_nontrivial take the month records), freeze/run/ledger/verdict. Any
framework edit changes `framework_sha256`. No card is currently frozen, so nothing is invalidated.

## 4. Error handling

- Posture is fail-closed, as in the rest of the framework. A malformed card raises CardError with every
  problem listed. A signal on the wrong index, or a missing hold, is refused.
- Any check FAIL gives INVALID, never FAIL.
- A panel containing any row ≥ 2021-07-05 makes `rule.py`'s `load_panel` raise. This is the discovery-data
  fence, asserted in a test.

## 5. Testing (`tests/test_rulecard_events.py`)

1. **Injected anti-edge recovered.** On a synthetic panel (`synthetic.py`), flagged names get −1% over the
   next 20 sessions. The primary is negative and t < −3.
2. **Null.** With random flags on a panel without an effect, |t| < 2 on average over seeds; the placebo passes.
3. **No look-ahead.** Truncating the panel at d leaves flags and eligibility at d unchanged
   (prefix_invariance).
4. **No holding-window drop.** An event with a +50% move inside its hold stays in the record, and SPL-1 fails
   the run.
5. **Timing.** Entry is the next open, exit is the close of the h-th own session, and a stale exit is flagged,
   not dropped.
6. **Card validation.** `event` without `hold_sessions`, or with decile bucketing, is refused.
7. **Data fence.** RC-0002's `load_panel` holds no row ≥ 2021-07-05.
8. The existing suites `tests/test_rulecard_*.py` still pass (month mode unchanged).

## 6. Sequence

1. Engine + tests.
2. RC-0002 CARD.yaml + `rule.py` (family and trials marked PENDING).
3. `cli dry`, no returns.
4. `cli power`, random events.
5. Owner decides `family_mapping` and `n_trials`, and approves.
6. `cli freeze --owner …`.
7. `cli run`, exactly once.
8. Registry rows by hand; DECISION_LOG entry.
