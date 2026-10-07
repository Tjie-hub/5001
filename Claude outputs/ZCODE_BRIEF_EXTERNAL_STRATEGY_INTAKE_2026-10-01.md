# ZCODE BRIEF — Intake of the external YouTube/NotebookLM strategy (idx-walkforward-5001)

**Issued:** 2026-10-01, by Claude (planner role, Owner's request) · **Target:** zcode on Ubuntu box
· **Repo:** `/home/tjiesar/10 Projects/idx-walkforward-5001` · **Branch:** `spec/external-strategy-intake`
(off current working branch; docs-only until Phase B)

## 0. Read first — why this is NOT "clone the strategy into 5001"

The Owner's original wording was "clone the external strategy into 5001". Under this repo's frozen
architecture (CLAUDE.md: Edge Registry, Gatekeeper, `research/` fence) a strategy cannot be dropped
into `engine/strategies.py` and go live. It enters as a **hypothesis**, goes through the gatekeeper
(REJECT / WATCHLIST / PROMOTE), then forward test, then a receipt-bound registry entry. A direct
clone would violate invariants #9 and #10. So this brief is an **intake**, not an implementation.

**Priority:** the 2026-09-30 redirect note stands — **P0/P1/P3/P4 come before this.** P1 (research
fence) *blocks all research work*, so Phase B below cannot start until P1 has landed. If P0/P1 are
still open when you pick this up, do Phase A only, then return to P0/P1.

## 1. Known blocker — the strategy source is missing

Earlier retrieval of the YouTube / NotebookLM material **failed**; no transcript, notes, or rules
exist anywhere in the repo (grep for notebooklm/youtube/external strategy: nothing). Do not
reconstruct the strategy from memory or guess its rules.

**Owner must supply, before Phase A can finish** (any one is enough):
- YouTube URL(s) + exported transcript, or
- NotebookLM notebook export / source notes, or
- Owner's own written summary of entry / exit / filters / timeframe.

Put the raw material in `docs/research_intake/external_strategy_2026-10/SOURCE/` (new dir, verbatim,
never edited afterward). If it is not there when you start, stop and write
`BLOCKED_NO_SOURCE.md` in that dir naming exactly what is missing. Do not proceed on assumptions.

## 2. Phase A — Spec only (safe now; docs-only, touches no code)

Produce `docs/research_intake/external_strategy_2026-10/SPEC.md` containing, **as stated by the
source, with quote/timestamp references**:

1. Name, author/channel, date, claimed market + timeframe (is it even IDX daily-bar compatible?).
2. Entry rule, exit rule (TP/SL/time/trailing), filters, position sizing, regime assumptions.
3. Every parameter and whether the source gave it or left it ambiguous. List ambiguities as open
   questions for the Owner — do **not** fill them in.
4. Claimed performance, with how the source measured it (in-sample? survivorship? costs? slippage?).
   Treat all of it as unverified marketing until our own pipeline says otherwise.
5. Data requirements vs. what `data/walkforward.db` + Stockbit tables actually have (bars, volume,
   flow, fundamentals). Flag anything we cannot compute point-in-time.
6. Overlap check: which existing strategy family it resembles (NR7/ORB/Inside Bar/TFB/Vol-Weighted/
   Momentum/VWAP/Conservative Confirm). A near-duplicate belongs in an existing multiplicity family,
   not a new one — read `docs/research_programs/HYPOTHESIS_REGISTRY.md` and `FAILURE_REGISTRY.md`
   first to confirm it hasn't been tried and rejected already.

Then a pure-function **draft** `strategy_fn` as a spec-level pseudo-code block inside SPEC.md.
No `.py` in `engine/` or `research/` in this phase.

## 3. Phase B — Register as a hypothesis (only after P1 lands)

1. Re-read `docs/RESEARCH_MASTER_PLAN.md` §3.1 and `docs/research_os/HYPOTHESIS_LIFECYCLE.md`.
2. Pick the multiplicity family (never narrow/split an existing active family). Frozen protocol
   written **before** any backtest result is seen: universe, as-of-date ADV filter (not today's ADV —
   see P4-1), costs per the modeled-cost approach, ARA/ARB fillability (P4-2) if P3/P4 landed.
3. Append (never edit) the entry to `HYPOTHESIS_REGISTRY.md` and log the decision in
   `DECISION_LOG.md` as a new dated entry.
4. Implement the strategy function **in `research/`**, not `engine/`; run the gatekeeper. Report the
   decision verbatim, including REJECT. A REJECT goes to `FAILURE_REGISTRY.md` — that is a valid,
   useful outcome, not a failure of this task.
5. Only a PROMOTE + forward-test evidence yields a registry entry; production reads it solely via
   `engine/registry_loader.py`.

## 4. Boundaries

- Never touch `docs/research_programs/P-M/**`, any `ledger.json`, or frozen protocols of in-flight
  hypotheses. Never edit existing DECISION_LOG / HYPOTHESIS_REGISTRY / FAILURE_REGISTRY entries.
- Do not add the strategy to `scheduler.py`, the watchlist UI, paper trade, or Telegram. No live path.
- Do not touch `.env`, `.stockbit_token`, or the production DB. `git pull --rebase`, never force-push.
- If Mimosa returns inconclusive, check `.mimosa/history/run-*.json` `errors` before assuming a
  security block (see the 2026-09-30 note).

## 5. Deliverables

- Phase A: `SOURCE/` (verbatim) + `SPEC.md` + a short list of open questions for the Owner — or
  `BLOCKED_NO_SOURCE.md`.
- Phase B (post-P1): hypothesis registered, protocol frozen, gatekeeper decision reported, with
  before/after numbers where any existing study was re-run.
- A one-paragraph handoff stating plainly: promoted / watchlist / rejected / blocked, and why.
