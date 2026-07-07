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

_cache = None


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
        entries.append(e)
    return {'entries': entries, 'skipped': skipped, 'hash': _registry_hash(path)}


def get_registry():
    global _cache
    if _cache is None:
        try:
            _cache = load_registry()
        except Exception as ex:
            fail_open_alarm("edge_registry", f"registry load failed: {ex}", count=1)
            _cache = {'entries': [], 'skipped': [('*', str(ex))], 'hash': 'load-failed'}
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
            f"{len(r['skipped'])} skipped")
