# Paper Trading Operating Procedure

**Version:** 1.0 · **Status:** ACTIVE · **Effective Date:** 2026-07-29
**Scope:** Operating procedures specific to the paper-trading lifecycle — entry validation, exit
validation, duplicate detection, risk monitoring, daily reporting, and incident handling — for the
IDX Walkforward Strategy Suite's `paper_trade.py`/`monitor.py` pipeline. Companion to
`Audit/PRODUCTION_DEPLOYMENT_GUIDE.md` (deployment mechanics) and `Audit/OPERATIONS_RUNBOOK.md`
(general daily/weekly/monthly cadence). This document does not change any trading logic — every gate
and threshold cited below is quoted from the current implementation, not proposed.

---

## 1. Entry Validation

Entries are opened via `paper_trade.py::open_trade()` (called from the scanner/scheduler pipeline
and, for premover signals, dry-run-checked first via `evaluate_premover_trade()`). Gates, in the
order the code actually evaluates them:

1. **DD circuit breaker** (`cfg.get("entries_blocked", 0) >= 1` / `is_entries_blocked()`) — if the
   drawdown circuit breaker has tripped, no new entries are accepted regardless of signal quality.
   Operator action: confirm via `check_dd_circuit_breaker()` / the DD status route why it tripped
   before considering any override.
2. **Max open positions** (`len(open_trades) >= max_open`, configurable, `cfg["max_open"]`) — a hard
   cap on concurrent exposure.
