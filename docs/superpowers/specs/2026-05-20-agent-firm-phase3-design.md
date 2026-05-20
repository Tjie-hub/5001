# Agent Firm Phase 3 Design — Decision Audit & Performance Dashboard

## Goal

Add a decision audit tab to the existing backtest dashboard that correlates agent firm decisions (approve/veto) with actual paper trade outcomes. Phase 2 runs in shadow mode — every signal becomes a paper trade regardless of decision. Phase 3 makes the shadow data visible: were approved signals better than vetoed ones?

**Acceptance bar from Phase 2:** approve-cohort Sharpe ≥ baseline + 0.2 AND veto-cohort win_rate < baseline − 5pp. Phase 3 builds the tooling to measure this.

---

## Architecture

```
engine/agent_firm/analytics.py          ← NEW: 3 pure query functions
tests/agent_firm/test_analytics.py      ← NEW: 6 unit tests (temp SQLite)
app.py                                  ← add /api/agent/audit endpoint
templates/backtest_multi.html           ← add "Agent Audit" tab
```

No new DB tables. Reads from existing: `agent_decisions`, `agent_traces`, `paper_trades`.

---

## Analytics Module (`engine/agent_firm/analytics.py`)

Three pure functions. Each takes `db_path: str` and returns a plain Python structure. All exceptions are caught and return safe empty values.

### `cohort_summary(db_path) -> dict`

Joins `agent_decisions` to `paper_trades` on:
```sql
agent_decisions.ticker = paper_trades.ticker
AND DATE(agent_decisions.scan_time) = paper_trades.entry_date
```

For each cohort — `approve` (decision=approve, matched trade), `veto` (decision=veto, matched trade), `baseline` (all closed paper trades regardless of agent decision):

| Field | Description |
|---|---|
| `n` | Count of matched closed trades |
| `win_rate` | % where `pnl_pct > 0` |
| `avg_return_pct` | AVG(pnl_pct) |
| `sharpe` | AVG(pnl_pct) / STDEV(pnl_pct) — computed in Python |

Returns:
```python
{
    "approve":  {"n": int, "win_rate": float, "avg_return_pct": float, "sharpe": float},
    "veto":     {"n": int, "win_rate": float, "avg_return_pct": float, "sharpe": float},
    "baseline": {"n": int, "win_rate": float, "avg_return_pct": float, "sharpe": float},
}
```

Empty/error returns all zeroed dicts.

### `agent_agreement(db_path) -> list[dict]`

For each role in `agent_traces`, parses `output` JSON and checks whether the agent's verdict directionally matches the final risk `decision` on the parent `agent_decisions` row.

Alignment rules:
- `technical`: `output.verdict == "BULLISH"` → aligned with `approve`
- `flow`: `output.flow_verdict == "ACCUMULATING"` → aligned with `approve`
- `regime`: `output.regime_call == "TRENDING"` → aligned with `approve`
- `news`: `output.sentiment == "BULLISH"` → aligned with `approve`
- `bull`: always present — aligned when final decision is `approve`
- `bear`: always present — aligned when final decision is `veto`

Returns:
```python
[
    {"role": str, "decisions": int, "aligned": int, "agreement_pct": float},
    ...  # one row per role
]
```

Empty list on error.

### `decision_log(db_path, limit=100) -> list[dict]`

Left-joins `agent_decisions` → `paper_trades` on ticker+date. Returns most recent `limit` rows.

```python
[
    {
        "date": str,           # DATE(scan_time)
        "ticker": str,
        "strategy": str,
        "decision": str,       # "approve" | "veto" | "degraded" | "bypassed"
        "confidence": float,
        "size_hint": float,
        "rationale": str,
        "outcome": str | None, # "CLOSED" | "OPEN" | None (no matching trade)
        "pnl_pct": float | None,
    },
    ...
]
```

---

## API Endpoint

**`GET /api/agent/audit`** — added to `app.py`

Returns all three analytics under one fetch. Tab JS calls this once on first tab activation.

