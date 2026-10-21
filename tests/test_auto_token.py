"""Regression tests for the Stockbit token-refresh hardening (incident 2026-07-27).

Root cause: `should_skip_refresh()` used a flat 6h-remaining threshold that did
not account for the gap to the day's last consumer (18:30/20:15 WIB crons). A
token issued off-schedule (2026-07-26 17:31) still had 8.9h remaining at the
next 08:40 check -- past the old 6h bar -- so the proactive refresh was
skipped, and the token expired at 17:31, one hour before the 18:30
`stockbit_flow` cron needed it. See docs/audit/STOCKBIT_TOKEN_REFRESH_HARDENING.md.

These tests exercise the pure logic in auto_token.py with monkeypatched I/O
(no real Playwright browser, no real network, no real files) -- see
tests/test_stockbit_fetcher_ensure_valid_token.py for the companion fix to the
manual-token fallback bypass (the second, compounding root cause).
"""
import base64
import json
import os
import re
import stat
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

import auto_token as at

# Captured before the module-level `no_telegram` autouse fixture (below) can
# monkeypatch at.send_telegram to a no-op -- TestSendTelegramRedaction calls
# this directly so it exercises the REAL implementation, not the test-suite's
# safety-net mock.
_real_send_telegram = at.send_telegram


def _make_jwt(iat_offset_h=0.0, exp_offset_h=24.0):
    """Build a syntactically-valid JWT with iat/exp claims offset from now."""
    now = time.time()
    payload = {
        "iat": int(now + iat_offset_h * 3600),
        "exp": int(now + exp_offset_h * 3600),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    header_b64 = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.fakesignature"


@pytest.fixture
def token_file(tmp_path, monkeypatch):
    f = tmp_path / ".stockbit_token"
    monkeypatch.setattr(at, "TOKEN_FILE", f)
    return f


@pytest.fixture
def lock_file(tmp_path, monkeypatch):
    f = tmp_path / ".stockbit_token.lock"
    monkeypatch.setattr(at, "LOCK_FILE", f)
    return f


@pytest.fixture(autouse=True)
def no_telegram(monkeypatch):
    monkeypatch.setattr(at, "send_telegram", lambda *a, **k: None)


@pytest.fixture(autouse=True)
def isolated_log_file(tmp_path, monkeypatch):
    """at.log() appends to LOG_FILE at call time — without this redirect the suite
    wrote fake "Token refreshed" lines into the real logs/auto_token.log, where
    they have been mistaken for run evidence."""
    monkeypatch.setattr(at, "LOG_FILE", tmp_path / "auto_token.log")


@pytest.fixture(autouse=True)
def isolated_state_dirs(tmp_path, monkeypatch):
    """at.main() runs the T3 legacy-state migration first; without this
    redirect the suite would MOVE THE LIVE repo .playwright_state/ (the real
    Stockbit login) as a side effect of running the tests."""
    monkeypatch.setattr(at, "LEGACY_STATE_DIR", tmp_path / "legacy_state")
    monkeypatch.setattr(at, "STATE_DIR", tmp_path / "state_dir")


# ── should_skip_refresh: margin threshold (Requirement 2 + 3) ──

def test_skips_when_remaining_exceeds_margin(token_file, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=20))  # 20h remaining
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at.should_skip_refresh(margin_hours=14) is True


def test_does_not_skip_within_margin_the_2026_07_27_regression(token_file, monkeypatch):
    """Pins the exact incident: 8.9h remaining must NOT be treated as fresh."""
    token_file.write_text(_make_jwt(exp_offset_h=8.9))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at.should_skip_refresh(margin_hours=at.REFRESH_MARGIN_HOURS) is False


def test_does_not_skip_when_already_expired(token_file, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=-1))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at.should_skip_refresh(margin_hours=14) is False


def test_does_not_skip_on_implausible_remaining_clock_skew(token_file, monkeypatch):
    """A token claiming >48h remaining (impossible for a 24h-TTL token) is
    treated as a clock-skew/corruption signal, not as 'very fresh'."""
    token_file.write_text(_make_jwt(exp_offset_h=100))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at.should_skip_refresh(margin_hours=14) is False


def test_does_not_skip_when_verify_fails_even_if_time_remains(token_file, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=20))
    monkeypatch.setattr(at, "verify_token", lambda t: False)
    assert at.should_skip_refresh(margin_hours=14) is False


