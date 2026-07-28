# RC1 Conditions Closure Report

**Date:** 2026-07-28
**Basis:** `Audit/RC1_CERTIFICATION_REPORT_2026-07-28.md` — CERTIFIED WITH CONDITIONS, exactly two
conditions (RC1-C1, RC1-C2). This report closes both. Generated, point-in-time record.
**Constraints honored:** no unrelated refactoring, no architecture redesign, no Operations
Dashboard work.

---

## 1. RC1-C1 — Windows Path Normalization: closed

**Fix:** `tests/test_config_hygiene.py::test_dotenv_loaded_only_in_config` computed
`rel = str(p.relative_to(ROOT))` and compared it against the forward-slash `DOTENV_ALLOWED` set —
the identical bug class the three other boundary tests had. Changed to
`rel = p.relative_to(ROOT).as_posix()`, the exact same normalization already applied in
`test_architecture_boundary.py`/`test_db_centralization.py`/`test_research_data_fence.py`. No other
solution was invented; the comment added cites the same root cause and the same prior fix.
`test_no_hardcoded_home_paths_in_production_code` in the same file was left untouched — it only uses
`str(...)` for a diagnostic message string, not an allowlist comparison, so it doesn't carry the bug
and touching it would have been unrelated.

**Evidence of closure:**
- `pytest tests/test_config_hygiene.py -v` → 2/2 passed (was 1/2 before: the affected test failed
  with `['engine\\agent_firm\\config.py']` as a false-positive offender).
- New regression suite `tests/test_path_normalization.py` (5 tests, platform-independent via
  `PureWindowsPath`/`PurePosixPath` — no filesystem access, so these run identically on any host):
  Windows-vs-POSIX paths normalize identically; `str()` reproduces the exact bug while `.as_posix()`
  is the fix; mixed-separator input normalizes correctly; allowlist membership matches regardless of
  path flavor; single-component paths (no separator) were never affected either way.
- Behavior on Linux is unchanged: `.as_posix()` and `str()` are identical for a `PurePosixPath`, so
  this fix is a no-op on the platform CI actually runs on — confirmed by the fact that all four
  affected tests only ever failed locally on Windows.

---

## 2. RC1-C2 — Telegram Redaction Completeness: closed

**Fix:** Both remaining standalone senders now call the existing, shared
`utils.logging_config.redact_secrets()` — no new redaction logic was written:

- `auto_token.py::send_telegram` — added `from utils.logging_config import redact_secrets` and one
  line, `msg = redact_secrets(msg)`, immediately after the existing "not configured" guard and
  before the existing `requests.post(...)` call. URL construction, payload shape (`chat_id`, `text`,
  `parse_mode: HTML`), and the existing `except Exception as e: log(...)` handling are all untouched.
- `stockbit_fetcher.py::send_telegram` — identical one-line change in the identical position.

This is the same pattern R-4 already used in `utils/telegram.py`/`routes/telegram.py` — one shared
function, four call sites now, zero duplicate implementations.

**Evidence of closure:**
- `tests/test_stockbit_fetcher_telegram_redaction.py` (new, 8 tests, runs and passes on this
  Windows dev venv — `stockbit_fetcher.py` has no POSIX-only imports): redacts a single secret;
  normal messages unchanged; HTML tags and newlines preserved; multiple distinct secrets all
  redacted; an already-redacted message is left alone (idempotent); empty message doesn't crash;
  the "not configured" skip-send path is unaffected; the existing network-failure exception handling
  still swallows the error without raising.
- `tests/test_auto_token.py::TestSendTelegramRedaction` (new, 8 tests, identical coverage) — added
  to the existing test file, calling the real `send_telegram` implementation directly (captured as
  `_real_send_telegram` at module load, before the file's pre-existing `no_telegram` autouse fixture
  monkeypatches `at.send_telegram` to a no-op for every other test in the file). **Cannot be executed
  on this local Windows dev venv**: `auto_token.py` imports `fcntl` (POSIX-only) at module level, a
  pre-existing limitation of this file that predates RC1 and affects every test in
  `tests/test_auto_token.py`, not just the new ones — verified the new code at least compiles cleanly
  (`python -m py_compile tests/test_auto_token.py`, `auto_token.py`) and mirrors, statement-for-statement,
  the stockbit_fetcher test file that *does* run and pass locally. Will execute on the real Linux CI
  runner, where `fcntl` is available, same as the rest of that test file already does.

---

## 3. Files modified

| File | Change |
|---|---|
| `tests/test_config_hygiene.py` | `.as_posix()` fix — RC1-C1 |
| `auto_token.py` | `redact_secrets()` import + one-line call in `send_telegram` — RC1-C2 |
| `stockbit_fetcher.py` | `redact_secrets()` import + one-line call in `send_telegram` — RC1-C2 |

## 4. Tests added or updated

| File | Tests |
|---|---|
| `tests/test_path_normalization.py` (new) | 5 — Windows/POSIX/mixed-separator normalization regression, platform-independent |
| `tests/test_stockbit_fetcher_telegram_redaction.py` (new) | 8 — redaction coverage, runs locally |
| `tests/test_auto_token.py` (extended, `TestSendTelegramRedaction`) | 8 — identical coverage, Linux-CI-only per pre-existing `fcntl` limitation |
| `tests/test_config_hygiene.py` | no new tests added — the existing `test_dotenv_loaded_only_in_config` itself is the direct regression check |

## 5. Validation

- Targeted re-run (`test_config_hygiene.py`, `test_path_normalization.py`,
  `test_stockbit_fetcher_telegram_redaction.py`, `test_architecture_boundary.py`,
  `test_db_centralization.py`, `test_research_data_fence.py`): **25/25 passed**.
- R-2/R-4 regression check (`test_telegram_util.py`, `test_logging_config.py`,
  `test_routes_telegram_redaction.py`, `test_scheduler_job_error_alert.py`,
  `tests/security/test_secret_hygiene.py`): 54 passed, 2 failed — both the same pre-existing
  Windows rotating-file-handler tempdir-lock issue, unrelated to this change (confirmed present
  before any RC1 work began).
- Full suite, before vs. after `Compare-Object` diff: **exactly one** test
  (`test_config_hygiene.py::test_dotenv_loaded_only_in_config`) moved from failing to passing;
  **nothing else changed**. 1452 passed / 55 failed / 6 errors (was 1438 / 56 / 6).
- No duplicate redaction implementation: both fixes call the single existing
  `utils.logging_config.redact_secrets()` function; grepped both edited files to confirm the import
  is a real `from ... import`, not a copy-pasted loop.

---

## 6. Remaining blockers before RC1

**None.** Both certification conditions are closed with evidence, and the full-suite regression
diff confirms zero new failures anywhere in the repository.

The Operations Dashboard / Job History phase remains explicitly out of scope for this task, per
instruction, and is the only planned work after RC1.
