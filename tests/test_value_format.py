import subprocess
import pathlib

FMT = pathlib.Path("static/format.js").resolve()


def _fmt(v):
    script = f"const m=require('{FMT}');process.stdout.write(m.fmtSigned({v}));"
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_trillion_tier():
    assert _fmt(-1.3548e12) == "-1.35T"


def test_billion_tier():
    assert _fmt(2.0e9) == "+2.0B"


def test_million_tier():
    assert _fmt(-3.4e6) == "-3.4M"


def test_null_dash():
    assert _fmt("null") == "—"
