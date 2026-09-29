# ZCODE BRIEF — Broad edge search for a NEW family (screens only)

**Issued:** 2026-09-29 by the main session (XPS) at the Owner's request · **Branch:** `ops/hardening-2026-07-10`
**Output dir (the only place you write):** `docs/research_programs/P-M/broad_search/`
**Authority:** screens only. You may not register a hypothesis, open a forward test, consume a
family slot, or edit `DECISION_LOG.md`, `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md` or any frozen
protocol. Draft proposed entries in your output dir; the Owner decides them.

---

## 0. Mission

Every family tried so far is spent, null or in flight. The only live deciders (VOLEX-001, FADE-001,
REGIME-002) mature from mid-October. Use that wait to **map and screen families nobody has touched**,
and bring back at most three screen verdicts plus a ranked map. A clean null is a full success: it
narrows the search. **Do not tune your way to a pass.**

## 1. Read first (in this order)

1. `docs/research_notes/RULE_FIRST_PROTOCOL_2026-09-24.md` — method rules R1–R10, the Rule Card, and
   §6 candidates C1–C5. C2 (issuance) and C4 (index adds) were **never run**.
2. `docs/roadmap/DECISION_LOG.md` **D-055 … D-063**. In particular D-062 (the standing
   no-correlated-registration directive and the deflation audit) and D-063 (F-1 rule, FORU,
   HYP-PM-0007).
3. `docs/research_programs/AUDIT_2026-09-28_DEFLATION.md` + `deflation_audit/` — the trial census
   (252 as of 09-28) and the full-census bar (**|Z| ≈ 2.84**).
4. `docs/research_programs/AUDIT_2026-09-24_RESULT_VALIDITY.md` — the overlap/look-ahead failure modes
   that killed earlier results. §4 of `forward_volex/REMEASUREMENT_RESULT_2026-09-23.md` covers the
   symmetric-window look-ahead lesson.
5. `P-M/insider_screen/` — **the template for a screen**: PREDECLARATION.md + .sha256, committed
   before the run → script → RESULT json → VERDICT.md.
6. `P-M/ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` — your own earlier map; v2 supersedes it.

## 2. Spent, in flight, or blocked — do NOT re-open

| Area | Status | Why it is closed |
|---|---|---|
| Microstructure flow {I5,I6,I7,I12} (broker/foreign flow) | 4 members, all FAILED/INVALID | tested seven ways; re-open only with a new mechanism and ≥2 years of PIT flow |
| C-family {C2,C3,C7} | done | INVALID / NOT CONFIRMED ×2 |
| Price-Trend {T1} | REGIME-002 in flight | dead at the deflation bar; TREND-003 declined (D-063) |
| Price-Reversal {R1} (breakdowns, sweeps, MIRROR, falling wedge) | FADE-001 in flight | D-062: nothing correlated before ~2026-10-19 |
| Volatility / lottery (VOLEX, MAX RC-0001) | VOLEX-001 in flight; RC-0001 underpowered | don't add a sibling |
| Insider disclosures | SCREEN-PM-INS-001 null (D-061) | last unscanned in-house dataset, read |
| ARA/ARB price-limit (I1) | HYP-PM-0008 refused | continuation not capturable, short leg illegal |
| Chart patterns (exhaustion, double top, lower-high, staircase, ATR climax) | null | memory notes 2026-09-25 |
| Index reconstitution (HYP-PA-0001) | FAILED | ADD-side subgroup is forward-only (C4) |
| 12-1 momentum, 1-month reversal, Ramadan/calendar | low prior / anti-edge / n≈13 | RULE_FIRST §6 parked table |
| Value/profitability | data-blocked | no point-in-time fundamentals with filing dates |

## 3. Open search space — candidate families (map all, screen the best ≤3)

**A · Corporate-finance events `{CF}` — highest priority, best data.**
`walkforward.db::corporate_action_events` (2009–2026, `raw_json` with `*_created` timestamps):
rightissue 317 · warrant 147 · tenderoffer 163 · stocksplit 194 · stock_reverse 19 · bonus 82 ·
dividend 4,754 · rups (AGM/EGM, with agenda fields) 6,708.
- A1 **issuance avoidance.** Rights issues, private placements and warrants predict low 6–12m returns
  (McLean-Pontiff-Watanabe 2009, 41 countries; driven by post-issuance *under*-performance, which suits
  a long-only book).
- A2 **tender-offer anchoring.** A mandatory tender offer price acts as a floor/anchor; measure the
  drift from announcement to completion.
- A3 **split / reverse-split announcement drift.** A reverse split is a distress marker (avoidance).
- A4 **dividend events.** Initiation or omission, and ex-date behaviour, against the prior-year
  payout.
- A5 **EGM agenda as early signal.** A `rups` agenda that approves issuance precedes the rightissue
  record. Test whether it moves the PIT date earlier.

**B · Listing lifecycle `{LC}`.** IPO long-run underperformance (avoidance) and the lock-up expiry
supply shock. The listing date is proxied by the first bar in `history_long.db::ohlcv_long`
(2000–2026, 929 tickers); verify it against IDX where possible. Partly data-blocked — say how much.

**C · Trading-status events `{TS}`.** Resumption after suspension (`suspension_events`, 3,189 rows,
with a classification). The special-monitoring / full-call-auction board has **no table**, so list it
as a data-acquisition item only.