def test_does_not_skip_when_no_token_file(token_file):
    assert at.should_skip_refresh(margin_hours=14) is False


# ── atomic token write (Requirement 3) ──

def test_write_token_atomic_writes_content_and_mode(token_file):
    at._write_token_atomic("abc.def.ghi", token_file=token_file)
    assert token_file.read_text() == "abc.def.ghi"
    mode = stat.S_IMODE(os.stat(token_file).st_mode)
    assert mode == 0o600


def test_write_token_atomic_leaves_no_temp_file_on_success(token_file):
    at._write_token_atomic("abc.def.ghi", token_file=token_file)
    leftovers = list(token_file.parent.glob(".stockbit_token.*.tmp"))
    assert leftovers == []


def test_write_token_atomic_never_leaves_partial_file_on_failure(token_file, monkeypatch):
    token_file.write_text("old-valid-token")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(os, "fdopen", boom)
    with pytest.raises(OSError):
        at._write_token_atomic("new-token", token_file=token_file)

    # original file untouched -- a failed write must never corrupt the
    # existing credential
    assert token_file.read_text() == "old-valid-token"
    leftovers = list(token_file.parent.glob(".stockbit_token.*.tmp"))
    assert leftovers == []


# ── retry with backoff (Requirement 3: transient failures) ──

def test_retry_with_backoff_succeeds_after_transient_failures():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("transient")
        return "token-value"

    slept = []
    result = at._retry_with_backoff(
        flaky, max_retries=3, backoff_base=1, label="test", sleep_fn=slept.append
    )
    assert result == "token-value"
    assert len(calls) == 3
    assert slept == [1, 2]  # exponential: 1*2^0, 1*2^1


def test_retry_with_backoff_returns_none_after_exhausting_all_attempts():
    def always_fails():
        raise ConnectionError("permanent-ish")

    result = at._retry_with_backoff(
        always_fails, max_retries=3, backoff_base=0, label="test", sleep_fn=lambda s: None
    )
    assert result is None


def test_retry_with_backoff_treats_falsy_result_as_failure_and_retries():
    calls = []

    def returns_none_then_value():
        calls.append(1)
        return None if len(calls) < 2 else "ok"

    result = at._retry_with_backoff(
        returns_none_then_value, max_retries=3, backoff_base=0, label="test", sleep_fn=lambda s: None
    )
    assert result == "ok"
    assert len(calls) == 2


# ── concurrency lock (Requirement 3 + 5: prevent concurrent refreshes) ──

def test_refresh_lock_blocks_a_second_concurrent_acquire(lock_file):
    with at._refresh_lock(lock_path=lock_file) as first_acquired:
        assert first_acquired is True
        with at._refresh_lock(lock_path=lock_file) as second_acquired:
            assert second_acquired is False


def test_refresh_lock_is_released_after_context_exits(lock_file):
    with at._refresh_lock(lock_path=lock_file) as acquired:
        assert acquired is True
    with at._refresh_lock(lock_path=lock_file) as acquired_again:
        assert acquired_again is True


# ── preserve existing token on refresh failure (Requirement 4) ──

def test_old_token_still_safe_true_when_valid_and_recent(token_file, monkeypatch):
    token_file.write_text(_make_jwt(iat_offset_h=-5))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at._old_token_still_safe(max_age_hours=20, token_file=token_file) is True


def test_old_token_still_safe_false_when_too_old(token_file, monkeypatch):
    token_file.write_text(_make_jwt(iat_offset_h=-21))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at._old_token_still_safe(max_age_hours=20, token_file=token_file) is False


def test_old_token_still_safe_false_when_verify_fails(token_file, monkeypatch):
    token_file.write_text(_make_jwt(iat_offset_h=-1))
    monkeypatch.setattr(at, "verify_token", lambda t: False)
    assert at._old_token_still_safe(max_age_hours=20, token_file=token_file) is False


def test_old_token_still_safe_false_when_no_file(token_file):
    assert at._old_token_still_safe(max_age_hours=20, token_file=token_file) is False


# ── end-to-end main() behavior (mocked I/O) ──

@pytest.fixture
def no_state_dir(monkeypatch, tmp_path):
    # keep check_state_size/cleanup_zombies inert -- not under test here
    monkeypatch.setattr(at, "check_state_size", lambda: None)
    monkeypatch.setattr(at, "cleanup_zombies", lambda: None)


