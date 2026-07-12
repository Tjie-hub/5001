"""Edge Registry loader — the production side of the research→production contract.

Spec: docs/superpowers/specs/2026-07-07-research-production-separation-design.md §6.
Production reads the registry ONCE (cached), validates schema + compatibility, and
exposes approved_universe() to the selector. Incompatible/invalid entries are skipped
with a visible alarm; loader failure degrades to None (selector falls back to legacy
behavior) — never crashes the engine.
"""
import hashlib
import json
import logging
import os
import subprocess

import yaml

from engine.fail_open_alarm import fail_open_alarm

logger = logging.getLogger(__name__)

ENGINE_VERSIONS = {'data_schema': 1, 'exit_kernel': 1,
                   'regime_model': 1, 'engine_version': 1}

REGISTRY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'registry', 'edge_registry.yaml')

_REQUIRED = ('id', 'version', 'status', 'strategy_fn', 'regimes',
             'universe_artifact', 'requires', 'changelog')
_LOADABLE = ('APPROVED', 'SHADOW')
_LIFECYCLE = ('CANDIDATE', 'SUSPENDED', 'RETIRED', 'SUPERSEDED')

# Forward-test bar for APPROVED. Mirrors research.studies.phase5_tracker.RULE;
# engine/ must not import research/, so it is pinned here and asserted equal by
# tests/test_registry_lifecycle.py::test_forward_bar_matches_phase5_rule.
_FORWARD_BAR = {'min_n': 15, 'go_exp': 0.50}

# Shrink-only lifecycle debt (like tests/test_research_data_fence._ROUTES_WRITE_DEBT).
# Pre-existing APPROVED/SHADOW entries that predate R-10 enforcement. NEW violations are
# NOT added here — they fail CI. Entries are removed as they remediate, never added.
_LIFECYCLE_DEBT = {
    ("NR7_BULL", 1): {
        "reason": "APPROVED 2026-07-04 under the pre-Phase-C generalization bar; "
                  "Phase C gate=REJECT and shadow N=0. Governs on legacy grounds.",
        "remediation": "Phase 5 forward test (phase5_tracker); deadline 2027-01-08.",
        "deadline": "2027-01-08",
    },
}

_cache = None


def validate_evidence(entry, manifest, bar):
    """Return a list of reasons a SHADOW/APPROVED entry fails its evidence receipt.

    Pure. Empty list == compliant (or a non-loadable status that needs no receipt).
    SHADOW needs a Phase C PROMOTE gate_decision; APPROVED also needs a Phase 5
    forward GO clearing `bar`."""
    status = entry.get('status')
    if status not in ('SHADOW', 'APPROVED'):
        return []
    ev = (manifest or {}).get('evidence') or {}
    reasons = []
    gd = ev.get('gate_decision') or {}
    if gd.get('final_state') != 'PROMOTE_TO_FORWARD_TEST':
        reasons.append('no PROMOTE gate_decision')
    if status == 'APPROVED':
        fw = ev.get('forward') or {}
        if fw.get('verdict') != 'GO':
            reasons.append('forward verdict != GO')
        elif fw.get('n', 0) < bar['min_n'] or fw.get('exp_pct', -1.0) < bar['go_exp']:
            reasons.append(
                f"forward below bar (n={fw.get('n')}, exp={fw.get('exp_pct')})")
    return reasons