**D · Cross-asset lead `{X}`.** Overnight US ADR (TLK) → TLKM open; USD/IDR (`IDR=X`) and coal / CPO
proxies → sector names (`ticker_sector`, 780 rows). Only next-open entries count; show that the move
isn't already in the open (capturability).

**E · Industry cross-section `{S}`.** Within-industry lead-lag (big → small; Hou 2007). This is
**probably {T1}-correlated**: declare it, and if you screen it at all, run a double sort against trend
onset.

**F · Attention `{N}`.** `news_mentions` only covers 2026-04 onward (about 5 months), so screening is
underpowered by construction. Propose a forward recorder only; do not screen.

## 4. Hard rules (each one is here because of a past failure)

1. **Predeclare, then run.** Write PREDECLARATION.md for each screen and commit it (with its sha256)
   *before* reading any outcome. It must fix: rule, universe, PIT date field, estimand, benchmarks
   (EW-book **and** IHSG), at most 2 horizons, split (pre-2021 `ohlcv_long` = discovery-as-replication,
   2021-07→2026 = confirmation), primary, **kill rule**, and a noise floor / MDE computed from event
   counts alone.
2. **Multiplicity.** Every arm joins the D-062 census. A candidate passes only at **|Z| ≥ 2.84** (or
   the recomputed bar after your arms are added). Budget: **≤ 24 arms in total** for this brief. Report
   the count.
3. **Point-in-time.** Use announcement timestamps (`rightissue_created`, `rups_created`, …), never
   ex-dates or effective dates. Audit 20 random events per type against the IDX disclosure where you
   can. A symmetric `±N` window is look-ahead until proven otherwise.
4. **Prices — critical trap.** Load through `data.adjustments` (`read_raw_ohlcv` / the
   `research.rulecard.data` loaders); a hand-rolled `SELECT … FROM ohlcv` in research code fails CI.
   **The adjustment layer applies splits only.** Rights issues, bonus issues and reverse splits are
   *not* adjusted: 20 rights issues since 2021 have a factor ≥1.05, led by FORU ×19.5 (ex 2026-09-22),
   PACK ×13.2 and PANI ×5.7. Any issuance screen that ignores this "discovers" the mechanical
   ex-rights drop. Compute returns across ex-dates with each event's own `*_adj_factor`, **and** report
   the same estimate with ex-date windows excluded. **Exclude FORU from 2026-09-14.**
5. **Costs and liquidity.** Floor of 0.60% round trip, plus D-059's modeled cost by ADV (1.5–3.5%
   all-in below adv20 Rp 5bn). Report gross and net. Primary universe: adv20 ≥ Rp 5bn. Low-ADV results
   are a fingerprint, never the primary.
6. **Long-only.** An anti-edge is an avoidance filter. Never a short.
7. **Inference.** Event-time, clustered by date/month; overlapping holds → date-blocked bootstrap or
   Driscoll-Kraay. Headline the per-date mean, not the per-trade mean.
8. **Survivorship.** State the delisted coverage of `ohlcv_long` before any long-side claim.
9. **Reproducibility (D-063 F-1 rule).** Commit every driver script next to its result. Record each
   run through `research/tracking.py` (run_id, git sha, dataset fingerprint). Any number you report
   must regenerate from committed code. Scripts that live only in /tmp are what caused F-1.
10. **Correlation (D-062).** Nothing whose signal overlaps breakdown/sweep, trend onset or
    volatility exclusion. If overlap can't be avoided, declare it and report the incremental effect
    in a double sort.
11. **Stop rule.** If any primary clears the bar: **stop, do not refine, do not run variants.** Write
    the verdict and hand it to the Owner. A pass followed by tuning is worth nothing.
12. **Boundaries.** Read-only on the production DB (use a snapshot: an XPS `scripts.db_backup`
    archive; record its fingerprint). Never run production code or write production tables. Commit
    only under your output dir; `git pull --rebase` before pushing; never force-push.

## 5. Deliverables (in order)

**Phase 0 — no outcome data may be read.**
- `FAMILY_MAP_v2.md`: for each family A–F, give mechanism, IDX/EM literature prior (sign, magnitude,
  source), PIT audit result, event counts per year overall and at adv20 ≥ 5bn, noise floor / MDE,
  capturability, independence from §2, and a proposed family label. Then a ranked shortlist and a
  data-gap list.
- `RIGHTS_ADJUSTMENT_AUDIT.md` (read-only, counts only, no returns). How many ex-rights, bonus or
  reverse-split dates fall inside the formation or holding windows recorded in the FADE-001,
  VOLEX-001 and REGIME-002 ledgers? Does an unadjusted ex-date drop plausibly create or kill a signal?
  **Report only; never touch a ledger.** If the answer is "material", stop and flag it first. That
  finding outranks every screen.

**Phase 1 —** predeclare the top ≤3 screens from the map (commit), then run them.

**Phase 2 —** a `VERDICT.md` per screen, `CENSUS_UPDATE.md` (arms added, new bar), and
`HANDOFF_BROAD_SEARCH_<date>.md`. The handoff contains proposed (not recorded) DECISION_LOG text for
any survivor and a proposed FAILURE_REGISTRY-style note for each null.

**Timing.** Phase 0 before ~2026-10-15 (the first VOLEX maturities), Phases 1–2 before ~2026-10-26.
Nothing here is urgent enough to cut a rule.

## 6. What "done" looks like

A ranked map of new families with data-readiness facts, one audit answer on rights adjustment, and
at most three predeclared screen verdicts, all regenerable from committed code. Most likely outcome:
nulls plus one or two families worth a Rule Card. That result is fine.
