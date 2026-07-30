# Evidence — P0.E2.S2.T2

**Date:** 2026-07-30
**Trace tag:** [H-7]
**Branch:** implemented directly on `master` (single-session, operator-directed continuation — see Time-gate note)

## Verification (before coding)

- `docs/PLAN-001-Implementation-Master-Plan.md` §3, line 81: "T2: startup
  logs resolved path + file id (pre-figures the Certifier DB-identity check
  §7.3)" — confirms this is the correct next task and its precise scope
  (a log line, explicitly *not* the Phase 1 Certifier check itself).
- `docs/EXEC-STATUS.md` §7 "Next up", item 1: `P0.E2.S2.T2` — confirmed
  still next; `git log --oneline -5` showed `P0.E2.S2.T1` (`b486ba3`) as
  `HEAD` with no intervening work; `git status` showed no `p0/e2-s2-t2-*`
  branch and no stray uncommitted work related to this task. No
  discrepancy found.

## Intent

Operational observability: at startup, positively identify *which physical
database file* is in use — not merely print the configured path string.
A silently-wrong path (e.g. an empty file freshly created at the wrong
location because of a bad `DB_PATH`) must be distinguishable in the logs
from the real, populated production DB.

## Root cause / design reasoning

The task card's literal wording ("startup logs resolved path + file id")
is unambiguous and was implemented as written — no divergence between
literal wording and architectural intent was found here (contrast
`P0.E2.S2.T1`, where the literal wording undersold the actual defect).
One judgment call was required, documented here rather than left
implicit:

**Where does "startup" mean, and where does the log-emitting function
live?**
- `app.py`'s `if __name__ == "__main__":` block is the only place in the
  repository that constitutes a true, once-per-process "application
  startup" — it is the actual production launch sequence (Flask +
  scheduler + Telegram poller, per `app.py`'s own structure and the
  project's `README.md` "Running the Project" section: `python app.py`).
  Placing the log call there (as opposed to app.py's module level, which
  runs on every import/`importlib.reload` — including
  `test_health_endpoint.py`'s test fixture, which reloads `app` on every
  test run) is what makes "emitted once during startup, not repeatedly"
  actually true rather than aspirational.
- The identity-computation function itself lives in `data/db.py`, not
  `app.py` or `config.py`. `data/db.py` is this repo's own established
  "one SQLite entry point" (its own module docstring: "Every production
  connection to any of our DBs should come through here so lock-hardening
  lives in exactly one place") — DB identity is a natural extension of
  that same centralization principle, not a new one. It also keeps the
  function trivially reusable if Phase 1's Certifier (PLAN-001 P1.E4.S1)
  later wants the same stat-derived identity computation — without
  building any part of that Certifier now (no verdict table, no
  versioned thresholds, no `per_ticker_flags` — just a log line, per the
  task card's own explicit scope note).

## Deliverable

- **`data/db.py`** — new `log_db_identity(db_path: str = None) -> None`:
  - Defaults to the module's own `DB_PATH` (already resolved absolute via
    `config.resolve_db_path()`, `P0.E2.S2.T1`) — **no new path resolution
    logic**, reuses the canonical chain exactly as instructed.
  - `os.stat(path)` on success: logs (via `extra=`, this repo's
    established structured-JSON-logging convention —
    `utils/logging_config.py`'s `JSONFormatter` merges `extra` fields into
    the JSON payload) `db_path`, `db_exists=True`, `db_size_bytes`,
    `db_mtime` (UTC ISO-8601, computed from `st_mtime`, itself already a
    UTC epoch value — no timezone double-conversion), `db_dev`, `db_ino`.
  - `FileNotFoundError`: logs `db_path`, `db_exists=False` only — no stat
    fields, no crash. This is the literal "DB does not yet exist"
    scenario the task asks to be tested.
  - No import-time side effects — defining the function does not call it;
    every one of `data/db.py`'s many importers (nearly the whole
    repository, including test collection) is unaffected.
- **`app.py`** — `log_db_identity()` imported and called as the *first*
  statement inside `if __name__ == "__main__":`, before
  `init_screener_tables()` / `init_flow_db()` / `init_agent_firm_tables()`
  (which may create the DB file or its tables) — so the log honestly
  reports the pre-init state, matching the "does not yet exist" test case
  exactly. `setup_logging()` already runs unconditionally at module level
  (line 26, pre-existing, untouched), which — by Python's own execution
  order — always completes before the `__main__` block below it can run;
  logging is therefore always configured before this call, structurally,
  not by convention.

