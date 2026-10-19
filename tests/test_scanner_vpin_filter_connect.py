"""2026-10-19 audit (pyflakes): the momentum scan's VPIN filter called `_db_connect`, a name removed by the Phase 3C
refactor (2c58bbf). With filter_vpin=1 every ticker raised NameError, the except logged a warning and the ticker
passed: the filter would have been silently off. It is 0 by default, so it never fired."""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "scheduler" / "scanner.py"


def test_scanner_calls_only_defined_connection_helpers():
    tree = ast.parse(SRC.read_text())
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "_db_connect" not in called
