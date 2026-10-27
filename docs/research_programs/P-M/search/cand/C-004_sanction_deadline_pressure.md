# C-004 · BEI filing-sanction deadlines as forced-attention/forced-selling pressure

**Status: PROPOSE-ONLY. Likely UNDERPOWERED at every floor the program would accept — recommend record-only.**

## 1. Mechanism
BEI escalates sanctions for late financial filings (Peringatan Tertulis I/II/III, fines, then **suspension from
day 91**). Escalation is a public, rule-based calendar: institutions with mandates excluding suspended names must
sell before suspension binds; retail attention spikes. Prediction: sanctioned names underperform the book in the
window between the announced sanction tier and the day-91 suspension. Structural (a rule, not a pattern); the
barrier is durable while BEI's enforcement regime stands. M4.2 forced deleveraging / M5.1 salience.

## 2. Falsifiable prediction
Cohort: names appearing in the late-filer/sanction lists at tier ≥ PT-II (escalation with a dated deadline).
Outcome: equal-weight cohort excess vs liquid book, event month → +1m/+3m, negative. Kill: cohort excess ≥ 0 or
n < 20 events (the HYP-PM-0018 stop precedent).

## 3. Data
`P-M/data_acquisition/12_FQ_LATE_FILERS_2026-10-26.csv` (built 10-26): 417 rows, 142 tickers, 6 periods
(FY2024→FY2025-Q), all [S] news-sourced, sanction tiers and article dates. Depth: news coverage is 2025-04→;
pre-2025 sanction waves are NOT systematically in the CSV (reconstructable only from BEI announcements, which are
blocked from this machine → owner-browser item). fin.db filing dates do not exist (the day-30 question of H3.2
was unanswerable for the same reason). PIT: article date is the availability date; tier escalation dates inside
articles are sometimes partial.

## 4. Counts and prior-only power
142 tickers × ≤6 periods ≈ at most ~300 issuer-period events, concentrated in 2 sanction cycles (Apr–Jun 2025,
Jun 2026) → ~2-3 event months. Monthly formations available: **< 24**. SE on a 24-month rank panel ≈ 2.0%/mo →
MDE80 ≈ 5%/mo; power at any plausible drag (0.5–2%/mo) < 10%. **UNDERPOWERED — same class as tenders (C5) and
lock-ups (C8).** The 2026 wave (day-91 suspensions from 2026-06-30) offers at most a handful of extra events.

## 5. Non-overlap proof
Nearest rows: **{FQ} PIT deadlines (D-111)** — uses filing deadlines as an AVAILABILITY rule, never as a signal;
this is the first deadline-as-signal design. **C8 lock-up** (a different forced-supply calendar, withdrawn on
power); **C6 {CF} issuance** (supply event, null). No overlap with any registered arm.

## 6. Cost / capacity
Cohort is small-cap heavy; ADV gate would cut it hard; short horizon → turnover cost dominant. Moot given §4.

## 7. Distinctness from the live book
None — orthogonal. But per the G0 stop-rule precedents (D-080, D-087, D-094, D-097, D-102, D-110, PEAD), this
arm would very likely be withdrawn at its own G0.

**Recommendation: do NOT register. Keep as a monitored list** (the CSV already exists; a prospective recorder
alongside the {FQ} PIT machinery costs nothing and builds the cohort for a future era with more cycles).