3. **Duplicate position** (`any(t["ticker"] == ticker for t in open_trades)`) — see §3.
4. **3-day stop-loss cooldown** — a ticker that was stopped out at a loss (`exit_reason IN
   ('STOPPED_OUT','SL','TRAIL','MA_BREAK','R7_TRAIL_SL')`) within the last 3 days is refused re-entry
   (`paper_trade.py:302-314`). This exists to prevent immediate re-entry into a name that just proved
   the thesis wrong, and covers every stop-family exit reason across the strategy engine's history
   (not just the current engine's naming), by design.
5. **Regime filter** (when `cfg.get('filter_regime', 1)` is on) — reads `backtest_cache`, does not
   load fresh OHLCV, gates entry against the current regime classification.
6. **SL/TP level computation** — `atr = _calc_atr_from_db(ticker)`, then initial stop/target come
   from the strategy's own exit policy (`engine.exits.get_policy(strategy).initial_levels(...)`) —
   **not** a blanket 2×ATR/3×ATR bracket for every strategy. An explicit caller-supplied `sl_price`/
   `tp_price` (e.g. from the Swing Onset screener or counter-trend levels) always wins over the
   computed default.

**Entry validation checklist (operator review, not a code gate):**
- [ ] For any manually-opened trade (via API/UI rather than the automated scanner), confirm the
      same gates above were actually evaluated — `open_trade()` is the single entry point; do not
      construct a `paper_trades` row by any other path.
- [ ] Spot-check that `strategy` on new trades resolves to the intended value —
      `get_best_strategy_for_ticker(ticker)` is the default when no strategy is explicitly passed;
      confirm this isn't silently picking an unintended strategy for a ticker with thin backtest
      history.
- [ ] Confirm the computed SL distance/percentage looks sane for the instrument's typical daily
      range — a zero or near-zero ATR (illiquid ticker, data gap) can produce a degenerate stop.

---

## 2. Exit Validation

Exits run through `monitor.py::check_all_open_trades()`, called on the scheduler's monitoring
cadence. Two paths depending on strategy:

**Swing Trend strategy** (`_evaluate_swing_trend()`):
- Evaluates R1–R7 trigger conditions; trailing state (`sl_price`, `highest_seen`, `adx_peak`) is
  persisted on every tick regardless of whether a close is triggered.
- For probabilistic closes specifically tagged `R3_ADX_FADE` or `R4_DISTRIBUTION`, the agent firm
  gets an explicit veto (`_agent_confirms_exit()`) before the close is allowed to execute — if the
  agent does not confirm, the action is downgraded from `CLOSE` to `HOLD` and logged
  (`monitor.py:569-576`). This is a deliberate, narrow human-analogue check on exactly two
  lower-confidence exit triggers — R1/R2/R5/R6/R7 (and any others) close without an agent veto.
- On close: `close_trade(id, exit_price, reason, notify=False)`, then a Telegram message is sent
  separately if `result.get('message')` is set, and the alert is logged via
  `screener.db.log_trade_alert`.

**Non-swing strategies** (`_check_trade()`):
- Standard SL/TP/trailing-stop evaluation. Trailing-stop updates (`trail_update`) are persisted the
  same way — `sl_price`/`highest_seen` updated in-place even on ticks that don't close the trade.

**Known gap — no per-trade exception isolation (`Audit/PRODUCTION_ENGINE_BACKLOG.md` P1-4):** the
loop in `check_all_open_trades()` iterates all open trades in one pass; an unhandled exception
evaluating one trade is not currently isolated from the rest of that tick's trades. If a specific
ticker's data is malformed (e.g. a missing bar), it can abort evaluation for every ticker after it
in iteration order for that tick, silently (no exception surfaces as a per-trade alert distinct from
whatever generic error logging catches it). **Operational mitigation until this is fixed in code:**
if a trade appears to have missed an expected SL/TP/trailing update on a given day, check
`logs/app.log` for an unhandled exception on an *earlier*-evaluated ticker in the same monitoring
tick, not just the ticker of interest.

**Exit validation checklist:**
- [ ] For every closed trade, confirm `exit_reason` is one of the known values (SL/TP/TRAIL/TIME/
      STALE/MANUAL/STOPPED_OUT/R1–R7 codes) — an unrecognized exit reason is itself worth
      investigating, since it suggests a code path outside the normal `close_trade()` flow.
- [ ] For swing-trend `R3_ADX_FADE`/`R4_DISTRIBUTION` triggers, spot-check a sample of agent-vetoed
      HOLDs — confirm the veto reasoning (visible in the agent decision trail) is substantive, not a
      fail-soft default masquerading as a real review (a fail-soft/timeout path should be
      distinguishable in the trace from a genuine model judgment).
- [ ] Confirm trailing-stop persistence (`sl_price`/`highest_seen`) is monotonic in the expected
      direction for the position side — a trailing stop that moved backward would indicate a bug in
      the update logic, not normal behavior.

---

## 3. Duplicate Detection

Two independent code paths both enforce "one open position per ticker," and they agree:

- `open_trade()` (`paper_trade.py:299-300`): `if any(t["ticker"] == ticker for t in open_trades):
  return {"error": f"{ticker} sudah ada posisi terbuka"}`.
- `evaluate_premover_trade()` (`paper_trade.py:716-719`, the dry-run gate check used before a
  premover signal is even attempted): identical `any(t['ticker'] == ticker ...)` check, returning
  `skip_reason: 'already_open'`.

Both operate against `get_open_trades()` — a single live query, not a cached/stale list — so there
is no TOCTOU window between "check" and "open" beyond normal SQLite transaction semantics (a
`data.db.connect()`-based connection with `busy_timeout` covers serialization under concurrent
writers).

**Separately, at the reporting layer:** the EOD/Premarket watchlist snapshot/diff mechanism
(`engine/trade_plan.py::record_snapshot()`/`diff_watchlist()`) and the three daily Telegram jobs use
a `_job_sentinel(job, run_date)` composite-primary-key table — first `INSERT` wins — as a *report*
duplicate-send guard, distinct from the *trade* duplicate-position guard above. Do not conflate the
two: a duplicate report-send is a cosmetic/annoyance issue; a duplicate open position on the same
ticker would be an actual risk-sizing error. Both are structurally prevented today, by different
mechanisms, for different reasons.

**Duplicate detection checklist:**
- [ ] If you ever see two open `paper_trades` rows for the same ticker, treat it as a P0 defect
      investigation, not routine — the code path to produce this does not exist today under normal
      operation; its presence would indicate either direct DB manipulation outside `open_trade()`,
      or a genuine new bug.
- [ ] Confirm any manual/API-driven trade-opening path routes through `open_trade()` and not a
      direct `INSERT` — this is the single point where the duplicate gate is enforced.

---

## 4. Risk Monitoring

- **Position sizing input:** `agent_size_hint` is now written exactly once per candidate by
  `engine/position_sizing.py::resolve_size_hint()`, called from `scheduler/scanner.py`'s
  `resolve_agent_size_hints()` after both `run_edge_veto_stage()` and `run_agent_firm_gate()` have
  run (`scanner.py:1659`). **P0-1/ADR-AF-003 (Sizing Ownership) is resolved** — see
  `Audit/OPERATIONAL_HARDENING_REPORT.md` (2026-07-29) for the verification trail. The former
  collision (`scanner.py:962`/`1013` both unconditionally writing `agent_size_hint`, the second
  silently discarding the first) no longer exists: neither stage writes the field directly anymore
  (each only contributes an input — `edge_score` or `agent_size_tier`), enforced structurally by
  `tests/test_sizing_single_writer_invariant.py`'s source scan and behaviorally by
  `tests/test_sizing_collision_regression.py`. **Live production `EDGE_SCORE_MODE` was directly
  re-verified (SSH, 2026-07-29) as `shadow`**, not `enforce` — the collision was dormant in
  production even before this fix (the edge-veto stage's write only ever fired under `enforce`) —
  but the code-level defect is now eliminated regardless of mode. This change is currently
  **uncommitted** in the working tree (same caveat as §6's ADR-AF-002 note) — confirm it has been
  committed and deployed before relying on this resolved status in a running production process.
- **DD circuit breaker** (`paper_trade.py::check_dd_circuit_breaker()`, `compute_drawdown()`) —
  monitors realized drawdown over a rolling window (default 30 days) and blocks new entries
  (`is_entries_blocked()`) when tripped, without touching existing open positions. Review trip
  history and current state daily (§1.3 of the Operations Runbook) and weekly (§2.3).
- **Max open positions** — a hard cap (`cfg["max_open"]`, default 5) independent of DD state; both
  gates apply simultaneously, not as alternatives.
- **Stop-loss cooldown** — see §1 item 4; functions as a soft risk control against immediate
  re-entry churn on a name that just stopped out.
- **Agent-firm risk specialist veto** (`engine/agent_firm/agents/risk.py`) — part of the pre-trade
  agent review pipeline; consumes Tier 1 context objects assembled by
  `engine/agent_firm_context.py` per ADR-AF-002 (complete as of 2026-07-29 per `CLAUDE.md`'s own
  amendment — but see §6's note on this being uncommitted in the current working tree).

**Risk monitoring checklist:**
- [x] P0-1 sizing collision resolved and verified (2026-07-29) — no action item remains here beyond
      confirming the fix is committed/deployed (see §6).
- [ ] Daily/weekly DD circuit-breaker state reviewed (cross-reference Operations Runbook §1.3/§2.3).
- [ ] No open position exceeds what `max_open` and the sizing pipeline should have allowed —
      periodic manual cross-check, not just trust in the gates.

---

## 5. Daily Report Generation

The three daily Telegram reports are the primary paper-trading visibility mechanism. All three are
strictly reporting-only — none recomputes a score, rank, or exit decision; each reads
already-decided engine outputs (`CLAUDE.md`, verified independently in
`Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md`'s validation section).

| Report | Job | Time (WIB) | Paper-trading relevance |
|---|---|---|---|
| Premarket Shortlist | `scheduler.jobs.run_premarket_firm_scan` | 08:35 | Firm-vetted candidate shortlist for the day, with watchlist diff (NEW/REMOVED/UPGRADED/DOWNGRADED/STABLE) against yesterday's premarket snapshot (`strategy='premarket'` in `watchlist_snapshot`) |
| EOD Trade Plan | `scheduler.jobs.run_eod_trade_plan` | 16:40 | Consolidated agent-ranked long shortlist + Watchlist Changes vs. the prior EOD snapshot (`strategy='eod'`) — the primary daily "what would/did we trade" artifact |
| Forward-Testing Summary | `scheduler.jobs.run_forward_test_cycle` | 18:30 | `forward_testing/reporting.py` reads `ft_shadow_position`/`ft_shadow_trade` directly — new/closed/active shadow positions, cumulative win/loss scoreboard, best/worst closed trades, exit reasons shown verbatim |

All three share the `_job_sentinel(job, run_date)` dedup table — do not manually re-trigger a job to
"regenerate" a report; if a report needs to be resent, do it as an explicit manual message, not a
job re-run (re-running risks either a duplicate send if the sentinel allows it, or a silent no-op if
it doesn't — neither is the intended path).

**Daily report checklist:**
- [ ] All three reports received by their expected time (±5 min for scheduler jitter).
- [ ] EOD Watchlist Changes section reviewed against your own read of the day — confirm
      upgrades/downgrades correspond to real rank/confidence shifts, not stale data.
- [ ] Forward-Testing scoreboard reviewed for the day's net effect on the cumulative win/loss
      picture — a single bad day is not itself an incident, but a multi-day negative trend not
      explained by regime is worth escalating to §6 (weekly review) early rather than waiting.

---

## 6. Incident Handling

Paper-trading-specific incidents beyond the general categories in
`Audit/OPERATIONS_RUNBOOK.md` §5 (scheduler crash, Telegram delivery, provider exhaustion, DB
lock/corruption, disk full, heartbeat trip — all apply here too and are not repeated):

### 6.1 A trade opened that should have been blocked by a gate

1. Identify which gate should have fired (§1) and pull the actual `open_trade()` call's inputs from
   `logs/app.log` around the open timestamp.
2. Check whether the trade was opened via the normal scanner/scheduler path or a manual/API call —
   a manual call bypassing intended pre-checks (e.g. calling with an explicit `sl_price` that skips
   the cooldown check's *effect* even though the cooldown check itself still ran) is a different
   root cause than a genuine gate-logic bug.
3. If it's a genuine gate-logic defect (the gate ran, evaluated correctly per its current code, but
   the code itself has a bug), this is a P0-class code defect — do not attempt an in-session hotfix
   without going through normal review; instead, manually close the position if risk warrants it and
   file the defect for proper fix-and-test.

### 6.2 A closed trade's exit reason looks wrong

1. Pull the full `_check_trade()`/`_evaluate_swing_trend()` evaluation trail for that trade from
   `logs/app.log` for the tick that closed it.
2. Distinguish three cases: (a) the exit logic is correct and the reason accurately reflects it —
   not an incident; (b) the exit logic is correct but exposes a known gap (e.g. the missing
   per-trade exception isolation in §2 masked an earlier failure that tick) — log as a known-gap
   occurrence, prioritize the underlying fix; (c) genuinely wrong exit logic — P0-class defect,
   same escalation as §6.1.

### 6.3 Watchlist snapshot/diff looks inconsistent between Premarket and EOD

1. Remember `strategy='premarket'` and `strategy='eod'` are **independent** histories in
   `watchlist_snapshot` (composite key `(date, strategy, ticker)`) — an EOD "NEW" entry for a ticker
   that was already on the morning's premarket shortlist is expected behavior (different
   comparison base), not a bug.
2. If a ticker appears with contradictory conviction/confidence between the two same-day reports,
   check whether intraday data (flow, price action) genuinely changed between 08:35 and 16:40 before
   assuming a data or diff-logic bug.

### 6.4 Agent firm review appears absent or degenerate for a signal

1. Check `provider_events` and the agent decision trail for that signal's timestamp — determine
   whether this was a genuine fail-open (both providers exhausted, per Operations Runbook §5.3) vs.
   a configuration issue (`AGENT_FIRM_ENABLED=false`, or a single-provider router silently missing
   failover).
2. A fail-open signal should still be clearly marked as such in whatever trail records the decision
   — if it's indistinguishable from a genuine agent review in the data, that's worth flagging as an
   observability gap (tracked generally under the Operations Dashboard milestone,
   `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`'s "unexpected fail-soft activations" metric).

---

## 7. Weekly Operating Procedure (paper-trading-specific)

- [ ] Closed-trade review: win rate, average R-multiple, exit-reason distribution for the week
      (SL/TP/TRAIL/TIME/STALE/R1–R7) — compare against the strategy's known backtest profile; a
      material live/backtest divergence is worth investigating before it compounds over more weeks.
- [ ] DD circuit-breaker trip history for the week — count, duration blocked, and whether each trip
      resolved as expected.
- [ ] Sample gate-rejection review — pull a handful of `evaluate_premover_trade()` rejections
      (`dd_circuit_breaker`, `max_open_N`, `already_open`, regime-filter) and confirm they look like
      correct rejections, not a gate firing on bad/stale input.
- [ ] Cross-check `EDGE_SCORE_MODE` hasn't changed since the last check (§4) — a mode change is a
      config event significant enough to warrant its own re-verification of the P0-1 sizing risk.
- [ ] Forward-testing scoreboard trend (cumulative win/loss) reviewed for the week as a whole, not
      just daily snapshots — a week-level view surfaces slower drifts a single day's report won't.

---

## 8. Production Launch Recommendation

**Recommendation: Continue paper trading; do not treat this as a transition to live capital yet.**
This assessment is scoped strictly to paper-trading continuation readiness, not a live-capital
go/no-go (this repository's own invariants — Research/Production separation, human-gated promotion —
mean a live-capital decision is out of scope for this document entirely).

**Supporting the recommendation (ready today):**
- The deployment mechanism (release/rollback/backup/restore) is built, tested, and has passed a
  real restore drill on production-scale data (2026-07-10).
- The core paper-trading gates (entry validation, duplicate detection, DD circuit breaker, exit
  logic including the agent-firm exit veto) are implemented, code-verified in this review, and
  structurally sound — no gap found in this review's inspection of the gating logic itself.
- The three daily reports give continuous, meaningful visibility into paper-trading performance
  without requiring a dashboard to exist first.
- ADR-AF-002 (Agent Firm Tier 1 Context Ownership) is reported complete, closing a real
  producer/consumer context-wiring gap that predated it.

**Open items to resolve or explicitly accept before treating paper trading as fully hardened**
(all sourced from `Audit/PRODUCTION_ENGINE_BACKLOG.md`, dated 2026-07-29 — the current canonical
list; do not rely on any older audit report's status claims over this one):

| Priority | Item | Why it matters for paper trading specifically |
|---|---|---|
| ~~P0-1~~ | ~~Implement ADR-AF-003 sizing ownership~~ | **Resolved, verified 2026-07-29** — see `Audit/OPERATIONAL_HARDENING_REPORT.md`. Uncommitted; commit before relying on it in production. |
| ~~P0-2~~ | ~~Confirm `EDGE_SCORE_MODE`'s live production value~~ | **Resolved, re-verified via SSH 2026-07-29: `shadow`** — collision was dormant, now moot regardless (P0-1 fixed). |
| ~~P0-3~~ | ~~Confirm `TELEGRAM_WEBHOOK_SECRET` is still set~~ | **Resolved, re-verified via SSH 2026-07-29: SET, non-empty.** |
| ~~P0-4~~ | ~~Harden `validate_config()` to enforce `TELEGRAM_WEBHOOK_SECRET`~~ | **Resolved** — `config.py::validate_config()` now requires it, matching `TELEGRAM_TOKEN`'s pattern. Uncommitted. |
| P1-4 | Per-trade exception isolation in `monitor.py` | A malformed ticker's data can currently mask exit evaluation for trades after it in the same tick |
| P1-2 / P2-6 | Cron dead-man's-switch for backup/restore-drill cadence; run a manual drill now | A known ~36h gap already occurred once undetected |

**Also flagged by this review, not previously captured in the backlog:** the current working tree
carries substantial uncommitted changes matching the ADR-AF-002 work CLAUDE.md describes as
COMPLETE (`engine/agent_firm/*`, `monitor.py`, `paper_trade.py`, `scheduler/jobs.py`,
`scheduler/scanner.py`, `data/db.py`, and their tests — 44 files, +1337/-341 lines uncommitted as of
this writing; branch is also 2 commits ahead of `origin/ops/hardening-2026-07-10`). This is the same
class of gap `Audit/RC1_FINAL_CERTIFICATION_2026-07-28.md` Finding F-1 previously identified and
required resolving before certifying that round of work: an uncommitted working tree has never run
through the real CI gate (`.github/workflows/test.yml` triggers only on `push`/`pull_request`), so
"ADR-AF-002 is complete and tested" currently rests on local verification only. **Recommend
committing and pushing this work (in reviewed, scoped commits) and confirming a green CI run before
treating ADR-AF-002's completion claim, or any of its downstream paper-trading behavior, as fully
verified** — this is a process action, not a design or implementation change, consistent with this
document's mandate not to modify architecture or implement new features.

**Bottom line:** the paper-trading pipeline's logic is sound by inspection; the two things standing
between "sound by inspection" and "operationally hardened" are (1) getting the current uncommitted
work committed and CI-verified, and (2) resolving or explicitly accepting the 4 P0 backlog items.
Neither requires new design work — both are execution of already-scoped, already-decided items.
