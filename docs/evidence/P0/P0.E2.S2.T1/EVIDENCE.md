# Evidence — P0.E2.S2.T1

**Date:** 2026-07-30
**Trace tag:** [H-7]
**Branch:** implemented directly on `master` (single-session, operator-directed continuation — see Time-gate note)

## Investigation

Audit finding H-7: `DB_PATH` was resolved independently in 20+ modules
instead of once. Three distinct sub-patterns were found by grepping every
`DB_PATH`/`walkforward.db` reference outside `_archive/`, `migrations/applied/`,
and `tests/`:

1. **8 modules duplicated the exact same wrong hardcoded absolute-path
   fallback** — `/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db`
   (wrong username, wrong directory layout for this repo — `tjiesar`/`10
   Projects` vs. the real `tjies`/`workspace/projects/5001`):
   `paper_trade.py`, `scheduler/scanner.py`, `scheduler/jobs.py`,
   `scheduler/reports.py`, `scheduler/utils.py`, `scheduler/__init__.py`,
   `engine/risk_alert.py`, `engine/regime_filter.py`'s `__main__` block, and
   `scripts/pattern_backtest.py`'s `DEFAULT_DB` — a stale example crontab
   line in `stockbit_fetcher.py`'s docstring also carried it.
2. **6 modules computed their own `__file__`-relative fallback and ignored
   the `DB_PATH` env var entirely** (ended at the same physical file by
   luck, but any operator override was silently dropped):
   `screener/brpt_filter.py`, `screener/reversal_filter.py`,
   `screener/idx_scraper.py` (also unnormalized — a literal `..` segment in
   the path string), `news_filter.py`, `screener/calculator.py`,
   `stockbit_fetcher.py`'s `WALKFORWARD_DB`.
3. **`research/jobs.py` + 3 `research/studies/*.py` files + `data/loaders.py`
   + `scripts/freeze_nr7_universe.py`** honored `DB_PATH` correctly but each
   duplicated the same `os.path.dirname(...)` fallback computation.
4. **`engine/strategies.py` had a worse variant**: two functions
   (`calc_opening_range_from_ticks`, `check_orb_intraday_signal`) defaulted
   `db_path` to the bare relative literal `'data/walkforward.db'` — not
   `__file__`-anchored at all, so a call from a different cwd resolves
   nowhere near the real DB — plus a third function (`get_ticker_data`) with
   the same relative literal hardcoded inline, no parameter at all.

**Root cause found during implementation, not before it:** while writing the
regression test for this task, `config.DB_PATH` itself failed the "must be
absolute" assertion when `DB_PATH` was set to this repo's own real `.env`
value. `.env`/`.env.example` ship `DB_PATH=data/walkforward.db` —
**relative**. `os.getenv("DB_PATH", <any absolute default>)` returns the env
var verbatim when it's set, so **every module's DB_PATH was resolving to a
relative path in the common case (env var present via `.env`), not just in
the fallback-unset case** — silently dependent on the process's cwd being
the repo root at launch. Centralizing *where* the fallback default is
computed (step 1 below) would not by itself have fixed this — the env
var's own value needed normalizing too. This is the literal H-7 defect
("resolve DB_PATH to an absolute path **once**"), not a secondary detail.

## Deliverable

- **`config.py`** (the single canonical resolution point):
  - `default_db_path()` — pure function, `_BASE / "data" / "walkforward.db"`
    as a string; no env read. The one place the *default value* is computed.
  - `resolve_db_path(raw)` — normalizes any `DB_PATH` value (from the env
    var, `.env`, or the default) to absolute, joining against `_BASE` if
    not already absolute. This is what actually fixes the root cause above.
  - `DB_PATH = resolve_db_path(os.getenv("DB_PATH", default_db_path()))`.
  - Module docstring's stale note (named "scheduler.py", which no longer
    exists as a single file post scheduler-split) corrected to name the two
    modules verified by actual test usage to need their own `os.getenv`
    call: `app.py` and `data/db.py`.
