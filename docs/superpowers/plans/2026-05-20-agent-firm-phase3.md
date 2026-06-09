# Agent Firm Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Decision Audit tab to the backtest dashboard that correlates agent firm decisions (approve/veto) with actual paper trade outcomes, measuring cohort Sharpe, per-agent agreement rate, and showing a scrollable decision log.

**Architecture:** `engine/agent_firm/analytics.py` holds three pure SQLite query functions (`cohort_summary`, `agent_agreement`, `decision_log`). `app.py` gets one thin `/api/agent/audit` endpoint. `backtest_multi.html` gets a new "Agent Audit" tab that lazily fetches that endpoint on first activation.

**Tech Stack:** Python 3.12, `sqlite3` (stdlib), `statistics` (stdlib), Flask `jsonify`, vanilla JS fetch.

**Reference spec:** `docs/superpowers/specs/2026-05-20-agent-firm-phase3-design.md`

**Working directory:** `/home/tjiesar/10 Projects/idx-walkforward-5001`
**Test runner:** `venv/bin/pytest tests/agent_firm/ -v`

---

## File Structure

**Created:**
- `engine/agent_firm/analytics.py`
- `tests/agent_firm/test_analytics.py`

**Modified:**
- `app.py` — add `GET /api/agent/audit` route after `agent_status` (line ~803)
- `templates/backtest_multi.html` — add tab button, panel HTML, JS loading function

---

## Task 1: `cohort_summary` — Approve vs Veto vs Baseline Returns

**Files:**
- Create: `engine/agent_firm/analytics.py`
- Create: `tests/agent_firm/test_analytics.py`

- [x] **Step 1: Write the failing tests**

Create `tests/agent_firm/test_analytics.py`:

```python
import json
import sqlite3
import pytest
from engine.agent_firm.analytics import cohort_summary


def _make_db(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strategy TEXT NOT NULL,
            quant_score REAL,
            decision TEXT NOT NULL,
            confidence REAL,
            size_hint REAL,
            rationale TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost_usd REAL,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE agent_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER REFERENCES agent_decisions(id),
            role TEXT NOT NULL,
            prompt_version TEXT,
            output TEXT,
            tools_called TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            strategy TEXT,
            entry_date TEXT,
            entry_price REAL,
            lots INTEGER,
            tp_price REAL,
            sl_price REAL,
            exit_date TEXT,
            exit_price REAL,
            exit_reason TEXT,
            pnl_rp REAL,
            pnl_pct REAL,
            status TEXT DEFAULT 'OPEN'
        );
    """)
    conn.commit()
    conn.close()
    return str(db)


def _seed_cohort_data(db_path):
    conn = sqlite3.connect(db_path)
    # 3 approved decisions → positive trades
    for i, (ticker, pnl) in enumerate([("BBRI", 3.2), ("TLKM", 2.1), ("ASII", 1.5)]):
        conn.execute(
            "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision) VALUES (?,?,?,?)",
            (f"2026-05-{10+i:02d}T10:00:00", ticker, "vol_weighted", "approve"),
        )
        conn.execute(
            "INSERT INTO paper_trades (ticker, entry_date, pnl_pct, status) VALUES (?,?,?,?)",
            (ticker, f"2026-05-{10+i:02d}", pnl, "CLOSED"),
        )
    # 2 veto decisions → negative trades
    for i, (ticker, pnl) in enumerate([("BMRI", -1.8), ("UNVR", -2.3)]):
        conn.execute(
            "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision) VALUES (?,?,?,?)",
            (f"2026-05-{13+i:02d}T10:00:00", ticker, "vol_weighted", "veto"),
        )
        conn.execute(
            "INSERT INTO paper_trades (ticker, entry_date, pnl_pct, status) VALUES (?,?,?,?)",
            (ticker, f"2026-05-{13+i:02d}", pnl, "CLOSED"),
        )
    conn.commit()
    conn.close()


def test_cohort_summary_approve_beats_baseline(tmp_path):
    db = _make_db(tmp_path)
    _seed_cohort_data(db)
    result = cohort_summary(db)
    assert result["approve"]["n"] == 3
    assert result["veto"]["n"] == 2
    assert result["baseline"]["n"] == 5  # all 5 closed trades
    assert result["approve"]["avg_return_pct"] > result["baseline"]["avg_return_pct"]
    assert result["veto"]["avg_return_pct"] < 0


def test_cohort_summary_empty_db(tmp_path):
    db = _make_db(tmp_path)
    result = cohort_summary(db)
    assert result["approve"]["n"] == 0
    assert result["veto"]["n"] == 0
    assert result["baseline"]["n"] == 0
```

