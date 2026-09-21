# ZCODE TOWR BREAKOUT → PULLBACK → CONTINUATION DEEP-DIVE

**Date:** 2026-09-10 · **Status:** DISCOVERY / DESCRIPTIVE ONLY — no forward-return alpha test, no p-values, no registration, no threshold optimization on outcomes, no production/governance writes.
**Evidence:** `pm_data_audit/towr_deepdive.json` (+ script `21_towr_deepdive.py`). All broker-flow "net" quantities are replaced by composition/structure measures (breadth, concentration, intensity, species tilt) per the recorded broker_flow net-degeneracy finding (family map §3).
**Data caveats:** broker_flow partial-ingestion days **2026-09-02 (none for TOWR) and 2026-09-08 (no broker rows)** — the re-acceleration day's flow structure is unobserved. Species fields use `freq`; semantics unresolved — C1 results are descriptive and flagged.

---

## 1. Executive summary

TOWR is objectively a breakout → pullback → continuation sequence (Aug 18–26 breakout/climax → Aug 27–Sep 3 pullback −5.5% → Sep 4 flat base → Sep 8–9 re-acceleration +8.6%). The pullback is **not** a sustained-intensity state: flow intensity collapsed (2.8→0.44×ADV20), buy-side breadth stayed at the cap while price fell, and selling came from a persistent perennial-seller group plus one breakout buyer (CC) flipping to distribute. The one distinctive day is **Sep 4**: zero price response against 37.6B of flow, a **new** desk-classified buyer (HP, 12.8B = 68% of the buy side) absorbing a 9.6B seller — an absorption signature. Historical analogues (1,625 objective events; 677 continuations / 948 failures) show the descriptive discriminator is the **intensity profile** — failures churn (breakout intensity 4.20 vs 2.97; pullback intensity 2.05 vs 1.24) while continuations retrace quietly — plus a weak desk-tilt signal during the pullback (+0.02 vs −0.01). Broker-identity persistence shows **no** discrimination. Classification: the pattern is **existing P-M mechanism (C7 contrast + C8 base-day), not a new family**. Verdict: **INTERESTING BUT UNPROVEN**.

## 2. TOWR objective phase timeline

Pre-stated mechanical rules (60-day-high close + volume ≥ 2×ADV20 for breakout; ≥3% close retracement for pullback; reclaim of breakout close for continuation) fire on **2025-07-21** — a prior TOWR breakout that **failed** (no reclaim in 10 sessions). The 2026 sequence evolves as an extension trend, so phases are stated from the table with the same ingredient definitions applied to the running move (no future information used to place earlier boundaries):

| Phase | Dates | Close path | Turnover | Intensity (×ADV20) |
|---|---|---|---|---|
| PRE (drift) | Aug 3–13 | 402 → 388 | 14–53B | 0.5–2.5 |
| **BREAKOUT leg** | **Aug 18–19** | 394 → 422 (+8.2%, 60d highs) | 90B / 123B | 3.4 / 4.6 |
| EXTENSION → climax | Aug 24–26 | 456 → 474 | 97B / 98B* / 265B | 3.7 / 3.8 / **10.1** |
| **PULLBACK** | **Aug 27–Sep 3** | 470 → 448 (−5.5%) | 86B → 16B → 25B | 2.8 → 0.44 |
| BASE (flat) | Sep 4 | 446 (0.0%) | 43B | 1.15 |
| **RE-ACCELERATION** | **Sep 8–9** | 470 → 484 (+8.6%) | 139B / 118B | 3.7 / 2.9 |

