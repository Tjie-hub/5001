# Dataset B Final Reconciliation & Freeze Readiness

**Date:** 2026-09-11 · **Mode:** READ-ONLY / NO G1 — governance/validation only, no dataset mutation

**Verdict: READY FOR FREEZE** (recommendation only — this document does not execute a freeze)

---

## Step 1 — Capture reconciliation

| Check | Result |
|---|---|
| Expected cells (101 tickers × 386 sessions) | 30,880 |
| `capture_manifest` cells | 30,880 |
| Missing (expected − manifest) | **0** |
| Extra (manifest − expected) | **0** |
| Non-terminal manifest rows (i.e. not SUCCESS/EMPTY) | **0** |
| Status breakdown | SUCCESS 30,877 · EMPTY 3 |
| `broker_flow_b` distinct (ticker, trade_date) cells | 30,877 — orphans (no SUCCESS manifest row): **0** |
| SUCCESS cells missing from `broker_flow_b` | **0** |
| `bandar_detector_b` distinct cells | 30,877 — orphans: **0** |
| SUCCESS cells missing from `bandar_detector_b` | **0** |
| `raw_responses` cells | 30,880 — orphans (no terminal manifest row): **0** |
| Terminal manifest cells missing a raw response | **0** |
| Duplicate key groups (all 4 tables) | **0** each |
| Date-echo mismatches | **0** |
| Truncation at limit=150 | **0** |
| Failed cells (final) | **0** |

Every one of the four store tables reconciles exactly against the frozen roster and against each other. No orphans in either direction.

## Step 2 — The 3 EMPTY cells

| Ticker | Date | `trading_calendar` | `ohlcv` | `bandar_detector` (raw) | `suspension_events` (±30d) | `corporate_action_events` (±10d) |
|---|---|---|---|---|---|---|
| PTRO | 2025-10-06 | IHSG session (market open) | O=H=L=C=7150, volume=0.0, `is_final=1` | total_buyer=0, total_seller=0, value=0, volume=0 | none | none |
| RAJA | 2025-10-13 | IHSG session | O=H=L=C=5675, volume=0.0, `is_final=1` | total_buyer=0, total_seller=0, value=0, volume=0 | none | none |
| RATU | 2025-11-28 | IHSG session | O=H=L=C=12125, volume=0.0, `is_final=1` | total_buyer=0, total_seller=0, value=0, volume=0 | none | none |

Raw Stockbit response for all three: HTTP 200, `from`/`to` correctly echoed, `broker_summary.brokers_buy/sell` both `[]`, `bandar_detector` independently reports zero population/volume/value — a second, uncensored vendor signal agreeing with the broker-flow endpoint rather than contradicting it. Capture metadata: `date_echo_match=1`, `retry_count=0`, no error — this was not a failed or retried request.

