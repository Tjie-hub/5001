# FWD-PM-BANK-001 — PROTOCOL (FROZEN)

**Status:** FROZEN 2026-10-05T16:09:16+00:00 on Owner approval ("Approve and push", 2026-10-05) of
[[OWNER_DECISION_PACKAGE_R2_BANK_2026-10-05]]. Changes only via an append-only deviation_log.md entry.

## 1. Claim (HYP-PM-0014, proposed)
After a **2-ATR climax low** in a big-4 Indonesian bank, the next 10 sessions return **more than the
market**: liquidity provision to forced sellers in the most liquid names (the I5 inventory-imbalance
mechanism, expressed in OHLCV only).

## 2. Signal (identical to the 2026-09-25 study and `jurnal26/bank_alert.py`; do not tune)
- Universe: **BBCA (primary)**, BBRI, BMRI, BBNI (secondary, pooled).
- Day t fires when close_t = lowest close of the last 20 sessions (t included) **and**
  close_t <= SMA20_t - 2 * ATR14_t (ATR = simple mean of true range, 14 sessions).
- De-duplication: a firing within 10 sessions of the previous firing of the same name is the same event.
- Entry: open of t+1. Exit: close of t+10. Prices: `ohlcv` is_final=1 (raw).
- Void (not written, not scored): a window holding a session with |ret| > 35%, a split, or a
  rights/bonus/reverse-split event (`corporate_action_events`): price steps that are not returns.
  (Chosen instead of issuance adjustment because voiding needs no adjustment model; FADE convention.)

## 3. Endpoints
- **Primary:** BBCA net 10-session return minus the equal-weight liquid book (ADV20 >= Rp 10 B) over the
  same window, net = gross - 0.60% round trip (cost authority). Bar: mean > 0 with one-sided t >= 2.0
  at decision time.
- **Secondary:** big-4 pooled, same endpoint; BBRI alone reported.
- **Reported beside, never decisive** (FADE DEV-001 lesson): gross contrast (no-information null = 0)
  and IHSG-relative excess.

## 4. Decision rule (Phase 5 forward-test rule, gate config forward_test_rule)
- Read at N >= 15 primary events, or 36 months, whichever first. BBCA fires ~3-5 x/year, so the
  expected read is **2029-2030**; the pooled secondary (~10-15/yr) gives an interim read in ~1-1.5 years.
- GO: primary mean net excess >= +0.50% and t >= 2.0. NO-GO: mean <= 0. Otherwise inconclusive at the
  time box. No early stop for good news; early stop only for a data or protocol defect (logged).

## 5. Evidence carried in (for context, not re-tested)
- In-sample 2021-10..2026-06: BBCA n 24 +3.14%/10d hedged, t 3.41 (selected after ~120 tests that day).
- Frozen pre-2021 OOS (2000-03..2021-09, one run, 2026-09-25): BBCA n 56 +1.64% t 2.36 (PASS vs bar 2.0);
  big-4 n 298 +0.76% t 2.23 (BBRI +2.02% t 3.04, BMRI +0.24%, BBNI -0.50%).
- Program deflation guard (D-064): |t| 3.06 @ N=266. The OOS t 2.36 is a single confirmatory test against
  its own pre-set bar, not a discovery; the forward test is what decides.

## 6. Recorder
`run_recorder.py` (tests: `tests/test_forward_bank_recorder.py`): appends CLOSED events to `ledger.json`
from `opened_utc` on, never back-fills, writes a row only when every leg is present; cron 09:40 daily
(after the 16:15 EOD is_final write of the previous session). Validated on history: reproduces the
study's event counts exactly (BBCA 25, BBRI 32, BMRI 25, BBNI 27 since 2021-07).
