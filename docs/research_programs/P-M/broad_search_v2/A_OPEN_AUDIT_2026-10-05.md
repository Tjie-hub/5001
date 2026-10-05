# A-OPEN audit (REVIEW_R1 §2.2) — local legs + blocked leg · 2026-10-05

Driver: `a_open_audit.py` (this directory); machine record `a_open_audit.json`; local corpus
`D:\IDX\data\walkforward.db` (read-only, ends 2026-07-29), window 2024-01-01 → 2026-07-29,
556,229 name-days with a trailing gap-σ.

## Leg 3 (the decisive leg) — BLOCKED ON THIS HOST

`data/frozen/stockbit-flow-bars-v002/` on tjiejet contains **only MANIFEST.json** (store pin
`fa7f07b3…`, 7.8 GB, window 2025-01-02→2026-04-28, 77.5M minute rows); the store file itself was
built on the production host and DBs do not sync to this machine. The daily-open vs first-minute-
print comparison therefore **cannot run here**. Options for the reviewer: run `v_e_minute_sequence`
on the host that holds the store, or ship the store over Twingate. This is the one open item for
R2 GO on the audit.

## Leg 1 — model check (§2.2): the discreteness signature is confirmed directionally

Predicted P(open = prev_close) from tick/price and trailing 20-day gap σ (Gaussian first-order
model: 2Φ(tick / (2·prev_close·σ_gap)) − 1), vs observed, by price bucket:

| price bucket | n | observed unchanged | predicted | median tick/price |
|---|---|---|---|---|
| < 200 | 259,260 | **60.8%** | 48.4% | 1.32% |
| < 500 | 110,976 | **51.1%** | 30.9% | 0.64% |
| < 2000 | 119,156 | **49.4%** | 29.8% | 0.56% |
| < 5000 | 39,264 | **43.9%** | 19.8% | 0.35% |
| ≥ 5000 | 27,573 | **45.8%** | 23.7% | 0.31% |
| all | 556,229 | 54.5% | 37.7% | — |

**Reading.** The observed unchanged-open rate falls monotonically with tick/price exactly as
discreteness predicts (60.8% → 43.9% as median tick/price falls 1.32% → 0.31%), and the model
reproduces the gradient (48.4% → 19.8%). The model's LEVEL underpredicts by ~17pp overall — a
first-order Gaussian diffusion cannot know that the pre-opening call auction clears AT the
reference price when order imbalance is small (price clustering at the previous close), which
raises the unchanged-open probability above the diffusive benchmark. This is the reviewer's
"IDX price discreteness plus the pre-opening call auction clearing at the previous close"
signature; nothing in it points to a fill artifact. GOTO's 66% at a 1.5%-per-tick price is the
extreme case the gradient predicts.

## Leg 2 — corpus vs yfinance opens (same window; NOT independent, recorded for continuity)

10 mega/large caps, 592 common sessions each: corpus open = yfinance open on **97.8–98.3%** of
cells (BBCA 98.3, TLKM/BBNI/BBRI/ADRO 98.1–98.3, ANTM 98.0, ASII 97.8) — consistent with the
reviewer's production check (95.2–100%). Both series are yfinance-sourced via `data/fetcher.py`,
so this is a pipeline-consistency check, not independence.

## Disposition

- The reviewer's ruling stands: opens are genuine (discreteness + auction clearing), the
  "degraded corpus" claim is **withdrawn**, and the valid-open row filter stays **rejected**.
- X1's predeclaration uses the §2.3 ex-ante eligibility rule (tick(close_d)/close_d ≤ 0.5%
  computed at close(d)) with the all-rows estimate as a co-equal lens — this is robust to either
  outcome of the pending minute-bar leg.
- The minute-bar leg is handed to the reviewer (see blocked-leg note above). If the store
  disagrees with the daily opens, everything stops and escalates per §2.2.
