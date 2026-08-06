# Workstream 2C — Business Output Audit & API Planning

**Status:** Audit deliverable, 2026-08-06. Production Engine Phase 2, Workstream 2C (Business
APIs), Step 1. **No endpoints implemented in this step** — planning only, per the task's own
constraint. Builds on the frozen Phase 2A foundation and frozen Workstream 2B (both untouched).

---

## 1. What actually exists (the surprise up front)

Four distinct, already-live "watchlist" mechanisms exist, each with its own table and its own
module — they are not layers of one system, they answer different questions:

| Mechanism | Table | Question it answers |
|---|---|---|
| `engine.trade_plan` | `watchlist_snapshot` | "What did the **firm approve**, ranked, for EOD/Premarket, on day X?" |
| `engine.watchlist_report` | `candidate_watchlist_snapshot` | "What was the **raw pre-firm candidate universe** the engine was watching on day X, before any veto?" |
| `engine.persistent_watchlist` | `persistent_watchlist` | "How long has ticker T **continuously** held an approved spot, across unbounded days?" |
| `engine.watchlist` | `regime_watchlist` | "Which oversold tickers were flagged in BEAR for BULL-flip prioritization?" (scanner input, not a report) |

All four are wired live into `scheduler/jobs.py` (`run_eod_trade_plan`, `run_premarket_firm_scan`)
or `scheduler/scanner.py` (`regime_watchlist`) as of this morning's commits. None of this was
speculative — every table has a real writer and, except `regime_watchlist`, an existing
Telegram-message consumer.

There is also **no persisted "report" artifact anywhere** — EOD/Premarket/Forward-Testing
reports are computed fresh from the tables above (plus `ft_shadow_position`/`ft_shadow_trade`
for forward-testing) each time the scheduler job runs, rendered straight to Telegram HTML text,
and never archived as their own row. This is a material finding for the Reports section below.

---

## 2. Mapping table

| Existing Artifact | Source (module / table) | Proposed Endpoint | Auth | Notes |
|---|---|---|---|---|
| Current EOD watchlist | `engine.trade_plan.watchlist_snapshot` (strategy='eod'), latest date | `GET /api/v1/watchlists/eod/current` | VIEWER | Direct SELECT, existing table, zero new logic |
| Current Premarket shortlist | same table, strategy='premarket' | `GET /api/v1/watchlists/premarket/current` | VIEWER | Same table, different key |
| Historical watchlist by date | `watchlist_snapshot` | `GET /api/v1/watchlists/{strategy}/{date}` | VIEWER | Append-only history already exists — no new storage needed |
| Watchlist diff / changes | `engine.trade_plan.diff_watchlist()` | `GET /api/v1/watchlists/{strategy}/{date}/diff` | VIEWER | Pure function over persisted rows, already used by the Telegram reports |
| Pre-firm candidate universe (today) | `engine.watchlist_report.candidate_watchlist_snapshot` | `GET /api/v1/candidates/universe/current` | VIEWER | See §Candidate Universe below — deliberately separate from "watchlist" (pre- vs post-firm) |
| Candidate universe by date | same table | `GET /api/v1/candidates/universe/{date}` | VIEWER | |
| Candidate universe diff | `engine.watchlist_report.diff_snapshot()` | `GET /api/v1/candidates/universe/{date}/diff` | VIEWER | |
| Persistent (multi-day) watchlist | `engine.persistent_watchlist.persistent_watchlist` | `GET /api/v1/watchlists/persistent` | VIEWER | One row per ticker (ACTIVE/REMOVED), not date-keyed — different shape from the snapshot endpoints above |
| Bear dip-scout watchlist | `engine.watchlist.regime_watchlist` | `GET /api/v1/watchlists/bear-dip-scout` (tentative) | VIEWER | Borderline — this is closer to a scanner *input* than a firm output; recommend deferring, see §Risks |
| Snapshot inventory (which date/strategy pairs exist) | `watchlist_snapshot` + `candidate_watchlist_snapshot`, `SELECT DISTINCT date, strategy` | `GET /api/v1/snapshots` | VIEWER | A metadata/index view, distinct from the content endpoints above — answers "what history exists to query," not "what's in it" |
| Forward-testing summary (opened/closed/scoreboard) | `forward_testing.reporting` (`get_positions_opened_on`, `get_trades_closed_on`, `win_loss_summary`, `best_worst_trades`) | `GET /api/v1/reports/forward-test/{date}` | VIEWER | Clean existing pure-data functions — best reuse case in the whole audit |
| EOD/Premarket "report" (narrative) | *no persisted artifact* — recomputed from `watchlist_snapshot` + live agent-decision context each run | *(deferred — see §Risks)* | — | The structured half is already the Watchlist API above; the narrative half needs live inputs beyond what's persisted |
| Screening output (technicals/VPIN) | `screener.db` (`daily_screen` table) + existing legacy `screener_bp` (`/api/screener/results`, `/vpin`, `/cumdelta`, etc.) | `GET /api/v1/candidates/screen` | VIEWER | Legacy `/api/screener/*` already does this outside `/api/v1` — see §Risks on migrate-vs-new |
| Reversal/premover watchlist | legacy `/api/screener/reversal`, `/api/premover/watchlist` (`routes/screener.py`) | `GET /api/v1/candidates/reversal-watchlist` | VIEWER | Same migrate-vs-new question |
| Agent decisions (recent) | `engine.agent_firm.analytics.decision_log(db_path, limit)` | `GET /api/v1/agent-firm/decisions` | VIEWER | Ready-made service function, exactly the shape an API controller wants |
| Agent cohort/agreement stats | `engine.agent_firm.analytics.cohort_summary()` / `agent_agreement()` | `GET /api/v1/agent-firm/analytics` | VIEWER | Also ready-made; no new aggregation needed |

