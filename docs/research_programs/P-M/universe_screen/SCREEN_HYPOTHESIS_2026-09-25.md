# New hypothesis: a retail-safe stock universe pre-filter (not a timing signal)

> **Filed 2026-09-25 from the Owner's note "Retail screening criteria 2026 09 25" (pasted in a Claude
> Code session; the note did not exist on disk).** Sections 1–5 and Sources are the note verbatim.
> The **Repository review** section at the end was added at filing and takes precedence where the
> two disagree. Test pre-declaration: `PREDECLARATION.md` (this folder); decision record D-058.

2026-09-25 · IDX program. Source: "Wisdom of the Crowd: Retail Orders and Stock Returns" Gemini
Notebook (same notebook as `LIT_REVIEW_RETAIL_EDGE_2026-09-23.md`, now 49 sources), two new queries
today. Full session transcript not saved by NotebookLM itself — this doc is the durable record.

## 1. Bottom line

This is a **screening hypothesis, not a factor/timing hypothesis**: which of the ~900 IDX-listed
names are even structurally fit for a retail account to hold, before any price or fundamental
signal is applied. It sits upstream of everything in `SWING_MIDTERM_PLAYBOOK_2026-09-23.md` — a
prefilter, not a competing sleeve.

The notebook proposed a 5-filter pipeline claiming to cut ~900 names to ~60–120. **Two of the five
filters (foreign-participation and fundamental-quality) turned out to rest on the same two papers
LIT_REVIEW already rejected on 2026-09-23** — the notebook re-surfaced them without flagging that on
its own; I only caught it by asking for exact citations, which it then confirmed:

| Paper | Used for | Status |
|---|---|---|
| Koesrindartoto, Aaron & Wang (2024), IJFS | "+4.92 to +6.93pp foreign AURR outperformance" → Filter 3 (foreign participation ≥10-20%) | Confirmed same paper flagged in LIT_REVIEW. Transaction data from **2003**, pre-dates the 2021-22 broker/domicile code closures that removed the intraday info edge Dvořák (2005) documented. Weak. |
| Rakim, Wijayani & Misra (2026), "PDY G5D5" | "28.57%/yr, Sharpe 322.7" → cited as evidence for Filter 4 (quality/profitability) | Confirmed same paper LIT_REVIEW rejected as not credible. The notebook now traces the exact error: Table 3 divides an 87.02 **percentage-point** cumulative return by a 0.0290 **decimal** stdev → units mismatch. Corrected Sharpe ≈ 30, still absurd — the G5D5 portfolio holds an average of **3 stocks**, returns 0.00% in 6 of 10 sample years, and the 942.76% cumulative return is driven almost entirely by one +920% year in 2021-22. Do not use, even "corrected." |

**Do not adopt Filters 3 and 4 as specified.** Keep Filters 1, 2, 5, which are IDX market-structure
facts, not disputed research claims — verify their specific numbers against current KSEI/IDX
regulation before coding them, since I have not independently checked the notebook's tick-size and
ARB/ARA figures.

## 2. The filters worth keeping (verify numbers, but the logic is structural, not a backtest claim)

1. **Board & auction status** — exclude Watchlist Board (Papan Pemantauan Khusus) and Acceleration
   Board names. Already established in `LIT_REVIEW_RETAIL_EDGE_2026-09-23.md` §6 (FCA since 25 Mar
   2024); this just formalizes it as a hard universe filter, not just an avoidance note.
2. **Liquidity / index-membership cutoff** — require IDX80 or Kompas100 membership, or ADV ≥ Rp 5
   billion/day. This is close to your existing `SWING_MIDTERM_PLAYBOOK` universe spec (ADV ≥ Rp 1bn);
   the notebook's number is stricter. Reconcile against your own ADV distribution rather than taking
   either number as given.
3. **Price tier** — share price ≥ Rp 200 (IDX's tick-size regime gets coarse and the ARB/ARA band
   widens to ±35% below that). Directionally consistent with your existing ≥Rp 50-100 floor in
   `SWING_MIDTERM_PLAYBOOK`; the notebook argues for a higher floor. Needs its own check.

