"""Agent firm: multi-agent LLM veto-gate for IDX signals.

Phase 1: 2 agents (Technical, Risk). Gated by AGENT_FIRM_ENABLED env var.
See docs/superpowers/specs/2026-05-19-agent-firm-hybrid-stack-design.md.
"""

from .firm import evaluate
from .schemas import AgentDecision, AgentResult, SignalCandidate

__all__ = ["SignalCandidate", "AgentDecision", "AgentResult", "evaluate"]
