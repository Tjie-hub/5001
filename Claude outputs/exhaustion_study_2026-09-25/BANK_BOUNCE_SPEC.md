# FROZEN SPEC — Bank climax-low bounce, pre-2021 out-of-sample test
Frozen: 2026-09-25, BEFORE any pre-2021 result was computed. One run, no re-tuning.

Origin: in-sample 2021-10..2026-06 (exh_confirm_grid.py BASE, DOWN): BBCA n24 +3.14%/10d hedged, win 79%, t 3.41;
BIG-4 n103 +1.22%, t 2.55. Found after ~120 exploratory tests on 2021-26 the same day.

Data: research/rulecard/data.py::load_extended_ohlcv (pre-2021 yfinance backfill + DB), rows with date <= 2021-09-30 for EVENTS
(forward window may run past it). Nothing from 2021-10+ is used for events.
Names: PRIMARY = BBCA. SECONDARY = BIG-4 pooled (BBCA, BBRI, BMRI, BBNI).
Name guard (replaces ADV>=10bn, which pre-2010 nominal values would fail): bar present (finite close) on >=18 of last 20
panel sessions and on the entry day; no >36% 1-day move in last 21 sessions.
Event (identical to in-sample): close = 20-session closing low AND (SMA20 - close) >= 2.0 x ATR14 (Wilder, true range).
Dedup: 10 sessions per name. Needs >=60 bars of history.
Trade: buy at open of next session; exit at close of the 10th session (entry day = session 1). Cost 0.60% round trip.
Hedge: minus EW mean of the same open->close window over the "book" = names with ADV20 >= Rp 1bn, close >= 50,
traded >= 18/20, no >36% move in 21 (extended panel; no index series exists in the DB).
Statistic: mean of hedged net return; t = mean / se over MONTHLY means (clustered by entry month).
PASS (PRIMARY): BBCA hedged mean > 0 AND t >= 2.0.   SECONDARY pass: BIG-4 hedged mean > 0 AND t >= 2.0.
Descriptive only (cannot rescue a fail): raw net, median, win rate, 20-session hold, sub-periods <=2009 / 2010..2021-09,
per-bank, exclusion of the single best trade.