---

## 3. Architecture review (per artifact)

For every row above the pattern is identical and already satisfies the required
Route → Service → Engine layering with **zero new business logic**:

- **Storage**: SQLite, existing tables, no new schema.
- **Service layer**: every artifact already has a pure, DB-path-parameterized Python function
  (`record_snapshot`/`diff_watchlist`/`diff_snapshot`/`update_watchlist`/`decision_log`/
  `cohort_summary`/the `forward_testing.reporting` functions) — a v1 controller would call
  these directly, exactly the pattern established in 2B-1/2B-2/2B-3/2B-4 (thin controller,
  `config.DB_PATH` read at call time, no `os.getenv`/raw SQL in the route).
- **Serialization**: none of these currently serialize to JSON — they either return plain dicts/
  lists already (safe to `ok()`-wrap as-is) or render Telegram HTML text (`build_message()`
  functions — **not** reused for an API; only their upstream data functions are).
- **Existing tests**: `tests/test_trade_plan.py`, `test_watchlist_report.py`,
  `test_persistent_watchlist.py`, `test_watchlist.py`, `test_bear_watchlist_ranking.py`,
  `test_unified_watchlist.py`, `test_dashboard_watchlist.py`, `tests/forward_testing/` — every
  underlying function is already unit-tested; a v1 route's own tests only need to cover the
  HTTP/envelope/auth layer, matching every prior 2B task's split.
- **Existing consumers**: Telegram (EOD/Premarket/Forward-Testing messages), the legacy
  dashboard HTML pages, and the legacy `/api/screener/*` / `/api/premover/*` JSON routes.

---

## 4. Security review

Nothing in this inventory is more sensitive than the Operational APIs already shipped at
`VIEWER`. Every artifact is:

- **Ticker/strategy/score data**, already broadcast to Telegram (a wider audience than any
  authenticated API caller) or already served by the existing unauthenticated-by-default legacy
  screener routes.
- **No PII, no credentials, no account/position sizing in currency terms** beyond what's already
  visible in `paper_trades`/`ft_shadow_position` via existing routes.

**Recommendation: VIEWER for every endpoint in the table**, no new role needed — consistent with
Workstream 2B's own finding.

