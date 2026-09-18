# Tradeability Re-run — the volatility overlay survives; one prior conclusion is withdrawn

**Date:** 2026-09-18 · **Scripts:** `scripts/{trade_panel,trade_rerun,trade_idx80}.py`
**Trigger:** `factor_zoo/ZCODE_REVIEW_V1.md` A-5 — rows that are *present but
untradeable* were invisible to every robustness test run so far. The review's
deferred observation warned the same exposure underlies this volatility work.

## 0. Result

**The overlay survives, and improves.** Its published increment was +0.287%/mo
(t 3.59); on a fully tradeability-conditioned panel it is **+0.291%/mo (t 4.39)**.
Unlike the 52-week-high book — which collapsed from +1.40%/mo (t 2.95) to
+0.88%/mo (t 2.15), with 95.6% of its positions averaging +0.14%/mo — this result
is not an artefact of frozen prints.

**But one prior conclusion is withdrawn:** the claimed advantage at the illiquid
end was itself contamination. See §4.

## 1. Three contamination flags, kept separate

They act through different mechanisms and must not be conflated:

| flag | meaning | rate |
|---|---|---|
| `frz_form` | zero-volume session inside the 60-day formation window — the volatility estimate is built on untradeable prints | 9.18% |
| `frz_fwd` | zero-volume session inside the 21-session forward window — the return could not have been earned | 2.89% |
| `susp` | inside a `suspension_events` episode | 1.70% |
| **CLEAN** | none of the above | **87.53%** |

Contamination is heavily concentrated in exactly the decile the overlay removes:

| park60 decile | frz_form | median park60 |
|---|---|---|
| D1 | 2.02% | 21.0 |
| D5 | 3.65% | 46.8 |
| D9 | 18.69% | 87.3 |
| **D10 (excluded)** | **31.89%** | 112.6 |

Nearly a third of the excluded names have trading gaps inside their own formation
window. That is why the test was necessary.

## 2. The overlay under each condition

| panel | incr %/mo | t | P(>0) | ann |
|---|---|---|---|---|
| as published (all rows) | +0.287 | 3.59 | 73% | +3.45% |
| drop `frz_fwd` only | +0.399 | 5.69 | 80% | +4.79% |
| drop `frz_form` only | +0.148 | 1.78 | 63% | +1.77% |
| drop suspensions only | +0.298 | 3.69 | 74% | +3.58% |
| **CLEAN (all three)** | **+0.291** | **4.39** | 66% | **+3.49%** |
| CLEAN + tradeable-price exit | +0.291 | 4.39 | 66% | +3.49% |

`frz_form`-only looks weak, but that filter deletes ~32% of the treatment group
— it removes the very tail the overlay targets, so it is not a fair test in
isolation. The CLEAN row applies all filters uniformly to the whole universe
before the overlay runs, which is the correct construction.

Decisively: **the excluded decile still underperforms on clean data**, −2.59%/mo
(t −4.39) versus −2.56%/mo (t −3.60) as published. High measured volatility
predicts underperformance among names that traded every day. The effect is not a
suspension artefact.

## 3. Era and asymmetry, CLEAN panel

| split | incr %/mo | t |
|---|---|---|
| 2021-2023 | +0.349 | 3.43 |
| 2024-2026 | +0.241 | 2.75 |
| **EX-2025** | **+0.293** | **3.92** |

Every era holds, and ex-2025 is *stronger* than the pooled published figure.
Exclusion-fraction plateau is intact: 5% t 4.33, 10% t 4.39, 15% t 4.14, 20% t 3.16.

**Correction to a published claim.** The parent findings stated the effect was
entirely defensive — up months −0.072%/mo (t −0.65). On clean data up months are
**+0.156%/mo (t 1.67)**, down months +0.417%/mo (t 4.67). Still strongly
asymmetric, but the "costs you money in rising markets" framing was a
contamination artefact and is withdrawn.

## 4. WITHDRAWN — the illiquid-end advantage

The parent findings reported that the effect was strongest and non-decaying at the
illiquid end ("least-liquid 200: +0.297%/mo, t 3.43, 2025 +0.463, 2026 +0.403")
and recommended opening a second forward test there.

On clean data that reverses. Full history, ADV terciles, CLEAN only:

| tercile | incr %/mo | t | ann |
|---|---|---|---|
| top ADV (IDX80-like) | +0.096 | 0.83 | +1.16% |
| **mid ADV** | **+0.447** | **4.59** | **+5.37%** |
| bottom ADV | +0.143 | 0.99 | +1.71% |

**The edge lives in the middle liquidity band.** The bottom tercile carries the
highest contamination rate, and once it is removed the apparent illiquid advantage
disappears (t 3.43 → 0.99). **The recommendation to open a less-liquid forward
test is withdrawn**; the defensible target is mid-ADV.

## 5. IDX80 — the failure is real, not contamination

| universe | as published | CLEAN |
|---|---|---|
| IDX80 | −0.286%/mo (t −0.98) | **−0.320%/mo (t −1.25)** |
| non-IDX80 liquid | +0.467%/mo (t 3.35) | **+0.371%/mo (t 4.13)** |

IDX80 is **99.34% clean** already (frz_form 0.54%), so contamination was never a
candidate explanation for its failure. The IDX80 addendum's conclusion stands
without revision.

## 6. What still needs re-running

This closes the volatility leg only. Still outstanding under the same conditioning:
- the fundamentals addendum (`factor_zoo/FUNDAMENTALS_ADDENDUM`) — its null results
  are probably robust to this, since contamination inflates rather than suppresses,
  but they have not been checked;
- the 002 forward-regime evidence, which shares the panel and the `shift(-21)`
  convention and whose ledger is live;
- the pattern-scan arms.
