# Phase 3B — Fail-Open Inventory (C-9) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the audit-critical C-9 fail-open in the agent-firm enforce gate — stop it promoting non-flow-confirmed signals during an LLM outage — and make the pipeline's silent fail-opens visible via a shared alarm helper.

**Architecture:** The scan pipeline is `intersection_results → flow gate (flow_confirmed) → edge veto → agent firm gate → trade`. The agent firm is meant to be a *filter* on top of the flow gate, but its enforce branch returns a subset of `intersection_results` (all signals) using `decision != "veto"` as the pass test. That (a) promotes candidates that failed flow confirmation and (b) fails open on LLM outage (`degraded`/`bypassed` are not vetoes, so during an outage everything passes and the flow gate is bypassed). Per the user's decision (2026-07-06), the firm **keeps** its ability to promote a *non-flow-confirmed* candidate — but **only on an explicit `approve`**; on `degraded`/`bypassed` it falls back to the flow gate's verdict (kept iff already flow-confirmed) and fires a visible alarm. A new `engine/fail_open_alarm.py` makes any fail-open (agent outage, adaptive-gate exception, whole-batch flow outage) surface in logs + Telegram instead of passing silently.

**Tech Stack:** Python 3, stdlib `logging`, `utils.telegram.send_telegram`, pytest + `unittest.mock`. No new dependencies.

---

## File Structure

- **Create** `engine/fail_open_alarm.py` — pure `format_fail_open_alarm(source, detail, count)` + side-effecting `fail_open_alarm(...)` (logs WARNING + best-effort Telegram). Single responsibility: surface fail-open events.
- **Create** `tests/test_fail_open_alarm.py` — unit tests for the helper.
- **Modify** `scheduler/scanner.py` — rewrite the enforce branch of `run_agent_firm_gate` (lines ~959-964) to Option B semantics + alarm on outage; wire the alarm into the adaptive-gate `except: pass` (~line 1299) and the whole-batch flow-outage path (~lines 1360-1363).
- **Modify** `tests/test_scheduler_firm_hook.py` — update the one test that encodes the buggy fail-open (`test_gate_enforce_mode_lets_degraded_pass_through`) and add tests for the new enforce semantics.

**Decision semantics reference (Option B), enforce mode:**

| Ticker state | Firm decision | Kept? |
|---|---|---|
| flow-confirmed | `approve` | yes |
| flow-confirmed | `veto` | **no** (veto wins over flow) |
| flow-confirmed | `degraded`/`bypassed` | yes (falls back to flow) |
| NOT flow-confirmed | `approve` | yes (**promotion**) |
| NOT flow-confirmed | `veto` | no |
| NOT flow-confirmed | `degraded`/`bypassed` | **no** (fail-closed to flow) |

Any `degraded`/`bypassed` present → fire `fail_open_alarm` once (visible outage).

---

### Task 1: Fail-open alarm helper

**Files:**
- Create: `engine/fail_open_alarm.py`
- Test: `tests/test_fail_open_alarm.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fail_open_alarm.py
"""Tests for engine.fail_open_alarm — surfacing silent fail-open events."""
import logging

import engine.fail_open_alarm as fa


def test_format_is_pure_and_includes_source_detail_count():
    msg = fa.format_fail_open_alarm("agent_firm_enforce", "LLM outage", 3)
    assert "agent_firm_enforce" in msg
    assert "LLM outage" in msg
    assert "3" in msg


def test_alarm_logs_warning(caplog):
    with caplog.at_level(logging.WARNING):
        fa.fail_open_alarm("flow_batch", "flow fetch failed", count=12, notify=False)
    assert any("flow_batch" in r.message and r.levelno == logging.WARNING
               for r in caplog.records)


def test_alarm_notifies_via_telegram_best_effort(monkeypatch):
    sent = []
    monkeypatch.setattr(fa, "send_telegram", lambda m: sent.append(m))
    fa.fail_open_alarm("agent_firm_enforce", "3 degraded", count=3, notify=True)
    assert len(sent) == 1
    assert "agent_firm_enforce" in sent[0]


def test_alarm_swallows_notifier_errors(monkeypatch):
    def _boom(_m):
        raise RuntimeError("telegram down")
    monkeypatch.setattr(fa, "send_telegram", _boom)
    # Must not raise — notification is best-effort.
    fa.fail_open_alarm("x", "y", count=1, notify=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_fail_open_alarm.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.fail_open_alarm'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/fail_open_alarm.py
"""Make silent fail-open events visible.

A "fail-open" is any point where a safety gate, on error/outage, lets signals
through (or falls back) rather than blocking. Historically these were logged at
best and never surfaced, so an LLM / flow / data outage silently degraded the
pipeline. This module records each fail-open at WARNING and best-effort notifies,
so an outage alarms instead of hiding. Import is side-effect free; call
``fail_open_alarm(...)`` at the fail-open site.
"""
import logging

from utils.telegram import send_telegram

logger = logging.getLogger(__name__)


def format_fail_open_alarm(source: str, detail: str, count: int) -> str:
    """Pure: build the human-readable alarm line (no side effects)."""
    return f"⚠️ FAIL-OPEN [{source}]: {detail} ({count} affected)"


def fail_open_alarm(source: str, detail: str, count: int = 0,
                    notify: bool = True) -> str:
    """Record a fail-open: log at WARNING and best-effort Telegram.

    Returns the formatted message. Never raises — a fail-open alarm must not
    itself break the pipeline.
    """
    msg = format_fail_open_alarm(source, detail, count)
    logger.warning(msg)
    if notify:
        try:
            send_telegram(msg)
        except Exception as _e:  # best-effort: notifier down must not raise
            logger.debug("fail_open_alarm notify failed: %s", _e)
    return msg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_fail_open_alarm.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/fail_open_alarm.py tests/test_fail_open_alarm.py
git commit -m "feat(safety): fail_open_alarm helper — surface silent fail-opens (Phase 3B)"
```