def test_normal_refresh_writes_fresh_token(token_file, lock_file, no_state_dir, monkeypatch):
    fresh = _make_jwt(iat_offset_h=0, exp_offset_h=24)
    monkeypatch.setattr(at, "auto_refresh", lambda: fresh)
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    monkeypatch.setattr(at, "credential_login", lambda: (_ for _ in ()).throw(AssertionError("should not be called")))

    at.main()

    assert token_file.read_text() == fresh


def test_expired_token_triggers_refresh(token_file, lock_file, no_state_dir, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=-2))  # already expired
    fresh = _make_jwt(exp_offset_h=24)
    monkeypatch.setattr(at, "auto_refresh", lambda: fresh)
    monkeypatch.setattr(at, "verify_token", lambda t: True)

    at.main()

    assert token_file.read_text() == fresh


def test_transient_auto_refresh_failure_recovers_via_retry(token_file, lock_file, no_state_dir, monkeypatch):
    fresh = _make_jwt(exp_offset_h=24)
    attempts = []

    def flaky_refresh():
        attempts.append(1)
        if len(attempts) < 2:
            raise TimeoutError("network blip")
        return fresh

    monkeypatch.setattr(at, "auto_refresh", flaky_refresh)
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    monkeypatch.setattr(at, "RETRY_BACKOFF_BASE_S", 0)

    at.main()

    assert len(attempts) == 2
    assert token_file.read_text() == fresh


def test_total_refresh_failure_preserves_old_token_and_alerts(token_file, lock_file, no_state_dir, monkeypatch):
    old_valid = _make_jwt(iat_offset_h=-2, exp_offset_h=22)
    token_file.write_text(old_valid)

    monkeypatch.setattr(at, "auto_refresh", lambda: None)
    monkeypatch.setattr(at, "credential_login", lambda: None)
    monkeypatch.setattr(at, "verify_token", lambda t: t == old_valid)  # only the old token verifies
    monkeypatch.setattr(at, "RETRY_BACKOFF_BASE_S", 0)

    at.main()  # should NOT raise / NOT sys.exit since old token is still safe

    # fail-safe: existing valid credential must not be touched/corrupted
    assert token_file.read_text() == old_valid


def test_total_refresh_failure_with_no_safe_fallback_exits_nonzero_and_alerts(
    token_file, lock_file, no_state_dir, monkeypatch
):
    stale = _make_jwt(exp_offset_h=-5)
    token_file.write_text(stale)

    monkeypatch.setattr(at, "auto_refresh", lambda: None)
    monkeypatch.setattr(at, "credential_login", lambda: None)
    monkeypatch.setattr(at, "verify_token", lambda t: False)
    monkeypatch.setattr(at, "RETRY_BACKOFF_BASE_S", 0)

    alerts = []
    monkeypatch.setattr(at, "send_telegram", lambda msg, **kw: alerts.append(msg))

    with pytest.raises(SystemExit) as exc:
        at.main()

    assert exc.value.code == 1
    assert any("GAGAL" in m for m in alerts)
    # the stale token on disk must not be silently replaced with garbage
    assert token_file.read_text() == stale


def test_idempotent_repeated_execution_does_not_double_refresh(token_file, lock_file, no_state_dir, monkeypatch):
    """Scheduler-restart scenario: main() invoked twice back to back must not
    re-run the (expensive, rate-limited) browser refresh the second time."""
    fresh = _make_jwt(exp_offset_h=24)
    calls = []

    def refresh_once():
        calls.append(1)
        return fresh

    monkeypatch.setattr(at, "auto_refresh", refresh_once)
    monkeypatch.setattr(at, "verify_token", lambda t: True)

    at.main()
    at.main()

    assert len(calls) == 1, "second invocation should have skipped via should_skip_refresh"
    assert token_file.read_text() == fresh


def test_concurrent_invocation_finds_lock_held_and_exits_cleanly(token_file, lock_file, no_state_dir, monkeypatch):
    """Simulates a second cron/manual invocation firing while a refresh is
    already in flight -- must not double-launch a browser, must not error."""
    calls = []
    monkeypatch.setattr(at, "auto_refresh", lambda: calls.append(1) or _make_jwt())
    monkeypatch.setattr(at, "verify_token", lambda t: True)

    with at._refresh_lock(lock_path=lock_file):
        # a concurrent main() call should observe the lock is held
        at.main()  # must return quietly, not raise, not call auto_refresh

    assert calls == []


