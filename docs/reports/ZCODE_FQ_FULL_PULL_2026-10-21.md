# ZCODE report — full {FQ} pull, pilot check, PIT revision, push (2026-10-21 → 2026-10-25)

Brief: `ZCODE_BRIEF_FQ_FULL_PULL_AND_PIT_REVISION_2026-10-21.md` (owner approvals A1 full pull ·
A2 push · A3 propose-only PIT). Companion to `ZCODE_FQ_BACKFILL_LC_FILING_2026-10-21.md`.
All rule carry-overs held: no outcome reads on the fundamentals, token file read-only, no login,
no `auto_token.py` except its read-only `--check` where the brief names it, no `--force`, no restart.

---

## Y4. Push — DONE (2026-10-21 10:59 WIB)

- Test gate re-run before pushing (files the 5 commits touched + the four guard suites):
  `tests/test_risk_live_event.py`, `tests/test_stockbit_fin_backfill.py`,
  `tests/test_architecture_boundary.py`, `tests/test_research_data_fence.py`,
  `tests/test_db_centralization.py`, `tests/security/test_secret_hygiene.py` —
  **57 passed in 3.90s** (same count the planner verified).
- Remote had not moved (0 behind). Fast-forward push, no force:
  `ede89c7..af5d8ad  ops/hardening-2026-07-10 -> ops/hardening-2026-07-10`;
  `git ls-remote` confirms origin at **af5d8ad**.
- Pushed set: `3315e0c` (D-109/D-110), `1e0af2e` (pre-open risk fix), `ef51c7b` (probe + doc),
  `820ff98` (backfill + tests), `af5d8ad` (PIT draft + first report).
- Pre-flight for Y2 done 10:59: `/mnt/storage2tb` mounted (453G free), local `/` 111G free,
  `~/idx_external/stockbit_fin` not yet created (the pilot creates it tonight).

## Y1. Pilot — **DONE, 5/5 PASS** (executed by systemd timer 2026-10-22 19:05 WIB; validated 10-23)

**History:** the 10-21 19:05 ZCode automation died one second in on a Z.ai 429 (quota) — zero
GETs. Re-armed as the one-off systemd user timer `fq-pilot-20261022` (the standing lesson: data
pulls are OS jobs; model turns only check results). Log `logs/fin_pilot_20261022.log`:
START 19:05:01 → pre-open check OK (token 12.6h) → fetch rc=0 (30 saved, 0 missing, **30/30
HTTP 200, no 401/403/429**) → parse rc=0 (**125,192 rows, 10 tickers**) → END 19:05:52 (51 s).

Pass criteria (numbers re-verified read-only from `manifest.jsonl` + `fin.db` on 10-23):

1. **10 names × 3 statements — PASS.** 30/30 files, every file with values; `fin_files` rows
   with `n_values = 0`: none.
2. **BTEL and TRAM pre-delisting history — PASS.** BTEL Q4-2007 → **Q3-2025** (144 income
   periods); TRAM Q1-2008 → **Q3-2019** (94). Both include their delisting-era quarters.
3. **Bank layouts — PASS on parsing, one caveat.** BBCA shows the bank layout (Interest
   Income / Interest Expense rows present). PNBS parses completely (110 periods, 0 failures)
   but its **stored row labels are generic** (Total Revenue / COGS / Gross Profit — no
   Pendapatan Bunga rows): Stockbit maps PNBS through the non-bank template. The Y2 coverage
   table's bank-vs-non-bank split should therefore key on Interest Income presence, not on
   SIC/issuer type, or PNBS will count as non-bank.
4. **No 401/403/429 — PASS.** All 30 manifest statuses are 200.
5. **Parse failures — PASS.** Zero `n_values = 0` files; no anomalies to explain.

Coverage per name (min → max quarter, all three statements): ASII/BBCA/KIJA/TOTO Q1-2008→Q2-2026
(148–296 periods); TLKM Q4-2007→Q2-2026; BTEL →Q3-2025; TRAM →Q3-2019; CUAN Q4-2021→Q2-2026;
PGEO Q4-2019→Q2-2026; PNBS Q4-2011→Q2-2026.

