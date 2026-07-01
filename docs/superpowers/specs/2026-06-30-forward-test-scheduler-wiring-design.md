# Forward-Test SHADOW Engine — Scheduler Wiring

**Date:** 2026-06-30
**Branch:** feat/tfb-context-filter
**Status:** Design approved, pending spec review

## Problem

The Phase-2 SHADOW position engine (`forward_testing/`) is built, tested (83 ft
tests green), and DoD-verified — but **nothing in production runs it**. A grep of
`scheduler/` for `forward_testing` / `shadow_manager` / `ShadowPosition` returns
zero hits. The engine is correct, tested, dead code.

Consequences observed in the prod audit:
- 204 shadow positions open, only 2 ever closed — because no scheduled job drives
  the ingest → open → exit-pass cycle. The 204 were created by a one-off manual
  prod smoke test, not by a recurring driver.
- The ft schema may have been initialized against the wrong DB (or never), per the
  audit notes.

Planning the downstream "decay detection / retire" machinery is premature: it
consumes a stream of *closing* shadow trades, and that stream does not yet exist.
This spec makes the existing engine **run** — nothing more.

## Goal

A single nightly scheduler job that drives the full SHADOW daily cycle against the
production DB, so the shadow-position population grows organically with both opens
and closes. Plus a one-time purge of the smoke-test cohort so the live data starts
clean.

## Non-goals (deliberately out of scope)

- Alpha-decay detection and strategy retire/flag logic
- Experiment / provenance ledger
- Portfolio construction, position sizing, correlation-vs-book checks
- Any dashboard, Telegram, or other surface for the shadow cohort
- Live (real-capital) A/B testing

## Decisions (locked with the user)

1. **Cadence:** one nightly EOD job, `run_date = today (WIB)`. Runs the ingest pass
   AND the exit pass in a single invocation.
2. **Slot:** 18:30 WIB, Mon–Fri (after the 16:00 close, the 16:05 flow fetch, and
   the 18:00 VPIN batch).
3. **Existing 204 positions:** purge them (start clean). They are smoke-test
   artifacts with stale entry dates; letting the exit pass process them would dump
   200+ fabricated exits into the trade population on day one.
4. **Costs:** use the default `Costs()` (commission_buy 0.15%, commission_sell
   0.25%, slippage 0.1%) — realistic IDX costs, NOT `Costs.zero()`.
5. **Observability:** log-only one-line summary for now. No Telegram (YAGNI).

## Architecture

### Component 1 — nightly job `run_forward_test_cycle()` (`scheduler/jobs.py`)

Fail-soft (matches the existing `try/except` + `print("[scheduler] …")` convention
used by sibling jobs). Accepts an optional `db_path` parameter (defaults to
`config.DB_PATH`) so tests can inject a temp DB.

Steps, for `run_date = today` in WIB:

1. `init_ft_tables(db_path)` — idempotent; guarantees the ft schema exists in the
   prod DB (`config.DB_PATH = data/walkforward.db`). Closes the "schema in wrong DB
   / never executed" hole.
2. Construct the stack against `db_path`:
   - `repo = FTRepo(db_path)`
   - `SignalAdapter(repo, db_path)`
   - `MarketDataResolver(db_path)`
   - `ExitPolicyRegistry()`
   - `LifecycleManager(repo)`
   - `ShadowPositionManager(repo, resolver, registry, lifecycle, db_path, costs=Costs())`
3. `n_ingested = SignalAdapter(repo, db_path).ingest(run_date)`
4. Snapshot open-position count; call `mgr.run(run_date)` (open pass + exit pass);
   snapshot again.
5. Log one line: `ingested=N opened=Δ closed=Δ open_now=K`.

**Idempotency:** `ingest` keys on `scheduled_signals.id`; `_maybe_open` skips any
signal that already has a position; the exit pass skips positions whose
`entry_date >= run_date`. A same-day re-run is therefore a no-op. This must hold at
the *job* layer, not just inside the manager.

### Component 2 — registration (`scheduler/__init__.py`)

Import `run_forward_test_cycle` alongside the other job imports, then:

```python
scheduler.add_job(run_forward_test_cycle, CronTrigger(
    day_of_week="mon-fri", hour=18, minute=30, timezone=WIB),
    id="forward_test_cycle", name="Forward-Test Cycle 18:30")
```

Add a matching line to the startup banner print block.

### Component 3 — one-time purge (`scripts/ft_purge_smoke_cohort.py`)

Idempotent standalone script:
- Delete all `ft_shadow_trade` rows, then all `ft_shadow_position` rows.
- Reset the lifecycle state of every affected signal back to `GENERATED` so a
  legitimately re-emitted signal can re-open cleanly on the next cycle. Because
  `GENERATED` is a *backward* transition, the script writes the signal state column
  directly (a one-off maintenance operation) rather than going through
  `LifecycleManager.transition`, which only permits forward moves.
- Never touches `scheduled_signals` source data — only ft-owned shadow rows.
- Run once, manually, before the first scheduled cycle.

## Data flow

```
scheduled_signals (today's scans)
        │  SignalAdapter.ingest(today)
        ▼
ft signals (state=GENERATED, track=SHADOW)
        │  ShadowPositionManager._open_pass(today)
        │  (opens fill at D+1 next_open; today's signals open tomorrow)
        ▼
ft_shadow_position (state=OPENED)
        │  ShadowPositionManager._exit_pass(today)
        │  (evaluates positions with entry_date < today against today's daily bar)
        ▼
ft_shadow_trade (closed round-trips) + lifecycle transition to CLOSED
```

## Error handling

- The whole job body is wrapped in `try/except`, logging the error and returning
  without raising — a failed cycle must never take down the scheduler (matches
  sibling jobs).
- `init_ft_tables` is idempotent, so a partially-initialized DB self-heals on the
  next run.
- If today's daily OHLCV bar is absent, `_maybe_open` defers opens (no D+1 bar) and
  the exit pass simply finds nothing new to evaluate — degrades safely to a no-op
  rather than fabricating fills.

## Testing

- **Job-level e2e** (`tests/forward_testing/test_scheduler_job.py`): seed
  `scheduled_signals` in a temp DB → call `run_forward_test_cycle(db_path=tmp)` →
  assert positions opened and lifecycle transitioned; call a second time → assert
  no new positions (job-layer idempotency).
- **Purge script test**: seed a fake shadow cohort → run purge → assert
  `ft_shadow_position` / `ft_shadow_trade` empty and affected signal states reset to
  `GENERATED`.
- Full existing ft suite (83 tests) must stay green.

## Open risk — data availability at 18:30

The exit pass evaluates today's open positions against **today's daily OHLCV bar**.
If that bar is not persisted to `walkforward.db` by 18:30 WIB, today's exits
silently defer one day.

**Verification step (implementation time, against live data):** confirm the daily
bar for `today` exists in the prod DB by ~18:30. If it does not, shift the slot
later, or fall back to the next-morning variant (`run_date = previous trading day`,
job at ~08:15). This is the one assumption to validate empirically rather than
trust.

## Rollout

1. Land code + tests on `feat/tfb-context-filter`.
2. Run `scripts/ft_purge_smoke_cohort.py` once against the prod DB.
3. Restart the app (via `start.sh`) so the new job registers.
4. Confirm the first 18:30 cycle logs a sane summary and the data-availability
   assumption holds.
