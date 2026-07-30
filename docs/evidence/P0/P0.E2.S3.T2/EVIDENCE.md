# Evidence — P0.E2.S3.T2

**Date:** 2026-07-30
**Trace tag:** [L-3]
**Branch:** implemented directly on `master` (single-session, operator-directed continuation — see Time-gate note)

## Verification (before coding)

- `docs/PLAN-001-Implementation-Master-Plan.md` §3, line 83: "T2: delete
  dead `_parse_args` `[L-3]`" — confirms this is the correct task.
- `docs/EXEC-STATUS.md` §7 "Next up", item 1: `P0.E2.S3.T2` — confirmed
  still next.
- `git log --oneline -5` showed `P0.E2.S3.T1` (`c12a963`) as `HEAD`, no
  intervening work; `git status` showed no `p0/e2-s3-t2-*` branch and no
  stray uncommitted work touching `stockbit_fetcher.py`. No discrepancy
  found.
- Traced `[L-3]` to the original audit:
  `Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` line 328: "**L-3:**
  `stockbit_fetcher._parse_args` is dead and buggy (self-referential list
  comprehension); `main()` re-implements parsing correctly. Delete."

## Confirming the code was truly dead (before deleting anything)

- **Every definition:** `grep -rn "_parse_args\b" --include="*.py" .`
  (excluding `.venv`/`__pycache__`) returned exactly one hit in the
  entire repository: the definition itself, `stockbit_fetcher.py:385`.
- **Every reference, code and non-code:** a second, unrestricted
  `grep -rn "_parse_args" .` (no file-type filter, so it also covers
  docs, configs, anything else) found the definition plus five
  documentation mentions (`PLAN-001`, `EXEC-STATUS.md`, this task's own
  `TASK-CARD.md`, and two `Audit/` lines) — all of them text *about* this
  task, none of them a call site.
- **Runtime entry points:** `stockbit_fetcher.py` has exactly two,
  both at `if __name__ == "__main__":` (line ~847): `main()` (default —
  the keystats fetcher) and `_run_flow_cmd()` (the `flow` subcommand).
  Read both in full:
  - `main()` (lines 407+) parses `--token` and `--cat` **inline**
    (`args = sys.argv[1:]`, then hand-rolled `if "--token" in args:` /
    `if "--cat" in args:` blocks) — never calls `_parse_args`. Its own
    `--cat` removal (`args = args[:i] + args[i + 2:]`) is a simple,
    correct slice — not the buggy comprehension `_parse_args` had.
  - `_run_flow_cmd()` (lines 808+) independently re-implements
    `--token`/`--cat`/`--date` parsing **again**, inline, with the same
    correct slice-based removal pattern — a third variant of the same
    logic, also never calling `_parse_args`.
  - Confirms the audit's exact characterization: `_parse_args` was
    superseded by (not shared by) both live entry points, each of which
    already re-implements the same parsing correctly on its own.
- **Test coverage of the dead function:** none existed —
  `grep -rln "stockbit_fetcher" tests/` found 5 files, none referencing
  `_parse_args`; all reference unrelated things (`fetch_keystats`/
  `save_keystats` patches, file-listing membership checks for other
  audits). No test needed updating or would break from the deletion.
- **Post-deletion confirmation:** `grep -n "_parse_args" stockbit_fetcher.py`
  returns nothing (exit 1); `python -c "import stockbit_fetcher;
  print(hasattr(stockbit_fetcher, '_parse_args'))"` prints `False`;
  `ast.parse()` on the file succeeds (valid syntax); `import
  stockbit_fetcher` succeeds cleanly.

**Conclusion: unambiguously dead code, zero live or indirect references,
zero test coverage of the deleted function.** No live usage found — safe
to delete per the task's own stop condition.

## Fix

Deleted `stockbit_fetcher.py:385-404` (the entire `_parse_args` function,
its docstring, and its body) verbatim — no other lines touched. `main()`
(now directly following the prior function, `save_keystats`) is
unchanged; the file's existing two-blank-line-between-functions
convention is preserved at the deletion site.

**No unused imports or constants to remove:** `_parse_args`'s only
import dependency was `sys` (`sys.argv` at line 400), which remains
actively used elsewhere in the file (`main()`'s own `sys.argv`/`sys.exit`,
`_run_flow_cmd`'s `sys.argv`/`sys.exit`) — nothing became orphaned.

**No refactoring of `main()` or `_run_flow_cmd()`:** both entry points'
own inline parsing is left exactly as it was — this task deletes
unreachable dead code, it does not consolidate or clean up the two live
(and structurally similar) parsing blocks that remain. Consolidating
them was considered and explicitly rejected as out of scope: the task
card says "delete dead `_parse_args`," not "deduplicate CLI parsing";
touching either live entry point's own logic would be exactly the
"opportunistic refactoring" / "unrelated CLI code" this task's rules
forbid, and PLAN-001 does not list a task for it.

## Tests

New `tests/test_stockbit_fetcher_cli.py`, 4 tests:
- `test_parse_args_function_no_longer_exists` — regression guard;
  confirmed to have **failed** against pre-fix `HEAD`
  (`git show HEAD:stockbit_fetcher.py | grep -c _parse_args` → `1`, so
  `hasattr(..., '_parse_args')` was `True` before this task) and to pass
  after the deletion — a genuine, not vacuous, guard against
  reintroduction.
- `test_main_parses_token_flag` — exercises `main()`'s own (surviving,
  correct) `--token` parsing end-to-end up to the point it cleanly
  `sys.exit(1)`s on no token (before any DB/network side effect),
  confirming the extracted token value reaches `ensure_valid_token`
  unchanged.
