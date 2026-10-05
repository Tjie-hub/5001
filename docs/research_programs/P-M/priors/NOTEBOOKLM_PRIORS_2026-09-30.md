# NotebookLM priors notebook — setup record + query answers · 2026-09-30

**Notebook:** "IDX Edge - Priors & Evidence Standards (2026-09)" ·
https://notebook.google.com/notebook/3d4faa92-9382-48c0-9ce9-ec425596dcac
Built on the account's own Google session in the ZCode browser pane. The pre-existing
"Wisdom of the Crowd: Retail Orders and Stock Returns" notebook was left untouched.

## Sources added (7 ingested / 17 attempted)

| # | source | status |
|---|---|---|
| 1 | Rouwenhorst (1999), Local Return Factors and Turnover in Emerging Stock Markets, JF — Yale ICF full PDF | **OK** |
| 2 | Bali, Cakici & Whitelaw (2011), Maxing Out — NBER w14804 full PDF | **OK** |
| 3 | Stambaugh, Yu & Yuan (2012), The Short of It — NBER w16898 page | **OK** |
| 4 | Hou, Xue & Zhang, Replicating Anomalies — NBER w23181 working-paper PDF (retry after SSRN failed) | **OK** |
| 5 | McLean & Pontiff, Does Academic Research Destroy Stock Return Predictability? — FMG working-paper PDF (retry after SSRN failed) | **OK** |
| 6 | Bailey & López de Prado (2014), The Deflated Sharpe Ratio — davidhbailey.com author PDF | **OK** |
| 7 | PROGRAM_STATE_2026-09-30 (text source: registries, NR7 SHADOW, 3 forward tests + decision dates, factor-zoo/IDX80 headlines, XP-001 table + EW-vs-IHSG gap, census N=270, data spans) | **OK** |

