# Dataset B Broker-Flow Historical Backfill — Capture & Materialization Report

**Date:** 2026-09-11 · **Status:** DATA CAPTURE + MATERIALIZATION (no G1, no return interpretation, no hypothesis changes)

**VERDICT: B1 = CLOSED · B2 = CLOSED · DATASET B = READY FOR FREEZE** (pending governance sign-off — this task does not self-authorize the freeze)

---

## A. Capture scope

- Source: frozen PIT roster `artifacts/DATASET_B_PIT_ROSTER_v1.json` (sha256 `f7e2fec0…3d8c57a`) — 8 periods, 101 tickers, 386 admitted sessions.
- Intended cells: **30,880** (exact match to the roster's `session_members` sum).
- Endpoint: `GET https://exodus.stockbit.com/marketdetectors/{ticker}` with `transaction_type=TRANSACTION_TYPE_NET`, `market_board=MARKET_BOARD_REGULER`, `investor_type=INVESTOR_TYPE_ALL`, `limit=150`, `from`/`to` both set to the session date.
- Cadence: 1.5s/request (the already-validated trial cadence — not rerun, not redesigned).

## B. Requests / success / failure / retries

| Metric | Value |
|---|---|
| Cells attempted | 30,880 / 30,880 (100%) |
| SUCCESS | 30,877 |
| EMPTY (vendor returned 0 brokers both sides) | 3 |
| HTTP_ERROR / RATE_LIMIT_EXCEEDED / EXCEPTION (final) | **0** |
| Transient 503s during capture (auto-retried on resume, all resolved) | 3 |
| Missing vs. intended | 0 |
| Extra (not in roster) | 0 |
| Duplicate cells | 0 |

Two interruptions occurred, both infrastructure-side, not data-side: the harness killed its tracked background task once for host memory pressure (unrelated processes — Obsidian, Chrome, other agent sessions — not this fetcher, which never appeared in the top-15 RSS list); recovery via a self-healing, idempotently-resuming supervisor (`store/run_backfill_supervised.sh`) picked up from the exact last checkpoint with zero re-fetching and zero data loss. `capture_manifest` is keyed `(ticker, session_date)` — every resume/restart verified skip-on-terminal-status empirically, not just by code review.

## C. Actual broker population and truncation check

| Metric | This capture (limit=150) | Prior 1-month trial |
|---|---|---|
| Max single-side population | 79 (buy) / 72 (sell) | 64 |
| Max total population | 88 | 77 |
| Cells at/above limit=150 (truncation) | **0** | 0 |
| Date-echo mismatches (`to` ≠ requested) | **0** | 0 |

No truncation anywhere in the full 386-session × 101-ticker window — the true broker population never approached the 150 cap. `broker_flow_b`: 1,518,727 rows; `bandar_detector_b`: 30,877 rows (one per SUCCESS cell).

## D. Missing/empty/partial cells

3 EMPTY cells, each a single ticker on a single date (not date-wide — every other ticker that date captured normally):

| Ticker | Date | Evidence | Classification |
|---|---|---|---|
| PTRO | 2025-10-06 | `ohlcv` bar O=H=L=C flat, volume=0.0; not in `suspension_events`; not market-wide | TICKER_LEVEL_ZERO_VOLUME_SESSION |
| RAJA | 2025-10-13 | same pattern | TICKER_LEVEL_ZERO_VOLUME_SESSION |
| RATU | 2025-11-28 | same pattern | TICKER_LEVEL_ZERO_VOLUME_SESSION |

Not classified as vendor-confirmed "suspension" — the repository holds no official suspension-notice registry to confirm one, consistent with the Stage-5 audit's standing caution. Not a scraper/data gap: the OHLCV bar exists cleanly, it's single-ticker not market-wide, and the vendor correctly returned zero broker rows because (per the flat, zero-volume bar) zero trades occurred that session. `GAP_CLASSIFICATION_v1.json` is untouched — its market-wide-breadth methodology covers a different phenomenon (2026-07-09/07-24) and doesn't apply here; this is a new, separately-evidenced, non-blocking finding, not a rewrite of that artifact.

2026-08-25 exclusion: **0 cells** generated for that date — correctly and automatically propagated because the frozen roster's `session_members` never included it in the first place.

Known partial dates 2026-07-09, 2026-07-24, 2026-09-02, 2026-09-08: **0 cells** each — none are in the 386-session admitted calendar (07-09/07-24 excluded as MARKET_GAP per the existing calendar/gap-classification work; 09-02/09-08 fall after the window end 2026-08-27). Not a capture defect.

## E. Storage location and schema

**New, isolated, pre-existing store: none found before this task.**

- Path: `docs/research_programs/P-M/dataset_b/store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite` (new)
- Size: 276 MB
- Tables: `capture_manifest` (cell-level checkpoint/provenance), `broker_flow_b` (mirrors production `broker_flow` columns, PK `(ticker, trade_date, broker_code, side)`), `bandar_detector_b` (PK `(ticker, trade_date)`), `raw_responses` (gzip-compressed full vendor JSON per cell, PK `(ticker, session_date)`), `capture_run_log` (per-run provenance: code hash, roster hash, cadence, limit, host, counts).
- Distinguishable from production by table naming (`_b` suffix), separate file, and separate directory tree (`dataset_b/store/`, entirely outside `data/`).
- Never written to by production; never writes to production. Confirmed both by code inspection (zero references to `data/walkforward.db`/`data.db`/`DB_PATH` in `backfill_broker_flow.py` outside a docstring explicitly forbidding it) and by empirical row-level check (§F).

## F. Dataset A protection check

| Check | Result |
|---|---|
| Production `broker_flow` row count, before task | 3,026,786 (rowid 36–3,029,737) |
| Production `broker_flow` row count, after task | 3,049,237 (rowid 36–3,052,188) |
| Delta | +22,451 rows, **all dated 2026-09-10** (single day, entirely outside the Dataset B window ending 2026-08-27) |
| Cause | Confirmed the live production `idx-walkforward` systemd service (`systemctl --user is-active` → `active`), continuing its normal daily ingestion — not this task |
| Production fetcher (`stockbit_fetcher.py`), schema (`data/db.py`), scheduler (`scheduler/jobs.py`, `scheduler/scanner.py`), `app.py` | All show pre-existing uncommitted modifications from **before** this task started (confirmed against the Stage-5/6 preflight baseline); this task's `git diff` contribution to every one of these files is empty — `git status --porcelain -- docs/research_programs/P-M/dataset_b/` shows the entire new tree as the only change this task made |
| Dataset A fingerprint | Not separately recomputed here (out of this task's scope — Dataset A's own F-1 fingerprint pins ticker/count/date-range/SUM(lot)/SUM(lot_value), none of which this task touched); row-count/rowid-range check above is the direct, stronger evidence this task did not write to `broker_flow` |

No production modification occurred. Nothing required STOP-and-report escalation.

## G. Post-capture 35-check validation

**35/35 PASS, 0 FAIL, 0 UNRESOLVED, 2 warnings — unchanged from the prior run.** Rerun of `validate.py` against current state confirms no regression: PIT roster, session calendar, corporate-action handling, RAJA quarantine, calendar-indexed forward returns (k=3/7/15, 0 violations across all 4 checks each), and the regime-aware residual sweep all still pass. This suite validates OHLCV/PIT/corporate-action/forward-return construction, which this capture task did not touch — its 35/35 is expected to be, and is, stable.

## H. Fingerprints/hashes

| Artifact | SHA-256 |
|---|---|
| `DATASET_B_FINGERPRINT_v1.json` (production-sourced, superseded for broker-flow claims) | `b0ad62826671e7da8236c3265304feaf890d20fab44104c3190dac591806f51b` |
| **`DATASET_B_FINGERPRINT_v2.json`** (materialized-store-sourced — current) | `1a68ab1c6c33409f16fe1c4dd40895c9f5a1b743693d05621e7338086cb8c5d9` |
| `DATASET_B_BROKER_FLOW_CAPTURE_COMPLETENESS_v1.json` | `78be5871ef45c2fb211ebf4ccbbbaf941bdd3f59687689db061275d482df0ce7` |
| `backfill_broker_flow.py` (capture code) | `5a0af8fff9ac34ef7471f4d261725c5790dd4a2767fd1ccabb375a1956628f68` |
| `fingerprint_v2.py` | `27af72d2189f72495654fab48916884238bbd7e438f71db67b860fa44097e17c` |
| `store/run_backfill_supervised.sh` | `891633173d58619a4c6867365ae3dcfa985b54495379d60ed043ce4c66dc99b1` |

v1→v2 fingerprint differs as expected: same 30,626 in-scope cells (RAJA quarantined), different digest, because v2 pins the full limit=150 population instead of the top-25-per-side production slice. v1 is retained, not deleted — a superseding artifact, not an overwrite.

## I. Files changed

| Path | New/Modified | Purpose | Production behavior changed |
|---|---|---|---|
| `dataset_b/backfill_broker_flow.py` | New | Standalone limit=150 capture fetcher | No |
| `dataset_b/fingerprint_v2.py` | New | Materialized-store-sourced fingerprint | No |
| `dataset_b/store/run_backfill_supervised.sh` | New | Self-healing capture supervisor | No |
| `dataset_b/store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite` | New (data) | Materialized Dataset B broker-flow store | No |
| `dataset_b/artifacts/DATASET_B_FINGERPRINT_v2.json` (+.sha256) | New | Current fingerprint | No |
| `dataset_b/artifacts/DATASET_B_BROKER_FLOW_CAPTURE_COMPLETENESS_v1.json` (+.sha256) | New | Completeness report | No |
| This report | New | Deliverable #8 | No |

All under `docs/`, none under any production path (`scheduler/`, `engine/`, `data/`, `app.py`, etc.). `git status --porcelain -- docs/research_programs/P-M/dataset_b/` shows exactly one line: the new tree, untracked (`??`). No commit was made — nothing pushed, per no explicit instruction to commit.

Pre-existing, unrelated working-tree modifications (confirmed present before this task and untouched by it): `app.py`, `data/db.py`, `stockbit_fetcher.py`, `scheduler/jobs.py`, `scheduler/scanner.py`, plus the broader pre-existing diff set noted in the prior Foundation Closure report.

## J. Remaining blockers

None that block a freeze decision on data-capture grounds. Carried forward from the Foundation Closure report, unaffected by this task:
- **B3 — `freq` semantics UNKNOWN** (non-blocking except for ticket-size features; this capture preserved `freq` exactly as returned, made no interpretation).
- RAJA remains quarantined (254/30,880 = 0.82% of cells) pending the corporate-action adjustment-basis decision already on record — unchanged by this task.

## K. B1 status

**CLOSED.** Full PIT sample captured at limit=150: 30,880/30,880 cells, 0 truncation, 0 date-echo mismatches, 0 unresolved failures, max observed population 88 (well under 150).

## L. B2 status

**CLOSED.** A dedicated, persistent, versioned Dataset B broker-flow store exists (`store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite`), independent of the live vendor API and of production `broker_flow`. The Dataset B fingerprint (v2) is now computed against this materialized store, not a live table.

## M. Dataset B freeze recommendation

All capture-side success conditions are met:

- [x] full PIT sample captured at limit=150
- [x] dedicated store exists
- [x] production `broker_flow` untouched
- [x] Dataset A unaffected (row-count delta fully attributed to the live scheduler, 0 rows in-window)
- [x] capture resumable/idempotent (proven empirically across 2 interruptions)
- [x] no unresolved capture failures
- [x] no date-echo mismatches
- [x] no unexplained missing cells
- [x] no truncation at limit=150
- [x] provenance recorded (code hash, roster hash, per-run log)
- [x] materialized store persistent
- [x] post-capture validation passes (35/35, unchanged)
- [x] 35/35 remains PASS

**Recommendation: the data-capture blockers (B1, B2) that were the sole blocking items in the prior Foundation Closure verdict are now closed.** This task does not itself declare Dataset B frozen — per standing governance instruction, freeze requires separate, explicit authorization from the program's governance process, not a self-declaration by the task that closed the last blocker. Next step, if authorized: freeze Dataset B against `DATASET_B_FINGERPRINT_v2.json`, then proceed to G1 (methodology/code-review gate) — still no return interpretation, no hypothesis action, performed here.
