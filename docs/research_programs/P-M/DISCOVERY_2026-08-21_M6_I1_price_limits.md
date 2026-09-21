# Discovery Record — S1 · M6/I1 price-limit asymmetry and delayed price response

**Date:** 2026-08-21 · **Stage:** S1 Literature Discovery **ONLY** · **Candidate entry:** I1 (no open family)
**Owner:** Claude · **ZCode: not involved; no ZCode file touched; HYP-PM-0002 read-only**
**Governed by:** [[LITERATURE_RESEARCH_STANDARD]] · [[RESEARCH_PROGRAM]] §6.1

> **Decision: CONDITIONAL GO.** One specific barrier must be resolved before registration. No
> hypothesis registered, no family slot consumed, no power computed, no sealed variable inspected,
> no limit-hit event calculated.

---

## 1. Research question

Does asymmetric auto-rejection design create a **predictable delayed market response** after one
side of the trading range becomes constrained — and is the response continuation, reversal, or
neither?

## 2. Search frame (declared before reading, §1.2)

| Element | Content |
|---|---|
| **Target class** | M6 · market design (D1) |
| **Target domain** | D1 primary; D3 (limits to arbitrage) for persistence; D2 for the exploitation channel |
| **Target field** | *Causal chain* — specifically what discriminates a **mechanical** limit effect from an **information** effect |
| **Transportability question** | Does IDX's rule design support the mechanism, and does a **single clean rule regime** exist in the data window? |
| **Exclusion commitment** | Exclude effects with no mechanism (EX1); abstract-only sources (EX7); anything requiring shorting as the capture leg (EX4-adjacent, IDX-infeasible) |

Priority followed (§1.3): **market design (1)** → limits to arbitrage (2) → emerging markets (3) →
microstructure (4). Behavioural not sourced (LR-2).

## 3. Cards created

| Card | Source | Grade | Contribution |
|---|---|---|---|
| **LC-PM-0006** *(amended)* | IDX Trading Mechanism | Q3 | Substrate; **ARB corrected −10% → −15%**; call-auction board exclusion |
| **LC-PM-0007** | Chen/Gao/He/Jiang/Xiong, *J. Econometrics* | **Q4** | The mechanism, account-level, with an ST-assignment natural experiment |
| **LC-PM-0008** | *Rev. Quant. Fin. Acc.* (2024), ChiNext | Q3 | Up/down asymmetry exists **under symmetric bands**; DiD template |
| **LC-PM-0009** | Composite regime reconstruction | Q3 | **Five regimes since 2020**; the R3 symmetric control |
| **LC-PM-0010** | Ma'rifah et al., *Jurnal Ecogen* | Q1 | Only Indonesia-specific study; n=5; uninformative null |

**Coverage of the 12 required areas:** 1 ✅(0007) · 2 ✅(0008) · 3 ✅(0007) · 4 ✅(0007,0010) ·
5 ✅(0008) · 6 ✅(0007) · 7 ✅(0008) · 8 ✅(0007,0008) · 9 ⚠️(0010, Q1 only) · 10 ✅(0009) ·
11 ⚠️ partial · 12 ✅(0007 ST experiment).

**Not obtained:** Kim & Rhee (1997, *JF*) — the foundational price-limit paper — was
**paywalled**; **excluded under EX7** rather than carded from its abstract. Its three hypotheses
(delayed price discovery, volatility spillover, trading interference) reach this record only
second-hand through LC-PM-0008, which tests them directly. **This is the largest gap in the sweep.**

## 4. The two rival mechanisms — and the fact that separates them

```
H_band  IDX band-width asymmetry (−15% vs +20/25/35%)          M6 · rule
        truncated selling pressure clears in a later session
                            ⇅  both predict asymmetric next-session response
H_side  intrinsic up/down asymmetry — shorting constraints,     M5/D3 · behaviour
        sentiment, manipulation, attention                       + limits to arbitrage
```

LC-PM-0008 shows H_side operates **even under symmetric bands** (ChiNext ±10→±20 on *both* sides
still produced opposite up/down effects). LC-PM-0007 shows the asymmetry in China arises from
**short-selling being infeasible** — large investors exploit the upper limit and cannot exploit the
lower one. **IDX shares that constraint.**

So in any single-regime IDX sample the two are **confounded**, and a study would report H_band while
measuring H_side.

**LC-PM-0009 supplies the separator.** IDX ran **symmetric** bands from **2023-09-04 to
2025-04-07** (~19 months, inside the corpus window). Attention, sentiment and manipulation do not
switch off on a decree date. **The band width does.**

| | Across R3 (symmetric) |
|---|---|
| H_band | effect **switches off**, returns in R4 |
| H_side | effect **persists unchanged** |

This is a genuine discriminating test on an exogenous, published, dated switch — and it **supersedes
the regression-discontinuity design proposed and then withdrawn earlier in this session**, which
failed because the running variable (the size of the move) is endogenous to the demand process. A
decree is not.

## 5. Where the executable version is — and is not

LC-PM-0007's headline is **+2.44% close-to-open after an upper-limit hit** (t=20.3), against
**−0.51%** for near-miss 9–10% days that did not hit. The discontinuity is at the **rule**, not the
move. But:

- Capture requires being **filled at the limit close**. At ARA the queue is buyers; a late arrival
  does not execute. The mechanism that creates the effect excludes you from it.
- The subsequent reversal (−1.31% days 21–60) requires **shorting**, which IDX does not practically
  permit.

**On the ARA side the effect is real, large, and un-harvestable in both directions** — structurally
identical to HYP-PA-0001's refuted ADD side.

**The ARB side inverts the execution asymmetry.** At a limit-down the queue is composed of
*sellers*; a buyer supplying liquidity into that wall **can be filled**, and any subsequent reversal
is **upward and long-only**. No card in this sweep establishes that effect — LC-PM-0008 explicitly
notes lower-limit hits are historically data-poor — but that is where an executable version could
exist, and it is the only place in this sweep where mechanism, execution and IDX's constraints line
up in the same direction.

## 6. Decision — CONDITIONAL GO

Distinctness is not in question: **I1 belongs to no open family**, the barrier is M6 (priority 1,
the only priority-1 finding across both sweeps), and there is **no overlap with HYP-PM-0002** in
mechanism, entry, formation variable, or horizon.

**The one barrier that must be resolved first is feasibility, not theory:**

> **Does a clean, single-regime, executable ARB-hit sample exist in sufficient number after
> excluding Papan Pemantauan Khusus, IPO first-days, corporate-action reference-price resets, and
> suspension/UMA events — and can a participant realistically be filled?**

R4 alone (2025-04-08 → present) is ~16 months. R1 (~23 months) is a *different* regime at −7% and
may not be poolable. If the survivable count is a few hundred events concentrated in manipulated
small caps, this is HYP-PA-0001 again with different labels.

**That count is an S2 feasibility task. It was not computed here** — the brief forbids it, and
correctly so: computing it is exactly where discovery would start contaminating confirmation.

## 7. Confirmations

- No inferential DB query · no limit-hit events calculated · no OFI, `cont_k`, returns or price
  responses computed · no power analysis · no sealed variable inspected
- No hypothesis registered · no family slot consumed
- `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `HYP-PM-0002_*` — **unmodified**
- No backfill launched · no ZCode file touched · no production code touched

**Files created:** `LC-PM-0007` … `LC-PM-0010`, this record.
**Files amended:** `LC-PM-0006` (ARB correction, amendment recorded in-card, original error
preserved in the amendment note).
