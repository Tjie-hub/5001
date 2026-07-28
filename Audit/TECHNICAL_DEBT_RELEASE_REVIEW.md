# Production Engine — Technical Debt Release Review

**Date:** 2026-07-28
**Scope:** Phase 6 of the final release certification — TODOs, FIXMEs, HACKs, debt allowlists,
ADRs/decision records, open issues, in the production code scope (`scheduler/`, `engine/`,
`forward_testing/`, `data/`, `screener/`, `routes/`, `app.py`, `monitor.py`, `paper_trade.py`,
`config.py`, `security/`, `scripts/`, `deploy/`) — deliberately excluding `research/`'s own separate,
already-mature governance corpus per that corpus's own documented review discipline.
**Method:** One dedicated adversarial fork, exhaustive grep-based catalogue, direct reading of every
debt allowlist's justification comment.

---

## Result: Zero Must-Resolve Items

No `TODO`/`FIXME`/`XXX`/`HACK`/`NotImplementedError`/disabled (`if False:`) code exists anywhere in
the full production scope — verified by direct grep, zero hits, corroborating (not merely repeating)
`CLAUDE.md`'s own claim. No canonical doc (`docs/OPERATIONS.md`, `docs/SECURITY.md`) admits an
unresolved "not yet implemented" gap in prose either. The debt inventory in production scope is
small, entirely bounded, and every entry carries a dated, specific justification tying it to a named
workstream or incident.

## Safe After Release — Inventory

1. **`_ROUTES_DEBT`** (`tests/test_architecture_boundary.py`) — 4 entries (`routes/backtest.py`,
   `routes/screener.py`, `routes/portfolio.py`, `routes_backtest_multi.py`), capped and shrink-only
   CI-enforced. Justification comment names the specific audit (R-2, Phase A) that surfaced them and
   states retirement is a deferred routing redesign. Bounded: any *new* violation still fails CI.
2. **`_ROUTES_WRITE_DEBT`** (`tests/test_research_data_fence.py`) — single entry
   (`routes/backtest.py`), same audit, same shrink-only enforcement.
3. **`_LIFECYCLE_DEBT`** (`engine/registry_loader.py`) — single entry `("NR7_BULL", 1)`, dated
   "APPROVED 2026-07-04" — the sole, documented R-10 receipt-bound registry lifecycle exception
   `CLAUDE.md` itself names.
4. **`_STATUS_DEBT`** (`research/knowledge/storage.py`) — under `research/`'s own separate,
   already-mature debt system; explicitly out of this review's assigned scope.
5. **Provider-hold state is process-local** (`docs/OPERATIONS.md`) — a documented design tradeoff,
   not a bug: worst case is a self-healing re-probe, with an explicit kill switch
   (`AGENT_FIRM_QUOTA_HOLD=false`). Part of the separate, already-known-excluded agent-firm
   quota-governor workstream, not an RC1 gap.
6. **Conditional `pytest.skip()` calls** (`tests/test_signal_checkers.py`) — all guarded by a real
   production-DB-availability check; opportunistic data-quality tests that correctly no-op in CI/fresh
   checkouts. No `@pytest.mark.skip`/`@pytest.mark.xfail` decorator exists anywhere in `tests/` at
   all — every skip in the repo follows this same self-explanatory pattern.
7. **`engine/strategy_registry/`** — not merely empty as `CLAUDE.md` states; the directory no longer
   exists at all (confirmed via `engine/strategy_specs.py`'s own note that it was deleted). No import
   references it anywhere. Better than documented — a stale wording gap in the doc, not a real issue.

## Must Resolve Before Release

**None found.**

## Items Surfaced Elsewhere in This Certification That Are Technical-Debt-Adjacent

These are tracked in `Audit/PRODUCTION_READINESS_REPORT.md` and `Audit/SECURITY_REVIEW_REPORT.md`
rather than here, since they're concrete defects/gaps rather than acknowledged, dated debt:
the `TELEGRAM_WEBHOOK_SECRET` fail-open gap (P0), the uncommitted token-hardening workstream
(P1, security), the redaction structural gaps (P1, security), and the several scheduler/monitoring
P1s. None of these carry a dated justification comment the way the items above do — they are
previously-unknown gaps this certification surfaced, not pre-acknowledged debt.

## Explicit Coverage Gap

GitHub Issues content was not checked — the reviewing fork had no `gh` CLI access and was instructed
not to guess. This is named as an explicit gap in this review's own coverage, not asserted clean.

## Conclusion

The debt inventory itself is not a release blocker by any measure — every item is bounded,
dated, shrink-only enforced where applicable, and consistent with the discipline `CLAUDE.md`
documents elsewhere in this repository's governance model.
