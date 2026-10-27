# SKEL-C-003 — Dividend-Yield Level as a Payout-Commitment Risk Premium (DRAFT SKELETON)

> **Status: DRAFT SKELETON, propose-only. NOT REGISTERED. No family slot consumed. No HYP id assigned.**
> Prepared without inspecting any return outcome; every number is a coverage count, a pre-existing published
> result (alpha_search_v2, disclosed as multiplicity debt), or a power arithmetic from the frozen cost/bar
> authorities. Registration belongs to the owner.

**Program:** P-M · (family TBD by owner: widen {FQ} or open Payout) · **Candidate ref:** `search/cand/C-003`
**Mechanism:** standing payout commitment (tax/agency + liquidity-level premium), monthly rank
**Era:** 2009-04 → 2026-09 (KSEI-complete panel; 209 formations)

## Hypothesis (sign fixed at registration)
Top-quintile trailing dividend yield (TTM dividends-paid / month-end price, PIT: only ex-dates/statements
available before t under D-111 v3) earns a positive net monthly spread over the EW liquid book.

## Universe / formation
Top-200 by KSEI market cap at t; ADV ≥ Rp 1bn (D-081); monthly close-to-close; net D-082 cost_realised on
turnover; long-only top quintile (~40 names).

## Bar and inference
|Z| ≥ 3.300069 (census 613 + this arm); one-sided NW t on 209 monthly formations; both halves > 0;
FM incremental over E/P, log-size, Parkinson-60, VOLEX (t ≥ 2).

## Stop rule (G0, prior-only, no outcomes)
G0 computes coverage + power only: (i) dividends-paid line coverage ≥ 60% of panel name-months; (ii) power at
the pre-registered floor 0.80%/mo ≥ 80% (expected ~0.22–0.30%/mo SE → passes); floor below 0.60%/mo or coverage
failure → stop, uncounted.

## Kill rule (G1, single run)
t < bar; either half ≤ 0; FM-over-E/P incremental t < 2 (re-labelled value → dead as a separate claim).

## Data bindings (to freeze at registration)
fin.db @ sha (post-{FQ} pull; sums file), KSEI csv @ sha, prices fingerprint, dividends extraction script sha,
cost authority D-082, bar authority D-064 §C/D-112.
