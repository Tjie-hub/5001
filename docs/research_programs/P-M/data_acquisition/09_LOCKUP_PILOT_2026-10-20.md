# Lock-up expiry calendar — 10-name sourcing pilot (2026-10-20)

**Purpose.** Follows `data_acquisition/03_LOCKUP_EXPIRY_CALENDAR_FEASIBILITY_2026-09-30.md`. Question: can we get
lock-up terms and expiry dates for IDX IPOs reliably and point-in-time? That decides whether the young-listing
screen (SCREEN-PM-LC-001, PASS but era-concentrated; {LC} not opened, D-064) can ever get a mechanism test.
**Scope.** Data sourcing only:
- no return, price or outcome was read for any pilot name;
- no hypothesis was drafted or registered;
- the census is unchanged.

The pilot names are well-known liquid IPOs, **not** drawn from the S2 cohort. The S2 RESULT stores no per-name
list, so the exact cohort needs a DB query on the box.

## 1. Rule baseline

- **POJK 25/POJK.04/2017:** anyone who acquired shares from the issuer **below the IPO price within the 6 months
  before filing** may not transfer any of them until **8 months after the registration statement becomes
  effective**.
- Lock-ups beyond that are voluntary. Prospectuses and IDX listing announcements often carry a **12-month "will
  not transfer control" pledge** from the controller. That is a control pledge, not a share lock-up: the
  controller may still sell down. It must **not** be coded as a supply event.
- So **expiry = effective date + 8 months**, *if* a POJK-25 lock-up exists at all.
- Two anchors check out:
  - **BUKA:** effective 2021-07-26 → +8 months = 2022-03-26 (a Saturday), and the reported expiry is
    2022-03-28, the next session.
  - **GOTO:** the reported expiry 2022-11-30 matches an effective date at the end of March 2022.

## 2. Pilot result (full table: `lockup_pilot_2026-10-20.csv`)

| Ticker | Listed | POJK-25 lock-up | Locked holders | 12-month control pledge | Source |
|---|---|---|---|---|---|
| BUKA | 2021-08-06 | yes | founder, Microsoft, employees (≥32 holders) | — | news; expiry 2022-03-28 reported |
| GOTO | 2022-04-11 | yes | >90% of shares (Alibaba, SoftBank among them) | — | news; expiry 2022-11-30 reported |
| PGEO | 2023-02-24 | **no** | — | PPI ≥ 1 year | IDX listing announcement |
| CUAN | 2023-03-08 | **no** | — | — | IDX listing announcement |
| NCKL | 2023-04-12 | yes | all shareholders (87.3% of shares listed) | — | IDX listing announcement |
| MBMA | 2023-04-18 | yes | MEN, Huayong (HK) | MDKA | IDX listing announcement |
| AMMN | 2023-07-07 | ? | — | — | announcement not found |
| BREN | 2023-10-09 | yes | BRPT, Green Era Energy | Prajogo Pangestu | IDX listing announcement |
| LOPI | 2023-10-11 (Akselerasi) | yes | 3 holders | 1 holder | IDX listing announcement |
| BRIS | 2018-05-09 | ? | — | — | the PDF exists but blocked automated fetch |

**Hit rate.**

| Item | Found | Detail |
|---|---|---|
| Lock-up yes/no and holders | **8 of 10** | 6 from IDX announcements, 2 from news |
| Effective date | **0 of 10** firm | Never in the announcement. Tentative timetables for 2 names, and AMMN's slipped: listing was planned for 07-05 and happened on 07-07 |
| Expiry date reported as such | 2 of 10 | Only the mega-IPOs get "lock-up berakhir" news coverage |

## 3. What the pilot changes

1. **A lock-up is not universal.** Two of the six IDX announcements read say **no** POJK-25 lock-up applies
   (PGEO, CUAN).
   - The convention proxy (listing + 6 or 8 months for every IPO) would therefore mislabel a material share of
     events. The 09-30 memo was right to call it "proxy of a proxy".
   - **Upside:** the IPOs with no lock-up are a ready-made **within-cohort control**. If young-listing
     underperformance is just as strong in no-lock-up IPOs, the supply-unlock mechanism is refuted.
   - This contrast is cheap and strong, and it **must be pre-declared before any outcome is read**.
