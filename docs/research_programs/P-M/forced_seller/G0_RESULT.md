# D-096 forced-seller reversal — G0 result (2026-10-14)

Freeze: 4dee5ec. Script: g0.py (reads no 2025+ return; power from 2023-24 price-only drop days).

Stop rule (D-086, inherited, frozen before power): **FIRED.**
- Pre-sample: 9,083 liquid drop days on 475 dates; sd of 5-session excess return 11.6%.
- Event-minus-control SE 0.63%; MDE at 80% power 2.6%; **power at the 0.30% floor 0.24%** vs the 20% minimum.
  Second-half-only judgement: SE 0.90%, power 0.15%.
- Sensitivity: even with SE halved to 0.3%, power at the floor would be about 1%.

Pre-outcome facts (2025-01-02 -> 2026-10-13, counts and correlations only):
- 500 events on 215 dates (211 first half / 289 second half, split 2025-12-10); 4,325 controls on 336 dates.
  Top-5 dates hold 13.4% of events (2026-05-29 alone 23).
- FS is not a drop-size proxy (Spearman with day return -0.004) but IS a volume proxy:
  Spearman with volume ratio 0.63; median volume ratio 2.6 for events vs 0.53 for controls.
  So the event is mostly high-volume (MAPI 10-12, at 1.1x, is atypical), and the declared
  Campbell-Grossman-Wang interaction cannot be separated from the event itself.
- Spearman FS vs Parkinson-60 volatility -0.43; vs concentration share 0.41.

Status: not registered, not counted. Census stays 612.