- [x] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_analytics.py::test_cohort_summary_approve_beats_baseline tests/agent_firm/test_analytics.py::test_cohort_summary_empty_db -v
```

Expected: `ModuleNotFoundError: No module named 'engine.agent_firm.analytics'`

- [x] **Step 3: Implement `cohort_summary`**

Create `engine/agent_firm/analytics.py`:

```python
"""Agent firm analytics — pure SQLite query functions for the audit dashboard."""

import json
import sqlite3
import statistics
from typing import Any


def cohort_summary(db_path: str) -> dict[str, Any]:
    """Cohort performance: approve vs veto vs baseline (all closed trades)."""
    empty = lambda: {"n": 0, "win_rate": 0.0, "avg_return_pct": 0.0, "sharpe": 0.0}
    result = {"approve": empty(), "veto": empty(), "baseline": empty()}
    try:
        conn = sqlite3.connect(db_path)
        approve_pnls = [r[0] for r in conn.execute("""
            SELECT pt.pnl_pct FROM agent_decisions ad
            JOIN paper_trades pt
              ON ad.ticker = pt.ticker AND DATE(ad.scan_time) = pt.entry_date
            WHERE ad.decision = 'approve' AND pt.status = 'CLOSED'
              AND pt.pnl_pct IS NOT NULL
        """).fetchall()]
        veto_pnls = [r[0] for r in conn.execute("""
            SELECT pt.pnl_pct FROM agent_decisions ad
            JOIN paper_trades pt
              ON ad.ticker = pt.ticker AND DATE(ad.scan_time) = pt.entry_date
            WHERE ad.decision = 'veto' AND pt.status = 'CLOSED'
              AND pt.pnl_pct IS NOT NULL
        """).fetchall()]
        baseline_pnls = [r[0] for r in conn.execute(
            "SELECT pnl_pct FROM paper_trades WHERE status = 'CLOSED' AND pnl_pct IS NOT NULL"
        ).fetchall()]
        conn.close()
        result["approve"] = _stats(approve_pnls)
        result["veto"] = _stats(veto_pnls)
        result["baseline"] = _stats(baseline_pnls)
    except Exception:
        pass
    return result


def _stats(pnls: list[float]) -> dict[str, Any]:
    if not pnls:
        return {"n": 0, "win_rate": 0.0, "avg_return_pct": 0.0, "sharpe": 0.0}
    n = len(pnls)
    win_rate = sum(1 for p in pnls if p > 0) / n
    avg = statistics.mean(pnls)
    try:
        sharpe = avg / statistics.stdev(pnls) if n >= 2 else 0.0
    except statistics.StatisticsError:
        sharpe = 0.0
    return {
        "n": n,
        "win_rate": round(win_rate, 4),
        "avg_return_pct": round(avg, 4),
        "sharpe": round(sharpe, 4),
    }
```

- [x] **Step 4: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_analytics.py::test_cohort_summary_approve_beats_baseline tests/agent_firm/test_analytics.py::test_cohort_summary_empty_db -v
```

Expected: 2 passed.

- [x] **Step 5: Commit**

```bash
git add engine/agent_firm/analytics.py tests/agent_firm/test_analytics.py
git commit -m "feat(agent_firm): analytics.py — cohort_summary (Phase 3 audit)"
```

---

## Task 2: `agent_agreement` — Per-Agent Alignment Rate

**Files:**
- Modify: `engine/agent_firm/analytics.py`
- Modify: `tests/agent_firm/test_analytics.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/agent_firm/test_analytics.py`:

