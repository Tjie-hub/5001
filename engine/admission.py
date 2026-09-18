"""engine/admission.py — one auditable answer to "may this strategy trade this
ticker right now, and on what evidence?"

WHY THIS EXISTS (audit 2026-09-02, findings S-1, S-2, L-1)
-----------------------------------------------------------
Admission was spread across `scheduler/scanner.py::_edge_selectable`,
`adaptive_strategy_selector` and `_get_disabled_strategies`, and the composite
outcome was invisible: on 2026-09-02 the live scanner could not admit a single
strategy for any of 877 tickers, in any regime, and had produced no BUY signal
since 2026-07-01 -- with no alert, no log line, and no diagnostic anywhere.
Every individual gate was working exactly as designed. Nobody could see the sum.

This module does not change what is admitted. It makes the decision explicit,
ordered, recorded, and reportable, and it adds the two gates the audit found
missing:

  * rule parity (L-1)  -- refuse a strategy whose live rule differs from the
                          rule research actually measured.
  * evidence staleness (S-2) -- refuse OOS statistics too old to describe the
                          current market. `_edge_selectable` never read
                          `last_computed` at all; a 2019 row was selected exactly
                          like a fresh one.

Both gates are strictly tightening. Neither can manufacture a signal.

The ordering is deliberate: cheapest and most decisive first, so the recorded
`stage` names the *primary* reason a strategy is out, not an incidental one.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import date
from typing import Any, Optional

from engine.rule_identity import live_rule_id, rule_parity

logger = logging.getLogger(__name__)

# wf_edge is refreshed weekly (deploy/crontab: Fri 16:05). Two refresh cycles of
# slack absorbs a missed run or a deploy weekend; beyond that the statistics no
# longer describe the market the scanner is trading and must not gate capital.
WF_EDGE_MAX_AGE_DAYS = 14

# Mirrors engine.wf_edge.N_MIN_TRADES -- below this the research layer makes no
# edge claim, so neither may admission.
from engine.wf_edge import N_MIN_TRADES  # noqa: E402

STAGE_DISABLED = "disabled"
STAGE_REGISTRY = "registry"
STAGE_RULE_PARITY = "rule_parity"
STAGE_OOS_EVIDENCE = "oos_evidence"
STAGE_STALENESS = "evidence_staleness"
STAGE_ADMITTED = "admitted"


@dataclass(frozen=True)
class AdmissionVerdict:
    ticker: str
    strategy: str
    admitted: bool
    stage: str
    reason: str
    registry_state: str                  # APPROVED | SHADOW | UNREGISTERED
    rule_id: str
    wf_expectancy_pct: Optional[float] = None
    wf_n_trades: Optional[int] = None
    wf_last_computed: Optional[str] = None
    evidence_source: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def manifest_rule_ids() -> dict[str, str]:
    """`rule_id:` declared in each loaded registry manifest.

    This is how a production-only gate is legitimised: re-run the walk-forward
    with the gate applied, then record the resulting live rule_id in the
    strategy's manifest. Admission then sees parity and lets it through. Absent a
    declaration, the researched rule is the bare strategy function -- which is
    what `research/walkforward_multi.py` actually runs today.
    """
    try:
        from engine.registry_loader import get_registry
        out = {}
        for e in get_registry()["entries"]:
            rid = (e.get("manifest_data") or {}).get("rule_id") or e.get("rule_id")
            if rid:
                out[e["strategy_fn"]] = rid
        return out
    except Exception:
        return {}


def _registry_state(strategy: str, ticker: str) -> tuple[str, bool]:
    """(state, ticker_in_frozen_universe). Imported lazily so this module stays
    importable without a registry file present."""
    from engine.registry_loader import registry_governance
    gov = registry_governance(strategy)
    if gov is None:
        return "UNREGISTERED", False
    if gov == "SHADOW":
        return "SHADOW", False
    return "APPROVED", (ticker in gov)


_RULE_RESEARCHED_CACHE: dict = {}


def reset_evidence_cache() -> None:
    """Clear the per-scan "has this rule been researched at all?" cache."""
    _RULE_RESEARCHED_CACHE.clear()


def rule_researched(conn, strategy: str, rule_id: str) -> bool:
    """Has a walk-forward study been run under exactly this rule?

    True when `wf_edge_rule` holds any row for (strategy, rule_id) — evidence
    that research measured the rule production will execute. Cached per scan;
    call reset_evidence_cache() between scan cycles.
    """
    key = (strategy, rule_id)
    if key in _RULE_RESEARCHED_CACHE:
        return _RULE_RESEARCHED_CACHE[key]
    found = False
    try:
        row = conn.execute(
            "SELECT 1 FROM wf_rule_study WHERE strategy=? AND rule_id=? LIMIT 1",
            (strategy, rule_id)).fetchone()
        found = row is not None
    except Exception:
        found = False
    if not found:
        # Fall back to row presence for studies recorded before the manifest
        # existed. A manifest is strictly more informative (it also proves a
        # study that produced zero qualifying rows), so it is checked first.
        try:
            row = conn.execute(
                "SELECT 1 FROM wf_edge_rule WHERE strategy=? AND rule_id=? LIMIT 1",
                (strategy, rule_id)).fetchone()
            found = row is not None
        except Exception:
            found = False
    _RULE_RESEARCHED_CACHE[key] = found
    return found


def _wf_row(conn, ticker: str, strategy: str, rule_id: str = None,
            prefer_rule: bool = False):
    """OOS statistics for (ticker, strategy) UNDER THE GIVEN RULE.

    `wf_edge` holds the bare-rule study; `wf_edge_rule` holds studies keyed by
    the rule that produced them. Evidence is only meaningful against its own
    rule, so when production executes a gated variant the bare table must not be
    consulted at all (that would be finding L-1 reintroduced one level up).

    Returns (row, source) with row = (expectancy_pct, n_trades, last_computed).
    """
    if prefer_rule and rule_id:
        try:
            row = conn.execute(
                "SELECT expectancy_pct, n_trades, last_computed FROM wf_edge_rule "
                "WHERE ticker=? AND strategy=? AND rule_id=? LIMIT 1",
                (ticker, strategy, rule_id)).fetchone()
            if row:
                return row, "wf_edge_rule"
        except Exception:
            pass
        return None, "wf_edge_rule"
    try:
        return conn.execute(
            "SELECT expectancy_pct, n_trades, last_computed FROM wf_edge "
            "WHERE ticker=? AND strategy=? LIMIT 1", (ticker, strategy),
        ).fetchone(), "wf_edge"
    except Exception:
        return None, "wf_edge"


def _age_days(last_computed: Optional[str], today: Optional[date] = None
              ) -> Optional[int]:
    if not last_computed:
        return None
    try:
        d = date.fromisoformat(str(last_computed)[:10])
    except (ValueError, TypeError):
        return None
    return ((today or date.today()) - d).days


def evaluate(conn, ticker: str, strategy: str, *, disabled: frozenset[str] | set,
             manifest_rule_ids: Optional[dict] = None,
             today: Optional[date] = None,
             require_registry: bool = False) -> AdmissionVerdict:
    """Full admission decision for one (ticker, strategy), with its reason.

    `require_registry=True` reproduces the registry-only path
    (`_edge_selectable(candidates=None)`, D-031 Decision 1): a strategy found by
    scanning wf_edge must independently clear APPROVED admission. When False,
    a genuinely UNREGISTERED strategy may still qualify on live wf_edge evidence
    (the D-031 Option C legacy exception) -- but now only if it also clears rule
    parity and staleness.
    """
    from engine.rule_identity import research_rule_id
    rid = live_rule_id(strategy)
    state, in_universe = _registry_state(strategy, ticker)

    # Which study does this rule's evidence live in? When the live rule already
    # equals the researched (bare) rule, wf_edge IS that study. Otherwise only a
    # rule-indexed study can speak for it.
    declared = manifest_rule_ids if manifest_rule_ids is not None else _declared()
    declared_rid = (declared or {}).get(strategy)
    bare_is_live = (rid == research_rule_id(strategy))
    researched = bare_is_live or rule_researched(conn, strategy, rid)
    row, source = _wf_row(conn, ticker, strategy, rid,
                          prefer_rule=not bare_is_live)
    exp = row[0] if row else None
    n = row[1] if row else None
    lc = row[2] if row else None

    def verdict(admitted, stage, reason):
        return AdmissionVerdict(ticker, strategy, admitted, stage, reason,
                                state, rid, exp, n, lc, source)

    if strategy in disabled:
        return verdict(False, STAGE_DISABLED,
                       "listed in paper_config disabled_strategies")

    if state == "SHADOW":
        # T7 invariant: SHADOW can never reach live execution via any fallback.
        return verdict(False, STAGE_REGISTRY,
                       "registry-governed but not APPROVED (SHADOW)")
    if state == "APPROVED" and not in_universe:
        return verdict(False, STAGE_REGISTRY,
                       "APPROVED but ticker is outside the frozen universe")
    if state == "UNREGISTERED" and require_registry:
        return verdict(False, STAGE_REGISTRY,
                       "no registry entry; registry-only admission path")

    declared = manifest_rule_ids if manifest_rule_ids is not None else _declared()
    # Parity holds when EITHER the rule sets already match, OR the strategy's
    # registry manifest declares the live rule as the one its evidence was
    # produced under, OR a walk-forward study exists that was actually run under
    # the live rule (wf_edge_rule). The last is the self-proving path: evidence
    # measured under the executed rule cannot misdescribe it.
    ok, why = rule_parity(strategy, declared_rid)
    if not ok and not researched:
        return verdict(False, STAGE_RULE_PARITY,
                       why + " — and no wf_edge_rule study exists for the live "
                             "rule (run: python -m research.cli wf-parity)")

    if state == "APPROVED" and in_universe:
        # Registry admission is receipt-bound (R-10) and carries its own frozen
        # universe; it does not additionally require a live wf_edge row.
        return verdict(True, STAGE_ADMITTED,
                       "APPROVED in frozen universe, rule parity holds")

    # Ungoverned legacy path: live OOS evidence must carry the whole claim.
    if row is None:
        return verdict(False, STAGE_OOS_EVIDENCE,
                       f"no {source} row for this (ticker, strategy) under "
                       f"rule {rid}")
    if n is None or n < N_MIN_TRADES:
        return verdict(False, STAGE_OOS_EVIDENCE,
                       f"pooled OOS sample too thin (n={n}, need >={N_MIN_TRADES})")
    if exp is None or exp <= 0:
        return verdict(False, STAGE_OOS_EVIDENCE,
                       f"non-positive pooled OOS expectancy ({exp})")

    age = _age_days(lc, today)
    if age is None:
        return verdict(False, STAGE_STALENESS,
                       f"unusable wf_edge last_computed={lc!r}")
    if age > WF_EDGE_MAX_AGE_DAYS:
        return verdict(False, STAGE_STALENESS,
                       f"wf_edge is {age}d old (max {WF_EDGE_MAX_AGE_DAYS}d)")

    return verdict(True, STAGE_ADMITTED,
                   f"positive pooled OOS expectancy {exp:+.3f}% over {n} trades "
                   f"in {source}, computed {lc}, measured under the live rule")


def _declared() -> dict[str, str]:
    return manifest_rule_ids()


def summarise(verdicts) -> dict[str, int]:
    """Count blocking stages across a batch -- the input to the health alert."""
    counts: dict[str, int] = {}
    for v in verdicts:
        counts[v.stage] = counts.get(v.stage, 0) + 1
    return counts


def format_diagnostic(counts: dict[str, int], *, scanned: int) -> str:
    """One human-readable line explaining why a scan admitted nothing."""
    if not counts:
        return f"admission: nothing evaluated ({scanned} tickers scanned)"
    parts = ", ".join(f"{k}={v}" for k, v in sorted(counts.items(),
                                                    key=lambda kv: -kv[1]))
    admitted = counts.get(STAGE_ADMITTED, 0)
    return (f"admission over {scanned} tickers: {admitted} admitted; "
            f"blocking stages -> {parts}")
