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

## Y1. Tonight's pilot — NOT RUN YET (automation fires 19:05 WIB; window 19:00–21:50)

- The session's automation (`automation-1639d2f4`, updated today) runs the whole of Y1 tonight:
  10-name fetch + parse (no `--force`), the pilot table + extrapolation in the companion report, the
  A1 paragraph update, validation of the five pass criteria, commit and push (A2). If the pilot had
  already run by the time it fires, it skips the fetch and validates only.
- **Pass criteria (to be recorded here):** (1) all 10 names × 3 statements; (2) BTEL/TRAM
  pre-delisting history; (3) bank layout parses (BBCA, PNBS); (4) no 401/403/429; (5) parse
  failures 0 or each explained. — pending.
- Fallback ladder per the brief: if tonight's window is missed entirely, Thursday 2026-10-22 after
  19:00, token checked read-only first.

## Y2. Full pull — NOT RUN YET (approval A1; **cannot be scheduled from this session** — runbook below)

**Scheduling limitation (harness, 2026-10-21 11:0x WIB):** this session is already bound to the
tonight-19:05 automation, and the scheduler refuses a second automation in the same session
("Cannot create a scheduled task inside a session that already belongs to a scheduled task"), and a
scheduled run may not create or reconfigure further automations. So Sunday's runs cannot be armed
from here. **To execute Sunday, open a fresh ZCode chat around 08:50 WIB, 2026-10-25, and point it at
the runbook below** (it may run Y2 live in that session — ~2 h — then Y3, or schedule within it).

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
