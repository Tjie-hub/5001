# Big-4 banks at ARB on the MSCI-shock day — descriptive context (2026-10-16)

**Type:** descriptive note, owner request ("big bank, as it already stress sell, have a research on this").
**Not a test, not a registration, no census arm.** The registered hypothesis is HYP-PM-0014 (bank 2-ATR climax low),
decided only by its forward test FWD-PM-BANK-001 (read at N ≥ 15 events or 36 months). Its ledger was **not read**
for this note, and nothing here changes its rule (`forward_bank/PROTOCOL.md`, "do not tune").

## 1. Today (provisional close from Stockbit at 15:54; final bars land ~17:00)

| Bank | Prev → last | Day | Signal state | Foreign today (Stockbit) |
|---|---|---|---|---|
| BBCA | 6,075 → 5,175 | −14.8% (ARB) | **5.1 ATR** below SMA20, 20d low | net **+Rp286bn** (buy 732 / sell 446) |
| BBRI | 3,100 → 2,640 | −14.8% (ARB) | **4.7 ATR** | net +Rp78bn |
| BMRI | 3,980 → 3,400 | −14.6% | **5.9 ATR** | net +Rp34bn |
| BBNI | 3,410 → 2,970 | −12.9% | **4.9 ATR** | net +Rp6bn |

- All four meet the climax rule today, but **each already fired within the last 10 sessions** (BBCA 10-08 and 10-12;
  BBRI 10-02 and 10-08; BMRI 10-08; BBNI 10-12). Under the frozen de-duplication today is the **same event**, not a
  new one: the forward test already holds these episodes.
- Foreigners were **net buyers** in all four on the day; the ARB selling was domestic. Foreign participation was
  small (BBCA ~9% of value), so this is one day's read, not a flow trend.

## 2. History: every day ≥ 4 ATR below SMA20 on a 20-day closing low (big-4, 2003 → 2026-09, `history_long`)

Raw, gross, overlapping days inside the same cascades (not independent; the counts overstate the evidence).
Entry = next open; 10d/20d = close of t+10/t+20; worst = lowest low in the 20 sessions after entry.

| Episode | Deep days | 10d after | 20d after | Worst-20d | What drove it |
|---|---|---|---|---|---|
| 2005-10 BBNI | 6.2–7.9 ATR, 3 weeks | −4 to −14% | −1 to −22% | −8 to −23% | stock-specific, kept falling |
| 2008-10 BMRI/BBNI (GFC; IDX halted 3 days) | 4.0–5.0 | +13 to +62% | −17 to +12% | −6 to −20% | panic, violent bounce, gave much back |
| **2013-06 BBCA/BBRI (taper tantrum, foreign outflow)** | 4.0–5.2 | **−1 to −8%** | −6 to +1% | −3 to −8% | **sustained foreign selling: no bounce** |
| 2015-04 / 06 / 09 (rupiah stress) | 4.0–5.7 | −5 to +34% | −5 to +44% | −1 to −13% | mixed; Sept-2015 low bounced hard |
| **2020-03 early (03-02 → 03-17)** | 4.0–5.4 | **−14 to −45%** | −13 to −30% | **−24 to −48%** | first deep days were nowhere near the bottom |
| 2020-03 late (03-19 → 03-24, after repeated ARB) | 4.0–6.5 | +6 to +30% | −8 to +27% | 0 to −22% | capitulation, then bounce |
| 2024-04 BBRI | 4.2–4.4 | −10% | −9 to −10% | −14 to −17% | stock-specific (asset quality) |
| **2026-01-28 BBCA (MSCI free-float scare, IDX halt days)** | 4.9 | **+11.6%** | +7.5% | −4.5% | the closest analog; recovered |
| 2026-06-08 BBCA/BBNI | 4.3–5.1 | +14 to +26% | +16 to +30% | ≈0% | bounced |

First-of-cascade events only (the de-duplicated definition), by depth: 2–3 ATR n 287, mean +1.38%/10d, win 56%;
3–4 ATR n 29, +0.28%, win 52%; ≥ 4 ATR n 4, +4.7% (n too small to mean anything). In 62–75% of events a lower close
came within the next 10 sessions: **the first climax day is usually not the low.**

## 3. Reading

1. **Depth does not time the bottom.** Days as deep as today (4.7–5.9 ATR) were followed by both the biggest bounces
   on record (2008-10, 2015-09, 2020-03 late) and by a further 25–45% fall (2020-03 early). Being 5 ATR down is not
   by itself evidence that the selling is over.
2. **What separated the episodes was the seller.** Panic and liquidation (forced selling that ends) reversed fast;
   a **sustained outflow** (2013 taper) ground lower with no bounce. Today the domestic side sold at ARB while
   foreigners net bought — closer to a panic on the day.
3. **The MSCI overhang is the part history cannot price.** If MSCI moves Indonesia to Standalone (decision by
   2027-06-30), passive EM trackers would have to sell at the effective date, and the big banks are the largest
   foreign-held weights. Index-deletion studies elsewhere show pressure into the effective date and only partial
   recovery after. That is a dated, known future seller, which none of the episodes above had, except arguably
   2026-01 (a warning, not a reclassification).
4. **Statistically, nothing new can be concluded today.** The ≥ 4 ATR cut is a post-hoc subgroup of an in-sample
   history (n 4 first events), and the live rule is in a frozen forward test. The forward test, not this note, decides
   HYP-PM-0014.

## 4. What is already recording this

- **FWD-PM-BANK-001** (bank climax, forward): holds the 10-02 → 10-12 episodes; read at N ≥ 15.
- **FWD-PM-HALTARB-001** (D-100): names at ARB on IHSG halt days; 2026-10-16 itself is excluded as the motivating case.
- jurnal26 `bank_alert.py` sends the climax signal as it fires (kind "bank").

No new arm is proposed: the Price-Reversal family is full (D-079 took slot 3), and a depth- or flow-conditioned
variant chosen after seeing this table would be a snooped design.
