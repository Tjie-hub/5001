# SKEL-C-006 — KSEI Mutual-Fund/Pension Share and Δ (DRAFT SKELETON)

> **Status: DRAFT SKELETON, propose-only. NOT REGISTERED. No HYP id.** No outcome inspected.

**Program:** P-M · same family decision as SKEL-C-001 · **Candidate ref:** `C-006`
**Mechanism:** mandate-driven custody flows (M4.4): (L_MF+L_PF+F_MF+F_PF)/total share and 1-m Δ
**Era:** 2009-04 → 2026-09 (209 formations)

## Hypothesis
Q5−Q1 monthly net spread (A1m) and Δ-tercile spread (A2m) vs the EW liquid book; sign fixed at registration
(mandate-flow persistence vs redemption-overhang).

## Universe / inference / kill
Identical to SKEL-C-001 (top-200 KSEI mcap, ADV ≥ Rp 1bn, bar 3.300069, NW t, both halves, FM incremental over
the same stack).

## Stop rule (G0)
Same floor condition as SKEL-C-001 (≥ 0.80%/mo owner-accepted, else do not run). One G0 event shared with
SKEL-C-001; each arm counts separately in the census ({OC} precedent).

## Data bindings
KSEI csv @ sha; MF/PF bucket density must be counted at build (schema verified present; density is a coverage
check, allowed pre-outcome).