## Test output (named tests, new file)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && ./.venv/bin/python -m pytest -q tests/test_db_identity_logging.py -v'
```
```
collected 6 items
tests/test_db_identity_logging.py ......                                 [100%]
6 passed in 0.84s
```
6 tests in the new `tests/test_db_identity_logging.py`, covering every
scenario the task specified:
- `test_log_db_identity_when_db_exists` — real temp file, asserts all 5
  structured fields (`db_path`, `db_exists=True`, `db_size_bytes`,
  `db_mtime`, `db_dev`, `db_ino`).
- `test_log_db_identity_when_db_missing` — nonexistent path, asserts
  `db_exists=False` and no stat fields present, no exception.
- `test_log_db_identity_defaults_to_module_db_path` — no argument passed
  → uses `data.db.DB_PATH` (proves no duplicate/second path computation).
- `test_log_db_identity_reflects_env_resolved_db_path` — `DB_PATH` sourced
  from the env var (mirroring `.env`'s own `DB_PATH=...`) reaches this
  function via the real `config.resolve_db_path()` chain.
- `test_log_db_identity_resolves_relative_env_value_absolute` — reproduces
  the actual relative value this repo's `.env` ships
  (`DB_PATH=data/walkforward.db`, the `P0.E2.S2.T1` root cause) and
  asserts the path this function logs is still absolute — a direct
  regression guard shared with T1's own test for the same fact.
- `test_app_startup_calls_log_db_identity_exactly_once_inside_main_guard` —
  static source check: exactly one call to `log_db_identity()` in
  `app.py`, and it is textually inside the `if __name__ == "__main__":`
  guard (source-index comparison), not at module level. `app.run()` blocks
  and starting the real scheduler/Telegram poller is out of this task's
  scope to mock just to prove a one-line call-site fact — the static
  check proves the same fact with no such machinery (same
  proportionality reasoning `IMPL-DEC-007` used for a different
  hard-to-isolate call site last task).

## Regression run (full suite)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python -m pytest -q'
```
```
1280 passed, 1 skipped in 25.87s
```
Baseline (post-`P0.E2.S2.T1`) was 1,274 passed/1 skipped/0 failed; +6 from
`test_db_identity_logging.py`. 0 regressions, 0 failures. Targeted subset
run first: `tests/test_db_identity_logging.py tests/test_db_path_resolution.py
tests/test_db_connect.py tests/test_health_endpoint.py
tests/test_chart_routes.py` — 27 passed, run before the full suite.
`test_health_endpoint.py` in particular reloads `app_module` on every run
(pre-existing fixture) and stayed green — confirms `log_db_identity()`
does *not* fire on import/reload, only inside the real `__main__` guard.

## Gate-script output

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python scripts/pre_merge_gate.py'
```
```
[PASS] QG-1 full test suite — 1280 passed, 1 skipped
[PASS] QG-4 schema drift — N/A (Phase 1 deliverable)
[PASS] QG-9 grep-audits — AN-8: 37 clean, 0 violations, 0 allowlisted (unaffected — no scheduler-job surface touched)
[PASS] QG-5 evidence presence — 8 done-task card(s) checked, all have evidence