**Dropped / quarantined:**
- Filter 3 (foreign participation ≥10-20%) — rests on the 2003-vintage Koesrindartoto clustering.
- Filter 4 (GPA top 40%, CFOA>0, low D/E "replicating foreign stock-picking + PDY G5D5") — the
  quality metric itself (gross profitability, low leverage) is fine and already recommended in
  `SWING_MIDTERM_PLAYBOOK` §4A from Li, Wei & Zhang (2023); it's the notebook's *evidentiary basis*
  here (foreign-picking regression + PDY G5D5) that's compromised. If you want a quality filter, cite
  Li-Wei-Zhang, not this.
- The dividend-yield-as-"confirmation signal" part of Filter 5 — same PDY contamination. A dividend
  filter is still defensible from `SWING_MIDTERM_PLAYBOOK`, just not for the reason given here.

## 3. What's actually new here vs. the existing program

- Not new: value/quality tilt, avoid watchlist/FCA, avoid IPOs <12mo, low-vol exclusion — all already
  in `SWING_MIDTERM_PLAYBOOK`.
- New: treating **board status + liquidity + price tier as a hard pre-filter applied before any
  strategy**, rather than scan-level avoidance rules layered on afterward. And the specific numbers
  (tick-size tiers, ARB/ARA band widths by price tier) as a mechanical, checkable spec rather than a
  general caution.

## 4. How to test it (cheap, no new data needed)

This doesn't need a new backtest — it's an ablation on what you already have:
1. Pull current board status (watchlist/FCA/Acceleration) and ADV for your 87-ticker universe (or
   the wider panel) as of each rebalance date.
2. Re-run HYP-PM-0010 (trend, forward-test open since 09-18) and the dividend/value book split by
   in-filter vs. out-of-filter names. If the filter is doing real work, the in-filter subset's
   Sharpe/t should not degrade relative to the full universe — and ideally the excluded names should
   show up disproportionately in your failed-breakdown / liquidity-sweep anti-edges, which would be a
   nice internal consistency check.
3. This is observational, not a new pre-registered hypothesis in the D-05x sense — it's a universe
   definition, so it doesn't need to clear the t≥2.87 gate. But log it as a deviation if it changes
   which names any live/paper strategy can trade.

## 5. Open items

- Verify the 5-tier price-fraction (tick size) table and the ARB/ARA band widths (±35%/±25%/±20% by
  price tier, ±10% inside FCA) against current IDX regulation directly — the notebook is a
  synthesis layer, not a primary source, and it has now twice surfaced a paper you'd already
  rejected without saying so.
- Reconcile the ADV/price cutoffs against your own data (see §2.2, §2.3) rather than adopting the
  notebook's numbers verbatim.
- Going forward, cross-check any new NotebookLM output against prior rejections **before** treating
  it as new evidence — ask it directly whether a claim matches a previously flagged source, the way
  the follow-up question in §1 did. It doesn't volunteer that on its own.

## Sources

- Notebook: "Wisdom of the Crowd: Retail Orders and Stock Returns" (Gemini Notebook, 49 sources as of
  2026-09-25).
- Koesrindartoto, Aaron & Wang (2024), "Do Foreign Investors Underperform or Outperform Domestic
  Investors in Trading Activities? Evidence from Indonesia," IJFS 12(4):100.
  https://www.mdpi.com/2227-7072/12/4/100
- Rakim, Wijayani & Misra (2026), "Profitable Dividend Yield Investment Strategy: Empirical Evidence
  from Indonesian Stock Exchange," Akuntansi: Jurnal Akuntansi Integratif 12(1):63-79. (Not
  independently located outside the notebook; treat as unverified pending direct access.)
- Cross-reference: `research/LIT_REVIEW_RETAIL_EDGE_2026-09-23.md` §7 (original rejection of both
  papers), `research/SWING_MIDTERM_PLAYBOOK_2026-09-23.md` §4 (existing universe/quality spec).

---

## Repository review (added at filing, 2026-09-25)

1. **The two cross-referenced documents are not in this repository or anywhere on this machine.**
   `research/LIT_REVIEW_RETAIL_EDGE_2026-09-23.md` and `research/SWING_MIDTERM_PLAYBOOK_2026-09-23.md`
   were searched for filesystem-wide and not found. The rejection of both papers and every "already in
   the playbook" claim in §2–§3 are therefore unverifiable here until those files are committed.
2. **Filter 1 (board status) is not testable historically.** The DB holds no point-in-time record of
   Watchlist/FCA/Acceleration board status or of IDX80/Kompas100 membership. Applying today's board list
   to past trades is look-ahead. Testing it requires collecting board status going forward, or
   reconstructing it from IDX announcements.
