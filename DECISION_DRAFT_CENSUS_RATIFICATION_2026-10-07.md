# DECISION_LOG draft: research census ratified at N = 595, the stricter count (2026-10-07)

**Status:** DRAFT. The owner ruled on 2026-10-07 ("use 3.28 as primary bar") that the stricter
recount governs. This entry records that ruling and completes the count.
**Filing:** append to `docs/roadmap/DECISION_LOG.md` on `ops/hardening-2026-07-10`. Use the next
free number at filing, expected **D-071**. The HYP-PM-0016 registration takes the number after it.
**Owner check before filing:** §"Owner choices" below.

---

### D-0xx · Research census ratified at N = 595 under the stricter count; deflation bar ≈ 3.29 for new gates (2026-10-07)

**Context.**

- **Two counts in circulation.** The recorded census on `ops/hardening` is **276**: D-064's 266, plus
  XP-001's 4 arms, plus HYP-PM-0015's 6 configurations (D-067). Its bar is ≈ 3.07.
- **The recount.** On 2026-10-05 the broad-search-v2 recount (`origin/research/broad-search-v2-zcode`,
  `P-M/broad_search_v2/recount/RECOUNT_W0_2026-10-05.md` and `CENSUS_NOTE.md`) counted studies that
  the recorded census never included:
  - 245 script-countable trials from the 2026-09-24/25 chart-pattern studies (13 artifacts in
    `Claude outputs/`, checksummed in place)
  - the double-top study at its upper bound, +20 (counted from notes; no surviving script)
  - a +20 placeholder for the gap-market microstructure battery (no surviving scripts)
  - X1's 6 arms

  That gave **N = 561, bar 3.2745**. It was a draft and never ratified.
- **The recount itself missed three items:**
  1. HYP-PM-0015's 6 configurations. The recount started from 270, not 276.
  2. The 2026-10-06 BOS / trendline-break study, 8 tests (4 arms × 2 eras). Exploratory, unregistered,
     script at `Claude outputs/bos_study_2026-10-06/bos_study.py`.
  3. The 2026-10-07 exit / position-management study. Its 10 non-baseline arms × 2 entry populations
     (E-SN, E-RND) give **20** at the upper bound. Under the recount's own rule, the random-entry
     control counts 0, which would give 10. The upper bound is taken per REVIEW_R1 §1, where
     over-counting only raises the bar.

  Descriptive statistics count 0 under the recount's rule (no trading-rule return statistic). This
  covers the owner's chart questions and the 2026-10-07 opening-minutes volatility profile.

**Decision.**

1. **The census is ratified at N = 595:**

   | Component | Trials |
   |---|---|
   | Recorded at D-064 / XP-001 | 270 |
   | 2026-09-24/25 pattern studies | 245 |
   | Double-top study (upper bound) | 20 |
   | Gap-battery placeholder | 20 |
   | X1 | 6 |
   | HYP-PM-0015 | 6 |
   | BOS / trendline-break | 8 |
   | Exit study (upper bound) | 20 |
   | **Total** | **595** |

   This supersedes the 276 count for every gate from this date. The bar is the exact two-sided
   E[max|Z|] (`deflation_audit/bar_v2.py`): **3.2912 at N = 595**.
2. **Each new gate freezes its bar at 595 + its own configurations**, computed exactly at G0. For
   example, HYP-PM-0016's 4 configurations give N = 599 and bar **3.2931**.

   Bars computed under the 276 count (≈ 3.07) may be **reported as a secondary line only**, and no
   configuration passes on them.
3. **Nothing recorded as dead revives** (the bar only rose). The survivor re-reads of RECOUNT_W0 §4
   stand:
   - FADE avoidance vs the EW book (|Z| 4.4) clears.
   - T1-D (3.84) and S2 / {LC} (3.66) clear. S2 stays era-concentrated and {LC} unopened, per
     D-064 §B.
   - **FADE avoidance vs the IHSG calendar (3.13) no longer clears.** FWD-PM-FADE-001 continues
     unchanged (Research Master Plan §3.2e). Its forward verdict is judged on its own frozen
     protocol, not on this bar.
4. **The two placeholder lines (the double top at its upper bound, and the gap-battery +20) stay
   until their trials are reconstructed from session records.** Reconstruction may only replace a
   placeholder with an exact count at or above its value. A lower reconstructed count needs its own
   superseding entry with evidence.
5. **Exploratory studies count from now on.** An exploratory study with a reported return statistic
   is added to the census at the time it is run, whether or not it's registered:
   - filed in `CENSUS_UPDATE.md`
   - with its script committed or checksummed
   - in the same session

   This closes the F-1 gap that left 300+ trials uncounted.

**Multiplicity.** No family is narrowed (D-028). Hypotheses keep their family counts (X8). This
entry only raises the program-wide census, which is append-only and monotonic. No wall-clock decay
(invariant 12).

**Amendment.** Only by a superseding D-entry.

---

## Owner choices before filing (not part of the entry text)

- **(a) Exit-study count: 20 (upper bound) or 10 (random-entry control counted 0).** The draft uses
  20. With 10, N = 585 and the bar is 3.286. The difference is negligible.
- **(b) RESOLVED 2026-10-07: owner chose 3.29 (N = 599); ZCode Revision 2.** The sniper's frozen bar. Your ruling set the primary bar at "3.28" (N = 565, 3.2765). The
  complete count gives N = 599, **3.2931**.
  - Recommendation: freeze HYP-PM-0016 at **3.29** (N = 599), so the predeclaration matches the
    ratified census. That's a one-constant change to session A's Revision 1 before approval.
  - If you prefer to keep 3.28, the draft's §2 example changes, and the sniper's HANDOFF must
    disclose the gap.
