# Audit: cumulative trade-book counters, every consumer (2026-10-09)

**Authority:** owner, 2026-10-09: "check the other ran and audit … many invalid test, check all".
**Scope:** read-only.
- Every Python file on every branch that reads `stockbit_flow_bars` or `stockbit_flow`, or the derived
  `verdict`, `smart_money` and `composite_score` (79 files on hardening, plus 6 on research branches).
- The exploratory scripts in scratch folders.
- jurnal26.

No registry, result or production code was changed by this audit.

## 1. The fact being audited

- **Cumulative:** the trade-book minute series for `buy_lot`, `sell_lot`, `buy_freq` and `sell_freq`
  are **running session totals**. They are monotone: 0 decreases in 177,688 steps on 2026-10-08. The
  same thing is documented in `engine/trade_flow.py` (2026-09-04), `research/studies/idx80_flow_study.py`
  and the D1/D2 audit (2026-09-10).
- **Per-minute:** `net_value` is per-minute; it correlates 1.000 with the minute increments.
  **`delta` = buy_lot − sell_lot** per bar is also cumulative.
- **The correct uses:**
  - the day's total is the last value (MAX)
  - minute flow is the difference between consecutive bars
  - a window's flow is the end value minus the start value
- **Summing** or **windowing** the raw lot, freq or delta values measures time-weighted running totals.
  Early-day trades are counted once for every later bar.
- **`stockbit_flow` daily table (until fix 47ff225):**
  - Its `buy_lot`, `sell_lot`, `net_lot`, `buy_freq` and `sell_freq` are sums of running totals, about
    100–200× too high and early-weighted.
  - Its `composite_score`, `verdict` and `smart_money` came from `flow_filter._analyze`, which treated
    the running totals as per-minute flow.
  - Its `net_value` was always **correct**.

## 2. Registered hypotheses

