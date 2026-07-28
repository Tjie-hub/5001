"""Guard tests: every registered route must be explicitly classified.

An unclassified route is a CI failure — and at request time the middleware
treats it as admin-only (fail closed), so forgetting to classify a new route
can never silently expose it.
"""
import importlib


def _app():
    import app as app_module
    importlib.reload(app_module)
    return app_module.app


def test_every_route_classified():
    from security.route_policy import POLICY
    app = _app()
    rules = {r.rule for r in app.url_map.iter_rules()}
    unclassified = rules - set(POLICY)
    assert not unclassified, f"routes missing from security policy: {sorted(unclassified)}"


def test_no_stale_policy_entries():
    from security.route_policy import POLICY
    app = _app()
    rules = {r.rule for r in app.url_map.iter_rules()}
    stale = set(POLICY) - rules
    assert not stale, f"policy entries for routes that no longer exist: {sorted(stale)}"


def test_policy_values_valid():
    from security.route_policy import POLICY, required_level
    from security.auth import PUBLIC, VIEWER, OPERATOR, ADMIN
    valid = {PUBLIC, VIEWER, OPERATOR, ADMIN}
    for rule, spec in POLICY.items():
        levels = spec.values() if isinstance(spec, dict) else [spec]
        for lv in levels:
            assert lv in valid, f"{rule}: bad level {lv!r}"
    assert required_level("/api/paper/config", "GET") == VIEWER
    assert required_level("/api/paper/config", "POST") == ADMIN
    assert required_level("/does/not/exist", "GET") == ADMIN  # fail closed
