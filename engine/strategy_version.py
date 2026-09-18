"""engine/strategy_version.py — the canonical identity of a running strategy.

WHY THIS EXISTS (audit 2026-09-02, remaining blocker #3)
---------------------------------------------------------
`ft_strategy_version` was created by the forward-testing schema and never
populated: `strategy_version_id` and `config_hash` were NULL on all 3,033
`ft_signal` rows. A forward test whose every row is unlabelled cannot prove what
rule it measured — the outcome is real but unattributable, which is the same
class of defect as evidence that names no rule (finding L-1).

A strategy's canonical version pins everything that can change what it trades:

    strategy      the STRATEGY_FUNCS key (the registry key everything else uses)
    version       'v<N>' from the registry when governed, else 'live'
    config_hash   sha256 over the backtest function source + the live checker
                  source + the live gate set + the exit-policy identity
    rule_id       engine/rule_identity.py — <strategy>@<gates>#<digest>
    entry_rules_ref / exit_policy_ref  the code that decides entries and exits

`config_hash` deliberately spans BOTH the research function and the live checker.
Those two diverging without anyone noticing is exactly what the audit found
(finding L-1); a single hash over both makes such a divergence change the
version, which forces a new forward-test cohort rather than silently continuing
an old one.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import textwrap
from typing import Any, Optional

from engine.rule_identity import live_gates, live_rule_id

ENTRY_RULES_REF = "engine.strategies:_CHECKER_DISPATCH + check_current_entry_signal"
EXIT_POLICY_REF = "engine.exits.policy:ExitPolicyRegistry"


def _src(fn) -> str:
    try:
        return textwrap.dedent(inspect.getsource(fn))
    except (OSError, TypeError):
        return ""


def _sources(strategy: str) -> tuple[str, str]:
    """(backtest function source, live checker source). Either may be empty —
    a strategy with no live checker cannot trade, and a strategy with no
    backtest function has no OOS evidence; both facts belong in the hash."""
    from engine.strategies import STRATEGY_FUNCS, _CHECKER_DISPATCH
    bt = STRATEGY_FUNCS.get(strategy)
    chk = _CHECKER_DISPATCH.get(strategy)
    bt_src = _src(bt) if bt else ""
    # the dispatch entry is a lambda; hash what it calls, not the lambda
    chk_src = ""
    if chk is not None:
        try:
            inner = chk.__code__.co_names
            import engine.strategies as st
            for name in inner:
                target = getattr(st, name, None)
                if callable(target) and name.startswith("check_"):
                    chk_src = _src(target)
                    break
        except Exception:
            chk_src = ""
        if not chk_src:
            chk_src = _src(chk)
    return bt_src, chk_src


def config_for(strategy: str, registry_version: Optional[int] = None) -> dict[str, Any]:
    """The full, serialisable configuration this strategy runs under."""
    bt_src, chk_src = _sources(strategy)
    gates = list(live_gates(strategy))
    return {
        "strategy": strategy,
        "registry_version": registry_version,
        "rule_id": live_rule_id(strategy),
        "live_gates": gates,
        "entry_rules_ref": ENTRY_RULES_REF,
        "exit_policy_ref": EXIT_POLICY_REF,
        "backtest_fn_sha256": hashlib.sha256(bt_src.encode()).hexdigest() if bt_src else None,
        "live_checker_sha256": hashlib.sha256(chk_src.encode()).hexdigest() if chk_src else None,
        "has_backtest_fn": bool(bt_src),
        "has_live_checker": bool(chk_src),
    }


def config_hash(strategy: str, registry_version: Optional[int] = None) -> str:
    cfg = config_for(strategy, registry_version)
    payload = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def version_label(strategy: str, registry_version: Optional[int] = None) -> str:
    return f"v{registry_version}" if registry_version else "live"


def _registry_versions() -> dict[str, int]:
    try:
        from engine.registry_loader import get_registry
        out = {}
        for e in get_registry()["entries"]:
            out[e["strategy_fn"]] = max(out.get(e["strategy_fn"], 0), int(e["version"]))
        return out
    except Exception:
        return {}


def upsert(conn, strategy: str, registry_version: Optional[int] = None) -> int:
    """Idempotently record this strategy's canonical version. Returns its id.

    Append-only in effect: a config change produces a NEW (strategy, version)
    row rather than editing the old one, because `version` embeds the config
    hash. Historical signals keep pointing at the version they actually ran
    under — the whole reason the column exists.
    """
    cfg = config_for(strategy, registry_version)
    h = config_hash(strategy, registry_version)
    label = f"{version_label(strategy, registry_version)}+{h}"
    conn.execute(
        "INSERT OR IGNORE INTO ft_strategy_version "
        "(strategy, version, config_json, config_hash, entry_rules_ref, exit_policy_ref) "
        "VALUES (?,?,?,?,?,?)",
        (strategy, label, json.dumps(cfg, sort_keys=True), h,
         ENTRY_RULES_REF, EXIT_POLICY_REF))
    row = conn.execute(
        "SELECT id FROM ft_strategy_version WHERE strategy=? AND version=?",
        (strategy, label)).fetchone()
    return row[0] if row else None


def sync_all(conn, strategies=None) -> dict[str, int]:
    """Record the canonical version of every known strategy plus the two
    watchlist cohorts. Returns {strategy: version_id}."""
    from engine.strategies import STRATEGY_FUNCS
    names = list(strategies) if strategies is not None else list(STRATEGY_FUNCS)
    regv = _registry_versions()
    out = {}
    for name in names:
        try:
            out[name] = upsert(conn, name, regv.get(name))
        except Exception:
            continue
    conn.commit()
    return out


def resolve(conn, strategy: str) -> tuple[Optional[int], Optional[str]]:
    """(version_id, config_hash) for `strategy` as it runs RIGHT NOW.

    Cohort pseudo-strategies ('eod', 'premarket') have no STRATEGY_FUNCS entry;
    they still get a version row so their forward-test cohort is pinned to the
    code that produced it.
    """
    regv = _registry_versions().get(strategy)
    try:
        vid = upsert(conn, strategy, regv)
        conn.commit()
        return vid, config_hash(strategy, regv)
    except Exception:
        return None, None
