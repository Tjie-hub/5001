# HANDOFF → Dell ZCode — operational start of FWD-PM-FADE-001 + pulse confirmation (2026-09-21)

**From:** ZCode (Windows, tjiejet) · **For:** ZCode on the Dell Ubuntu machine (production DB host)
**Repo:** `idx-walkforward-5001` · branch `ops/hardening-2026-07-10` · HEAD `24c106df7dd4d709279acf715a932210c8269987` (2026-09-21 08:52 WIB)
**Self-contained** — no prior conversation assumed. Everything below is already committed; this file just routes the next actions.

---

## 1. What happened on the Windows side since your last sync

1. **Your C7 reconciliation handoff was applied verbatim** — commit `898433d` (2026-09-20): registry
   main row, family-slot row, notes paragraph, header bump. MD5 of your handoff verified before
   applying; every cited number cross-checked against `g1_harness/C7_EXECUTION_REPORT_2026-09-14.md`.
   Consider that thread closed.
2. **Price-Reversal {R1} family OPENED; HYP-PM-0012 REGISTERED; FWD-PM-FADE-001 OPEN** — commit
   `24c106d` (2026-09-21), Owner-approved, decision **D-052**, package
   `forward_fade/OWNER_DECISION_PACKAGE_R1_OPEN_2026-09-21.md` (Option A). See `HYPOTHESIS_REGISTRY.md`
   (new row + family row + notes) and `P-M/HYP-PM-0012_REGISTERED.md`.
   - Registration protocol sha256 (pinned, do not modify the file):
     `e195967260888315028f33bbbea558ce2f8e02a9d049338cb655313c36a108c5`
   - Ledger `forward_fade/ledger.json`: opened empty, `opened_utc 2026-09-21T01:46:55+00:00`
     (= 08:46:55 WIB, pre-open), `first_eligible_entry 2026-09-22`.
   - Note: the whole `forward_fade/` dir (your 2026-09-20 work) came under version control with this
     act — spec frozen exactly as you wrote it, zero parameters touched.
3. Commit `7a54b27`: the Owner decision package that preceded the act (audit trail only).

## 2. PRIMARY TASK — start daily signal recording for FWD-PM-FADE-001

Mirror `forward_regime/run_formation.py` (read-only against the production DB via `data.db.connect`,
run daily after the settled-bar write, append-only ledger, refuse anything before `opened_utc`).
Frozen spec: `forward_fade/PROTOCOL.md` §2; the in-sample machinery to reuse verbatim is
`forward_fade/scripts/fade_failed_breakdown.py` (SHA256SUMS verified 2026-09-21).

- **Signal (session t, evaluated on t's settled bar):** `low(t) < lo20(t)` AND `close(t) > lo20(t)`,
  where `lo20` = prior-20-session rolling low shifted 1 — on the per-row threshold universe:
  `adv20 >= Rp 1e9` (shifted 1, min_periods 15), `close >= Rp 50`, >= 25 prior sessions,
  `volume > 0` on the row, >= 18 of trailing 20 sessions traded. Full per-ticker calendar frame —
  never drop rows before rolling windows.
- **Entry:** NEXT session's open. **Horizons:** fixed h ∈ {5,10,20} (exit at close of entry+h−1).
  **Costs:** 0.60% RT. **Benchmarks (both, per signal):** IHSG over the identical window; equal-weight
  liquid book (same eligibility at entry, same convention). Contamination guard: void a signal if any
  session in its window has `|ret| > 35%` or a recorded split.
- **Ledger discipline:** one object per signal, written when its h=20 leg closes (or flagged censored
  at data end); schema is in `ledger.json`; **never back-fill** — the runner must refuse any
  signal_date earlier than `opened_utc` (the run_formation.py precedent does exactly this).
- **Timing:** today's session (Mon 2026-09-21) is already a valid signal day (the act predates the
  open); its entries occur tomorrow (2026-09-22 = `first_eligible_entry`). So the first recorder run
  is TONIGHT after the settled write.
- **Sanity anchors:** in-sample rate ≈ 200 signals/month, ≈ 95% of days carry ≥ 1 signal (12,131
  signals / 1,151 dates / 757 tickers). A zero-signal day is possible; a signal-free MONTH trips
  falsification condition §5.5 (<100 distinct signal-dates by month 12) — just record honestly.
- **Do not modify** `PROTOCOL.md` (sha-pinned in D-052 and the ledger) or the frozen script — any
  change requires a dated supersession via an Owner act.

Commit cadence: same style as your REGIME-002 ledger commits, e.g.
`docs(P-M): FWD-PM-FADE-001 record <date> -- N signals, M closed, K censored`.

## 3. SECONDARY TASK — close the REGIME-002 pulse question

Windows could not distinguish "no signal on Fri 2026-09-18" from "the formation job didn't run":
`forward_regime/ledger.json` is unchanged since the 2026-09-17 amendments (still 0 trades) and the
Windows DB is intentionally stale. From the Dell side: (a) confirm whether `run_formation.py` ran
after Friday's settled write; (b) if it ran and emitted nothing, just note that (0-trade openings are
legitimate — REGIME-001 died of exactly the opposite problem); (c) if it did NOT run, restart the
daily job — the missed observation is simply missed; the no-back-fill rule stands, no catch-up insert.

## 4. Do NOT touch (each is registered/frozen)

- `forward_regime/PROTOCOL.md` (FWD-PM-REGIME-002, HYP-PM-0010) — three observability amendments are
  already the recorded state.
- `forward_fade/PROTOCOL.md` + `scripts/fade_failed_breakdown.py` (HYP-PM-0012, sha-pinned).
- The vol overlay (`forward_volex/` — unregistered by design, no slot).
- `forward_trend2/`, `forward_trend3/` remain DRAFTS — TREND-003's "episode-onset" variant has been
  *offered* to the Owner but NOT approved; don't build it unless the Owner says so (and if so, its
  §6 multiplicity accounting applies — 001/002/003 are one adaptive family).
- No short-side reading of FADE-001's signal, ever — registered anti-edge/avoidance only.

## 5. Open items (Owner-level, unchanged)

- `g1_harness/` backlog (~35 files uncommitted since `bf9f8ec`) still awaits per-file provenance
  triage — your context on those files is better than ours. Deliberately NOT bundled into any
  Windows commit.
- Mimosa pre-commit hook keeps reporting `scanner_enobufs` on Windows commits (docs-only so far);
  a full audit re-run is owed at some point.

## 6. Environment note

The stale `.git/index.lock` mount quirk happened on Windows too (2026-09-21) — markers
`.git/index.lock.stale-20260921*` are there. Same rule as your handoff recorded: `mv` the lock
aside, never `rm`.

**Definition of done:** tonight's FADE-001 recorder run committed (or a documented zero-signal day),
plus a one-line answer to §3's REGIME-002 question, both visible in the synced repo.
