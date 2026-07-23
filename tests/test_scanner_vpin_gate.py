"""Regression tests for the VPIN entry filter in scheduler.scanner (audit H-8).

H-8: `_vpin_conn = _db_connect(DB_PATH)` referenced an undefined name
(`_db_connect`), so `filter_vpin=1` made every ticker throw a NameError. The
except-path logged a warning without `continue`, so the ticker fell through
and passed the gate — the filter was a silent no-op no matter what VPIN said.

These tests drive scan_momentum_signals() through the VPIN block with the
surrounding filters (fundamental/sector/flow/liquidity) switched off, so
control reaches the VPIN block in isolation without needing full scan
fixtures. Most tests supply no OHLCV data for the test ticker, so a ticker
that gets past the VPIN block exits cleanly right after (df is None ->
continue) — that isolates the VPIN gate's own behavior, but on its own
can't distinguish "VPIN blocked the ticker" from "VPIN admitted it and it
was then excluded for an unrelated reason downstream" (both produce an
empty result). The two "downstream reached" tests below close that gap by
supplying a minimal >=25-row df and spying on calc_vol_ratio, the first
downstream call after the VPIN block — proof that the candidate actually
proceeded, not just an absence of evidence.

Coverage of the required behaviour matrix (P0.E1.S1.T2):
  1. VPIN enabled, DB available, PASS -> proceeds  : test_vpin_pass_lets_candidate_reach_downstream_processing
  2. VPIN enabled, DB available, FAIL -> blocked    : test_vpin_fail_blocks_candidate_before_downstream_processing
  3. VPIN enabled, DB unavailable -> blocked + alarm: test_vpin_fails_closed_and_alarms_on_db_unavailable
  4. VPIN enabled, eval exception -> blocked + alarm: test_vpin_fails_closed_and_alarms_on_calc_error
  5. VPIN disabled -> legacy behaviour preserved    : test_vpin_disabled_never_calls_calc_vpin_multi
  Cross-cutting: test_vpin_no_longer_raises_nameerror_on_db_unavailable (no silent pass),
  test_vpin_gate_is_deterministic_across_repeated_runs (determinism).
"""
import logging

import pandas as pd
import pytest

import engine.fail_open_alarm as fail_open_alarm_module
import scheduler.scanner as scanner


class _FakeConn:
    """Stand-in for a sqlite3.Connection: enough surface for the wf_map
    pre-query (execute(...).fetchall()) and the VPIN gate's close()."""

    def __init__(self):
        self.closed = False

    def execute(self, *_args, **_kwargs):
        return self

    def fetchall(self):
        return []

    def close(self):
        self.closed = True


def _base_config(**overrides):
    cfg = {
        "filter_fundamental": 0,
        "filter_sector": 0,
        "filter_flow": 0,
        "filter_rs": 0,
        "filter_regime": 0,
        "filter_vpin": 1,
        "filter_liquidity": 0,
        # "momentum" is disabled by default (scanner._DEFAULT_DISABLED) —
        # must be cleared or scan_momentum_signals() returns [] immediately.
        "disabled_strategies": "",
    }
    cfg.update(overrides)
    return cfg


@pytest.fixture
def wire_common_mocks(monkeypatch):
    """Wire every non-VPIN dependency scan_momentum_signals() needs to reach
    the per-ticker loop, without touching a real DB or network. Returns a
    setter for the VPIN-specific mocks (db_connect, calc_vpin_multi)."""

    monkeypatch.setattr("engine.calendar_filter.is_trading_day", lambda *a, **k: (True, ""))
    monkeypatch.setattr("engine.calendar_filter.is_blackout_day", lambda *a, **k: (False, ""))
    monkeypatch.setattr(scanner, "get_all_tickers", lambda: ["TESTVPIN"])
    monkeypatch.setattr(scanner, "_load_ohlcv_bulk", lambda: {})  # df stays None -> clean continue post-VPIN
    monkeypatch.setattr(scanner, "_get_sector_scores_cached", lambda: [])
    monkeypatch.setattr("engine.regime_filter.get_macro_overlay",
                         lambda *a, **k: {"idr_weakening": 0.0, "bi_rate": 6.25, "source": "test"})

    def _set(config=None, db_connect=None, calc_vpin_multi=None, ohlcv_map=None):
        monkeypatch.setattr("paper_trade.get_config", lambda: _base_config(**(config or {})))
        if db_connect is not None:
            monkeypatch.setattr(scanner, "db_connect", db_connect)
        if calc_vpin_multi is not None:
            monkeypatch.setattr("engine.vpin.calc_vpin_multi", calc_vpin_multi)
        if ohlcv_map is not None:
            monkeypatch.setattr(scanner, "_load_ohlcv_bulk", lambda: ohlcv_map)

    return _set