def _registry_hash(path):
    try:
        out = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                             cwd=os.path.dirname(path), capture_output=True,
                             text=True, timeout=5)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def load_registry(path=None, engine_versions=None):
    path = path or REGISTRY_PATH
    versions = engine_versions or ENGINE_VERSIONS
    with open(path, 'r') as f:
        raw = yaml.safe_load(f) or []
    entries, skipped = [], []
    violations, debt = [], []
    for e in raw:
        ident = f"{e.get('id', '?')}_v{e.get('version', '?')}"
        status = e.get('status')
        if status in _LIFECYCLE:
            continue                       # lifecycle state, not an error
        missing = [k for k in _REQUIRED if k not in e]
        if status not in _LOADABLE or missing:
            reason = f"invalid: status={status}, missing={missing}"
            skipped.append((ident, reason))
            fail_open_alarm("edge_registry", f"{ident} skipped — {reason}",
                            count=1, notify=False)
            continue
        mismatch = {k: (v, versions.get(k)) for k, v in e['requires'].items()
                    if versions.get(k) != v}
        if mismatch:
            reason = "incompatible: " + ", ".join(
                f"{k} needs {a} engine has {b}" for k, (a, b) in mismatch.items())
            skipped.append((ident, reason))
            fail_open_alarm("edge_registry", f"{ident} skipped — {reason}",
                            count=1, notify=False)
            continue
        art = os.path.join(os.path.dirname(path), e['universe_artifact'])
        try:
            with open(art, 'r') as f:
                e = dict(e, universe=set(json.load(f)['tickers']))
        except Exception as ex:
            skipped.append((ident, f"artifact unreadable: {ex}"))
            fail_open_alarm("edge_registry", f"{ident} artifact unreadable: {ex}",
                            count=1, notify=False)
            continue
        manifest = {}
        if e.get('manifest'):
            man_path = os.path.join(os.path.dirname(path), e['manifest'])
            try:
                with open(man_path, 'r') as f:
                    manifest = yaml.safe_load(f) or {}
            except Exception:
                manifest = {}
        # else: no manifest -> empty -> validate_evidence flags the missing receipt
        reasons = validate_evidence(e, manifest, _FORWARD_BAR)
        if reasons:
            key = (e['id'], e['version'])
            if key in _LIFECYCLE_DEBT:
                debt.append((ident, _LIFECYCLE_DEBT[key]['reason']))
                logger.info("edge_registry %s — known lifecycle debt (%s)",
                            ident, _LIFECYCLE_DEBT[key]['remediation'])
            else:
                violations.append((ident, "; ".join(reasons)))
                fail_open_alarm("edge_registry",
                                f"{ident} lifecycle-unverified — {'; '.join(reasons)}",
                                count=1, notify=False)
        entries.append(e)
    return {'entries': entries, 'skipped': skipped,
            'violations': violations, 'debt': debt, 'hash': _registry_hash(path)}


def get_registry():
    global _cache
    if _cache is None:
        try:
            _cache = load_registry()
        except Exception as ex:
            fail_open_alarm("edge_registry", f"registry load failed: {ex}", count=1)
            _cache = {'entries': [], 'skipped': [('*', str(ex))],
                      'violations': [], 'debt': [], 'hash': 'load-failed'}
    return _cache


def _reset_cache():
    global _cache
    _cache = None


def approved_universe(strategy_fn):
    """Frozen ticker set for an APPROVED registry strategy; None if not governed."""
    for e in get_registry()['entries']:
        if e['strategy_fn'] == strategy_fn and e['status'] == 'APPROVED':
            return e['universe']
    return None


def startup_summary():
    r = get_registry()
    n_app = sum(1 for e in r['entries'] if e['status'] == 'APPROVED')
    n_sh = sum(1 for e in r['entries'] if e['status'] == 'SHADOW')
    return (f"registry @{r['hash']}: {n_app} approved, {n_sh} shadow, "
            f"{len(r['skipped'])} skipped, {len(r.get('debt', []))} debt, "
            f"{len(r.get('violations', []))} unverified")


def announce_registry(telegram_fn=None):
    """Log + best-effort Telegram the loaded registry state at startup."""
    msg = "📜 " + startup_summary()
    logger.info(msg)
    print(f"  {msg}")
    if telegram_fn is None:
        try:
            from utils.telegram import send_telegram as telegram_fn
        except Exception:
            return
    try:
        telegram_fn(msg)
    except Exception as ex:
        logger.debug("registry announce telegram failed: %s", ex)
