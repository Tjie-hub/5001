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

---

## DEV-002 · 2026-10-20 · contamination guard measured over the holding window, as §2 states (recorder only)

**Authority.** DECISION_LOG D-104. Owner instruction 2026-10-19 ("fix") on the strategy logic check
(`docs/audit/IDX_FULL_AUDIT_2026-10-19.md` §5, T2).

**What changed.** `run_recorder.py` computes `bad_{h}` with `s.shift(-h).rolling(h, min_periods=1).sum()`,
which sums sessions t+1 .. t+h: the holding window §2 names ("any session in its holding window"). The
frozen line `s.shift(-1).rolling(h, min_periods=1).sum()` is right-aligned, so it summed t−h+2 .. t+1: the
h−2 sessions before the signal, the signal day and the entry day. A split on day 12 of the holding window
was therefore kept and one 5 sessions before the signal voided the signal. Test:
`tests/test_forward_fade_recorder.py` (h = 5 flags rows 15–19 for a bad row 20; the frozen form flags 19–23).

**Why.** §2 defines the window in words, and the frozen script's own comment says "contamination anywhere
in [signal+1 .. signal+h]": the code contradicted both. The same line sits in the frozen
`scripts/fade_failed_breakdown.py` and in `P-M/forward_regime/scripts/panel.py` (about 15 research
scripts reuse it); "three independent implementations agree" (PROTOCOL §1, §2) were copies of this line.

**Was any outcome visible?** No. `ledger.json` holds **0 signals** (sha256 `cb2de076…`). On the registered
in-sample data (through 2026-07-29, the frozen script re-run 2026-10-19) the protocol window moves the
h=20 result from −1.46%, t −8.16 to −1.49%, t −8.35 vs the EW book, and from −1.44%, t −5.61 to −1.48%,
t −5.73 vs IHSG: 43 contaminated signals had been kept (mean +5.9%, mostly >35% up-moves) and 56 clean
ones voided. The registered evidence stands; the frozen script and its SHA256SUMS are untouched. A dry run
on 2026-10-20 (counts only): 570 signals since opening, 21 with a closed h=20 window, 0 voided under either
window, so the first rows (09:35 today) are identical either way.

**What did NOT change.** Signal, universe, entry/exit, horizons, cost, benchmarks, inference, decision
rule, ledger schema and the frozen script. Voided signals are not stored, so nothing needs re-writing.
