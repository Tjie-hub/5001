# REGISTRATION DRAFT — HYP-PM-0018 tender-offer price floor (STOP) · 2026-10-09

> DRAFT for the planner to file (do not edit registries from the research branch).
> Expected D-number at filing: **D-079**. This draft records the STOP branch of D-074's stop
> rule — there is no G1 result to record.

---

### D-07XX · HYP-PM-0018 registered (tender-offer price floor, {SE} slot 2): G0 STOPPED under the D-074 stop rule — 12 eligible events < 20; spread ledger filed; census +1 (2026-10-09)

**Status:** RECORDED · **Date:** 2026-10-09 · **Type:** Registration + stop (D-074 §2.2).
**Approval authority:** Owner 2026-10-09 ("go for D-074"); D-074 (2026-10-08, "G1 + stop rule").

- **Registration.** HYP-PM-0018, family Structural-Event **{SE}** (opened D-076), slot 2.
  Branch `research/tender-offer-floor-2026-10` (from hardening `f86d272`), study at
  `docs/research_programs/P-M/tender_offer/` — PREDECLARATION + sha256 sidecar, drivers,
  8 PIT tests, counts-only census. The arm counts in the census from registration (**X8**):
  **N = 609**, bar **3.2978** (exact `bar_v2.e_max_abs_z(609)` = 3.29775843984798);
  D-074's stale 602/3.2945 superseded per the owner 2026-10-09.
- **Stop rule (owner, D-074):** the frozen population has **fewer than 20 eligible events** —
  reproduced **12** under the frozen rules (waterfall: 165 rows → 35 pre-coverage/malformed →
  4 open offers (DOOH, MBSS, NAYZ, SUPR — recorder cases) → 1 no-entry-bar → 28 zero-volume
  entries → 60 offers ≤ market → 16 ADV < Rp 1bn → 9 below the 0.60% + D-059 cost floor →
  12 eligible, 2022–2026). **No G1 was run and none may be.** Deliverable:
  `SPREAD_LEDGER.md` (pre-entry facts only). Power concurs: MDE 8.70% at n = 12 vs a median
  spread of 4.32% — undetectable even under full convergence.
- **Findings frozen at the G0** (pre-event only):
  - **tender_price is AS-ANNOUNCED** (rescale by the cumulative split factor at entry;
    LPGI/PTRO/EDGE evidence) — the opposite of dividend_value, which IS pre-scaled. Any
    future tender study must re-apply this basis test.
  - **PIT rule:** an offer is public at the close before `tender_start` (POJK 9/2018);
    `tender_created` is a vendor stamp (104/165 ≤ start; 18 on/after end) used for nothing.
  - **Mandatory vs voluntary: unreported** — event_note empty on all 165 rows, no field
    classifies. **Full vs partial: degenerate** — tender_percentage max 90.0, all offers
    partial under the ≥ 99 cut.
- **Forward recorder (D-074 §3), NOT built, owner-gated:** every new offer logged at
  `tender_start` and `tender_end`; first case DOOH (offer 148, window 2026-10-05 → 11-03);
  host beside `scripts/check_issuance_windows.py` (D-064 lineage).
- **Falsification:** not reached (no G1). The mechanism stands as accepted-not-tested; a
  re-open requires a new, disclosed G0 once ≥ 20 settled events exist.

---
