"""Root pytest configuration.

Guarantees pytest can never send a real Telegram message, no matter what
TELEGRAM_TOKEN/TELEGRAM_CHAT_ID are set to in .env (or in the shell) on the
machine running the suite.

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

os.environ["TELEGRAM_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""