| ID | Status | Flow instrument | Finding | Proposed classification (owner decides) |
|---|---|---|---|---|
| **HYP-PM-0001** / FAIL-PM-0001 | FAILED F2 | `OFI_t = delta/(buy_lot+sell_lot)` **per bar**, 1-minute → 15-minute reversal (`run_exp_pm_0001.py:55`) | Both terms are cumulative, so "1-minute OFI" was the session's running imbalance ratio. The tested construct is not the registered one. | **INVALID (data)**, outside F1–F9, the FAIL-PM-0007 precedent. Stays counted (X8). |
| **HYP-PM-0009** / FAIL-PM-0009 | FAILED F2 | `nbuy(seg) = SUM(buy_lot) − SUM(sell_lot)` over 09:00–09:59 and 14:50–15:49 (`run_exp_pm_0009.py:224–229`) | A sum of running totals over a segment is about (length × the running net level), not the segment's own flow. "Late vs early execution" was not measured. | **INVALID (data)**. Stays counted. |
| HYP-PM-0004 / -0005 (C-family G1) | INVALID (gov) / NOT CONFIRMED | Primary: `broker_flow` (C2 conduit, C3 breadth). The **NF control** = `(buy_lot−sell_lot)/(buy_lot+sell_lot)` from `stockbit_flow` daily (C7 report, check 4) | The primaries are not affected. The NF control is a ratio of summed running totals, an early-weighted imbalance and not the day's imbalance. | 0004 is already INVALID. **0005: annotate "control mis-specified".** The primary NULL very likely stands (t +0.32), but the control is not the registered construct. |
| HYP-PM-0003, -0007, -0008 | F2 / INVALID / draft | `broker_flow` only | Not affected (they don't read trade-book counters). | — |
| HYP-PM-0010/12/14/15/16/17/18/19/20 | various | OHLCV, corporate actions, KSEI; prices only from bars (0019 G0) | Not affected. | — |
| HYP-PM-0021 (OIB, G0 frozen today) | G0 | `MAX` per day | Correct by design. | — |

## 3. Exploratory and closed studies

| Study | Instrument | Status |
|---|---|---|
| Flow Edge Study (closed 2026-07-07, `_archive/analyze_flow_edge.py`) | `composite_score`, `smart_money` | **Tested the miscomputed labels.** Its "no edge" is valid only for the production feature as it was; a correctly computed verdict is untested. |
| Sprint 2026-09-15, daily families (`flow_family`, `interactions`, `adversarial_flow`) | `nb` = `net_value` | **Valid**: T2 acceleration, T3 flow/ADV, T4 toxicity filter, A/B/C families. |
| Sprint 2026-09-15, D1 lot-share acceleration | `buy_lot/(buy_lot+sell_lot)` from the daily table | **Affected** (it was DEAD anyway). |
| Sprint 2026-09-15, intraday (`run_intraday.py`) | 30-minute `SUM(buy_lot)`, `SUM(buy_lot+sell_lot)` (volume, VWAP weights, "heavy-tape" rank) | **Affected**, except the `net_value` and `late_share` features. It was killed for too few observations. |
| `pattern_scan/sweepflow.py` | `net_lot`, `composite_score`, `smart_money` (+ `net_value`) | **Affected**, except the `net_value` rows. |
| `research_data/build_research_views.py` (views_v1) | `buy_lot_sum`, `delta_sum` = sums over bars; `sb_*` from the daily table | **Affected columns.** Every consumer must use `net_value_sum` only. |
| G1 harness `nf_validate.py`, `freq_probe.py` | the daily table's lots and freq | Validation **against a mis-specified baseline**; the conclusions about NF and freq magnitude need re-checking. |
| Exhaustion study order-flow overlay (2026-09-25, memory: "sell-side aggressor / bandar Dist") | code not found in the repo or scratch | **Unverifiable.** Treat its flow-overlay conclusion as suspect. |
| idx80_flow_study, mechanism inventory B (opening-auction first bar), data-audit capture, stress G0 (prices), KSEI / retail-broker / OIB studies | MAX, the first bar, or prices only | **Correct.** |

## 4. Production

| Module | Use | Status |
|---|---|---|
| `flow_filter._analyze`, `stockbit_fetcher.fetch_flow` daily totals | running totals as per-minute flow; sums of running totals | **Fixed** in 47ff225 (live for the 18:30 cron; the web side after the owner's 5001 restart) |
| Verdict and smart_money consumers: `veto`, `edge_score`/`edge_enrich`, `monitor`, `premover_detector`, `swing_screener`, `strategies` R5 exit, `brpt_filter`, `reversal_filter`, agent firm FlowContext, `routes/*`, `screener/fundamental` | read the stored labels | **Correct from 2026-10-09.** All history before that is the old definition. |
| **`engine/delta_flow.py`** (CVD = `cumsum` of the cumulative delta; delta bars; footprint `delta_by_price`; `session_delta_stats`; stacked imbalances) | raw cumulative values treated as per-minute flow | **STILL WRONG.** It feeds `routes/chart.py` (the chart UI) and `engine/smc_flow.py`'s intraday tier. Fix next. |
| `engine/trade_flow.py` (`/api/v1/tickers/<s>/trade-flow`) | differences the counters | Correct. |
| jurnal26 `broker_watch.late_move` | last − value at 15:30 | Correct. |
| jurnal26 `review.py` flow5 | `net_value` (correct) + `smart_money` (old definition before 10-09) | Display only. |

## 5. Proposed actions (owner)

1. **D-entry:** reclassify **FAIL-PM-0001** and **FAIL-PM-0009** as **INVALID (data)**, like
   FAIL-PM-0007. Both stay counted (X8). The F2 count goes 9 → 7, and INVALID (data) goes 1 → 3.
   Neither mechanism has been tested.
2. **Annotate FAIL-PM-0005-G1:** the NF control was mis-specified. Primary unchanged.
3. **Fix `engine/delta_flow.py`** (de-cumulate, the same as `_per_minute`). This is a production change,
   so it needs the owner's merge and restart.
4. **Research rule:** trade-book lot, freq and delta values are used only as MAX, differences or window
   end-minus-start. Daily-table lots and freq before 2026-10-09 are not used. Add this to the semantic
   register.
5. **Optional:** recompute pre-10-09 `stockbit_flow` totals and labels from the stored bars (a
   production-data write).
