# Discovery Record — S1 · Short-horizon flow-conditioned price response

**Date:** 2026-08-21 · **Stage:** S1 Literature Discovery **ONLY** · **Program:** P-M · Microstructure Flow
**Owner:** Claude (discovery/literature task) · **ZCode: not involved; no ZCode file touched**
**Governed by:** [[LITERATURE_RESEARCH_STANDARD]] · [[RESEARCH_PROGRAM]] §5 (intake) · §6.1 (admissibility)

> **Status: no hypothesis registered. No family slot consumed. No power computed. No sealed variable
> inspected.** This record exists to make the S1 sweep auditable and to carry a **NO-GO
> recommendation** on the mechanism as framed.

---

## 1. Research question as posed

Does a **new** order-flow-conditioned price-response edge exist at a **shorter horizon** than
HYP-PM-0002 — next session, or 1–3 trading days — under candidate mechanism class **M2.x** (signed
order-flow imbalance → subsequent price response), and is it distinguishable between
**(A) immediate continuation**, **(B) short-horizon reversal**, and **(C) short-horizon persistence**?

## 2. Search frame (declared before reading — §1.2)

| Element | Content |
|---|---|
| **Target class** | M1 (inventory) and M2 (information) at daily-and-shorter horizon |
| **Target domain** | D2 microstructure; D3 limits to arbitrage; D1 market design |
| **Target field** | *Causal chain* and *competing explanations* — specifically, what discriminates A from B |
| **Transportability question** | Does the constrained participant class each mechanism names **exist on IDX**? |
| **Exclusion commitment** | Exclude any source reporting flow→return predictability with no mechanism (EX1); any US-specialist-dependent mechanism with no order-driven analogue (EX4-adjacent); any source obtainable only as abstract (EX7) |

**Search priority followed** (§1.3): market design (1) → limits to arbitrage (2) → emerging/
constrained markets (3) → microstructure (4). Behavioural (6) deliberately not sourced (LR-2).

## 3. Cards created

| Card | Source | Grade | Horizon | Market | Structure |
|---|---|---|---|---|---|
| LC-PM-0001 | Chordia & Subrahmanyam (2004) JFE | Q4 | **1–5 d cont.; 6–10 d rev.** | NYSE 1988–98 | specialist |
| LC-PM-0002 | Hendershott & Menkveld (2014) JFE | Q4 | **half-life 0.92 d** (small-cap 2.11) | NYSE 1994–05 | specialist |
| LC-PM-0003 | Andrade, Chang & Seasholes (2008) JFE | Q4 | **weekly+** | Taiwan 1994–02 | **order-driven, retail** |
| LC-PM-0004 | Kaniel, Saar & Titman (2008) JF | Q4 | **5–20 d** | NYSE 2000–03 | specialist |
| LC-PM-0005 | Nagel (2012) RFS | Q4 | 5-day overlay | US 1998–2010 | de facto providers |
| LC-PM-0006 | IDX Trading Mechanism (2026) | Q3 | — | **IDX** | **order-driven, NO DMM** |

Coverage against the nine required areas: 1 ✅ (0001) · 2 ✅ (0001) · 3 ✅ (0003, 0005) · 4 ✅ (0001,
0002) · 5 ✅ (0002 — the state-space decomposition) · 6 ✅ (0003 Taiwan; **no IDX-specific
peer-reviewed flow study located** — see §7) · 7 ✅ (0003 cross-stock) · 8 ✅ (0005 bounce; all cards
carry cost notes) · 9 ✅ (0002 is the canonical separation).

## 4. What the literature actually says about A vs B vs C at 1–3 days

**It says the question is not answerable at PROXY fidelity, and this is the central finding.**

Two mechanisms operate simultaneously inside the proposed window, with opposite signs:

```
  permanent component  ──── continues ────────────────────────►   (I7 / M2.1)
  transitory component ──── decays, half-life 0.92 d ────►        (I5 / M1)
                            └── large-cap 0.54 d · small-cap 2.11 d
  observed 1–3 d return = SUM of both
```