def _minimal_ohlcv_map(ticker="TESTVPIN"):
    """A >=25-row df — just enough to clear the `len(df) < 25` early-exit
    right after the VPIN block, so a spy on the next call (calc_vol_ratio)
    can prove downstream code was actually reached. Values are arbitrary —
    the spy raises before any of them would be read."""
    return {ticker: pd.DataFrame({"close": list(range(25)), "volume": [1000] * 25})}


def test_vpin_disabled_never_calls_calc_vpin_multi(wire_common_mocks, monkeypatch):
    """filter_vpin=0 — legacy off-switch behavior preserved."""
    called = []
    monkeypatch.setattr("engine.vpin.calc_vpin_multi", lambda *a, **k: called.append(1))
    wire_common_mocks(config={"filter_vpin": 0})

    result = scanner.scan_momentum_signals()

    assert called == []
    assert result == []


def test_vpin_no_longer_raises_nameerror_on_db_unavailable(wire_common_mocks):
    """Regression for H-8's root cause: the undefined `_db_connect` name is gone."""
    def _raise_db_unavailable(_path):
        raise OSError("unable to open database file")
    wire_common_mocks(db_connect=_raise_db_unavailable)

    # Must not raise NameError (or anything else) out of scan_momentum_signals.
    result = scanner.scan_momentum_signals()
    assert result == []


def test_vpin_fails_closed_and_alarms_on_db_unavailable(wire_common_mocks, monkeypatch, caplog):
    """Fail-closed (AN-5): DB unavailable -> ticker blocked, not passed."""
    alarm_calls = []
    monkeypatch.setattr(fail_open_alarm_module, "fail_closed_alarm",
                         lambda *a, **k: alarm_calls.append((a, k)))
    calc_calls = []
    monkeypatch.setattr("engine.vpin.calc_vpin_multi", lambda *a, **k: calc_calls.append(1))

    call_count = {"n": 0}

    def _db_connect(_path):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FakeConn()  # wf_map pre-query, before the ticker loop
        raise OSError("unable to open database file")

    wire_common_mocks(db_connect=_db_connect)

    with caplog.at_level(logging.WARNING):
        result = scanner.scan_momentum_signals()

    assert result == []  # ticker blocked, never reached signal assembly
    assert calc_calls == []  # never got past the failed connect
    assert len(alarm_calls) == 1
    args, kwargs = alarm_calls[0]
    assert args[0] == "vpin_gate"
    assert "TESTVPIN" in args[1]
    assert kwargs.get("notify") is False  # per-ticker: no Telegram spam (matches liquidity_gate convention)


def test_vpin_fails_closed_and_alarms_on_calc_error(wire_common_mocks, monkeypatch):
    """Fail-closed on any VPIN-block exception, not just a DB-connect failure —
    proves the fix isn't narrowly scoped to the one NameError call site. Also
    proves no resource leak: the connection opened before calc_vpin_multi blew
    up must still be closed by the try/finally around it."""
    alarm_calls = []
    monkeypatch.setattr(fail_open_alarm_module, "fail_closed_alarm",
                         lambda *a, **k: alarm_calls.append((a, k)))

    def _boom(*_a, **_k):
        raise RuntimeError("malformed vpin row")

    made_conns = []

    def _db_connect(_path):
        c = _FakeConn()
        made_conns.append(c)
        return c

    wire_common_mocks(db_connect=_db_connect, calc_vpin_multi=_boom)

    result = scanner.scan_momentum_signals()

    assert result == []
    assert len(alarm_calls) == 1
    assert "malformed vpin row" in alarm_calls[0][0][1]
    # made_conns[0] = wf_map pre-query, made_conns[1] = VPIN gate connection —
    # must be closed even though calc_vpin_multi raised (no leak on the error path).
    assert len(made_conns) == 2
    assert made_conns[1].closed is True


def test_vpin_passes_strong_buy_signal_and_closes_connection(wire_common_mocks, monkeypatch):
    """DB available, accepted signal — legacy pass-through behavior preserved,
    and the gate's own connection is closed (no leak on the success path)."""
    alarm_calls = []
    monkeypatch.setattr(fail_open_alarm_module, "fail_closed_alarm",
                         lambda *a, **k: alarm_calls.append((a, k)))

    made_conns = []

    def _db_connect(_path):
        c = _FakeConn()
        made_conns.append(c)
        return c

    wire_common_mocks(
        db_connect=_db_connect,
        calc_vpin_multi=lambda *a, **k: {"signal": "STRONG_BUY"},
    )

    scanner.scan_momentum_signals()

    assert alarm_calls == []
    # made_conns[0] = wf_map pre-query connection, made_conns[1] = VPIN gate connection
    assert len(made_conns) == 2
    assert made_conns[1].closed is True


