# DIAGNOSIS — minute-bar volume under-capture in stockbit_flow_bars · 2026-10-09

**Read-only audit** (no outcomes, no census arms). Branch
`research/data-audits-2026-10` @ b26198a. Data: pinned 2026-10-08 walkforward
snapshot (`a2d7e675…`, fingerprint `9c26e0df…`), `stockbit_flow_bars`
2025-01-02 → 2026-10-07 (416 sessions, 900 tickers, 102,963,190 rows), one grouped
query per month (rule from the brief; the full-table GROUP BY is slower than the
sum of monthly scans). Runtime: **11.1 min** (monthly scans 6–44 s each).

## TL;DR — the bars did not break; the denominator did

**Root cause: a vendor-side definition change. From 2026-07-06 (permanent from
2026-07-10) the daily OHLC endpoint (and the minute print tape) reports
CONSOLIDATED volume — including the negotiated market (NG) — while the
trade-book chart endpoint's cumulative buy/sell counters remain
REGULAR-MARKET-ONLY, as they always were.** The "capture" ratio
(max cum buy_lot + max cum sell_lot) × 100 / ohlcv volume therefore fell from a
median of exactly **1.000** to **0.576** (min 0.481): the ~43% that "went missing"
is NG volume the trade-book endpoint has never carried. It is not missing bars,
not a truncation, not a fetch-time regression, and not a bug in our pipeline.

## Evidence chain

1. **Break date:** first bad days 2026-07-06/07 (median capture 0.574/0.588),
   recovered 07-08/09 (1.000 — the vendor flip-flopped), permanently degraded from
   **2026-07-10** onward. Pre-break median 1.000 (p25=p75=1.000 — the ohlcv volume
   and the flow counters were the SAME number); post-break 0.576 (IQR ≈ 0.47–0.77).
2. **Not missing bars / time-of-day / auction:** post-break days carry exactly the
   same structure — 335 bars per ticker per day, modal last bar **16:14**, ~825
   tickers/day — identical to pre-break. There is no intraday window missing.
3. **The denominator doubled, the numerator didn't:** market-wide daily ohlcv volume
   jumped 15.8G → 31.8G shares on 07-06 (and 20.5G on 07-10, 45.8G by 07-14,
   83G by 10-06) while the flow totals stayed at the old level. Pre-break
   `ticks/ohlcv` = 1.6–1.9 (the minute print tape ALWAYS included NG — daily ohlcv
   did not); post-break `ticks/ohlcv` = **0.992–0.995 exactly** — the daily OHLC
   endpoint now equals the minute tape (consolidated). `flow/ohlcv` fell 0.99 →
   0.55 mechanically.
4. **All tickers equally affected** (post-break median capture by turnover tier:
   ≥10bn 0.61, 1–10bn 0.556, 100m–1bn 0.565, <100m 0.577) — consistent with a
   market-wide NG share, NOT with a ticker/subset fetch failure.
5. **Not the Friday session-2 gap, not the closing auction:** post-break Fridays
   actually capture BETTER (median 0.708, n=9) than other weekdays (0.569, n=36) —
   negotiated volume is a smaller share of Fridays' total; bar structure is
   identical either way.
6. **The 18:30 cron is not the bug — but it is new:** `logs/cron_stockbit_flow.log`
   begins 2026-07-10 18:30:01 (the crontab rework, commit 676ce54, added it). Before
   that, bars were written by **historical backfill campaigns**
   (`tools/backfill_flow_bars.py`, `fetch_flow(date=…)` full-day payloads; full
   universe 2025-01-02→2026-04-28 audited 2026-09-07, IDX80 to 2026-08-25) — which
   is why pre-07-10 dates sit at exactly 1.000. The daily live writer stores
   faithfully what the endpoint returns (see the dry run).
7. **3-day backfill dry run (read-only, stores nothing, token never printed):**
   fetched `fetch_flow(date=…)` for 2026-07-14 / 08-24 / 10-06 × BBCA, TLKM, BMRI,
   ACES — **12/12 totals IDENTICAL to the stored bars** (e.g. BBCA 07-14:
   1,598,688 lots both sides). The dated endpoint carries the same regular-only
   counters as the live one.

## Affected scope

- **Dates:** ≥ 2026-07-06 (blip) / ≥ 2026-07-10 (permanent). **Tickers:** all, in
  proportion to their NG share (median capture 0.55–0.58; liquid large-caps
  0.64–1.08 on some days — BBCA 10-06 was 1.08, i.e. NG share ≈ 0 that day).
- **Backfill via `fetch_flow(date=…)`: NOT feasible** — the 12/12 identity proves
  the endpoint never carried the missing volume. Recovering NG minute volume would
  need a different endpoint/source (owner-gated, out of audit scope).
- **Research results that used minute volume after the break:**
  - HYP-PM-0019 stress G0's 15:49 pre-close check — **prices only, unaffected**
    (disclosed at the time: "the known minute-volume under-capture since 2026-07 is
    irrelevant here").
  - Mechanism-inventory **class O volume-profile checks** (2026-10-08: cumulative
    lots, 2.5% tick share — "execution-timing only") — lots are regular-market-only;
    any ratio against ohlcv volume after 07-10 is understated by the NG share. Its
    null/secondary conclusion does not hinge on the level, but magnitudes are
    suspect — re-quote with a regular-market denominator before any future use.
  - **Production flow features** (code-level consumers, no research verdicts):
    `engine/delta_flow.py`, `engine/smc_flow.py`, `engine/trade_flow.py`,
    `engine/agent_firm/agents/flow.py`, `routes/v1/trade_flow.py` — anything
    normalising flow by ohlcv volume mixes regular-market numerators with
    consolidated denominators after 07-10.

## Correct semantics going forward

`stockbit_flow_bars` is a **regular-market order-flow tape** (and a clean one —
capture vs regular volume is ~1.0 by construction). `ohlcv.volume` (and `ticks`)
is **consolidated** since 2026-07-06. Never divide one by the other after the
break without expecting ~0.55–0.70. The correct normaliser for flow features is
the tape's own total: `(max buy_lot + max sell_lot) × 100` shares.

## Proposed fix — PATCH FILE ONLY (owner applies; nothing applied here)

`0001-flow-capture-alert.patch`: at the end of `stockbit_fetcher.run_flow`, compute
the day's median capture of the freshly written bars against ohlcv volume and
`log()` a WARNING line when it moves outside [0.75, 1.25] — a vendor definition
change would then surface within one day instead of three months. Plus a
documentation comment on the regular-vs-consolidated semantics at the bars INSERT.
Deliberately minimal: no schema change, no Telegram dependency, no restart
requirement beyond the owner's normal deploy. Alternative (stronger, owner-gated):
store a per-day capture ratio table for consumers to normalise against.

## Files

`capture_audit.py` (the audit), `capture_daily.json` (all 416 daily rows: medians,
IQR, frac<90%, bars/ticker, modal last bars, per-tier medians), `backfill_dryrun.py`
+ `backfill_dryrun.json` (the 12/12 identity), `0001-flow-capture-alert.patch`.

*— ZCode, 2026-10-09*