LC-PM-0002 identifies the two **only because it has proprietary end-of-day specialist inventory**.
Without an inventory observable, a signed-flow → forward-return statistic at k ∈ {1,2,3} measures
their **sum**, whose sign is uninformative about which mechanism produced it. That is **LIM2 exactly**
— the confound that forced the I5↔I7 family merge (D-028) and capped both prior P-M hypotheses at
causal-argument-not-identification.

Compounding this, the horizons in the literature **do not point at 1–3 days**:

- LC-PM-0001 continuation runs to 5 days — **but vanishes once contemporaneous imbalance is
  controlled**, i.e. it is largely same-day displacement observed with a lag.
- LC-PM-0003 (the only order-driven, retail-dominated source) establishes **weekly and longer**, not
  1–3 day.
- LC-PM-0004 establishes **5–20 days**.
- LC-PM-0005's reversal is **conditional on a stress state variable** IDX has no analogue for.

**No Q3+ source in this sweep establishes a flow-conditioned effect at 1–3 days in a market
structurally comparable to IDX.**

## 5. The transportability wall (LC-PM-0006, Fact 1)

Three of the five academic cards locate the constraint in a **designated** intermediary — the NYSE
specialist. **IDX has no designated market maker.** Under R9, a mechanism whose named participant
class does not exist in the target market is not transported at reduced magnitude; **it is not
transported at all.** Only LC-PM-0003 and LC-PM-0005 specify the mechanism in a form that survives.

## 6. Distinctness from HYP-PM-0002 — the decisive test

Read directly from `HYP-PM-0002_DRAFT.md`:

| | HYP-PM-0002 | Proposed new Edge |
|---|---|---|
| Family | P-M {I5,I6,I7,I12} | **same** |
| Primary entry | I7 | I5 or I7 — **same set** |
| Formation variable | `OFI_day` = Σdelta / Σ(buy_lot+sell_lot) | **identical** |
| Measurement | `cont_k = sign(OFI_day(t))·(logp(t+k) − logp(t))` | **identical form** |
| Horizon | **k ∈ {3, 7, 15}**, primary 7 | 1–3 |
| Data | `stockbit_flow_bars` → daily | **identical** |

**k = 3 is already inside PM-0002's declared grid.** A new Edge at 1–3 days would use the same
variable, the same measurement, the same data and the same family, overlapping the existing draft at
its lower bound. Under LIM3-type reasoning that is **not independent evidence** — it inflates the
P-M denominator without adding information, and PG-3 makes the slot permanent.

Testing **continuation** at 1–3 d = PM-0002's short tail.
Testing **reversal** at 1–3 d = HYP-PM-0001's mechanism (M1.1/I5) at a longer horizon — and the
EXP-PM-0001 close-out named the *only* legitimate continuation as **"re-opening inventory
mean-reversion under higher-fidelity (LOB) flow"**, i.e. the prescribed remedy was **better data,
not a longer horizon**. Changing k after a refutation is X2–X5/R15 territory unless the remedy is the
one the close-out specified.

## 7. Unverified / not located

- **No peer-reviewed IDX-specific order-flow → return study located.** Nearest structural analogues
  are Taiwan (LC-PM-0003) and an Indian order-driven study (Tripathi, *Finance Research Letters* 41,
  2021) that was **abstract-only** — excluded under **EX7**.
- **IDX historical ARA/ARB change dates UNVERIFIED** — the AEI source was robots-disallowed. **B8
  applies with full force** to any M6 claim built on the bands.
- IDX tick-size table and short-selling rules not extractable from the official page fetched.

## 8. Recommendation

**NO-GO on the M2.x short-horizon Edge as framed.** See the final report §15 for the reasoning and
for the one alternative the sweep did surface (LC-PM-0006 Fact 2, **M6 / I1**, which is *not* M2.x
and belongs to *no currently open family*).

## 9. Confirmations

- No inferential DB query · no OFI or `cont_k` computed · no price-response statistic computed
- No hypothesis registered · no family slot consumed · `HYPOTHESIS_REGISTRY.md` unmodified
- No power analysis · no sealed outcome variable inspected · no backfill launched
- No ZCode file touched · no production file touched · `HYP-PM-0002_DRAFT.md` read-only

**Files created (all new):** `LC-PM-0001.md` … `LC-PM-0006.md`, this record.
**Files modified: none.**
