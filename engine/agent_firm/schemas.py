"""Pydantic schemas for the agent firm.

Decision lifecycle:
  approve  — Risk Manager approved; signal proceeds to Telegram
  veto     — Risk Manager blocked; signal does not proceed (Phase 3+)
  bypassed — Firm was disabled or kill-switched; signal proceeds unevaluated
  degraded — Risk Manager call failed; signal proceeds (fail-open)
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SignalCandidate(BaseModel):
    ticker: str
    strategy: str
    score: float
    scan_time: str
    regime: Optional[str] = None
    flow_verdict: Optional[str] = None
    foreign_score: Optional[float] = None
    indicators: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    role: str
    status: Literal["ok", "failed"]
    output: Optional[dict[str, Any]] = None
    prompt_version: str = "v1"
    tokens_in: int = 0
    tokens_out: int = 0
    duration_s: float = 0.0
    tools_called: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class AgentDecision(BaseModel):
    ticker: str
    strategy: str
    scan_time: str
    quant_score: float
    decision: Literal["approve", "veto", "bypassed", "degraded"]
    confidence: Optional[float] = None
    size_hint: Optional[float] = None
    rationale: Optional[str] = None
    traces: list[AgentResult] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