---

### Task 2: C-9 fix — agent-firm enforce gate (Option B)

**Files:**
- Modify: `scheduler/scanner.py` (function `run_agent_firm_gate`, enforce branch ~959-964)
- Test: `tests/test_scheduler_firm_hook.py`

- [ ] **Step 1: Update the test that encodes the buggy behavior + add new-semantics tests**

In `tests/test_scheduler_firm_hook.py`, **replace** the existing
`test_gate_enforce_mode_lets_degraded_pass_through` with the tests below. The old
test asserted a *non-flow-confirmed* `degraded` ticker passes — that is C-9. New
semantics: `degraded`/`bypassed` fall back to the flow gate, so a non-flow-confirmed
degraded ticker is dropped; a flow-confirmed one is kept; an explicit `approve`
still promotes a non-flow-confirmed ticker; an explicit `veto` drops even a
flow-confirmed one.

```python
def test_enforce_degraded_non_flow_confirmed_is_dropped(monkeypatch):
    """C-9 fix: degraded (LLM failed) on a NON-flow-confirmed ticker falls back
    to the flow gate → dropped. Explicit approve still promotes."""
    import engine.fail_open_alarm as fa
    monkeypatch.setattr(fa, "fail_open_alarm", lambda *a, **k: "")
    approved = MagicMock(ticker="AMMN", decision="approve")
    degraded = MagicMock(ticker="MDKA", decision="degraded")

    intersection_results = [
        _make_result("AMMN", flow_score=1, confirmed=False),
        _make_result("MDKA", flow_score=1, confirmed=False),
    ]

    result = _call_gate(intersection_results, [],
                        _mock_firm_module(lambda c: [approved, degraded]),
                        _mock_config_module(is_active=True, get_enforce=True))

    assert {r["ticker"] for r in result} == {"AMMN"}, \
        "approve promotes; degraded non-flow-confirmed is dropped"


def test_enforce_degraded_flow_confirmed_is_kept(monkeypatch):
    """degraded on a flow-confirmed ticker falls back to flow → kept."""
    import engine.fail_open_alarm as fa
    monkeypatch.setattr(fa, "fail_open_alarm", lambda *a, **k: "")
    degraded = MagicMock(ticker="BBRI", decision="degraded")

    flow_confirmed = [_make_result("BBRI", flow_score=3, confirmed=True)]
    intersection_results = list(flow_confirmed)

    result = _call_gate(intersection_results, flow_confirmed,
                        _mock_firm_module(lambda c: [degraded]),
                        _mock_config_module(is_active=True, get_enforce=True))

    assert {r["ticker"] for r in result} == {"BBRI"}


def test_enforce_veto_drops_flow_confirmed(monkeypatch):
    """Explicit veto wins over the flow gate — a flow-confirmed veto is dropped."""
    import engine.fail_open_alarm as fa
    monkeypatch.setattr(fa, "fail_open_alarm", lambda *a, **k: "")
    vetoed = MagicMock(ticker="MDKA", decision="veto")
    approved = MagicMock(ticker="BBRI", decision="approve")

    flow_confirmed = [
        _make_result("MDKA", flow_score=3, confirmed=True),
        _make_result("BBRI", flow_score=3, confirmed=True),
    ]
    intersection_results = list(flow_confirmed)

    result = _call_gate(intersection_results, flow_confirmed,
                        _mock_firm_module(lambda c: [vetoed, approved]),
                        _mock_config_module(is_active=True, get_enforce=True))

    assert {r["ticker"] for r in result} == {"BBRI"}


def test_enforce_outage_fires_fail_open_alarm(monkeypatch):
    """Any degraded/bypassed present → a single visible fail-open alarm fires."""
    import engine.fail_open_alarm as fa
    calls = []
    monkeypatch.setattr(fa, "fail_open_alarm",
                        lambda *a, **k: calls.append((a, k)) or "")
    degraded = MagicMock(ticker="MDKA", decision="degraded")
    bypassed = MagicMock(ticker="ANTM", decision="bypassed")

    intersection_results = [
        _make_result("MDKA", flow_score=1, confirmed=False),
        _make_result("ANTM", flow_score=1, confirmed=False),
    ]

    _call_gate(intersection_results, [],
               _mock_firm_module(lambda c: [degraded, bypassed]),
               _mock_config_module(is_active=True, get_enforce=True))

    assert len(calls) == 1, "outage must alarm exactly once per gate call"
```