```json
{
  "cohorts": {
    "approve":  {"n": 14, "win_rate": 0.71, "avg_return_pct": 2.1, "sharpe": 1.4},
    "veto":     {"n": 8,  "win_rate": 0.38, "avg_return_pct": -0.8, "sharpe": -0.3},
    "baseline": {"n": 22, "win_rate": 0.59, "avg_return_pct": 1.2, "sharpe": 0.8}
  },
  "agreement": [
    {"role": "technical", "decisions": 22, "aligned": 17, "agreement_pct": 77.3},
    ...
  ],
  "log": [
    {"date": "2026-05-20", "ticker": "BBRI", "strategy": "vol_weighted",
     "decision": "approve", "confidence": 0.82, "size_hint": 1.0,
     "rationale": "Risk: all aligned.\nBull/Bear: bull dominates.",
     "outcome": "OPEN", "pnl_pct": null},
    ...
  ]
}
```

On DB error: `{"error": "...", "cohorts": {...zeroed}, "agreement": [], "log": []}` with HTTP 200.

---

## Dashboard Tab

New "Agent Audit" tab in `backtest_multi.html`, added alongside existing tabs. Data fetched lazily on first tab click.

**Layout (top to bottom):**

**Row 1 — Cohort Cards (3 cards)**
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  APPROVED   │  │   VETOED    │  │  BASELINE   │
│  n=14       │  │  n=8        │  │  n=22       │
│  win 71%    │  │  win 38%    │  │  win 59%    │
│  avg +2.1%  │  │  avg -0.8%  │  │  avg +1.2%  │
│  Sharpe 1.4 │  │  Sharpe -0.3│  │  Sharpe 0.8 │
└─────────────┘  └─────────────┘  └─────────────┘
```
Color-coded: green (approve), red (veto), grey (baseline). Empty state: "No closed trades yet."

**Row 2 — Agent Agreement Table**

| Role | Decisions | Aligned | Agreement% |
|---|---|---|---|
| technical | 22 | 17 | 77% |
| flow | 22 | 15 | 68% |
| ... | | | |

**Row 3 — Decision Log (scrollable, 100 rows)**

| Date | Ticker | Strategy | Decision | Conf | Outcome | P&L% |
|---|---|---|---|---|---|---|
| 2026-05-20 | BBRI | vol_weighted | approve | 0.82 | OPEN | — |

Clicking a row expands the rationale inline (toggle).

---

## Error Handling

- All `analytics.py` functions catch exceptions and return safe empty structures — no crashes
- `/api/agent/audit` wraps in try/except, always returns HTTP 200
- Tab JS shows "No data yet" when counts are zero — expected during early shadow mode
- Sharpe computed as 0.0 when fewer than 2 data points (no division by zero)

---

## Testing (`tests/agent_firm/test_analytics.py`)

Six tests, all against temp SQLite with fixture data. TDD: red → green → commit.

| Test | Asserts |
|---|---|
| `test_cohort_summary_approve_beats_baseline` | 3 approve closed (+pnl) + 2 veto (-pnl) → approve avg_return > baseline |
| `test_cohort_summary_empty_db` | No rows → all counts=0, no exception |
| `test_agent_agreement_counts_roles` | 4 traces per decision → 4 role rows returned |
| `test_agent_agreement_empty` | No traces → returns `[]` |
| `test_decision_log_returns_rows` | 5 decisions + matched trades → log length=5 |
| `test_decision_log_no_paper_trade_outcome_is_none` | Veto with no matching trade → `outcome=None` |

---

## File Summary

**Created:**
- `engine/agent_firm/analytics.py`
- `tests/agent_firm/test_analytics.py`

**Modified:**
- `app.py` — add `GET /api/agent/audit` route
- `templates/backtest_multi.html` — add "Agent Audit" tab with 3-section layout

**Unchanged:** DB schema, firm.py, scheduler.py, all Phase 1/2 tests.

---

## Implementation Notes

- `analytics.py` imports only `sqlite3` and `statistics` (stdlib) — no new dependencies
- `statistics.mean` / `statistics.stdev` used for Sharpe — safe with `try/except StatisticsError`
- Tab JS uses the same `fetch`/`.then` pattern as the existing badge script
- Existing `test_analytics.py` (if any) — check before creating; none exists in current codebase
