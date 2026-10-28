# ZCODE — {FQ} registration, C-003 pin + G0, E/P G1 ordering (2026-10-28)

Brief: `ZCODE_BRIEF_FQ_REGISTRATION_C003_PIN_2026-10-28.md`. Census **614** from D-115 on. Push HOLD.

| Item | Status |
|---|---|
| M1 D-entries filed | **DONE** — **D-113** (PEAD G0 withdrawal, WITHDRAWN uncounted) + **D-114** ({FQ} E/P G0 passed) — `f39ffa8`; both carry "Approval authority: Owner, 2026-10-28" |
| M2 HYP-PM-0023 registered | **DONE** — registration record `P-M/fq/HYP-PM-0023_REGISTERED.md` (sha `7155e1c7…`, pinned in `g1_fq_ep.py::REG_SHA256`; script sha `f5d35449…` at pin), registry row + {FQ} family line appended, **D-115** (one arm, census 613→614, no-widening clause verbatim) — `ad05040`. G1 **not run** |
| M3 C-003 freeze pinned + G0 run | **DONE, G0 PASSED → STOPPED-FOR-OWNER** — freeze final (dividends only, {PY}, floor 0.80%/mo, gate (b); sha `2789ab21…`), `g0_dy_breadth.py` implements the pre-registered placebo (sha `497f32b9…`), **D-116** (`7c116ba`), G0 run once (`98370bb`): **formable 209/209 months, placebo σ_m 3.54%/mo, SE 0.245%/mo, t 3.27 at the floor, power 48.7% ≥ 20% — stop rule not fired; MDE80 0.61%/mo**. Registration go/no-go = owner |
| M4 Buyback marked | **DONE** — shortlist row 9: "UNDERPOWERED — not folded into C-003 (owner 2026-10-28)" |
| M5 E/P G1 | **NOT RUN — by the brief's own rule**: M3 ended at "passes", so M5 waits for the owner's C-003 registration decision (C-003 must not be chosen after seeing E/P's G1). Everything is pinned and ready: `g1_fq_ep.py` verifies `REG_SHA256` |

## The C-003 G0 result in full (no returns read)

Coverage: 209/209 months formable (≥30 valid-yield names; median 68; name-month payer coverage 33.9%,
reported not gated). Power: seeded random-quintile placebo (10 draws, seed 20261028; the {OC}/{RF} precedent —
random buckets carry no yield information), σ_m **3.54%/mo** → SE_mean 0.245%/mo over 209 formations;
t at the 0.80%/mo floor = **3.27** vs bar 3.300069 → **power 48.7%** against the 20% stop; MDE80
**0.61%/mo**. Result JSON: `P-M/dy/G0_RESULT_20261028T092519.json`.

**Honest note on the two wrong predictions.** The candidate file claimed "~80–95% at 0.80%/mo" (plain 5%
test — an error), and the freeze §4 recorded my expectation of "single digits" from extrapolating the {OC}
G0's σ (≈9.8%/mo on its thinner ADV-gated panel). The measured placebo on this top-200, price≥50 panel is
3.54%/mo — the freeze's pre-registered measured rule governed, and both predictions are now corrected on the
record (D-116 records the candidate-file error; this report records the σ-extrapolation miss).

## What the owner holds now (open decisions)

1. **C-003 ({PY} dividend yield): registration go/no-go.** Registration text is drafted in the freeze §8
   (HYP-PM-00NN, one-sided t ≥ 3.300069 at census 615, FM-over-E/P separator, both halves, kill rule). Note
   the floor sits just below the bar's face value (t 3.27): a registration is a real risk that the arm
   under-delivers at G1 — the 50%-haircut caution of D-112-style thinking applies.
2. **HYP-PM-0023 E/P G1**: run it (one shot, `g1_fq_ep.py`) — either now, or after the C-003 decision, per
   the ordering rule the owner set.
3. Standing items: 2026-11-02 rebalance switch; PEAD D-entry is now filed (D-113); push decision (HOLD).

## Files and commits
`f39ffa8` D-113/D-114 · `ad05040` HYP-PM-0023 registration + D-115 · `7c116ba` C-003 freeze final + D-116 ·
`98370bb` C-003 G0 result · this commit — M4 shortlist mark, this report, TODO census update.
Reg sha `7155e1c739c890379b23382180271734173fc2de8ff4de22bf782b4bece9847b` · freeze sha
`2789ab21dedc269d0eeaf20b264c27a0e29c82362c6790a8065318524350c208` · DY G0 script sha
`497f32b9…` · G1 script sha `f5d35449…` (all at pin time).