# ── failure-alert instructions (T1, incident 2026-10-21) ──
#
# Root cause: both failure alerts gave repair steps that could not work --
# `python3 auto_token.py --login` without the venv (system python has no
# playwright) or the cd, and `echo 'TOKEN' > ~/.stockbit_token` (wrong path,
# and echo creates mode 664 which startup validation rejects). The owner
# followed the 10-21 08:40 alert into a dead end while the token was expired.

def test_no_saved_session_alert_gives_working_instructions(tmp_path, monkeypatch):
    monkeypatch.setattr(at, "STATE_DIR", tmp_path / "no_such_state_dir")
    sent = []
    monkeypatch.setattr(at, "send_telegram", lambda msg, **kw: sent.append(msg))

    at.auto_refresh()  # STATE_DIR check happens before the playwright import

    assert len(sent) == 1
    msg = sent[0]
    assert "venv/bin/python3 auto_token.py --login" in msg
    assert f'cd "{at.BASE_DIR}"' in msg               # repo path from BASE_DIR, quoted
    assert str(tmp_path / "no_such_state_dir") in msg  # says WHICH folder is missing
    assert "~1 menit" in msg                          # warns capture is slow
    assert "~/.stockbit_token" not in msg


def test_final_failure_alert_gives_working_instructions(
    token_file, lock_file, no_state_dir, monkeypatch
):
    stale = _make_jwt(exp_offset_h=-5)  # expired -> readable status line
    token_file.write_text(stale)

    monkeypatch.setattr(at, "auto_refresh", lambda: None)
    monkeypatch.setattr(at, "credential_login", lambda: None)
    monkeypatch.setattr(at, "verify_token", lambda t: False)
    monkeypatch.setattr(at, "RETRY_BACKOFF_BASE_S", 0)

    alerts = []
    monkeypatch.setattr(at, "send_telegram", lambda msg, **kw: alerts.append(msg))

    with pytest.raises(SystemExit) as exc:
        at.main()
    assert exc.value.code == 1

    final = alerts[-1]
    assert "venv/bin/python3 auto_token.py --login" in final
    assert f'cd "{at.BASE_DIR}"' in final
    # manual paste path: repo file (never ~/.stockbit_token), mode 600
    assert f'install -m 600 /dev/stdin "{token_file}"' in final
    assert "menit" in final                        # minutes-left from the JWT decode
    assert "~/.stockbit_token" not in final
    assert "echo" not in final


# ── failure diagnosability (T2, incident 2026-10-21) ──
#
# The 08:40 "probably sent" alert and the 08:40:08 credential-fallback death
# ("Login redirect detected" then nothing) both left zero evidence. send
# outcomes are now logged; the redirect-but-no-token path records url/title,
# a timestamped screenshot, and the page's error/OTP text; --login says what
# it is doing during the ~20 s silent capture.

class TestSendTelegramOutcomeLogging:
    """Every real send logs 'sent ok' or 'HTTP <code>' — never the token or
    chat id."""

    @pytest.fixture(autouse=True)
    def _hermetic_gate(self, tmp_path, monkeypatch):
        import utils.notify_policy as np
        monkeypatch.setattr(np, "OFF_FILE", str(tmp_path / "TELEGRAM_OFF"))
        monkeypatch.setattr(np, "STATE_FILE", str(tmp_path / "notify_state.json"))
        monkeypatch.setattr(np, "DIGEST_DIR", str(tmp_path / "digest_buffer"))

    def _send(self, monkeypatch, resp):
        from types import SimpleNamespace  # noqa: F401  (used by callers)
        monkeypatch.setattr(at, "TELEGRAM_TOKEN", "tok123")
        monkeypatch.setattr(at, "TELEGRAM_CHAT_ID", "chat456")
        with patch("auto_token.requests.post", return_value=resp) as mock_post:
            ok = _real_send_telegram("outcome test", event="system.test_probe")
        assert mock_post.call_args  # the send really happened
        return ok

    def _log_text(self, tmp_path):
        # the autouse isolated_log_file fixture points at.LOG_FILE here
        return (tmp_path / "auto_token.log").read_text()

    def test_successful_send_logs_sent_ok(self, tmp_path, monkeypatch):
        from types import SimpleNamespace
        ok = self._send(monkeypatch, SimpleNamespace(ok=True, status_code=200))
        assert ok is True
        log = self._log_text(tmp_path)
        assert "[telegram] sent ok" in log
        assert "tok123" not in log and "chat456" not in log  # no creds in log

    def test_http_failure_logs_status_code(self, tmp_path, monkeypatch):
        from types import SimpleNamespace
        ok = self._send(monkeypatch, SimpleNamespace(ok=False, status_code=502))
        assert ok is False
        assert "HTTP 502" in self._log_text(tmp_path)