- **`app.py`, `data/db.py`** — verified via `grep -rn "importlib.reload("
  tests/` that these two are the *only* modules ever reloaded standalone
  (without `config` being reloaded first) while `DB_PATH` is monkeypatched
  via env var — every other reload site (`routes/chart.py`,
  `engine/delta_flow.py`, `routes/backtest.py`, `routes/screener.py`,
  `engine/agent_firm/*`) reloads `config` first, and no test reloads any
  `scheduler/` submodule at all (the doc comment's "scheduler.py" claim was
  stale — pre-dates the 2026-05-30 scheduler-split). Kept their own
  `os.getenv('DB_PATH', default_db_path())` call for reload compatibility,
  now wrapped in `resolve_db_path(...)` so they get the same absolute
  guarantee as everywhere else.
- **~20 modules converted to `from config import DB_PATH`** (or
  `as _DB_PATH` / `as WALKFORWARD_DB` where the local name differs), fully
  deleting their own fallback logic: the 3 duplicate-pattern groups above,
  minus `app.py`/`data/db.py`.
- **`engine/strategies.py`**: the two functions with a bare relative default
  switched to `db_path: str = None` + `if db_path is None: from config
  import DB_PATH; db_path = DB_PATH` inside the body — matching an idiom
  *already used* by a third function in the same file
  (`check_crash_recovery_signal`), not a new pattern. `get_ticker_data`'s
  unconditional relative literal replaced with `from config import DB_PATH
  as db_path`.
