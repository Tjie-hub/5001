# SHOCK→ABSORPTION→CONTINUATION — FEASIBILITY REPORT (2026-09-21)

**VERDICT: DEAD (null)** — per the frozen bar in FEASIBILITY_SPEC §5 (`cd0cd0a`): the h=20
excess vs the EW-book is **−1.95% with cluster-t = −1.73**, far below the required ≥ +2; the
pattern as formalized does not predict positive continuation. Nothing is built; no recorder,
no registration, no slot consumed.

**Secondary observation (stated, not pursued):** at the pre-committed horizons the excess is
significantly **NEGATIVE** — h=5 −1.77% (t −3.76), h=10 −2.22% (t −3.28), both vs the EW-book;
IHSG-benchmark reads agree (−1.41% t −2.85; −1.65% t −2.25). Post-shock top-broker-accumulation
names *underperform* the liquid book: the formalization behaves as an anti-edge (FADE-class),
the mirror of the trader narrative. This is one exploratory pass; pursuing the negative
direction requires a **new dated spec** with an independent rebuild and this count carried as
multiplicity debt. Nothing is registered from this document.

## 1. Census

| quantity | value |
|---|---|
| qualifying up-shocks (≥ +10%, ≥Rp50, ≥25 sessions, 2025-01-02→) | 7,426 |
| shocks with absorption marker (`top1` ≥ Normal Acc within 3 sessions) | 1,108 (14.9%) |
| distinct entry dates | 216 |
| entry-tail (marker fired, entry not yet printed) | 4 |
| h=20 legs valid / tail-pending / voided (contamination) | 951 / 127 / 13 |

Concentration: top ticker ALKA = 14 events (1.3%); top-5 (ALKA, LINK, BRMS, RAJA, KONI) =
5.2%. Not a single-name effect.

## 2. Sanity anchors (spec §6)

- **SMMT**: five events fired from its April–June 2026 shocks (2026-04-24→04-27 marker,
  04-27→04-28, 05-22→05-26, 06-09→06-12, 06-19→06-22) — the machinery detects the pattern
  when bandar rows exist. Its Sep-16 shock (+15.67%) is **data-limited**: SMMT has a bandar
  row on 09-16 (top1 = Big Acc, ON the shock day — excluded by the strictly-after window by
  design) and no rows on 09-17/09-18 (data end), so no marker could be evaluated.
- **TUGU**: shock Sep-16 (+12.03%) likewise **data-limited** — no bandar rows after 09-16
  (last row: 09-16 = Big Dist), pre-stated in §6. Its pre-shock accumulation (Big Acc
  09-10/11/14) is visible in the event attributes via the pre-shock flag where events fired.

## 3. Per-horizon table (excess vs both benchmarks, net 0.60% RT, next-open convention)

| h | N | dates | exc vs EW-book | t | exc vs IHSG | t |
|---|---|---|---|---|---|---|
| 5 | 1,042 | 208 | −1.769% | −3.755 | −1.410% | −2.852 |
| 10 | 1,021 | 204 | −2.224% | −3.277 | −1.649% | −2.245 |
| 20 | 951 | 198 | −1.952% | −1.727 | −0.636% | −0.521 |

## 4. Pre-declared descriptive splits (attributes, never gated)

**adv20 tier** (mean excess vs EW-book):

| tier | n | h=5 | h=10 | h=20 |
|---|---|---|---|---|
| < Rp1bn | 439 | −1.51% | −1.45% | +1.38% |
| Rp1–5bn | 242 | −2.37% | −2.13% | −2.94% |
| Rp5–20bn | 168 | −2.09% | −3.43% | −4.99% |
| ≥ Rp20bn | 259 | −1.47% | −2.83% | −4.39% |

The negative read is strongest in the *liquid* tiers — the opposite of a small-cap-only
artefact. Only the <1bn tier's h=20 turns mildly positive (+1.38%).

**pre-shock accumulation flag** (top1 ≥ Normal Acc within 5 sessions before the shock):
False (n=294): h5 −1.99% / h10 −2.34% / h20 −4.30%; True (n=814): −1.69% / −2.18% / −1.08%.
The TUGU-style pre-shock-accumulation configuration is *less* negative — but negative
everywhere.

**VPIN at marker** (564 of 1,108 events have coverage, marker ≥ 2026-06-05): LOW (n=159)
h5 −2.21% / h10 −3.29%; HIGH (42) −2.18% / −4.50%; TOXIC (207) −1.96% / −2.51%; MODERATE
(156) −0.60% / −0.06%. The anecdote's "VPIN HIGH→LOW drop = healthy absorption" reading is
not supported: LOW-label markers are among the most negative. Stage 2 stays descriptive per
spec §4.

## 5. Honest limitations

1. One pass, executed in the main session (the cold-session subagent backend was unavailable —
   `model-not-found`; disclosed at firing). Integrity rests on the pre-committed thresholds of
   the frozen spec, all honored: no parameter was changed after the run started; the only code
   fix after the first write was the Mimosa-required path derivation (absolute → `__file__`
   relative), before any run.
2. Broker history is 21 months, one market slice; bandar rows depend on the daily stockbit
   fetch — missing rows narrow marker windows silently (Sep-16 anchors), never imputed.
3. The negative-sign observation at h=5/h=10 is exploratory: it carries this session's
   multiplicity and would need the independent-rebuild treatment FADE received before any
   registration.
4. Benchmarks use the FADE liquid book; event universe is ungated by design (spec §3), so
   small-cap events are measured against a liquid-book bar — a conservative choice for a
   *positive*-claim test, and if anything it understates the negative read's breadth across
   tiers (§4).

## 6. Deliverables

- `scripts/feasibility_count.py` (read-only, one pass, this run)
- `results_2026-09-21.json` (all 1,108 events + summary + verdict)
- this report

Routing honored per spec §5 / Owner option A: DEAD → report only; **no recorder, no ledger,
no registration.**
