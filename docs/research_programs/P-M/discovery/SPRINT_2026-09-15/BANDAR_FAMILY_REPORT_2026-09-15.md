# FAMILY #1: BANDAR — FAMILY REPORT

**Date:** 2026-09-15 · **Program:** P-M · family-by-family discovery, family 1 of 6
**Stage:** DISCOVERY ONLY. No registration, no execution, no registry change.
**Adversarial-pass standards applied:** suspension-clean base, PIT z-scores, declared kill rules,
declared skip-list (label levels alone were already killed in sprint 1: Big Acc +0.09% / Big Dist
+0.17% h5, net-negative).

**Key question:** *Does bandar information contain any economically meaningful, incremental,
PIT-usable information that can become a tradable long-only signal or a robust risk filter?*

**Answer: not as an entry signal — yes, as a negative-information risk filter.**

---

## A. DATA AUDIT

**What exists** (`bandar_detector`, production `walkforward.db`, PK (ticker, trade_date), no duplicates):
106,189 rows, 872 tickers, 400 sessions, 2025-01-02..2026-09-14. Mean 265 names/day but **p10 = 96,
p90 = 831** — vendor coverage per day is highly variable, i.e. the event "appears in this table at
all" is itself selective. 56,666 of 123,287 liquid tradable base observations (46%) are bandar-covered.

| Field | Type | Verified economic meaning |
|---|---|---|
| `total_buyer`, `total_seller` | int | count of buy-side / sell-side **brokers** on the day (verified: matches `v_b_concentration.bandar_*`) |
| `net_broker_count` | int | exactly `total_buyer − total_seller` (arithmetic identity verified) — broker **breadth**, not size |
| `top1/top3/top5/top10_accdist`, `avg_accdist` | text | vendor's 7-class ordinal regime for the top-k brokers by traded value: {Big, Normal, Small} × {Acc, Dist} + Neutral. **The vendor's mapping rule is not in the repo and could not be verified** — treat as a black-box ordinal. top1 ≠ top3 in 61% of rows (cohort-specific, not one label per stock) |
| `broker_accdist` | text | simple flag (e.g. "Acc") — semantics unverified, not used |
| `value`, `volume` | int | **units unknown: bandar `volume` ≈ 0.4% of OHLCV volume, `value` ≈ 0.43 × close×volume** — NOT full-day totals. Usable only for self-normalized ratios; never as absolute rupiah |
| `avg_price` | real | ≈ OHLCV close (median ratio 1.000) — consistent, unremarkable |
| `updated_at` | ts | concentrated 17:00–20:00 WIB same day → **PIT for a close(t+1) entry; historically unprovable** whether intraday revisions occurred (a minority of rows show daytime timestamps) |

**Economic meaning in one sentence:** the whole table is a vendor repackaging of IDX broker-summary
*breadth* (how many brokers traded, on which side) plus a black-box ordinal classification of what the
dominant brokers were doing. It carries **no bandar size, no bandar identity, no persistence
structure** beyond what we construct. The vendor cannot name the "bandar" either.

**Missing dimensions:** no bandar capital/size; no identity (and program rule: brokerage ownership —
including `investor_type` Lokal/Asing/Pemerintah in Dataset B — is never end-investor identity);
no pre-2025 history (family cannot be OOS-tested historically); label mapping unverifiable;
`value`/`volume` unusable in absolute terms.

---

## B–C. CONSTRUCTION SEARCH AND ECONOMIC TESTS (predeclared tree, all results)

Base: suspension-clean liquid mask ∩ bandar coverage. h5 shown (full h1/h2/h3/h5/h10/h20, medians,
trimmed means, hit rates, tail shares in `cache/bandar_family.json`). Cost sensitivity: 40/50/60bp —
no construction's h5 exceeds +0.80%, so **nothing in this family clears 60bp with margin**.

| Construction | n | h5 (net of 60bp) | halves+ | Verdict |
|---|---|---|---|---|
| B1 breadth net>0 | 32,431 | −0.17% (−0.77%) | 3/4* | negative |
| B2 buyer-share ≥0.60 | 19,440 | −0.20% (−0.80%) | 3/4* | negative |
| B3 breadth z≥+2 | 1,101 | −0.06% | 3/4 | negative |
| B4 participation z≥+2 ("crowded") | 2,069 | +0.79% (+0.19%); h10 +1.53%, h20 +2.99% | 3/4 | **fails FM (below)** |
| B5 Δ1d breadth z≥+2 | 1,351 | +0.41% (−0.19%) | 3/4 | below cost |
| B6 Δ5d breadth z≥+1.5 | 3,376 | +0.17% | 2/4 | fail |
| B7 acceleration z≥+1.5 | 3,355 | −0.12% | 3/4* | negative |
| B8 buy-run ≥3/5 | 25,144 | −0.23% | 3/4* | negative |
| B10 flip into Big Acc | 5,140 | −0.16% | 3/4* | negative |
| B11 flip into Big Dist | 5,841 | −0.21% | 3/4* | negative (both flips bad → label transitions carry no direction) |
| B12 Acc-run ≥2 / ≥3 days | 9,045 / 4,489 | −0.15% / −0.20% | 2/4 | fail |
| B13 Big-Acc into weakness | 2,323 | −0.28% | 2/4 | fail (absorption again negative) |
| B14 Big-Dist into strength | 942 | +0.25% | 3/4 | below cost; bot-ADV variant noise (n=168, 1/4) |
| B15 breadth buy + price down | 4,246 | +0.22% | 3/4 | below cost |
| B16 breadth sell + price up | 4,813 | +0.63% (+0.03%) | 3/4 | selection effect — **FM negative (below)** |
| B4 × ADV terciles, B14/B16 × ADV terciles | — | no tier clears cost with margin | — | fail |

