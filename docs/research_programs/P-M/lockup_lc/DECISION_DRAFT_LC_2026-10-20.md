# DECISION_LOG drafts — {LC} opened, lock-up G0 stop rule fired (2026-10-20)

**Status:** ready to file. The D-numbers are assigned at filing; check the log's last number first (the D-066 /
D-069 collision precedent). Nothing has been appended to `DECISION_LOG.md` yet.

---

### D-0xx · {LC} opened; mechanism accepted: lock-up expiry supply overhang; G0 frozen under the D-086 stop rule
**Status:** RECORDED · **Date:** 2026-10-20 · **Type:** Family opening + mechanism acceptance (D-070 §1) + G0 freeze ·
**Approval authority:** Owner, 2026-10-20: "Open {LC}". The question was asked after the 10-name lock-up sourcing pilot
(`P-M/data_acquisition/09_LOCKUP_PILOT_2026-10-20.md`).

- **Family:** Listing-Lifecycle **{LC}** opens. D-064 had left it unopened after SCREEN-PM-LC-001 passed at screen
  level but concentrated in one era.
- **Mechanism:** POJK 25/2017 lock-ups end 8 months after the effective date. With no practical single-stock
  shorting on IDX, the expected supply concentrates price pressure around expiry.
  - Pre-declared sign: negative.
  - The no-lock-up IPOs (PGEO and CUAN in the pilot) are the pre-declared mechanism control.
  - 12-month "control" pledges are not events.
- **Frozen G0:** `P-M/lockup_lc/G0_FREEZE_LC_LOCKUP_2026-10-20.md`, sha256 `03b40527fc136c00…`, pinned in
  `g0_lockup_power.py`.
  - Cohort: S2's exact listing rule.
  - Window: [E−5, E+20] against the EW liquid book, clustered by expiry month.
  - Floor: 2.0%, from external literature, not from S2.
  - Lock-up share for power: 0.60. Minimum power: 20%.
  - Power comes from placebo-window [E−52, E−27] dispersion only, and no window mean was output.
- **Census:** stays at 613. The arm would count only at registration (N = 614).

**Amendment.** Only by a superseding D-entry.

---

### D-0xx · {LC} lock-up expiry G0: stop rule fired — WITHDRAWN before registration (uncounted)
**Status:** RECORDED · **Date:** 2026-10-20 · **Type:** G0 stop + withdrawal ·
**Approval authority:** the frozen stop rule (preceding entry; precedents D-087, D-094, D-097, D-102).

- **Run.** Once, on 2026-10-20 at 18:55 WIB.
  - Script `g0_lockup_power.py`, sha256 `2f5a6ab4d7a89a24…`. Freeze sha verified.
  - DB: the live `data/walkforward.db`, opened read-only.
  - Output: `G0_RESULT_20261020T185556.json` and `cohort_lc_20261020T185556.csv`.
- **Cohort: 226**, identical to S2.
  - 441 listings since 2015; 215 below the ADV gate.
  - 13 issuance wealth corrections; 27 FORU rows dropped (D-063).
  - Placebo values for **225** events across **86** expiry months. One name had its expiry beyond the data.
- **Stop rule: FIRED.**

  | Measure | Value |
  |---|---|
  | Per-event 26-session excess sd | **25.3%** (the pre-run assumption was 12–15%) |
  | SE over months, all names | 2.17% |
  | SE at a 0.60 lock-up share | 2.80% |
  | MDE at 80% power | **11.6%** |
  | Power at the 2.0% floor | **0.49%**, against the 20% minimum |

  The rule fires even under generous assumptions. With every name assumed locked, power is about 0.9%. With a 5%
  floor, it is about 6.5%.
- **Status: WITHDRAWN.**
  - Never registered, so it is not counted. The census stays at **613** and no HYPOTHESIS_REGISTRY row is added.
  - {LC} stays open with no members.
  - The lock-up sourcing for the 226 names (about 2–3 days) is **not** spent. The 10-name pilot table stays as a
    data record.
- **Pre-outcome facts kept:**
  - Young-listing returns are extremely dispersed: a 25% sd over 26 sessions.
  - **No dated event study on this cohort can reach the census bar at any plausible effect size.**
  - SCREEN-PM-LC-001 (the 252-session young-listing underperformance) remains a screen-level observation only. It
    is not registered and not tradeable as tested.
- **No outcome was read.** No event-window return was computed, and no window mean was output.

**Amendment.** Only by a superseding D-entry.
