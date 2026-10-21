"""Hermetic tests for scripts/stockbit_fin_backfill.py — no network.

Parser tests read the 2026-10-20 probe output (out/stockbit_fin_probe_20261020_183349/,
gitignored) and skip if it is absent; the probe doc pins what those files contain.
Behavioural tests (resume, time-window refusal, 401 stop) run against a tmp OUT_DIR
and a stubbed requests module, so they never touch the token or the network.
"""
import argparse
import base64
import importlib.util
import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "out" / "stockbit_fin_probe_20261020_183349"

_spec = importlib.util.spec_from_file_location(
    "stockbit_fin_backfill", REPO / "scripts" / "stockbit_fin_backfill.py")
sfb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sfb)

requires_probe = pytest.mark.skipif(
    not PROBE.exists(), reason=f"probe output not present: {PROBE}")


def load_report(name: str) -> str:
    j = json.loads((PROBE / name).read_text(encoding="utf-8"))
    return (j.get("data") or {}).get("html_report") or ""


def fetch_args(**kw) -> argparse.Namespace:
    base = dict(tickers=None, limit=0, max_minutes=170, force=False, dry_run=False)
    base.update(kw)
    return argparse.Namespace(**base)


# ---------------------------------------------------------------- to_number

@pytest.mark.parametrize("raw,expect_val,expect_unit", [
    ("4303879000000.000000", 4.303879e12, None),      # data-raw IDR, full precision
    ("-223831000000.000000", -2.23831e11, None),      # data-raw negative, signed
    ("18,637.07 B", 1.863707e13, None),               # shown-text suffix form
    ("0.93%", 0.93, "%"),                             # shown-text percent
    ("(1,234)", -1234.0, None),                       # accounting parentheses
    ("(1,234.5 B)", -1.2345e12, None),
    ("(0.93%)", -0.93, "%"),
    ("-", None, None),                                # empty cell
    ("n/a", None, None),
    ("N/A", None, None),
    ("", None, None),
    (None, None, None),
])
def test_to_number(raw, expect_val, expect_unit):
    val, unit = sfb.to_number(raw)
    assert val == pytest.approx(expect_val) if expect_val is not None else val is None
    assert unit == expect_unit


# ---------------------------------------------------------------- parser on probe files

EXPECTED_BOUNDS = {  # from the probe doc table (10_STOCKBIT_FIN_HISTORY_PROBE)
    "BBCA__fin_income_q.json": ((2008, 1), (2026, 2), 74),
    "TLKM__fin_income_q.json": ((2007, 4), (2026, 2), 75),
    "BTEL__fin_income_q.json": ((2007, 4), (2025, 3), 72),   # delisted
    "TRAM__fin_income_q.json": ((2008, 1), (2019, 3), 47),   # delisted
}


@requires_probe
@pytest.mark.parametrize("name", sorted(EXPECTED_BOUNDS))
def test_parse_period_columns(name):
    rows = sfb.parse_report(load_report(name))
    yq = sorted({(r["year"], r["quarter"]) for r in rows if r["year"]})
    lo, hi, n = EXPECTED_BOUNDS[name]
    assert (yq[0], yq[-1], len(yq)) == (lo, hi, n)
    # quarter -> calendar period end (Q1 2008 is present in all four files)
    pe = {r["period"]: r["period_end"] for r in rows}
    assert pe["Q1 2008"] == "2008-03-31"


@requires_probe
def test_parse_bbc_bank_layout_indonesian_rows_idr():
    rows = sfb.parse_report(load_report("BBCA__fin_income_q.json"))
    stmt = [r for r in rows if r["section"] == "statement"]
    en = {r["account_en"] for r in stmt}
    idn = {r["account_id"] for r in stmt}
    assert "Total Revenue" in en and "Total Pendapatan" in idn   # data-lang-1 / data-lang-0
    assert "Interest Income" in en                              # bank layout row BBCA has
    tot = next(r for r in stmt if r["account_en"] == "Total Revenue"
               and r["period"] == "Q1 2008")
    assert tot["value"] == pytest.approx(4_303_879_000_000.0)   # IDR from data-raw
    # hierarchy carried for the nested-set left/right values
    assert tot["row_left"] == 1 and tot["row_right"] > 1 and tot["is_head"] == 1