```python
from engine.agent_firm.analytics import agent_agreement


def _seed_agreement_data(db_path):
    conn = sqlite3.connect(db_path)
    # 1 approve decision with 4 aligned traces
    cur = conn.execute(
        "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision) VALUES (?,?,?,?)",
        ("2026-05-20T10:00:00", "BBRI", "vol_weighted", "approve"),
    )
    did = cur.lastrowid
    traces = [
        ("technical", json.dumps({"verdict": "BULLISH", "conviction": 0.7})),
        ("flow",      json.dumps({"flow_verdict": "ACCUMULATING"})),
        ("regime",    json.dumps({"regime_call": "TRENDING"})),
        ("news",      json.dumps({"sentiment": "BULLISH"})),
        ("bull",      json.dumps({"bull_case": "Strong flow."})),
        ("bear",      json.dumps({"bear_case": "Rate risk."})),
    ]
    for role, output in traces:
        conn.execute(
            "INSERT INTO agent_traces (decision_id, role, output) VALUES (?,?,?)",
            (did, role, output),
        )
    conn.commit()
    conn.close()


def test_agent_agreement_counts_roles(tmp_path):
    db = _make_db(tmp_path)
    _seed_agreement_data(db)
    result = agent_agreement(db)
    roles = [r["role"] for r in result]
    assert set(roles) == {"technical", "flow", "regime", "news", "bull", "bear"}
    # All 4 analyst traces are bullish-aligned with approve decision
    for r in result:
        assert r["decisions"] == 1
        assert r["agreement_pct"] == 100.0 or r["role"] == "bear"
    # bear is aligned with veto, not approve → agreement_pct 0.0
    bear_row = next(r for r in result if r["role"] == "bear")
    assert bear_row["agreement_pct"] == 0.0


def test_agent_agreement_empty(tmp_path):
    db = _make_db(tmp_path)
    result = agent_agreement(db)
    assert result == []
```

