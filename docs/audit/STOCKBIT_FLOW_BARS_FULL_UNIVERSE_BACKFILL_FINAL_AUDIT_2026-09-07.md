# stockbit_flow_bars Full-Universe Backfill — Final Audit

**Date:** 2026-09-07 · **Author:** Claude Code session · **Status:** FINAL AUDIT, PASS.
Read-only throughout — no DB writes, no schema changes, no code changes. Independently
re-derives every coverage number from the database using the same predicates the backfill
orchestrator (`tools/agent_backfill_idx80.py`, `tools/flow_bars_gap.py`) used, so this audit
cannot silently agree with a stale or self-reported number — it recomputes from scratch.

**Mission context:** closes out the full-universe `stockbit_flow_bars` historical backfill
authorized and executed 2026-09-06 (see `docs/audit/STOCKBIT_FLOW_BARS_FULL_UNIVERSE_BACKFILL_READINESS_2026-09-01.md`
and `docs/audit/DATA_FOUNDATION_STABILIZATION_AND_RECOVERABILITY_GATE_2026-09-01.md` for the
readiness/authorization trail). This report is the pre-freeze gate for dataset
**`stockbit-flow-bars-v002`**.

---

## Scope audited

- **Date range:** `[2025-01-02, 2026-04-28)` (upper bound exclusive)
- **Universe:** full active `idx_tickers` set — 958 tickers (`data.fetcher.load_all_tickers()`)
- **Table:** `stockbit_flow_bars` (minute-level flow bars), cross-referenced against
  `stockbit_flow` (daily summary, used only to certify a genuinely empty session — see
  `tools/flow_bars_gap.py`)

## 1. SQLite integrity

| Check | Result |
|---|---|
| `PRAGMA integrity_check` | **ok** |
| `PRAGMA quick_check` | **ok** |
| `PRAGMA foreign_key_check` | 272 violations, **all** in `(agent_traces → agent_decisions)` — a table pair with no relationship to this dataset. Pre-existing, out of scope for this freeze, not touched or altered by this audit or the backfill. Flagged for visibility, not treated as a blocker. |

## 2. Schema

`stockbit_flow_bars`: `PRIMARY KEY (ticker, trade_date, bar_time)`, all three key columns
`NOT NULL`, plus `buy_lot, sell_lot, buy_freq, sell_freq, net_value, price, delta` (nullable
INTEGER). Indexes: the PK's own autoindex, plus `idx_flow_bars_date` (non-unique, on
`trade_date`). Matches the schema the runner (`tools/backfill_flow_bars.py`) and the completion
predicate (`tools/flow_bars_gap.py`) assume.

## 3. Coverage — independently recomputed

| Metric | Value |
|---|---:|
| Universe size | 958 tickers |
| IHSG-confirmed trading dates in window | 309 (of 309 `trading_calendar` rows — 0 unconfirmed) |
| Expected ticker-days (958 × 309) | 296,022 |
| Ticker-days with actual bars | 239,695 (**80.972%**) |
| Ticker-days complete (bars OR confirmed-empty session) | **295,143 (99.7031%)** |
| Missing ticker-days | **879** |
| Dates fully covered | 308 / 309 |
| Dates partially covered | 1 / 309 |
| Dates with zero coverage | 0 / 309 |

These numbers are **identical** to the orchestrator's own post-run "Coverage (after)" report from
the 2026-09-06 execution log — independently reproduced from the raw tables, not read from that
log. No drift between what the backfill claimed and what the database actually contains.

## 4. The single partial date — verified to be exactly the known fixture exception

| Check | Result |
|---|---|
| Dates with **any** missing cell | `["2025-04-14"]` — exactly one date, exactly the known fixture |
| Missing cells outside the fixture date | **0** (empty set) |
| `2025-04-14` completion | 79 / 958 complete (the original always-covered IDX80 set only) |
| `2025-04-14` `stockbit_flow_bars` row count | 26,465 (≈335 bars × 79 tickers — matches the IDX80 baseline exactly) |
| `2025-04-14` `stockbit_flow` summary rows | 79 (same 79 tickers — no confirmed-empty markers for the other 879, i.e. genuinely un-fetched, not "checked and empty") |

`2025-04-14` is `tools/agent_backfill_idx80.py::FROZEN_FIXTURE_DATES` — a date the orchestrator
refuses by construction to ever launch a child for (reserved for a separate Day-1 sign-off test).
**Confirmed: the sole gap in the entire window is exactly this reserved date, at exactly the
pre-existing IDX80-only state it had before this backfill began — the backfill introduced no new
gaps anywhere, and closed every gap it was permitted to touch.**

## 5. Duplicate / corrupt row checks

| Check | Result |
|---|---|
| Duplicate `(ticker, trade_date, bar_time)` rows in window | **0** |
| Rows with a NULL primary-key column in window | **0** |
| Total `stockbit_flow_bars` rows in window | 77,559,605 |
| Distinct tickers with ≥1 bar row in window | 900 (of 958 — the other 58 have zero recorded activity anywhere in the window, consistent with prior readiness-report findings on suspended/no-history tickers) |
| Distinct dates with ≥1 bar row in window | 309 (all of them) |

## 6. Verdict

**FINAL AUDIT: PASS.**

- No integrity corruption.
- No unexpected missing ticker-days anywhere outside `2025-04-14`.
- No duplicate or NULL-key rows.
- Coverage matches the orchestrator's own final report exactly, independently re-derived.
- The `2025-04-14` exception is exactly, and only, the known protected fixture condition.

This audit clears `stockbit-flow-bars-v002` for freeze, scoped as: `stockbit_flow_bars` +
`stockbit_flow` for `[2025-01-02, 2026-04-28)`, plus `idx_tickers` (full, as the universe
reference), `trading_calendar` (window), and `ohlcv` restricted to `ticker='IHSG'` (window, the
calendar-confirmation subset only — **not** the full multi-ticker OHLCV corpus, which is out of
scope for this dataset and not included in the frozen artifact).

See `data/frozen/stockbit-flow-bars-v002/MANIFEST.json` for the freeze record (hash, byte size,
row counts, timestamp).

**Timestamp of this audit:** 2026-09-07 (WIB), against `data/walkforward.db` as it stood at that
time (a live, continuously-written production database — see the manifest for why the frozen
artifact is a separate narrow export, not the production file itself).