\* "3/4 halves" with the negative h5 means 3 quarters are ≥ the (negative) mean — i.e. broadly
negative, not stable-positive.

---

## D. INCREMENTALITY — the decisive result

Fama-MacBeth, h5, controls = [ret1, ret5-z, volume-z, **platform flow z**] (bandar must add
information beyond price, volume, and the Stockbit platform flow already tested):

| Bandar flag | FM β | t |
|---|---|---|
| B2 buyer-share ≥0.6 | **−0.53%** | **−4.94** |
| B3 breadth z≥2 | −0.30% | −1.05 |
| B6 Δ5d breadth ≥1.5 | −0.76% | −3.71 |
| B7 acceleration ≥1.5 | **−0.94%** | **−5.70** |
| B10 flip-into-Big-Acc | −0.77% | −4.84 |
| B13 Big-Acc & down-day | −0.76% | −3.26 |
| B16 breadth-sell & up-day | −0.56% | −2.28 |
| B4 crowded participation | −0.30% | −0.87 (not incremental) |

**Every single construction has a negative conditional coefficient.** Broker-count breadth — the
classic "many brokers are accumulating" retail narrative — is a **contrarian negative marker** on IDX
in this window, and the information is incremental (it survives platform-flow, price, and volume
controls). The family's only positive portfolio cells (B4 crowded; B16 sell-into-strength) fail FM —
they are price/volume selection effects, exactly the UP3 pattern.

Avoidance economics (declared filter rule: spread negative ≥3/4 halves, n≥500):
- buyer-share ≥0.6 vs ≤0.45: spreads −6 / −41 / −37 / **+19** bp → 3/4 halves, n≈3.4–7.3K. **Passes.**
- Acc-run ≥2 vs rest: −29 / −16 / +3 / −40 bp → 3/4 halves, small. Passes weakly.
- Strongest conditioning found: up-move events with bandar-buying-heavy vs bandar-light:
  h5 −48bp, **h10 −102bp** spread.

---

## E. SURVIVORSHIP / PIT — what cannot be established retrospectively

- Coverage is vendor-selective (96–831 names/day) — selection into the panel is unmodeled.
- Label semantics are a black box; the mapping could change silently vendor-side.
- No pre-2025 bandar data → **no historical OOS is possible for this family**; only prospective
  capture can confirm. Canvas survivorship (100% current-roster backfill) applies to every cell.
- Same-day-evening PIT is assumed from `updated_at` and cannot be proven historically.

---

## F. FAMILY VERDICT

## **AVOIDANCE** (not SURVIVES, not DEAD)

- **No entry signal exists in this family.** All accumulation-direction constructions (breadth
  buying, buyer share, buy-runs, flips into Acc, Acc persistence, acceleration) are flat-to-negative
  at h5, none clears cost, and every FM coefficient is negative with strong t. The vendor's
  "accumulation" labels and broker-breadth buying are **effective reverse indicators** on IDX in
  2025-26.
- **The family earns its keep as a risk filter:** *veto/de-weight entries (and outstanding longs)
  when bandar breadth-buying is heavy on the signal day* — buyer-share ≥ ~0.55–0.60, or a flip into
  Acc, especially inside an up-move (h10 spread ≈ −100bp in up-moves). This is incremental to
  platform flow (FM controls) and 3/4-half stable at h5 with large n.
- Smallest exact filter candidate, if the owner wants to pursue it: **"bandar buyer-share ≥ 0.55 on
  the entry signal day ⇒ veto"** attached to a named parent strategy, frozen spec (threshold, lookback
  60, coverage handling), prospective confirmation window, power/MDE. As with the platform-outflow
  filter, there is no historical holdout — only forward data can confirm.
- Spend no further research time on bandar **entry** constructions; the declared tree is exhausted.

```json
{
  "family": "bandar",
  "verdict": "AVOIDANCE",
  "entry_survivors": [],
  "filter_candidate": "bandar buyer-share >= ~0.55-0.60 veto (3/4 halves; FM-confirmed negative information; up-move conditioned h10 spread ~ -100bp)",
  "constructions_tested": 20,
  "next_family": "price / price-structure"
}
```
