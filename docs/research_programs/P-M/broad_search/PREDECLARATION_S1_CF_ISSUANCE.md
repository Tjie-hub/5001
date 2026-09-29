# PREDECLARATION — S1 `{CF}` issuance-avoidance screen (SCREEN-PM-CF-001)

**Status:** frozen before any outcome is computed · **Date:** 2026-09-29 ·
**Authority:** brief `ZCODE_BRIEF_BROAD_EDGE_SEARCH_2026-09-29.md` (screens only; no registration,
no family slot, no DECISION_LOG/registry edits). One run. Every cell of the pre-declared grid is
reported; the verdict is the pre-declared primary cell only. **This file and `screen_s1_issuance.py`
are committed (with this file's sha256) before the run.**

## Rule (pre-declared)

Avoidance screen: after an equity-issuance announcement, does the name underperform the equal-weight
liquid book? Two pre-declared event definitions:

- **RI (primary def):** a rightissue record, flagged on the ticker's FIRST own session strictly
  after `rightissue_created` (announcement stamp; known at that close).
- **RUPS (coarse proxy def):** a rups (AGM/EGM) record flagged the same way on `rups_created` —
  37% of rights issues are preceded by a rups within 12 months; agenda content is empty, so this
  arm is the "meeting announced" proxy, not an approval signal.

Defects dropped and counted: events with announcement stamp outside [2013-01-01, 2026-09-16]
(program cutoff); events whose ticker has no panel row after the stamp; duplicate flags on the same
ticker-day collapse to one flag (event count recorded). **FORU excluded entirely from 2026-09-14
onward** (D-063; unconfirmed ×19.5 corporate action).

## Universe (pre-declared)

Flag row must satisfy the engine's ex-ante liquid gate (`liquid_idx_v1`) **and** trailing adv20 at
the flag row ≥ **Rp 5bn** (brief rule 5 primary universe; the adv20 is computed on the
wealth-corrected panel — deviation from raw is bounded by the event's own adjustment factor and
declared). The benchmark book is the engine's EW liquid book (adv20 ≥ Rp 1bn) — never IHSG (BM-1).
Low-ADV flagged events are excluded from cells by construction and counted (fingerprint, not arm).

## PIT date fields (pre-declared)

`rightissue_created`, `rups_created`. Phase-0 audit: 100% present; weekend stamps 0.3%/0.0%
(such stamps land on the next own session by the flag rule); created-after-ex-date stamps (10.7% of
RI) only *delay* a flag — no look-ahead path exists. No ex-date, cum-date or effective date enters
any flag or entry.

## Price handling — the mechanical ex-drop (brief rule 4)

The panel is split-adjusted at source but NOT adjusted for rights/bonus/reverse splits. The screen
therefore runs every cell twice on the same flags:

- **CORRECTED (primary lens):** the panel is wealth-corrected at every issuance-type ex-date of
  every held ticker: all rows strictly before the ex-date are multiplied by
  `φ = P_ex/(m·P_ex − c)`, with `m = 1 + ratio_new/ratio_old` and `c = (ratio_new/ratio_old) ×
  subscription_price` from the event's own `raw_json` (bonus: c=0, m=factor; reverse: m=factor<1,
  c=0; splits: skipped, already adjusted at source). Corrections are **gap-verified** (applied only
  when the raw series shows the mechanical jump; each application listed in the run's audit, mirroring
  `adjust_unadjusted_splits` / `repair_db_splits`). The corrected panel drives features, eligibility,
  positions and book alike — one coherent price basis.
- **RAW (observability lens):** the uncorrected panel — the mechanical-drop-distorted upper bound
  on the negative, reported beside the primary, gating nothing.

