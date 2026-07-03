# Walk-Forward Tuning Protocol (Phase 2B, audit C-6 / parameter leakage)

## Why this exists
The audit found strategy parameters (TFB gates/trail, Panic v3, momentum
thresholds) were chosen from full-history studies that INCLUDE every window the
walk-forward later "validates" on. That is in-sample tuning wearing an OOS
costume. This protocol fixes the process; the code (walk_forward_split, the
metric fixes in walkforward_multi.py) only makes the measurement honest.

## Rules
1. **Freeze before validate.** Any parameter (entry threshold, ATR mult, gate
   cut) is chosen on a TUNING span that ends strictly before the first window
   whose score will be reported. Default tuning span: 2021-07 .. 2023-12.
   Default reported-OOS span: 2024-01 onward.
2. **Embargo.** Leave >= 1 test-window (3 months) gap between the end of tuning
   data and the start of reported OOS, so a trade opened near the tuning
   boundary cannot exit inside reported OOS.
3. **One knob at a time, pre-registered.** Record the hypothesis + the exact
   param grid BEFORE running. No post-hoc "best of N" without reporting N
   (multiple-testing inflates apparent edge).
4. **Report sample size.** Every published metric carries windows_tested and
   pooled total_trades (now emitted by _summarize_strategy). A consistency %
   on < 8 windows or an expectancy on < 20 pooled trades is not actionable
   (wf_edge already enforces N_MIN_TRADES=20).
5. **Gate meaning.** On the 5y corpus a ticker gets ~16 OOS windows; the live
   gates BLACKLIST=33% (~5/16) and MIN_CONSIST=50% (8/16) are now defensible.
   Do not lower them to admit more names.

## What is NOT yet solved (tracked)
- Point-in-time index membership (which names were in LQ45/IDX80 on each past
  date). The corpus is survivorship-inclusive for names still fetchable, but
  fully delisted names have no history. Flagged for a future PIT-universe task.
- Split-adjustment in research: raw prices show splits as discontinuities;
  corporate_actions (Phase 2A) is the substrate for adjusting when a study
  needs it. No strategy currently adjusts; document per-study.
