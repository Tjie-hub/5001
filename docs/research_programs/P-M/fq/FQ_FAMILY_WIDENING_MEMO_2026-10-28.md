# {FQ} family-widening memo (K5, `ZCODE_BRIEF_WEDNESDAY_2026-10-28.md`) — propose-only

No code run, no returns read. Context: the E/P arm's G0 **passed** (2026-10-27 17:41: 203/208 qualifying
months, T_eff 16.92y, power 41.5% vs the 20% stop — `588ce80`), so the panel machinery is proven powered for
monthly fundamental ranks on the 998-ticker universe. This memo costs the sibling arms the owner could add to
the family. Census 613 → bar 3.300069; each added arm moves it ≈ +0.0002 (the D-064 §C scale: the bar is
E[max|Z|] over the census; one arm at N=614 ≈ 3.3003).

## 1. Candidate arms on the same panel (top-200 KSEI mcap, D-111 v3 PIT, monthly 2009-04→)

| Arm | Mechanism (one line) | Why it survives IDX frictions | fin.db fields (coverage today) |
|---|---|---|---|
| **Book-to-market** | cheap-vs-expensive error term; the classic value sibling | monthly turnover ~0.15, no event execution; long-only top quintile | statement equity (998) / KSEI mcap — the {FQ} machinery verbatim |
| **Gross profitability** (Novy-Marx: (rev − COGS)/assets) | quality premium: productive firms earn a premium independent of value | same; big caps liquid | Total Revenue 998, Gross Profit 942, Total Aset 998 |
| **Low asset growth** | empire-building / issuance-adjacent anti-signal: fast asset growth predicts underperformance | exclusion/long-only form (AVOID top growth) — the cheapest class | Total Aset 998 (YoY differencing, same-statement PIT) |
| **Low leverage** | financial-distress risk premium: low-liability firms earn a premium | same book mechanics | Total Liabilities 998 / equity or assets |

Field caveat shared by all: statement-date availability via D-111 v3 (identical to E/P — already solved);
USD reporters via the {FQ} magnitude rule (already solved); off-quarter fiscal years excluded (already
solved). No new data acquisition needed for any arm.

## 2. Registry cross-check (already-tested relatives — none of these four was tested on THIS panel)
- **factor_zoo / alpha_search_v2 (2026-09-18/19):** B/M, ROE, RNOA, CF/P **null/dead** — but on the
  2021–26 tradeability panel (59 months, price/ADV-screened, pre-{FQ} fundamentals extraction with the
  8.6%-coverage OCF source). The {FQ} panel is 209 months, survivorship-complete, PIT-v3 — a materially
  different (and stronger) test bed; under the search brief's non-overlap rule these are **re-tests on a new
  panel**, which the owner must acknowledge as re-parameterisation risk, not virgin cells.
- **D1/D3/D4 rows of `00_EXCLUSION_INDEX`** cite the same history. Gross profitability was null in
  alpha_v2's EM set (942-ticker GP coverage now vs the old source's coverage is the difference worth a
  coverage count at any G0).
- **Dividend yield (C-003) and buybacks (C-009)** are NOT part of this memo's scope — they are separate
  candidates with their own files (payout family question).

## 3. Multiplicity cost and prior-only power
- Census: each arm +1 (613→614…618); bar 3.300069 → ≈3.3015 at 618 (five arms). Negligible vs effect sizes.
- Power: the proven E/P machinery computed power 41.5% at the IR 0.75 floor over 16.92 effective years. The
  sibling arms share the formation calendar and noise structure, so the same power class applies
  (roughly 35–45% at an IR-0.75-equivalent effect; underpowered below IR ~0.6). The honest statement: widening
  is POWERED for effects of the size the E/P bar assumes, and each arm must run its own G0 (coverage + power,
  no outcomes) before registration.
- Family governance: {FQ} widening is a formal amendment (families widen, never narrow — invariant #12); all
  arms share one family ledger; the FM separator between arms becomes part of the registered design
  (E/P vs B/M vs GP correlation is the known high-correlation risk — B/M and E/P are close cousins
  mechanically; the owner may prefer to pick ONE valuation arm).

## 4. Recommendation
**Wait: register E/P alone first (HYP-PM-0023 go/no-go), widen after its G1.** Rationale: (a) the E/P G0 pass
makes the family alive — adding arms before G1 multiplies multiplicity without adding information about the
family's first claim; (b) B/M is highly correlated with E/P (same denominator family) — widening to B/M
before G1 risks spending a census slot on a near-duplicate; (c) gross profitability is the one sibling with a
distinct literature prior and full field coverage (942/998) — the natural SECOND arm by formal amendment
after E/P's G1; (d) low-asset-growth and low-leverage are cheap AVOID-form overlays if ever wanted, with
weaker IDX-specific priors. Widening NOW is viable (powered, data-ready) but spends slots before the first
claim is tested. **Do not file; the owner decides.**