class _ScreenshotPage:
    def __init__(self):
        self.paths = []

    def screenshot(self, path):
        Path(path).write_bytes(b"png")
        self.paths.append(path)


def test_login_debug_screenshot_timestamped_mode_600_and_retention(tmp_path):
    for i in range(5):
        (tmp_path / f"login_debug_2020010{i + 1}_000000.png").write_bytes(b"old")

    at._save_login_debug_screenshot(_ScreenshotPage(), log_dir=tmp_path)

    shots = sorted(tmp_path.glob("login_debug_*.png"))
    assert len(shots) == at.LOGIN_DEBUG_KEEP           # keep the last 5
    new = [p for p in shots if p.read_bytes() == b"png"]
    assert len(new) == 1
    assert re.fullmatch(r"login_debug_\d{8}_\d{6}\.png", new[0].name)
    assert stat.S_IMODE(os.stat(new[0]).st_mode) == 0o600
    # the oldest was pruned, the 4 newest of the pre-existing were kept
    assert (tmp_path / "login_debug_20200101_000000.png") not in shots


def test_login_debug_screenshot_never_raises_on_page_error(tmp_path):
    class _Boom:
        def screenshot(self, path):
            raise RuntimeError("page closed")

    at._save_login_debug_screenshot(_Boom(), log_dir=tmp_path)  # must not raise


class _TextPage:
    """Fake page whose locator(text=...).count() is 1 for hit substrings."""

    def __init__(self, hits):
        self._hits = hits

    def locator(self, sel):
        hit = any(h in sel for h in self._hits)

        class _L:
            def count(self):
                return 1 if hit else 0

        return _L()


def test_error_texts_cover_base_and_device_verification_words():
    assert at._log_login_error_texts(_TextPage(["Invalid"])) == "Invalid"
    assert at._log_login_error_texts(
        _TextPage(["OTP"]), extra_texts=at.DEVICE_VERIFICATION_TEXTS) == "OTP"
    assert at._log_login_error_texts(_TextPage([])) is None


class _FakeLoginContext:
    def __init__(self, page):
        self.pages = [page]

    def close(self):
        pass


def _install_fake_playwright(monkeypatch, page):
    """Fake playwright.sync_api in sys.modules — no browser is ever launched."""
    import types

    class _Chromium:
        def launch_persistent_context(self, **kwargs):
            return _FakeLoginContext(page)

    class _PW:
        chromium = _Chromium()

    class _CM:
        def __enter__(self):
            return _PW()

        def __exit__(self, *a):
            return False

    sync_mod = types.ModuleType("playwright.sync_api")
    sync_mod.sync_playwright = lambda: _CM()
    pw_mod = types.ModuleType("playwright")
    pw_mod.sync_api = sync_mod
    monkeypatch.setitem(sys.modules, "playwright", pw_mod)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_mod)


def test_initial_login_ux_and_atomic_mode_600_write(tmp_path, monkeypatch, capsys, token_file):
    monkeypatch.setenv("DISPLAY", ":20")
    monkeypatch.setattr(at, "STATE_DIR", tmp_path / "state")
    _install_fake_playwright(monkeypatch, _FakePage())
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    jwt = _make_jwt(exp_offset_h=24)
    monkeypatch.setattr(at, "_capture_from_page", lambda page, navigate=True: jwt)
    monkeypatch.setattr(at, "verify_token", lambda t: True)

    at.initial_login()

    out = capsys.readouterr().out
    assert "ENTER DI TERMINAL INI" in out             # pre-ENTER instruction
    assert "Capturing token (up to 55 s)..." in out   # right after ENTER
    assert "Expire" in out and "24.0h" in out         # result with expiry
    assert token_file.read_text() == jwt
    assert stat.S_IMODE(os.stat(token_file).st_mode) == 0o600  # was 644 via write_text