Ex-date window exclusion (the brief's alternative estimate) is not run as a separate arm: the
corrected lens supersedes it because it uses each event's own terms. **FORU from 2026-09-14 is
excluded before corrections; it has no usable event terms.**

## Estimand, benchmarks, horizons, split (pre-declared)

- Engine: `research/rulecard/events.py` (D-060) via `run_event_months` — next-own-session-open entry,
  fixed own-session hold, day-weighted calendar-time monthly excess vs the EW liquid book.
- Monthly excess series per cell: primary statistic = mean / SE (ddof=1) of the valid months'
  `primary` values (the engine's day-weighted monthly excess, in %/mo). Per-date mean daily excess
  is reported beside it (brief rule 7: headline the per-date mean). The calendar-time series has no
  overlapping-window dependence (audit R-1); no additional clustering is applied.
- **Benchmarks: EW liquid book (all cells) and IHSG (confirmation half only — the corpus has no
  pre-2021 IHSG series; declared).** vs-IHSG monthly excess = sleeve monthly return − IHSG monthly
  return over the same months, reported as observability, gating nothing (R4b).
- Horizons: **hold_sessions ∈ {126, 252}** own sessions (≈6m / 12m; MPW's post-issuance drift is a
  12-month phenomenon; two horizons is the brief's maximum).
- **Split (pre-declared by the brief): entries strictly before 2021-07-05 = discovery-as-replication
  half; entries on/after 2021-07-05 = confirmation half.** The ex-2025 split is NOT used here.

## Grid (every cell run and reported; each cell = one arm; 8 arms)

2 defs (RI, RUPS) × 2 holds (126, 252) × 2 halves (pre-2021, 2021+) = 8 cells, all on the
CORRECTED panel. The RAW lens is reported inside the same 8 arms (not extra arms). Net-of-cost
observability at the frozen 0.60% round trip and D-059-modeled-cost qualitative reading via the
engine's adv-tercile cells ride inside the same arms. Engine checks run per cell: FILL-1 (order),
ID-1 (non-degenerate). Placebo/random instrumentation runs **only if** the primary cell is read
positive (D-061 precedent).

- **PRIMARY CELL: RI · hold 252 · confirmation half (entries ≥ 2021-07-05) · CORRECTED · gross.**
- Pre-declared sign: **negative** (issuers underperform).

## Verdict rule (pre-declared)

- Primary cell readable only if it has ≥ **48 valid months** (engine validity) — otherwise the
  screen closes **NOT TESTED — UNDERPOWERED**, no slot consumed (RC-0002 precedent).
- If readable: **screen PASS** requires two-sided |t| ≥ **2.86** on the primary monthly series —
  the recomputed full-census bar: N = 252 disclosed trials + 14 arms from this brief = 266;
  E[max|Z|] = (1−γ)·Φ⁻¹(1−1/266) + γ·Φ⁻¹(1−1/(266·e)), γ = 0.5772 ⇒ **2.857** — AND the point
  estimate negative AND the discovery-as-replication half (RI · hold 252 · pre-2021) carries the
  same sign if it has ≥ 12 valid months. If the discovery half has < 12 valid months, the maximum
  verdict is **EFFECT_CONFIRMATION_ONLY** (handed to the owner, never promoted). t < bar ⇒
  **screen FAIL (null)**; the `{CF}` issuance lead closes at screen level; re-open is a new screen id.
- **Stop rule (brief rule 11):** if the primary passes — stop, no variants, no refinement; write
  the verdict and hand it to the Owner.
- A PASS is a recommendation to draft a Rule Card; registration stays an Owner decision, and the
  D-062 standing directive (nothing correlated with an in-flight forward test) applies to any such
  proposal.

## Power statement (before the run, from event counts alone — R5 honesty)

D-056 noise floor on this panel: decile σ ≈ 6.5%/mo, quintile ≈ 4.6%/mo; an event sleeve is
comparable or thinner. At N = 120–145 valid months the two-sided MDE at the bar is ≈ 1.6–2.0%/mo;
at N = 48–70 it is ≈ 2.4–3.0%/mo. The US-calibrated, haircut effect (MPW ≈ −8%/yr top-minus-bottom
decile [M] ⇒ issuer-vs-rest ≈ −0.3%/mo × 0.5 decay) is **an order of magnitude below the MDE**: the
formally expected verdict of a true US-sized effect is NULL. The screen is run because IDX rights
issues are dilution *events* (median factor 1.43, deep discounts) whose per-event magnitude
plausibly exceeds US composite issuance, and because a pre-declared null closes the family cheaply.
This statement is part of the frozen record; neither outcome may be read as surprising.

## Falsification note

This is the map's rank-1 family: strongest published prior, cleanest PIT, best event density. A
null here — under the census bar, on the corrected lens — closes corporate-finance issuance
avoidance for this program and hardens the no-tradeable-edge record.
