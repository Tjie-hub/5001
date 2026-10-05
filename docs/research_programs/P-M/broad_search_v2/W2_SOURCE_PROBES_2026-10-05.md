# W2 · SOURCE PROBES — seven feasibility memos, one-time test downloads · 2026-10-05

Standing rules honored: public sources only, no logins, no CAPTCHAs, nothing behind auth; every
block is reported rather than worked around (idx.co.id, MSCI bulk, lock-ups). Probe 1 doubles as
the X1 brief's P0-B and lives with its code in `P-M/cross_asset/`.

| # | probe | verdict | one-line |
|---|---|---|---|
| 1 | Cross-asset prices + JISDOR | **DONE (acquired)** | see §1 |
| 2 | Commodities | **PARTIAL** | gold/oil/copper/gas free; coal & CPO blocked |
| 3 | MSCI/FTSE index reviews | **FTSE YES / MSCI NO** | FTSE JSON API no-auth; MSCI needs registration |
| 4 | Attention data | **Wikipedia YES / Trends NO** | pageviews API from 2015-07; Trends 429+ToS |
| 5 | Suspension archive | **IN CORPUS (2022+)** | 359 real events; 2,830 data-gap artifacts; pre-2022 absent |
| 6 | Holiday + BI meeting calendars | **LIMITED** | IDX blocked; timeanddate no market tag; BI dates public (recent yrs) |
| 7 | Lock-up dates | **BLOCKED** | no structured public source anywhere free |

## 1 · Cross-asset prices + JISDOR — DONE (acquired 2026-10-05)

`P-M/cross_asset/` holds the working acquisition: EIDO/TLK/SPY/USDIDR=X/^JKSE/TLKM.JK via
yfinance (no auth), MANIFEST.json with per-file sha256/rows/range, gap report (USDIDR=X 214-day
hole located: 2003-05-01→2003-12-01), TLK ADS-ratio gate (SEC-verified 20→40→200→100; yfinance
series split-adjusted, no ratio change appears as a return), and **JISDOR** — Bank Indonesia's
official fixing — verified downloadable WITHOUT auth via the JISDOR page's own XLSX export
(3,236 daily rows, 2013-05-20→2026-10-02; `fetch_jisdor.py` documents the ASP.NET-postback
method; the standalone re-run is still being debugged and the copy is pinned by sha256 in the
MANIFEST). Driver: `fetch_cross_asset.py` + `fetch_jisdor.py`.

## 2 · Commodities — PARTIAL

One-time probe (yfinance, period=max, no auth): GC=F gold futures 2000-08→ (6,549 rows), GLD
2004-11→, CL=F WTI 2000-08→ (6,557), USO 2006-04→, NG=F natgas 2000-08→, HG=F copper 2000-08→;
NICKEL/JJN EMPTY, NICK.L London ETF 2008-01→ (imperfect proxy); **BTU coal-equity proxy only
2017-04→, KOL EMPTY, FCPO=F CPO futures EMPTY, CPO.JK/PALM EMPTY** — same verdict as memo 04.
Consequence: an IDX coal/CPO overnight family has no free signal leg; only gold/oil/nickel-proxy
sectors are testable.

## 3 · MSCI / FTSE Russell index reviews — FTSE YES, MSCI NO

- **FTSE Russell: USABLE WITHOUT AUTH.** Public JSON API found in the research portal:
  `https://research.ftserussell.com/products/index-notices/Backend/GetNotices?id=GEISAC&...`
  returns notices with `Title, AnnouncedDate, EffectiveDate, IsReview, HasCsv` and index tags
  (`ASEAN`, `GEISAC`); paging demonstrably reaches back years; country classification PDFs
  (matrix-of-markets: Indonesia = Secondary Emerging, as of 2026-04-07) are direct no-auth
  downloads on lseg.com. Per-stock add/delete detail sits in per-review-round attachments.
- **MSCI: effectively blocked.** Review hub renders only US/China/ESG/Frontier/MENA sections —
  no ACWI/EM listing; per-cycle add/delete PDFs exist on app2.msci.com but only at known URLs
  (search-indexed), no crawlable EM listing without registration (`/BMREGDownload` disallowed in
  robots.txt = registration-gated). Verdict: IX1 proceeds on FTSE, not MSCI.

## 4 · Attention data — Wikipedia YES, Google Trends NO

- **Wikipedia pageviews: USABLE, no auth.** REST API
  `wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/all-access/user/{article}/daily/{start}/{end}`
  returns daily JSON from **2015-07-01** (verified for en.wiki "Telekomunikasi_Indonesia" and
  id.wiki "Bank_Central_Asia", 3,746 rows). Caveat: zero-view days are OMITTED — low-traffic
  names need a calendar left-join. Coverage breadth for ~500 liquid IDX names is unproven (that
  test is the gating item for any N1 screen).
- **Google Trends: SKIP.** No official free API; the unofficial endpoint returns 429 even with a
  browser UA, and scrapers violate ToS. Reported, not worked around.

## 5 · Suspension archive — IN CORPUS (2022+ only)

Direct probe of the local corpus (read-only): `suspension_events` = 3,189 rows,
2022-04-28→2026-07-17; **classification split: 359 `suspension` (real) vs 2,830 `data_gap`
(corpus collection gaps — NOT market suspensions)**. Pre-2022: absent by construction. Any TS1
screen runs on the 359 real events with date clustering, and says so.

## 6 · Holiday + BI meeting calendars — LIMITED

- **IDX holiday calendar: BLOCKED** — idx.co.id 403 with `Cf-Mitigated: challenge` (both plain
  fetch and reader; consistent with all prior probes).
- **timeanddate.com: USABLE WITH LIMITATIONS** (via reader): national/joint-holiday tables back
  to 2000, but **no market-closure tag exists** — IDX occasionally deviates on joint-leave days,
  so reconstructed calendars are approximations, not exchange-verified.
- **BI rate decisions: USABLE WITH LIMITATIONS** — `bi.go.id/id/statistik/indikator/BI-Rate.aspx`
  (no auth) lists decision dates + rates + press-release links (23 Sep 2026 5.75% … 21 Jan 2026
  4.75% verified); ASP.NET postback pagination blocks bulk 2010+ scraping by plain GET; older
  history = per-release retrieval. The dedicated RDG calendar PDFs are decorative (no dates) and
  historical year files 302 to 404.

## 7 · IPO lock-up dates — BLOCKED

idx.co.id 403 (Cloudflare); eipo.idx.co.id / idxdata.co.id unreachable; e-bursa.com squatted
(redirects to spam domains); idnfinancials.com has annual reports only, no lock-up fields. No
structured public source exists; lock-up terms live inside per-IPO prospectus PDFs behind the
IDX wall. LC2 stays data-blocked pending an Owner IDX-direct/vendor ruling (same gate as {FQ}).
