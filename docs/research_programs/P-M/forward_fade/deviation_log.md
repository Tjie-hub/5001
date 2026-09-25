# FWD-PM-FADE-001 — deviation log

Append-only. Never rewritten. Every entry is dated and states what changed, why, and whether any
outcome was visible at the time.

---

## DEV-001 · 2026-09-24 · gross contrast and overlap-robust t reported beside the frozen statistics (observability only)

**Authority.** DECISION_LOG D-057. Owner instruction on 2026-09-24 ("approve all"), option (b) of
`docs/research_programs/AUDIT_2026-09-24_RESULT_VALIDITY.md` §4.

**What changed.**
- Nothing in PROTOCOL.md §2 or §3. The PROTOCOL.md sha256 stays `e1959672…`.
- Nothing in `ledger.json`, `run_recorder.py` or `scripts/fade_failed_breakdown.py`. SHA256SUMS
  unchanged.
- **Added:** `P-M/forward_robust/robust_report.py`, a read-only report (tests:
  `tests/test_forward_robust_report.py`).
  - **When:** at every read (3-month interim, 12 and 18 months), next to the frozen net t on both
    benchmarks.
  - **What it reports:**
    - the **gross** contrast (`gross_return − benchmark`, whose no-information null is 0) against
      IHSG and the EW-book;
    - for net and gross: month-cluster t and Driscoll-Kraay t with L = 20;
    - for gross: calendar-time portfolio t (NW(5)).

**Why.**
- **Cost on one leg.** The frozen endpoint subtracts the 0.60% round trip from the signal leg only,
  against gross benchmarks. A pattern with no information therefore scores −0.60%. The frozen null of
  0 is not the no-information null.
- **Entry-date clustering.** The frozen t clusters on the signal date while the 20-session holds
  overlap.
- **Audit evidence** (in-sample, h20, same spec):

  | benchmark | net t | gross | month t | DK t | calendar t |
  |---|---|---|---|---|---|
  | IHSG | −5.7 | −0.86% | −1.65 | −1.86 to −1.98 | −3.13 |
  | EW-book | −8.2 | −0.89% | −3.56 | −3.85 to −3.96 | −4.42 |

  - The holding-window guard, corporate-action windows and a symmetric EW-book guard each moved these
    by 0.01 percentage point or less.
- **Read through the §3 rule:** P(PROMOTE at 18 months | no information) ≈ 3–14%, against about 0.1%
  intended.

**Was any outcome visible?** No. `ledger.json` holds **0 signals**: sha256 `cb2de076…`, unchanged since
2026-09-21 01:49 UTC. The first h=20 leg cannot close before about 2026-10-20. The report was written
and tested on synthetic ledgers only.

**What did NOT change.**
- Signal, constants, contamination guard, dual benchmarks, net endpoint, entry-date inference,
  checkpoints, thresholds and dead-signal guard.
- **The §3 rule remains the only decision.**

**Pre-declared reading.**
- If §3 yields PROMOTE-track or PROMOTE while the **gross** calendar-time t on either benchmark is
  > −2.5 (12 months) or > −3.0 (18 months), the read is recorded as **"PROMOTE under the frozen rule;
  not confirmed on the gross contrast under overlap-robust inference."**
- Any action on that disagreement, including whether the signal may enter BOOK_OVERLAY_POLICY, is a
  separate Owner decision.