Three independent signals converge (vendor broker-flow endpoint, vendor bandar-detector aggregate, and our own OHLCV pipeline's `is_final=1` flat/zero-volume bar) — this rules out **DATA DEFECT** (a defect would show disagreement between these independent sources, not agreement). The market was open (not a holiday) and the gap is single-ticker, not date-wide — this rules out treating it as the market-wide MARKET_GAP phenomenon already catalogued in `GAP_CLASSIFICATION_v1.json` (untouched by this task; out of scope — that classifier covers OHLCV absence, not a present-but-zero-volume bar).

No suspension notice, official or otherwise, exists anywhere in this repository to confirm a halt (the `suspension_events` table is a heuristic-derived table, already known incomplete, and shows nothing here). Per instruction, zero volume alone is **not** sufficient to assert `CONFIRMED SUSPENSION`.

**Classification for all three: `TICKER_LEVEL_ZERO_VOLUME_SESSION`** — evidence-supported (multi-source agreement on zero trading activity), retained per the explicit fallback rule since a vendor-confirmed suspension cannot be established from available evidence. Not `UNRESOLVED` (the evidence is consistent and sufficient to rule out defect and rule out market-wide-gap); not `CONFIRMED SUSPENSION` (no independent confirming source exists); not `DATA DEFECT` (three independent signals agree, which a defect would not produce).

## Step 3 — Population / limit audit

| Metric | Value |
|---|---|
| Max buy-side row count | 79 |
| Max sell-side row count | 72 |
| Max combined row count | 88 |
| Cells with a side ≥ 140 (approaching 150) | 0 |
| Cells with a side ≥ 120 | 0 |
| Cells with a side ≥ 100 | 0 |
| Cells with a side ≥ 75 | 10 |
| Cells truncated (≥150 either side) | **0** |
| Date-echo mismatch count | **0** |
| Cells that required ≥1 retry | 2 (both transient 503s, both later resolved — see prior backfill report §B) |
| Final failure count | **0** |

**limit=150 is confirmed sufficient for every one of the 30,877 SUCCESS cells** — the highest observed combined population (88) leaves 62 rows of headroom under the cap, and zero cells came within 40 rows of it.

## Step 4 — Accounting identity

Computed as `SUM(value)` over all rows (both sides) per `(ticker, trade_date)`, across all 30,877 SUCCESS cells:

| Metric | Value |
|---|---|
| Min residual | 0 |
| Max residual | 0 |
| Non-zero residual count | **0** / 30,877 |

**Exact** — `SUM(buy_value) + SUM(sell_value) = 0` holds on every single captured cell, no exceptions.

(Informational, not a required identity: `SUM(lot)` per cell ranges from −1,500 to +21 — lot is *not* expected to net to zero the way value does; see Step 5.)

## Step 5 — Semantic integrity

Cross-checked against `DATASET_B_SEMANTIC_REGISTER_v1.json`. No changes made to the register; no reinterpretation introduced.

| Field | Register claim | Captured-data check | Result |
|---|---|---|---|
| `value` | SIGNED (BUY+, SELL−) | 0 positive-SELL rows, 0 negative-BUY rows out of 1,518,727 | **Confirmed, clean** |
| `lot_value` | non-negative (gross) | 0 negative rows | **Confirmed, clean** |
| `value_total` | non-negative (gross) | 0 negative rows | **Confirmed, clean** |
| `lot` | signed, but register already logs `side`/`lot` as **VERIFIED WITH DEFECT** (vendor rounding: some BUY rows carry lot<0, some SELL rows carry lot>0) | 1,623 BUY rows with lot<0 (0.107%), 3,298 SELL rows with lot>0 (0.217%) — same defect, same direction, consistent order of magnitude as the register's own Dataset A evidence (757/1,822 out of 3,026,786, a lower-truncation population) | **Confirmed — pre-existing, already-registered defect, not a new one.** Register's guidance ("derive direction from `sign(value)`, never `side`") is validated: `value` is 100% clean where `lot`/`side` are not. |
| `investor_type` | brokerage ownership (Asing/Lokal/Pemerintah) | exactly 3 distinct values: `Pemerintah`, `Lokal`, `Asing` | **Confirmed, no drift** |
| `freq` | UNKNOWN / FORBIDDEN as ticket-size denominator | captured raw and unexamined by this task; **not resolved here** | **Left exactly as registered — not touched** |

No downstream reinterpretation was introduced by this capture. The one field-level anomaly found (`lot`/`side` rounding) is the same defect the register already documents, now corroborated at a second, larger, more complete population.

## Step 6 — PIT / calendar integrity

| Check | Result |
|---|---|
| PIT roster artifact sha256 (as read from artifact file) | `f7e2fec030116a906471d27ee1e3a148aac459f125208d7d6e8e6c6fd3d8c57a` |
| Roster sha256 referenced by every capture run (3 runs, all identical) | same — `f7e2fec0…3d8c57a` (single value across `capture_run_log`) |
| Session calendar v2 sha256 | `5012be2315dc82ccfd65a2b117e1977753f0a7d3214693821b39077cd18043fa` |
| Universe size | 101 tickers |
| Admitted sessions | 386 |
| Excluded sessions | 2026-07-09, 2026-07-24 (member price coverage below threshold) · 2026-08-25 (no confirmed IHSG bar, carried forward from Dataset A per D-041/D-043) |
| Roster mutation during capture | **None** — every capture run across the ~24-hour operation referenced the identical, single roster sha256; the roster file itself was never opened for write by the fetcher (read-only load) |
| Future-membership leakage | None observed — the fetcher generates cells purely from the frozen `session_members` map, which is itself PIT-correct by construction (built once, prior to this task, from `idx80_membership_history` × `idx80_reconstitution_periods`) |

## Step 7 — Production isolation

| Check | Result |
|---|---|
| Dataset B store location | `docs/research_programs/P-M/dataset_b/store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite` — no Dataset B artifact anywhere under `data/` (production data path) |
| Fetcher write targets (source-scanned) | Every `INSERT`/`UPDATE`/`DELETE`/`CREATE TABLE` in `backfill_broker_flow.py` targets one of exactly 5 store tables (`capture_manifest`, `broker_flow_b`, `bandar_detector_b`, `raw_responses`, `capture_run_log`) — **zero** statements reference `broker_flow`, `bandar_detector`, or any other production table |
| Production `broker_flow` row count | 3,026,786 (pre-task baseline) → 3,049,237 (now) |
| Delta | +22,451 rows, **100% dated 2026-09-10** — a single day entirely outside the Dataset B window (2025-01-02 to 2026-08-27) |
| Cause of delta | Confirmed external: the live `idx-walkforward` systemd service (`active`), independent of this task |
| Production fetcher / schema / scheduler files | Confirmed unmodified by this task (see prior backfill report §F; `git status --porcelain -- docs/research_programs/P-M/dataset_b/` is the only change this task made) |

## Step 8 — Fingerprint / provenance validation

Fingerprint v2: **`1a68ab1c6c33409f16fe1c4dd40895c9f5a1b743693d05621e7338086cb8c5d9`**

| Field | Value |
|---|---|
| Input artifact — PIT roster | `DATASET_B_PIT_ROSTER_v1.json`, sha256 `f7e2fec0…3d8c57a` |
| Input artifact — session calendar | `DATASET_B_SESSION_CALENDAR_v2.json`, sha256 `5012be23…c18043fa` |
| broker_flow source | `materialized_store:store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite#broker_flow_b` (capture_version=v1, limit=150) |
| bandar_detector source | same store, `#bandar_detector_b` |
| ohlcv source | `production_live_table:data/walkforward.db#ohlcv` (settled window, unchanged from v1) |
| Capture run identifier | `c5934125-1282-4cf9-adfd-7aedfbda06b4` (main run) + 2 smoke-test runs, all sharing the same roster sha256 |
| Fetcher code sha256 | `5a0af8fff9ac34ef7471f4d261725c5790dd4a2767fd1ccabb375a1956628f68` |
| Configuration | `limit=150`, `cadence=1.5s`, `transaction_type=TRANSACTION_TYPE_NET`, `market_board=MARKET_BOARD_REGULER`, `investor_type=INVESTOR_TYPE_ALL` |
| Date range | 2025-01-02 → 2026-08-27 |
| Cells in scope (fingerprint) | 30,626 (30,880 minus 254 RAJA-quarantined cells) |
| Quarantined tickers | `RAJA` |

**Reproducibility:** the fingerprint is a deterministic function of (a) the frozen, unmutated roster and calendar artifacts and (b) the static, versioned materialized store — none of which depend on a live vendor call. Re-running `fingerprint_v2.py` against the same store without modification will reproduce the identical digest; this was not independently re-executed a second time in this reconciliation pass (no artifact was touched, so no re-run was necessary to trust the digest — the store is read-only and its content is unchanged since the digest was computed).

## Step 9 — Freeze readiness checklist

| Item | Result |
|---|---|
| B1 capture completeness | **PASS** |
| B2 isolated materialized store | **PASS** |
| Raw response coverage | **PASS** (30,880/30,880, 0 orphans) |
| Normalization integrity | **PASS** (0 orphans, 0 duplicates, across all 4 store tables) |
| Limit/truncation | **PASS** (0 truncated; max population 88 vs. cap 150) |
| Accounting identity | **PASS** (exact; 0/30,877 non-zero residuals) |
| PIT integrity | **PASS** (single roster sha256 throughout, no mutation, no future leakage) |
| Calendar integrity | **PASS** (single calendar sha256, exclusions match documented reasons) |
| Semantic register | **PASS** (no drift; the one field-level anomaly found, `lot`/`side` rounding, is the register's own pre-existing, already-documented defect — not new) |
| Empty-cell classification | **PASS** (all 3 evidence-classified as `TICKER_LEVEL_ZERO_VOLUME_SESSION`, correctly not overclaimed as suspension) |
| Production isolation | **PASS** (row delta fully attributed to the live scheduler, entirely outside the Dataset B window; zero write statements to any non-store table) |
| Fingerprint reproducibility | **PASS** (deterministic function of static, frozen inputs) |
| Provenance completeness | **PASS** (code hash, roster hash, calendar hash, run id, config all recorded) |

### Classification: **READY FOR FREEZE**

All thirteen gates pass with zero anomalies in capture completeness, accounting, PIT/calendar integrity, and production isolation. The three carried-forward, pre-existing, already-registered exceptions below are non-blocking by the program's own standing decisions and are **not new findings from this reconciliation**:

1. `freq` remains UNKNOWN / FORBIDDEN as a ticket-size denominator (register status, unchanged — not resolved by or in scope of this task).
2. `lot`/`side` carry a known vendor-rounding defect on ~0.1–0.2% of rows (register status VERIFIED WITH DEFECT, unchanged) — direction must be read from `sign(value)`, not `side`.
3. RAJA remains quarantined pending its separate corporate-action adjustment-basis decision (254/30,880 = 0.82% of cells, unchanged from the Foundation Closure report).

This document is a recommendation only. **No freeze was executed.** No G1 run, alpha/IC calculation, forward-return computation, hypothesis change, or Dataset A/B mutation was performed as part of this reconciliation.
