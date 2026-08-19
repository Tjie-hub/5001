"""Edge Registry admission-status API (Production Engine Phase 2 follow-on).

Thin controller over engine.registry_loader.get_registry() -- the same
cached, fail-soft read every production admission check (approved_universe,
registry_governance, admission_path) already goes through. Read-only: never
writes to the registry, never touches load_registry()'s cache directly.

Entry summaries expose only id/version/status/strategy_fn/regimes -- the
fields already on a loaded entry -- never the internal `universe` (a large
ticker set, not JSON-serializable), `requires`, or `manifest` path.
"""
from engine import registry_loader
from routes.v1 import api_v1_bp
from routes.v1.envelope import ok

_ENTRY_FIELDS = ("id", "version", "status", "strategy_fn", "regimes")


def _entry_summary(entry: dict) -> dict:
    return {k: entry[k] for k in _ENTRY_FIELDS}


@api_v1_bp.route("/registry/status", methods=["GET"])
def registry_status():
    """Edge Registry admission summary: approved/shadow counts + entries.

    T7 invariant #9 (production-admission auditability) already requires
    every admission decision to be traceable to get_registry()['hash']; this
    endpoint surfaces that same state for the Production Panel rather than
    computing a second, possibly-drifting view of it.
    """
    r = registry_loader.get_registry()
    entries = r["entries"]
    approved = sum(1 for e in entries if e["status"] == "APPROVED")
    shadow = sum(1 for e in entries if e["status"] == "SHADOW")
    return ok({
        "hash": r["hash"],
        "approved": approved,
        "shadow": shadow,
        "entries": [_entry_summary(e) for e in entries],
        "skipped_count": len(r["skipped"]),
        "debt_count": len(r["debt"]),
        "violation_count": len(r["violations"]),
    })