*Aug 25 broker rows = 0 (Dataset A's excluded date); Sep 2 and Sep 8 broker rows missing/partial (known ingestion defects).

## 3. Breakout microstructure

- Three pulses with **rotating lead buyers**: Aug 18 CC 9.8B/AK 7.7B; Aug 19 essentially single-desk **PD 22.5B** (77% of the buy side, t1b=0.77); Aug 24 CC 11.4B; Aug 26 **BB 23.3B + KZ 13.2B** on the 265B climax.
- Sell side hit the 25-broker cap on every breakout day (ns=25) while buy-side counts were lower (13–24) — the crowd was *selling into* the advance; top sellers persistent (OD, AK, BK, SQ, ZP).
- Concentration: CONC positive and rising into the climax (+0.11 to +0.45) — buy side increasingly concentrated.

## 4. Pullback microstructure

- Price −5.5% over 6 sessions on **collapsing intensity** (2.84 → 1.08 → 1.89 → 1.33 → 0.44): the retracement was quiet, not churned.
- Buy-side breadth stayed at cap (nb=25 vs ns=16–22) on most pullback days — participation did not deteriorate.
- Sellers: the **same perennial group** (OD, AK, BK, ZP) that sold through the breakout, **plus CC** — an earlier top breakout buyer — flipping to distribute (6.9B, 8.3B on Aug 27/31). This is distribution by a prior buyer, evidence *against* a pure "same-agent persistence" story.
- Sep 1 species tilt −0.53 (aggregator-heavy buys); Sep 3 gross only 13.8B — crowd dip-buying, then near-silence.

## 5. Continuation microstructure

- **Sep 4 base day: price 0.0% against 37.6B gross** (1.15×ADV20), buy breadth 25 vs 17, **new desk-classified buyer HP 12.8B (68% of buy side)** absorbing NI's 9.6B of selling, species tilt **+0.67**, CONC +0.19.
- Sep 8 re-acceleration +5.4% (int 3.72) — **broker structure unobserved** (partial ingestion). Sep 9 +3.0% to 484: buyers recur (YU, KZ, CC — all pre-pullback buyers), sellers the perennial group.

## 6. Broker identity transitions

| Question | Observation |
|---|---|
| Who entered before breakout | Small, rotating buyers (CC, AK, KZ) during the Aug 3–13 drift |
| Who dominated breakout | A different lead each pulse: CC (Aug 18), PD (Aug 19, 77% share), CC (Aug 24), BB+KZ (Aug 26 climax) |
| Who remained active in pullback | The perennial sellers (OD, AK, BK, ZP) kept selling; buy-side counts stayed at cap |
| Who disappeared | PD (the Aug 19 dominant buyer) vanished after the breakout pulse |
| New brokers at pullback/base | **HP** (new, desk-classified, 12.8B) and DX at the Sep 4 base; new seller NI |
| Same brokers directionally persistent? | Sellers yes (OD/AK/BK/ZP); buyers **no** (rotating) |
| Did pullback selling come from prior buyers? | **Partially — CC flipped from top breakout buyer to top pullback seller** |

"Same-agent structural persistence through retracement" is therefore **not** the TOWR mechanism: the persistent agents were the sellers; the buyers rotated, one distributed, and the base day was marked by a *new* entrant.

## 7. Breadth vs concentration

- Breakout: breadth narrow-ish (nb 13–24) with sell-side capped; concentration rising (CONC → +0.45).
- Pullback: breadth *broadened* on the buy side (nb=25, cap) while concentration stayed slightly negative (−0.10 to +0.19) — broad, shallow dip-buying.
- Base (Sep 4): the one day with both — high buy breadth (25) AND concentrated desk buying (t1b 0.68, st +0.67).
- Continuation: narrower again (nb 17) with sell side capped.
- The structural change present in the pullback that was absent at the breakout: **buyer-count breadth at cap while price fell** (shallow crowd support), vs the breakout's concentrated single-desk advances.

## 8. C7 flow-intensity analysis

Intensity did **not** stay elevated through the pullback (2.84 → 0.44). C7's own analogue contrast is real but is about the *contrast*: failed breakouts churn (breakout 4.20 vs 2.97; pullback 2.05 vs 1.24 median intensity) while continuations retrace quietly. TOWR's quiet pullback is consistent with the continuation group. **C7 alone does not explain the TOWR structure** — the pullback's distinctive content is the Sep 4 flat-price absorption day, not an intensity state.

## 9. C8 absorption analysis

Sep 4 is the absorption candidate: 37.6B gross (1.15×ADV20 — moderate, not extreme), zero close-to-close move, a 9.6B seller fully absorbed, buyer concentration 68% in a single new desk-classified broker, and re-acceleration followed within two sessions. This resembles **selling absorbed by concentrated demand**, layered on an otherwise ordinary low-volume retracement. It is one day; intensity was not extreme; and the analogue contrast for absorption-type states has not been tested event-wise.

## 10. C1 species analysis / dependency status

Species tilt is computed (prefix classifier; uses `freq`) — **[DEPENDENT ON CLAUDE VALIDATION: freq semantics]**. Descriptively: Sep 4 st=+0.67 (desk-heavy buys at the base), pullback days mildly aggregator-tilted (Sep 1 −0.53), analogue medians CONT +0.02 vs FAIL −0.01 at the pullback. Direction consistent with the species mechanism; magnitude small; treated as indicative only.

## 11. Price/flow disagreement

The single clear disagreement event is **Sep 4**: 37.6B of flow, 68% of buying in one desk, zero price response — large broker activity with no price move (absorption/resilience). The reverse (large price move without broker activity) occurred on **Sep 8** (+5.4% with no broker data — unobservable, not disagreement). The pullback as a whole was price-down + broadly-supported (breadth at cap) — a mild constructive disagreement.

## 12. Historical successful analogues

1,625 objective events (pre-stated rules; features fixed at pullback-day close; outcome label — reclaim of breakout close within 10 sessions — applied only afterward). CONT group (n≈160–164 with broker data) medians: breakout intensity 2.97, **pullback intensity 1.24 (quiet)**, breadth 42/42 brokers, pullback species tilt +0.02, buy-top-5 overlap 0.20, buyer-flip count 2.

## 13. Historical failed analogues

FAIL group (n≈256–267) medians: **breakout intensity 4.20 (blow-off), pullback intensity 2.05 (churn)**, breadth 38/39 (fewer brokers, contracting), pullback species tilt −0.01, overlap 0.20, flips 2. Failures are the *majority* outcome (948 vs 677). Concentration, identity overlap, and flip counts do **not** discriminate.

## 14. Look-ahead audit

Features for every event and for TOWR's phase boundaries use only data ≤ the pullback-day close (60-day highs, ADV20, broker aggregates of past days). Future prices are used **only** to assign the CONT/FAIL label after features were fixed. No threshold was tuned on outcomes (all cut-offs pre-stated: 60d high, 2×ADV, −3% retrace, 10-session windows). The TOWR narrative boundaries were checked against these same mechanical rules; the 2026 sequence is a trend-extension variant of the breakout rule (60-day-high first crossed in August), disclosed rather than re-fitted.

## 15. Mechanism classification

**EXISTING P-M MECHANISM (C7 contrast + C8 base-day), not a new family.** Economic reasoning: the discriminating content between continuation and failure is (i) an intensity/volume-profile contrast (churn vs quiet retracement) — that is C7's state space, arguably reducible to a volume-profile effect; and (ii) a flat-price concentrated-demand base day — that is C8's absorption state. The broker-identity transition story ("same-agent persistence") tested and **failed**; species tilt adds a weak C1-flavored overlay. No new economic dimension (no new information source beyond participation/intensity/absorption) is required to describe TOWR.

## 16. Evidence against the mechanism

- Identity-persistence features show **zero discrimination** (overlap 0.20/0.20, flips 2/2) — the TOWR-specific HP story has no analogue-level support yet.
- The intensity contrast is largely a **volume-profile effect** — the task's own challenge "simply explained by volume" is partially conceded: the discriminative content measured so far IS the volume/intensity profile, not broker identity.
- Single-day snapshot per event (pullback-day close only) — intra-pullback structure (like TOWR's Sep 4) is not captured by the analogue features; the C8 signature is untested across events.
- Confounds uncontrolled: market regime, sector, liquidity tier, listing age; windows overlap in time (clustered events).
- TOWR-specific data gaps (Sep 2/8 broker rows) mean the re-acceleration's microstructure is unobserved.
- TOWR is not unique (1,625 analogues) but the *Sep-4-type base day* has not been searched for systematically; and TOWR's own 2025-07 episode shows the same nominal setup failing.

## 17. What remains unknown

- Whether Sep-4-type absorption base days (flat price + concentrated new-desk demand) discriminate CONT vs FAIL at event level — testable descriptively under Dataset B.
- Whether the intensity-profile contrast survives controls (liquidity tier, regime, 2025 vs 2026 sub-periods) — a modeling task, not more discovery.
- C1 species read of the base day (freq semantics **[DEP-B]**).
- Who bought Sep 8 (broker data missing) — unrecoverable from current tables.
- Why 2026-08-25 has no market session (cause [UNRESOLVED] per Dataset A handoff).

## 18. Recommendation for future Dataset B testing

If any P-M G1 candidate is later derived from this pattern, it should be formulated as an **C8-conditioned state test** ("flat-price, desk-concentrated base day after breakout-pullback") with the C7 intensity profile as a declared control — not as a new family registration — and only after the DEP-B blockers in the custody/handoff report are cleared. TOWR itself remains an unlabeled live case at data end (Sep 9): its outcome is future information and must not be used.
