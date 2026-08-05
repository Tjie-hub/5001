# AF-2 WP3 — Specialist Context Consumption Matrix

Companion to `Audit/AF2_WP3_IMPLEMENTATION_REPORT.md`. One row per specialist that exists in
`engine/agent_firm/agents/`; the brief's org-chart roles without a code module are called out
separately below the table.

| Specialist | File | Consumes (Tier 1 context) | Still receives (non-context) | Deterministic derivation removed | Missing-context behavior |
|---|---|---|---|---|---|
| Technical Analyst | `agents/technical.py` | `candidate.technical` (`TechnicalContext`) | Candidate identity summary (ticker/strategy/score/regime/flow_verdict/foreign_score) | Raw 60-bar OHLCV `sqlite_query`; the prompt no longer asks the LLM to compute S/R itself | `candidate.technical or TechnicalContext()` — degrades to all-`None`/`NEUTRAL` defaults; verified by `test_technical_missing_context_degrades_to_default_not_raise` |
| Flow Specialist | `agents/flow.py` | `candidate.flow` (`FlowContext`) | Candidate identity summary | Raw `stockbit_flow`/`broker_flow`/`stockbit_flow_bars` rows; the prompt's explicit "sum net_lot" instruction | `candidate.flow or FlowContext()` — degrades to `verdict=None`, `trend_7d="flat"`; verified by `test_flow_missing_context_degrades_to_default_not_raise` |
| Regime Analyst | `agents/regime.py` | `candidate.regime_context` (`RegimeContext`) | Candidate identity summary (incl. legacy `regime` tag) | Raw `wf_scores`/`daily_screen` rows; the prompt's literal VPIN/vol_ratio/Sharpe thresholds (a second regime classifier) | `candidate.regime_context or RegimeContext()` — degrades to `regime_call="UNKNOWN"`; verified by `test_regime_missing_context_degrades_to_default_not_raise` |
| News/Sentiment Analyst | `agents/news.py` | `candidate.news` (`NewsContext`) | Candidate identity summary; live Tavily web search (unchanged — genuine NLU, no canonical producer) | Raw `news_mentions` dict (was already non-deterministic in its own right — no threshold logic existed here to remove) | `candidate.news or NewsContext()` — degrades to `mentions_count_7d=0`, `has_catalyst=False`; verified by `test_news_missing_context_degrades_to_default_not_raise` |
| Risk Manager | `agents/risk.py` | `candidate.portfolio` (`PortfolioContext`) + `candidate.risk_limits` (`RiskContext`), **newly wired this WP** | Analyst/bull/bear `AgentResult`s; trimmed candidate identity summary (previously the full `model_dump()`, which silently leaked all 8 Tier-1 objects since WP2) | N/A — Risk Manager already consumed only pre-produced analyst outputs, never raw market data; this WP *adds* consumption (closing a delivery gap) rather than removing a computation | `candidate.portfolio or PortfolioContext()` / `candidate.risk_limits or RiskContext()` — degrades to `already_open_position=False`, `entries_blocked=False`, `drawdown_pct=None`; verified by `test_risk_missing_portfolio_and_risk_context_degrades_to_default` |
| Bull Researcher | `agents/bull.py` | *(unchanged this WP)* — `analyst_reports` only | Full `candidate.model_dump()` (pre-existing, not trimmed this WP — see Known Limitation #5) | N/A — never derived raw data; confirmed unmodified | N/A (no Tier 1 field read directly) |
| Bear Researcher | `agents/bear.py` | *(unchanged this WP)* — `analyst_reports` + bull case | Full `candidate.model_dump()` (same as Bull) | N/A — never derived raw data; confirmed unmodified | N/A |

## Brief roles with no corresponding code module

| Brief role | Mapped to | Status |
|---|---|---|
| Portfolio Manager | `risk.py`'s new `PortfolioContext` consumption (above) | Closed this WP — no separate agent exists; the capital-facing check now lives where the capital-facing decision is made |
| CIO | `bull.py`/`bear.py` (structurally closest: consume specialist outputs only) | Already compliant, unmodified |
| Consensus | `ConsensusContext` (schemas.py, Tier 2) | **Unbuilt** — no `guardrails.py::build_consensus_summary()`, no evaluation-graph attach point; inherited gap from WP1/WP2, explicitly not closed this WP (see Implementation Report) |

## Prompt payload shape, before → after (per specialist)

| Specialist | Before (raw data key(s) in the user message) | After (typed context key in the user message) |
|---|---|---|
| Technical | `ohlcv_recent_60d` (60 raw bars) | `technical_context` (11 precomputed fields + 10-bar color) |
| Flow | `stockbit_flow_14d`, `broker_flow_14d`, `stockbit_flow_bars_7d` | `flow_context` (7 precomputed fields) |
| Regime | `wf_scores`, `sector_data_10d` | `regime_context` (6 precomputed fields) |
| News | `news_mentions_7d` (untyped) | `news_context` (`mentions_7d`, `mentions_count_7d`, `has_catalyst`) + unchanged `web_search_results` |
| Risk | *(no portfolio/risk data delivered at all — gap)* | `portfolio_context` (2 fields), `risk_context` (2 fields), added alongside unchanged `analyst_reports` |
