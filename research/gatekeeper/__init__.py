"""Phase C — Statistical Gatekeeper (design: docs/superpowers/specs/
2026-07-12-phase-c-statistical-gatekeeper-design.md).

A mandatory, deterministic, reproducible statistical promotion gate. Every strategy
runs through an 8-stage pipeline and receives exactly one of REJECT / WATCHLIST /
PROMOTE_TO_FORWARD_TEST. The gate makes NO production-deployment decision and never
writes the edge registry — it emits evidence + the frozen forward-test rule.

Research-domain only: writes only research tables (gate_decisions, gate_evidence)
and a results doc; all statistics delegate to research.statistics (Phase B).
"""
