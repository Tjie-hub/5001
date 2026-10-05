# 04 · Cross-asset series ({X} anchor) — FEASIBILITY MEMO · 2026-09-30

**Item (D-c #4):** TLK ADR / USD-IDR / coal-CPO proxies for the `{X}` family
(`FAMILY_MAP_v2.md` §D: "no in-house series … data-blocked"). **Scoping only** — no pipeline
wiring, no DB writes, no screens run. POC fetch executed once 2026-09-30T03:01Z
(`fetch_crossasset_poc.py`, yfinance 1.7.0, output embedded below).

## Verdict

**Free/scriptable path exists for the anchor.** TLK (NYSE ADR), USD/IDR, and IHSG all fetch
clean via yfinance. Coal and CPO do **not** have free futures sources; only equity-grade proxies
exist. This is the only D-c item where a working POC ran on the first attempt from the Windows
mirror (no credentials needed). Sample artifact: `SAMPLE_OUTPUT_crossasset_poc.json`
(captured 2026-09-30T03:19Z via stdout redirect; first run 03:01Z produced identical results).

## POC result (actual, one run)

| Series | Status | Range | Rows | Gaps | Note |
|---|---|---|---|---|---|
| TLK (NYSE ADR) | OK | 1995-11-14 → 2026-09-29 | 7,768 | max 7d; none >7d | the `{X}` anchor works |
| USDIDR=X | OK | 2001-06-28 → 2026-09-30 | 6,378 | **3 gaps >7d, max 214d** | indicative aggregate, not JISDOR |
| ^JKSE | OK | 1990-04-06 → 2026-09-30 | 8,880 | 23 gaps >7d (hist.) | alignment benchmark |
| KOL (coal ETF) | **EMPTY** | — | — | — | Yahoo 404, "possibly delisted" |
| BTU (Peabody) | OK | 2017-04-03 → 2026-09-29 | 2,386 | none >7d | equity-grade coal proxy only |
| FCPO=F (CPO) | **EMPTY** | — | — | — | Bursa CPO futures not free on Yahoo |

## PIT / semantics notes

- yfinance daily bars are exchange-local **dates**; the close of date *t* is observable only
  after that market's close. A US close (16:00 ET) maps to ~03:00–04:00 WIB the next calendar
  day — i.e. ~5–6h **before** the IDX open. The overnight-TLK→IDX-open mechanism is therefore
  naturally aligned, and any signal rule must trade at t+1 (no same-bar reads).
- Yahoo's USDIDR=X is an **indicative aggregate**, not BI's JISDOR fixing. JISDOR is published
  daily free by Bank Indonesia and is the PIT-authoritative alternative; worth wiring in the real
  acquisition brief, not this POC.
- TLK is USD-denominated; any TLK-vs-TLKM.JK spread test needs the ADR ratio (1 ADR = 20
  ordinary shares) and the FX leg — that cross-check is the natural validity gate for the
  acquired series.
- The 214-day gap in USDIDR=X must be located and explained before any use (likely Yahoo
  history hole, not a real market closure).

## Literature prior (Owner's NotebookLM corpus, "Wisdom of the Crowd", 35 sources)

Queried 2026-09-30: the corpus is **entirely silent** on overnight/lead-lag US→IDX transmission
tests (one market-integration reference, Endri et al. 2024, in a reference list only). The anchor
lead is therefore not falsified or crowded *in the Owner's own collected literature* — and our
in-house null set ({T1} deflated, flow family null) never touched cross-asset transmission.

## Effort estimate (real acquisition brief)

~1 day: fetch script → `ohlcv`-style external table with its own fetch-log + sha256 discipline,
gap report, JISDOR addition, TLK↔TLKM.JK cross-check, PIT spec line. Ongoing accrual via the
existing recorder pattern is trivial after that. Screen arms are spent only if/when a screen is
pre-declared (census bar 2.8575, N=266 as of D-064).