3. **§4.2 must not touch the live forward test.** FWD-PM-REGIME-002's universe is frozen
   (`forward_regime/PROTOCOL.md`: `adv20 >= Rp 1e9`, `close >= Rp 50`). Applying this filter to it would
   be a mid-test rule change. The split in this folder runs on the **in-sample reference trades only**
   (data ≤ 2026-09-16) and is exploratory.
4. **§4.3 is half right.** A universe definition is not a hypothesis and needs no G1 gate. But choosing a
   cutoff after seeing the split is snooping on the universe, so the cutoffs were fixed on structural
   grounds before the run (`PREDECLARATION.md`, D-058).
5. **Not done in this pass:** the "dividend/value book" split (no such book exists in this repo) and the
   FADE anti-edge consistency check in §4.2.
6. **Tick size / ARB figures** (unverified against primary IDX rules — still open): from general knowledge,
   tick size is Rp 1 below Rp 200, Rp 2 to 500, Rp 5 to 2,000, Rp 10 to 5,000, Rp 25 above; auto-rejection
   bands ≈ ±35% / ±25% / ±20% by tier and ±10% for FCA names. Consistent with the note, not confirmed.

---

## Result of the pre-declared split (2026-09-25, `RESULT_20260925T020206Z.json`)

One run, filters and rules as fixed in `PREDECLARATION.md`. T1 spec-002 reference trades, data ≤ 2026-09-16,
excess over IHSG net of 0.60% round trip. t = month-clustered / Driscoll-Kraay L=60.

| period | subset | N | mean %/trade | t_month | t_dk60 |
|---|---|---:|---:|---:|---:|
| FULL | all trades | 7,541 | +2.36 | 4.13 | 3.30 |
| FULL | P200 in / out | 5,432 / 2,109 | +1.95 / +3.43 | 3.87 / 3.14 | 3.17 / 2.49 |
| FULL | A5 in / out | 4,750 / 2,791 | +1.11 / +4.49 | 2.04 / 4.83 | 2.14 / 3.63 |
| FULL | P200+A5 in / out | 3,811 / 3,730 | +1.07 / +3.68 | 2.02 / 4.51 | 1.92 / 3.53 |
| ex-2025 | all trades | 5,738 | +1.25 | 2.90 | 2.46 |
| ex-2025 | P200 in / out | 4,274 / 1,464 | +1.25 / +1.27 | 2.81 / 1.32 | 2.26 / 1.19 |
| ex-2025 | A5 in / out | 3,710 / 2,028 | **+0.29** / +3.01 | **0.62** / 3.86 | 0.59 / 3.51 |
| ex-2025 | P200+A5 in / out | 3,034 / 2,704 | **+0.36** / +2.26 | **0.76** / 3.25 | 0.69 / 2.98 |

In − out difference (t_month): P200 −1.48% (−1.49) / −0.03% (−0.03); A5 −3.38% (−3.75) / −2.72% (−3.12);
P200+A5 −2.61% (−3.25) / −1.90% (−2.35) — FULL / ex-2025.

**Pre-declared verdicts.** All three filters **cost return** (in-filter mean below the full universe in both
periods). The in − out gap is **detected** for A5 and P200+A5, **not** for P200.

**Reading (≤5 lines).**
1. The Rp 200 price floor is nearly neutral ex-2025 (+1.25 vs +1.25). It removes 25% of trades without changing
   the mean. Its FULL-period cost comes from 2025 low-priced names.
2. **The T1 edge lives almost entirely in names with adv20 < Rp 5bn.** In liquid names it is +0.29%/trade, t 0.6,
   ex-2025. That is below FWD-PM-REGIME-002's PASS bar (+0.55%) and its FAIL floor (+0.30%).
3. That is the same pattern as TFB (net-negative on liquid names) and VOLEX (top-ADV tercile fails). The flat
   0.60% round trip almost certainly understates the cost of trading Rp 1–5bn names, so part of the "out" edge may
   be untradeable friction rather than alpha.
4. This does not change FWD-PM-REGIME-002 (frozen universe). It does say what its forward result will mostly be
   measuring: sub-Rp 5bn momentum.

**Replication note.** Yesterday's `overlap_audit` gave 7,191 trades on the same code and cutoff. The +350
are exactly the positions still open at the cutoff and marked to 2026-09-16, dropped then because IHSG
2026-09-16 was missing; that bar was repaired after the audit (corpus 1,087,571 → 1,087,572 rows).
