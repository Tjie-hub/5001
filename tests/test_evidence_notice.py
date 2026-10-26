"""The "Unvalidated — no tested edge" notice (production signal audit 2026-10-26 §4.3) must stay on every page that
shows strategy or watchlist signals: workspace Signals + Scanner panels, dashboard Unified Watchlist. Renders the real
templates through Jinja with stub globals, so the check needs no app runtime or DB."""
import os

import jinja2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(ROOT, "templates")
MARKER = 'data-evidence="unvalidated"'


def _render(name):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES))
    env.globals.update(url_for=lambda *a, **k: "/", request=None, config={}, get_flashed_messages=lambda **k: [])
    return env.get_template(name).render()


def test_partial_names_the_evidence_status():
    html = _render("_evidence_notice.html")
    assert MARKER in html
    assert "Unvalidated" in html and "D-070" in html and "D-066" in html


def test_workspace_signals_and_scanner_panels_carry_the_notice():
    html = _render("workspace.html")
    assert html.count(MARKER) == 2
    sig = html.index('id="panel-signals"')
    scan = html.index('id="panel-scanner"')
    nxt = html.index('id="panel-backtest"')
    assert sig < html.index(MARKER, sig) < scan          # one inside the Signals panel
    assert scan < html.index(MARKER, scan) < nxt          # one inside the Scanner panel


def test_dashboard_unified_watchlist_carries_the_notice():
    html = _render("dashboard.html")
    assert html.count(MARKER) == 1
    assert html.index("Unified Watchlist") < html.index(MARKER) < html.index('id="unifiedWatch"')