@requires_probe
def test_parse_tlk_non_bank_layout():
    rows = sfb.parse_report(load_report("TLKM__fin_income_q.json"))
    stmt = [r for r in rows if r["section"] == "statement"]
    en = {r["account_en"] for r in stmt}
    assert "Total Revenue" in en                 # common top line
    assert "Interest Income" not in en           # the bank-specific BBCA row is absent
    pe = {r["period"]: r["period_end"] for r in rows}
    assert pe["Q4 2007"] == "2007-12-31"
    tot = next(r for r in stmt if r["account_en"] == "Total Revenue"
               and r["period"] == "Q4 2007")
    assert tot["value"] == pytest.approx(62_494_615_000_000.0)


@requires_probe
def test_parse_delisted_names_keep_history():
    """BTEL and TRAM are delisted; their statements must still parse with full history."""
    btel = sfb.parse_report(load_report("BTEL__fin_income_q.json"))
    neg = [r for r in btel if r["section"] == "statement" and r["value"] is not None
           and r["value"] < 0]
    assert neg, "BTEL income statement must carry negative values (COGS)"
    cogs = next(r for r in neg if r["account_en"] == "Total Cost Of Goods Sold"
                and r["period"] == "Q4 2007")
    assert cogs["value"] == pytest.approx(-382_143_230_938.0)
    tram = sfb.parse_report(load_report("TRAM__fin_income_q.json"))
    assert any(r["value"] is not None and r["value"] < 0 for r in tram)


@requires_probe
def test_parse_empty_and_na_cells():
    rows = sfb.parse_report(load_report("BBCA__fin_income_q.json"))
    # '-' cells (data-raw '-') parse to None, never 0.0
    dash = [r for r in rows if r["value_raw"] == "-"]
    assert dash and all(r["value"] is None for r in dash)
    # shown 'n/a' with data-raw '0.000000' must be None, not zero: BBCA's EBITDA
    # row displays n/a in its early quarters (verified against the probe file)
    ebitda_q108 = next(r for r in rows if r["account_en"] == "EBITDA (Quarter)"
                       and r["period"] == "Q1 2008")
    assert ebitda_q108["value"] is None and ebitda_q108["value_raw"] == "0.000000"


@requires_probe
def test_parse_derived_section_split():
    rows = sfb.parse_report(load_report("BBCA__fin_income_q.json"))
    derived = {r["account_en"] for r in rows if r["section"] == "derived"}
    assert {"EPS (Quarter)", "PE Ratio (Quarter)", "Share Outstanding"} <= derived
    assert "Total Revenue" not in derived


# ---------------------------------------------------------------- resumability

def test_done_set_files_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(sfb, "OUT_DIR", tmp_path)
    raw = tmp_path / "raw" / "AAAA"
    raw.mkdir(parents=True)
    (raw / "income.json.gz").write_bytes(b"x")
    man = tmp_path / "manifest.jsonl"
    man.write_text(json.dumps({"ticker": "BBBB", "statement": "cashflow", "status": 404})
                   + "\n" + json.dumps({"ticker": "CCCC", "statement": "balance", "status": "empty"})
                   + "\n" + json.dumps({"ticker": "DDDD", "statement": "income", "status": 200})
                   + "\n", encoding="utf-8")
    done = sfb.done_set()
    assert ("AAAA", "income") in done           # saved file on disk
    assert ("BBBB", "cashflow") in done         # recorded 404
    assert ("CCCC", "balance") in done          # recorded empty
    assert ("DDDD", "income") not in done       # 200 without a file: refetch


def test_fetch_dry_run_skips_done(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sfb, "OUT_DIR", tmp_path)
    raw = tmp_path / "raw" / "AAAA"
    raw.mkdir(parents=True)
    (raw / "income.json.gz").write_bytes(b"x")
    rc = sfb.fetch(fetch_args(tickers=["AAAA", "BBBB"], dry_run=True))
    out = capsys.readouterr().out
    assert rc == 0
    assert "universe 2 tickers; 6 requests total, 1 already done, 5 to go" in out


