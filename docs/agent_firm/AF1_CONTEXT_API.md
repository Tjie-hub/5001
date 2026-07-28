# AF-1 — Context API Design

**Date:** 2026-07-28
**Principle:** Agent Firm must never open a production database connection to gather its own
evaluation context. Production Engine hands Agent Firm everything it needs as typed data, through a
defined API; Agent Firm's job is to reason over that data, not to go get it.
**Basis:** direct inspection of `engine/agent_firm/firm.py::_build_context()` — the actual function
this design replaces. Today it runs seven raw SQL queries (`paper_trades`, `ohlcv`, `broker_flow`,
`stockbit_flow`, `stockbit_flow_bars`, `wf_scores`, `daily_screen`) plus a `news_lookup.lookup()` call,
against the shared database, on every single evaluation. This is Blocker 2 from
`AGENT_FIRM_ARCHITECTURE.md`, more extensive than that document's original scope (which named only
`tools/news_lookup.py`/`tools/sqlite_query.py`) — `_build_context()` itself is the larger instance of
the same problem and is the primary subject of this design.

---

## The Six Context Types

### `MarketContext`
Market-wide (not ticker-specific) state.
```
regime: str                        # already exists as SignalCandidate.regime today
ihsg_recent: list[OhlcvBar]         # replaces the raw "SELECT ... WHERE ticker='IHSG'" query
market_risk_score: float | None     # already computed by Production Engine for /metrics — currently
                                     # never handed to Agent Firm at all; this closes that gap
```

### `Opportunity`
The signal being evaluated — formalizes what `SignalCandidate` already is; not a new type, a naming
clarification that `SignalCandidate` *is* the `Opportunity` object referenced in the AF-1 brief.
No field changes from the existing, versioned `SignalCandidate` (see `AGENT_FIRM_INTERFACE_SPEC.md`).

### `RecentHistory`
Everything ticker-specific and price/flow/signal-history-derived — replaces `ohlcv`, `broker_flow`,
`stockbit_flow`, `stockbit_flow_bars`, `wf_scores`, `sector_data`, and `news_mentions` from
`_build_context()`.
```
ohlcv: list[OhlcvBar]                        # last 60 days, replaces the raw ohlcv query
broker_flow: list[BrokerFlowRow]             # last 14 days
stockbit_flow: list[StockbitFlowRow]         # last 14 days, daily granularity
stockbit_flow_bars: list[StockbitFlowBarRow] # last 7 days, intraday granularity
strategy_edge: list[WfScoreRow]              # per-strategy walk-forward scores for this ticker
                                              # (reads from wf_scores, a research-owned,
                                              # write-fenced table per CLAUDE.md — Production
                                              # Engine already only reads this table today, so
                                              # this context type doesn't change that boundary,
                                              # only who executes the read)
recent_screen_signals: list[ScreenRow]       # last 10 days of daily_screen (VPIN/vol-ratio)
news_mentions: list[NewsMention]             # last 7 days
```

### `PortfolioState`
Currently open positions — replaces `_build_context()`'s `open_trades` query.
```
open_trades: list[OpenTrade]   # ticker, entry_price, lots, tp_price, sl_price — same fields
                                # already queried today, just typed instead of raw rows
```

### `RiskLimits` — genuinely new, closes a real, currently-existing gap
**Today, Agent Firm has zero visibility into Production Engine's own risk-management state.**
Verified directly: `paper_trade.py::is_entries_blocked()` (the drawdown circuit breaker's public
check) exists and is called by Production Engine's own trading logic, but is never queried by, or
passed to, any part of `engine/agent_firm/`. This means the Risk Manager agent can currently approve
new signals while Production Engine's own circuit breaker has already blocked new entries
system-wide — a real, evidenced inconsistency this Context API is designed to close, not merely a
theoretical tidiness improvement.
```
entries_blocked: bool           # from paper_trade.py::is_entries_blocked()
drawdown_pct: float | None      # current realized drawdown, if entries_blocked is True
auth_mode: str                  # informational only — AUTH_MODE, so Agent Firm's own audit
                                 # trail can note what access-control regime was active
```
**Contract:** Agent Firm's Risk agent MUST treat `entries_blocked=True` as at least as strong a signal
as any of its own analysis — the guardrails mechanism (`apply_guardrails`, already deterministic and
post-LLM) is the natural place to enforce "never approve while `entries_blocked`," matching the
existing pattern where deterministic checks override LLM output.

### `SessionState`
```
scan_time: str          # already exists as SignalCandidate.scan_time — no new field, just named
wib_session: str        # "premarket" | "regular" | "post-close" — derivable from scan_time,
                         # currently NOT computed and handed in; agents that care about session
                         # timing today would have to parse scan_time themselves
```

---

## How This Replaces `_build_context()`

Production Engine assembles these six objects (a straightforward query layer, since every field maps
to an existing, already-executed query — this design does not invent new data sources, it types and
relocates existing ones) and passes them into `evaluate`/`evaluate_staged` as part of the call,
instead of Agent Firm reaching into `data.db.connect()` itself mid-evaluation. `MarketContext` and
`PortfolioState` correspond to `_build_context()`'s existing process-level `_market_ctx` cache
(computed once per scan cycle, shared across candidates) — `reset_market_ctx()` remains the correct
lifecycle hook for invalidating them, unchanged from today.

## What This Does Not Change

- `wf_scores` remains research-owned and write-fenced; this design only moves *who executes the read*
  (Production Engine, as part of assembling `RecentHistory`) — it does not grant Agent Firm any new
  write access or change the research/production boundary `CLAUDE.md` already governs.
- No new external data source is introduced — every field above already exists as a query somewhere
  in `_build_context()` or `paper_trade.py` today.
- The `SignalCandidate`/`AgentDecision` contract from `AGENT_FIRM_INTERFACE_SPEC.md` is unaffected —
  this design adds four new *input* objects alongside `SignalCandidate`, it does not change
  `SignalCandidate` itself or the return type.

## Open Item for AF-2 (Named, Not Decided Here)

Whether these six objects are passed as one bundled `EvaluationContext` parameter or as five separate
named parameters to `evaluate`/`evaluate_staged` is an implementation-level API-shape decision, not an
architectural one — left to AF-2, since either choice satisfies every constraint in this document and
the Interface Spec identically.