def test_vpin_blocks_non_buy_signal_legacy_behavior_preserved(wire_common_mocks, monkeypatch):
    """DB available, rejected signal — the pre-existing (already-correct)
    block-on-non-BUY branch is untouched by this fix."""
    alarm_calls = []
    monkeypatch.setattr(fail_open_alarm_module, "fail_closed_alarm",
                         lambda *a, **k: alarm_calls.append((a, k)))

    wire_common_mocks(
        db_connect=lambda _path: _FakeConn(),
        calc_vpin_multi=lambda *a, **k: {"signal": "DISTRIBUTION"},
    )

    result = scanner.scan_momentum_signals()

    assert result == []
    assert alarm_calls == []  # a normal block is not a gate failure — no alarm


def test_vpin_pass_lets_candidate_reach_downstream_processing(wire_common_mocks, monkeypatch):
    """Row 1 of the required matrix: VPIN PASS must let the candidate proceed,
    not merely fail to alarm. An empty `signals` result alone can't prove that
    (a downstream-None df would produce the same empty result even if VPIN had
    blocked). Proof: supply a df that clears the next check (len>=25) and spy
    on calc_vol_ratio — the first call made after the VPIN block — to show
    execution actually reached it."""
    downstream_reached = []

    def _spy_calc_vol_ratio(*_a, **_k):
        downstream_reached.append(1)
        raise RuntimeError("test-marker: downstream reached (expected, caught by the per-ticker handler)")

    monkeypatch.setattr("engine.indicators.calc_vol_ratio", _spy_calc_vol_ratio)

    alarm_calls = []
    monkeypatch.setattr(fail_open_alarm_module, "fail_closed_alarm",
                         lambda *a, **k: alarm_calls.append((a, k)))

    wire_common_mocks(
        db_connect=lambda _path: _FakeConn(),
        calc_vpin_multi=lambda *a, **k: {"signal": "STRONG_BUY"},
        ohlcv_map=_minimal_ohlcv_map(),
    )

    scanner.scan_momentum_signals()  # the marker exception is swallowed by the per-ticker try/except

    assert downstream_reached == [1]  # candidate proceeded past the VPIN gate
    assert alarm_calls == []


def test_vpin_fail_blocks_candidate_before_downstream_processing(wire_common_mocks, monkeypatch):
    """Row 2 of the required matrix, strengthened: proves the block happens
    at the VPIN gate itself — downstream code (calc_vol_ratio) is never
    reached — using the same df that would otherwise let it through, so this
    isn't just "result was empty because df was None"."""
    downstream_reached = []
    monkeypatch.setattr("engine.indicators.calc_vol_ratio",
                         lambda *a, **k: downstream_reached.append(1))

    alarm_calls = []
    monkeypatch.setattr(fail_open_alarm_module, "fail_closed_alarm",
                         lambda *a, **k: alarm_calls.append((a, k)))

    wire_common_mocks(
        db_connect=lambda _path: _FakeConn(),
        calc_vpin_multi=lambda *a, **k: {"signal": "DISTRIBUTION"},
        ohlcv_map=_minimal_ohlcv_map(),
    )

    result = scanner.scan_momentum_signals()

    assert result == []
    assert downstream_reached == []  # never got past the VPIN gate
    assert alarm_calls == []  # a normal block is not a gate failure — no alarm


def test_vpin_gate_is_deterministic_across_repeated_runs(wire_common_mocks, monkeypatch):
    """Same inputs, same mocks, twice -> identical disposition and alarm
    count both times. No hidden state (caches, counters) leaks between runs."""
    alarm_calls = []
    monkeypatch.setattr(fail_open_alarm_module, "fail_closed_alarm",
                         lambda *a, **k: alarm_calls.append((a, k)))

    call_count = {"n": 0}

    def _db_connect(_path):
        call_count["n"] += 1
        if call_count["n"] % 2 == 1:
            return _FakeConn()  # wf_map pre-query, once per run
        raise OSError("unable to open database file")  # VPIN gate call, once per run

    wire_common_mocks(db_connect=_db_connect)

    result_1 = scanner.scan_momentum_signals()
    result_2 = scanner.scan_momentum_signals()

    assert result_1 == result_2 == []
    assert len(alarm_calls) == 2  # exactly one alarm per run, no accumulation/dedup surprise
    assert alarm_calls[0] == alarm_calls[1]
