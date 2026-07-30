"""P0.E2.S3.T2 -- delete dead stockbit_fetcher._parse_args (L-3).

Audit L-3: `_parse_args` was dead (zero call sites anywhere in the repo,
confirmed by repo-wide grep before deletion) and buggy (self-referential
list comprehension re-indexing `args` while reassigning it); `main()`
already re-implements `--token`/`--cat` parsing correctly inline and is
the only path actually used -- `_parse_args` was pure unreachable dead
weight. This module guards against reintroduction of the dead function
and exercises `main()`'s own parsing, the sole surviving live path, to
confirm its runtime behavior (which this task must preserve identically)
is what it appears to be.
"""
import sys

import pytest

import stockbit_fetcher


def test_parse_args_function_no_longer_exists():
    """Regression guard: _parse_args was deleted as dead code (L-3); a
    reintroduction (e.g. via a bad merge) should fail this test."""
    assert not hasattr(stockbit_fetcher, "_parse_args")


def test_main_parses_token_flag(monkeypatch):
    """main()'s own --token parsing (the surviving, correct
    implementation) extracts the token value and passes it through to
    ensure_valid_token -- exercised up to (not past) the point where a
    None token cleanly sys.exit(1)s, before any DB/network side effects."""
    monkeypatch.setattr(sys, "argv", ["stockbit_fetcher.py", "--token", "ABC123", "BBCA"])
    captured = {}

    def _fake_ensure_valid_token(manual_token=None):
        captured["manual_token"] = manual_token
        return None

    monkeypatch.setattr(stockbit_fetcher, "ensure_valid_token", _fake_ensure_valid_token)
    monkeypatch.setattr(stockbit_fetcher, "log", lambda *a, **k: None)

    with pytest.raises(SystemExit) as exc_info:
        stockbit_fetcher.main()

    assert exc_info.value.code == 1
    assert captured["manual_token"] == "ABC123"


def test_main_parses_cat_flag(monkeypatch):
    """main()'s own --cat parsing extracts and uppercases the category,
    and does not leak the flag or its value into the ticker/category
    resolution -- the exact class of bug _parse_args had (self-referential
    indexing while filtering) but main()'s simpler slice-based removal
    (`args[:i] + args[i+2:]`) does not."""
    monkeypatch.setattr(sys, "argv", ["stockbit_fetcher.py", "--cat", "idx30"])
    captured = {}

    def _fake_get_tickers(category=None):
        captured["category"] = category
        return []

    def _fake_ensure_valid_token(manual_token=None):
        return None

    monkeypatch.setattr(stockbit_fetcher, "get_tickers", _fake_get_tickers)
    monkeypatch.setattr(stockbit_fetcher, "ensure_valid_token", _fake_ensure_valid_token)
    monkeypatch.setattr(stockbit_fetcher, "log", lambda *a, **k: None)

    with pytest.raises(SystemExit) as exc_info:
        stockbit_fetcher.main()

    assert exc_info.value.code == 1
    assert captured["category"] == "IDX30"


def test_main_explicit_tickers_override_category(monkeypatch):
    """Positional ticker args (no --cat) bypass get_tickers()/category
    resolution entirely -- main()'s own documented behavior
    ('Explicit tickers override category'), unrelated to and unaffected
    by the _parse_args deletion, exercised here as a control."""
    monkeypatch.setattr(sys, "argv", ["stockbit_fetcher.py", "bbca", "tlkm"])
    called = {"get_tickers": False}

    def _fake_get_tickers(category=None):
        called["get_tickers"] = True
        return []

    def _fake_ensure_valid_token(manual_token=None):
        return None

    monkeypatch.setattr(stockbit_fetcher, "get_tickers", _fake_get_tickers)
    monkeypatch.setattr(stockbit_fetcher, "ensure_valid_token", _fake_ensure_valid_token)
    monkeypatch.setattr(stockbit_fetcher, "log", lambda *a, **k: None)

    with pytest.raises(SystemExit):
        stockbit_fetcher.main()

    assert called["get_tickers"] is False
