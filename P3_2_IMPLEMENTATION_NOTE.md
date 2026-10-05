# P3-2 Implementation Note — live/backtest execution-model alignment

**Date:** 2026-09-30 · **Branch:** `fix/p3-execution-model-mismatch` (off `ops/hardening-2026-07-10` @ `90e1238`)
**Brief:** `ZCODE_BRIEF_P3_EXECUTION_MODEL_FIX_2026-09-30.md` · **Ruling §1 (a) — delay live fills to
next-bar-open — FOLLOWED as written.** No reason to prefer (b) surfaced in the code.

## The call sites actually found (re-located by symbol, as the brief required)

| # | Site | What it did | What it does now |
|---|------|-------------|------------------|
| 1 | `scheduler/scanner.py` `daily_signal_scan()` (16:00 WIB) — the TODO.md-cited bug | `scan_momentum_signals()` loads via `_load_ohlcv_bulk()` (partial bars, `is_final=0`) and the auto-open block called `open_trade(s["close"], …)` — the forming bar's latest price, straight into the insert | Signals **stage** (`paper_trade.stage_entry`); `run_staged_entry_fills` (09:10/10:10 next session) opens at that session's bar open |
| 2 | `scheduler/jobs.py` `run_premover_eod()` (16:30 WIB) — **found during this fix, not cited in TODO.md** | `premover_detector.run_scan()` reads `SELECT * FROM ohlcv` with **no `is_final` filter**; enforce mode called `open_trade(close_price, …)` — a possibly-provisional, always same-bar fill | Setups **stage** with the same mechanism; fill at next-session open |
| 3 | `scheduler/scanner.py` `scheduled_multi_strategy_scan()` (5×/day — re-verified in `scheduler/__init__.py`: 09:05/10:05/11:05/13:35/14:35) | Since audit L-2 (2026-09-02) this path routes every signal through `engine/entry_convention.executable_entry()`, which always returns STAGE — it **already never fills in-session** | **Unchanged** (already conforms); staged signals reach the EOD trade plan (report-only). No fill executor existed for it before this fix; the momentum/premover lanes now share the one that exists |

Note on site 1: the momentum lane is currently **admission-blocked** (`scan_momentum_signals`
requires Edge Registry admission for "Momentum Following", which has no entry — verified in
`registry/edge_registry.yaml`), so the bug is live-in-waiting rather than firing today. NR7_BULL v2
is SHADOW (D-029). The premover lane's auto-open is off unless `auto_trade_from_premover` is set in
`paper_config` (default `off`). The fix matters for the moment either lane activates; it does not
change today's live behavior on its own.

## The mechanism

- `paper_trade.staged_entries` table + `stage_entry()` / `resolve_staged_entries()`:
  a staged signal records ticker, strategy, signal bar date, and the decision price (audit trail
  only — never a fill). Resolution fills at **the open of the first bar dated after the signal
  bar** — the exact price every WF strategy fills at (`engine/entry_convention.py`). At fill time
  that bar is provisional (`is_final=0`), but its open was fixed by the session's first print;
  the bar's *close* — the old bug's price — can never reach a fill.
- Window semantics: fill window is the ticker's **first session after the signal bar** (bar-history
  based, so weekends/holidays/suspensions behave). Miss it (bar never published, position slots
  full, duplicate position) → the entry is `SKIPPED`/`EXPIRED`, never filled at a retrospective
  price — the L-2 defect is structurally unreachable, including "one day late" variants.
- `scheduler/jobs.run_staged_entry_fills()` (registered 09:10 + 10:10 Mon–Fri in
  `scheduler/__init__.py`): runs the yfinance incremental fetch (ohlcv otherwise has no bar for
  the current session until the 16:00 fetch), then resolves. `open_trade()`'s own guards (DD
  breaker, max_open, duplicate, 3-day SL cooldown, ARA/ARB caps, sizing) own all fill-time
  validation — the resolver maps its error dict to a skip.
- Signal detection upstream is untouched: same filters, same thresholds, same forming-bar input.
  This is a fill-timing fix only, per the brief.

## Found but deliberately NOT changed (bigger gap, listed per brief §3)

- **Exits:** `monitor.py`'s hourly open-trade monitor closes trades at `_get_current_price()` —
  the latest ohlcv close including provisional bars (intraday that is typically *yesterday's*
  settled close; after 16:00 it is the provisional bar). The backtest exit model evaluates
  completed bars with a 1-bar trailing-stop lag. Aligning exit timing to the backtest model would
  delay stop-loss response — a live risk-profile change, not a fill-timing correction, and it
  deserves its own explicit decision before anyone ships it.
- **Manual opens** (`routes/backtest.py:912`): the API route takes an operator-supplied price.
  User-driven, out of scope.
