# Agent Firm Mode Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an OFF / SHADOW / ENFORCE segmented pill to the dashboard topbar that toggles Agent Firm mode at runtime without restarting the server.

**Architecture:** Add a `_runtime` mutable dict to `config.py` that overrides env-var constants at runtime; a new `POST /api/agent/config` endpoint writes it; the topbar pill calls that endpoint and updates the UI. State is session-only — resets to `.env` values on restart.

**Tech Stack:** Python/Flask (backend), vanilla JS + inline styles (frontend, matching existing pattern)

---

### Task 1: Add runtime override to `engine/agent_firm/config.py`

**Files:**
- Modify: `engine/agent_firm/config.py`

- [x] **Step 1: Add `_runtime`, `set_mode()`, `get_enforce()`, update `is_active()`**

Replace the existing `is_active()` function with the following additions at the bottom of the file:

```python
_runtime: dict | None = None


def set_mode(enabled: bool, enforce: bool) -> None:
    global _runtime
    _runtime = {"enabled": enabled, "enforce": enforce}


def get_enforce() -> bool:
    return _runtime["enforce"] if _runtime is not None else FIRM_ENFORCE


def is_active() -> bool:
    enabled = _runtime["enabled"] if _runtime is not None else FIRM_ENABLED
    if not enabled:
        return False
    if KILL_SWITCH_FILE.exists():
        return False
    return True
```

Final file should look like:

```python
"""Agent firm configuration via environment variables.

All settings have sensible defaults. The firm is OFF by default to ensure
Phase 1 production deploy has zero behavioral impact.
"""

import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


FIRM_ENABLED = _env_bool("AGENT_FIRM_ENABLED", False)
FIRM_ENFORCE = _env_bool("AGENT_FIRM_ENFORCE", False)

DAILY_SPEND_CAP_USD = float(os.getenv("AGENT_FIRM_DAILY_CAP", "5.0"))
KILL_SWITCH_FILE = Path(os.getenv("AGENT_FIRM_KILL_FILE", "/tmp/agent_firm.disable"))

MODEL_ID = os.getenv("AGENT_FIRM_MODEL", "deepseek-v4-pro")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

PRICE_INPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_IN", "0.435"))
PRICE_OUTPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_OUT", "0.870"))

PER_AGENT_TIMEOUT_S = float(os.getenv("AGENT_FIRM_AGENT_TIMEOUT", "75"))

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_MAX_RESULTS = int(os.getenv("AGENT_FIRM_TAVILY_MAX", "5"))

_runtime: dict | None = None


def set_mode(enabled: bool, enforce: bool) -> None:
    global _runtime
    _runtime = {"enabled": enabled, "enforce": enforce}


def get_enforce() -> bool:
    return _runtime["enforce"] if _runtime is not None else FIRM_ENFORCE


def is_active() -> bool:
    enabled = _runtime["enabled"] if _runtime is not None else FIRM_ENABLED
    if not enabled:
        return False
    if KILL_SWITCH_FILE.exists():
        return False
    return True
```

- [x] **Step 2: Verify syntax**

```bash
python3 -c "from engine.agent_firm import config; print(config.is_active(), config.get_enforce())"
```

Expected: `True False` (since AGENT_FIRM_ENABLED=true in .env, ENFORCE not set)

- [x] **Step 3: Commit**

```bash
git add engine/agent_firm/config.py
git commit -m "feat(agent-firm): add runtime mode override with set_mode/get_enforce"
```

---

### Task 2: Add `POST /api/agent/config` to `app.py` and fix `agent_status`

**Files:**
- Modify: `app.py:808-814` (agent_status), insert after line 814

- [x] **Step 1: Update `agent_status` to use `get_enforce()`**

In `app.py` line 810, change:
```python
        "enforce": _agent_config.FIRM_ENFORCE,
```
to:
```python
        "enforce": _agent_config.get_enforce(),
```

- [x] **Step 2: Add `POST /api/agent/config` route after `agent_status`**

Insert after the closing of `agent_status` (after line 814, before `@app.route("/api/agent/audit"`):

```python
@app.route("/api/agent/config", methods=["POST"])
def agent_config():
    from engine.agent_firm import config as _agent_config
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")
    if mode not in ("off", "shadow", "enforce"):
        return jsonify({"error": "mode must be off, shadow, or enforce"}), 400
    _agent_config.set_mode(enabled=mode in ("shadow", "enforce"), enforce=mode == "enforce")
    return jsonify({
        "enabled": _agent_config.is_active() or mode in ("shadow", "enforce"),
        "enforce": _agent_config.get_enforce(),
        "active": _agent_config.is_active(),
    })
```

- [x] **Step 3: Verify endpoint**

```bash
curl -s -X POST http://localhost:5001/api/agent/config \
  -H "Content-Type: application/json" \
  -d '{"mode":"shadow"}' | python3 -m json.tool
```

Expected:
```json
{
    "active": true,
    "enabled": true,
    "enforce": false
}
```

```bash
curl -s -X POST http://localhost:5001/api/agent/config \
  -H "Content-Type: application/json" \
  -d '{"mode":"off"}' | python3 -m json.tool
```

Expected:
```json
{
    "active": false,
    "enabled": false,
    "enforce": false
}
```

