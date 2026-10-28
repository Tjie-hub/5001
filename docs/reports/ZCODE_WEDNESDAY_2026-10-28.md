# ZCODE Wednesday 2026-10-28 — status report

Brief: `ZCODE_BRIEF_WEDNESDAY_2026-10-28.md`. Work spanned two sessions (the 17:41 G0 close-out by the Claude
session; K2–K4 same-day by ZCode on 10-27; K5 + this report by ZCode on 10-28). Push HOLD everywhere.

| Item | Status |
|---|---|
| K1 {FQ} E/P G0 result | **DONE — PASSED** (203/208 qualifying months, T_eff 16.92y, power 41.5% vs 20% stop; stop rule NOT fired) — `588ce80`; proposed D-entry `7bb2215`, not filed; no G1, no registration |
| K2 Rebalance list verification | **DONE** — Kontan [S] (26 Oct) agrees exactly with both branch lists (`ba3fd29` / `01b0bbb`); no amendments; unmerged until 2026-11-02 |
| K3 Security scan rerun | **DONE** — focused Mimosa reruns completed: 5001 `e14a7f8..76dd6b3` 0 findings in changed files (seal `ad5f3d4f…`); jurnal26 `01b0bbb` 1 pre-existing hit (`tape_backfill.py:91`, blame `bf50036`; seal `1f2e8d0d…`); `test_secret_hygiene` 5 passed. Follow-up: the C-003 `_ticker_currency` f-string predicate was removed overnight (`106db63`, constant SQL + bound labels; currency output identical on all 998 tickers; 20/20 tests). Full-repo pre-commit scan still `scanner_enobufs` — only focused reruns have completed; no security claim beyond them |
| K4 The 51 unresolved KSEI codes | **DONE — no retry warranted**: all 51 are absent from `idx_tickers` (never tracked, delisted KSEI-history names); zero transient failures (no 401/403/429 in the 10-26 log); fin.db unchanged (sha `caefb1a2…`), so K4.2/K4.3 have nothing to do and the G0 pin was never at risk |
| K5 {FQ} family-widening memo | **DONE** — `P-M/fq/FQ_FAMILY_WIDENING_MEMO_2026-10-28.md`: B/M, gross profitability, low asset growth, low leverage all field-ready (998/998/942/998 coverage, no new acquisition); multiplicity cost ≈ +0.0002 bar per arm; **recommendation: register E/P alone, widen (GP first) after its G1** — propose-only |

## {FQ} G0 numbers (K1, for the record)
Qualifying months **203/208**, T_eff **16.92 years**, power at the D-112 floor (IR 0.75) **41.5%** — stop rule
(20%) **not fired**. Pins re-verified before the run: freeze `e14ab4d9…`, script unchanged since `d1e9497`,
fin.db `caefb1a2…` via the sums file. FX cross-check: 0 of 4,908 vendor/Yahoo period-end rates beyond 3%.
Proposed D-entry text (all pins included): `P-M/fq/DECISION_PROPOSAL_FQ_G0_2026-10-28.md` — **not filed**;
registration (HYP-PM-0023, census 613→614) and the single G1 run wait for the owner's go.

## Beyond the Wednesday brief (recorded for completeness)
- **Buyback brief** (`ZCODE_BRIEF_BUYBACK_2026-10-28.md`, owner: "tambahkan buyback"): executed 10-28 —
  `P-M/buyback/00/01`, `search/cand/C-009_buyback.md`, shortlist row 9, report
  `ZCODE_BUYBACK_2026-10-28.md` (`03071ed`). Verdict: announcement design INFEASIBLE locally (IDX page 403 →
  owner-browser); executed series feasible-thin (139 tickers / 787 periods in fin.db); **C-009 UNDERPOWERED
  standalone — composite net-payout path inside the C-003 freeze is the powered alternative** (owner
  question, to be decided before the C-003 freeze is pinned).
- **C-003 dependency line (L4) resolved**: E/P G0 passed → the FM-over-E/P separator at C-003's G1 is
  measurable against a live control, and freeze §6's family Option A (widen {FQ}) is live alongside Option B.
- **jurnal26 auction 09:30 render crash** fixed overnight (jurnal26 `e0f7c68`, 3 regression tests, 264
  passed; the 10-27 report regenerated — the Tuesday report's "all fires exit 0" was true before 09:30 only).

## Open (owner)
1. {FQ}: file the G0 D-entry; go/no-go HYP-PM-0023 registration + the single G1 run.
2. C-003: pin the freeze (or edits), the floor, the liquidity gate, the family option — and now also the
   buyback-composite question (fold net payout in, or keep dividends pure).
3. Buyback: owner-browser IDX announcement pull (and the HSC exclusion date) if the announcement design is
   ever wanted.
4. 2026-11-02 rebalance switch (both branches + flags + restarts, per the Tuesday report §J4.2).
5. PEAD D-entry; push decision (HOLD; 5001 37 ahead, jurnal26 9 ahead).

## Files and commits (this report's lineage)
`588ce80` (G0 run), `7bb2215` (D-entry text), `106db63` (C-003 SQL fix), `78a85ec` (TODO 10-28), `03071ed`
(buyback), this commit (K5 memo + Wednesday report + TODO). jurnal26: `e0f7c68` (render fix).
