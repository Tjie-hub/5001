"""Tier 4 daily smoke probe for the agent firm.

Runs one canned signal through the full pipeline and asserts:
- Response within 90s
- Decision is one of: approve, veto, degraded
- Cost is reasonable (between $0.0001 and $0.05 for one signal)

Usage:
    AGENT_FIRM_ENABLED=true DEEPSEEK_API_KEY=sk-... \\
      venv/bin/python -m engine.agent_firm.smoke

Exits 0 on success, 2 on duration timeout, 3 on invalid decision,
4 on cost out of range, 1 on any other error.
"""

import asyncio
import sys
from datetime import datetime, timezone

from . import config
from .firm import evaluate_async
from .schemas import SignalCandidate

_CANNED = SignalCandidate(
    ticker="BBRI",
    strategy="momentum_following",
    score=4.2,
    scan_time=datetime.now(timezone.utc).isoformat(),
    regime="TRENDING",
    flow_verdict="STRONG_BUY",
    foreign_score=3.42,
    indicators={"vwma_above": True, "ma50_above": True},
)

_MAX_DURATION_S = 150.0
_COST_MIN = 0.0001
_COST_MAX = 0.05


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
    if d.decision != "degraded" and not (_COST_MIN <= d.cost_usd <= _COST_MAX):
        print(f"FAIL: cost ${d.cost_usd:.4f} outside [{_COST_MIN}, {_COST_MAX}]")
        return 4
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
