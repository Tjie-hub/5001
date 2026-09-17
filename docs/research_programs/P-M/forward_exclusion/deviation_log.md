# FWD-PM-VOLEX-001 — deviation log

Append-only. Never rewritten. Every entry is dated and states what changed,
why, and whether any outcome was visible at the time.

---

## DEV-001 · 2026-09-16 · first formation regenerated on repaired price data

**What changed.** The first formation was regenerated and now sits on a
different session.

| | original | corrected |
|---|---|---|
| formation date | 2026-09-14 | **2026-09-15** |
| fingerprint | `2d646cf063a69a99` | `f264c69d053a80bc` |
| cut point (annualised range vol) | 82.66% | 82.86% |
| universe / held | 200 / 180 | 200 / 180 |
| excluded — added | — | **BAPA** |
| excluded — removed | **KBLV** | — |

Nineteen of the twenty excluded names are unchanged.

**Why — two independent causes, both blind to any outcome.**

1. *Corrupted panel.* Session 2026-09-07 was holding 778 bars stranded at
   `is_final=0` — an EOD-scraper run that never completed. Every `is_final=1`
   query, including this one, therefore saw 137 of 915 tickers on that date,
   and 2026-09-07 sits inside the trailing 60-session Parkinson volatility
   window used to rank the universe. `scripts/repair_provisional_bars.py`
   repaired 2,349 stranded bars across six sessions on 2026-09-16
   (2026-07-08, 07-22, 08-20, 08-26, 09-01, 09-07); 1,467 of them carried a
   materially wrong close.

2. *Session completeness moved.* At 06:50 UTC, when the original formation ran,
   2026-09-15 showed only 824 finalised rows — still mid-finalisation — so the
   protocol's §session-guard rejected it and the run fell back to 2026-09-14.
   By 13:00 UTC that session had finished finalising (914 rows, 0 provisional)
   and legitimately became the latest complete session. The guard behaved
   exactly as specified in both runs; the underlying data changed between them.

**Was any outcome visible?** No. Both runs occurred on 2026-09-16 and no
outcome can mature before ~2026-10-15 (entry `close(t+1)` + 21 sessions). The
ledger held zero matured outcomes throughout. This is a data-quality
correction made blind — it cannot have been influenced by, and could not
influence, any result.

**What did NOT change.** The frozen spec — universe rule, estimator, exclusion
fraction, entry convention, horizon, benchmark, decision rule, session guard —
is untouched. No formation was added or removed; the single first formation
was recomputed.

**Lesson carried into the protocol.** A formation taken on the same day as the
session it forms on is exposed to mid-finalisation state. Future runs fire
Mondays 07:30 WIB against the previous week's sessions, which are settled long
before — but the guard, not the schedule, remains the control.

**Superseded record.** The pre-repair ledger is preserved verbatim at
`superseded/ledger_2026-09-16_pre_repair.json`.
