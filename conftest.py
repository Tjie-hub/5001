"""Root pytest configuration.

Guarantees pytest can never send a real Telegram message, no matter what
TELEGRAM_TOKEN/TELEGRAM_CHAT_ID are set to in .env (or in the shell) on the
machine running the suite, and can never touch the real database under
data/ (DB_PATH is pinned below, before config.py is first imported).

Root cause this closes: config.py:16 calls `load_dotenv(_BASE / ".env")` at
import time, unconditionally, in every process that imports `config` --
which most test modules do transitively (e.g. via `scheduler.jobs`). Every
send_telegram()-shaped function in this repo (utils.telegram.send_telegram,
stockbit_fetcher.send_telegram, auto_token's module-level TELEGRAM_TOKEN/
TELEGRAM_CHAT_ID, ...) ultimately reads those two credentials from the
process environment, with no test/dry-run switch of its own -- so a test
that forgets to mock its send_telegram call sends a real message. This is
what happened in tests/forward_testing/test_scheduler_job.py
(test_cycle_ingests_and_opens / test_cycle_is_idempotent).

Mechanism: the two lines below run as plain module-level code, so they
execute at conftest.py IMPORT time -- pytest loads the rootdir conftest.py
before collecting (importing) any test module or subdirectory conftest.py,
so this always runs before config.py, utils/telegram.py, stockbit_fetcher.py,
auto_token.py, or any test file gets a chance to read/capture a credential.
Forcing the keys to an empty string here means python-dotenv's later
load_dotenv() call (override=False by default) leaves them alone -- the real
values from .env are never loaded into this process at all, so every
send_telegram()-shaped function's own existing
`if not token or not chat_id: return` guard fires by default. No production
code path is touched.

Opt-in for a real integration test (if one is ever intentionally added):
override the credential for that one test with
`monkeypatch.setenv("TELEGRAM_TOKEN", "...")` /
`monkeypatch.setenv("TELEGRAM_CHAT_ID", "...")`, or
`monkeypatch.setattr(<module>, "TELEGRAM_TOKEN", "...")` for a module that
captured its own constant at import time (e.g. auto_token.py) -- monkeypatch
always wins for the duration of that test and reverts automatically
afterwards. This is the same pattern already used by
tests/test_telegram_util.py and tests/test_auto_token.py.
"""
import os
import tempfile

os.environ["TELEGRAM_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""

# Same mechanism for the database path (2026-09-30). config.py:22 reads
# DB_PATH from the environment at import time, ~20 modules freeze that value
# with `from config import DB_PATH`, and security/audit_trail.py:32 re-reads
# os.getenv("DB_PATH", config.DB_PATH) on every call. Without this pin, any
# test that reaches those resolvers creates or writes
# <repo>/data/walkforward.db -- on a dev/production checkout that is the real
# multi-GB database. Forensic trigger: 245 provider_switch audit rows in
# D:\IDX\data\walkforward.db carry tests/agent_firm/providers/test_alerts.py's
# frozen _RESET_A timestamp ("resumes ~2026-07-10T11:20:00+00:00") across
# 2026-07-10..2026-09-30 -- every suite run on that box appended audit rows
# to the real DB (one run = 10 rows, reproduced in a fresh clone).
# One scratch database per suite run here (covers import-time bindings); the
# per-test layer lives in tests/conftest.py::_isolate_db_path. A test that
# needs its own database passes db_path=/uses tmp_path, or monkeypatches
# DB_PATH itself (monkeypatch wins for that test, same opt-in rule as the
# Telegram pins above).
os.environ["DB_PATH"] = os.path.join(
    tempfile.mkdtemp(prefix="idx-test-db-"), "walkforward.db")
