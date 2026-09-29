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

---

## DEV-002 · 2026-09-23 · scorer waits for complete entry and exit sessions

**What changed.** `score()` in `run_forward.py` now returns no outcome (the formation stays pending)
unless BOTH the entry session d0 = close(t+1) and the exit session d1 = d0 + 21 sessions pass the
protocol's existing session-completeness guard (priced-ticker count >= 95% of the trailing-20-session
median). While either fails, the run prints `[wait]`; once at least 10 later complete sessions exist
and it still fails, it prints `[stuck] ... Owner decision required`. No automatic fallback date is
ever chosen. Patch: `DEV-002_score_completeness.patch`.

**Why.** The guard protected formation dates only. `score()` indexed the raw session list, and its
`basket()` applies `dropna()`, so an exit on a partial fetch silently removed every name without a
final close that day from both books. Outcomes are never re-scored, so the degraded result would
have been frozen into this append-only ledger. The hazard is live, not theoretical: on 2026-09-23 the
provisional-bars check reported 2026-09-16 (868 final / 46 provisional), 2026-09-18 (110 / 806) and
2026-09-21 (91 / 823) stranded, and 2026-07-09 and 2026-07-24 thin (~15% of norm). The suspension
audit found 794 names missing at exit across its backtest arms on the raw calendar, and 5 with
partial sessions excluded.

**Was any outcome visible?** No. The ledger holds one formation (2026-09-15), `outcome: null`; the
earliest possible maturity is d1 ≈ 2026-10-15. The change was designed from a code reading and a
backtest audit, blind to any forward result.

**What did NOT change.** Universe, estimator, exclusion fraction, entry convention (close(t+1)),
horizon (21 sessions, still counted on the raw session list, so d0/d1 are the same dates as
before), benchmark, endpoint, decision rule, formation cadence and formation guard. Names missing on
an otherwise COMPLETE exit session (genuine suspensions) are still dropped exactly as before. That
behaviour is out of scope here; the audit measured it at 5 names over ~47 periods.

**Residual risk, stated.** A session that never finalises blocks scoring of any formation that
enters or exits on it. That is deliberate: a missing outcome is recoverable, a wrong one in an
append-only ledger is not. `[stuck]` hands the case to the Owner. The standing remedy for a stranded
session is `scripts/repair_provisional_bars.py --apply`.

---

## OBS-2026-09-29 · Issuance ex-dates inside the first holding window — observation, NO deviation

**Detected by** `scripts/check_issuance_windows.py` (new under D-064 §D; detection only, never edits
the ledger). Formation 2026-09-15 holds two names whose rights-issue ex-date falls inside the
21-session hold (entry close 2026-09-16 → d1 ≈ 2026-10-15):

- **BUVA**: rightissue ex 2026-09-25 (m 1.25, c 62.5), HELD.
- **ENRG**: rightissue ex 2026-10-05 (m 1.5, c 155), HELD.

The research price corpus is split-adjusted only (D-063/D-064), so each prints a mechanical step.

**Why no deviation.** Both names are in the 180-name HELD leg, and the benchmark is the equal-weight
**same 200-name universe**. The step therefore enters both sides with weights 1/180 vs 1/200: net
effect on the spread ≈ step × (1/180 − 1/200) ≈ **0.01%** for a −20% step. That is immaterial
against the decision rule. The frozen protocol is unchanged, the formation is scored as specified,
and this note exists so the question is on record before the outcome is visible (`outcome: null`).

Five further names (BNBR, ENRG 08-14, SINI, COCO, PADI) have July–August ex-dates inside the
Parkinson-60 **lookback**. The estimator is range-based (ln(high/low) per day), so a close-to-close
gap barely moves it. This is reported as information and is not a contamination claim.
