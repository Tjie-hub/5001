"""PIT tests for the online-retail broker imbalance G0 (hermetic)."""
import ast
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import flow as FL  # noqa: E402


def _imports(p):
    out = set()
    for n in ast.walk(ast.parse(Path(p).read_text())):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
    return out


def test_no_outcome_import():
    for f in ("flow.py", "g0_census.py"):
        assert "outcomes" not in _imports(HERE / f)


def test_signal_uses_only_given_days_and_r_group():
    d1, d2, d3, d4 = (date(2025, 4, 8 + i) for i in range(4))
    daily = {("AAAA", d): {"r": 10.0, "f": -5.0, "gross": 100.0, "rb": {"XL"}} for d in (d1, d2, d3)}
    daily[("AAAA", d4)] = {"r": 1e9, "f": 0.0, "gross": 1e9, "rb": {"XL"}}  # a later day must not leak
    s = FL.signal(daily, "AAAA", [d1, d2, d3])
    assert abs(s["ri"] - 0.1) < 1e-12 and abs(s["fi"] + 0.05) < 1e-12
    assert FL.signal(daily, "AAAA", [d1]) is not None            # short week: min(3, len) sessions
    assert FL.signal({}, "AAAA", [d1, d2, d3]) is None


def test_weeks_and_formation_window_excluded():
    ss = [date(2025, 3, 27), date(2025, 3, 28), date(2025, 3, 31), date(2025, 4, 8), date(2025, 4, 9),
          date(2025, 4, 14)]
    w = FL.weeks(ss)
    assert [x[-1] for x in w] == [date(2025, 3, 28), date(2025, 3, 31), date(2025, 4, 9), date(2025, 4, 14)]

    class P:
        sessions = ss
    assert all(x[0] >= FL.TEST_START for x in FL.formation_weeks(P))


def test_frozen_constants():
    assert FL.R_GROUP == ("XL", "XC", "YP", "PD", "KK")
    assert FL.N_FROZEN == 612 and FL.BAR_FROZEN == 3.2991
    assert FL.STOP_EFFECT_WEEKLY == 0.0030 and FL.STOP_POWER_MIN == 0.20