- `premover_detector.run_scan()`'s raw `SELECT *` (no finality filter) is left as-is for
  *detection* — the brief forbids changing upstream detection, and the staged fill no longer
  consumes its price as a fill. Worth a look when P4-9 scores the never-tested strategies.

## P3-3 — NOT done (Owner call, flagged ready)

Resetting the forward-test/shadow clock remains TODO.md P3-3 and is an Owner decision: any
forward-test evidence collected under the old model is not evidence for the new one, and restarting
the window touches live paper-trade history Tjie may be watching. The code side is ready for it.

## Test evidence (real tally)

`DB_PATH=data/walkforward.db ./venv/bin/python -m pytest -q` (WSL, Python 3.12.13 venv — CI-matching;
**the `DB_PATH` override is required on this box**: the tree's `.env` carries the production XPS-13
path `/home/tjiesar/10 Projects/...`, which doesn't exist in WSL and breaks any test that touches
the default DB before monkeypatching — 4 tests in `tests/test_scanner_to_open_trade_integration.py`
fail for that reason alone, verified against a pristine worktree of `90e1238`).

- New: `tests/test_entry_staging.py` — 8 passed (fill==next bar's open ≠ forming close ≠ decision
  price; same-day signal never fills; missing bar stays pending; missed window expires;
  suspension-resume fills at first traded open; duplicate/max_open skip).
- Full suite tally (`logs/pytest_full_20260930_p3.log`, 2026-09-30, WSL Python 3.12.13):
  **12 failed, 3446 passed, 3 skipped in 467.84s.** All 12 verified pre-existing/environmental,
  none in touched code — each reproduced or root-caused independently:
  - 6× `tests/test_config_validation.py` + 1× `tests/agent_firm/providers/test_provider_hierarchy.py`:
    caused by the tree's `.env` (production XPS-13 paths/keys). Reproduced 11/12 on a pristine
    `90e1238` worktree **with this tree's `.env` copied in**; with no `.env` (CI condition) they
    pass.
  - 4× `tests/test_value_format.py`: shells out to `node`, not installed in WSL.
  - 1× `tests/security/test_secret_hygiene.py`: trips on untracked vendored packages
    (`.winvenv/Lib/site-packages/langsmith/client.py`) sitting in the working tree — a P0-5
    untracked-pile symptom, not a source change (passes on the pristine worktree).

## Deployment boundary

Not deployed (per brief §3): no `deploy/crontab` change, no production restart. The new scheduler
jobs activate on the next deliberate release; `staged_entries` creates itself idempotently on first
use (`CREATE TABLE IF NOT EXISTS`, repo convention).

## Addendum — independent WSL verification (2026-10-01, ZCode session)

Re-verified the branch on WSL against the brief, on top of the 2026-09-30 sessions:

- **Mutation check — the regression tests genuinely pin the bug.** Temporarily mutating
  `resolve_staged_entries` to fill at the bar's `close` (the old same-bar semantics) fails
  `test_fill_price_is_next_bar_open_not_forming_close` and
  `test_suspension_resume_fills_at_first_traded_open`; restored, all pass.
- **Call-site sweep re-done independently** (`grep open_trade(` across live paths): the table above
  is complete. `scheduler/scanner.py`'s remaining `open_trade` (multi-strategy lane) sits behind
  `executable_entry()`, which can only return STAGE/REJECT in the current code — unreachable today,
  and any future FILL it returned would by contract use a genuinely obtainable price. Other hits:
  `routes/backtest.py` manual open (operator price, by design), `engine/historical/runner.py`
  (different `_open_trade` symbol), `migrations/applied/*` (historical scripts). `monitor.py`'s
  exit path reads the latest close with no `is_final` filter — the deferred exit-timing gap, real
  as described.
- **Fix: `stage_entry()` silently dropped its `note` parameter** — the premover lane passes
  `pattern={..} score={..}` there and it never reached the INSERT. Now persisted
  (`test_note_persisted_for_audit_trail` pins it). Audit-trail only; fill semantics unchanged.
- **Full-suite tally (WSL, Python 3.12.13 venv, `DB_PATH=data/walkforward.db`,
  `logs/pytest_full_20261001_p3_zcode.log`): 8 failed / 3451 passed / 3 skipped in 394.39s.**
  vs the 2026-09-30 baseline (12F/3446P/3S): +1 pass is the new note test; +4 passes are
  `tests/test_value_format.py` — `node` (v24.18.0) is now installed in WSL. All 8 remaining
  failures environmental, none in touched code, each re-derived this run: 6×
  `test_config_validation.py` + 1× `test_provider_hierarchy.py` (the tree's production `.env` on
  the 777-mode /mnt/d drvfs mount trips the chmod-600 startup check, and its provider override
  reorders the router — CI runs without `.env` and passes), 1× `test_secret_hygiene.py` (untracked
  vendored `.winvenv/` Windows packages). `tests/test_entry_staging.py`: 9/9 pass.
