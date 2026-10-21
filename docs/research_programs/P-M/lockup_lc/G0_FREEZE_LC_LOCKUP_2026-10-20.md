# G0 FREEZE — {LC} lock-up expiry (supply overhang) · 2026-10-20

**Status of this file.** It is a DRAFT D-entry plus the G0 freeze. It was frozen **before any power number was
computed**, and `g0_lockup_power.py` pins its sha256 and refuses to run if the file changes.
- Nothing has been appended to `DECISION_LOG.md` and nothing is registered.
- **No return in any event window has been read.** The G0 reads only the cohort's names and dates, plus return
  dispersion in a pre-event placebo window. Means are never printed.
- Census stays at **613**.

**Approval.** The owner answered "Open {LC}" on 2026-10-20. The question was put after the lock-up sourcing pilot
(`data_acquisition/09_LOCKUP_PILOT_2026-10-20.md`), as the next step so the lock-up work could continue. The
D-number is assigned at filing.

---

### D-0xx · {LC} opened; mechanism accepted: lock-up expiry supply overhang; G0 frozen under the D-086 stop rule

- **Family.** **Listing-Lifecycle {LC}** opens with this entry. D-064 left it unopened after SCREEN-PM-LC-001
  (young-listing avoidance) passed at screen level but was concentrated in one era. This arm would be slot 1.
- **Mechanism (forced supply, not price prediction; D-070 §1).**
  - Under POJK 25/POJK.04/2017, holders who acquired shares below the IPO price within 6 months before filing
    may not transfer them until **8 months after the registration statement becomes effective**.
  - The expiry date is public at listing. On IDX there is no practical single-stock short selling, so the
    expected supply cannot be pre-sold by arbitrageurs. Price pressure therefore concentrates around expiry
    (Ofek and Richardson 2000; Field and Hanka 2001; Brav and Gompers 2003).
  - **Pre-declared sign: negative** excess return around expiry.
  - **Rival:** generic young-listing underperformance (Ritter 1991), which S2 already measured at the
    252-session horizon.
  - **The mechanism is separated from the rival by a pre-declared secondary.** IPOs whose listing announcement
    states **no** POJK-25 lock-up (PGEO and CUAN in the pilot) get a pseudo-expiry at the same age. A supply
    mechanism predicts the effect in lock-up IPOs only.
- **Distinctness.** S2 holds from listing + 26 sessions for 126 or 252 sessions. This arm is a **dated supply
  event inside that window**. It overlaps S2 by construction, which is disclosed. S2 is a screen and is not
  registered, so no registered test is duplicated.
- **12-month control pledges are not events.** A controller's 12-month pledge "not to transfer control"
  restricts control, not shares. It is never coded as an expiry.

#### Frozen design

| Item | Frozen value |
|---|---|
| Cohort | SCREEN-PM-LC-001's listing rule exactly: first panel bar in [2015-01-01, 2026-09-16], not on a corpus coverage-start date, flagged at own session `n_prior = 25` with trailing ADV20 ≥ Rp 5bn (`screen_s2_listings.build_flags`). FORU excluded from 2026-09-14 (D-063) |
| Lock-up flag (G1) | From the IDX "Pengumuman Pencatatan Efek" for each IPO: yes / no / unknown. Unknown is excluded and counted |
| Event date E | Effective date + 8 calendar months, snapped to the first session on or after. **G0:** effective ≈ the session 8 sessions before the first bar. **G1:** the sourced effective date where available, otherwise the same estimate (pre-declared; the share estimated is reported) |
| Window | Daily returns on sessions **[E−5, E+20]** (26 returns): entry at close(E−6), exit at close(E+20) |
| Outcome | Compounded name return minus compounded equal-weight liquid-book return (`events._book`, ADV20 ≥ Rp 1bn) over the same sessions. Wealth-corrected panel (S2's primary lens) |
| Inference | One value per expiry calendar month (mean over that month's lock-up events). t = mean / (sd / √M) over months with at least one event |
| Pass (G1) | t ≤ −bar **and** both halves (entries before / on or after 2021-07-05) negative **and** the no-lock-up pseudo-expiry contrast in the same direction. The bar is recomputed at registration (≈ 3.3001 at N = 614) |
| Effect floor | **2.0%** over the 26-session window. From external literature (US expiry CARs about −1% to −3%), **not** from S2 |
| Minimum power | **20%** at the floor (D-086 stop rule) |
| Lock-up share for power | **0.60** of the cohort. Conservative against the pilot's 6 of 8 |

#### Power method (G0; frozen)

1. For every cohort name, take a **placebo window** of 26 sessions ending at **E−27**, i.e. sessions
   [E−52, E−27], and require the session coverage there. That window lies wholly before the event window and
   after the flag row.
2. Compute that window's excess return as in the outcome definition, assign it to E's calendar month, and take
   the cross-month sd of the monthly means: **SE_full = sd / √M**.
3. **SE_lock = SE_full / √0.60.** Power = Φ(floor / SE_lock − bar), one-sided because the sign is
   pre-declared. MDE at 80% = (bar + 0.8416) × SE_lock.
4. Only dispersion, SE, MDE, power and counts are printed or stored. **No mean of any window is output.**
5. **If power < 20%, the stop rule FIRES.** The arm is **WITHDRAWN before registration and not counted**
   (precedents D-087, D-094, D-097, D-102). {LC} stays open with no members, and the lock-up sourcing (about
   2–3 days for 226 names) is not spent.
6. **If power ≥ 20%:** source the flag and effective date for the whole cohort (an owner ToS ruling is needed
   to script it), then registration, then one G1 run.

#### Disclosed pre-run arithmetic (assumption, not a measurement)

- A 26-session excess sd of about 12–15% for young mid caps and about 120 lock-up events over about 100 expiry
  months give SE_lock ≈ 1.2–1.5%.
- That puts the MDE at 80% at about 5–6% and **power at the 2% floor at roughly 3–8%**. **The stop rule is
  expected to fire.**
- This G0 exists to confirm that cheaply before any sourcing is spent.

#### Disclosures

- S2's outcome is known: PASS, strongest at h126 after 2021. The floor, window and sign come from the mechanism
  and the external literature, not from S2.
- The 10 pilot names were sourced for terms only; no return was read.
- The snapshot behind S2 (`walkforward-20260928-213012`) may now sit on the 2 TB archive drive. The G0 runs on the
  path given by `--db`, default the live `data/walkforward.db` opened read-only, and records that path. The cohort
  may differ from S2's 226 by onboarding changes since 09-28; the count is reported.

**Amendment.** Only by a superseding D-entry.
