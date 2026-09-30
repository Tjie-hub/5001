# 07 · OHLCV before 2021-07 (incl. delisted) — FEASIBILITY MEMO · 2026-09-30

**Item (planner task 3B):** can the pre-backfill price panel be deepened — and can the
delisted-name blind spot be closed — from reachable sources? Scoping + POC probes only;
no backfill, no DB writes. POC: `poc_pit_fundamentals_ohlcv.py` (this directory).

## Verdict

**Free sources deepen nothing that matters and cannot close the delisted gap.** Survivor
names already have deep free history (and the repo's backfill `hist_pre2021.pkl` IS the
yfinance source); confirmed-delisted names are **purged from Yahoo**; the only true recovery
paths (IDX-direct or paid vendor) sit behind the same Owner decision as memo 06. The
survivorship blind spot stands, with its known sign: for AVOID-side results it biases
*against* the effect (worst names missing), recorded in every spec since S2.

## POC results (2026-09-30, yfinance 1.2.0)

| probe | rows | first | last | reading |
|---|---|---|---|---|
| BTEL.JK (delisted — Bakrie Telecom, forced delisting ~2019) | **0** | — | — | **delisted names are purged from Yahoo** — the blind spot is confirmed, not hypothetical |
| ELTY.JK | 6,020 | 2002-06-13 | 2026-09-30 | deep history where the name survives |
| DUTI.JK | 6,131 | 2002-01-09 | 2026-09-29 | same |

Corpus-side survivorship count (already recorded in S2): **54 of 929** `ohlcv_long` names end
before 2026; pre-2021 the panel is the yfinance backfill, so anything Yahoo purged before the
backfill's fetch date is absent by construction.

## Sources, ranked

1. **yfinance `.JK` (free, scriptable)** — depth for survivors to 2002 and earlier (POC);
   zero depth for the delisted (BTEL probe). Marginal value of a systematic refetch: gap/corporate-
   action repair for survivors only — the backfill already did this pass. Effort: 1–2 days for a
   full survivor audit; **does not touch the delisted gap**.
2. **IDX/KSEI historical daily summaries (Ringkasan Saham, daily files back to ~2011)** — would
   cover delisted names while listed. Same Cloudflare wall as memo 06 (POC probe 3: HTTP 403);
   Owner ToS ruling required before any retrieval engineering. Effort post-ruling: 4–6 days
   (daily files, year by year) + storage.
3. **Kaggle/community datasets** — stale one-off snapshots, unknown method, no update path;
   not a corpus-grade source. Not recommended beyond cross-checks.
4. **Paid vendor (Refinitiv/Nasdaq Data Link/regional vendors)** — full delisted history with
   corporate actions; cost decision for the Owner. Effort once licensed: 2–3 days.

## Effort summary if the Owner pursues this

- Survivor-panel audit via yfinance: 1–2 days, free, low value (backfill already covers it).
- Delisted recovery to 2012: **only via Owner-authorized IDX retrieval (4–6 days) or a paid
  vendor (2–3 days + cost)**. Free-only acquisition cannot do it — demonstrated by the BTEL
  probe, not assumed.
