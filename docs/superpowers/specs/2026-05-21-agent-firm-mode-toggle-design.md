# Agent Firm Mode Toggle — Design Spec

**Date:** 2026-05-21  
**Status:** Approved

## Summary

Add a segmented OFF / SHADOW / ENFORCE pill to the dashboard topbar so the Agent Firm mode can be changed without editing `.env` or restarting the server. State is session-only (resets to whatever `.env` says on restart).

## Backend

### `engine/agent_firm/config.py`

Add a module-level `_runtime` dict (initially `None`) and two functions:

- `set_mode(enabled: bool, enforce: bool) -> None` — writes `_runtime`
- `get_enforce() -> bool` — returns `_runtime["enforce"]` if set, else `FIRM_ENFORCE`
- Update `is_active()` — checks `_runtime["enabled"]` if set, else `FIRM_ENABLED`

### `app.py`

- Add `POST /api/agent/config` — accepts `{"mode": "off"|"shadow"|"enforce"}`, calls `config.set_mode()`, returns updated status JSON
- Update `agent_status()` — replace `_agent_config.FIRM_ENFORCE` with `_agent_config.get_enforce()`

### `scheduler.py`

- Line ~800: replace `_firm_cfg.FIRM_ENFORCE` with `_firm_cfg.get_enforce()`

## Frontend (`templates/backtest_multi.html`)

### Topbar pill

Insert a segmented pill (OFF / SHADOW / ENFORCE) into the topbar `top-right` div area, right of the market clock. Follows existing `.seg button` pattern.

Active state colours:
- OFF — white text, neutral border
- SHADOW — `#fbbf24` amber, `#2d2200` background
- ENFORCE — `#4ade80` green, `#052e16` background

### Behaviour

- On page load: call `/api/agent/status`, set active segment from `(active, enforce)` flags
- OFF / SHADOW click: `POST /api/agent/config {mode}` immediately, then refresh pill + existing badge
- ENFORCE click: show confirm modal first ("Vetoed tickers will be dropped from paper trade signals"), then POST on confirm
- On API error: show toast notification, revert pill to previous state

### Confirm modal

Reuses existing modal markup pattern. Plain `confirm()` dialog is acceptable if modal is complex.

## Constraints

- Session-only: no writes to `.env`, no server restart
- Kill-switch file (`/tmp/agent_firm.disable`) takes precedence over runtime state — if present, firm stays inactive regardless
- Existing badge (top-right read-only display) stays unchanged; pill POST updates both