# ── saved-login state dir moved out of the repo (T3, incident 2026-10-21) ──
#
# Root cause of the outage: .playwright_state/ lived in the repo root, so a
# cleanup deleted it as "a browser profile, recreated on next run". It is not
# recreated — it IS the saved login. New home: XDG state dir, outside any
# repo; the legacy dir is moved (never deleted) on the first run after the
# change, and a .MOVED pointer is left behind.

def test_state_dir_respects_xdg_state_home(monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", "/xdg/custom")
    assert at._resolve_state_dir() == Path(
        "/xdg/custom") / "idx-walkforward" / "playwright_state"


def test_state_dir_defaults_to_local_state(monkeypatch):
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    assert at._resolve_state_dir() == Path.home() / ".local" / "state" / \
        "idx-walkforward" / "playwright_state"


def test_migrate_moves_legacy_and_leaves_note(tmp_path):
    legacy = tmp_path / ".playwright_state"
    legacy.mkdir()
    (legacy / "Cookies").write_text("session")
    new = tmp_path / "xdg" / "idx-walkforward" / "playwright_state"

    status = at._migrate_legacy_state_dir(legacy_dir=legacy, new_dir=new)

    assert status == "migrated"
    assert not legacy.exists()                      # moved, not copied
    assert (new / "Cookies").read_text() == "session"
    assert stat.S_IMODE(os.stat(new).st_mode) == 0o700
    note = tmp_path / ".playwright_state.MOVED"
    assert note.is_file()
    assert str(new) in note.read_text()             # says where the login went


def test_migrate_both_exist_uses_new_and_never_deletes_legacy(tmp_path):
    legacy = tmp_path / ".playwright_state"
    legacy.mkdir()
    (legacy / "Cookies").write_text("old-login")
    new = tmp_path / "xdg" / "idx-walkforward" / "playwright_state"
    new.mkdir(parents=True)
    (new / "Cookies").write_text("new-login")

    status = at._migrate_legacy_state_dir(legacy_dir=legacy, new_dir=new)

    assert status == "both-exist"
    assert (legacy / "Cookies").read_text() == "old-login"   # untouched
    assert (new / "Cookies").read_text() == "new-login"
    assert not (tmp_path / ".playwright_state.MOVED").exists()


def test_migrate_no_legacy_is_a_noop(tmp_path):
    status = at._migrate_legacy_state_dir(
        legacy_dir=tmp_path / ".playwright_state",
        new_dir=tmp_path / "xdg" / "idx-walkforward" / "playwright_state")

    assert status == "no-legacy"
    assert not (tmp_path / "xdg").exists()          # nothing created


def test_migrate_rename_failure_falls_back_to_legacy(tmp_path, monkeypatch):
    legacy = tmp_path / ".playwright_state"
    legacy.mkdir()
    new = tmp_path / "xdg" / "idx-walkforward" / "playwright_state"
    monkeypatch.setattr(at, "STATE_DIR", new)

    def boom(*a):
        raise OSError(18, "cross-device link")

    monkeypatch.setattr(at.os, "rename", boom)

    status = at._migrate_legacy_state_dir(legacy_dir=legacy, new_dir=new)

    assert status == "rename-failed"
    assert at.STATE_DIR == legacy     # this run keeps using the legacy dir
    assert legacy.is_dir()            # never deleted on failure either
    assert not new.exists()


def test_main_runs_migration_before_any_mode(tmp_path, monkeypatch, token_file, lock_file):
    legacy = tmp_path / "legacy_state"     # matches the autouse fixture's path
    legacy.mkdir()
    (legacy / "Cookies").write_text("session")

    monkeypatch.setattr(at, "should_skip_refresh", lambda *a: True)

    at.main()

    assert (tmp_path / "state_dir" / "Cookies").read_text() == "session"


# ── pre-open light check (T4, 2026-10-21) ──
#
# The single 08:40 refresh attempt expired the token exactly AT the open —
# zero slack. The new 08:30 pre-open gate must alert (BLACKOUT_EXEMPT,
# data.token_expired) with the working manual fix while there is still time.

def test_preopen_check_ok_when_fresh_and_api_verified(token_file, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=10.0))
    monkeypatch.setattr(at, "verify_token", lambda t: True)

    assert at.preopen_check() is True


