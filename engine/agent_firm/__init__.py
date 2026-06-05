"""Agent firm: multi-agent LLM veto-gate for IDX signals.

Phase 1: 2 agents (Technical, Risk). Gated by AGENT_FIRM_ENABLED env var.
See docs/superpowers/specs/2026-05-19-agent-firm-hybrid-stack-design.md.
"""

from .schemas import AgentDecision, AgentResult, SignalCandidate


def evaluate(candidates):
    from .firm import evaluate as _evaluate  # lazy — avoids eager langgraph import
    return _evaluate(candidates)


__all__ = ["SignalCandidate", "AgentDecision", "AgentResult", "evaluate"]