# ---------------------------------------------------------------- time-window refusal

WIB = sfb.WIB


def at(day: str, hh: int, mm: int) -> datetime:
    return datetime.fromisoformat(f"{day}T{hh:02d}:{mm:02d}:00").replace(tzinfo=WIB)


def test_blocked():
    # weekday market/EOD window 08:30–19:00
    assert sfb.blocked(at("2026-10-19", 8, 29)) is None     # Monday, before
    assert sfb.blocked(at("2026-10-19", 8, 30)) is not None # Monday, first blocked minute
    assert sfb.blocked(at("2026-10-23", 12, 0)) is not None # Friday midday
    assert sfb.blocked(at("2026-10-23", 18, 59)) is not None
    assert sfb.blocked(at("2026-10-23", 19, 0)) is None     # Friday, window over
    # nightly window 21:50–23:30, every day (jurnal26 tape backfill)
    assert sfb.blocked(at("2026-10-23", 21, 49)) is None
    assert sfb.blocked(at("2026-10-23", 21, 50)) is not None
    assert sfb.blocked(at("2026-10-24", 22, 0)) is not None  # Saturday too
    assert sfb.blocked(at("2026-10-24", 23, 30)) is None
    # weekends have no market window
    assert sfb.blocked(at("2026-10-25", 12, 0)) is None      # Sunday noon: the good window


def test_fetch_refuses_in_window_before_token(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sfb, "OUT_DIR", tmp_path)
    monkeypatch.setattr(sfb, "blocked", lambda now: "weekday 08:30-19:00 WIB (test)")

    def no_token():
        raise AssertionError("token read during a refused run")
    monkeypatch.setattr(sfb, "read_token", no_token)
    rc = sfb.fetch(fetch_args(tickers=["AAAA"]))
    assert rc == 2
    assert "REFUSED" in capsys.readouterr().out


# ---------------------------------------------------------------- 401 stops the run

def _fake_token(minutes_valid: int = 60) -> str:
    exp = int(datetime.now(timezone.utc).timestamp()) + minutes_valid * 60
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode()
    return f"h.{payload}.s"


def test_fetch_401_stops_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sfb, "OUT_DIR", tmp_path)
    monkeypatch.setattr(sfb, "blocked", lambda now: None)
    monkeypatch.setattr(sfb, "read_token", lambda: _fake_token())

    class Resp:
        status_code = 401
    calls = []

    class Session:
        def get(self, url, headers=None, timeout=None):
            calls.append(url)
            return Resp()
    fake_requests = types.SimpleNamespace(
        Session=Session, RequestException=Exception)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    rc = sfb.fetch(fetch_args(tickers=["AAAA", "BBBB"], max_minutes=5))
    out = capsys.readouterr().out
    assert rc == 2
    assert "STOP: 401" in out
    assert len(calls) == 1, "the run must stop at once after the first 401"
    assert not list((tmp_path / "raw").rglob("*.json.gz")), "no raw file may be written"
    man = tmp_path / "manifest.jsonl"
    assert not man.exists() or man.read_text(encoding="utf-8").strip() == ""


def test_fetch_token_expiry_refusal(tmp_path, monkeypatch, capsys):
    """A token with <10 min left is refused before any GET."""
    monkeypatch.setattr(sfb, "OUT_DIR", tmp_path)
    monkeypatch.setattr(sfb, "blocked", lambda now: None)
    monkeypatch.setattr(sfb, "read_token", lambda: _fake_token(minutes_valid=5))
    got = []

    class Session:
        def get(self, *a, **kw):
            got.append(1)
            raise AssertionError("no GET may happen")
    monkeypatch.setitem(sys.modules, "requests",
                        types.SimpleNamespace(Session=Session, RequestException=Exception))
    rc = sfb.fetch(fetch_args(tickers=["AAAA"]))
    assert rc == 2
    assert "token expires" in capsys.readouterr().out
    assert not got
