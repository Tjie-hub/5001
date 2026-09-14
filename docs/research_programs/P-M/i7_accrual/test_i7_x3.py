#!/usr/bin/env python3
"""X3 gate tests (R5 remediation).

The v004 correction's central change -- the X3 session-level gate -- had zero
test coverage: `grep -c X3 test_i7_admissibility.py` returned 0. These tests
close that gap. They do NOT alter the semantics of any existing test;
`test_i7_admissibility.py` is untouched.

Structural tests (1-4, 7) run against in-memory fixtures, so they assert the
GATE's behaviour rather than one dataset's contents. Cohort tests (5-6) run
against the FROZEN v004 artifact read-only.

Run:  python3 test_i7_x3.py          (no-pytest fallback)
      python3 -m pytest test_i7_x3.py -q
"""
from __future__ import annotations

import ast
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import i7_admissibility as ADM          # noqa: E402
import build_v004_freeze as B           # noqa: E402

V004 = os.path.join(HERE, "store", "I7_V004_ADMISSIBLE_v1.sqlite")

# A Thursday inside the contemporaneous window -> structural grid 335.
SESSION = "2026-05-07"
GOOD_CAPTURE = f"{SESSION}T20:00:00"


def _fixture(cells):
    """In-memory production stand-in. `cells` = [(ticker, date, updated_at, n_bars)]."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, updated_at TEXT)")
    con.execute("CREATE TABLE stockbit_flow_bars (ticker TEXT, trade_date TEXT, bar_time TEXT)")
    for tk, d, ua, nb in cells:
        con.execute("INSERT INTO stockbit_flow VALUES (?,?,?)", (tk, d, ua))
        for i in range(nb or 0):
            con.execute("INSERT INTO stockbit_flow_bars VALUES (?,?,?)",
                        (tk, d, f"{i:04d}"))
    con.commit()
    return con


def _rules(rows):
    return {(r[0], r[1]): (r[6], r[7]) for r in rows}   # -> (admissible, rule)


# --- 1. is_admitted = 0 -> X3 ------------------------------------------------

def test_is_admitted_zero_session_is_x3():
    """A session the calendar evaluated and REJECTED is X3-excluded."""
    con = _fixture([("AAAA", SESSION, GOOD_CAPTURE, 335)])
    rows = B.collect(con, admitted=set())        # calendar rejected it
    adm, rule = _rules(rows)[("AAAA", SESSION)]
    assert adm == 0 and rule == "X3", (adm, rule)


# --- 2. absent from the effective calendar -> X3 -----------------------------

def test_absent_from_calendar_session_is_x3():
    """A session the calendar never covered is X3-excluded by the same gate.
    The gate is membership in the EFFECTIVE calendar (base + extension); it
    does not distinguish 'evaluated and rejected' from 'never evaluated'."""
    con = _fixture([("BBBB", SESSION, GOOD_CAPTURE, 335)])
    rows = B.collect(con, admitted={"2026-05-06"})   # some other session only
    adm, rule = _rules(rows)[("BBBB", SESSION)]
    assert adm == 0 and rule == "X3", (adm, rule)


# --- 3. X3 precedes ADM.admissible() -----------------------------------------

def test_x3_precedes_epit_predicates():
    """A cell that would fail an E-PIT rule AND sits in a non-admitted session
    is labelled X3 -- proving the session gate ran first. If E-PIT ran first
    the label would be E-PIT-3 (pre-cutoff) or E-PIT-4 (wrong grid)."""
    con = _fixture([
        ("CCCC", SESSION, f"{SESSION}T09:30:00", 335),   # would be E-PIT-3
        ("DDDD", SESSION, GOOD_CAPTURE, 7),              # would be E-PIT-4
    ])
    rows = B.collect(con, admitted=set())
    r = _rules(rows)
    assert r[("CCCC", SESSION)] == (0, "X3"), r[("CCCC", SESSION)]
    assert r[("DDDD", SESSION)] == (0, "X3"), r[("DDDD", SESSION)]
    # and the same cells ARE E-PIT-labelled once the session is admitted
    rows2 = B.collect(con, admitted={SESSION})
    r2 = _rules(rows2)
    assert r2[("CCCC", SESSION)] == (0, "E-PIT-3"), r2[("CCCC", SESSION)]
    assert r2[("DDDD", SESSION)] == (0, "E-PIT-4"), r2[("DDDD", SESSION)]


# --- 4. an X3 session cannot reach the admitted queue ------------------------

def test_x3_session_cannot_be_admitted():
    """Even a perfectly-formed cell is not admitted if its session fails X3."""
    con = _fixture([("EEEE", SESSION, GOOD_CAPTURE, 335)])
    assert _rules(B.collect(con, admitted={SESSION}))[("EEEE", SESSION)] == (1, None)
    assert _rules(B.collect(con, admitted=set()))[("EEEE", SESSION)] == (0, "X3")


# --- 5. 2026-07-09 is excluded in the frozen cohort --------------------------

def test_frozen_2026_07_09_is_x3_excluded():
    """The one session the readiness review identified. Every cell X3, none
    admitted, no bars carried into the freeze."""
    con = sqlite3.connect(f"file:{V004}?mode=ro", uri=True)
    tot, adm, x3 = con.execute(
        "SELECT COUNT(*), SUM(admissible), "
        "SUM(CASE WHEN exclusion_rule='X3' THEN 1 ELSE 0 END) "
        "FROM admissibility_ledger WHERE session_date='2026-07-09'").fetchone()
    bars = con.execute("SELECT COUNT(*) FROM flow_bars_v004 "
                       "WHERE trade_date='2026-07-09'").fetchone()[0]
    con.close()
    assert tot == 958 and adm == 0 and x3 == 958 and bars == 0, (tot, adm, x3, bars)


# --- 6. no minimum-cell rule: 2026-09-08 keeps its single unit ---------------

def test_frozen_2026_09_08_retains_single_admitted_cell():
    """A one-cell session is NOT dropped. No minimum-cell or minimum-session
    rule exists at the accrual layer; the estimator disposes of it."""
    con = sqlite3.connect(f"file:{V004}?mode=ro", uri=True)
    n = con.execute("SELECT COUNT(*) FROM admissibility_ledger "
                    "WHERE session_date='2026-09-08' AND admissible=1").fetchone()[0]
    con.close()
    assert n == 1, n


def test_no_minimum_cell_rule_in_source():
    """No cells-per-session threshold anywhere in the accrual code path."""
    src = open(os.path.join(HERE, "build_v004_freeze.py")).read()
    for bad in ("min_cells", "MIN_CELLS", "min_sessions", "MIN_SESSIONS"):
        assert bad not in src, bad


# --- 7. X5/X6 remain outside the accrual layer -------------------------------

def test_x5_x6_not_applied_at_accrual():
    """X5 (corporate action / RAJA / price floor / liquidity) and X6
    (t,t+1,t+2 consecutivity) are estimation-layer. Proven by AST: no
    executable SQL in the accrual builder touches ohlcv or corporate_actions,
    and no statement is dynamically constructed."""
    tree = ast.parse(open(os.path.join(HERE, "build_v004_freeze.py")).read())
    offenders = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr in ("execute", "executemany", "executescript"):
            for a in n.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    s = a.value.lower()
                    for tok in ("ohlcv", "corporate_action", "close",
                                "ret1", "fwd", "pnl"):
                        if tok in s:
                            offenders.append((n.lineno, tok))
                elif isinstance(a, (ast.JoinedStr, ast.BinOp)):
                    offenders.append((n.lineno, "DYNAMIC_SQL"))
    assert not offenders, offenders


def test_accrual_reads_only_provenance_and_bar_columns():
    """Whitelist the accrual builder's entire executable read surface."""
    tree = ast.parse(open(os.path.join(HERE, "build_v004_freeze.py")).read())
    tables = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            s = n.value.lower()
            for t in ("stockbit_flow_bars", "stockbit_flow", "ohlcv",
                      "corporate_actions", "paper_trades", "wf_edge"):
                if f"from {t}" in s:
                    tables.add(t)
    assert tables <= {"stockbit_flow_bars", "stockbit_flow"}, tables


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    bad = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as e:
            bad += 1
            print(f"  FAIL  {fn.__name__}  {e}")
    print(f"\n{len(fns)-bad}/{len(fns)} passed")
    raise SystemExit(1 if bad else 0)