def test_preopen_check_alerts_when_expiring_within_3h(token_file, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=2.0))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    sends = []
    monkeypatch.setattr(at, "send_telegram",
                        lambda msg, **kw: sends.append((msg, kw)) or True)

    assert at.preopen_check() is True  # problem + alert delivered

    msg, kw = sends[0]
    assert kw["event"] == "data.token_expired"
    assert kw["subject"] == "preopen_check"
    assert "venv/bin/python3 auto_token.py --login" in msg
    assert "menit" in msg


def test_preopen_check_alerts_when_api_verify_fails(token_file, monkeypatch):
    """A server-side revocation keeps a valid exp claim (2026-09-21/22) — the
    live verify is what catches it."""
    token_file.write_text(_make_jwt(exp_offset_h=10.0))
    monkeypatch.setattr(at, "verify_token", lambda t: False)
    sends = []
    monkeypatch.setattr(at, "send_telegram",
                        lambda msg, **kw: sends.append((msg, kw)) or True)

    assert at.preopen_check() is True
    assert len(sends) == 1
    assert "revoked" in sends[0][0]


def test_preopen_check_alerts_when_token_file_missing(token_file, monkeypatch):
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    sends = []
    monkeypatch.setattr(at, "send_telegram",
                        lambda msg, **kw: sends.append((msg, kw)) or True)

    assert at.preopen_check() is True
    assert len(sends) == 1
    assert "tidak ada" in sends[0][0]


def test_preopen_check_false_only_when_alert_undeliverable(token_file, monkeypatch):
    """Exit-1 semantics: a detected problem whose alert could not be sent is
    the ONLY failure — cron_wrap's generic alert is then the fallback."""
    token_file.write_text(_make_jwt(exp_offset_h=2.0))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    monkeypatch.setattr(at, "send_telegram", lambda msg, **kw: False)

    assert at.preopen_check() is False


# ── JWT-shape validation at capture time (incident 2026-09-22) ──
#
# Root cause: `_capture_from_page`'s `on_request` listener accepted the FIRST
# `Authorization: Bearer <value>` header seen on any exodus.stockbit.com
# request, with no check that <value> is actually JWT-shaped. Stockbit's SPA
# fires an early request with the literal header `Authorization: Bearer
# undefined` before its client-side auth state hydrates -- guaranteed right
# after credential_login()'s `localStorage.clear()` -- so the listener locked
# onto "undefined" and the wait loop exited immediately instead of waiting for
# the real token moments later. verify_token() only checks HTTP status (not
# token shape), so "undefined" (9 bytes) was written straight to
# .stockbit_token, and every downstream consumer sent `Bearer undefined`.

class _FakeRequest:
    def __init__(self, url, auth_header):
        self.url = url
        self._headers = {"authorization": auth_header} if auth_header else {}

    @property
    def headers(self):
        return self._headers


class _FakePage:
    def __init__(self):
        self._handlers = {}

    def on(self, event, cb):
        self._handlers[event] = cb

    def remove_listener(self, event, cb):
        self._handlers.pop(event, None)

    def goto(self, *a, **k):
        pass

    def evaluate(self, *a, **k):
        pass

    def fire(self, request):
        self._handlers["request"](request)


class TestJwtShapeGuardAtCapture:
    def test_is_jwt_shaped_rejects_the_undefined_literal(self):
        assert at._is_jwt_shaped("undefined") is False

    def test_is_jwt_shaped_rejects_empty_and_malformed(self):
        assert at._is_jwt_shaped("") is False
        assert at._is_jwt_shaped("only.two") is False
        assert at._is_jwt_shaped("a..c") is False

    def test_is_jwt_shaped_accepts_a_real_looking_jwt(self):
        assert at._is_jwt_shaped(_make_jwt()) is True

    def test_capture_ignores_bearer_undefined_and_waits_for_real_token(self, monkeypatch):
        page = _FakePage()
        real_jwt = _make_jwt()
        events = iter([
            _FakeRequest("https://exodus.stockbit.com/keystats/BBCA", "Bearer undefined"),
            _FakeRequest("https://exodus.stockbit.com/keystats/BBCA", f"Bearer {real_jwt}"),
        ])

        def fake_sleep(_seconds):
            try:
                page.fire(next(events))
            except StopIteration:
                pass

        monkeypatch.setattr(at.time, "sleep", fake_sleep)

        result = at._capture_from_page(page, navigate=False)

        assert result == real_jwt


