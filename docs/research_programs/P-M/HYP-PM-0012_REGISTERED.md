# HYP-PM-0012 — REGISTERED

**Registered:** 2026-09-21T01:46:55+00:00 · **Program:** P-M · **Family:** Price-Reversal {R1} (member 1)
**Spec id:** FWD-PM-FADE-001 · **Status:** REGISTERED → IN_TESTING
**Frozen protocol:** `P-M/forward_fade/PROTOCOL.md` · sha256 `e195967260888315028f33bbbea558ce2f8e02a9d049338cb655313c36a108c5`
**Ledger:** `P-M/forward_fade/ledger.json` (opened empty; no back-fill permitted)

## Mechanism

Failed-breakdown anti-edge. A liquid IDX name sweeps intraday below its trailing 20-session low,
then closes back above it — the widely-taught bullish "stop-hunt/spring/shakeout" reversal. The
registered claim inverts the retail reading: uninformed buying attracted by the popular pattern
underperforms net of cost, so forward excess after the signal is NEGATIVE. Signal: low(t) <
lo20(t) and close(t) > lo20(t), lo20 = prior-20-session rolling low shifted 1; per-row liquid
threshold universe (`adv20 >= Rp 1e9`, `close >= Rp 50`, >= 18 of trailing 20 sessions traded);
next-session-open fill; fixed 5/10/20-session holds; 0.60% RT. No entry is proposed: the eventual
tradeable form is an avoidance/exit overlay (`BOOK_OVERLAY_POLICY.md` two-stage rule), never a
short and never a standalone entry.

## Frozen endpoint and decision rule

Primary endpoint: per-signal h=20 excess vs BOTH benchmarks (IHSG; equal-weight liquid book),
one-way entry-date-clustered SE. Both must clear independently — one significant and one null is
not sufficient.

- 12 months: PROMOTE track requires t < −2.5 on both AND cumulative excess negative on both.
- 18 months (final): PROMOTE requires t < −3.0 on both.
- REJECT at any checkpoint: cumulative excess turns >= 0 on either benchmark, or < 100 distinct
  signal-dates by month 12 (dead-signal guard).
- Decay haircut (pre-declared): forward h=20 vs IHSG weaker than −0.5% at month 12 = decayed
  in-sample estimate, not a deferred confirmation.

## Backtest reference (in-sample discovery, no confirmatory weight)

12,131 signals / 1,151 dates / 757 tickers, 2021-07-05 → 2026-07-29. h=20: −1.46% vs IHSG
(t −5.64), −1.47% vs EW-book (t −8.20); ex-2025 −1.88% (t −6.80, IHSG). Three independent builds
(original scan, its self-audit next-open correction, this spec's from-scratch rebuild) agree within
0.1–0.3pp. Bonferroni-18 (full discovery scan) cleared at every horizon. Breadth clean: top ticker
(CMNT) 0.6% of signals; ticker-demeaned panel test still significant (−1.02%, t −3.97).

## Family declaration (binding, append-only)

**P-M · Price-Reversal {R1}** — short-horizon reversal / failed-breakout patterns derived from
OHLCV only (no flow instrument, no trend features), measured as negative forward excess, liquid IDX
universe. Opened at this registration per D-028/PG-3, Owner ruling **D-052**. Widening {R1} later
is permitted; narrowing or splitting it is not. Other 2026-09-17 scan arms (liquidity sweep,
Wedge Pop, …) remain unregistered candidates; any arm later registered into {R1} inherits the
scan's multiplicity.

## Disclosed prior search

Arm P3a of `P-M/pattern_scan/PATTERN_SCAN_2026-09-17.md` (~12 arms + 6 strictness variants on one
corpus). The mechanism argument is post-hoc plausibility for a search-discovered effect, carried
honestly in PROTOCOL §0/§8. The close-fill bias the scan found in itself (§7 there) is designed
out here from the start (next-open fill).

## Carried limitations

No dedicated split-continuity audit for this universe (±35% contamination guard only, PROTOCOL
§8.3); fixed-horizon event study — no claim about optimal holding period; overlay application
(suppress entries vs accelerate exits) deliberately unscoped until a checkpoint clears; ADV20
threshold proxy, not real IDX80 membership history (re-derive before operational use); costs are
the repo authority, not broker-quoted.

**ID note:** HYP-PM-0011 is reserved-retired, never assigned (it appears once in the registry as
the untaken "conservative reading" of the 2026-09-17 supersession note); D-052 assigns 0012.