One field-level note for `GET /api/v1/agent-firm/decisions`: `decision_log()`'s rows likely
include `rationale` (free-text LLM output) and cost fields (`tokens_in/out`, `cost_usd`) — none
of these are secrets, but cost fields are operationally sensitive in the sense of being
internal financial detail; recommend keeping them in the v1 response (they're not exposed
anywhere else today, and PSR/metrics already expose comparable operational detail) rather than
redacting, but flagging for explicit sign-off when 2C's agent-firm task is scoped (not part of
2C-1..4's stated order, so not blocking now).

---

## 5. OpenAPI planning summary

Every endpoint above: `GET`, `VIEWER`, standard envelope, standard error envelope (`404
NOT_FOUND` for an unknown date/strategy/ticker — e.g. `GET /api/v1/watchlists/eod/2020-01-01`
where no snapshot exists that day), no request body, path/query params only (`date`, `strategy`,
`limit`). No new error codes needed beyond what `routes/v1/envelope.py` already defines. Full
per-endpoint OpenAPI entries (`_PATHS` additions) are implementation-stage work for each of
2C-1..4, not written here per the task's "no implementation" constraint — this section confirms
no endpoint here needs a contract shape the frozen foundation can't already express.

---

## 6. Risks / inconsistencies discovered

1. **"Daily Report" has no clean 1:1 API mapping.** Its structured content is already the
   Watchlist API (§2); its narrative content (`engine.trade_plan.build_message()`) needs live
   inputs (today's agent decisions, VPIN gate, regime) that aren't all persisted for arbitrary
   past dates. Recommend 2C-3 (Report APIs) scope to what **is** cleanly reusable —
   Forward-Testing Summary (`forward_testing.reporting`, fully data-backed) — and treat
   EOD/Premarket "report" as *already covered* by the Watchlist API rather than inventing a
   second, weaker view of the same data. Flagging for explicit decision before 2C-3 starts.
2. **Legacy `/api/screener/*` and `/api/premover/*` already do most of what a "Candidate
   Universe API" would do**, outside `/api/v1` and the standard envelope (same situation as
   the pre-existing `/api/status/*` this session migrated in Workstream A Task 1). 2C-4 should
   decide, per-endpoint, whether to **migrate** (delete the legacy route, matching the Task 1
   precedent) or **add a new v1 endpoint alongside** (if the legacy route has active non-API
   consumers, e.g. a dashboard page directly calling it) — this needs a quick consumer check per
   route at 2C-4 design time, not assumed either way here.
3. **`regime_watchlist` (bear dip-scout) is arguably scanner input, not a business output.**
   Recommend deferring it out of 2C-1..4's initial scope; it doesn't block anything and can be
   added later if a consumer actually needs it.
4. **No new storage is needed anywhere in this inventory** — every proposed endpoint reads a
   table that already exists with a real writer already in production. This audit found no gap
   requiring anything like 2B-1's `scheduler.get_scheduler()` getter or 2B-3's
   `sectors_app_mode()` getter — the service functions already exist and are already
   DB-path-parameterized.

---

## 7. Recommended implementation order for Phase 2C

Per the brief's own stated order (2C-1 Watchlist → 2C-2 Snapshot → 2C-3 Report → 2C-4 Candidate
Universe), refined by this audit:

1. **2C-1 — Watchlist APIs**: `watchlist_snapshot` (current/historical/diff) +
   `persistent_watchlist`. Cleanest reuse in the whole inventory; no open questions.
2. **2C-2 — Snapshot APIs**: the `/api/v1/snapshots` inventory/index endpoint. Small, and now
   that 2C-1 exists, mostly a `SELECT DISTINCT date, strategy` over the same tables — natural
   follow-on, not a new subsystem.
3. **2C-3 — Report APIs**: start with Forward-Testing Summary only (clean, fully data-backed);
   resolve risk #1 above (EOD/Premarket narrative report scope) before or during design rather
   than assuming a shape.
4. **2C-4 — Candidate Universe APIs**: `candidate_watchlist_snapshot` (clean) +
   the migrate-vs-new decision for legacy `/api/screener/*`/`/api/premover/*` (risk #2) — resolve
   per-route at design time, same working method as every 2B task (audit → design proposal →
   TDD).

Each task follows the same design → TDD → implementation → full regression → isolated commit →
completion report → review cycle already established across every Workstream A/2B task in this
session.
