# D-096 forced-seller reversal — G0 FREEZE (written before any power or outcome number)

Frozen 2026-10-14, from the counts in D-096 only (no event outcome read).

- Instrument: FS = (largest single-broker net sale, retail R = {XL,XC,YP,PD,KK} excluded as sellers) / ADV20.
  ADV20 = prior-20-session mean of close x volume (ohlcv). Liquid = ADV20 >= Rp 5bn.
- Event: FS >= 0.5 and day return <= -3%.  Control (drop-only): FS < 0.1 and day return <= -3%.
- Primary outcome: next-session open -> close of t+5, net of 0.60% round trip (D-082),
  minus the same-date equal-weight liquid cross-section. Claim = event minus control, date-clustered.
- Window: 2025-01-02 -> last date with t+5 available. Both calendar halves must be > 0.
- Bar: 3.2996 (N = 613 if registered). Secondary (volume ratio) is reported, not gating.
- Stop rule (D-086, inherited unchanged): effect floor 0.30% net per 5-session claim,
  minimum power 20% at that floor vs the bar. If power < 20% the arm is WITHDRAWN, uncounted.
- Power is estimated only from a pre-sample (2023-01 -> 2024-12) of PRICE-ONLY drop days
  (day return <= -3%, liquid); the 2025+ window and any FS event outcome are not read.