- [x] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat(agent-firm): add POST /api/agent/config for runtime mode switching"
```

---

### Task 3: Update `scheduler.py` to use `get_enforce()`

**Files:**
- Modify: `scheduler.py:800`

- [x] **Step 1: Swap `FIRM_ENFORCE` for `get_enforce()`**

Line 800, change:
```python
            if _firm_cfg.FIRM_ENFORCE:
```
to:
```python
            if _firm_cfg.get_enforce():
```

- [x] **Step 2: Commit**

```bash
git add scheduler.py
git commit -m "feat(agent-firm): scheduler uses get_enforce() to respect runtime mode"
```

---

### Task 4: Add pill to topbar in `templates/backtest_multi.html`

**Files:**
- Modify: `templates/backtest_multi.html:477-495` (badge script), `templates/backtest_multi.html:508-518` (top-right div)

- [x] **Step 1: Insert pill HTML into `top-right` div**

In the `<div class="top-right">` block (lines 508-518), insert the pill before the closing `</div>` (before line 518's `</div>`), after the tweaks button:

```html
    <div id="firm-pill" style="display:flex;border:1px solid #333;border-radius:5px;overflow:hidden;font-size:10px;margin-right:2px;">
      <button id="firm-off"     onclick="setFirmMode('off')"     style="padding:3px 9px;border:none;cursor:pointer;background:#1f1f1f;color:#fff;font-weight:700;">OFF</button>
      <button id="firm-shadow"  onclick="setFirmMode('shadow')"  style="padding:3px 9px;border:none;cursor:pointer;border-left:1px solid #333;background:#111;color:#555;">SHADOW</button>
      <button id="firm-enforce" onclick="setFirmMode('enforce')" style="padding:3px 9px;border:none;cursor:pointer;border-left:1px solid #333;background:#111;color:#555;">ENFORCE</button>
    </div>
```

- [x] **Step 2: Add `updateFirmPill` and `setFirmMode` JS functions**

Replace the existing badge `<script>` block (lines 477-496) with this expanded version:

```html
<script>
function updateFirmPill(active, enforce) {
  const off = document.getElementById('firm-off');
  const shadow = document.getElementById('firm-shadow');
  const enf = document.getElementById('firm-enforce');
  const pill = document.getElementById('firm-pill');
  if (!off) return;
  [off, shadow, enf].forEach(b => { b.style.background='#111'; b.style.color='#555'; b.style.fontWeight=''; });
  if (!active) {
    off.style.background='#1f1f1f'; off.style.color='#fff'; off.style.fontWeight='700';
    pill.style.borderColor='#333';
  } else if (enforce) {
    enf.style.background='#052e16'; enf.style.color='#4ade80'; enf.style.fontWeight='700';
    pill.style.borderColor='#16a34a';
  } else {
    shadow.style.background='#2d2200'; shadow.style.color='#fbbf24'; shadow.style.fontWeight='700';
    pill.style.borderColor='#92400e';
  }
}

function setFirmMode(mode) {
  if (mode === 'enforce' && !confirm('Switch to ENFORCE?\n\nVetoed tickers will be dropped from paper trade signals.')) return;
  fetch('/api/agent/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mode})
  })
  .then(r => r.ok ? r.json() : Promise.reject())
  .then(s => {
    updateFirmPill(s.active, s.enforce);
    const el = document.getElementById('agent-firm-state');
    const badge = document.getElementById('agent-firm-badge');
    if (el && badge) {
      if (!s.active) { el.textContent='OFF'; el.style.color='#888'; badge.style.color='#888'; badge.style.borderColor='#444'; }
      else { el.textContent = s.enforce ? 'ENFORCE' : 'SHADOW'; badge.style.color = s.enforce ? '#fff' : '#fc0'; badge.style.borderColor = s.enforce ? '#0c0' : '#fc0'; }
    }
  })
  .catch(() => { if (typeof showToast === 'function') showToast('Agent firm update failed', 'error'); });
}

fetch('/api/agent/status').then(r => r.json()).then(s => {
  const el = document.getElementById('agent-firm-state');
  const badge = document.getElementById('agent-firm-badge');
  const st = s.today_stats || {};
  const statsLine = st.evaluated
    ? ` | ${st.evaluated} eval · ${st.approved} ✓ · ${st.vetoed} ✗ · $${(st.cost_usd||0).toFixed(4)}`
    : '';
  if (s.active) {
    el.textContent = (s.enforce ? 'ENFORCE' : 'SHADOW') + statsLine;
    badge.style.color = s.enforce ? '#fff' : '#fc0';
    badge.style.borderColor = s.enforce ? '#0c0' : '#fc0';
  } else {
    el.textContent = 'OFF';
    el.style.color = '#888';
  }
  updateFirmPill(s.active, s.enforce);
}).catch(() => {
  document.getElementById('agent-firm-state').textContent = 'ERR';
});
</script>
```

- [x] **Step 3: Verify in browser**

Open `http://localhost:5001` — topbar should show OFF/SHADOW/ENFORCE pill with SHADOW highlighted amber (current state). Click ENFORCE, confirm dialog should appear. Click cancel — pill stays on SHADOW. Click OFF — pill goes neutral.

- [x] **Step 4: Commit**

```bash
git add templates/backtest_multi.html
git commit -m "feat(agent-firm): add OFF/SHADOW/ENFORCE topbar pill with confirm on enforce"
```
