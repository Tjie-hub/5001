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

# Execution-model compatibility pins (spec §6, docs/superpowers/specs/
# 2026-07-07-research-production-separation-design.md:176-185). Each field
# must be bumped whenever the semantics it names change, so a registry
# entry's `requires{}` (frozen at approval time) stops matching and the
# entry is skipped rather than silently admitted under a different
# execution model (T7 invariant #7) -- e.g. a 1B-style exit-kernel change
# bumps exit_kernel: 1 -> 2. As of 2026-08-19 (T7 audit) this has never
# been bumped since introduction and nothing previously enforced the
# discipline; see tests/test_t7_execution_model_pinning.py for a
# source-hash-based drift check on the one live registry entry.
#   data_schema:    the OHLCV corpus basis (1 = post-2A raw-basis corpus)
#   exit_kernel:    SL/TP/exit semantics (1 = post-1B unified kernel)
#   regime_model:   detect_regime()'s BULL/BEAR/SIDEWAYS + ADX sub-band logic
#   engine_version: overall engine semantics (1 = post-Phase-3 engine)
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
# NR7_BULL v2's entry was removed 2026-10-01 (D-066): the entry is RETIRED now, and a
# lifecycle state is skipped before the debt check ever runs, so the grandfather was
# unreachable dead code — removal is the allowed shrink direction.
_LIFECYCLE_DEBT = {}

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
    # Lifecycle-state records (CANDIDATE/SUSPENDED/RETIRED/SUPERSEDED) are not
    # loaded as entries — no validation, no universe — but they are collected
    # minimally so registry_governance()/admission_path() can tell a REGISTERED
    # but non-live strategy (sentinel, callers must exclude) from a genuinely
    # UNREGISTERED one (None, the sole case where legacy handling is safe).
    # D-066 lesson: without this, RETIRED is indistinguishable from "never
    # registered" and the D-031 Option C legacy fallback re-exposes a retired
    # strategy to live selection on any positive wf_edge row.
    lifecycle = []
    for e in raw:
        ident = f"{e.get('id', '?')}_v{e.get('version', '?')}"
        status = e.get('status')
        if status in _LIFECYCLE:
            lifecycle.append({'id': e.get('id'), 'version': e.get('version'),
                              'status': status, 'strategy_fn': e.get('strategy_fn')})
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
                    loaded = yaml.safe_load(f)
                manifest = loaded if isinstance(loaded, dict) else {}
            except Exception:
                manifest = {}
        # else: no manifest -> empty -> validate_evidence flags the missing receipt
        # Attach the manifest so downstream admission can read its declared
        # `rule_id:` (audit L-1) without re-opening the file. Read-only payload;
        # nothing here changes loading or validation semantics.
        e = dict(e, manifest_data=manifest)
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
                continue                   # unverified & ungrandfathered: do not load
        entries.append(e)
    return {'entries': entries, 'skipped': skipped,
            'violations': violations, 'debt': debt, 'lifecycle': lifecycle,
            'hash': _registry_hash(path)}


def get_registry():
    global _cache
    if _cache is None:
        try:
            _cache = load_registry()
        except Exception as ex:
            fail_open_alarm("edge_registry", f"registry load failed: {ex}", count=1)
            _cache = {'entries': [], 'skipped': [('*', str(ex))],
                      'violations': [], 'debt': [], 'lifecycle': [],
                      'hash': 'load-failed'}
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


def registry_governance(strategy_fn):
    """Governance state of `strategy_fn` in the currently loaded registry.

    Returns the frozen ticker universe (set) if APPROVED; the sentinel string
    'SHADOW' if the strategy is registry-governed but not (yet) APPROVED —
    callers MUST exclude it outright rather than fall back to an ungoverned
    path, per the T7 invariant that a SHADOW strategy can never reach live
    execution via a fallback. Returns None only when the strategy has no
    registry record at all — including when the registry itself failed to load
    (get_registry() then degrades to an empty entries list) — which is the
    sole case where legacy/ungoverned handling is safe.

    'RETIRED' (D-066): a strategy whose every record is in a terminal
    lifecycle state (RETIRED/SUPERSEDED — nothing loadable) gets the same
    contract as 'SHADOW': registered, excluded outright, never a legacy
    fallback. Treating it as UNREGISTERED would let the D-031 Option C
    path re-admit it on a stale positive wf_edge row.
    """
    matches = [e for e in get_registry()['entries'] if e['strategy_fn'] == strategy_fn]
    for e in matches:
        if e['status'] == 'APPROVED':
            return e['universe']
    if matches:
        return 'SHADOW'
    lifec = [r for r in get_registry().get('lifecycle', [])
             if r.get('strategy_fn') == strategy_fn]
    if lifec:
        return 'RETIRED'
    return None


def admission_path(strategy_fn):
    """Human-readable classification of why `strategy_fn` is (or isn't)
    currently admitted -- for post-hoc auditability (T7 invariant #9).

    One of:
      'UNREGISTERED'    -- no registry entry at all
      'SHADOW'          -- registry-governed, not (yet) APPROVED
      'RETIRED'         -- registered but every record is in a terminal
                           lifecycle state (RETIRED/SUPERSEDED); excluded
                           outright, never a legacy fallback (D-066)
      'APPROVED_DEBT'   -- APPROVED via a _LIFECYCLE_DEBT grandfather
                           exception (no clean evidence receipt)
      'APPROVED_CLEAN'  -- APPROVED with a fully valid evidence receipt

    Callers (e.g. scheduler.scanner's auto-open) record this alongside
    get_registry()['hash'] on the resulting trade so any admission can be
    traced back to the exact registry state that authorized it, without a
    second registry -- both values are read straight off get_registry().
    """
    r = get_registry()
    matches = [e for e in r['entries'] if e['strategy_fn'] == strategy_fn]
    if not matches:
        if any(x.get('strategy_fn') == strategy_fn
               for x in r.get('lifecycle', [])):
            return 'RETIRED'
        return 'UNREGISTERED'
    approved = [e for e in matches if e['status'] == 'APPROVED']
    if not approved:
        return 'SHADOW'
    debt_idents = {d[0] for d in r['debt']}
    for e in approved:
        if f"{e['id']}_v{e['version']}" in debt_idents:
            return 'APPROVED_DEBT'
    return 'APPROVED_CLEAN'


def startup_summary():
    r = get_registry()
    n_app = sum(1 for e in r['entries'] if e['status'] == 'APPROVED')
    n_sh = sum(1 for e in r['entries'] if e['status'] == 'SHADOW')
    n_ret = sum(1 for x in r.get('lifecycle', []) if x.get('status') == 'RETIRED')
    return (f"registry @{r['hash']}: {n_app} approved, {n_sh} shadow, "
            f"{n_ret} retired, {len(r['skipped'])} skipped, "
            f"{len(r.get('debt', []))} debt, "
            f"{len(r.get('violations', []))} unverified")


def announce_registry(telegram_fn=None):
    """Log + best-effort Telegram the loaded registry state at startup."""
    msg = "📜 " + startup_summary()
    logger.info(msg)
    if telegram_fn is None:
        try:
            from utils.telegram import send_telegram as telegram_fn
        except Exception:
            return
    try:
        telegram_fn(msg)
    except Exception as ex:
        logger.debug("registry announce telegram failed: %s", ex)
