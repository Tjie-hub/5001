# SKEL-C-005 — USDIDR × Currency-Exposure, FM Interaction Form (DRAFT SKELETON — CONDITIONAL)

> **Status: DRAFT SKELETON, propose-only, CONDITIONAL on the exposure-classification acquisition (C-005 §3).**
> NOT REGISTERED. No HYP id. No outcome inspected.

**Program:** P-M · Macro-Transmission (new family if taken) · **Candidate ref:** `C-005`
**Mechanism:** FX-regime transmission to USD-exposed cash flows (M3.1/M4.4); FX series verified 2008-12→2026-10
**Era:** 2009-04 → 2026-09 (209 formations, FM pooled)

## Hypothesis
Fama-MacBeth interaction: next-month return ~ β_FX × exposure-classification × USDIDR-Δ(t). The classification
ladder (owner picks ONE before build): (i) 108 USD-reporter flags (ready, coarse); (ii) + revenue-currency
disclosure (acquisition: public filings, ~2 Stockbit calls × 959 tickers, one evening).

## Inference
FM interaction t over 209 months; SE ≈ 0.7%/mo on the interaction → power at 1.0%/mo ≈ 40%, at 1.5%/mo ≈ 75%.
Bar 3.300069; both halves > 0; incremental over E/P/size/vol.

## Stop rule (G0, prior-only)
Power at the pre-registered floor 1.0%/mo ≥ 20% passes by a hair — the honest gate is the classification
quality: if the owner accepts ladder (i), an additional G0 check is required that the 108-flag book is not
simply "large caps" (rank overlap with size < 50%).

## Kill rule (G1)
Interaction t < bar; halves; incremental.

## Data bindings
fx csv @ sha, fin.db @ sha, classification file @ sha + its acquisition log; cost D-082; bar D-064 §C/D-112.
