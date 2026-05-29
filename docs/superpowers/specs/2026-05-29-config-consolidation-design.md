# Config Consolidation — Design Spec

_Date: 2026-05-29_
_Task: TODO Sprint 12 R2_

---

## Problem

`DB_PATH` is defined in 10+ files. `load_dotenv()` is called in 4 entry points. Four files hardcode the absolute DB path with no `os.getenv()` fallback at all. `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are duplicated across 5 files. There is no single source of truth.

---

## Solution

Create `config.py` at project root. It calls `load_dotenv()` once and exports all shared env-var constants. Every module imports from it instead of re-reading the environment.

---

## `config.py` (new file)

```python
from pathlib import Path
from dotenv import load_dotenv
import os

_BASE = Path(__file__).parent
load_dotenv(_BASE / ".env")

DB_PATH                 = os.getenv("DB_PATH", str(_BASE / "data" / "walkforward.db"))
TELEGRAM_TOKEN          = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID        = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_URL             = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH            = os.getenv("WEBHOOK_PATH", "/telegram/updates")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
FLASK_SECRET_KEY        = os.getenv("FLASK_SECRET_KEY", "")
SECTORS_APP_MODE        = os.getenv("SECTORS_APP_MODE", "off").strip().lower()
```

`DB_PATH` is resolved relative to `config.py`'s own location, so it is correct regardless of the working directory at import time.

---

## Files to Update

Each file gets `from config import <needed_names>` at the top and loses its local definitions.

| File | Remove | Import |
|------|--------|--------|
| `app.py` | `load_dotenv()`, lines 19–24, 27 (`app.secret_key = os.getenv(...)`) | `DB_PATH, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, WEBHOOK_URL, WEBHOOK_PATH, TELEGRAM_WEBHOOK_SECRET, FLASK_SECRET_KEY` |
| `scheduler.py` | `load_dotenv()`, lines 17–20 | `DB_PATH, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SECTORS_APP_MODE` |
| `paper_trade.py` | `load_dotenv()`, line 12 | `DB_PATH` |
| `monitor.py` | 5 inline `os.getenv('DB_PATH', ...)` calls + lines 13–14 | `DB_PATH, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID` |
| `data/db.py` | line 5 local definition | `DB_PATH` |
| `screener/db.py` | line 7 local definition | `DB_PATH` |
| `screener/brpt_filter.py` | line 45 hardcoded `_DB_PATH` | `DB_PATH` (rename refs from `_DB_PATH` → `DB_PATH`) |
| `screener/idx_scraper.py` | line 28 hardcoded `_DB_PATH` | `DB_PATH` |
| `engine/sector_rotation.py` | line 14 local definition | `DB_PATH` |
| `engine/sectors_app_filter.py` | line 33 local definition | `DB_PATH` |
| `engine/suspension_detector.py` | lines 94–96 `_DEFAULT_DB_PATH = os.getenv(...)` | `DB_PATH` — rename `_DEFAULT_DB_PATH` → `DB_PATH` in the two `db_path or _DEFAULT_DB_PATH` call sites |
| `news_filter.py` | line 26 hardcoded `_DB_PATH` | `DB_PATH` |
| `flow_filter.py` | line 29 hardcoded `_DB_PATH` | `DB_PATH` |
| `engine/regime_filter.py` | hardcoded path in `__main__` block (line 350, local scope only) | add `from config import DB_PATH` inside the `if __name__ == "__main__":` block |
| `stockbit_fetcher.py` | lines 96–97 `os.environ.get(...)` | `TELEGRAM_TOKEN, TELEGRAM_CHAT_ID` |

---

## Out of Scope

- `engine/agent_firm/config.py` — self-contained DeepSeek/Tavily subsystem, leave it
- `auto_token.py` — standalone Stockbit token-refresh script; keeps its own `load_dotenv()` and `STOCKBIT_USER/PASS`
- `_archive/` — dead code
- `tests/` — test fixtures use `monkeypatch.setenv("DB_PATH", ...)` which overrides env at runtime; no change needed

---

## `app.py` special case

`app.secret_key` is currently set as:
```python
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)
```
After the change, `FLASK_SECRET_KEY` from config will be `""` (empty string) when unset. The `or os.urandom(32)` fallback in `app.py` handles this correctly — empty string is falsy, so the random fallback fires. No behaviour change.

---

## Testing

- `pytest` full suite must pass after the change
- Manually verify Flask app starts (`systemctl status idx-walkforward-5001`) with correct DB path
- No `load_dotenv` or `os.getenv("DB_PATH"` remaining in active-codebase `.py` files (except `config.py` itself, `engine/agent_firm/config.py`, `engine/pattern_backtest.py` CLI arg default, and `auto_token.py`)

---

## What Changes at Runtime

Nothing. `config.py` reads the same `.env` file that `load_dotenv()` was reading before. All values are identical. The only difference is that `.env` is read once instead of multiple times on import.
