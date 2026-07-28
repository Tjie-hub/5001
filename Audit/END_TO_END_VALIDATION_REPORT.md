# Production Engine — End-to-End Validation Report

**Date:** 2026-07-28
**Scope:** Phase 3 of the final release certification — execute or verify the complete production
workflow: startup → database initialization → migrations → scheduler registration → signal
generation → opportunity pipeline → agent firm routing → paper trade creation → metrics updates →
backup → restore → graceful shutdown.
**Method:** Where a real, safe execution was possible without touching live secrets or making real
external calls (Stockbit, Telegram, Anthropic/Z.ai), this reviewer actually ran it, in an isolated
sandbox, and reports the real observed outcome. Where a genuine live run wasn't safely possible
(would require real credentials or could send real Telegram messages / hit real trading APIs), this
report says so explicitly and cites the hermetic test coverage that substitutes for it instead —
consistent with this task's instruction not to claim something passed without actually running it.

---

## What Was Actually Executed (not simulated, not assumed)

### Startup → DB initialization → migrations → scheduler registration

Ran `init_runtime()` directly, in an isolated Python process, against a scratch DB path and dummy
Telegram/env values (real `.env` never touched — env vars set before import, relying on
`python-dotenv`'s confirmed `override=False` default so the real `.env`'s values could never leak in
or be overwritten).

**First run (fresh, empty DB):**
- Uncaught crash: `UnicodeEncodeError` in `engine/registry_loader.py::announce_registry()`
  (see `Audit/PRODUCTION_READINESS_REPORT.md` P0 finding — fixed, commit `e30d4f3`).
- After that fix: succeeded. **42 scheduler jobs registered**, 12→15 tables created (screener, flow,
  agent-firm, and — after the second fix below — `paper_trades`/`scheduled_signals`).

**Simulated restart (second `init_runtime()` call against the same DB, same process):**
- Before the `paper_trades` fix: raised `ConfigError: DB missing required table: paper_trades` —
  the boot-deadlock defect (see Production Readiness Report P0 — fixed, commit `4826cae`).
- After that fix: **restart succeeded**, 42 jobs re-registered.

This is real, executed evidence — not a code-reading inference — that a from-scratch environment can
now complete: fresh boot → migrations → scheduler registration → clean restart on the same DB,
end-to-end, without manual intervention.

### Graceful shutdown

Called `scheduler.shutdown(wait=False)` (as the pre-fix production code did) and separately reasoned
through `wait=True` (the fix) against the actual installed APScheduler library's own docstring
(`BaseScheduler.shutdown`) — confirmed `wait=True` is "wait until all currently executing jobs have
finished," the correct semantics for the code's own stated intent. See Production Readiness Report
for the fix (commit `368f6c8`). Did not construct a live long-running-job-during-shutdown race
(would require a real, slow scheduled job mid-execution) — the fix is verified correct by matching
documented library semantics exactly, not by reproducing the race under time pressure.

### Secret redaction, live

During the smoke test above, `announce_registry()` attempted a real Telegram send with the dummy
fake token — it failed (expected: no real bot exists, and this sandbox has a local SSL/cert-chain
issue unrelated to the app), but the resulting log line read:

```
ERROR  utils.telegram  [telegram] send failed after 3 attempts: ...
  /bot[REDACTED]/sendMessage (Caused by SSLError(...))
```

The fake token was correctly redacted in a real failure path, live, not just in a unit test. Positive,
concrete confirmation the R-4 redaction mechanism works end-to-end.

---

## What Was Verified Via Targeted/Hermetic Tests (not a live run, and why)

**Signal generation, opportunity pipeline, agent firm routing, paper trade creation, metrics
updates:** exercising these for real requires either real market data + a real LLM provider call
(Z.ai/Claude), or the hermetic test suite's own mocked equivalents. Actually running the real path
was not attempted — it would require live credentials this review doesn't have access to, and could
send real Telegram messages or make real billed LLM calls, which this review is not authorized to do
unprompted. Instead:
- `run_agent_firm_gate`'s fail-open/fail-closed behavior (both providers down) was verified by
  reading the code directly and confirmed exemplary (see Production Readiness Report "Verified
  Clean") — not executed live, but the logic path was traced concretely, not assumed.
- `paper_trade.py::open_trade`/`close_trade` atomicity was verified by reading the actual SQL
  (single INSERT/UPDATE, all fields populated together) — confirmed no crash window, not executed
  live against a real signal.
- `engine/exits/evaluator.py`'s STOP→TP→TIME ordering was verified by reading the pure, deterministic
  function directly.
- Backup and restore were verified via **real historical execution logs** (`logs/cron_db_backup.log`,
  `logs/cron_db_restore_drill.log`) showing actual runs with `rc=0`, `integrity=ok`, matching row
  counts — genuine production evidence, not a fresh test run, though this same evidence surfaced a
  real gap: a ~36h missed-cron-invocation window around 2026-07-25/26 (see Production Readiness
  Report P1 finding).

**Gap this report names explicitly, per instruction not to hand-wave:** there is no automated,
CI-integrated test that exercises the *complete* live pipeline (real signal → real agent-firm call →
real paper trade → real metrics update) in one continuous run. Coverage today is a combination of
(a) unit/integration tests with mocked I/O at each stage, and (b) this review's own live
`init_runtime()` smoke test for the startup half of the pipeline. A true continuous rehearsal would
require either a long-running staging environment with fake-but-live market hours, or a recorded
market-data fixture driven through the real agent-firm/paper-trade code paths — neither exists today.
This is named as a gap, not silently assumed covered.

---

## Documented Gaps (from this phase)

1. No full live-market rehearsal exists; coverage is unit/integration-level per stage, not
   end-to-end in one continuous execution.
2. No idempotency guard exists against `init_runtime()` being called twice *without* an intervening
   shutdown in the same process — this review's smoke test didn't cleanly exercise "two schedulers
   running simultaneously" (the paper_trades bug intervened on the first attempt; the corrected
   version was tested with an explicit `shutdown()` between calls). Under real gunicorn/systemd
   operation this never happens (one `post_worker_init` call per worker process lifetime, confirmed
   in the Production Readiness Report as "Verified Clean") — flagged here only because it was in this
   phase's literal scope ("scheduler persistence") and wasn't cleanly exercised end-to-end.
3. Backup/restore-drill cron-firing gap (2026-07-25/26) — see Production Readiness Report.

---

## Conclusion

The startup→migration→scheduler-registration→restart segment of the production workflow was
genuinely executed, not assumed, and two real defects were found and fixed as a direct result of that
execution (not from static reading alone). The remainder of the pipeline (signal → agent firm →
paper trade → metrics) is validated at unit/integration granularity, with no full live rehearsal —
named as a gap, not claimed as covered.