Note: `test_gate_enforce_mode_filters_from_intersection_results` (AMMN approve /
MDKA veto, both non-flow-confirmed) stays valid under Option B — approve promotes
AMMN, veto drops MDKA → result `[AMMN]`. Leave it unchanged.

- [ ] **Step 2: Run tests to verify the new ones fail (and the stale one is gone)**

Run: `./venv/bin/python -m pytest tests/test_scheduler_firm_hook.py -q`
Expected: FAIL — the 4 new `test_enforce_*` tests fail because `run_agent_firm_gate`
still uses the old `decision != "veto"` pass-set from `intersection_results` and
does not import/fire `fail_open_alarm`.

- [ ] **Step 3: Rewrite the enforce branch (Option B)**

In `scheduler/scanner.py`, replace the enforce block inside `run_agent_firm_gate`
(currently):

```python
        if _firm_cfg.get_enforce():
            # Pass-set is the evaluated candidates that were not explicitly vetoed.
            # Fail-open: degraded/bypassed (LLM failed or spend-capped) proceed per
            # the decision contract; only an explicit veto blocks a signal.
            _pass = {d.ticker for d in _decisions if d.decision != "veto"}
            return [r for r in intersection_results if r["ticker"] in _pass]

        return flow_confirmed
```

with:

```python
        if _firm_cfg.get_enforce():
            # C-9 fix (Phase 3B): the firm is a filter ON TOP OF the flow gate.
            #   approve  → kept (may promote a non-flow-confirmed candidate)
            #   veto     → dropped (wins even over a flow-confirmed signal)
            #   degraded / bypassed → NO real evaluation → fall back to the flow
            #     gate's verdict (kept iff already flow-confirmed) + alarm, so an
            #     LLM outage can no longer silently promote every signal.
            _approved = {d.ticker for d in _decisions if d.decision == "approve"}
            _vetoed = {d.ticker for d in _decisions if d.decision == "veto"}
            _outage = [d.ticker for d in _decisions
                       if d.decision in ("degraded", "bypassed")]
            if _outage:
                from engine.fail_open_alarm import fail_open_alarm
                fail_open_alarm(
                    "agent_firm_enforce",
                    f"{len(_outage)} degraded/bypassed → flow-gate fallback",
                    count=len(_outage),
                )
            _flow_tickers = {r["ticker"] for r in flow_confirmed}
            _kept_fc = [r for r in flow_confirmed if r["ticker"] not in _vetoed]
            _promoted = [r for r in intersection_results
                         if r["ticker"] in _approved
                         and r["ticker"] not in _flow_tickers]
            return _kept_fc + _promoted

        return flow_confirmed
```

