"""PIT and synthetic tests for the daily OIB G0 (hermetic)."""
import ast
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import oib as OI  # noqa: E402


def _imports(p):
    out = set()
    for n in ast.walk(ast.parse(Path(p).read_text())):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
    return out


def test_no_outcome_import():
    for f in ("oib.py", "g0_census.py", "extract_daily.py"):
        assert "outcomes" not in _imports(HERE / f)


def test_oib_uses_final_cumulative_totals_and_bar_floor():
    d1, d2 = date(2025, 4, 8), date(2025, 4, 9)
    daily = {("A", d1): (300.0, 100.0, 335), ("A", d2): (1e9, 0.0, 335), ("B", d1): (300.0, 100.0, 50)}
    assert OI.oib_of(daily, "A", [d1]) == 0.5           # a later day never leaks in
    assert OI.oib_of(daily, "B", [d1]) is None          # under MIN_BARS: not captured
    assert abs(OI.oib_of(daily, "A", [d1, d2]) - (1e9 + 200) / (1e9 + 400)) < 1e-12


def test_quintile_ties_and_size():
    rows = [{"t": f"T{i:02d}", "oib": i / 10} for i in range(10)]
    q1, q5, n = OI.quintiles(rows)
    assert (q1, q5, n) == (["T00", "T01"], ["T08", "T09"], 10)


def test_frozen_constants():
    assert OI.N_FROZEN == 612 and OI.BAR_FROZEN == 3.2991
    assert OI.STOP_EFFECT_DAILY == 0.0010 and OI.STOP_POWER_MIN == 0.20 and OI.MIN_BARS == 200