**Full-pull extrapolation (coverage/parse stats only):** 30 GETs took 49 s wall
(**1.63 s/GET** incl. the script's 1.5 s pacing). Remaining after the pilot: **2,847 GETs ×
1.63 s ≈ 77 min** — comfortably inside the 170-min `--max-minutes` cap for Sunday's s1
(09:05), so the 13:00 s2 resume is expected to be a no-op safety net. Rows: 125,192 rows / 30
files ≈ 4.2k rows per file → **≈ 12.0M rows** expected across the full 2,877-file universe.

*(Superseded plan notes: the original `automation-1639d2f4` Y1 turn and its fallback ladder are
history — the 429 killed the first attempt; nothing else ran.)*

## Y2. Full pull — ARMED (Sunday 2026-10-25; approval A1; data steps as OS timers)

**Armed 2026-10-23 (A2):** two one-off systemd user timers run
`scripts/fin_full_pull_20261025.sh` (commit `4a56236` + the A2 review fixes):
- `fq-fullpull-20261025-s1.timer` — **Sun 2026-10-25 09:05 WIB**, tag `s1`
  (log `logs/fin_full_pull_20261025_s1.log`);
- `fq-fullpull-20261025-s2.timer` — **Sun 13:00 WIB**, tag `s2` — a resume that refuses while
  s1 still holds the flock (`~/idx_external/stockbit_fin/.pull.lock`) and no-ops when the
  pull is complete.
- Guards in the script: runs only on 2026-10-25 (never catches up on a missed window); refuses
  while the jurnal26 tape-backfill **service** is active (the A2 fix: the service state, not a
  `pgrep` substring that also matched editors/greps); token must pass `--preopen-check` (rc 0);
  ≥5G free where the raw store lands; then `fetch` — no `--force`, default 170-min cap.
- Token: `crontab -l` confirmed `40 21 * * 6,0` — Saturday 21:40 refresh ⇒ token valid to
  Sunday ~21:40, covering both sessions (s1 ends ≤ 11:55 at the 77-min extrapolation; s2 ≤ 15:50
  worst case), all clear of jurnal26's 21:05 backfill.
- Expected: ≈ 77 min for the 2,847 remaining GETs (1.63 s/GET from the pilot) → s2 is a no-op
  safety net. **Stop-and-report** rules live inside the fetcher (401/403 stop; a second 429
  backoff stops; >5% parse failures after parse).

**Scheduling limitation (history, 2026-10-21/22):** a ZCode automation could not be re-armed
(one per session; the 10-21 one died on the Z.ai 429) — which produced the standing rule this
now follows: data pulls are OS jobs. **The Sunday-afternoon/Monday model turn (parse, sha256
manifest, coverage table, archive copy, Y3 PIT v2) runs in a FRESH ZCode chat, per the runbook
below.**

### Y2 runbook (Sunday 2026-10-25, daytime; approval A1)

1. **Pre-checks:** `date` (Sunday, before ~20:30); token expiry read-only —
   `venv/bin/python3 auto_token.py --check` (explicitly allowed by the brief Y1/Y2; reads only) or
   decode `.stockbit_token` JWT `exp` directly; expect the Saturday-21:40 token valid to ~21:40 —
   if the check shows otherwise, STOP and report, never log in. No jurnal26 backfill process
   running (`ps aux | grep -i` jurnal26/backfill — the nightly tape job runs 21:05→06:30 and must
   be done). `df -h ~/idx_external` (≥ a few GB free) and `mountpoint -q /mnt/storage2tb`.
2. **Dry-run first:** `venv/bin/python3 scripts/stockbit_fin_backfill.py fetch --dry-run` — expect
   ≈ 2,847 to go (2,877 minus the pilot's 30).
3. **Run** (background, log teed to `~/idx_external/stockbit_fin/fetch_20261025.log`):
   `venv/bin/python3 scripts/stockbit_fin_backfill.py fetch` — **no `--force`**, default
   `--max-minutes 170` per session. It is resumable: if the cap or token stops it, and the window
   still allows (before ~20:30, to stay clear of the 21:05 jurnal26 job and the 21:50 code
   refusal), re-run `fetch`; it skips done files. Never re-login.
4. **Stop and report — no retry loop — on any of:** 401 or 403 (the script stops itself); a
   **second** 429 backoff event (two separate `backing off` log lines for 429 → kill the fetch,
   report); after parse, **>5% parse failures** (fin_files rows with n_values = 0).
5. **Then:** `venv/bin/python3 scripts/stockbit_fin_backfill.py parse`; build the sha256 pin
   manifest for `raw/*` + `fin.db` (+ `manifest.jsonl`) →
   `~/idx_external/stockbit_fin/SHA256SUMS_2026-10-25.txt` (sha256sum format, sorted).
6. **Coverage table** (coverage/parse stats ONLY — no return, spread, IC, or join to prices):
   tickers × statements present; quarters per ticker (min/median/max; how many tickers ≥ 40
   quarters); **how many of the 41 stale/delisted names have history** (recompute the 41 the same
   way: last `ohlcv` bar < max-date − 90 d); bank vs non-bank layout counts (statement-section rows
   containing e.g. `Interest Income` / `Pendapatan Bunga`).
7. **Off-SSD copy:** `mkdir -p /mnt/storage2tb/idx-archive/stockbit_fin/2026-10-25/`; copy `raw/`,
   `manifest.jsonl`, `SHA256SUMS_2026-10-25.txt`, `fin.db`; recompute sha256 on the mount and
   compare both sides (report any mismatch; delete nothing; local copy stays).
8. **Record** run log summary, stop reasons, coverage table, the SHA256SUMS file's own sha256, and
   the archive verification in this report's Y2 section. Commit code/doc changes + coverage (NOT
   data — it lives outside the repo). **Push** (A2; never force; remote moved → fetch+rebase; on
   conflict stop and report).

### Y3 runbook (after Y2's data exists; approval A3 — propose only)

Write `P-M/data_acquisition/11_FQ_PIT_RULE_DRAFT_V2_2026-10-25.md` (sibling; original untouched):

1. **H1 basis:** recommend (a) uniform 31 Oct lag or (b) lag by each issuer's actual attestation if
   any field shows it — with the reason. Try for a sample count of audited H1s from public
   announcement titles/news (idx.co.id is blocked from this box; use news/secondary and say what
   the sample is). If unknowable, recommend (a) as the conservative default and say why.
2. **Buffer:** justify the +1 month against late filers with observable evidence — IDX suspension
   waves (59 names end-Jul 2025, 46 names Jan 2025, 39 names Jan 2024, Rp 50/150 jt fine ladders;
   sources already in session context) — no returns.
3. **COVID 2020:** find the primary texts of the OJK/IDX 2020 deadline relaxations (ojk.go.id is
   reachable from this box) and give the extended lags for the affected periods; if only
   press-release-level sources are reachable, say exactly that.
4. **Restatement check (needs Y2 data):** pick ≈ 20 issuer-periods (banks, large and small caps,
   pre- and post-2015) from `fin.db`; compare stored values against originally published statements
   via reachable PDFs (idx.co.id blocked — issuer IR sites, OJK disclosure portals; report
   reachability honestly); difference rate. Data-vs-data only; reads no outcome.
5. **Blocked texts:** record the two texts missing from this box — (i) the Kep-36/PM/2003 primary
   text (Regime A 2008–2011), (ii) the official Kep-00087/BEI/12-2025 PDF and the pre-2025 I-E
   quarterly article — with URLs
   (https://www.idx.co.id/Media/gmddcpw4/signed_peraturan_nomor_ie_tentang_kewajiban_penyampaian_informasi.pdf;
   the OJK X.K.2 page pattern for the 2003 decision) and what each settles.
6. **End with a "decisions for the owner" list.** Commit and push. **No freeze, no D-entry, no {FQ}
   mechanism entry.**