- **`screener/stockbit_screener.py`**: function-local fallback (only
  evaluated when the caller doesn't pass `db_path` explicitly) kept its
  per-call `os.getenv` re-read (existing behavior — always current env at
  call time, more fresh than a module-level import), but the fallback
  default and the final value are now `resolve_db_path(os.getenv("DB_PATH",
  default_db_path()))` instead of a locally duplicated computation.
- **`stockbit_fetcher.py`**: stale crontab-example path in the module
  docstring corrected (was a comment, not executable — but the same wrong
  path string, worth fixing for the same reason as everywhere else).

## Explicit scope exclusions (documented, not oversights)

- **`_archive/*.py`** — dead/archived code. Same boundary the H-1/H-2/AN-8
  audit used.
- **`migrations/applied/patch_adaptive_strategy.py`** — a `DB_PATH` string
  appears, but only inside a Python *source-code template string*
  (`NEW_FUNCTION = '''...'''`) meant to be spliced into a legacy single-file
  `scheduler.py` that no longer exists; this is an already-applied, one-off
  historical migration artifact, not live code.
- **`scripts/verify_flow_coverage.py`**'s `--db` argparse default
  (`'data/walkforward.db'`) — a manual diagnostic CLI tool, not imported by
  any other module, not scheduler-registered (confirmed clean by the AN-8
  audit's 37/37 check), conventionally run from the repo root like the
  repo's other `scripts/*.py` utilities. Left as-is: it is a leaf CLI
  default flag, not a module resolving "the" DB_PATH for other code to
  consume, and touching it is outside "config resolves DB_PATH once; all
  **modules** import it."
- **`.env` / `.env.example`**: left as `DB_PATH=data/walkforward.db`
  (relative) — no longer a bug now that `config.resolve_db_path()`
  normalizes any value, absolute or relative, so the example continues to
  demonstrate a valid, simpler-to-read configuration.

## Test output (named tests, new file)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && ./.venv/bin/python -m pytest -q tests/test_db_path_resolution.py -v'
```
```
collected 5 items
tests/test_db_path_resolution.py .....                                   [100%]
5 passed in 0.54s
```
5 tests in the new `tests/test_db_path_resolution.py`:
- `test_no_stale_hardcoded_db_path_remains` — repo-wide grep-audit (same
  idiom as `scripts/audits/an8_unregistered_jobs.py`) for the exact stale
  hardcoded string; fails if reintroduced anywhere in live code.
- `test_default_db_path_is_absolute_and_targets_data_dir`
- `test_config_db_path_falls_back_to_default_when_env_unset`
- `test_relative_env_db_path_still_resolves_absolute` — reproduces the real
  `.env`'s own relative value directly (`DB_PATH=data/walkforward.db`) and
  asserts `config.DB_PATH` is still absolute. This is the test that failed
  before the `resolve_db_path()` fix and is the direct regression guard for
  the actual root cause.
- `test_centralized_modules_resolve_to_config_db_path_by_default` — spot
  checks `data/db.py`, `paper_trade.py`, `scheduler/scanner.py`, and
  `screener/brpt_filter.py` (one from each of the three original duplicate
  categories) all agree with `config.DB_PATH`.

Confirmed each new/changed assertion fails against the pre-fix code: with
`config.py` reverted to `DB_PATH = os.getenv("DB_PATH", default_db_path())`
(no `resolve_db_path` wrapper), `test_relative_env_db_path_still_resolves_absolute`
fails with `assert False` (`Path("data/walkforward.db").is_absolute()` is
`False`) — this was empirically observed during implementation (see
"Root cause found during implementation" above), not asserted after the
fact.

## Regression run (full suite)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python -m pytest -q'
```
```
1274 passed, 1 skipped in 25.39s
```
Baseline (post-P0.E2.S1.T2) was 1,269 passed/1 skipped/0 failed; +5 from
`test_db_path_resolution.py`. 0 regressions, 0 failures. Targeted subset run
first: `tests/test_db_connect.py tests/test_market_schema.py
tests/test_health_endpoint.py tests/test_chart_routes.py
tests/test_bearish_signal_path.py` (the tests most directly exercising
`DB_PATH` reload/monkeypatch machinery) — 34 passed, run before the full
suite.

## Gate-script output

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python scripts/pre_merge_gate.py'
```
```
[PASS] QG-1 full test suite — 1274 passed, 1 skipped
[PASS] QG-4 schema drift — N/A (Phase 1 deliverable)
[PASS] QG-9 grep-audits — AN-8: 37 clean, 0 violations, 0 allowlisted (unaffected — no scheduler-job surface touched)
[PASS] QG-5 evidence presence — 8 done-task card(s) checked, all have evidence

GATE: PASS
```

## Direct smoke-import verification (outside pytest's reload machinery)

To rule out any circular-import regression across ~20 touched modules,
imported all of them in a single fresh interpreter process (real `.env` in
effect, not mocked) and printed each module's resolved `DB_PATH`:

```
python -c "import app, config, paper_trade, scheduler, scheduler.scanner, ... ; print(...)"
```
```
config.DB_PATH      = /home/tjies/workspace/projects/5001/data/walkforward.db
app.DB_PATH          = /home/tjies/workspace/projects/5001/data/walkforward.db
paper_trade.DB_PATH  = /home/tjies/workspace/projects/5001/data/walkforward.db
scheduler.DB_PATH    = /home/tjies/workspace/projects/5001/data/walkforward.db
scanner.DB_PATH      = /home/tjies/workspace/projects/5001/data/walkforward.db
brpt_filter._DB_PATH = /home/tjies/workspace/projects/5001/data/walkforward.db
stockbit_fetcher.WALKFORWARD_DB = /home/tjies/workspace/projects/5001/data/walkforward.db
ALL IMPORTS OK
```
All agree, all absolute, no import errors — including under the repo's real
(relative-valued) `.env`, the actual condition that exposed the root cause.

(`scripts/freeze_nr7_universe.py` was excluded from this smoke import: it
executes a real DB query at module import time — pre-existing script design
unrelated to this task — and raised `sqlite3.OperationalError: no such
table: wf_edge` against this sandbox's DB state, which has no bearing on
DB_PATH resolution; its `DB_PATH` line itself was verified by direct code
read, same as every other file in this task.)

## Decision entries filed

- `IMPL-DEC-008` — resolving relative `DB_PATH` env values to absolute via a
  shared `resolve_db_path()` normalizer, rather than only centralizing the
  *default* value (see `docs/EXEC-DECISIONS.md`).

## Self-review (EXEC-001 §3.1 step 3, checklist §5.1/§5.2/§5.4)

- Diff does only what the task card says: eliminate per-module DB_PATH
  fallback/resolution duplication, make resolution absolute everywhere. No
  drive-by changes — did not touch `load_dotenv()` calls, `.env` files, or
  unrelated constants in any touched file (e.g. `TELEGRAM_TOKEN`,
  `RESULTS` path in the two `research/studies/*.py` files were left
  untouched even though adjacent to the edited lines).
- No FROZEN surface touched; Phase 0 stays legacy-only.
- No new dependency, framework, or plugin point (ER-12) — `resolve_db_path`
  is `pathlib` only, already imported by `config.py`.
- Every touched module's final resolved `DB_PATH` value is unchanged from
  before this task for the normal runtime case (repo root cwd, real `.env`)
  — confirmed by the smoke-import output above all pointing at the one real
  `data/walkforward.db` file. This is a resolution-mechanism change, not a
  data-location change: no migration, no new file, no risk to which
  database gets opened in production.
- Task exists verbatim in PLAN-001 §3 (`P0.E2.S2.T1 ... [H-7]`); no
  forward-phase work smuggled in (ER-2) — the DB identity *Certifier* check
  (schema version, startup identity logging) is explicitly Phase 1 (P1.E4.S1)
  and P0.E2.S2.T2 respectively; this task is resolution-plumbing only.

## Cold review (EXEC-001 §4)

**Performed 2026-07-30, as an independent reviewer pass**, focused per the
operator's instructions on: hidden duplicate path resolution, startup edge
cases, configuration precedence, cross-platform path handling, regression
risk, migration safety.

- **Hidden duplicate path resolution:** re-ran the repo-wide grep after
  implementation (`grep -rn "os.getenv(.DB_PATH.\|walkforward\.db"` across
  all non-excluded `.py` files) — every remaining hit is either
  `config.py` itself, a docstring/comment mention of "walkforward.db" with
  no resolution logic, or the one documented scope exclusion
  (`scripts/verify_flow_coverage.py`). No hidden duplicates found.
- **Configuration precedence:** env var still wins over the default in all
  cases (`os.getenv("DB_PATH", default)` unchanged in shape); `resolve_db_path`
  only normalizes absoluteness, never overrides an explicit value's
  location. Verified by `test_relative_env_db_path_still_resolves_absolute`
  and the direct smoke import under the real `.env`.
- **Startup edge cases:** an already-absolute `DB_PATH` (e.g. an operator
  setting `DB_PATH=/custom/path/wf.db`) passes through `resolve_db_path`
  unchanged (`Path(raw).is_absolute()` short-circuits) — no double-joining
  risk. A `DB_PATH` with a leading `~` is *not* expanded (pre-existing
  behavior — neither the old nor new code called `expanduser()`); this is
  unchanged, not a regression, but flagged for the record: `~` in `.env`
  would resolve as a literal relative-looking segment today, in both the
  old and new code.
- **Cross-platform path handling:** `resolve_db_path` uses `pathlib.Path`
  throughout (`Path(raw)`, `.is_absolute()`, `_BASE / p`), the same
  primitive `config.py` already used for `_BASE`; no manual string
  concatenation introduced.
- **Regression risk:** full suite re-run clean (1,274/1,269 baseline);
  direct smoke-import of every touched module confirmed zero circular
  imports; the two genuinely reload-sensitive modules (`app.py`,
  `data/db.py`) were identified by grepping actual test usage
  (`importlib.reload(...)` call sites), not by trusting the pre-existing
  (and, for "scheduler.py", stale) code comment.
- **Migration safety:** no schema change, no data migration; this task only
  changes *how* the DB file path is computed, and the smoke-import evidence
  confirms it computes the identical path as before in the normal runtime
  case. Rollback is a plain `git revert`.

**0 findings requiring further code changes.** The one substantive
correction this task required — normalizing relative `DB_PATH` values, not
just centralizing the default — was found and fixed during implementation,
while writing the regression test (see "Root cause found during
implementation" above), before any cold-review pass; documented here rather
than silently folded in, per the same discipline `P0.E2.S1.T2`'s cold review
used for its own mid-flight correction.

**Time-gate note:** as with prior P0 tasks this cycle, this cold review
occurred in the same continuous session as the implementation; operator
explicitly directed continuation.