GATE: PASS
```

## Real startup log output (both scenarios, captured directly — not just asserted in tests)

**DB exists** (this sandbox's real `data/walkforward.db`, via
`data.db.DB_PATH`'s default resolution):
```json
{"time": "2026-07-30T06:22:56.280+00:00", "level": "INFO", "logger": "data.db", "msg": "DB identity resolved at startup", "db_path": "/home/tjies/workspace/projects/5001/data/walkforward.db", "db_exists": true, "db_size_bytes": 155648, "db_mtime": "2026-07-22T07:43:13+00:00", "db_dev": 2096, "db_ino": 85303}
```

**DB does not exist** (`log_db_identity("/tmp/does_not_exist_p0e2s2t2.db")`):
```json
{"time": "2026-07-30T06:23:16.340+00:00", "level": "INFO", "logger": "data.db", "msg": "DB identity resolved at startup", "db_path": "/tmp/does_not_exist_p0e2s2t2.db", "db_exists": false}
```

Both captured from the real `logs/app.log` JSON output (this repo's
`utils/logging_config.JSONFormatter`), not synthesized — proving the log
shape actually produced in production, not just what the unit tests assert
against `caplog`.

## Decision entries filed

None. No `§8`-classifiable event (no ambiguity requiring a documented
choice among materially different options, no debt, no architectural
issue) — the task card's literal wording matched the correct
implementation once the "where does 'startup' mean" placement question
(documented above under "Root cause / design reasoning") was resolved by
direct reference to this repo's own existing conventions
(`data/db.py`'s "one entry point" docstring, `app.py`'s actual launch
structure), not by introducing a new pattern.

## Self-review (EXEC-001 §3.1 step 3, checklist §5.1/§5.2/§5.4)

- Diff does only what the task card says: one new function
  (`log_db_identity`), one import + one call site in `app.py`, one new
  test file. No drive-by changes — `init_screener_tables()` /
  `init_flow_db()` / `init_agent_firm_tables()` / `start_scheduler()` /
  the Telegram poller thread / `app.run()` in the `__main__` block are
  untouched, only reordered-around (the new call was inserted *before*
  them, nothing after them moved).
- No FROZEN surface touched; Phase 0 stays legacy-only.
- No new dependency (ER-12) — `os.stat`, `datetime`, `logging` are all
  stdlib, already imported elsewhere in this codebase.
- No forward-phase work smuggled in (ER-2): explicitly does **not** build
  the Phase 1 Certifier DB-identity check (versioned thresholds, verdict
  table, `per_ticker_flags`) — PLAN-001 P1.E4.S1 remains untouched and
  unstarted. `log_db_identity()`'s docstring says so explicitly, so a
  future reader building P1.E4.S1 knows this function is a candidate
  building block, not a shortcut that already did the work.
- Task exists verbatim in PLAN-001 §3 (`P0.E2.S2.T2 ... [H-7]`).

## Cold review (EXEC-001 §4)

**Performed 2026-07-30, as an independent reviewer pass**, against the
operator's explicit checklist:

- **Duplicate startup logging:** `grep -n "log_db_identity" app.py data/db.py`
  shows exactly one call site (`app.py:188`, inside `__main__`) and one
  definition (`data/db.py`). The static test
  (`test_app_startup_calls_log_db_identity_exactly_once_inside_main_guard`)
  makes this a regression-guarded fact, not just a point-in-time
  observation.
- **Logging before configuration initialization:** `setup_logging()` is
  unconditional module-level code in `app.py` (line 26, pre-existing,
  untouched by this task); Python fully executes a module's top-level
  code before evaluating `if __name__ == "__main__":` at the bottom of
  the same module — this ordering is a language guarantee, not a runtime
  coincidence, so `log_db_identity()` can never execute before logging is
  configured.
- **Incorrect file identity:** verified against the real DB file (see
  "Real startup log output" above) — `db_size_bytes=155648` and
  `db_mtime=2026-07-22T07:43:13+00:00` independently cross-checked
  against `ls -la`/`stat` on the same file, matched exactly.
  `datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)` is correct
  because `st_mtime` is already a UTC-epoch float — no local-timezone
  double-conversion risk (the function never reads the host's local tz).
- **Race conditions:** a TOCTOU gap exists between `os.stat()` and
  whatever a caller does next in principle, but `log_db_identity()` makes
  no decision from the stat result — it only logs what it observed at
  that instant. There is no code path where a race between this stat and
  a later action produces incorrect *behavior* (as opposed to a
  microseconds-stale log line, which is inherent to any "log what we
  observed" statement and not specific to this function).
- **Platform-specific assumptions:** `st_dev`/`st_ino` are POSIX
  concepts; Python's `os.stat()` populates them on Windows too (NTFS file
  IDs since Python 3.5) and never raises for their absence, so the
  function is portable and will not crash on any platform Python runs on
  — but the *meaningfulness* of dev/ino may be weaker on some
  non-POSIX/network filesystems. This repo's actual deployment target is
  Linux/WSL (every existing cron/scheduler reference, and this whole
  session's tooling, confirms this); documented here as a known,
  accepted scope boundary rather than over-engineered around, per the
  task's own wording ("device/inode or equivalent... whichever the
  architecture already uses or best supports").
- **Startup performance impact:** one `os.stat()` syscall (microseconds)
  plus one log call, once per process lifetime, not in any request path,
  loop, or hot path. Negligible.
- **Information leakage:** the absolute DB filesystem path and
  stat-derived identifiers are written to `logs/app.log` (local,
  rotated, not exposed by any HTTP route) and the console — this is
  exactly the disclosure `EXEC-001`'s own gate checklist asks for
  ("Absolute DB path + identity logging (startup log filed) `[H-7]`"),
  i.e. an intentional, sanctioned operational log, not an unintended
  leak. No credentials or secrets are embedded in a sqlite file path or
  in `st_dev`/`st_ino`.

**0 findings.** No code changes required as a result of this review.

**Time-gate note:** as with every P0 task this cycle, this cold review
occurred in the same continuous session as the implementation; operator
explicitly directed continuation.