2. **The primary source is the IDX "Pengumuman Pencatatan Efek"** for each IPO.
   - It is PIT: published on or before listing day, so expiry is knowable at listing.
   - It gives the yes/no flag, the locked holders and the voluntary pledges.
   - It does **not** give the effective date or the number of locked shares. The exception is when "all
     shareholders" are locked: the overhang is then the founder shares (NCKL 87.3%).
   - idnfinancials mirrors these as `fs3/content/announcements/{YYYY}/{TICKER}/{YYYYMMDD}_{TICKER}_IPO.pdf`,
     confirmed for 2022–2024 and linked for 2018. The idx.co.id original is behind Cloudflare.
3. **Effective date.** It comes from the final prospectus cover or OJK's effective notice. Failing that,
   estimate it as listing minus the e-IPO timetable (about 1.5–2 weeks). If that estimate is pre-declared, a
   ± few-session error is tolerable at monthly resolution.
4. **Effort is higher than the 09-30 estimate** of 1 day for 158 names.
   - The S2 gate actually passed **226** listings.
   - Manual work runs about 5 minutes per name for the announcement, plus the prospectus where the overhang
     size is needed: **about 2–3 working days**.
   - Scripted bulk download from either host is bot-guarded, and that is an **owner ToS call**. The box already
     scrapes idx.co.id (`screener/idx_scraper`), so the technical path exists.
5. **Power is the likely binding constraint.**
   - Roughly 60–70% of 226 have a lock-up, so about 140 events, clustered by month.
   - An expiry-window test has far fewer effective observations than S2's 252-session hold.
   - The D-086 stop rule (power ≥ 20%, counts only) should be computed **before** any manual sourcing beyond
     this pilot.

## 4. Governance

S2's verdict carried a frozen stop rule: "no variants, no refinement, no further looks at any window of this
data". Its next step is an **owner decision**: open {LC} and draft RC-0003, or shelve it (D-064). A lock-up test
is a new mechanism study under D-070 §1 and needs its own D-entry before a G0.

## 5. Recommended sequence (if pursued)

1. **Owner:** open {LC}, yes or no. If no, stop here and shelve this pilot.
2. **5 minutes on the box:** pull the exact 226-name S2 cohort (ticker, first bar) from the DB, names and dates
   only.
3. **Counts-only power check** under the D-086 stop rule, assuming about 65% of names have a lock-up. If it
   fires, withdraw: there is no census cost and no sourcing spent.
4. **Only if power is adequate:**
   - source the yes/no flag, holders and effective date for all 226 (manual, or scripted after a ToS ruling);
   - pre-declare the lock-up vs no-lock-up contrast;
   - then G1.

## Sources

- IDX listing announcements via idnfinancials:
  - [PGEO](https://www.idnfinancials.com/fs3/content/announcements/2023/PGEO/20230224_PGEO_IPO.pdf)
  - [CUAN](https://www.idnfinancials.com/fs3/content/announcements/2023/CUAN/20230308_CUAN_IPO.pdf)
  - [NCKL](https://www.idnfinancials.com/fs3/content/announcements/2023/NCKL/20230412_NCKL_IPO.pdf)
  - [MBMA](https://www.idnfinancials.com/ar/fs3/content/announcements/2023/MBMA/20230418_MBMA_IPO.pdf)
  - [BREN](https://www.idnfinancials.com/ar/fs3/content/announcements/2023/BREN/20231009_BREN_IPO.pdf)
  - [LOPI](https://www.idnfinancials.com/fs3/content/announcements/2023/LOPI/20231011_LOPI_IPO.pdf)
  - [BRIS announcement page](https://www.idnfinancials.com/announcement/5161/bank-brisyariah-ipo-saham-pada-mei)
- Rule: [Hukumonline on POJK 25/2017](https://www.hukumonline.com/berita/a/melihat-makna-lock-up-saham-dalam-peraturan-ojk-25-2017-lt638f27e33808e)
- GOTO/BUKA expiry: [Bisnis 2022-10-20](https://market.bisnis.com/read/20221020/192/1589853/periode-lock-up-goto-berakhir-november-cek-rekam-jejak-penguncian-buka)
- BUKA timetable: [Bisnis 2021-07-13](https://market.bisnis.com/read/20210713/7/1417037/sistem-e-ipo-belum-layani-ipo-bukalapak-buka-ini-cara-belinya)
- AMMN timetable: [Bisnis 2023-06-01](https://market.bisnis.com/read/20230601/192/1661213/jadwal-ipo-amman-mineral-ammn-penawaran-sampai-16-juni)
