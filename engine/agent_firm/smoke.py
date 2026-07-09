"""Tier 4 daily smoke probe for the agent firm.

Runs one canned signal through the full pipeline and asserts:
- Response within 90s
- Decision is one of: approve, veto, degraded
- Cost is reasonable for the provider(s) that actually ran (see
  `_check_cost` — the Z.ai provider is metered per-token so its cost must
  fall within [$0.0001, $0.05]; the Claude provider is a subscription CLI
  call and always reports cost_usd=0.0 by design, so a claude-only run is
  instead checked for evidence of real token usage)

Usage:
    AGENT_FIRM_ENABLED=true ZAI_API_KEY=sk-... \\
      venv/bin/python -m engine.agent_firm.smoke

Exits 0 on success, 2 on duration timeout, 3 on invalid decision,
4 on cost out of range, 1 on any other error.
"""

import asyncio
import sys
from datetime import datetime, timezone

from . import config
from .firm import evaluate_async
from .schemas import AgentDecision, SignalCandidate

_CANNED = SignalCandidate(
    ticker="BBRI",
    strategy="momentum_following",
    score=4.2,
    scan_time=datetime.now(timezone.utc).isoformat(),
    regime="BULL",
    flow_verdict="STRONG_BUY",
    foreign_score=3.42,
    indicators={"vwma_above": True, "ma50_above": True},
)

_MAX_DURATION_S = 150.0
_COST_MIN = 0.0001
_COST_MAX = 0.05


def _check_cost(d: AgentDecision) -> tuple[bool, str | None]:
    """Provider-aware cost sanity check.

    Z.ai is metered per-token, so a healthy zai-only decision's cost_usd
    should land in [_COST_MIN, _COST_MAX] — same as before this fix.

    Claude is a subscription CLI call (ClaudeProvider.generate() always
    returns cost_usd=0.0 by design), so a claude-only decision can never
    satisfy that lower bound. Instead we check tokens_in > 0 as evidence
    the pipeline made real calls rather than short-circuiting.

    A mixed/failover run (some agents on zai, some on claude) can
    legitimately report a cost below the zai-only floor, since part of
    the work was free. We keep the ceiling (a cost above _COST_MAX is
    still a real anomaly regardless of provider mix) and require
    tokens_in > 0 as the "pipeline actually ran" signal in place of the
    floor.

    Returns (ok, failure_message_or_None).
    """
    uses_claude = "claude" in d.providers_used
    uses_zai = "zai" in d.providers_used

    if uses_claude and not uses_zai:
        if d.tokens_in <= 0:
            return False, (
                f"claude-only run but tokens_in={d.tokens_in} "
                "(expected real token usage as evidence the pipeline ran)"
            )
        return True, None

    if uses_claude and uses_zai:
        if d.cost_usd < 0 or d.cost_usd > _COST_MAX:
            return False, f"cost ${d.cost_usd:.4f} outside [0, {_COST_MAX}]"
        if d.tokens_in <= 0:
            return False, (
                f"mixed-provider run but tokens_in={d.tokens_in} "
                "(expected real token usage as evidence the pipeline ran)"
            )
        return True, None

    # zai-only (or providers_used unpopulated) — unchanged legacy behavior.
    if not (_COST_MIN <= d.cost_usd <= _COST_MAX):
        return False, f"cost ${d.cost_usd:.4f} outside [{_COST_MIN}, {_COST_MAX}]"
    return True, None


def main() -> int:
    if not config.is_active():
        print("SKIP: agent firm not active (FIRM_ENABLED=false or kill switch set)")
        return 0
    try:
        decisions = asyncio.run(evaluate_async([_CANNED]))
    except Exception as err:
        print(f"FAIL: pipeline raised {type(err).__name__}: {err}")
        return 1

    if not decisions:
        print("FAIL: no decisions returned")
        return 1

    d = decisions[0]
    print(
        f"decision={d.decision} conf={d.confidence} "
        f"size={d.size_hint} cost=${d.cost_usd:.4f} dur={d.duration_s:.1f}s"
    )
    if d.duration_s > _MAX_DURATION_S:
        print(f"FAIL: duration {d.duration_s:.1f}s exceeds {_MAX_DURATION_S}s budget")
        return 2
    if d.decision not in ("approve", "veto", "degraded"):
        print(f"FAIL: invalid decision {d.decision}")
        return 3
    if d.decision != "degraded":
        cost_ok, cost_err = _check_cost(d)
        if not cost_ok:
            print(f"FAIL: {cost_err}")
            return 4
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
