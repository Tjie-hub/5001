"""AF-2 ADR-AF-003 — single-writer invariant. Source-scan enforcement, same pattern as
tests/test_architecture_boundary.py: a CI-enforced guarantee that `agent_size_hint` is written
in exactly one place in the entire codebase, not just tested against today's known call sites.

This is the automated guarantee behind ADR-AF-003's central claim: "there is exactly one write
to agent_size_hint per candidate, performed by one function... never a second write silently
clobbering a first." A future change that adds a second direct-write site would fail this test
immediately, rather than silently reintroducing the collision the ADR fixed.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Matches `r["agent_size_hint"] = ...` / `r['agent_size_hint'] = ...` (dict-key assignment via
# bracket notation) — the exact shape both of the old, now-removed direct-write sites used, and
# the shape the one remaining permitted site (engine.position_sizing's scanner-side call in
# resolve_agent_size_hints()) also uses. Deliberately does NOT match `.get("agent_size_hint")`
# (a read) or an attribute-style write (no such site exists or is expected).
ASSIGNMENT = re.compile(r"""\[["']agent_size_hint["']\]\s*=(?!=)""")

# Scopes consistent with test_architecture_boundary.py's own PRODUCTION_SCOPES/PRODUCTION_FILES —
# this invariant only governs production code, not test fixtures (which legitimately construct
# dicts containing an "agent_size_hint" key as literal test data via `key: value`, not `d[key] =`
# assignment, so they don't match this pattern anyway).
PRODUCTION_SCOPES = ["scheduler", "engine", "forward_testing", "data", "screener", "routes"]
PRODUCTION_FILES = ["monitor.py", "paper_trade.py", "app.py"]

# The one permitted assignment site — engine/position_sizing.py's own scanner-side call, per
# ADR-AF-003. Anything outside this exact location is a regression.
_PERMITTED_FILE = "scheduler/scanner.py"


def _py_files(scopes, files):
    for scope in scopes:
        yield from (ROOT / scope).rglob("*.py")
    for f in files:
        p = ROOT / f
        if p.exists():
            yield p


def test_agent_size_hint_has_exactly_one_writer():
    sites = []
    for p in _py_files(PRODUCTION_SCOPES, PRODUCTION_FILES):
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding="utf-8")
        for m in ASSIGNMENT.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            sites.append((rel, line_no))

    assert len(sites) == 1, (
        f"agent_size_hint must be written in exactly one place (ADR-AF-003) — "
        f"found {len(sites)}: {sites}"
    )
    assert sites[0][0] == _PERMITTED_FILE, (
        f"the sole agent_size_hint write must live in {_PERMITTED_FILE}, found in {sites[0][0]} "
        f"instead — either the permitted site moved (update this test) or a second writer "
        f"reappeared (a regression)"
    )


def test_run_edge_veto_stage_does_not_write_agent_size_hint():
    """Direct regression guard for the specific, historical first write site."""
    text = (ROOT / "scheduler" / "scanner.py").read_text(encoding="utf-8")
    # Isolate run_edge_veto_stage()'s own body (up to the next top-level `def `).
    start = text.index("def run_edge_veto_stage(")
    end = text.index("\ndef ", start + 1)
    body = text[start:end]
    assert not ASSIGNMENT.search(body), (
        "run_edge_veto_stage() must not write agent_size_hint directly (ADR-AF-003) — "
        "it may only attach edge_score as an input"
    )


def test_run_agent_firm_gate_does_not_write_agent_size_hint():
    """Direct regression guard for the specific, historical second write site."""
    text = (ROOT / "scheduler" / "scanner.py").read_text(encoding="utf-8")
    start = text.index("def run_agent_firm_gate(")
    end = text.index("\ndef ", start + 1)
    body = text[start:end]
    assert not ASSIGNMENT.search(body), (
        "run_agent_firm_gate() must not write agent_size_hint directly (ADR-AF-003) — "
        "it may only attach agent_size_tier as an input"
    )


def test_resolve_agent_size_hints_is_the_permitted_writer():
    text = (ROOT / "scheduler" / "scanner.py").read_text(encoding="utf-8")
    start = text.index("def resolve_agent_size_hints(")
    end = text.index("\ndef ", start + 1)
    body = text[start:end]
    assert ASSIGNMENT.search(body), (
        "resolve_agent_size_hints() must be the function that writes agent_size_hint"
    )
    assert "resolve_size_hint(" in body, (
        "resolve_agent_size_hints() must delegate to engine.position_sizing.resolve_size_hint() "
        "— the value must not be computed inline, bypassing the single authority"
    )
