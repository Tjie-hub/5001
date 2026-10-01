# BLOCKED — NO SOURCE

**Date:** 2026-10-01 · **Task:** ZCODE_BRIEF_EXTERNAL_STRATEGY_INTAKE_2026-10-01.md (Phase A)
**Status:** BLOCKED at the Phase A gate. No SPEC.md produced. **Nothing was reconstructed or
guessed** — per the brief, Phase A cannot start without the verbatim source, and Phase B is
additionally blocked behind P1 (research fence), which has not landed.

## What is missing (Owner must supply ANY ONE of these, placed verbatim in this SOURCE/ dir)

1. **YouTube URL(s) + exported transcript** of the strategy video(s), or
2. **NotebookLM notebook export / source notes** for the strategy, or
3. **Owner's own written summary** of the strategy: entry rule, exit rule (TP/SL/time/trailing),
   filters, timeframe, position sizing.

Any one is enough to start Phase A. Rules will never be inferred from memory, a video title, or a
channel name.

## What was checked before declaring BLOCKED (2026-10-01, XPS-13 worktree)

- `docs/research_intake/` did not exist — created now, with only this file in it.
- Repo-wide grep for `notebooklm`, `youtube.com`, `youtu.be` across .md/.txt/.yaml/.json: hits are
  only the brief itself, P-M methodology/priors memos, DECISION_LOG, and STRATEGY_AUDIT — none is
  a transcript, export, or rule summary of the external strategy.
- Candidate material found in the untracked `Claude outputs/` dir was inspected and classified as
  **in-house session output, not the external source**:
  - `RULE_FIRST_PROTOCOL_2026-09-24.md` — the D-055 rule-first methodology (already adopted;
    lives in `research/rulecard/`), not a strategy.
  - `BRPT_PATTERN_PLAYBOOK_2026-09-25.md` — exploratory single-ticker BRPT pattern study.
  - `parabolic_bottom.{pine,py}`, `staircase_bottom.{pine,py}`, `exhaustion_study_2026-09-25/` —
    TradingView/python scanners derived from prior in-house backtests, self-labelled
    "NO reliable edge. Visual scanner only."

  If the Owner actually meant one of these to be the "external strategy", say so and copy the
  file(s) into this SOURCE/ dir verbatim — do not point at them in place; this dir is the intake
  of record.

## What happens when the source arrives

Phase A (`SPEC.md`, docs-only, on branch `spec/external-strategy-intake`) per brief §2: named
rules with quote/timestamp references, parameter ambiguity list as open questions, claimed
performance treated as unverified marketing, data-requirements check against
`data/walkforward.db`, overlap check against HYPOTHESIS_REGISTRY/FAILURE_REGISTRY families.
Phase B stays gated behind P1 (research fence cutover) per brief §3 and TODO.md sequencing.
