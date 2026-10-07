# OWNER DECISION PACKAGE — widen P-M · Price-Reversal {R1} -> {R1, R2}, register HYP-PM-0014, open FWD-PM-BANK-001

**Prepared:** 2026-10-05 (Claude Code, Dell) after Owner instruction "fix all" (gap 1 of the
literature comparison: "no live proof of the bank edge"). **Nothing below is applied yet.** One Owner act
approves all three parts; the texts apply verbatim.

## 1. What is decided
1. **Family:** widen **P-M · Price-Reversal** from {R1} to **{R1, R2}**. R2 = OHLCV-only short-horizon
   *positive* reversal after a volatility climax in mega-cap liquid names.
   - Why widen instead of opening a new family: invariant 12 scopes families by data epoch + feature
     space. R2 uses the same feature space as R1 (OHLCV short-horizon reversal). A new family would be a
     split that resets multiplicity, which PG-3/PG-6/R7.5 forbid. Widening is allowed by formal
     amendment (D-028) and costs R1 nothing it already has.
   - Consequence: the family's registered count goes 1 -> 2 and both members are judged with that count.
2. **Register HYP-PM-0014** per [[PROTOCOL]] (frozen) (freeze to PROTOCOL.md, sha256 recorded at approval).
3. **Open FWD-PM-BANK-001**: write `run_recorder.py` + tests, add one cron line after the 16:15 EOD
   write (like FWD-PM-FADE-001 at 09:35), record from the registration timestamp, no back-fill.

## 2. Honest risks the Owner is accepting
- **Selection:** BBCA was picked after ~120 looks that day; the OOS pass was one test at t 2.36, below
  the program deflation bar 3.06. Registration does not claim validity; it buys a clean forward test.
- **Time:** primary read needs N >= 15 BBCA events, about 3-4 years. The pooled secondary reads sooner
  but BMRI/BBNI did not pass OOS individually.
- **Effect size halved** OOS (3.14 -> 1.64), the usual post-selection decay (McLean & Pontiff 2016).
- The personal Telegram alert (`jurnal26/bank_alert.py`) already fires on the same rule; it is not the
  recorder and is not evidence.

## 3. Texts applied on approval
- **DECISION_LOG** new entry: "D-0xx · P-M Price-Reversal widened {R1} -> {R1,R2}; HYP-PM-0014 registered
  (bank 2-ATR climax-low liquidity provision); FWD-PM-BANK-001 opened. Approval authority: Owner
  <date/quote>."
- **HYPOTHESIS_REGISTRY** row: `HYP-PM-0014 | P-M · Price-Reversal {R1,R2} (R2) | big-4 bank 2-ATR climax
  low -> 10-session excess vs EW liquid book (BBCA primary) | REGISTERED -> IN_TESTING | PROTOCOL.md
  sha256 … | family slot 2`; family-slot ledger row updated to **2**.

## 4. Owner act
Reply **"approve R2"** (or amend). Without it nothing is registered and the alert stays a personal alert.