**Failed (bot-walled, reported not substituted):** Li/Wei/Zhang 2023 PBFJ (ScienceDirect
abstract blocked), Hanauer & Lauterbach 2019 EMR (ScienceDirect blocked), Blitz/Pang/van Vliet
2013 EMR (SSRN blocked), Ritter 1991 JF (Wiley blocked), Field & Hanka 2001 JF (Wiley blocked),
Harvey/Liu/Zhu 2016 RFS (Duke PDF + SSRN both failed), Novy-Marx & Velikov 2016 RFS (OUP
abstract blocked), UMA Indonesia (ResearchGate blocked), IDX Peraturan I-X Papan Pemantauan
Khusus PDF, IDX Bell Apr-2024 PDF, IDX short-selling Peng-00168 PDF (all three idx.co.id PDFs
rejected by NotebookLM's fetcher). Every number below is quoted from an INGESTED source;
paywalled papers contribute no numbers to this memo.

## Query (a) — per-factor IDX/EM effect sizes (as stated in the ingested sources)

| factor | effect (as stated) | sample | t | source |
|---|---|---|---|---|
| Momentum W−L, EM | +0.39%/mo (stock-EW); +0.58%/mo (country-EW); positive in 17/20 countries | 1,705 firms, 20 EM, 1982-01→1997-04 | t 2.35 / 3.78 | Rouwenhorst |
| Size SMB, EM | +0.69%/mo (all-market EW); +0.70%/mo (cross-country EW) ≈ 8.3–8.4%/yr | same | t 3.09 | Rouwenhorst |
| Size SMB, **Indonesia** | **−0.46%/mo** — small 0.22%/mo vs big 0.69%/mo (USD), insignificant | IDX names inside Rouwenhorst's EM sample, 1990-01→1997-04 | t −0.77 | Rouwenhorst |
| Value HML, EM | +0.72%/mo (stock-EW) / +0.93%/mo (country-EW ≈ 9.0%/yr); FF(1998) VW EM value 16.91%/yr (t 3.06); VW E/P 4.04%/yr (t 0.58) | 20 EM, 1987-01→1997-04 (accounting data from 1987); FF: 17 EM 1987–1995 | t 3.82 / 4.00; FF 3.06 / 0.58 | Rouwenhorst |
| Value E/P, EM | +0.60%/mo (SE 0.13%) ≈ 7.44%/yr | same | (SE 0.13) | Rouwenhorst |
| MAX decile 10−1, US | VW raw −1.03%/mo, 4-factor alpha −1.18%/mo; EW raw −0.65%/mo (t −1.83), alpha −0.66%/mo (t −2.31) | US CRSP 1962-07→2005-12 | t −2.83 / −4.71 (VW) | Bali-Cakici-Whitelaw |
| IVOL decile 10−1, US | VW raw −0.93%/mo, alpha −1.33%/mo (t −5.09); **EW flips sign**: raw +0.37%/mo (t 1.09), alpha −0.14 (t −0.64) | same | t −3.23 / −5.09 (VW) | Bali-Cakici-Whitelaw |

**Weighting warning (直接 relevant to our EW books):** Bali-Cakici-Whitelaw show the MAX
lottery effect and the IVOL risk effect **cancel under equal-weighting** in univariate sorts;
Rouwenhorst's EM premia are EW-based and larger than FF's value-weighted estimates.

## Query (b) — size premium sign in IDX vs this sample's EW-vs-IHSG gap

- EM-wide: SMB **positive** (+0.69%/mo, t 3.09, 1982–97).
- **Indonesia specifically: SMB NEGATIVE** — −0.46%/mo (t −0.77), 1990–97: small caps
  underperformed big caps in IDX (statistically insignificant).
- Our sample (PROGRAM_STATE): the EW top-200 liquid universe **trailed IHSG ≈ 0.56%/mo gross
  over 54 months** (2021-08→2026-06), and the factor zoo's IDX80 restriction was
  "everything fails".
- **Reading:** Rouwenhorst's Indonesia sign and our EW-vs-IHSG gap point the same way — the
  liquid-I EW book carries a small-cap tilt relative to the cap-weighted index, and IDX has
  historically paid **negative** rent for that tilt. The gap is a benchmark/tilt property,
  not evidence of missing alpha in the exclusion rules (XP-001's C rule loses to the EW
  universe itself, i.e. after the tilt is controlled).

## Query (c) — evidence standards for short samples (as stated in the ingested sources)

- **McLean & Pontiff**: 82 characteristics, 68 studies; average original in-sample span
  **323 months (~27 years)**; in-sample extreme-quintile long-short mean **42.8 bps/month**;
  out-of-sample decay ~**9.7%–26%** (strongest spec 9.7%, p 0.386; continuous 20.2%, p 0.090);
  post-publication decline larger again (58% lower post-publication per the paper's abstract
  of the 26%/58% decomposition). Standard: a 54-month window is ~1/6 of the typical discovery
  sample, and published effects decay ~10–30% OOS.
- **Bailey & López de Prado (DSR)**: the Deflated Sharpe Ratio corrects for selection bias
  under multiple testing + non-normality; our census bar (t ≥ 2.8575 at N=270 arms, D-064) is
  the program's operationalization of the same multiple-testing logic.
- **Hou, Xue & Zhang**: of 452 anomalies from 447 papers, **~65% fail to replicate** (t-stat
  ≤ 1.96 threshold incl. all p ≥ 1% brands), replication failures cluster in **microcaps**,
  and anomalies are largely absorbed by a replication-standard 3-factor model. Standard:
  anomaly returns measured in thin caps do not clear a tradeability bar.

## NotebookLM session notes

- NotebookLM's URL importer was bot-walled by ScienceDirect, Wiley, SSRN, OUP, ResearchGate
  and idx.co.id (11 failures); NBER PDFs/pages, an institutional PDF (Yale ICF), author PDFs
  (davidhbailey.com, FMG) ingest cleanly. Future adds should go straight to NBER/author/
  institutional copies.
- One stray chat turn ("Saya ingin mempelajari topik baru") exists in the notebook from a
  mis-click during setup; harmless, left in place.