- [x] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_analytics.py::test_agent_agreement_counts_roles tests/agent_firm/test_analytics.py::test_agent_agreement_empty -v
```

Expected: `ImportError: cannot import name 'agent_agreement'`

- [x] **Step 3: Add `agent_agreement` to analytics.py**

Append to `engine/agent_firm/analytics.py` after the `_stats` helper:

```python
def agent_agreement(db_path: str) -> list[dict[str, Any]]:
    """Per-agent directional alignment with the final risk decision."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT at.role, at.output, ad.decision
            FROM agent_traces at
            JOIN agent_decisions ad ON at.decision_id = ad.id
            WHERE ad.decision IN ('approve', 'veto')
        """).fetchall()
        conn.close()
    except Exception:
        return []

    from collections import defaultdict
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"decisions": 0, "aligned": 0})

    for row in rows:
        role = row["role"]
        decision = row["decision"]
        counts[role]["decisions"] += 1
        try:
            output = json.loads(row["output"] or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        aligned = _is_aligned(role, output, decision)
        if aligned:
            counts[role]["aligned"] += 1

    result = []
    for role in ["technical", "flow", "regime", "news", "bull", "bear"]:
        if role in counts:
            d = counts[role]["decisions"]
            a = counts[role]["aligned"]
            result.append({
                "role": role,
                "decisions": d,
                "aligned": a,
                "agreement_pct": round(a / d * 100, 1) if d > 0 else 0.0,
            })
    return result


def _is_aligned(role: str, output: dict, decision: str) -> bool:
    is_approve = decision == "approve"
    if role == "technical":
        return (output.get("verdict") == "BULLISH") == is_approve
    if role == "flow":
        return (output.get("flow_verdict") == "ACCUMULATING") == is_approve
    if role == "regime":
        return (output.get("regime_call") == "TRENDING") == is_approve
    if role == "news":
        return (output.get("sentiment") == "BULLISH") == is_approve
    if role == "bull":
        return is_approve
    if role == "bear":
        return not is_approve
    return False
```

- [x] **Step 4: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_analytics.py::test_agent_agreement_counts_roles tests/agent_firm/test_analytics.py::test_agent_agreement_empty -v
```

Expected: 2 passed.

- [x] **Step 5: Run full analytics test file**

```bash
venv/bin/pytest tests/agent_firm/test_analytics.py -v
```

Expected: 4 passed.

- [x] **Step 6: Commit**

```bash
git add engine/agent_firm/analytics.py tests/agent_firm/test_analytics.py
git commit -m "feat(agent_firm): agent_agreement analytics — per-role alignment rate"
```

---

## Task 3: `decision_log` — Chronological Audit Trail

**Files:**
- Modify: `engine/agent_firm/analytics.py`
- Modify: `tests/agent_firm/test_analytics.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/agent_firm/test_analytics.py`:

```python
from engine.agent_firm.analytics import decision_log


def _seed_log_data(db_path):
    conn = sqlite3.connect(db_path)
    # 3 approve decisions with matching closed paper trades
    for i, ticker in enumerate(["BBRI", "TLKM", "ASII"]):
        conn.execute(
            "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision, confidence, size_hint, rationale) "
            "VALUES (?,?,?,?,?,?,?)",
            (f"2026-05-{10+i:02d}T10:00:00", ticker, "vol_weighted", "approve",
             0.75, 1.0, f"Risk: aligned.\nBull/Bear: bull case."),
        )
        conn.execute(
            "INSERT INTO paper_trades (ticker, entry_date, pnl_pct, status) VALUES (?,?,?,?)",
            (ticker, f"2026-05-{10+i:02d}", 2.5, "CLOSED"),
        )
    # 1 veto decision with NO matching paper trade
    conn.execute(
        "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision, confidence, size_hint, rationale) "
        "VALUES (?,?,?,?,?,?,?)",
        ("2026-05-15T10:00:00", "BMRI", "vol_weighted", "veto", 0.6, 0.0, "Risk: distributing."),
    )
    conn.commit()
    conn.close()


def test_decision_log_returns_rows(tmp_path):
    db = _make_db(tmp_path)
    _seed_log_data(db)
    result = decision_log(db)
    assert len(result) == 4
    assert all("ticker" in r for r in result)
    assert all("decision" in r for r in result)


def test_decision_log_no_paper_trade_outcome_is_none(tmp_path):
    db = _make_db(tmp_path)
    _seed_log_data(db)
    result = decision_log(db)
    veto_row = next(r for r in result if r["decision"] == "veto")
    assert veto_row["outcome"] is None
    assert veto_row["pnl_pct"] is None


def test_decision_log_empty_db(tmp_path):
    db = _make_db(tmp_path)
    result = decision_log(db)
    assert result == []
```

- [x] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/agent_firm/test_analytics.py::test_decision_log_returns_rows tests/agent_firm/test_analytics.py::test_decision_log_no_paper_trade_outcome_is_none tests/agent_firm/test_analytics.py::test_decision_log_empty_db -v
```

Expected: `ImportError: cannot import name 'decision_log'`

- [x] **Step 3: Add `decision_log` to analytics.py**

Append to `engine/agent_firm/analytics.py`:

```python
def decision_log(db_path: str, limit: int = 100) -> list[dict[str, Any]]:
    """Chronological log of decisions with matched paper trade outcomes."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT
                DATE(ad.scan_time) AS date,
                ad.ticker,
                ad.strategy,
                ad.decision,
                ad.confidence,
                ad.size_hint,
                ad.rationale,
                pt.status   AS outcome,
                pt.pnl_pct
            FROM agent_decisions ad
            LEFT JOIN paper_trades pt
                ON ad.ticker = pt.ticker
               AND DATE(ad.scan_time) = pt.entry_date
            ORDER BY ad.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []
```

- [x] **Step 4: Run tests**

```bash
venv/bin/pytest tests/agent_firm/test_analytics.py -v
```

Expected: 7 passed (all analytics tests).

- [x] **Step 5: Run full agent_firm test suite to confirm no regressions**

```bash
venv/bin/pytest tests/agent_firm/ -v --tb=short 2>&1 | tail -5
```

Expected: all prior tests + 7 new analytics tests pass.

- [x] **Step 6: Commit**

```bash
git add engine/agent_firm/analytics.py tests/agent_firm/test_analytics.py
git commit -m "feat(agent_firm): decision_log analytics — chronological audit trail"
```

---

## Task 4: `/api/agent/audit` Endpoint

**Files:**
- Modify: `app.py`

- [x] **Step 1: Read the agent_status block**

```bash
grep -n "agent_status\|agent/status\|agent/audit\|DB_PATH" app.py | head -20
```

Note the line number of `@app.route("/api/agent/status"...)` (currently ~line 770). The new route goes directly after the closing `}` of `agent_status`.

- [x] **Step 2: Add the endpoint**

In `app.py`, find the line `@app.route("/api/scheduler/run"...)` (currently ~line 804) and insert the following block immediately before it:

```python
@app.route("/api/agent/audit", methods=["GET"])
def agent_audit():
    try:
        from engine.agent_firm.analytics import agent_agreement, cohort_summary, decision_log
        return jsonify({
            "cohorts":   cohort_summary(DB_PATH),
            "agreement": agent_agreement(DB_PATH),
            "log":       decision_log(DB_PATH, limit=100),
        })
    except Exception as e:
        return jsonify({
            "error":     str(e),
            "cohorts":   {"approve": {"n":0,"win_rate":0.0,"avg_return_pct":0.0,"sharpe":0.0},
                          "veto":    {"n":0,"win_rate":0.0,"avg_return_pct":0.0,"sharpe":0.0},
                          "baseline":{"n":0,"win_rate":0.0,"avg_return_pct":0.0,"sharpe":0.0}},
            "agreement": [],
            "log":       [],
        })

```

- [x] **Step 3: Verify no syntax error**

```bash
venv/bin/python -c "import app; print('app ok')"
```

Expected: `app ok`

- [x] **Step 4: Smoke-test the endpoint (if Flask dev server is running)**

```bash
curl -s http://localhost:5001/api/agent/audit | python3 -m json.tool 2>/dev/null | head -20 || echo "server not running — skip"
```

Expected: JSON with `cohorts`, `agreement`, `log` keys, or "server not running — skip".

- [x] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat(agent_firm): /api/agent/audit endpoint (cohorts + agreement + log)"
```

---

## Task 5: Agent Audit Dashboard Tab

**Files:**
- Modify: `templates/backtest_multi.html`

The existing tab buttons are around line 524–532. The tab panels start around line 541. The `setActiveTab` function is around line 1231. Add the new tab in all three places.

- [x] **Step 1: Add the tab button**

In `templates/backtest_multi.html`, find:

```html
    <button class="tab" data-tab="calendar">Calendar</button>
```

Add immediately after it:

```html
    <button class="tab" data-tab="audit">Agent Audit</button>
```

- [x] **Step 2: Add the tab panel**

Find the closing tag of the last panel (search for `id="panel-calendar"`). After the closing `</section>` of that panel, add:

```html
<section class="tab-panel" id="panel-audit">
  <div id="audit-loading" style="padding:24px 0;color:var(--text-dim);font-size:13px">Loading…</div>
  <div id="audit-content" style="display:none">

    <!-- Cohort Cards -->
    <div id="audit-cohorts" style="display:flex;gap:12px;margin-bottom:18px"></div>

    <!-- Agent Agreement -->
    <div style="margin-bottom:6px;font-size:11px;color:var(--text-dim);text-transform:uppercase;letter-spacing:.06em">Agent Agreement</div>
    <div class="table-wrap" style="margin-bottom:16px">
      <table class="data small">
        <thead>
          <tr>
            <th>Role</th><th>Decisions</th><th>Aligned</th><th>Agreement%</th>
          </tr>
        </thead>
        <tbody id="audit-agreement-body"></tbody>
      </table>
    </div>

    <!-- Decision Log -->
    <div style="margin-bottom:6px;font-size:11px;color:var(--text-dim);text-transform:uppercase;letter-spacing:.06em">Decision Log</div>
    <div class="table-wrap">
      <table class="data small">
        <thead>
          <tr>
            <th>Date</th><th>Ticker</th><th>Strategy</th>
            <th>Decision</th><th>Conf</th><th>Size</th>
            <th>Outcome</th><th>P&amp;L%</th>
          </tr>
        </thead>
        <tbody id="audit-log-body"></tbody>
      </table>
    </div>

  </div>
</section>
```

- [x] **Step 3: Wire lazy load into `setActiveTab`**

Find:

```javascript
  if (name === 'paper')    loadPaperTrades();
```

Add immediately after it:

```javascript
  if (name === 'audit')    loadAuditData();
```

- [x] **Step 4: Add `loadAuditData` and `toggleRationale` JS**

Find the closing of the `setActiveTab` function block (around `}` after the `updateIndicator` call). After the `updateIndicator` function definition, add the following new functions:

```javascript
let _auditLoaded = false;
function loadAuditData() {
  if (_auditLoaded) return;
  fetch('/api/agent/audit').then(r => r.json()).then(data => {
    _auditLoaded = true;
    document.getElementById('audit-loading').style.display = 'none';
    document.getElementById('audit-content').style.display = 'block';

    // Cohort Cards
    const cohorts = document.getElementById('audit-cohorts');
    cohorts.innerHTML = '';
    const palette = {approve:'var(--green)',veto:'var(--red)',baseline:'var(--text-dim)'};
    ['approve','veto','baseline'].forEach(k => {
      const c = (data.cohorts||{})[k] || {};
      const col = palette[k];
      const sign = (c.avg_return_pct||0) >= 0 ? '+' : '';
      cohorts.innerHTML += `<div style="flex:1;min-width:120px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px">
        <div style="font-size:10px;color:${col};font-weight:700;letter-spacing:.07em;text-transform:uppercase;margin-bottom:8px">${k}</div>
        <div style="font-size:12px;color:var(--text-dim);line-height:1.8">
          n = ${c.n||0}<br>
          win ${((c.win_rate||0)*100).toFixed(0)}%<br>
          avg ${sign}${(c.avg_return_pct||0).toFixed(2)}%<br>
          Sharpe ${(c.sharpe||0).toFixed(2)}
        </div>
      </div>`;
    });

    // Agreement Table
    const agBody = document.getElementById('audit-agreement-body');
    agBody.innerHTML = '';
    if ((data.agreement||[]).length) {
      data.agreement.forEach(r => {
        agBody.innerHTML += `<tr><td>${r.role}</td><td>${r.decisions}</td><td>${r.aligned}</td><td>${r.agreement_pct}%</td></tr>`;
      });
    } else {
      agBody.innerHTML = '<tr><td colspan="4" style="color:var(--text-dim)">No data yet</td></tr>';
    }

    // Decision Log
    const logBody = document.getElementById('audit-log-body');
    logBody.innerHTML = '';
    if ((data.log||[]).length) {
      data.log.forEach((r, i) => {
        const dCol = r.decision === 'approve' ? 'var(--green)' : r.decision === 'veto' ? 'var(--red)' : 'var(--text-dim)';
        const pnl  = r.pnl_pct != null ? (r.pnl_pct >= 0 ? '+' : '') + parseFloat(r.pnl_pct).toFixed(2) + '%' : '—';
        const pCol = r.pnl_pct > 0 ? 'var(--green)' : r.pnl_pct < 0 ? 'var(--red)' : 'var(--text-dim)';
        logBody.innerHTML += `
          <tr style="cursor:pointer" onclick="toggleRationale(${i})">
            <td>${r.date||'—'}</td>
            <td>${r.ticker}</td>
            <td style="color:var(--text-dim)">${r.strategy}</td>
            <td style="color:${dCol};font-weight:600">${r.decision}</td>
            <td>${r.confidence != null ? (r.confidence*100).toFixed(0)+'%' : '—'}</td>
            <td>${r.size_hint != null ? parseFloat(r.size_hint).toFixed(1)+'x' : '—'}</td>
            <td>${r.outcome||'—'}</td>
            <td style="color:${pCol}">${pnl}</td>
          </tr>
          <tr id="rationale-${i}" style="display:none">
            <td colspan="8" style="color:var(--text-dim);font-size:11px;padding:8px 14px;white-space:pre-wrap;background:var(--surface-2)">${(r.rationale||'(no rationale)').replace(/</g,'&lt;')}</td>
          </tr>`;
      });
    } else {
      logBody.innerHTML = '<tr><td colspan="8" style="color:var(--text-dim)">No decisions yet</td></tr>';
    }
  }).catch(() => {
    document.getElementById('audit-loading').textContent = 'Failed to load audit data.';
  });
}
function toggleRationale(i) {
  const el = document.getElementById('rationale-' + i);
  if (el) el.style.display = el.style.display === 'none' ? '' : 'none';
}
```

- [x] **Step 5: Verify the HTML is valid (no unclosed tags)**

```bash
venv/bin/python -c "
from html.parser import HTMLParser
class V(HTMLParser): pass
p = V()
p.feed(open('templates/backtest_multi.html').read())
print('html parse ok')
"
```

Expected: `html parse ok`

- [x] **Step 6: Verify app still imports cleanly**

```bash
venv/bin/python -c "import app; print('app ok')"
```

Expected: `app ok`

- [x] **Step 7: Commit**

```bash
git add templates/backtest_multi.html
git commit -m "feat(agent_firm): Agent Audit dashboard tab — cohorts, agreement, decision log"
```

---

## Final Verification

- [x] **Run full test suite**

```bash
venv/bin/pytest tests/agent_firm/ -v --tb=short 2>&1 | tail -10
```

Expected: all prior tests pass + 7 new analytics tests pass (total 69+).

- [x] **Verify smoke probe still works**

```bash
AGENT_FIRM_ENABLED=false venv/bin/python -m engine.agent_firm.smoke
echo "exit: $?"
```

Expected: `SKIP` and exit 0.

- [x] **Verify scheduler imports cleanly**

```bash
venv/bin/python -c "import scheduler; print('scheduler ok')"
```

Expected: `scheduler ok`.

- [x] **Tag Phase 3**

```bash
git tag -a phase3-agent-firm-audit -m "Phase 3 complete: decision audit dashboard + analytics module"
```