- `test_main_parses_cat_flag` — exercises `main()`'s own `--cat` parsing:
  category is extracted, uppercased, and correctly excluded from further
  ticker resolution — the exact class of correctness `_parse_args`' bug
  put at risk, proven here on the surviving code path instead.
- `test_main_explicit_tickers_override_category` — control: positional
  ticker args bypass `get_tickers()`/category resolution entirely,
  `main()`'s own documented behavior, unrelated to and unaffected by the
  deletion, included so the other two tests aren't the only signal that
  `main()` still works at all.

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && ./.venv/bin/python -m pytest -q tests/test_stockbit_fetcher_cli.py -v'
```
```
collected 4 items
tests/test_stockbit_fetcher_cli.py ....                                  [100%]
4 passed in 0.64s
```

## Regression run (full suite)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python -m pytest -q'
```
```
1287 passed, 1 skipped in 25.25s
```
Baseline (post-`P0.E2.S3.T1`) was 1,283 passed/1 skipped/0 failed; +4 from
`test_stockbit_fetcher_cli.py`. 0 regressions, 0 failures. Targeted subset
run first: `tests/test_stockbit_fetcher_cli.py tests/test_fundamental_refresh.py
tests/test_architecture_boundary.py tests/test_research_data_fence.py
tests/test_db_centralization.py` (every existing test file that touches
`stockbit_fetcher.py` at all) — 34 passed, run before the full suite.

## Gate-script output

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python scripts/pre_merge_gate.py'
```
```
[PASS] QG-1 full test suite — 1287 passed, 1 skipped
[PASS] QG-4 schema drift — N/A (Phase 1 deliverable)
[PASS] QG-9 grep-audits — AN-8: 37 clean, 0 violations, 0 allowlisted (unaffected — no scheduler-job surface touched)
[PASS] QG-5 evidence presence — 8 done-task card(s) checked, all have evidence

GATE: PASS
```

## Decision entries filed

None. No `§8`-classifiable event — a straightforward dead-code deletion
with an unambiguous, exhaustively-verified root cause (zero call sites)
already fully specified by the original audit. The one judgment call
(leave the two live entry points' duplicated-but-correct inline parsing
alone, rather than consolidating them) is documented above under "Fix"
rather than as a numbered decision — it is a scope boundary, not a
design choice among materially different implementations of *this*
task.

## Self-review (EXEC-001 §3.1 step 3, checklist §5.1/§5.2/§5.4)

- Diff does only what the task card says: one function deleted, one new
  test file. No drive-by changes — `main()`, `_run_flow_cmd()`, and every
  other function in `stockbit_fetcher.py` are byte-for-byte unchanged.
- No FROZEN surface touched; Phase 0 stays legacy-only.
- No new dependency (ER-12).
- No forward-phase work smuggled in (ER-2) — did not consolidate the two
  live entry points' duplicated parsing logic, did not add new CLI
  flags, did not touch `_run_flow_cmd()`.
- Task exists verbatim in PLAN-001 §3 (`P0.E2.S3.T2 ... [L-3]`).

## Cold review (EXEC-001 §4)

**Performed 2026-07-30, as an independent reviewer pass**, against the
operator's explicit checklist:

- **No remaining references:** repo-wide grep (unrestricted, not just
  `.py`) re-run post-deletion found zero code references; the only
  remaining hits are documentation *about* this task (expected, and
  correctly so — the audit report is a read-only historical record of
  what was true at audit time, not edited by this or any prior P0 task).
- **No import regressions:** `sys`, the only module `_parse_args`
  touched, remains in active use in both surviving entry points;
  `ast.parse()` confirms valid syntax; a real `import stockbit_fetcher`
  succeeds with no errors.
- **No CLI behavior changes:** `_parse_args` was unreachable — deleting
  unreachable code cannot change reachable behavior by construction. New
  tests independently exercise `main()`'s actual, surviving parsing
  (`--token`, `--cat`, and the explicit-tickers-override-category case)
  and confirm it works exactly as the audit said it already did,
  correctly, before this task touched anything.
- **No dead code left behind:** checked whether any other code existed
  solely to support `_parse_args` (helper functions, constants) — none
  found; its only dependency was the already-used `sys` import.
- **Documentation consistency:** `Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md`
  is the only doc describing `_parse_args`'s bug in detail, and it is an
  explicitly read-only, point-in-time record — correctly left unedited,
  same treatment as `P0.E2.S3.T1`'s audit citation. `EXEC-STATUS.md` and
  `GATE.md` are the live trackers and are updated below.
- **Maintenance implications:** strictly positive — 20 lines of dead,
  buggy code removed; no new abstraction, no new surface added; the two
  remaining independent inline-parsing implementations are pre-existing
  (not introduced by this task) and intentionally left alone per the
  task's own scope.

**0 findings.** No code changes required as a result of this review.

**Time-gate note:** as with every P0 task this cycle, this cold review
occurred in the same continuous session as the implementation; operator
explicitly directed continuation.