class TestSendTelegramRedaction:
    """RC1-C2 regression tests: auto_token.send_telegram now redacts secrets
    via the shared utils.logging_config.redact_secrets() — same rule already
    applied to utils.telegram.send_telegram / routes.telegram.send_telegram_reply
    (RC1 fix R-4). Calls _real_send_telegram directly to bypass the module's
    own `no_telegram` autouse mock (see top of file) and exercise the actual
    implementation.
    """

    @pytest.fixture(autouse=True)
    def _hermetic_gate(self, tmp_path, monkeypatch):
        """Hermetic vs the production box: logs/TELEGRAM_OFF really exists
        there (owner blackout 2026-10-05); gate state must not touch real
        files. These tests exercise the send path with the switch off."""
        import utils.notify_policy as np
        monkeypatch.setattr(np, "OFF_FILE", str(tmp_path / "TELEGRAM_OFF"))
        monkeypatch.setattr(np, "STATE_FILE", str(tmp_path / "notify_state.json"))
        monkeypatch.setattr(np, "DIGEST_DIR", str(tmp_path / "digest_buffer"))

    def _sent_text(self, monkeypatch, msg, secret_env=None):
        monkeypatch.setattr(at, "TELEGRAM_TOKEN", "tok123")
        monkeypatch.setattr(at, "TELEGRAM_CHAT_ID", "chat456")
        for k, v in (secret_env or {}).items():
            monkeypatch.setenv(k, v)
        with patch("auto_token.requests.post") as mock_post:
            _real_send_telegram(msg, event="system.test_probe")
        if not mock_post.call_args:
            return None
        return mock_post.call_args.kwargs["json"]["text"]

    def test_redacts_a_single_configured_secret(self, monkeypatch):
        text = self._sent_text(monkeypatch, "token leaked: supersecretzaikey",
                               {"ZAI_API_KEY": "supersecretzaikey"})
        assert "supersecretzaikey" not in text
        assert "[REDACTED]" in text

    def test_normal_message_is_unchanged(self, monkeypatch):
        text = self._sent_text(monkeypatch, "Token refreshed OK, 20h remaining",
                               {"ZAI_API_KEY": "supersecretzaikey"})
        assert text == "Token refreshed OK, 20h remaining"

    def test_html_formatting_and_newlines_preserved(self, monkeypatch):
        msg = "<b>Token Refresh FAILED</b>\nreason: supersecretzaikey"
        text = self._sent_text(monkeypatch, msg, {"ZAI_API_KEY": "supersecretzaikey"})
        assert "<b>Token Refresh FAILED</b>" in text
        assert "\nreason:" in text
        assert "supersecretzaikey" not in text

    def test_multiple_distinct_secrets_all_redacted(self, monkeypatch):
        text = self._sent_text(
            monkeypatch, "zaikeyvalueone and stockbitpassone both leaked",
            {"ZAI_API_KEY": "zaikeyvalueone", "STOCKBIT_PASS": "stockbitpassone"})
        assert "zaikeyvalueone" not in text and "stockbitpassone" not in text
        assert text.count("[REDACTED]") == 2

    def test_already_redacted_message_is_left_alone(self, monkeypatch):
        text = self._sent_text(monkeypatch, "value: [REDACTED] already masked",
                               {"ZAI_API_KEY": "supersecretzaikey"})
        assert text == "value: [REDACTED] already masked"

    def test_empty_message_does_not_crash(self, monkeypatch):
        text = self._sent_text(monkeypatch, "", {"ZAI_API_KEY": "supersecretzaikey"})
        assert text == ""

    def test_skips_send_when_telegram_not_configured(self, monkeypatch):
        monkeypatch.setattr(at, "TELEGRAM_TOKEN", None)
        monkeypatch.setattr(at, "TELEGRAM_CHAT_ID", None)
        with patch("auto_token.requests.post") as mock_post:
            _real_send_telegram("should not send")
        mock_post.assert_not_called()

    def test_existing_network_error_handling_preserved(self, monkeypatch):
        monkeypatch.setattr(at, "TELEGRAM_TOKEN", "tok123")
        monkeypatch.setattr(at, "TELEGRAM_CHAT_ID", "chat456")
        with patch("auto_token.requests.post", side_effect=Exception("network down")):
            _real_send_telegram("test message")   # must not raise