Also update the function docstring line
`    - enforce mode → agent-approved tickers from intersection_results[:20]`
to:
`    - enforce mode → flow_confirmed minus vetoes, plus explicitly-approved`
`      promotions; degraded/bypassed fall back to the flow gate (+ alarm).`

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/test_scheduler_firm_hook.py -q`
Expected: PASS (all enforce tests green, including the unchanged approve/veto test)

- [ ] **Step 5: Commit**

```bash
git add scheduler/scanner.py tests/test_scheduler_firm_hook.py
git commit -m "fix(safety): C-9 — agent-firm enforce is flow-gate filter, fail-closed on LLM outage (Phase 3B)"
```

---

### Task 3: Surface the two remaining silent fail-opens

**Files:**
- Modify: `scheduler/scanner.py` (adaptive-gate `except: pass` ~1299; whole-batch flow outage ~1360-1363)

These two sites currently swallow failures silently. Make them visible with the
Task-1 helper. No behavior change to the pipeline's pass/block logic — only
observability. (These are exercised via the live scan, not unit-tested here;
keep the edits minimal and mechanical.)

- [ ] **Step 1: Alarm on whole-batch flow outage**

In `scheduler/scanner.py`, the flow-fetch `except` (~line 1360) sets every result
to `UNAVAILABLE`. That is correctly fail-*closed* for the flow gate but silent.
Add an alarm. Replace:

```python
        except Exception as e:
            print(f"[{time_str}] Flow fetch error: {e}")
            for r in intersection_results:
                r['flow'] = {'score': None, 'verdict': 'UNAVAILABLE', 'confirmed': False}
```

with:

```python
        except Exception as e:
            print(f"[{time_str}] Flow fetch error: {e}")
            from engine.fail_open_alarm import fail_open_alarm
            fail_open_alarm("flow_batch", f"flow fetch failed: {str(e)[:120]}",
                            count=len(intersection_results))
            for r in intersection_results:
                r['flow'] = {'score': None, 'verdict': 'UNAVAILABLE', 'confirmed': False}
```

- [ ] **Step 2: Alarm on the adaptive-gate exception swallow**

Find the `pass  # fail-open: don't block a ticker because the gate threw` (~line
1299). Read the surrounding `try/except` (roughly 10 lines above it) to get the
exact indentation and the loop variable in scope (the per-ticker `ticker`
name). Replace the bare swallow:

```python
            except Exception:
                pass  # fail-open: don't block a ticker because the gate threw
```

with (matching the file's existing indentation exactly):

```python
            except Exception as _gate_err:
                # fail-open: don't block a ticker because the gate threw — but
                # make it visible rather than silent (Phase 3B).
                from engine.fail_open_alarm import fail_open_alarm
                fail_open_alarm("adaptive_gate",
                                f"gate error, ticker passed: {str(_gate_err)[:120]}",
                                count=1, notify=False)
```

Note: `notify=False` here — a per-ticker gate error inside the scan loop can fire
many times; log-only avoids Telegram spam. The flow-batch alarm (Step 1) fires
once per scan, so it notifies.

- [ ] **Step 3: Verify import resolves and nothing else broke**

Run: `./venv/bin/python -c "import scheduler.scanner"`
Expected: no error (imports resolve).

Run: `./venv/bin/python -m pytest tests/test_scheduler_firm_hook.py tests/test_fail_open_alarm.py tests/test_agent_size_hint.py tests/test_bear_watchlist_ranking.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add scheduler/scanner.py
git commit -m "feat(safety): alarm on flow-batch outage + adaptive-gate swallow (Phase 3B)"
```

---

### Task 4: Full-suite regression + finish

- [ ] **Step 1: Run the full test suite**

Run: `./venv/bin/python -m pytest -q`
Expected: no NEW failures vs baseline (baseline before this branch: ~1041 passed,
3 skipped). The only intentionally changed test is the replaced
`test_gate_enforce_mode_lets_degraded_pass_through` (removed) → superseded by the
4 new `test_enforce_*` tests.

- [ ] **Step 2: Finish the branch**

Announce and use the **superpowers:finishing-a-development-branch** skill:
verify tests green → present options → push + PR to `master` → manual-merge (repo
disallows GitHub auto-merge) → deploy by restarting the app via `./start.sh` in a
quiet slot.

PR body should note: C-9 closed per Option B (firm keeps explicit-approve
promotion but falls back to the flow gate on `degraded`/`bypassed`, with a visible
fail-open alarm); two additional silent fail-opens (flow-batch outage,
adaptive-gate swallow) now alarm.

---

## Self-Review Notes

- **Spec coverage:** C-9 fix (Task 2) ✓; flow-gate asymmetry — resolved by the
  enforce fallback-to-flow (Task 2) and made visible (Task 3) ✓; fail-open alarm
  helper (Task 1) + wiring (Tasks 2, 3) ✓.
- **Type consistency:** helper is `fail_open_alarm(source, detail, count=0,
  notify=True) -> str` everywhere; `format_fail_open_alarm(source, detail, count)`
  pure. Enforce branch uses `flow_confirmed` (list of result dicts) and
  `intersection_results` (list of result dicts) — same shapes already in the
  function.
- **Behavior change is intentional and localized:** only the enforce branch and
  one test change trading behavior; Tasks 1 & 3 are observability-only.
