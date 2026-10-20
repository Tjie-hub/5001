# FWD-PM-BANK-001 — deviation log

Append-only. Never rewritten. Every entry is dated and states what changed, why, and whether any outcome was
visible at the time (PROTOCOL.md: "Changes only via an append-only deviation_log.md entry").

---

## DEV-001 · 2026-10-20 · the benchmark book uses the bank leg's own void rule

**Authority.** DECISION_LOG D-104. Owner instruction 2026-10-19 ("fix") on the strategy logic check
(`docs/audit/IDX_FULL_AUDIT_2026-10-19.md` §5, T3).

**What changed.** `run_recorder.py` `load()`: a member of the equal-weight liquid book (ADV20 >= Rp 10 B)
is left out of a signal date's book when its window t+1 .. t+10 holds a price-step event (`stocksplit`,
`stock_reverse`, `rightissue`, `bonus` in `corporate_action_events`, or a split in `corporate_actions`)
or a session move beyond 35%: the void rule PROTOCOL §2 already applies to the bank leg. Test:
`tests/test_forward_bank_recorder.py::test_book_leaves_out_a_member_whose_window_holds_a_price_step`.
`SHA256SUMS.txt` updated for `run_recorder.py`: `c8e440c47adfd4a8…` → `d7d508aab79d2251…` (PROTOCOL.md unchanged).

**Why.** Raw prices step down at a split or rights ex-date. The bank leg was voided on such steps, the book
was not, so a member's step entered the benchmark as a return and lowered it, which raises the bank's
excess. On 2021-07 .. 2026-09 history, 42% of signal dates had at least one such member; the mean effect is
small but the July 2026 cluster (RAJA, RMKE, MLPT splits; COCO, BNBR, PADI rights) moved the book by up to
1.85 pp, against a GO bar of +0.50%.

**Was any outcome visible?** No. `ledger.json` holds **0 events** (sha256 `5005f691…`); the first window
closes 2026-10-22. The measurement above used only the benchmark on dates before 2026-10-01: 1,245 dates,
519 changed, mean shift +0.003 pp, largest +1.85 pp. No bank event and no forward-window value was read.

**What did NOT change.** The signal, de-dup, entry/exit, the bank leg's own void rule, cost, endpoints,
decision rule, IHSG benchmark and ledger schema. The study evidence (PROTOCOL §5) was computed with the
unscreened book; the change is blind and its average effect on history is near zero.
